import React, { useEffect, useState } from "react";
import { Comparison, EvaluationRun } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { MetricCard } from "../components/ui/MetricCard";
import { Badge, CategoryBadge } from "../components/ui/Badge";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  HelpCircle,
  RotateCw,
  Split,
  TrendingDown,
  TrendingUp,
  XCircle
} from "lucide-react";

export const ComparePage: React.FC = () => {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [baselineId, setBaselineId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const data = await api.getEvaluations();
        setRuns(data);
        if (data.length >= 2) {
          setBaselineId(data[1].id);
          setCandidateId(data[0].id);
        } else if (data.length === 1) {
          setBaselineId(data[0].id);
          setCandidateId(data[0].id);
        }
      } catch (err: any) {
        setErrorMsg(err.message);
      }
    };
    fetchRuns();
  }, []);

  const handleCompare = async () => {
    if (!baselineId || !candidateId) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const comp = await api.createComparison({
        baseline_run_id: baselineId,
        candidate_run_id: candidateId,
      });
      setComparison(comp);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const deltas = comparison?.metric_deltas || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-2xl text-ink tracking-tight flex items-center gap-2">
            <Split size={24} />
            <span>RAG Configuration Comparison Matrix</span>
          </h1>
          <p className="font-mono text-xs text-ink/70">
            Compare baseline vs. candidate runs evaluated on identical ground-truth test cases.
            Highlights regressions as prominently as improvements.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-danger/10 border-2 border-danger text-danger text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* Run Selection Form */}
      <Card title="Select Runs to Compare">
        <div className="space-y-4 font-mono text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold uppercase mb-1">Baseline Run (A)</label>
              <select
                value={baselineId}
                onChange={(e) => setBaselineId(e.target.value)}
                className="w-full p-2 border-2 border-ink bg-paper"
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.is_simulated ? "SIMULATED" : "REAL"} &bull; {new Date(r.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Candidate Run (B)</label>
              <select
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                className="w-full p-2 border-2 border-ink bg-paper"
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.is_simulated ? "SIMULATED" : "REAL"} &bull; {new Date(r.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Button
            variant="primary"
            size="md"
            icon={<Split size={16} />}
            disabled={!baselineId || !candidateId || loading}
            onClick={handleCompare}
          >
            {loading ? "Computing Metric Deltas..." : "Execute Side-by-Side Comparison"}
          </Button>
        </div>
      </Card>

      {/* Comparison Results */}
      {comparison && (
        <div className="space-y-6">
          {/* Statistical Caution Banner if small sample */}
          {comparison.sample_size_warning && (
            <div className="p-3.5 bg-warning/20 border-2 border-ink shadow-[2px_2px_0_#171717] font-mono text-xs flex items-center gap-2 font-bold">
              <AlertTriangle size={18} className="text-warning flex-shrink-0" />
              <span>{comparison.sample_size_warning}</span>
            </div>
          )}

          {/* Delta Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard
              label="Pass Rate Delta"
              value={`${(comparison.candidate_pass_rate * 100).toFixed(1)}%`}
              sublabel={`Baseline: ${(comparison.baseline_pass_rate * 100).toFixed(1)}%`}
              delta={comparison.pass_rate_delta}
              metricType="deterministic"
            />
            <MetricCard
              label="Recall@K Delta"
              value={comparison.mean_recall_delta >= 0 ? `+${comparison.mean_recall_delta}` : comparison.mean_recall_delta}
              sublabel="Average evidence retrieval shift"
              delta={comparison.mean_recall_delta}
              metricType="deterministic"
            />
            <MetricCard
              label="Improved Cases"
              value={deltas.improved_cases ?? 0}
              sublabel="Questions promoted to pass"
              metricType="deterministic"
            />
            <MetricCard
              label="Regressed Cases"
              value={deltas.regressed_cases ?? 0}
              sublabel="Questions that failed in candidate"
              metricType="deterministic"
              highlight={deltas.regressed_cases > 0}
            />
          </div>

          {/* Per-Case Regressions / Improvements Explorer Table */}
          <Card title={`Per-Question Transition Matrix (${comparison.per_case_comparisons.length} cases)`}>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-mono text-xs border-collapse">
                <thead>
                  <tr className="border-b-2 border-ink bg-surface-muted/50">
                    <th className="p-2.5">STATUS</th>
                    <th className="p-2.5">QUESTION</th>
                    <th className="p-2.5">BASELINE CATEGORY</th>
                    <th className="p-2.5">CANDIDATE CATEGORY</th>
                    <th className="p-2.5">RECALL DELTA</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.per_case_comparisons.map((c) => {
                    const isImproved = c.status_change === "improved";
                    const isRegressed = c.status_change === "regressed";

                    return (
                      <tr
                        key={c.test_case_id}
                        className={`border-b border-ink/20 transition-all ${
                          isRegressed
                            ? "bg-danger/10 hover:bg-danger/15"
                            : isImproved
                            ? "bg-lime/10 hover:bg-lime/20"
                            : "hover:bg-surface-muted/30"
                        }`}
                      >
                        <td className="p-2.5">
                          {isImproved ? (
                            <span className="inline-flex items-center gap-1 text-ink font-bold bg-lime px-2 py-0.5 border border-ink">
                              <TrendingUp size={12} /> IMPROVED
                            </span>
                          ) : isRegressed ? (
                            <span className="inline-flex items-center gap-1 text-white font-bold bg-danger px-2 py-0.5 border border-ink">
                              <TrendingDown size={12} /> REGRESSED
                            </span>
                          ) : (
                            <span className="text-ink/60 font-bold px-2 py-0.5 border border-ink/40 bg-surface">
                              UNCHANGED
                            </span>
                          )}
                        </td>

                        <td className="p-2.5 font-bold font-display text-sm text-ink max-w-sm">
                          {c.question}
                        </td>

                        <td className="p-2.5">
                          <CategoryBadge category={c.baseline_category} />
                        </td>

                        <td className="p-2.5">
                          <CategoryBadge category={c.candidate_category} />
                        </td>

                        <td className="p-2.5 font-bold">
                          <span
                            className={
                              c.recall_delta > 0
                                ? "text-success font-bold"
                                : c.recall_delta < 0
                                ? "text-danger font-bold"
                                : "text-ink/60"
                            }
                          >
                            {c.recall_delta > 0 ? `+${c.recall_delta.toFixed(2)}` : c.recall_delta.toFixed(2)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
