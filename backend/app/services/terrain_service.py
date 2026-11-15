"""Terrain service for the supplied NASA MOLA package.

Key rules
---------
- The DEM is a projected *metre* grid (Mars equirectangular, central meridian 0).
  API coordinates are planetocentric lon/lat, so they must be transformed before
  sampling. ``pyproj`` is not required; rasterio's PROJ bridge is used with a
  deterministic spherical fallback.
- Coverage classes: ``0`` no elevation, ``1`` elevation + derivatives valid,
  ``2`` elevation valid but slope/roughness undefined. Class 2 must never be used
  for slope/roughness and unknown cells are never zero-cost.
- NoData is NaN in the supplied rasters. NaN is treated as unknown, never as 0.
- Derivatives are ~463 m baseline products, not rover-scale trafficability.
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform as warp_transform
except Exception:  # pragma: no cover - rasterio is a hard runtime dependency
    rasterio = None
    CRS = None
    warp_transform = None

from app.core.exceptions import NotFoundError, UnavailableError
from app.core.logging_config import get_logger
from app.data_pipeline.dataset_paths import get_dataset_paths, static_url_for

logger = get_logger(__name__)

REGION_ID = "gale_crater"
REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"
MARS_RADIUS_M = 3_396_190.0
GEOGRAPHIC_CRS_PROJ4 = f"+proj=longlat +R={MARS_RADIUS_M} +no_defs"

COVERAGE_LABELS = {
    0: "no elevation data",
    1: "elevation, slope and roughness valid",
    2: "elevation valid, slope/roughness undefined",
}

TERRAIN_SOURCE = {
    "name": "MGS MOLA DEM global mosaic, 463 m/px (Gale AOI clip)",
    "provider": "NASA / USGS Astrogeology",
    "product_id": "Mars_MGS_MOLA_DEM_mosaic_global_463m",
    "source_uri": "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
}

CTX_SOURCE = {
    "name": "Global CTX Mosaic of Mars (Caltech Murray Lab), Gale AOI",
    "provider": "NASA/JPL/MSSS imagery, Caltech Murray Lab mosaic",
    "product_id": "MurrayLab_GlobalCTXMosaic_V01_E136_N-08",
    "source_uri": "https://murray-lab.caltech.edu/CTX/V01/tiles/",
}

REMS_SOURCE = {
    "name": "Curiosity REMS MODRDR environmental tables (sols 9 and 11)",
    "provider": "NASA PDS Atmospheres (MSL-M-REMS-5-MODRDR-V1.0)",
    "product_id": "MSL-M-REMS-5-MODRDR-V1.0",
    "source_uri": "https://pds-atmospheres.nmsu.edu/PDS/data/mslrem_1001/",
}

RAD_SOURCE = {
    "name": "Curiosity RAD calibrated RDR (sols 1-3)",
    "provider": "NASA PDS PPI (MSL-M-RAD-3-RDR-V1.0)",
    "product_id": "MSL-M-RAD-3-RDR-V1.0",
    "source_uri": "https://pds-ppi.igpp.ucla.edu/data/MSL-M-RAD-3-RDR-V1.0/",
}

DERIVATIVE_LIMITATION = (
    "Slope and roughness are derived at the ~463 m MOLA pixel baseline. "
    "They are regional indicators, not rover-scale trafficability or hazard verification."
)
COVERAGE_LIMITATION = (
    "Coverage classes: 0 = no elevation, 1 = elevation/slope/roughness valid, "
    "2 = elevation valid but slope/roughness undefined. Unknown is never treated as zero risk."
)


@dataclass
class RasterLayer:
    key: str
    path: Any
    data: np.ndarray
    transform: Any
    crs: Any
    nodata: Optional[float]
    unit: str
    provenance: str

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def resolution_m(self) -> float:
        return float(abs(self.transform.a))


class TerrainService:
    """Coordinate-aware access to the MOLA elevation / slope / roughness rasters."""

    def __init__(self) -> None:
        self._paths = get_dataset_paths()
        self._layers: Dict[str, RasterLayer] = {}
        self._lock = threading.RLock()
        self._overlay_metadata: Optional[Dict[str, Any]] = None
        self._provenance: Optional[Dict[str, Any]] = None
        self._geographic_crs = CRS.from_proj4(GEOGRAPHIC_CRS_PROJ4) if CRS else None

    # ------------------------------------------------------------------ loading
    def available(self) -> bool:
        if self._paths is None:
            return False
        return all(
            path.exists()
            for path in (
                self._paths.elevation_tif,
                self._paths.slope_tif,
                self._paths.roughness_tif,
                self._paths.coverage_tif,
            )
        )

    def _file_for(self, key: str):
        if self._paths is None:
            raise UnavailableError(
                "NASA DHRUVION_DATA package not found. Set DHRUVION_DATA_DIR to the package root."
            )
        mapping = {
            "elevation": self._paths.elevation_tif,
            "slope": self._paths.slope_tif,
            "roughness": self._paths.roughness_tif,
            "coverage": self._paths.coverage_tif,
        }
        if key not in mapping:
            raise NotFoundError("Unknown terrain layer", details={"layer": key})
        return mapping[key]

    def _load(self, key: str) -> RasterLayer:
        if rasterio is None:
            raise UnavailableError("rasterio is not installed on the server")
        with self._lock:
            if key in self._layers:
                return self._layers[key]
            path = self._file_for(key)
            if not path.exists():
                raise UnavailableError(
                    "Terrain file unavailable", details={"layer": key, "file": path.name}
                )
            with rasterio.open(path) as src:
                data = src.read(1)
                layer = RasterLayer(
                    key=key,
                    path=path,
                    data=data,
                    transform=src.transform,
                    crs=src.crs,
                    nodata=src.nodata,
                    unit={
                        "elevation": "m",
                        "slope": "degree",
                        "roughness": "m (TRI, Riley 1999)",
                        "coverage": "class",
                    }[key],
                    provenance="observed" if key == "elevation" else "derived",
                )
            self._layers[key] = layer
            return layer

    def _require(self, key: str) -> RasterLayer:
        try:
            return self._load(key)
        except UnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise UnavailableError(f"Unable to read terrain layer: {exc}") from exc

    # --------------------------------------------------------------- metadata
    def overlay_metadata(self) -> Dict[str, Any]:
        if self._overlay_metadata is None:
            self._overlay_metadata = {}
            if self._paths and self._paths.terrain_overlay_metadata.exists():
                try:
                    self._overlay_metadata = json.loads(
                        self._paths.terrain_overlay_metadata.read_text(encoding="utf-8")
                    )
                except Exception as exc:  # pragma: no cover - corrupt package
                    logger.warning("Could not read terrain overlay metadata: %s", exc)
        return self._overlay_metadata

    def provenance(self) -> Dict[str, Any]:
        if self._provenance is None:
            self._provenance = {}
            if self._paths and self._paths.terrain_provenance.exists():
                try:
                    self._provenance = json.loads(
                        self._paths.terrain_provenance.read_text(encoding="utf-8")
                    )
                except Exception as exc:  # pragma: no cover
                    logger.warning("Could not read terrain provenance: %s", exc)
        return self._provenance

    def bounds_latlon(self) -> Optional[Dict[str, float]]:
        meta = self.overlay_metadata()
        bounds = meta.get("bounds_latlon")
        if isinstance(bounds, dict) and {"south", "north", "west", "east"} <= set(bounds):
            return {k: float(bounds[k]) for k in ("south", "north", "west", "east")}
        try:
            elevation = self._require("elevation")
        except UnavailableError:
            return None
        west, south = self._from_raster_crs(elevation, elevation.transform.c, elevation.transform.f)
        east, north = self._from_raster_crs(
            elevation,
            elevation.transform.c + elevation.transform.a * elevation.width,
            elevation.transform.f + elevation.transform.e * elevation.height,
        )
        return {
            "south": min(south, north),
            "north": max(south, north),
            "west": min(west, east),
            "east": max(west, east),
        }

    def resolution_m(self) -> Optional[float]:
        try:
            return self._require("elevation").resolution_m
        except UnavailableError:
            return None

    def source(self) -> Dict[str, Any]:
        return dict(TERRAIN_SOURCE)

    def limitations(self) -> List[str]:
        return [DERIVATIVE_LIMITATION, COVERAGE_LIMITATION]

    # ----------------------------------------------------------- coordinates
    def _to_raster_crs(self, layer: RasterLayer, lon: float, lat: float) -> Tuple[float, float]:
        if warp_transform is not None and self._geographic_crs is not None and layer.crs is not None:
            try:
                xs, ys = warp_transform(self._geographic_crs, layer.crs, [lon], [lat])
                return float(xs[0]), float(ys[0])
            except Exception as exc:  # pragma: no cover - PROJ data issues
                logger.debug("PROJ transform failed, using spherical fallback: %s", exc)
        # Mars equirectangular with central meridian 0: x = R*lon, y = R*lat.
        return MARS_RADIUS_M * math.radians(lon), MARS_RADIUS_M * math.radians(lat)

    def _from_raster_crs(self, layer: RasterLayer, x: float, y: float) -> Tuple[float, float]:
        if warp_transform is not None and self._geographic_crs is not None and layer.crs is not None:
            try:
                lons, lats = warp_transform(layer.crs, self._geographic_crs, [x], [y])
                return float(lons[0]), float(lats[0])
            except Exception as exc:  # pragma: no cover
                logger.debug("PROJ inverse transform failed: %s", exc)
        return math.degrees(x / MARS_RADIUS_M), math.degrees(y / MARS_RADIUS_M)

    @staticmethod
    def _pixel_index(layer: RasterLayer, x: float, y: float) -> Optional[Tuple[int, int]]:
        try:
            col, row = (~layer.transform) * (x, y)
        except Exception:  # pragma: no cover
            return None
        r, c = int(math.floor(row)), int(math.floor(col))
        if 0 <= r < layer.height and 0 <= c < layer.width:
            return r, c
        return None

    @staticmethod
    def _value(layer: RasterLayer, row: int, col: int) -> Optional[float]:
        raw = layer.data[row, col]
        if np.ma.isMaskedArray(raw) and np.ma.is_masked(raw):
            return None
        value = float(raw)
        if not math.isfinite(value):
            return None
        if layer.nodata is not None:
            nodata = float(layer.nodata)
            if math.isnan(nodata):
                if math.isnan(value):
                    return None
            elif value == nodata:
                return None
        return value

    def coverage_class(self, row: int, col: int) -> int:
        try:
            coverage = self._load("coverage")
        except UnavailableError:
            return 0
        raw = coverage.data[row, col]
        try:
            return int(raw)
        except Exception:  # pragma: no cover
            return 0

    def _point_index(self, lon: float, lat: float) -> Optional[Tuple[int, int, int]]:
        """Return ``(row, col, coverage_class)`` or ``None`` outside the grid."""
        try:
            elevation = self._require("elevation")
        except UnavailableError:
            return None
        x, y = self._to_raster_crs(elevation, lon, lat)
        rc = self._pixel_index(elevation, x, y)
        if rc is None:
            return None
        row, col = rc
        return row, col, self.coverage_class(row, col)

    # ---------------------------------------------------------------- queries
    def _coverage_block(self, coverage_class: int) -> Dict[str, Any]:
        bounds = self.bounds_latlon()
        return {
            "class": coverage_class,
            "label": COVERAGE_LABELS.get(coverage_class, "unknown"),
            "bounds_latlon": bounds,
            "resolution_m": self.resolution_m(),
            "classes": COVERAGE_LABELS,
        }

    def point(self, lon: float, lat: float, region_id: str = REGION_ID) -> Dict[str, Any]:
        self._assert_region(region_id)

        if not self.available():
            return self._unavailable_point(lon, lat, "NASA terrain package is not available on this server.")

        located = self._point_index(lon, lat)
        if located is None:
            return self._unavailable_point(lon, lat, "Coordinate outside MOLA coverage.", coverage_class=0)

        row, col, coverage_class = located
        values: Dict[str, Optional[float]] = {"elevation_m": None, "slope_deg": None, "roughness": None}
        provenance: List[str] = []
        warnings: List[str] = []

        elevation = self._value(self._require("elevation"), row, col) if coverage_class in (1, 2) else None
        if elevation is not None:
            values["elevation_m"] = round(elevation, 3)
            provenance.append("observed")

        if coverage_class == 1:
            slope = self._value(self._require("slope"), row, col)
            roughness = self._value(self._require("roughness"), row, col)
            if slope is not None:
                values["slope_deg"] = round(slope, 3)
                provenance.append("derived")
            if roughness is not None:
                values["roughness"] = round(roughness, 3)
                if "derived" not in provenance:
                    provenance.append("derived")
        elif coverage_class == 2:
            warnings.append(
                "Coverage class 2: elevation is valid, but slope and roughness are undefined at this "
                "border cell and are intentionally not reported."
            )
        elif coverage_class == 0:
            warnings.append("Coverage class 0: no elevation data at this cell.")

        if elevation is None:
            availability = "unavailable"
            warnings.append("No elevation value is available at this coordinate.")
        elif values["slope_deg"] is None or values["roughness"] is None:
            availability = "partial"
        else:
            availability = "available"

        return {
            "region_id": REGION_ID,
            "coordinate": {"x": lon, "y": lat, "crs": REGION_CRS},
            "values": values,
            "units": {
                "elevation_m": "m",
                "slope_deg": "degree",
                "roughness": "m (TRI, Riley 1999)",
            },
            "coverage": self._coverage_block(coverage_class),
            "provenance": list(dict.fromkeys(provenance)),
            "availability": availability,
            "source": self.source(),
            "warnings": warnings,
            "limitations": self.limitations(),
        }

    def _unavailable_point(
        self, lon: float, lat: float, warning: str, coverage_class: int = 0
    ) -> Dict[str, Any]:
        return {
            "region_id": REGION_ID,
            "coordinate": {"x": lon, "y": lat, "crs": REGION_CRS},
            "values": {"elevation_m": None, "slope_deg": None, "roughness": None},
            "units": {
                "elevation_m": "m",
                "slope_deg": "degree",
                "roughness": "m (TRI, Riley 1999)",
            },
            "coverage": self._coverage_block(coverage_class),
            "provenance": [],
            "availability": "unavailable",
            "source": self.source(),
            "warnings": [warning],
            "limitations": self.limitations(),
        }

    def layer_point(self, layer_key: str, lon: float, lat: float) -> Dict[str, Any]:
        """Single-layer query used by ``/api/terrain/<layer>`` endpoints."""
        if layer_key not in ("elevation", "slope", "roughness", "coverage"):
            raise NotFoundError("Unknown terrain layer", details={"layer": layer_key})

        point = self.point(lon, lat)
        coverage_class = int(point["coverage"]["class"])

        if layer_key == "coverage":
            return {
                "layer": "coverage",
                "region_id": REGION_ID,
                "coordinate": point["coordinate"],
                "value": coverage_class,
                "unit": "class",
                "label": COVERAGE_LABELS.get(coverage_class, "unknown"),
                "availability": "available" if self.available() else "unavailable",
                "coverage": point["coverage"],
                "provenance": "derived",
                "source": self.source(),
                "warnings": point["warnings"],
                "limitations": self.limitations(),
            }

        value_map = {
            "elevation": ("elevation_m", "m", "observed", point["values"]["elevation_m"]),
            "slope": ("slope_deg", "degree", "derived", point["values"]["slope_deg"]),
            "roughness": ("roughness", "m (TRI, Riley 1999)", "derived", point["values"]["roughness"]),
        }
        field, unit, provenance, value = value_map[layer_key]

        if value is None:
            availability = "unavailable"
        elif coverage_class == 2 and layer_key in ("slope", "roughness"):
            availability = "unavailable"
        else:
            availability = "available"

        warnings = list(point["warnings"])
        if availability == "unavailable" and layer_key in ("slope", "roughness") and coverage_class == 2:
            warnings.append(
                f"{layer_key} is undefined for coverage class 2; it is not replaced with a zero or inferred value."
            )

        return {
            "layer": layer_key,
            "region_id": REGION_ID,
            "coordinate": point["coordinate"],
            "value": value,
            "field": field,
            "unit": unit,
            "availability": availability,
            "coverage": point["coverage"],
            "provenance": provenance,
            "source": self.source(),
            "warnings": warnings,
            "limitations": self.limitations(),
        }

    def coverage_at(self, lon: float, lat: float) -> Dict[str, Any]:
        return self.layer_point("coverage", lon, lat)

    def coverage_summary(self) -> Dict[str, Any]:
        if not self.available():
            raise UnavailableError("NASA terrain package is not available on this server.")
        coverage = self._require("coverage")
        counts = {str(k): int(np.count_nonzero(coverage.data == k)) for k in (0, 1, 2)}
        total = int(coverage.data.size)
        counts["other"] = int(total - sum(counts.values()))
        percentages = {
            key: round(100.0 * value / total, 3) if total else None for key, value in counts.items()
        }
        return {
            "region_id": REGION_ID,
            "bounds_latlon": self.bounds_latlon(),
            "resolution_m": self.resolution_m(),
            "total_cells": total,
            "counts": counts,
            "percentages": percentages,
            "classes": COVERAGE_LABELS,
            "availability": "available",
            "provenance": "derived",
            "source": self.source(),
            "warnings": [],
            "limitations": self.limitations(),
        }

    def profile(
        self, start_lon: float, start_lat: float, end_lon: float, end_lat: float, samples: int = 25
    ) -> Dict[str, Any]:
        samples = max(2, min(int(samples), 200))
        points: List[Dict[str, Any]] = []
        distance = 0.0
        previous: Optional[Tuple[float, float]] = None
        for index in range(samples):
            fraction = index / (samples - 1)
            lon = start_lon + (end_lon - start_lon) * fraction
            lat = start_lat + (end_lat - start_lat) * fraction
            if previous is not None:
                distance += self._ground_distance(previous[0], previous[1], lon, lat)
            previous = (lon, lat)
            point = self.point(lon, lat)
            point["distance_m"] = round(distance, 1)
            points.append(point)

        elevations = [p["values"]["elevation_m"] for p in points if p["values"]["elevation_m"] is not None]
        slopes = [p["values"]["slope_deg"] for p in points if p["values"]["slope_deg"] is not None]
        classes = [p["coverage"]["class"] for p in points]
        return {
            "region_id": REGION_ID,
            "start": {"x": start_lon, "y": start_lat, "crs": REGION_CRS},
            "end": {"x": end_lon, "y": end_lat, "crs": REGION_CRS},
            "samples": samples,
            "distance_m": round(distance, 1),
            "points": points,
            "summary": {
                "valid_elevation_samples": len(elevations),
                "missing_elevation_samples": samples - len(elevations),
                "min_elevation_m": round(min(elevations), 1) if elevations else None,
                "max_elevation_m": round(max(elevations), 1) if elevations else None,
                "mean_elevation_m": round(sum(elevations) / len(elevations), 1) if elevations else None,
                "max_slope_deg": round(max(slopes), 2) if slopes else None,
                "mean_slope_deg": round(sum(slopes) / len(slopes), 2) if slopes else None,
                "coverage_class_counts": {str(k): classes.count(k) for k in sorted(set(classes))},
            },
            "availability": "available" if elevations else "unavailable",
            "provenance": ["observed", "derived"] if slopes else ["observed"],
            "source": self.source(),
            "warnings": [] if elevations else ["No valid elevation samples along this profile."],
            "limitations": self.limitations(),
        }

    def _ground_distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        lat_mid = math.radians((lat1 + lat2) / 2.0)
        dx = MARS_RADIUS_M * math.radians(lon2 - lon1) * math.cos(lat_mid)
        dy = MARS_RADIUS_M * math.radians(lat2 - lat1)
        return math.hypot(dx, dy)

    # ------------------------------------------------------------ raster grid
    def grid(self) -> Dict[str, Any]:
        """Cached arrays + georeferencing for deterministic route planning."""
        if not self.available():
            raise UnavailableError("NASA terrain package is not available on this server.")
        elevation = self._require("elevation")
        slope = self._require("slope")
        roughness = self._require("roughness")
        coverage = self._require("coverage")
        return {
            "elevation": elevation.data,
            "slope": slope.data,
            "roughness": roughness.data,
            "coverage": coverage.data,
            "transform": elevation.transform,
            "crs": elevation.crs,
            "width": elevation.width,
            "height": elevation.height,
            "resolution_x_m": float(abs(elevation.transform.a)),
            "resolution_y_m": float(abs(elevation.transform.e)),
        }

    def latlon_for_pixel(self, row: int, col: int) -> Tuple[float, float]:
        elevation = self._require("elevation")
        x = elevation.transform.c + (col + 0.5) * elevation.transform.a
        y = elevation.transform.f + (row + 0.5) * elevation.transform.e
        return self._from_raster_crs(elevation, x, y)

    def pixel_for_latlon(self, lon: float, lat: float) -> Optional[Tuple[int, int]]:
        located = self._point_index(lon, lat)
        if located is None:
            return None
        return located[0], located[1]

    def is_usable(self, row: int, col: int) -> bool:
        cls = self.coverage_class(row, col)
        if cls not in (1, 2):
            return False
        return self._value(self._require("elevation"), row, col) is not None

    # -------------------------------------------------------------- metadata
    def layer_metadata(self) -> Dict[str, Any]:
        try:
            elevation = self._require("elevation")
        except UnavailableError as exc:
            return {"available": False, "reason": str(exc)}
        meta = self.overlay_metadata()
        return {
            "available": True,
            "bounds_latlon": self.bounds_latlon(),
            "resolution_m": elevation.resolution_m,
            "shape": [elevation.height, elevation.width],
            "crs": elevation.crs.to_string() if elevation.crs else None,
            "nodata": "NaN",
            "units": {"elevation": "m", "slope": "degree", "roughness": "m (TRI Riley 1999)"},
            "display": meta.get("layers", {}),
            "image_projection": meta.get("image_projection"),
            "latitude_type": meta.get("latitude_type"),
            "provenance": self.provenance(),
        }

    def overlay_url(self, layer: str) -> Optional[str]:
        if self._paths is None:
            return None
        mapping = {
            "elevation": self._paths.elevation_png,
            "slope": self._paths.slope_png,
            "roughness": self._paths.roughness_png,
            "coverage": self._paths.coverage_png,
        }
        path = mapping.get(layer)
        if path is None or not path.exists():
            return None
        return static_url_for(path)

    @staticmethod
    def _assert_region(region_id: str) -> None:
        if region_id != REGION_ID:
            raise NotFoundError("Unknown region", details={"region_id": region_id})


_terrain_service: Optional[TerrainService] = None
_terrain_lock = threading.Lock()


def get_terrain_service() -> TerrainService:
    global _terrain_service
    with _terrain_lock:
        if _terrain_service is None:
            _terrain_service = TerrainService()
        return _terrain_service
