import React, { useEffect, useState } from "react";
import { Document } from "../lib/types";
import { api } from "../lib/api";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import {
  AlertTriangle,
  Database,
  FileText,
  Layers,
  RotateCw,
  Trash2,
  Upload
} from "lucide-react";

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Upload inputs
  const [file, setFile] = useState<File | null>(null);
  const [chunkSize, setChunkSize] = useState(800);
  const [chunkOverlap, setChunkOverlap] = useState(150);

  const fetchDocs = async () => {
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("chunk_size", chunkSize.toString());
    formData.append("chunk_overlap", chunkOverlap.toString());

    try {
      const res = await api.uploadDocument(formData);
      setSuccessMsg(`Document '${res.original_name}' uploaded and indexed successfully (${res.chunk_count} chunks).`);
      setFile(null);
      fetchDocs();
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleSeedSample = async () => {
    setErrorMsg(null);
    try {
      const res = await api.seedSampleDocument();
      setSuccessMsg(`Sample document '${res.original_name}' loaded.`);
      fetchDocs();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDelete = async (docId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete '${name}' and all its indexed chunks?`)) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      setSuccessMsg(`Deleted '${name}'.`);
      fetchDocs();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleViewChunks = async (docId: string) => {
    try {
      const detailed = await api.getDocument(docId);
      setSelectedDoc(detailed);
      setDetailModalOpen(true);
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 bg-surface border-brutal border-ink shadow-brutal">
        <div>
          <h1 className="font-display font-black text-2xl text-ink tracking-tight flex items-center gap-2">
            <FileText size={24} />
            <span>Document Repository &amp; Chunk Viewer</span>
          </h1>
          <p className="font-mono text-xs text-ink/70">
            Upload PDF, TXT, or DOCX files. View chunking boundaries, char offsets, and page mappings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="md"
            icon={<Database size={15} />}
            onClick={handleSeedSample}
          >
            Load Sample Doc
          </Button>
          <Button
            variant="ghost"
            size="md"
            icon={<RotateCw size={15} />}
            onClick={fetchDocs}
          >
            Refresh
          </Button>
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

      {/* Upload Box + Document List Bento */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Form Card */}
        <Card title="Upload New Document">
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block font-mono text-xs font-bold uppercase mb-1">
                Select File (PDF, DOCX, TXT)
              </label>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md,.csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full font-mono text-xs p-2 border-2 border-ink bg-paper file:mr-2 file:py-1 file:px-2 file:border-2 file:border-ink file:bg-lime file:font-bold file:text-xs cursor-pointer"
                required
              />
              <p className="font-mono text-[11px] text-ink/60 mt-1">
                Max size: 20 MB. Note: Scanned image PDFs are flagged (OCR not supported).
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-mono text-xs font-bold uppercase mb-1">
                  Chunk Size (chars)
                </label>
                <input
                  type="number"
                  min={100}
                  max={4000}
                  step={50}
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number(e.target.value))}
                  className="w-full font-mono text-xs p-2 border-2 border-ink bg-paper"
                />
              </div>
              <div>
                <label className="block font-mono text-xs font-bold uppercase mb-1">
                  Overlap (chars)
                </label>
                <input
                  type="number"
                  min={0}
                  max={500}
                  step={25}
                  value={chunkOverlap}
                  onChange={(e) => setChunkOverlap(Number(e.target.value))}
                  className="w-full font-mono text-xs p-2 border-2 border-ink bg-paper"
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full"
              icon={<Upload size={16} />}
              disabled={!file || uploading}
            >
              {uploading ? "Extracting & Indexing..." : "Process & Embed"}
            </Button>
          </form>
        </Card>

        {/* Documents Table (Span 2) */}
        <div className="lg:col-span-2">
          <Card title={`Uploaded Documents (${documents.length})`}>
            {documents.length === 0 ? (
              <div className="py-12 text-center font-mono text-xs text-ink/60">
                No documents uploaded yet. Upload a document or click 'Load Sample Doc'.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="border-b-2 border-ink bg-surface-muted/50">
                      <th className="p-2.5">FILE NAME</th>
                      <th className="p-2.5">TYPE</th>
                      <th className="p-2.5">PAGES</th>
                      <th className="p-2.5">CHUNKS</th>
                      <th className="p-2.5">CHARS</th>
                      <th className="p-2.5">STATUS</th>
                      <th className="p-2.5 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((d) => (
                      <tr
                        key={d.id}
                        className="border-b border-ink/20 hover:bg-surface-muted/30 transition-all"
                      >
                        <td className="p-2.5 font-bold flex items-center gap-1.5">
                          <FileText size={14} className="text-ink/60" />
                          <span>{d.original_name}</span>
                          {d.is_sample && <Badge variant="lime" size="sm">SAMPLE</Badge>}
                        </td>
                        <td className="p-2.5 uppercase">{d.file_type}</td>
                        <td className="p-2.5">{d.page_count}</td>
                        <td className="p-2.5 font-bold">{d.chunk_count}</td>
                        <td className="p-2.5">{d.char_count.toLocaleString()}</td>
                        <td className="p-2.5">
                          {d.status === "indexed" ? (
                            <Badge variant="pass" size="sm">INDEXED</Badge>
                          ) : (
                            <Badge variant="fail" size="sm">ERROR</Badge>
                          )}
                        </td>
                        <td className="p-2.5 text-right space-x-1">
                          <Button
                            variant="secondary"
                            size="sm"
                            icon={<Layers size={13} />}
                            onClick={() => handleViewChunks(d.id)}
                          >
                            Chunks
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            icon={<Trash2 size={13} />}
                            onClick={() => handleDelete(d.id, d.original_name)}
                          >
                            Delete
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
      </div>

      {/* Chunk Viewer Modal */}
      <Modal
        isOpen={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        title={`Chunk Viewer: ${selectedDoc?.original_name || ""}`}
        maxWidth="2xl"
      >
        <div className="space-y-4">
          <div className="p-3 bg-paper border border-ink font-mono text-xs grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div><strong>Pages:</strong> {selectedDoc?.page_count}</div>
            <div><strong>Total Chunks:</strong> {selectedDoc?.chunk_count}</div>
            <div><strong>Characters:</strong> {selectedDoc?.char_count}</div>
            <div><strong>Format:</strong> {selectedDoc?.file_type?.toUpperCase()}</div>
          </div>

          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {selectedDoc?.chunks?.map((c) => (
              <div key={c.id} className="p-3 border-2 border-ink bg-surface shadow-[2px_2px_0_#171717]">
                <div className="flex items-center justify-between border-b border-ink/20 pb-1.5 mb-2 font-mono text-xs">
                  <span className="font-bold text-ink">Chunk ID: {c.id}</span>
                  <div className="flex items-center gap-2">
                    <span className="bg-lime/40 px-1 border border-ink">Page {c.page}</span>
                    <span className="text-ink/60">Offsets: {c.char_start}–{c.char_end}</span>
                    <span className="text-ink/60">~{c.token_count_estimate} tok</span>
                  </div>
                </div>
                <div className="font-mono text-xs bg-paper p-2 border border-ink/20 whitespace-pre-wrap leading-relaxed">
                  {c.text}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  );
};
