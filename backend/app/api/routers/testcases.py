import csv
import io
import json
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.database import get_db
from app.models.models import Chunk, TestCase
from app.schemas.schemas import (
    GenerateTestCasesRequest,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate
)
from app.services.testgen import generate_test_cases_from_chunks

router = APIRouter(prefix="/api/testcases", tags=["testcases"])

def _to_response(tc: TestCase) -> TestCaseResponse:
    ev_list = []
    try:
        if tc.expected_evidence_json:
            ev_list = json.loads(tc.expected_evidence_json)
    except Exception:
        pass

    demo_cits = []
    try:
        if tc.demo_citations_json:
            demo_cits = json.loads(tc.demo_citations_json)
    except Exception:
        pass

    return TestCaseResponse(
        id=tc.id,
        document_id=tc.document_id,
        question=tc.question,
        question_type=tc.question_type,  # type: ignore
        reference_answer=tc.reference_answer,
        expected_evidence=ev_list,
        should_abstain=tc.should_abstain,
        status=tc.status,
        source=tc.source,
        notes=tc.notes or "",
        demo_answer=tc.demo_answer,
        demo_citations=demo_cits,
        created_at=tc.created_at,
        updated_at=tc.updated_at
    )

@router.get("", response_model=List[TestCaseResponse])
def list_test_cases(
    document_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(TestCase)
    if document_id:
        query = query.filter(TestCase.document_id == document_id)
    if status:
        query = query.filter(TestCase.status == status)
    if question_type:
        query = query.filter(TestCase.question_type == question_type)

    cases = query.order_by(TestCase.created_at.desc()).all()
    return [_to_response(c) for c in cases]

@router.post("", response_model=TestCaseResponse)
def create_test_case(payload: TestCaseCreate, db: Session = Depends(get_db)):
    tc_id = f"tc-{uuid.uuid4().hex[:8]}"
    ev_json = json.dumps([e.model_dump() for e in payload.expected_evidence])
    tc = TestCase(
        id=tc_id,
        document_id=payload.document_id,
        question=payload.question,
        question_type=payload.question_type,
        reference_answer=payload.reference_answer,
        expected_evidence_json=ev_json,
        should_abstain=payload.should_abstain,
        status=payload.status,
        source=payload.source,
        notes=payload.notes or ""
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return _to_response(tc)

@router.get("/{case_id}", response_model=TestCaseResponse)
def get_test_case(case_id: str, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    return _to_response(tc)

@router.patch("/{case_id}", response_model=TestCaseResponse)
def update_test_case(case_id: str, payload: TestCaseUpdate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    if payload.question is not None:
        tc.question = payload.question
    if payload.question_type is not None:
        tc.question_type = payload.question_type
    if payload.reference_answer is not None:
        tc.reference_answer = payload.reference_answer
    if payload.expected_evidence is not None:
        tc.expected_evidence_json = json.dumps([e.model_dump() for e in payload.expected_evidence])
    if payload.should_abstain is not None:
        tc.should_abstain = payload.should_abstain
    if payload.status is not None:
        tc.status = payload.status
    if payload.notes is not None:
        tc.notes = payload.notes

    db.commit()
    db.refresh(tc)
    return _to_response(tc)

@router.delete("/{case_id}")
def delete_test_case(case_id: str, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")
    db.delete(tc)
    db.commit()
    return {"message": "Test case deleted successfully."}

@router.post("/generate", response_model=List[TestCaseResponse])
def generate_cases(payload: GenerateTestCasesRequest, db: Session = Depends(get_db)):
    """Generates evaluation test cases via LLM. Output is always 'unverified'."""
    chunks = db.query(Chunk).filter(Chunk.document_id == payload.document_id).all()
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for document.")

    chunk_dicts = [
        {"id": c.id, "page": c.page, "text": c.text}
        for c in chunks
    ]
    created = generate_test_cases_from_chunks(
        document_id=payload.document_id,
        chunks=chunk_dicts,
        num_cases=payload.num_cases
    )
    for c in created:
        db.add(c)
    db.commit()
    return [_to_response(c) for c in created]

@router.post("/seed-sample", response_model=List[TestCaseResponse])
def seed_sample_test_cases(db: Session = Depends(get_db)):
    sample_file = os.path.join(settings.SAMPLE_DIR, "sample_testcases.json")
    if not os.path.exists(sample_file):
        raise HTTPException(status_code=404, detail="Sample test cases file not found.")

    with open(sample_file, "r", encoding="utf-8") as f:
        cases_data = json.load(f)

    seeded = []
    for item in cases_data:
        existing = db.query(TestCase).filter(TestCase.id == item["id"]).first()
        if not existing:
            tc = TestCase(
                id=item["id"],
                document_id="sample_doc",
                question=item["question"],
                question_type=item["question_type"],
                reference_answer=item["reference_answer"],
                expected_evidence_json=json.dumps(item.get("expected_evidence", [])),
                should_abstain=item.get("should_abstain", False),
                status=item.get("status", "approved"),
                source="sample",
                notes=item.get("notes", ""),
                demo_answer=item.get("demo_answer"),
                demo_citations_json=json.dumps(item.get("demo_citations", []))
            )
            db.add(tc)
            seeded.append(tc)
        else:
            seeded.append(existing)

    db.commit()
    return [_to_response(c) for c in seeded]

@router.get("/export/csv")
def export_testcases_csv(db: Session = Depends(get_db)):
    cases = db.query(TestCase).order_by(TestCase.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "document_id", "question", "question_type",
        "reference_answer", "expected_evidence", "should_abstain", "status", "source", "notes"
    ])
    for c in cases:
        writer.writerow([
            c.id, c.document_id or "", c.question, c.question_type,
            c.reference_answer, c.expected_evidence_json,
            "true" if c.should_abstain else "false", c.status, c.source, c.notes or ""
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=truth_inspector_testcases.csv"}
    )

@router.post("/import/csv")
async def import_testcases_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Imports test cases from a CSV file.
    Validates mandatory columns and reports row-level errors without crashing.
    """
    content = await file.read()
    text = None
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = content.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty or missing headers.")

    fieldnames = [f.strip().lower() for f in reader.fieldnames]
    if "question" not in fieldnames or "reference_answer" not in fieldnames:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least 'question' and 'reference_answer' columns."
        )

    valid_types = {"direct_factual", "paraphrased", "multi_passage", "numerical", "unanswerable"}
    imported = []
    errors = []

    for idx, row in enumerate(reader, start=2):
        row_clean = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        question = row_clean.get("question", "")
        ref_answer = row_clean.get("reference_answer", "")

        if not question or not ref_answer:
            errors.append(f"Row {idx}: Missing question or reference_answer.")
            continue

        q_type = row_clean.get("question_type", "direct_factual").lower()
        if q_type not in valid_types:
            q_type = "direct_factual"

        should_abstain_raw = row_clean.get("should_abstain", "").lower()
        should_abstain = should_abstain_raw in ["true", "1", "yes"] or q_type == "unanswerable"

        ev_raw = row_clean.get("expected_evidence", "[]")
        ev_json = "[]"
        if ev_raw:
            try:
                parsed_ev = json.loads(ev_raw)
                if isinstance(parsed_ev, list):
                    ev_json = json.dumps(parsed_ev)
                elif isinstance(parsed_ev, dict):
                    ev_json = json.dumps([parsed_ev])
            except Exception:
                # If plaintext span was given, wrap into single span
                ev_json = json.dumps([{"text_span": ev_raw}])

        tc_id = row_clean.get("id") or f"tc-imp-{uuid.uuid4().hex[:8]}"
        existing = db.query(TestCase).filter(TestCase.id == tc_id).first()
        if existing:
            tc_id = f"tc-imp-{uuid.uuid4().hex[:8]}"

        tc = TestCase(
            id=tc_id,
            document_id=row_clean.get("document_id") or None,
            question=question,
            question_type=q_type,
            reference_answer=ref_answer,
            expected_evidence_json=ev_json,
            should_abstain=should_abstain,
            status=row_clean.get("status", "approved"),
            source="imported",
            notes=row_clean.get("notes", "")
        )
        db.add(tc)
        imported.append(tc)

    db.commit()
    return {
        "imported_count": len(imported),
        "error_count": len(errors),
        "errors": errors,
        "message": f"Successfully imported {len(imported)} test cases ({len(errors)} row errors)."
    }
