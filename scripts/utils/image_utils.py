from pathlib import Path
import numpy as np
from PIL import Image
import torch


def load_image_rgb(path: Path | str) -> np.ndarray:
    """Load an image file and return an RGB uint8 numpy array (H, W, 3)."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)


def save_image_rgb(path: Path | str, img_arr: np.ndarray) -> None:
    """Save an RGB uint8 numpy array (H, W, 3) to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(img_arr)
    img.save(path)


def uint8_to_tensor(img_arr: np.ndarray) -> torch.Tensor:
    """Convert (H, W, 3) uint8 [0, 255] numpy array to (3, H, W) float32 [0.0, 1.0] tensor."""
    t = torch.from_numpy(img_arr).float() / 255.0
    return t.permute(2, 0, 1)


def tensor_to_uint8(tensor: torch.Tensor) -> np.ndarray:
    """Convert (1, 3, H, W) or (3, H, W) float32 [0.0, 1.0] tensor to (H, W, 3) uint8 [0, 255] array."""
    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)
    arr = tensor.permute(1, 2, 0).clamp(0.0, 1.0).numpy()
    return (arr * 255.0).round().astype(np.uint8)
