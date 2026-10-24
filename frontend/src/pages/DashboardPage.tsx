import React, { useEffect, useState } from "react";
import { EvaluationRun, ProviderStatus } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { MetricCard } from "../components/ui/MetricCard";
import { Badge, CategoryBadge } from "../components/ui/Badge";
import { FailureCategoryChart } from "../components/domain/FailureCategoryChart";
import {
  Activity,
  ArrowRight,
  Database,
  FileText,
  Play,
  RotateCw,
  ShieldAlert,
  Sparkles
} from "lucide-react";

interface DashboardPageProps {
  onNavigate: (tab: string, runId?: string) => void;
  providerStatus?: ProviderStatus | null;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  providerStatus,
}) => {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const fetchRuns = async () => {
    try {
      const data = await api.getEvaluations();
      setRuns(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const latestRun = runs.length > 0 ? runs[0] : null;

  const handleSeedSample = async () => {
    setActionLoading(true);
    try {
      await api.seedSampleDocument();
      await api.seedSampleTestCases();
      setMessage("Deterministic sample document & test cases loaded successfully!");
      fetchRuns();
    } catch (err: any) {
      setMessage(`Error seeding sample data: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  // Compute category breakdown from latest run
  const categoryCounts: Record<string, number> = {};
  if (latestRun && (latestRun as any).results) {
    for (const r of (latestRun as any).results) {
      categoryCounts[r.category] = (categoryCounts[r.category] || 0) + 1;
    }
  }

  const chartData = Object.entries(categoryCounts).map(([cat, count]) => ({
    category: cat,
    count,
  }));

  return (
    <div className="space-y-6">
      {/* Hero Header */}
      <div className="p-6 sm:p-8 bg-paper border-brutal border-ink shadow-brutal flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-lime border border-ink text-xs font-mono font-bold uppercase shadow-[2px_2px_0_#171717]">
            <Sparkles size={13} />
            <span>RAG Truth &amp; Failure Inspector</span>
          </div>
          <h1 className="font-display font-black text-3xl sm:text-4xl text-ink tracking-tight">
            Trust, but verify.
          </h1>
          <p className="font-body text-sm sm:text-base text-ink/80 leading-relaxed">
            A developer platform to evaluate Retrieval-Augmented Generation systems and explain
            <strong className="text-ink font-bold"> WHY </strong> answers fail. Measure evidence
            grounding, inspect retrieval recall, classify failure modes via rule-based decision trees,
            and compare pipeline configurations.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          <Button
            variant="primary"
            size="lg"
            icon={<Play size={18} />}
            onClick={() => onNavigate("runner")}
          >
            Run Evaluation
          </Button>
          <Button
            variant="secondary"
            size="lg"
            icon={<Database size={18} />}
            onClick={handleSeedSample}
            disabled={actionLoading}
          >
            Load Sample Data
          </Button>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-surface border-2 border-ink text-xs font-mono font-bold shadow-[2px_2px_0_#171717] flex justify-between items-center">
          <span>{message}</span>
          <button onClick={() => setMessage(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* Asymmetrical Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {/* Latest Run Feature Panel (Span 2 or 3) */}
        <div className="md:col-span-2 lg:col-span-3">
          <Card
            title={
              <div className="flex items-center gap-2">
                <Activity size={18} />
                <span>Latest Evaluation Run</span>
                {latestRun?.is_simulated && <Badge variant="simulated" size="sm">SIMULATED</Badge>}
              </div>
            }
            action={
              latestRun ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onNavigate("results", latestRun.id)}
                >
                  View Details &rarr;
                </Button>
              ) : null
            }
          >
            {latestRun ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-baseline justify-between gap-4 pb-3 border-b-2 border-ink/20">
                  <div>
                    <h2 className="font-display font-bold text-xl text-ink">{latestRun.name}</h2>
                    <p className="font-mono text-xs text-ink/60">
                      Model: {latestRun.model_name} &bull; Cases: {latestRun.evaluated_case_count}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-ink/70">STATUS:</span>
                    <Badge variant={latestRun.status === "completed" ? "pass" : "review"}>
                      {latestRun.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>

                {/* 3 Key Metrics Banner */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-paper border border-ink">
                    <div className="font-mono text-[11px] text-ink/70 uppercase">Pass Rate</div>
                    <div className="font-display text-2xl font-bold text-ink">
                      {latestRun.pass_rate !== null && latestRun.pass_rate !== undefined
                        ? `${(latestRun.pass_rate * 100).toFixed(1)}%`
                        : "N/A"}
                    </div>
                  </div>
                  <div className="p-3 bg-paper border border-ink">
                    <div className="font-mono text-[11px] text-ink/70 uppercase">Mean Recall@K</div>
                    <div className="font-display text-2xl font-bold text-ink">
                      {latestRun.mean_recall !== null && latestRun.mean_recall !== undefined
                        ? latestRun.mean_recall.toFixed(3)
                        : "N/A"}
                    </div>
                  </div>
                  <div className="p-3 bg-paper border border-ink">
                    <div className="font-mono text-[11px] text-ink/70 uppercase">Mean MRR</div>
                    <div className="font-display text-2xl font-bold text-ink">
                      {latestRun.mean_mrr !== null && latestRun.mean_mrr !== undefined
                        ? latestRun.mean_mrr.toFixed(3)
                        : "N/A"}
                    </div>
                  </div>
                </div>

                {/* Failure Modes Chart */}
                <div className="pt-2">
                  <div className="font-mono text-xs font-bold uppercase mb-2">Failure Mode Distribution:</div>
                  <FailureCategoryChart data={chartData} />
                </div>
              </div>
            ) : (
              <div className="py-12 text-center space-y-3 font-mono">
                <ShieldAlert size={36} className="mx-auto text-ink/40" />
                <p className="text-sm font-bold">No evaluation runs recorded yet.</p>
                <p className="text-xs text-ink/60 max-w-sm mx-auto">
                  Load the sample Acme Corp dataset and click 'Run Evaluation' to see real deterministic metrics.
                </p>
                <Button variant="primary" size="md" onClick={() => onNavigate("runner")}>
                  Start First Run
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Quick Nav / Benchmark Bento Sidecard */}
        <div className="space-y-6">
          <Card title="Quick Inspection">
            <div className="space-y-3 font-mono text-xs">
              <div
                onClick={() => onNavigate("playground")}
                className="p-3 border-2 border-ink bg-surface-muted/40 hover:bg-lime/20 cursor-pointer transition-all flex items-center justify-between"
              >
                <div>
                  <div className="font-bold text-sm">Playground</div>
                  <div className="text-[11px] text-ink/70">Ask question &amp; see citations</div>
                </div>
                <ArrowRight size={16} />
              </div>

              <div
                onClick={() => onNavigate("testcases")}
                className="p-3 border-2 border-ink bg-surface-muted/40 hover:bg-lime/20 cursor-pointer transition-all flex items-center justify-between"
              >
                <div>
                  <div className="font-bold text-sm">Test Cases</div>
                  <div className="text-[11px] text-ink/70">Inspect ground-truth test set</div>
                </div>
                <ArrowRight size={16} />
              </div>

              <div
                onClick={() => onNavigate("compare")}
                className="p-3 border-2 border-ink bg-surface-muted/40 hover:bg-lime/20 cursor-pointer transition-all flex items-center justify-between"
              >
                <div>
                  <div className="font-bold text-sm">Compare Runs</div>
                  <div className="text-[11px] text-ink/70">Baseline vs candidate diff</div>
                </div>
                <ArrowRight size={16} />
              </div>
            </div>
          </Card>

          {/* Metric Philosophy Box */}
          <Card title="Source of Truth">
            <div className="text-xs font-mono space-y-2 text-ink/80 leading-relaxed">
              <p>
                <strong className="text-ink font-bold">Deterministic first:</strong> Recall@K, Hit Rate,
                and MRR run on local embeddings. Zero fake numbers.
              </p>
              <p>
                <strong className="text-ink font-bold">Never guess:</strong> If evidence is missing, cases
                are flagged <Badge variant="review" size="sm">NEEDS REVIEW</Badge>.
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Recent Runs Table */}
      <Card
        title="Recent Evaluation Runs"
        action={
          <Button variant="ghost" size="sm" icon={<RotateCw size={14} />} onClick={fetchRuns}>
            Refresh
          </Button>
        }
      >
        {runs.length === 0 ? (
          <div className="py-6 text-center font-mono text-xs text-ink/60">
            No past runs stored in SQLite.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-ink bg-surface-muted/50">
                  <th className="p-2.5">RUN NAME</th>
                  <th className="p-2.5">TYPE</th>
                  <th className="p-2.5">CASES</th>
                  <th className="p-2.5">PASS RATE</th>
                  <th className="p-2.5">RECALL@K</th>
                  <th className="p-2.5">DATE</th>
                  <th className="p-2.5 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-ink/20 hover:bg-surface-muted/30 transition-all cursor-pointer"
                    onClick={() => onNavigate("results", r.id)}
                  >
                    <td className="p-2.5 font-bold font-display text-sm">{r.name}</td>
                    <td className="p-2.5">
                      {r.is_simulated ? (
                        <Badge variant="simulated" size="sm">SIMULATED</Badge>
                      ) : (
                        <Badge variant="pass" size="sm">REAL</Badge>
                      )}
                    </td>
                    <td className="p-2.5">{r.evaluated_case_count}</td>
                    <td className="p-2.5 font-bold">
                      {r.pass_rate !== null && r.pass_rate !== undefined
                        ? `${(r.pass_rate * 100).toFixed(1)}%`
                        : "N/A"}
                    </td>
                    <td className="p-2.5">
                      {r.mean_recall !== null && r.mean_recall !== undefined
                        ? r.mean_recall.toFixed(3)
                        : "N/A"}
                    </td>
                    <td className="p-2.5 text-ink/60">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-2.5 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onNavigate("results", r.id);
                        }}
                      >
                        Inspect &rarr;
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
