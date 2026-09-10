"""
SATVIGIL — Maritime Module: AIS Background Worker
Ingests GFW/AISHub vessel dicts, computes AIS gap duration,
inserts to PostGIS vessel_risk_records, and broadcasts WebSocket alerts.

NOTE: fetch_ais_vessels() returns LIST OF DICTS (not VesselResponse objects).
      All access uses dict.get() — never attribute access.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    Background worker — runs every 15 minutes via scheduler.py.

    Pipeline:
      1. Fetch vessels from GFW (or AISHub fallback) as list of dicts
      2. For each vessel, calculate AIS gap from last DB record
      3. Insert new VesselRiskRecord row to PostGIS
      4. Create Alert if risk > 0.7 or vessel is inside MPA
      5. Broadcast new alerts over WebSocket
    """
    vessels = await fetch_ais_vessels()
    if not vessels:
        logger.warning("ais_worker_empty", hint="All AIS sources returned empty — check GFW token")
        return

    now = datetime.now(timezone.utc)
    new_alerts = []

    async with AsyncSessionLocal() as db:
        try:
            for v in vessels:
                # ── Dict access (v is a dict, NOT a VesselResponse object) ──
                mmsi        = str(v.get("MMSI") or v.get("mmsi") or "")
                vessel_name = str(v.get("NAME") or v.get("name") or "Unknown Vessel").strip()
                vessel_type = int(v.get("TYPE") or v.get("vessel_type") or 0)
                flag        = str(v.get("flag") or "")
                lat         = float(v.get("LATITUDE") or v.get("lat") or 0.0)
                lon         = float(v.get("LONGITUDE") or v.get("lon") or 0.0)
                risk_score  = float(v.get("risk_score") or 0.0)
                gfw_id      = str(v.get("gfw_vessel_id") or "")

                if not mmsi:
                    continue  # skip vessels without MMSI

                # ── Calculate AIS gap from last DB record ──────────────────
                stmt = (
                    select(VesselRiskRecord)
                    .where(VesselRiskRecord.mmsi == mmsi)
                    .order_by(VesselRiskRecord.recorded_at.desc())
                    .limit(1)
                )
                last_record = (await db.execute(stmt)).scalar_one_or_none()

                ais_gap_minutes = 0
                if last_record and last_record.recorded_at:
                    last_time = last_record.recorded_at
                    if last_time.tzinfo is None:
                        last_time = last_time.replace(tzinfo=timezone.utc)
                    delta = now - last_time
                    ais_gap_minutes = int(delta.total_seconds() / 60)

                is_dark     = ais_gap_minutes > 45
                is_loitering = False  # GFW presence data doesn't give instantaneous speed
                inside_mpa  = bool(v.get("in_mpa") or False)

                # ── Re-score if we now know the gap ───────────────────────
                # Import here to avoid circular; calculate_vessel_risk_score
                # accepts the raw dict with LATITUDE/LONGITUDE keys
                from app.services.maritime.ais_fetcher import calculate_vessel_risk_score
                risk_score = calculate_vessel_risk_score(v, ais_gap_minutes=ais_gap_minutes)

                # ── Insert VesselRiskRecord to PostGIS ────────────────────
                point_wkt = f"SRID=4326;POINT({lon} {lat})"
                record = VesselRiskRecord(
                    mmsi=mmsi,
                    vessel_id=gfw_id or mmsi,
                    vessel_name=vessel_name,
                    vessel_type=vessel_type,
                    flag=flag,
                    risk_score=risk_score,
                    is_dark=is_dark,
                    is_loitering=is_loitering,
                    inside_mpa=inside_mpa,
                    last_known_lat=lat,
                    last_known_lon=lon,
                    ais_gap_minutes=ais_gap_minutes,
                    recorded_at=now,
                )
                db.add(record)

                # ── Create Alert if high risk ─────────────────────────────
                if risk_score > 0.7 or inside_mpa:
                    alert_type = AlertType.ILLEGAL_FISHING if inside_mpa else AlertType.OIL_SPILL
                    risk_level = RiskLevel.CRITICAL if risk_score > 0.8 else RiskLevel.HIGH
                    alert = Alert(
                        alert_type=alert_type,
                        risk_level=risk_level,
                        risk_score=risk_score,
                        latitude=lat,
                        longitude=lon,
                        location=point_wkt,
                        title=f"High Risk Vessel: {vessel_name}",
                        description=(
                            f"Vessel {vessel_name} (MMSI: {mmsi}) risk score {risk_score:.2f}. "
                            f"AIS gap: {ais_gap_minutes}min. "
                            f"{'⚠ Dark vessel. ' if is_dark else ''}"
                            f"{'📍 Inside MPA.' if inside_mpa else ''}"
                        ),
                        source_dataset="GFW",
                        confidence="high",
                        is_active=True,
                        created_at=now,
                    )
                    db.add(alert)
                    new_alerts.append(alert)

            await db.commit()

            # ── Broadcast alerts over WebSocket ───────────────────────────
            for alert in new_alerts:
                try:
                    await manager.broadcast({
                        "event": "new_alert",
                        "data": AlertSummary.model_validate(alert).model_dump(mode="json"),
                    })
                except Exception as ws_err:
                    logger.warning("alert_broadcast_failed", error=str(ws_err))

            logger.info(
                "ais_worker_success",
                processed=len(vessels),
                new_alerts=len(new_alerts),
            )

        except Exception as e:
            await db.rollback()
            logger.error("ais_worker_failed", error=str(e))
            raise
