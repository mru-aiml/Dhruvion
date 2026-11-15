"""Imagery service for managing and serving Mars surface imagery tiles and overlays."""

import logging
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from app.core.config import settings
from app.core.exceptions import UnavailableError, NotFoundError
from app.core.logging_config import get_logger
from app.data_pipeline.dataset_paths import get_dataset_paths, static_url_for

logger = get_logger(__name__)


class ImageryType(str, Enum):
    """Types of imagery layers."""
    BASEMAP = "basemap"
    OVERLAY = "overlay"
    DERIVED = "derived"


@dataclass
class ImageryLayer:
    """Imagery layer metadata."""
    id: str
    name: str
    layer_type: str  # "tiles", "overlay"
    imagery_type: ImageryType
    status: str  # "observed", "derived", "simulated", "unavailable"
    availability: str  # "available", "unavailable", "partial"
    source: Dict[str, Any]
    crs: str
    resolution_m: Optional[float] = None
    units: Optional[str] = None
    bounds: Optional[List[float]] = None
    tile_url_template: Optional[str] = None
    overlay_url: Optional[str] = None
    max_zoom: Optional[int] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class TileRequest:
    """Tile request parameters."""
    layer_id: str
    z: int
    x: int
    y: int


class ImageryService:
    """
    Service for managing and serving Mars imagery layers.
    
    Handles:
    - Layer catalog management
    - Tile proxying from NASA Mars Trek
    - Local overlay serving
    - Layer availability tracking
    """
    
    def __init__(self):
        self._layer_catalog: Dict[str, ImageryLayer] = {}
        self._initialize_layers()
    
    def _initialize_layers(self):
        """Initialize the layer catalog with known layers."""
        REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"
        
        # NASA Mars Trek WMTS layers
        self._layer_catalog["mars_trek_mola_colorshade"] = ImageryLayer(
            id="mars_trek_mola_colorshade",
            name="Mars Trek MOLA Color-Shaded Relief",
            layer_type="tiles",
            imagery_type=ImageryType.BASEMAP,
            status="observed",
            availability="available",
            source={
                "name": "Mars MGS MOLA ClrShade merge global 463m",
                "provider": "NASA Mars Trek",
                "product_id": "Mars_MGS_MOLA_ClrShade_merge_global_463m",
                "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml",
            },
            crs=REGION_CRS,
            resolution_m=463.0,
            units="color-shaded relief",
            tile_url_template="https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
            max_zoom=8,
            warnings=["Basemap tile layer from NASA Mars Trek. Not a verified elevation raster for terrain queries."],
        )
        
        self._layer_catalog["mola_roughness"] = ImageryLayer(
            id="mola_roughness",
            name="MOLA Global Roughness",
            layer_type="tiles",
            imagery_type=ImageryType.BASEMAP,
            status="observed",
            availability="available",
            source={
                "name": "MOLA roughness",
                "provider": "NASA Mars Trek",
                "product_id": "mola_roughness",
                "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/WMTSCapabilities.xml",
            },
            crs=REGION_CRS,
            resolution_m=2368.0,
            units="roughness index",
            tile_url_template="https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/default/default028mm/{z}/{y}/{x}.png",
            max_zoom=1,
            warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval at zoom 0-1 only."],
        )
        
        self._layer_catalog["mars_mola_hrsc_blend"] = ImageryLayer(
            id="mars_mola_hrsc_blend",
            name="MOLA + HRSC Color Hillshade",
            layer_type="tiles",
            imagery_type=ImageryType.BASEMAP,
            status="observed",
            availability="available",
            source={
                "name": "MOLA + HRSC blend",
                "provider": "NASA Mars Trek",
                "product_id": "Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw",
                "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/WMTSCapabilities.xml",
            },
            crs=REGION_CRS,
            resolution_m=200.0,
            units="color-shaded relief",
            tile_url_template="https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
            max_zoom=8,
            warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval around Gale Crater."],
        )
        
        self._layer_catalog["gale_ctx"] = ImageryLayer(
            id="gale_ctx",
            name="Gale Crater CTX Mosaic",
            layer_type="tiles",
            imagery_type=ImageryType.BASEMAP,
            status="observed",
            availability="available",
            source={
                "name": "Gale CTX Block Adjacency",
                "provider": "NASA Mars Trek",
                "product_id": "Gale_CTX_BlockAdj_dd",
                "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/WMTSCapabilities.xml",
            },
            crs=REGION_CRS,
            resolution_m=6.0,
            units="imagery",
            tile_url_template="https://trek.nasa.gov/tiles/Mars/EQ/Gale_CTX_BlockAdj_dd/1.0.0/default/default028mm/{z}/{y}/{x}.png",
            max_zoom=8,
            warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval around Gale Crater at zoom 5."],
        )
        
        self._layer_catalog["viking_mdim"] = ImageryLayer(
            id="viking_mdim",
            name="Viking Global Color Mosaic",
            layer_type="tiles",
            imagery_type=ImageryType.BASEMAP,
            status="observed",
            availability="available",
            source={
                "name": "Viking MDIM21",
                "provider": "NASA Mars Trek",
                "product_id": "Mars_Viking_MDIM21_ClrMosaic_global_232m",
                "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml",
            },
            crs=REGION_CRS,
            resolution_m=232.0,
            units="imagery",
            tile_url_template="https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
            max_zoom=8,
            warnings=["NASA Mars Trek WMTS layer. Validated tile retrieval around Gale Crater."],
        )
        
        # Local processed overlays
        self._layer_catalog["mola_elevation"] = ImageryLayer(
            id="mola_elevation",
            name="Elevation / MOLA",
            layer_type="overlay",
            imagery_type=ImageryType.DERIVED,
            status="observed",
            availability="available",
            source={
                "name": "MGS MOLA MEGDR topography tile megt00n090hb",
                "provider": "NASA PDS",
                "product_id": "MEGT00N090HB.IMG",
                "source_uri": "https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg128/megt00n090hb.img",
            },
            crs=REGION_CRS,
            resolution_m=463.0,
            units="m",
            overlay_url="/static/mola/gale/elevation.png",
            warnings=["Processed from megt00n090hb.img; coverage lon 137-138 E, lat -4.0 to -6.5; NoData=0."],
        )
        
        self._layer_catalog["slope"] = ImageryLayer(
            id="slope",
            name="Slope Analysis",
            layer_type="overlay",
            imagery_type=ImageryType.DERIVED,
            status="derived",
            availability="available",
            source={
                "name": "Derived from MOLA elevation",
                "provider": "DHRUVION processing",
                "product_id": None,
                "source_uri": None,
            },
            crs=REGION_CRS,
            resolution_m=463.0,
            units="deg",
            overlay_url="/static/mola/gale/slope.png",
            warnings=["Derived from megt00n090hb.img using arctan gradient; coverage lon 137-138 E, lat -4.0 to -6.5."],
        )
        
        self._layer_catalog["roughness"] = ImageryLayer(
            id="roughness",
            name="Terrain Roughness",
            layer_type="overlay",
            imagery_type=ImageryType.DERIVED,
            status="derived",
            availability="available",
            source={
                "name": "Derived from MOLA elevation",
                "provider": "DHRUVION processing",
                "product_id": None,
                "source_uri": None,
            },
            crs=REGION_CRS,
            resolution_m=463.0,
            units="index",
            overlay_url="/static/mola/gale/roughness.png",
            warnings=["Derived from megt00n090hb.img using 3x3 local std; coverage lon 137-138 E, lat -4.0 to -6.5."],
        )
        
        # Unavailable layers
        self._layer_catalog["themis_thermal"] = ImageryLayer(
            id="themis_thermal",
            name="THEMIS Thermal",
            layer_type="overlay",
            imagery_type=ImageryType.DERIVED,
            status="observed",
            availability="unavailable",
            source={"name": "THEMIS", "provider": "NASA/ASU", "product_id": None, "source_uri": "https://themis.asu.edu/"},
            crs=REGION_CRS,
            units="K",
            warnings=["Optional layer; no THEMIS product loaded."],
        )
        
        self._layer_catalog["science_targets"] = ImageryLayer(
            id="science_targets",
            name="Science Targets",
            layer_type="overlay",
            imagery_type=ImageryType.DERIVED,
            status="simulated",
            availability="unavailable",
            source={"name": None, "provider": None, "product_id": None, "source_uri": None},
            crs=REGION_CRS,
            warnings=["No verified science target dataset loaded. Simulated targets are frontend-only and labelled."],
        )
        
        self._layer_catalog["hazard_overlay"] = ImageryLayer(
            id="hazard_overlay",
            name="Hazard Overlay",
            layer_type="overlay",
            imagery_type=ImageryType.DERIVED,
            status="derived",
            availability="unavailable",
            source={"name": None, "provider": None, "product_id": None, "source_uri": None},
            crs=REGION_CRS,
            warnings=["No hazard dataset loaded."],
        )
    
    def get_layer(self, layer_id: str) -> ImageryLayer:
        """Get a layer by ID."""
        if layer_id not in self._layer_catalog:
            raise NotFoundError("Layer not found", details={"layer_id": layer_id})
        return self._layer_catalog[layer_id]
    
    def get_all_layers(self) -> List[ImageryLayer]:
        """Get all layers."""
        return list(self._layer_catalog.values())
    
    def get_layers_by_type(self, imagery_type: ImageryType) -> List[ImageryLayer]:
        """Get layers filtered by imagery type."""
        return [l for l in self._layer_catalog.values() if l.imagery_type == imagery_type]
    
    def get_layers_by_availability(self, availability: str) -> List[ImageryLayer]:
        """Get layers filtered by availability."""
        return [l for l in self._layer_catalog.values() if l.availability == availability]
    
    def get_tile_url(self, layer_id: str, z: int, x: int, y: int) -> str:
        """
        Generate tile URL for a layer.
        
        For WMTS layers, returns NASA Mars Trek URL.
        For local overlays, returns static file URL.
        """
        layer = self.get_layer(layer_id)
        
        if layer.tile_url_template:
            return layer.tile_url_template.format(z=z, x=x, y=y)
        
        if layer.overlay_url:
            # For static overlays, we could serve tiles from the image
            # For now, return the static image URL (frontend handles tiling)
            return layer.overlay_url
        
        raise UnavailableError(f"Layer {layer_id} does not support tile serving")
    
    def fetch_tile(self, layer_id: str, z: int, x: int, y: int) -> Tuple[bytes, str]:
        """
        Fetch a tile from the source.
        
        Returns:
            Tuple of (tile_data, content_type)
        """
        layer = self.get_layer(layer_id)
        
        if not layer.tile_url_template:
            raise UnavailableError(f"Layer {layer_id} does not support tile fetching")
        
        if z > (layer.max_zoom or 18):
            raise ValueError(f"Zoom level {z} exceeds max zoom {layer.max_zoom}")
        
        url = self.get_tile_url(layer_id, z, x, y)
        
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg")
            return data, content_type
        except Exception as e:
            logger.error(f"Tile fetch failed for {layer_id}/{z}/{x}/{y}: {e}")
            raise UnavailableError(f"Tile fetch failed: {e}")
    
    def get_layer_catalog(self, region_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the layer catalog formatted for API response."""
        if region_id and region_id != "gale_crater":
            raise NotFoundError("Unknown region", details={"region_id": region_id})

        layers = []
        for layer in self._layer_catalog.values():
            layer_dict = {
                "id": layer.id,
                "name": layer.name,
                "layer_type": layer.layer_type,
                "imagery_type": (
                    layer.imagery_type.value
                    if isinstance(layer.imagery_type, ImageryType)
                    else str(layer.imagery_type)
                ),
                "status": layer.status,
                "availability": layer.availability,
                "source": layer.source,
                "crs": layer.crs,
                "resolution_m": layer.resolution_m,
                "units": layer.units,
                "warnings": layer.warnings,
            }
            
            if layer.bounds:
                layer_dict["bounds"] = layer.bounds
            if layer.tile_url_template:
                layer_dict["tile_url_template"] = layer.tile_url_template
            if layer.overlay_url:
                layer_dict["overlay_url"] = layer.overlay_url
            if layer.max_zoom:
                layer_dict["max_zoom"] = layer.max_zoom
            
            layers.append(layer_dict)
        
        return {"region_id": region_id or "gale_crater", "items": layers}
    
    def validate_layer_availability(self, layer_id: str) -> bool:
        """Check if a layer is available for use."""
        layer = self._layer_catalog.get(layer_id)
        if not layer:
            return False
        return layer.availability in ("available", "partial")

    # --------------------------------------------------------------- CTX
    def get_ctx_imagery(self) -> Dict[str, Any]:
        """Return the processed CTX overlay with package-derived georeferencing."""
        paths = get_dataset_paths()
        if paths is None:
            return {
                "available": False,
                "reason": "DHRUVION_DATA package not found.",
                "provenance": "unavailable",
            }
        metadata: Dict[str, Any] = {}
        if paths.ctx_overlay_metadata.exists():
            try:
                metadata = json.loads(paths.ctx_overlay_metadata.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - corrupt package metadata
                logger.warning("Could not read CTX overlay metadata: %s", exc)
        alignment = metadata.get("alignment_with_dem", {})
        overlay_url = static_url_for(paths.ctx_png)
        return {
            "available": bool(overlay_url) and paths.ctx_tif.exists(),
            "id": "gale_ctx_local",
            "name": "Gale CTX Mosaic (processed clip)",
            "layer_type": "overlay",
            "provenance": "observed",
            "units": "DN (8-bit, not reflectance)",
            "projection": metadata.get("image_projection", "Mars_2015_Ocentric_Equirectangular_clon_0"),
            "latitude_type": metadata.get("latitude_type", "planetocentric"),
            "longitude_direction": metadata.get("longitude_direction", "east-positive"),
            "bounds": {
                "leaflet_bounds": metadata.get("leaflet_bounds"),
                "bounds_latlon": _leaflet_to_latlon(metadata.get("leaflet_bounds")),
            },
            "resolution_m": (alignment.get("image_res") or [None])[0],
            "overlay_url": overlay_url,
            "geotiff": _relative(paths.ctx_tif),
            "alignment_with_dem": alignment,
            "partial_coverage": True,
            "display": {
                "stretch": metadata.get("stretch"),
                "nodata_handling": metadata.get("nodata_handling"),
            },
            "source": {
                "name": "Global CTX Mosaic of Mars (Caltech Murray Lab), Gale AOI",
                "provider": "NASA/JPL/MSSS imagery, Caltech Murray Lab mosaic",
                "product_id": "MurrayLab_GlobalCTXMosaic_V01_E136_N-08",
                "source_uri": "https://murray-lab.caltech.edu/CTX/V01/tiles/",
            },
            "warnings": [
                "Pixel values are 8-bit DN, not calibrated reflectance.",
                "Partial coverage: lat -6.9187..-4.0, lon 136.1999..139.4.",
                "CTX/DEM are near-equivalent CRS with a different grid; do not assume pixel alignment.",
            ],
            "limitations": [
                "Do not stretch or repeat the CTX image into areas it does not cover.",
                "Use the Mars equirectangular projection, never Web Mercator.",
            ],
        }


def _relative(path: Path) -> Optional[str]:
    paths = get_dataset_paths()
    if paths is None:
        return None
    try:
        return path.resolve().relative_to(paths.root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def _leaflet_to_latlon(bounds: Any) -> Optional[Dict[str, float]]:
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        return None
    try:
        (south, west), (north, east) = bounds
        return {"south": float(south), "north": float(north), "west": float(west), "east": float(east)}
    except (TypeError, ValueError):
        return None


# Global service instance
_imagery_service: Optional["ImageryService"] = None


def get_imagery_service() -> ImageryService:
    """Get or create the imagery service instance."""
    global _imagery_service
    if _imagery_service is None:
        _imagery_service = ImageryService()
    return _imagery_service