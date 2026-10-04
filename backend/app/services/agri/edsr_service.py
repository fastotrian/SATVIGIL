from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import torch

# Ensure scripts directory is on sys.path to import models & utils
SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from models import build_edsr
    from utils.image_utils import uint8_to_tensor, tensor_to_uint8
except ImportError:
    # Fallback import if running from other contexts
    build_edsr = None
    uint8_to_tensor = None
    tensor_to_uint8 = None


class EDSRInferenceEngine:
    """Singleton service for EDSR super-resolution inference on RGB satellite rasters."""
    _instance: Optional[EDSRInferenceEngine] = None

    def __init__(self, checkpoint_path: Optional[str] = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.checkpoint_path = checkpoint_path or str(SCRIPTS_DIR / "best_model.pth")
        self.model = None
        self.model_config = {}
        self.scale = 4
        self._load_model()

    @classmethod
    def get_instance(cls) -> EDSRInferenceEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self) -> None:
        if not os.path.exists(self.checkpoint_path):
            print(f"[EDSR] Warning: Checkpoint not found at {self.checkpoint_path}")
            return

        try:
            ckpt = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
            self.model_config = ckpt.get("model_config", {
                "in_channels": 3,
                "out_channels": 3,
                "features": 64,
                "num_blocks": 32,
                "scale": 4,
                "res_scale": 1.0
            })
            self.scale = self.model_config.get("scale", 4)
            self.model = build_edsr(self.model_config).to(self.device)
            state = ckpt["model_state"] if "model_state" in ckpt else ckpt
            self.model.load_state_dict(state)
            self.model.eval()
            print(f"[EDSR Engine] Loaded {self.checkpoint_path} on {self.device} (params: {self.model.num_parameters():,}, scale: {self.scale}x)")
        except Exception as e:
            print(f"[EDSR Engine] Error loading model: {e}")

    def enhance_patch(self, rgb_patch: np.ndarray) -> np.ndarray:
        """
        Enhance a single RGB patch (H, W, 3) uint8 [0, 255].
        Returns (H*scale, W*scale, 3) uint8 [0, 255].
        """
        if self.model is None:
            # Fallback bicubic upscaling if model not loaded
            h, w = rgb_patch.shape[:2]
            img = Image.fromarray(rgb_patch).resize((w * self.scale, h * self.scale), Image.BICUBIC)
            return np.array(img, dtype=np.uint8)

        t = uint8_to_tensor(rgb_patch).unsqueeze(0).to(self.device)
        with torch.no_grad():
            sr_t = self.model(t).clamp(0.0, 1.0).cpu()
        return tensor_to_uint8(sr_t)

    def enhance_image(self, rgb_image: np.ndarray, patch_size: int = 128, overlap: int = 16) -> np.ndarray:
        """
        Enhance large RGB image using overlapping tile reconstruction to conserve memory.
        """
        h, w, c = rgb_image.shape
        scale = self.scale
        out_h, out_w = h * scale, w * scale

        if h <= patch_size and w <= patch_size:
            return self.enhance_patch(rgb_image)

        output = np.zeros((out_h, out_w, c), dtype=np.float32)
        weight = np.zeros((out_h, out_w, 1), dtype=np.float32)

        stride = patch_size - overlap
        y_steps = list(range(0, max(1, h - patch_size + 1), stride))
        if y_steps[-1] + patch_size < h:
            y_steps.append(h - patch_size)

        x_steps = list(range(0, max(1, w - patch_size + 1), stride))
        if x_steps[-1] + patch_size < w:
            x_steps.append(w - patch_size)

        for y in y_steps:
            for x in x_steps:
                patch = rgb_image[y:y+patch_size, x:x+patch_size]
                sr_patch = self.enhance_patch(patch).astype(np.float32)

                py, px = y * scale, x * scale
                ph, pw = patch_size * scale, patch_size * scale

                # Blending weight matrix (cosine feathering)
                wy = np.sin(np.linspace(0, np.pi, ph)).reshape(-1, 1)
                wx = np.sin(np.linspace(0, np.pi, pw)).reshape(1, -1)
                w_patch = (wy * wx)[..., np.newaxis]

                output[py:py+ph, px:px+pw] += sr_patch * w_patch
                weight[py:py+ph, px:px+pw] += w_patch

        # Normalize overlapping regions
        weight = np.maximum(weight, 1e-5)
        enhanced = (output / weight).round().clip(0, 255).astype(np.uint8)
        return enhanced
