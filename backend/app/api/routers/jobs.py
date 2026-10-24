import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Job
from app.schemas.schemas import JobResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    payload = None
    try:
        if job.result_payload_json:
            payload = json.loads(job.result_payload_json)
    except Exception:
        pass

    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        progress_percent=job.progress_percent,
        message=job.message or "",
        result_payload=payload,
        error_details=job.error_details,
        created_at=job.created_at,
        updated_at=job.updated_at
    )
