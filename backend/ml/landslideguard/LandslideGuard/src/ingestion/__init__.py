"""LandslideGuard - Module 1: Copernicus Data Space Ecosystem (CDSE)
Sentinel-2 L2A ingestion.

Scope of this package (per Module-1 contract):

    AOI + date range + cloud threshold
        -> CDSE Catalog API
        -> Sentinel-2 L2A search
        -> AOI / date / cloud filter
        -> deterministic ranking
        -> download to a project-managed cache
        -> product-level integrity validation
        -> IngestionResult

This package MUST NOT construct the Detection V1 14-channel tensor,
resample bands, guess B10, run inference, or modify frozen artifacts.
Module 2 will consume `IngestionResult.local_path` and produce the 14-
channel input.
"""
from .schemas import (
    IngestionRequest, IngestionResult, ProductMetadata,
    IngestionStatus, CacheStatus,
)
from .errors import IngestionError, ErrorCode
from .pipeline import ingest

__all__ = [
    "IngestionRequest", "IngestionResult", "ProductMetadata",
    "IngestionStatus", "CacheStatus",
    "IngestionError", "ErrorCode",
    "ingest",
]
