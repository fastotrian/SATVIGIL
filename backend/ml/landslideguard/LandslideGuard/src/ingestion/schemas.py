"""Typed dataclasses for the CDSE ingestion module.

`IngestionRequest`  - user input (AOI + date range + cloud threshold).
`ProductMetadata`   - one CDSE catalog product.
`IngestionResult`   - final output of `ingest()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class IngestionStatus(str, Enum):
    SUCCESS   = "SUCCESS"
    CACHE_HIT = "CACHE_HIT"
    FAILED    = "FAILED"


class CacheStatus(str, Enum):
    MISS      = "MISS"       # Not present locally; downloaded fresh.
    HIT       = "HIT"        # Cached copy passed integrity checks.
    CORRUPTED = "CORRUPTED"  # Present but rejected -> re-downloaded.


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ------------------------------ input ------------------------------

@dataclass(frozen=True)
class IngestionRequest:
    """One CDSE Sentinel-2 L2A ingestion request.

    AOI is a well-known-text (WKT) polygon in WGS84 (EPSG:4326). Callers
    can also build one from a bbox with `aoi.bbox_to_wkt(...)`.
    """
    aoi_wkt: str
    start: str                    # ISO 8601, e.g. "2024-07-25T00:00:00Z"
    end: str                      # ISO 8601, exclusive upper bound
    max_cloud_cover: float = 30.0 # per cent, in [0, 100]
    max_results: int = 50         # cap on catalog results returned
    target_date: str | None = None  # optional; used by ranker for tie-break
    aoi_label: str = ""             # human-readable label (e.g. "wayanad")

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------ product ----------------------------

@dataclass
class ProductMetadata:
    """One CDSE Sentinel-2 L2A product surfaced by the catalog.

    All fields are safe to log / serialize. Never include credentials.
    """
    product_id: str                # OData product UUID
    name: str                      # e.g. "S2A_MSIL2A_20240728T053641_..."
    product_type: str              # "S2MSI2A"
    platform: str                  # "SENTINEL-2"
    tile_id: str | None            # T43QGE (parsed from name)
    acquisition_start: str         # ISO 8601 UTC
    acquisition_end: str           # ISO 8601 UTC
    processing_level: str          # "L2A"
    processing_baseline: str | None
    cloud_cover: float | None
    footprint_wkt: str | None      # scene footprint in EPSG:4326
    aoi_intersection_ratio: float | None  # 0..1 (set by pipeline)
    online: bool                   # CDSE availability flag
    download_url: str              # OData $value URL
    provider: str = "CDSE"
    size_bytes: int | None = None
    checksum: str | None = None    # server-side MD5 if reported

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ------------------------------ output -----------------------------

@dataclass
class IngestionResult:
    status: IngestionStatus
    cache_status: CacheStatus
    request: IngestionRequest | None = None
    product: ProductMetadata | None = None
    local_path: str | None = None       # dir OR .zip on disk
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None  # local SHA-256 of the downloaded archive
    validation: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=utc_now_iso)
    error: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


__all__ = [
    "IngestionStatus", "CacheStatus",
    "IngestionRequest", "ProductMetadata", "IngestionResult",
    "utc_now_iso",
]
