from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.services.metrics import (
    compute_retrieval_recall_at_k,
    compute_normalized_match,
    compute_numeric_match,
    is_chunk_matching_evidence,
    normalize_text
)

# Canonical Diagnosis Category Slugs (Master Prompt Section 4.E)
CAT_RETRIEVAL_MISS = "retrieval_miss"
CAT_INCOMPLETE_OR_IRRELEVANT = "incomplete_or_irrelevant_context"
CAT_UNSUPPORTED_ANSWER = "unsupported_answer"
CAT_INCORRECT_DESPITE_CONTEXT = "incorrect_despite_relevant_context"
CAT_CITATION_ERROR = "citation_error"
CAT_UNANSWERABLE_ANSWERED = "unanswerable_answered"
CAT_NEEDS_REVIEW = "needs_review"
CAT_PASS = "pass"

ALL_DIAGNOSIS_CATEGORIES = [
    CAT_PASS,
    CAT_RETRIEVAL_MISS,
    CAT_INCOMPLETE_OR_IRRELEVANT,
    CAT_UNSUPPORTED_ANSWER,
    CAT_INCORRECT_DESPITE_CONTEXT,
    CAT_CITATION_ERROR,
    CAT_UNANSWERABLE_ANSWERED,
    CAT_NEEDS_REVIEW
]

class DiagnosisResult(BaseModel):
    category: str
    rule_fired: str
    rule_facts: Dict[str, Any]
    suggested_debugging_step: str
    confidence: str  # high, medium, low
    model_diagnosis_explanation: Optional[str] = None

