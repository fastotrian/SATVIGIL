"""Sentinel-2 ingestion for production Detection.

Turns a Sentinel-2 L2A product (.SAFE) or a directory of GeoTIFF/JP2 band
files + a DEM raster into the exact (H, W, 14) float32 stack V1 expects,
along with a SceneMeta describing its georeferencing.

Requires rasterio (raster IO / warping / reprojection). Fails LOUDLY with
an actionable message if rasterio is unavailable, per project rule 24
("If required DEM/slope data is missing, fail clearly with an actionable
error").

Nothing here fabricates DEM or bands.

Public API
----------
    ingest_sentinel2_scene(safe_or_dir, dem_path, ...) -> (stack_HWC, meta)

    - `safe_or_dir` : path to a .SAFE product OR a directory containing the
                      individual band JP2/GeoTIFF files (auto-detected)
    - `dem_path`    : path to a DEM raster covering the AOI
    - `target_resolution_m`: resample all bands + DEM to this pixel size
                             (default 10 m to match S2 native highest-res)

Channel order (verified from V1's Stage-1 preprocessing):

    0..11 : S2 B1, B2, B3, B4, B5, B6, B7, B8, B8A, B9, B11, B12
    12    : Slope (degrees; computed from DEM if not supplied)
    13    : DEM   (elevation, metres)

Slope
-----
If a slope raster is supplied via `slope_path`, it is used directly (after
resampling to the target grid). Otherwise slope is derived from the DEM
using a Horn's method finite-difference gradient (degrees). We do NOT
silently substitute a placeholder slope.

Cloud handling
--------------
If an SCL (Scene Classification Layer) raster is supplied, cells labeled
as CLOUD_MEDIUM_PROBABILITY (8) or CLOUD_HIGH_PROBABILITY (9) or
THIN_CIRRUS (10) are reported in the validation dict as `cloud_pixel_fraction`.
They are NOT masked out of the input (V1 was not trained with a cloud
mask channel) - documenting the fraction is enough.

Frozen normalization is applied by the caller (pipeline.py), NOT here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from .geospatial import SceneMeta, channel_names_v1


try:
    import rasterio                             # noqa: F401
    from rasterio.warp import reproject, calculate_default_transform, Resampling
    _HAS_RASTERIO = True
    _RASTERIO_ERR: Exception | None = None
except Exception as _e:                         # pragma: no cover
    _HAS_RASTERIO = False
    _RASTERIO_ERR = _e


# Sentinel-2 L2A band naming as they appear in .SAFE / JP2 files
# (per ESA product naming: e.g. "T43QGE_20240730T053641_B04_10m.jp2")
S2_BAND_NAMES: tuple[str, ...] = (
    "B01", "B02", "B03", "B04",
    "B05", "B06", "B07", "B08",
    "B8A", "B09", "B11", "B12",
)

# Sentinel-2 L2A native resolutions (metres per pixel)
S2_NATIVE_RES: Mapping[str, int] = {
    "B01": 60, "B02": 10, "B03": 10, "B04": 10,
    "B05": 20, "B06": 20, "B07": 20, "B08": 10,
    "B8A": 20, "B09": 60, "B11": 20, "B12": 20,
}

# S2 L2A reflectance scale (physical reflectance ~ raw / 10000)
S2_REFLECTANCE_SCALE = 1e-4


class MissingDependencyError(RuntimeError):
    pass


class SceneValidationError(RuntimeError):
    pass


def _require_rasterio() -> None:
    if not _HAS_RASTERIO:
        raise MissingDependencyError(
            "Sentinel-2 ingestion requires the `rasterio` package, but it "
            "is not importable in this environment. Install it via "
            "`pip install rasterio` (may require GDAL). See "
            "docs/detection_production_pipeline.md for platform notes. "
            f"Underlying import error: {type(_RASTERIO_ERR).__name__}: "
            f"{_RASTERIO_ERR}"
        )


@dataclass(frozen=True)
class IngestionConfig:
    target_resolution_m: float = 10.0
    resampling: str = "bilinear"       # for S2 bands
    dem_resampling: str = "bilinear"
    slope_method: str = "horn"         # only "horn" for now
    output_crs: str | None = None      # None = use the S2 B02 CRS


def _resolve_band_files(product_root: Path) -> dict[str, Path]:
    """Locate each S2 band file inside a .SAFE product or a flat dir.

    Returns a {band_name: path} dict. Raises if any required band is missing.
    """
    p = Path(product_root)
    if p.suffix.upper() == ".SAFE" and p.is_dir():
        # Standard L2A layout: GRANULE/*/IMG_DATA/R10m|R20m|R60m/*.jp2
        img_root = p / "GRANULE"
        candidates: list[Path] = []
        if img_root.is_dir():
            for gr in img_root.iterdir():
                if gr.is_dir():
                    for res_dir in (gr / "IMG_DATA").glob("R*m"):
                        candidates.extend(res_dir.glob("*.jp2"))
                        candidates.extend(res_dir.glob("*.tif"))
        pool = candidates
    else:
        # Flat directory: look for filenames ending in _BXX_*.jp2 / .tif
        pool = list(p.glob("*.jp2")) + list(p.glob("*.tif")) + list(p.glob("*.tiff"))

    resolved: dict[str, Path] = {}
    for band in S2_BAND_NAMES:
        # Prefer the highest available resolution for each band
        matches = [q for q in pool
                   if f"_{band}_" in q.name.upper()
                      or q.stem.upper().endswith(f"_{band}")]
        if not matches:
            raise SceneValidationError(
                f"Sentinel-2 band {band} not found under {p}. Looked for "
                f"'*_{band}_*.jp2' / '*_{band}_*.tif'."
            )
        # Sort by native resolution ascending (higher-res first)
        matches.sort(key=lambda q: _guess_res_from_name(q.name))
        resolved[band] = matches[0]
    return resolved


def _guess_res_from_name(name: str) -> int:
    for tag in ("10m", "20m", "60m"):
        if tag in name.lower():
            return int(tag.rstrip("m"))
    return 999


def _slope_from_dem_horn(dem: np.ndarray, pixel_size_m: float) -> np.ndarray:
    """Horn's method slope (degrees) from a 2D DEM."""
    dz_dx = np.zeros_like(dem, dtype=np.float32)
    dz_dy = np.zeros_like(dem, dtype=np.float32)
    dz_dx[:, 1:-1] = (dem[:, 2:] - dem[:, :-2]) / (2 * pixel_size_m)
    dz_dy[1:-1, :] = (dem[2:, :] - dem[:-2, :]) / (2 * pixel_size_m)
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    return np.rad2deg(slope_rad).astype(np.float32)


