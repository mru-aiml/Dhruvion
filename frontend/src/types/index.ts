// Shared domain types mirroring api.md and the DHRUVION NASA dataset contracts.

export type ProvenanceStatus = "observed" | "derived" | "simulated" | "unavailable";
export type Availability = "available" | "partial" | "unavailable" | "stale";
export type FeasibilityStatus = "feasible" | "caution" | "not_feasible" | "unverified";
export type RouteStrategy = "shortest" | "safest_estimated" | "balanced";

export interface Coordinate {
  x: number;
  y: number;
  crs: string;
}

export interface DataSource {
  name?: string | null;
  provider?: string | null;
  product_id?: string | null;
  source_uri?: string | null;
}

export interface BoundsLatLon {
  south: number;
  north: number;
  west: number;
  east: number;
}

export interface CoverageClass {
  class: number | null;
  label: string;
  bounds_latlon?: BoundsLatLon;
  resolution_m?: number | null;
  classes?: Record<string, string>;
}

export interface LayerBounds {
  bounds_latlon?: BoundsLatLon;
  leaflet_bounds?: [[number, number], [number, number]];
}

export interface LayerDisplay {
  png?: string;
  colormap?: string;
  units?: string;
  display_vmin?: number;
  display_vmax?: number;
  stretch?: string;
}

export interface LayerMeta {
  id: string;
  name: string;
  layer_type: string;
  status: ProvenanceStatus;
  availability: Availability;
  source?: DataSource;
  crs?: string | null;
  resolution_m?: number | null;
  units?: string | null;
  bounds?: LayerBounds | unknown;
  acquired_at?: string | null;
  processed_at?: string | null;
  overlay_url?: string | null;
  tile_url_template?: string | null;
  max_zoom?: number | null;
  imagery_type?: string | null;
  display?: LayerDisplay;
  warnings?: string[];
}

export interface Region {
  id: string;
  name: string;
  body: string;
  crs: string;
  availability: Availability;
  bounds_latlon?: BoundsLatLon;
  resolution_m?: number | null;
  latitude_type?: string;
  source?: DataSource | null;
  warnings?: string[];
}

export interface TerrainValue {
  elevation_m: number | null;
  slope_deg: number | null;
  roughness: number | null;
}

export interface TerrainUnits {
  elevation_m: string;
  slope_deg: string;
  roughness: string;
}

export interface TerrainQueryResponse {
  region_id: string;
  coordinate: Coordinate;
  values: TerrainValue;
  provenance: ProvenanceStatus[];
  availability: Availability;
  warnings: string[];
  units?: TerrainUnits;
  coverage?: CoverageClass;
  source?: DataSource;
  limitations?: string[];
  classification?: string;
}

export interface TerrainLayerPointResponse {
  layer: string;
  region_id: string;
  coordinate: Coordinate;
  value: number | string | null;
  field?: string;
  unit: string;
  label?: string;
  availability: Availability;
  coverage: CoverageClass;
  provenance: string;
  source?: DataSource;
  warnings: string[];
  limitations?: string[];
}

export interface TerrainProfilePoint {
  region_id: string;
  coordinate: Coordinate;
  values: TerrainValue;
  units?: TerrainUnits;
  coverage?: CoverageClass;
  provenance: ProvenanceStatus[];
  availability: Availability;
  source?: DataSource;
  warnings: string[];
  limitations?: string[];
  distance_m: number;
}

export interface TerrainProfileResponse {
  region_id: string;
  start: Coordinate;
  end: Coordinate;
  samples: number;
  distance_m: number;
  points: TerrainProfilePoint[];
}

export interface CoverageSummary {
  region_id: string;
  bounds_latlon: BoundsLatLon;
  resolution_m: number;
  total_cells: number;
  counts: Record<string, number>;
  percentages: Record<string, number>;
  classes: Record<string, string>;
  availability: Availability;
  provenance: string;
  source?: DataSource;
  warnings: string[];
  limitations: string[];
}

export interface HazardFeatureCollection {
  type: "FeatureCollection";
  features: unknown[];
}

export interface HazardsResponse {
  region_id: string;
  features: HazardFeatureCollection;
  summary: { identified_count: number; unknown_coverage: boolean };
  provenance: ProvenanceStatus[];
  warnings: string[];
}

export interface ScienceTarget {
  id: string;
  name: string;
  feature_type: string | null;
  geometry: { type: "Point"; coordinates: [number, number] };
  coordinate_crs: string;
  priority: number | null;
  description: string | null;
  interpretation: string | null;
  provenance: ProvenanceStatus[];
  warnings: string[];
  distance_m?: number | null;
  source_name?: string | null;
  visited?: boolean;
}

export interface TargetsResponse {
  region_id: string;
  items: ScienceTarget[];
  availability?: Availability;
  warnings?: string[];
}

