import heapq
import json
import math
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

try:
    import rasterio
except Exception:
    rasterio = None

from app.core.config import settings
from app.core.exceptions import (
    UnavailableError,
    InvalidInputError,
    NotFoundError,
)
from app.schemas.models import (
    HealthResponse,
    Region,
    Layer,
    TerrainResponse,
    Coordinate,
    TerrainValue,
    HazardsResponse,
    TargetsResponse,
    ScienceTarget,
)

router = APIRouter()

REGION_ID = "gale_crater"
REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"

# Layer catalog - matches api.md specification
LAYERS = [
    Layer(
        id="mars_trek_mola_colorshade",
        name="Mars Trek MOLA Color-Shaded Relief",
        layer_type="tiles",
        status="observed",
        availability="available",
        source={
            "name": "Mars MGS MOLA ClrShade merge global 463m",
            "provider": "NASA Mars Trek",
            "product_id": "Mars_MGS_MOLA_ClrShade_merge_global_463m",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml",
        },
        crs=REGION_CRS,
        resolution_m=463.0,
        units="color-shaded relief",
        warnings=["Basemap tile layer from NASA Mars Trek. Not a verified elevation raster for terrain queries."],
    ),
    Layer(
        id="mola_roughness",
        name="MOLA Global Roughness",
        layer_type="tiles",
        status="observed",
        availability="available",
        source={
            "name": "MOLA roughness",
            "provider": "NASA Mars Trek",
            "product_id": "mola_roughness",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/WMTSCapabilities.xml",
        },
        crs=REGION_CRS,
        resolution_m=2368.0,
        units="roughness index",
        overlay_url=None,
        warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval at zoom 0-1 only."],
    ),
    Layer(
        id="mars_mola_hrsc_blend",
        name="MOLA + HRSC Color Hillshade",
        layer_type="tiles",
        status="observed",
        availability="available",
        source={
            "name": "MOLA + HRSC blend",
            "provider": "NASA Mars Trek",
            "product_id": "Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/WMTSCapabilities.xml",
        },
        crs=REGION_CRS,
        resolution_m=200.0,
        units="color-shaded relief",
        overlay_url=None,
        warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval around Gale Crater."],
    ),
    Layer(
        id="gale_ctx",
        name="Gale Crater CTX Mosaic",
        layer_type="tiles",
        status="observed",
        availability="available",
        source={
            "name": "Gale CTX Block Adjacency",
            "provider": "NASA Mars Trek",
            "product_id": "Gale_CTX_BlockAdj_dd",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/WMTSCapabilities.xml",
        },
        crs=REGION_CRS,
        resolution_m=6.0,
        units="imagery",
        overlay_url=None,
        warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval around Gale Crater at zoom 5."],
    ),
    Layer(
        id="viking_mdim",
        name="Viking Global Color Mosaic",
        layer_type="tiles",
        status="observed",
        availability="available",
        source={
            "name": "Viking MDIM21",
            "provider": "NASA Mars Trek",
            "product_id": "Mars_Viking_MDIM21_ClrMosaic_global_232m",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml",
        },
        crs=REGION_CRS,
        resolution_m=232.0,
        units="imagery",
        overlay_url=None,
        warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval around Gale Crater."],
    ),
    Layer(
        id="mola_elevation",
        name="Elevation / MOLA",
        layer_type="raster",
        status="observed",
        availability="available",
        source={
            "name": "MGS MOLA MEGDR topography tile megt00n090hb",
            "provider": "NASA PDS",
            "product_id": "MEGT00N090HB.IMG",
            "source_uri": "https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.img",
        },
        crs=REGION_CRS,
        resolution_m=463.0,
        units="m",
        overlay_url="/static/mola/gale/elevation.png",
        warnings=["Processed from megt00n090hb.img; coverage lon 137-138 E, lat -4.0 to -6.5; NoData=0."],
    ),
    Layer(
        id="slope",
        name="Slope Analysis",
        layer_type="derived",
        status="derived",
        availability="available",
        source={
            "name": "Derived from MOLA elevation",
            "provider": "DHRUVION processing",
            "product_id": None,
            "source_uri": None,
        },
        crs=REGION_CRS,
        resolution_m=463.0,
        units="deg",
        overlay_url="/static/mola/gale/slope.png",
        warnings=["Derived from megt00n090hb.img using arctan gradient; coverage lon 137-138 E, lat -4.0 to -6.5."],
    ),
    Layer(
        id="roughness",
        name="Terrain Roughness",
        layer_type="derived",
        status="derived",
        availability="available",
        source={
            "name": "Derived from MOLA elevation",
            "provider": "DHRUVION processing",
            "product_id": None,
            "source_uri": None,
        },
        crs=REGION_CRS,
        resolution_m=463.0,
        units="index",
        overlay_url="/static/mola/gale/roughness.png",
        warnings=["Derived from megt00n090hb.img using 3x3 local std; coverage lon 137-138 E, lat -4.0 to -6.5."],
    ),
    Layer(
        id="themis_thermal",
        name="THEMIS Thermal",
        layer_type="raster",
        status="observed",
        availability="unavailable",
        source={"name": "THEMIS", "provider": "NASA/ASU", "product_id": None, "source_uri": "https://themis.asu.edu/"},
        crs=REGION_CRS,
        units="K",
        warnings=["Optional layer; no THEMIS product loaded."],
    ),
    Layer(
        id="science_targets",
        name="Science Targets",
        layer_type="vector",
        status="simulated",
        availability="unavailable",
        source={"name": None, "provider": None, "product_id": None, "source_uri": None},
        crs=REGION_CRS,
        warnings=["No verified science target dataset loaded. Simulated targets are frontend-only and labelled."],
    ),
    Layer(
        id="hazard_overlay",
        name="Hazard Overlay",
        layer_type="derived",
        status="derived",
        availability="unavailable",
        source={"name": None, "provider": None, "product_id": None, "source_uri": None},
        crs=REGION_CRS,
        warnings=["No hazard dataset loaded."],
    ),
]


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="dhruvion-api", version=settings.API_VERSION)


