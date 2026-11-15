import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Bot,
  Info,
  MapPin,
  Route as RouteIcon,
  ShieldCheck,
  Target,
  ThermometerSun,
} from "lucide-react";
import { MapContainer, TileLayer } from "react-leaflet";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import StatCard from "../../components/common/StatCard";
import StatusPill from "../../components/common/StatusPill";
import Button, { buttonClasses } from "../../components/common/Button";
import { ErrorState, LoadingState } from "../../components/common/States";
import { ProvenanceBadge, SimulatedLabel } from "../../components/common/StatusBadge";
import { MarsCRS, MOLA_ATTRIBUTION, MOLA_BASEMAP_URL } from "../../components/map/mars";
import { endpoints } from "../../services/api/endpoints";
import { apiErrorMessage } from "../../services/api/client";
import { DEMO_TARGETS } from "../../data/demo";
import type {
  AssistantHealthResponse,
  CoverageSummary,
  DatasetCatalogResponse,
  LayerMeta,
  RadiationResponse,
  Region,
  RemsResponse,
} from "../../types";

const REGION_ID = "gale_crater";
const PHASES = ["Plan", "Traverse", "Science", "Return"];

const CHART_TOOLTIP = {
  background: "#171411",
  border: "1px solid #624536",
  borderRadius: 4,
  fontSize: 11,
  color: "#F3F0EC",
};