export interface RouteMetrics {
  distance_m: number;
  estimated_duration_min: number | null;
  terrain_difficulty: number | null;
  hazard_count: number | null;
  mean_slope_deg?: number | null;
  max_slope_deg?: number | null;
  mean_roughness_m?: number | null;
  elevation_min_m?: number | null;
  elevation_max_m?: number | null;
  elevation_gain_m?: number | null;
  elevation_loss_m?: number | null;
  coverage_class_counts?: Record<string, number>;
  unknown_derivative_cells?: number;
  valid_derivative_cells?: number;
  cell_count?: number;
  feasibility_status?: FeasibilityStatus;
}

export interface Route {
  id: string;
  strategy: RouteStrategy;
  geometry: { type: "LineString"; coordinates: [number, number][] };
  distance_m: number;
  estimated_duration_min: number | null;
  terrain_difficulty: number | null;
  hazard_count: number | null;
  feasibility_status: FeasibilityStatus;
  rationale: string;
  provenance: ProvenanceStatus[];
  warnings: string[];
  start?: Coordinate;
  destination?: Coordinate;
  metrics?: RouteMetrics;
  coverage?: {
    start?: CoverageClass;
    destination?: CoverageClass;
    route_counts?: Record<string, number>;
  };
  assumptions?: string[];
  limitations?: string[];
  units?: Record<string, string>;
  source?: DataSource;
  classification?: string;
  algorithm?: Record<string, unknown>;
  mission_id?: string;
  role?: string;
}

export interface RouteOptimizeResponse {
  region_id: string;
  routes: Route[];
  algorithm?: { name: string; version: string; cost_model: Record<string, unknown> };
  warnings?: string[];
}

export interface TimeBudget {
  outbound_min: number | null;
  exploration_min: number | null;
  return_min: number | null;
  reserve_min: number | null;
  total_min: number | null;
  limit_min: number | null;
  remaining_after_plan_min?: number | null;
}

export interface MissionPlanResponse {
  mission_id: string;
  route: Route;
  time_budget: TimeBudget;
  feasibility_status: FeasibilityStatus;
  reasons: string[];
  assumptions: string[];
  warnings: string[];
  name?: string;
  region_id?: string;
  start?: Coordinate;
  destination?: Coordinate;
  route_strategy?: string;
  travel_speed_m_per_min?: number;
  coverage?: Record<string, unknown>;
  limitations?: string[];
  classification?: string;
  source?: DataSource;
  provenance?: ProvenanceStatus[];
  created_at?: string;
}

export interface ReturnFeasibilityResponse {
  return_route: Route | Record<string, unknown>;
  estimated_return_min: number | null;
  remaining_time_min: number;
  reserve_time_min: number;
  feasibility_status: FeasibilityStatus;
  reasons: string[];
  warnings: string[];
}

export interface RerouteResponse {
  original_route_id: string;
  alternative_route: Route | Record<string, unknown>;
  distance_delta_m: number | null;
  duration_delta_min: number | null;
  feasibility_status: FeasibilityStatus;
  scenario_status: "observed" | "simulated";
  reason: string;
  provenance: ProvenanceStatus[];
  warnings: string[];
  mission_id?: string;
  limitations?: string[];
  classification?: string;
  source?: DataSource;
}

export interface AssistantToolActivity {
  tool: string;
  status: string;
  arguments?: Record<string, unknown>;
  duration_ms?: number | null;
  error?: string | null;
}

export interface AssistantObservation {
  tool: string;
  label: string;
  value: unknown;
  unit?: string | null;
  provenance?: string | null;
  source?: string | null;
  coverage?: string | null;
}

export interface AssistantConfidence {
  level: string;
  basis: string;
  limitations: string[];
}

export interface AssistantResponse {
  // Original contract fields.
  message: string;
  intent: string;
  recommendation?: unknown;
  tool_activity: AssistantToolActivity[];
  evidence: unknown[];
  warnings: string[];
  sources: unknown[];
  actions: string[];

  // Additive structured fields used by the integrated assistant UI.
  answer?: string;
  tools_used?: string[];
  observations?: AssistantObservation[];
  units?: Record<string, string>;
  limitations?: string[];
  confidence?: AssistantConfidence;
  fallback?: boolean;
  model?: string | null;
  mission_id?: string | null;
  grounding?: Record<string, unknown>;
}

export interface AssistantHealthResponse {
  status: string;
  llm_enabled: boolean;
  provider: string;
  model: string;
  available: boolean;
  base_url?: string | null;
  error?: string | null;
  tools: string[];
  fallback_available: boolean;
}

export interface DatasetEntry {
  dataset_id: string;
  name: string;
  dataset_type: string;
  format: string;
  status: string;
  provenance: string;
  file_path: string;
  metadata_path?: string | null;
  crs?: string | null;
  coverage?: { bounds_latlon?: BoundsLatLon; resolution_m?: number | null };
  resolution_m?: number | null;
  file_size_bytes?: number | null;
  feature_count?: number | null;
  geometry_types?: string[];
  warnings?: string[];
  metadata?: Record<string, unknown>;
}

export interface DatasetCatalogResponse {
  catalog_version: number;
  generated_at: string;
  datasets: DatasetEntry[];
  statistics: Record<string, unknown>;
}