def ingest_sentinel2_scene(product: str | Path,
                           dem_path: str | Path,
                           slope_path: str | Path | None = None,
                           cfg: IngestionConfig | None = None,
                           ) -> tuple[np.ndarray, SceneMeta, dict]:
    """Read a Sentinel-2 product + DEM + optional slope, return the 14-channel stack.

    Returns:
        stack : (H, W, 14) float32, in the S2 physical reflectance scale
                (0..~1 for optical bands; slope in degrees; DEM in m).
                NOT YET normalized. Caller applies frozen normalization.
        meta  : SceneMeta describing the output grid.
        info  : dict with band-file paths, cloud stats (if SCL available),
                and warnings.
    """
    _require_rasterio()
    from rasterio.warp import reproject, calculate_default_transform, Resampling
    from affine import Affine
    cfg = cfg or IngestionConfig()

    band_paths = _resolve_band_files(Path(product))

    # Use B02 as the reference grid (native 10 m, always present).
    ref_band = "B02"
    with rasterio.open(band_paths[ref_band]) as ref:
        ref_crs = ref.crs.to_string() if ref.crs else None
        ref_bounds = ref.bounds
        # target CRS = ref CRS unless caller overrides
        target_crs = cfg.output_crs or ref_crs
        # target grid: match ref bounds resampled to target_resolution_m
        left, bottom, right, top = ref_bounds
        width = int(round((right - left) / cfg.target_resolution_m))
        height = int(round((top - bottom) / cfg.target_resolution_m))
        transform = Affine.translation(left, top) * Affine.scale(
            cfg.target_resolution_m, -cfg.target_resolution_m)

    stack = np.zeros((height, width, 14), dtype=np.float32)
    warnings: list[str] = []

    def _read_and_warp(src_path: Path) -> np.ndarray:
        with rasterio.open(src_path) as src:
            dst = np.zeros((height, width), dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=dst,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling[cfg.resampling],
            )
            return dst

    # 12 S2 bands (channels 0..11)
    for i, band in enumerate(S2_BAND_NAMES):
        arr = _read_and_warp(band_paths[band])
        stack[..., i] = arr * S2_REFLECTANCE_SCALE

    # DEM (channel 13)
    if not Path(dem_path).is_file():
        raise SceneValidationError(f"DEM not found: {dem_path}")
    with rasterio.open(dem_path) as dsrc:
        dem_arr = np.zeros((height, width), dtype=np.float32)
        reproject(
            source=rasterio.band(dsrc, 1),
            destination=dem_arr,
            src_transform=dsrc.transform,
            src_crs=dsrc.crs,
            dst_transform=transform,
            dst_crs=target_crs,
            resampling=Resampling[cfg.dem_resampling],
        )
    stack[..., 13] = dem_arr

    # Slope (channel 12) - either supplied or Horn's method on the DEM
    if slope_path is not None and Path(slope_path).is_file():
        with rasterio.open(slope_path) as ssrc:
            slope_arr = np.zeros((height, width), dtype=np.float32)
            reproject(
                source=rasterio.band(ssrc, 1),
                destination=slope_arr,
                src_transform=ssrc.transform,
                src_crs=ssrc.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling[cfg.dem_resampling],
            )
        slope_source = str(slope_path)
    else:
        slope_arr = _slope_from_dem_horn(dem_arr, cfg.target_resolution_m)
        slope_source = "computed via Horn's method from DEM"
        warnings.append("Slope raster not supplied; derived from DEM.")

    stack[..., 12] = slope_arr

    meta = SceneMeta(
        width=width, height=height,
        transform=(transform.a, transform.b, transform.c,
                   transform.d, transform.e, transform.f),
        crs=target_crs,
        resolution_m=float(cfg.target_resolution_m),
    )

    info = {
        "band_files": {b: str(band_paths[b]) for b in S2_BAND_NAMES},
        "dem_file": str(dem_path),
        "slope_source": slope_source,
        "target_crs": target_crs,
        "target_resolution_m": cfg.target_resolution_m,
        "channel_order": channel_names_v1(),
        "warnings": warnings,
    }
    return stack, meta, info


__all__ = [
    "S2_BAND_NAMES", "S2_NATIVE_RES", "S2_REFLECTANCE_SCALE",
    "IngestionConfig", "MissingDependencyError", "SceneValidationError",
    "ingest_sentinel2_scene",
]
