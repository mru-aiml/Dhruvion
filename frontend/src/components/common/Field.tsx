import { clsx } from "clsx";
import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

export const inputClass =
  "w-full rounded-control border border-line bg-[#0f0c09] px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/70 transition-colors duration-150 focus:border-mars-orange/70 focus:outline-none focus:ring-2 focus:ring-mars-orange/20 disabled:cursor-not-allowed disabled:opacity-50";

export const selectClass = `${inputClass} appearance-none pr-8`;

export function FieldShell({
  label,
  htmlFor,
  hint,
  error,
  children,
  className,
}: {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("min-w-0", className)}>
      <label htmlFor={htmlFor} className="mb-1.5 block text-micro text-text-muted">
        {label}
      </label>
      {children}
      {error ? (
        <p className="mt-1.5 text-[11px] leading-snug text-critical-red" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-[11px] leading-snug text-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

export function TextInput({
  className,
  invalid,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return (
    <input
      className={clsx(inputClass, invalid && "border-critical-red/60", className)}
      aria-invalid={invalid || undefined}
      {...rest}
    />
  );
}

export function SelectInput({
  className,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={clsx(selectClass, className)} {...rest}>
      {children}
    </select>
  );
}

export function Textarea({
  className,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={clsx(inputClass, "resize-none", className)} {...rest} />;
}
