import { clsx } from "clsx";
import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "border-mars-orange bg-mars-orange text-[#170d08] hover:border-[#ff8054] hover:bg-[#ff8054]",
  secondary:
    "border-line bg-surface2 text-text-primary hover:border-amber/60 hover:bg-surface3",
  ghost:
    "border-transparent bg-transparent text-text-secondary hover:bg-surface2 hover:text-text-primary",
  danger:
    "border-critical-red bg-critical-red text-[#1b0707] hover:border-[#ef7373] hover:bg-[#ef7373]",
  outline:
    "border-line bg-transparent text-text-primary hover:border-mars-orange/70 hover:text-mars-orange",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "px-2.5 py-1.5 text-[10px] tracking-[0.1em]",
  md: "px-3.5 py-2 text-[11px] tracking-[0.09em]",
  lg: "px-4 py-2.5 text-xs tracking-[0.08em]",
};

export function buttonClasses(
  variant: ButtonVariant = "secondary",
  size: ButtonSize = "md",
  className?: string,
) {
  return clsx(
    "inline-flex items-center justify-center gap-2 rounded-control border font-semibold uppercase transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
}

export default function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  icon,
  className,
  children,
  disabled,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Loader2 size={14} className="animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  );
}
