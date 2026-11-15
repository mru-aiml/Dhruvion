"""Dataset catalog for managing and querying all available datasets."""

import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from enum import Enum

from app.core.config import settings
from app.core.logging_config import get_logger

from app.data_pipeline.ingestion import discover_datasets, get_dataset_status
from app.data_pipeline.metadata import DatasetMetadata, load_metadata, save_metadata
from app.data_pipeline.validation import validate_raster, validate_vector, validate_metadata_file

logger = get_logger(__name__)


class DatasetAvailability(str, Enum):
    """Dataset availability status for catalog."""
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    UNVALIDATED = "unvalidated"
    ERROR = "error"


@dataclass
class DatasetEntry:
    """Catalog entry for a dataset."""
    dataset_id: str
    name: str
    dataset_type: str  # "raster", "vector", "tiles"
    format: str
    status: str  # DatasetAvailability
    provenance: str
    file_path: str
    metadata_path: Optional[str] = None
    crs: Optional[str] = None
    coverage: Optional[Dict[str, Any]] = None
    resolution_m: Optional[float] = None
    file_size_bytes: Optional[int] = None
    feature_count: Optional[int] = None
    geometry_types: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_validated: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}
    
    @classmethod
    def from_metadata(cls, metadata: "DatasetMetadata") -> "DatasetEntry":
        """Create catalog entry from metadata."""
        return cls(
            dataset_id=metadata.dataset_id,
            name=metadata.name,
            dataset_type=metadata.dataset_type.value,
            format=metadata.format or "unknown",
            status=metadata.status.value,
            provenance=metadata.provenance.value,
            file_path=metadata.file_path or "",
            metadata_path="",
            crs=metadata.spatial_reference.crs,
            coverage=metadata.coverage.to_dict() if metadata.coverage else None,
            resolution_m=metadata.resolution_m,
            file_size_bytes=metadata.file_size_bytes,
            feature_count=metadata.feature_count,
            geometry_types=metadata.geometry_types,
            warnings=metadata.quality.warnings,
            last_validated=metadata.quality.validation_timestamp,
            metadata=metadata.to_dict(),
        )


