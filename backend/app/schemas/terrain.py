"""Terrain schemas for API requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    x: float
    y: float
    crs: str


class TerrainValue(BaseModel):
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    roughness: Optional[float] = None


class TerrainQueryRequest(BaseModel):
    region_id: str = "gale_crater"
    x: float = Field(..., description="Longitude coordinate")
    y: float = Field(..., description="Latitude coordinate")
    layers: Optional[List[str]] = Field(default=None, description="Layers to query: elevation, slope, roughness")


class TerrainQueryResponse(BaseModel):
    region_id: str
    coordinate: Coordinate
    values: TerrainValue
    provenance: List[str] = []
    availability: str
    warnings: List[str] = []


class RasterLayerInfo(BaseModel):
    id: str
    name: str
    units: str
    type: str  # "observed" or "derived"
    available: bool
    metadata: Dict[str, Any] = {}


class RasterLayersResponse(BaseModel):
    layers: List[RasterLayerInfo]


class CoordinateValidationRequest(BaseModel):
    x: float
    y: float


class CoordinateValidationResponse(BaseModel):
    valid: bool
    coordinate: Coordinate
    coverage_bounds: Optional[List[float]] = None
    message: str


class LayerStatisticsResponse(BaseModel):
    layer_id: str
    count: int
    min: float
    max: float
    mean: float
    std: float
    median: float
    nodata_count: int
    total_pixels: int


class LayerStatisticsError(BaseModel):
    layer_id: str
    error: str