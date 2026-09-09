"""
SATVIGIL — Spatial Query Schemas
"""
from pydantic import BaseModel
from typing import List

from app.schemas.alert import AlertNearResponse
from app.schemas.vessel import VesselNearResponse
from app.schemas.hotspot import HotspotNearResponse

class SpatialRadiusResponse(BaseModel):
    """Unified response for GET /api/v1/alerts/near"""
    query_lat: float
    query_lon: float
    radius_km: float
    alerts: List[AlertNearResponse]
    vessels: List[VesselNearResponse]
    hotspots: List[HotspotNearResponse]