@router.get("/regions")
def regions():
    return {"items": [Region(id=REGION_ID, name="Gale Crater", body="Mars", crs=REGION_CRS, availability="available")]}


@router.get("/layers")
def layers(region_id: str = Query(...)):
    if region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": region_id})
    return {"region_id": region_id, "items": [l.model_dump() for l in LAYERS]}


# Path to processed raster files
ELEVATION_TIF = settings.PROCESSED_DIR / "mola" / "gale" / "elevation.tif"
SLOPE_TIF = settings.PROCESSED_DIR / "mola" / "gale" / "slope.tif"
ROUGHNESS_TIF = settings.PROCESSED_DIR / "mola" / "gale" / "roughness.tif"


def _sample(tif_path: Path, x: float, y: float) -> Optional[float]:
    """Sample a raster at given coordinates."""
    if rasterio is None or not tif_path.exists():
        return None
    try:
        with rasterio.open(tif_path) as src:
            for val in src.sample([(x, y)]):
                v = float(val[0])
                if v == 0.0 or v != v:  # nodata or nan
                    return None
                return v
    except Exception:
        return None
    return None


@router.get("/terrain", response_model=TerrainResponse)
def terrain(region_id: str = Query(...), x: float = Query(...), y: float = Query(...)):
    if region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": region_id})

    elev = _sample(ELEVATION_TIF, x, y)
    slope = _sample(SLOPE_TIF, x, y)
    rough = _sample(ROUGHNESS_TIF, x, y)

    if elev is None and slope is None and rough is None:
        availability = "unavailable"
        warnings = ["Coordinate outside processed MOLA coverage or NoData."]
    else:
        availability = "available"
        warnings = []

    prov = ["observed"] if elev is not None else []
    if slope is not None:
        prov.append("derived")

    return TerrainResponse(
        region_id=region_id,
        coordinate=Coordinate(x=x, y=y, crs=REGION_CRS),
        values=TerrainValue(elevation_m=elev, slope_deg=slope, roughness=rough),
        provenance=prov,
        availability=availability,
        warnings=warnings,
    )


