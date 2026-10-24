import React, { useEffect, useState } from "react";
import { Document, QuestionType, TestCase } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import {
  Check,
  CheckSquare,
  Download,
  Filter,
  Plus,
  RotateCw,
  Sparkles,
  Trash2,
  Upload,
  X
} from "lucide-react";

export const TestCasesPage: React.FC = () => {
  const [cases, setCases] = useState<TestCase[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Create Modal state
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newQuestion, setNewQuestion] = useState("");
  const [newType, setNewType] = useState<QuestionType>("direct_factual");
  const [newRefAnswer, setNewRefAnswer] = useState("");
  const [newExpectedSpan, setNewExpectedSpan] = useState("");
  const [newExpectedPage, setNewExpectedPage] = useState<number>(1);
  const [newShouldAbstain, setNewShouldAbstain] = useState(false);
  const [newDocId, setNewDocId] = useState("");

  // CSV Import Modal state
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [isUploadingCsv, setIsUploadingCsv] = useState(false);
  const [importStats, setImportStats] = useState<{
    imported_count: number;
    error_count: number;
    errors: string[];
    message: string;
  } | null>(null);

  const fetchData = async () => {
    try {
      const [tcData, docData] = await Promise.all([
        api.getTestCases(),
        api.getDocuments(),
      ]);
      setCases(tcData);
      setDocs(docData);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleStatusChange = async (id: string, status: "approved" | "rejected" | "unverified") => {
    try {
      await api.updateTestCase(id, { status });
      setCases((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status } : c))
      );
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this test case?")) return;
    try {
      await api.deleteTestCase(id);
      setCases((prev) => prev.filter((c) => c.id !== id));
      setSuccessMsg("Test case deleted.");
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestion.trim() || !newRefAnswer.trim()) return;

    try {
      const ev = [];
      if (newExpectedSpan.trim()) {
        ev.push({
          page: newExpectedPage,
          text_span: newExpectedSpan.trim(),
        });
      }

      const res = await api.createTestCase({
        question: newQuestion.trim(),
        question_type: newType,
        reference_answer: newRefAnswer.trim(),
        expected_evidence: ev,
        should_abstain: newShouldAbstain || newType === "unanswerable",
        status: "approved",
        document_id: newDocId || undefined,
      });

      setCases((prev) => [res, ...prev]);
      setCreateModalOpen(false);
      setSuccessMsg("Test case created and approved.");
      setNewQuestion("");
      setNewRefAnswer("");
      setNewExpectedSpan("");
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleSeedSample = async () => {
    try {
      await api.seedSampleTestCases();
      setSuccessMsg("Seeded sample test dataset across all 5 question types.");
      fetchData();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;
    setIsUploadingCsv(true);
    try {
      const res = await api.importTestCasesCsv(csvFile);
      setImportStats(res);
      setSuccessMsg(`Successfully imported ${res.imported_count} test cases.`);
      fetchData();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to import CSV");
    } finally {
      setIsUploadingCsv(false);
    }
  };

  const filteredCases = cases.filter((c) => {
    if (typeFilter !== "all" && c.question_type !== typeFilter) return false;
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="p-5 bg-surface border-brutal border-ink shadow-brutal flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-2xl text-ink tracking-tight flex items-center gap-2">
            <CheckSquare size={24} />
            <span>Test Case Repository &amp; Ground Truth Editor</span>
          </h1>
          <p className="font-mono text-xs text-ink/70">
            Define reference answers and expected evidence annotations. Only approved cases are evaluated.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            size="md"
            icon={<Plus size={15} />}
            onClick={() => setCreateModalOpen(true)}
          >
            Create Case
          </Button>
          <Button
            variant="secondary"
            size="md"
            icon={<Sparkles size={15} />}
            onClick={handleSeedSample}
          >
            Seed Sample Cases
          </Button>
          <Button
            variant="secondary"
            size="md"
            icon={<Upload size={15} />}
            onClick={() => {
              setImportModalOpen(true);
              setImportStats(null);
              setCsvFile(null);
            }}
          >
            Import CSV
          </Button>
          <a
            href={api.getTestCasesCsvUrl()}
            className="inline-flex items-center gap-1.5 px-4 py-2 border-[2.5px] border-ink bg-surface text-xs font-mono font-bold hover:bg-surface-muted shadow-[3px_3px_0_#171717] transition-all"
            download
          >
            <Download size={14} />
            Export CSV
          </a>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-danger/10 border-2 border-danger text-danger text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {successMsg && (
        <div className="p-3 bg-lime/20 border-2 border-ink text-ink text-xs font-mono font-bold flex justify-between items-center shadow-[2px_2px_0_#171717]">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="underline cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="p-3 bg-surface border-2 border-ink shadow-[3px_3px_0_#171717] flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-ink/60" />
            <span className="font-bold">QUESTION TYPE:</span>
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

          <div className="flex items-center gap-2">
            <span className="font-bold">STATUS:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="p-1 border border-ink bg-paper font-mono text-xs"
            >
              <option value="all">All Statuses</option>
              <option value="approved">Approved</option>
              <option value="unverified">Unverified</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        <div className="text-ink/60">
          Showing <strong>{filteredCases.length}</strong> of {cases.length} cases
        </div>
      </div>

      {/* Test Cases Table */}
      <Card title={`Benchmark Test Cases (${filteredCases.length})`}>
        {filteredCases.length === 0 ? (
          <div className="py-12 text-center font-mono text-xs text-ink/60">
            No test cases found matching filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b-2 border-ink bg-surface-muted/50">
                  <th className="p-2.5">ID / TYPE</th>
                  <th className="p-2.5">QUESTION &amp; REFERENCE ANSWER</th>
                  <th className="p-2.5">EXPECTED EVIDENCE</th>
                  <th className="p-2.5">STATUS</th>
                  <th className="p-2.5 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.map((tc) => (
                  <tr
                    key={tc.id}
                    className="border-b border-ink/20 hover:bg-surface-muted/30 transition-all"
                  >
                    <td className="p-2.5 align-top w-40">
                      <div className="font-bold">{tc.id}</div>
                      <Badge variant="neutral" size="sm" className="mt-1">
                        {tc.question_type.replace(/_/g, " ")}
                      </Badge>
                      {tc.should_abstain && (
                        <div className="mt-1">
                          <Badge variant="warning" size="sm">MUST ABSTAIN</Badge>
                        </div>
                      )}
                    </td>

                    <td className="p-2.5 align-top max-w-md">
                      <div className="font-bold text-ink mb-1 text-sm font-display">
                        {tc.question}
                      </div>
                      <div className="p-2 bg-paper border border-ink/20 text-xs text-ink/80 leading-relaxed">
                        <span className="font-bold text-ink/60 block text-[10px] uppercase">
                          Reference Answer:
                        </span>
                        {tc.reference_answer}
                      </div>
                    </td>

                    <td className="p-2.5 align-top max-w-xs">
                      {tc.expected_evidence && tc.expected_evidence.length > 0 ? (
                        <div className="space-y-1">
                          {tc.expected_evidence.map((ev, i) => (
                            <div
                              key={i}
                              className="p-1 bg-surface-muted border border-ink/20 text-[11px]"
                            >
                              {ev.page && <span className="font-bold">Page {ev.page}: </span>}
                              {ev.chunk_id && <span className="font-bold">[{ev.chunk_id}] </span>}
                              <span className="text-ink/80 italic truncate block">
                                "{ev.text_span || ""}"
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-ink/50 italic text-[11px]">
                          {tc.should_abstain ? "None (Unanswerable)" : "No evidence annotated"}
                        </span>
                      )}
                    </td>

                    <td className="p-2.5 align-top w-28">
                      <Badge
                        variant={
                          tc.status === "approved"
                            ? "pass"
                            : tc.status === "rejected"
                            ? "fail"
                            : "review"
                        }
                      >
                        {tc.status.toUpperCase()}
                      </Badge>
                    </td>

                    <td className="p-2.5 align-top text-right space-x-1 w-36">
                      {tc.status !== "approved" && (
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={<Check size={12} />}
                          onClick={() => handleStatusChange(tc.id, "approved")}
                          title="Approve test case for evaluations"
                        >
                          Approve
                        </Button>
                      )}
                      {tc.status !== "rejected" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={<X size={12} />}
                          onClick={() => handleStatusChange(tc.id, "rejected")}
                          title="Reject"
                        >
                          Reject
                        </Button>
                      )}
                      <Button
                        variant="danger"
                        size="sm"
                        icon={<Trash2 size={12} />}
                        onClick={() => handleDelete(tc.id)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Create Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create Benchmark Test Case"
        maxWidth="lg"
      >
        <form onSubmit={handleCreate} className="space-y-4 font-mono text-xs">
          <div>
            <label className="block font-bold uppercase mb-1">Question</label>
            <textarea
              rows={2}
              value={newQuestion}
              onChange={(e) => setNewQuestion(e.target.value)}
              className="w-full p-2 border-2 border-ink bg-paper"
              placeholder="e.g. What is the standard rate limit for Tier 1?"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold uppercase mb-1">Question Type</label>
              <select
                value={newType}
                onChange={(e) => {
                  const val = e.target.value as QuestionType;
                  setNewType(val);
                  if (val === "unanswerable") {
                    setNewShouldAbstain(true);
                    setNewRefAnswer("INSUFFICIENT_EVIDENCE");
                  }
                }}
                className="w-full p-2 border-2 border-ink bg-paper"
              >
                <option value="direct_factual">Direct Factual</option>
                <option value="paraphrased">Paraphrased</option>
                <option value="multi_passage">Multi-Passage</option>
                <option value="numerical">Numerical</option>
                <option value="unanswerable">Unanswerable</option>
              </select>
            </div>

            <div>
              <label className="block font-bold uppercase mb-1">Associate Document</label>
              <select
                value={newDocId}
                onChange={(e) => setNewDocId(e.target.value)}
                className="w-full p-2 border-2 border-ink bg-paper"
              >
                <option value="">Any / General</option>
                {docs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.original_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block font-bold uppercase mb-1">Reference Answer</label>
            <textarea
              rows={2}
              value={newRefAnswer}
              onChange={(e) => setNewRefAnswer(e.target.value)}
              className="w-full p-2 border-2 border-ink bg-paper"
              placeholder="Ground truth factual reference answer..."
              required
            />
          </div>

          <div className="p-3 border border-ink/40 bg-surface-muted/30 space-y-2">
            <span className="font-bold block uppercase text-[11px]">
              Expected Evidence Annotation (For Recall@K):
            </span>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-[10px] uppercase font-bold">Page Number</label>
                <input
                  type="number"
                  min={1}
                  value={newExpectedPage}
                  onChange={(e) => setNewExpectedPage(Number(e.target.value))}
                  className="w-full p-1.5 border border-ink bg-paper"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-[10px] uppercase font-bold">Quote / Text Span</label>
                <input
                  type="text"
                  value={newExpectedSpan}
                  onChange={(e) => setNewExpectedSpan(e.target.value)}
                  placeholder="Exact quote from document..."
                  className="w-full p-1.5 border border-ink bg-paper"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="abstainCheck"
              checked={newShouldAbstain}
              onChange={(e) => setNewShouldAbstain(e.target.checked)}
              className="accent-ink"
            />
            <label htmlFor="abstainCheck" className="font-bold cursor-pointer">
              Should Abstain (Model must output INSUFFICIENT_EVIDENCE)
            </label>
          </div>

          <Button type="submit" variant="primary" size="md" className="w-full">
            Save &amp; Approve Test Case
          </Button>
        </form>
      </Modal>

      {/* CSV Import Modal */}
      <Modal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        title="Import Test Cases from CSV"
      >
        <form onSubmit={handleImportCsv} className="space-y-4 font-mono text-xs">
          <div className="p-3 bg-surface-muted/40 border border-ink/40 text-[11px] space-y-1">
            <p className="font-bold uppercase text-ink">Supported CSV Headers:</p>
            <p className="text-ink/80 font-mono text-[10px]">
              <code>question, reference_answer, question_type, expected_evidence, should_abstain, document_id</code>
            </p>
            <p className="text-ink/60 text-[10px]">
              Expected evidence can be JSON string e.g. <code>[{'{"page": 1, "text_span": "quote"}'}]</code> or plain text span.
            </p>
          </div>

          <div>
            <label className="block font-bold uppercase mb-1">Select CSV File</label>
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                setCsvFile(file);
                setImportStats(null);
              }}
              className="w-full p-2 border-2 border-ink bg-paper cursor-pointer"
              required
            />
          </div>

          {importStats && (
            <div className="space-y-2">
              <div className="p-2.5 bg-lime/20 border-2 border-ink text-ink font-bold">
                ✓ Imported {importStats.imported_count} cases successfully.
                {importStats.error_count > 0 && ` (${importStats.error_count} rows skipped with issues)`}
              </div>
              {importStats.errors && importStats.errors.length > 0 && (
                <div className="p-2 bg-danger/10 border border-danger text-danger text-[11px] max-h-32 overflow-y-auto">
                  <p className="font-bold mb-1">Row Errors:</p>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {importStats.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setImportModalOpen(false)}
            >
              Close
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={isUploadingCsv}
              disabled={!csvFile}
            >
              Upload &amp; Import
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
