"""
SATVIGIL — Alert Pydantic v2 Schemas
Mirrors: backend/app/models/alert.py  →  Alert table

Schema tiers:
  AlertSummary          — condensed, used in list responses
  AlertResponse         — full detail, used by GET /api/v1/alerts/{id}
  AlertListResponse     — paginated wrapper for GET /api/v1/alerts
  AlertNearResponse     — extends summary with distance_km for GET /api/v1/alerts/near
  WebSocketAlertMessage — envelope for WS push events
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Enums (mirror models.alert — kept here so routes/schemas stay independent) ─

class AlertType(str, enum.Enum):
    OIL_SPILL            = "oil_spill"
    ILLEGAL_FISHING      = "illegal_fishing"
    FIRE_INDUSTRIAL      = "fire_industrial"
    FIRE_WILDFIRE        = "fire_wildfire"
    FIRE_STUBBLE         = "fire_stubble"
    FIRE_GAS_FLARE       = "fire_gas_flare"
    FIRE_MINING          = "fire_mining"
    INDUSTRIAL_POLLUTION = "industrial_pollution"
    LANDSLIDE_RISK       = "landslide_risk"


class RiskLevel(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ── Reusable annotated types ───────────────────────────────────────────────────

RiskScore = Annotated[float, Field(ge=0.0, le=1.0, description="Normalised risk score 0.0–1.0")]
Latitude  = Annotated[float, Field(ge=-90.0, le=90.0, description="Decimal degrees WGS-84")]
Longitude = Annotated[float, Field(ge=-180.0, le=180.0, description="Decimal degrees WGS-84")]


# ── AlertSummary — lightweight, used inside list / WS responses ────────────────

class AlertSummary(BaseModel):
    """Condensed alert — omits description and resolved_at to reduce payload size."""
    model_config = ConfigDict(from_attributes=True)

    id:             int
    alert_type:     AlertType
    risk_level:     RiskLevel
    risk_score:     RiskScore
    latitude:       Latitude
    longitude:      Longitude
    title:          str
    source_dataset: Optional[str] = Field(
        None, description="Originating dataset: FIRMS | AIS | SENTINEL"
    )
    confidence:     Optional[str] = Field(
        None, description="Detection confidence: low | nominal | high"
    )
    is_active:      bool
    created_at:     datetime


# ── AlertResponse — full detail ───────────────────────────────────────────────

class AlertResponse(AlertSummary):
    """Full alert record — returned by GET /api/v1/alerts/{id}."""
    description: Optional[str]   = None
    resolved_at: Optional[datetime] = None
    updated_at:  Optional[datetime] = None


# ── AlertListResponse — paginated list wrapper ────────────────────────────────

class AlertListResponse(BaseModel):
    """Paginated envelope for GET /api/v1/alerts."""
    alerts: List[AlertSummary]
    total:  int = Field(..., description="Total records matching filters (before limit/offset)")
    limit:  int = Field(50,  description="Page size requested")
    offset: int = Field(0,   description="Page offset requested")


# ── AlertNearResponse — proximity search result ───────────────────────────────

class AlertNearResponse(AlertSummary):
    """Alert with computed distance — returned by GET /api/v1/alerts/near."""
    distance_km: float = Field(..., ge=0, description="Great-circle distance from query point in km")


# ── WebSocketAlertMessage — WS push envelope ─────────────────────────────────

class WebSocketAlertMessage(BaseModel):
    """
    Server → Client WebSocket message format.
    See: .ai/API_REFERENCE.md § 8. WebSocket Protocol
    event values: new_alert | update_alert | resolve_alert | ping
    """
    event: str                    = Field(..., description="Event type identifier")
    data:  Optional[AlertSummary] = None
