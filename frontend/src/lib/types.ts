export type QuestionType =
  | "direct_factual"
  | "paraphrased"
  | "multi_passage"
  | "numerical"
  | "unanswerable";

export type DiagnosisCategory =
  | "pass"
  | "retrieval_miss"
  | "incomplete_or_irrelevant_context"
  | "unsupported_answer"
  | "incorrect_despite_relevant_context"
  | "citation_error"
  | "unanswerable_answered"
  | "needs_review";

export interface Chunk {
  id: string;
  document_id: string;
  page: number;
  chunk_index: number;
  char_start: number;
  char_end: number;
  text: string;
  char_count: number;
  token_count_estimate: number;
}

export interface Document {
  id: string;
  filename: string;
  original_name: string;
  file_type: string;
  file_size_bytes: number;
  page_count: number;
  chunk_count: number;
  char_count: number;
  is_sample: boolean;
  status: "processing" | "indexed" | "error";
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  chunks?: Chunk[];
}

export interface Configuration {
  id: string;
  name: string;
  description?: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  similarity_threshold: number;
  embedding_model: string;
  llm_model: string;
  prompt_template_version: string;
  abstention_enabled: boolean;
  is_default: boolean;
  created_at?: string;
}

export interface ExpectedEvidence {
  chunk_id?: string;
  page?: number;
  text_span?: string;
}

export interface TestCase {
  id: string;
  document_id?: string | null;
  question: string;
  question_type: QuestionType;
  reference_answer: string;
  expected_evidence: ExpectedEvidence[];
  should_abstain: boolean;
  status: "unverified" | "approved" | "rejected";
  source: "manual" | "generated" | "imported" | "sample";
  notes?: string;
  demo_answer?: string;
  demo_citations?: string[];
  created_at: string;
  updated_at: string;
}

export interface RetrievedPassage {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page: number;
  score: number;
  text: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  citations: string[];
  abstained: boolean;
  retrieved_passages: RetrievedPassage[];
  prompt_used: string;
  provider: string;
  model: string;
  latency_ms: number;
  is_demo: boolean;
}

export interface ReviewerOverride {
  id: string;
  case_result_id: string;
  original_category: string;
  overridden_category: string;
  reviewer_notes: string;
  created_at: string;
}

export interface CaseResult {
  id: string;
  run_id: string;
  test_case_id: string;
  question: string;
  question_type: QuestionType;
  reference_answer: string;
  generated_answer: string;
  abstained: boolean;
  citations: string[];
  retrieved_chunks: RetrievedPassage[];
  recall_k: Record<string, number>;
  hit_rate_k: Record<string, number>;
  mrr: number;
  exact_match: number;
  normalized_match: number;
  numeric_match?: number | null;
  citation_correctness?: number | null;
  abstention_correctness?: number | null;
  judge_correctness?: number | null;
  judge_faithfulness?: number | null;
  judge_relevance?: number | null;
  judge_rationale?: string | null;
  category: DiagnosisCategory;
  rule_fired: string;
  rule_facts: Record<string, any>;
  suggested_debugging_step: string;
  confidence: "high" | "medium" | "low";
  model_diagnosis_explanation?: string | null;
  is_simulated: boolean;
  error?: string | null;
  overrides: ReviewerOverride[];
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  name: string;
  configuration_id: string;
  configuration_snapshot: Record<string, any>;
  test_case_count: number;
  evaluated_case_count: number;
  is_simulated: boolean;
  simulation_config?: Record<string, any> | null;
  llm_judge_enabled: boolean;
  provider: string;
  model_name: string;
  status: "pending" | "running" | "completed" | "failed";
  pass_rate?: number | null;
  mean_recall?: number | null;
  mean_mrr?: number | null;
  mean_groundedness?: number | null;
  pass_threshold: number;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
  results?: CaseResult[];
}

export interface PerCaseComparison {
  test_case_id: string;
  question: string;
  question_type: string;
  baseline_category: string;
  candidate_category: string;
  status_change: "improved" | "regressed" | "unchanged";
  baseline_recall: number;
  candidate_recall: number;
  recall_delta: number;
  baseline_answer: string;
  candidate_answer: string;
}

export interface Comparison {
  id: string;
  name: string;
  baseline_run_id: string;
  candidate_run_id: string;
  test_case_count: number;
  baseline_pass_rate: number;
  candidate_pass_rate: number;
  pass_rate_delta: number;
  mean_recall_delta: number;
  mean_mrr_delta: number;
  metric_deltas: Record<string, any>;
  category_changes: Record<string, any>;
  per_case_comparisons: PerCaseComparison[];
  sample_size_warning?: string | null;
  created_at: string;
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  model: string;
  embedding_model: string;
  connection_tested: boolean;
  connection_status: "connected" | "not_configured" | "error";
  error_details?: string | null;
  demo_mode: boolean;
}

export interface MetricDefinition {
  slug: string;
  name: string;
  metric_type: "deterministic" | "model_judged";
  formula: string;
  description: string;
  limitations: string;
}

export interface SystemHealth {
  status: "healthy" | "degraded";
  product: string;
  tagline: string;
  version: string;
  database: {
    status: string;
    dialect: string;
    tables_initialized: boolean;
    table_count: number;
    tables?: string[];
    healthy: boolean;
    error?: string;
  };
  vectorstore: {
    status: string;
    provider: string;
    collection: string;
    chunk_count: number;
    distance_metric?: string;
    healthy: boolean;
    error?: string;
  };
  embeddings: {
    status: string;
    model: string;
    dimension: number;
    normalized?: boolean;
    healthy: boolean;
    error?: string;
  };
  llm_provider: {
    provider: string;
    configured: boolean;
    model: string;
  };
}

