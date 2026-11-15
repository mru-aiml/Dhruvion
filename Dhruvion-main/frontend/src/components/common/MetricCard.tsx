export default function MetricCard({
  label, value, unit, status,
}: { label: string; value: string | number | null; unit?: string; status?: string }) {
  return (
    <div className="panel p-4">
      <div className="text-micro text-text-muted">{label}</div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold tabular">{value ?? "—"}</span>
        {unit && <span className="text-xs text-text-muted">{unit}</span>}
      </div>
      {status && <div className="mt-1 text-micro text-text-secondary">{status}</div>}
    </div>
  );
}
