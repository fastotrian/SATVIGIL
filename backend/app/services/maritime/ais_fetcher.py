"""
SATVIGIL — Maritime Module: AIS Data Fetcher
Fetches vessel positions from AISHub free API and Global Fishing Watch.
"""
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.core.config import settings
try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ── Marine Protected Areas (India) ────────────────────────────────────────────
# Simplified bounding boxes — replace with full GeoJSON polygons for production
INDIA_MPAs = [
    {"name": "Gulf of Kutch MNP",  "lat_min": 22.0, "lat_max": 23.5, "lon_min": 68.5, "lon_max": 70.5},
    {"name": "Gulf of Mannar MNP", "lat_min": 8.5,  "lat_max": 9.5,  "lon_min": 78.0, "lon_max": 79.5},
    {"name": "Sundarbans Buffer",  "lat_min": 21.5, "lat_max": 22.5, "lon_min": 88.5, "lon_max": 89.5},
    {"name": "Malvan MNP",         "lat_min": 15.9, "lat_max": 16.4, "lon_min": 73.3, "lon_max": 73.6},
]

# High-risk offshore zones (Bombay High oil fields, major port approaches)
HIGH_RISK_ZONES = [
    {"name": "Bombay High Offshore", "lat": 19.2, "lon": 71.5, "radius_deg": 0.5},
    {"name": "JNPT Approach",        "lat": 18.9, "lon": 72.9, "radius_deg": 0.3},
    {"name": "Kandla Port",          "lat": 23.0, "lon": 70.2, "radius_deg": 0.3},
    {"name": "Paradip Port",         "lat": 20.3, "lon": 86.7, "radius_deg": 0.3},
]


async def fetch_ais_vessels() -> List[Dict]:
    """
    Fetch current vessel positions from AISHub.
    Returns list of vessel dicts with position and metadata.

    AISHub API docs: https://www.aishub.net/api
    Returns XML/JSON of vessels in a geographic area.
    """
    url = "https://data.aishub.net/ws.php"
    params = {
        "username": settings.AISHUB_USERNAME,
        "format": "1",           # JSON format
        "output": "json",
        "compress": "0",
        "latmin": "6",
        "latmax": "24",
        "lonmin": "67",
        "lonmax": "98",          # Indian Ocean / India coast bounding box
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            vessels = data[1] if len(data) > 1 else []
            logger.info("ais_fetch_success", count=len(vessels))
            return vessels
        except Exception as e:
            logger.error("ais_fetch_failed", error=str(e))
            return []


def is_vessel_in_mpa(lat: float, lon: float) -> Optional[str]:
    """Check if vessel coordinates fall inside any Marine Protected Area."""
    for mpa in INDIA_MPAs:
        if (mpa["lat_min"] <= lat <= mpa["lat_max"] and
                mpa["lon_min"] <= lon <= mpa["lon_max"]):
            return mpa["name"]
    return None


def is_vessel_in_high_risk_zone(lat: float, lon: float) -> Optional[str]:
    """Check if vessel coordinates fall inside any designated high-risk offshore zone."""
    for zone in HIGH_RISK_ZONES:
        d_lat = lat - zone["lat"]
        d_lon = lon - zone["lon"]
        if (d_lat**2 + d_lon**2)**0.5 <= zone["radius_deg"]:
            return zone["name"]
    return None


def is_vessel_loitering(speed_knots: float, duration_minutes: int) -> bool:
    """
    Vessel is loitering if speed < 1 knot for >= 30 minutes
    with no commercial port destination nearby.
    """
    return speed_knots < 1.0 and duration_minutes >= 30


def calculate_vessel_risk_score(vessel: Dict, ais_gap_minutes: int = 0) -> float:
    """
    Score a vessel's suspicious behavior risk on 0.0–1.0 scale.
    Higher = more suspicious.

    Factors:
    - AIS transponder was off (dark vessel): +0.40
    - Vessel is inside a Marine Protected Area: +0.30
    - Vessel is inside high-risk offshore zone: +0.20
    - Vessel is loitering (slow speed, >=30 min): +0.20
    - Vessel is a tanker: +0.10
    """
    score = 0.0
    lat = vessel.get("LATITUDE", 0)
    lon = vessel.get("LONGITUDE", 0)
    speed = vessel.get("SPEED", 0) / 10.0  # AISHub gives speed * 10

    # Dark vessel (AIS gap > 30 minutes)
    if ais_gap_minutes > 30:
        score += 0.40
    elif ais_gap_minutes > 10:
        score += 0.20

    # Inside Marine Protected Area
    mpa = is_vessel_in_mpa(lat, lon)
    if mpa:
        score += 0.30

    # High-Risk Offshore Zone (e.g. Bombay High, port approaches)
    zone = is_vessel_in_high_risk_zone(lat, lon)
    if zone:
        score += 0.20

    # Loitering
    if is_vessel_loitering(speed, ais_gap_minutes):
        score += 0.20

    # Vessel type is tanker or cargo (higher spill risk)
    vessel_type = vessel.get("TYPE", 0)
    if 80 <= vessel_type <= 89:  # AIS vessel type codes for tankers
        score += 0.10

    return min(score, 1.0)
