"""Evidence-based cache policy configuration.

Defaults are derived from the Phase-6 live measurements (see
phase6_multi_location_live_report.md), NOT chosen arbitrarily:

  * Measured cache after Phase 6 : ~2784.5 MB (84 IMERG granules + 6 SRTM tiles)
  * Measured IMERG granule       : ~32 MB each (0.1deg global daily NetCDF)
  * Measured SRTM tile zip        : ~13.5 MB each (1x1 degree)
  * Measured growth               : ~467 MB / location (14 IMERG + 1 tile)
  * Free disk after Phase 6       : ~7.33-7.58 GB (D:)

Sizing calculation (documented):
  envelope = free_disk + current_cache ≈ 7.58 + 2.78 = 10.36 GB
  hard ceiling (keep MIN_FREE) = envelope - MIN_FREE = 10.36 - 5.0 = 5.36 GB
  MAX_CACHE chosen BELOW the ceiling with margin -> 4.0 GB
    (at 4.0 GB cache, free ≈ 6.36 GB, i.e. 1.36 GB above the 5 GB guard)

Two datasets are treated differently:
  * IMERG  : time-dependent, continuously growing; shorter retention, evicted first.
  * SRTM   : static, reusable terrain; longer retention, evicted last (protected).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class CachePolicy:
    # Hard download guard (preserved from Phase 4/5/6).
    min_free_disk_gb: float = 5.0
    # Soft cap enforced by maintenance/eviction.
    max_cache_size_gb: float = 4.0
    # Per-dataset soft caps (sum == max_cache_size_gb).
    imerg_cache_limit_gb: float = 3.0
    srtm_cache_limit_gb: float = 1.0
    # Retention windows (days since last access).
    imerg_retention_days: int = 30
    srtm_retention_days: int = 365
    # Conservative per-file size estimates for pre-download space planning (MB).
    imerg_granule_mb: float = 33.0
    srtm_tile_mb: float = 25.0

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        assert self.min_free_disk_gb > 0
        assert self.max_cache_size_gb > 0
        assert self.imerg_cache_limit_gb + self.srtm_cache_limit_gb <= self.max_cache_size_gb + 1e-9, \
            "IMERG + SRTM sub-limits must not exceed the total max cache"


DEFAULT_POLICY = CachePolicy()

__all__ = ["CachePolicy", "DEFAULT_POLICY"]
