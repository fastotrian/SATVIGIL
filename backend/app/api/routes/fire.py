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

def _get_demo_hotspots() -> list[ThermalHotspotSchema]:
    now = datetime.utcnow()
    raw_data = [
        {
            "id": 1,
            "latitude": 19.38,
            "longitude": 71.33,
            "frp": 125.4,
            "brightness": 328.5,
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": now,
            "fire_type": "gas_flare",
            "land_use": "petroleum",
            "near_cpcb_cluster": False,
            "recurrence_count": 28,
            "created_at": now,
        },
        {
            "id": 2,
            "latitude": 19.86,
            "longitude": 72.69,
            "frp": 460.0,
            "brightness": 352.1,
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": now,
            "fire_type": "industrial",
            "land_use": "industrial",
            "near_cpcb_cluster": True,
            "recurrence_count": 14,
            "created_at": now,
        },
        {
            "id": 3,
            "latitude": 20.37,
            "longitude": 72.90,
            "frp": 385.2,
            "brightness": 344.0,
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": now,
            "fire_type": "industrial",
            "land_use": "industrial",
            "near_cpcb_cluster": True,
            "recurrence_count": 9,
            "created_at": now,
        },
        {
            "id": 4,
            "latitude": 30.90,
            "longitude": 75.85,
            "frp": 48.0,
            "brightness": 305.2,
            "confidence": "nominal",
            "satellite": "MODIS_NRT",
            "acquired_at": now,
            "fire_type": "stubble",
            "land_use": "farmland",
            "near_cpcb_cluster": False,
            "recurrence_count": 2,
            "created_at": now,
        },
        {
            "id": 5,
            "latitude": 30.21,
            "longitude": 74.94,
            "frp": 36.5,
            "brightness": 298.0,
            "confidence": "nominal",
            "satellite": "MODIS_NRT",
            "acquired_at": now,
            "fire_type": "stubble",
            "land_use": "farmland",
            "near_cpcb_cluster": False,
            "recurrence_count": 1,
            "created_at": now,
        },
        {
            "id": 6,
            "latitude": 11.60,
            "longitude": 76.08,
            "frp": 140.0,
            "brightness": 330.4,
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": now,
            "fire_type": "wildfire",
            "land_use": "forest",
            "near_cpcb_cluster": False,
            "recurrence_count": 1,
            "created_at": now,
        },
        {
            "id": 7,
            "latitude": 23.75,
            "longitude": 86.41,
            "frp": 92.0,
            "brightness": 318.0,
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": now,
            "fire_type": "mining",
            "land_use": "quarry",
            "near_cpcb_cluster": True,
            "recurrence_count": 18,
            "created_at": now,
        },
        {
            "id": 8,
            "latitude": 21.62,
            "longitude": 73.00,
            "frp": 155.0,
            "brightness": 332.0,
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": now,
            "fire_type": "gas_flare",
            "land_use": "petroleum",
            "near_cpcb_cluster": True,
            "recurrence_count": 22,
            "created_at": now,
        },
    ]

    res = []
    for item in raw_data:
        agency_info = get_responding_agency(item["fire_type"])
        res.append(
            ThermalHotspotSchema(
                id=item["id"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                frp=item["frp"],
                brightness=item["brightness"],
                confidence=item["confidence"],
                satellite=item["satellite"],
                acquired_at=item["acquired_at"],
                fire_type=item["fire_type"],
                land_use=item["land_use"],
                near_cpcb_cluster=item["near_cpcb_cluster"],
                recurrence_count=item["recurrence_count"],
                created_at=item["created_at"],
                responding_agency=agency_info.get("agency"),
                recommended_action=agency_info.get("action"),
            )
        )
    return res


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
    try:
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
    except Exception:
        # Graceful fallback to demo hotspots when DB is offline
        demo_all = _get_demo_hotspots()
        filtered = demo_all
        if fire_type:
            filtered = [h for h in filtered if h.fire_type == fire_type.value]
        if min_frp is not None:
            filtered = [h for h in filtered if h.frp and h.frp >= min_frp]
        if near_cpcb_only:
            filtered = [h for h in filtered if h.near_cpcb_cluster]

        paginated = filtered[offset : offset + limit]
        return HotspotListResponse(
            hotspots=paginated,
            total=len(filtered),
            limit=limit,
            offset=offset,
        )


@router.get("/hotspots/{id}", response_model=ThermalHotspotSchema)
async def get_hotspot(id: int, db: AsyncSession = Depends(get_db)):
    try:
        query = select(ThermalHotspot).where(ThermalHotspot.id == id)
        result = await db.execute(query)
        hotspot_db = result.scalar_one_or_none()
        if hotspot_db:
            return enrich_hotspot(hotspot_db)
    except Exception:
        pass

    for demo in _get_demo_hotspots():
        if demo.id == id:
            return demo
            
    raise HTTPException(status_code=404, detail="Hotspot not found")


@router.get("/recurrence", response_model=HotspotListResponse)
async def get_recurrence(
    min_recurrence: int = Query(3, ge=1, description="Minimum recurrence count"),
    fire_type: Optional[FireType] = Query(None, description="Filter by fire type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    try:
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
    except Exception:
        demo_all = [h for h in _get_demo_hotspots() if (h.recurrence_count or 0) >= min_recurrence]
        if fire_type:
            demo_all = [h for h in demo_all if h.fire_type == fire_type.value]
        paginated = demo_all[offset : offset + limit]
        return HotspotListResponse(
            hotspots=paginated,
            total=len(demo_all),
            limit=limit,
            offset=offset,
        )

