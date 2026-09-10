"""
SATVIGIL — Alerts API Routes
GET /api/v1/alerts        — list all active alerts (filterable)
GET /api/v1/alerts/{id}   — get single alert details
WS  /api/v1/alerts/live   — WebSocket for real-time alert push
"""
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
import json

from app.models.alert import Alert

from app.core.database import get_db
from app.schemas.alert import (
    AlertResponse,
    AlertSummary,
    AlertListResponse,
    AlertNearResponse,
    WebSocketAlertMessage,
)
from app.schemas.spatial import SpatialRadiusResponse
from app.services.spatial.radius_search import get_entities_near_point

router = APIRouter()

# ── WebSocket connection manager ──────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass


manager = ConnectionManager()


def _get_demo_alerts() -> list[AlertSummary]:
    now = datetime.now(timezone.utc)
    return [
        AlertSummary(
            id=1,
            alert_type="oil_spill",
            risk_level="critical",
            risk_score=0.95,
            title="Active Oil Slick Detected (4.8 km²)",
            latitude=19.20,
            longitude=71.50,
            source_dataset="SENTINEL",
            confidence="high",
            is_active=True,
            created_at=now,
        ),
        AlertSummary(
            id=2,
            alert_type="oil_spill",
            risk_level="critical",
            risk_score=0.91,
            title="AIS Transponder Off: MT GUJARAT PRIDE",
            latitude=19.15,
            longitude=71.45,
            source_dataset="AIS",
            confidence="high",
            is_active=True,
            created_at=now,
        ),
        AlertSummary(
            id=3,
            alert_type="illegal_fishing",
            risk_level="high",
            risk_score=0.78,
            title="Protected Area Breach: FV KUTCH FISHERMAN",
            latitude=22.50,
            longitude=69.20,
            source_dataset="AIS",
            confidence="nominal",
            is_active=True,
            created_at=now,
        ),
        AlertSummary(
            id=4,
            alert_type="fire_gas_flare",
            risk_level="medium",
            risk_score=0.62,
            title="Offshore Gas Flare Detected: Bombay High",
            latitude=19.38,
            longitude=71.33,
            source_dataset="FIRMS",
            confidence="high",
            is_active=True,
            created_at=now,
        ),
    ]


@router.get("/", response_model=AlertListResponse)
async def get_alerts(
    alert_type: Optional[str] = Query(None, description="Filter by type: oil_spill, fire_industrial, etc."),
    risk_level: Optional[str] = Query(None, description="Filter by risk: low, medium, high, critical"),
    is_active: Optional[bool] = Query(True, description="Filter by active status (default: True = active only)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active alerts. Supports filtering by type, risk level, and active status.
    Used by the frontend map to load markers on initial render.
    """
    try:
        # Build base query
        stmt = select(Alert)

        # Apply optional filters
        if alert_type is not None:
            stmt = stmt.where(Alert.alert_type == alert_type)
        if risk_level is not None:
            stmt = stmt.where(Alert.risk_level == risk_level)
        if is_active is not None:
            stmt = stmt.where(Alert.is_active == is_active)

        # Count total (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()

        return AlertListResponse(
            alerts=[AlertSummary.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception:
        demo_all = _get_demo_alerts()
        if alert_type:
            demo_all = [a for a in demo_all if a.alert_type == alert_type]
        if risk_level:
            demo_all = [a for a in demo_all if a.risk_level == risk_level]
        if is_active is not None:
            demo_all = [a for a in demo_all if a.is_active == is_active]
        paginated = demo_all[offset : offset + limit]
        return AlertListResponse(
            alerts=paginated,
            total=len(demo_all),
            limit=limit,
            offset=offset,
        )


@router.get("/near", response_model=SpatialRadiusResponse)
async def get_alerts_near(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    radius_km: float = Query(..., gt=0, le=500, description="Radius in km"),
    db: AsyncSession = Depends(get_db),
):
    """
    Find alerts, vessels, and hotspots within a given radius using PostGIS.
    Max radius is 500km to prevent full table scans.
    """
    try:
        alerts, vessels, hotspots = await get_entities_near_point(db, lat, lon, radius_km)
        return SpatialRadiusResponse(
            query_lat=lat,
            query_lon=lon,
            radius_km=radius_km,
            alerts=alerts,
            vessels=vessels,
            hotspots=hotspots,
        )
    except Exception:
        return SpatialRadiusResponse(
            query_lat=lat,
            query_lon=lon,
            radius_km=radius_km,
            alerts=[],
            vessels=[],
            hotspots=[],
        )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Get details for a single alert (clicked on map)."""
    try:
        result = await db.get(Alert, alert_id)
        if result is not None:
            return AlertResponse.model_validate(result)
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    return AlertResponse(
        id=alert_id,
        alert_type="oil_spill",
        risk_level="critical",
        title=f"Alert #{alert_id}",
        description="Active satellite anomaly",
        latitude=19.20,
        longitude=71.50,
        is_active=True,
        metadata_payload={},
        created_at=now,
        updated_at=now,
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """
    Mark an alert as resolved/inactive.
    Sets is_active=False and resolved_at=now().
    Broadcasts a resolve_alert WS event to all connected clients.
    """
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    if not alert.is_active:
        raise HTTPException(status_code=409, detail="Alert is already acknowledged")

    alert.is_active = False
    alert.resolved_at = datetime.now(timezone.utc)
    await db.flush()   # push to DB within current transaction (get_db commits on exit)

    # Broadcast resolution to all live WebSocket clients
    await manager.broadcast({
        "event": "resolve_alert",
        "data": AlertSummary.model_validate(alert).model_dump(mode="json"),
    })

    return AlertResponse.model_validate(alert)


@router.websocket("/live")
async def alert_websocket(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint — frontend connects here to receive new alerts in real time.
    Every time the scheduler triggers a new detection, it broadcasts here.
    """
    await manager.connect(websocket)
    try:
        # ── Send current active alerts immediately on connect ──────────────
        stmt = select(Alert).where(Alert.is_active == True).order_by(Alert.created_at.desc()).limit(50)
        rows = (await db.execute(stmt)).scalars().all()
        init_payload = {
            "event": "init",
            "data": [AlertSummary.model_validate(r).model_dump(mode="json") for r in rows],
        }
        await websocket.send_text(json.dumps(init_payload))

        # ── Keep-alive ping loop ───────────────────────────────────────────
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"event": "ping", "data": None}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
