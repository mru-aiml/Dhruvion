import { useCallback, useEffect, useState } from "react";
import {
  Crosshair,
  Layers,
  Loader2,
  Minus,
  Plus,
  RotateCcw,
  Target,
} from "lucide-react";
import { ImageOverlay, MapContainer, Marker, Polyline, TileLayer, useMap } from "react-leaflet";
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
  API_ORIGIN,
  GALE_BOUNDS,
  LAYER_MAX_ZOOM,
  LAYER_TILE_URLS,
  MARS_BOUNDS,
  MOLA_ATTRIBUTION,
  MOLA_BASEMAP_URL,
  MarsCRS,
} from "../../components/map/mars";
import { endpoints } from "../../services/api/endpoints";
import { pushNotification } from "../../utils/notifications";
import { apiErrorMessage } from "../../services/api/client";
import { DEMO_LAYERS, DEMO_ROUTE_COORDS, DEMO_TARGETS } from "../../data/demo";
import type { LayerMeta, ScienceTarget } from "../../types";

const DEFAULT_ENABLED: Record<string, boolean> = {
  mars_trek_mola_colorshade: true,
  mola_elevation: false,
  slope: false,
  roughness: false,
};

interface TerrainPoint {
  elevation_m: number | null;
  slope_deg: number | null;
  roughness: number | null;
  availability: string;
}

