"""
SATVIGIL — schemas package
Re-exports all Pydantic v2 request/response models for use by API routes.

Usage:
    from app.schemas import AlertListResponse, VesselSchema, ThermalHotspotSchema
"""

# ── Alert schemas ──────────────────────────────────────────────────────────────
from app.schemas.alert import (
    AlertType,
    RiskLevel,
    RiskScore,
    Latitude,
    Longitude,
    AlertSummary,
    AlertResponse,
    AlertListResponse,
    AlertNearResponse,
    WebSocketAlertMessage,
)

# ── Vessel & Spill schemas ─────────────────────────────────────────────────────
from app.schemas.vessel import (
    VesselSchema,
    SpillAlertSchema,
    VesselListResponse,
)

# ── Thermal Hotspot schemas ────────────────────────────────────────────────────
from app.schemas.hotspot import (
    FireType,
    ThermalHotspotSchema,
    HotspotListResponse,
)

__all__ = [
    # alert
    "AlertType",
    "RiskLevel",
    "RiskScore",
    "Latitude",
    "Longitude",
    "AlertSummary",
    "AlertResponse",
    "AlertListResponse",
    "AlertNearResponse",
    "WebSocketAlertMessage",
    # vessel
    "VesselSchema",
    "SpillAlertSchema",
    "VesselListResponse",
    # hotspot
    "FireType",
    "ThermalHotspotSchema",
    "HotspotListResponse",
]

# -- Spatial schemas -----------------------------------------------------------
from app.schemas.spatial import SpatialRadiusResponse
from app.schemas.vessel import VesselNearResponse
from app.schemas.hotspot import HotspotNearResponse

__all__.extend([
    "SpatialRadiusResponse",
    "VesselNearResponse",
    "HotspotNearResponse"
])
