import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2,
  RotateCcw,
  Target,
} from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import StatusPill from "../../components/common/StatusPill";
import Button from "../../components/common/Button";
import Toggle from "../../components/common/Toggle";
import { EmptyState, ErrorState, LoadingState } from "../../components/common/States";
import { ProvenanceBadge, SimulatedLabel } from "../../components/common/StatusBadge";
import {
  GALE_BOUNDS,
  MOLA_ATTRIBUTION,
  MOLA_BASEMAP_URL,
  API_ORIGIN,
  assetUrl,
  boundsCenter,
  layerLeafletBounds,
  toLeafletBounds,
} from "../../components/map/mars";
import { MarsMap } from "../../components/map/MarsMap";
import { endpoints } from "../../services/api/endpoints";
import { pushNotification } from "../../utils/notifications";
import { apiErrorMessage } from "../../services/api/client";
import { DEMO_ROUTE_COORDS, DEMO_TARGETS } from "../../data/demo";
import type {
  CoverageClass,
  CtxImagery,
  DatasetCatalogResponse,
  ImageryResponse,
  LayerMeta,
  Region,
  ScienceTarget,
  TerrainQueryResponse,
} from "../../types";

const REGION_ID = "gale_crater";

const DEFAULT_ENABLED: Record<string, boolean> = {
  mars_trek_mola_colorshade: true,
  gale_ctx_local: false,
  mola_roughness_trek: false,
  mars_mola_hrsc_blend: false,
  viking_mdim: false,
  mola_elevation: false,
  slope: false,
  roughness: false,
};

interface TileEntry {
  id: string;
  name: string;
  url: string;
  maxZoom: number;
  status: string;
  resolutionM: number | null;
  warnings?: string[];
}

