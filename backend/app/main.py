"""
SATVIGIL — FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import alerts, maritime, fire, landslide, pollution, health
from app.tasks.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


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
