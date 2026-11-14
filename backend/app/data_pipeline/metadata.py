"""Dataset metadata handling and validation."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DatasetType(str, Enum):
    """Dataset type enumeration."""
    RASTER = "raster"
    VECTOR = "vector"
    TILES = "tiles"
    DERIVED = "derived"
    OTHER = "other"


class DataStatus(str, Enum):
    """Dataset availability status."""
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    UNVALIDATED = "unvalidated"
    ERROR = "error"


class ProvenanceStatus(str, Enum):
    """Data provenance status."""
    OBSERVED = "observed"
    DERIVED = "derived"
    SIMULATED = "simulated"
    UNAVAILABLE = "unavailable"


@dataclass
class DataSource:
    """Source information for a dataset."""
    name: Optional[str] = None
    provider: Optional[str] = None
    product_id: Optional[str] = None
    source_uri: Optional[str] = None
    acquisition_date: Optional[str] = None
    processing_date: Optional[str] = None
    license_notes: Optional[str] = None
    checksum_sha256: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SpatialReference:
    """Spatial reference system information."""
    crs: Optional[str] = None
    crs_wkt: Optional[str] = None
    crs_authority: Optional[str] = None
    crs_code: Optional[int] = None
    coordinate_system: Optional[str] = None  # e.g., "planetocentric", "planetographic"
    datum: Optional[str] = None
    prime_meridian: Optional[str] = None
    ellipsoid: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class SpatialCoverage:
    """Spatial coverage information."""
    bounds: Optional[Tuple[float, float, float, float]] = None  # (minx, miny, maxx, maxy)
    crs: Optional[str] = None
    resolution_m: Optional[float] = None
    resolution_unit: str = "meters"
    pixel_size_x: Optional[float] = None
    pixel_size_y: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.bounds:
            d["bounds"] = list(self.bounds)
        return d


@dataclass
class ProcessingInfo:
    """Processing history and derivation information."""
    method: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    software: Optional[str] = None
    version: Optional[str] = None
    timestamp: Optional[str] = None
    input_datasets: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class QualityInfo:
    """Data quality and validation information."""
    completeness: Optional[float] = None  # 0.0 to 1.0
    accuracy: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    validation_timestamp: Optional[str] = None
    validation_passed: Optional[bool] = None
    nodata_handling: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DatasetMetadata:
    """
    Comprehensive dataset metadata following NASA/PDS conventions.
    
    This is the canonical metadata model for all datasets in DHRUVION.
    """
    # Identity
    dataset_id: str
    name: str
    dataset_type: DatasetType
    status: DataStatus = DataStatus.UNVALIDATED
    provenance: ProvenanceStatus = ProvenanceStatus.UNAVAILABLE
    
    # Source information
    source: DataSource = field(default_factory=DataSource)
    
    # Spatial information
    spatial_reference: SpatialReference = field(default_factory=SpatialReference)
    coverage: SpatialCoverage = field(default_factory=SpatialCoverage)
    
    # Data characteristics
    format: Optional[str] = None  # e.g., "GeoTIFF", "GeoJSON", "IMG"
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    
    # Raster-specific
    resolution_m: Optional[float] = None
    pixel_size_x: Optional[float] = None
    pixel_size_y: Optional[float] = None
    nodata_value: Optional[float] = None
    bands: Optional[int] = None
    dtype: Optional[str] = None
    
    # Vector-specific
    feature_count: Optional[int] = None
    geometry_types: List[str] = field(default_factory=list)
    property_keys: List[str] = field(default_factory=list)
    
    # Derived/processing
    processing: ProcessingInfo = field(default_factory=ProcessingInfo)
    quality: QualityInfo = field(default_factory=QualityInfo)
    
    # Temporal
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acquired_at: Optional[str] = None
    
    # Catalog metadata
    catalog_version: int = 1
    tags: List[str] = field(default_factory=list)
    region_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        d = {}
        for k, v in asdict(self).items():
            if v is not None:
                if isinstance(v, Enum):
                    d[k] = v.value
                elif isinstance(v, (list, dict)) and not v:
                    continue  # Skip empty collections
                else:
                    d[k] = v
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetMetadata":
        """Create from dictionary."""
        # Convert enums
        if "dataset_type" in data and isinstance(data["dataset_type"], str):
            data["dataset_type"] = DatasetType(data["dataset_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = DataStatus(data["status"])
        if "provenance" in data and isinstance(data["provenance"], str):
            data["provenance"] = ProvenanceStatus(data["provenance"])
        
        # Convert nested objects
        if "source" in data and isinstance(data["source"], dict):
            data["source"] = DataSource(**data["source"])
        if "spatial_reference" in data and isinstance(data["spatial_reference"], dict):
            data["spatial_reference"] = SpatialReference(**data["spatial_reference"])
        if "coverage" in data and isinstance(data["coverage"], dict):
            data["coverage"] = SpatialCoverage(**data["coverage"])
        if "processing" in data and isinstance(data["processing"], dict):
            data["processing"] = ProcessingInfo(**data["processing"])
        if "quality" in data and isinstance(data["quality"], dict):
            data["quality"] = QualityInfo(**data["quality"])
        
        # Convert coverage bounds tuple
        if "coverage" in data and isinstance(data["coverage"], dict):
            cov = data["coverage"]
            if "bounds" in cov and isinstance(cov["bounds"], list):
                cov["bounds"] = tuple(cov["bounds"])
        
        return cls(**data)
    
    def update_timestamp(self):
        self.updated_at = datetime.utcnow().isoformat()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a concise summary for API responses."""
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "dataset_type": self.dataset_type.value,
            "status": self.status.value,
            "provenance": self.provenance.value,
            "format": self.format,
            "coverage": self.coverage.to_dict() if self.coverage else None,
            "crs": self.spatial_reference.crs,
            "resolution_m": self.resolution_m,
            "availability": self.status.value,
            "provenance": self.provenance.value,
            "warnings": self.quality.warnings,
        }