export default function MartianMapPage() {
  const [region, setRegion] = useState<Region | null>(null);
  const [layers, setLayers] = useState<LayerMeta[]>([]);
  const [imagery, setImagery] = useState<ImageryResponse | null>(null);
  const [datasets, setDatasets] = useState<DatasetCatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [enabled, setEnabled] = useState<Record<string, boolean>>(DEFAULT_ENABLED);
  const [showDemoTargets, setShowDemoTargets] = useState(true);
  const [showDemoRoute, setShowDemoRoute] = useState(false);
  const [selected, setSelected] = useState<ScienceTarget | null>(DEMO_TARGETS[0] ?? null);
  const [coords, setCoords] = useState<{ x: number; y: number } | null>(null);
  const [terrain, setTerrain] = useState<TerrainQueryResponse | null>(null);
  const [terrainLoading, setTerrainLoading] = useState(false);
  const [terrainError, setTerrainError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      endpoints.regions(),
      endpoints.layers(REGION_ID),
      endpoints.imagery(),
      endpoints.datasets(),
    ])
      .then(([regionsResult, layersResult, imageryResult, datasetsResult]) => {
        if (!active) return;
        if (regionsResult.status === "fulfilled") {
          setRegion(regionsResult.value.items.find((item) => item.id === REGION_ID) ?? regionsResult.value.items[0] ?? null);
        }
        if (layersResult.status === "fulfilled") {
          setLayers(layersResult.value.items);
        } else {
          setError(apiErrorMessage(layersResult.reason));
        }
        if (imageryResult.status === "fulfilled") setImagery(imageryResult.value);
        if (datasetsResult.status === "fulfilled") setDatasets(datasetsResult.value);
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  useEffect(() => {
    if (!coords) return;
    let active = true;
    setTerrainLoading(true);
    setTerrainError(null);
    endpoints
      .terrain(REGION_ID, coords.x, coords.y)
      .then((response) => {
        if (!active) return;
        setTerrain(response);
        if (response.availability === "unavailable") {
          pushNotification("Terrain query outside MOLA coverage.", "/map");
        }
      })
      .catch((reason) => {
        if (!active) return;
        setTerrain(null);
        setTerrainError(apiErrorMessage(reason));
      })
      .finally(() => active && setTerrainLoading(false));
    return () => {
      active = false;
    };
  }, [coords, reloadKey]);

  const toggle = (id: string) => setEnabled((previous) => ({ ...previous, [id]: !previous[id] }));

  const resetLayers = () => {
    setEnabled(DEFAULT_ENABLED);
    setShowDemoTargets(true);
    setShowDemoRoute(false);
  };

  const regionBounds = toLeafletBounds(region?.bounds_latlon) ?? GALE_BOUNDS;
  const center = boundsCenter(region?.bounds_latlon);

  const basemap = imagery?.tiles?.["mars_trek_mola_colorshade"];
  const basemapUrl = basemap?.tile_url_template ?? MOLA_BASEMAP_URL;

  const tileLayers: TileEntry[] = useMemo(() => {
    const catalog = new Map(layers.map((layer) => [layer.id, layer]));
    const entries: TileEntry[] = [];
    Object.entries(imagery?.tiles ?? {}).forEach(([id, tile]) => {
      if (id === "mars_trek_mola_colorshade") return;
      const meta = catalog.get(id);
      entries.push({
        id,
        name: meta?.name ?? tile.name,
        url: tile.tile_url_template,
        maxZoom: tile.max_zoom ?? 8,
        status: meta?.status ?? "observed",
        resolutionM: meta?.resolution_m ?? null,
        warnings: meta?.warnings,
      });
    });
    layers
      .filter((layer) => layer.layer_type === "tiles" && layer.tile_url_template)
      .forEach((layer) => {
        if (!entries.some((entry) => entry.id === layer.id) && layer.id !== "mars_trek_mola_colorshade") {
          entries.push({
            id: layer.id,
            name: layer.name,
            url: layer.tile_url_template as string,
            maxZoom: layer.max_zoom ?? 8,
            status: layer.status,
            resolutionM: layer.resolution_m ?? null,
            warnings: layer.warnings,
          });
        }
      });
    return entries;
  }, [imagery, layers]);

  const overlays = useMemo(() => {
    const entries = layers
      .filter((layer) => layer.overlay_url && layer.availability !== "unavailable")
      .map((layer) => ({
        id: layer.id,
        name: layer.name,
        url: assetUrl(layer.overlay_url),
        bounds: layerLeafletBounds(layer.bounds) ?? regionBounds,
        status: layer.status,
        resolutionM: layer.resolution_m ?? null,
        warnings: layer.warnings,
        display: layer.display,
      }));
    const ctx: CtxImagery | undefined = imagery?.ctx;
    if (ctx?.available && ctx.overlay_url) {
      entries.push({
        id: "gale_ctx_local",
        name: ctx.name,
        url: assetUrl(ctx.overlay_url),
        bounds: layerLeafletBounds(ctx.bounds) ?? regionBounds,
        status: "observed",
        resolutionM: ctx.resolution_m,
        warnings: ctx.warnings,
        display: ctx.display,
      });
    }
    return entries.filter((entry) => Boolean(entry.url));
  }, [layers, imagery, regionBounds]);

  const unavailableLayers = layers.filter((layer) => layer.availability === "unavailable");
  const availableCount = layers.filter((layer) => layer.availability !== "unavailable").length;
  const datasetCounts = useMemo(() => {
    const counts: Record<string, number> = { available: 0, partial: 0, unavailable: 0, other: 0 };
    (datasets?.datasets ?? []).forEach((dataset) => {
      counts[dataset.status] = (counts[dataset.status] ?? 0) + 1;
    });
    return counts;
  }, [datasets]);

  const markerIcon = useCallback(
    () =>
      L.divIcon({
        className: "",
        html: '<div style="width:14px;height:14px;border-radius:50%;background:#55C7D9;border:2px solid #F3F0EC;box-shadow:0 0 0 3px rgba(85,199,217,0.18)"></div>',
        iconSize: [14, 14],
      }),
    [],
  );

  // Build tile layer configs for MarsMap
  const baseTileLayer = {
    id: "mars_trek_mola_colorshade",
    name: basemap?.name ?? "Mars Trek MOLA Color-Shaded Relief",
    url: basemapUrl,
    maxZoom: basemap?.max_zoom ?? 8,
    status: "observed" as const,
    resolutionM: null,
    warnings: undefined,
  };

  // NASA Trek layer IDs that support the backend tile proxy
  const PROXIED_LAYER_IDS = new Set([
    "mars_trek_mola_colorshade",
    "mola_roughness",
    "mars_mola_hrsc_blend",
    "gale_ctx",
    "viking_mdim",
  ]);

  const tileLayerConfigs = [
    baseTileLayer,
    ...tileLayers,
  ].map((layer) => {
    const isProxied = PROXIED_LAYER_IDS.has(layer.id);
    return {
      id: layer.id,
      url: layer.url,
      attribution: layer.id === "mars_trek_mola_colorshade" ? MOLA_ATTRIBUTION : "NASA Mars Trek",
      maxZoom: layer.maxZoom,
      tileSize: 256,
      visible: enabled[layer.id] ?? false,
      // Use backend proxy for NASA Trek layers to avoid CORS issues
      useProxy: isProxied,
      proxyLayerId: isProxied ? layer.id : undefined,
    };
  });

  const overlayConfigs = overlays.map((layer) => ({
    id: layer.id,
    url: layer.url as string,
    bounds: layer.bounds,
    opacity: layer.id === "gale_ctx_local" ? 0.9 : 0.62,
    visible: enabled[layer.id] ?? false,
  }));

  const demoTargetMarkers = showDemoTargets
    ? DEMO_TARGETS.map((target) => ({
        id: target.id,
        position: [target.geometry.coordinates[1], target.geometry.coordinates[0]] as [number, number],
        icon: markerIcon(),
        title: `${target.name} (simulated target)`,
        onClick: () => setSelected(target),
      }))
    : [];

  const demoRoutePolyline = showDemoRoute
    ? [{
        id: "demo_route",
        positions: DEMO_ROUTE_COORDS.map(([x, y]) => [y, x] as [number, number]),
        color: "#F06B3D",
        weight: 3,
        opacity: 0.9,
        dashArray: "1 0",
        visible: true,
      }]
    : [];

  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-10.75rem)] lg:min-h-[560px]">
      <PageHeader
        eyebrow="Surface workspace"
        title="Interactive Martian Map"
        description="NASA Mars Trek imagery and locally processed MOLA/CTX overlays. Basemaps and elevation are observed; slope and roughness are derived. Overlay bounds, projection and units come from the dataset metadata, not hardcoded map constants."
        meta={
          <>
            <StatusPill tone="observed">MOLA / CTX observed</StatusPill>
            <StatusPill tone="derived">Slope · roughness derived</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              Mars equirectangular · planetocentric
            </StatusPill>
          </>
        }
        actions={
          <Button
            variant="secondary"
            size="md"
            icon={<RotateCcw size={14} />}
            onClick={resetLayers}
          >
            Reset view
          </Button>
        }
      />

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_348px]">
        <section className="panel relative min-h-[420px] overflow-hidden lg:min-h-0">
          {loading && (
            <div className="absolute inset-0 z-[1200] grid place-items-center bg-canvas/70 backdrop-blur-[1px]">
              <LoadingState label="Loading mission layers…" />
            </div>
          )}

          <MarsMap
            center={center}
            zoom={5}
            minZoom={0}
            maxZoom={8}
            scrollWheelZoom={false}
            zoomControl={false}
            attributionControl={true}
            proxyBaseUrl={API_ORIGIN}
            tileLayers={tileLayerConfigs}
            imageOverlays={overlayConfigs}
            markers={demoTargetMarkers}
            polylines={demoRoutePolyline}
            onMapClick={(x, y) => setCoords({ x, y })}
            onPointerMove={(_lat, _lng) => {
              // Could update a coordinate readout here
            }}
            fitBounds={regionBounds}
          />

          <div className="pointer-events-none absolute left-3 top-3 z-[900] flex flex-wrap items-center gap-1.5">
            <span className="rounded border border-line/80 bg-black/65 px-2 py-1 text-[9px] uppercase tracking-[0.1em] text-text-secondary backdrop-blur-sm">
              {region?.name ?? "Gale Crater"} · Mars
            </span>
            <span className="rounded border border-safe-green/30 bg-black/65 px-2 py-1 text-[9px] uppercase tracking-[0.1em] text-safe-green backdrop-blur-sm">
              Basemap observed
            </span>
          </div>

          {error && (
            <div className="absolute left-3 top-14 z-[1100] w-[min(360px,calc(100%-24px))]">
              <ErrorState message={error} onRetry={() => setReloadKey((key) => key + 1)} compact />
            </div>
          )}
        </section>

        <aside className="dash-scroll flex min-h-0 flex-col gap-3 lg:overflow-y-auto lg:pr-1">
          <SectionCard
            eyebrow="Data sources"
            title="Layers"
            description={`${availableCount} of ${layers.length || 0} catalogued layers available · ${region?.resolution_m ? `${region.resolution_m.toFixed(0)} m/px regional grid` : "resolution pending"}.`}
            actions={
              <Button variant="ghost" size="sm" onClick={resetLayers}>
                Reset
              </Button>
            }
            bodyClassName="p-0"
            flush
          >
            <LayerGroup title="Observed basemaps">
              <LayerRow
                id="mars_trek_mola_colorshade"
                name={basemap?.name ?? "Mars Trek MOLA Color-Shaded Relief"}
                meta="observed · NASA Mars Trek tiles"
                enabled={Boolean(enabled.mars_trek_mola_colorshade)}
                onToggle={() => toggle("mars_trek_mola_colorshade")}
                tone="observed"
              />
              {tileLayers.map((layer) => (
                <LayerRow
                  key={layer.id}
                  name={layer.name}
                  meta={`${layer.status} · ${
                    layer.resolutionM ? `${layer.resolutionM} m/px` : "tile layer"
                  }`}
                  enabled={Boolean(enabled[layer.id])}
                  onToggle={() => toggle(layer.id)}
                  tone={layer.status === "derived" ? "derived" : "observed"}
                  title={layer.warnings?.join(" ")}
                />
              ))}
            </LayerGroup>

            <LayerGroup title="Local analysis overlays">
              {overlays.map((layer) => (
                <LayerRow
                  key={layer.id}
                  name={layer.name}
                  meta={`${layer.status} · ${layer.resolutionM ? `${layer.resolutionM.toFixed(1)} m/px` : "metadata bounds"}`}
                  enabled={Boolean(enabled[layer.id])}
                  onToggle={() => toggle(layer.id)}
                  tone={layer.status === "derived" ? "derived" : "observed"}
                  title={layer.warnings?.join(" ")}
                />
              ))}
              {overlays.length === 0 && (
                <p className="px-3 py-3 text-[11px] text-text-muted">No local overlays available.</p>
              )}
            </LayerGroup>

            <LayerGroup title="Unavailable sources">
              {unavailableLayers.map((layer) => (
                <LayerRow
                  key={layer.id}
                  name={layer.name}
                  meta={layer.layer_type}
                  enabled={false}
                  onToggle={() => undefined}
                  disabled
                  tone="unavailable"
                  title={layer.warnings?.join(" ")}
                />
              ))}
              {unavailableLayers.length === 0 && (
                <p className="px-3 py-3 text-[11px] text-text-muted">
                  No unavailable catalogued layers.
                </p>
              )}
            </LayerGroup>

            <LayerGroup title="Simulated overlays" hint="Frontend-only demonstration">
              <LayerRow
                name="Demo science targets"
                meta="simulated · 3 points · catalog unavailable"
                enabled={showDemoTargets}
                onToggle={() => setShowDemoTargets((value) => !value)}
                tone="simulated"
              />
              <LayerRow
                name="Demo traverse"
                meta="simulated · route geometry"
                enabled={showDemoRoute}
                onToggle={() => setShowDemoRoute((value) => !value)}
                tone="simulated"
              />
            </LayerGroup>
          </SectionCard>

          <SectionCard
            eyebrow="NASA package"
            title="Dataset status"
            actions={
              <StatusPill tone={datasetCounts.available > 0 ? "observed" : "unavailable"}>
                {datasets?.datasets.length ?? 0} entries
              </StatusPill>
            }
            bodyClassName="p-3.5"
          >
            <dl className="space-y-1.5 text-[11px]">
              <StatusRow label="Available" value={datasetCounts.available ?? 0} tone="text-safe-green" />
              <StatusRow label="Partial" value={datasetCounts.partial ?? 0} tone="text-warning-amber" />
              <StatusRow label="Unavailable" value={datasetCounts.unavailable ?? 0} tone="text-critical-red" />
              <StatusRow label="Catalog version" value={datasets?.catalog_version ?? "—"} tone="text-text-secondary" />
            </dl>
            {imagery?.ctx && (
              <p className="mt-3 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
                CTX: {imagery.ctx.units}. Partial coverage lat{" "}
                {imagery.ctx.bounds.bounds_latlon?.south.toFixed(3)}..{imagery.ctx.bounds.bounds_latlon?.north.toFixed(3)}, lon{" "}
                {imagery.ctx.bounds.bounds_latlon?.west.toFixed(3)}..{imagery.ctx.bounds.bounds_latlon?.east.toFixed(3)}. Not
                stretched into uncovered areas.
              </p>
            )}
          </SectionCard>

          <SectionCard eyebrow="Map key" title="Legend" bodyClassName="p-3.5">
            <ul className="space-y-2 text-[11px]">
              <LegendItem color="#F06B3D" label="Simulated traverse" />
              <LegendItem color="#55C7D9" label="Simulated science target" dot />
              <LegendItem color="#D9A06A" label="MOLA elevation overlay" fill />
              <LegendItem color="#8FA6B8" label="Local CTX mosaic (DN)" fill />
              <LegendItem color="#E45C5C" label="Hazard overlay (unavailable)" muted />
            </ul>
            <p className="mt-3 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
              Unknown coverage is never rendered as safe terrain. Overlay bounds come from
              dataset metadata; Web Mercator is not used for Mars.
            </p>
          </SectionCard>

          <SectionCard
            eyebrow="Inspector"
            title="Feature inspector"
            actions={terrainLoading ? <Loader2 size={14} className="animate-spin text-mars-orange" /> : null}
            bodyClassName="p-3.5"
          >
            {coords ? (
              <div className="mb-3 rounded-control border border-line/70 bg-surface2/60 p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-micro text-text-muted">Point query</span>
                  <StatusPill
                    tone={
                      terrain?.availability === "available"
                        ? "observed"
                        : terrain?.availability === "partial"
                        ? "caution"
                        : "unavailable"
                    }
                  >
                    {terrain?.availability ?? "pending"}
                  </StatusPill>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-[10px]">
                  <Value label="Elev" value={terrain?.values.elevation_m} unit=" m" />
                  <Value label="Slope" value={terrain?.values.slope_deg} unit="°" />
                  <Value label="Rough" value={terrain?.values.roughness} unit=" m" />
                </div>
                <div className="mt-2 text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  Planetocentric lon {coords.x.toFixed(4)}° · lat {coords.y.toFixed(4)}°
                </div>
                {terrain?.coverage && <CoverageLine coverage={terrain.coverage} />}
                {terrain?.source?.provider && (
                  <p className="mt-1 text-[9px] leading-relaxed text-text-muted">
                    {terrain.source.provider} · {terrain.classification ?? "OBSERVED + DERIVED"}
                  </p>
                )}
                {terrain?.limitations?.[0] && (
                  <p className="mt-1 text-[9px] leading-relaxed text-text-muted">{terrain.limitations[0]}</p>
                )}
                {terrainError && (
                  <p className="mt-1.5 text-[10px] text-critical-red">{terrainError}</p>
                )}
              </div>
            ) : (
              <p className="mb-3 rounded-control border border-dashed border-line/70 px-2.5 py-2 text-[10px] leading-relaxed text-text-muted">
                Click the map to query the processed MOLA raster. Values are unavailable outside
                coverage and are never zero-filled.
              </p>
            )}

            {selected ? (
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-text-primary">{selected.name}</div>
                    <div className="text-[9px] uppercase tracking-[0.08em] text-text-muted">
                      {selected.feature_type ?? "Feature"}
                    </div>
                  </div>
                  <SimulatedLabel />
                </div>
                <dl className="space-y-1.5 text-[10px]">
                  <InspectorRow
                    label="Coordinates"
                    value={`${selected.geometry.coordinates[0].toFixed(2)}, ${selected.geometry.coordinates[1].toFixed(2)}`}
                  />
                  <InspectorRow label="Priority" value={selected.priority ?? "—"} />
                  <InspectorRow
                    label="Distance"
                    value={selected.distance_m ? `${(selected.distance_m / 1000).toFixed(2)} km` : "—"}
                  />
                  <InspectorRow label="Source" value={selected.source_name ?? "—"} />
                </dl>
                <p className="text-[11px] leading-relaxed text-text-secondary">
                  {selected.description}
                </p>
                {selected.interpretation && (
                  <p className="border-l border-amber/40 pl-2 text-[10px] leading-relaxed text-text-muted">
                    Interpretation: {selected.interpretation}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <ProvenanceBadge status={selected.provenance[0] ?? "simulated"} />
                  <StatusPill tone="unavailable" dot={false}>
                    No verified target catalogue
                  </StatusPill>
                </div>
              </div>
            ) : (
              <EmptyState
                title="No feature selected"
                description="Select a simulated target marker to inspect its demonstration record."
                icon={<Target size={18} aria-hidden />}
                className="px-3 py-5"
              />
            )}
          </SectionCard>
        </aside>
      </div>
    </div>
  );
}

