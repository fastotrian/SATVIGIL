"""
SATVIGIL — Fire Module: FIRMS Database Processor
Responsible for taking fetched FIRMS data and upserting into the PostGIS database.
"""
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import structlog
from datetime import datetime

from app.models.alert import ThermalHotspot
from app.services.fire.firms_fetcher import classify_fire, is_near_cpcb_cluster

logger = structlog.get_logger()

async def ingest_firms_batch(df: pd.DataFrame, db: AsyncSession):
    """
    Process a pandas DataFrame of FIRMS thermal detections and upsert to PostGIS.
    Records are unique on (latitude, longitude, acquired_at).
    """
    if df is None or df.empty:
        logger.info("firms_ingest_empty", msg="No FIRMS data to ingest.")
        return 0

    inserted_count = 0
    
    for _, row in df.iterrows():
        lat = row.get("latitude")
        lon = row.get("longitude")
        
        # FIRMS data has acq_date and acq_time
        acq_date = str(row.get("acq_date", ""))
        acq_time = str(row.get("acq_time", "")).zfill(4) # Ensure 4 digits e.g. "0420"
        
        try:
            acquired_at = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")
        except ValueError:
            # Fallback
            acquired_at = datetime.utcnow()
            
        near_cpcb, _ = is_near_cpcb_cluster(lat, lon)
        # We need OSM land use theoretically, but for now we fallback to 'unknown' 
        # or mock it if we don't have the OSM pipeline ready.
        # Here we just pass unknown and let classify_fire use the CPCB/FRP fallback.
        fire_type = classify_fire(row, land_use="unknown")
        
        point = f"SRID=4326;POINT({lon} {lat})"
        
        stmt = insert(ThermalHotspot).values(
            latitude=lat,
            longitude=lon,
            location=point,
            frp=row.get("frp"),
            brightness=row.get("bright_ti4") or row.get("brightness"),
            confidence=row.get("confidence", "nominal"),
            satellite=row.get("satellite", "VIIRS"),
            acquired_at=acquired_at,
            fire_type=fire_type,
            land_use="unknown",
            near_cpcb_cluster=near_cpcb,
            recurrence_count=1 # Default, will be updated by recurrence tracker
        )
        
        # On conflict do nothing for (latitude, longitude, acquired_at)
        # Note: We need a unique constraint in the DB for this to work natively.
        # If no constraint exists, we can use a select/insert pattern.
        # Since alembic isn't set up yet, we'll do a safe manual check to avoid Duplicate errors if constraint is missing.
        
        from sqlalchemy import select
        check_stmt = select(ThermalHotspot.id).where(
            ThermalHotspot.latitude == lat,
            ThermalHotspot.longitude == lon,
            ThermalHotspot.acquired_at == acquired_at
        )
        
        existing = (await db.execute(check_stmt)).scalar_one_or_none()
        
        if not existing:
            db.add(ThermalHotspot(
                latitude=lat,
                longitude=lon,
                location=point,
                frp=row.get("frp"),
                brightness=row.get("bright_ti4") or row.get("brightness"),
                confidence=row.get("confidence", "nominal"),
                satellite=row.get("satellite", "VIIRS"),
                acquired_at=acquired_at,
                fire_type=fire_type,
                land_use="unknown",
                near_cpcb_cluster=near_cpcb,
                recurrence_count=1
            ))
            inserted_count += 1
            
    try:
        await db.commit()
        logger.info("firms_ingest_success", inserted=inserted_count)
    except Exception as e:
        await db.rollback()
        logger.error("firms_ingest_failed", error=str(e))
        
    return inserted_count
