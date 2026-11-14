// Shared domain types mirroring api.md contracts.

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
  bounds?: unknown;
  acquired_at?: string | null;
  processed_at?: string | null;
  overlay_url?: string | null;
  warnings?: string[];
}

export interface Region {
  id: string;
  name: string;
  body: string;
  crs: string;
  availability: Availability;
}

export interface TerrainValue {
  elevation_m: number | null;
  slope_deg: number | null;
  roughness: number | null;
}

export interface TerrainQueryResponse {
  region_id: string;
  coordinate: Coordinate;
  values: TerrainValue;
  provenance: ProvenanceStatus[];
  availability: Availability;
  warnings: string[];
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
}

export interface RouteOptimizeResponse {
  region_id: string;
  routes: Route[];
  algorithm?: { name: string; version: string; cost_model: Record<string, unknown> };
}

export interface TimeBudget {
  outbound_min: number | null;
  exploration_min: number | null;
  return_min: number | null;
  reserve_min: number | null;
  total_min: number | null;
  limit_min: number | null;
}

export interface MissionPlanResponse {
  mission_id: string;
  route: Route | Record<string, unknown>;
  time_budget: TimeBudget;
  feasibility_status: FeasibilityStatus;
  reasons: string[];
  assumptions: string[];
  warnings: string[];
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
}

export interface AssistantToolActivity {
  tool: string;
  status: string;
}

export interface AssistantResponse {
  message: string;
  intent: string;
  recommendation?: unknown;
  tool_activity: AssistantToolActivity[];
  evidence: unknown[];
  warnings: string[];
  sources: unknown[];
  actions: string[];
}

export interface ReportResponse {
  report_id: string;
  format: string;
  status: string;
  download_url: string | null;
  provenance: ProvenanceStatus[];
  warnings: string[];
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ApiError {
  error: { code: string; message: string; details?: Record<string, unknown> };
  request_id?: string;
}
