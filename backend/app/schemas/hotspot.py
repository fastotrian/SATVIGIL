"""
SATVIGIL — Thermal Hotspot Pydantic v2 Schemas
Mirrors: backend/app/models/alert.py  →  ThermalHotspot table (NASA FIRMS data)

Schema list:
  FireType             — classified fire category enum
  ThermalHotspotSchema — full hotspot record + 2 enriched API-layer fields
  HotspotListResponse  — paginated wrapper for GET /api/v1/fire/hotspots
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.alert import Latitude, Longitude


# ── FireType enum ─────────────────────────────────────────────────────────────

class FireType(str, enum.Enum):
    """
    XGBoost classifier output categories.
    Matches fire_type column values in ThermalHotspot.
    Also aligns with AlertType values (e.g. FIRE_INDUSTRIAL → 'industrial').
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

    responding_agency and recommended_action are NOT stored in the DB;
    they are computed at the service/route layer by the fire classifier's
    agency routing table (see services/fire/firms_fetcher.py) and passed in.
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
        None, description="XGBoost-classified fire category"
    )
    land_use:           Optional[str]   = Field(
        None, description="Land-use category from OpenStreetMap"
    )
    near_cpcb_cluster:  bool            = Field(
        False, description="True if within 10 km of a CPCB-designated polluted industrial cluster"
    )
    recurrence_count:   int             = Field(
        1, ge=1, description="Number of times this grid cell has fired (rolling 30-day window)"
    )
    created_at:         datetime

    # ── Enriched fields (computed at API layer, not stored in DB) ─────────────
    responding_agency:    Optional[str] = Field(
        None,
        description=(
            "Agency responsible for response, derived from fire type + land use. "
            "e.g. 'CPCB + State Fire Services' for industrial fires near CPCB clusters."
        )
    )
    recommended_action:   Optional[str] = Field(
        None,
        description=(
            "Recommended response action. "
            "e.g. 'Emergency response + PESO investigation' for gas flares."
        )
    )


# ── HotspotListResponse — paginated wrapper ───────────────────────────────────

class HotspotListResponse(BaseModel):
    """Paginated envelope for GET /api/v1/fire/hotspots."""
    hotspots: List[ThermalHotspotSchema]
    total:    int  = Field(..., description="Total hotspot records before pagination")
    limit:    int  = Field(50,  description="Page size requested")
    offset:   int  = Field(0,   description="Page offset requested")

# -- HotspotNearResponse � proximity search result -----------------------------

class HotspotNearResponse(ThermalHotspotSchema):
    """Hotspot with computed distance � returned by GET /api/v1/alerts/near."""
    distance_km: float = Field(..., ge=0, description="Great-circle distance from query point in km")