function LayerGroup({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-line/50 last:border-b-0">
      <div className="flex items-center justify-between gap-2 px-3 pb-1 pt-2.5">
        <span className="text-[9px] font-semibold uppercase tracking-[0.12em] text-text-muted">
          {title}
        </span>
        {hint && <span className="text-[8px] uppercase tracking-[0.06em] text-text-muted/70">{hint}</span>}
      </div>
      <div className="pb-1.5">{children}</div>
    </div>
  );
}

function LayerRow({
  name,
  meta,
  enabled,
  onToggle,
  disabled = false,
  tone,
  title,
}: {
  id?: string;
  name: string;
  meta: string;
  enabled: boolean;
  onToggle: () => void;
  disabled?: boolean;
  tone: "observed" | "derived" | "simulated" | "unavailable";
  title?: string;
}) {
  return (
    <div
      className={`flex items-center justify-between gap-2 px-3 py-1.5 ${
        disabled ? "opacity-55" : ""
      }`}
      title={title}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span
            aria-hidden
            className={`h-1.5 w-1.5 shrink-0 rounded-full ${
              tone === "observed"
                ? "bg-safe-green"
                : tone === "derived"
                ? "bg-cyan"
                : tone === "simulated"
                ? "bg-amber"
                : "bg-text-muted"
            }`}
          />
          <span className="truncate text-[11px] text-text-primary">{name}</span>
        </div>
        <div className="mt-0.5 truncate pl-3 text-[9px] uppercase tracking-[0.06em] text-text-muted">
          {meta}
        </div>
      </div>
      <Toggle
        checked={enabled}
        onChange={onToggle}
        disabled={disabled}
        id={undefined}
        label={undefined}
        description={`Toggle ${name}`}
      />
    </div>
  );
}

