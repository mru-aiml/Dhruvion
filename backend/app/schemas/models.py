from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Region(BaseModel):
    id: str
    name: str
    body: str
    crs: str
    availability: str


class Source(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    product_id: Optional[str] = None
    source_uri: Optional[str] = None


class Layer(BaseModel):
    id: str
    name: str
    layer_type: str
    status: str
    availability: str
    source: Source = Source()
    crs: Optional[str] = None
    resolution_m: Optional[float] = None
    units: Optional[str] = None
    bounds: Optional[Any] = None
    acquired_at: Optional[str] = None
    processed_at: Optional[str] = None
    overlay_url: Optional[str] = None
    warnings: List[str] = []


class Coordinate(BaseModel):
    x: float
    y: float
    crs: str


class TerrainValue(BaseModel):
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    roughness: Optional[float] = None


class TerrainResponse(BaseModel):
    region_id: str
    coordinate: Coordinate
    values: TerrainValue
    provenance: List[str] = []
    availability: str
    warnings: List[str] = []


class HazardFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[Any] = []


class HazardsResponse(BaseModel):
    region_id: str
    features: HazardFeatureCollection
    summary: Dict[str, Any]
    provenance: List[str] = []
    warnings: List[str] = []


class ScienceTarget(BaseModel):
    id: str
    name: str
    feature_type: Optional[str] = None
    geometry: Dict[str, Any]
    coordinate_crs: str
    priority: Optional[float] = None
    description: Optional[str] = None
    interpretation: Optional[str] = None
    provenance: List[str] = []
    warnings: List[str] = []
    distance_m: Optional[float] = None
    source_name: Optional[str] = None
    visited: Optional[bool] = None


class TargetsResponse(BaseModel):
    region_id: str
    items: List[ScienceTarget] = []


class RouteCoordinate(BaseModel):
    x: float
    y: float
    crs: str = "urn:ogc:def:crs:IAU2000::104905"


class RouteGeometry(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]


class Route(BaseModel):
    id: str
    strategy: str
    geometry: RouteGeometry
    distance_m: float
    estimated_duration_min: Optional[float] = None
    terrain_difficulty: Optional[float] = None
    hazard_count: Optional[int] = None
    feasibility_status: str
    rationale: str
    provenance: List[str] = []
    warnings: List[str] = []


class RouteOptimizeRequest(BaseModel):
    region_id: str = "gale_crater"
    start: RouteCoordinate
    destination: RouteCoordinate
    strategies: List[str] = Field(default=["shortest", "safest_estimated", "balanced"])
    max_difficulty: Optional[float] = None
    risk_weight: float = 1.0
    travel_speed_m_per_min: Optional[float] = None


class RouteOptimizeResponse(BaseModel):
    region_id: str
    routes: List[Route]
    algorithm: Dict[str, Any]


class TimeBudget(BaseModel):
    outbound_min: Optional[float] = None
    exploration_min: Optional[float] = None
    return_min: Optional[float] = None
    reserve_min: Optional[float] = None
    total_min: Optional[float] = None
    limit_min: Optional[float] = None


class MissionPlanRequest(BaseModel):
    mission_id: Optional[str] = None
    region_id: str = "gale_crater"
    start: RouteCoordinate
    destination: RouteCoordinate
    time_limit_min: float = 240
    exploration_time_min: float = 30
    reserve_time_min: float = 30
    travel_speed_m_per_min: Optional[float] = None
    route_strategy: str = "balanced"


class MissionPlanResponse(BaseModel):
    mission_id: str
    route: Route
    time_budget: TimeBudget
    feasibility_status: str
    reasons: List[str] = []
    assumptions: List[str] = []
    warnings: List[str] = []


class MissionReturnRequest(BaseModel):
    mission_id: str
    current_location: RouteCoordinate
    remaining_time_min: float
    reserve_time_min: float = 20


class ReturnFeasibilityResponse(BaseModel):
    return_route: Dict[str, Any]
    estimated_return_min: Optional[float] = None
    remaining_time_min: float
    reserve_time_min: float
    feasibility_status: str
    reasons: List[str] = []
    warnings: List[str] = []


class RerouteRequest(BaseModel):
    mission_id: str
    original_route_id: str
    blocked_geometry: Dict[str, Any]
    scenario_status: str = "simulated"
    remaining_time_min: float


class RerouteResponse(BaseModel):
    original_route_id: str
    alternative_route: Dict[str, Any]
    distance_delta_m: Optional[float] = None
    duration_delta_min: Optional[float] = None
    feasibility_status: str
    scenario_status: str
    reason: str
    provenance: List[str] = []
    warnings: List[str] = []


class AssistantToolActivity(BaseModel):
    tool: str
    status: str


class AssistantRequest(BaseModel):
    message: str
    mission_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    message: str
    intent: str
    recommendation: Optional[Dict[str, Any]] = None
    tool_activity: List[AssistantToolActivity] = []
    evidence: List[Any] = []
    warnings: List[str] = []
    sources: List[Any] = []
    actions: List[str] = []


class ReportRequest(BaseModel):
    mission_id: Optional[str] = None
    format: str = "json"


class ReportResponse(BaseModel):
    report_id: str
    format: str
    status: str
    download_url: Optional[str] = None
    provenance: List[str] = []
    warnings: List[str] = []


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ApiErrorResponse(BaseModel):
    error: Dict[str, Any]
    request_id: Optional[str] = None