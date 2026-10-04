"""High-level production Detection pipeline.

Two entry points:

    run_h5_regression(...)      : Landslide4Sense H5 patch -> DetectionResult
    run_sentinel2_scene(...)    : Sentinel-2 product      -> DetectionResult

Both:
    1. Load V1 (`checkpoints/detection/best_model.pth`)
    2. Load train-only normalization statistics
    3. Build the (H, W, 14) stack
    4. Normalize (frozen z-score)
    5. Run tiled inference (128x128, model-locked)
    6. Threshold at 0.60 (LOCKED)
    7. Postprocess (min_area, hole-fill)
    8. Polygonize (pixel- or geo-coords)
    9. Emit DetectionResult JSON + GeoJSON + MonitoringHandoff JSON
   10. Optionally save GeoTIFF (only when rasterio is available AND we have a
       real georeferenced scene)

Never modifies V1 weights, never retrains, never re-tunes the threshold.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .model import UNet
from .preprocessing import (
    NormalizationStats, sanitize, normalize, read_image, read_mask,
    N_CHANNELS, PATCH_H, PATCH_W,
)
from .postprocessing import PostprocessingConfig, apply as apply_postproc
from .tiled_inference import TilingConfig, run_tiled_inference
from .polygon import (
    PolygonizeConfig, polygonize_pixel, polygonize_geo,
    detections_to_geojson,
)
from .geospatial import SceneMeta, channel_names_v1
from .schemas import (
    V1_MODEL_NAME, V1_THRESHOLD_LOCKED,
    Detection, DetectionResult, SourceInfo, InputInfo,
    HandoffFeature, MonitoringHandoff, build_validation_dict,
)


REPO = Path(__file__).resolve().parents[2]
DEFAULT_V1_CKPT = REPO / "checkpoints" / "detection" / "best_model.pth"
DEFAULT_NORM = REPO / "outputs/detection/data_verification/normalization_statistics.json"


# -------------------------------- utilities --------------------------------

def _pick_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_v1(checkpoint: str | Path, device: torch.device) -> torch.nn.Module:
    payload = torch.load(str(checkpoint), map_location=device, weights_only=False)
    sd = payload["model"] if isinstance(payload, dict) and "model" in payload else payload
    model = UNet(in_channels=14, out_channels=1, base_features=16)
    missing, unexpected = model.load_state_dict(sd, strict=True)
    if missing or unexpected:
        raise RuntimeError(f"V1 checkpoint mismatch: missing={missing} "
                           f"unexpected={unexpected}")
    return model.to(device).eval()


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def _write_json(path: Path, obj: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path


def _try_write_geotiff(path: Path, arr: np.ndarray, meta: SceneMeta,
                       dtype: str) -> Path | None:
    """Write a GeoTIFF when rasterio is available. Returns None otherwise."""
    try:
        import rasterio
        from affine import Affine
    except Exception:
        return None
    a, b, c, d, e, f = meta.transform
    transform = Affine(a, b, c, d, e, f)
    profile = {
        "driver": "GTiff",
        "height": arr.shape[0],
        "width": arr.shape[1],
        "count": 1,
        "dtype": dtype,
        "crs": meta.crs,
        "transform": transform,
        "compress": "lzw",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(arr.astype(dtype), 1)
    return path


def _handoff_from_detections(scene_id: str,
                             dets: list[Detection],
                             source: str,
                             acquisition_date: str | None,
                             ) -> MonitoringHandoff:
    feats = []
    for d in dets:
        if d.area_m2 is None:
            # H5 patch: skip handoff (no real-world coords).
            continue
        feats.append(HandoffFeature(
            site_id=d.site_id,
            geometry=d.geometry,
            centroid=d.centroid,
            area_m2=d.area_m2,
            detection_confidence=d.detection_confidence,
            source=source,
            acquisition_date=acquisition_date,
            crs=d.crs,
        ))
    return MonitoringHandoff(scene_id=scene_id, features=feats)


# ------------------------------ H5 regression ------------------------------

def run_h5_regression(h5_path: str | Path,
                      *,
                      checkpoint: str | Path = DEFAULT_V1_CKPT,
                      norm_stats_path: str | Path = DEFAULT_NORM,
                      output_dir: str | Path = REPO / "outputs/detection/inference",
                      postproc: PostprocessingConfig | None = None,
                      polygonize_cfg: PolygonizeConfig | None = None,
                      device: torch.device | None = None,
                      gt_mask_path: str | Path | None = None,
                      ) -> DetectionResult:
    """Run V1 on one Landslide4Sense H5 patch. Deterministic, no training."""
    h5_path = Path(h5_path)
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    device = device or _pick_device()

    stats = NormalizationStats.from_json(norm_stats_path)
    model = _load_v1(checkpoint, device)

    img_hwc = read_image(h5_path)                              # (128,128,14)
    x = normalize(sanitize(img_hwc.astype(np.float32)), stats)

    # For 128x128 input we still go through tiled_inference (single tile,
    # exercises the same code path).
    t0 = time.time()
    prob = run_tiled_inference(model, x, device=device,
                               cfg=TilingConfig(tile=PATCH_H, stride=PATCH_H,
                                                batch_size=1, use_amp=False))
    infer_s = time.time() - t0

    mask_raw = (prob >= V1_THRESHOLD_LOCKED).astype(np.uint8)
    pp = postproc or PostprocessingConfig(threshold=V1_THRESHOLD_LOCKED,
                                          min_area=8, max_hole=4)
    mask_clean = apply_postproc(prob, pp)

    # Polygonize in pixel coords (H5 patch has no CRS)
    dets = polygonize_pixel(mask_clean, prob,
                            cfg=polygonize_cfg or PolygonizeConfig())

    # Optional GT metrics
    metrics = None
    if gt_mask_path is None:
        # Try to find a companion mask file
        for cand in [h5_path.with_name(h5_path.stem + "_mask.h5"),
                     h5_path.parent.parent / "mask" / h5_path.name.replace("image_", "mask_")]:
            if cand.is_file():
                gt_mask_path = cand
                break
    if gt_mask_path is not None:
        gt = read_mask(gt_mask_path)
        tp = int(((mask_clean == 1) & (gt == 1)).sum())
        fp = int(((mask_clean == 1) & (gt == 0)).sum())
        fn = int(((mask_clean == 0) & (gt == 1)).sum())
        tn = int(((mask_clean == 0) & (gt == 0)).sum())
        dice = (2 * tp) / (2 * tp + fp + fn) if (2 * tp + fp + fn) else float("nan")
        iou = tp / (tp + fp + fn) if (tp + fp + fn) else float("nan")
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        rec = tp / (tp + fn) if (tp + fn) else float("nan")
        metrics = {"gt_mask": str(gt_mask_path),
                   "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                   "dice": dice, "iou": iou,
                   "precision": prec, "recall": rec,
                   "threshold": V1_THRESHOLD_LOCKED}

    validation = build_validation_dict(
        source=str(h5_path),
        crs=None, width=PATCH_W, height=PATCH_H, resolution=None,
        channels=N_CHANNELS, channel_order=channel_names_v1(),
        dem_available=True, slope_available=True,
        nan_count=int(np.isnan(img_hwc).sum()),
        inf_count=int(np.isinf(img_hwc).sum()),
    )

    scene_id = h5_path.stem
    result = DetectionResult(
        run_id=_new_run_id(), scene_id=scene_id,
        checkpoint=str(checkpoint),
        device=str(device),
        source=SourceInfo(type="h5", product=str(h5_path)),
        input=InputInfo(channels=14, tile_size=PATCH_H, stride=PATCH_H,
                        width_px=PATCH_W, height_px=PATCH_H),
        inference_seconds=infer_s,
        detections=dets,
        validation=validation,
        metrics_against_gt=metrics,
        limitations=[
            "Landslide4Sense HDF5 patches carry no CRS/affine transform; "
            "polygon coordinates are pixel-space, not geographic.",
            "Detection confidence is the mean sigmoid probability inside the "
            "polygon (uncalibrated).",
        ],
    )

    # Persist artifacts
    _write_json(output_dir / f"{scene_id}_result.json", result.to_dict())
    _write_json(output_dir / f"{scene_id}_validation.json", validation)
    prob_dir = REPO / "outputs/detection/probability_maps"
    mask_dir = REPO / "outputs/detection/masks"
    poly_dir = REPO / "outputs/detection/polygons"
    prob_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    poly_dir.mkdir(parents=True, exist_ok=True)
    np.save(prob_dir / f"{scene_id}_probability.npy", prob)
    np.save(mask_dir / f"{scene_id}_mask_raw.npy", mask_raw)
    np.save(mask_dir / f"{scene_id}_mask_clean.npy", mask_clean)
    _write_json(poly_dir / f"{scene_id}_landslides.geojson",
                detections_to_geojson(dets))
    return result


# ---------------------------- Sentinel-2 pipeline --------------------------

def run_sentinel2_scene(product: str | Path,
                        dem_path: str | Path,
                        *,
                        slope_path: str | Path | None = None,
                        checkpoint: str | Path = DEFAULT_V1_CKPT,
                        norm_stats_path: str | Path = DEFAULT_NORM,
                        output_dir: str | Path = REPO / "outputs/detection/inference",
                        postproc: PostprocessingConfig | None = None,
                        polygonize_cfg: PolygonizeConfig | None = None,
                        tiling: TilingConfig | None = None,
                        device: torch.device | None = None,
                        acquisition_date: str | None = None,
                        ) -> DetectionResult:
    """Full-scene V1 inference on a Sentinel-2 L2A product.

    Fails LOUDLY with an actionable error if rasterio (needed for raster
    IO) or the DEM raster is unavailable. Nothing is fabricated.
    """
    from .sentinel2 import ingest_sentinel2_scene, IngestionConfig

    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    device = device or _pick_device()
    stats = NormalizationStats.from_json(norm_stats_path)
    model = _load_v1(checkpoint, device)

    stack, meta, info = ingest_sentinel2_scene(product, dem_path,
                                               slope_path=slope_path,
                                               cfg=IngestionConfig())
    # Normalize (frozen)
    x = normalize(sanitize(stack.astype(np.float32)), stats)

    # Full-scene tiled inference
    t0 = time.time()
    prob = run_tiled_inference(model, x, device=device,
                               cfg=tiling or TilingConfig(tile=PATCH_H,
                                                          stride=PATCH_H,
                                                          batch_size=8,
                                                          use_amp=True))
    infer_s = time.time() - t0

    mask_raw = (prob >= V1_THRESHOLD_LOCKED).astype(np.uint8)
    pp = postproc or PostprocessingConfig(threshold=V1_THRESHOLD_LOCKED,
                                          min_area=32, max_hole=8)
    mask_clean = apply_postproc(prob, pp)

    dets = polygonize_geo(mask_clean, prob, meta,
                          cfg=polygonize_cfg or PolygonizeConfig())

    validation = build_validation_dict(
        source=str(product),
        crs=meta.crs, width=meta.width, height=meta.height,
        resolution=meta.resolution_m,
        channels=14, channel_order=channel_names_v1(),
        dem_available=True, slope_available=True,
        nan_count=int(np.isnan(stack).sum()),
        inf_count=int(np.isinf(stack).sum()),
        warnings=info.get("warnings", []),
    )

    scene_id = Path(product).stem
    result = DetectionResult(
        run_id=_new_run_id(), scene_id=scene_id,
        checkpoint=str(checkpoint),
        device=str(device),
        source=SourceInfo(type="sentinel-2", product=str(product),
                          acquisition_date=acquisition_date),
        input=InputInfo(channels=14, tile_size=PATCH_H,
                        stride=(tiling.stride if tiling else PATCH_H),
                        crs=meta.crs, resolution_m=meta.resolution_m,
                        width_px=meta.width, height_px=meta.height,
                        dem_source=info["dem_file"],
                        slope_method=info["slope_source"]),
        inference_seconds=infer_s,
        detections=dets,
        validation=validation,
        limitations=[
            "Optical S2 imagery is cloud-sensitive; cloud-covered pixels may "
            "produce false negatives.",
            "V1 was trained on Landslide4Sense; performance on other regions "
            "is not formally validated.",
            "detection_confidence is the mean sigmoid probability inside each "
            "polygon, not a calibrated probability of landslide occurrence.",
        ],
    )

    # Persist
    _write_json(output_dir / f"{scene_id}_result.json", result.to_dict())
    _write_json(output_dir / f"{scene_id}_validation.json", validation)
    prob_dir = REPO / "outputs/detection/probability_maps"
    mask_dir = REPO / "outputs/detection/masks"
    poly_dir = REPO / "outputs/detection/polygons"
    handoff_dir = REPO / "outputs/detection/monitoring_handoff"
    for d in [prob_dir, mask_dir, poly_dir, handoff_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Save georeferenced rasters if rasterio present
    _try_write_geotiff(prob_dir / f"{scene_id}_probability.tif", prob, meta, "float32")
    _try_write_geotiff(mask_dir / f"{scene_id}_mask_raw.tif", mask_raw, meta, "uint8")
    _try_write_geotiff(mask_dir / f"{scene_id}_mask_clean.tif", mask_clean, meta, "uint8")
    _write_json(poly_dir / f"{scene_id}_landslides.geojson",
                detections_to_geojson(dets))
    handoff = _handoff_from_detections(scene_id, dets,
                                        source="Sentinel-2",
                                        acquisition_date=acquisition_date)
    _write_json(handoff_dir / f"{scene_id}_monitoring_handoff.json",
                handoff.to_dict())
    return result


__all__ = [
    "run_h5_regression", "run_sentinel2_scene",
    "DEFAULT_V1_CKPT", "DEFAULT_NORM",
]
