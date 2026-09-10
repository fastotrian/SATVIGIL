"""
SATVIGIL — Maritime Module: AIS Data Fetcher
============================================
Primary source : Global Fishing Watch (GFW) API v3
                 Uses the same endpoint proven by scripts/fetch_gfw_vessel_track.py
Fallback       : AISHub (requires NMEA contributor account)

GFW returns vessel PRESENCE data (aggregated hourly grid cells).
We extract the latest unique position per vessel and normalize
to AISHub-compatible dict keys so parse_vessel() in maritime.py
works with zero changes.

Output format per vessel dict:
  MMSI       : str   — AIS mobile station identifier
  NAME       : str   — vessel name
  TYPE       : int   — AIS vessel type code (80=Tanker, 70=Cargo, 30=Fishing…)
  LATITUDE   : float — degrees N
  LONGITUDE  : float — degrees E
  SPEED      : float — speed * 10 (AISHub convention; 0 if unavailable from GFW)
  COURSE     : float — course over ground degrees (0 if unavailable)
  ais_gap_minutes : int — derived from GFW gap events or 0
  flag       : str   — ISO 3-letter country code
  gfw_vessel_id : str — GFW internal ID for track lookups
"""
import httpx
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from pathlib import Path

from app.core.config import settings

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# GFW API CONFIG
# ─────────────────────────────────────────────────────────────────────────────

GFW_BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"

# Token from scripts/fetch_gfw_vessel_track.py (proven working)
# Prefer env var GFW_API_TOKEN; fall back to the hardcoded team token
_TEAM_GFW_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImtpZEtleSJ9"
    ".eyJkYXRhIjp7Im5hbWUiOiJTQVRWSUdJTCIsInVzZXJJZCI6Njk5Mjgs"
    "ImFwcGxpY2F0aW9uTmFtZSI6IlNBVFZJR0lMIiwiaWQiOjE0MDI1LCJ0"
    "eXBlIjoidXNlci1hcHBsaWNhdGlvbiJ9LCJpYXQiOjE3ODg0NzA1NjYs"
    "ImV4cCI6MjEwMzgzMDU2NiwiYXVkIjoiZ2Z3IiwiaXNzIjoiZ2Z3In0"
    ".mGtBnTjmesVPp73HIIf-3f9x6wOTIfmdUUlouuAJyTACOvmaTJtO0RR_"
    "g0QMNAbvkEtkE2AvS7veOESpYCq2ky0bm8KQQ9TvKy2JikL6lhBwCXwj"
    "LMNH4Sz8eAU7TCbAO15PqU3xHNqJtVyeashiTKL8oSj6uNKMQ_yHMbV6"
    "24nao8npc_i4nZUFhdwL3mudEV-xXndgGUN42_M-XXJ84esc28KYN_3T2r"
    "g7a1oDuM1VtQC67ihb8OaI6_BgZEfW4_oYbz8znLHrMTl1KlE7Hsa4E5s"
    "XLZ6Qz3sVWHUJDncThnB8xUY1IlmZZcvprDddXcbVtlfXgciIE7qT_pOo"
    "SqlgQKil2cS_tvnjZwjTdzRPQaz5XnJkMuchn5ujIGD-EJb4a_dEakUeb"
    "wpoPHud_PCxv54DDV2xp2DY4PBlatEoB12yhrrASp2-A2Swg4aRmwIsIwv"
    "YCa3_YGxuwo-DRnLMpDAgHZIHuHox6kDJKme9XNbKDexBkzAZOtSDOFIq"
)


def _gfw_token() -> str:
    """Return GFW API token — env var takes priority over team default."""
    return settings.GFW_API_TOKEN.strip() or _TEAM_GFW_TOKEN


# Indian Ocean / India EEZ bounding box (same as friend's script + broader)
INDIA_OCEAN_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [67.0,  6.0],
        [98.0,  6.0],
        [98.0, 24.0],
        [67.0, 24.0],
        [67.0,  6.0],
    ]],
}

