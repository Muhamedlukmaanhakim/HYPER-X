from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Configuration, TestCase
from app.schemas.schemas import AskRequest, AskResponse
from app.services.rag import ask_question

router = APIRouter(prefix="/api/rag", tags=["rag"])

@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    """
    Playground endpoint:
    Embeds question, retrieves top-K passages with similarity scores, generates answer
    citing evidence, and returns full provenance (prompt used, latency, citations, abstention status).
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    config = None
    if payload.configuration_id:
        config = db.query(Configuration).filter(Configuration.id == payload.configuration_id).first()

    top_k = payload.top_k or (config.top_k if config else 3)
    similarity_thresh = payload.similarity_threshold or (config.similarity_threshold if config else 0.0)
    model_name = config.llm_model if config else None

    # Check for sample testcase demo fallback
    demo_fallback = None
    demo_citations = None
    matched_tc = db.query(TestCase).filter(
        TestCase.question.ilike(f"%{payload.question.strip()[:40]}%")
    ).first()
    if matched_tc and matched_tc.demo_answer:
        demo_fallback = matched_tc.demo_answer
        import json
        try:
            demo_citations = json.loads(matched_tc.demo_citations_json or "[]")
        except Exception:
            pass

    response = ask_question(
        question=payload.question,
        top_k=top_k,
        similarity_threshold=similarity_thresh,
        collection_name="default_rag",
        model_name=model_name,
        demo_answer_fallback=demo_fallback,
        demo_citations_fallback=demo_citations
    )

    return response
