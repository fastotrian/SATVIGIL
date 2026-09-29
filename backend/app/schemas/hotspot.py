"""
SATVIGIL — Thermal Hotspot Pydantic v2 Schemas
Mirrors: backend/app/models/alert.py  →  ThermalHotspot table (NASA FIRMS data)
Grounded in: scripts/india_fire_intelligence_v2 (1).py
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, List, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alert import Latitude, Longitude


# ── FireType enum ─────────────────────────────────────────────────────────────

class FireType(str, enum.Enum):
    """
    Fire intelligence classifier output categories.
    Matches fire_type column values in ThermalHotspot.
    """
    INDUSTRIAL = "industrial"
    GAS_FLARE  = "gas_flare"
    WILDFIRE   = "wildfire"
    STUBBLE    = "stubble"
    MINING     = "mining"
    UNKNOWN    = "unknown"


# ── ThermalHotspotSchema — full hotspot record ────────────────────────────────

class ThermalHotspotSchema(BaseModel):
    """
    Full thermal hotspot record — returned by:
      GET /api/v1/fire/hotspots         (inside HotspotListResponse)
      GET /api/v1/fire/recurrence       (hotspots with recurrence_count > threshold)
      GET /api/v1/pollution/clusters    (CPCB-adjacent hotspots)
    """
    model_config = ConfigDict(from_attributes=True)

    id:                 int
    latitude:           Latitude
    longitude:          Longitude

    # ── FIRMS sensor data ──────────────────────────────────────────────────────
    frp:                Optional[float] = Field(
        None, ge=0, description="Fire Radiative Power in megawatts (MW)"
    )
    brightness:         Optional[float] = Field(
        None, description="Brightness temperature in Kelvin"
    )
    confidence:         Optional[str]   = Field(
        None, description="FIRMS detection confidence: low | nominal | high"
    )
    satellite:          Optional[str]   = Field(
        None, description="Source sensor: VIIRS | MODIS | etc."
    )
    acquired_at:        datetime         = Field(
        ..., description="Satellite overpass time (UTC)"
    )

    # ── Classification output ──────────────────────────────────────────────────
    fire_type:          Optional[FireType] = Field(
        None, description="Classified fire category"
    )
    classification_score: Optional[float] = Field(
        None, description="Numeric confidence score from V2 engine (0-100)"
    )
    classification_reason: Optional[str] = Field(
        None, description="Reason for classification"
    )
    land_use:           Optional[str]   = Field(
        None, description="Land-use category"
    )
    near_cpcb_cluster:  bool            = Field(
        False, description="True if within 15 km of a CPCB-designated polluted industrial cluster"
    )
    cpcb_cpa_name:      Optional[str]   = Field(
        None, description="Name of the nearest CPCB Critically Polluted Area"
    )
    recurrence_count:   int             = Field(
        1, ge=1, description="Number of times this spatial grid cell has fired"
    )
    recurrence_cluster_id: Optional[int] = Field(
        None, description="DBSCAN recurrence cluster ID"
    )
    created_at:         datetime

    # ── Enriched statutory enforcement fields ─────────────────────────────────
    responding_agency:    Optional[str] = Field(
        None,
        description="Agency responsible for enforcement (e.g. CAQM, State Forest Dept, CPCB, PESO, IBM)"
    )
    recommended_action:   Optional[str] = Field(
        None,
        description="Recommended statutory enforcement action per Indian environmental acts"
    )


# ── HotspotListResponse — paginated wrapper ───────────────────────────────────

class HotspotListResponse(BaseModel):
    """Paginated envelope for GET /api/v1/fire/hotspots."""
    hotspots: List[ThermalHotspotSchema]
    total:    int  = Field(..., description="Total hotspot records before pagination")
    limit:    int  = Field(50,  description="Page size requested")
    offset:   int  = Field(0,   description="Page offset requested")


class HotspotNearResponse(ThermalHotspotSchema):
    """Hotspot with computed distance — returned by GET /api/v1/alerts/near."""
    distance_km: float = Field(..., ge=0, description="Great-circle distance from query point in km")


class CPCBRecurringHotspotSchema(BaseModel):
    """Recurring pollution cluster associated with a CPCB CPA (Critically Polluted Area)."""
    cpcb_cpa_name:          str
    recurrence_cluster_id:  int
    detection_count:        int
    center_lat:             float
    center_lon:             float
    dominant_fire_type:     str
    first_seen:             Optional[datetime] = None
    last_seen:              Optional[datetime] = None
    avg_frp:                float
    max_frp:                float
    avg_confidence:         float


class FireStatsResponse(BaseModel):
    """High-level intelligence summary for the Thermal Zone command center."""
    total_hotspots:         int
    by_fire_type:           Dict[str, int]
    recurring_clusters:     int
    cpcb_cpa_associated:    int
    sensor:                 str = "NASA VIIRS NRT"
    data_source:            str = "LIVE_FIRMS"