@router.get("/hazards", response_model=HazardsResponse)
def hazards(region_id: str = Query(...)):
    if region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": region_id})
    return HazardsResponse(
        region_id=region_id,
        features={"type": "FeatureCollection", "features": []},
        summary={"identified_count": 0, "unknown_coverage": True},
        provenance=[],
        warnings=["No hazard dataset loaded. Empty result does not imply hazard-free terrain."],
    )


@router.get("/targets", response_model=TargetsResponse)
def targets(region_id: str = Query(...)):
    if region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": region_id})
    return TargetsResponse(region_id=region_id, items=[])


# Route optimization models
from pydantic import BaseModel, Field


class RouteCoordinate(BaseModel):
    x: float
    y: float
    crs: str = REGION_CRS


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
    routes: List[Dict[str, Any]]
    algorithm: Dict[str, Any]


def _load_raster(path: Path):
    if rasterio is None or not path.exists():
        return None
    with rasterio.open(path) as src:
        return src.read(1).astype("float32"), src


def _latlon_to_rc(lat: float, lon: float) -> tuple[int, int]:
    """Convert lat/lon to row/col in the raster."""
    col = (lon - 137.0) * 128.0
    row = (-4.0 - lat) * 128.0
    return int(round(row)), int(round(col))


def _rc_to_latlon(row: int, col: int) -> tuple[float, float]:
    lat = -4.0 - (row + 0.5) / 128.0
    lon = 137.0 + (col + 0.5) / 128.0
    return lat, lon


def _astar(elev, slope, lam, start_rc, end_rc):
    if elev is None:
        return None
    h, w = elev.shape
    sr, sc = start_rc
    er, ec = end_rc
    if not (0 <= sr < h and 0 <= sc < w and 0 <= er < h and 0 <= ec < w):
        return None
    if elev[sr, sc] == 0 or elev[er, ec] == 0:
        return None

    def risk(r, c):
        s = slope[r, c] if slope is not None else 0.0
        if s != s:
            return 1.0
        return min(1.0, max(0.0, s / 45.0))

    open_set = [(0.0, (sr, sc))]
    g = {(sr, sc): 0.0}
    came = {}

    while open_set:
        _, cur = heapq.heappop(open_set)
        if cur == (er, ec):
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            return path

        r, c = cur
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not (0 <= nr < h and 0 <= nc < w):
                    continue
                if elev[nr, nc] == 0:
                    continue
                dist = math.hypot(dr, dc) * 463.0577
                edge = dist * (1.0 + lam * risk(nr, nc))
                ng = g[cur] + edge
                if ng < g.get((nr, nc), float("inf")):
                    g[(nr, nc)] = ng
                    came[(nr, nc)] = cur
                    hr = math.hypot(nr - er, nc - ec) * 463.0577
                    heapq.heappush(open_set, (ng + hr, (nr, nc)))
    return None


@router.post("/route/optimize", response_model=RouteOptimizeResponse)
def route_optimize(payload: RouteOptimizeRequest):
    if payload.region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": payload.region_id})

    sx, sy = payload.start.x, payload.start.y
    dx, dy = payload.destination.x, payload.destination.y

    try:
        sr, sc = _latlon_to_rc(sy, sx)
        er, ec = _latlon_to_rc(dy, dx)
    except Exception:
        raise InvalidInputError("Invalid coordinates")

    elev_data = _load_raster(ELEVATION_TIF)
    slope_data = _load_raster(SLOPE_TIF)
    elev = elev_data[0] if elev_data else None
    slope = slope_data[0] if slope_data else None

    lam_map = {"shortest": 0.0, "safest_estimated": 2.0, "balanced": 1.0}
    routes = []

    for strat in payload.strategies:
        lam = lam_map.get(strat, 1.0)
        path = _astar(elev, slope, lam, (sr, sc), (er, ec))
        if path is None:
            continue

        coords = [[_rc_to_latlon(r, c)[1], _rc_to_latlon(r, c)[0]] for r, c in path]

        dist = 0.0
        for i in range(1, len(path)):
            r1, c1 = path[i - 1]
            r2, c2 = path[i]
            dist += math.hypot(r2 - r1, c2 - c1) * 463.0577

        slopes = [float(slope[r, c]) for r, c in path if slope is not None and slope[r, c] == slope[r, c]]
        diff = float(sum(slopes) / len(slopes)) if slopes else None
        hazard_count = sum(1 for r, c in path if slope is not None and slope[r, c] > 15)

        routes.append({
            "id": f"route-{strat}",
            "strategy": strat,
            "geometry": {"type": "LineString", "coordinates": coords},
            "distance_m": round(dist, 1),
            "estimated_duration_min": round(dist / 60.0, 1),
            "terrain_difficulty": round(diff, 2) if diff is not None else None,
            "hazard_count": hazard_count,
            "feasibility_status": "feasible",
            "rationale": f"{strat} route computed from MOLA elevation/slope within processed coverage.",
            "provenance": ["derived"],
            "warnings": ["Route computed from processed MOLA raster (OBSERVED/DERIVED)."],
        })

    return RouteOptimizeResponse(
        region_id=payload.region_id,
        routes=routes,
        algorithm={"name": "A*", "version": "1.0", "cost_model": {"lambda": lam_map}},
    )


