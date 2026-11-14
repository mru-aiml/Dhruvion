"""Terrain data service for querying elevation, slope, and roughness data."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from app.core.config import settings
from app.core.exceptions import UnavailableError, InvalidInputError, NotFoundError
from app.core.logging_config import get_logger
from app.data_pipeline.raster_loader import (
    RasterDataset,
    load_raster_dataset,
    query_raster_at,
    get_raster_info,
)
from app.data_pipeline.catalog import get_dataset_catalog

logger = get_logger(__name__)


@dataclass
class TerrainQueryResult:
    """Result of a terrain query."""
    region_id: str
    coordinate: Dict[str, Any]
    values: Dict[str, Optional[float]]
    provenance: List[str]
    availability: str
    warnings: List[str]


class TerrainDataService:
    """
    Service for querying terrain data (elevation, slope, roughness).
    
    Manages raster datasets and provides coordinate-based queries.
    """
    
    def __init__(self):
        self._datasets: Dict[str, Any] = {}  # Cache of loaded raster datasets
        self._catalog = get_dataset_catalog()
        self._region_crs = "urn:ogc:def:crs:IAU2000::104905"
    
    def _get_elevation_dataset(self) -> Any:
        """Get the elevation raster dataset."""
        if "elevation" not in self._datasets:
            path = settings.PROCESSED_DIR / "mola" / "gale" / "elevation.tif"
            if not path.exists():
                raise UnavailableError("Elevation raster not found. Run processing scripts first.")
            self._datasets["elevation"] = load_raster_dataset(path, "mola_elevation", "MOLA Elevation")
        return self._datasets["elevation"]
    
    def _get_slope_dataset(self) -> Any:
        """Get the slope raster dataset."""
        if "slope" not in self._datasets:
            path = settings.PROCESSED_DIR / "mola" / "gale" / "slope.tif"
            if not path.exists():
                raise UnavailableError("Slope raster not found. Run processing scripts first.")
            self._datasets["slope"] = load_raster_dataset(path, "slope", "Slope Analysis")
        return self._datasets["slope"]
    
    def _get_roughness_dataset(self) -> Any:
        """Get the roughness raster dataset."""
        if "roughness" not in self._datasets:
            path = settings.PROCESSED_DIR / "mola" / "gale" / "roughness.tif"
            if not path.exists():
                raise UnavailableError("Roughness raster not found. Run processing scripts first.")
            self._datasets["roughness"] = load_raster_dataset(path, "roughness", "Terrain Roughness")
        return self._datasets["roughness"]
    
    def query_terrain(
        self,
        region_id: str,
        x: float,
        y: float,
        layers: Optional[List[str]] = None
    ) -> TerrainQueryResult:
        """
        Query terrain values at a coordinate.
        
        Args:
            region_id: Region identifier (must be "gale_crater")
            x: Longitude coordinate
            y: Latitude coordinate
            layers: Optional list of layers to query (default: all)
            
        Returns:
            TerrainQueryResult with values and provenance
        """
        if region_id != "gale_crater":
            raise NotFoundError("Unknown region", details={"region_id": region_id})
        
        # Default layers
        if layers is None:
            layers = ["elevation", "slope", "roughness"]
        
        values = {}
        provenance = []
        warnings = []
        
        for layer in layers:
            try:
                if layer == "elevation":
                    dataset = self._get_elevation_dataset()
                    val = query_raster_at(dataset, x, y)
                    if val is not None:
                        values["elevation_m"] = val
                        provenance.append("observed")
                    else:
                        values["elevation_m"] = None
                elif layer == "slope":
                    dataset = self._get_slope_dataset()
                    val = query_raster_at(dataset, x, y)
                    if val is not None:
                        values["slope_deg"] = val
                        provenance.append("derived")
                    else:
                        values["slope_deg"] = None
                elif layer == "roughness":
                    dataset = self._get_roughness_dataset()
                    val = query_raster_at(dataset, x, y)
                    if val is not None:
                        values["roughness"] = val
                        provenance.append("derived")
                    else:
                        values["roughness"] = None
                else:
                    warnings.append(f"Unknown layer: {layer}")
            except UnavailableError as e:
                warnings.append(f"Layer {layer}: {e}")
                values[layer] = None
            except Exception as e:
                logger.warning(f"Error querying {layer}: {e}")
                warnings.append(f"Error querying {layer}: {e}")
                values[layer] = None
        
        # Determine overall availability
        available_values = [v for v in values.values() if v is not None]
        if not available_values:
            availability = "unavailable"
            if not warnings:
                warnings.append("Coordinate outside processed MOLA coverage or NoData.")
        else:
            availability = "available"
        
        # Deduplicate provenance
        provenance = list(dict.fromkeys(provenance))
        
        return TerrainQueryResult(
            region_id=region_id,
            coordinate={"x": x, "y": y, "crs": self._region_crs},
            values=values,
            provenance=provenance,
            availability=availability,
            warnings=warnings,
        )
    
    def get_raster_metadata(self, layer_id: str) -> Dict[str, Any]:
        """Get metadata for a specific raster layer."""
        layer_paths = {
            "mola_elevation": settings.PROCESSED_DIR / "mola" / "gale" / "elevation.tif",
            "slope": settings.PROCESSED_DIR / "mola" / "gale" / "slope.tif",
            "roughness": settings.PROCESSED_DIR / "mola" / "gale" / "roughness.tif",
        }
        
        if layer_id not in layer_paths:
            raise NotFoundError("Unknown layer", details={"layer_id": layer_id})
        
        path = layer_paths[layer_id]
        return get_raster_info(path)
    
    def get_available_layers(self) -> List[Dict[str, Any]]:
        """Get list of available raster layers with metadata."""
        layers = []
        layer_configs = {
            "mola_elevation": {"name": "Elevation / MOLA", "units": "m", "type": "observed"},
            "slope": {"name": "Slope Analysis", "units": "deg", "type": "derived"},
            "roughness": {"name": "Terrain Roughness", "units": "index", "type": "derived"},
        }
        
        for layer_id, config in layer_configs.items():
            path = {
                "mola_elevation": settings.PROCESSED_DIR / "mola" / "gale" / "elevation.tif",
                "slope": settings.PROCESSED_DIR / "mola" / "gale" / "slope.tif",
                "roughness": settings.PROCESSED_DIR / "mola" / "gale" / "roughness.tif",
            }[layer_id]
            
            available = path.exists()
            info = get_raster_info(path) if available else {"error": "File not found"}
            
            layers.append({
                "id": layer_id,
                "name": config["name"],
                "units": config["units"],
                "type": config["type"],
                "available": available,
                "metadata": info,
            })
        
        return layers
    
    def validate_coordinate(self, x: float, y: float) -> Dict[str, Any]:
        """
        Validate that a coordinate is within processed coverage.
        """
        # Use catalog to get coverage bounds
        catalog = self._catalog
        elevation_entry = catalog.get("mola_elevation")
        
        if not elevation_entry or not elevation_entry.coverage:
            return {
                "valid": False,
                "reason": "Coverage information not available",
            }
        
        bounds = elevation_entry.coverage.get("bounds")
        if not bounds:
            return {"valid": False, "reason": "Coverage bounds not available"}
        
        minx, miny, maxx, maxy = bounds
        is_valid = bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]
        
        return {
            "valid": is_valid,
            "coordinate": {"x": x, "y": y},
            "coverage_bounds": bounds,
            "message": "Coordinate within processed coverage" if is_valid else "Coordinate outside processed coverage",
        }
    
    def get_layer_statistics(self, layer_id: str) -> Dict[str, Any]:
        """
        Get statistical summary of a raster layer.
        
        Note: This reads the entire raster - use with caution for large files.
        """
        layer_paths = {
            "mola_elevation": settings.PROCESSED_DIR / "mola" / "gale" / "elevation.tif",
            "slope": settings.PROCESSED_DIR / "mola" / "gale" / "slope.tif",
            "roughness": settings.PROCESSED_DIR / "mola" / "gale" / "roughness.tif",
        }
        
        if layer_id not in layer_paths:
            raise NotFoundError("Unknown layer", details={"layer_id": layer_id})
        
        path = layer_paths[layer_id]
        if not path.exists():
            raise UnavailableError(f"Layer file not found: {layer_id}")
        
        from app.data_pipeline.raster_loader import load_raster_dataset
        dataset = load_raster_dataset(path, layer_id, layer_id)
        
        # Read all data (masked)
        import numpy as np
        data = dataset.read_all(masked=True)
        
        if data.mask.all():
            return {"error": "All data is NoData"}
        
        valid_data = data.compressed()
        
        return {
            "layer_id": layer_id,
            "count": int(valid_data.size),
            "min": float(np.nanmin(valid_data)),
            "max": float(np.nanmax(valid_data)),
            "mean": float(np.mean(valid_data)),
            "std": float(np.std(valid_data)),
            "median": float(np.median(valid_data)),
            "nodata_count": int(np.sum(data.mask)),
            "total_pixels": int(data.size),
        }


# Global service instance
_terrain_service: Optional[TerrainDataService] = None


def get_terrain_data_service() -> TerrainDataService:
    """Get or create the terrain data service instance."""
    global _terrain_service
    if _terrain_service is None:
        _terrain_service = TerrainDataService()
    return _terrain_service