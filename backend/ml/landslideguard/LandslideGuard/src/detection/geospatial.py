"""Geospatial primitives for production Detection.

Kept minimal on purpose: this file must load and be importable even if
`rasterio` is absent. Rasterio is only needed by `sentinel2.py`.

Provides:
    SceneMeta          - CRS + affine transform + shape (single source of truth for
                         a scene's georeferencing)
    px_to_xy           - pixel indices -> map coords in the scene's CRS
    xy_to_lonlat       - reproject map coords -> WGS84 lon/lat
    channel_names_v1() - canonical 14-channel names (S2 B1..B12 + Slope + DEM)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

try:
    import pyproj                       # noqa: F401
    _HAS_PYPROJ = True
except Exception:
    _HAS_PYPROJ = False


# The 14 V1 channels, in the order the model expects.
V1_CHANNEL_NAMES: tuple[str, ...] = (
    "S2_B1",  "S2_B2",  "S2_B3",  "S2_B4",
    "S2_B5",  "S2_B6",  "S2_B7",  "S2_B8",
    "S2_B8A", "S2_B9",  "S2_B11", "S2_B12",
    "Slope",  "DEM",
)


def channel_names_v1() -> list[str]:
    return list(V1_CHANNEL_NAMES)


@dataclass(frozen=True)
class SceneMeta:
    """A scene's georeferencing.

    `transform` is a 6-tuple (a, b, c, d, e, f) in the same order as GDAL's
    `GetGeoTransform`, i.e. map_x = a*px + b*py + c, map_y = d*px + e*py + f.
    For a north-up image with square pixels this reduces to
        (pixel_size, 0, x_origin, 0, -pixel_size, y_origin).

    If `crs` is None the scene has no georeference (e.g., Landslide4Sense H5).
    """
    width: int
    height: int
    transform: tuple[float, float, float, float, float, float]
    crs: str | None                     # e.g. "EPSG:32643"; None for pixel-space
    resolution_m: float | None = None   # nominal pixel size in metres

    def px_to_xy(self, col_px: float, row_px: float) -> tuple[float, float]:
        a, b, c, d, e, f = self.transform
        x = a * col_px + b * row_px + c
        y = d * col_px + e * row_px + f
        return float(x), float(y)

    @classmethod
    def pixel_only(cls, width: int, height: int) -> "SceneMeta":
        """A scene with no georeference (transform is identity, CRS None)."""
        return cls(width=width, height=height,
                   transform=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0),
                   crs=None, resolution_m=None)


def xy_to_lonlat(x: float, y: float, src_crs: str,
                 dst_crs: str = "EPSG:4326") -> tuple[float, float]:
    """Reproject a single (x, y) from src_crs to WGS84 lon/lat.

    Requires pyproj. If unavailable, raises RuntimeError.
    """
    if not _HAS_PYPROJ:
        raise RuntimeError("pyproj is required for CRS reprojection but was "
                           "not importable; see requirements.txt")
    import pyproj
    tr = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    lon, lat = tr.transform(x, y)
    return float(lon), float(lat)


def bbox_of_ring(ring: Sequence[Tuple[float, float]]
                 ) -> tuple[float, float, float, float]:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return (min(xs), min(ys), max(xs), max(ys))


__all__ = [
    "V1_CHANNEL_NAMES", "channel_names_v1",
    "SceneMeta", "xy_to_lonlat", "bbox_of_ring",
]
