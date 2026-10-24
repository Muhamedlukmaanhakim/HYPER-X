import React from "react";
import { RetrievedPassage } from "../../lib/types";
import { Badge } from "./Badge";
import { FileText } from "lucide-react";

interface PassageViewerProps {
  passages: RetrievedPassage[];
  highlightText?: string;
  expectedChunkIds?: string[];
}

export const PassageViewer: React.FC<PassageViewerProps> = ({
  passages,
  highlightText,
  expectedChunkIds = [],
}) => {
  if (!passages || passages.length === 0) {
    return (
      <div className="p-4 border-2 border-dashed border-ink/40 bg-surface-muted/20 text-center font-mono text-xs text-ink/60">
        No passages retrieved.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {passages.map((p, idx) => {
        const isTarget = expectedChunkIds.includes(p.chunk_id);
        return (
          <div
            key={p.chunk_id || idx}
            className={`p-3 border-2 border-ink bg-surface transition-all ${
              isTarget
                ? "ring-2 ring-lime shadow-[3px_3px_0_#C6FF4D]"
                : "shadow-[2px_2px_0_#171717]"
            }`}
          >
            <div className="flex items-center justify-between border-b border-ink/20 pb-2 mb-2 font-mono text-xs">
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-ink/70" />
                <span className="font-bold text-ink">Page {p.page}</span>
                <span className="text-ink/60">[{p.chunk_id}]</span>
                {isTarget && (
                  <Badge variant="pass" size="sm">
                    GROUND TRUTH EVIDENCE
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1.5 font-bold">
                <span className="text-[11px] text-ink/60">SIMILARITY:</span>
                <span className="bg-lime/50 px-1.5 py-0.5 border border-ink text-xs">
                  {p.score !== undefined ? p.score.toFixed(3) : "N/A"}
                </span>
              </div>
            </div>

            <div className="font-mono text-xs leading-relaxed text-ink/90 whitespace-pre-wrap bg-paper/60 p-2 border border-ink/20">
              {p.text}
            </div>
          </div>
        );
      })}
    </div>
  );
};
