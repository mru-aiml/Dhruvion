"""Science data service for managing science targets and geological features."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from app.core.config import settings
from app.core.exceptions import UnavailableError, NotFoundError, InvalidInputError
from app.core.logging_config import get_logger
from app.data_pipeline.vector_loader import (
    VectorDataset,
    load_vector_dataset,
    query_vector_features,
    validate_geojson,
    get_vector_info,
)
from app.data_pipeline.catalog import get_dataset_catalog

logger = get_logger(__name__)


@dataclass
class ScienceTarget:
    """Science target representation."""
    id: str
    name: str
    feature_type: Optional[str] = None
    geometry: Dict[str, Any] = None
    coordinate_crs: str = "urn:ogc:def:crs:IAU2000::104905"
    priority: Optional[float] = None
    description: Optional[str] = None
    interpretation: Optional[str] = None
    provenance: List[str] = None
    warnings: List[str] = None
    distance_m: Optional[float] = None
    source_name: Optional[str] = None
    visited: Optional[bool] = None
    
    def __post_init__(self):
        if self.geometry is None:
            self.geometry = {"type": "Point", "coordinates": [0, 0]}
        if self.provenance is None:
            self.provenance = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ScienceTargetFilter:
    """Filter parameters for science target queries."""
    query: Optional[str] = None
    feature_type: Optional[str] = None
    priority_min: Optional[float] = None
    priority_max: Optional[float] = None
    visited: Optional[bool] = None
    bbox: Optional[Tuple[float, float, float, float]] = None  # (minx, miny, maxx, maxy)
    max_distance_m: Optional[float] = None
    origin_x: Optional[float] = None
    origin_y: Optional[float] = None


class ScienceDataService:
    """
    Service for managing and querying science targets and geological features.
    
    Handles:
    - Loading and validating science target catalogs
    - Filtering and searching targets
    - Distance calculations
    - Provenance tracking
    """
    
    def __init__(self):
        self._catalogs: Dict[str, VectorDataset] = {}
        self._region_crs = "urn:ogc:def:crs:IAU2000::104905"
        self._targets_cache: Dict[str, List[ScienceTarget]] = {}
    
    def load_catalog(self, catalog_id: str, path: Path) -> int:
        """
        Load a science target catalog from file.
        
        Returns number of features loaded.
        """
        dataset = load_vector_dataset(path, catalog_id, f"Science Targets - {catalog_id}")
        dataset.load()
        
        # Convert features to ScienceTarget objects
        targets = []
        for feat in dataset.features:
            target = self._feature_to_target(feat)
            targets.append(target)
        
        self._catalogs[catalog_id] = dataset
        self._targets_cache[catalog_id] = targets
        
        logger.info(f"Loaded science target catalog '{catalog_id}' with {len(targets)} targets")
        return len(targets)
    
    def _feature_to_target(self, feature) -> ScienceTarget:
        """Convert vector feature to ScienceTarget."""
        props = feature.properties
        coords = feature.geometry.get("coordinates", [0, 0])
        
        return ScienceTarget(
            id=feature.id,
            name=props.get("name", f"Target {feature.id}"),
            feature_type=props.get("feature_type"),
            geometry={
                "type": "Point",
                "coordinates": coords
            },
            coordinate_crs=props.get("coordinate_crs", "urn:ogc:def:crs:IAU2000::104905"),
            priority=props.get("priority"),
            description=props.get("description"),
            interpretation=props.get("interpretation"),
            provenance=props.get("provenance", ["simulated"]),
            warnings=props.get("warnings", []),
            distance_m=props.get("distance_m"),
            source_name=props.get("source_name"),
            visited=props.get("visited"),
        )
    
    def get_targets(
        self,
        catalog_id: str,
        filters: Optional[ScienceTargetFilter] = None,
        limit: Optional[int] = None
    ) -> List[ScienceTarget]:
        """
        Get science targets with optional filtering.
        """
        if catalog_id not in self._targets_cache:
            raise NotFoundError("Catalog not found", details={"catalog_id": catalog_id})
        
        targets = self._targets_cache[catalog_id]
        
        if not filters:
            return targets[:limit] if limit else targets
        
        # Apply filters
        filtered = []
        for target in targets:
            if not self._matches_filter(target, filters):
                continue
            filtered.append(target)
        
        if limit:
            filtered = filtered[:limit]
        
        return filtered
    
    def _matches_filter(self, target: ScienceTarget, filters: ScienceTargetFilter) -> bool:
        """Check if target matches all filter criteria."""
        
        # Text search
        if filters.query:
            query = filters.query.lower()
            searchable = " ".join([
                target.name or "",
                target.feature_type or "",
                target.description or "",
                target.source_name or "",
            ]).lower()
            if query not in searchable:
                return False
        
        # Feature type
        if filters.feature_type and target.feature_type != filters.feature_type:
            return False
        
        # Priority range
        if filters.priority_min is not None and (target.priority or 0) < filters.priority_min:
            return False
        if filters.priority_max is not None and (target.priority or 0) > filters.priority_max:
            return False
        
        # Visit state
        if filters.visited is not None and target.visited != filters.visited:
            return False
        
        # Distance from origin
        if filters.max_distance_m is not None and filters.origin_x is not None and filters.origin_y is not None:
            coords = target.geometry.get("coordinates", [0, 0])
            dist = self._calculate_distance(
                filters.origin_x, filters.origin_y,
                coords[0], coords[1]
            )
            if dist > filters.max_distance_m:
                return False
        
        # Bounding box
        if filters.bbox:
            coords = target.geometry.get("coordinates", [0, 0])
            minx, miny, maxx, maxy = filters.bbox
            if not (minx <= coords[0] <= maxx and miny <= coords[1] <= maxy):
                return False
        
        return True
    
    def _calculate_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate approximate distance in meters between two coordinates."""
        # Simple approximation for small distances on Mars
        # 1 degree lat ≈ 59 km, 1 degree lon ≈ 59 km * cos(lat)
        import math
        lat_avg = (y1 + y2) / 2
        dx = (x2 - x1) * 59000 * math.cos(math.radians(lat_avg))
        dy = (y2 - y1) * 59000
        return math.sqrt(dx * dx + dy * dy)
    
    def get_target_by_id(self, catalog_id: str, target_id: str) -> ScienceTarget:
        """Get a specific target by ID."""
        targets = self.get_targets(catalog_id)
        for target in targets:
            if target.id == target_id:
                return target
        raise NotFoundError("Target not found", details={"target_id": target_id})
    
    def get_feature_types(self, catalog_id: str) -> List[str]:
        """Get unique feature types in catalog."""
        targets = self.get_targets(catalog_id)
        types = set(t.feature_type for t in targets if t.feature_type)
        return sorted(types)
    
    def get_priority_stats(self, catalog_id: str) -> Dict[str, Any]:
        """Get priority statistics for catalog."""
        targets = self.get_targets(catalog_id)
        priorities = [t.priority for t in targets if t.priority is not None]
        
        if not priorities:
            return {"count": 0, "min": None, "max": None, "mean": None}
        
        return {
            "count": len(priorities),
            "min": min(priorities),
            "max": max(priorities),
            "mean": sum(priorities) / len(priorities),
            "high_priority": sum(1 for p in priorities if p >= 0.8),
            "medium_priority": sum(1 for p in priorities if 0.5 <= p < 0.8),
            "low_priority": sum(1 for p in priorities if p < 0.5),
        }
    
    def get_visit_stats(self, catalog_id: str) -> Dict[str, int]:
        """Get visit statistics for catalog."""
        targets = self.get_targets(catalog_id)
        visited = sum(1 for t in targets if t.visited)
        unvisited = sum(1 for t in targets if t.visited is False)
        unknown = sum(1 for t in targets if t.visited is None)
        
        return {
            "total": len(targets),
            "visited": visited,
            "unvisited": unvisited,
            "unknown": unknown,
        }
    
    def get_catalog_info(self, catalog_id: str) -> Dict[str, Any]:
        """Get catalog metadata."""
        if catalog_id not in self._catalogs:
            raise NotFoundError("Catalog not found", details={"catalog_id": catalog_id})
        
        dataset = self._catalogs[catalog_id]
        targets = self._targets_cache[catalog_id]
        
        return {
            "catalog_id": catalog_id,
            "name": dataset.name,
            "feature_count": len(targets),
            "crs": dataset.crs,
            "bounds": dataset.bounds,
            "feature_types": self.get_feature_types(catalog_id),
            "priority_stats": self.get_priority_stats(catalog_id),
            "visit_stats": self.get_visit_stats(catalog_id),
        }
    
    def get_available_catalogs(self) -> List[Dict[str, Any]]:
        """Get list of available catalogs."""
        return [self.get_catalog_info(cid) for cid in self._catalogs.keys()]
    
    def find_nearest_targets(
        self,
        catalog_id: str,
        x: float,
        y: float,
        max_distance_m: float = 5000,
        limit: int = 5
    ) -> List[ScienceTarget]:
        """Find targets nearest to a coordinate."""
        filters = ScienceTargetFilter(
            origin_x=x,
            origin_y=y,
            max_distance_m=max_distance_m,
        )
        targets = self.get_targets(catalog_id, filters)
        
        # Sort by distance
        targets_with_dist = []
        for t in targets:
            coords = t.geometry.get("coordinates", [0, 0])
            dist = self._calculate_distance(x, y, coords[0], coords[1])
            targets_with_dist.append((dist, t))
        
        targets_with_dist.sort(key=lambda x: x[0])
        return [t for _, t in targets_with_dist[:limit]]


# Global service instance
_science_service: Optional[ScienceDataService] = None


def get_science_data_service() -> ScienceDataService:
    """Get or create the science data service instance."""
    global _science_service
    if _science_service is None:
        _science_service = ScienceDataService()
        # Load demo catalog if available
        demo_path = settings.DATA_DIR / "processed" / "science_targets.geojson"
        if demo_path.exists():
            try:
                _science_service.load_catalog("demo", demo_path)
            except Exception as e:
                logger.warning(f"Could not load demo science targets: {e}")
    return _science_service