"""
SATVIGIL — Maritime Module: AIS Background Worker
Ingests AIS data, computes gap duration, inserts to PostGIS, and broadcasts alerts.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
import structlog
import uuid

from app.models.alert import VesselRiskRecord, Alert, AlertType, RiskLevel
from app.services.maritime.ais_fetcher import fetch_ais_vessels
from app.core.database import AsyncSessionLocal
from app.api.routes.alerts import manager
from app.schemas.alert import AlertSummary

logger = structlog.get_logger()

async def run_ais_ingest():
    """
    Background worker that runs every 15 minutes.
    Fetches AIS, updates vessel_risk_records, creates alerts, and broadcasts.
    """
    vessels = await fetch_ais_vessels()
    if not vessels:
        logger.warning("ais_worker_empty")
        return

    now = datetime.now(timezone.utc)
    new_alerts = []

    async with AsyncSessionLocal() as db:
        try:
            for v in vessels:
                mmsi = str(v.mmsi)
                # Check for existing record to calculate gap
                stmt = select(VesselRiskRecord).where(VesselRiskRecord.mmsi == mmsi).order_by(VesselRiskRecord.recorded_at.desc()).limit(1)
                last_record = (await db.execute(stmt)).scalar_one_or_none()
                
                ais_gap_minutes = 0
                if last_record and last_record.recorded_at:
                    # ensure tz-aware
                    last_time = last_record.recorded_at
                    if last_time.tzinfo is None:
                        last_time = last_time.replace(tzinfo=timezone.utc)
                    delta = now - last_time
                    ais_gap_minutes = int(delta.total_seconds() / 60)
                
                # We update the vessel risk object with gap
                v.ais_gap_minutes = ais_gap_minutes
                # Basic rule: if gap > 45 mins, it's considered dark
                if ais_gap_minutes > 45:
                    v.is_dark = True
                
                # Insert to vessel_risk_records
                point = f"SRID=4326;POINT({v.last_known_lon} {v.last_known_lat})"
                record = VesselRiskRecord(
                    mmsi=mmsi,
                    vessel_id=v.vessel_id,
                    vessel_name=v.vessel_name,
                    vessel_type=v.vessel_type,
                    flag=v.flag,
                    risk_score=v.risk_score,
                    is_dark=v.is_dark,
                    is_loitering=v.is_loitering,
                    inside_mpa=v.inside_mpa,
                    last_known_lat=v.last_known_lat,
                    last_known_lon=v.last_known_lon,
                    ais_gap_minutes=v.ais_gap_minutes,
                    recorded_at=now
                )
                db.add(record)
                
                # Create alert if risk > 0.7 or inside MPA
                if v.risk_score > 0.7 or v.inside_mpa:
                    alert = Alert(
                        alert_type=AlertType.ILLEGAL_FISHING if v.inside_mpa else AlertType.OIL_SPILL,
                        risk_level=RiskLevel.CRITICAL if v.risk_score > 0.8 else RiskLevel.HIGH,
                        risk_score=v.risk_score,
                        latitude=v.last_known_lat,
                        longitude=v.last_known_lon,
                        location=point,
                        title=f"High Risk Vessel Activity: {v.vessel_name}",
                        description=f"Vessel {v.vessel_name} (MMSI: {mmsi}) flagged with score {v.risk_score}. Dark gap: {v.ais_gap_minutes}m.",
                        source_dataset="AIS",
                        confidence="high",
                        is_active=True,
                        created_at=now
                    )
                    db.add(alert)
                    new_alerts.append(alert)

            await db.commit()
            
            # Broadcast new alerts after commit (to have IDs)
            for alert in new_alerts:
                await manager.broadcast({
                    "event": "new_alert",
                    "data": AlertSummary.model_validate(alert).model_dump(mode="json")
                })
                
            logger.info("ais_worker_success", processed=len(vessels), new_alerts=len(new_alerts))
        except Exception as e:
            await db.rollback()
            logger.error("ais_worker_failed", error=str(e))
