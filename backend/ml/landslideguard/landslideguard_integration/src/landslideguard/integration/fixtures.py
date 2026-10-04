"""Controlled/synthetic fixtures for the Phase-3 end-to-end integration.

These are NOT real observations. Every fixture is stamped
`source = "controlled_test_fixture"`. The Detection fixture is not a real
Sentinel-2 detection; the Monitoring history is not newly processed
Sentinel-1/InSAR data.

The Detection fixture is centred on a real coordinate/date
(POS_35: 34.0935, 74.9112, 2007-03-12) purely so the frozen Phase-2 rainfall
and terrain reference providers can resolve features for it locally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

CONTROLLED_SOURCE = "controlled_test_fixture"

# Real coordinate/date so local IMERG-reference + SRTM providers resolve.
_FIXTURE_LAT = 34.0935
_FIXTURE_LON = 74.9112
_FIXTURE_DATE = "2007-03-12"
_HALF = 0.01  # ~1 km half-box in degrees


def _square_polygon(lat: float, lon: float, half: float = _HALF) -> dict:
    """A small axis-aligned square polygon (GeoJSON, [lon, lat] order)."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - half, lat - half],
            [lon + half, lat - half],
            [lon + half, lat + half],
            [lon - half, lat + half],
            [lon - half, lat - half],
        ]],
    }


@dataclass
class DetectionFixture:
    """Mirrors Detection's HandoffFeature/Detection contract fields."""
    scene_ref: str                 # scene-local label, e.g. "LS-001" (NOT a cross-module id)
    geometry: dict                 # GeoJSON polygon
    centroid: dict                 # {"latitude","longitude"}
    area_m2: float
    bbox: list                     # [minlon, minlat, maxlon, maxlat]
    detection_confidence: float
    crs: str
    source: str = CONTROLLED_SOURCE
    acquisition_date: str = _FIXTURE_DATE
    model: str = "detection_v1"
    threshold: float = 0.60


def controlled_detection_fixture(crs: str = "EPSG:4326") -> DetectionFixture:
    """A controlled detection near POS_35.

    crs="EPSG:4326"  -> geometry already in lat/lon (passthrough in the adapter)
    crs="EPSG:32643" -> geometry reprojected into UTM 43N, to exercise the
                        adapter's real CRS transformation back to 4326.
    """
    lat, lon = _FIXTURE_LAT, _FIXTURE_LON
    geom_4326 = _square_polygon(lat, lon)
    centroid = {"latitude": lat, "longitude": lon}
    bbox_4326 = [lon - _HALF, lat - _HALF, lon + _HALF, lat + _HALF]

    if crs == "EPSG:4326":
        return DetectionFixture(
            scene_ref="LS-001", geometry=geom_4326, centroid=centroid,
            area_m2=4.0e6, bbox=bbox_4326, detection_confidence=0.9209731221,
            crs="EPSG:4326",
        )

    # Reproject the polygon + centroid into the requested projected CRS so the
    # fixture genuinely carries non-4326 coordinates.
    import pyproj
    tr = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    ring = [list(tr.transform(x, y)) for x, y in geom_4326["coordinates"][0]]
    geom_proj = {"type": "Polygon", "coordinates": [ring]}
    cx, cy = tr.transform(lon, lat)
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return DetectionFixture(
        scene_ref="LS-001", geometry=geom_proj,
        centroid={"x": cx, "y": cy},   # projected centroid (no lat/lon yet)
        area_m2=4.0e6, bbox=[min(xs), min(ys), max(xs), max(ys)],
        detection_confidence=0.9209731221, crs=crs,
    )


# ---- Controlled Monitoring history (12 raw displacement observations) ----
# Plausible declining-displacement window in the range of the verified V2 test
# set. NOT real InSAR. Deterministic.
CONTROLLED_MONITORING_HISTORY = [
    -45.6, -47.1, -48.9, -50.2, -51.8, -53.0,
    -54.7, -56.1, -57.9, -59.2, -61.0, -62.4,
]

CONTROLLED_MONITORING_META = {
    "source": CONTROLLED_SOURCE,
    "note": "Synthetic displacement window; not processed Sentinel-1/InSAR data.",
    "time_steps": list(range(40, 52)),
}


__all__ = [
    "CONTROLLED_SOURCE",
    "DetectionFixture",
    "controlled_detection_fixture",
    "CONTROLLED_MONITORING_HISTORY",
    "CONTROLLED_MONITORING_META",
]
