import React, { useEffect, useState } from "react";
import { Configuration } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import {
  AlertCircle,
  Bug,
  CheckCircle2,
  FileCheck,
  Play,
  RotateCw,
  Sliders,
  Sparkles,
  Zap
} from "lucide-react";

interface EvaluationRunnerPageProps {
  onEvaluationCompleted: (runId: string) => void;
}

export const EvaluationRunnerPage: React.FC<EvaluationRunnerPageProps> = ({
  onEvaluationCompleted,
}) => {
  const [configs, setConfigs] = useState<Configuration[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState("");
  const [runName, setRunName] = useState("");
  const [includeUnverified, setIncludeUnverified] = useState(false);
  const [llmJudgeEnabled, setLlmJudgeEnabled] = useState(false);
  const [kValues, setKValues] = useState<string>("1, 3, 5");
  const [passThreshold, setPassThreshold] = useState(0.70);

  // Failure Injection Controls
  const [injectionEnabled, setInjectionEnabled] = useState(false);
  const [removeRelevant, setRemoveRelevant] = useState(true);
  const [injectDistractors, setInjectDistractors] = useState(false);
  const [reduceK, setReduceK] = useState<number | undefined>(undefined);
  const [truncateChars, setTruncateChars] = useState<number | undefined>(undefined);

  const [running, setRunning] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const data = await api.getConfigurations();
        setConfigs(data);
        if (data.length > 0) {
          const def = data.find((c) => c.is_default) || data[0];
          setSelectedConfigId(def.id);
        }
      } catch (err: any) {
        setErrorMsg(err.message);
      }
    };
    fetchConfigs();
  }, []);

  const handleLaunch = async (overrideSimulation?: boolean) => {
    setRunning(true);
    setErrorMsg(null);

    const isSim = overrideSimulation !== undefined ? overrideSimulation : injectionEnabled;
    const parsedK = kValues
      .split(",")
      .map((k) => parseInt(k.trim(), 10))
      .filter((k) => !isNaN(k) && k > 0);

    const payload = {
      name: runName.trim() || undefined,
      configuration_id: selectedConfigId,
      include_unverified: includeUnverified,
      k_values: parsedK.length > 0 ? parsedK : [1, 3, 5],
      llm_judge_enabled: llmJudgeEnabled,
      pass_threshold: passThreshold,
      failure_injection: isSim
        ? {
            enabled: true,
            remove_relevant_chunk: removeRelevant,
            inject_distractors: injectDistractors,
            num_distractors: 2,
            reduce_top_k: reduceK,
            truncate_context_chars: truncateChars,
          }
        : undefined,
    };

    try {
      const run = await api.runEvaluation(payload);
      onEvaluationCompleted(run.id);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-2xl text-ink tracking-tight flex items-center gap-2">
            <Play size={24} />
            <span>Launch Evaluation Run</span>
          </h1>
          <p className="font-mono text-xs text-ink/70">
            Execute benchmark evaluation, compute deterministic metrics &amp; classify failure modes.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-danger/10 border-2 border-danger text-danger text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* One-Click Demo Action Bar */}
      <div className="p-4 bg-paper border-2 border-ink shadow-brutal flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <div className="font-display font-bold text-sm text-ink flex items-center gap-1.5">
            <Sparkles size={16} className="text-lime-hover" />
            <span>One-Click Hackathon Benchmark Demo</span>
          </div>
          <p className="font-mono text-xs text-ink/70">
            Instantly run baseline vs. simulated failure to witness the failure diagnosis engine in action.
          </p>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <Button
            variant="primary"
            size="md"
            icon={<CheckCircle2 size={15} />}
            disabled={running}
            onClick={() => handleLaunch(false)}
          >
            Run Baseline
          </Button>
          <Button
            variant="secondary"
            size="md"
            icon={<Bug size={15} />}
            disabled={running}
            onClick={() => handleLaunch(true)}
          >
            Run Injected Failure
          </Button>
        </div>
      </div>

      {/* Main Configuration Setup Form */}
      <Card title="Run Setup &amp; Parameters">
        <div className="space-y-5 font-mono text-xs">
          {/* Run Name & Configuration */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold uppercase mb-1">Evaluation Run Name</label>
              <input
                type="text"
                value={runName}
                onChange={(e) => setRunName(e.target.value)}
                placeholder="e.g. Baseline RAG Run v1"
                className="w-full p-2 border-2 border-ink bg-paper"
              />
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">RAG Configuration</label>
              <select
                value={selectedConfigId}
                onChange={(e) => setSelectedConfigId(e.target.value)}
                className="w-full p-2 border-2 border-ink bg-paper"
              >
                {configs.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} (Chunk: {c.chunk_size}, Top-K: {c.top_k})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Metric K values and threshold */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-ink/20">
            <div>
              <label className="block font-bold uppercase mb-1">
                Recall@K Cutoff List (comma-separated)
              </label>
              <input
                type="text"
                value={kValues}
                onChange={(e) => setKValues(e.target.value)}
                placeholder="1, 3, 5, 10"
                className="w-full p-2 border-2 border-ink bg-paper"
              />
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">
                Pass Threshold Score: {passThreshold}
              </label>
              <input
                type="range"
                min={0.5}
                max={0.95}
                step={0.05}
                value={passThreshold}
                onChange={(e) => setPassThreshold(Number(e.target.value))}
                className="w-full accent-ink cursor-pointer"
              />
            </div>
          </div>

          {/* Toggles */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-ink/20">
            <label className="flex items-center gap-2 p-2 border border-ink bg-paper cursor-pointer">
              <input
                type="checkbox"
                checked={includeUnverified}
                onChange={(e) => setIncludeUnverified(e.target.checked)}
                className="accent-ink"
              />
              <span className="font-bold">Include Unverified Test Cases</span>
            </label>

            <label className="flex items-center gap-2 p-2 border border-ink bg-paper cursor-pointer">
              <input
                type="checkbox"
                checked={llmJudgeEnabled}
                onChange={(e) => setLlmJudgeEnabled(e.target.checked)}
                className="accent-ink"
              />
              <div>
                <span className="font-bold block">Enable LLM Judge</span>
                <span className="text-[10px] text-ink/60">Requires Anthropic API key</span>
              </div>
            </label>
          </div>

          {/* Controlled Failure Injection Box */}
          <div className="p-4 border-2 border-ink bg-[#FFF6E5] space-y-3 shadow-[2px_2px_0_#171717]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bug size={16} />
                <span className="font-bold uppercase">Controlled Failure Injection (Evaluation-Only)</span>
              </div>
              <label className="flex items-center gap-2 font-bold cursor-pointer">
                <input
                  type="checkbox"
                  checked={injectionEnabled}
                  onChange={(e) => setInjectionEnabled(e.target.checked)}
                  className="accent-ink"
                />
                <span>Simulate Failure</span>
              </label>
            </div>
            <p className="text-[11px] text-ink/80 leading-normal">
              Applies perturbations in-memory at retrieval time. The vector index is{" "}
              <strong>NEVER</strong> modified. The run will be badged{" "}
              <Badge variant="simulated" size="sm">SIMULATED</Badge>.
            </p>

            {injectionEnabled && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-ink/20">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={removeRelevant}
                    onChange={(e) => setRemoveRelevant(e.target.checked)}
                    className="accent-ink"
                  />
                  <span>Drop relevant evidence chunk (Forces retrieval miss)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={injectDistractors}
                    onChange={(e) => setInjectDistractors(e.target.checked)}
                    className="accent-ink"
                  />
                  <span>Inject noise distractors into top ranks</span>
                </label>
              </div>
            )}
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full"
            icon={<Play size={18} />}
            disabled={running}
            onClick={() => handleLaunch()}
          >
            {running ? "Running Evaluation & Diagnosing Cases..." : "Start Evaluation Run"}
          </Button>
        </div>
      </Card>
    </div>
  );
};
