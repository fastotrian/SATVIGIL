"""
Test script for Copernicus Sentinel Hub Process API.
Exchanges COPERNICUS_CLIENT_ID & COPERNICUS_CLIENT_SECRET for an access token,
then fetches a live calibrated Sentinel-1 C-SAR radar patch over Bombay High.
"""
import os
import sys
import httpx
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

client_id = settings.COPERNICUS_CLIENT_ID.strip()
client_secret = settings.COPERNICUS_CLIENT_SECRET.strip()

if not client_id or not client_secret:
    print("\n[ERROR] COPERNICUS_CLIENT_ID or COPERNICUS_CLIENT_SECRET is empty!")
    print("Please paste them into backend/.env and save the file (Ctrl+S).\n")
    sys.exit(1)

print(f"\n[1/3] Using Copernicus Client ID: {client_id[:8]}...{client_id[-4:] if len(client_id)>12 else ''}")

# Step 1: Get OAuth2 Access Token
token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
token_payload = {
    "client_id": "cdse-public",
    "username": client_id,
    "password": client_secret,
    "grant_type": "password",
}

# Also try standard client_credentials grant type if user created an OAuth2 client
oauth_payload = {
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret,
}

print("[2/3] Authenticating with Copernicus Identity Service...")
access_token = None

with httpx.Client(timeout=20.0) as client:
    # Try client_credentials first (standard for Sentinel Hub OAuth clients)
    resp = client.post(token_url, data=oauth_payload)
    if resp.status_code == 200:
        access_token = resp.json().get("access_token")
        print("  -> Authentication successful via client_credentials grant!")
    else:
        # Fallback to password grant
        resp2 = client.post(token_url, data=token_payload)
        if resp2.status_code == 200:
            access_token = resp2.json().get("access_token")
            print("  -> Authentication successful via user credentials grant!")
        else:
            print(f"  -> Authentication failed: HTTP {resp.status_code}")
            print(f"     Response: {resp.text[:250]}")
            sys.exit(1)

# Step 2: Query Sentinel Hub Process API for Bombay High Sentinel-1 C-SAR
print("[3/3] Requesting live Sentinel-1 C-SAR radar raster for Bombay High (19.20 N, 71.50 E)...")

PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

evalscript = """
//VERSION=3
function setup() {
  return {
    input: ["VV"],
    output: { id: "default", bands: 1, sampleType: "UINT16" }
  };
}

function evaluatePixel(samples) {
  // Sentinel-1 linear backscatter power to 16-bit unsigned digital number
  let val = Math.min(Math.max(Math.round(samples.VV * 1000.0), 1), 65535);
  return [val];
}
"""

request_payload = {
    "input": {
        "bounds": {
            "bbox": [70.8, 18.6, 72.4, 19.8],
            "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
        },
        "data": [{
            "type": "sentinel-1-grd",
            "dataFilter": {
                "timeRange": {
                    "from": "2026-08-01T00:00:00Z",
                    "to": "2026-09-13T23:59:59Z"
                },
                "acquisitionMode": "IW",
                "polarization": "DV"
            }
        }]
    },
    "output": {
        "width": 256,
        "height": 256,
        "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
    },
    "evalscript": evalscript
}

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/tar"
}

with httpx.Client(timeout=60.0) as client:
    res = client.post(PROCESS_URL, json=request_payload, headers=headers)
    if res.status_code == 200:
        import io
        import tarfile
        out_file = Path(__file__).resolve().parents[1] / "data" / "sar" / "live_sentinel1_bombay_high_vv.tif"
        
        # Check if response is tar archive
        if res.content.startswith(b"default.tif"):
            with tarfile.open(fileobj=io.BytesIO(res.content)) as tar:
                member = tar.extractfile("default.tif")
                out_file.write_bytes(member.read())
        else:
            out_file.write_bytes(res.content)
            
        print(f"\n[SUCCESS] Live Sentinel-1 C-SAR raster downloaded from Process API!")
        print(f"Saved to: {out_file} ({out_file.stat().st_size} bytes)")
        
        from PIL import Image
        import numpy as np
        with Image.open(out_file) as img:
            arr = np.array(img)
            print(f"Verified GeoTIFF: shape={arr.shape}, dtype={arr.dtype}, min={np.min(arr)}, max={np.max(arr)}, mean={np.mean(arr):.1f}")
    else:
        print(f"\nProcess API response: HTTP {res.status_code}")
        print(f"Body: {res.text[:300]}")
