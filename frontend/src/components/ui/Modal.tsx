import React, { useEffect } from "react";
import { X } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl";
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = "lg",
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidthStyles = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-2xl",
    "2xl": "max-w-4xl",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/60 backdrop-blur-none">
      <div
        className={`w-full ${maxWidthStyles[maxWidth]} bg-surface border-brutal border-ink shadow-[6px_6px_0_#171717] animate-in fade-in zoom-in-95 duration-100`}
      >
        <div className="flex items-center justify-between border-b-2 border-ink px-4 py-3 bg-surface-muted/40">
          <h3 className="font-display font-bold text-lg text-ink tracking-tight">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-surface-muted border-2 border-transparent hover:border-ink transition-all cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-5 max-h-[80vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  );
};
