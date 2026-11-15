"""Single layer catalogue used by ``/api/layers`` and the frontend map.

The catalogue is built from the files that actually exist in the handover
package. Local overlays carry metadata-derived bounds so the frontend can place
them on a Mars equirectangular map without hardcoded developer bounds.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Dict, List, Optional

from app.core.exceptions import NotFoundError
from app.data_pipeline.dataset_paths import get_dataset_paths, static_url_for
from app.services.terrain_service import CTX_SOURCE, get_terrain_service

REGION_ID = "gale_crater"
REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"

TILE_LAYERS = [
    {
        "id": "mars_trek_mola_colorshade",
        "name": "Mars Trek MOLA Color-Shaded Relief",
        "layer_type": "tiles",
        "status": "observed",
        "availability": "available",
        "source": {
            "name": "Mars MGS MOLA ClrShade merge global 463m",
            "provider": "NASA Mars Trek",
            "product_id": "Mars_MGS_MOLA_ClrShade_merge_global_463m",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml",
        },
        "crs": REGION_CRS,
        "resolution_m": 463.0,
        "units": "color-shaded relief",
        "tile_url_template": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
        "max_zoom": 8,
        "warnings": ["NASA Mars Trek WMTS basemap; not used for terrain value queries."],
    },
    {
        "id": "mola_roughness_trek",
        "name": "MOLA Global Roughness (Mars Trek)",
        "layer_type": "tiles",
        "status": "observed",
        "availability": "available",
        "source": {
            "name": "MOLA roughness",
            "provider": "NASA Mars Trek",
            "product_id": "mola_roughness",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/WMTSCapabilities.xml",
        },
        "crs": REGION_CRS,
        "resolution_m": 2368.0,
        "units": "roughness index",
        "tile_url_template": "https://trek.nasa.gov/tiles/Mars/EQ/mola_roughness/1.0.0/default/default028mm/{z}/{y}/{x}.png",
        "max_zoom": 1,
        "warnings": ["NASA Mars Trek WMTS layer; validated at zoom 0-1 only."],
    },
    {
        "id": "mars_mola_hrsc_blend",
        "name": "MOLA + HRSC Color Hillshade",
        "layer_type": "tiles",
        "status": "observed",
        "availability": "available",
        "source": {
            "name": "MOLA + HRSC blend",
            "provider": "NASA Mars Trek",
            "product_id": "Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/WMTSCapabilities.xml",
        },
        "crs": REGION_CRS,
        "resolution_m": 200.0,
        "units": "color-shaded relief",
        "tile_url_template": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MOLA_blend200ppx_HRSC_ClrShade_clon0dd_200mpp_lzw/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
        "max_zoom": 8,
        "warnings": ["NASA Mars Trek WMTS layer."],
    },
    {
        "id": "viking_mdim",
        "name": "Viking Global Color Mosaic",
        "layer_type": "tiles",
        "status": "observed",
        "availability": "available",
        "source": {
            "name": "Viking MDIM21",
            "provider": "NASA Mars Trek",
            "product_id": "Mars_Viking_MDIM21_ClrMosaic_global_232m",
            "source_uri": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml",
        },
        "crs": REGION_CRS,
        "resolution_m": 232.0,
        "units": "imagery",
        "tile_url_template": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg",
        "max_zoom": 8,
        "warnings": ["NASA Mars Trek WMTS layer."],
    },
]


def _read_json(path) -> Optional[Dict[str, Any]]:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - corrupt package metadata
        return None


class LayerCatalog:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, Any]] = None

    def _terrain_overlay_meta(self) -> Dict[str, Any]:
        return get_terrain_service().overlay_metadata()

    def _ctx_meta(self) -> Dict[str, Any]:
        paths = get_dataset_paths()
        if paths is None:
            return {}
        return _read_json(paths.ctx_overlay_metadata) or {}

    def _package_layers(self) -> List[Dict[str, Any]]:
        terrain = get_terrain_service()
        metadata = terrain.layer_metadata()
        overlay_meta = self._terrain_overlay_meta()
        bounds = {
            "bounds_latlon": terrain.bounds_latlon(),
            "leaflet_bounds": overlay_meta.get("leaflet_bounds"),
        }
        display = overlay_meta.get("layers", {})
        limitations = terrain.limitations()

        layers: List[Dict[str, Any]] = []
        terrain_specs = [
            ("mola_elevation", "Elevation / MOLA", "observed", "m", "elevation", "Observed MOLA elevation."),
            ("slope", "Slope (MOLA-derived)", "derived", "degree", "slope", "Horn (1981) 3x3 slope at ~463 m baseline."),
            ("roughness", "Terrain Roughness (TRI)", "derived", "m (TRI Riley 1999)", "roughness", "Riley (1999) TRI at ~463 m baseline."),
            ("coverage", "Coverage Mask", "derived", "class", "coverage", "0 no elevation, 1 valid derivatives, 2 elevation only."),
        ]
        if not metadata.get("available"):
            for layer_id, name, status, unit, _key, note in terrain_specs:
                layers.append(
                    {
                        "id": layer_id,
                        "name": name,
                        "layer_type": "overlay",
                        "status": status,
                        "availability": "unavailable",
                        "source": terrain.source(),
                        "crs": REGION_CRS,
                        "resolution_m": None,
                        "units": unit,
                        "bounds": bounds,
                        "overlay_url": None,
                        "warnings": ["NASA terrain package is not available on this server."],
                    }
                )
            return layers

        for layer_id, name, status, unit, key, note in terrain_specs:
            overlay_url = terrain.overlay_url(key)
            layers.append(
                {
                    "id": layer_id,
                    "name": name,
                    "layer_type": "overlay",
                    "status": status,
                    "availability": "available" if overlay_url else "unavailable",
                    "source": terrain.source(),
                    "crs": REGION_CRS,
                    "resolution_m": metadata.get("resolution_m"),
                    "units": unit,
                    "bounds": bounds,
                    "overlay_url": overlay_url,
                    "display": display.get(key, {}),
                    "warnings": [note, *limitations],
                }
            )

        ctx_meta = self._ctx_meta()
        paths = get_dataset_paths()
        ctx_url = static_url_for(paths.ctx_png) if paths else None
        alignment = ctx_meta.get("alignment_with_dem", {})
        layers.append(
            {
                "id": "gale_ctx",
                "name": "Gale CTX Mosaic (local processed clip)",
                "layer_type": "overlay",
                "status": "observed",
                "availability": "available" if ctx_url else "unavailable",
                "source": dict(CTX_SOURCE),
                "crs": REGION_CRS,
                "resolution_m": (alignment.get("image_res") or [None])[0],
                "units": "DN (8-bit, not reflectance)",
                "bounds": {
                    "leaflet_bounds": ctx_meta.get("leaflet_bounds"),
                    "bounds_latlon": _leaflet_to_latlon(ctx_meta.get("leaflet_bounds")),
                },
                "overlay_url": ctx_url,
                "warnings": [
                    "CTX PNG values are 8-bit DN, not calibrated reflectance.",
                    "CTX and DEM are near-equivalent CRS with a different grid; max offset "
                    f"{alignment.get('max_coordinate_offset_m', 'unknown')} m exceeds the "
                    f"{alignment.get('equivalence_tolerance_m', 'unknown')} m tolerance.",
                    "Partial coverage: the CTX clip does not cover the full DEM AOI.",
                ],
            }
        )

        layers.append(
            {
                "id": "hazard_overlay",
                "name": "Derived Hazard Classification",
                "layer_type": "derived",
                "status": "derived",
                "availability": "available",
                "source": terrain.source(),
                "crs": REGION_CRS,
                "resolution_m": metadata.get("resolution_m"),
                "units": "class (low/moderate/high/unknown)",
                "bounds": bounds,
                "overlay_url": None,
                "warnings": [
                    "Hazard classes are derived from slope/roughness at ~463 m baseline; not rover-scale obstacles.",
                    "Use /api/hazards for the current derived summary.",
                ],
            }
        )

        layers.append(
            {
                "id": "rems_environment",
                "name": "REMS Environmental Context (point)",
                "layer_type": "environment",
                "status": "observed",
                "availability": "available",
                "source": {
                    "name": "Curiosity REMS MODRDR (sols 9 and 11)",
                    "provider": "NASA PDS Atmospheres",
                    "product_id": "MSL-M-REMS-5-MODRDR-V1.0",
                    "source_uri": "https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/",
                },
                "crs": REGION_CRS,
                "resolution_m": None,
                "units": "K, Pa, m/s, degree, %, W/m^2",
                "bounds": {"type": "point", "name": "Curiosity rover location"},
                "overlay_url": None,
                "warnings": ["Historical point measurements; not live, forecast, or spatially distributed."],
            }
        )
        layers.append(
            {
                "id": "rad_dosimetry",
                "name": "RAD Dosimetry (point)",
                "layer_type": "environment",
                "status": "observed",
                "availability": "available",
                "source": {
                    "name": "Curiosity RAD RDR (sols 1-3)",
                    "provider": "NASA PDS PPI",
                    "product_id": "MSL-M-RAD-3-RDR-V1.0",
                    "source_uri": "https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/",
                },
                "crs": REGION_CRS,
                "resolution_m": None,
                "units": "microGray / Hour",
                "bounds": {"type": "point", "name": "Curiosity rover location"},
                "overlay_url": None,
                "warnings": [
                    "Detectors B and E are separate and are never combined.",
                    "Historical point measurements; not route-specific radiation predictions.",
                ],
            }
        )
        return layers

    def catalog(self, region_id: str = REGION_ID) -> Dict[str, Any]:
        if region_id != REGION_ID:
            raise NotFoundError("Unknown region", details={"region_id": region_id})
        with self._lock:
            if self._cache is not None:
                return self._cache
            layers = list(TILE_LAYERS)
            layers.extend(self._package_layers())
            layers.extend(
                [
                    {
                        "id": "themis_thermal",
                        "name": "THEMIS Thermal",
                        "layer_type": "raster",
                        "status": "unavailable",
                        "availability": "unavailable",
                        "source": {
                            "name": "THEMIS",
                            "provider": "NASA/ASU",
                            "product_id": None,
                            "source_uri": "https://themis.asu.edu/",
                        },
                        "crs": REGION_CRS,
                        "resolution_m": None,
                        "units": "K",
                        "bounds": None,
                        "overlay_url": None,
                        "warnings": ["Optional layer; no THEMIS product supplied in this package."],
                    },
                    {
                        "id": "science_targets",
                        "name": "Science Targets",
                        "layer_type": "vector",
                        "status": "simulated",
                        "availability": "unavailable",
                        "source": {"name": None, "provider": None, "product_id": None, "source_uri": None},
                        "crs": REGION_CRS,
                        "resolution_m": None,
                        "units": None,
                        "bounds": None,
                        "overlay_url": None,
                        "warnings": ["No verified science target dataset supplied. Demo targets are frontend-only."],
                    },
                ]
            )
            self._cache = {"region_id": region_id, "items": layers}
            return self._cache

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None


def _leaflet_to_latlon(bounds: Any) -> Optional[Dict[str, float]]:
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        return None
    try:
        (south, west), (north, east) = bounds
        return {"south": float(south), "north": float(north), "west": float(west), "east": float(east)}
    except (TypeError, ValueError):
        return None


_catalog: Optional[LayerCatalog] = None
_lock = threading.Lock()


def get_layer_catalog() -> LayerCatalog:
    global _catalog
    with _lock:
        if _catalog is None:
            _catalog = LayerCatalog()
        return _catalog
