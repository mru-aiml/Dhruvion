import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  Clock,
  Info,
  MapPin,
  Microscope,
  Route as RouteIcon,
  Target,
} from "lucide-react";
import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import StatCard from "../../components/common/StatCard";
import StatusPill from "../../components/common/StatusPill";
import Button, { buttonClasses } from "../../components/common/Button";
import { SimulatedLabel } from "../../components/common/StatusBadge";
import { MarsCRS, MOLA_ATTRIBUTION, MOLA_BASEMAP_URL } from "../../components/map/mars";
import { DEMO_ALERTS, DEMO_TIMELINE } from "../../data/demo";

const PHASES = ["Plan", "Traverse", "Science", "Return"];
const AVAILABILITY = [
  { label: "Basemap", value: "MOLA hillshade", tone: "observed" as const, note: "Observed" },
  { label: "Elevation", value: "MOLA MEGDR", tone: "derived" as const, note: "Derived" },
  { label: "Science", value: "Demo catalog", tone: "simulated" as const, note: "Simulated" },
  { label: "Hazards", value: "No catalogue", tone: "unavailable" as const, note: "Unavailable" },
];

export default function OverviewPage() {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Mission overview · DEMO-001"
        title="Mission Alpha-1"
        description="Gale Crater, Mars. A planning-phase traverse prototype built on NASA Mars Trek imagery, local MOLA elevation, and explicitly simulated mission context."
        meta={
          <>
            <StatusPill tone="info">Planned phase</StatusPill>
            <StatusPill tone="caution">Data partial</StatusPill>
            <StatusPill tone="simulated">Simulated context</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              <MapPin size={10} /> Gale Crater
            </StatusPill>
          </>
        }
        actions={
          <>
            <Link to="/routes" className={buttonClasses("primary", "md")}>
              <RouteIcon size={14} /> Route planner
            </Link>
            <Link to="/reports" className={buttonClasses("secondary", "md")}>
              Mission report
            </Link>
          </>
        }
      />

      <section className="panel p-4 sm:p-5">
        <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr] lg:divide-x lg:divide-line/60">
          <div className="min-w-0 lg:pr-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-micro text-mars-orange/90">Mission status</div>
                <h2 className="mt-1 font-heading text-base font-semibold">Planning phase</h2>
              </div>
              <span className="text-[10px] uppercase tracking-[0.12em] text-text-muted">
                Phase 01 / 04
              </span>
            </div>
            <p className="mt-2 max-w-xl text-xs leading-relaxed text-text-secondary">
              Traverse candidates are configured. Terrain verification remains partial, so
              route risk is reported as estimated rather than observed.
            </p>

            <ol className="mt-4 grid grid-cols-4 gap-1.5" aria-label="Mission phases">
              {PHASES.map((phase, index) => (
                <li key={phase} className="min-w-0">
                  <div
                    className={`h-1 rounded-full ${
                      index === 0 ? "bg-mars-orange" : "bg-surface3"
                    }`}
                  />
                  <div
                    className={`mt-2 truncate text-[9px] uppercase tracking-[0.1em] ${
                      index === 0 ? "text-text-primary" : "text-text-muted"
                    }`}
                  >
                    {phase}
                  </div>
                  <div className="text-[9px] uppercase tracking-[0.08em] text-text-muted/70">
                    {index === 0 ? "Current" : "Pending"}
                  </div>
                </li>
              ))}
            </ol>

            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-line/50 pt-3 text-xs sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
              {[
                ["Outbound", "45 min"],
                ["Return", "50 min"],
                ["Difficulty", "Moderate"],
                ["Objective", "Geological sampling"],
              ].map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <dt className="text-[9px] uppercase tracking-[0.1em] text-text-muted">{label}</dt>
                  <dd className="mt-0.5 truncate text-[11px] text-text-secondary">{value}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="min-w-0 lg:pl-5">
            <div className="flex items-center justify-between">
              <div className="text-micro text-mars-orange/90">Data readiness</div>
              <StatusPill tone="caution">Partial</StatusPill>
            </div>
            <ul className="mt-2 divide-y divide-line/40">
              {AVAILABILITY.map((item) => (
                <li key={item.label} className="flex items-center justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <div className="truncate text-[11px] text-text-secondary">{item.label}</div>
                    <div className="truncate text-[9px] uppercase tracking-[0.08em] text-text-muted">
                      {item.value}
                    </div>
                  </div>
                  <StatusPill tone={item.tone}>{item.note}</StatusPill>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
              Unavailable sources stay unavailable. They are never treated as safe or zero-risk.
            </p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Mission time budget"
          value={240}
          unit="min"
          icon={Clock}
          tone="orange"
          status={<StatusPill tone="simulated">Simulated</StatusPill>}
          footnote="30 min reserve included in the current plan."
        />
        <StatCard
          label="Planned traverse"
          value="3.2"
          unit="km"
          icon={RouteIcon}
          tone="info"
          status={<StatusPill tone="simulated">Simulated</StatusPill>}
          footnote="Balanced route candidate · estimated geometry."
        />
        <StatCard
          label="Science targets"
          value={3}
          icon={Microscope}
          tone="neutral"
          status={<StatusPill tone="simulated">Simulated</StatusPill>}
          footnote="Demo geology catalogue, not a verified target list."
        />
        <StatCard
          label="Identified hazards"
          value={1}
          icon={AlertTriangle}
          tone="warning"
          status={<StatusPill tone="unavailable">No overlay</StatusPill>}
          footnote="Recorded in the scenario, not an observed hazard layer."
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,1fr)]">
        <SectionCard
          eyebrow="MOLA hillshade"
          title="Terrain visualization"
          actions={
            <>
              <StatusPill tone="observed">Observed</StatusPill>
              <Link
                to="/map"
                className="inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.1em] text-mars-orange hover:underline"
              >
                Full map <ArrowRight size={12} />
              </Link>
            </>
          }
          flush
        >
          <div className="p-3 sm:p-4">
            <div className="relative h-[240px] overflow-hidden rounded-control border border-line sm:h-[320px]">
              <div aria-hidden className="pointer-events-none absolute inset-2 z-[500]">
                <span className="absolute left-0 top-0 h-4 w-4 border-l border-t border-mars-orange/70" />
                <span className="absolute right-0 top-0 h-4 w-4 border-r border-t border-mars-orange/70" />
                <span className="absolute bottom-0 left-0 h-4 w-4 border-b border-l border-mars-orange/70" />
                <span className="absolute bottom-0 right-0 h-4 w-4 border-b border-r border-mars-orange/70" />
              </div>
              <div className="pointer-events-none absolute left-3 top-3 z-[500] rounded border border-line/80 bg-black/60 px-2 py-1 backdrop-blur-sm">
                <div className="text-[9px] uppercase tracking-[0.12em] text-text-muted">
                  Gale Crater · Aeolis Mons
                </div>
                <div className="text-[10px] font-medium text-text-primary">
                  5.4°S · 137.8°E
                </div>
              </div>
              <MapContainer
                crs={MarsCRS}
                center={[-5.4, 137.8]}
                zoom={5}
                style={{ height: "100%", width: "100%", background: "#14100c" }}
                zoomControl={false}
                attributionControl={false}
                scrollWheelZoom={false}
                className="dhruvion-map"
              >
                <TileLayer
                  url={MOLA_BASEMAP_URL}
                  attribution={MOLA_ATTRIBUTION}
                  tileSize={256}
                  maxZoom={8}
                />
              </MapContainer>
              <div className="pointer-events-none absolute bottom-2 right-2 z-[500] bg-black/55 px-1.5 py-0.5 text-[8px] uppercase tracking-[0.08em] text-text-muted">
                NASA Mars Trek
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-[10px] leading-relaxed text-text-muted">
                Mars MGS MOLA color hillshade · 463 m/px global mosaic. Pan and zoom are
                available; this overview does not load analysis overlays.
              </p>
              <div className="flex flex-wrap gap-1.5">
                <StatusPill tone="observed">Basemap</StatusPill>
                <StatusPill tone="derived">Elevation</StatusPill>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Surface analysis"
          title="Terrain intelligence"
          actions={<StatusPill tone="caution">2 unavailable</StatusPill>}
        >
          <div className="space-y-4">
            <TerrainRow
              label="Slope"
              value="Unavailable"
              state="unavailable"
              description="No verified slope raster connected."
            />
            <TerrainRow
              label="Roughness"
              value="Unavailable"
              state="unavailable"
              description="Derived layer exists, but analysis is not loaded here."
            />
            <TerrainRow
              label="Elevation change"
              value="320 m"
              state="simulated"
              bar={60}
              description="Scenario estimate across the planned traverse."
            />
            <TerrainRow
              label="Nearby hazards"
              value="1 identified"
              state="simulated"
              bar={25}
              description="Recorded obstruction in the demo scenario."
            />
          </div>
          <div className="mt-4 border-t border-line/50 pt-3">
            <div className="flex flex-wrap items-center gap-2">
              <SimulatedLabel />
              <StatusPill tone="neutral">Partial coverage</StatusPill>
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
              Missing terrain values are displayed as unavailable, never converted into a
              low-risk score.
            </p>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard
          eyebrow="Attention"
          title="Mission alerts"
          actions={<StatusPill tone="caution">2 open</StatusPill>}
        >
          <div className="space-y-2">
            {DEMO_ALERTS.map((alert) => {
              const caution = alert.severity === "Caution";
              return (
                <div
                  key={`${alert.time}-${alert.message}`}
                  className={`flex items-start gap-2.5 rounded-control border p-2.5 ${
                    caution
                      ? "border-warning-amber/35 bg-warning-amber/[0.06]"
                      : "border-cyan/25 bg-cyan/[0.04]"
                  }`}
                >
                  {caution ? (
                    <AlertTriangle
                      size={14}
                      className="mt-0.5 shrink-0 text-warning-amber"
                      aria-hidden
                    />
                  ) : (
                    <Info size={14} className="mt-0.5 shrink-0 text-cyan" aria-hidden />
                  )}
                  <div className="min-w-0">
                    <div className="text-[11px] leading-snug text-text-primary">
                      {alert.message}
                    </div>
                    <div className="mt-1 text-[9px] uppercase tracking-[0.1em] text-text-muted">
                      {alert.time} · {alert.severity}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Mission log"
          title="Activity timeline"
          actions={<Activity size={14} className="text-text-muted" aria-hidden />}
        >
          <ol className="relative ml-1.5 border-l border-line/70">
            {DEMO_TIMELINE.map((item) => (
              <li key={`${item.time}-${item.event}`} className="relative pb-3 pl-4 last:pb-0">
                <span
                  aria-hidden
                  className={`absolute -left-[4.5px] top-1 h-2 w-2 rounded-full border-2 border-surface1 ${
                    item.status === "completed"
                      ? "bg-safe-green"
                      : item.status === "in progress"
                        ? "bg-warning-amber"
                        : "bg-surface3"
                  }`}
                />
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[11px] leading-snug text-text-primary">{item.event}</span>
                  <span className="shrink-0 text-[9px] tabular text-text-muted">{item.time}</span>
                </div>
                <div className="mt-0.5 text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  {item.category} · {item.status}
                </div>
              </li>
            ))}
          </ol>
        </SectionCard>

        <SectionCard
          eyebrow="Decision support"
          title="AI mission briefing"
          actions={<Bot size={14} className="text-cyan" aria-hidden />}
        >
          <div className="space-y-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-secondary">
                Recommendation
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-text-secondary">
                A balanced route to Mount Sharp Outcrop is estimated feasible within the
                240 min budget under configured assumptions.
              </p>
            </div>
            <div className="border-t border-line/50 pt-2">
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-secondary">
                Risk assessment
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-text-secondary">
                Terrain risk is <span className="text-warning-amber">unverified</span> — no
                verified slope source is loaded. Do not treat it as safe.
              </p>
            </div>
            <div className="border-t border-line/50 pt-2">
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-secondary">
                Availability
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
                Elevation: derived · slope and roughness: unavailable · science targets:
                simulated.
              </p>
            </div>
            <Link
              to="/assistant"
              className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.1em] text-mars-orange hover:underline"
            >
              Open assistant <ArrowRight size={12} />
            </Link>
          </div>
        </SectionCard>
      </div>

      <SectionCard
        eyebrow="Science priority"
        title="Recommended exploration target"
        actions={<StatusPill tone="simulated">Simulated catalogue</StatusPill>}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-control border border-mars-orange/35 bg-mars-orange/10 text-mars-orange">
              <Target size={18} aria-hidden />
            </span>
            <div className="min-w-0">
              <div className="font-heading text-sm font-semibold text-text-primary">
                Mount Sharp Outcrop
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-secondary">
                <span>Sedimentary outcrop</span>
                <span className="text-text-muted">·</span>
                <span className="tabular">1.2 km from traverse</span>
                <span className="text-text-muted">·</span>
                <span className="tabular">5.38°S, 137.42°E</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                  Priority
                </span>
                <span className="h-1.5 w-28 overflow-hidden rounded-full bg-surface3">
                  <span className="block h-full w-[90%] rounded-full bg-mars-orange" />
                </span>
                <span className="text-[10px] tabular text-text-secondary">0.90</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link to="/science" className={buttonClasses("primary", "md")}>
              Inspect target <ArrowRight size={13} />
            </Link>
            <Button variant="ghost" size="md" disabled title="Target actions require a verified science API">
              Add to mission
            </Button>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}

function TerrainRow({
  label,
  value,
  state,
  description,
  bar,
}: {
  label: string;
  value: string;
  state: "available" | "partial" | "unavailable" | "simulated";
  description: string;
  bar?: number;
}) {
  const barColor =
    state === "unavailable"
      ? "bg-surface3"
      : state === "simulated"
        ? "bg-amber"
        : state === "partial"
          ? "bg-warning-amber"
          : "bg-safe-green";
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] text-text-secondary">{label}</span>
        <span
          className={`text-[9px] font-medium uppercase tracking-[0.1em] ${
            state === "unavailable" ? "text-text-muted" : "text-text-secondary"
          }`}
        >
          {value} · {state}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface3">
        <div
          className={`h-full rounded-full ${barColor}`}
          style={{ width: `${bar ?? (state === "unavailable" ? 6 : 50)}%` }}
        />
      </div>
      <p className="mt-1 text-[10px] leading-relaxed text-text-muted">{description}</p>
    </div>
  );
}
