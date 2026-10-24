import React, { useEffect, useState } from "react";
import { CaseResult, EvaluationRun } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { MetricCard } from "../components/ui/MetricCard";
import { Badge, CategoryBadge } from "../components/ui/Badge";
import { FailureCategoryChart } from "../components/domain/FailureCategoryChart";
import {
  ArrowLeft,
  CheckCircle,
  Download,
  ExternalLink,
  Eye,
  Filter,
  Layers,
  RotateCw,
  Search,
  ShieldAlert,
  Sparkles
} from "lucide-react";

interface ResultsPageProps {
  runId: string;
  onBack: () => void;
  onSelectCase: (caseResult: CaseResult) => void;
}

export const ResultsPage: React.FC<ResultsPageProps> = ({
  runId,
  onBack,
  onSelectCase,
}) => {
  const [run, setRun] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchRunDetails = async () => {
    try {
      const data = await api.getEvaluation(runId);
      setRun(data);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRunDetails();
  }, [runId]);

  if (loading) {
    return (
      <div className="py-20 text-center font-mono text-sm">
        <RotateCw size={24} className="animate-spin mx-auto mb-2 text-ink" />
        Loading evaluation run results &amp; metric calculations...
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8 text-center font-mono">
        <p className="text-danger font-bold mb-4">{errorMsg || "Evaluation run not found."}</p>
        <Button variant="secondary" onClick={onBack}>
          &larr; Back to Dashboard
        </Button>
      </div>
    );
  }

  const results = run.results || [];

  // Compute category chart data
  const counts: Record<string, number> = {};
  for (const r of results) {
    counts[r.category] = (counts[r.category] || 0) + 1;
  }
  const chartData = Object.entries(counts).map(([cat, count]) => ({
    category: cat,
    count,
  }));

  // Filtering
  const filteredResults = results.filter((r) => {
    if (categoryFilter !== "all" && r.category !== categoryFilter) return false;
    if (typeFilter !== "all" && r.question_type !== typeFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        r.question.toLowerCase().includes(q) ||
        r.reference_answer.toLowerCase().includes(q) ||
        r.generated_answer.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <button
            onClick={onBack}
            className="font-mono text-xs text-ink/70 hover:text-ink hover:underline flex items-center gap-1 cursor-pointer"
          >
            <ArrowLeft size={14} /> Back to Runs
          </button>
          <div className="flex items-center gap-3">
            <h1 className="font-display font-black text-2xl text-ink tracking-tight">
              {run.name}
            </h1>
            {run.is_simulated ? (
              <Badge variant="simulated" size="md">SIMULATED (FAILURE INJECTED)</Badge>
            ) : (
              <Badge variant="pass" size="md">REAL RUN</Badge>
            )}
            <Badge variant="neutral" size="sm">{run.model_name}</Badge>
          </div>
          <p className="font-mono text-xs text-ink/60">
            Run ID: {run.id} &bull; Timestamp: {new Date(run.created_at).toLocaleString()}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href={api.getRunCsvUrl(run.id)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 border-[2.5px] border-ink bg-lime text-xs font-mono font-bold hover:bg-lime-hover shadow-[3px_3px_0_#171717] transition-all"
            download
          >
            <Download size={14} />
            Export Case CSV
          </a>
          <a
            href={api.getRunSummaryCsvUrl(run.id)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 border-[2.5px] border-ink bg-surface text-xs font-mono font-bold hover:bg-surface-muted shadow-[3px_3px_0_#171717] transition-all"
            download
          >
            <Download size={14} />
            Summary CSV
          </a>
          <a
            href={api.getRunHtmlReportUrl(run.id)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 border-[2.5px] border-ink bg-paper text-xs font-mono font-bold hover:bg-surface-muted shadow-[3px_3px_0_#171717] transition-all"
          >
            <ExternalLink size={14} />
            Executive HTML Report
          </a>
        </div>
      </div>

      {/* Metric Cards Bento Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Pass Rate"
          value={
            run.pass_rate !== null && run.pass_rate !== undefined
              ? `${(run.pass_rate * 100).toFixed(1)}%`
              : "N/A"
          }
          sublabel={`Threshold: ≥ ${run.pass_threshold * 100}%`}
          metricType="deterministic"
          formula="passed_cases / total_cases"
          limitation="Requires correctness and absence of critical failure modes."
          highlight={true}
        />
        <MetricCard
          label="Mean Recall@K"
          value={
            run.mean_recall !== null && run.mean_recall !== undefined
              ? run.mean_recall.toFixed(3)
              : "N/A"
          }
          sublabel="Evidence coverage in top-K"
          metricType="deterministic"
          formula="matched_expected_evidence / total_expected_evidence"
          limitation="Relies on annotated expected evidence spans."
        />
        <MetricCard
          label="Mean MRR"
          value={
            run.mean_mrr !== null && run.mean_mrr !== undefined
              ? run.mean_mrr.toFixed(3)
              : "N/A"
          }
          sublabel="Rank of 1st relevant chunk"
          metricType="deterministic"
          formula="1.0 / first_relevant_chunk_rank"
          limitation="Only evaluates the first relevant chunk in retrieved order."
        />
        <MetricCard
          label="Total Cases"
          value={run.evaluated_case_count}
          sublabel="Evaluated test cases"
          metricType="deterministic"
        />
      </div>

      {/* Failure Category Distribution Panel */}
      <Card title="Failure Modes &amp; Diagnosis Distribution">
        <FailureCategoryChart data={chartData} />
      </Card>

      {/* Filter and Search Bar */}
      <div className="p-3 bg-surface border-2 border-ink shadow-[3px_3px_0_#171717] flex flex-wrap items-center justify-between gap-3 font-mono text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-ink/60" />
            <span className="font-bold">CATEGORY:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="p-1 border border-ink bg-paper font-mono text-xs"
            >
              <option value="all">All Categories</option>
              <option value="pass">Pass</option>
              <option value="retrieval_miss">Retrieval Miss</option>
              <option value="incomplete_or_irrelevant_context">Incomplete Context</option>
              <option value="unsupported_answer">Unsupported Answer</option>
              <option value="incorrect_despite_relevant_context">Incorrect Despite Context</option>
              <option value="citation_error">Citation Error</option>
              <option value="unanswerable_answered">Unanswerable Answered</option>
              <option value="needs_review">Needs Review</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="font-bold">TYPE:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="p-1 border border-ink bg-paper font-mono text-xs"
            >
              <option value="all">All Types</option>
              <option value="direct_factual">Direct Factual</option>
              <option value="paraphrased">Paraphrased</option>
              <option value="multi_passage">Multi-Passage</option>
              <option value="numerical">Numerical</option>
              <option value="unanswerable">Unanswerable</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Search size={14} className="text-ink/60" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search questions or answers..."
            className="p-1 border border-ink bg-paper font-mono text-xs w-48 sm:w-64"
          />
        </div>
      </div>

      {/* Case Explorer Table */}
      <Card title={`Case Explorer (${filteredResults.length} cases)`}>
        {filteredResults.length === 0 ? (
          <div className="py-8 text-center font-mono text-xs text-ink/60">
            No case results matching active filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-ink bg-surface-muted/50">
                  <th className="p-2.5">CATEGORY &amp; RULE</th>
                  <th className="p-2.5">QUESTION</th>
                  <th className="p-2.5">GENERATED ANSWER VS REFERENCE</th>
                  <th className="p-2.5">RECALL@K</th>
                  <th className="p-2.5">CITATIONS</th>
                  <th className="p-2.5 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((r) => {
                  let recVal = 0.0;
                  try {
                    const parsed = r.recall_k || {};
                    recVal = parsed["3"] ?? parsed["1"] ?? r.mrr;
                  } catch {}

                  return (
                    <tr
                      key={r.id}
                      className="border-b border-ink/20 hover:bg-surface-muted/30 transition-all cursor-pointer"
                      onClick={() => onSelectCase(r)}
                    >
                      <td className="p-2.5 align-top w-52">
                        <CategoryBadge category={r.category} />
                        <div className="text-[11px] text-ink/70 mt-1 font-bold line-clamp-2">
                          {r.rule_fired}
                        </div>
                        {r.overrides && r.overrides.length > 0 && (
                          <Badge variant="warning" size="sm" className="mt-1">
                            OVERRIDDEN
                          </Badge>
                        )}
                      </td>

                      <td className="p-2.5 align-top max-w-xs">
                        <div className="font-bold text-ink text-sm font-display mb-1">
                          {r.question}
                        </div>
                        <Badge variant="neutral" size="sm">
                          {r.question_type.replace(/_/g, " ")}
                        </Badge>
                      </td>

                      <td className="p-2.5 align-top max-w-md space-y-1">
                        <div className="p-1.5 bg-paper border border-ink/20 text-xs">
                          <span className="font-bold text-ink/60 block text-[10px] uppercase">
                            Generated Output:
                          </span>
                          <span className={r.abstained ? "text-warning font-bold" : "text-ink"}>
                            {r.generated_answer}
                          </span>
                        </div>
                        <div className="p-1.5 bg-surface-muted/40 border border-ink/10 text-[11px] text-ink/70">
                          <span className="font-bold text-ink/60 block text-[9px] uppercase">
                            Reference:
                          </span>
                          {r.reference_answer}
                        </div>
                      </td>

                      <td className="p-2.5 align-top font-bold">
                        {recVal.toFixed(2)}
                      </td>

                      <td className="p-2.5 align-top">
                        {r.citations && r.citations.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {r.citations.map((c, i) => (
                              <span key={i} className="px-1 border border-ink bg-lime/40 text-[10px]">
                                [{c}]
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-ink/40 text-[11px]">None</span>
                        )}
                      </td>

                      <td className="p-2.5 align-top text-right">
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={<Eye size={12} />}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectCase(r);
                          }}
                        >
                          Diagnose
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
