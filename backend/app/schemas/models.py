from typing import Any, Dict, List, Optional
from pydantic import BaseModel

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

class HazardsResponse(BaseModel):
    region_id: str
    features: Dict[str, Any]
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

class TargetsResponse(BaseModel):
    region_id: str
    items: List[ScienceTarget] = []

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
