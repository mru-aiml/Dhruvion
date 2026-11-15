from datetime import datetime
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
    units: Dict[str, str] = {}
    coverage: Optional[Dict[str, Any]] = None
    source: Optional[Dict[str, Any]] = None
    limitations: List[str] = []
    classification: Optional[str] = None


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
    start: Optional[Dict[str, Any]] = None
    destination: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = {}
    coverage: Optional[Dict[str, Any]] = None
    assumptions: List[str] = []
    limitations: List[str] = []
    units: Dict[str, str] = {}
    source: Optional[Dict[str, Any]] = None
    classification: Optional[str] = None
    algorithm: Optional[Dict[str, Any]] = None
    mission_id: Optional[str] = None
    role: Optional[str] = None


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
    warnings: List[str] = []


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
    name: Optional[str] = None
    region_id: Optional[str] = None
    start: Optional[Dict[str, Any]] = None
    destination: Optional[Dict[str, Any]] = None
    route_strategy: Optional[str] = None
    travel_speed_m_per_min: Optional[float] = None
    coverage: Optional[Dict[str, Any]] = None
    limitations: List[str] = []
    classification: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    provenance: List[str] = []
    created_at: Optional[str] = None


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
    strategy: str = "balanced"
    buffer_m: Optional[float] = None


class RerouteResponse(BaseModel):
    mission_id: Optional[str] = None
    original_route_id: str
    alternative_route: Dict[str, Any] = {}
    distance_delta_m: Optional[float] = None
    duration_delta_min: Optional[float] = None
    feasibility_status: str
    scenario_status: str
    reason: str
    provenance: List[str] = []
    warnings: List[str] = []
    limitations: List[str] = []
    classification: str = "DERIVED"
    source: Optional[Dict[str, Any]] = None


class Coordinate(BaseModel):
    x: float
    y: float


class MissionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    region_id: str = "gale_crater"
    mission_type: str = "traverse"
    start: Coordinate
    destination: Coordinate
    time_budget_min: float = Field(gt=0)
    available_sols: Optional[float] = Field(default=None, gt=0)
    objectives: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    status: str = "draft"


class MissionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    region_id: Optional[str] = None
    mission_type: Optional[str] = None
    start: Optional[Coordinate] = None
    destination: Optional[Coordinate] = None
    time_budget_min: Optional[float] = Field(default=None, gt=0)
    available_sols: Optional[float] = Field(default=None, gt=0)
    objectives: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class MissionRouteCreate(BaseModel):
    strategy: str = "balanced"
    geometry: List[List[float]]
    distance_m: Optional[float] = None
    estimated_duration_min: Optional[float] = None
    terrain_difficulty: Optional[float] = None
    max_slope_deg: Optional[float] = None
    feasibility: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class MissionRouteResponse(BaseModel):
    id: str
    mission_id: str
    strategy: str
    geometry: List[List[float]]
    distance_m: Optional[float] = None
    estimated_duration_min: Optional[float] = None
    terrain_difficulty: Optional[float] = None
    max_slope_deg: Optional[float] = None
    feasibility: Optional[str] = None
    parameters: Dict[str, Any] = {}
    created_at: datetime


class MissionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    region_id: str
    mission_type: str
    start: Coordinate
    destination: Coordinate
    time_budget_min: float
    available_sols: Optional[float] = None
    objectives: List[str] = []
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    mission_id: Optional[str] = None
    generated_at: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ApiErrorResponse(BaseModel):
    error: Dict[str, Any]
    request_id: Optional[str] = None