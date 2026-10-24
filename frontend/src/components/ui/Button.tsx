import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "dark";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  icon,
  className = "",
  disabled,
  loading = false,
  ...props
}) => {
  const baseStyles =
    "font-display font-semibold transition-all inline-flex items-center justify-center gap-2 border-[2.5px] border-ink rounded-none cursor-pointer select-none brutal-btn-active disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none";

  const sizeStyles = {
    sm: "px-2.5 py-1 text-xs shadow-[2px_2px_0_#171717]",
    md: "px-4 py-2 text-sm shadow-[3px_3px_0_#171717]",
    lg: "px-6 py-3 text-base shadow-[4px_4px_0_#171717]",
  };

  const variantStyles = {
    primary: "bg-lime text-ink hover:bg-lime-hover hover:shadow-[4px_4px_0_#171717]",
    secondary: "bg-surface text-ink hover:bg-surface-muted hover:shadow-[4px_4px_0_#171717]",
    danger: "bg-danger text-white hover:opacity-95 hover:shadow-[4px_4px_0_#171717]",
    ghost: "bg-transparent border-transparent shadow-none hover:bg-surface-muted hover:border-ink",
    dark: "bg-ink text-white hover:bg-surface-dark hover:shadow-[4px_4px_0_#C6FF4D]",
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="inline-block w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin flex-shrink-0" />
      ) : (
        icon && <span className="flex-shrink-0">{icon}</span>
      )}
      <span>{children}</span>
    </button>
  );
};
