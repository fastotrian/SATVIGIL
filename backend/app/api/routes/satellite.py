"""
SATVIGIL — Satellite Radar Surveillance API Routes
===================================================
Endpoints for querying the Copernicus Data Space Ecosystem (CDSE)
and executing microwave radar oil spill segmentation pipelines.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.services.satellite.copernicus_cdse import (
    search_sentinel1_scenes,
    INDIAN_SAR_SECTORS,
    fetch_vessel_satellite_snapshot,
)
from app.services.satellite.sar_spill_detector import (
    detect_oil_slick_from_sar,
)
from app.services.ml.super_resolution import apply_super_resolution

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


@router.get("/vessel-image")
async def get_vessel_satellite_image(
    lat: float = Query(..., description="Vessel latitude"),
    lon: float = Query(..., description="Vessel longitude"),
    mmsi: Optional[int] = Query(None, description="Vessel MMSI"),
    sensor: str = Query("sentinel1", description="Satellite sensor: sentinel1 (SAR Radar) or sentinel2 (Optical RGB)"),
    course: float = Query(0.0, description="Vessel course over ground in degrees"),
    speed: float = Query(12.0, description="Vessel speed over ground in knots"),
):
    """
    Returns an on-the-fly satellite reconnaissance snapshot centered on any vessel's coordinates.
    Directly connected to Copernicus Sentinel Hub Process API with AIS target signature fusion.
    """
    try:
        image_bytes, provider = await fetch_vessel_satellite_snapshot(
            lat=lat,
            lon=lon,
            mmsi=mmsi,
            sensor=sensor,
            course=course,
            speed=speed,
        )
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={
                "X-Satellite-Provider": provider,
                "Cache-Control": "public, max-age=3600",
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Satellite reconnaissance image generation error: {exc}")


@router.get("/thermal-image")
async def get_thermal_satellite_image(
    lat: float = Query(..., description="Hotspot latitude"),
    lon: float = Query(..., description="Hotspot longitude"),
    enhance: bool = Query(False, description="Apply EDSR Super-Resolution")
):
    """
    Returns an on-the-fly satellite reconnaissance snapshot centered on any thermal hotspot.
    Applies Deep Learning Super-Resolution (EDSR) if enhance is True.
    """
    try:
        image_bytes, provider = await fetch_vessel_satellite_snapshot(
            lat=lat,
            lon=lon,
            mmsi=None,
            sensor="sentinel2",
            course=0.0,
            speed=0.0,
        )
        
        if enhance:
            image_bytes = await apply_super_resolution(image_bytes)
            
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={
                "X-Satellite-Provider": provider,
                "X-Super-Resolution": "EDSR" if enhance else "None",
                "Cache-Control": "public, max-age=3600",
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Thermal hotspot image generation error: {exc}")
