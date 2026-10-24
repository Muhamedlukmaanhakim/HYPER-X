import React, { useState } from "react";
import { CaseResult } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge, CategoryBadge } from "../components/ui/Badge";
import { PassageViewer } from "../components/ui/PassageViewer";
import {
  ArrowLeft,
  CheckCircle,
  Layers,
  Save,
  Sparkles
} from "lucide-react";

interface FailureDetailPageProps {
  caseResult: CaseResult;
  onBack: () => void;
  onOverrideUpdated: () => void;
}

export const FailureDetailPage: React.FC<FailureDetailPageProps> = ({
  caseResult,
  onBack,
  onOverrideUpdated,
}) => {
  const [overrideCat, setOverrideCat] = useState(caseResult.category);
  const [overrideNotes, setOverrideNotes] = useState("");
  const [savingOverride, setSavingOverride] = useState(false);
  const [overrideSuccess, setOverrideSuccess] = useState(false);
  const [modelExplanation, setModelExplanation] = useState(caseResult.model_diagnosis_explanation || "");
  const [generatingExplanation, setGeneratingExplanation] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const facts = caseResult.rule_facts || {};

  const handleSaveOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingOverride(true);
    setErrorMsg(null);
    try {
      await api.createReviewerOverride(caseResult.run_id, caseResult.id, {
        overridden_category: overrideCat,
        reviewer_notes: overrideNotes.trim(),
      });
      setOverrideSuccess(true);
      onOverrideUpdated();
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setSavingOverride(false);
    }
  };

  const handleGenerateExplanation = async () => {
    setGeneratingExplanation(true);
    setErrorMsg(null);
    try {
      const res = await api.generateCaseExplanation(caseResult.run_id, caseResult.id);
      setModelExplanation(res.model_diagnosis_explanation);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setGeneratingExplanation(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <button
            onClick={onBack}
            className="font-mono text-xs text-ink/70 hover:text-ink hover:underline flex items-center gap-1 cursor-pointer"
          >
            <ArrowLeft size={14} /> Back to Evaluation Results
          </button>
          <div className="flex items-center gap-2">
            <h1 className="font-display font-black text-2xl text-ink tracking-tight">
              Failure Diagnosis &amp; Root Cause Inspector
            </h1>
            <CategoryBadge category={caseResult.category} />
          </div>
          <p className="font-mono text-xs text-ink/60">
            Case ID: {caseResult.test_case_id} &bull; Type: {caseResult.question_type.toUpperCase()}
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="font-bold">DIAGNOSIS CONFIDENCE:</span>
          <Badge
            variant={caseResult.confidence === "high" ? "pass" : "review"}
            size="md"
          >
            {caseResult.confidence.toUpperCase()} CONFIDENCE
          </Badge>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-danger/10 border-2 border-danger text-danger text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {overrideSuccess && (
        <div className="p-3 bg-lime/20 border-2 border-ink text-ink text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>Reviewer override and note recorded successfully!</span>
          <button onClick={() => setOverrideSuccess(false)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* The 4 Core Panels Mandated by Section 4.E */}
      <div className="space-y-6">
        {/* PANEL 1: Measured Observations */}
        <Card title="1. Measured Observations (Empirical Facts)">
          <div className="space-y-4 font-mono text-xs">
            {/* Question & Answers Side by Side */}
            <div className="p-3 bg-paper border border-ink space-y-2">
              <div>
                <span className="font-bold uppercase text-ink/60 block text-[10px]">Benchmark Question:</span>
                <span className="text-sm font-display font-bold text-ink">{caseResult.question}</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-ink/20">
                <div className="p-2.5 bg-surface border border-ink/20">
                  <span className="font-bold uppercase text-ink/60 block text-[10px]">Reference Answer:</span>
                  <span className="text-ink/90 font-medium">{caseResult.reference_answer}</span>
                </div>
                <div className="p-2.5 bg-surface border border-ink/20">
                  <span className="font-bold uppercase text-ink/60 block text-[10px]">
                    Generated Answer {caseResult.abstained && "(Abstained)"}:
                  </span>
                  <span className={caseResult.abstained ? "text-warning font-bold" : "text-ink"}>
                    {caseResult.generated_answer}
                  </span>
                </div>
              </div>
            </div>

            {/* Metric Measurements Table */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
              <div className="p-2 bg-paper border border-ink">
                <div className="text-[10px] text-ink/60 uppercase">Recall Score</div>
                <div className="text-lg font-bold">
                  {facts.recall !== undefined ? Number(facts.recall).toFixed(3) : "N/A"}
                </div>
              </div>
              <div className="p-2 bg-paper border border-ink">
                <div className="text-[10px] text-ink/60 uppercase">Hit Rate</div>
                <div className="text-lg font-bold">
                  {facts.hit_rate !== undefined ? Number(facts.hit_rate).toFixed(1) : "N/A"}
                </div>
              </div>
              <div className="p-2 bg-paper border border-ink">
                <div className="text-[10px] text-ink/60 uppercase">MRR</div>
                <div className="text-lg font-bold">
                  {facts.mrr !== undefined ? Number(facts.mrr).toFixed(3) : "N/A"}
                </div>
              </div>
              <div className="p-2 bg-paper border border-ink">
                <div className="text-[10px] text-ink/60 uppercase">Token F1</div>
                <div className="text-lg font-bold">
                  {facts.normalized_match !== undefined ? Number(facts.normalized_match).toFixed(3) : "N/A"}
                </div>
              </div>
            </div>

            {/* Retrieved Context Passages */}
            <div className="pt-2">
              <div className="font-bold uppercase text-[11px] mb-2 flex items-center gap-1.5 text-ink">
                <Layers size={14} /> Retrieved Evidence Context ({caseResult.retrieved_chunks.length} passages):
              </div>
              <PassageViewer
                passages={caseResult.retrieved_chunks}
                highlightText={caseResult.generated_answer}
              />
            </div>
          </div>
        </Card>

        {/* PANEL 2: Rule-Based Classification */}
        <Card title="2. Rule-Based Classification (Deterministic Decision Tree)">
          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 bg-surface border-2 border-ink flex items-center justify-between">
              <div>
                <span className="font-bold text-ink/60 uppercase block text-[10px]">
                  Fired Decision Rule:
                </span>
                <span className="text-sm font-display font-bold text-ink">
                  {caseResult.rule_fired}
                </span>
              </div>
              <CategoryBadge category={caseResult.category} />
            </div>

            {/* Suggested Next Step */}
            <div className="p-3 bg-lime/20 border-2 border-ink space-y-1">
              <span className="font-bold text-ink uppercase text-[11px] flex items-center gap-1.5">
                <CheckCircle size={14} /> Recommended Actionable Debugging Step:
              </span>
              <p className="text-ink leading-relaxed">
                {caseResult.suggested_debugging_step}
              </p>
            </div>
          </div>
        </Card>

        {/* PANEL 3: Model-Generated Explanation */}
        <Card title="3. Model-Generated Diagnosis (not established fact)">
          <div className="space-y-3 font-mono text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-ink/70">
                AI-synthesized failure narrative explaining context gaps, query alignment, and reasoning patterns.
              </p>
              <Button
                variant="secondary"
                size="sm"
                icon={<Sparkles size={14} className={generatingExplanation ? "animate-spin" : ""} />}
                onClick={handleGenerateExplanation}
                disabled={generatingExplanation}
              >
                {generatingExplanation
                  ? "Synthesizing..."
                  : modelExplanation
                  ? "Re-generate Diagnosis"
                  : "Generate Explanation"}
              </Button>
            </div>

            {modelExplanation ? (
              <div className="p-3.5 bg-paper border-2 border-ink shadow-[2px_2px_0_#171717] space-y-1.5">
                <div className="font-bold uppercase text-[10px] text-ink/60 flex items-center gap-1.5">
                  <Badge variant="warning" size="sm">INDICATIVE ONLY</Badge>
                  <span>Model-Generated Diagnosis (not established fact)</span>
                </div>
                <p className="text-sm font-medium font-body leading-relaxed text-ink whitespace-pre-wrap">
                  {modelExplanation}
                </p>
              </div>
            ) : (
              <div className="p-4 border-2 border-dashed border-ink/40 bg-surface-muted/20 text-center text-ink/60">
                No model-generated explanation generated yet. Click 'Generate Explanation' to synthesize narrative root cause.
              </div>
            )}
          </div>
        </Card>

        {/* PANEL 4: Human-Verified Conclusion (Reviewer Overrides) */}
        <Card title="4. Human-Verified Conclusion &amp; Category Override">
          <div className="space-y-4 font-mono text-xs">
            <p className="text-ink/80 leading-relaxed">
              Human reviewers can override the automated rule-based classification and attach notes.
              The original decision tree output is preserved; overrides are stored separately for full auditability.
            </p>

            {/* Existing Overrides List */}
            {caseResult.overrides && caseResult.overrides.length > 0 && (
              <div className="p-3 bg-surface-muted border border-ink space-y-2">
                <span className="font-bold uppercase text-[10px] text-ink/70">
                  Recorded Reviewer Overrides:
                </span>
                {caseResult.overrides.map((ovr) => (
                  <div key={ovr.id} className="p-2 bg-surface border border-ink/30 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="line-through text-ink/50">{ovr.original_category}</span>
                        <span>&rarr;</span>
                        <CategoryBadge category={ovr.overridden_category} />
                      </div>
                      <span className="text-[10px] text-ink/50">
                        {new Date(ovr.created_at).toLocaleString()}
                      </span>
                    </div>
                    {ovr.reviewer_notes && (
                      <p className="italic text-ink/80 font-body">"{ovr.reviewer_notes}"</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Override Form */}
            <form onSubmit={handleSaveOverride} className="space-y-3 pt-2 border-t border-ink/20">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold uppercase mb-1">Override Category</label>
                  <select
                    value={overrideCat}
                    onChange={(e) => setOverrideCat(e.target.value as any)}
                    className="w-full p-2 border-2 border-ink bg-paper font-mono text-xs"
                  >
                    <option value="pass">PASS</option>
                    <option value="retrieval_miss">RETRIEVAL MISS</option>
                    <option value="incomplete_or_irrelevant_context">INCOMPLETE CONTEXT</option>
                    <option value="unsupported_answer">UNSUPPORTED ANSWER</option>
                    <option value="incorrect_despite_relevant_context">INCORRECT DESPITE CONTEXT</option>
                    <option value="citation_error">CITATION ERROR</option>
                    <option value="unanswerable_answered">UNANSWERABLE ANSWERED</option>
                    <option value="needs_review">NEEDS REVIEW</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold uppercase mb-1">Reviewer Note / Justification</label>
                  <input
                    type="text"
                    value={overrideNotes}
                    onChange={(e) => setOverrideNotes(e.target.value)}
                    placeholder="Rationale for overriding rule..."
                    className="w-full p-2 border-2 border-ink bg-paper font-mono text-xs"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="md"
                icon={<Save size={14} />}
                disabled={savingOverride}
              >
                {savingOverride ? "Saving Override..." : "Save Reviewer Override"}
              </Button>
            </form>
          </div>
        </Card>
      </div>
    </div>
  );
};