export interface ImageryLayerInfo {
  name: string;
  tile_url_template: string;
  max_zoom: number;
  source?: DataSource;
}

export interface CtxImagery {
  available: boolean;
  id: string;
  name: string;
  layer_type: string;
  provenance: string;
  units: string;
  projection: string;
  latitude_type: string;
  longitude_direction: string;
  bounds: LayerBounds;
  resolution_m: number;
  overlay_url: string;
  geotiff?: string;
  alignment_with_dem?: Record<string, unknown>;
  partial_coverage: boolean;
  display?: LayerDisplay;
  source?: DataSource;
  warnings: string[];
  limitations: string[];
}

export interface ImageryResponse {
  region_id: string;
  ctx: CtxImagery;
  tiles: Record<string, ImageryLayerInfo>;
  warnings: string[];
  limitations: string[];
}

export interface RemsMeasurement {
  measurement: string;
  label: string;
  quantity?: string;
  unit: string;
  filter: string;
  n_rows: number;
  n_valid: number;
  n_missing: number;
  mean: number | null;
  min: number | null;
  max: number | null;
  median: number | null;
  std: number | null;
}

export interface RemsWindSummary {
  sol: number;
  speed: {
    availability: string;
    n_valid: number;
    unit: string;
    mean: number | null;
    min: number | null;
    max: number | null;
  };
  direction: {
    availability: string;
    n_valid: number;
    unit: string;
    mean: number | null;
    min: number | null;
    max: number | null;
    circular?: {
      circular_mean_deg: number;
      resultant_length: number;
      n_directions: number;
    };
  };
  provenance: string;
  note: string;
}

export interface RemsResponse {
  instrument: string;
  region_id: string;
  availability: Availability;
  observation_type: string;
  sols: number[];
  default_filter: string;
  location: { name: string; type: string; note: string };
  units: Record<string, string>;
  measurements: Record<string, Record<string, RemsMeasurement>>;
  wind: Record<string, RemsWindSummary>;
  trends: Array<Record<string, unknown>>;
  coverage: Record<string, unknown>;
  provenance: string;
  source?: DataSource;
  warnings: string[];
  limitations: string[];
}

export interface RadSolSummary {
  sol: number;
  n_observations: number;
  n_valid: number;
  n_missing: number;
  mean: number | null;
  min: number | null;
  max: number | null;
  median: number | null;
  std: number | null;
  utc_first?: string;
  utc_last?: string;
}

export interface RadDetectorSummary {
  measurement: string;
  detector: string;
  unit: string;
  filter: string;
  sols: Record<string, RadSolSummary>;
}

export interface RadiationResponse {
  instrument: string;
  region_id: string;
  availability: Availability;
  observation_type: string;
  sols: number[];
  detectors: Record<string, RadDetectorSummary>;
  unit: string;
  trends: Array<Record<string, unknown>>;
  location: { name: string; type: string; note: string };
  coverage: Record<string, unknown>;
  provenance: string;
  source?: DataSource;
  warnings: string[];
  limitations: string[];
}

export interface ReportResponse {
  report_id: string;
  format: string;
  status: string;
  download_url: string | null;
  provenance: ProvenanceStatus[];
  warnings: string[];
  mission_id?: string | null;
  generated_at?: string | null;
  content?: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface MissionCoordinate {
  x: number;
  y: number;
}

export interface MissionRecord {
  id: string;
  name: string;
  description: string | null;
  region_id: string;
  mission_type: string;
  start: MissionCoordinate;
  destination: MissionCoordinate;
  time_budget_min: number;
  available_sols: number | null;
  objectives: string[];
  notes: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface MissionCreateRequest {
  name: string;
  description?: string | null;
  region_id?: string;
  mission_type?: string;
  start: MissionCoordinate;
  destination: MissionCoordinate;
  time_budget_min: number;
  available_sols?: number | null;
  objectives?: string[];
  notes?: string | null;
  status?: string;
}

export interface MissionRouteRecord {
  id: string;
  mission_id: string;
  strategy: string;
  geometry: [number, number][];
  distance_m: number | null;
  estimated_duration_min: number | null;
  terrain_difficulty: number | null;
  max_slope_deg: number | null;
  feasibility: string | null;
  parameters: Record<string, unknown>;
  created_at: string;
}

export interface MissionRouteCreateRequest {
  strategy: string;
  geometry: [number, number][];
  distance_m?: number | null;
  estimated_duration_min?: number | null;
  terrain_difficulty?: number | null;
  max_slope_deg?: number | null;
  feasibility?: string | null;
  parameters?: Record<string, unknown>;
}

export interface MissionUpdateRequest {
  name?: string;
  description?: string | null;
  region_id?: string;
  mission_type?: string;
  start?: MissionCoordinate;
  destination?: MissionCoordinate;
  time_budget_min?: number;
  available_sols?: number | null;
  objectives?: string[];
  notes?: string | null;
  status?: string;
}

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}
