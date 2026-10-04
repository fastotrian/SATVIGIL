"""AOI + date-range validation for CDSE ingestion.

Reuses `shapely` (already a project dependency). Nothing here reprojects
- CDSE OData catalog wants EPSG:4326 polygons directly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from shapely.geometry import Polygon, mapping
from shapely.wkt import loads as wkt_loads
from shapely.errors import GEOSException

from .errors import ErrorCode, IngestionError


def bbox_to_wkt(west: float, south: float, east: float, north: float) -> str:
    """Return a closed WGS84 WKT polygon for a lon/lat bounding box.

    Order is (W, S, E, N). Raises `IngestionError(INVALID_AOI)` if the box
    is degenerate or spans the antimeridian.
    """
    if not (-180 <= west < east <= 180):
        raise IngestionError(
            ErrorCode.INVALID_AOI,
            "West must be less than east and both must be in [-180, 180].",
            {"west": west, "east": east})
    if not (-90 <= south < north <= 90):
        raise IngestionError(
            ErrorCode.INVALID_AOI,
            "South must be less than north and both must be in [-90, 90].",
            {"south": south, "north": north})
    return (
        f"POLYGON(({west} {south},"
        f"{east} {south},"
        f"{east} {north},"
        f"{west} {north},"
        f"{west} {south}))"
    )


def parse_aoi_wkt(wkt: str) -> Polygon:
    """Parse a WKT polygon into a Shapely geometry and validate it."""
    try:
        geom = wkt_loads(wkt)
    except (GEOSException, ValueError, TypeError) as e:
        raise IngestionError(
            ErrorCode.INVALID_AOI,
            f"AOI is not valid WKT: {e.__class__.__name__}",
            {"reason": str(e)}) from e
    if geom.is_empty:
        raise IngestionError(ErrorCode.INVALID_AOI, "AOI polygon is empty.")
    if not geom.is_valid:
        raise IngestionError(
            ErrorCode.INVALID_AOI,
            "AOI polygon is not valid (self-intersecting or degenerate).",
            {"explanation": str(geom)[:200]})
    minx, miny, maxx, maxy = geom.bounds
    if not (-180 <= minx <= 180 and -180 <= maxx <= 180
            and -90 <= miny <= 90 and -90 <= maxy <= 90):
        raise IngestionError(
            ErrorCode.INVALID_AOI,
            "AOI bounds are outside the WGS84 domain.",
            {"bounds": [minx, miny, maxx, maxy]})
    return geom


def parse_utc_iso(s: str, field: str) -> datetime:
    """Accept an ISO-8601 timestamp with 'Z' or explicit '+00:00' offset."""
    if not isinstance(s, str) or not s:
        raise IngestionError(
            ErrorCode.INVALID_DATE_RANGE,
            f"{field} must be an ISO 8601 UTC timestamp string.",
            {"got": s})
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        raise IngestionError(
            ErrorCode.INVALID_DATE_RANGE,
            f"{field} is not a valid ISO 8601 timestamp.",
            {"got": s, "reason": str(e)}) from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_date_range(start_iso: str, end_iso: str
                        ) -> tuple[datetime, datetime]:
    start = parse_utc_iso(start_iso, "start")
    end   = parse_utc_iso(end_iso,   "end")
    if start >= end:
        raise IngestionError(
            ErrorCode.INVALID_DATE_RANGE,
            "Start must strictly precede end.",
            {"start": start_iso, "end": end_iso})
    if (end - start).days > 366:
        # not a hard error - just guard against pathological queries
        pass
    return start, end


def validate_cloud_threshold(v: float) -> float:
    if not isinstance(v, (int, float)):
        raise IngestionError(
            ErrorCode.INVALID_CLOUD_THRESHOLD,
            "max_cloud_cover must be a number.",
            {"got": v})
    if not (0.0 <= float(v) <= 100.0):
        raise IngestionError(
            ErrorCode.INVALID_CLOUD_THRESHOLD,
            "max_cloud_cover must be in [0, 100].",
            {"got": float(v)})
    return float(v)


def aoi_to_geojson(polygon: Polygon) -> dict:
    return mapping(polygon)


__all__ = [
    "bbox_to_wkt", "parse_aoi_wkt",
    "parse_utc_iso", "validate_date_range", "validate_cloud_threshold",
    "aoi_to_geojson",
]
