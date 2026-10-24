import {
  AskResponse,
  Comparison,
  Configuration,
  Document,
  EvaluationRun,
  MetricDefinition,
  ProviderStatus,
  ReviewerOverride,
  SystemHealth,
  TestCase
} from "./types";


const API_BASE = "http://127.0.0.1:8000/api";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...(options?.headers || {}),
      },
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson?.error?.message) {
          errorMsg = errJson.error.message;
        } else if (errJson?.detail) {
          errorMsg = errJson.detail;
        }
      } catch {
        errorMsg = await res.text();
      }
      throw new Error(errorMsg || `Request failed with status ${res.status}`);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Settings & Provider
  getHealth: () => request<SystemHealth>("/health"),
  getProviderStatus: () => request<ProviderStatus>("/settings/status"),
  testConnection: () =>
    request<{ configured: boolean; connected: boolean; latency_ms?: number; message?: string; error?: string }>(
      "/settings/test-connection",
      { method: "POST" }
    ),
  getConfigurations: () => request<Configuration[]>("/settings/configurations"),

  createConfiguration: (data: Partial<Configuration>) =>
    request<Configuration>("/settings/configurations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getMetricDefinitions: () => request<MetricDefinition[]>("/settings/metrics"),

  // Documents
  getDocuments: () => request<Document[]>("/documents"),
  getDocument: (id: string) => request<Document>(`/documents/${id}`),
  uploadDocument: (formData: FormData) =>
    request<Document>("/documents/upload", {
      method: "POST",
      body: formData,
    }),
  deleteDocument: (id: string) =>
    request<{ message: string }>(`/documents/${id}`, { method: "DELETE" }),
  seedSampleDocument: () =>
    request<Document>("/documents/seed-sample", { method: "POST" }),

  // RAG Playground
  askRag: (data: { question: string; top_k?: number; similarity_threshold?: number; configuration_id?: string }) =>
    request<AskResponse>("/rag/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Test Cases
  getTestCases: (params?: { document_id?: string; status?: string; question_type?: string }) => {
    const q = new URLSearchParams();
    if (params?.document_id) q.set("document_id", params.document_id);
    if (params?.status) q.set("status", params.status);
    if (params?.question_type) q.set("question_type", params.question_type);
    const qs = q.toString();
    return request<TestCase[]>(`/testcases${qs ? `?${qs}` : ""}`);
  },
  createTestCase: (data: Partial<TestCase>) =>
    request<TestCase>("/testcases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  updateTestCase: (id: string, data: Partial<TestCase>) =>
    request<TestCase>(`/testcases/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteTestCase: (id: string) =>
    request<{ message: string }>(`/testcases/${id}`, { method: "DELETE" }),
  seedSampleTestCases: () => request<TestCase[]>("/testcases/seed-sample", { method: "POST" }),
  generateTestCases: (data: { document_id: string; num_cases?: number }) =>
    request<TestCase[]>("/testcases/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  importTestCasesCsv: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<{ imported_count: number; error_count: number; errors: string[]; message: string }>(
      "/testcases/import/csv",
      {
        method: "POST",
        body: formData,
      }
    );
  },

  // Evaluations
  getEvaluations: () => request<EvaluationRun[]>("/evaluations"),
  getEvaluation: (id: string) => request<EvaluationRun>(`/evaluations/${id}`),
  runEvaluation: (data: any) =>
    request<EvaluationRun>("/evaluations/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  deleteEvaluation: (id: string) =>
    request<{ message: string }>(`/evaluations/${id}`, { method: "DELETE" }),
  createReviewerOverride: (runId: string, caseResultId: string, data: { overridden_category: string; reviewer_notes?: string }) =>
    request<ReviewerOverride>(`/evaluations/${runId}/results/${caseResultId}/overrides`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  generateCaseExplanation: (runId: string, caseResultId: string) =>
    request<{ case_result_id: string; category: string; model_diagnosis_explanation: string }>(
      `/evaluations/${runId}/results/${caseResultId}/explain`,
      { method: "POST" }
    ),

  // Comparisons
  getComparisons: () => request<Comparison[]>("/comparisons"),
  getComparison: (id: string) => request<Comparison>(`/comparisons/${id}`),
  createComparison: (data: { baseline_run_id: string; candidate_run_id: string; name?: string }) =>
    request<Comparison>("/comparisons", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),


  // Exports URLs
  getRunCsvUrl: (runId: string) => `${API_BASE}/exports/runs/${runId}/csv`,
  getRunSummaryCsvUrl: (runId: string) => `${API_BASE}/exports/runs/${runId}/summary-csv`,
  getRunHtmlReportUrl: (runId: string) => `${API_BASE}/exports/runs/${runId}/html-report`,
  getTestCasesCsvUrl: () => `${API_BASE}/testcases/export/csv`,
};
