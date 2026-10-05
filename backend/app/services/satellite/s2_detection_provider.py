
import asyncio
import io
import math
import os
import zipfile
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
import rasterio

from app.core.config import settings
from .copernicus_cdse import get_cdse_access_token

logger = logging.getLogger(__name__)

async def fetch_s2_detection_payload(lat: float, lon: float, delta_deg: float = 0.05, output_dir: str = "data/s2_cache"):
    """
    Fetches the 12 optical bands of Sentinel-2 L2A + Copernicus DEM using the Sentinel Hub Process API.
    Splits them into individual single-band TIFFs for compatibility with Detection V1 contract.
    """
    token = await get_cdse_access_token()
    if not token:
        raise ValueError("Failed to get CDSE access token")

    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    
    # 12 optical bands L2A
    evalscript_s2 = """//VERSION=3
function setup() {
  return {
    input: ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"],
    output: { id: "default", bands: 12, sampleType: "UINT16" }
  };
}
function evaluatePixel(sample) {
  return [
    sample.B01 * 10000, sample.B02 * 10000, sample.B03 * 10000, sample.B04 * 10000,
    sample.B05 * 10000, sample.B06 * 10000, sample.B07 * 10000, sample.B08 * 10000,
    sample.B8A * 10000, sample.B09 * 10000, sample.B11 * 10000, sample.B12 * 10000
  ];
}
"""
    bbox = [lon - delta_deg, lat - delta_deg, lon + delta_deg, lat + delta_deg]
    w, h = 1024, 1024

    payload_s2 = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00Z"),
                        "to": datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59Z")
                    },
                    "maxCloudCoverage": 20
                }
            }]
        },
        "output": {
            "width": w,
            "height": h,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
        },
        "evalscript": evalscript_s2
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp_s2 = await client.post(
            "https://sh.dataspace.copernicus.eu/api/v1/process",
            json=payload_s2,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff"}
        )
        if resp_s2.status_code != 200:
            raise RuntimeError(f"CDSE API Error S2: {resp_s2.text}")
        s2_bytes = resp_s2.content

    evalscript_dem = """//VERSION=3
function setup() {
  return {
    input: ["DEM"],
    output: { id: "default", bands: 1, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  return [sample.DEM];
}
"""
    payload_dem = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
            },
            "data": [{"type": "dem"}]
        },
        "output": {
            "width": w,
            "height": h,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
        },
        "evalscript": evalscript_dem
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp_dem = await client.post(
            "https://sh.dataspace.copernicus.eu/api/v1/process",
            json=payload_dem,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff"}
        )
        if resp_dem.status_code != 200:
            raise RuntimeError(f"CDSE API Error DEM: {resp_dem.text}")
        dem_bytes = resp_dem.content

    with open(out_p / "s2_multiband.tif", "wb") as f:
        f.write(s2_bytes)
    with open(out_p / "_DEM_.tif", "wb") as f:
        f.write(dem_bytes)

    bands = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]
    with rasterio.open(out_p / "s2_multiband.tif") as src:
        prof = src.profile
        prof.update(count=1)
        for i, b_name in enumerate(bands):
            b_data = src.read(i + 1)
            b_path = out_p / f"s2_{b_name}_.tif"
            with rasterio.open(b_path, "w", **prof) as dst:
                dst.write(b_data, 1)

    logger.info(f"Successfully generated detection payload at {out_p}")
    return out_p

