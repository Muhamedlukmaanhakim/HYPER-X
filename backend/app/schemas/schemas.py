from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

# --- Documents & Chunks ---
class ChunkResponse(BaseModel):
    id: str
    document_id: str
    page: int
    chunk_index: int
    char_start: int
    char_end: int
    text: str
    char_count: int
    token_count_estimate: int

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    file_type: str
    file_size_bytes: int
    page_count: int
    chunk_count: int
    char_count: int
    is_sample: bool
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentDetailResponse(DocumentResponse):
    chunks: List[ChunkResponse] = []

# --- Configurations ---
class ConfigurationCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 3
    similarity_threshold: float = 0.0
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "claude-3-5-sonnet-20241022"
    prompt_template_version: str = "v1_strict_grounded"
    abstention_enabled: bool = True
    is_default: bool = False

class ConfigurationResponse(ConfigurationCreate):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Playground / RAG Ask ---
class AskRequest(BaseModel):
    question: str
    configuration_id: Optional[str] = None
    document_id: Optional[str] = None
    top_k: Optional[int] = 3
    similarity_threshold: Optional[float] = 0.0

class RetrievedPassage(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    score: float
    text: str

class AskResponse(BaseModel):
    question: str
    answer: str
    citations: List[str] = []
    abstained: bool = False
    retrieved_passages: List[RetrievedPassage] = []
    prompt_used: str
    provider: str
    model: str
    latency_ms: float
    is_demo: bool = False

# --- Test Cases ---
QuestionType = Literal[
    "direct_factual",
    "paraphrased",
    "multi_passage",
    "numerical",
    "unanswerable"
]

class ExpectedEvidenceItem(BaseModel):
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    text_span: Optional[str] = None

class TestCaseCreate(BaseModel):
    document_id: Optional[str] = None
    question: str
    question_type: QuestionType = "direct_factual"
    reference_answer: str
    expected_evidence: List[ExpectedEvidenceItem] = []
    should_abstain: bool = False
    status: Literal["unverified", "approved", "rejected"] = "approved"
    source: Literal["manual", "generated", "imported", "sample"] = "manual"
    notes: Optional[str] = ""

class TestCaseUpdate(BaseModel):
    question: Optional[str] = None
    question_type: Optional[QuestionType] = None
    reference_answer: Optional[str] = None
    expected_evidence: Optional[List[ExpectedEvidenceItem]] = None
    should_abstain: Optional[bool] = None
    status: Optional[Literal["unverified", "approved", "rejected"]] = None
    notes: Optional[str] = None

class TestCaseResponse(BaseModel):
    id: str
    document_id: Optional[str] = None
    question: str
    question_type: QuestionType
    reference_answer: str
    expected_evidence: List[ExpectedEvidenceItem] = []
    should_abstain: bool
    status: str
    source: str
    notes: str
    demo_answer: Optional[str] = None
    demo_citations: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class GenerateTestCasesRequest(BaseModel):
    document_id: str
    num_cases: int = 5
    question_types: Optional[List[QuestionType]] = None

# --- Failure Injection ---
class FailureInjectionConfig(BaseModel):
    enabled: bool = False
    remove_relevant_chunk: bool = False
    inject_distractors: bool = False
    num_distractors: int = 2
    reduce_top_k: Optional[int] = None
    truncate_context_chars: Optional[int] = None

# --- Evaluation Runs ---
class EvaluationRunCreate(BaseModel):
    name: Optional[str] = None
    configuration_id: str
    test_case_ids: Optional[List[str]] = None
    include_unverified: bool = False
    k_values: List[int] = [1, 3, 5]
    llm_judge_enabled: bool = False
    pass_threshold: float = 0.70
    failure_injection: Optional[FailureInjectionConfig] = None

class ReviewerOverrideResponse(BaseModel):
    id: str
    case_result_id: str
    original_category: str
    overridden_category: str
    reviewer_notes: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CaseResultResponse(BaseModel):
    id: str
    run_id: str
    test_case_id: str
    question: str
    question_type: str
    reference_answer: str
    generated_answer: str
    abstained: bool
    citations: List[str] = []
    retrieved_chunks: List[Dict[str, Any]] = []
    recall_k: Dict[str, float] = {}
    hit_rate_k: Dict[str, float] = {}
    mrr: float = 0.0
    exact_match: float = 0.0
    normalized_match: float = 0.0
    numeric_match: Optional[float] = None
    citation_correctness: Optional[float] = None
    abstention_correctness: Optional[float] = None
    judge_correctness: Optional[float] = None
    judge_faithfulness: Optional[float] = None
    judge_relevance: Optional[float] = None
    judge_rationale: Optional[str] = None
    category: str
    rule_fired: str
    rule_facts: Dict[str, Any] = {}
    suggested_debugging_step: str
    confidence: str
    model_diagnosis_explanation: Optional[str] = None
    is_simulated: bool = False
    error: Optional[str] = None
    overrides: List[ReviewerOverrideResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EvaluationRunResponse(BaseModel):
    id: str
    name: str
    configuration_id: str
    configuration_snapshot: Dict[str, Any]
    test_case_count: int
    evaluated_case_count: int
    is_simulated: bool
    simulation_config: Optional[Dict[str, Any]] = None
    llm_judge_enabled: bool
    provider: str
    model_name: str
    status: str
    pass_rate: Optional[float] = None
    mean_recall: Optional[float] = None
    mean_mrr: Optional[float] = None
    mean_groundedness: Optional[float] = None
    pass_threshold: float
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class EvaluationRunDetailResponse(EvaluationRunResponse):
    results: List[CaseResultResponse] = []

# --- Reviewer Override ---
class ReviewerOverrideCreate(BaseModel):
    overridden_category: str
    reviewer_notes: Optional[str] = ""

# --- Comparison ---
class ComparisonCreate(BaseModel):
    name: Optional[str] = None
    baseline_run_id: str
    candidate_run_id: str

class PerCaseComparison(BaseModel):
    test_case_id: str
    question: str
    question_type: str
    baseline_category: str
    candidate_category: str
    status_change: Literal["improved", "regressed", "unchanged"]
    baseline_recall: float
    candidate_recall: float
    recall_delta: float
    baseline_answer: str
    candidate_answer: str

class ComparisonResponse(BaseModel):
    id: str
    name: str
    baseline_run_id: str
    candidate_run_id: str
    test_case_count: int
    baseline_pass_rate: float
    candidate_pass_rate: float
    pass_rate_delta: float
    mean_recall_delta: float
    mean_mrr_delta: float
    metric_deltas: Dict[str, float]
    category_changes: Dict[str, Any]
    per_case_comparisons: List[PerCaseComparison] = []
    sample_size_warning: Optional[str] = None
    created_at: datetime

# --- Provider & Settings ---
class ProviderStatusResponse(BaseModel):
    provider: str
    configured: bool
    model: str
    embedding_model: str
    connection_tested: bool = False
    connection_status: Literal["connected", "not_configured", "error"] = "not_configured"
    error_details: Optional[str] = None
    demo_mode: bool = True

class SettingsUpdate(BaseModel):
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None

# --- Jobs ---
class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    progress_percent: int
    message: str
    result_payload: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Metric Definitions ---
class MetricDefinitionResponse(BaseModel):
    slug: str
    name: str
    metric_type: Literal["deterministic", "model_judged"]
    formula: str
    description: str
    limitations: str
