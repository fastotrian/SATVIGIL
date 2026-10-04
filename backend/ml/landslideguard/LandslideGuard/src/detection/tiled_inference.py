"""Full-scene tiled inference over an already-normalized 14-channel stack.

Contract:
    input  stack: (H, W, 14) float32, ALREADY normalized (train-only z-score).
    output prob : (H, W)      float32 in [0, 1], SAME geographic footprint.

Design points:
    - Fixed 128x128 tile size (V1's contract).
    - Configurable stride; default = 128 (non-overlapping, deterministic).
    - Edge tiles are reflection-padded to 128x128 before the model call, then
      the pad is stripped from the prediction. No pixels are discarded.
    - Overlapping tiles are averaged using a simple sum/count accumulator.
    - Runs under torch.inference_mode() + model.eval(). Optional AMP on CUDA.
    - Batched: `batch_size` tiles per forward pass (default 8).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

import numpy as np
import torch


TILE = 128
DEFAULT_STRIDE = 128


@dataclass(frozen=True)
class TilingConfig:
    tile: int = TILE
    stride: int = DEFAULT_STRIDE
    batch_size: int = 8
    use_amp: bool = True                # no-op on CPU
    pad_mode: str = "reflect"           # "reflect" | "constant"


def _tile_origins(size: int, tile: int, stride: int) -> list[int]:
    """List of top-left origins along one axis so every pixel is covered."""
    if size <= tile:
        return [0]
    origins = list(range(0, size - tile + 1, stride))
    last = size - tile
    if origins[-1] != last:
        origins.append(last)
    return origins


def _pad_to_tile(patch: np.ndarray, tile: int, mode: str) -> tuple[np.ndarray, int, int]:
    """Reflection-pad a (h, w, C) patch up to (tile, tile, C).

    Returns (padded, orig_h, orig_w) so we can strip the pad later.
    """
    h, w, c = patch.shape
    if h == tile and w == tile:
        return patch, h, w
    pad_h = tile - h
    pad_w = tile - w
    padded = np.pad(patch,
                    ((0, pad_h), (0, pad_w), (0, 0)),
                    mode=mode if mode == "reflect" else "constant")
    return padded, h, w


@torch.inference_mode()
def run_tiled_inference(model: torch.nn.Module,
                        stack: np.ndarray,
                        device: torch.device | None = None,
                        cfg: TilingConfig | None = None,
                        ) -> np.ndarray:
    """Run V1 over a (H, W, 14) already-normalized float32 stack.

    Returns a (H, W) float32 probability map.
    """
    if stack.ndim != 3 or stack.shape[-1] != 14:
        raise ValueError(f"expected (H, W, 14) stack, got {stack.shape}")
    if stack.dtype != np.float32:
        stack = stack.astype(np.float32, copy=False)
    if cfg is None:
        cfg = TilingConfig()
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = cfg.use_amp and device.type == "cuda"

    H, W, _ = stack.shape
    prob_sum = np.zeros((H, W), dtype=np.float32)
    prob_cnt = np.zeros((H, W), dtype=np.float32)

    ys = _tile_origins(H, cfg.tile, cfg.stride)
    xs = _tile_origins(W, cfg.tile, cfg.stride)

    model = model.to(device).eval()

    # Iterate tiles, batch them
    coords: list[tuple[int, int, int, int]] = []   # (y0, x0, orig_h, orig_w)
    tensors: list[torch.Tensor] = []

    def _flush(coords_batch, tensors_batch):
        if not tensors_batch:
            return
        batch = torch.stack(tensors_batch, dim=0).to(device, non_blocking=True)
        if use_amp:
            with torch.amp.autocast(device_type="cuda", enabled=True):
                logits = model(batch).float()
        else:
            logits = model(batch)
        probs = torch.sigmoid(logits)[:, 0].cpu().numpy()   # (b, tile, tile)
        for (y0, x0, oh, ow), p in zip(coords_batch, probs):
            prob_sum[y0:y0+oh, x0:x0+ow] += p[:oh, :ow]
            prob_cnt[y0:y0+oh, x0:x0+ow] += 1.0

    for y0 in ys:
        for x0 in xs:
            y1 = min(y0 + cfg.tile, H)
            x1 = min(x0 + cfg.tile, W)
            patch = stack[y0:y1, x0:x1, :]
            padded, oh, ow = _pad_to_tile(patch, cfg.tile, cfg.pad_mode)
            t = torch.from_numpy(np.ascontiguousarray(padded.transpose(2, 0, 1)))
            tensors.append(t)
            coords.append((y0, x0, oh, ow))
            if len(tensors) >= cfg.batch_size:
                _flush(coords, tensors)
                coords, tensors = [], []
    _flush(coords, tensors)

    # Guard against a rare zero-count pixel (shouldn't happen because we grow
    # origins so every pixel is covered)
    prob_cnt[prob_cnt == 0] = 1.0
    prob = prob_sum / prob_cnt
    return prob.astype(np.float32)


def iter_tile_origins(H: int, W: int, cfg: TilingConfig | None = None
                      ) -> Iterator[tuple[int, int]]:
    """Debug helper: enumerate the (y0, x0) origins that will be used."""
    cfg = cfg or TilingConfig()
    for y0 in _tile_origins(H, cfg.tile, cfg.stride):
        for x0 in _tile_origins(W, cfg.tile, cfg.stride):
            yield y0, x0


__all__ = ["TILE", "DEFAULT_STRIDE", "TilingConfig",
           "run_tiled_inference", "iter_tile_origins"]
