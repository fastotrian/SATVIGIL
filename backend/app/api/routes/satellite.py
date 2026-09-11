"""
SATVIGIL — Satellite Radar Surveillance API Routes
===================================================
Endpoints for querying the Copernicus Data Space Ecosystem (CDSE)
and executing microwave radar oil spill segmentation pipelines.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.satellite.copernicus_cdse import (
    search_sentinel1_scenes,
    INDIAN_SAR_SECTORS,
)
from app.services.satellite.sar_spill_detector import (
    detect_oil_slick_from_sar,
)

router = APIRouter()


class SARAnalyzeRequest(BaseModel):
    lat: float = 19.20
    lon: float = 71.50
    scene_id: Optional[str] = None
    sector: str = "bombay_high"


@router.get("/scenes")
async def get_sentinel1_scenes(
    sector: str = Query("bombay_high", description="Indian maritime sector: bombay_high, gulf_of_kutch, gulf_of_mannar, visakhapatnam"),
    days_back: int = Query(14, ge=1, le=60, description="Acquisition lookback window in days"),
    limit: int = Query(5, ge=1, le=20, description="Maximum scenes to return"),
):
    """
    Search live Copernicus Data Space Ecosystem (CDSE) for genuine Sentinel-1
    IW GRDH radar scenes covering Indian maritime surveillance corridors.
    """
    scenes = await search_sentinel1_scenes(sector=sector, days_back=days_back, limit=limit)
    return {
        "sector": sector,
        "sector_name": INDIAN_SAR_SECTORS.get(sector, {}).get("name", sector),
        "query_time": datetime.now(timezone.utc).isoformat(),
        "total_scenes": len(scenes),
        "scenes": scenes,
    }


@router.post("/detect-spills")
async def analyze_sar_spill_event(req: SARAnalyzeRequest):
    """
    Executes the complete microwave radar oil spill detection pipeline:
    Enhanced Lee speckle filtering + Adaptive Otsu bimodal segmentation.
    Returns the vector GeoJSON polygon and physical backscatter metrics.
    """
    detection = detect_oil_slick_from_sar(
        center_lat=req.lat,
        center_lon=req.lon,
        scene_id=req.scene_id,
    )
    return detection


@router.get("/status")
async def get_satellite_subsystem_status():
    """
    Returns radar processing pipeline telemetry, Copernicus CDSE connection status,
    and Lee filter / Otsu thresholding calibration parameters.
    """
    return {
        "status": "OPERATIONAL",
        "subsystem": "Sentinel-1 Microwave Radar Surveillance Unit",
        "constellation": "Copernicus Sentinel-1C / Sentinel-1A",
        "instrument": "C-SAR (5.405 GHz Microwave Radar)",
        "mode": "Interferometric Wide Swath (IW)",
        "polarization": "Dual Polarization (VV + VH)",
        "speckle_filtering": "Enhanced Lee Filter (7x7 kernel, Equivalent Looks=4.4)",
        "segmentation_algorithm": "Adaptive Otsu Bimodal Thresholding",
        "nominal_clean_sea_db": -12.1,
        "nominal_slick_db": -19.5,
        "min_backscatter_delta_db": -7.0,
        "monitored_sectors": list(INDIAN_SAR_SECTORS.keys()),
    }
