import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "surface" | "paper" | "lime" | "dark" | "flat";
  title?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = "",
  variant = "surface",
  title,
  action,
  footer,
}) => {
  const variantStyles = {
    surface: "bg-surface text-ink shadow-brutal border-brutal border-ink",
    paper: "bg-paper text-ink shadow-brutal border-brutal border-ink",
    lime: "bg-lime text-ink shadow-brutal border-brutal border-ink",
    dark: "bg-ink text-white shadow-brutal border-brutal border-ink",
    flat: "bg-surface text-ink border-2 border-ink",
  };

  return (
    <div className={`rounded-none transition-all ${variantStyles[variant]} ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b-2 border-ink px-4 py-3 bg-surface-muted/30">
          <div className="font-display font-bold text-base tracking-tight">{title}</div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
      {footer && (
        <div className="border-t-2 border-ink px-4 py-2.5 bg-surface-muted/20 text-xs font-mono">
          {footer}
        </div>
      )}
    </div>
  );
};