export default function MartianMapPage() {
  const [layers, setLayers] = useState<LayerMeta[]>(DEMO_LAYERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [enabled, setEnabled] = useState<Record<string, boolean>>(DEFAULT_ENABLED);
  const [showDemoTargets, setShowDemoTargets] = useState(true);
  const [showDemoRoute, setShowDemoRoute] = useState(true);
  const [selected, setSelected] = useState<ScienceTarget | null>(DEMO_TARGETS[0] ?? null);
  const [coords, setCoords] = useState<{ x: number; y: number } | null>(null);
  const [terrain, setTerrain] = useState<TerrainPoint | null>(null);
  const [terrainLoading, setTerrainLoading] = useState(false);
  const [terrainError, setTerrainError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    endpoints
      .layers("gale_crater")
      .then((response) => {
        if (response.items && response.items.length) setLayers(response.items);
        setError(null);
      })
      .catch((reason) => setError(apiErrorMessage(reason)))
      .finally(() => setLoading(false));
  }, [reloadKey]);

  useEffect(() => {
    if (!coords) return;
    let active = true;
    setTerrainLoading(true);
    setTerrainError(null);
    endpoints
      .terrain("gale_crater", coords.x, coords.y)
      .then((response) => {
        if (!active) return;
        setTerrain({
          elevation_m: response.values.elevation_m,
          slope_deg: response.values.slope_deg,
          roughness: response.values.roughness,
          availability: response.availability,
        });
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
    setShowDemoRoute(true);
  };

  const tileLayers = layers.filter((layer) => layer.id in LAYER_TILE_URLS && layer.id !== "mars_trek_mola_colorshade");
  const overlayLayers = layers.filter((layer) => Boolean(layer.overlay_url));
  const unavailableLayers = layers.filter((layer) => layer.availability === "unavailable");
  const availableCount = layers.filter((layer) => layer.availability !== "unavailable").length;

  const markerIcon = useCallback(
    () =>
      L.divIcon({
        className: "",
        html: '<div style="width:14px;height:14px;border-radius:50%;background:#55C7D9;border:2px solid #F3F0EC;box-shadow:0 0 0 3px rgba(85,199,217,0.18)"></div>',
        iconSize: [14, 14],
      }),
    [],
  );

  return (
    <div className="flex flex-col gap-4 lg:h-[calc(100vh-10.75rem)] lg:min-h-[560px]">
      <PageHeader
        eyebrow="Surface workspace"
        title="Interactive Martian Map"
        description="NASA Mars Trek imagery and locally processed MOLA overlays. Basemaps are observed; slope and roughness are derived. The coordinate grid is a prototype CRS."
        meta={
          <>
            <StatusPill tone="observed">MOLA basemap</StatusPill>
            <StatusPill tone="derived">Local analysis</StatusPill>
            <StatusPill tone="simulated">Prototype CRS</StatusPill>
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

          <MapContainer
            crs={MarsCRS}
            center={[-5.4, 137.4]}
            zoom={5}
            minZoom={0}
            maxZoom={8}
            style={{ height: "100%", width: "100%", background: "#14100c" }}
            zoomControl={false}
            attributionControl
            className="dhruvion-map"
          >
            {enabled.mars_trek_mola_colorshade && (
              <TileLayer
                url={MOLA_BASEMAP_URL}
                attribution={MOLA_ATTRIBUTION}
                tileSize={256}
                maxZoom={8}
              />
            )}
            {tileLayers
              .filter((layer) => enabled[layer.id])
              .map((layer) => (
                <TileLayer
                  key={layer.id}
                  url={LAYER_TILE_URLS[layer.id]}
                  attribution="NASA Mars Trek"
                  tileSize={256}
                  maxZoom={LAYER_MAX_ZOOM[layer.id] ?? 8}
                />
              ))}
            {overlayLayers
              .filter((layer) => enabled[layer.id])
              .map((layer) => (
                <ImageOverlay
                  key={layer.id}
                  url={`${API_ORIGIN}${layer.overlay_url}`}
                  bounds={GALE_BOUNDS}
                  opacity={0.62}
                />
              ))}

            {showDemoRoute && (
              <Polyline
                positions={DEMO_ROUTE_COORDS.map(([x, y]) => [y, x]) as L.LatLngExpression[]}
                pathOptions={{ color: "#F06B3D", weight: 3, opacity: 0.9, dashArray: "1 0" }}
              />
            )}

            {showDemoTargets &&
              DEMO_TARGETS.map((target) => (
                <Marker
                  key={target.id}
                  position={[target.geometry.coordinates[1], target.geometry.coordinates[0]]}
                  icon={markerIcon()}
                  title={`${target.name} (simulated target)`}
                  eventHandlers={{ click: () => setSelected(target) }}
                />
              ))}

            <MapClick setCoords={setCoords} />
            <MapControls />
            <MapReadout coordinate={coords} />
          </MapContainer>

          <div className="pointer-events-none absolute left-3 top-3 z-[900] flex flex-wrap items-center gap-1.5">
            <span className="rounded border border-line/80 bg-black/65 px-2 py-1 text-[9px] uppercase tracking-[0.1em] text-text-secondary backdrop-blur-sm">
              Gale Crater · Mars
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
            description={`${availableCount} of ${layers.length || 11} catalogued layers available in this build.`}
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
                name="Mars Trek MOLA Color-Shaded Relief"
                meta="Observed · 463 m/px"
                enabled={Boolean(enabled.mars_trek_mola_colorshade)}
                onToggle={() => toggle("mars_trek_mola_colorshade")}
                tone="observed"
              />
              {tileLayers.map((layer) => (
                <LayerRow
                  key={layer.id}
                  name={layer.name}
                  meta={`${layer.status} · ${
                    layer.resolution_m ? `${layer.resolution_m} m/px` : layer.layer_type
                  }`}
                  enabled={Boolean(enabled[layer.id])}
                  onToggle={() => toggle(layer.id)}
                  tone={layer.status === "derived" ? "derived" : "observed"}
                  title={layer.warnings?.join(" ")}
                />
              ))}
            </LayerGroup>

            <LayerGroup title="Local analysis overlays">
              {overlayLayers.map((layer) => (
                <LayerRow
                  key={layer.id}
                  name={layer.name}
                  meta={`${layer.status} · ${layer.resolution_m ?? "—"} m/px`}
                  enabled={Boolean(enabled[layer.id])}
                  onToggle={() => toggle(layer.id)}
                  tone={layer.status === "derived" ? "derived" : "observed"}
                  title={layer.warnings?.join(" ")}
                />
              ))}
              {overlayLayers.length === 0 && (
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
                meta="simulated · 3 points"
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

          <SectionCard eyebrow="Map key" title="Legend" bodyClassName="p-3.5">
            <ul className="space-y-2 text-[11px]">
              <LegendItem color="#F06B3D" label="Simulated traverse" />
              <LegendItem color="#55C7D9" label="Simulated science target" dot />
              <LegendItem color="#D9A06A" label="Derived elevation overlay" fill />
              <LegendItem color="#E45C5C" label="Hazard overlay (unavailable)" muted />
            </ul>
            <p className="mt-3 border-t border-line/50 pt-2 text-[10px] leading-relaxed text-text-muted">
              Unavailable layers remain disabled and are never rendered as empty safe terrain.
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
                  <Value label="Elev" value={terrain?.elevation_m} unit="m" />
                  <Value label="Slope" value={terrain?.slope_deg} unit="°" />
                  <Value label="Rough" value={terrain?.roughness} unit="" />
                </div>
                <div className="mt-2 text-[9px] uppercase tracking-[0.08em] text-text-muted">
                  Prototype grid x {coords.x.toFixed(2)} · y {coords.y.toFixed(2)}
                </div>
                {terrainError && (
                  <p className="mt-1.5 text-[10px] text-critical-red">{terrainError}</p>
                )}
              </div>
            ) : (
              <p className="mb-3 rounded-control border border-dashed border-line/70 px-2.5 py-2 text-[10px] leading-relaxed text-text-muted">
                Click the map to query the local MOLA raster. Values are unavailable outside
                coverage.
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
                  <StatusPill tone="neutral" dot={false}>
                    Target actions pending API
                  </StatusPill>
                </div>
              </div>
            ) : (
              <EmptyState
                title="No feature selected"
                description="Select a simulated target marker to inspect its catalogue record."
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

function MapClick({ setCoords }: { setCoords: (coords: { x: number; y: number }) => void }) {
  const map = useMap();
  useEffect(() => {
    const handler = (event: L.LeafletMouseEvent) => {
      setCoords({ x: event.latlng.lng, y: event.latlng.lat });
    };
    map.on("click", handler);
    return () => {
      map.off("click", handler);
    };
  }, [map, setCoords]);
  return null;
}

function MapControls() {
  const map = useMap();
  return (
    <div className="absolute right-3 top-14 z-[1000] flex flex-col overflow-hidden rounded-control border border-line/80 bg-surface1/90 backdrop-blur-sm">
      <MapButton label="Zoom in" onClick={() => map.zoomIn()}>
        <Plus size={15} />
      </MapButton>
      <MapButton label="Zoom out" onClick={() => map.zoomOut()}>
        <Minus size={15} />
      </MapButton>
      <MapButton label="Recenter on Gale Crater" onClick={() => map.setView([-5.4, 137.4], 5)}>
        <Crosshair size={15} />
      </MapButton>
      <MapButton label="Fit Mars" onClick={() => map.fitBounds(MARS_BOUNDS)}>
        <Layers size={15} />
      </MapButton>
    </div>
  );
}

function MapButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="grid h-8 w-8 place-items-center border-b border-line/60 text-text-secondary transition-colors last:border-b-0 hover:bg-surface3 hover:text-text-primary"
    >
      {children}
    </button>
  );
}

function MapReadout({ coordinate }: { coordinate: { x: number; y: number } | null }) {
  const map = useMap();
  const [view, setView] = useState(() => ({
    zoom: map.getZoom(),
    lat: map.getCenter().lat,
    lng: map.getCenter().lng,
  }));

  useEffect(() => {
    const update = () =>
      setView({ zoom: map.getZoom(), lat: map.getCenter().lat, lng: map.getCenter().lng });
    map.on("moveend zoomend", update);
    update();
    return () => {
      map.off("moveend zoomend", update);
    };
  }, [map]);

  return (
    <div className="pointer-events-none absolute bottom-6 left-3 z-[900] rounded border border-line/80 bg-black/65 px-2 py-1 text-[9px] uppercase tracking-[0.08em] text-text-secondary backdrop-blur-sm">
      <span className="tabular">
        {coordinate ? `x ${coordinate.x.toFixed(2)} · y ${coordinate.y.toFixed(2)}` : "Click map for point query"}
      </span>
      <span className="mx-1.5 text-text-muted">/</span>
      <span className="tabular text-text-muted">
        z{view.zoom} · {view.lat.toFixed(2)}°, {view.lng.toFixed(2)}°
      </span>
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
