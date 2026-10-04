"""Run super-resolution inference on a single RGB image."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch
import yaml

torch.set_num_threads(1)

from models import build_edsr
from utils.image_utils import (
    load_image_rgb,
    save_image_rgb,
    tensor_to_uint8,
    uint8_to_tensor,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="EDSR SR inference on one image.")
    parser.add_argument("--input", required=True, help="Path to LR RGB input image.")
    parser.add_argument("--output", required=True, help="Path to write SR image.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--checkpoint", default=None,
                        help="Model checkpoint; defaults to <checkpoint_dir>/best_model.pth")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[env] device = {device}")

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        raise FileNotFoundError(f"Input image not found: {in_path}")

    lr = load_image_rgb(in_path)
    print(f"[in ] {in_path.name}  shape = {lr.shape}")

    ckpt_path = Path(args.checkpoint) if args.checkpoint else Path(cfg["output"]["checkpoint_dir"]) / "best_model.pth"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}. Train first?")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model_cfg = ckpt.get("model_config", cfg["model"])
    model = build_edsr(model_cfg).to(device)
    state = ckpt["model_state"] if "model_state" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()
    print(f"[model] loaded {ckpt_path}  params = {model.num_parameters():,}")

    lr_t = uint8_to_tensor(lr).unsqueeze(0).to(device)
    with torch.no_grad():
        sr_t = model(lr_t).clamp(0.0, 1.0).cpu()

    sr = tensor_to_uint8(sr_t)
    print(f"[out] shape = {sr.shape}")
    save_image_rgb(out_path, sr)
    print(f"[out] wrote {out_path}")


if __name__ == "__main__":
    main()
