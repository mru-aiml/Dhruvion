"""Dataset, imagery, raster compatibility, and science catalogue routes."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Query

from app.core.exceptions import InvalidInputError, NotFoundError, UnavailableError
from app.data_pipeline.dataset_paths import get_dataset_paths
from app.data_pipeline.validation import validate_raster, validate_vector
from app.schemas.dataset import (
    DatasetCatalogRebuildResponse,
    DatasetCatalogResponse,
    DatasetEntry,
    DatasetValidationRequest,
    DatasetValidationResponse,
)
from app.schemas.imagery import (
    ImageryLayerCatalogResponse,
    LayerAvailabilityRequest,
    LayerAvailabilityResponse,
)
from app.services.dataset_catalog_service import get_dataset_catalog_service
from app.services.imagery_service import get_imagery_service
from app.services.terrain_service import get_terrain_service

router = APIRouter(tags=["datasets"])


# ---------------------------------------------------------------- datasets
@router.get("/datasets", response_model=DatasetCatalogResponse)
def datasets(
    dataset_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    provenance: Optional[str] = Query(None),
    region_id: Optional[str] = Query(None),
    text_query: Optional[str] = Query(None),
):
    result = get_dataset_catalog_service().catalog(
        dataset_type=dataset_type,
        status=status,
        provenance=provenance,
        region_id=region_id,
        text_query=text_query,
    )
    return {
        "catalog_version": result["catalog_version"],
        "generated_at": result["generated_at"],
        "datasets": result["datasets"],
        "statistics": result["statistics"],
    }


@router.get("/datasets/{dataset_id}", response_model=DatasetEntry)
def dataset_detail(dataset_id: str):
    return get_dataset_catalog_service().get(dataset_id)


@router.post("/datasets/validate", response_model=DatasetValidationResponse)
def validate_dataset(request: DatasetValidationRequest):
    path = Path(request.path)
    if not path.exists():
        raise NotFoundError("File not found for validation", details={"path": path.name})
    suffix = path.suffix.lower()
    if suffix in {".tif", ".tiff", ".img", ".geotiff"}:
        result = validate_raster(path)
    elif suffix in {".geojson", ".json"}:
        result = validate_vector(path)
    else:
        raise InvalidInputError("Unsupported file format for validation", details={"suffix": suffix})
    return {
        "is_valid": result.is_valid,
        "dataset_id": result.dataset_id,
        "dataset_path": result.dataset_path,
        "issues": [issue.__dict__ for issue in result.issues],
    }


@router.post("/datasets/rebuild", response_model=DatasetCatalogRebuildResponse)
def rebuild_dataset_catalog():
    get_dataset_catalog_service().invalidate()
    result = get_dataset_catalog_service().catalog()
    count = len(result["datasets"])
    return {
        "datasets_count": count,
        "message": f"Dataset catalog rebuilt from the installed package ({count} entries).",
    }


# ----------------------------------------------------------------- imagery
@router.get("/imagery")
def imagery():
    return {
        "region_id": "gale_crater",
        "ctx": get_imagery_service().get_ctx_imagery(),
        "tiles": {
            layer.id: {
                "name": layer.name,
                "tile_url_template": layer.tile_url_template,
                "max_zoom": layer.max_zoom,
                "source": layer.source,
            }
            for layer in get_imagery_service().get_all_layers()
            if layer.tile_url_template
        },
        "warnings": [
            "NASA Mars Trek tiles are remote and may be unavailable offline; local CTX and terrain overlays remain usable."
        ],
        "limitations": [
            "Use a Mars equirectangular projection; Web Mercator is not valid for Mars overlays.",
            "CTX DN values are not reflectance.",
        ],
    }


@router.get("/imagery/layers", response_model=ImageryLayerCatalogResponse)
def imagery_layers(region_id: Optional[str] = Query(None)):
    return get_imagery_service().get_layer_catalog(region_id)


@router.post("/imagery/layers/check-availability", response_model=List[LayerAvailabilityResponse])
def check_imagery_availability(request: LayerAvailabilityRequest):
    service = get_imagery_service()
    return [
        {"layer_id": layer_id, "available": service.validate_layer_availability(layer_id)}
        for layer_id in request.layer_ids
    ]


# -------------------------------------------------- raster compatibility API
TERRAIN_LAYER_IDS = {
    "mola_elevation": "elevation",
    "elevation": "elevation",
    "slope": "slope",
    "roughness": "roughness",
    "coverage": "coverage",
}


def _terrain_layer_id(layer_id: str) -> str:
    key = TERRAIN_LAYER_IDS.get(layer_id)
    if key is None:
        raise NotFoundError("Raster layer not found", details={"layer_id": layer_id})
    return key


@router.get("/raster/layers")
def raster_layers():
    terrain = get_terrain_service()
    items = []
    for layer_id, key in (("mola_elevation", "elevation"), ("slope", "slope"), ("roughness", "roughness"), ("coverage", "coverage")):
        items.append(
            {
                "layer_id": layer_id,
                "name": {
                    "elevation": "Elevation / MOLA",
                    "slope": "Slope (MOLA-derived)",
                    "roughness": "Terrain Roughness (TRI)",
                    "coverage": "Coverage Mask",
                }[key],
                "key": key,
                "available": terrain.available(),
                "resolution_m": terrain.resolution_m(),
                "bounds_latlon": terrain.bounds_latlon(),
            }
        )
    return {"layers": items}


@router.get("/raster/layers/{layer_id}/metadata")
def raster_metadata(layer_id: str):
    key = _terrain_layer_id(layer_id)
    terrain = get_terrain_service()
    metadata = terrain.layer_metadata()
    metadata["layer_id"] = layer_id
    metadata["key"] = key
    metadata["overlay_url"] = terrain.overlay_url(key)
    return metadata


@router.get("/raster/layers/{layer_id}/statistics")
def raster_statistics(layer_id: str):
    key = _terrain_layer_id(layer_id)
    terrain = get_terrain_service()
    if not terrain.available():
        raise UnavailableError("NASA terrain package is not available on this server.")
    grid = terrain.grid()
    data = grid[key]
    values = data[np.isfinite(data)] if np.issubdtype(data.dtype, np.floating) else data
    if values.size == 0:
        return {"layer_id": layer_id, "error": "No finite values available."}
    return {
        "layer_id": layer_id,
        "key": key,
        "count": int(values.size),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "units": terrain.layer_metadata().get("units", {}).get(key),
        "bounds_latlon": terrain.bounds_latlon(),
        "resolution_m": terrain.resolution_m(),
        "source": terrain.source(),
        "provenance": "observed" if key == "elevation" else "derived",
        "limitations": terrain.limitations(),
    }


@router.post("/raster/validate-coordinate")
def validate_coordinate(payload: Dict[str, Any]):
    try:
        x = float(payload["x"])
        y = float(payload["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInputError("x (longitude) and y (latitude) are required") from exc
    result = get_terrain_service().coverage_at(x, y)
    return {
        "valid": result["availability"] == "available" and result["coverage"]["class"] in (1, 2),
        "coordinate": result["coordinate"],
        "coverage": result["coverage"],
        "availability": result["availability"],
        "warnings": result["warnings"],
        "limitations": result["limitations"],
    }


# ---------------------------------------------------------- science catalog
@router.get("/science/catalogs")
def science_catalogs():
    paths = get_dataset_paths()
    return {
        "catalogs": [],
        "availability": "unavailable",
        "warnings": [
            "No verified science-target dataset was supplied in the NASA handover package. "
            "Science targets shown in the UI are simulated and labelled."
        ],
        "package_installed": paths is not None,
    }


@router.get("/science/catalogs/{catalog_id}")
def science_catalog_info(catalog_id: str):
    raise NotFoundError(
        "No verified science-target catalog is installed",
        details={"catalog_id": catalog_id},
    )
