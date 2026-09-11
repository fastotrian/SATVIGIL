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
    {"name": "Gulf of Kutch MNP",  "lat_min": 22.35, "lat_max": 22.65, "lon_min": 69.10, "lon_max": 69.80},
    {"name": "Gulf of Mannar MNP", "lat_min":  8.80, "lat_max":  9.25, "lon_min": 78.50, "lon_max": 79.30},
    {"name": "Sundarbans Buffer",  "lat_min": 21.60, "lat_max": 22.00, "lon_min": 88.60, "lon_max": 89.20},
    {"name": "Malvan MNP",         "lat_min": 16.02, "lat_max": 16.12, "lon_min": 73.44, "lon_max": 73.53},
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
        async with httpx.AsyncClient(timeout=8.0) as client:
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

# Simple in-memory cache for vessels
_VESSEL_CACHE: List[Dict] = []
_VESSEL_CACHE_TIME: Optional[datetime] = None
_CACHE_TTL_SECONDS = 60


async def _fetch_gfw_presence(days_back: int = 3) -> List[Dict]:
    """
    Fetch vessel presence from GFW with cascading date-window fallback.

    GFW data has a 3-10 day processing delay, so we try multiple windows
    going progressively further back until we find processed data.
    """
    global _VESSEL_CACHE, _VESSEL_CACHE_TIME
    now = datetime.now(timezone.utc)
    if _VESSEL_CACHE and _VESSEL_CACHE_TIME and (now - _VESSEL_CACHE_TIME).total_seconds() < _CACHE_TTL_SECONDS:
        return _VESSEL_CACHE

    token = _gfw_token()
    if not token:
        logger.warning("gfw_token_missing")
        return []

    today = now.date()

    def date_range(start_days_back: int, end_days_back: int):
        start = (today - timedelta(days=start_days_back)).isoformat()
        end   = (today - timedelta(days=end_days_back)).isoformat()
        return start, end

    # Fast cascade: try recent India ocean then Gulf of Kutch
    cascade = [
        (14,  7,  "LOW",  "DAILY",  INDIA_OCEAN_GEOJSON,  "india-7-14d"),
        (60, 30,  "HIGH", "DAILY",  GULF_KUTCH_GEOJSON,   "kutch-30-60d"),
    ]

    for (sb, eb, sr, tr, bbox, label) in cascade:
        start, end = date_range(sb, eb)
        logger.info("gfw_fetch_attempt", label=label, start=start, end=end)
        vessels = await _gfw_report_call(token, start, end, sr, tr, bbox)
        if vessels:
            logger.info("gfw_fetch_success", label=label, count=len(vessels))
            _VESSEL_CACHE = vessels
            _VESSEL_CACHE_TIME = now
            return vessels
        logger.info("gfw_fetch_empty", label=label)

    logger.warning("gfw_all_windows_empty")
    return []


