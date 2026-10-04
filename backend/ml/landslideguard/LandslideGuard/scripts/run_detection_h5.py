"""Run V1 detection on one (or many) Landslide4Sense H5 patches.

Usage:
    python scripts/run_detection_h5.py --input <file.h5> [--input file2.h5 ...] \
        [--checkpoint checkpoints/detection/best_model.pth] \
        [--output-dir outputs/detection/inference] \
        [--gt-mask <path>] [--json-only] [--save-png]

For each input:
    - loads V1
    - runs frozen 14-channel inference
    - writes probability .npy, mask .npy, GeoJSON (pixel coords),
      DetectionResult JSON, validation JSON
    - if GT mask is next to the input, appends metrics_against_gt
    - optional 4-panel PNG when --save-png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np
import torch

from src.detection.pipeline import run_h5_regression, DEFAULT_V1_CKPT, DEFAULT_NORM
from src.detection.preprocessing import read_image, read_mask


def _save_panel_png(h5_path: Path, out_png: Path, prob: np.ndarray,
                    mask: np.ndarray, gt_path: Path | None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    img = read_image(h5_path)
    r, g, b = img[..., 3], img[..., 2], img[..., 1]
    rgb = np.stack([r, g, b], axis=-1)
    lo, hi = np.percentile(rgb, [2, 98])
    rgb01 = np.clip((rgb - lo) / max(hi - lo, 1e-6), 0, 1)
    n_ax = 4 if gt_path else 3
    fig, ax = plt.subplots(1, n_ax, figsize=(3.2 * n_ax, 3.5))
    ax[0].imshow(rgb01); ax[0].set_title("RGB (B4,B3,B2)")
    ax[1].imshow(prob, cmap="magma", vmin=0, vmax=1)
    ax[1].set_title(f"V1 prob  max={prob.max():.3f}")
    ax[2].imshow(mask, cmap="Greens", vmin=0, vmax=1)
    ax[2].set_title(f"pred @ thr=0.60  ({int(mask.sum())} px)")
    if gt_path is not None:
        gt = read_mask(gt_path)
        ov = rgb01.copy()
        ov[(mask == 1) & (gt == 1)] = [0, 1, 0]
        ov[(mask == 1) & (gt == 0)] = [1, 0, 0]
        ov[(mask == 0) & (gt == 1)] = [0, 0, 1]
        ax[3].imshow(ov); ax[3].set_title("overlay TP/FP/FN")
    for a in ax:
        a.set_xticks([]); a.set_yticks([])
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120, bbox_inches="tight"); plt.close(fig)


def _try_load_prob(scene_id: str) -> np.ndarray | None:
    p = REPO / f"outputs/detection/probability_maps/{scene_id}_probability.npy"
    return np.load(p) if p.is_file() else None


def _try_load_mask(scene_id: str) -> np.ndarray | None:
    p = REPO / f"outputs/detection/masks/{scene_id}_mask_clean.npy"
    return np.load(p) if p.is_file() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", action="append", required=True,
                    help="path to .h5 image tile (may be given multiple times)")
    ap.add_argument("--checkpoint", default=str(DEFAULT_V1_CKPT))
    ap.add_argument("--normalization", default=str(DEFAULT_NORM))
    ap.add_argument("--output-dir", default=str(REPO / "outputs/detection/inference"))
    ap.add_argument("--gt-mask", default=None,
                    help="single GT mask path (used only if exactly one --input)")
    ap.add_argument("--json-only", action="store_true",
                    help="skip probability/mask numpy writes (still writes JSON)")
    ap.add_argument("--save-png", action="store_true",
                    help="write a 4-panel PNG next to the input")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    for raw in args.input:
        h5 = Path(raw)
        gt = Path(args.gt_mask) if args.gt_mask and len(args.input) == 1 else None
        result = run_h5_regression(
            h5, checkpoint=args.checkpoint, norm_stats_path=args.normalization,
            output_dir=args.output_dir, device=device, gt_mask_path=gt,
        )
        detected = len(result.detections)
        line = f"[{h5.name}] detections={detected} device={result.device} " \
               f"inference_s={result.inference_seconds:.3f}"
        if result.metrics_against_gt is not None:
            m = result.metrics_against_gt
            line += (f"  |  GT dice={m['dice']:.4f} iou={m['iou']:.4f} "
                     f"tp={m['tp']} fp={m['fp']} fn={m['fn']}")
        print(line)
        if args.save_png:
            prob = _try_load_prob(result.scene_id)
            mask = _try_load_mask(result.scene_id)
            gt_here = gt
            if gt_here is None:
                cand = h5.with_name(h5.stem + "_mask.h5")
                gt_here = cand if cand.is_file() else None
            if prob is not None and mask is not None:
                out_png = REPO / f"outputs/detection/visualizations/{result.scene_id}_panels.png"
                _save_panel_png(h5, out_png, prob, mask, gt_here)
                print(f"    saved {out_png}")


if __name__ == "__main__":
    main()
