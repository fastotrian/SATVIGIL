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


# ── Legal & Evidentiary Dossier Schemas (MARPOL / Merchant Shipping Act) ──

class SatelliteSarEvidenceSchema(BaseModel):
    satellite: str = "Sentinel-1C C-SAR (IW Swath, VV/VH)"
    band: str = "C-band (5.405 GHz microwave)"
    acquisition_mode: str = "IW (Interferometric Wide Swath)"
    polarization: str = "Dual Polarization (VV + VH)"
    orbit_pass: str = "Relative Orbit Track #142 / Descending Node"
    scene_id: str = "S1C_IW_GRDH_1SDV_20260910T053649_20260910T053714_055591_06C82F_B7E2"
    slick_area_km2: float = 4.82
    slick_length_km: float = 8.4
    slick_width_max_km: float = 0.92
    est_volume_litres: int = 3850
    backscatter_clean_db: float = -12.1
    backscatter_slick_db: float = -19.5
    backscatter_delta_db: float = -7.4
    sar_image_url: str = "/sar_spill_bombay_high.jpg"


class CulpritVesselProfileSchema(BaseModel):
    name: str = "MT GUJARAT PRIDE"
    imo: str = "9418236"
    mmsi: str = "419082341"
    call_sign: str = "VTAA"
    flag_state: str = "India (Indian Registry)"
    flag_code: str = "IN"
    vessel_type: str = "Crude Oil / Chemical Tanker"
    gross_tonnage: int = 62450
    deadweight_tonnage: int = 115000
    build_year: int = 2018
    owner_operator: str = "Gujarat Maritime Shipping Corp., Mumbai / Kandla"
    last_port_of_call: str = "Fujairah Anchorage, UAE"
    destination: str = "JNPT, Mumbai, India"
    pre_incident_speed_kts: float = 12.4
    incident_speed_kts: float = 6.1
    course_deg: float = 174.0
    ais_gap_duration_minutes: int = 47


class AttributionMLBreakdownSchema(BaseModel):
    composite_confidence: float = 94.2
    spatial_proximity_score: float = 98.5
    ais_dark_gap_score: float = 96.0
    vessel_type_risk_score: float = 92.0
    svr_kinematics_anomaly_score: float = 90.5
    p_value: str = "< 0.001 (Statistically Significant)"


class StatutoryViolationSchema(BaseModel):
    statute: str
    regulation: str
    description: str


class PenalSanctionsSchema(BaseModel):
    detention_order: str = "Immediate Port State Control (PSC) Arrest at JNPT / Mumbai Port"
    statutory_fine_inr: str = "₹ 50,00,000 to ₹ 2,00,00,000"
    statutory_fine_usd: str = "$60,000 – $240,000 USD"
    cleanup_liability: str = "100% Comprehensive Ecological Remediation Cost Recovery"
    criminal_proceedings: str = "Lodging of FIR against Master & Ship Operator under Merchant Shipping Act Section 356K"


class ContainmentDirectiveSchema(BaseModel):
    dispersant_recommended: str = "Type 2/3 Concentrated Bio-dispersant (OSD-II)"
    dispersant_litres: int = 4200
    boom_perimeter_meters: int = 2800
    response_vessel: str = "ICGS Samudra Prahari (CG-01)"
    intercept_station: str = "ICG Regional HQ (West), Worli, Mumbai"
    intercept_course_deg: int = 248
    intercept_speed_kts: float = 18.0
    intercept_eta_hours: str = "2h 18m"


class LocationSchema(BaseModel):
    lat: float = 19.20
    lon: float = 71.50
    zone: str = "Arabian Sea — Mumbai High Offshore Sector (28 NM WNW)"
    eez_status: str = "Indian Exclusive Economic Zone (200 NM Sovereign Boundary)"


class ForensicDossierResponse(BaseModel):
    dossier_id: str = "ICG-DOS-2026-AR-0941"
    classification: str = "RESTRICTED // LAW ENFORCEMENT & MARITIME EVIDENCE"
    issuing_authority: str = "DIRECTORATE GENERAL OF SHIPPING / INDIAN COAST GUARD (WESTERN COMMAND)"
    incident_id: str = "SPILL-20260907-001"
    compiled_at: datetime
    evidence_sha256_hash: str = "7d8f5c3e91b24a6e804f519c23b8e714652a9103c847d1f5b630e2417c89a502"
    location: LocationSchema
    satellite_sar: SatelliteSarEvidenceSchema
    culprit_vessel: CulpritVesselProfileSchema
    attribution_ml: AttributionMLBreakdownSchema
    statutory_violations: List[StatutoryViolationSchema]
    penal_sanctions: PenalSanctionsSchema
    containment_directive: ContainmentDirectiveSchema


# ── INCOIS OOSA Ocean Drift Trajectory Simulation Schemas ──

class AssetImpactWarningSchema(BaseModel):
    asset_name: str
    asset_type: str  # "ONGC_PLATFORM" | "MPA_SANCTUARY" | "PORT" | "COASTLINE"
    distance_nm: float
    time_to_impact_hours: Optional[float] = None
    threat_level: str  # "HIGH" | "MEDIUM" | "WATCH"
    coordinates: List[float]  # [lon, lat]


class DriftStepForecastSchema(BaseModel):
    time_offset_hours: int
    forecast_time: datetime
    centroid_lat: float
    centroid_lon: float
    area_km2: float
    drift_speed_knots: float
    drift_heading_deg: float
    wind_speed_knots: float
    wind_heading_deg: float
    current_speed_knots: float
    current_heading_deg: float
    geojson_polygon: Dict[str, Any]
    active_warnings: List[AssetImpactWarningSchema] = []
    containment_recommendation: str


class SpillDriftForecastResponse(BaseModel):
    spill_id: str
    base_time: datetime
    initial_area_km2: float
    drift_model: str = "INCOIS-OOSA Fay Spreading + Arabian Sea Ocean Current Model"
    trajectory_points: List[Dict[str, Any]]
    steps: List[DriftStepForecastSchema]