# Mission Planning
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


class TimeBudget(BaseModel):
    outbound_min: Optional[float] = None
    exploration_min: Optional[float] = None
    return_min: Optional[float] = None
    reserve_min: Optional[float] = None
    total_min: Optional[float] = None
    limit_min: Optional[float] = None


class MissionPlanResponse(BaseModel):
    mission_id: str
    route: Dict[str, Any]
    time_budget: TimeBudget
    feasibility_status: str
    reasons: List[str] = []
    assumptions: List[str] = []
    warnings: List[str] = []


@router.post("/mission/plan", response_model=MissionPlanResponse)
def mission_plan(payload: MissionPlanRequest):
    if payload.region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": payload.region_id})

    # Reuse route optimization logic
    sx, sy = payload.start.x, payload.start.y
    dx, dy = payload.destination.x, payload.destination.y

    try:
        sr, sc = _latlon_to_rc(sy, sx)
        er, ec = _latlon_to_rc(dy, dx)
    except Exception:
        raise InvalidInputError("Invalid coordinates")

    elev_data = _load_raster(ELEVATION_TIF)
    slope_data = _load_raster(SLOPE_TIF)
    elev = elev_data[0] if elev_data else None
    slope = slope_data[0] if slope_data else None

    lam = 1.0  # balanced
    path = _astar(elev, slope, lam, (sr, sc), (er, ec))

    if path is None:
        raise UnavailableError("No valid route found within processed coverage")

    coords = [[_rc_to_latlon(r, c)[1], _rc_to_latlon(r, c)[0]] for r, c in path]

    dist = 0.0
    for i in range(1, len(path)):
        r1, c1 = path[i - 1]
        r2, c2 = path[i]
        dist += math.hypot(r2 - r1, c2 - c1) * 463.0577

    slopes = [float(slope[r, c]) for r, c in path if slope is not None and slope[r, c] == slope[r, c]]
    diff = float(sum(slopes) / len(slopes)) if slopes else None
    hazard_count = sum(1 for r, c in path if slope is not None and slope[r, c] > 15)

    # Calculate time budget
    travel_speed = payload.travel_speed_m_per_min or 60.0  # m/min default
    outbound_duration = dist / travel_speed if travel_speed > 0 else None
    return_duration = outbound_duration  # simplified: same path back
    exploration = payload.exploration_time_min
    reserve = payload.reserve_time_min

    total = 0.0
    if outbound_duration is not None:
        total += outbound_duration
    total += exploration
    if return_duration is not None:
        total += return_duration
    total += reserve

    feasibility = "feasible"
    reasons = []
    if total > payload.time_limit_min:
        feasibility = "not_feasible"
        reasons.append(f"Total time {total:.1f} min exceeds limit {payload.time_limit_min} min")
    elif total > payload.time_limit_min * 0.9:
        feasibility = "caution"
        reasons.append(f"Total time {total:.1f} min near limit {payload.time_limit_min} min")

    if outbound_duration is None or return_duration is None:
        feasibility = "unverified"
        reasons.append("Missing return route or travel speed")

    mission_id = uuid.uuid4().hex[:12]

    return MissionPlanResponse(
        mission_id=mission_id,
        route={
            "id": f"route-{mission_id}",
            "strategy": payload.route_strategy,
            "geometry": {"type": "LineString", "coordinates": coords},
            "distance_m": round(dist, 1),
            "estimated_duration_min": round(outbound_duration, 1) if outbound_duration else None,
            "terrain_difficulty": round(diff, 2) if diff else None,
            "hazard_count": hazard_count,
            "feasibility_status": "feasible",
            "rationale": f"Balanced route computed from MOLA elevation/slope within processed coverage.",
            "provenance": ["derived"],
            "warnings": ["Route computed from processed MOLA raster (OBSERVED/DERIVED)."],
        },
        time_budget=TimeBudget(
            outbound_min=round(outbound_duration, 1) if outbound_duration else None,
            exploration_min=exploration,
            return_min=round(return_duration, 1) if return_duration else None,
            reserve_min=reserve,
            total_min=round(total, 1),
            limit_min=payload.time_limit_min,
        ),
        feasibility_status=feasibility,
        reasons=reasons,
        assumptions=[
            f"Travel speed: {travel_speed} m/min",
            "Symmetric outbound/return path assumed",
            "Exploration time fixed",
        ],
        warnings=["Mission plan based on processed MOLA raster (OBSERVED/DERIVED). Missing data yields UNVERIFIED."],
    )


