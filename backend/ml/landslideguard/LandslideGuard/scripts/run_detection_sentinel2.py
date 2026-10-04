"""Run V1 detection on a full Sentinel-2 L2A scene.

Usage:
    python scripts/run_detection_sentinel2.py \
        --input <path/to/S2A_MSIL2A_*.SAFE-or-flat-dir> \
        --dem <path/to/dem.tif> \
        [--slope <path/to/slope.tif>] \
        [--checkpoint checkpoints/detection/best_model.pth] \
        [--output-dir outputs/detection/inference] \
        [--acquisition-date 2024-07-30]

Requires:
    rasterio (raster IO)
    pyproj    (CRS reprojection for polygon output)
    shapely   (polygon geometry)
    scipy     (connected components + slope)

If rasterio is not installed the script fails cleanly with an actionable
message. Nothing is fabricated.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import torch

from src.detection.pipeline import (
    run_sentinel2_scene, DEFAULT_V1_CKPT, DEFAULT_NORM,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True,
                    help="Path to a Sentinel-2 L2A .SAFE product OR a flat "
                         "directory of Sentinel-2 band JP2/TIFF files")
    ap.add_argument("--dem", "-d", required=True,
                    help="Path to a DEM raster covering the scene")
    ap.add_argument("--slope", default=None,
                    help="Optional slope raster; if omitted, slope is derived "
                         "from the DEM via Horn's method")
    ap.add_argument("--checkpoint", default=str(DEFAULT_V1_CKPT))
    ap.add_argument("--normalization", default=str(DEFAULT_NORM))
    ap.add_argument("--output-dir",
                    default=str(REPO / "outputs/detection/inference"))
    ap.add_argument("--acquisition-date", default=None,
                    help="ISO date of the S2 acquisition (used in the "
                         "monitoring handoff)")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    result = run_sentinel2_scene(
        args.input, dem_path=args.dem, slope_path=args.slope,
        checkpoint=args.checkpoint, norm_stats_path=args.normalization,
        output_dir=args.output_dir, device=device,
        acquisition_date=args.acquisition_date,
    )
    print(f"[{result.scene_id}] detections={len(result.detections)} "
          f"device={result.device} inference_s={result.inference_seconds:.2f}")
    for d in result.detections[:10]:
        print(f"  {d.site_id}  area_m2={d.area_m2:.0f}  "
              f"conf={d.detection_confidence:.3f}  "
              f"centroid=({d.centroid.get('latitude', '?')}, "
              f"{d.centroid.get('longitude', '?')})")
    if len(result.detections) > 10:
        print(f"  ... {len(result.detections) - 10} more")


if __name__ == "__main__":
    main()
