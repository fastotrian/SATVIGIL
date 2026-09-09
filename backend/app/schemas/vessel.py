"""
SATVIGIL — Vessel & Spill Pydantic v2 Schemas
Mirrors: backend/app/models/alert.py  →  VesselRiskRecord table

Schema list:
  VesselSchema       — maps 1:1 to VesselRiskRecord + computed risk_level field
  SpillAlertSchema   — filtered Alert view (alert_type=oil_spill) for maritime route
  VesselListResponse — paginated wrapper for GET /api/v1/maritime/vessels
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.alert import Latitude, Longitude, RiskLevel, RiskScore


# ── Risk thresholds (single source of truth — also used by ais_fetcher.py) ────

def _score_to_risk_level(score: float) -> str:
    """Convert a 0.0–1.0 risk score to a human-readable risk level label."""
    if score < 0.30:
        return RiskLevel.LOW.value
    if score < 0.60:
        return RiskLevel.MEDIUM.value
    if score < 0.85:
        return RiskLevel.HIGH.value
    return RiskLevel.CRITICAL.value


# ── VesselSchema — full vessel record ────────────────────────────────────────

class VesselSchema(BaseModel):
    """
    Full vessel risk record — returned by:
      GET /api/v1/maritime/vessels          (inside VesselListResponse)
      GET /api/v1/maritime/vessels/{mmsi}   (direct)

    risk_level is a computed field derived from risk_score at serialisation time;
    it is NOT stored in the DB (VesselRiskRecord has only risk_score).
    """
    model_config = ConfigDict(from_attributes=True)

    mmsi:            str = Field(..., description="Maritime Mobile Service Identity (9 digits)")
    vessel_name:     Optional[str]  = None
    vessel_type:     Optional[str]  = None
    risk_score:      RiskScore
    is_dark:         bool           = Field(False, description="AIS transponder switched off")
    is_loitering:    bool           = Field(False, description="Speed < 1 kt for > 60 minutes")
    inside_mpa:      bool           = Field(False, description="Located inside a Marine Protected Area")
    last_known_lat:  Latitude
    last_known_lon:  Longitude
    ais_gap_minutes: Optional[int]  = Field(
        None, ge=0, description="Duration (minutes) the AIS transponder was silent"
    )
    recorded_at:     datetime

    @computed_field  # type: ignore[misc]
    @property
    def risk_level(self) -> str:
        """Derived from risk_score — low | medium | high | critical."""
        return _score_to_risk_level(self.risk_score)


# ── SpillAlertSchema — oil spill filtered view ───────────────────────────────

class SpillAlertSchema(BaseModel):
    """
    Oil spill detection — a filtered view of the Alert table
    (alert_type = 'oil_spill', source_dataset = 'SENTINEL').

    Returned by GET /api/v1/maritime/spills.
    """
    model_config = ConfigDict(from_attributes=True)

    id:             int
    latitude:       Latitude
    longitude:      Longitude
    risk_score:     RiskScore
    risk_level:     RiskLevel
    title:          str
    source_dataset: Optional[str] = Field(
        "SENTINEL", description="Always SENTINEL for satellite-detected spills"
    )
    confidence:     Optional[str] = Field(
        None, description="Detection confidence: low | nominal | high"
    )
    is_active:      bool
    created_at:     datetime


# ── VesselListResponse — paginated wrapper ────────────────────────────────────

class VesselListResponse(BaseModel):
    """Paginated envelope for GET /api/v1/maritime/vessels."""
    vessels: List[VesselSchema]
    total:   int  = Field(..., description="Total vessel records before pagination")
    limit:   int  = Field(50,  description="Page size requested")
    offset:  int  = Field(0,   description="Page offset requested")

# -- VesselNearResponse � proximity search result ------------------------------

class VesselNearResponse(VesselSchema):
    """Vessel with computed distance � returned by GET /api/v1/alerts/near."""
    distance_km: float = Field(..., ge=0, description="Great-circle distance from query point in km")