# Mission Return Feasibility
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


@router.post("/mission/return", response_model=ReturnFeasibilityResponse)
def mission_return(payload: MissionReturnRequest):
    # Simplified: compute return from current location to a default base
    # In a real implementation, this would use the mission's original start location
    base_lat, base_lon = -5.45, 137.35  # Example base location

    sx, sy = payload.current_location.x, payload.current_location.y
    dx, dy = base_lon, base_lat

    try:
        sr, sc = _latlon_to_rc(sy, sx)
        er, ec = _latlon_to_rc(dy, dx)
    except Exception:
        raise InvalidInputError("Invalid coordinates")

    elev_data = _load_raster(ELEVATION_TIF)
    slope_data = _load_raster(SLOPE_TIF)
    elev = elev_data[0] if elev_data else None
    slope = slope_data[0] if slope_data else None

    path = _astar(elev, slope, 1.0, (sr, sc), (er, ec))

    if path is None:
        return ReturnFeasibilityResponse(
            return_route={},
            estimated_return_min=None,
            remaining_time_min=payload.remaining_time_min,
            reserve_time_min=payload.reserve_time_min,
            feasibility_status="unverified",
            reasons=["No valid return path found within processed coverage"],
            warnings=["Return feasibility UNVERIFIED - missing route data"],
        )

    coords = [[_rc_to_latlon(r, c)[1], _rc_to_latlon(r, c)[0]] for r, c in path]

    dist = 0.0
    for i in range(1, len(path)):
        r1, c1 = path[i - 1]
        r2, c2 = path[i]
        dist += math.hypot(r2 - r1, c2 - c1) * 463.0577

    travel_speed = 60.0  # m/min
    return_duration = dist / travel_speed if travel_speed > 0 else None
    total_required = (return_duration or 0) + payload.reserve_time_min

    if return_duration is None:
        feasibility = "unverified"
        reasons = ["Missing return route data"]
    elif total_required > payload.remaining_time_min:
        feasibility = "not_feasible"
        reasons = [f"Required {total_required:.1f} min exceeds remaining {payload.remaining_time_min} min"]
    elif total_required > payload.remaining_time_min * 0.9:
        feasibility = "caution"
        reasons = [f"Tight margin: required {total_required:.1f} min vs remaining {payload.remaining_time_min} min"]
    else:
        feasibility = "feasible"
        reasons = ["Return feasible within time budget"]

    return ReturnFeasibilityResponse(
        return_route={
            "id": f"return-{uuid.uuid4().hex[:8]}",
            "geometry": {"type": "LineString", "coordinates": coords},
            "distance_m": round(dist, 1),
            "estimated_duration_min": round(return_duration, 1) if return_duration else None,
        },
        estimated_return_min=round(return_duration, 1) if return_duration else None,
        remaining_time_min=payload.remaining_time_min,
        reserve_time_min=payload.reserve_time_min,
        feasibility_status=feasibility,
        reasons=reasons,
        warnings=["Return feasibility based on processed MOLA raster. Missing data yields UNVERIFIED."],
    )


