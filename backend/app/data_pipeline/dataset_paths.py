"""Resolve and describe the supplied NASA ``DHRUVION_DATA`` handover package.

The package is treated as a configurable input, never as a developer-specific
absolute path. Resolution order:

1. ``DHRUVION_DATA_DIR`` environment variable / settings value
2. ``<repo>/DHRUVION_DATA``
3. ``<repo>/data/source_packages/nasa_dataset_package_2026/DHRUVION_DATA``
4. ``<repo>/Dhruvion-main/data/source_packages/nasa_dataset_package_2026/DHRUVION_DATA``

All callers should go through :func:`get_dataset_paths`. Every path is optional:
services must report ``unavailable`` rather than inventing data when a file is
missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

# Known product file names inside the package (stable handover contract).
TERRAIN_PREFIX = "Mars_MGS_MOLA_DEM_mosaic_global_463m__GaleAOI"
CTX_PREFIX = "MurrayLab_GlobalCTXMosaic_V01_E136_N-08__GaleAOI_x10__GaleAOI"


def _candidate_dirs() -> List[Path]:
    candidates: List[Path] = []
    configured = settings.DHRUVION_DATA_DIR or os.environ.get("DHRUVION_DATA_DIR")
    if configured:
        candidates.append(Path(configured).expanduser())

    base = settings.BASE_DIR
    candidates.extend(
        [
            base / "DHRUVION_DATA",
            base / "data" / "source_packages" / "nasa_dataset_package_2026" / "DHRUVION_DATA",
            base / "Dhruvion-main" / "data" / "source_packages" / "nasa_dataset_package_2026" / "DHRUVION_DATA",
        ]
    )
    return candidates


@lru_cache(maxsize=1)
def resolve_dataset_dir() -> Optional[Path]:
    """Return the first candidate directory that looks like a DHRUVION package."""
    for candidate in _candidate_dirs():
        try:
            if candidate.is_dir() and (candidate / "processed").is_dir():
                return candidate.resolve()
        except OSError:
            continue
    return None


@dataclass(frozen=True)
class DatasetPaths:
    """All optional file paths for the handover package."""

    root: Path

    # Terrain
    terrain_dir: Path
    elevation_tif: Path
    slope_tif: Path
    roughness_tif: Path
    coverage_tif: Path
    elevation_png: Path
    slope_png: Path
    roughness_png: Path
    coverage_png: Path
    terrain_overlay_metadata: Path
    terrain_provenance: Path

    # CTX
    ctx_dir: Path
    ctx_png: Path
    ctx_tif: Path
    ctx_overlay_metadata: Path
    ctx_provenance: Path

    # REMS
    rems_dir: Path
    rems_sol_summary: Path
    rems_session_summary: Path
    rems_observations: Path
    rems_trends: Path
    rems_provenance: Path

    # RAD
    rad_dir: Path
    rad_sol_summary: Path
    rad_observations: Path
    rad_trends: Path
    rad_provenance: Path

    # Package catalogs
    metadata_dir: Path
    final_catalog: Path
    validated_catalog: Path
    package_manifest: Path

    @property
    def processed_dir(self) -> Path:
        return self.root / "processed"

    def missing(self, *names: str) -> List[str]:
        """Return the names of required attributes whose files do not exist."""
        missing: List[str] = []
        for name in names:
            value = getattr(self, name, None)
            if not isinstance(value, Path) or not value.exists():
                missing.append(name)
        return missing


@lru_cache(maxsize=1)
def get_dataset_paths() -> Optional[DatasetPaths]:
    """Return resolved paths, or ``None`` when the package is not installed."""
    root = resolve_dataset_dir()
    if root is None:
        return None

    terrain = root / "processed" / "terrain"
    ctx = root / "processed" / "ctx"
    rems = root / "processed" / "rems"
    rad = root / "processed" / "rad"
    metadata = root / "metadata"

    return DatasetPaths(
        root=root,
        terrain_dir=terrain,
        elevation_tif=terrain / f"{TERRAIN_PREFIX}_elevation_m.tif",
        slope_tif=terrain / f"{TERRAIN_PREFIX}_slope_deg.tif",
        roughness_tif=terrain / f"{TERRAIN_PREFIX}_roughness_tri_riley_m.tif",
        coverage_tif=terrain / f"{TERRAIN_PREFIX}_coverage_mask.tif",
        elevation_png=terrain / f"{TERRAIN_PREFIX}_elevation.png",
        slope_png=terrain / f"{TERRAIN_PREFIX}_slope.png",
        roughness_png=terrain / f"{TERRAIN_PREFIX}_roughness.png",
        coverage_png=terrain / f"{TERRAIN_PREFIX}_coverage.png",
        terrain_overlay_metadata=terrain / f"{TERRAIN_PREFIX}_overlay_metadata.json",
        terrain_provenance=terrain / f"{TERRAIN_PREFIX}_terrain_provenance.json",
        ctx_dir=ctx,
        ctx_png=ctx / f"{CTX_PREFIX}.png",
        ctx_tif=ctx / f"{CTX_PREFIX}_clip.tif",
        ctx_overlay_metadata=ctx / f"{CTX_PREFIX}_overlay_metadata.json",
        ctx_provenance=ctx / f"{CTX_PREFIX}_ctx_provenance.json",
        rems_dir=rems,
        rems_sol_summary=rems / "rems_sol_summary.json",
        rems_session_summary=rems / "rems_session_summary.json",
        rems_observations=rems / "rems_observations_clean.json",
        rems_trends=rems / "rems_trends.json",
        rems_provenance=rems / "rems_processing_provenance.json",
        rad_dir=rad,
        rad_sol_summary=rad / "rad_sol_summary.json",
        rad_observations=rad / "rad_observations_clean.json",
        rad_trends=rad / "rad_trends.json",
        rad_provenance=rad / "rad_processing_provenance.json",
        metadata_dir=metadata,
        final_catalog=metadata / "FINAL_DATASET_CATALOG.json",
        validated_catalog=metadata / "validated_dataset_catalog.json",
        package_manifest=metadata / "PACKAGE_MANIFEST.json",
    )


def static_url_for(path: Path) -> Optional[str]:
    """Map a package file to its mounted ``/static/dhruvion`` URL."""
    paths = get_dataset_paths()
    if paths is None:
        return None
    try:
        relative = path.resolve().relative_to(paths.root.resolve())
    except (OSError, ValueError):
        return None
    mount = settings.DATASET_STATIC_MOUNT.rstrip("/")
    return f"{mount}/{relative.as_posix()}"


def reset_dataset_paths_cache() -> None:
    """Clear resolver caches (used by tests and when configuration changes)."""
    resolve_dataset_dir.cache_clear()
    get_dataset_paths.cache_clear()
