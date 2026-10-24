import csv
import io
import json
from typing import Any, Dict, List
from app.models.models import CaseResult, EvaluationRun

def export_run_cases_to_csv(run: EvaluationRun, results: List[CaseResult]) -> str:
    """
    Exports detailed per-case evaluation results to CSV with complete metric transparency.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Run ID",
        "Run Name",
        "Configuration ID",
        "Case ID",
        "Question",
        "Question Type",
        "Reference Answer",
        "Generated Answer",
        "Abstained",
        "Citations",
        "Retrieved Chunk IDs",
        "Recall@1",
        "Recall@3",
        "Recall@5",
        "MRR",
        "Exact Match",
        "Normalized Match F1",
        "Numeric Match",
        "Citation Correctness",
        "Abstention Correctness",
        "Judge Correctness",
        "Judge Faithfulness",
        "Category Slug",
        "Rule Fired",
        "Suggested Debugging Step",
        "Confidence",
        "Simulated (Failure Injected)",
        "Error",
        "Created At"
    ])

    for r in results:
        # Parse recall dict
        rec_dict = {}
        try:
            if r.recall_k_json:
                rec_dict = json.loads(r.recall_k_json)
        except Exception:
            pass

        # Parse citations
        cits = []
        try:
            if r.citations_json:
                cits = json.loads(r.citations_json)
        except Exception:
            pass

        # Parse retrieved chunk ids
        ret_ids = []
        try:
            if r.retrieved_chunks_json:
                ret_chunks = json.loads(r.retrieved_chunks_json)
                ret_ids = [c.get("chunk_id", "") for c in ret_chunks]
        except Exception:
            pass

        writer.writerow([
            r.run_id,
            run.name,
            run.configuration_id,
            r.test_case_id,
            r.question,
            r.question_type,
            r.reference_answer,
            r.generated_answer,
            "YES" if r.abstained else "NO",
            "; ".join(cits),
            "; ".join(ret_ids),
            rec_dict.get("1", ""),
            rec_dict.get("3", ""),
            rec_dict.get("5", ""),
            r.mrr,
            r.exact_match,
            r.normalized_match,
            r.numeric_match if r.numeric_match is not None else "",
            r.citation_correctness if r.citation_correctness is not None else "",
            r.abstention_correctness if r.abstention_correctness is not None else "",
            r.judge_correctness if r.judge_correctness is not None else "",
            r.judge_faithfulness if r.judge_faithfulness is not None else "",
            r.category,
            r.rule_fired,
            r.suggested_debugging_step,
            r.confidence,
            "SIMULATED" if r.is_simulated else "REAL",
            r.error or "",
            r.created_at.isoformat() if r.created_at else ""
        ])

    return output.getvalue()

def export_run_summary_to_csv(run: EvaluationRun, results: List[CaseResult]) -> str:
    """
    Exports high-level run summary statistics and category distribution to CSV.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # General info
    writer.writerow(["Evaluation Run Summary Report", "AI Truth Inspector"])
    writer.writerow(["Run ID", run.id])
    writer.writerow(["Run Name", run.name])
    writer.writerow(["Configuration ID", run.configuration_id])
    writer.writerow(["Provider", run.provider])
    writer.writerow(["Model", run.model_name])
    writer.writerow(["Is Simulated (Failure Injected)", "YES" if run.is_simulated else "NO"])
    writer.writerow(["Pass Threshold", run.pass_threshold])
    writer.writerow(["Total Cases Evaluated", len(results)])
    writer.writerow(["Pass Rate", f"{run.pass_rate * 100:.1f}%" if run.pass_rate is not None else "N/A"])
    writer.writerow(["Mean Recall", f"{run.mean_recall:.4f}" if run.mean_recall is not None else "N/A"])
    writer.writerow(["Mean MRR", f"{run.mean_mrr:.4f}" if run.mean_mrr is not None else "N/A"])
    writer.writerow([])

    # Category breakdown
    writer.writerow(["Failure Category Breakdown"])
    writer.writerow(["Category", "Count", "Percentage"])
    total = len(results) or 1
    counts: Dict[str, int] = {}
    for r in results:
        counts[r.category] = counts.get(r.category, 0) + 1

    for cat, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        writer.writerow([cat, count, f"{(count / total) * 100:.1f}%"])

    return output.getvalue()

