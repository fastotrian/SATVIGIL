"""
SATVIGIL — Landslide API Route
Static Mock for Demo Purposes (Wayanad & Joshimath SAR InSAR deformation)
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Any

router = APIRouter()

@router.get("/risk-areas")
async def get_landslide_risk_areas():
    """
    Returns static GeoJSON FeatureCollection of landslide risk zones.
    Used for Sprint 3 Demo to demonstrate SAR/InSAR data without live pipeline.
    """
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [76.08, 11.60],
                            [76.12, 11.60],
                            [76.12, 11.65],
                            [76.08, 11.65],
                            [76.08, 11.60]
                        ]
                    ]
                },
                "properties": {
                    "id": 1,
                    "region": "Wayanad, Kerala",
                    "risk_level": "critical",
                    "displacement_mm": 45.2,
                    "velocity_mm_per_day": 2.1,
                    "sensor": "Sentinel-1 InSAR",
                    "last_updated": "2026-08-12T00:00:00Z"
                }
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [79.55, 30.54],
                            [79.58, 30.54],
                            [79.58, 30.57],
                            [79.55, 30.57],
                            [79.55, 30.54]
                        ]
                    ]
                },
                "properties": {
                    "id": 2,
                    "region": "Joshimath, Uttarakhand",
                    "risk_level": "high",
                    "displacement_mm": 28.7,
                    "velocity_mm_per_day": 1.4,
                    "sensor": "Sentinel-1 InSAR",
                    "last_updated": "2026-08-20T00:00:00Z"
                }
            }
        ]
    }