# Emergency Reroute
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


@router.post("/route/reroute", response_model=RerouteResponse)
def reroute(payload: RerouteRequest):
    if payload.scenario_status not in ("observed", "simulated"):
        raise InvalidInputError("scenario_status must be 'observed' or 'simulated'")

    # Simplified: generate an alternative route avoiding a blocked point
    # In a real implementation, this would use the actual route geometry and obstacle
    raise UnavailableError(
        "Emergency rerouting not fully implemented in this build",
        details={"message": "Reroute service requires full route geometry and obstacle processing"}
    )


# Assistant
class AssistantRequest(BaseModel):
    message: str
    mission_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class AssistantToolActivity(BaseModel):
    tool: str
    status: str


class AssistantResponse(BaseModel):
    message: str
    intent: str
    recommendation: Optional[Dict[str, Any]] = None
    tool_activity: List[AssistantToolActivity] = []
    evidence: List[Any] = []
    warnings: List[str] = []
    sources: List[Any] = []
    actions: List[str] = []


@router.post("/assistant/ask", response_model=AssistantResponse)
def assistant_ask(payload: AssistantRequest):
    # Tool routing would happen here in a full implementation
    # For now, return a structured response indicating the assistant is available
    # but tools are not yet connected
    return AssistantResponse(
        message="AI Mission Assistant is available. Tool routing is not yet implemented in this build.",
        intent="unknown",
        tool_activity=[],
        evidence=[],
        warnings=["Assistant tools not connected in this prototype"],
        sources=[],
        actions=["Connect tool routing in AssistantService"],
    )


# Mission Report
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


@router.post("/mission/report", response_model=ReportResponse)
def mission_report(payload: ReportRequest):
    report_id = uuid.uuid4().hex
    out_dir = settings.REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{report_id}.json"

    content = {
        "report_id": report_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": payload.format,
        "status": "generated",
        "mission_id": payload.mission_id,
        "note": "Report generated from available backend data only.",
    }
    file_path.write_text(json.dumps(content, indent=2))

    return ReportResponse(
        report_id=report_id,
        format=payload.format,
        status="generated",
        download_url=f"/static/reports/{report_id}.json",
        provenance=[],
        warnings=["Report contains only available backend data; simulated values are excluded."],
    )


# Tile proxy for NASA Mars Trek WMTS
TILE_MAP = {
    "mars_trek_mola_colorshade": ("Mars_MGS_MOLA_ClrShade_merge_global_463m", "jpg"),
    "mola_roughness": ("mola_roughness", "png"),
    "mars_mola_hrsc_blend": ("Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw", "jpg"),
    "gale_ctx": ("Gale_CTX_BlockAdj_dd", "png"),
    "viking_mdim": ("Mars_Viking_MDIM21_ClrMosaic_global_232m", "jpg"),
}


@router.get("/tiles/{layer}/{z}/{x}/{y}.png")
def tiles(layer: str, z: int, x: int, y: int):
    if layer not in TILE_MAP:
        raise NotFoundError("Layer not tileable or unavailable", details={"layer": layer})
    nasa_id, ext = TILE_MAP[layer]
    url = f"https://trek.nasa.gov/tiles/Mars/EQ/{nasa_id}/1.0.0/default/default028mm/{z}/{y}/{x}.{ext}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg" if ext == "jpg" else "image/png")
    except Exception as e:
        raise UnavailableError(f"Tile fetch failed: {e}", details={"layer": layer, "url": url})
    from fastapi.responses import Response
    return Response(content=data, media_type=content_type)