import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Compass,
  MapPin,
  Navigation,
  RotateCcw,
  Route as RouteIcon,
  ShieldCheck,
  X,
} from "lucide-react";
import { MapContainer, Polyline, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import StatCard from "../../components/common/StatCard";
import StatusPill from "../../components/common/StatusPill";
import Button from "../../components/common/Button";
import { FeasibilityBadge, SimulatedLabel } from "../../components/common/StatusBadge";
import { MarsCRS, MOLA_ATTRIBUTION, MOLA_BASEMAP_URL } from "../../components/map/mars";

const ORIGINAL_ROUTE: [number, number][] = [
  [-5.45, 137.35],
  [-5.42, 137.38],
  [-5.4, 137.4],
  [-5.38, 137.42],
];
const ALT_ROUTE: [number, number][] = [
  [-5.45, 137.35],
  [-5.44, 137.36],
  [-5.4, 137.41],
  [-5.38, 137.42],
];

const SCENARIO = {
  remainingMin: 90,
  distanceToBaseKm: 2.1,
  originalDistanceKm: 3.2,
  originalDurationMin: 38,
  alternativeDistanceKm: 3.52,
  alternativeDurationMin: 44,
  distanceDeltaM: 320,
  durationDeltaMin: 6,
  reserveMin: 46,
};

export default function EmergencyPage() {
  const [generated, setGenerated] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [generating, setGenerating] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    },
    [],
  );

  const generate = () => {
    setGenerating(true);
    timerRef.current = window.setTimeout(() => {
      setGenerating(false);
      setGenerated(true);
      setConfirm(false);
      timerRef.current = null;
    }, 700);
  };

  const resetScenario = () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setGenerating(false);
    setGenerated(false);
    setConfirm(false);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Contingency workspace"
        title="Emergency Navigation"
        description="A simulated blocked-traverse scenario for Gale Crater. The obstruction and reroute are injected for training; no observed hazard dataset is connected in this build."
        meta={
          <>
            <SimulatedLabel />
            <StatusPill tone="critical">Scenario incident</StatusPill>
            <StatusPill tone="unavailable">No hazard overlay</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              <MapPin size={10} /> Gale Crater
            </StatusPill>
          </>
        }
        actions={
          generated ? (
            <Button
              variant="secondary"
              size="md"
              icon={<RotateCcw size={14} />}
              onClick={resetScenario}
            >
              Reset scenario
            </Button>
          ) : undefined
        }
      />

      <IncidentBanner />

      <div aria-live="polite">
        {generated && (
          <div className="panel flex flex-wrap items-start gap-3 border-safe-green/45 bg-safe-green/[0.06] p-3.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-control border border-safe-green/40 bg-safe-green/10 text-safe-green">
              <CheckCircle2 size={18} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-[9px] font-semibold uppercase tracking-[0.12em] text-safe-green">
                    Reroute complete
                  </div>
                  <h2 className="mt-0.5 font-heading text-sm font-semibold text-text-primary">
                    Alternative route generated and validated
                  </h2>
                </div>
                <StatusPill tone="feasible">Return feasible</StatusPill>
              </div>
              <p className="mt-1.5 max-w-3xl text-[11px] leading-relaxed text-text-secondary">
                The simulated alternative avoids the blocked mid-traverse segment and returns
                within the remaining {SCENARIO.remainingMin} min budget, leaving an estimated{" "}
                {SCENARIO.reserveMin} min reserve. Feasibility is a scenario estimate, not a
                certified traverse plan.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Remaining mission time"
          value={SCENARIO.remainingMin}
          unit="min"
          icon={Clock}
          tone="warning"
          status={<StatusPill tone="caution">Low reserve</StatusPill>}
          footnote="Scenario clock. Not live telemetry."
        />
        <StatCard
          label="Distance to base"
          value={SCENARIO.distanceToBaseKm}
          unit="km"
          icon={Navigation}
          tone="danger"
          status={<StatusPill tone="critical">Return required</StatusPill>}
          footnote="Straight-line scenario distance to the landing site."
        />
        <StatCard
          label="Alternative route"
          value={generated ? "Available" : "Not generated"}
          icon={RouteIcon}
          tone={generated ? "safe" : "warning"}
          status={
            generated ? (
              <StatusPill tone="feasible">Rerouted</StatusPill>
            ) : (
              <StatusPill tone="caution">Action required</StatusPill>
            )
          }
          footnote="Frontend-computed demonstration reroute."
        />
        <StatCard
          label="Return status"
          value={generated ? "FEASIBLE" : "UNVERIFIED"}
          icon={ShieldCheck}
          tone={generated ? "safe" : "neutral"}
          status={
            generated ? (
              <StatusPill tone="feasible">Validated</StatusPill>
            ) : (
              <StatusPill tone="neutral">Awaiting reroute</StatusPill>
            )
          }
          footnote="Missing route data stays unverified, never assumed safe."
        />
      </div>

      {!generated ? (
        <SectionCard
          eyebrow="Contingency protocol"
          title="Generate a safe alternative route"
          description="The original traverse is treated as blocked. Re-planning is a local scenario calculation and does not query an observed hazard service."
          actions={
            <>
              <StatusPill tone="critical">Blocked</StatusPill>
              <SimulatedLabel />
            </>
          }
        >
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <ol className="grid gap-2.5 sm:grid-cols-3">
              {[
                {
                  icon: AlertTriangle,
                  title: "Mark obstruction",
                  body: "Flag the mid-traverse segment as blocked in the scenario.",
                },
                {
                  icon: Compass,
                  title: "Re-plan around it",
                  body: "Compute a demonstration detour around the affected segment.",
                },
                {
                  icon: ShieldCheck,
                  title: "Validate return",
                  body: "Check the detour against the remaining 90 min budget.",
                },
              ].map((step, index) => {
                const Icon = step.icon;
                return (
                  <li
                    key={step.title}
                    className="rounded-control border border-line/60 bg-surface2/40 p-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="grid h-6 w-6 place-items-center rounded-full border border-line bg-surface1 text-[9px] font-semibold tabular text-text-secondary">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <Icon size={14} className="text-warning-amber" aria-hidden />
                    </div>
                    <div className="mt-2 text-[11px] font-medium text-text-primary">
                      {step.title}
                    </div>
                    <p className="mt-1 text-[10px] leading-relaxed text-text-muted">
                      {step.body}
                    </p>
                  </li>
                );
              })}
            </ol>

            <div className="flex flex-col items-stretch gap-2 lg:w-64">
              <Button
                variant="danger"
                size="lg"
                icon={<AlertTriangle size={15} />}
                onClick={() => setConfirm(true)}
                className="w-full"
              >
                Generate alternative
              </Button>
              <p className="text-center text-[9px] uppercase tracking-[0.1em] text-text-muted">
                Simulated · no rover command sent
              </p>
            </div>
          </div>
        </SectionCard>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,1fr)]">
          <SectionCard
            eyebrow="Route comparison"
            title="Before / after traverse"
            actions={
              <>
                <StatusPill tone="critical">Original blocked</StatusPill>
                <StatusPill tone="feasible">Alternative feasible</StatusPill>
              </>
            }
            flush
          >
            <div className="p-3.5">
              <div className="grid gap-3 sm:grid-cols-2">
                <RouteMap
                  kind="original"
                  heading="Before · blocked"
                  route={ORIGINAL_ROUTE}
                  color="#E45C5C"
                />
                <RouteMap
                  kind="alternative"
                  heading="After · rerouted"
                  route={ALT_ROUTE}
                  color="#65B88A"
                />
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <RouteSummary
                  tone="critical"
                  label="Original route"
                  distance={SCENARIO.originalDistanceKm}
                  duration={SCENARIO.originalDurationMin}
                  note="Blocked at mid-traverse"
                />
                <RouteSummary
                  tone="safe"
                  label="Alternative route"
                  distance={SCENARIO.alternativeDistanceKm}
                  duration={SCENARIO.alternativeDurationMin}
                  note="Avoids blocked segment"
                />
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line/50 pt-2.5">
                <div className="flex flex-wrap items-center gap-3 text-[9px] uppercase tracking-[0.08em]">
                  <span className="flex items-center gap-1.5 text-text-secondary">
                    <span className="h-0.5 w-4 bg-critical-red" /> Original · blocked
                  </span>
                  <span className="flex items-center gap-1.5 text-text-secondary">
                    <span className="h-0.5 w-4 border-t-2 border-dashed border-safe-green" />{" "}
                    Alternative · feasible
                  </span>
                </div>
                <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  NASA Mars Trek basemap · observed
                </span>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Rerouting results"
            title="Scenario delta"
            actions={<FeasibilityBadge status="feasible" />}
            bodyClassName="p-4"
          >
            <dl className="space-y-2.5">
              <ResultRow label="New distance" value={`${SCENARIO.alternativeDistanceKm.toFixed(2)} km`} />
              <ResultRow label="New duration" value={`${SCENARIO.alternativeDurationMin} min`} />
              <ResultRow
                label="Distance delta"
                value={`+${SCENARIO.distanceDeltaM} m`}
                tone="warning"
              />
              <ResultRow
                label="Duration delta"
                value={`+${SCENARIO.durationDeltaMin} min`}
                tone="warning"
              />
              <ResultRow
                label="Remaining budget"
                value={`${SCENARIO.reserveMin} min reserve`}
                tone="safe"
              />
              <ResultRow label="Reroute reason" value="Simulated rockfall on original segment" />
            </dl>

            <div className="mt-4 rounded-control border border-safe-green/30 bg-safe-green/[0.05] p-2.5">
              <div className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-safe-green">
                <CheckCircle2 size={12} aria-hidden /> Return validated
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-text-secondary">
                44 min detour fits inside the 90 min remaining budget with an estimated 46 min
                reserve under scenario assumptions.
              </p>
            </div>

            <div className="mt-3 border-t border-line/50 pt-2.5">
              <div className="flex flex-wrap items-center gap-1.5">
                <SimulatedLabel />
                <StatusPill tone="unavailable">No observed evidence</StatusPill>
              </div>
              <p className="mt-1.5 text-[10px] leading-relaxed text-text-muted">
                Evidence: simulated scenario only. No hazard raster or observation supports this
                obstruction or the detour geometry.
              </p>
            </div>
          </SectionCard>
        </div>
      )}

      {confirm && (
        <ConfirmReroute
          generating={generating}
          onCancel={() => setConfirm(false)}
          onConfirm={generate}
        />
      )}
    </div>
  );
}