# ─────────────────────────────────────────────────────────────────────────────
# Marine Protected Areas — India
# ─────────────────────────────────────────────────────────────────────────────
INDIA_MPAs = [
    {"name": "Gulf of Kutch MNP",  "lat_min": 22.0, "lat_max": 23.5, "lon_min": 68.5, "lon_max": 70.5},
    {"name": "Gulf of Mannar MNP", "lat_min":  8.5, "lat_max":  9.5, "lon_min": 78.0, "lon_max": 79.5},
    {"name": "Sundarbans Buffer",  "lat_min": 21.5, "lat_max": 22.5, "lon_min": 88.5, "lon_max": 89.5},
    {"name": "Malvan MNP",         "lat_min": 15.9, "lat_max": 16.4, "lon_min": 73.3, "lon_max": 73.6},
]

HIGH_RISK_ZONES = [
    {"name": "Bombay High Offshore", "lat": 19.2, "lon": 71.5, "radius_deg": 0.5},
    {"name": "JNPT Approach",        "lat": 18.9, "lon": 72.9, "radius_deg": 0.3},
    {"name": "Kandla Port",          "lat": 23.0, "lon": 70.2, "radius_deg": 0.3},
    {"name": "Paradip Port",         "lat": 20.3, "lon": 86.7, "radius_deg": 0.3},
]

# ─────────────────────────────────────────────────────────────────────────────
# GFW vessel type → AIS vessel type code mapping
# ─────────────────────────────────────────────────────────────────────────────
GFW_TYPE_TO_AIS: Dict[str, int] = {
    "FISHING":          30,
    "CARRIER":          70,
    "CARGO":            71,
    "TANKER":           80,
    "PASSENGER":        60,
    "SUPPORT":          50,
    "SAILING":          36,
    "PLEASURE":         37,
    "OTHER":             0,
    "SEISMIC_VESSEL":   50,
    "BUNKER_OR_TANKER": 80,
    "CARGO_OR_TANKER":  80,
    "FISHING_SUPPORT":  30,
}


def _gfw_type_to_ais(gfw_type: Optional[str]) -> int:
    """Convert GFW vessel category string to AIS numeric type code."""
    if not gfw_type:
        return 0
    return GFW_TYPE_TO_AIS.get(gfw_type.upper(), 0)


# ─────────────────────────────────────────────────────────────────────────────
# GFW 4Wings Presence Fetch — same endpoint as scripts/fetch_gfw_vessel_track.py
# ─────────────────────────────────────────────────────────────────────────────

async def _gfw_report_call(
    token: str,
    start: str,
    end: str,
    spatial_res: str,
    temporal_res: str,
    geojson: dict,
) -> List[Dict]:
    """Single GFW 4wings report POST. Returns parsed vessel list or []."""
    url = f"{GFW_BASE_URL}/4wings/report"
    params = {
        "spatial-resolution": spatial_res,
        "temporal-resolution": temporal_res,
        "group-by": "VESSEL_ID",
        "datasets[0]": "public-global-presence:latest",
        "date-range": f"{start},{end}",
        "format": "JSON",
        "spatial-aggregation": "false",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, params=params, json={"geojson": geojson}, headers=headers)

        if response.status_code == 401:
            logger.error("gfw_unauthorized", hint="Check GFW_API_TOKEN in .env")
            return []
        if not response.is_success:
            logger.warning("gfw_call_failed", status=response.status_code, body=response.text[:200])
            return []

        return _parse_gfw_response(response.json())
    except httpx.TimeoutException:
        logger.warning("gfw_call_timeout", start=start, end=end, res=spatial_res)
        return []
    except Exception as e:
        logger.warning("gfw_call_exception", error=str(e))
        return []


# Gulf of Kutch bbox — smaller, proven to work (friend's script)
GULF_KUTCH_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [68.5, 22.0], [70.8, 22.0], [70.8, 23.1],
        [68.5, 23.1], [68.5, 22.0],
    ]],
}


