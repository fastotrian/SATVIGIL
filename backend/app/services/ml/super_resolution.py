import io
import torch
import torchvision.transforms as T
from PIL import Image
from app.services.ml.edsr_model import build_edsr
from pathlib import Path

# Load model globally on module import
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Adjust path based on execution environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = BASE_DIR / "ml" / "models" / "edsr" / "best_model.pth"

edsr_model = None

def init_model():
    global edsr_model
    if edsr_model is not None:
        return

    if not MODEL_PATH.exists():
        print(f"[Warning] Super-resolution model not found at {MODEL_PATH}")
        return

    ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    model_cfg = ckpt.get("model_config", {})
    edsr_model = build_edsr(model_cfg).to(device)
    edsr_model.load_state_dict(ckpt.get("model_state", ckpt))
    edsr_model.eval()

async def apply_super_resolution(image_bytes: bytes) -> bytes:
    if edsr_model is None:
        init_model()
    
    if edsr_model is None:
        # If model failed to load, return original image
        return image_bytes

    try:
        # Load image from bytes
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Convert to tensor
        img_t = T.ToTensor()(img).unsqueeze(0).to(device)
        
        # Inference
        with torch.no_grad():
            sr_t = edsr_model(img_t).clamp(0.0, 1.0).cpu().squeeze(0)
            
        # Convert back to PIL Image
        sr_img = T.ToPILImage()(sr_t)
        
        # Save to bytes
        out_buf = io.BytesIO()
        sr_img.save(out_buf, format="JPEG", quality=90)
        return out_buf.getvalue()
    except Exception as e:
        print(f"[Error] Super-resolution failed: {e}")
        return image_bytes
