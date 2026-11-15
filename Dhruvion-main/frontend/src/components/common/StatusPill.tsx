import { clsx } from "clsx";
import type { ReactNode } from "react";

export type StatusTone =
  | "observed"
  | "derived"
  | "simulated"
  | "unavailable"
  | "feasible"
  | "caution"
  | "critical"
  | "info"
  | "neutral";

const TONES: Record<StatusTone, string> = {
  observed: "border-safe-green/35 bg-safe-green/10 text-safe-green",
  derived: "border-cyan/35 bg-cyan/10 text-cyan",
  simulated: "border-amber/35 bg-amber/10 text-amber",
  unavailable: "border-line bg-surface2 text-text-muted",
  feasible: "border-safe-green/35 bg-safe-green/10 text-safe-green",
  caution: "border-warning-amber/40 bg-warning-amber/10 text-warning-amber",
  critical: "border-critical-red/40 bg-critical-red/10 text-critical-red",
  info: "border-cyan/30 bg-cyan/5 text-cyan",
  neutral: "border-line bg-surface2 text-text-secondary",
};

export default function StatusPill({
  tone = "neutral",
  children,
  dot = true,
  className,
}: {
  tone?: StatusTone;
  children: ReactNode;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase leading-4 tracking-[0.12em]",
        TONES[tone],
        className,
      )}
    >
      {dot && <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-current" />}
      {children}
    </span>
  );
}