async def _fetch_gfw_presence(_unused_days_back: int = 3) -> List[Dict]:
    """
    Fetch vessel presence from GFW with cascading date-window fallback.

    GFW data has a 3-10 day processing delay, so we try multiple windows
    going progressively further back until we find processed data.

    Cascade (stops at first window that returns vessels):
      1. India Ocean bbox — DAILY, 7→14 days back   (broad, recent)
      2. India Ocean bbox — DAILY, 14→30 days back  (broader time)
      3. Gulf of Kutch   — DAILY, 30→60 days back   (small bbox, proven)
      4. Gulf of Kutch   — DAILY, 60→90 days back   (further back)
    """
    token = _gfw_token()
    if not token:
        logger.warning("gfw_token_missing")
        return []

    today = datetime.now(timezone.utc).date()

    def date_range(start_days_back: int, end_days_back: int):
        start = (today - timedelta(days=start_days_back)).isoformat()
        end   = (today - timedelta(days=end_days_back)).isoformat()
        return start, end

    # Cascade: (start_days_back, end_days_back, spatial_res, temporal_res, geojson, label)
    cascade = [
        (14,  7,  "LOW",  "DAILY",  INDIA_OCEAN_GEOJSON,  "india-7-14d"),
        (30, 14,  "LOW",  "DAILY",  INDIA_OCEAN_GEOJSON,  "india-14-30d"),
        (60, 30,  "LOW",  "DAILY",  INDIA_OCEAN_GEOJSON,  "india-30-60d"),
        (60, 30,  "HIGH", "DAILY",  GULF_KUTCH_GEOJSON,   "kutch-30-60d"),
        (90, 60,  "HIGH", "DAILY",  GULF_KUTCH_GEOJSON,   "kutch-60-90d"),
    ]

    for (sb, eb, sr, tr, bbox, label) in cascade:
        start, end = date_range(sb, eb)
        logger.info("gfw_fetch_attempt", label=label, start=start, end=end)
        vessels = await _gfw_report_call(token, start, end, sr, tr, bbox)
        if vessels:
            logger.info("gfw_fetch_success", label=label, count=len(vessels))
            return vessels
        logger.info("gfw_fetch_empty", label=label)

    logger.warning("gfw_all_windows_empty")
    return []


def _parse_gfw_response(data: dict) -> List[Dict]:
    """
    Parse GFW 4wings report JSON into AISHub-compatible vessel dicts.

    GFW response structure (group-by=VESSEL_ID):
      { "entries": [ { "<date>": [ { vesselId, lat, lon, hours, mmsi, ... } ] } ] }

    We take the LATEST observation per vessel (highest date) as the
    "current position" and normalize to the AISHub key format.
    """
    entries = data.get("entries", [])
    # vessel_id → latest row
    latest: Dict[str, dict] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for date_key, rows in entry.items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                vid = row.get("vesselId") or row.get("vessel_id")
                lat = row.get("lat")
                lon = row.get("lon")
                if not vid or lat is None or lon is None:
                    continue
                # Keep the row with the most recent date_key per vessel
                if vid not in latest or date_key > latest[vid].get("_date", ""):
                    row["_date"] = date_key
                    latest[vid] = row

    vessels = []
    for vid, row in latest.items():
        mmsi = str(row.get("mmsi") or "")
        if not mmsi or mmsi == "None":
            mmsi = vid[:9] if len(vid) >= 9 else vid  # fallback

        name = (
            row.get("shipName")
            or row.get("ship_name")
            or row.get("name")
            or f"GFW-{mmsi}"
        ).strip()

        gfw_type = row.get("vesselType") or row.get("vessel_type") or ""
        ais_type = _gfw_type_to_ais(gfw_type)
        flag = row.get("flag") or row.get("countryCode") or ""

        vessels.append({
            # AISHub-compatible keys (parse_vessel() in maritime.py reads these)
            "MMSI":      mmsi,
            "NAME":      name,
            "TYPE":      ais_type,
            "LATITUDE":  float(row.get("lat", 0)),
            "LONGITUDE": float(row.get("lon", 0)),
            "SPEED":     0,          # GFW presence doesn't include instantaneous speed
            "COURSE":    0.0,        # GFW presence doesn't include course
            "ais_gap_minutes": 0,    # enriched later by ais_worker if DB records exist
            # Extra GFW fields kept for ais_worker enrichment
            "flag":          flag,
            "gfw_vessel_id": vid,
            "gfw_type":      gfw_type,
            "presence_hours": float(row.get("hours", 0)),
            "_last_seen_date": row.get("_date", ""),
        })

    logger.info("gfw_vessels_parsed", count=len(vessels))
    return vessels


