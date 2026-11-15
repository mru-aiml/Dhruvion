import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Compass,
  Loader2,
  MapPin,
  Navigation,
  RotateCcw,
  Route as RouteIcon,
  ShieldCheck,
  X,
} from "lucide-react";
import { MapContainer, Polyline, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import StatCard from "../../components/common/StatCard";
import StatusPill from "../../components/common/StatusPill";
import Button from "../../components/common/Button";
import { FeasibilityBadge, ProvenanceBadge, SimulatedLabel } from "../../components/common/StatusBadge";
import { MarsCRS, MOLA_ATTRIBUTION, MOLA_BASEMAP_URL } from "../../components/map/mars";
import { endpoints } from "../../services/api/endpoints";
import { apiErrorMessage } from "../../services/api/client";
import { loadMission, saveMission } from "../../services/missionStore";
import type { MissionPlanResponse, RerouteResponse, Route } from "../../types";

const REGION_ID = "gale_crater";
const DEFAULT_START = { lat: -4.5, lon: 137.2 };
const DEFAULT_DEST = { lat: -4.55, lon: 137.3 };
const DEFAULT_TIME_LIMIT = 600;
const MARS_RADIUS_M = 3_396_190;
const BLOCKAGE_BUFFER_M = 1500;

export default function EmergencyPage() {
  const [mission, setMission] = useState<MissionPlanResponse | null>(null);
  const [result, setResult] = useState<RerouteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const current = await ensureMission();
        if (active) setMission(current);
      } catch (reason) {
        if (active) setError(apiErrorMessage(reason));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const originalRoute = mission?.route ?? null;
  const alternativeRoute = asRoute(result?.alternative_route);
  const remainingMin =
    mission?.time_budget.remaining_after_plan_min ?? mission?.time_budget.limit_min ?? null;
  const distanceToBaseKm = mission ? groundDistanceM(mission.destination, mission.start) / 1000 : null;
  const generated = result !== null;
  const feasibility = result?.feasibility_status;

  const generate = async () => {
    setGenerating(true);
    setError(null);
    try {
      let current = mission ?? (await ensureMission());
      setMission(current);
      const route = current.route;
      const blockage = blockedPoint(route);
      if (!blockage) {
        throw new Error("The mission route has no geometry to block.");
      }

      const body = (missionId: string) => ({
        mission_id: missionId,
        original_route_id: route.id,
        blocked_geometry: blockage,
        scenario_status: "simulated",
        remaining_time_min:
          current.time_budget.remaining_after_plan_min ??
          current.time_budget.limit_min ??
          DEFAULT_TIME_LIMIT,
        strategy: current.route_strategy ?? "balanced",
        buffer_m: BLOCKAGE_BUFFER_M,
      });

      let response: RerouteResponse;
      try {
        response = await endpoints.reroute(body(current.mission_id));
      } catch {
        // Backend missions are in memory; replan once if the stored mission went stale.
        current = await planDefaultMission();
        saveMission(current);
        setMission(current);
        response = await endpoints.reroute(body(current.mission_id));
      }

      setResult(response);
      setConfirm(false);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setGenerating(false);
    }
  };

  const resetScenario = () => {
    setResult(null);
    setConfirm(false);
    setError(null);
  };

  const rerouteFeasible =
    feasibility === "feasible" ? true : feasibility === "caution" ? false : false;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Contingency workspace"
        title="Emergency Navigation"
        description="A simulated blockage is injected at the midpoint of the current backend mission route. The alternative path, distances and durations are computed by the real coverage-aware A* planner; no observed hazard dataset is connected."
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

      <IncidentBanner mission={mission} remainingMin={remainingMin} />

      <div aria-live="polite">
        {generated && (
          <div
            className={`panel flex flex-wrap items-start gap-3 p-3.5 ${
              feasibility === "feasible"
                ? "border-safe-green/45 bg-safe-green/[0.06]"
                : "border-warning-amber/45 bg-warning-amber/[0.06]"
            }`}
          >
            <span
              className={`grid h-9 w-9 shrink-0 place-items-center rounded-control border ${
                feasibility === "feasible"
                  ? "border-safe-green/40 bg-safe-green/10 text-safe-green"
                  : "border-warning-amber/40 bg-warning-amber/10 text-warning-amber"
              }`}
            >
              {feasibility === "feasible" ? (
                <CheckCircle2 size={18} aria-hidden />
              ) : (
                <AlertTriangle size={18} aria-hidden />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div
                    className={`text-[9px] font-semibold uppercase tracking-[0.12em] ${
                      feasibility === "feasible" ? "text-safe-green" : "text-warning-amber"
                    }`}
                  >
                    {feasibility === "feasible" ? "Reroute complete" : "Reroute limited"}
                  </div>
                  <h2 className="mt-0.5 font-heading text-sm font-semibold text-text-primary">
                    {result?.reason ?? "Alternative route evaluated"}
                  </h2>
                </div>
                {feasibility && <FeasibilityBadge status={feasibility} />}
              </div>
              <p className="mt-1.5 max-w-3xl text-[11px] leading-relaxed text-text-secondary">
                Computed by the backend A* planner over the processed MOLA grid with a simulated{" "}
                {BLOCKAGE_BUFFER_M} m blockage buffer at the route midpoint. Values are planning
                estimates, not a certified traverse.
              </p>
            </div>
          </div>
        )}
      </div>

      {error && <div className="text-xs text-critical-red">{error}</div>}

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Remaining mission time"
          value={loading ? "—" : fmt(remainingMin)}
          unit={remainingMin === null ? undefined : "min"}
          icon={Clock}
          tone="warning"
          status={
            remainingMin === null ? (
              <StatusPill tone="neutral">Unavailable</StatusPill>
            ) : remainingMin < 30 ? (
              <StatusPill tone="caution">Low reserve</StatusPill>
            ) : (
              <StatusPill tone="neutral">Planning budget</StatusPill>
            )
          }
          footnote="Derived from the mission time budget. Not live telemetry."
        />
        <StatCard
          label="Distance to base"
          value={loading ? "—" : distanceToBaseKm === null ? "—" : distanceToBaseKm.toFixed(2)}
          unit={distanceToBaseKm === null ? undefined : "km"}
          icon={Navigation}
          tone="danger"
          status={<StatusPill tone="critical">Return required</StatusPill>}
          footnote="Straight-line distance from the mission destination to the recorded start."
        />
        <StatCard
          label="Alternative route"
          value={generated ? (alternativeRoute ? "Available" : "Unavailable") : "Not generated"}
          icon={RouteIcon}
          tone={generated && alternativeRoute ? "safe" : "warning"}
          status={
            generated && alternativeRoute ? (
              <StatusPill tone="feasible">Rerouted</StatusPill>
            ) : (
              <StatusPill tone="caution">Action required</StatusPill>
            )
          }
          footnote="Backend A* detour around the simulated blockage."
        />
        <StatCard
          label="Return status"
          value={feasibility ? feasibility.replace(/_/g, " ").toUpperCase() : "UNVERIFIED"}
          icon={ShieldCheck}
          tone={feasibility === "feasible" ? "safe" : feasibility ? "warning" : "neutral"}
          status={
            feasibility ? (
              <StatusPill tone={feasibility === "feasible" ? "feasible" : "caution"}>
                {feasibility === "feasible" ? "Validated" : "Review required"}
              </StatusPill>
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
          title="Generate an alternative route"
          description="The current mission route is treated as blocked at its midpoint. Re-planning uses the real terrain grid and the supplied simulated blockage geometry."
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
                  title: "Inject obstruction",
                  body: "A simulated point blockage is placed at the midpoint of the mission route.",
                },
                {
                  icon: Compass,
                  title: "Re-plan around it",
                  body: "The backend A* planner computes a detour over the MOLA coverage grid.",
                },
                {
                  icon: ShieldCheck,
                  title: "Validate the result",
                  body: "Feasibility is checked against the remaining mission time budget.",
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
                icon={generating ? <Loader2 size={15} className="animate-spin" /> : <AlertTriangle size={15} />}
                onClick={() => setConfirm(true)}
                disabled={loading || !mission}
                className="w-full"
              >
                {generating ? "Computing detour" : "Generate alternative"}
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
                <FeasibilityBadge status={feasibility ?? "unverified"} />
              </>
            }
            flush
          >
            <div className="p-3.5">
              <div className="grid gap-3 sm:grid-cols-2">
                <RouteMap
                  kind="original"
                  heading="Before · blocked"
                  route={originalRoute ? routePositions(originalRoute) : []}
                  color="#E45C5C"
                />
                <RouteMap
                  kind="alternative"
                  heading="After · rerouted"
                  route={alternativeRoute ? routePositions(alternativeRoute) : []}
                  color="#65B88A"
                />
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <RouteSummary
                  tone="critical"
                  label="Original route"
                  distanceKm={originalRoute ? originalRoute.distance_m / 1000 : null}
                  durationMin={originalRoute?.estimated_duration_min ?? null}
                  note="Blocked at midpoint"
                />
                <RouteSummary
                  tone="safe"
                  label="Alternative route"
                  distanceKm={alternativeRoute ? alternativeRoute.distance_m / 1000 : null}
                  durationMin={alternativeRoute?.estimated_duration_min ?? null}
                  note={alternativeRoute ? "Avoids blocked segment" : "No alternative found"}
                />
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line/50 pt-2.5">
                <div className="flex flex-wrap items-center gap-3 text-[9px] uppercase tracking-[0.08em]">
                  <span className="flex items-center gap-1.5 text-text-secondary">
                    <span className="h-0.5 w-4 bg-critical-red" /> Original · blocked
                  </span>
                  <span className="flex items-center gap-1.5 text-text-secondary">
                    <span className="h-0.5 w-4 border-t-2 border-dashed border-safe-green" />{" "}
                    Alternative · computed
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
            title="Backend delta"
            actions={<FeasibilityBadge status={feasibility ?? "unverified"} />}
            bodyClassName="p-4"
          >
            <dl className="space-y-2.5">
              <ResultRow
                label="New distance"
                value={
                  alternativeRoute
                    ? `${(alternativeRoute.distance_m / 1000).toFixed(2)} km`
                    : "unavailable"
                }
              />
              <ResultRow
                label="New duration"
                value={alternativeRoute ? fmtMin(alternativeRoute.estimated_duration_min) : "unavailable"}
              />
              <ResultRow
                label="Distance delta"
                value={formatDelta(result?.distance_delta_m, "m", 0)}
                tone={deltaTone(result?.distance_delta_m)}
              />
              <ResultRow
                label="Duration delta"
                value={formatDelta(result?.duration_delta_min, "min", 1)}
                tone={deltaTone(result?.duration_delta_min)}
              />
              <ResultRow
                label="Remaining budget"
                value={remainingMin === null ? "unavailable" : `${remainingMin} min`}
                tone="safe"
              />
              <ResultRow label="Scenario" value="Simulated midpoint blockage" />
            </dl>

            <div
              className={`mt-4 rounded-control border p-2.5 ${
                rerouteFeasible
                  ? "border-safe-green/30 bg-safe-green/[0.05]"
                  : "border-warning-amber/30 bg-warning-amber/[0.05]"
              }`}
            >
              <div
                className={`flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.12em] ${
                  rerouteFeasible ? "text-safe-green" : "text-warning-amber"
                }`}
              >
                {rerouteFeasible ? (
                  <CheckCircle2 size={12} aria-hidden />
                ) : (
                  <AlertTriangle size={12} aria-hidden />
                )}
                {rerouteFeasible ? "Return validated" : "Review required"}
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-text-secondary">
                {result?.reason ?? "No backend feasibility reason returned."}
              </p>
            </div>

            {result?.warnings && result.warnings.length > 0 && (
              <div className="mt-3 border-t border-line/50 pt-2.5">
                <div className="text-[9px] uppercase tracking-[0.1em] text-warning-amber">
                  Warnings
                </div>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[10px] leading-relaxed text-text-secondary">
                  {result.warnings.slice(0, 4).map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line/50 pt-2.5">
              <SimulatedLabel />
              <StatusPill tone="unavailable">No observed evidence</StatusPill>
              {(result?.provenance ?? []).map((entry) => (
                <ProvenanceBadge key={entry} status={entry} />
              ))}
            </div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-text-muted">
              Evidence: simulated scenario plus derived terrain routing. No hazard raster or
              observation supports this obstruction.
            </p>
          </SectionCard>
        </div>
      )}

      {confirm && (
        <ConfirmReroute
          generating={generating}
          remainingMin={remainingMin}
          onCancel={() => setConfirm(false)}
          onConfirm={generate}
        />
      )}
    </div>
  );
}

function IncidentBanner({
  mission,
  remainingMin,
}: {
  mission: MissionPlanResponse | null;
  remainingMin: number | null;
}) {
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
            A point obstruction is injected at the midpoint of the current mission route for this
            training scenario. This is not live rover telemetry and no observed hazard dataset is
            connected.
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-critical-red/20 pt-2.5 sm:grid-cols-4">
            {[
              ["Hazard type", "Point blockage (simulated)"],
              ["Blocked segment", "Midpoint of mission route"],
              ["Mission", mission?.mission_id ?? "unavailable"],
              ["Remaining time", remainingMin === null ? "unavailable" : `${remainingMin} min`],
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
  const center = route.length
    ? route[Math.floor(route.length / 2)]
    : ([-5.4, 137.4] as [number, number]);
  return (
    <div className="min-w-0">
      <div
        className={`relative h-[210px] overflow-hidden rounded-control border sm:h-[250px] ${
          critical ? "border-critical-red/40" : "border-safe-green/40"
        }`}
      >
        <MapContainer
          crs={MarsCRS}
          center={center}
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
          {route.length > 1 && (
            <>
              <Polyline
                positions={route}
                pathOptions={{
                  color,
                  weight: 3.5,
                  opacity: 0.95,
                  dashArray: critical ? undefined : "7 5",
                }}
              />
              <FitRoute route={route} />
            </>
          )}
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
        {!route.length && (
          <div className="pointer-events-none absolute inset-0 grid place-items-center bg-black/40">
            <span className="rounded border border-line bg-black/70 px-3 py-1 text-[10px] uppercase tracking-[0.12em] text-text-muted">
              No geometry returned
            </span>
          </div>
        )}
      </div>
      <div className="mt-1 text-[9px] uppercase tracking-[0.08em] text-text-muted">
        {critical ? "Original mission route" : "Backend-computed detour"} · Mars equirectangular
      </div>
    </div>
  );
}

function RouteSummary({
  tone,
  label,
  distanceKm,
  durationMin,
  note,
}: {
  tone: "critical" | "safe";
  label: string;
  distanceKm: number | null;
  durationMin: number | null;
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
          {critical ? "Blocked" : "Computed"}
        </span>
      </div>
      <div className="mt-1 flex items-baseline gap-3 text-[11px] tabular text-text-secondary">
        <span>{distanceKm === null ? "—" : `${distanceKm.toFixed(2)} km`}</span>
        <span className="text-text-muted">·</span>
        <span>{durationMin === null ? "—" : `${durationMin} min`}</span>
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
  remainingMin,
  onCancel,
  onConfirm,
}: {
  generating: boolean;
  remainingMin: number | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
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
        role="dialog"
        aria-modal="true"
        aria-labelledby="reroute-title"
        aria-describedby="reroute-description"
        className="panel relative w-full max-w-md border-critical-red/40 bg-surface1 p-5 shadow-2xl"
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
          A simulated point blockage will be injected at the midpoint of the mission route. The
          backend A* planner will compute a detour. This scenario is simulated and does not command
          the rover or query an observed hazard service.
        </p>

        <dl className="mt-3 grid grid-cols-2 gap-2 rounded-control border border-line/60 bg-surface2/40 p-2.5 text-[10px]">
          <div>
            <dt className="text-[9px] uppercase tracking-[0.08em] text-text-muted">Blocked</dt>
            <dd className="mt-0.5 text-text-secondary">Midpoint point + {BLOCKAGE_BUFFER_M} m buffer</dd>
          </div>
          <div>
            <dt className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
              Remaining time
            </dt>
            <dd className="mt-0.5 tabular text-text-secondary">
              {remainingMin === null ? "unavailable" : `${remainingMin} min`}
            </dd>
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

function FitRoute({ route }: { route: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (route.length > 1) {
      map.fitBounds(L.latLngBounds(route.map(([lat, lon]) => L.latLng(lat, lon))), {
        padding: [20, 20],
        maxZoom: 9,
      });
    }
  }, [map, route]);
  return null;
}

async function planDefaultMission(): Promise<MissionPlanResponse> {
  return endpoints.missionPlan({
    region_id: REGION_ID,
    start: { x: DEFAULT_START.lon, y: DEFAULT_START.lat, crs: "urn:ogc:def:crs:IAU2000::104905" },
    destination: { x: DEFAULT_DEST.lon, y: DEFAULT_DEST.lat, crs: "urn:ogc:def:crs:IAU2000::104905" },
    time_limit_min: DEFAULT_TIME_LIMIT,
    exploration_time_min: 30,
    reserve_time_min: 30,
    route_strategy: "balanced",
  });
}

async function ensureMission(): Promise<MissionPlanResponse> {
  const stored = loadMission();
  if (stored) return stored;
  const planned = await planDefaultMission();
  saveMission(planned);
  return planned;
}

function blockedPoint(route: Route) {
  const coordinates = route.geometry?.coordinates;
  if (!coordinates || coordinates.length === 0) return null;
  const midpoint = coordinates[Math.floor(coordinates.length / 2)];
  return { type: "Point", coordinates: midpoint };
}

function asRoute(value: RerouteResponse["alternative_route"] | undefined): Route | null {
  const candidate = value as Route | undefined;
  return candidate && Array.isArray(candidate.geometry?.coordinates) ? candidate : null;
}

function routePositions(route: Route): [number, number][] {
  return route.geometry.coordinates.map(([lon, lat]) => [lat, lon] as [number, number]);
}

function groundDistanceM(
  a: { x?: number; y?: number } | undefined,
  b: { x?: number; y?: number } | undefined,
): number {
  if (
    !a ||
    !b ||
    typeof a.x !== "number" ||
    typeof a.y !== "number" ||
    typeof b.x !== "number" ||
    typeof b.y !== "number"
  ) {
    return 0;
  }
  const toRad = (value: number) => (value * Math.PI) / 180;
  const dLat = toRad(b.y - a.y);
  const dLon = toRad(b.x - a.x);
  const lat1 = toRad(a.y);
  const lat2 = toRad(b.y);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * MARS_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

function formatDelta(value: number | null | undefined, unit: string, digits: number): string {
  if (value === null || value === undefined) return "unavailable";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)} ${unit}`;
}

function deltaTone(value: number | null | undefined): "neutral" | "warning" | "safe" {
  if (value === null || value === undefined) return "neutral";
  return value > 0 ? "warning" : "safe";
}

function fmtMin(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value} min`;
}

function fmt(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
}
