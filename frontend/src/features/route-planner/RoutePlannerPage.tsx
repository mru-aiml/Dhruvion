import { useCallback, useEffect, useState } from "react";
import { Check, Clock, Gauge, Loader2, MapPin, Play, RotateCcw, Route as RouteIcon } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import Button from "../../components/common/Button";
import StatusPill from "../../components/common/StatusPill";
import { ErrorState } from "../../components/common/States";
import { TextInput } from "../../components/common/Field";
import { FeasibilityBadge, ProvenanceBadge } from "../../components/common/StatusBadge";
import { LAYER_TILE_URLS, MOLA_ATTRIBUTION, MOLA_BASEMAP_URL, API_ORIGIN } from "../../components/map/mars";
import { MarsMap } from "../../components/map/MarsMap";
import { endpoints } from "../../services/api/endpoints";
import { apiErrorMessage } from "../../services/api/client";
import { clearMission, saveMission } from "../../services/missionStore";
import type {
  FeasibilityStatus,
  MissionPlanResponse,
  Route,
  RouteStrategy,
  TerrainProfileResponse,
} from "../../types";

const REGION_ID = "gale_crater";
const DEFAULT_START = { lat: -4.5, lon: 137.2 };
const DEFAULT_DEST = { lat: -4.55, lon: 137.3 };
const DEFAULT_TIME_LIMIT = 600;

const STRATEGY_LABEL: Record<RouteStrategy, string> = {
  shortest: "Shortest Route",
  safest_estimated: "Safest Route",
  balanced: "Balanced Route",
};