# ─────────────────────────────────────────────────────────────────────────────
# AISHub Fetch (kept as secondary fallback if GFW is unavailable)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_aishub_vessels() -> List[Dict]:
    """Fetch from AISHub (requires NMEA contributor account + username)."""
    if not settings.AISHUB_USERNAME:
        return []

    url = "https://data.aishub.net/ws.php"
    params = {
        "username": settings.AISHUB_USERNAME,
        "format": "1",
        "output": "json",
        "compress": "0",
        "latmin": "6", "latmax": "24",
        "lonmin": "67", "lonmax": "98",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            vessels = data[1] if len(data) > 1 else []
            logger.info("aishub_fetch_success", count=len(vessels))
            return vessels
    except Exception as e:
        logger.error("aishub_fetch_failed", error=str(e))
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Public API — called by maritime.py routes and ais_worker.py
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_ais_vessels() -> List[Dict]:
    """
    Fetch current vessel positions.
    Priority:
      1. Global Fishing Watch (GFW) API  ← primary (friend's proven token)
      2. AISHub API                      ← if GFW fails and AISHUB_USERNAME set
      3. Returns []                      ← maritime.py falls back to demo scenario
    """
    # 1. Try GFW
    vessels = await _fetch_gfw_presence(days_back=3)
    if vessels:
        logger.info("ais_source_gfw", count=len(vessels))
        return vessels

    # 2. Try AISHub
    vessels = await _fetch_aishub_vessels()
    if vessels:
        logger.info("ais_source_aishub", count=len(vessels))
        return vessels

    logger.warning("ais_all_sources_failed_using_demo_fallback")
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Risk Scoring & MPA Helpers (used by maritime.py routes)
# ─────────────────────────────────────────────────────────────────────────────

def is_vessel_in_mpa(lat: float, lon: float) -> Optional[str]:
    """Return MPA name if vessel is inside any Marine Protected Area, else None."""
    for mpa in INDIA_MPAs:
        if (mpa["lat_min"] <= lat <= mpa["lat_max"] and
                mpa["lon_min"] <= lon <= mpa["lon_max"]):
            return mpa["name"]
    return None


def is_vessel_in_high_risk_zone(lat: float, lon: float) -> Optional[str]:
    """Return zone name if vessel is inside a high-risk offshore zone."""
    for zone in HIGH_RISK_ZONES:
        d = ((lat - zone["lat"]) ** 2 + (lon - zone["lon"]) ** 2) ** 0.5
        if d <= zone["radius_deg"]:
            return zone["name"]
    return None


def is_vessel_loitering(speed_knots: float, duration_minutes: int) -> bool:
    """Vessel is loitering if speed < 1 knot for >= 30 minutes."""
    return speed_knots < 1.0 and duration_minutes >= 30


def calculate_vessel_risk_score(vessel: Dict, ais_gap_minutes: int = 0) -> float:
    """
    Score a vessel's suspicious behavior risk on 0.0–1.0 scale.

    Signals:
      +0.40  AIS dark gap > 30 minutes
      +0.20  AIS dark gap 10–30 minutes
      +0.30  Inside Marine Protected Area
      +0.20  Inside high-risk offshore zone (Bombay High etc.)
      +0.20  Loitering (speed < 1 kt, gap >= 30 min)
      +0.10  Tanker vessel type
    """
    score = 0.0
    lat = float(vessel.get("LATITUDE", 0))
    lon = float(vessel.get("LONGITUDE", 0))
    raw_speed = float(vessel.get("SPEED", 0))
    speed = raw_speed / 10.0 if raw_speed > 30 else raw_speed

    if ais_gap_minutes > 30:
        score += 0.40
    elif ais_gap_minutes > 10:
        score += 0.20

    if is_vessel_in_mpa(lat, lon):
        score += 0.30

    if is_vessel_in_high_risk_zone(lat, lon):
        score += 0.20

    if is_vessel_loitering(speed, ais_gap_minutes):
        score += 0.20

    vessel_type = int(vessel.get("TYPE", 0))
    if 80 <= vessel_type <= 89:
        score += 0.10

    return min(score, 1.0)
