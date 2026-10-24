import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.database import get_db
from app.models.models import (
    CaseResult,
    Chunk,
    Configuration,
    EvaluationRun,
    ReviewerOverride,
    TestCase
)
from app.schemas.schemas import (
    CaseResultResponse,
    EvaluationRunCreate,
    EvaluationRunDetailResponse,
    EvaluationRunResponse,
    ReviewerOverrideCreate,
    ReviewerOverrideResponse
)
from app.services.diagnosis import diagnose_case
from app.services.failure_injection import apply_failure_injection
from app.services.metrics import (
    compute_abstention_correctness,
    compute_citation_correctness,
    compute_exact_match,
    compute_hit_rate_at_k,
    compute_mrr,
    compute_normalized_match,
    compute_numeric_match,
    compute_retrieval_recall_at_k
)
from app.services.providers import get_llm_provider
from app.services.rag import ask_question

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])

def _run_to_response(run: EvaluationRun) -> EvaluationRunResponse:
    snap = {}
    try:
        snap = json.loads(run.configuration_snapshot_json)
    except Exception:
        pass
    sim_cfg = None
    try:
        if run.simulation_config_json:
            sim_cfg = json.loads(run.simulation_config_json)
    except Exception:
        pass

    return EvaluationRunResponse(
        id=run.id,
        name=run.name,
        configuration_id=run.configuration_id,
        configuration_snapshot=snap,
        test_case_count=run.test_case_count,
        evaluated_case_count=run.evaluated_case_count,
        is_simulated=run.is_simulated,
        simulation_config=sim_cfg,
        llm_judge_enabled=run.llm_judge_enabled,
        provider=run.provider,
        model_name=run.model_name,
        status=run.status,
        pass_rate=run.pass_rate,
        mean_recall=run.mean_recall,
        mean_mrr=run.mean_mrr,
        mean_groundedness=run.mean_groundedness,
        pass_threshold=run.pass_threshold,
        error_message=run.error_message,
        created_at=run.created_at,
        completed_at=run.completed_at
    )

def _case_result_to_response(cr: CaseResult) -> CaseResultResponse:
    rec_k = {}
    hit_k = {}
    cits = []
    ret_chunks = []
    r_facts = {}
    try:
        rec_k = json.loads(cr.recall_k_json) if cr.recall_k_json else {}
        hit_k = json.loads(cr.hit_rate_k_json) if cr.hit_rate_k_json else {}
        cits = json.loads(cr.citations_json) if cr.citations_json else []
        ret_chunks = json.loads(cr.retrieved_chunks_json) if cr.retrieved_chunks_json else []
        r_facts = json.loads(cr.rule_facts_json) if cr.rule_facts_json else {}
    except Exception:
        pass

    overrides_list = [
        ReviewerOverrideResponse.model_validate(o) for o in (cr.overrides or [])
    ]

    return CaseResultResponse(
        id=cr.id,
        run_id=cr.run_id,
        test_case_id=cr.test_case_id,
        question=cr.question,
        question_type=cr.question_type,
        reference_answer=cr.reference_answer,
        generated_answer=cr.generated_answer,
        abstained=cr.abstained,
        citations=cits,
        retrieved_chunks=ret_chunks,
        recall_k=rec_k,
        hit_rate_k=hit_k,
        mrr=cr.mrr,
        exact_match=cr.exact_match,
        normalized_match=cr.normalized_match,
        numeric_match=cr.numeric_match,
        citation_correctness=cr.citation_correctness,
        abstention_correctness=cr.abstention_correctness,
        judge_correctness=cr.judge_correctness,
        judge_faithfulness=cr.judge_faithfulness,
        judge_relevance=cr.judge_relevance,
        judge_rationale=cr.judge_rationale,
        category=cr.category,
        rule_fired=cr.rule_fired,
        rule_facts=r_facts,
        suggested_debugging_step=cr.suggested_debugging_step,
        confidence=cr.confidence,
        model_diagnosis_explanation=cr.model_diagnosis_explanation,
        is_simulated=cr.is_simulated,
        error=cr.error,
        overrides=overrides_list,
        created_at=cr.created_at
    )

@router.get("", response_model=List[EvaluationRunResponse])
def list_evaluations(db: Session = Depends(get_db)):
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).all()
    return [_run_to_response(r) for r in runs]

