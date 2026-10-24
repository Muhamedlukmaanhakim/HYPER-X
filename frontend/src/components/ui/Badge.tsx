import React from "react";

export type BadgeVariant =
  | "demo"
  | "simulated"
  | "pass"
  | "fail"
  | "review"
  | "warning"
  | "lime"
  | "neutral"
  | "deterministic"
  | "model_judged";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "neutral",
  className = "",
  size = "md",
}) => {
  const base =
    "inline-flex items-center font-mono font-bold uppercase tracking-wider border-2 border-ink select-none";

  const sizes = {
    sm: "px-1.5 py-0.5 text-[10px]",
    md: "px-2.5 py-0.5 text-xs",
  };

  const variants: Record<BadgeVariant, string> = {
    demo: "bg-[#FFB020] text-ink shadow-[2px_2px_0_#171717] ring-1 ring-ink",
    simulated: "bg-[#B197FC] text-ink shadow-[2px_2px_0_#171717]",
    pass: "bg-lime text-ink shadow-[2px_2px_0_#171717]",
    fail: "bg-danger text-white shadow-[2px_2px_0_#171717]",
    review: "bg-warning text-ink shadow-[2px_2px_0_#171717]",
    warning: "bg-warning text-ink shadow-[2px_2px_0_#171717]",
    lime: "bg-lime text-ink shadow-[2px_2px_0_#171717]",
    neutral: "bg-surface text-ink shadow-[1px_1px_0_#171717]",
    deterministic: "bg-surface-muted text-ink border-ink text-[10px]",
    model_judged: "bg-info text-white border-ink text-[10px]",
  };

  return (
    <span className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
};

export const CategoryBadge: React.FC<{ category: string; className?: string }> = ({
  category,
  className = "",
}) => {
  const categoryMap: Record<string, { label: string; variant: BadgeVariant }> = {
    pass: { label: "PASS", variant: "pass" },
    retrieval_miss: { label: "RETRIEVAL MISS", variant: "fail" },
    incomplete_or_irrelevant_context: { label: "INCOMPLETE CONTEXT", variant: "warning" },
    unsupported_answer: { label: "UNSUPPORTED ANSWER", variant: "fail" },
    incorrect_despite_relevant_context: { label: "INCORRECT DESPITE CONTEXT", variant: "fail" },
    citation_error: { label: "CITATION ERROR", variant: "warning" },
    unanswerable_answered: { label: "UNANSWERABLE ANSWERED", variant: "fail" },
    needs_review: { label: "NEEDS REVIEW", variant: "review" },
  };

  const info = categoryMap[category] || { label: category.toUpperCase(), variant: "neutral" };
  return (
    <Badge variant={info.variant} className={className}>
      {info.label}
    </Badge>
  );
};