class DatasetCatalog:
    """
    Thread-safe dataset catalog for managing all available datasets.
    
    Provides discovery, indexing, and querying of all datasets.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or settings.DATA_DIR
        self._catalog: Dict[str, DatasetEntry] = {}
        self._lock = threading.RLock()
        self._last_rebuild: Optional[datetime] = None
        self._metadata_cache: Dict[str, "DatasetMetadata"] = {}
    
    def rebuild(self, force: bool = False) -> int:
        """
        Rebuild the catalog by discovering all datasets.
        
        Returns number of datasets in catalog.
        """
        with self._lock:
            logger.info("Rebuilding dataset catalog...")
            self._catalog.clear()
            self._metadata_cache.clear()
            
            datasets = discover_datasets(self._data_dir)
            
            for dataset_info in datasets:
                entry = self._create_entry(dataset_info)
                if entry:
                    self._catalog[entry.dataset_id] = entry
            
            self._last_rebuild = datetime.utcnow()
            logger.info(f"Catalog rebuilt with {len(self._catalog)} datasets")
            return len(self._catalog)
    
    def _create_entry(self, dataset_info) -> Optional[DatasetEntry]:
        """Create catalog entry from discovered dataset info."""
        try:
            status = get_dataset_status(dataset_info)
            
            # Try to load metadata
            metadata = None
            if dataset_info.metadata_path and dataset_info.metadata_path.exists():
                from app.data_pipeline.metadata import load_metadata
                metadata = load_metadata(dataset_info.metadata_path)
            
            if metadata:
                return DatasetEntry.from_metadata(metadata)
            
            # Fallback to basic info
            file_size = dataset_info.source_path.stat().st_size if dataset_info.source_path.exists() else None
            
            return DatasetEntry(
                dataset_id=dataset_info.dataset_id,
                name=dataset_info.name,
                dataset_type=dataset_info.dataset_type,
                format=dataset_info.format,
                status=status,
                provenance=dataset_info.metadata.get("provenance", "unavailable"),
                file_path=str(dataset_info.source_path),
                metadata_path=str(dataset_info.metadata_path) if dataset_info.metadata_path else None,
                crs=dataset_info.metadata.get("crs"),
                coverage=self._extract_coverage(dataset_info.metadata),
                resolution_m=dataset_info.metadata.get("resolution_m") or dataset_info.metadata.get("pixel_size_m"),
                file_size_bytes=file_size,
                metadata=dataset_info.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create entry for {dataset_info.dataset_id}: {e}")
            return None
    
    def _extract_coverage(self, metadata: Dict) -> Optional[Dict[str, Any]]:
        """Extract coverage info from metadata."""
        if "coverage" in metadata:
            cov = metadata["coverage"]
            if isinstance(cov, dict) and "bounds" in cov:
                bounds = cov["bounds"]
                if isinstance(bounds, (list, tuple)) and len(bounds) == 4:
                    return {
                        "bounds": list(bounds),
                        "crs": cov.get("crs"),
                        "resolution_m": cov.get("resolution_m"),
                    }
        return None
    
    def get(self, dataset_id: str) -> Optional[DatasetEntry]:
        """Get dataset entry by ID."""
        with self._lock:
            return self._catalog.get(dataset_id)
    
    def get_all(self) -> List[DatasetEntry]:
        """Get all dataset entries."""
        with self._lock:
            return list(self._catalog.values())
    
    def get_by_type(self, dataset_type: str) -> List[DatasetEntry]:
        """Get entries by dataset type."""
        with self._lock:
            return [e for e in self._catalog.values() if e.dataset_type == dataset_type]
    
    def get_by_status(self, status: str) -> List[DatasetEntry]:
        """Get entries by availability status."""
        with self._lock:
            return [e for e in self._catalog.values() if e.status == status]
    
    def get_by_region(self, region_id: str) -> List[DatasetEntry]:
        """Get entries for a specific region (from metadata tags)."""
        with self._lock:
            return [e for e in self._catalog.values() 
                    if e.metadata.get("region_id") == region_id]
    
    def get_by_provenance(self, provenance: str) -> List[DatasetEntry]:
        """Get entries by provenance status."""
        with self._lock:
            return [e for e in self._catalog.values() if e.provenance == provenance]
    
    def search(
        self,
        dataset_type: Optional[str] = None,
        status: Optional[str] = None,
        provenance: Optional[str] = None,
        region_id: Optional[str] = None,
        text_query: Optional[str] = None,
    ) -> List[DatasetEntry]:
        """Search catalog with filters."""
        with self._lock:
            results = list(self._catalog.values())
            
            if dataset_type:
                results = [e for e in results if e.dataset_type == dataset_type]
            if status:
                results = [e for e in results if e.status == status]
            if provenance:
                results = [e for e in results if e.provenance == provenance]
            if region_id:
                results = [e for e in results if e.metadata.get("region_id") == region_id]
            if text_query:
                query = text_query.lower()
                results = [e for e in results 
                          if query in e.name.lower() or 
                             query in e.dataset_id.lower() or
                             query in str(e.metadata).lower()]
            
            return results
    
    def get_metadata(self, dataset_id: str) -> Optional["DatasetMetadata"]:
        """Get full metadata for a dataset (with caching)."""
        with self._lock:
            if dataset_id in self._metadata_cache:
                return self._metadata_cache[dataset_id]
            
            entry = self._catalog.get(dataset_id)
            if not entry or not entry.metadata_path:
                return None
            
            from app.data_pipeline.metadata import load_metadata
            metadata = load_metadata(Path(entry.metadata_path))
            if metadata:
                self._metadata_cache[dataset_id] = metadata
            return metadata
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        with self._lock:
            stats = {
                "total_datasets": len(self._catalog),
                "by_type": {},
                "by_status": {},
                "by_provenance": {},
                "total_size_bytes": 0,
                "last_rebuild": self._last_rebuild.isoformat() if self._last_rebuild else None,
            }
            
            for entry in self._catalog.values():
                stats["by_type"][entry.dataset_type] = stats["by_type"].get(entry.dataset_type, 0) + 1
                stats["by_status"][entry.status] = stats["by_status"].get(entry.status, 0) + 1
                stats["by_provenance"][entry.provenance] = stats["by_provenance"].get(entry.provenance, 0) + 1
                if entry.file_size_bytes:
                    stats["total_size_bytes"] += entry.file_size_bytes
            
            return stats
    
    def export_catalog(self, output_path: Path) -> bool:
        """Export catalog to JSON file."""
        try:
            with self._lock:
                data = {
                    "catalog_version": 1,
                    "generated_at": datetime.utcnow().isoformat(),
                    "datasets": [e.to_dict() for e in self._catalog.values()],
                    "statistics": self.get_statistics(),
                }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export catalog: {e}")
            return False


# Global catalog instance
_catalog_instance: Optional[DatasetCatalog] = None
_catalog_lock = threading.Lock()


def get_dataset_catalog(data_dir: Optional[Path] = None) -> DatasetCatalog:
    """Get or create the global dataset catalog instance."""
    global _catalog_instance
    
    with _catalog_lock:
        if _catalog_instance is None:
            _catalog_instance = DatasetCatalog(data_dir)
        return _catalog_instance


def rebuild_catalog(data_dir: Optional[Path] = None) -> DatasetCatalog:
    """Force rebuild of the global catalog."""
    global _catalog_instance
    
    with _catalog_lock:
        _catalog_instance = DatasetCatalog(data_dir)
        _catalog_instance.rebuild(force=True)
        return _catalog_instance