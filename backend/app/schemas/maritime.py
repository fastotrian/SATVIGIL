"""
SATVIGIL — Maritime Pydantic Schemas
Defines request and response shapes matching frontend/src/types/maritime.ts.
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import get_risk_label

RiskLevel = Literal["CRITICAL", "WARNING", "WATCH", "NORMAL"]
AlertType = Literal["OIL_SPILL", "DARK_VESSEL", "ILLEGAL_FISHING", "FIRE", "LANDSLIDE"]


class VesselResponse(BaseModel):
    """
    AIS Vessel entity matching frontend `Vessel` interface.
    """
    model_config = ConfigDict(from_attributes=True)

    mmsi: str
    vessel_name: str
    vessel_type: int
    vessel_type_label: str
    lat: float
    lon: float
    speed_knots: float
    course_deg: float
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    ais_gap_minutes: int = 0
    is_dark: bool = False
    in_mpa: bool = False
    mpa_name: Optional[str] = None
    last_seen: datetime


class VesselListResponse(BaseModel):
    """
    Wrapper for returning a list of vessels with telemetry metadata.
    """
    model_config = ConfigDict(from_attributes=True)

    vessels: List[VesselResponse]
    total: int
    timestamp: datetime


class SpillCandidateResponse(BaseModel):
    """
    Correlated vessel candidate for an oil spill incident.
    """
    model_config = ConfigDict(from_attributes=True)

    mmsi: str
    vessel_name: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    distance_km: float
    type_risk: float
    heading_score: float
    behavioral_anomaly: bool = False


class SpillEventResponse(BaseModel):
    """
    Detected oil spill incident with Copernicus metadata and top correlated vessels.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    detected_at: datetime
    lat: float
    lon: float
    area_km2: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    sentinel_scene_id: str
    top_candidates: List[SpillCandidateResponse] = []
    geojson_polygon: Dict[str, Any]
    sar_image_url: Optional[str] = None   # Annotated SAR image URL for popup display


class AlertResponse(BaseModel):
    """
    Maritime alert entity matching frontend `Alert` interface.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_type: AlertType
    risk_level: RiskLevel
    title: str
    description: str
    lat: float
    lon: float
    created_at: datetime
    vessel_mmsi: Optional[str] = None
    acknowledged: bool = False


class SimulateDarkVesselRequest(BaseModel):
    """
    Request payload to simulate a dark vessel during hackathon demo.
    """
    mmsi: str
    lat: float
    lon: float
    ais_gap_minutes: int


class SimulateSpillRequest(BaseModel):
    """
    Request payload to trigger oil spill detection simulation during hackathon demo.
    """
    spill_lat: float = 19.15
    spill_lon: float = 71.45
    spill_trail_bearing: float = 250.0
    time_window_hours: int = 12

