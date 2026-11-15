import { clsx } from "clsx";
import type { ComponentType, ReactNode } from "react";

type StatTone = "neutral" | "orange" | "safe" | "warning" | "danger" | "info";

const ICON_TONES: Record<StatTone, string> = {
  neutral: "border-line bg-surface2 text-text-secondary",
  orange: "border-mars-orange/35 bg-mars-orange/10 text-mars-orange",
  safe: "border-safe-green/30 bg-safe-green/10 text-safe-green",
  warning: "border-warning-amber/35 bg-warning-amber/10 text-warning-amber",
  danger: "border-critical-red/35 bg-critical-red/10 text-critical-red",
  info: "border-cyan/30 bg-cyan/10 text-cyan",
};

interface StatCardProps {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  icon?: ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean }>;
  tone?: StatTone;
  status?: ReactNode;
  footnote?: ReactNode;
  className?: string;
}

export default function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  tone = "neutral",
  status,
  footnote,
  className,
}: StatCardProps) {
  return (
    <div className={clsx("panel min-w-0 p-4", className)}>
      <div className="flex items-start justify-between gap-3">
        <span className="text-micro leading-4 text-text-muted">{label}</span>
        {Icon && (
          <span
            className={clsx(
              "grid h-8 w-8 shrink-0 place-items-center rounded-control border",
              ICON_TONES[tone],
            )}
          >
            <Icon size={15} aria-hidden />
          </span>
        )}
      </div>
      <div className="mt-2.5 flex items-baseline gap-1.5">
        <span className="font-heading text-2xl font-semibold tabular leading-none text-text-primary">
          {value}
        </span>
        {unit && <span className="text-[11px] text-text-muted">{unit}</span>}
      </div>
      {status && <div className="mt-2.5">{status}</div>}
      {footnote && <div className="mt-2 text-[11px] leading-relaxed text-text-muted">{footnote}</div>}
    </div>
  );
}
