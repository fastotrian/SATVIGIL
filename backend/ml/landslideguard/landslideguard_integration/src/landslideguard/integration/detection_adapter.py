"""Detection -> Monitoring handoff adapter.

Consumes a Detection fixture/handoff feature and emits a
`detection_monitoring/1.0` feature (validated against the Phase-1 schema),
registering a canonical site_id in the site registry.

CRS policy: if the detection geometry is not EPSG:4326, it is REPROJECTED
(real pyproj transform) to EPSG:4326 before the integration boundary. The
original CRS is preserved in metadata (`source_crs`). Coordinates are never
relabeled without transformation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..schemas import DETECTION_MONITORING_SCHEMA, validate
from ..common import SiteRegistry
from .fixtures import DetectionFixture


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _reproject_ring(ring, transformer):
    return [list(transformer.transform(x, y)) for x, y in ring]


def _to_4326(geometry: dict, centroid: dict, crs: str):
    """Return (geometry_4326, centroid_4326_latlon, source_crs)."""
    if crs == "EPSG:4326":
        # Passthrough; centroid already lat/lon.
        return geometry, centroid, "EPSG:4326"

    import pyproj
    tr = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    if geometry["type"] != "Polygon":
        raise ValueError(f"adapter supports Polygon only, got {geometry['type']}")
    new_coords = [_reproject_ring(ring, tr) for ring in geometry["coordinates"]]
    geom_4326 = {"type": "Polygon", "coordinates": new_coords}

    # Centroid: accept projected {x,y} or recompute from ring.
    if "x" in centroid and "y" in centroid:
        lon, lat = tr.transform(centroid["x"], centroid["y"])
    else:
        ring = new_coords[0]
        lon = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
        lat = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    return geom_4326, {"latitude": float(lat), "longitude": float(lon)}, crs


def adapt_detection_to_monitoring(
    fixture: DetectionFixture,
    registry: SiteRegistry,
    *,
    scene_id: str = "controlled_scene",
) -> dict:
    """Register a canonical site and return a validated detection_monitoring doc.

    The returned doc has exactly one feature (the detection), carrying the
    minted site_id and EPSG:4326 geometry.
    """
    geom_4326, centroid_4326, source_crs = _to_4326(
        fixture.geometry, fixture.centroid, fixture.crs
    )

    rec = registry.register(
        geometry=geom_4326,
        centroid=centroid_4326,
        source=fixture.source,
        source_ref=fixture.scene_ref,     # LS-001 stored as reference, NOT identity
        first_detection_time=fixture.acquisition_date,
        attributes={"source_crs": source_crs,
                    "detection_confidence": fixture.detection_confidence},
    )

    feature = {
        "site_id": rec.site_id,
        "detection_scene_ref": fixture.scene_ref,
        "geometry": geom_4326,
        "centroid": centroid_4326,
        "area_m2": float(fixture.area_m2),
        "detection_confidence": float(fixture.detection_confidence),
        "detection_confidence_is_calibrated": False,
        "source": fixture.source,
        "acquisition_date": fixture.acquisition_date,
        "model": fixture.model,
        "threshold": float(fixture.threshold),
        "crs": "EPSG:4326",
        # provenance (extra; allowed by additionalProperties)
        "source_crs": source_crs,
        "bbox": fixture.bbox,
    }

    doc = {
        "schema": "landslideguard.detection_monitoring/1.0",
        "generated_at": _utc_now_iso(),
        "scene_id": scene_id,
        "event_time_utc": fixture.acquisition_date,
        "features": [feature],
    }
    validate(doc, DETECTION_MONITORING_SCHEMA)
    return doc


__all__ = ["adapt_detection_to_monitoring"]
