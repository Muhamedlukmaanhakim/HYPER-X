import json
from typing import Any, Dict, List
from app.models.models import CaseResult, EvaluationRun
from app.schemas.schemas import ComparisonResponse, PerCaseComparison

def compare_evaluation_runs(
    baseline_run: EvaluationRun,
    candidate_run: EvaluationRun,
    baseline_results: List[CaseResult],
    candidate_results: List[CaseResult]
) -> Dict[str, Any]:
    """
    Computes real, un-fabricated delta metrics between baseline and candidate evaluation runs
    evaluated on identical test cases.
    Identifies improved, regressed, and unchanged test cases.
    """
    candidate_by_case = {r.test_case_id: r for r in candidate_results}
    per_case_comparisons: List[PerCaseComparison] = []

    improved_count = 0
    regressed_count = 0
    unchanged_count = 0

    category_changes: Dict[str, Dict[str, int]] = {}

    for b_res in baseline_results:
        c_res = candidate_by_case.get(b_res.test_case_id)
        if not c_res:
            continue

        b_recall = float(b_res.mrr or 0.0)
        c_recall = float(c_res.mrr or 0.0)

        # Parse recall@1 or recall@3 if available
        try:
            b_rec_dict = json.loads(b_res.recall_k_json) if b_res.recall_k_json else {}
            c_rec_dict = json.loads(c_res.recall_k_json) if c_res.recall_k_json else {}
            b_val = float(b_rec_dict.get("3", b_rec_dict.get("1", 0.0)))
            c_val = float(c_rec_dict.get("3", c_rec_dict.get("1", 0.0)))
        except Exception:
            b_val = b_res.mrr
            c_val = c_res.mrr

        b_cat = b_res.category
        c_cat = c_res.category

        # Improvement / regression evaluation
        status_change = "unchanged"
        if b_cat != "pass" and c_cat == "pass":
            status_change = "improved"
            improved_count += 1
        elif b_cat == "pass" and c_cat != "pass":
            status_change = "regressed"
            regressed_count += 1
        else:
            # Check metric score changes
            if c_val > b_val + 0.1:
                status_change = "improved"
                improved_count += 1
            elif c_val < b_val - 0.1:
                status_change = "regressed"
                regressed_count += 1
            else:
                unchanged_count += 1

        # Track category transition
        cat_key = f"{b_cat} -> {c_cat}"
        if cat_key not in category_changes:
            category_changes[cat_key] = {"count": 0, "baseline": b_cat, "candidate": c_cat}
        category_changes[cat_key]["count"] += 1

        per_case_comparisons.append(
            PerCaseComparison(
                test_case_id=b_res.test_case_id,
                question=b_res.question,
                question_type=b_res.question_type,
                baseline_category=b_cat,
                candidate_category=c_cat,
                status_change=status_change,
                baseline_recall=round(b_val, 3),
                candidate_recall=round(c_val, 3),
                recall_delta=round(c_val - b_val, 3),
                baseline_answer=b_res.generated_answer,
                candidate_answer=c_res.generated_answer
            )
        )

    b_pass = baseline_run.pass_rate or 0.0
    c_pass = candidate_run.pass_rate or 0.0
    b_rec = baseline_run.mean_recall or 0.0
    c_rec = candidate_run.mean_recall or 0.0
    b_mrr = baseline_run.mean_mrr or 0.0
    c_mrr = candidate_run.mean_mrr or 0.0

    n_cases = len(per_case_comparisons)
    warning = None
    if n_cases < 20:
        warning = f"Statistical Caution: Sample size is small (n={n_cases}); observed metric deltas may be subject to variance or noise."

    return {
        "test_case_count": n_cases,
        "baseline_pass_rate": round(b_pass, 4),
        "candidate_pass_rate": round(c_pass, 4),
        "pass_rate_delta": round(c_pass - b_pass, 4),
        "mean_recall_delta": round(c_rec - b_rec, 4),
        "mean_mrr_delta": round(c_mrr - b_mrr, 4),
        "metric_deltas": {
            "pass_rate_delta": round(c_pass - b_pass, 4),
            "recall_delta": round(c_rec - b_rec, 4),
            "mrr_delta": round(c_mrr - b_mrr, 4),
            "improved_cases": improved_count,
            "regressed_cases": regressed_count,
            "unchanged_cases": unchanged_count
        },
        "category_changes": category_changes,
        "per_case_comparisons": [p.model_dump() for p in per_case_comparisons],
        "sample_size_warning": warning
    }
