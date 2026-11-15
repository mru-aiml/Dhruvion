import { useMemo, useState } from "react";
import {
  ChevronDown,
  Crosshair,
  Eye,
  Filter,
  Layers,
  MapPin,
  Mountain,
  Search,
  SlidersHorizontal,
  Target,
  X,
} from "lucide-react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import PageHeader from "../../components/common/PageHeader";
import SectionCard from "../../components/common/SectionCard";
import StatusPill from "../../components/common/StatusPill";
import Button from "../../components/common/Button";

import { SelectInput, TextInput } from "../../components/common/Field";
import { EmptyState } from "../../components/common/States";
import { ProvenanceBadge, SimulatedLabel } from "../../components/common/StatusBadge";
import {
  MOLA_ATTRIBUTION,
  MOLA_BASEMAP_URL,
  GALE_BOUNDS,
} from "../../components/map/mars";
import { MarsMap } from "../../components/map/MarsMap";
import { DEMO_TARGETS } from "../../data/demo";
import type { ScienceTarget } from "../../types";

type PriorityFilter = "all" | "high" | "medium" | "low";
type VisitedFilter = "all" | "visited" | "unvisited";

const MAP_CENTER: [number, number] = [-5.4, 137.6];

function createTargetIcon(selected: boolean) {
  const size = selected ? 20 : 14;
  return L.divIcon({
    className: "",
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${
      selected ? "#F06B3D" : "#55C7D9"
    };border:2px solid ${selected ? "#F3F0EC" : "#0e0c0a"};box-shadow:0 0 0 3px ${
      selected ? "rgba(240,107,61,0.22)" : "rgba(85,199,217,0.18)"
    }"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const TARGET_ICON = createTargetIcon(false);
const SELECTED_TARGET_ICON = createTargetIcon(true);

export default function ScienceExplorerPage() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");
  const [visitedFilter, setVisitedFilter] = useState<VisitedFilter>("all");

  const [selected, setSelected] = useState<ScienceTarget | null>(DEMO_TARGETS[0] ?? null);

  const types = useMemo(
    () =>
      Array.from(
        new Set(DEMO_TARGETS.map((target) => target.feature_type).filter(Boolean)),
      ) as string[],
    [],
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return DEMO_TARGETS.filter((target) => {
      if (needle) {
        const haystack = [
          target.name,
          target.feature_type ?? "",
          target.description ?? "",
          target.source_name ?? "",
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      if (typeFilter !== "all" && target.feature_type !== typeFilter) return false;
      if (priorityFilter !== "all") {
        const priority = target.priority ?? 0;
        if (priorityFilter === "high" && priority < 0.8) return false;
        if (priorityFilter === "medium" && (priority < 0.5 || priority >= 0.8)) return false;
        if (priorityFilter === "low" && priority >= 0.5) return false;
      }
      if (visitedFilter === "visited" && !target.visited) return false;
      if (visitedFilter === "unvisited" && target.visited) return false;
      return true;
    });
  }, [query, typeFilter, priorityFilter, visitedFilter]);

  const filtersActive =
    query.trim() !== "" ||
    typeFilter !== "all" ||
    priorityFilter !== "all" ||
    visitedFilter !== "all";

  const clearFilters = () => {
    setQuery("");
    setTypeFilter("all");
    setPriorityFilter("all");
    setVisitedFilter("all");
  };

  // Handle map click to select target
  const handleMapClick = (lat: number, lng: number) => {
    // Find closest target
    let closest: ScienceTarget | null = null;
    let minDist = Infinity;
    for (const target of DEMO_TARGETS) {
      const [tLng, tLat] = target.geometry.coordinates;
      const dist = Math.hypot(lat - tLat, lng - tLng);
      if (dist < minDist) {
        minDist = dist;
        closest = target;
      }
    }
    if (closest && minDist < 0.05) { // ~5km threshold
      setSelected(closest);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Science workspace"
        title="Science Explorer"
        description="Inspect the demo geology catalogue for Gale Crater. Target records are simulated; the MOLA basemap is observed Mars Trek imagery and the elevation overlay is locally derived."
        meta={
          <>
            <StatusPill tone="simulated">Simulated catalogue</StatusPill>
            <StatusPill tone="observed">MOLA basemap</StatusPill>
            <StatusPill tone="derived">Elevation overlay</StatusPill>
            <StatusPill tone="neutral" dot={false}>
              <MapPin size={10} /> Gale Crater
            </StatusPill>
          </>
        }
      />

      <SectionCard
        eyebrow="Catalogue filters"
        title="Find a target"
        actions={
          <span className="text-[10px] uppercase tracking-[0.1em] text-text-muted">
            <span className="tabular text-text-secondary">{filtered.length}</span> of{" "}
            {DEMO_TARGETS.length} targets
          </span>
        }
        bodyClassName="p-3.5"
      >
        <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-[minmax(0,1.7fr)_repeat(3,minmax(0,1fr))_auto] xl:items-end">
          <label className="block min-w-0">
            <span className="mb-1 block text-[9px] uppercase tracking-[0.12em] text-text-muted">
              Search
            </span>
            <span className="relative block">
              <Search
                size={13}
                aria-hidden
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
              />
              <TextInput
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Name, feature type, source…"
                className="pl-8"
                aria-label="Search science targets"
              />
            </span>
          </label>

          <SelectField label="Feature type" icon={<Filter size={11} />}>
            <SelectInput
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
              aria-label="Filter by feature type"
            >
              <option value="all">All features</option>
              {types.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </SelectInput>
          </SelectField>

          <SelectField label="Priority" icon={<SlidersHorizontal size={11} />}>
            <SelectInput
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value as PriorityFilter)}
              aria-label="Filter by priority"
            >
              <option value="all">Any priority</option>
              <option value="high">High (≥ 0.80)</option>
              <option value="medium">Medium (0.50–0.79)</option>
              <option value="low">Low (&lt; 0.50)</option>
            </SelectInput>
          </SelectField>

          <SelectField label="Visit state" icon={<Eye size={11} />}>
            <SelectInput
              value={visitedFilter}
              onChange={(event) => setVisitedFilter(event.target.value as VisitedFilter)}
              aria-label="Filter by visit state"
            >
              <option value="all">Any state</option>
              <option value="visited">Visited</option>
              <option value="unvisited">Unvisited</option>
            </SelectInput>
          </SelectField>

          <Button
            variant="ghost"
            size="md"
            icon={<X size={13} />}
            onClick={clearFilters}
            disabled={!filtersActive}
            className="h-[38px]"
          >
            Clear
          </Button>
        </div>
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        <SectionCard
          eyebrow="Target list"
          title="Catalogue entries"
          actions={
            <StatusPill tone="simulated">
              {filtered.length} match{filtered.length === 1 ? "" : "es"}
            </StatusPill>
          }
          bodyClassName="p-2.5"
        >
          <div className="dash-scroll max-h-[560px] space-y-2 overflow-y-auto pr-1 xl:max-h-[calc(100vh-19rem)]">
            {filtered.map((target) => {
              const active = selected?.id === target.id;
              return (
                <button
                  key={target.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setSelected(target)}
                  className={`group relative flex w-full items-start gap-3 overflow-hidden rounded-control border p-2.5 text-left transition-colors duration-150 ${
                    active
                      ? "border-mars-orange bg-mars-orange/[0.06]"
                      : "border-line/70 bg-surface1 hover:border-amber/50 hover:bg-surface2"
                  }`}
                >
                  {active && (
                    <span aria-hidden className="absolute inset-y-0 left-0 w-0.5 bg-mars-orange" />
                  )}
                  <span
                    className={`grid h-9 w-9 shrink-0 place-items-center rounded-control border ${
                      active
                        ? "border-mars-orange/45 bg-mars-orange/10 text-mars-orange"
                        : "border-line bg-surface2 text-text-muted group-hover:text-text-secondary"
                    }`}
                  >
                    <Target size={15} aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-start justify-between gap-2">
                      <span className="truncate text-[12px] font-medium text-text-primary">
                        {target.name}
                      </span>
                      <span className="shrink-0 text-[9px] tabular text-text-muted">
                        {formatPriority(target.priority)}
                      </span>
                    </span>
                    <span className="mt-0.5 block truncate text-[9px] uppercase tracking-[0.08em] text-text-muted">
                      {target.feature_type ?? "Unclassified"}
                    </span>
                    <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <span
                        className={`inline-flex items-center rounded border px-1 py-0.5 text-[8px] font-medium uppercase tracking-[0.08em] ${
                          target.visited
                            ? "border-cyan/30 bg-cyan/[0.06] text-cyan"
                            : "border-line bg-surface2 text-text-muted"
                        }`}
                      >
                        {target.visited ? "Visited" : "Unvisited"}
                      </span>
                      <span className="text-[9px] tabular text-text-muted">
                        {target.distance_m
                          ? `${(target.distance_m / 1000).toFixed(2)} km`
                          : "Distance —"}
                      </span>
                    </span>
                  </span>
                </button>
              );
            })}

            {filtered.length === 0 && (
              <EmptyState
                title="No targets match"
                description="Adjust the search text or filters to widen the catalogue."
                icon={<Search size={18} aria-hidden />}
                action={
                  <Button variant="secondary" size="sm" onClick={clearFilters}>
                    Clear filters
                  </Button>
                }
                className="my-2"
              />
            )}
          </div>
          <div className="mt-2 flex items-center gap-1.5 border-t border-line/50 px-1 pt-2 text-[9px] uppercase tracking-[0.08em] text-text-muted">
            <Mountain size={10} aria-hidden />
            Demo catalogue · simulated records
          </div>
        </SectionCard>

        <div className="min-w-0 space-y-4">
          <SectionCard
            eyebrow="Terrain preview"
            title="Gale Crater surface"
            actions={
              <>
                <StatusPill tone="observed">Basemap</StatusPill>
              </>
            }
            flush
          >
            <div className="relative h-[280px] sm:h-[340px]">
              <div aria-hidden className="pointer-events-none absolute inset-2 z-[500]">
                <span className="absolute left-0 top-0 h-4 w-4 border-l border-t border-mars-orange/70" />
                <span className="absolute right-0 top-0 h-4 w-4 border-r border-t border-mars-orange/70" />
                <span className="absolute bottom-0 left-0 h-4 w-4 border-b border-l border-mars-orange/70" />
                <span className="absolute bottom-0 right-0 h-4 w-4 border-b border-r border-mars-orange/70" />
              </div>

              <div className="pointer-events-none absolute left-3 top-3 z-[900] rounded border border-line/80 bg-black/65 px-2 py-1 backdrop-blur-sm">
                <div className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
                  Gale Crater · Aeolis Mons
                </div>
                <div className="text-[10px] font-medium text-text-primary">
                  5.4°S · 137.8°E
                </div>
              </div>

              <MarsMap
                center={MAP_CENTER}
                zoom={7}
                minZoom={0}
                maxZoom={8}
                scrollWheelZoom={false}
                zoomControl={false}
                attributionControl={true}
                containerHeight="100%"
                tileLayers={[
                  {
                    id: "mola_basemap",
                    url: MOLA_BASEMAP_URL,
                    attribution: MOLA_ATTRIBUTION,
                    maxZoom: 8,
                    tileSize: 256,
                    visible: true,
                  },
                ]}
                markers={DEMO_TARGETS.map((target) => {
                  const active = selected?.id === target.id;
                  return {
                    id: target.id,
                    position: [
                      target.geometry.coordinates[1],
                      target.geometry.coordinates[0],
                    ] as [number, number],
                    icon: active ? SELECTED_TARGET_ICON : TARGET_ICON,
                    title: `${target.name} (simulated target)`,
                    onClick: () => setSelected(target),
                  };
                })}
                onMapClick={handleMapClick}
                fitBounds={GALE_BOUNDS}
              />

              <div className="pointer-events-none absolute bottom-2 right-2 z-[900] flex flex-wrap items-center gap-1 bg-black/60 px-1.5 py-1 backdrop-blur-sm">
                <span className="text-[8px] uppercase tracking-[0.08em] text-text-muted">
                  NASA Mars Trek · MGS MOLA
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line/50 px-3.5 py-2.5">
              <p className="text-[10px] leading-relaxed text-text-muted">
                Hillshade is observed imagery; the elevation raster is derived from local MOLA
                processing. Markers are simulated catalogue points, not verified observations.
              </p>
              <div className="flex flex-wrap items-center gap-1.5">
                <StatusPill tone="simulated">Markers simulated</StatusPill>
                <StatusPill tone="derived">Elevation derived</StatusPill>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            eyebrow="Inspection"
            title={selected ? selected.name : "Target inspection"}
            actions={<SimulatedLabel />}
            bodyClassName="p-4"
          >
            {selected ? (
              <div className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
                  <div className="min-w-0 rounded-control border border-line/70 bg-surface2/40 p-4 text-center text-xs text-text-muted">
                    No mission imagery available for this simulated target. The map displays the NASA Mars Trek MOLA colour hillshade basemap; catalogue markers are simulated and are not verified observations.
                  </div>

                  <dl className="grid grid-cols-2 gap-x-3 gap-y-2.5 lg:grid-cols-1">
                    <InspectorRow label="Feature type" value={selected.feature_type ?? "—"} />
                    <InspectorRow
                      label="Coordinates"
                      value={`${selected.geometry.coordinates[0].toFixed(2)}, ${selected.geometry.coordinates[1].toFixed(2)}`}
                    />
                    <InspectorRow
                      label="Distance"
                      value={
                        selected.distance_m
                          ? `${(selected.distance_m / 1000).toFixed(2)} km`
                          : "—"
                      }
                    />
                    <InspectorRow label="Visit state" value={selected.visited ? "Visited" : "Unvisited"} />
                    <InspectorRow label="Source" value={selected.source_name ?? "—"} />
                    <InspectorRow label="Coordinate CRS" value={selected.coordinate_crs} />
                  </dl>
                </div>

                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[9px] uppercase tracking-[0.12em] text-text-muted">
                      Priority score
                    </span>
                    <span className="text-[11px] tabular text-text-secondary">
                      {formatPriority(selected.priority)}
                    </span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface3">
                    <div
                      className="h-full rounded-full bg-mars-orange"
                      style={{ width: `${Math.round((selected.priority ?? 0) * 100)}%` }}
                    />
                  </div>
                </div>

                <div className="border-t border-line/50 pt-3">
                  <div className="text-[9px] uppercase tracking-[0.12em] text-text-muted">
                    Description
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                    {selected.description ?? "No description provided."}
                  </p>
                </div>

                {selected.interpretation && (
                  <div className="rounded-control border border-amber/30 bg-amber/[0.05] p-2.5">
                    <div className="text-[9px] font-semibold uppercase tracking-[0.12em] text-amber">
                      Interpretation · not observed
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-text-secondary">
                      {selected.interpretation}
                    </p>
                  </div>
                )}

                {(selected.warnings?.length > 0 || selected.provenance.length > 0) && (
                  <div className="flex flex-wrap items-center gap-2 border-t border-line/50 pt-3">
                    {selected.provenance.map((entry) => (
                      <ProvenanceBadge key={entry} status={entry} />
                    ))}
                    {selected.warnings?.map((warning) => (
                      <span
                        key={warning}
                        className="text-[10px] leading-relaxed text-text-muted"
                      >
                        {warning}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line/50 pt-3">
                  <p className="max-w-sm text-[10px] leading-relaxed text-text-muted">
                    Target actions require a verified science target API. None is connected in
                    this build.
                  </p>
                  <Button
                    variant="ghost"
                    size="md"
                    disabled
                    title="Target actions require a verified science target API"
                    icon={<Crosshair size={13} />}
                  >
                    Add to traverse
                  </Button>
                </div>
              </div>
            ) : (
              <EmptyState
                title="No target selected"
                description="Select a catalogue entry or a simulated map marker to inspect it."
                icon={<Layers size={18} aria-hidden />}
              />
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

function SelectField({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <label className="block min-w-0">
      <span className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-[0.12em] text-text-muted">
        {icon} {label}
      </span>
      <span className="relative block">
        {children}
        <ChevronDown
          size={13}
          aria-hidden
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted"
        />
      </span>
    </label>
  );
}

function InspectorRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[9px] uppercase tracking-[0.1em] text-text-muted">{label}</dt>
      <dd className="mt-0.5 truncate text-[11px] tabular text-text-secondary">{value}</dd>
    </div>
  );
}

function formatPriority(priority: number | null) {
  return priority === null || priority === undefined ? "—" : priority.toFixed(2);
}