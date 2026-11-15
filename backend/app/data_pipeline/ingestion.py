"""Dataset ingestion and discovery utilities."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DatasetInfo:
    """Discovered dataset information."""
    dataset_id: str
    name: str
    dataset_type: str  # "raster", "vector", "tiles"
    source_path: Path
    metadata_path: Optional[Path] = None
    format: str = "unknown"
    status: str = "discovered"  # discovered, validated, available, error
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)


def discover_datasets(base_path: Optional[Path] = None) -> List[DatasetInfo]:
    """
    Discover all datasets in the data directories.
    
    Scans RAW_DIR, PROCESSED_DIR for supported dataset formats.
    """
    if base_path is None:
        base_path = settings.DATA_DIR
    
    datasets = []
    
    # Search in raw directory
    raw_dir = base_path / "raw"
    if raw_dir.exists():
        datasets.extend(_discover_in_directory(raw_dir, "raw"))
    
    # Search in processed directory
    processed_dir = base_path / "processed"
    if processed_dir.exists():
        datasets.extend(_discover_in_directory(processed_dir, "processed"))
    
    logger.info(f"Discovered {len(datasets)} datasets")
    return datasets


def _discover_in_directory(directory: Path, category: str) -> List[DatasetInfo]:
    """Recursively discover datasets in a directory."""
    datasets = []
    
    # Supported raster formats
    raster_extensions = {".tif", ".tiff", ".img", ".geotiff", ".gtiff"}
    # Supported vector formats
    vector_extensions = {".geojson", ".json", ".shp", ".gpkg"}
    
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        
        # Skip metadata files and hidden files
        if file_path.name.startswith(".") or file_path.name == "metadata.json" or file_path.name.endswith("_metadata.json"):
            continue
        
        # Determine dataset type
        if file_path.suffix.lower() in raster_extensions:
            dataset_type = "raster"
        elif file_path.suffix.lower() in vector_extensions:
            dataset_type = "vector"
        else:
            continue  # Skip unsupported formats
        
        # Look for associated metadata file
        # First check for stem-specific metadata (e.g., slope_metadata.json for slope.tif)
        metadata_path = file_path.parent / f"{file_path.stem}_metadata.json"
        if not metadata_path.exists():
            # Then check for generic metadata.json in same directory
            metadata_path = file_path.parent / "metadata.json"
        if not metadata_path.exists():
            # Check parent directories up to 2 levels
            for parent in file_path.parents:
                meta_path = parent / "metadata.json"
                if meta_path.exists():
                    metadata_path = meta_path
                    break
        
        # Generate dataset ID from relative path
        relative_path = file_path.relative_to(settings.DATA_DIR)
        dataset_id = str(relative_path).replace("/", "_").replace(".", "_")
        
        dataset_info = DatasetInfo(
            dataset_id=dataset_id,
            name=file_path.stem,
            dataset_type=dataset_type,
            source_path=file_path,
            metadata_path=metadata_path if metadata_path.exists() else None,
            format=file_path.suffix.lower(),
        )
        
        # Load metadata if available
        if dataset_info.metadata_path:
            try:
                with open(dataset_info.metadata_path, "r") as f:
                    dataset_info.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata for {dataset_info.dataset_id}: {e}")
                dataset_info.validation_errors.append(f"Metadata load error: {e}")
        
        datasets.append(dataset_info)
    
    return datasets


def load_dataset_metadata(dataset_info: "DatasetInfo") -> Dict[str, Any]:
    """Load and return metadata for a discovered dataset."""
    if dataset_info.metadata:
        return dataset_info.metadata
    
    if dataset_info.metadata_path and dataset_info.metadata_path.exists():
        try:
            with open(dataset_info.metadata_path, "r") as f:
                dataset_info.metadata = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metadata for {dataset_info.dataset_id}: {e}")
            dataset_info.validation_errors.append(f"Metadata load error: {e}")
    
    return dataset_info.metadata


def get_dataset_status(dataset_info: "DatasetInfo") -> str:
    """
    Determine the status of a dataset based on its metadata and validation.
    
    Returns: "available", "unavailable", "unvalidated", "error"
    """
    if dataset_info.validation_errors:
        return "error"
    
    if not dataset_info.metadata_path or not dataset_info.metadata_path.exists():
        return "unvalidated"
    
    metadata = dataset_info.metadata
    if not metadata:
        return "unvalidated"
    
    # Check for required metadata fields
    required_fields = ["source_file", "coverage", "crs", "units"]
    missing_fields = [field for field in required_fields if field not in metadata]
    
    if missing_fields:
        return "unvalidated"
    
    # Check if source file exists
    if not dataset_info.source_path.exists():
        return "unavailable"
    
    return "available"