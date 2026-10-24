from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import CaseResult, EvaluationRun
from app.services.reports import (
    export_run_cases_to_csv,
    export_run_summary_to_csv,
    generate_run_html_report
)

router = APIRouter(prefix="/api/exports", tags=["exports"])

@router.get("/runs/{run_id}/csv")
def download_run_csv(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    results = db.query(CaseResult).filter(CaseResult.run_id == run_id).all()
    csv_content = export_run_cases_to_csv(run, results)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=truth_inspector_run_{run_id}.csv"}
    )

@router.get("/runs/{run_id}/summary-csv")
def download_run_summary_csv(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    results = db.query(CaseResult).filter(CaseResult.run_id == run_id).all()
    csv_content = export_run_summary_to_csv(run, results)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=truth_inspector_summary_{run_id}.csv"}
    )

@router.get("/runs/{run_id}/html-report")
def download_run_html_report(run_id: str, db: Session = Depends(get_db)):
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    results = db.query(CaseResult).filter(CaseResult.run_id == run_id).all()
    html_content = generate_run_html_report(run, results)

    return Response(
        content=html_content,
        media_type="text/html"
    )
