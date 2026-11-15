"""Vector dataset (GeoJSON) loading and querying utilities."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

try:
    from shapely.geometry import shape, mapping, GeometryCollection
    from shapely.geometry.base import BaseGeometry
    from shapely.ops import transform as shapely_transform
    from shapely import is_valid, validation
    SHAPELY_AVAILABLE = True
except Exception:
    SHAPELY_AVAILABLE = False

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VectorFeature:
    """Represents a single vector feature."""
    id: str
    geometry: Dict[str, Any]
    properties: Dict[str, Any]
    crs: Optional[str] = None
    _shapely_geom: Optional[Any] = field(default=None, repr=False)
    
    @property
    def shapely_geom(self):
        """Get Shapely geometry object (lazy)."""
        if self._shapely_geom is None and SHAPELY_AVAILABLE:
            self._shapely_geom = shape(self.geometry)
        return self._shapely_geom
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property value."""
        return self.properties.get(key, default)
    
    def get_coordinates(self) -> Optional[Tuple[float, float]]:
        """Get centroid coordinates for point geometries."""
        if self.shapely_geom and self.shapely_geom.geom_type == "Point":
            return (self.shapely_geom.x, self.shapely_geom.y)
        return None
    
    def get_bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Get geometry bounds (minx, miny, maxx, maxy)."""
        if self.shapely_geom:
            return self.shapely_geom.bounds
        return None


@dataclass
class VectorDataset:
    """Container for a loaded vector dataset with metadata."""
    path: Path
    dataset_id: str
    name: str
    
    # Parsed data
    _data: Optional[Dict[str, Any]] = None
    _features: Optional[List[VectorFeature]] = None
    _crs: Optional[str] = None
    _bounds: Optional[Tuple[float, float, float, float]] = None
    
    def __post_init__(self):
        if not self.path.exists():
            raise FileNotFoundError(f"Vector file not found: {self.path}")
    
    def load(self) -> Dict[str, Any]:
        """Load and parse the vector file."""
        if self._data is not None:
            return self._data
        
        with open(self.path, "r") as f:
            self._data = json.load(f)
        
        # Extract features
        self._features = []
        features_data = self._data.get("features", [])
        
        for i, feat in enumerate(features_data):
            geom = feat.get("geometry")
            props = feat.get("properties", {})
            feat_id = feat.get("id", f"feature_{i}")
            
            feature = VectorFeature(
                id=str(feat_id),
                geometry=geom if geom else {},
                properties=props,
            )
            self._features.append(feature)
        
        # Extract CRS from GeoJSON
        self._crs = self._data.get("crs", {}).get("properties", {}).get("name", "EPSG:4326")
        
        # Calculate bounds
        self._calculate_bounds()
        
        return self._data
    
    def _calculate_bounds(self):
        """Calculate combined bounds of all features."""
        if not SHAPELY_AVAILABLE or not self._features:
            self._bounds = None
            return
        
        bounds = None
        for feat in self._features:
            feat_bounds = feat.get_bounds()
            if feat_bounds:
                if bounds is None:
                    bounds = feat_bounds
                else:
                    bounds = (
                        min(bounds[0], feat_bounds[0]),
                        min(bounds[1], feat_bounds[1]),
                        max(bounds[2], feat_bounds[2]),
                        max(bounds[3], feat_bounds[3]),
                    )
        self._bounds = bounds
    
    @property
    def features(self) -> List[VectorFeature]:
        """Get all features (loads if needed)."""
        if self._features is None:
            self.load()
        return self._features or []
    
    @property
    def crs(self) -> Optional[str]:
        if self._crs is None:
            self.load()
        return self._crs
    
    @property
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        if self._bounds is None:
            self.load()
        return self._bounds
    
    @property
    def feature_count(self) -> int:
        return len(self.features)
    
    def get_feature_by_id(self, feature_id: str) -> Optional[VectorFeature]:
        """Get a feature by its ID."""
        for feat in self.features:
            if feat.id == feature_id:
                return feat
        return None
    
    def filter_by_property(self, key: str, value: Any) -> List[VectorFeature]:
        """Filter features by property value."""
        return [f for f in self.features if f.properties.get(key) == value]
    
    def filter_by_bbox(
        self,
        minx: float,
        miny: float,
        maxx: float,
        maxy: float
    ) -> List[VectorFeature]:
        """Filter features within a bounding box."""
        if not SHAPELY_AVAILABLE:
            return []
        
        from shapely.geometry import box
        bbox = box(minx, miny, maxx, maxy)
        
        result = []
        for feat in self.features:
            if feat.shapely_geom and feat.shapely_geom.intersects(bbox):
                result.append(feat)
        return result
    
    def get_features_in_radius(
        self,
        center_x: float,
        center_y: float,
        radius_m: float,
        crs: str = "EPSG:4326"
    ) -> List[VectorFeature]:
        """
        Get features within radius of a point.
        Note: For accurate distance in meters, use projected CRS.
        """
        if not SHAPELY_AVAILABLE:
            return []
        
        from shapely.geometry import Point
        from shapely.ops import transform
        import pyproj
        
        # For now, use simple bbox approximation
        # In production, would use proper projection
        from shapely.geometry import Point
        center = Point(center_x, center_y)
        # Approximate: 1 degree ≈ 111km at equator
        deg_radius = radius_m / 111000.0
        bbox = center.buffer(deg_radius).bounds
        
        return self.filter_by_bbox(*bbox)
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get a summary of vector dataset metadata."""
        self.load()
        return {
            "path": str(self.path),
            "dataset_id": self.dataset_id,
            "name": self.name,
            "feature_count": self.feature_count,
            "crs": self.crs,
            "bounds": self.bounds,
            "feature_types": list(set(
                f.geometry.get("type", "Unknown") for f in self.features
            )) if self.features else [],
            "property_keys": list(set(
                k for f in self.features for k in f.properties.keys()
            )) if self.features else [],
        }