@router.get("/{run_id}", response_model=EvaluationRunDetailResponse)
def get_evaluation(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    results = db.query(CaseResult).filter(CaseResult.run_id == run_id).all()
    res = EvaluationRunDetailResponse.model_validate(_run_to_response(run))
    res.results = [_case_result_to_response(cr) for cr in results]
    return res

@router.post("/run", response_model=EvaluationRunResponse)
def create_evaluation_run(payload: EvaluationRunCreate, db: Session = Depends(get_db)):
    """
    Executes a complete evaluation run:
    1. Loads configuration snapshot.
    2. Selects approved test cases (or unverified if requested).
    3. Runs retrieval and grounded generation for each test case.
    4. Applies optional failure injection at retrieval time (flagged SIMULATED).
    5. Calculates deterministic metrics (Recall@K, Hit Rate@K, MRR, EM, F1, Numeric, Citations, Abstention).
    6. Executes optional LLM judge with structured validation and retry.
    7. Evaluates pure 8-step failure diagnosis decision tree.
    8. Persists all records reproducibly.
    """
    config = db.query(Configuration).filter(Configuration.id == payload.configuration_id).first()
    if not config:
        # Fallback to default config or create one
        config = db.query(Configuration).filter(Configuration.is_default == True).first()
        if not config:
            config = Configuration(
                id=f"cfg_{uuid.uuid4().hex[:8]}",
                name="Default Balanced RAG",
                description="Default configuration with 800-char chunks and top-3 retrieval",
                chunk_size=800,
                chunk_overlap=150,
                top_k=3,
                similarity_threshold=0.0,
                embedding_model=settings.EMBEDDING_MODEL,
                llm_model=settings.LLM_MODEL,
                is_default=True
            )
            db.add(config)
            db.commit()
            db.refresh(config)

    # Filter test cases
    tc_query = db.query(TestCase)
    if payload.test_case_ids:
        tc_query = tc_query.filter(TestCase.id.in_(payload.test_case_ids))
    elif not payload.include_unverified:
        tc_query = tc_query.filter(TestCase.status == "approved")

    test_cases = tc_query.all()
    if not test_cases:
        raise HTTPException(
            status_code=400,
            detail="No eligible test cases found for evaluation. Approve test cases or toggle 'Include unverified'."
        )

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    is_simulated = bool(payload.failure_injection and payload.failure_injection.enabled)
    run_name = payload.name or f"Run #{run_id[-4:]} ({'SIMULATED' if is_simulated else 'Baseline'})"

    # Pre-fetch all available chunks for distractor pool if failure injection is active
    all_chunks_raw = []
    if is_simulated:
        all_c_recs = db.query(Chunk).limit(100).all()
        all_chunks_raw = [
            {"chunk_id": c.id, "page": c.page, "text": c.text, "document_id": c.document_id}
            for c in all_c_recs
        ]

    config_snapshot = {
        "id": config.id,
        "name": config.name,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "top_k": config.top_k,
        "similarity_threshold": config.similarity_threshold,
        "embedding_model": config.embedding_model,
        "llm_model": config.llm_model,
        "prompt_template_version": config.prompt_template_version,
        "abstention_enabled": config.abstention_enabled,
        "k_values": payload.k_values
    }

    eval_run = EvaluationRun(
        id=run_id,
        name=run_name,
        configuration_id=config.id,
        configuration_snapshot_json=json.dumps(config_snapshot),
        test_case_count=len(test_cases),
        evaluated_case_count=0,
        is_simulated=is_simulated,
        simulation_config_json=json.dumps(payload.failure_injection.model_dump()) if payload.failure_injection else None,
        llm_judge_enabled=payload.llm_judge_enabled,
        provider=settings.LLM_PROVIDER,
        model_name=config.llm_model,
        status="running",
        pass_threshold=payload.pass_threshold
    )
    db.add(eval_run)
    db.commit()

    # Execute cases
    passed_count = 0
    total_recall = 0.0
    total_mrr = 0.0
    case_results: List[CaseResult] = []

    for tc in test_cases:
        expected_ev = []
        try:
            if tc.expected_evidence_json:
                expected_ev = json.loads(tc.expected_evidence_json)
        except Exception:
            pass

        # 1. Ask RAG
        demo_cits = None
        try:
            if tc.demo_citations_json:
                demo_cits = json.loads(tc.demo_citations_json)
        except Exception:
            pass

        # Pre-retrieve passages to allow controlled failure injection
        from app.services.embeddings import embed_query
        from app.services.vectorstore import query_collection
        q_vec = embed_query(tc.question)
        raw_passages = query_collection(
            query_embedding=q_vec,
            top_k=config.top_k,
            collection_name="default_rag"
        )

        # Apply failure injection if configured
        final_passages = raw_passages
        if is_simulated:
            final_passages = apply_failure_injection(
                retrieved_passages=raw_passages,
                expected_evidence=expected_ev,
                all_available_chunks=all_chunks_raw,
                injection_config=payload.failure_injection
            )

        rag_resp = ask_question(
            question=tc.question,
            top_k=config.top_k,
            similarity_threshold=config.similarity_threshold,
            custom_passages=final_passages,
            model_name=config.llm_model,
            demo_answer_fallback=tc.demo_answer,
            demo_citations_fallback=demo_cits
        )

        retrieved_list = [p.model_dump() for p in rag_resp.retrieved_passages]

        # 2. Compute Deterministic Metrics
        recall_k_map = {}
        hit_rate_k_map = {}
        for k_val in payload.k_values:
            recall_k_map[str(k_val)] = compute_retrieval_recall_at_k(retrieved_list, expected_ev, k=k_val)
            hit_rate_k_map[str(k_val)] = compute_hit_rate_at_k(retrieved_list, expected_ev, k=k_val)

        mrr_val = compute_mrr(retrieved_list, expected_ev)
        em_val = compute_exact_match(rag_resp.answer, tc.reference_answer)
        f1_val = compute_normalized_match(rag_resp.answer, tc.reference_answer)
        num_val = compute_numeric_match(rag_resp.answer, tc.reference_answer) if tc.question_type == "numerical" else None
        cit_corr = compute_citation_correctness(rag_resp.citations, expected_ev, retrieved_list)
        abs_corr = compute_abstention_correctness(tc.should_abstain, rag_resp.abstained)

        # Primary recall for summary stats (e.g. at top_k or default 3)
        primary_k = str(min(payload.k_values, key=lambda x: abs(x - config.top_k)))
        case_recall = recall_k_map.get(primary_k, 0.0)
        total_recall += case_recall
        total_mrr += mrr_val

        # 3. Optional LLM Judge
        judge_corr = None
        judge_faith = None
        judge_rel = None
        judge_rat = None
        judge_err = False

        if payload.llm_judge_enabled and not rag_resp.is_demo:
            try:
                judge_provider = get_llm_provider(model=config.llm_model)
                judge_prompt = (
                    f"QUESTION: {tc.question}\n"
                    f"REFERENCE ANSWER: {tc.reference_answer}\n"
                    f"GENERATED ANSWER: {rag_resp.answer}\n"
                    f"RETRIEVED CONTEXT:\n{rag_resp.prompt_used}\n\n"
                    "Evaluate the generated answer against reference and context. "
                    "Rate correctness (0.0 to 1.0) and verify if claims are grounded."
                )
                j_res = judge_provider.judge(judge_prompt)
                judge_corr = j_res.score
                judge_faith = j_res.score
                judge_rat = j_res.rationale
                judge_err = j_res.is_error
            except Exception as e:
                judge_err = True
                judge_rat = f"Judge exception: {str(e)}"

        # 4. Failure Diagnosis Decision Tree
        diag_metrics = {
            "recall": case_recall,
            "hit_rate": hit_rate_k_map.get(primary_k, 0.0),
            "mrr": mrr_val,
            "exact_match": em_val,
            "normalized_match": f1_val,
            "numeric_match": num_val,
            "citation_correctness": cit_corr,
            "abstention_correctness": abs_corr,
            "judge_correctness": judge_corr,
            "judge_faithfulness": judge_faith,
            "judge_is_error": judge_err
        }

        diag = diagnose_case(
            question=tc.question,
            question_type=tc.question_type,
            reference_answer=tc.reference_answer,
            generated_answer=rag_resp.answer,
            expected_evidence=expected_ev,
            retrieved_chunks=retrieved_list,
            abstained=rag_resp.abstained,
            should_abstain=tc.should_abstain,
            citations=rag_resp.citations,
            metrics=diag_metrics
        )

        if diag.category == "pass":
            passed_count += 1

        case_res = CaseResult(
            id=f"res_{uuid.uuid4().hex[:10]}",
            run_id=run_id,
            test_case_id=tc.id,
            question=tc.question,
            question_type=tc.question_type,
            reference_answer=tc.reference_answer,
            generated_answer=rag_resp.answer,
            abstained=rag_resp.abstained,
            citations_json=json.dumps(rag_resp.citations),
            retrieved_chunks_json=json.dumps(retrieved_list),
            recall_k_json=json.dumps(recall_k_map),
            hit_rate_k_json=json.dumps(hit_rate_k_map),
            mrr=mrr_val,
            exact_match=em_val,
            normalized_match=f1_val,
            numeric_match=num_val,
            citation_correctness=cit_corr,
            abstention_correctness=abs_corr,
            judge_correctness=judge_corr,
            judge_faithfulness=judge_faith,
            judge_relevance=judge_rel,
            judge_rationale=judge_rat,
            category=diag.category,
            rule_fired=diag.rule_fired,
            rule_facts_json=json.dumps(diag.rule_facts),
            suggested_debugging_step=diag.suggested_debugging_step,
            confidence=diag.confidence,
            model_diagnosis_explanation=diag.model_diagnosis_explanation,
            is_simulated=is_simulated
        )
        db.add(case_res)
        case_results.append(case_res)

    # Complete Run
    n_total = len(test_cases)
    eval_run.status = "completed"
    eval_run.evaluated_case_count = n_total
    eval_run.pass_rate = round(passed_count / n_total, 4) if n_total > 0 else 0.0
    eval_run.mean_recall = round(total_recall / n_total, 4) if n_total > 0 else 0.0
    eval_run.mean_mrr = round(total_mrr / n_total, 4) if n_total > 0 else 0.0
    eval_run.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(eval_run)

    return _run_to_response(eval_run)

@router.post("/{run_id}/results/{case_result_id}/overrides", response_model=ReviewerOverrideResponse)
def create_reviewer_override(
    run_id: str,
    case_result_id: str,
    payload: ReviewerOverrideCreate,
    db: Session = Depends(get_db)
):
    cr = db.query(CaseResult).filter(CaseResult.id == case_result_id, CaseResult.run_id == run_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Case result not found")

    override = ReviewerOverride(
        id=f"ovr_{uuid.uuid4().hex[:8]}",
        case_result_id=case_result_id,
        original_category=cr.category,
        overridden_category=payload.overridden_category,
        reviewer_notes=payload.reviewer_notes or ""
    )
    # The original rule output is preserved; override record is stored separately!
    db.add(override)
    db.commit()
    db.refresh(override)
    return ReviewerOverrideResponse.model_validate(override)

@router.post("/{run_id}/results/{case_result_id}/explain")
def generate_case_explanation(
    run_id: str,
    case_result_id: str,
    db: Session = Depends(get_db)
):
    """
    Generates or updates the LLM-written narrative failure explanation.
    Labelled 'Model-generated diagnosis (not established fact)' in the UI.
    """
    cr = db.query(CaseResult).filter(CaseResult.id == case_result_id, CaseResult.run_id == run_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Case result not found")

    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    facts = {}
    try:
        if cr.rule_facts_json:
            facts = json.loads(cr.rule_facts_json)
    except Exception:
        pass

    from app.core.security import is_api_key_configured
    if not is_api_key_configured(settings.ANTHROPIC_API_KEY):
        # Demo mode narrative synthesis
        rec = facts.get("recall", 0.0)
        cits = facts.get("citations", [])
        explanation = (
            f"The evaluation engine classified this case as '{cr.category.upper()}' under {cr.rule_fired}. "
            f"Observed recall was {rec:.2f}. "
            + ("Zero target evidence chunks were surfaced in top-K context." if rec == 0.0 else f"Retrieved context matched {rec*100:.0f}% of ground truth evidence.")
            + f" Citations detected: {len(cits)}. Next step: {cr.suggested_debugging_step}"
        )
    else:
        try:
            provider = get_llm_provider(model=run.model_name if run else None)
            prompt = (
                f"You are an AI diagnostic system analyzing a RAG test failure.\n"
                f"Question: {cr.question}\n"
                f"Reference Answer: {cr.reference_answer}\n"
                f"Generated Answer: {cr.generated_answer}\n"
                f"Classification Category: {cr.category}\n"
                f"Rule Fired: {cr.rule_fired}\n"
                f"Measured Facts: {json.dumps(facts)}\n\n"
                f"Provide a concise, 2-3 sentence technical diagnostic explanation explaining WHY this result occurred "
                f"and how to resolve it. Be direct, factual, and analytical."
            )
            resp = provider.generate(
                prompt=prompt,
                system_prompt="You are an expert diagnostic assistant for RAG pipeline evaluation.",
                max_tokens=250,
                temperature=0.1
            )
            explanation = resp.text.strip()
        except Exception as e:
            explanation = f"Diagnostic generation encountered error: {str(e)}"

    cr.model_diagnosis_explanation = explanation
    db.commit()
    db.refresh(cr)

    return {
        "case_result_id": cr.id,
        "category": cr.category,
        "model_diagnosis_explanation": cr.model_diagnosis_explanation
    }

@router.delete("/{run_id}")
def delete_evaluation_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    db.delete(run)
    db.commit()
    return {"message": f"Evaluation run {run_id} deleted successfully."}
