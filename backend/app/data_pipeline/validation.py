"""Validation utilities for geospatial datasets."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Validation issue severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    dataset_id: Optional[str] = None
    dataset_path: Optional[str] = None
    
    def add_error(self, code: str, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        self.issues.append(ValidationIssue(ValidationSeverity.ERROR, code, message, field, details))
        self.is_valid = False
    
    def add_warning(self, code: str, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        self.issues.append(ValidationIssue(ValidationSeverity.WARNING, code, message, field, details))
    
    def add_info(self, code: str, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        self.issues.append(ValidationIssue(ValidationSeverity.INFO, code, message, field, details))
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "issues": [
                {
                    "severity": i.severity.value,
                    "code": i.code,
                    "message": i.message,
                    "field": i.field,
                    "details": i.details,
                }
                for i in self.issues
            ],
        }


def validate_raster(path: Path) -> ValidationResult:
    """
    Validate a raster dataset file.
    
    Checks:
    - File exists and is readable
    - Valid raster format
    - CRS defined
    - Valid bounds
    - NoData value defined
    - Valid dimensions
    - Reasonable resolution
    """
    from app.data_pipeline.raster_loader import get_raster_info
    
    result = ValidationResult(dataset_path=str(path))
    
    if not path.exists():
        result.add_error("FILE_NOT_FOUND", f"Raster file not found: {path}")
        return result
    
    info = get_raster_info(path)
    if "error" in info:
        result.add_error("READ_ERROR", f"Failed to read raster: {info['error']}")
        return result
    
    # Validate CRS
    if not info.get("crs"):
        result.add_error("MISSING_CRS", "Raster has no CRS defined")
    else:
        result.add_info("CRS_OK", f"CRS: {info['crs']}")
    
    # Validate bounds
    bounds = info.get("bounds")
    if not bounds:
        result.add_error("MISSING_BOUNDS", "Raster has no bounds")
    else:
        result.add_info("BOUNDS_OK", f"Bounds: {bounds}")
    
    # Validate resolution
    resolution = info.get("resolution")
    if not resolution or resolution[0] is None or resolution[1] is None:
        result.add_warning("MISSING_RESOLUTION", "Could not determine pixel resolution")
    else:
        x_res, y_res = resolution
        result.add_info("RESOLUTION_OK", f"Resolution: {x_res:.2f} x {y_res:.2f}")
        
        # Warn if resolution seems unreasonable for Mars data
        if x_res > 10000 or y_res > 10000:
            result.add_warning("UNUSUAL_RESOLUTION", 
                f"Unusually large pixel size: {x_res:.2f} x {y_res:.2f}")
    
    # Validate dimensions
    width = info.get("width", 0)
    height = info.get("height", 0)
    if width <= 0 or height <= 0:
        result.add_error("INVALID_DIMENSIONS", f"Invalid dimensions: {width}x{height}")
    else:
        result.add_info("DIMENSIONS_OK", f"Dimensions: {width}x{height}")
    
    # Validate NoData
    nodata = info.get("nodata")
    if nodata is None:
        result.add_warning("MISSING_NODATA", "NoData value not defined")
    else:
        result.add_info("NODATA_OK", f"NoData value: {nodata}")
    
    # Validate CRS is Mars-appropriate
    crs = info.get("crs", "")
    if crs and "mars" not in crs.lower() and "iau" not in crs.lower() and "3396" not in crs:
        result.add_warning("NON_MARS_CRS", f"CRS may not be Mars-specific: {crs}")
    
    return result


def validate_vector(path: Path) -> ValidationResult:
    """
    Validate a vector dataset file (GeoJSON).
    
    Checks:
    - File exists and is readable
    - Valid GeoJSON structure
    - FeatureCollection type
    - Valid geometries
    - CRS defined
    - Properties present
    """
    from app.data_pipeline.vector_loader import validate_geojson, get_vector_info
    
    result = ValidationResult(dataset_path=str(path))
    
    if not path.exists():
        result.add_error("FILE_NOT_FOUND", f"Vector file not found: {path}")
        return result
    
    info = get_vector_info(path)
    if "error" in info:
        result.add_error("READ_ERROR", f"Failed to read vector: {info['error']}")
        return result
    
    # Validate structure
    with open(path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error("INVALID_JSON", f"Invalid JSON: {e}")
            return result
    
    is_valid, errors = validate_geojson(data)
    if not is_valid:
        for err in errors:
            result.add_error("GEOJSON_INVALID", err)
        return result
    
    result.add_info("GEOJSON_VALID", "GeoJSON structure is valid")
    
    # Check feature count
    feature_count = info.get("feature_count", 0)
    if feature_count == 0:
        result.add_warning("EMPTY_FEATURES", "No features in dataset")
    else:
        result.add_info("FEATURE_COUNT_OK", f"Feature count: {feature_count}")
    
    # Check geometry types
    geom_types = info.get("geometry_types", [])
    if not geom_types:
        result.add_warning("NO_GEOMETRY_TYPES", "No geometry types found")
    else:
        result.add_info("GEOM_TYPES_OK", f"Geometry types: {', '.join(geom_types)}")
    
    # Check CRS
    crs = info.get("crs")
    if not crs:
        result.add_error("MISSING_CRS", "Vector dataset has no CRS")
    else:
        result.add_info("CRS_OK", f"CRS: {crs}")
    
    # Check properties
    prop_keys = info.get("property_keys", [])
    if not prop_keys:
        result.add_warning("NO_PROPERTIES", "No property keys found")
    else:
        result.add_info("PROPERTIES_OK", f"Property keys: {len(prop_keys)}")
    
    return result


def validate_metadata_file(path: Path) -> ValidationResult:
    """
    Validate a dataset metadata JSON file.
    """
    from app.data_pipeline.metadata import load_metadata, validate_metadata
    
    result = ValidationResult(dataset_path=str(path))
    
    if not path.exists():
        result.add_error("FILE_NOT_FOUND", f"Metadata file not found: {path}")
        return result
    
    metadata = load_metadata(path)
    if metadata is None:
        result.add_error("LOAD_FAILED", "Failed to load metadata")
        return result
    
    result.dataset_id = metadata.dataset_id
    
    is_valid, errors = validate_metadata(metadata)
    if not is_valid:
        for err in errors:
            result.add_error("METADATA_INVALID", err)
    else:
        result.add_info("METADATA_VALID", "Metadata structure is valid")
    
    # Additional checks
    if metadata.status.value == "unvalidated":
        result.add_warning("UNVALIDATED", "Dataset status is unvalidated")
    
    if metadata.provenance.value == "unavailable":
        result.add_warning("PROVENANCE_UNAVAILABLE", "Provenance is unavailable")
    
    if not metadata.coverage.bounds:
        result.add_warning("MISSING_BOUNDS", "No spatial bounds in metadata")
    
    if not metadata.source.provider:
        result.add_warning("MISSING_PROVIDER", "No data provider specified")
    
    return result


def validate_coordinate_in_coverage(
    x: float,
    y: float,
    coverage_bounds: Tuple[float, float, float, float],
    crs: Optional[str] = None
) -> ValidationResult:
    """
    Validate that a coordinate falls within dataset coverage.
    """
    result = ValidationResult()
    
    minx, miny, maxx, maxy = coverage_bounds
    
    if not (minx <= x <= maxx and miny <= y <= maxy):
        result.add_error(
            "COORDINATE_OUTSIDE_COVERAGE",
            f"Coordinate ({x}, {y}) outside coverage bounds {coverage_bounds}",
            details={"coordinate": [x, y], "bounds": list(coverage_bounds)}
        )
    else:
        result.add_info("COORDINATE_IN_COVERAGE", f"Coordinate within coverage")
    
    return result


def validate_dataset_catalog(catalog: List[Dict[str, Any]]) -> ValidationResult:
    """
    Validate a dataset catalog for consistency.
    """
    result = ValidationResult()
    
    dataset_ids = set()
    for entry in catalog:
        dataset_id = entry.get("dataset_id")
        if not dataset_id:
            result.add_error("MISSING_ID", "Dataset entry missing dataset_id")
            continue
        
        if dataset_id in dataset_ids:
            result.add_error("DUPLICATE_ID", f"Duplicate dataset_id: {dataset_id}")
        dataset_ids.add(dataset_id)
        
        # Check required fields
        for field in ["name", "dataset_type", "status", "file_path"]:
            if not entry.get(field):
                result.add_warning("MISSING_FIELD", f"Missing {field} for {dataset_id}")
    
    if result.is_valid:
        result.add_info("CATALOG_VALID", f"Catalog contains {len(catalog)} datasets")
    
    return result


def run_full_validation(data_dir: Path) -> Dict[str, ValidationResult]:
    """
    Run full validation on all datasets in the data directory.
    
    Returns:
        Dictionary mapping dataset_id to ValidationResult
    """
    from app.data_pipeline.ingestion import discover_datasets
    
    results = {}
    datasets = discover_datasets(data_dir)
    
    for dataset in datasets:
        if dataset.dataset_type == "raster":
            result = validate_raster(dataset.source_path)
        elif dataset.dataset_type == "vector":
            result = validate_vector(dataset.source_path)
        else:
            result = ValidationResult()
            result.add_warning("UNKNOWN_TYPE", f"Unknown dataset type: {dataset.dataset_type}")
        
        result.dataset_id = dataset.dataset_id
        result.dataset_path = str(dataset.source_path)
        results[dataset.dataset_id] = result
    
    return results