def load_vector_dataset(
    path: Path,
    dataset_id: Optional[str] = None,
    name: Optional[str] = None
) -> VectorDataset:
    """
    Load a vector dataset from file.
    
    Args:
        path: Path to vector file (GeoJSON)
        dataset_id: Optional dataset identifier
        name: Optional display name
        
    Returns:
        VectorDataset instance
    """
    if dataset_id is None:
        dataset_id = path.stem
    if name is None:
        name = dataset_id
    
    return VectorDataset(
        path=path,
        dataset_id=dataset_id,
        name=name
    )


def query_vector_features(
    vector: VectorDataset,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    properties: Optional[Dict[str, Any]] = None,
    geometry_type: Optional[str] = None,
    limit: Optional[int] = None
) -> List[VectorFeature]:
    """
    Query vector features with optional filters.
    
    Args:
        vector: VectorDataset to query
        bbox: Optional (minx, miny, maxx, maxy) filter
        properties: Optional property filters {key: value}
        geometry_type: Optional geometry type filter (Point, LineString, Polygon, etc.)
        limit: Maximum number of features to return
        
    Returns:
        List of matching VectorFeature objects
    """
    results = vector.features
    
    # Filter by bbox
    if bbox:
        minx, miny, maxx, maxy = bbox
        results = vector.filter_by_bbox(minx, miny, maxx, maxy)
    else:
        results = list(results)
    
    # Filter by properties
    if properties:
        for key, value in properties.items():
            results = [f for f in results if f.properties.get(key) == value]
    
    # Filter by geometry type
    if geometry_type and SHAPELY_AVAILABLE:
        results = [f for f in results if f.shapely_geom and f.shapely_geom.geom_type == geometry_type]
    
    # Apply limit
    if limit and limit > 0:
        results = results[:limit]
    
    return results


def load_vector_dataset_from_geojson(path: Path) -> Dict[str, Any]:
    """
    Load and parse a GeoJSON file.
    
    Returns raw GeoJSON dict for simple use cases.
    """
    with open(path, "r") as f:
        return json.load(f)


