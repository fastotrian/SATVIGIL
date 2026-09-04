"""
SATVIGIL — Pydantic Schemas (request/response shapes)
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    risk_level: str
    risk_score: float           # 0.0 – 1.0
    latitude: float
    longitude: float
    title: str
    description: Optional[str]
    source_dataset: Optional[str]
    confidence: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int


class VesselResponse(BaseModel):
    mmsi: str
    vessel_name: Optional[str]
    risk_score: float
    is_dark: bool
    is_loitering: bool
    inside_mpa: bool
    mpa_name: Optional[str]
    last_known_lat: float
    last_known_lon: float
    ais_gap_minutes: int
    recorded_at: datetime

    class Config:
        from_attributes = True


class FireHotspotResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    frp: float
    confidence: str
    fire_type: str
    land_use: Optional[str]
    near_cpcb_cluster: bool
    recurrence_count: int
    responding_agency: str
    acquired_at: datetime

    class Config:
        from_attributes = True
