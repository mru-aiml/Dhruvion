import { useState } from "react";
import { Check, Clock, Gauge, MapPin, Play, RotateCcw, Route as RouteIcon } from "lucide-react";
import { MapContainer, Polyline, TileLayer } from "react-leaflet";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import Button from "../../components/common/Button";
import StatusPill from "../../components/common/StatusPill";
import { ErrorState } from "../../components/common/States";
import { TextInput } from "../../components/common/Field";
import { FeasibilityBadge, ProvenanceBadge, SimulatedLabel } from "../../components/common/StatusBadge";
import { MarsCRS, MOLA_ATTRIBUTION, MOLA_BASEMAP_URL } from "../../components/map/mars";
import { endpoints } from "../../services/api/endpoints";
import { apiErrorMessage } from "../../services/api/client";
import type { FeasibilityStatus, RouteStrategy } from "../../types";

interface RouteCardData {
  id: string;
  strategy: RouteStrategy;
  name: string;
  distance_m: number;
  duration_min: number;
  difficulty: number;
  hazards: number;
  feasibility: FeasibilityStatus;
  rationale: string;
  geometry: [number, number][];
}

const SHORT_ROUTE: [number, number][] = [
  [-5.45, 137.35],
  [-5.43, 137.37],
  [-5.41, 137.39],
  [-5.39, 137.41],
  [-5.38, 137.42],
];
const SAFE_ROUTE: [number, number][] = [
  [-5.45, 137.35],
  [-5.46, 137.36],
  [-5.44, 137.39],
  [-5.40, 137.41],
  [-5.38, 137.42],
];
const BALANCED_ROUTE: [number, number][] = [
  [-5.45, 137.35],
  [-5.44, 137.37],
  [-5.42, 137.39],
  [-5.40, 137.41],
  [-5.38, 137.42],
];

const BASELINE_ROUTES: RouteCardData[] = [
  {
    id: "r-short",
    strategy: "shortest",
    name: "Shortest Route",
    distance_m: 2850,
    duration_min: 38,
    difficulty: 6.2,
    hazards: 2,
    feasibility: "caution",
    rationale: "Minimizes geometric distance; crosses two moderate-slope segments.",
    geometry: SHORT_ROUTE,
  },
  {
    id: "r-safe",
    strategy: "safest_estimated",
    name: "Safest Route",
    distance_m: 3420,
    duration_min: 46,
    difficulty: 3.1,
    hazards: 0,
    feasibility: "feasible",
    rationale: "Avoids identified hazard zones; longer traverse.",
    geometry: SAFE_ROUTE,
  },
  {
    id: "r-bal",
    strategy: "balanced",
    name: "Balanced Route",
    distance_m: 3050,
    duration_min: 41,
    difficulty: 4.0,
    hazards: 1,
    feasibility: "feasible",
    rationale: "Trade-off between distance and terrain penalty.",
    geometry: BALANCED_ROUTE,
  },
];

const ELEVATION_PROFILE = [
  { d: 0, elev: 0 },
  { d: 0.5, elev: 40 },
  { d: 1.0, elev: 90 },
  { d: 1.5, elev: 60 },
  { d: 2.0, elev: 120 },
  { d: 2.5, elev: 80 },
  { d: 3.0, elev: 150 },
  { d: 3.2, elev: 110 },
];

