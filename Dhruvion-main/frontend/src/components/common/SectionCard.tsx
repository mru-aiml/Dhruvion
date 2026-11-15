import { clsx } from "clsx";
import type { ReactNode } from "react";

interface SectionCardProps {
  title?: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  flush?: boolean;
  id?: string;
}

export default function SectionCard({
  title,
  eyebrow,
  description,
  actions,
  children,
  className,
  bodyClassName,
  flush = false,
  id,
}: SectionCardProps) {
  const hasHeader = Boolean(title || eyebrow || actions || description);
  return (
    <section id={id} className={clsx("panel min-w-0", className)}>
      {hasHeader && (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line/60 px-4 py-3">
          <div className="min-w-0">
            {eyebrow && <div className="text-micro text-mars-orange/90">{eyebrow}</div>}
            {title && (
              <h2 className="font-heading text-sm font-semibold leading-snug text-text-primary">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-1 max-w-xl text-xs leading-relaxed text-text-muted">{description}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={clsx(flush ? "" : "p-4", bodyClassName)}>{children}</div>
    </section>
  );
}
