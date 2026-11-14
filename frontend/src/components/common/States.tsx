import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-6 text-sm text-text-secondary" role="status">
      <Loader2 size={16} className="animate-spin text-mars-orange" aria-hidden />
      {label}
    </div>
  );
}

export function SkeletonRows({ rows = 4, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="h-9 animate-pulse rounded-control border border-line/40 bg-surface2/60"
        />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-control border border-dashed border-line/70 bg-surface1/40 px-6 py-10 text-center ${className}`}
    >
      <span className="grid h-10 w-10 place-items-center rounded-full border border-line bg-surface2 text-text-muted">
        {icon ?? <Inbox size={18} aria-hidden />}
      </span>
      <div className="mt-3 text-sm font-medium text-text-primary">{title}</div>
      {description && (
        <div className="mt-1 max-w-sm text-xs leading-relaxed text-text-secondary">
          {description}
        </div>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  compact = false,
}: {
  message: string;
  onRetry?: () => void;
  compact?: boolean;
}) {
  return (
    <div
      role="alert"
      className={`rounded-control border border-critical-red/40 bg-critical-red/[0.07] ${
        compact ? "px-3 py-2" : "p-4"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <AlertCircle size={16} className="mt-0.5 shrink-0 text-critical-red" aria-hidden />
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-critical-red">
            Request failed
          </div>
          <div className="mt-1 text-xs leading-relaxed text-text-secondary">{message}</div>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-mars-orange hover:underline"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