export default function RoutePlannerPage() {
  const [selected, setSelected] = useState<string>("");
  const [timeLimit, setTimeLimit] = useState(DEFAULT_TIME_LIMIT);
  const [calculating, setCalculating] = useState(false);
  const [missionLoading, setMissionLoading] = useState(false);
  const [startLat, setStartLat] = useState(DEFAULT_START.lat);
  const [startLon, setStartLon] = useState(DEFAULT_START.lon);
  const [destLat, setDestLat] = useState(DEFAULT_DEST.lat);
  const [destLon, setDestLon] = useState(DEFAULT_DEST.lon);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [mission, setMission] = useState<MissionPlanResponse | null>(null);
  const [profile, setProfile] = useState<TerrainProfileResponse | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [basemap, setBasemap] = useState("mars_trek_mola_colorshade");
  const [selectMode, setSelectMode] = useState<"start" | "destination" | null>(null);
  const [pointer, setPointer] = useState<{ lat: number; lon: number } | null>(null);
  const [missions, setMissions] = useState<{ id: string; name: string }[]>([]);
  const [saveMissionId, setSaveMissionId] = useState("");
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const selectedRoute = routes.find((route) => route.id === selected) ?? routes[0] ?? null;

  useEffect(() => {
    endpoints
      .missions()
      .then((data) => setMissions(data.map((mission) => ({ id: mission.id, name: mission.name }))))
      .catch(() => setMissions([]));
  }, []);

  const calculate = useCallback(
    async (start = startLon, startY = startLat, end = destLon, endY = destLat, limit = timeLimit) => {
      setCalculating(true);
      setRouteError(null);
      setBudgetError(null);
      try {
        const body = {
          region_id: REGION_ID,
          start: { x: start, y: startY, crs: "urn:ogc:def:crs:IAU2000::104905" },
          destination: { x: end, y: endY, crs: "urn:ogc:def:crs:IAU2000::104905" },
          strategies: ["shortest", "safest_estimated", "balanced"],
        };
        const [routesResult, missionResult] = await Promise.allSettled([
          endpoints.routeOptimize(body),
          endpoints.missionPlan({
            region_id: REGION_ID,
            start: body.start,
            destination: body.destination,
            time_limit_min: limit,
            exploration_time_min: 30,
            reserve_time_min: 30,
            route_strategy: "balanced",
          }),
        ]);

        if (routesResult.status === "rejected") {
          throw routesResult.reason;
        }
        const nextRoutes = routesResult.value.routes ?? [];
        if (!nextRoutes.length) {
          setRoutes([]);
          setSelected("");
          setRouteError("No route returned. The coordinates may fall outside MOLA coverage.");
          return;
        }
        setRoutes(nextRoutes);
        setSelected((current) =>
          nextRoutes.some((route) => route.id === current) ? current : nextRoutes[0].id,
        );

        if (missionResult.status === "fulfilled") {
          setMission(missionResult.value);
          saveMission(missionResult.value);
        } else {
          setMission(null);
          clearMission();
          setBudgetError(apiErrorMessage(missionResult.reason));
        }
      } catch (reason) {
        setRoutes([]);
        setSelected("");
        setMission(null);
        setProfile(null);
        setRouteError(apiErrorMessage(reason));
      } finally {
        setCalculating(false);
      }
    },
    [startLon, startLat, destLon, destLat, timeLimit],
  );

  // Compute real routes for the default in-coverage scenario on first load.
  useEffect(() => {
    void calculate(DEFAULT_START.lon, DEFAULT_START.lat, DEFAULT_DEST.lon, DEFAULT_DEST.lat, DEFAULT_TIME_LIMIT);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedRoute) {
      setProfile(null);
      return;
    }
    const start = selectedRoute.start ?? { x: startLon, y: startLat };
    const end = selectedRoute.destination ?? { x: destLon, y: destLat };
    let active = true;
    setProfileLoading(true);
    endpoints
      .terrainProfile(REGION_ID, { x: start.x, y: start.y }, { x: end.x, y: end.y }, 48)
      .then((response) => active && setProfile(response))
      .catch(() => active && setProfile(null))
      .finally(() => active && setProfileLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRoute?.id]);

  const selectRoute = async (route: Route) => {
    setSelected(route.id);
    if (!mission) return;
    setMissionLoading(true);
    setBudgetError(null);
    try {
      const nextMission = await endpoints.missionPlan({
        region_id: REGION_ID,
        start: route.start ?? { x: startLon, y: startLat, crs: mission.route.start?.crs },
        destination: route.destination ?? { x: destLon, y: destLat, crs: mission.route.destination?.crs },
        time_limit_min: timeLimit,
        exploration_time_min: mission.time_budget.exploration_min ?? 30,
        reserve_time_min: mission.time_budget.reserve_min ?? 30,
        route_strategy: route.strategy,
      });
      setMission(nextMission);
      saveMission(nextMission);
    } catch (reason) {
      setBudgetError(apiErrorMessage(reason));
    } finally {
      setMissionLoading(false);
    }
  };

  const resetScenario = () => {
    setStartLat(DEFAULT_START.lat);
    setStartLon(DEFAULT_START.lon);
    setDestLat(DEFAULT_DEST.lat);
    setDestLon(DEFAULT_DEST.lon);
    setTimeLimit(DEFAULT_TIME_LIMIT);
    void calculate(DEFAULT_START.lon, DEFAULT_START.lat, DEFAULT_DEST.lon, DEFAULT_DEST.lat, DEFAULT_TIME_LIMIT);
  };

  const profileData = (profile?.points ?? [])
    .filter((point) => point.values.elevation_m !== null)
    .map((point) => ({
      distance_km: Number((point.distance_m / 1000).toFixed(2)),
      elevation_m: point.values.elevation_m,
      slope_deg: point.values.slope_deg,
    }));

  // Build markers for start and destination
  const startMarker = {
    id: "start",
    position: [startLat, startLon] as [number, number],
    icon: L.divIcon({
      className: "dhruvion-marker-start",
      html: '<span style="display:block;width:14px;height:14px;border-radius:50%;background:#F06B3D;border:2px solid #fff;"></span>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    }),
    draggable: true,
    onDragEnd: (lat: number, lng: number) => {
      setStartLat(lat);
      setStartLon(lng);
    },
    title: "Start point (draggable)",
  };

  const destMarker = {
    id: "destination",
    position: [destLat, destLon] as [number, number],
    icon: L.divIcon({
      className: "dhruvion-marker-dest",
      html: '<span style="display:block;width:14px;height:14px;border-radius:50%;background:#38bdf8;border:2px solid #fff;"></span>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    }),
    draggable: true,
    onDragEnd: (lat: number, lng: number) => {
      setDestLat(lat);
      setDestLon(lng);
    },
    title: "Destination point (draggable)",
  };

  // Build polylines for routes
  const routePolylines = routes.map((route) => ({
    id: route.id,
    positions: route.geometry.coordinates.map(([lon, lat]) => [lat, lon] as [number, number]),
    color: route.id === selectedRoute?.id ? "#F06B3D" : "#9AA5B1",
    weight: route.id === selectedRoute?.id ? 3.5 : 1.5,
    opacity: route.id === selectedRoute?.id ? 1 : 0.55,
    visible: true,
  }));

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Traverse workspace"
        title="Route Planner"
        description="A* traverse candidates computed on the processed 463 m MOLA coverage grid. Elevation is observed; slope, roughness, distance, duration and difficulty are derived under documented planning assumptions."
        meta={
          <>
            <StatusPill tone="observed">Observed elevation</StatusPill>
            <StatusPill tone="derived">Derived terrain cost</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              A* · coverage-aware
            </StatusPill>
          </>
        }
        actions={
          <Button variant="secondary" size="md" icon={<RotateCcw size={14} />} onClick={resetScenario}>
            Reset scenario
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <label className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
          Basemap
          <select
            className="ml-2 rounded-control border border-line bg-surface1 px-2 py-1 text-xs text-text-primary"
            value={basemap}
            onChange={(event) => setBasemap(event.target.value)}
          >
            <option value="mars_trek_mola_colorshade">Mars colour hillshade</option>
            <option value="mars_mola_hrsc_blend">MOLA+HRSC blend</option>
            <option value="mola_roughness">MOLA roughness</option>
            <option value="gale_ctx">Gale CTX</option>
            <option value="viking_mdim">Viking MDIM</option>
          </select>
        </label>
        <Button variant={selectMode === "start" ? "primary" : "secondary"} size="sm" onClick={() => setSelectMode("start")}>
          Set start
        </Button>
        <Button variant={selectMode === "destination" ? "primary" : "secondary"} size="sm" onClick={() => setSelectMode("destination")}>
          Set destination
        </Button>
        {pointer && (
          <span className="text-[10px] text-text-muted">
            {pointer.lat.toFixed(4)}, {pointer.lon.toFixed(4)}
          </span>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_308px]">
        <SectionCard
          eyebrow="Route map"
          title="Traverse candidates"
          actions={
            selectedRoute && (
              <StatusPill tone={feasibilityTone(selectedRoute.feasibility_status)}>
                {STRATEGY_LABEL[selectedRoute.strategy] ?? selectedRoute.strategy} selected
              </StatusPill>
            )
          }
          flush
        >
          <div className="relative h-[320px] sm:h-[400px] xl:h-[440px]">
            <MarsMap
              center={[-5.4, 137.4]}
              zoom={6}
              minZoom={0}
              maxZoom={8}
              scrollWheelZoom={false}
              zoomControl={false}
              attributionControl={true}
              containerHeight="100%"
              proxyBaseUrl={API_ORIGIN}
              tileLayers={[
                {
                  id: basemap,
                  url: LAYER_TILE_URLS[basemap] ?? MOLA_BASEMAP_URL,
                  attribution: MOLA_ATTRIBUTION,
                  maxZoom: 8,
                  tileSize: 256,
                  visible: true,
                  // Use backend proxy for all NASA Trek layers to avoid CORS issues
                  useProxy: LAYER_TILE_URLS[basemap]?.includes("trek.nasa.gov"),
                  proxyLayerId: basemap,
                },
              ]}
              onMapReady={() => {
                if (import.meta.env.DEV) {
                  console.log('[RoutePlannerPage] Map ready, basemap:', basemap);
                  console.log('[RoutePlannerPage] API_ORIGIN:', API_ORIGIN);
                }
              }}
              markers={[
                startMarker,
                destMarker,
              ]}
              polylines={routePolylines}
              onMapClick={(lat, lon) => {
                if (selectMode === "start") {
                  setStartLat(lat);
                  setStartLon(lon);
                  setSelectMode(null);
                } else if (selectMode === "destination") {
                  setDestLat(lat);
                  setDestLon(lon);
                  setSelectMode(null);
                }
              }}
              onPointerMove={(lat, lon) => setPointer({ lat, lon })}
              fitBounds={routes.length > 0 ? routes.flatMap((r) => r.geometry.coordinates.map(([lon, lat]) => [lat, lon] as [number, number])) : null}
              fitBoundsTrigger={routes.length > 0 ? (selectedRoute?.id.split("").reduce((a, c) => a + c.charCodeAt(0), 0) ?? 0) : 0}
            />
            <div className="pointer-events-none absolute left-3 top-3 rounded border border-line/80 bg-black/65 px-2 py-1 backdrop-blur-sm">
              <div className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                Gale Crater · Mars equirectangular
              </div>
              <div className="text-[10px] text-text-primary">
                {routes.length} candidate{routes.length === 1 ? "" : "s"} ·{" "}
                {selectedRoute ? `${(selectedRoute.distance_m / 1000).toFixed(2)} km` : "no selection"}
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
                <MapPin size={11} /> Start (planetocentric)
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
              onClick={() => calculate()}
            >
              {calculating ? "Calculating routes" : "Calculate routes"}
            </Button>

            {routeError && <ErrorState message={routeError} compact />}

            <p className="text-[10px] leading-relaxed text-text-muted">
              Routes are computed on the processed MOLA grid. Points outside the Gale Crater
              window return no route; class 2 cells are crossed only with an explicit uncertainty
              penalty, never as zero risk.
            </p>
          </div>
        </SectionCard>
      </div>

      {routes.length === 0 && !calculating && (
        <SectionCard eyebrow="Traverse candidates" title="No candidates yet">
          <p className="text-xs text-text-secondary">
            Enter coordinates inside the processed Gale Crater window and calculate routes.
          </p>
        </SectionCard>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        {routes.map((route) => {
          const active = route.id === selectedRoute?.id;
          return (
            <button
              key={route.id}
              type="button"
              aria-pressed={active}
              onClick={() => void selectRoute(route)}
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
                    {STRATEGY_LABEL[route.strategy] ?? route.strategy}
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
                <RouteMetric
                  label="Duration"
                  value={route.estimated_duration_min === null ? "—" : `${route.estimated_duration_min} min`}
                />
                <RouteMetric
                  label="Difficulty"
                  value={route.terrain_difficulty === null ? "—" : route.terrain_difficulty.toFixed(2)}
                />
                <RouteMetric
                  label="Max slope"
                  value={
                    route.metrics?.max_slope_deg === null || route.metrics?.max_slope_deg === undefined
                      ? "—"
                      : `${route.metrics.max_slope_deg}°`
                  }
                />
              </dl>

              <div className="mt-3 flex items-center justify-between gap-2">
                <FeasibilityBadge status={route.feasibility_status} />
                <span className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                  {active ? "Selected" : "Select"}
                </span>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-text-muted">{route.rationale}</p>
            </button>
          );
        })}
      </div>

      <SectionCard eyebrow="Mission" title="Save route to mission">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded-control border border-line bg-surface1 px-3 py-2 text-sm text-text-primary"
            value={saveMissionId}
            onChange={(event) => setSaveMissionId(event.target.value)}
          >
            <option value="">Select mission</option>
            {missions.map((mission) => (
              <option key={mission.id} value={mission.id}>
                {mission.name}
              </option>
            ))}
          </select>
          <Button
            variant="primary"
            disabled={!saveMissionId || !selectedRoute}
            onClick={async () => {
              if (!saveMissionId || !selectedRoute) return;
              try {
                await endpoints.missionRouteCreate(saveMissionId, {
                  strategy: selectedRoute.strategy,
                  geometry: selectedRoute.geometry.coordinates,
                  distance_m: selectedRoute.distance_m,
                  estimated_duration_min: selectedRoute.estimated_duration_min,
                  terrain_difficulty: selectedRoute.terrain_difficulty,
                  max_slope_deg: selectedRoute.metrics?.max_slope_deg ?? null,
                  feasibility: selectedRoute.feasibility_status,
                  parameters: { time_limit_min: timeLimit },
                });
                setSaveStatus("Route saved to mission.");
              } catch (reason) {
                setSaveStatus(reason instanceof Error ? reason.message : "Failed to save route");
              }
            }}
          >
            Save to Mission
          </Button>
          {saveStatus && <span className="text-xs text-text-secondary">{saveStatus}</span>}
        </div>
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard
          eyebrow="Time budget"
          title="Mission feasibility"
          actions={
            mission ? (
              <FeasibilityBadge status={mission.feasibility_status} />
            ) : missionLoading ? (
              <Loader2 size={14} className="animate-spin text-mars-orange" />
            ) : null
          }
        >
          {mission ? (
            <>
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <StatusPill tone="derived" dot={false}>
                  {mission.route_strategy?.replace(/_/g, " ") ?? "balanced"} strategy
                </StatusPill>
                <ProvenanceBadge status="derived" />
                <span className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  {mission.mission_id}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <MiniMetric label="Outbound" value={fmt(mission.time_budget.outbound_min)} unit="min" icon={Clock} />
                <MiniMetric label="Exploration" value={fmt(mission.time_budget.exploration_min)} unit="min" icon={MapPin} />
                <MiniMetric label="Return" value={fmt(mission.time_budget.return_min)} unit="min" icon={Clock} />
                <MiniMetric label="Reserve" value={fmt(mission.time_budget.reserve_min)} unit="min" icon={Gauge} />
                <MiniMetric label="Total" value={fmt(mission.time_budget.total_min)} unit="min" icon={RouteIcon} emphasis />
                <MiniMetric label="Limit" value={fmt(mission.time_budget.limit_min)} unit="min" icon={Gauge} />
              </div>
              {mission.reasons.length > 0 && (
                <p className="mt-2 text-[10px] leading-relaxed text-text-secondary">
                  {mission.reasons.join(" ")}
                </p>
              )}
              <div className="mt-3 border-t border-line/50 pt-2.5">
                <p className="text-[9px] uppercase tracking-[0.1em] text-text-muted">Assumptions</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[10px] leading-relaxed text-text-muted">
                  {(mission.assumptions ?? []).slice(0, 3).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-line/50 pt-2">
                <StatusPill tone="neutral" dot={false}>
                  Estimated, not certified
                </StatusPill>
                <StatusPill tone="caution" dot={false}>
                  Regional 463 m baseline
                </StatusPill>
              </div>
            </>
          ) : (
            <p className="text-xs text-text-muted">
              {budgetError ?? "Calculate routes to compute the backend mission time budget."}
            </p>
          )}
        </SectionCard>

        <SectionCard
          eyebrow="Terrain profile"
          title="Sampled elevation profile"
          actions={
            profileLoading ? (
              <Loader2 size={14} className="animate-spin text-mars-orange" />
            ) : (
              <StatusPill tone="observed">MOLA observed</StatusPill>
            )
          }
        >
          {profileData.length > 1 ? (
            <>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={profileData} margin={{ top: 6, right: 8, bottom: 0, left: -12 }}>
                    <CartesianGrid stroke="#624536" strokeOpacity={0.18} vertical={false} />
                    <XAxis
                      dataKey="distance_km"
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
                      labelFormatter={(value) => `${value} km along route`}
                      formatter={(value, name) => [
                        name === "elevation_m" ? `${value} m` : `${value}°`,
                        name === "elevation_m" ? "Elevation" : "Slope",
                      ]}
                    />
                    <Line
                      type="monotone"
                      dataKey="elevation_m"
                      stroke="#F06B3D"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 3, fill: "#F06B3D" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
                {profileData.length} samples over {profile ? (profile.distance_m / 1000).toFixed(2) : "—"} km,
                sampled from the processed MOLA elevation raster. The profile does not certify
                rover-scale trafficability.
              </p>
            </>
          ) : (
            <p className="text-xs text-text-muted">
              {profileLoading ? "Sampling the selected route…" : "No terrain profile available for this route."}
            </p>
          )}
        </SectionCard>
      </div>
    </div>
  );
}

function fmt(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : String(value);
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