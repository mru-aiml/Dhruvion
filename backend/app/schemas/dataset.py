"""Dataset schemas for API requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class DatasetType(str, Enum):
    RASTER = "raster"
    VECTOR = "vector"
    TILES = "tiles"
    DERIVED = "derived"
    OTHER = "other"


class DataStatus(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    UNVALIDATED = "unvalidated"
    ERROR = "error"


class ProvenanceStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    SIMULATED = "simulated"
    UNAVAILABLE = "unavailable"


class DataSource(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    product_id: Optional[str] = None
    source_uri: Optional[str] = None
    acquisition_date: Optional[str] = None
    processing_date: Optional[str] = None
    license_notes: Optional[str] = None
    checksum_sha256: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SpatialReference(BaseModel):
    crs: Optional[str] = None
    crs_wkt: Optional[str] = None
    crs_authority: Optional[str] = None
    crs_code: Optional[int] = None
    coordinate_system: Optional[str] = None
    datum: Optional[str] = None
    prime_meridian: Optional[str] = None
    ellipsoid: Optional[str] = None


class SpatialCoverage(BaseModel):
    bounds: Optional[List[float]] = None  # [minx, miny, maxx, maxy]
    crs: Optional[str] = None
    resolution_m: Optional[float] = None
    resolution_unit: str = "meters"
    pixel_size_x: Optional[float] = None
    pixel_size_y: Optional[float] = None


class ProcessingInfo(BaseModel):
    method: Optional[str] = None
    parameters: Dict[str, Any] = {}
    software: Optional[str] = None
    version: Optional[str] = None
    timestamp: Optional[str] = None
    input_datasets: List[str] = []


class QualityInfo(BaseModel):
    completeness: Optional[float] = None
    accuracy: Optional[str] = None
    warnings: List[str] = []
    validation_timestamp: Optional[str] = None
    validation_passed: Optional[bool] = None
    nodata_handling: Optional[str] = None


class DatasetMetadata(BaseModel):
    """Complete dataset metadata model."""
    dataset_id: str
    name: str
    dataset_type: DatasetType
    status: DataStatus = DataStatus.UNVALIDATED
    provenance: ProvenanceStatus = ProvenanceStatus.UNAVAILABLE
    source: DataSource = DataSource()
    spatial_reference: SpatialReference = SpatialReference()
    coverage: SpatialCoverage = SpatialCoverage()
    format: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    resolution_m: Optional[float] = None
    pixel_size_x: Optional[float] = None
    pixel_size_y: Optional[float] = None
    nodata_value: Optional[float] = None
    bands: Optional[int] = None
    dtype: Optional[str] = None
    feature_count: Optional[int] = None
    geometry_types: List[str] = []
    property_keys: List[str] = []
    processing: ProcessingInfo = ProcessingInfo()
    quality: QualityInfo = QualityInfo()
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    acquired_at: Optional[str] = None
    catalog_version: int = 1
    tags: List[str] = []
    region_id: Optional[str] = None


class DatasetEntry(BaseModel):
    """Catalog entry for API responses."""
    dataset_id: str
    name: str
    dataset_type: str
    format: str
    status: str
    provenance: str
    file_path: str
    metadata_path: Optional[str] = None
    crs: Optional[str] = None
    coverage: Optional[Dict[str, Any]] = None
    resolution_m: Optional[float] = None
    file_size_bytes: Optional[int] = None
    feature_count: Optional[int] = None
    geometry_types: List[str] = []
    warnings: List[str] = []
    last_validated: Optional[str] = None
    metadata: Dict[str, Any] = {}


class DatasetCatalogResponse(BaseModel):
    catalog_version: int
    generated_at: str
    datasets: List[DatasetEntry]
    statistics: Dict[str, Any]


class DatasetValidationRequest(BaseModel):
    path: str


class DatasetValidationResponse(BaseModel):
    is_valid: bool
    dataset_id: Optional[str] = None
    dataset_path: Optional[str] = None
    issues: List[Dict[str, Any]] = []


class DatasetCatalogRequest(BaseModel):
    data_dir: Optional[str] = None


class DatasetCatalogRebuildResponse(BaseModel):
    datasets_count: int
    message: str