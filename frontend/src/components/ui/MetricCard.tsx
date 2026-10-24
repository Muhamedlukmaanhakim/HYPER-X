import React, { useState } from "react";
import { Badge } from "./Badge";
import { HelpCircle } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  metricType?: "deterministic" | "model_judged";
  formula?: string;
  limitation?: string;
  delta?: number;
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  sublabel,
  metricType = "deterministic",
  formula,
  limitation,
  delta,
  highlight = false,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div
      className={`relative p-4 border-brutal border-ink bg-surface shadow-brutal transition-all ${
        highlight ? "ring-2 ring-lime" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-mono text-xs uppercase tracking-wider text-ink/80 font-bold">
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          <Badge variant={metricType} size="sm">
            {metricType === "deterministic" ? "DETERMINISTIC" : "MODEL-JUDGED"}
          </Badge>
          {(formula || limitation) && (
            <button
              type="button"
              onClick={() => setShowTooltip(!showTooltip)}
              className="text-ink/60 hover:text-ink cursor-pointer"
              title="Metric Info"
            >
              <HelpCircle size={14} />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="font-display text-3xl font-extrabold tracking-tight text-ink">
          {value}
        </span>
        {delta !== undefined && delta !== 0 && (
          <span
            className={`font-mono text-xs font-bold px-1.5 py-0.5 border border-ink ${
              delta > 0
                ? "bg-lime text-ink"
                : "bg-danger text-white"
            }`}
          >
            {delta > 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3)}
          </span>
        )}
      </div>

      {sublabel && (
        <p className="mt-1 font-mono text-[11px] text-ink/70 truncate">{sublabel}</p>
      )}

      {showTooltip && (
        <div className="mt-3 p-2.5 bg-paper border-2 border-ink text-xs font-mono shadow-[2px_2px_0_#171717]">
          {formula && (
            <div className="mb-1">
              <span className="font-bold">Formula: </span>
              <span className="text-ink/80">{formula}</span>
            </div>
          )}
          {limitation && (
            <div>
              <span className="font-bold text-danger">Limitation: </span>
              <span className="text-ink/80">{limitation}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
