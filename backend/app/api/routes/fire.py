"""
SATVIGIL — Fire API Route (PS 162)
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.alert import ThermalHotspot
from app.schemas.hotspot import HotspotListResponse, ThermalHotspotSchema, FireType
from app.services.fire.firms_fetcher import get_responding_agency

router = APIRouter()

def enrich_hotspot(hotspot: ThermalHotspot) -> ThermalHotspotSchema:
    agency_info = get_responding_agency(hotspot.fire_type)
    return ThermalHotspotSchema(
        id=hotspot.id,
        latitude=hotspot.latitude,
        longitude=hotspot.longitude,
        frp=hotspot.frp,
        brightness=hotspot.brightness,
        confidence=hotspot.confidence,
        satellite=hotspot.satellite,
        acquired_at=hotspot.acquired_at,
        fire_type=hotspot.fire_type,
        land_use=hotspot.land_use,
        near_cpcb_cluster=hotspot.near_cpcb_cluster,
        recurrence_count=hotspot.recurrence_count,
        created_at=hotspot.created_at,
        responding_agency=agency_info.get("agency"),
        recommended_action=agency_info.get("action")
    )

@router.get("/hotspots", response_model=HotspotListResponse)
async def get_hotspots(
    fire_type: Optional[FireType] = Query(None, description="Filter by fire type"),
    min_frp: Optional[float] = Query(None, description="Minimum Fire Radiative Power (MW)"),
    start_date: Optional[datetime] = Query(None, description="Filter by acquisition date (start)"),
    end_date: Optional[datetime] = Query(None, description="Filter by acquisition date (end)"),
    near_cpcb_only: Optional[bool] = Query(False, description="Only show hotspots near CPCB clusters"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(ThermalHotspot)
    count_query = select(func.count(ThermalHotspot.id))

    if fire_type:
        query = query.where(ThermalHotspot.fire_type == fire_type.value)
        count_query = count_query.where(ThermalHotspot.fire_type == fire_type.value)
    
    if min_frp is not None:
        query = query.where(ThermalHotspot.frp >= min_frp)
        count_query = count_query.where(ThermalHotspot.frp >= min_frp)
        
    if start_date:
        query = query.where(ThermalHotspot.acquired_at >= start_date)
        count_query = count_query.where(ThermalHotspot.acquired_at >= start_date)
        
    if end_date:
        query = query.where(ThermalHotspot.acquired_at <= end_date)
        count_query = count_query.where(ThermalHotspot.acquired_at <= end_date)
        
    if near_cpcb_only:
        query = query.where(ThermalHotspot.near_cpcb_cluster == True)
        count_query = count_query.where(ThermalHotspot.near_cpcb_cluster == True)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(ThermalHotspot.acquired_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    hotspots_db = result.scalars().all()

    hotspots = [enrich_hotspot(h) for h in hotspots_db]

    return HotspotListResponse(
        hotspots=hotspots,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/hotspots/{id}", response_model=ThermalHotspotSchema)
async def get_hotspot(id: int, db: AsyncSession = Depends(get_db)):
    query = select(ThermalHotspot).where(ThermalHotspot.id == id)
    result = await db.execute(query)
    hotspot_db = result.scalar_one_or_none()
    
    if not hotspot_db:
        raise HTTPException(status_code=404, detail="Hotspot not found")
        
    return enrich_hotspot(hotspot_db)

@router.get("/recurrence", response_model=HotspotListResponse)
async def get_recurrence(
    min_recurrence: int = Query(3, ge=1, description="Minimum recurrence count"),
    fire_type: Optional[FireType] = Query(None, description="Filter by fire type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(ThermalHotspot).where(ThermalHotspot.recurrence_count >= min_recurrence)
    count_query = select(func.count(ThermalHotspot.id)).where(ThermalHotspot.recurrence_count >= min_recurrence)

    if fire_type:
        query = query.where(ThermalHotspot.fire_type == fire_type.value)
        count_query = count_query.where(ThermalHotspot.fire_type == fire_type.value)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(ThermalHotspot.recurrence_count.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    hotspots_db = result.scalars().all()

    hotspots = [enrich_hotspot(h) for h in hotspots_db]

    return HotspotListResponse(
        hotspots=hotspots,
        total=total,
        limit=limit,
        offset=offset
    )