def validate_geojson(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a GeoJSON structure.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not isinstance(data, dict):
        errors.append("GeoJSON must be a dictionary")
        return False, errors
    
    # Check required fields
    if "type" not in data:
        errors.append("Missing 'type' field")
    elif data["type"] not in ("FeatureCollection", "Feature", "GeometryCollection"):
        errors.append(f"Invalid type: {data['type']}")
    
    if data.get("type") == "FeatureCollection":
        if "features" not in data:
            errors.append("FeatureCollection missing 'features' array")
        elif not isinstance(data["features"], list):
            errors.append("'features' must be a list")
        else:
            for i, feat in enumerate(data["features"]):
                feat_errors = _validate_feature(feat, i)
                errors.extend(feat_errors)
    
    elif data.get("type") == "Feature":
        feat_errors = _validate_feature(data, 0)
        errors.extend(feat_errors)
    
    return len(errors) == 0, errors


def _validate_feature(feat: Dict[str, Any], index: int) -> List[str]:
    """Validate a single GeoJSON feature."""
    errors = []
    prefix = f"Feature {index}: "
    
    if not isinstance(feat, dict):
        errors.append(f"{prefix}Feature must be an object")
        return errors
    
    if feat.get("type") != "Feature":
        errors.append(f"{prefix}type must be 'Feature'")
    
    if "geometry" not in feat:
        errors.append(f"{prefix}missing 'geometry'")
    elif feat["geometry"] is not None:
        geom_errors = _validate_geometry(feat["geometry"], f"{prefix}geometry: ")
        errors.extend(geom_errors)
    
    if "properties" in feat and not isinstance(feat["properties"], dict):
        errors.append(f"{prefix}properties must be an object")
    
    return errors


def _validate_geometry(geom: Dict[str, Any], prefix: str) -> List[str]:
    """Validate a GeoJSON geometry object."""
    errors = []
    
    if not isinstance(geom, dict):
        errors.append(f"{prefix}must be an object")
        return errors
    
    if "type" not in geom:
        errors.append(f"{prefix}missing 'type'")
        return errors
    
    valid_types = [
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon", "GeometryCollection"
    ]
    
    if geom["type"] not in valid_types:
        errors.append(f"{prefix}invalid geometry type: {geom['type']}")
        return errors
    
    if "coordinates" not in geom:
        errors.append(f"{prefix}missing 'coordinates'")
        return errors
    
    # Basic coordinate validation
    coords = geom["coordinates"]
    if geom["type"] == "Point":
        if not isinstance(coords, list) or len(coords) < 2:
            errors.append(f"{prefix}Point coordinates must be [x, y]")
    elif geom["type"] in ("LineString", "MultiPoint"):
        if not isinstance(coords, list):
            errors.append(f"{prefix}coordinates must be a list")
    elif geom["type"] in ("Polygon", "MultiLineString"):
        if not isinstance(coords, list):
            errors.append(f"{prefix}coordinates must be a list of lists")
    elif geom["type"] == "MultiPolygon":
        if not isinstance(coords, list):
            errors.append(f"{prefix}coordinates must be a list of lists of lists")
    elif geom["type"] == "GeometryCollection":
        if "geometries" not in geom or not isinstance(geom["geometries"], list):
            errors.append(f"{prefix}GeometryCollection must have 'geometries' list")
    
    return errors


def get_vector_info(path: Path) -> Dict[str, Any]:
    """
    Get basic vector dataset information without fully loading features.
    
    Useful for cataloging and validation.
    """
    if not path.exists():
        return {"error": "File not found"}
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
        
        if data.get("type") != "FeatureCollection":
            return {"error": "Not a FeatureCollection"}
        
        features = data.get("features", [])
        geom_types = set()
        prop_keys = set()
        
        for feat in features[:100]:  # Sample first 100
            geom = feat.get("geometry", {})
            if geom.get("type"):
                geom_types.add(geom["type"])
            props = feat.get("properties", {})
            prop_keys.update(props.keys())
        
        crs = data.get("crs", {}).get("properties", {}).get("name", "EPSG:4326")
        
        return {
            "path": str(path),
            "feature_count": len(features),
            "geometry_types": list(geom_types),
            "property_keys": list(prop_keys),
            "crs": crs,
        }
    except Exception as e:
        return {"error": str(e)}