import React, { useState } from "react";
import { AskResponse } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { PassageViewer } from "../components/ui/PassageViewer";
import { Compass, HelpCircle, Layers, Send, Sparkles } from "lucide-react";

export const PlaygroundPage: React.FC = () => {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(3);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.0);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const sampleQuestions = [
    "What encryption standard and envelope key rotation schedule does Acme Corp enforce for data at rest?",
    "What is the standard API rate limit for Tier 1 consumers and the associated burst maximum?",
    "What is the liquid nitrogen cooling temperature for Acme Corp's quantum processor fleet?",
    "How long are general debug logs kept before deletion compared to financial ledgers?",
  ];

  const handleAsk = async (qText?: string) => {
    const q = (qText || question).trim();
    if (!q) return;

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.askRag({
        question: q,
        top_k: topK,
        similarity_threshold: similarityThreshold,
      });
      setResponse(res);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-2xl text-ink tracking-tight flex items-center gap-2">
            <Compass size={24} />
            <span>RAG Playground: Question &amp; Evidence Inspector</span>
          </h1>
          <p className="font-mono text-xs text-ink/70">
            Submit a query to inspect live retrieval ranking, similarity scores, citations, and grounded generation side-by-side.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-danger/10 border-2 border-danger text-danger text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* Query Bar & Presets */}
      <Card title="Ask Document Index">
        <div className="space-y-3">
          <div className="flex gap-2">
            <textarea
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question grounded in your uploaded documents..."
              className="w-full font-mono text-sm p-3 border-2 border-ink bg-paper focus:bg-white resize-none"
            />
            <Button
              variant="primary"
              size="lg"
              className="flex-shrink-0"
              icon={<Send size={16} />}
              onClick={() => handleAsk()}
              disabled={!question.trim() || loading}
            >
              {loading ? "Searching..." : "Ask"}
            </Button>
          </div>

          {/* Quick sample prompt chips */}
          <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-xs">
            <span className="font-bold text-ink/60">Sample Queries:</span>
            {sampleQuestions.map((sq, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setQuestion(sq);
                  handleAsk(sq);
                }}
                className="px-2 py-0.5 border border-ink bg-surface-muted hover:bg-lime text-xs transition-all cursor-pointer truncate max-w-xs"
                title={sq}
              >
                {sq}
              </button>
            ))}
          </div>

          {/* Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-ink/20 font-mono text-xs">
            <div>
              <div className="flex justify-between font-bold mb-1">
                <span>Top-K Retrieval Count:</span>
                <span className="bg-paper px-1 border border-ink">{topK}</span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full accent-ink cursor-pointer"
              />
            </div>
            <div>
              <div className="flex justify-between font-bold mb-1">
                <span>Similarity Threshold (Cosine):</span>
                <span className="bg-paper px-1 border border-ink">{similarityThreshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0.0}
                max={0.9}
                step={0.05}
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="w-full accent-ink cursor-pointer"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Side-by-Side Results & Evidence */}
      {response && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Generated Answer Panel */}
          <Card
            title={
              <div className="flex items-center gap-2">
                <span>Answer Provenance</span>
                {response.is_demo ? (
                  <Badge variant="demo" size="sm">DEMO — PRE-RECORDED</Badge>
                ) : (
                  <Badge variant="pass" size="sm">LIVE GENERATION</Badge>
                )}
                {response.abstained && (
                  <Badge variant="warning" size="sm">ABSTAINED</Badge>
                )}
              </div>
            }
            footer={
              <div className="flex justify-between">
                <span>Latency: {response.latency_ms} ms</span>
                <span>Model: {response.model}</span>
              </div>
            }
          >
            <div className="space-y-4">
              <div
                className={`p-4 border-2 border-ink ${
                  response.abstained
                    ? "bg-[#FFF6E5] text-ink"
                    : "bg-surface text-ink"
                }`}
              >
                <div className="font-mono text-xs text-ink/60 font-bold mb-1 uppercase">
                  Grounded Output:
                </div>
                <div className="font-body text-base font-medium leading-relaxed whitespace-pre-wrap">
                  {response.answer}
                </div>
              </div>

              {/* Citations Pill List */}
              <div>
                <div className="font-mono text-xs font-bold uppercase mb-1.5">
                  Extracted Citations ({response.citations.length}):
                </div>
                {response.citations.length === 0 ? (
                  <span className="font-mono text-xs text-ink/60">
                    No explicit citations parsed from answer text.
                  </span>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {response.citations.map((c, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 border border-ink bg-lime font-mono text-xs font-bold"
                      >
                        [{c}]
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Exact Prompt Used (Stored for reproducibility) */}
              <div>
                <div className="font-mono text-xs font-bold uppercase mb-1">
                  Full Grounded Prompt Sent to Provider:
                </div>
                <div className="p-2.5 bg-paper border border-ink font-mono text-[11px] max-h-40 overflow-y-auto leading-normal whitespace-pre-wrap">
                  {response.prompt_used}
                </div>
              </div>
            </div>
          </Card>

          {/* Retrieved Evidence Passages */}
          <Card
            title={
              <div className="flex items-center gap-2">
                <Layers size={16} />
                <span>Retrieved Context ({response.retrieved_passages.length})</span>
              </div>
            }
          >
            <PassageViewer
              passages={response.retrieved_passages}
              highlightText={response.answer}
            />
          </Card>
        </div>
      )}
    </div>
  );
};
