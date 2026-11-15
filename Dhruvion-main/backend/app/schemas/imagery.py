"""Imagery schemas for API requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ImageryType(str, Enum):
    BASEMAP = "basemap"
    OVERLAY = "overlay"
    DERIVED = "derived"


class ImageryLayer(BaseModel):
    id: str
    name: str
    layer_type: str  # "tiles", "overlay"
    imagery_type: ImageryType
    status: str
    availability: str
    source: Dict[str, Any]
    crs: str
    resolution_m: Optional[float] = None
    units: Optional[str] = None
    bounds: Optional[List[float]] = None
    tile_url_template: Optional[str] = None
    overlay_url: Optional[str] = None
    max_zoom: Optional[int] = None
    warnings: List[str] = []


class ImageryLayerCatalogResponse(BaseModel):
    region_id: str
    items: List[ImageryLayer]


class TileRequest(BaseModel):
    layer_id: str
    z: int = Field(..., ge=0, le=18)
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)


class LayerAvailabilityRequest(BaseModel):
    layer_ids: List[str]


class LayerAvailabilityResponse(BaseModel):
    layer_id: str
    available: bool