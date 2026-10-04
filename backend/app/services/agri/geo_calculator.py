from __future__ import annotations
import math
from typing import Dict, Any, List, Tuple
import numpy as np


def compute_ndvi(nir_band: np.ndarray, red_band: np.ndarray) -> np.ndarray:
    """
    Compute Normalized Difference Vegetation Index (NDVI) from calibrated Sentinel-2 bands.
    NDVI = (NIR - Red) / (NIR + Red)
    Valid range is [-1.0, 1.0].
    """
    nir = nir_band.astype(np.float32)
    red = red_band.astype(np.float32)
    denominator = nir + red
    # Avoid zero division
    zero_mask = denominator == 0
    ndvi = np.zeros_like(denominator)
    ndvi[~zero_mask] = (nir[~zero_mask] - red[~zero_mask]) / denominator[~zero_mask]
    return np.clip(ndvi, -1.0, 1.0)


def classify_ndvi_pixel(ndvi_val: float) -> str:
    """Classify NDVI value into vegetative vigor category."""
    if ndvi_val >= 0.50:
        return "healthy"
    elif ndvi_val >= 0.30:
        return "moderate"
    elif ndvi_val >= 0.15:
        return "stressed"
    else:
        return "critical"


def compute_polygon_geodesic_area_ha(coords: List[List[float]]) -> float:
    """
    Compute geodesic parcel area in hectares from WGS84 [lon, lat] coordinates.
    Uses spherical shoelace approximation calibrated for mid-latitudes (India 8°N-35°N).
    """
    if len(coords) < 3:
        return 0.0

    # Earth radius in meters
    R = 6378137.0
    area = 0.0
    n = len(coords)

    # Convert degrees to radians
    rad_coords = [(math.radians(p[0]), math.radians(p[1])) for p in coords]

    for i in range(n):
        j = (i + 1) % n
        lon1, lat1 = rad_coords[i]
        lon2, lat2 = rad_coords[j]
        area += (lon2 - lon1) * (2.0 + math.sin(lat1) + math.sin(lat2))

    area = abs(area * R * R / 2.0)
    # 1 hectare = 10,000 square meters
    return round(area / 10000.0, 2)


def compute_damage_delta(
    pre_ndvi: np.ndarray,
    post_ndvi: np.ndarray
) -> Dict[str, Any]:
    """
    Compute pre/post disaster vegetative difference and categorize severity.
    ΔNDVI = post_ndvi - pre_ndvi. A negative drop indicates crop destruction / submerged vegetation.
    """
    delta = post_ndvi.astype(np.float32) - pre_ndvi.astype(np.float32)
    severe_drop = delta <= -0.25
    moderate_drop = (delta > -0.25) & (delta <= -0.10)
    stable_or_better = delta > -0.10

    total_pixels = delta.size
    severe_pct = float(np.sum(severe_drop) / total_pixels * 100.0)
    moderate_pct = float(np.sum(moderate_drop) / total_pixels * 100.0)
    stable_pct = float(np.sum(stable_or_better) / total_pixels * 100.0)

    overall_severity = "HIGH" if severe_pct >= 20.0 else ("MODERATE" if severe_pct + moderate_pct >= 30.0 else "LOW")

    return {
        "mean_pre_ndvi": float(np.mean(pre_ndvi)),
        "mean_post_ndvi": float(np.mean(post_ndvi)),
        "mean_delta_ndvi": float(np.mean(delta)),
        "severe_damage_pct": round(severe_pct, 1),
        "moderate_damage_pct": round(moderate_pct, 1),
        "stable_pct": round(stable_pct, 1),
        "severity": overall_severity
    }
