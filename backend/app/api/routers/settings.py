import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import is_api_key_configured
from app.models.database import get_db
from app.models.models import Configuration, MetricDefinition
from app.schemas.schemas import (
    ConfigurationCreate,
    ConfigurationResponse,
    MetricDefinitionResponse,
    ProviderStatusResponse
)
from app.services.providers import get_llm_provider

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/status", response_model=ProviderStatusResponse)
def get_provider_status():
    """
    Returns provider configuration status.
    CRITICAL SECURITY RULE: Never returns or exposes the secret key.
    """
    active_prov = (settings.LLM_PROVIDER or "gemini").lower()
    if active_prov == "demo":
        return ProviderStatusResponse(
            provider="demo",
            configured=True,
            model="offline-deterministic",
            embedding_model=settings.EMBEDDING_MODEL,
            connection_tested=True,
            connection_status="connected",
            demo_mode=True
        )
    elif is_api_key_configured(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY):
        active_prov = "gemini"
        has_key = True
    elif is_api_key_configured(settings.ANTHROPIC_API_KEY):
        active_prov = "anthropic"
        has_key = True
    else:
        has_key = False

    return ProviderStatusResponse(
        provider=active_prov,
        configured=has_key,
        model=settings.LLM_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
        connection_tested=False,
        connection_status="connected" if has_key else "not_configured",
        demo_mode=not has_key
    )

@router.post("/test-connection")
def test_connection():
    """
    Executes a minimal test ping to the configured LLM provider without processing any documents.
    """
    provider = get_llm_provider()
    result = provider.test_connection()
    return result

@router.get("/configurations", response_model=List[ConfigurationResponse])
def list_configurations(db: Session = Depends(get_db)):
    configs = db.query(Configuration).order_by(Configuration.created_at.desc()).all()
    if not configs:
        # Create default config if empty
        default_cfg = Configuration(
            id="cfg_default",
            name="Balanced Default RAG",
            description="800-char chunks, 150-char overlap, top-3 retrieval with cosine similarity",
            chunk_size=800,
            chunk_overlap=150,
            top_k=3,
            similarity_threshold=0.0,
            embedding_model=settings.EMBEDDING_MODEL,
            llm_model=settings.LLM_MODEL,
            is_default=True
        )
        db.add(default_cfg)
        db.commit()
        db.refresh(default_cfg)
        return [ConfigurationResponse.model_validate(default_cfg)]
    return [ConfigurationResponse.model_validate(c) for c in configs]

@router.post("/configurations", response_model=ConfigurationResponse)
def create_configuration(payload: ConfigurationCreate, db: Session = Depends(get_db)):
    cfg_id = f"cfg_{uuid.uuid4().hex[:8]}"
    if payload.is_default:
        # Reset other defaults
        db.query(Configuration).update({"is_default": False})

    cfg = Configuration(
        id=cfg_id,
        name=payload.name,
        description=payload.description or "",
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
        embedding_model=payload.embedding_model,
        llm_model=payload.llm_model,
        prompt_template_version=payload.prompt_template_version,
        abstention_enabled=payload.abstention_enabled,
        is_default=payload.is_default
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return ConfigurationResponse.model_validate(cfg)

@router.get("/metrics", response_model=List[MetricDefinitionResponse])
def get_metric_definitions():
    """Returns stored metric definitions (formulas, descriptions, limitations)."""
    return [
        MetricDefinitionResponse(
            slug="retrieval_recall_k",
            name="Retrieval Recall@K",
            metric_type="deterministic",
            formula="matched_expected_evidence_chunks_in_top_k / total_expected_evidence_chunks",
            description="Fraction of annotated ground-truth evidence passages successfully retrieved in the top-K passages.",
            limitations="Assumes expected evidence spans are thoroughly annotated. Different chunking boundaries use span-overlap mapping."
        ),
        MetricDefinitionResponse(
            slug="hit_rate_k",
            name="Hit Rate@K",
            metric_type="deterministic",
            formula="1.0 if any expected evidence piece is in top-K else 0.0",
            description="Binary indicator showing whether at least one necessary piece of evidence was surfaced in top-K context.",
            limitations="Does not measure whether all required multi-passage evidence was retrieved."
        ),
        MetricDefinitionResponse(
            slug="mrr",
            name="Mean Reciprocal Rank (MRR)",
            metric_type="deterministic",
            formula="1.0 / first_relevant_chunk_rank",
            description="Measures how high in the retrieved candidate list the first relevant passage appears.",
            limitations="Only values the very first relevant passage; subsequent relevant passages do not affect the score."
        ),
        MetricDefinitionResponse(
            slug="exact_match",
            name="Exact Match (EM)",
            metric_type="deterministic",
            formula="1.0 if normalized_prediction == normalized_reference else 0.0",
            description="Strict string equality after lowercasing, punctuation stripping, and article removal.",
            limitations="Too rigid for generative answers that express identical facts with different vocabulary."
        ),
        MetricDefinitionResponse(
            slug="normalized_match",
            name="Normalized Token F1",
            metric_type="deterministic",
            formula="2 * (precision * recall) / (precision + recall) over word tokens",
            description="Harmonic mean of token-level precision and recall between generated and reference answers.",
            limitations="Word-bag overlap metric that cannot detect negations or subtle semantic contradictions."
        ),
        MetricDefinitionResponse(
            slug="numeric_match",
            name="Numeric Match",
            metric_type="deterministic",
            formula="1.0 if all reference numbers appear in generated answer within 1% tolerance else 0.0",
            description="Precision extraction and numeric comparison for numerical/quantitative benchmark questions.",
            limitations="Does not verify units of measurement unless units are parsed as part of the text."
        ),
        MetricDefinitionResponse(
            slug="citation_correctness",
            name="Citation Correctness",
            metric_type="deterministic",
            formula="valid_citations_matching_evidence / total_generated_citations",
            description="Verifies that bracketed chunk IDs and page numbers explicitly cite true supporting evidence.",
            limitations="Requires model to follow citation syntax brackets [Page X] or [chunk_id]."
        ),
        MetricDefinitionResponse(
            slug="abstention_correctness",
            name="Abstention Correctness",
            metric_type="deterministic",
            formula="1.0 if correctly abstained on unanswerable question or answered answerable case else 0.0",
            description="Tests system guardrails: answers when evidence is present, abstains with INSUFFICIENT_EVIDENCE when absent.",
            limitations="Binary check based on sentinel string presence."
        ),
        MetricDefinitionResponse(
            slug="judge_correctness",
            name="Model-Judged Semantic Correctness",
            metric_type="model_judged",
            formula="Calibrated LLM judge score (0.0 to 1.0) with structured JSON rationale",
            description="Uses an LLM judge to verify semantic factual equivalence between generated and reference answers.",
            limitations="LLM judges can exhibit bias, self-preference, and occasional hallucination; indicative, not ground truth."
        )
    ]
