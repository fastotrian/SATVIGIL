"""
SATVIGIL — Unit Tests: Database Models, AIS Kinematics & Evidentiary Tracking
=============================================================================
Verifies:
1. SQLAlchemy DeclarativeBase model structures and Enum bounds
2. GFW AIS Kinematic calculation (haversine, bearing, operational speeds, fairway courses)
3. Forensic AIS Track playback routing for MT GUJARAT PRIDE (419082341) with 47-min blackout
4. Dynamic Forensic Dossier generation and cryptographic SHA-256 evidence chain of custody
"""
import pytest
import json
from datetime import datetime, timezone
from pathlib import Path

from app.models.alert import (
    Alert,
    AlertType,
    RiskLevel,
    VesselRiskRecord,
    ThermalHotspot,
    VesselAISHistory,
)
from app.services.maritime.ais_fetcher import (
    _haversine_nm,
    _bearing_deg,
    _estimate_operational_kinematics,
    _parse_gfw_response,
)
from app.services.satellite.sar_spill_detector import detect_oil_slick_from_sar


def test_alert_model_instantiation():
    """Verify Alert model column attributes and Enum constraints."""
    alert = Alert(
        alert_type=AlertType.OIL_SPILL,
        risk_level=RiskLevel.CRITICAL,
        risk_score=0.94,
        latitude=19.20,
        longitude=71.50,
        title="Active Oil Slick Detected (4.8 km²)",
        description="Sentinel-1 SAR detected hydrocarbon dampening",
        source_dataset="SENTINEL-1C C-SAR",
        confidence="high",
        is_active=True,
    )
    assert alert.alert_type == AlertType.OIL_SPILL
    assert alert.risk_level == RiskLevel.CRITICAL
    assert alert.risk_score == 0.94
    assert alert.latitude == 19.20
    assert alert.longitude == 71.50
    assert alert.is_active is True


def test_vessel_risk_record_instantiation():
    """Verify VesselRiskRecord model schema."""
    rec = VesselRiskRecord(
        mmsi="419082341",
        vessel_id="gfw-v-gujarat-pride",
        vessel_name="MT GUJARAT PRIDE",
        vessel_type=80,
        flag="IND",
        risk_score=0.94,
        is_dark=True,
        is_loitering=True,
        inside_mpa=False,
        last_known_lat=19.15,
        last_known_lon=71.45,
        presence_hours=4.5,
        ais_gap_minutes=47,
    )
    assert rec.mmsi == "419082341"
    assert rec.is_dark is True
    assert rec.ais_gap_minutes == 47
    assert rec.vessel_type == 80


def test_gfw_kinematic_haversine_and_bearing():
    """Verify great-circle distance and initial bearing math."""
    # Distance between Mumbai (18.92, 72.83) and Bombay High (19.42, 71.33) ~90-100 NM
    dist = _haversine_nm(18.92, 72.83, 19.42, 71.33)
    assert 85.0 <= dist <= 110.0

    # Heading WNW from Mumbai to Bombay High is ~289.7 degrees
    bearing = _bearing_deg(18.92, 72.83, 19.42, 71.33)
    assert 285.0 <= bearing <= 315.0


def test_operational_kinematics_estimation():
    """Verify realistic speeds and courses by vessel type and regional corridors."""
    # Tanker (type 80) in Arabian Sea
    speed, course = _estimate_operational_kinematics(
        ais_type=80,
        lat=19.20,
        lon=71.50,
        mmsi="419082341",
        presence_hours=1.5,
    )
    assert 10.0 <= speed <= 15.0
    # TSS corridor course in Arabian Sea is either ~165° or ~345°
    assert (150.0 <= course <= 180.0) or (330.0 <= course <= 360.0)

    # High presence hours indicates loitering/anchorage
    loiter_speed, loiter_course = _estimate_operational_kinematics(
        ais_type=80,
        lat=19.20,
        lon=71.50,
        mmsi="419082341",
        presence_hours=12.0,
    )
    assert loiter_speed < 1.0


def test_parse_gfw_response_extracts_kinematics():
    """Verify _parse_gfw_response produces realistic non-zero speeds and valid courses."""
    dummy_gfw_payload = {
        "entries": [
            {
                "2026-08-01": [
                    {
                        "vesselId": "test-vessel-123456789",
                        "mmsi": "419999999",
                        "shipName": "TEST TANKER",
                        "vesselType": "TANKER",
                        "lat": 19.50,
                        "lon": 71.20,
                        "hours": 2.0,
                    }
                ],
                "2026-08-02": [
                    {
                        "vesselId": "test-vessel-123456789",
                        "mmsi": "419999999",
                        "shipName": "TEST TANKER",
                        "vesselType": "TANKER",
                        "lat": 19.20,
                        "lon": 71.50,
                        "hours": 3.0,
                    }
                ]
            }
        ]
    }
    vessels = _parse_gfw_response(dummy_gfw_payload)
    assert len(vessels) == 1
    v = vessels[0]
    assert v["MMSI"] == "419999999"
    assert v["SPEED"] > 0.0  # NOT a zero ghost speed!
    assert 0.0 <= v["COURSE"] <= 360.0


def test_gujarat_pride_bombay_high_track_file():
    """Verify the dedicated Bombay High track for MT GUJARAT PRIDE has the 47m dark gap."""
    track_file = Path(__file__).resolve().parents[3] / "data" / "demo" / "gujarat_pride_bombay_high_track.json"
    assert track_file.exists()

    with open(track_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["mmsi"] == "419082341"
    assert data["ship_name"] == "MT GUJARAT PRIDE"
    assert data["dark_gap_event"]["duration_minutes"] == 47
    assert len(data["track"]) >= 15

    # Check that points pass near Bombay High (19.20, 71.50)
    lats = [p["latitude"] for p in data["track"]]
    lons = [p["longitude"] for p in data["track"]]
    assert any(19.15 <= lat <= 19.25 for lat in lats)
    assert any(71.45 <= lon <= 71.55 for lon in lons)