def diagnose_case(
    question: str,
    question_type: str,
    reference_answer: str,
    generated_answer: str,
    expected_evidence: List[Dict[str, Any]],
    retrieved_chunks: List[Dict[str, Any]],
    abstained: bool,
    should_abstain: bool,
    citations: List[str],
    metrics: Dict[str, Any]
) -> DiagnosisResult:
    """
    Pure, unit-tested failure diagnosis decision tree evaluated in strict order (1 to 8):
    1. If expected evidence annotations are missing/ambiguous for an answerable case -> needs_review.
    2. If case is unanswerable and system did not abstain -> unanswerable_answered.
    3. If answerable and NO expected evidence chunk appears in retrieved top-K -> retrieval_miss.
    4. If only part of expected evidence retrieved and answer is wrong -> incomplete_or_irrelevant_context.
    5. If evidence retrieved but answer contains claims unsupported by context -> unsupported_answer.
    6. If evidence fully retrieved, answer is supported-looking but incorrect -> incorrect_despite_relevant_context.
    7. If answer is correct but citations wrong/missing -> citation_error.
    8. If signals conflict or judge errored -> needs_review.
    Otherwise -> pass.
    """
    # Extract measured metric facts
    recall = metrics.get("recall", 0.0)
    hit_rate = metrics.get("hit_rate", 0.0)
    mrr = metrics.get("mrr", 0.0)
    norm_match = metrics.get("normalized_match", 0.0)
    exact_match = metrics.get("exact_match", 0.0)
    numeric_match = metrics.get("numeric_match")
    citation_correctness = metrics.get("citation_correctness")
    judge_correctness = metrics.get("judge_correctness")
    judge_faithfulness = metrics.get("judge_faithfulness")
    judge_is_error = metrics.get("judge_is_error", False)

    facts = {
        "recall": recall,
        "hit_rate": hit_rate,
        "mrr": mrr,
        "normalized_match": norm_match,
        "exact_match": exact_match,
        "numeric_match": numeric_match,
        "citation_correctness": citation_correctness,
        "judge_correctness": judge_correctness,
        "judge_faithfulness": judge_faithfulness,
        "judge_is_error": judge_is_error,
        "abstained": abstained,
        "should_abstain": should_abstain,
        "expected_evidence_count": len(expected_evidence),
        "retrieved_count": len(retrieved_chunks),
        "citations_count": len(citations),
        "citations": citations
    }

    # Determine general correctness of the answer
    is_correct = False
    if exact_match == 1.0:
        is_correct = True
    elif numeric_match is not None and numeric_match == 1.0:
        is_correct = True
    elif judge_correctness is not None and not judge_is_error and judge_correctness >= 0.70:
        is_correct = True
    elif norm_match >= 0.75:
        is_correct = True
    elif should_abstain and abstained:
        is_correct = True

    # Check context support (faithfulness)
    is_supported = True
    if judge_faithfulness is not None and not judge_is_error:
        is_supported = (judge_faithfulness >= 0.60)
    else:
        # Deterministic support check: does generated answer overlap with retrieved text
        all_retrieved_text = " ".join(c.get("text", "") for c in retrieved_chunks)
        overlap = compute_normalized_match(generated_answer, all_retrieved_text)
        is_supported = (overlap >= 0.30 or abstained)

    # RULE 1: Missing or ambiguous expected evidence for an answerable case
    if not should_abstain and not expected_evidence:
        return DiagnosisResult(
            category=CAT_NEEDS_REVIEW,
            rule_fired="Rule 1: Expected evidence annotations are missing or ambiguous for an answerable case",
            rule_facts=facts,
            suggested_debugging_step="Annotate the ground-truth expected evidence (chunk IDs or page + text spans) in Test Cases.",
            confidence="high"
        )

    # RULE 2: Case is unanswerable and system failed to abstain
    if should_abstain and not abstained:
        return DiagnosisResult(
            category=CAT_UNANSWERABLE_ANSWERED,
            rule_fired="Rule 2: System answered an unanswerable question instead of abstaining",
            rule_facts=facts,
            suggested_debugging_step="Review RAG prompt abstention guardrails and verify similarity threshold (e.g. bump to 0.70+).",
            confidence="high"
        )

    # RULE 3: Answerable and NO expected evidence chunk appears in top-K
    if not should_abstain and hit_rate == 0.0 and recall == 0.0:
        return DiagnosisResult(
            category=CAT_RETRIEVAL_MISS,
            rule_fired="Rule 3: Retrieval miss — zero expected evidence chunks found in retrieved top-K context",
            rule_facts=facts,
            suggested_debugging_step="Inspect embedding model, adjust chunk size/overlap, or increase top-K retrieval depth.",
            confidence="high"
        )

    # RULE 4: Partial evidence retrieved or mostly distractors and answer is wrong/incomplete
    if not should_abstain and recall < 1.0 and not is_correct:
        return DiagnosisResult(
            category=CAT_INCOMPLETE_OR_IRRELEVANT,
            rule_fired=f"Rule 4: Incomplete context — only partial evidence retrieved (Recall={recall:.2f}) and answer is inaccurate",
            rule_facts=facts,
            suggested_debugging_step="Increase top-K retrieval count, enable hybrid search, or check if multi-passage chunks are scattered across document.",
            confidence="high"
        )

    # RULE 5: Evidence was retrieved but answer contains unsupported claims (hallucination)
    if not should_abstain and recall > 0.0 and not is_supported and not is_correct:
        return DiagnosisResult(
            category=CAT_UNSUPPORTED_ANSWER,
            rule_fired="Rule 5: Unsupported claims — generated answer contains extrapolations not grounded in retrieved context",
            rule_facts=facts,
            suggested_debugging_step="Enforce strict groundedness prompt instructions with lower LLM temperature (0.0).",
            confidence="medium" if judge_faithfulness is not None else "low"
        )

    # RULE 6: Evidence fully retrieved, answer looks supported, but is incorrect
    if not should_abstain and recall >= 1.0 and not is_correct:
        return DiagnosisResult(
            category=CAT_INCORRECT_DESPITE_CONTEXT,
            rule_fired="Rule 6: Reasoning failure — 100% of evidence was retrieved, but model synthesized an incorrect answer",
            rule_facts=facts,
            suggested_debugging_step="Examine prompt formatting, test a higher-capability model (e.g. Claude 3.5 Sonnet), or add few-shot reasoning examples.",
            confidence="high" if exact_match == 0.0 and (numeric_match == 0.0 or norm_match < 0.4) else "medium"
        )

    # RULE 7: Answer is correct but citations wrong or missing
    if is_correct and not should_abstain:
        if not citations or (citation_correctness is not None and citation_correctness < 0.50):
            return DiagnosisResult(
                category=CAT_CITATION_ERROR,
                rule_fired="Rule 7: Citation error — answer is correct, but citations are missing or do not match evidence",
                rule_facts=facts,
                suggested_debugging_step="Refine prompt citation formatting instructions (e.g. [Page X] or [chunk_id]) and verify parser regex.",
                confidence="high"
            )

    # RULE 8: Signals conflict or judge errored
    if judge_is_error:
        return DiagnosisResult(
            category=CAT_NEEDS_REVIEW,
            rule_fired="Rule 8: Inconclusive signals — model judge encountered an execution or JSON formatting error",
            rule_facts=facts,
            suggested_debugging_step="Inspect judge prompt/API logs and manually review this test case result.",
            confidence="low"
        )

    # If answer is correct and no rules flagged failures: PASS
    if is_correct:
        return DiagnosisResult(
            category=CAT_PASS,
            rule_fired="Evaluation passed — evidence retrieved, answer verified grounded and correct",
            rule_facts=facts,
            suggested_debugging_step="No action required. Retrieval and answer generation performed as expected.",
            confidence="high"
        )

    # Fallback to needs_review for ambiguous border cases
    return DiagnosisResult(
        category=CAT_NEEDS_REVIEW,
        rule_fired="Fallback: Test case signals do not meet threshold criteria for automatic pass or failure",
        rule_facts=facts,
        suggested_debugging_step="Conduct manual human review and assign a category override if appropriate.",
        confidence="low"
    )
