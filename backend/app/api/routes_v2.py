"""Phase 2 API routes for dataset catalog, imagery, and science data."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    UnavailableError,
    InvalidInputError,
    NotFoundError,
)
from app.core.logging_config import get_logger
from app.services.terrain_data_service import get_terrain_data_service
from app.services.imagery_service import get_imagery_service
from app.services.science_data_service import get_science_data_service
from app.data_pipeline.catalog import get_dataset_catalog, rebuild_catalog
from app.data_pipeline.validation import validate_raster, validate_vector, validate_metadata_file
from app.schemas.dataset import (
    DatasetCatalogResponse,
    DatasetEntry,
    DatasetValidationRequest,
    DatasetValidationResponse,
    DatasetCatalogRebuildResponse,
)
from app.schemas.terrain import (
    RasterLayersResponse,
    CoordinateValidationRequest,
    CoordinateValidationResponse,
    LayerStatisticsResponse,
    LayerStatisticsError,
)
from app.schemas.imagery import (
    ImageryLayerCatalogResponse,
    LayerAvailabilityRequest,
    LayerAvailabilityResponse,
)
from app.schemas.models import (
    TerrainResponse,
    HazardsResponse,
    TargetsResponse,
)

router = APIRouter(tags=["Phase 2"])

logger = get_logger(__name__)


# Dataset Catalog Endpoints

@router.get("/datasets", response_model=DatasetCatalogResponse)
def get_dataset_catalog(
    dataset_type: Optional[str] = Query(None, description="Filter by dataset type"),
    status: Optional[str] = Query(None, description="Filter by availability status"),
    provenance: Optional[str] = Query(None, description="Filter by provenance"),
    region_id: Optional[str] = Query(None, description="Filter by region"),
    text_query: Optional[str] = Query(None, description="Text search query"),
):
    """Get the dataset catalog with optional filters."""
    catalog = get_dataset_catalog()
    
    results = catalog.search(
        dataset_type=dataset_type,
        status=status,
        provenance=provenance,
        region_id=region_id,
        text_query=text_query,
    )
    
    return DatasetCatalogResponse(
        catalog_version=1,
        generated_at=datetime.utcnow().isoformat(),
        datasets=results,
        statistics=catalog.get_statistics(),
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetEntry)
def get_dataset(dataset_id: str):
    """Get a specific dataset by ID."""
    catalog = get_dataset_catalog()
    entry = catalog.get(dataset_id)
    
    if not entry:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    
    return entry


@router.post("/datasets/validate", response_model=DatasetValidationResponse)
def validate_dataset(request: DatasetValidationRequest):
    """Validate a dataset file."""
    path = Path(request.path)
    
    # Try raster validation first
    result = None
    if path.suffix.lower() in {".tif", ".tiff", ".img", ".geotiff"}:
        from app.data_pipeline.validation import validate_raster
        result = validate_raster(path)
    elif path.suffix.lower() in {".geojson", ".json"}:
        from app.data_pipeline.validation import validate_vector
        result = validate_vector(path)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported file format for validation"
        )
    
    return DatasetValidationResponse(
        is_valid=result.is_valid,
        dataset_id=result.dataset_id,
        dataset_path=result.dataset_path,
        issues=[i.__dict__ for i in result.issues],
    )


@router.post("/datasets/rebuild", response_model=DatasetCatalogRebuildResponse)
def rebuild_dataset_catalog():
    """Force rebuild of the dataset catalog."""
    catalog = rebuild_catalog()
    count = len(catalog._catalog)
    return DatasetCatalogRebuildResponse(
        datasets_count=count,
        message=f"Catalog rebuilt with {count} datasets",
    )


# Raster/Terrain Endpoints

@router.get("/raster/layers", response_model=RasterLayersResponse)
def get_raster_layers():
    """Get list of available raster/terrain layers."""
    service = get_terrain_data_service()
    layers = service.get_available_layers()
    return RasterLayersResponse(layers=layers)


@router.get("/raster/layers/{layer_id}/metadata")
def get_raster_metadata(layer_id: str):
    """Get metadata for a specific raster layer."""
    service = get_terrain_data_service()
    try:
        metadata = service.get_raster_metadata(layer_id)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/raster/layers/{layer_id}/statistics")
def get_raster_statistics(layer_id: str):
    """Get statistics for a raster layer."""
    service = get_terrain_data_service()
    try:
        stats = service.get_layer_statistics(layer_id)
        if "error" in stats:
            return LayerStatisticsError(layer_id=layer_id, error=stats["error"])
        return LayerStatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/raster/validate-coordinate", response_model=CoordinateValidationResponse)
def validate_coordinate(request: CoordinateValidationRequest):
    """Validate if a coordinate is within processed coverage."""
    service = get_terrain_data_service()
    result = service.validate_coordinate(request.x, request.y)
    return CoordinateValidationResponse(**result)


# Imagery Endpoints

@router.get("/imagery/layers", response_model=ImageryLayerCatalogResponse)
def get_imagery_layers(region_id: Optional[str] = Query(None)):
    """Get imagery layer catalog."""
    service = get_imagery_service()
    catalog = service.get_layer_catalog(region_id)
    return ImageryLayerCatalogResponse(**catalog)


@router.post("/imagery/layers/check-availability", response_model=List[LayerAvailabilityResponse])
def check_layer_availability(request: LayerAvailabilityRequest):
    """Check availability of multiple layers."""
    service = get_imagery_service()
    results = []
    for layer_id in request.layer_ids:
        available = service.validate_layer_availability(layer_id)
        results.append(LayerAvailabilityResponse(layer_id=layer_id, available=available))
    return results


# Science Data Endpoints

@router.get("/science/catalogs")
def get_science_catalogs():
    """Get available science target catalogs."""
    service = get_science_data_service()
    return {"catalogs": service.get_available_catalogs()}


@router.get("/science/catalogs/{catalog_id}")
def get_science_catalog_info(catalog_id: str):
    """Get information about a science target catalog."""
    service = get_science_data_service()
    try:
        return service.get_catalog_info(catalog_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/science/catalogs/{catalog_id}/targets")
def get_science_targets(
    catalog_id: str,
    query: Optional[str] = Query(None),
    feature_type: Optional[str] = Query(None),
    priority_min: Optional[float] = Query(None),
    priority_max: Optional[float] = Query(None),
    visited: Optional[bool] = Query(None),
    limit: Optional[int] = Query(None),
):
    """Get science targets with optional filtering."""
    service = get_science_data_service()
    
    from app.services.science_data_service import ScienceTargetFilter
    filters = ScienceTargetFilter(
        query=query,
        feature_type=feature_type,
        priority_min=priority_min,
        priority_max=priority_max,
        visited=visited,
    )
    
    try:
        targets = service.get_targets(catalog_id, filters, limit)
        return {"targets": [t.__dict__ for t in targets], "count": len(targets)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/science/catalogs/{catalog_id}/targets/{target_id}")
def get_science_target(catalog_id: str, target_id: str):
    """Get a specific science target by ID."""
    service = get_science_data_service()
    try:
        target = service.get_target_by_id(catalog_id, target_id)
        return target.__dict__
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/science/catalogs/{catalog_id}/nearest")
def find_nearest_targets(
    catalog_id: str,
    x: float = Query(...),
    y: float = Query(...),
    max_distance_m: float = Query(5000),
    limit: int = Query(5),
):
    """Find nearest targets to a coordinate."""
    service = get_science_data_service()
    try:
        targets = service.find_nearest_targets(catalog_id, x, y, max_distance_m, limit)
        return {"targets": [t.__dict__ for t in targets], "count": len(targets)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/science/catalogs/{catalog_id}/feature-types")
def get_feature_types(catalog_id: str):
    """Get unique feature types in catalog."""
    service = get_science_data_service()
    try:
        return {"feature_types": service.get_feature_types(catalog_id)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/science/catalogs/{catalog_id}/priority-stats")
def get_priority_stats(catalog_id: str):
    """Get priority statistics for catalog."""
    service = get_science_data_service()
    try:
        return service.get_priority_stats(catalog_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/science/catalogs/{catalog_id}/visit-stats")
def get_visit_stats(catalog_id: str):
    """Get visit statistics for catalog."""
    service = get_science_data_service()
    try:
        return service.get_visit_stats(catalog_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


from datetime import datetime