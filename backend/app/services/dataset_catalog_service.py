"""Dataset catalogue built from the verified NASA handover package.

The catalogue reports files that are actually installed. Files that the
package manifest marks as not downloaded are still listed with
``status="unavailable"`` so the UI can distinguish "not supplied" from
"supplied and broken". Absolute developer paths are never returned.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.exceptions import NotFoundError
from app.data_pipeline.dataset_paths import get_dataset_paths
from app.services.rad_service import get_rad_service
from app.services.rems_service import get_rems_service
from app.services.terrain_service import get_terrain_service

REGION_ID = "gale_crater"
REGION_CRS = "urn:ogc:def:crs:IAU2000::104905"


def _read_json(path) -> Any:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover
        return None


def _relative(path) -> Optional[str]:
    paths = get_dataset_paths()
    if paths is None or path is None:
        return None
    try:
        return path.resolve().relative_to(paths.root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


class DatasetCatalogService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: Optional[Dict[str, Any]] = None

    # --------------------------------------------------------------- helpers
    def _file_entry(
        self,
        dataset_id: str,
        name: str,
        dataset_type: str,
        file_format: str,
        provenance: str,
        path,
        metadata_path=None,
        crs: Optional[str] = REGION_CRS,
        resolution_m: Optional[float] = None,
        coverage: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        geometry_types: Optional[List[str]] = None,
        feature_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        exists = bool(path is not None and path.exists())
        return {
            "dataset_id": dataset_id,
            "name": name,
            "dataset_type": dataset_type,
            "format": file_format,
            "status": status or ("available" if exists else "unavailable"),
            "provenance": provenance if exists else "unavailable",
            "file_path": _relative(path) if path is not None else "",
            "metadata_path": _relative(metadata_path) if metadata_path is not None else None,
            "crs": crs,
            "coverage": coverage,
            "resolution_m": resolution_m,
            "file_size_bytes": path.stat().st_size if exists else None,
            "feature_count": feature_count,
            "geometry_types": geometry_types or [],
            "warnings": warnings or ([] if exists else ["File is not present in the handover package."]),
            "last_validated": None,
            "metadata": metadata or {},
        }

    @staticmethod
    def _text(entry: Dict[str, Any]) -> str:
        return " ".join(
            str(value)
            for value in (
                entry.get("dataset_id"),
                entry.get("name"),
                entry.get("dataset_type"),
                entry.get("format"),
                entry.get("status"),
                entry.get("provenance"),
                (entry.get("metadata") or {}).get("product_id"),
                (entry.get("metadata") or {}).get("classification"),
            )
            if value
        ).lower()

    # ------------------------------------------------------------- catalogue
    def _build(self) -> Dict[str, Any]:
        paths = get_dataset_paths()
        terrain = get_terrain_service()
        entries: List[Dict[str, Any]] = []

        terrain_provenance = terrain.provenance()
        stats = terrain_provenance.get("statistics", {})
        elevation_stats = stats.get("elevation_m", {})
        input_sha = (terrain_provenance.get("input") or {}).get("sha256")
        bounds = terrain.bounds_latlon()
        terrain_coverage = {"bounds_latlon": bounds, "resolution_m": terrain.resolution_m()}
        terrain_metadata = {
            "product_id": "Mars_MGS_MOLA_DEM_mosaic_global_463m",
            "provider": "NASA / USGS Astrogeology",
            "classification": "OBSERVED (elevation) / DERIVED (slope, roughness, coverage)",
            "processing_level": "Derived gridded product",
            "validation_status": "VALIDATED WITH LIMITATIONS",
            "input_sha256": input_sha,
            "limitations": (
                "Pixel baseline ~463 m. Slopes understate local rover-scale slopes. "
                "Coverage class 2 cells have no slope/roughness."
            ),
            "statistics": {
                "elevation_min_m": elevation_stats.get("min"),
                "elevation_max_m": elevation_stats.get("max"),
                "elevation_mean_m": elevation_stats.get("mean"),
            },
        }

        if paths is not None:
            entries.extend(
                [
                    self._file_entry(
                        "terrain_elevation",
                        "MOLA Elevation (Gale AOI clip)",
                        "raster",
                        "GeoTIFF (float32)",
                        "observed",
                        paths.elevation_tif,
                        metadata_path=paths.terrain_overlay_metadata,
                        resolution_m=terrain.resolution_m(),
                        coverage=terrain_coverage,
                        warnings=list(terrain.limitations()),
                        metadata={**terrain_metadata, "units": "m"},
                    ),
                    self._file_entry(
                        "terrain_slope",
                        "Slope (Horn 1981, MOLA-derived)",
                        "derived",
                        "GeoTIFF (float32)",
                        "derived",
                        paths.slope_tif,
                        metadata_path=paths.terrain_provenance,
                        resolution_m=terrain.resolution_m(),
                        coverage=terrain_coverage,
                        warnings=[
                            "Derived at ~463 m/px; regional indicator, not rover-scale trafficability.",
                            "Coverage class 2 cells are NoData (NaN) and are not zero-filled.",
                        ],
                        metadata={**terrain_metadata, "units": "degree", "method": "Horn (1981) 3x3"},
                    ),
                    self._file_entry(
                        "terrain_roughness",
                        "Terrain Ruggedness Index (Riley 1999, MOLA-derived)",
                        "derived",
                        "GeoTIFF (float32)",
                        "derived",
                        paths.roughness_tif,
                        metadata_path=paths.terrain_provenance,
                        resolution_m=terrain.resolution_m(),
                        coverage=terrain_coverage,
                        warnings=[
                            "Derived at ~463 m/px; regional indicator, not rover-scale trafficability.",
                            "Coverage class 2 cells are NoData (NaN) and are not zero-filled.",
                        ],
                        metadata={
                            **terrain_metadata,
                            "units": "m (TRI, Riley 1999)",
                            "method": "Riley, DeGloria & Elliot (1999)",
                        },
                    ),
                    self._file_entry(
                        "terrain_coverage",
                        "Terrain Coverage Mask",
                        "derived",
                        "GeoTIFF (uint8)",
                        "derived",
                        paths.coverage_tif,
                        metadata_path=paths.terrain_overlay_metadata,
                        resolution_m=terrain.resolution_m(),
                        coverage=terrain_coverage,
                        warnings=["Classes: 0 no elevation, 1 valid derivatives, 2 elevation only."],
                        metadata={
                            **terrain_metadata,
                            "units": "class",
                            "classes": {0: "no elevation", 1: "valid derivatives", 2: "elevation only"},
                        },
                    ),
                ]
            )

            ctx_meta = _read_json(paths.ctx_overlay_metadata) or {}
            alignment = ctx_meta.get("alignment_with_dem", {})
            ctx_res = (alignment.get("image_res") or [None])[0]
            entries.append(
                self._file_entry(
                    "ctx_mosaic",
                    "Gale Crater CTX Mosaic (processed clip)",
                    "raster",
                    "GeoTIFF (uint8) + PNG display product",
                    "observed",
                    paths.ctx_tif,
                    metadata_path=paths.ctx_overlay_metadata,
                    crs=ctx_meta.get("image_projection", "Mars_2015_Ocentric_Equirectangular_clon_0"),
                    resolution_m=ctx_res,
                    coverage={
                        "bounds_latlon": _leaflet_latlon(ctx_meta.get("leaflet_bounds")),
                        "partial_coverage": True,
                    },
                    warnings=[
                        "Pixel values are 8-bit DN, not calibrated reflectance.",
                        "Partial coverage: lat -6.9187..-4.0, lon 136.1999..139.4; the DEM AOI extends beyond it.",
                        "CTX/DEM alignment is NEAR_EQUIVALENT_CRS_DIFFERENT_GRID with a max offset of "
                        f"{alignment.get('max_coordinate_offset_m', 'unknown')} m.",
                    ],
                    metadata={
                        "product_id": "MurrayLab_GlobalCTXMosaic_V01_E136_N-08",
                        "provider": "NASA/JPL/MSSS, Caltech Murray Lab",
                        "classification": "OBSERVED",
                        "projection": ctx_meta.get("image_projection"),
                        "latitude_type": ctx_meta.get("latitude_type"),
                        "stretch": ctx_meta.get("stretch"),
                        "alignment": alignment,
                    },
                )
            )
        else:
            for dataset_id, name, dtype in (
                ("terrain_elevation", "MOLA Elevation (Gale AOI clip)", "raster"),
                ("terrain_slope", "Slope (MOLA-derived)", "derived"),
                ("terrain_roughness", "Terrain Ruggedness Index (MOLA-derived)", "derived"),
                ("terrain_coverage", "Terrain Coverage Mask", "derived"),
                ("ctx_mosaic", "Gale Crater CTX Mosaic", "raster"),
            ):
                entries.append(
                    self._file_entry(
                        dataset_id,
                        name,
                        dtype,
                        "GeoTIFF",
                        "unavailable",
                        None,
                        status="unavailable",
                        metadata={"reason": "DHRUVION_DATA package not installed."},
                    )
                )

        rems = get_rems_service()
        rad = get_rad_service()
        if paths is not None:
            entries.append(
                self._file_entry(
                    "rems_environment",
                    "Curiosity REMS Environmental Tables (sols 9 and 11)",
                    "other",
                    "JSON tables",
                    "observed",
                    paths.rems_observations,
                    metadata_path=paths.rems_provenance,
                    crs=None,
                    coverage={
                        "type": "point",
                        "spatial": "Curiosity rover location only",
                        "temporal_sols": [9, 11],
                        "live": False,
                        "forecast": False,
                    },
                    warnings=[
                        "Historical rover point measurements; not live, forecast, or spatially distributed.",
                        "Wind samples are sparse and reported as insufficient_data.",
                    ],
                    metadata={
                        "product_id": "MSL-M-REMS-5-MODRDR-V1.0",
                        "provider": "NASA PDS Atmospheres",
                        "classification": "OBSERVED + DERIVED statistics",
                        "units": ["K", "Pa", "m/s", "degree", "%", "W/m^2"],
                        "default_filter": "all_valid_values",
                    },
                )
            )
            entries.append(
                self._file_entry(
                    "rad_dosimetry",
                    "Curiosity RAD Dosimetry (sols 1-3)",
                    "other",
                    "JSON tables",
                    "observed",
                    paths.rad_observations,
                    metadata_path=paths.rad_provenance,
                    crs=None,
                    coverage={
                        "type": "point",
                        "spatial": "Curiosity rover location only",
                        "temporal_sols": [1, 2, 3],
                        "route_specific": False,
                    },
                    warnings=[
                        "Detectors B and E are separate and never combined.",
                        "qc_placeholder is not a quality flag.",
                        "Historical point measurements; not route-specific radiation predictions.",
                    ],
                    metadata={
                        "product_id": "MSL-M-RAD-3-RDR-V1.0",
                        "provider": "NASA PDS PPI",
                        "classification": "OBSERVED",
                        "unit": "microGray / Hour",
                        "detectors": ["B (silicon detector)", "E (BC-432 plastic scintillator)"],
                    },
                )
            )

        # NASA Mars Trek tile layers are catalogued but are not local files.
        for layer in (
            ("mars_trek_mola_colorshade", "Mars Trek MOLA Color-Shaded Relief", "tiles", 463.0),
            ("mola_roughness_trek", "MOLA Global Roughness (Mars Trek)", "tiles", 2368.0),
            ("mars_mola_hrsc_blend", "MOLA + HRSC Color Hillshade", "tiles", 200.0),
            ("viking_mdim", "Viking Global Color Mosaic", "tiles", 232.0),
        ):
            entries.append(
                {
                    "dataset_id": layer[0],
                    "name": layer[1],
                    "dataset_type": layer[2],
                    "format": "WMTS tiles",
                    "status": "available",
                    "provenance": "observed",
                    "file_path": "",
                    "metadata_path": None,
                    "crs": REGION_CRS,
                    "coverage": {"global": True},
                    "resolution_m": layer[3],
                    "file_size_bytes": None,
                    "feature_count": None,
                    "geometry_types": [],
                    "warnings": ["NASA Mars Trek tile service; requires network access."],
                    "last_validated": None,
                    "metadata": {
                        "provider": "NASA Mars Trek",
                        "classification": "OBSERVED",
                        "remote": True,
                    },
                }
            )

        entries.extend(self._unavailable_from_manifest())

        available = [entry for entry in entries if entry["status"] == "available"]
        statistics = {
            "total": len(entries),
            "available": len(available),
            "unavailable": len(entries) - len(available),
            "observed": sum(1 for entry in entries if entry["provenance"] == "observed"),
            "derived": sum(1 for entry in entries if entry["provenance"] == "derived"),
            "simulated": sum(1 for entry in entries if entry["provenance"] == "simulated"),
            "by_type": {},
            "package_installed": paths is not None,
            "package_name": paths.root.name if paths is not None else None,
        }
        for entry in entries:
            statistics["by_type"][entry["dataset_type"]] = statistics["by_type"].get(entry["dataset_type"], 0) + 1
        return {
            "catalog_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": entries,
            "statistics": statistics,
        }

    def _unavailable_from_manifest(self) -> List[Dict[str, Any]]:
        paths = get_dataset_paths()
        if paths is None:
            return []
        manifest = _read_json(paths.final_catalog)
        if not manifest:
            return []
        entries: List[Dict[str, Any]] = []
        for candidate in manifest.get("datasets", []):
            availability = str(candidate.get("availability", ""))
            if not availability.upper().startswith("NOT AVAILABLE"):
                continue
            candidate_id = candidate.get("candidate_id") or candidate.get("dataset_name", "unknown")
            entries.append(
                {
                    "dataset_id": f"package_{str(candidate_id).lower()}",
                    "name": candidate.get("dataset_name", "Unavailable package candidate"),
                    "dataset_type": "other",
                    "format": candidate.get("file_format") or "unknown",
                    "status": "unavailable",
                    "provenance": "unavailable",
                    "file_path": "",
                    "metadata_path": None,
                    "crs": None,
                    "coverage": None,
                    "resolution_m": None,
                    "file_size_bytes": None,
                    "feature_count": None,
                    "geometry_types": [],
                    "warnings": [
                        candidate.get("not_available_reason")
                        or "Not available in the handover package.",
                        candidate.get("limitations") or "",
                    ],
                    "last_validated": None,
                    "metadata": {
                        "candidate_id": candidate_id,
                        "product_id": candidate.get("product_id"),
                        "classification": candidate.get("classification"),
                        "processing_level": candidate.get("processing_level"),
                        "coverage_text": candidate.get("coverage"),
                        "validation_status": candidate.get("validation_status"),
                        "source_url": candidate.get("source_url"),
                    },
                }
            )
        return entries

    # ---------------------------------------------------------------- public
    def catalog(
        self,
        dataset_type: Optional[str] = None,
        status: Optional[str] = None,
        provenance: Optional[str] = None,
        region_id: Optional[str] = None,
        text_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        if region_id and region_id != REGION_ID:
            raise NotFoundError("Unknown region", details={"region_id": region_id})
        with self._lock:
            if self._cache is None:
                self._cache = self._build()
            data = {
                "catalog_version": self._cache["catalog_version"],
                "generated_at": self._cache["generated_at"],
                "datasets": list(self._cache["datasets"]),
                "statistics": dict(self._cache["statistics"]),
            }
        entries = data["datasets"]
        if dataset_type:
            entries = [entry for entry in entries if entry["dataset_type"] == dataset_type]
        if status:
            entries = [entry for entry in entries if entry["status"] == status]
        if provenance:
            entries = [entry for entry in entries if entry["provenance"] == provenance]
        if text_query:
            needle = text_query.lower()
            entries = [entry for entry in entries if needle in self._text(entry)]
        data["datasets"] = entries
        data["statistics"]["filtered_total"] = len(entries)
        return data

    def get(self, dataset_id: str) -> Dict[str, Any]:
        for entry in self.catalog()["datasets"]:
            if entry["dataset_id"] == dataset_id:
                return entry
        raise NotFoundError("Dataset not found", details={"dataset_id": dataset_id})

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None


def _leaflet_latlon(bounds: Any) -> Optional[Dict[str, float]]:
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        return None
    try:
        (south, west), (north, east) = bounds
        return {"south": float(south), "north": float(north), "west": float(west), "east": float(east)}
    except (TypeError, ValueError):
        return None


_catalog: Optional[DatasetCatalogService] = None
_lock = threading.Lock()


def get_dataset_catalog_service() -> DatasetCatalogService:
    global _catalog
    with _lock:
        if _catalog is None:
            _catalog = DatasetCatalogService()
        return _catalog
