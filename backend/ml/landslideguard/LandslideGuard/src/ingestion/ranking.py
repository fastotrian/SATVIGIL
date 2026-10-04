"""Deterministic Sentinel-2 L2A product ranking.

Policy (documented in ranking.py::RANKING_POLICY):

    1. valid product (already enforced by `catalog.apply_filters`)
    2. lowest cloud cover
    3. greatest AOI intersection ratio (highest overlap with the AOI)
    4. closest acquisition time to `request.target_date`
       (falls back to the mid-point of [start, end] if no target given)
    5. product_id lexicographic order (final tie-break)

Every rule is a total order, so the sort is fully deterministic even when
several products tie on the first few keys.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from .aoi import parse_utc_iso
from .schemas import ProductMetadata, IngestionRequest


RANKING_POLICY = (
    "1) lowest cloudCover  "
    "2) greatest AOI intersection ratio  "
    "3) acquisition time closest to target_date "
    "(midpoint of [start, end] if not supplied)  "
    "4) product_id ascending"
)


def _resolve_target(request: IngestionRequest) -> datetime:
    if request.target_date:
        return parse_utc_iso(request.target_date, "target_date")
    s = parse_utc_iso(request.start, "start")
    e = parse_utc_iso(request.end,   "end")
    return s + (e - s) / 2


def _sort_key(p: ProductMetadata, target: datetime):
    cloud = 999.0 if p.cloud_cover is None else float(p.cloud_cover)
    # bigger overlap should sort earlier; invert sign for ascending sort
    overlap_key = -(p.aoi_intersection_ratio if p.aoi_intersection_ratio is not None else 0.0)
    # time distance to the target
    try:
        acq = parse_utc_iso(p.acquisition_start, "acquisition_start")
    except Exception:
        acq = target + timedelta(days=99999)
    time_dist_s = abs((acq - target).total_seconds())
    return (round(cloud, 6), round(overlap_key, 9), time_dist_s, p.product_id)


def rank_products(products: Sequence[ProductMetadata],
                  request: IngestionRequest) -> list[ProductMetadata]:
    """Return a NEW list of products in deterministic ranked order."""
    if not products:
        return []
    target = _resolve_target(request)
    return sorted(products, key=lambda p: _sort_key(p, target))


def select_best(products: Sequence[ProductMetadata],
                request: IngestionRequest) -> ProductMetadata | None:
    ranked = rank_products(products, request)
    return ranked[0] if ranked else None


__all__ = ["RANKING_POLICY", "rank_products", "select_best"]