export default function OverviewPage() {
  const [region, setRegion] = useState<Region | null>(null);
  const [layers, setLayers] = useState<LayerMeta[]>([]);
  const [coverage, setCoverage] = useState<CoverageSummary | null>(null);
  const [datasets, setDatasets] = useState<DatasetCatalogResponse | null>(null);
  const [rems, setRems] = useState<RemsResponse | null>(null);
  const [rad, setRad] = useState<RadiationResponse | null>(null);
  const [health, setHealth] = useState<AssistantHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      endpoints.regions(),
      endpoints.layers(REGION_ID),
      endpoints.terrainCoverageSummary(REGION_ID),
      endpoints.datasets(),
      endpoints.rems(REGION_ID),
      endpoints.radiation(REGION_ID),
      endpoints.assistantHealth(),
    ])
      .then(([regions, layerResult, coverageResult, datasetResult, remsResult, radResult, healthResult]) => {
        if (!active) return;
        if (regions.status === "fulfilled") {
          setRegion(regions.value.items.find((item) => item.id === REGION_ID) ?? regions.value.items[0] ?? null);
        }
        if (layerResult.status === "fulfilled") setLayers(layerResult.value.items);
        else setError(apiErrorMessage(layerResult.reason));
        if (coverageResult.status === "fulfilled") setCoverage(coverageResult.value);
        if (datasetResult.status === "fulfilled") setDatasets(datasetResult.value);
        if (remsResult.status === "fulfilled") setRems(remsResult.value);
        if (radResult.status === "fulfilled") setRad(radResult.value);
        if (healthResult.status === "fulfilled") setHealth(healthResult.value);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const layerById = useMemo(() => new Map(layers.map((layer) => [layer.id, layer])), [layers]);
  const elevationLayer = layerById.get("mola_elevation");
  const slopeLayer = layerById.get("slope");
  const roughnessLayer = layerById.get("roughness");

  const datasetCounts = useMemo(() => {
    const counts: Record<string, number> = { available: 0, partial: 0, unavailable: 0 };
    (datasets?.datasets ?? []).forEach((dataset) => {
      counts[dataset.status] = (counts[dataset.status] ?? 0) + 1;
    });
    return counts;
  }, [datasets]);

  const class1Pct = coverage?.percentages["1"] ?? null;
  const class2Pct = coverage?.percentages["2"] ?? null;

  const remsSeries = useMemo(() => {
    if (!rems) return [];
    return rems.sols.map((sol) => {
      const measurements = rems.measurements[String(sol)] ?? {};
      return {
        sol: `Sol ${sol}`,
        air: measurements.air_temperature?.mean ?? null,
        ground: measurements.ground_temperature?.mean ?? null,
        pressure: measurements.pressure?.mean ?? null,
      };
    });
  }, [rems]);

  const radSeries = useMemo(() => {
    if (!rad) return [];
    const b = rad.detectors.dose_rate_B?.sols ?? {};
    const e = rad.detectors.dose_rate_E?.sols ?? {};
    return rad.sols.map((sol) => ({
      sol: `Sol ${sol}`,
      detector_b: b[String(sol)]?.mean ?? null,
      detector_e: e[String(sol)]?.mean ?? null,
    }));
  }, [rad]);

  const warnings = useMemo(() => {
    const items = new Set<string>();
    (datasets?.datasets ?? []).forEach((dataset) => {
      (dataset.warnings ?? []).forEach((warning) => items.add(warning));
    });
    layers.forEach((layer) => (layer.warnings ?? []).forEach((warning) => items.add(warning)));
    coverage?.warnings.forEach((warning) => items.add(warning));
    rems?.warnings.forEach((warning) => items.add(warning));
    rad?.warnings.forEach((warning) => items.add(warning));
    return Array.from(items).slice(0, 6);
  }, [datasets, layers, coverage, rems, rad]);

  const limitations = useMemo(() => {
    const items = new Set<string>();
    coverage?.limitations.forEach((item) => items.add(item));
    rems?.limitations.forEach((item) => items.add(item));
    rad?.limitations.forEach((item) => items.add(item));
    return Array.from(items).slice(0, 5);
  }, [coverage, rems, rad]);

  const target = DEMO_TARGETS[0];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Mission overview · Gale Crater"
        title="Mission situational awareness"
        description="A planning-phase workspace built on the supplied NASA package: MOLA elevation/slope/roughness, a processed CTX mosaic, historical REMS environment and RAD dose rates. Terrain values come from verified rasters; REMS and RAD are single-location 2012 measurements, never live or route-specific."
        meta={
          <>
            <StatusPill tone={region?.availability === "available" ? "observed" : "unavailable"}>
              {region?.availability ?? "loading"} region
            </StatusPill>
            <StatusPill tone="derived">Derived terrain analysis</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              <MapPin size={10} /> {region?.name ?? "Gale Crater"}, Mars
            </StatusPill>
          </>
        }
        actions={
          <>
            <Link to="/missions" className={buttonClasses("primary", "md")}>
              + Add mission
            </Link>
            <Link to="/routes" className={buttonClasses("secondary", "md")}>
              <RouteIcon size={14} /> Route planner
            </Link>
            <Link to="/reports" className={buttonClasses("secondary", "md")}>
              Mission report
            </Link>
          </>
        }
      />

      {loading && (
        <div className="panel p-4">
          <LoadingState label="Loading NASA package status…" />
        </div>
      )}
      {error && (
        <div className="panel p-4">
          <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} compact />
        </div>
      )}

      <section className="panel p-4 sm:p-5">
        <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr] lg:divide-x lg:divide-line/60">
          <div className="min-w-0 lg:pr-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-micro text-mars-orange/90">Planning phase</div>
                <h2 className="mt-1 font-heading text-base font-semibold">Data-backed traverse planning</h2>
              </div>
              <span className="text-[10px] uppercase tracking-[0.12em] text-text-muted">
                Phase 01 / 04
              </span>
            </div>
            <p className="mt-2 max-w-xl text-xs leading-relaxed text-text-secondary">
              Route candidates are computed from observed MOLA elevation with derived slope and
              roughness. Every response carries units, coverage and source metadata; class 2 cells
              are never treated as zero risk.
            </p>

            <ol className="mt-4 grid grid-cols-4 gap-1.5" aria-label="Mission phases">
              {PHASES.map((phase, index) => (
                <li key={phase} className="min-w-0">
                  <div className={`h-1 rounded-full ${index === 0 ? "bg-mars-orange" : "bg-surface3"}`} />
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

            <div className="mt-4 border-t border-line/50 pt-3">
              <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.08em] text-text-muted">
                <span>Terrain coverage · class 1 valid</span>
                <span className="tabular text-text-secondary">{class1Pct === null ? "—" : `${class1Pct.toFixed(2)}%`}</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface3">
                <div
                  className="h-full rounded-full bg-safe-green"
                  style={{ width: `${Math.min(100, class1Pct ?? 0)}%` }}
                />
              </div>
              <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[9px] uppercase tracking-[0.08em] text-text-muted">
                <span>Class 0: {coverage?.percentages["0"]?.toFixed(2) ?? "—"}%</span>
                <span>Class 2: {class2Pct === null ? "—" : `${class2Pct.toFixed(2)}%`}</span>
                <span>{coverage?.total_cells?.toLocaleString() ?? "—"} cells</span>
              </div>
            </div>
          </div>

          <div className="min-w-0 lg:pl-5">
            <div className="flex items-center justify-between">
              <div className="text-micro text-mars-orange/90">Data readiness</div>
              <StatusPill tone={datasetCounts.unavailable > 0 ? "caution" : "observed"}>
                {datasetCounts.available} available
              </StatusPill>
            </div>
            <ul className="mt-2 divide-y divide-line/40">
              {[
                { label: "Elevation · MOLA", layer: elevationLayer, note: "Observed" },
                { label: "Slope · MOLA-derived", layer: slopeLayer, note: "Derived" },
                { label: "Roughness · TRI", layer: roughnessLayer, note: "Derived" },
                { label: "CTX mosaic", layer: undefined, note: "Observed" },
                { label: "REMS environment", layer: undefined, note: "Historical" },
                { label: "RAD dose rate", layer: undefined, note: "Historical" },
              ].map((item) => (
                <li key={item.label} className="flex items-center justify-between gap-3 py-1.5">
                  <div className="min-w-0">
                    <div className="truncate text-[11px] text-text-secondary">{item.label}</div>
                    <div className="truncate text-[9px] uppercase tracking-[0.08em] text-text-muted">
                      {item.layer?.resolution_m ? `${item.layer.resolution_m.toFixed(0)} m/px` : item.note}
                    </div>
                  </div>
                  <StatusPill
                    tone={
                      item.layer?.availability === "unavailable"
                        ? "unavailable"
                        : item.note === "Observed" || item.note === "Historical"
                          ? "observed"
                          : "derived"
                    }
                  >
                    {item.layer?.availability ?? "available"}
                  </StatusPill>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
              Unavailable sources stay unavailable. Missing coverage is never converted into a
              low-risk score.
            </p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Catalogued datasets"
          value={datasets?.datasets.length ?? "—"}
          unit="assets"
          icon={Activity}
          tone="info"
          status={<StatusPill tone="observed">{datasetCounts.available} available</StatusPill>}
          footnote={`Catalog v${datasets?.catalog_version ?? "—"} from the installed NASA package.`}
        />
        <StatCard
          label="Valid terrain cells"
          value={class1Pct === null ? "—" : class1Pct.toFixed(1)}
          unit="%"
          icon={RouteIcon}
          tone="safe"
          status={<StatusPill tone="derived">Derived coverage</StatusPill>}
          footnote={`${coverage?.counts["2"] ?? "—"} class 2 cells lack slope/roughness.`}
        />
        <StatCard
          label="REMS sols"
          value={rems?.sols.length ?? "—"}
          unit="sols"
          icon={ThermometerSun}
          tone="neutral"
          status={<StatusPill tone="observed">Observed</StatusPill>}
          footnote="Curiosity rover point measurements, not live weather or a forecast."
        />
        <StatCard
          label="RAD sols"
          value={rad?.sols.length ?? "—"}
          unit="sols"
          icon={ShieldCheck}
          tone="warning"
          status={<StatusPill tone="observed">Observed</StatusPill>}
          footnote="Detectors B and E stay separate. Not a route radiation model."
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
                  {region?.bounds_latlon
                    ? `${((region.bounds_latlon.south + region.bounds_latlon.north) / 2).toFixed(2)}° lat · ${((region.bounds_latlon.west + region.bounds_latlon.east) / 2).toFixed(2)}° lon`
                    : "5.4°S · 137.8°E"}
                </div>
              </div>
              <MapContainer
                crs={MarsCRS}
                center={[
                  region?.bounds_latlon
                    ? (region.bounds_latlon.south + region.bounds_latlon.north) / 2
                    : -5.4,
                  region?.bounds_latlon
                    ? (region.bounds_latlon.west + region.bounds_latlon.east) / 2
                    : 137.8,
                ]}
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
                Mars MGS MOLA color hillshade · {region?.resolution_m ? `${region.resolution_m.toFixed(0)} m/px` : "463 m/px"} regional grid.
                Analysis overlays are available in the full map.
              </p>
              <div className="flex flex-wrap gap-1.5">
                <StatusPill tone="observed">Basemap</StatusPill>
                <StatusPill tone="derived">Terrain analysis</StatusPill>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Surface analysis"
          title="Terrain intelligence"
          actions={
            <StatusPill tone={layerById.get("slope")?.availability === "unavailable" ? "unavailable" : "derived"}>
              {layerById.get("slope")?.availability === "unavailable" ? "Unavailable" : "Derived"}
            </StatusPill>
          }
        >
          <div className="space-y-4">
            <TerrainRow
              label="Elevation (MOLA)"
              value={elevationLayer?.availability === "unavailable" ? "Unavailable" : "Observed"}
              state={elevationLayer?.availability === "unavailable" ? "unavailable" : "available"}
              bar={class1Pct ?? 0}
              description="Cell values are sampled from the processed MOLA elevation raster in metres."
            />
            <TerrainRow
              label="Slope"
              value={slopeLayer?.availability === "unavailable" ? "Unavailable" : "Derived"}
              state={slopeLayer?.availability === "unavailable" ? "unavailable" : "partial"}
              bar={class1Pct ?? 0}
              description="Horn (1981) slope in degrees at the ~463 m pixel baseline; regional, not rover-scale."
            />
            <TerrainRow
              label="Roughness"
              value={roughnessLayer?.availability === "unavailable" ? "Unavailable" : "Derived"}
              state={roughnessLayer?.availability === "unavailable" ? "unavailable" : "partial"}
              bar={class1Pct ?? 0}
              description="Riley (1999) terrain ruggedness index in metres; class 2 cells are undefined."
            />
            <TerrainRow
              label="Class 2 uncertainty"
              value={class2Pct === null ? "—" : `${class2Pct.toFixed(2)}%`}
              state="partial"
              bar={class2Pct ?? 0}
              description="Cells with elevation but no slope/roughness receive an explicit penalty in routing."
            />
          </div>
          <div className="mt-4 border-t border-line/50 pt-3">
            <div className="flex flex-wrap items-center gap-2">
              <ProvenanceBadge status="observed" />
              <ProvenanceBadge status="derived" />
              <StatusPill tone="neutral">Partial coverage</StatusPill>
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
              Missing terrain values are displayed as unavailable, never converted into a low-risk
              score.
            </p>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard
          eyebrow="REMS · historical"
          title="Environment at the rover"
          actions={
            <StatusPill tone={rems?.availability === "available" ? "observed" : "unavailable"}>
              {rems?.availability ?? "loading"}
            </StatusPill>
          }
        >
          {remsSeries.length > 0 ? (
            <>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={remsSeries} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
                    <CartesianGrid stroke="#624536" strokeOpacity={0.18} vertical={false} />
                    <XAxis dataKey="sol" tick={{ fill: "#786C65", fontSize: 9 }} tickLine={false} axisLine={{ stroke: "#624536", strokeOpacity: 0.4 }} />
                    <YAxis tick={{ fill: "#786C65", fontSize: 9 }} tickLine={false} axisLine={false} unit=" K" />
                    <Tooltip contentStyle={CHART_TOOLTIP} formatter={(value, name) => [`${value} K`, name === "air" ? "Air temperature" : "Ground temperature"]} />
                    <Legend wrapperStyle={{ fontSize: 10, color: "#B1A39A" }} />
                    <Line type="monotone" dataKey="air" name="Air temperature" stroke="#F06B3D" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="ground" name="Ground brightness" stroke="#55C7D9" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-line/50 pt-2 text-[10px] sm:grid-cols-4">
                {remsSeries.map((row) => (
                  <div key={row.sol}>
                    <dt className="uppercase tracking-[0.08em] text-text-muted">{row.sol}</dt>
                    <dd className="tabular text-text-secondary">
                      {row.air === null ? "—" : `${row.air.toFixed(1)} K`} · {row.pressure === null ? "—" : `${row.pressure.toFixed(0)} Pa`}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-[10px] leading-relaxed text-text-muted">
                {rems?.location.name}. Historical point measurements (sols {rems?.sols.join(", ")}),
                not live telemetry, forecast or a spatially distributed field.
              </p>
            </>
          ) : (
            <p className="text-xs text-text-muted">REMS data unavailable in this package.</p>
          )}
        </SectionCard>

        <SectionCard
          eyebrow="RAD · historical"
          title="Dose rate by detector"
          actions={
            <StatusPill tone={rad?.availability === "available" ? "observed" : "unavailable"}>
              {rad?.availability ?? "loading"}
            </StatusPill>
          }
        >
          {radSeries.length > 0 ? (
            <>
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={radSeries} margin={{ top: 6, right: 8, bottom: 0, left: -6 }}>
                    <CartesianGrid stroke="#624536" strokeOpacity={0.18} vertical={false} />
                    <XAxis dataKey="sol" tick={{ fill: "#786C65", fontSize: 9 }} tickLine={false} axisLine={{ stroke: "#624536", strokeOpacity: 0.4 }} />
                    <YAxis tick={{ fill: "#786C65", fontSize: 9 }} tickLine={false} axisLine={false} unit=" µGy/h" width={62} />
                    <Tooltip contentStyle={CHART_TOOLTIP} formatter={(value, name) => [`${value} µGy/h`, name === "detector_b" ? "Detector B (silicon)" : "Detector E (plastic)"]} />
                    <Legend wrapperStyle={{ fontSize: 10, color: "#B1A39A" }} />
                    <Line type="monotone" dataKey="detector_b" name="Detector B" stroke="#F06B3D" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="detector_e" name="Detector E" stroke="#55C7D9" strokeWidth={2} strokeDasharray="5 3" dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-3 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
                {rad?.unit}. Detectors B and E measure different quantities and are never merged.
                Historical Curiosity measurements at one rover location, sols {rad?.sols.join(", ")}; not a route-specific prediction.
              </p>
            </>
          ) : (
            <p className="text-xs text-text-muted">RAD data unavailable in this package.</p>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard
          eyebrow="Attention"
          title="Data warnings"
          actions={<StatusPill tone={warnings.length ? "caution" : "observed"}>{warnings.length} noted</StatusPill>}
        >
          <div className="space-y-2">
            {warnings.length > 0 ? (
              warnings.map((warning) => (
                <div key={warning} className="flex items-start gap-2.5 rounded-control border border-warning-amber/30 bg-warning-amber/[0.05] p-2.5">
                  <Info size={14} className="mt-0.5 shrink-0 text-warning-amber" aria-hidden />
                  <p className="text-[11px] leading-snug text-text-secondary">{warning}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-text-muted">No dataset warnings reported.</p>
            )}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Provenance" title="Coverage & limitations">
          <dl className="space-y-2 text-[11px]">
            <ProvenanceRow
              label="Region bounds"
              value={
                coverage
                  ? `${coverage.bounds_latlon.south.toFixed(2)}..${coverage.bounds_latlon.north.toFixed(2)} lat`
                  : "—"
              }
            />
            <ProvenanceRow
              label="Longitude"
              value={coverage ? `${coverage.bounds_latlon.west.toFixed(2)}..${coverage.bounds_latlon.east.toFixed(2)}` : "—"}
            />
            <ProvenanceRow label="CRS" value={region?.crs ?? "—"} />
            <ProvenanceRow label="Latitude type" value={region?.latitude_type ?? "planetocentric"} />
            <ProvenanceRow label="Provider" value={elevationLayer?.source?.provider ?? "—"} />
          </dl>
          <ul className="mt-3 list-disc space-y-1 border-t border-line/50 pl-4 pt-2 text-[10px] leading-relaxed text-text-muted">
            {limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard
          eyebrow="Decision support"
          title="AI mission assistant"
          actions={<Bot size={14} className="text-cyan" aria-hidden />}
        >
          <div className="space-y-3">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-secondary">
                Model status
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-text-secondary">
                {health
                  ? health.available
                    ? `${health.provider} · ${health.model} reachable.`
                    : `Model unavailable (${health.error ?? "not reachable"}); deterministic tool fallback is active.`
                  : "Checking model availability…"}
              </p>
            </div>
            <div className="border-t border-line/50 pt-2">
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-secondary">
                Grounding
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-text-secondary">
                {health?.tools.length ?? 0} allowlisted tools call the same terrain, route,
                feasibility and environment services as this dashboard. The model explains results;
                it does not compute them.
              </p>
            </div>
            <div className="border-t border-line/50 pt-2">
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-text-secondary">
                Availability
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
                Terrain: {layerById.get("slope")?.availability ?? "pending"} · REMS:{" "}
                {rems?.availability ?? "pending"} · RAD: {rad?.availability ?? "pending"}.
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
        title="No verified science catalogue"
        actions={<StatusPill tone="unavailable">Backend unavailable</StatusPill>}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-control border border-amber/35 bg-amber/10 text-amber">
              <Target size={18} aria-hidden />
            </span>
            <div className="min-w-0">
              <div className="font-heading text-sm font-semibold text-text-primary">
                {target?.name ?? "Demonstration target"}
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-secondary">
                <span>{target?.feature_type ?? "demo feature"}</span>
                <span className="text-text-muted">·</span>
                <span className="tabular">{target?.distance_m ? `${(target.distance_m / 1000).toFixed(1)} km` : "—"}</span>
                <span className="text-text-muted">·</span>
                <span className="tabular">
                  {target ? `${target.geometry.coordinates[1].toFixed(2)}°, ${target.geometry.coordinates[0].toFixed(2)}°` : "—"}
                </span>
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-text-muted">
                The NASA handover package contains no verified science-target GeoJSON. Targets in
                this UI are simulated and labelled; the backend returns an unavailable catalogue.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SimulatedLabel />
            <Link to="/science" className={buttonClasses("primary", "md")}>
              Inspect demo target <ArrowRight size={13} />
            </Link>
            <Button variant="ghost" size="md" disabled title="Requires a verified science-target dataset">
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
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${bar ?? (state === "unavailable" ? 6 : 50)}%` }} />
      </div>
      <p className="mt-1 text-[10px] leading-relaxed text-text-muted">{description}</p>
    </div>
  );
}

function ProvenanceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2 border-b border-line/40 pb-1.5 last:border-b-0 last:pb-0">
      <dt className="shrink-0 text-text-muted">{label}</dt>
      <dd className="max-w-[62%] truncate text-right tabular text-text-secondary" title={value}>
        {value}
      </dd>
    </div>
  );
}
