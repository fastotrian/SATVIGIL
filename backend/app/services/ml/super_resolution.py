import io
import torch
import numpy as np
from PIL import Image
from typing import Optional
from app.services.agri.edsr_service import EDSRInferenceEngine


async def apply_super_resolution(image_bytes: bytes) -> bytes:
    """
    Applies the validated 4x EDSR super-resolution engine (32 ResBlocks, 64 features, 2.7M params)
    to any satellite raster image bytes (JPEG / PNG).
    """
    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        rgb_arr = np.array(img, dtype=np.uint8)

        engine = EDSRInferenceEngine.get_instance()
        sr_arr = engine.enhance_image(rgb_arr, patch_size=128, overlap=16)

        sr_img = Image.fromarray(sr_arr)
        out_buf = io.BytesIO()
        sr_img.save(out_buf, format="JPEG", quality=92)
        return out_buf.getvalue()
    except Exception as e:
        print(f"[Error] Super-resolution failed: {e}")
        return image_bytes
