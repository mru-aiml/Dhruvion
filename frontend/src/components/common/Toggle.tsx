import { clsx } from "clsx";
import type { ReactNode } from "react";

export default function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className,
  id,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  label?: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
  className?: string;
  id?: string;
}) {
  const control = (
    <button
      type="button"
      role="switch"
      id={id}
      aria-checked={checked}
      aria-label={!label && typeof description === "string" ? description : undefined}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative inline-flex h-[22px] w-10 shrink-0 items-center rounded-full border transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40",
        checked ? "border-mars-orange/80 bg-mars-orange" : "border-line bg-surface3",
      )}
    >
      <span
        aria-hidden
        className={clsx(
          "absolute top-[2px] h-4 w-4 rounded-full shadow-sm transition-transform duration-150",
          checked ? "translate-x-[20px] bg-[#180d07]" : "translate-x-[2px] bg-text-secondary",
        )}
      />
    </button>
  );

  if (!label && !description) return <span className={className}>{control}</span>;

  return (
    <div
      className={clsx(
        "flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0",
        className,
      )}
    >
      <div className="min-w-0">
        {label && (
          <div className="text-sm font-medium leading-snug text-text-primary">{label}</div>
        )}
        {description && (
          <div className="mt-0.5 text-[11px] leading-relaxed text-text-muted">{description}</div>
        )}
      </div>
      {control}
    </div>
  );
}
