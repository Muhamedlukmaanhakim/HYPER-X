import React, { useEffect, useState } from "react";
import { Configuration, MetricDefinition, ProviderStatus, SystemHealth } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import {
  CheckCircle,
  Database,
  HelpCircle,
  Key,
  Layers,
  Plus,
  RotateCw,
  Server,
  Settings,
  ShieldCheck,
  XCircle
} from "lucide-react";

export const SettingsPage: React.FC = () => {
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [configs, setConfigs] = useState<Configuration[]>([]);
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);


  // New Config State
  const [showNewConfig, setShowNewConfig] = useState(false);
  const [newCfgName, setNewCfgName] = useState("");
  const [newChunkSize, setNewChunkSize] = useState(800);
  const [newChunkOverlap, setNewChunkOverlap] = useState(150);
  const [newTopK, setNewTopK] = useState(3);
  const [newSimilarity, setNewSimilarity] = useState(0.0);

  const fetchData = async () => {
    try {
      const [st, cfgs, mets, hlth] = await Promise.all([
        api.getProviderStatus(),
        api.getConfigurations(),
        api.getMetricDefinitions(),
        api.getHealth().catch(() => null),
      ]);
      setStatus(st);
      setConfigs(cfgs);
      setMetrics(mets);
      if (hlth) setHealth(hlth);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    try {
      const res = await api.testConnection();
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        connected: false,
        error: err.message,
        message: "Failed to connect to LLM provider.",
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleCreateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCfgName.trim()) return;
    try {
      await api.createConfiguration({
        name: newCfgName.trim(),
        chunk_size: newChunkSize,
        chunk_overlap: newChunkOverlap,
        top_k: newTopK,
        similarity_threshold: newSimilarity,
      });
      setShowNewConfig(false);
      setNewCfgName("");
      fetchData();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-2xl text-ink tracking-tight flex items-center gap-2">
            <Settings size={24} />
            <span>Settings &amp; Environment Diagnostics</span>
          </h1>
          <p className="font-mono text-xs text-ink/70">
            Provider configuration, API connectivity tests, local embedding status, and metric documentation.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-danger/10 border-2 border-danger text-danger text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* Provider Connectivity & Zero-Secret Security Box */}
      <Card title={`LLM Provider Connectivity (${status?.provider === "demo" ? "Zero-Cost Demo Mode" : status?.provider === "gemini" ? "Google Gemini" : "Anthropic Claude"})`}>
        <div className="space-y-4 font-mono text-xs">
          <div className="p-4 bg-paper border-2 border-ink space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <span className="font-bold text-ink/70 uppercase block text-[10px]">Configured Provider:</span>
                <span className="font-display font-bold text-base text-ink">
                  {status?.provider === "demo" ? "Zero-Cost Demo Mode (Offline)" : status?.provider === "gemini" ? "Google Gemini" : "Anthropic Claude"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-ink/70 uppercase text-[10px]">Status:</span>
                {status?.configured ? (
                  <Badge variant="pass" size="md">
                    {status?.provider === "demo" ? "ACTIVE & READY (OFFLINE)" : "CONFIGURED IN BACKEND .ENV"}
                  </Badge>
                ) : (
                  <Badge variant="demo" size="md">NOT CONFIGURED (DEMO MODE)</Badge>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-ink/20">
              <div>
                <span className="text-ink/60 uppercase text-[10px] block">LLM Model:</span>
                <span className="font-bold">
                  {status?.provider === "demo" ? "Local Deterministic Synthesis" : status?.model || "gemini-1.5-flash"}
                </span>
              </div>
              <div>
                <span className="text-ink/60 uppercase text-[10px] block">Local Embeddings:</span>
                <span className="font-bold text-success">
                  {status?.embedding_model || "all-MiniLM-L6-v2"} (Local, $0.00 cost)
                </span>
              </div>
            </div>
          </div>

          {/* Test Connection Button */}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              size="md"
              icon={<RotateCw size={14} className={testingConnection ? "animate-spin" : ""} />}
              onClick={handleTestConnection}
              disabled={testingConnection}
            >
              {testingConnection ? "Testing Ping..." : "Test Connection"}
            </Button>
            {testResult && (
              <div
                className={`p-2 border-2 border-ink flex items-center gap-2 font-bold ${
                  testResult.connected
                    ? "bg-lime/30 text-ink"
                    : "bg-danger/20 text-danger"
                }`}
              >
                {testResult.connected ? <CheckCircle size={15} /> : <XCircle size={15} />}
                <span>
                  {testResult.connected
                    ? `Connected! Latency: ${testResult.latency_ms} ms`
                    : `Connection Failed: ${testResult.message || testResult.error}`}
                </span>
              </div>
            )}
          </div>

          {/* Security & Key Setup Instructions */}
          <div className="p-4 bg-surface-muted/40 border border-ink space-y-2 leading-relaxed">
            <div className="flex items-center gap-2 font-bold text-ink">
              <Key size={15} />
              <span>How to Configure Your API Key (Zero Secrets in UI Rule):</span>
            </div>
            {status?.provider === "gemini" ? (
              <ol className="list-decimal list-inside space-y-1 text-ink/80 text-[11px]">
                <li>
                  Obtain a Gemini API key from Google AI Studio:{" "}
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noreferrer"
                    className="underline font-bold hover:text-ink"
                  >
                    Google AI Studio
                  </a>{" "}
                  (or copy your existing key).
                </li>
                <li>
                  Open <code className="bg-paper px-1 border border-ink">backend/.env</code> in your editor.
                </li>
                <li>
                  Add: <code className="bg-paper px-1 border border-ink">GEMINI_API_KEY=AIzaSy...</code>
                </li>
                <li>
                  Optionally configure model: <code className="bg-paper px-1 border border-ink">LLM_MODEL=gemini-1.5-flash</code> (or <code className="bg-paper px-1 border border-ink">gemini-2.0-flash</code>).
                </li>
                <li>Restart the backend server and return here to run 'Test Connection'.</li>
              </ol>
            ) : (
              <ol className="list-decimal list-inside space-y-1 text-ink/80 text-[11px]">
                <li>
                  Obtain an API key from the{" "}
                  <a
                    href="https://console.anthropic.com/settings/keys"
                    target="_blank"
                    rel="noreferrer"
                    className="underline font-bold hover:text-ink"
                  >
                    Anthropic Console
                  </a>.
                </li>
                <li>
                  Open <code className="bg-paper px-1 border border-ink">backend/.env</code> in your project.
                </li>
                <li>
                  Add the line: <code className="bg-paper px-1 border border-ink">ANTHROPIC_API_KEY=sk-ant-api03-...</code>
                </li>
                <li>Restart the backend server and return here to run 'Test Connection'.</li>
              </ol>
            )}
            <p className="text-[10px] text-ink/60 italic">
              Security note: API keys are NEVER entered or stored in the browser. Embeddings run locally via sentence-transformers and send zero data outside your machine.
            </p>
          </div>
        </div>
      </Card>

      {/* Database & Storage Diagnostics */}
      <Card title="Database & Storage Diagnostics">
        <div className="space-y-4 font-mono text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* SQLite Card */}
            <div className="p-4 bg-paper border-2 border-ink space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink uppercase text-[11px] flex items-center gap-1.5">
                  <Database size={15} />
                  <span>SQLite Database</span>
                </span>
                {health?.database.healthy ? (
                  <Badge variant="pass" size="sm">CONNECTED</Badge>
                ) : (
                  <Badge variant="fail" size="sm">UNAVAILABLE</Badge>
                )}
              </div>
              <div className="text-[11px] text-ink/80 space-y-1">
                <div>
                  <span className="text-ink/60">Dialect:</span> <span className="font-bold">{health?.database.dialect || "sqlite"}</span>
                </div>
                <div>
                  <span className="text-ink/60">Tables:</span>{" "}
                  <span className="font-bold">
                    {health?.database.tables_initialized ? `${health?.database.table_count} Initialized` : "Pending Schema"}
                  </span>
                </div>
                {health?.database.error && (
                  <div className="text-danger text-[10px] pt-1 border-t border-danger/30 font-bold">
                    {health.database.error}
                  </div>
                )}
              </div>
            </div>

            {/* ChromaDB Card */}
            <div className="p-4 bg-paper border-2 border-ink space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink uppercase text-[11px] flex items-center gap-1.5">
                  <Layers size={15} />
                  <span>ChromaDB Vector Store</span>
                </span>
                {health?.vectorstore.healthy ? (
                  <Badge variant="pass" size="sm">CONNECTED</Badge>
                ) : (
                  <Badge variant="fail" size="sm">UNAVAILABLE</Badge>
                )}
              </div>
              <div className="text-[11px] text-ink/80 space-y-1">
                <div>
                  <span className="text-ink/60">Collection:</span>{" "}
                  <span className="font-bold">{health?.vectorstore.collection || "default_rag"}</span>
                </div>
                <div>
                  <span className="text-ink/60">Indexed Chunks:</span>{" "}
                  <span className="font-bold">{health?.vectorstore.chunk_count ?? 0}</span>
                </div>
                {health?.vectorstore.error && (
                  <div className="text-danger text-[10px] pt-1 border-t border-danger/30 font-bold">
                    {health.vectorstore.error}
                  </div>
                )}
              </div>
            </div>

            {/* Embedding Model Card */}
            <div className="p-4 bg-paper border-2 border-ink space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-ink uppercase text-[11px] flex items-center gap-1.5">
                  <Server size={15} />
                  <span>Local Embeddings</span>
                </span>
                {health?.embeddings.healthy ? (
                  <Badge variant="pass" size="sm">READY</Badge>
                ) : (
                  <Badge variant="fail" size="sm">UNAVAILABLE</Badge>
                )}

              </div>
              <div className="text-[11px] text-ink/80 space-y-1">
                <div>
                  <span className="text-ink/60">Model:</span>{" "}
                  <span className="font-bold">{health?.embeddings.model || "all-MiniLM-L6-v2"}</span>
                </div>
                <div>
                  <span className="text-ink/60">Dimensions:</span>{" "}
                  <span className="font-bold">{health?.embeddings.dimension || 384} floats</span>
                </div>
                {health?.embeddings.error && (
                  <div className="text-danger text-[10px] pt-1 border-t border-danger/30 font-bold">
                    {health.embeddings.error}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* RAG Configurations List */}
      <Card
        title={`RAG Configurations (${configs.length})`}

        action={
          <Button
            variant="secondary"
            size="sm"
            icon={<Plus size={14} />}
            onClick={() => setShowNewConfig(!showNewConfig)}
          >
            {showNewConfig ? "Cancel" : "Add Config"}
          </Button>
        }
      >
        <div className="space-y-4 font-mono text-xs">
          {showNewConfig && (
            <form onSubmit={handleCreateConfig} className="p-4 bg-paper border-2 border-ink space-y-3">
              <span className="font-bold uppercase block text-sm font-display">New RAG Configuration</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold mb-1">Configuration Name</label>
                  <input
                    type="text"
                    value={newCfgName}
                    onChange={(e) => setNewCfgName(e.target.value)}
                    placeholder="e.g. Fine-grained 400-char chunks"
                    className="w-full p-1.5 border border-ink bg-white"
                    required
                  />
                </div>
                <div>
                  <label className="block font-bold mb-1">Top-K Retrieval</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={newTopK}
                    onChange={(e) => setNewTopK(Number(e.target.value))}
                    className="w-full p-1.5 border border-ink bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold mb-1">Chunk Size (chars)</label>
                  <input
                    type="number"
                    min={100}
                    max={2000}
                    step={50}
                    value={newChunkSize}
                    onChange={(e) => setNewChunkSize(Number(e.target.value))}
                    className="w-full p-1.5 border border-ink bg-white"
                  />
                </div>
                <div>
                  <label className="block font-bold mb-1">Chunk Overlap (chars)</label>
                  <input
                    type="number"
                    min={0}
                    max={400}
                    step={25}
                    value={newChunkOverlap}
                    onChange={(e) => setNewChunkOverlap(Number(e.target.value))}
                    className="w-full p-1.5 border border-ink bg-white"
                  />
                </div>
              </div>
              <Button type="submit" variant="primary" size="sm">
                Save Configuration
              </Button>
            </form>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {configs.map((c) => (
              <div key={c.id} className="p-3 border-2 border-ink bg-surface shadow-[2px_2px_0_#171717]">
                <div className="flex items-center justify-between pb-1 mb-2 border-b border-ink/20 font-bold">
                  <span>{c.name}</span>
                  {c.is_default && <Badge variant="pass" size="sm">DEFAULT</Badge>}
                </div>
                <div className="space-y-1 text-ink/80 text-[11px]">
                  <div>Chunk Size: <strong>{c.chunk_size} chars</strong> (Overlap: {c.chunk_overlap})</div>
                  <div>Top-K: <strong>{c.top_k} passages</strong></div>
                  <div>Embedding: <strong>{c.embedding_model}</strong></div>
                  <div>LLM Model: <strong>{c.llm_model}</strong></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Metric Definitions Reference Table */}
      <Card title="Stored Metric Definitions &amp; Measurement Formulas">
        <div className="overflow-x-auto font-mono text-xs">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b-2 border-ink bg-surface-muted/50">
                <th className="p-2.5">METRIC</th>
                <th className="p-2.5">TYPE</th>
                <th className="p-2.5">MATHEMATICAL FORMULA</th>
                <th className="p-2.5">KNOWN LIMITATIONS</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.slug} className="border-b border-ink/20 hover:bg-surface-muted/30">
                  <td className="p-2.5 font-bold font-display text-sm">{m.name}</td>
                  <td className="p-2.5">
                    <Badge variant={m.metric_type} size="sm">
                      {m.metric_type.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="p-2.5 text-ink/80 bg-paper/50 font-mono text-[11px]">{m.formula}</td>
                  <td className="p-2.5 text-ink/70 text-[11px] max-w-xs">{m.limitations}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