def load_metadata(path: Path) -> Optional[DatasetMetadata]:
    """
    Load metadata from a JSON file.
    
    Returns None if file doesn't exist or is invalid.
    """
    if not path.exists():
        logger.warning(f"Metadata file not found: {path}")
        return None
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return DatasetMetadata.from_dict(data)
    except Exception as e:
        logger.error(f"Failed to load metadata from {path}: {e}")
        return None


def save_metadata(metadata: DatasetMetadata, path: Path) -> bool:
    """
    Save metadata to a JSON file.
    
    Returns True on success.
    """
    try:
        metadata.update_timestamp()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save metadata to {path}: {e}")
        return False


def validate_metadata(metadata: DatasetMetadata) -> Tuple[bool, List[str]]:
    """
    Validate dataset metadata for completeness and correctness.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Required fields
    if not metadata.dataset_id:
        errors.append("Missing dataset_id")
    if not metadata.name:
        errors.append("Missing name")
    if not metadata.dataset_type:
        errors.append("Missing dataset_type")
    
    # Spatial reference validation
    if metadata.spatial_reference:
        if not metadata.spatial_reference.crs:
            errors.append("Missing CRS in spatial reference")
    else:
        errors.append("Missing spatial reference")
    
    # Coverage validation
    if metadata.coverage:
        if metadata.coverage.bounds:
            bounds = metadata.coverage.bounds
            if len(bounds) != 4:
                errors.append("Bounds must have 4 values (minx, miny, maxx, maxy)")
            else:
                minx, miny, maxx, maxy = bounds
                if minx >= maxx or miny >= maxy:
                    errors.append("Invalid bounds: min >= max")
    else:
        errors.append("Missing spatial coverage")
    
    # Source validation
    if metadata.source and metadata.source.provider:
        if metadata.source.provider not in ["NASA", "PDS", "USGS", "JPL", "ASU", "ESA", "DHRUVION processing"]:
            logger.warning(f"Unrecognized provider: {metadata.source.provider}")
    
    # File validation
    if metadata.file_path:
        from pathlib import Path
        if not Path(metadata.file_path).exists():
            errors.append(f"Source file does not exist: {metadata.file_path}")
    
    return len(errors) == 0, errors


def merge_metadata(base: DatasetMetadata, update: DatasetMetadata) -> DatasetMetadata:
    """
    Merge two metadata objects, with update taking precedence.
    
    Non-None fields from update override base.
    """
    base_dict = base.to_dict()
    update_dict = update.to_dict()
    
    # Deep merge for nested objects
    for key in ["source", "spatial_reference", "coverage", "processing", "quality"]:
        if key in update_dict and update_dict[key]:
            if key in base_dict and base_dict[key]:
                # Merge nested dicts
                merged = {**base_dict[key], **update_dict[key]}
                base_dict[key] = merged
            else:
                base_dict[key] = update_dict[key]
        elif key in update_dict and update_dict[key]:
            base_dict[key] = update_dict[key]
        # For simple fields, just use update if not None
        elif key in update_dict and update_dict[key] is not None:
            base_dict[key] = update_dict[key]
    
    return DatasetMetadata.from_dict(base_dict)


def create_metadata_from_raster(
    path: Path,
    dataset_id: str,
    name: str,
    source: DataSource,
    spatial_ref: SpatialReference,
    coverage: SpatialCoverage,
    provenance: ProvenanceStatus = ProvenanceStatus.OBSERVED,
) -> DatasetMetadata:
    """
    Create metadata from raster file properties.
    """
    from app.data_pipeline.raster_loader import get_raster_info
    
    info = get_raster_info(path)
    if "error" in info:
        raise ValueError(f"Failed to read raster: {info['error']}")
    
    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        name=name,
        dataset_type=DatasetType.RASTER,
        status=DataStatus.AVAILABLE,
        provenance=provenance,
        source=source,
        spatial_reference=spatial_ref,
        coverage=coverage,
        format="GeoTIFF" if path.suffix.lower() in (".tif", ".tiff") else path.suffix,
        file_path=str(path),
        file_size_bytes=path.stat().st_size if path.exists() else None,
        resolution_m=info.get("resolution", [None, None])[0],
        pixel_size_x=info.get("resolution", [None, None])[0],
        pixel_size_y=info.get("resolution", [None, None])[1],
        nodata_value=info.get("nodata"),
        bands=info.get("count"),
        dtype=info.get("dtype"),
    )
    
    return metadata


def create_metadata_from_vector(
    path: Path,
    dataset_id: str,
    name: str,
    source: DataSource,
    spatial_ref: SpatialReference,
    coverage: SpatialCoverage,
    provenance: ProvenanceStatus = ProvenanceStatus.OBSERVED,
) -> DatasetMetadata:
    """
    Create metadata from vector file properties.
    """
    info = get_vector_info(path)
    if "error" in info:
        raise ValueError(f"Failed to read vector: {info['error']}")
    
    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        name=name,
        dataset_type=DatasetType.VECTOR,
        status=DataStatus.AVAILABLE,
        provenance=provenance,
        source=source,
        spatial_reference=spatial_ref,
        coverage=coverage,
        format="GeoJSON" if path.suffix.lower() == ".geojson" else path.suffix,
        file_path=str(path),
        file_size_bytes=path.stat().st_size if path.exists() else None,
        feature_count=info.get("feature_count"),
        geometry_types=info.get("geometry_types", []),
        property_keys=info.get("property_keys", []),
    )
    
    return metadata