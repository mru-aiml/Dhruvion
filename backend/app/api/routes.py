"""Core API routes: health, region, layers, terrain, hazards, targets, tiles."""

from __future__ import annotations

import urllib.request
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.config import settings
from app.core.exceptions import InvalidInputError, NotFoundError, UnavailableError
from app.schemas.models import (
    HealthResponse,
    Region,
    TerrainResponse,
    TargetsResponse,
)
from app.services.hazard_service import get_hazard_service
from app.services.layer_catalog import get_layer_catalog
from app.services.terrain_service import REGION_CRS, REGION_ID, get_terrain_service

router = APIRouter(tags=["core"])

TILE_MAP = {
    "mars_trek_mola_colorshade": ("Mars_MGS_MOLA_ClrShade_merge_global_463m", "jpg"),
    "mola_roughness": ("mola_roughness", "png"),
    "mars_mola_hrsc_blend": ("Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw", "jpg"),
    "gale_ctx": ("Gale_CTX_BlockAdj_dd", "png"),
    "viking_mdim": ("Mars_Viking_MDIM21_ClrMosaic_global_232m", "jpg"),
}


def _assert_region(region_id: str) -> None:
    if region_id != REGION_ID:
        raise NotFoundError("Unknown region", details={"region_id": region_id})


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="dhruvion-api", version=settings.API_VERSION)


@router.get("/regions")
def regions():
    terrain = get_terrain_service()
    available = terrain.available()
    return {
        "items": [
            {
                "id": REGION_ID,
                "name": "Gale Crater",
                "body": "Mars",
                "crs": REGION_CRS,
                "availability": "available" if available else "unavailable",
                "bounds_latlon": terrain.bounds_latlon(),
                "resolution_m": terrain.resolution_m(),
                "latitude_type": "planetocentric",
                "source": terrain.source() if available else None,
                "warnings": [] if available else ["NASA terrain package is not available on this server."],
            }
        ]
    }


@router.get("/layers")
def layers(region_id: str = Query(...)):
    _assert_region(region_id)
    return get_layer_catalog().catalog(region_id)


@router.get("/terrain", response_model=TerrainResponse)
def terrain(
    region_id: str = Query(...),
    x: float = Query(..., description="Longitude in degrees (planetocentric, east-positive)"),
    y: float = Query(..., description="Latitude in degrees (planetocentric)"),
):
    _assert_region(region_id)
    body = get_terrain_service().point(x, y, region_id=region_id)
    body["classification"] = "OBSERVED (elevation) + DERIVED (slope/roughness)"
    return body


@router.get("/terrain/elevation")
def terrain_elevation(region_id: str = Query(...), x: float = Query(...), y: float = Query(...)):
    _assert_region(region_id)
    return get_terrain_service().layer_point("elevation", x, y)


@router.get("/terrain/slope")
def terrain_slope(region_id: str = Query(...), x: float = Query(...), y: float = Query(...)):
    _assert_region(region_id)
    return get_terrain_service().layer_point("slope", x, y)


@router.get("/terrain/roughness")
def terrain_roughness(region_id: str = Query(...), x: float = Query(...), y: float = Query(...)):
    _assert_region(region_id)
    return get_terrain_service().layer_point("roughness", x, y)


@router.get("/terrain/coverage")
def terrain_coverage(region_id: str = Query(...), x: float = Query(...), y: float = Query(...)):
    _assert_region(region_id)
    return get_terrain_service().coverage_at(x, y)


@router.get("/terrain/coverage/summary")
def terrain_coverage_summary(region_id: str = Query(...)):
    _assert_region(region_id)
    return get_terrain_service().coverage_summary()


@router.get("/terrain/profile")
def terrain_profile(
    region_id: str = Query(...),
    start_x: float = Query(...),
    start_y: float = Query(...),
    end_x: float = Query(...),
    end_y: float = Query(...),
    samples: int = Query(25, ge=2, le=200),
):
    _assert_region(region_id)
    return get_terrain_service().profile(start_x, start_y, end_x, end_y, samples=samples)


@router.get("/hazards")
def hazards(region_id: str = Query(...)):
    _assert_region(region_id)
    return get_hazard_service().summary()


@router.get("/hazards/query")
def hazard_query(region_id: str = Query(...), x: float = Query(...), y: float = Query(...)):
    _assert_region(region_id)
    return get_hazard_service().point(x, y)


@router.get("/targets", response_model=TargetsResponse)
def targets(region_id: str = Query(...)):
    _assert_region(region_id)
    return {
        "region_id": region_id,
        "items": [],
        "availability": "unavailable",
        "warnings": [
            "No verified science-target dataset was supplied in this package; "
            "the UI demo targets are simulated and frontend-only."
        ],
    }


@router.get("/tiles/{layer}/{z}/{x}/{y}.png")
def tiles(layer: str, z: int, x: int, y: int):
    if layer not in TILE_MAP:
        raise NotFoundError("Layer not tileable or unavailable", details={"layer": layer})
    if z < 0 or z > 12:
        raise InvalidInputError("Zoom level out of range", details={"z": z})
    nasa_id, ext = TILE_MAP[layer]
    url = f"https://trek.nasa.gov/tiles/Mars/EQ/{nasa_id}/1.0.0/default/default028mm/{z}/{y}/{x}.{ext}"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type", "image/jpeg" if ext == "jpg" else "image/png")
    except Exception as exc:
        raise UnavailableError(
            "NASA Mars Trek tile fetch failed", details={"layer": layer, "url": url, "error": str(exc)}
        )
    return Response(content=data, media_type=content_type)
