import type { FeasibilityStatus, Availability } from "../../types";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

const feasibilityMap: Record<FeasibilityStatus, { label: string; color: string; Icon: typeof CheckCircle2 }> = {
  feasible: { label: "FEASIBLE", color: "text-safe-green border-safe-green/40 bg-safe-green/10", Icon: CheckCircle2 },
  caution: { label: "CAUTION", color: "text-warning-amber border-warning-amber/40 bg-warning-amber/10", Icon: AlertTriangle },
  not_feasible: { label: "NOT FEASIBLE", color: "text-critical-red border-critical-red/40 bg-critical-red/10", Icon: XCircle },
  unverified: { label: "UNVERIFIED", color: "text-text-muted border-line bg-surface2", Icon: HelpCircle },
};

export function FeasibilityBadge({ status }: { status: FeasibilityStatus }) {
  const m = feasibilityMap[status];
  const Icon = m.Icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md border text-micro ${m.color}`}>
      <Icon size={12} /> {m.label}
    </span>
  );
}

const availabilityMap: Record<Availability, { label: string; color: string }> = {
  available: { label: "AVAILABLE", color: "text-safe-green" },
  partial: { label: "PARTIAL", color: "text-warning-amber" },
  unavailable: { label: "UNAVAILABLE", color: "text-critical-red" },
  stale: { label: "STALE", color: "text-warning-amber" },
};

export function AvailabilityBadge({ status }: { status: Availability }) {
  const m = availabilityMap[status];
  return <span className={`text-micro ${m.color}`}>{m.label}</span>;
}

export function ProvenanceBadge({ status }: { status: string }) {
  const color =
    status === "observed" ? "text-safe-green border-safe-green/30" :
    status === "derived" ? "text-cyan border-cyan/30" :
    status === "simulated" ? "text-amber border-amber/30" :
    "text-text-muted border-line";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded border text-micro ${color}`}>
      {status.toUpperCase()}
    </span>
  );
}

export function SimulatedLabel() {
  return <span className="inline-flex items-center px-1.5 py-0.5 rounded border border-amber/40 bg-amber/10 text-amber text-micro">SIMULATED</span>;
}
