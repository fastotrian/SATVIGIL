"""
SATVIGIL — Database Models
One unified Alert model + module-specific detail tables.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum, JSON
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import enum
from app.core.database import Base


class AlertType(str, enum.Enum):
    OIL_SPILL = "oil_spill"
    ILLEGAL_FISHING = "illegal_fishing"
    FIRE_INDUSTRIAL = "fire_industrial"
    FIRE_WILDFIRE = "fire_wildfire"
    FIRE_STUBBLE = "fire_stubble"
    FIRE_GAS_FLARE = "fire_gas_flare"
    FIRE_MINING = "fire_mining"
    INDUSTRIAL_POLLUTION = "industrial_pollution"
    LANDSLIDE_RISK = "landslide_risk"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """Core alert record — one row per detected event."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    risk_score = Column(Float, nullable=False)          # 0.0 – 1.0

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326))     # PostGIS spatial column

    title = Column(String(255), nullable=False)
    description = Column(Text)
    source_dataset = Column(String(100))                # "FIRMS", "AIS", "SENTINEL"
    confidence = Column(String(20))                     # "low" | "nominal" | "high"

    is_active = Column(Boolean, default=True)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VesselRiskRecord(Base):
    """Vessel behavior risk scoring record (maritime module)."""
    __tablename__ = "vessel_risk_records"

    id = Column(Integer, primary_key=True)
    mmsi = Column(String(20), nullable=False, index=True)  # Vessel ID
    vessel_id = Column(String(50))                         # Internal or external vessel tracking ID
    vessel_name = Column(String(255))
    vessel_type = Column(String(100))
    flag = Column(String(50))                              # Country flag
    risk_score = Column(Float)
    is_dark = Column(Boolean, default=False)               # AIS transponder off
    is_loitering = Column(Boolean, default=False)
    inside_mpa = Column(Boolean, default=False)            # Marine Protected Area
    last_known_lat = Column(Float)
    last_known_lon = Column(Float)
    presence_hours = Column(Float)                         # Hours present in monitoring zone
    ais_gap_minutes = Column(Integer)                      # How long AIS was off
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class ThermalHotspot(Base):
    """FIRMS thermal detection record — used for both fire and pollution modules."""
    __tablename__ = "thermal_hotspots"

    id = Column(Integer, primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326))
    frp = Column(Float)                                    # Fire Radiative Power (MW)
    brightness = Column(Float)
    confidence = Column(String(20))
    satellite = Column(String(50))
    acquired_at = Column(DateTime(timezone=True), nullable=False)
    fire_type = Column(String(50))                         # classified type
    classification_reason = Column(Text)                   # Reason for classification (e.g. from CPCB)
    land_use = Column(String(100))                         # from OSM
    near_cpcb_cluster = Column(Boolean, default=False)
    recurrence_count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VesselAISHistory(Base):
    """Continuous Lat/Long trace for a specific vessel."""
    __tablename__ = "vessel_ais_history"

    id = Column(Integer, primary_key=True)
    mmsi = Column(String(20), nullable=False, index=True)
    vessel_id = Column(String(50))
    ship_name = Column(String(255))
    flag = Column(String(50))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326))
    presence_hours = Column(Float)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class CPCBPollutedArea(Base):
    """CPCB Flagged Critical Polluted Areas."""
    __tablename__ = "cpcb_polluted_areas"

    id = Column(Integer, primary_key=True)
    center_lat = Column(Float, nullable=False)
    center_lon = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326))
    region_radius = Column(Float)                          # Radius in meters or km
    recurring_causes = Column(JSON)                        # List of causes for recurring fire
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LandslideRiskZone(Base):
    """Landslide Detection - Region Covering Polygon Coordinates and Risk Zone metadata."""
    __tablename__ = "landslide_risk_zones"

    id = Column(Integer, primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    polygon_coordinates = Column(Geometry("POLYGON", srid=4326))
    slope = Column(Float)
    elevation = Column(Float)
    moisture = Column(Float)
    distance_to_road = Column(Float)
    distance_to_river = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LandslideMonitoringZone(Base):
    """Landslide Detection - Monitoring Zone kinematics."""
    __tablename__ = "landslide_monitoring_zones"

    id = Column(Integer, primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(Geometry("POINT", srid=4326))
    time_range = Column(String(100))
    displacement = Column(Float)
    velocity = Column(Float)
    acceleration = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