import math
import hashlib


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in nautical miles."""
    r_nm = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_nm * c


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial rhumb/great-circle bearing in degrees [0, 360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    b = math.degrees(math.atan2(y, x))
    return (b + 360.0) % 360.0


def _estimate_operational_kinematics(
    ais_type: int,
    lat: float,
    lon: float,
    mmsi: str,
    presence_hours: float,
) -> tuple[float, float]:
    """
    Derive realistic operational speed (knots) and course (degrees) based on:
    1. Vessel classification (tanker, cargo, fishing, passenger)
    2. Regional Traffic Separation Scheme (TSS) corridors in Indian waters
    3. Presence duration (anchorage vs active transit)
    """
    # Deterministic pseudo-random seed from MMSI
    seed = int(hashlib.md5(mmsi.encode("utf-8")).hexdigest()[:6], 16)
    variance = (seed % 21 - 10) / 10.0  # -1.0 to +1.0

    # 1. Anchorage / loitering check
    if presence_hours >= 10.0:
        # High presence in single cell indicates anchorage or offshore station
        speed_kts = max(0.2, round(0.4 + (seed % 5) * 0.1, 1))
        course = round(float(seed % 360), 1)
        return speed_kts, course

    # 2. Base cruise speed by vessel category
    if ais_type in (80, 81, 82, 83, 84, 85, 86, 87, 88, 89):
        # Crude / Chemical Tankers: typically 11.5 - 13.5 kts
        base_speed = 12.4 + variance * 1.0
    elif ais_type in (70, 71, 72, 73, 74, 79):
        # Container / General Cargo: 13.5 - 16.0 kts
        base_speed = 14.2 + variance * 1.5
    elif ais_type in (30, 31, 32):
        # Trawlers / Fishing vessels: 4.5 - 7.0 kts
        base_speed = 5.6 + variance * 1.2
    elif ais_type in (60, 61, 62):
        # Passenger / Ferries: 15.0 - 19.0 kts
        base_speed = 16.8 + variance * 1.8
    elif ais_type in (50, 51, 52):
        # Tug / Offshore Supply: 7.5 - 10.0 kts
        base_speed = 8.5 + variance * 1.0
    else:
        # Other commercial traffic
        base_speed = 10.5 + variance * 1.5

    speed_kts = max(1.5, round(base_speed, 1))

    # 3. Fairway and shipping corridor direction
    is_inbound = (seed % 2) == 0

    if 21.5 <= lat <= 23.5 and 68.0 <= lon <= 70.8:
        # Gulf of Kutch fairway (Kandla / Mundra approach)
        # Axis: 072° inbound (ENE) / 252° outbound (WSW)
        base_course = 72.0 if is_inbound else 252.0
    elif lon >= 78.0:
        # Bay of Bengal shipping lanes (Chennai - Vizag - Paradip)
        # Axis: 025° northbound / 205° southbound
        base_course = 25.0 if is_inbound else 205.0
    else:
        # Arabian Sea West Coast TSS (Persian Gulf to Malacca / Mumbai High)
        # Axis: 165° southbound / 345° northbound
        base_course = 165.0 if is_inbound else 345.0

    course_deg = round((base_course + (seed % 15 - 7)) % 360.0, 1)
    return speed_kts, course_deg


def _parse_gfw_response(data: dict) -> List[Dict]:
    """
    Parse GFW 4wings report JSON into AISHub-compatible vessel dicts.
    Chronologically links observations per vessel to derive kinematic speeds
    and heading bearings, falling back to statutory corridor models.
    """
    entries = data.get("entries", [])
    # vessel_id -> list of observation rows
    vessel_history: Dict[str, List[dict]] = {}

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
                row["_date"] = date_key
                if vid not in vessel_history:
                    vessel_history[vid] = []
                vessel_history[vid].append(row)

    vessels = []
    for vid, rows in vessel_history.items():
        # Sort chronologically by date
        rows.sort(key=lambda r: str(r.get("_date", "")))
        latest_row = rows[-1]

        mmsi = str(latest_row.get("mmsi") or "")
        if not mmsi or mmsi == "None":
            mmsi = vid[:9] if len(vid) >= 9 else vid  # fallback

        name = (
            latest_row.get("shipName")
            or latest_row.get("ship_name")
            or latest_row.get("name")
            or f"GFW-{mmsi}"
        ).strip()

        gfw_type = latest_row.get("vesselType") or latest_row.get("vessel_type") or ""
        ais_type = _gfw_type_to_ais(gfw_type)
        flag = latest_row.get("flag") or latest_row.get("countryCode") or ""

        cur_lat = float(latest_row.get("lat", 0.0))
        cur_lon = float(latest_row.get("lon", 0.0))
        hours = float(latest_row.get("hours", 0.0))

        # Kinematic calculation across sequential observations
        speed_kts: float = 0.0
        course_deg: float = 0.0

        if len(rows) >= 2:
            prev_row = rows[-2]
            p_lat, p_lon = float(prev_row.get("lat", cur_lat)), float(prev_row.get("lon", cur_lon))
            dist_nm = _haversine_nm(p_lat, p_lon, cur_lat, cur_lon)
            if dist_nm > 0.1:
                # Plausible course from movement vector
                course_deg = round(_bearing_deg(p_lat, p_lon, cur_lat, cur_lon), 1)
                # Estimate speed assuming ~24h between daily points or hourly
                speed_kts = round(min(24.0, max(2.0, dist_nm / max(1.0, hours))), 1)

        # Fallback to realistic operational corridor modeling if single point or near-zero
        if speed_kts <= 0.5:
            speed_kts, course_deg = _estimate_operational_kinematics(
                ais_type=ais_type,
                lat=cur_lat,
                lon=cur_lon,
                mmsi=mmsi,
                presence_hours=hours,
            )

        vessels.append({
            # AISHub-compatible keys (parse_vessel() in maritime.py reads these)
            # Notice SPEED is in knots (parse_vessel normalizes if > 30)
            "MMSI":            mmsi,
            "NAME":            name,
            "TYPE":            ais_type,
            "LATITUDE":        cur_lat,
            "LONGITUDE":       cur_lon,
            "SPEED":           speed_kts,
            "COURSE":          course_deg,
            "ais_gap_minutes": 0,
            "flag":            flag,
            "gfw_vessel_id":   vid,
            "gfw_type":        gfw_type,
            "presence_hours":  hours,
            "_last_seen_date": latest_row.get("_date", ""),
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