def generate_run_html_report(run: EvaluationRun, results: List[CaseResult]) -> str:
    """
    Generates a publication-grade, self-contained HTML executive report
    formatted with Neo-Brutalist typography and browser print-to-PDF styles.
    """
    total = len(results) or 1
    counts: Dict[str, int] = {}
    for r in results:
        counts[r.category] = counts.get(r.category, 0) + 1

    cat_rows = "".join(
        f"<tr><td><strong>{cat.replace('_', ' ').upper()}</strong></td><td>{cnt}</td><td>{(cnt/total)*100:.1f}%</td></tr>"
        for cat, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    )

    case_rows = "".join(
        f"""
        <tr class="{'sim-row' if r.is_simulated else ''}">
            <td><strong>{r.test_case_id}</strong><br><span class="badge">{r.question_type}</span></td>
            <td><strong>{r.question}</strong><br><small style="color:#555;">Ref: {r.reference_answer}</small></td>
            <td><div style="background:#f5f3ed; padding:4px 6px; border:1px solid #ddd;">{r.generated_answer}</div></td>
            <td><span class="badge badge-{r.category}">{r.category.upper()}</span><br><small>{r.rule_fired}</small></td>
            <td><strong>{r.mrr:.2f}</strong></td>
            <td><small>{r.suggested_debugging_step}</small></td>
        </tr>
        """
        for r in results
    )

    pass_pct = f"{run.pass_rate * 100:.1f}%" if run.pass_rate is not None else "N/A"
    recall_str = f"{run.mean_recall:.3f}" if run.mean_recall is not None else "N/A"
    mrr_str = f"{run.mean_mrr:.3f}" if run.mean_mrr is not None else "N/A"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AI Truth Inspector — Executive Report: {run.name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; margin: 30px; background: #fff; color: #171717; }}
  .header {{ border-bottom: 3px solid #171717; padding-bottom: 12px; margin-bottom: 24px; }}
  .tagline {{ font-size: 13px; font-weight: bold; color: #555; text-transform: uppercase; letter-spacing: 1px; }}
  h1 {{ font-size: 26px; margin: 4px 0; }}
  .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .metric-box {{ border: 2px solid #171717; padding: 12px; background: #f5f3ed; }}
  .metric-label {{ font-size: 11px; text-transform: uppercase; font-weight: bold; color: #555; }}
  .metric-val {{ font-size: 24px; font-weight: 800; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 12px; }}
  th, td {{ border: 1px solid #171717; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #171717; color: #fff; text-transform: uppercase; font-size: 11px; }}
  .badge {{ display: inline-block; padding: 2px 6px; font-size: 10px; font-weight: bold; border: 1px solid #171717; background: #ece9e0; }}
  .badge-pass {{ background: #C6FF4D; }}
  .badge-retrieval_miss, .badge-unsupported_answer {{ background: #FF5A52; color: #fff; }}
  .badge-incomplete_or_irrelevant_context {{ background: #FFB020; }}
  .badge-needs_review {{ background: #ffd43b; }}
  .print-btn {{ background: #C6FF4D; border: 2px solid #171717; padding: 8px 16px; font-weight: bold; cursor: pointer; margin-bottom: 20px; }}
  @media print {{ .print-btn {{ display: none; }} body {{ margin: 0; }} }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
<div class="header">
  <div class="tagline">AI Truth Inspector &bull; "Trust, but verify."</div>
  <h1>Evaluation Executive Report: {run.name}</h1>
  <div>Run ID: <code>{run.id}</code> &bull; Model: <strong>{run.model_name}</strong> &bull; Date: {run.created_at}</div>
  <div style="margin-top:4px;">Execution Mode: <strong>{"SIMULATED (FAILURE INJECTED)" if run.is_simulated else "REAL LIVE RUN"}</strong></div>
</div>

<div class="metrics-grid">
  <div class="metric-box">
    <div class="metric-label">Pass Rate</div>
    <div class="metric-val">{pass_pct}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Mean Recall@K</div>
    <div class="metric-val">{recall_str}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Mean MRR</div>
    <div class="metric-val">{mrr_str}</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Cases Evaluated</div>
    <div class="metric-val">{len(results)}</div>
  </div>
</div>

<h3>Failure Mode Category Distribution</h3>
<table style="max-width: 600px;">
  <thead>
    <tr><th>Category</th><th>Count</th><th>Ratio</th></tr>
  </thead>
  <tbody>
    {cat_rows}
  </tbody>
</table>

<h3>Detailed Case Results</h3>
<table>
  <thead>
    <tr>
      <th>Case ID</th>
      <th>Question &amp; Reference</th>
      <th>Generated Answer</th>
      <th>Diagnosis &amp; Rule</th>
      <th>MRR</th>
      <th>Recommended Action</th>
    </tr>
  </thead>
  <tbody>
    {case_rows}
  </tbody>
</table>

<div style="font-size:11px; color:#666; border-top:1px solid #ccc; padding-top:8px;">
  Generated automatically by AI Truth Inspector. Deterministic metrics are evaluated locally via sentence-transformers and cosine distance ChromaDB.
</div>
</body>
</html>"""