function LegendItem({
  color,
  label,
  dot,
  fill,
  muted,
}: {
  color: string;
  label: string;
  dot?: boolean;
  fill?: boolean;
  muted?: boolean;
}) {
  return (
    <li className={`flex items-center gap-2 ${muted ? "opacity-55" : ""}`}>
      {dot ? (
        <span
          className="inline-block h-2.5 w-2.5 shrink-0 rounded-full border-2"
          style={{ borderColor: color, background: color }}
        />
      ) : fill ? (
        <span
          className="inline-block h-2.5 w-4 shrink-0 rounded-sm border"
          style={{ background: `${color}33`, borderColor: color }}
        />
      ) : (
        <span
          className="inline-block h-0.5 w-5 shrink-0"
          style={{ background: color }}
        />
      )}
      <span className="text-text-secondary">{label}</span>
    </li>
  );
}

function StatusRow({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-text-muted">{label}</dt>
      <dd className={`tabular ${tone}`}>{value}</dd>
    </div>
  );
}

function CoverageLine({ coverage }: { coverage: CoverageClass }) {
  return (
    <div className="mt-1.5 rounded border border-line/60 bg-surface1/50 px-1.5 py-1 text-[9px] leading-relaxed text-text-muted">
      <span className="uppercase tracking-[0.08em]">Coverage class {coverage.class ?? "—"}</span>
      <span className="mx-1">·</span>
      {coverage.label}
    </div>
  );
}

function Value({
  label,
  value,
  unit,
}: {
  label: string;
  value: number | null | undefined;
  unit: string;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[8px] uppercase tracking-[0.08em] text-text-muted">{label}</div>
      <div className="truncate text-[11px] tabular text-text-primary">
        {value === null || value === undefined ? "—" : `${value}${unit}`}
      </div>
    </div>
  );
}

function InspectorRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-text-muted">{label}</dt>
      <dd className="truncate text-right tabular text-text-secondary">{value}</dd>
    </div>
  );
}