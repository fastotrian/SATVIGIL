"""
SATVIGIL — FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import alerts, maritime, fire, landslide, pollution, health, satellite
from app.tasks.scheduler import start_scheduler, shutdown_scheduler


import logging

logger = logging.getLogger("satvigil")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with graceful degradation if DB is offline."""
    # Startup: attempt DB connection and table synchronization
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connection established and tables verified.")
    except Exception as exc:
        logger.warning(
            "PostgreSQL database unavailable (%s). Running with in-memory & demo fallback data.",
            exc,
        )

    try:
        start_scheduler()
    except Exception as exc:
        logger.warning("Background scheduler failed to start (%s). Continuing without scheduler.", exc)

    yield

    # Shutdown
    try:
        shutdown_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="SATVIGIL API",
    description="AI-Powered Satellite Monitoring Platform for India",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(health.router,     prefix="/api/v1",          tags=["Health"])
app.include_router(alerts.router,     prefix="/api/v1/alerts",   tags=["Alerts"])
app.include_router(maritime.router,   prefix="/api/v1/maritime", tags=["Maritime"])
app.include_router(fire.router,       prefix="/api/v1/fire",     tags=["Fire"])
app.include_router(landslide.router,  prefix="/api/v1/landslide",tags=["Landslide"])
app.include_router(pollution.router,  prefix="/api/v1/pollution",tags=["Pollution"])
app.include_router(satellite.router,  prefix="/api/v1/satellite",tags=["Satellite"])
