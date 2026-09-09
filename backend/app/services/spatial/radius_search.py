"""
SATVIGIL — Spatial Radius Search Service
Executes parallel ST_DWithin geography queries for alerts, vessels, and hotspots.
"""
import asyncio
from typing import Tuple, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast
from geoalchemy2 import Geography

from app.models.alert import Alert, VesselRiskRecord, ThermalHotspot

async def get_entities_near_point(
    db: AsyncSession,
    lat: float,
    lon: float,
    radius_km: float
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Finds alerts, vessels, and hotspots within a given radius using PostGIS ST_DWithin.
    Returns three lists of dicts, sorted by distance_km.
    """
    radius_m = radius_km * 1000.0
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    geog_point = cast(point, Geography)

    # 1. Alert Query
    alert_dist = (func.ST_Distance(cast(Alert.location, Geography), geog_point) / 1000.0).label("distance_km")
    stmt_alert = select(Alert, alert_dist).where(
        func.ST_DWithin(cast(Alert.location, Geography), geog_point, radius_m)
    ).order_by(alert_dist).limit(100)

    # 2. Vessel Query
    vessel_point = func.ST_SetSRID(func.ST_MakePoint(VesselRiskRecord.last_known_lon, VesselRiskRecord.last_known_lat), 4326)
    vessel_dist = (func.ST_Distance(cast(vessel_point, Geography), geog_point) / 1000.0).label("distance_km")
    stmt_vessel = select(VesselRiskRecord, vessel_dist).where(
        func.ST_DWithin(cast(vessel_point, Geography), geog_point, radius_m)
    ).order_by(vessel_dist).limit(100)

    # 3. Hotspot Query
    hotspot_dist = (func.ST_Distance(cast(ThermalHotspot.location, Geography), geog_point) / 1000.0).label("distance_km")
    stmt_hotspot = select(ThermalHotspot, hotspot_dist).where(
        func.ST_DWithin(cast(ThermalHotspot.location, Geography), geog_point, radius_m)
    ).order_by(hotspot_dist).limit(100)

    # Execute all 3 queries concurrently
    alert_res, vessel_res, hotspot_res = await asyncio.gather(
        db.execute(stmt_alert),
        db.execute(stmt_vessel),
        db.execute(stmt_hotspot)
    )

    def to_dicts(rows):
        out = []
        for entity, dist in rows.all():
            # Convert SQLAlchemy model to dict, exclude internal state
            d = {c.name: getattr(entity, c.name) for c in entity.__table__.columns}
            d["distance_km"] = float(dist)
            out.append(d)
        return out

    return to_dicts(alert_res), to_dicts(vessel_res), to_dicts(hotspot_res)