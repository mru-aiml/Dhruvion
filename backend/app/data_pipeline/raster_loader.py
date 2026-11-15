"""Raster dataset loading and querying utilities."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Any, Dict, List
from contextlib import contextmanager

import numpy as np

try:
    import rasterio
    from rasterio.windows import Window
    from rasterio.transform import xy, rowcol
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
except Exception:
    rasterio = None
    CRS = None
    Resampling = None

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RasterDataset:
    """Container for a loaded raster dataset with metadata."""
    path: Path
    dataset_id: str
    name: str
    
    # Rasterio dataset (opened on demand)
    _src: Optional[Any] = None
    
    # Cached properties
    _profile: Optional[Dict[str, Any]] = None
    _crs: Optional[Any] = None
    _transform: Optional[Any] = None
    _bounds: Optional[Tuple[float, float, float, float]] = None
    _nodata: Optional[float] = None
    _shape: Optional[Tuple[int, int]] = None
    _dtype: Optional[str] = None
    _crs_str: Optional[str] = None
    
    def __post_init__(self):
        if rasterio is None:
            raise RuntimeError("rasterio is not available")
        if not self.path.exists():
            raise FileNotFoundError(f"Raster file not found: {self.path}")
    
    def open(self) -> Any:
        """Open the raster dataset if not already open."""
        if self._src is None or self._src.closed:
            self._src = rasterio.open(self.path)
            self._profile = self._src.profile.copy()
            self._crs = self._src.crs
            self._transform = self._src.transform
            self._bounds = self._src.bounds
            self._nodata = self._src.nodata
            self._shape = (self._src.height, self._src.width)
            self._dtype = self._src.dtypes[0] if self._src.dtypes else None
            self._crs_str = str(self._src.crs) if self._src.crs else None
        return self._src
    
    def close(self):
        """Close the raster dataset."""
        if self._src and not self._src.closed:
            self._src.close()
            self._src = None
    
    @contextmanager
    def opened(self):
        """Context manager for automatic open/close."""
        try:
            src = self.open()
            yield src
        finally:
            # Don't close here - keep for reuse
            pass
    
    @property
    def profile(self) -> Dict[str, Any]:
        """Get raster profile (metadata)."""
        if self._profile is None:
            self.open()
        return self._profile or {}
    
    @property
    def crs(self) -> Optional[Any]:
        """Get coordinate reference system."""
        if self._crs is None:
            self.open()
        return self._crs
    
    @property
    def crs_str(self) -> Optional[str]:
        """Get CRS as string."""
        if self._crs_str is None:
            self.open()
        return self._crs_str
    
    @property
    def transform(self) -> Optional[Any]:
        """Get affine transform."""
        if self._transform is None:
            self.open()
        return self._transform
    
    @property
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Get bounds (left, bottom, right, top)."""
        if self._bounds is None:
            self.open()
        return self._bounds
    
    @property
    def nodata(self) -> Optional[float]:
        """Get nodata value."""
        if self._nodata is None:
            self.open()
        return self._nodata
    
    @property
    def shape(self) -> Optional[Tuple[int, int]]:
        """Get (height, width)."""
        if self._shape is None:
            self.open()
        return self._shape
    
    @property
    def width(self) -> int:
        return self.shape[1] if self.shape else 0
    
    @property
    def height(self) -> int:
        return self.shape[0] if self.shape else 0
    
    @property
    def dtype(self) -> Optional[str]:
        if self._dtype is None:
            self.open()
        return self._dtype
    
    def get_resolution(self) -> Tuple[float, float]:
        """Get pixel resolution in CRS units (x_res, y_res)."""
        transform = self.transform
        if transform:
            return abs(transform.a), abs(transform.e)
        return 0.0, 0.0
    
    def contains_coordinate(self, x: float, y: float) -> bool:
        """Check if coordinate is within raster bounds."""
        if self.bounds is None:
            return False
        left, bottom, right, top = self.bounds
        return left <= x <= right and bottom <= y <= top
    
    def coordinate_to_pixel(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert CRS coordinate to pixel row/col.
        
        Returns (row, col) - 0-indexed pixel coordinates.
        """
        src = self.open()
        row, col = rowcol(self.transform, x, y)
        return row, col
    
    def pixel_to_coordinate(self, row: int, col: int) -> Tuple[float, float]:
        """
        Convert pixel row/col to CRS coordinate.
        
        Returns (x, y) in CRS units.
        """
        return xy(self.transform, row, col)
    
    def read_window(self, window: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Read a window from the raster.
        
        Args:
            window: (row_start, col_start, height, width)
            
        Returns:
            numpy array of shape (height, width)
        """
        src = self.open()
        row_start, col_start, height, width = window
        rasterio_window = Window(col_start, row_start, width, height)
        data = src.read(1, window=rasterio_window)
        return data
    
    def sample_at(self, x: float, y: float) -> Optional[float]:
        """
        Sample raster value at given CRS coordinate.
        
        Returns None if coordinate is outside bounds or at NoData.
        """
        if not self.contains_coordinate(x, y):
            return None
        
        src = self.open()
        try:
            for val in src.sample([(x, y)]):
                v = float(val[0])
                nodata = self.nodata
                if nodata is not None and (v == nodata or np.isnan(v)):
                    return None
                return v
        except Exception as e:
            logger.warning(f"Error sampling at ({x}, {y}): {e}")
            return None
        return None
    
    def read_all(self, masked: bool = True) -> np.ndarray:
        """
        Read entire raster into memory (use with caution for large rasters).
        
        Args:
            masked: If True, return masked array with NoData masked
            
        Returns:
            numpy array of shape (height, width)
        """
        src = self.open()
        data = src.read(1)
        if masked and self.nodata is not None:
            data = np.ma.masked_equal(data, self.nodata)
        return data
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get a summary of raster metadata."""
        self.open()
        return {
            "path": str(self.path),
            "dataset_id": self.dataset_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "dtype": self.dtype,
            "crs": self.crs_str,
            "transform": [float(x) for x in self.transform.to_gdal()] if self.transform else None,
            "bounds": self.bounds,
            "resolution": self.get_resolution(),
            "nodata": self.nodata,
            "count": 1,
        }


def load_raster_dataset(
    path: Path,
    dataset_id: Optional[str] = None,
    name: Optional[str] = None
) -> RasterDataset:
    """
    Load a raster dataset from file.
    
    Args:
        path: Path to raster file
        dataset_id: Optional dataset identifier (default: filename stem)
        name: Optional display name (default: dataset_id)
        
    Returns:
        RasterDataset instance
    """
    if dataset_id is None:
        dataset_id = path.stem
    if name is None:
        name = dataset_id
    
    return RasterDataset(
        path=path,
        dataset_id=dataset_id,
        name=name
    )


def query_raster_at(
    raster: RasterDataset,
    x: float,
    y: float
) -> Optional[float]:
    """
    Query raster value at coordinate.
    
    Returns None if coordinate is outside bounds or at NoData.
    """
    return raster.sample_at(x, y)


def get_raster_info(path: Path) -> Dict[str, Any]:
    """
    Get basic raster information without fully loading data.
    
    Useful for cataloging and validation.
    """
    if rasterio is None:
        return {"error": "rasterio not available"}
    
    if not path.exists():
        return {"error": "File not found"}
    
    try:
        with rasterio.open(path) as src:
            return {
                "path": str(path),
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": src.dtypes[0] if src.dtypes else None,
                "crs": str(src.crs) if src.crs else None,
                "bounds": src.bounds,
                "transform": list(src.transform.to_gdal()) if src.transform else None,
                "nodata": src.nodata,
                "resolution": (abs(src.transform.a), abs(src.transform.e)) if src.transform else None,
                "driver": src.driver,
            }
    except Exception as e:
        return {"error": str(e)}