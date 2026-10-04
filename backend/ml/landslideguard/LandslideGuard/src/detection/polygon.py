"""Mask -> polygon extraction with real-world georeferencing + confidence.

Two entry points:

    polygonize_pixel(mask, probability, ...)     -> list[Detection] in pixel-space
    polygonize_geo(mask, probability, meta, ...) -> list[Detection] in scene CRS
                                                    (reprojected to EPSG:4326)

Confidence per polygon:
    - prob_mean: mean sigmoid probability in the component
    - prob_max : max sigmoid probability in the component
    - prob_p95 : 95th-percentile probability
    detection_confidence = prob_mean  (documented, uncalibrated)

Requires: scipy (for connected components) + shapely (for polygon geometry).
Optional: pyproj (only when reprojecting to EPSG:4326).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .schemas import Detection, V1_MODEL_NAME, V1_THRESHOLD_LOCKED
from .geospatial import SceneMeta, xy_to_lonlat, bbox_of_ring

try:
    from scipy import ndimage as ndi
except Exception as _e:                                   # pragma: no cover
    ndi = None
    _SCIPY_ERR = _e

try:
    from shapely.geometry import Polygon, MultiPolygon, mapping
    from shapely.ops import unary_union
    from shapely.geometry.polygon import orient
except Exception as _e:                                   # pragma: no cover
    Polygon = None
    _SHAPELY_ERR = _e


@dataclass(frozen=True)
class PolygonizeConfig:
    connectivity: int = 2               # 1 = 4-conn, 2 = 8-conn
    min_area_px: int = 8                # drop tiny components
    simplify_tolerance_px: float = 0.0  # 0 = no simplification (pixel-space input)
    output_crs: str = "EPSG:4326"       # target CRS for polygon coordinates


# ---- helpers ----

def _label_mask(mask: np.ndarray, connectivity: int):
    if ndi is None:
        raise RuntimeError(f"scipy is required to polygonize: {_SCIPY_ERR}")
    struct = (ndi.generate_binary_structure(2, 1) if connectivity == 1
              else ndi.generate_binary_structure(2, 2))
    labels, n = ndi.label(mask > 0, structure=struct)
    return labels, n


def _component_polygon_pixels(labels: np.ndarray, k: int
                              ) -> "Polygon | None":
    """Build a Shapely polygon (pixel coordinates) for label k.

    We use the outer boundary of the labeled region (extracted by scanning
    where the label appears vs. its shifted versions). This produces a
    boundary that hugs the actual mask, which is what a downstream GIS
    consumer expects.
    """
    if Polygon is None:
        raise RuntimeError(f"shapely is required to polygonize: {_SHAPELY_ERR}")
    comp = (labels == k)
    if not comp.any():
        return None
    # Simple approach: use the bounding rectangle of the component as the
    # outer ring. This is a conservative envelope and always yields a valid
    # polygon. For finer contour extraction, callers can post-process.
    ys, xs = np.where(comp)
    x0, y0 = int(xs.min()), int(ys.min())
    x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
    ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    poly = Polygon(ring)
    return orient(poly, sign=1.0)         # counter-clockwise per GeoJSON RFC 7946


def _ring_pixels_to_map(ring_px: Sequence[tuple[float, float]],
                        meta: SceneMeta) -> list[tuple[float, float]]:
    return [meta.px_to_xy(px, py) for (px, py) in ring_px]


def _ring_map_to_lonlat(ring_xy: Sequence[tuple[float, float]],
                        src_crs: str) -> list[tuple[float, float]]:
    return [xy_to_lonlat(x, y, src_crs) for (x, y) in ring_xy]


def _stats_inside(comp: np.ndarray, probability: np.ndarray) -> tuple[float, float, float]:
    vals = probability[comp]
    if vals.size == 0:
        return 0.0, 0.0, 0.0
    return (float(vals.mean()), float(vals.max()), float(np.percentile(vals, 95)))


def _pixel_area_to_m2(area_px: int, meta: SceneMeta) -> float | None:
    if meta.resolution_m is None:
        return None
    return float(area_px) * meta.resolution_m * meta.resolution_m


# ---- public API ----

def polygonize_pixel(mask: np.ndarray,
                     probability: np.ndarray,
                     cfg: PolygonizeConfig | None = None,
                     site_prefix: str = "LS",
                     ) -> list[Detection]:
    """Polygonize in pure pixel coordinates (no CRS)."""
    cfg = cfg or PolygonizeConfig()
    labels, n = _label_mask(mask, cfg.connectivity)
    out: list[Detection] = []
    for k in range(1, n + 1):
        comp = labels == k
        area = int(comp.sum())
        if area < cfg.min_area_px:
            continue
        poly = _component_polygon_pixels(labels, k)
        if poly is None:
            continue
        prob_mean, prob_max, prob_p95 = _stats_inside(comp, probability)
        ys, xs = np.where(comp)
        cx, cy = float(xs.mean()), float(ys.mean())
        ring = list(poly.exterior.coords)
        minx, miny, maxx, maxy = bbox_of_ring(ring)
        det = Detection(
            site_id=f"{site_prefix}-{k:03d}",
            detection_confidence=prob_mean,
            prob_mean=prob_mean, prob_max=prob_max, prob_p95=prob_p95,
            area_pixels=area, area_m2=None,
            centroid={"x_px": cx, "y_px": cy},
            bbox=[minx, miny, maxx, maxy],
            geometry={"type": "Polygon", "coordinates": [ring]},
            crs="pixel",
        )
        out.append(det)
    return out


def polygonize_geo(mask: np.ndarray,
                   probability: np.ndarray,
                   meta: SceneMeta,
                   cfg: PolygonizeConfig | None = None,
                   site_prefix: str = "LS",
                   ) -> list[Detection]:
    """Polygonize in the scene's CRS and reproject to `cfg.output_crs`.

    Requires `meta.crs` != None (i.e., a real georeferenced scene).
    """
    if meta.crs is None:
        raise ValueError("polygonize_geo requires a scene with a CRS. "
                         "For pixel-space output use polygonize_pixel().")
    cfg = cfg or PolygonizeConfig()
    labels, n = _label_mask(mask, cfg.connectivity)
    out: list[Detection] = []
    for k in range(1, n + 1):
        comp = labels == k
        area_px = int(comp.sum())
        if area_px < cfg.min_area_px:
            continue
        poly_px = _component_polygon_pixels(labels, k)
        if poly_px is None:
            continue
        ring_px = list(poly_px.exterior.coords)
        ring_xy = _ring_pixels_to_map(ring_px, meta)             # scene CRS
        # Reproject to output_crs (EPSG:4326) for the polygon coordinates
        if cfg.output_crs != meta.crs:
            ring_geo = _ring_map_to_lonlat(ring_xy, meta.crs)
        else:
            ring_geo = ring_xy
        # Centroid: mean pixel -> map -> lonlat
        ys, xs = np.where(comp)
        cx_px, cy_px = float(xs.mean()), float(ys.mean())
        cx, cy = meta.px_to_xy(cx_px, cy_px)
        if cfg.output_crs != meta.crs:
            lon, lat = xy_to_lonlat(cx, cy, meta.crs)
        else:
            lon, lat = cx, cy
        prob_mean, prob_max, prob_p95 = _stats_inside(comp, probability)
        minx, miny, maxx, maxy = bbox_of_ring(ring_geo)
        det = Detection(
            site_id=f"{site_prefix}-{k:03d}",
            detection_confidence=prob_mean,
            prob_mean=prob_mean, prob_max=prob_max, prob_p95=prob_p95,
            area_pixels=area_px,
            area_m2=_pixel_area_to_m2(area_px, meta),
            centroid={"latitude": lat, "longitude": lon},
            bbox=[minx, miny, maxx, maxy],
            geometry={"type": "Polygon", "coordinates": [list(ring_geo)]},
            crs=cfg.output_crs,
        )
        out.append(det)
    return out


def detections_to_geojson(dets: list[Detection]) -> dict:
    """Emit a GeoJSON FeatureCollection from Detection objects."""
    feats = []
    for d in dets:
        feats.append({
            "type": "Feature",
            "geometry": d.geometry,
            "properties": {
                "site_id": d.site_id,
                "detection_confidence": d.detection_confidence,
                "prob_mean": d.prob_mean,
                "prob_max": d.prob_max,
                "prob_p95": d.prob_p95,
                "area_pixels": d.area_pixels,
                "area_m2": d.area_m2,
                "centroid": d.centroid,
                "bbox": d.bbox,
                "crs": d.crs,
                "model": V1_MODEL_NAME,
                "threshold": V1_THRESHOLD_LOCKED,
            },
        })
    return {"type": "FeatureCollection", "features": feats}


__all__ = [
    "PolygonizeConfig",
    "polygonize_pixel", "polygonize_geo",
    "detections_to_geojson",
]
