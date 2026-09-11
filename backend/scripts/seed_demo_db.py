"""
SATVIGIL — Production / Demo Database Seeding Script
====================================================
Initializes PostgreSQL + PostGIS schemas and seeds realistic maritime,
thermal hotspot, and pollution incident data into PostGIS tables.

Usage:
  cd backend
  python scripts/seed_demo_db.py
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, func
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.alert import (
    Alert,
    AlertType,
    RiskLevel,
    VesselRiskRecord,
    ThermalHotspot,
    CPCBPollutedArea,
)
from app.services.satellite.sar_spill_detector import detect_oil_slick_from_sar


async def seed_database():
    print("=" * 70)
    print("SATVIGIL PostGIS Database Initializer & Seeder")
    print("=" * 70)

    # 1. Test database connectivity and create tables
    try:
        print("[1/4] Connecting to PostgreSQL/PostGIS engine...")
        async with engine.begin() as conn:
            # Enable PostGIS extension if superuser permits
            try:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                print("      + PostGIS extension verified.")
            except Exception as ext_err:
                print(f"      - PostGIS extension note: {ext_err}")

            print("      + Creating tables from DeclarativeBase metadata...")
            await conn.run_sync(Base.metadata.create_all)
            print("      + Tables created successfully.")
    except Exception as e:
        print(f"\n[ERROR] Database connection failed: {e}")
        print("Note: If PostgreSQL is not running locally, SATVIGIL automatically runs")
        print("with high-fidelity in-memory caching and demo fallback providers.\n")
        return

    now = datetime.now(timezone.utc)

    # 2. Run SAR detector to get genuine backscatter & slick metrics
    print("\n[2/4] Executing Copernicus Sentinel-1 SAR Detection Pipeline for Bombay High...")
    sar_detection = detect_oil_slick_from_sar(center_lat=19.20, center_lon=71.50)
    slick_area = round(float(sar_detection.get("slick_area_km2", 4.82)), 2)
    conf = round(float(sar_detection.get("detection_confidence", 0.94)), 2)
    scene_id = sar_detection.get("scene_id", "S1C_IW_GRDH_1SDV_20260910T053649")
    print(f"      + Detected slick area: {slick_area} km² | Confidence: {conf * 100:.1f}%")
    print(f"      + SAR Scene ID: {scene_id}")

    # 3. Seed Alerts
    print("\n[3/4] Seeding core operational alerts...")
    async with AsyncSessionLocal() as session:
        # Check if alerts already exist
        existing_alerts = (await session.execute(select(func.count(Alert.id)))).scalar_one()
        if existing_alerts > 0:
            print(f"      + Found {existing_alerts} existing alerts in database. Skipping duplicate seed.")
        else:
            alerts_to_insert = [
                Alert(
                    alert_type=AlertType.OIL_SPILL,
                    risk_level=RiskLevel.CRITICAL,
                    risk_score=conf,
                    latitude=19.20,
                    longitude=71.50,
                    title=f"Active Oil Slick Detected ({slick_area} km²)",
                    description=(
                        f"Sentinel-1 C-SAR IW GRDH detected hydrocarbon surface dampening "
                        f"near Bombay High (delta sigma0: -7.4 dB). Correlated with MT GUJARAT PRIDE track."
                    ),
                    source_dataset="SENTINEL-1C C-SAR",
                    confidence="high",
                    is_active=True,
                ),
                Alert(
                    alert_type=AlertType.OIL_SPILL,
                    risk_level=RiskLevel.CRITICAL,
                    risk_score=0.94,
                    latitude=19.15,
                    longitude=71.45,
                    title="AIS Transponder Off: MT GUJARAT PRIDE (47m blackout)",
                    description="Vessel transponder blackout during passage across Bombay High oil field.",
                    source_dataset="GFW AIS",
                    confidence="high",
                    is_active=True,
                ),
                Alert(
                    alert_type=AlertType.ILLEGAL_FISHING,
                    risk_level=RiskLevel.HIGH,
                    risk_score=0.78,
                    latitude=22.50,
                    longitude=69.20,
                    title="Protected Area Breach: FV KUTCH FISHERMAN",
                    description="Mechanized fishing vessel operating inside Gulf of Kutch Marine National Park sanctuary boundary.",
                    source_dataset="GFW AIS",
                    confidence="nominal",
                    is_active=True,
                ),
                Alert(
                    alert_type=AlertType.FIRE_GAS_FLARE,
                    risk_level=RiskLevel.MEDIUM,
                    risk_score=0.62,
                    latitude=19.38,
                    longitude=71.33,
                    title="Offshore Gas Flare Detected: Bombay High Platform (FRP 42.5 MW)",
                    description="Continuous flare emission observed by NOAA-20 / VIIRS thermal sensor.",
                    source_dataset="NASA FIRMS",
                    confidence="high",
                    is_active=True,
                ),
                Alert(
                    alert_type=AlertType.INDUSTRIAL_POLLUTION,
                    risk_level=RiskLevel.HIGH,
                    risk_score=0.81,
                    latitude=21.62,
                    longitude=73.01,
                    title="Industrial Thermal Emission: CPCB Ankleshwar Cluster",
                    description="Severe thermal cluster emission within CPCB Critically Polluted Industrial Zone.",
                    source_dataset="NASA FIRMS",
                    confidence="high",
                    is_active=True,
                ),
            ]
            for a in alerts_to_insert:
                session.add(a)
            await session.commit()
            print(f"      + Inserted {len(alerts_to_insert)} production alert records.")

        # 4. Seed Vessel Risk Records
        print("\n[4/4] Seeding initial Vessel Risk Records...")
        existing_vessels = (await session.execute(select(func.count(VesselRiskRecord.id)))).scalar_one()
        if existing_vessels > 0:
            print(f"      + Found {existing_vessels} existing vessel records. Skipping duplicate seed.")
        else:
            vessels_to_insert = [
                VesselRiskRecord(
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
                ),
                VesselRiskRecord(
                    mmsi="419000003",
                    vessel_id="gfw-v-kutch-fisherman",
                    vessel_name="FV KUTCH FISHERMAN",
                    vessel_type=30,
                    flag="IND",
                    risk_score=0.78,
                    is_dark=False,
                    is_loitering=True,
                    inside_mpa=True,
                    last_known_lat=22.50,
                    last_known_lon=69.20,
                    presence_hours=8.2,
                    ais_gap_minutes=20,
                ),
                VesselRiskRecord(
                    mmsi="419001845",
                    vessel_id="gfw-v-419001-kutch-tanker",
                    vessel_name="MV KUTCH EXPLORER",
                    vessel_type=80,
                    flag="IND",
                    risk_score=0.35,
                    is_dark=False,
                    is_loitering=False,
                    inside_mpa=False,
                    last_known_lat=22.967,
                    last_known_lon=70.230,
                    presence_hours=1.2,
                    ais_gap_minutes=0,
                ),
            ]
            for v in vessels_to_insert:
                session.add(v)
            await session.commit()
            print(f"      + Inserted {len(vessels_to_insert)} vessel risk records.")

    print("\n" + "=" * 70)
    print("Database seeding completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_database())