function IncidentBanner() {
  return (
    <section
      role="alert"
      aria-live="assertive"
      className="panel border-critical-red/50 bg-critical-red/[0.055] p-4"
    >
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-control border border-critical-red/45 bg-critical-red/10 text-critical-red">
          <AlertTriangle size={20} aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-critical-red">
                Hazard alert · simulated scenario
              </div>
              <h2 className="mt-0.5 font-heading text-base font-semibold text-text-primary">
                Blocked traverse detected
              </h2>
            </div>
            <StatusPill tone="critical">Danger</StatusPill>
          </div>
          <p className="mt-1.5 max-w-3xl text-xs leading-relaxed text-text-secondary">
            A rockfall obstruction has been injected into the demo scenario across the
            mid-traverse segment. This is a training simulation, not live rover telemetry, and no
            observed hazard dataset is connected.
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-critical-red/20 pt-2.5 sm:grid-cols-4">
            {[
              ["Hazard type", "Rockfall (simulated)"],
              ["Blocked segment", "Mid-traverse"],
              ["Scenario time", "09:26"],
              ["Remaining time", `${SCENARIO.remainingMin} min`],
            ].map(([label, value]) => (
              <div key={label} className="min-w-0">
                <dt className="text-[9px] uppercase tracking-[0.1em] text-text-muted">{label}</dt>
                <dd className="mt-0.5 truncate text-[11px] text-text-secondary">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}

function RouteMap({
  kind,
  heading,
  route,
  color,
}: {
  kind: "original" | "alternative";
  heading: string;
  route: [number, number][];
  color: string;
}) {
  const critical = kind === "original";
  return (
    <div className="min-w-0">
      <div
        className={`relative h-[210px] overflow-hidden rounded-control border sm:h-[250px] ${
          critical ? "border-critical-red/40" : "border-safe-green/40"
        }`}
      >
        <MapContainer
          crs={MarsCRS}
          center={[-5.4, 137.4]}
          zoom={7}
          style={{ height: "100%", width: "100%", background: "#14100c" }}
          zoomControl={false}
          attributionControl
          scrollWheelZoom={false}
          className="dhruvion-map"
        >
          <TileLayer
            url={MOLA_BASEMAP_URL}
            attribution={MOLA_ATTRIBUTION}
            tileSize={256}
            maxZoom={8}
          />
          <Polyline
            positions={route}
            pathOptions={{
              color,
              weight: 3.5,
              opacity: 0.95,
              dashArray: critical ? undefined : "7 5",
            }}
          />
        </MapContainer>
        <div
          className={`pointer-events-none absolute left-2.5 top-2.5 rounded border bg-black/70 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.1em] backdrop-blur-sm ${
            critical
              ? "border-critical-red/50 text-critical-red"
              : "border-safe-green/50 text-safe-green"
          }`}
        >
          {heading}
        </div>
        {critical && (
          <div className="pointer-events-none absolute inset-0 grid place-items-center bg-black/20">
            <span className="rounded border border-critical-red/60 bg-black/70 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-critical-red">
              Blocked
            </span>
          </div>
        )}
      </div>
      <div className="mt-1 text-[9px] uppercase tracking-[0.08em] text-text-muted">
        {critical ? "Original scenario route" : "Demonstration detour"} · prototype CRS
      </div>
    </div>
  );
}

function RouteSummary({
  tone,
  label,
  distance,
  duration,
  note,
}: {
  tone: "critical" | "safe";
  label: string;
  distance: number;
  duration: number;
  note: string;
}) {
  const critical = tone === "critical";
  return (
    <div
      className={`rounded-control border px-3 py-2.5 ${
        critical
          ? "border-critical-red/30 bg-critical-red/[0.045]"
          : "border-safe-green/30 bg-safe-green/[0.045]"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium text-text-primary">{label}</span>
        <span
          className={`text-[9px] font-semibold uppercase tracking-[0.08em] ${
            critical ? "text-critical-red" : "text-safe-green"
          }`}
        >
          {critical ? "Blocked" : "Feasible"}
        </span>
      </div>
      <div className="mt-1 flex items-baseline gap-3 text-[11px] tabular text-text-secondary">
        <span>{distance.toFixed(2)} km</span>
        <span className="text-text-muted">·</span>
        <span>{duration} min</span>
      </div>
      <div className="mt-0.5 text-[9px] uppercase tracking-[0.08em] text-text-muted">{note}</div>
    </div>
  );
}

function ResultRow({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "warning" | "safe";
}) {
  const valueColor =
    tone === "warning" ? "text-warning-amber" : tone === "safe" ? "text-safe-green" : "text-text-primary";
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line/40 pb-2.5 last:border-b-0 last:pb-0">
      <dt className="text-[11px] text-text-muted">{label}</dt>
      <dd className={`max-w-[60%] text-right text-[11px] tabular leading-snug ${valueColor}`}>
        {value}
      </dd>
    </div>
  );
}

function ConfirmReroute({
  generating,
  onCancel,
  onConfirm,
}: {
  generating: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !generating) onCancel();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [generating, onCancel]);

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Cancel reroute"
        className="absolute inset-0 bg-black/70 backdrop-blur-[2px]"
        onClick={onCancel}
      />
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="reroute-title"
        aria-describedby="reroute-description"
        className="panel relative w-full max-w-md border-critical-red/40 bg-surface1 p-5 shadow-2xl outline-none"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-control border border-critical-red/40 bg-critical-red/10 text-critical-red">
              <AlertTriangle size={18} aria-hidden />
            </span>
            <div>
              <div className="text-[9px] font-semibold uppercase tracking-[0.12em] text-critical-red">
                Confirm contingency action
              </div>
              <h2 id="reroute-title" className="mt-0.5 font-heading text-base font-semibold">
                Generate alternative route?
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            aria-label="Close dialog"
            disabled={generating}
            className="grid h-7 w-7 place-items-center rounded-control border border-transparent text-text-muted transition-colors hover:border-line hover:bg-surface2 hover:text-text-primary disabled:opacity-40"
          >
            <X size={15} />
          </button>
        </div>

        <p id="reroute-description" className="mt-3 text-xs leading-relaxed text-text-secondary">
          The current route will be marked blocked and a demonstration detour will be calculated.
          This scenario is simulated and does not command the rover or query an observed hazard
          service.
        </p>

        <dl className="mt-3 grid grid-cols-2 gap-2 rounded-control border border-line/60 bg-surface2/40 p-2.5 text-[10px]">
          <div>
            <dt className="text-[9px] uppercase tracking-[0.08em] text-text-muted">Blocked</dt>
            <dd className="mt-0.5 text-text-secondary">Mid-traverse segment</dd>
          </div>
          <div>
            <dt className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
              Remaining time
            </dt>
            <dd className="mt-0.5 tabular text-text-secondary">{SCENARIO.remainingMin} min</dd>
          </div>
        </dl>

        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button variant="secondary" size="md" onClick={onCancel} disabled={generating}>
            Cancel
          </Button>
          <Button
            variant="danger"
            size="md"
            icon={<AlertTriangle size={13} />}
            loading={generating}
            onClick={onConfirm}
          >
            {generating ? "Generating detour" : "Confirm reroute"}
          </Button>
        </div>
      </div>
    </div>
  );
}