export default function RoutePlannerPage() {
  const [selected, setSelected] = useState<string>("r-bal");
  const [timeLimit, setTimeLimit] = useState(240);
  const [calculating, setCalculating] = useState(false);
  const [startLat, setStartLat] = useState(-5.45);
  const [startLon, setStartLon] = useState(137.35);
  const [destLat, setDestLat] = useState(-5.38);
  const [destLon, setDestLon] = useState(137.42);
  const [routes, setRoutes] = useState<RouteCardData[]>(BASELINE_ROUTES);
  const [routeError, setRouteError] = useState<string | null>(null);

  const selectedCard = routes.find((route) => route.id === selected) ?? routes[0];

  const handleCalculate = async () => {
    setCalculating(true);
    setRouteError(null);
    try {
      const response = await endpoints.routeOptimize({
        region_id: "gale_crater",
        start: { x: startLon, y: startLat, crs: "urn:ogc:def:crs:IAU2000::104905" },
        destination: { x: destLon, y: destLat, crs: "urn:ogc:def:crs:IAU2000::104905" },
        strategies: ["shortest", "safest_estimated", "balanced"],
      });
      if (response.routes && response.routes.length) {
        const mapped: RouteCardData[] = response.routes.map((route) => ({
          id: route.id,
          strategy: route.strategy,
          name:
            route.strategy === "shortest"
              ? "Shortest Route"
              : route.strategy === "safest_estimated"
                ? "Safest Route"
                : "Balanced Route",
          distance_m: route.distance_m,
          duration_min: route.estimated_duration_min ?? 0,
          difficulty: route.terrain_difficulty ?? 0,
          hazards: route.hazard_count ?? 0,
          feasibility: route.feasibility_status,
          rationale: route.rationale,
          // Backend route geometry follows GeoJSON [lon, lat]; Leaflet needs [lat, lon].
          geometry: route.geometry.coordinates.map(
            ([lon, lat]) => [lat, lon] as [number, number],
          ),
        }));
        setRoutes(mapped);
        setSelected(mapped[0].id);
      } else {
        setRouteError("No route returned. The coordinates may fall outside MOLA coverage.");
      }
    } catch (reason) {
      setRouteError(apiErrorMessage(reason));
    } finally {
      setCalculating(false);
    }
  };

  const resetScenario = () => {
    setRoutes(BASELINE_ROUTES);
    setSelected("r-bal");
    setRouteError(null);
    setStartLat(-5.45);
    setStartLon(137.35);
    setDestLat(-5.38);
    setDestLon(137.42);
    setTimeLimit(240);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Traverse workspace"
        title="Route Planner"
        description="Compare shortest, lowest-estimated-risk, and balanced traverse candidates. Baseline geometries are simulated; calculated routes use the processed MOLA raster when coordinates fall inside coverage."
        meta={
          <>
            <SimulatedLabel />
            <StatusPill tone="derived">MOLA-derived distance</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              A* · prototype cost model
            </StatusPill>
          </>
        }
        actions={
          <Button variant="secondary" size="md" icon={<RotateCcw size={14} />} onClick={resetScenario}>
            Reset scenario
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_308px]">
        <SectionCard
          eyebrow="Route map"
          title="Traverse candidates"
          actions={
            selectedCard && (
              <StatusPill tone={feasibilityTone(selectedCard.feasibility)}>
                {selectedCard.name} selected
              </StatusPill>
            )
          }
          flush
        >
          <div className="relative h-[320px] sm:h-[400px] xl:h-[440px]">
            <MapContainer
              crs={MarsCRS}
              center={[-5.4, 137.4]}
              zoom={6}
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
              {routes.map((route) => (
                <Polyline
                  key={route.id}
                  positions={route.geometry}
                  pathOptions={
                    route.id === selectedCard?.id
                      ? { color: "#F06B3D", weight: 3.5, opacity: 1 }
                      : { color: "#9AA5B1", weight: 1.5, opacity: 0.55 }
                  }
                />
              ))}
            </MapContainer>
            <div className="pointer-events-none absolute left-3 top-3 rounded border border-line/80 bg-black/65 px-2 py-1 backdrop-blur-sm">
              <div className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                Gale Crater · prototype CRS
              </div>
              <div className="text-[10px] text-text-primary">
                {routes.length} candidate{routes.length === 1 ? "" : "s"} ·{" "}
                {selectedCard ? `${(selectedCard.distance_m / 1000).toFixed(2)} km` : "no selection"}
              </div>
            </div>
            <div className="pointer-events-none absolute bottom-6 left-3 flex flex-wrap gap-2 rounded border border-line/70 bg-black/60 px-2 py-1 text-[9px] uppercase tracking-[0.08em] backdrop-blur-sm">
              <span className="flex items-center gap-1.5 text-text-secondary">
                <span className="h-0.5 w-4 bg-mars-orange" /> Selected
              </span>
              <span className="flex items-center gap-1.5 text-text-muted">
                <span className="h-0.5 w-4 bg-[#9AA5B1]" /> Other candidate
              </span>
            </div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Inputs" title="Route configuration" bodyClassName="p-4">
          <div className="space-y-3.5">
            <div>
              <div className="mb-1.5 flex items-center gap-1.5 text-micro text-text-muted">
                <MapPin size={11} /> Start
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  Latitude
                  <TextInput
                    type="number"
                    step="0.01"
                    value={startLat}
                    onChange={(event) => setStartLat(Number(event.target.value))}
                    className="mt-1"
                    aria-label="Start latitude"
                  />
                </label>
                <label className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  Longitude
                  <TextInput
                    type="number"
                    step="0.01"
                    value={startLon}
                    onChange={(event) => setStartLon(Number(event.target.value))}
                    className="mt-1"
                    aria-label="Start longitude"
                  />
                </label>
              </div>
            </div>

            <div>
              <div className="mb-1.5 flex items-center gap-1.5 text-micro text-text-muted">
                <MapPin size={11} /> Destination
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  Latitude
                  <TextInput
                    type="number"
                    step="0.01"
                    value={destLat}
                    onChange={(event) => setDestLat(Number(event.target.value))}
                    className="mt-1"
                    aria-label="Destination latitude"
                  />
                </label>
                <label className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  Longitude
                  <TextInput
                    type="number"
                    step="0.01"
                    value={destLon}
                    onChange={(event) => setDestLon(Number(event.target.value))}
                    className="mt-1"
                    aria-label="Destination longitude"
                  />
                </label>
              </div>
            </div>

            <label className="block text-[9px] uppercase tracking-[0.08em] text-text-muted">
              Mission time limit (min)
              <TextInput
                type="number"
                min={1}
                value={timeLimit}
                onChange={(event) => setTimeLimit(Number(event.target.value))}
                className="mt-1"
              />
            </label>

            <Button
              variant="primary"
              size="lg"
              className="w-full"
              icon={<Play size={14} />}
              loading={calculating}
              onClick={handleCalculate}
            >
              {calculating ? "Calculating routes" : "Calculate routes"}
            </Button>

            {routeError && <ErrorState message={routeError} compact />}

            <p className="text-[10px] leading-relaxed text-text-muted">
              Routes are computed from the processed MOLA elevation and slope rasters. Points
              outside the processed Gale Crater window return no route.
            </p>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {routes.map((route) => {
          const active = route.id === selectedCard?.id;
          return (
            <button
              key={route.id}
              type="button"
              aria-pressed={active}
              onClick={() => setSelected(route.id)}
              className={`group relative min-w-0 overflow-hidden border p-4 text-left transition-colors duration-150 ${
                active
                  ? "border-mars-orange bg-mars-orange/[0.055]"
                  : "border-line bg-surface1 hover:border-amber/50 hover:bg-surface2"
              }`}
            >
              {active && <span aria-hidden className="absolute inset-x-0 top-0 h-0.5 bg-mars-orange" />}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                    {route.strategy.replace(/_/g, " ")}
                  </div>
                  <div className="mt-0.5 font-heading text-sm font-semibold text-text-primary">
                    {route.name}
                  </div>
                </div>
                {active ? (
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full border border-mars-orange/50 bg-mars-orange/15 text-mars-orange">
                    <Check size={11} />
                  </span>
                ) : (
                  <RouteIcon size={15} className="mt-0.5 shrink-0 text-text-muted" aria-hidden />
                )}
              </div>

              <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 border-t border-line/50 pt-3">
                <RouteMetric label="Distance" value={`${(route.distance_m / 1000).toFixed(2)} km`} />
                <RouteMetric label="Duration" value={`${route.duration_min} min`} />
                <RouteMetric label="Difficulty" value={route.difficulty.toFixed(1)} />
                <RouteMetric label="Hazards" value={String(route.hazards)} />
              </dl>

              <div className="mt-3 flex items-center justify-between gap-2">
                <FeasibilityBadge status={route.feasibility} />
                <span className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                  {active ? "Selected" : "Select"}
                </span>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-text-muted">{route.rationale}</p>
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard
          eyebrow="Time budget"
          title="Feasibility summary"
          actions={selectedCard && <FeasibilityBadge status={selectedCard.feasibility} />}
        >
          {selectedCard ? (
            <>
              <div className="grid grid-cols-3 gap-2">
                <MiniMetric label="Outbound" value={`${selectedCard.duration_min}`} unit="min" icon={Clock} />
                <MiniMetric label="Exploration" value="30" unit="min" icon={MapPin} />
                <MiniMetric label="Return" value={`${selectedCard.duration_min + 5}`} unit="min" icon={Clock} />
                <MiniMetric label="Reserve" value="30" unit="min" icon={Gauge} />
                <MiniMetric
                  label="Total"
                  value={`${selectedCard.duration_min * 2 + 65}`}
                  unit="min"
                  icon={RouteIcon}
                  emphasis
                />
                <MiniMetric label="Limit" value={`${timeLimit}`} unit="min" icon={Gauge} />
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line/50 pt-3">
                <SimulatedLabel />
                <ProvenanceBadge status="simulated" />
                <StatusPill tone="neutral" dot={false}>
                  Estimated, not certified
                </StatusPill>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
                T_total = T_outbound + T_exploration + T_return + T_reserve. A missing return
                route yields UNVERIFIED.
              </p>
            </>
          ) : (
            <p className="text-xs text-text-muted">Calculate a route to see the time budget.</p>
          )}
        </SectionCard>

        <SectionCard
          eyebrow="Terrain profile"
          title="Elevation profile"
          actions={<StatusPill tone="simulated">Simulated</StatusPill>}
        >
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={ELEVATION_PROFILE} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#624536" strokeOpacity={0.18} vertical={false} />
                <XAxis
                  dataKey="d"
                  tick={{ fill: "#786C65", fontSize: 9 }}
                  tickLine={false}
                  axisLine={{ stroke: "#624536", strokeOpacity: 0.4 }}
                  unit=" km"
                />
                <YAxis
                  tick={{ fill: "#786C65", fontSize: 9 }}
                  tickLine={false}
                  axisLine={false}
                  unit=" m"
                />
                <Tooltip
                  contentStyle={{
                    background: "#171411",
                    border: "1px solid #624536",
                    borderRadius: 4,
                    fontSize: 11,
                    color: "#F3F0EC",
                  }}
                  labelStyle={{ color: "#B1A39A" }}
                  formatter={(value) => [`${value} m`, "Elevation"]}
                />
                <Line
                  type="monotone"
                  dataKey="elev"
                  stroke="#F06B3D"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 3, fill: "#F06B3D" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
            Illustrative profile, not sampled from a verified route raster.
          </p>
        </SectionCard>
      </div>
    </div>
  );
}

function feasibilityTone(status: FeasibilityStatus) {
  if (status === "feasible") return "feasible" as const;
  if (status === "caution") return "caution" as const;
  if (status === "not_feasible") return "critical" as const;
  return "neutral" as const;
}

function RouteMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[8px] uppercase tracking-[0.1em] text-text-muted">{label}</dt>
      <dd className="mt-0.5 truncate text-[11px] tabular text-text-primary">{value}</dd>
    </div>
  );
}

function MiniMetric({
  label,
  value,
  unit,
  icon: Icon,
  emphasis,
}: {
  label: string;
  value: string;
  unit: string;
  icon: typeof Clock;
  emphasis?: boolean;
}) {
  return (
    <div
      className={`min-w-0 rounded-control border px-2.5 py-2 ${
        emphasis ? "border-mars-orange/40 bg-mars-orange/[0.06]" : "border-line/60 bg-surface2/40"
      }`}
    >
      <div className="flex items-center gap-1 text-[8px] uppercase tracking-[0.09em] text-text-muted">
        <Icon size={10} aria-hidden /> {label}
      </div>
      <div className="mt-1 truncate text-sm font-semibold tabular text-text-primary">
        {value} <span className="text-[9px] font-normal text-text-muted">{unit}</span>
      </div>
    </div>
  );
}
