import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import CaseResult, Comparison, EvaluationRun
from app.schemas.schemas import ComparisonCreate, ComparisonResponse
from app.services.comparison import compare_evaluation_runs

router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])

@router.get("", response_model=List[ComparisonResponse])
def list_comparisons(db: Session = Depends(get_db)):
    comps = db.query(Comparison).order_by(Comparison.created_at.desc()).all()
    out = []
    for comp in comps:
        metric_deltas = {}
        cat_changes = {}
        try:
            metric_deltas = json.loads(comp.metric_deltas_json or "{}")
            cat_changes = json.loads(comp.category_changes_json or "{}")
        except Exception:
            pass

        out.append(
            ComparisonResponse(
                id=comp.id,
                name=comp.name,
                baseline_run_id=comp.baseline_run_id,
                candidate_run_id=comp.candidate_run_id,
                test_case_count=comp.test_case_count,
                baseline_pass_rate=metric_deltas.get("pass_rate_baseline", 0.0),
                candidate_pass_rate=metric_deltas.get("pass_rate_candidate", 0.0),
                pass_rate_delta=metric_deltas.get("pass_rate_delta", 0.0),
                mean_recall_delta=metric_deltas.get("mean_recall_delta", 0.0),
                mean_mrr_delta=metric_deltas.get("mean_mrr_delta", 0.0),
                metric_deltas=metric_deltas,
                category_changes=cat_changes,
                per_case_comparisons=[],
                sample_size_warning="",
                created_at=comp.created_at
            )
        )
    return out

@router.post("", response_model=ComparisonResponse)

def create_comparison(payload: ComparisonCreate, db: Session = Depends(get_db)):
    baseline_run = db.query(EvaluationRun).filter(EvaluationRun.id == payload.baseline_run_id).first()
    candidate_run = db.query(EvaluationRun).filter(EvaluationRun.id == payload.candidate_run_id).first()

    if not baseline_run or not candidate_run:
        raise HTTPException(status_code=404, detail="Baseline or Candidate evaluation run not found.")

    b_results = db.query(CaseResult).filter(CaseResult.run_id == baseline_run.id).all()
    c_results = db.query(CaseResult).filter(CaseResult.run_id == candidate_run.id).all()

    comparison_data = compare_evaluation_runs(
        baseline_run=baseline_run,
        candidate_run=candidate_run,
        baseline_results=b_results,
        candidate_results=c_results
    )

    comp_id = f"cmp_{uuid.uuid4().hex[:8]}"
    comp_name = payload.name or f"Comparison: {baseline_run.name} vs {candidate_run.name}"

    comp_rec = Comparison(
        id=comp_id,
        name=comp_name,
        baseline_run_id=baseline_run.id,
        candidate_run_id=candidate_run.id,
        test_case_count=comparison_data["test_case_count"],
        metric_deltas_json=json.dumps(comparison_data["metric_deltas"]),
        category_changes_json=json.dumps(comparison_data["category_changes"])
    )
    db.add(comp_rec)
    db.commit()

    return ComparisonResponse(
        id=comp_id,
        name=comp_name,
        baseline_run_id=baseline_run.id,
        candidate_run_id=candidate_run.id,
        test_case_count=comparison_data["test_case_count"],
        baseline_pass_rate=comparison_data["baseline_pass_rate"],
        candidate_pass_rate=comparison_data["candidate_pass_rate"],
        pass_rate_delta=comparison_data["pass_rate_delta"],
        mean_recall_delta=comparison_data["mean_recall_delta"],
        mean_mrr_delta=comparison_data["mean_mrr_delta"],
        metric_deltas=comparison_data["metric_deltas"],
        category_changes=comparison_data["category_changes"],
        per_case_comparisons=comparison_data["per_case_comparisons"],
        sample_size_warning=comparison_data["sample_size_warning"],
        created_at=comp_rec.created_at
    )

@router.get("/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(comparison_id: str, db: Session = Depends(get_db)):
    comp = db.query(Comparison).filter(Comparison.id == comparison_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison record not found")

    baseline_run = db.query(EvaluationRun).filter(EvaluationRun.id == comp.baseline_run_id).first()
    candidate_run = db.query(EvaluationRun).filter(EvaluationRun.id == comp.candidate_run_id).first()

    b_results = db.query(CaseResult).filter(CaseResult.run_id == comp.baseline_run_id).all()
    c_results = db.query(CaseResult).filter(CaseResult.run_id == comp.candidate_run_id).all()

    comparison_data = compare_evaluation_runs(
        baseline_run=baseline_run,
        candidate_run=candidate_run,
        baseline_results=b_results,
        candidate_results=c_results
    )

    return ComparisonResponse(
        id=comp.id,
        name=comp.name,
        baseline_run_id=comp.baseline_run_id,
        candidate_run_id=comp.candidate_run_id,
        test_case_count=comp.test_case_count,
        baseline_pass_rate=comparison_data["baseline_pass_rate"],
        candidate_pass_rate=comparison_data["candidate_pass_rate"],
        pass_rate_delta=comparison_data["pass_rate_delta"],
        mean_recall_delta=comparison_data["mean_recall_delta"],
        mean_mrr_delta=comparison_data["mean_mrr_delta"],
        metric_deltas=comparison_data["metric_deltas"],
        category_changes=comparison_data["category_changes"],
        per_case_comparisons=comparison_data["per_case_comparisons"],
        sample_size_warning=comparison_data["sample_size_warning"],
        created_at=comp.created_at
    )
