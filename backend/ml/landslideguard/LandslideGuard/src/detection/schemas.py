"""Schemas + dataclasses for production Detection outputs.

Only defines shapes: no inference, no I/O side effects. Downstream modules
build instances and serialize them with `to_dict()`.

The two consumer contracts:

    DetectionResult   -> outputs/detection/inference/<scene_id>_result.json
    MonitoringHandoff -> outputs/detection/monitoring_handoff/<scene_id>_monitoring_handoff.json

The Monitoring team consumes the HandoffFeature list (one per detection).
Every geometry is in EPSG:4326 (lat/lon) unless `crs_authority` says
otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


V1_MODEL_NAME = "V1"
V1_THRESHOLD_LOCKED = 0.60


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SourceInfo:
    type: str                # "h5" | "sentinel-2"
    product: str | None = None
    acquisition_date: str | None = None
    cloud_coverage: float | None = None
    granule: str | None = None


@dataclass
class InputInfo:
    channels: int = 14
    tile_size: int = 128
    stride: int = 128
    crs: str | None = None
    resolution_m: float | None = None
    width_px: int | None = None
    height_px: int | None = None
    dem_source: str | None = None
    slope_method: str | None = None


@dataclass
class Detection:
    """One landslide polygon."""
    site_id: str
    detection_confidence: float          # NOT a calibrated occurrence probability
    prob_mean: float
    prob_max: float
    prob_p95: float
    area_pixels: int
    area_m2: float | None                # None when working purely in pixel-space (h5 patches)
    centroid: dict                        # {"latitude": .., "longitude": ..} OR {"x_px":, "y_px":}
    bbox: list[float]                    # [minx, miny, maxx, maxy] in polygon CRS
    geometry: dict                        # GeoJSON geometry (Polygon/MultiPolygon)
    crs: str                              # e.g. "EPSG:32643" or "pixel"


@dataclass
class DetectionResult:
    run_id: str
    scene_id: str
    model: str = V1_MODEL_NAME
    checkpoint: str = ""
    threshold: float = V1_THRESHOLD_LOCKED
    device: str = "cpu"
    generated_at: str = field(default_factory=utc_now_iso)
    source: SourceInfo = field(default_factory=lambda: SourceInfo(type="h5"))
    input: InputInfo = field(default_factory=InputInfo)
    inference_seconds: float | None = None
    detections: list[Detection] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    metrics_against_gt: dict[str, Any] | None = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HandoffFeature:
    """One AOI to send to Monitoring."""
    site_id: str
    geometry: dict                # GeoJSON polygon (real-world, EPSG:4326 preferred)
    centroid: dict                # {"latitude", "longitude"}
    area_m2: float
    detection_confidence: float
    source: str                   # "Sentinel-2" | "Landslide4Sense"
    acquisition_date: str | None
    model: str = V1_MODEL_NAME
    threshold: float = V1_THRESHOLD_LOCKED
    crs: str = "EPSG:4326"


@dataclass
class MonitoringHandoff:
    scene_id: str
    generated_at: str = field(default_factory=utc_now_iso)
    features: list[HandoffFeature] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---- Input validation report structure (Phase 8) ----

def build_validation_dict(*,
                          source: str,
                          crs: str | None,
                          width: int | None,
                          height: int | None,
                          resolution: float | None,
                          channels: int,
                          channel_order: list[str],
                          dem_available: bool,
                          slope_available: bool,
                          nan_count: int,
                          inf_count: int,
                          warnings: list[str] | None = None) -> dict:
    valid = (channels == 14
             and (nan_count == 0)
             and (inf_count == 0)
             and (width or 0) > 0
             and (height or 0) > 0)
    return {
        "source": source,
        "crs": crs,
        "width": width,
        "height": height,
        "resolution": resolution,
        "channels": channels,
        "channel_order": channel_order,
        "dem_available": dem_available,
        "slope_available": slope_available,
        "nan_count": int(nan_count),
        "inf_count": int(inf_count),
        "warnings": warnings or [],
        "valid": bool(valid),
    }


__all__ = [
    "V1_MODEL_NAME", "V1_THRESHOLD_LOCKED",
    "SourceInfo", "InputInfo",
    "Detection", "DetectionResult",
    "HandoffFeature", "MonitoringHandoff",
    "build_validation_dict", "utc_now_iso",
]
