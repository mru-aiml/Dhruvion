import heapq
import json
import math
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

try:
    import rasterio
except Exception:
    rasterio = None
from fastapi.responses import StreamingResponse
from app.schemas.models import (
    HealthResponse, Region, Layer, TerrainResponse, Coordinate, TerrainValue,
    HazardsResponse, TargetsResponse, ScienceTarget,
)

router = APIRouter()

REGION_ID = "gale_crater"
REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"

LAYERS = [
    Layer(
        id="mars_trek_mola_colorshade",
        name="Mars Trek MOLA Color-Shaded Relief",
        layer_type="tiles",
        status="observed",
        availability="available",
        source={"name": "Mars MGS MOLA ClrShade merge global 463m", "provider": "NASA Mars Trek", "product_id": "Mars_MGS_MOLA_ClrShade_merge_global_463m", "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml"},
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
        source={"name": "MOLA roughness", "provider": "NASA Mars Trek", "product_id": "mola_roughness", "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/WMTSCapabilities.xml"},
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
        source={"name": "MOLA + HRSC blend", "provider": "NASA Mars Trek", "product_id": "Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw", "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/WMTSCapabilities.xml"},
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
        source={"name": "Gale CTX Block Adjacency", "provider": "NASA Mars Trek", "product_id": "Gale_CTX_BlockAdj_dd", "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/WMTSCapabilities.xml"},
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
        source={"name": "Viking MDIM21", "provider": "NASA Mars Trek", "product_id": "Mars_Viking_MDIM21_ClrMosaic_global_232m", "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml"},
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
        source={"name": "MGS MOLA MEGDR topography tile megt00n090hb", "provider": "NASA PDS", "product_id": "MEGT00N090HB.IMG", "source_uri": "https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.img"},
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
        source={"name": "Derived from MOLA elevation", "provider": "DHRUVION processing", "product_id": None, "source_uri": None},
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
        source={"name": "Derived from MOLA elevation", "provider": "DHRUVION processing", "product_id": None, "source_uri": None},
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
    return HealthResponse(status="ok", service="dhruvion-api", version="0.1.0")


@router.get("/regions")
def regions():
    return {"items": [Region(id=REGION_ID, name="Gale Crater", body="Mars", crs=REGION_CRS, availability="available")]}


@router.get("/layers")
def layers(region_id: str = Query(...)):
    if region_id != REGION_ID:
        raise HTTPException(status_code=404, detail="Unknown region")
    return {"region_id": region_id, "items": [l.model_dump() for l in LAYERS]}


ELEVATION_TIF = Path(__file__).resolve().parents[3] / "data" / "processed" / "mola" / "gale" / "elevation.tif"
SLOPE_TIF = Path(__file__).resolve().parents[3] / "data" / "processed" / "mola" / "gale" / "slope.tif"
ROUGHNESS_TIF = Path(__file__).resolve().parents[3] / "data" / "processed" / "mola" / "gale" / "roughness.tif"

def _sample(tif_path, x, y):
    if rasterio is None or not tif_path.exists():
        return None
    try:
        with rasterio.open(tif_path) as src:
            # x=lon, y=lat
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
        raise HTTPException(status_code=404, detail="Unknown region")
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
        raise HTTPException(status_code=404, detail="Unknown region")
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
        raise HTTPException(status_code=404, detail="Unknown region")
    return TargetsResponse(region_id=region_id, items=[])


def _load_raster(path):
    if rasterio is None or not path.exists():
        return None
    with rasterio.open(path) as src:
        return src.read(1).astype("float32"), src

def _latlon_to_rc(lat, lon):
    col = (lon - 137.0) * 128.0
    row = (-4.0 - lat) * 128.0
    return int(round(row)), int(round(col))

def _rc_to_latlon(row, col):
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
    # normalize slope 0-1
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
            # reconstruct
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
                    # heuristic
                    hr = math.hypot(nr - er, nc - ec) * 463.0577
                    heapq.heappush(open_set, (ng + hr, (nr, nc)))
    return None

@router.post("/route/optimize")
def route_optimize(payload: dict):
    region_id = payload.get("region_id", "gale_crater")
    if region_id != "gale_crater":
        raise HTTPException(status_code=404, detail="Unknown region")
    start = payload.get("start", {})
    dest = payload.get("destination", {})
    sx, sy = start.get("x"), start.get("y")
    dx, dy = dest.get("x"), dest.get("y")
    if sx is None or sy is None or dx is None or dy is None:
        raise HTTPException(status_code=422, detail="start and destination coordinates required")
    try:
        sr, sc = _latlon_to_rc(sy, sx)
        er, ec = _latlon_to_rc(dy, dx)
    except Exception:
        raise HTTPException(status_code=422, detail="invalid coordinates")
    elev_data = _load_raster(ELEVATION_TIF)
    slope_data = _load_raster(SLOPE_TIF)
    elev = elev_data[0] if elev_data else None
    slope = slope_data[0] if slope_data else None
    strategies = payload.get("strategies", ["shortest", "safest_estimated", "balanced"])
    lam_map = {"shortest": 0.0, "safest_estimated": 2.0, "balanced": 1.0}
    routes = []
    for strat in strategies:
        lam = lam_map.get(strat, 1.0)
        path = _astar(elev, slope, lam, (sr, sc), (er, ec))
        if path is None:
            continue
        coords = [[_rc_to_latlon(r, c)[1], _rc_to_latlon(r, c)[0]] for r, c in path]
        # distance
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
    return {"region_id": region_id, "routes": routes, "algorithm": {"name": "A*", "version": "1.0", "cost_model": {"lambda": lam_map}}}

@router.post("/assistant/ask")
def assistant_ask(payload: dict):
    raise HTTPException(status_code=503, detail="AI assistant backend is not implemented.")

@router.post("/mission/report")
def mission_report(payload: dict):
    report_id = uuid.uuid4().hex
    out_dir = Path(__file__).resolve().parents[3] / "data" / "processed" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{report_id}.json"
    content = {
        "report_id": report_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": payload.get("format", "json"),
        "status": "generated",
        "mission_id": payload.get("mission_id"),
        "note": "Report generated from available backend data only.",
    }
    file_path.write_text(json.dumps(content, indent=2))
    return {
        "report_id": report_id,
        "format": payload.get("format", "json"),
        "status": "generated",
        "download_url": f"/static/reports/{report_id}.json",
        "provenance": [],
        "warnings": ["Report contains only available backend data; simulated values are excluded."],
    }

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
        raise HTTPException(status_code=404, detail="Layer not tileable or unavailable")
    nasa_id, ext = TILE_MAP[layer]
    url = f"https://trek.nasa.gov/tiles/Mars/EQ/{nasa_id}/1.0.0/default/default028mm/{z}/{y}/{x}.{ext}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "image/jpeg" if ext == "jpg" else "image/png")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tile fetch failed: {e}")
    from fastapi.responses import Response
    return Response(content=data, media_type=content_type)
