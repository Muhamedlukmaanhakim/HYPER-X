from datetime import datetime, timezone
import json
from typing import Any, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.models.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, txt
    file_size_bytes = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    chunk_count = Column(Integer, default=0)
    char_count = Column(Integer, default=0)
    is_sample = Column(Boolean, default=False)
    status = Column(String(20), default="processing")  # processing, indexed, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String(100), primary_key=True)  # {doc_id}:{page}:{index}
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page = Column(Integer, default=1)
    chunk_index = Column(Integer, nullable=False)
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    char_count = Column(Integer, default=0)
    token_count_estimate = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="chunks")


class Configuration(Base):
    __tablename__ = "configurations"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    chunk_size = Column(Integer, default=800)
    chunk_overlap = Column(Integer, default=150)
    top_k = Column(Integer, default=3)
    similarity_threshold = Column(Float, default=0.0)
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    llm_model = Column(String(100), default="claude-3-5-sonnet-20241022")
    prompt_template_version = Column(String(20), default="v1_strict_grounded")
    abstention_enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False)  # direct_factual, paraphrased, multi_passage, numerical, unanswerable
    reference_answer = Column(Text, nullable=False)
    expected_evidence_json = Column(Text, default="[]")  # List of chunk IDs or {page, text_span}
    should_abstain = Column(Boolean, default=False)
    status = Column(String(20), default="unverified")  # unverified, approved, rejected
    source = Column(String(20), default="manual")  # manual, generated, imported, sample
    notes = Column(Text, default="")
    demo_answer = Column(Text, nullable=True)
    demo_citations_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    configuration_id = Column(String(36), ForeignKey("configurations.id"), nullable=False)
    configuration_snapshot_json = Column(Text, nullable=False)
    test_case_count = Column(Integer, default=0)
    evaluated_case_count = Column(Integer, default=0)
    is_simulated = Column(Boolean, default=False)
    simulation_config_json = Column(Text, nullable=True)
    llm_judge_enabled = Column(Boolean, default=False)
    provider = Column(String(30), default="anthropic")
    model_name = Column(String(100), default="claude-3-5-sonnet-20241022")
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    pass_rate = Column(Float, nullable=True)
    mean_recall = Column(Float, nullable=True)
    mean_mrr = Column(Float, nullable=True)
    mean_groundedness = Column(Float, nullable=True)
    pass_threshold = Column(Float, default=0.70)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    results = relationship("CaseResult", back_populates="run", cascade="all, delete-orphan")


class CaseResult(Base):
    __tablename__ = "case_results"

    id = Column(String(36), primary_key=True)
    run_id = Column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id = Column(String(36), nullable=False)
    question = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False)
    reference_answer = Column(Text, nullable=False)
    generated_answer = Column(Text, nullable=False)
    abstained = Column(Boolean, default=False)
    citations_json = Column(Text, default="[]")
    retrieved_chunks_json = Column(Text, default="[]")
    
    # Metrics
    recall_k_json = Column(Text, default="{}")  # {"1": 1.0, "3": 1.0, "5": 1.0}
    hit_rate_k_json = Column(Text, default="{}")
    mrr = Column(Float, default=0.0)
    exact_match = Column(Float, default=0.0)
    normalized_match = Column(Float, default=0.0)
    numeric_match = Column(Float, nullable=True)
    citation_correctness = Column(Float, nullable=True)
    abstention_correctness = Column(Float, nullable=True)
    
    # Model-based metrics
    judge_correctness = Column(Float, nullable=True)
    judge_faithfulness = Column(Float, nullable=True)
    judge_relevance = Column(Float, nullable=True)
    judge_rationale = Column(Text, nullable=True)
    
    # Diagnosis (Section 4.E exact slugs)
    category = Column(String(40), nullable=False)
    rule_fired = Column(String(100), nullable=False)
    rule_facts_json = Column(Text, default="{}")
    suggested_debugging_step = Column(Text, nullable=False)
    confidence = Column(String(10), default="high")  # high, medium, low
    model_diagnosis_explanation = Column(Text, nullable=True)
    is_simulated = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    run = relationship("EvaluationRun", back_populates="results")
    overrides = relationship("ReviewerOverride", back_populates="case_result", cascade="all, delete-orphan")


class ReviewerOverride(Base):
    __tablename__ = "reviewer_overrides"

    id = Column(String(36), primary_key=True)
    case_result_id = Column(String(36), ForeignKey("case_results.id", ondelete="CASCADE"), nullable=False, index=True)
    original_category = Column(String(40), nullable=False)
    overridden_category = Column(String(40), nullable=False)
    reviewer_notes = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)

    case_result = relationship("CaseResult", back_populates="overrides")


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    baseline_run_id = Column(String(36), ForeignKey("evaluation_runs.id"), nullable=False)
    candidate_run_id = Column(String(36), ForeignKey("evaluation_runs.id"), nullable=False)
    test_case_count = Column(Integer, default=0)
    metric_deltas_json = Column(Text, default="{}")
    category_changes_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True)
    job_type = Column(String(30), nullable=False)  # document_ingestion, evaluation_run, testgen
    status = Column(String(20), default="queued")  # queued, running, completed, failed
    progress_percent = Column(Integer, default=0)
    message = Column(String(255), default="")
    result_payload_json = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id = Column(String(36), primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    metric_type = Column(String(20), nullable=False)  # deterministic, model_judged
    formula = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    limitations = Column(Text, nullable=False)
