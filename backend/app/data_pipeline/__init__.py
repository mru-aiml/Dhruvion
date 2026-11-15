"""Data pipeline package for DHRUVION Mars geospatial data processing."""

from app.data_pipeline.catalog import DatasetCatalog, get_dataset_catalog
from app.data_pipeline.ingestion import discover_datasets, load_dataset_metadata
from app.data_pipeline.raster_loader import RasterDataset, load_raster_dataset, query_raster_at
from app.data_pipeline.vector_loader import VectorDataset, load_vector_dataset, query_vector_features
from app.data_pipeline.metadata import DatasetMetadata, load_metadata, validate_metadata
from app.data_pipeline.validation import validate_raster, validate_vector, ValidationResult
from app.data_pipeline.catalog import DatasetEntry, DatasetCatalog

__all__ = [
    "DatasetCatalog",
    "get_dataset_catalog",
    "discover_datasets",
    "load_dataset_metadata",
    "RasterDataset",
    "load_raster_dataset",
    "query_raster_at",
    "VectorDataset",
    "load_vector_dataset",
    "query_vector_features",
    "DatasetMetadata",
    "load_metadata",
    "validate_metadata",
    "validate_raster",
    "validate_vector",
    "ValidationResult",
    "DatasetEntry",
]