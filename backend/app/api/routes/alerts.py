"""
SATVIGIL — Alerts API Routes
GET /api/v1/alerts        — list all active alerts (filterable)
GET /api/v1/alerts/{id}   — get single alert details
WS  /api/v1/alerts/live   — WebSocket for real-time alert push
"""
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import asyncio
import json

from app.core.database import get_db
from app.schemas.alert import AlertResponse, AlertListResponse

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


@router.get("/", response_model=AlertListResponse)
async def get_alerts(
    alert_type: Optional[str] = Query(None, description="Filter by type: oil_spill, fire_industrial, etc."),
    risk_level: Optional[str] = Query(None, description="Filter by risk: low, medium, high, critical"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active alerts. Supports filtering by type and risk level.
    Used by the frontend map to load markers on initial render.
    """
    # TODO: Query from DB using Alert model
    # For hackathon demo, returns mock data — replace with real DB query
    return {"alerts": [], "total": 0}


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Get details for a single alert (clicked on map)."""
    # TODO: DB query
    return {}


@router.websocket("/live")
async def alert_websocket(websocket: WebSocket):
    """
    WebSocket endpoint — frontend connects here to receive new alerts in real time.
    Every time the scheduler triggers a new detection, it broadcasts here.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive with ping
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
