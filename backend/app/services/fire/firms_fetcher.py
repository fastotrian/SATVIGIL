"""
SATVIGIL — Fire Module: NASA FIRMS Fetcher + Fire Classifier

Pulls VIIRS/MODIS thermal hotspot data for India.
Classifies each hotspot as: industrial | wildfire | stubble | gas_flare | mining

Datasets used:
  - NASA FIRMS (VIIRS 375m NRT): https://firms.modaps.eosdis.nasa.gov/api/
  - VIIRS Nightfire (VNF) for gas flare separation: https://eogdata.mines.edu/products/vnf/
  - OpenStreetMap via Geofabrik India shapefile for land use context
  - CPCB Critically Polluted Areas list (hardcoded from public PDF)
"""
import httpx
import pandas as pd
from io import StringIO
from datetime import datetime
from typing import List, Dict, Tuple
from app.core.config import settings
import structlog

logger = structlog.get_logger()

# ── CPCB Critically Polluted Industrial Clusters (43 flagged areas) ───────────
# Source: CPCB Comprehensive Environmental Assessment of Industrial Clusters, 2009
# Coordinates from public records — verify all before production use
CPCB_CLUSTERS = [
    {"name": "Vapi",           "lat": 20.3733, "lon": 72.9050, "state": "Gujarat"},
    {"name": "Ankleshwar",     "lat": 21.6265, "lon": 73.0025, "state": "Gujarat"},
    {"name": "Ludhiana",       "lat": 30.9010, "lon": 75.8573, "state": "Punjab"},
    {"name": "Tarapur",        "lat": 19.8607, "lon": 72.6900, "state": "Maharashtra"},
    {"name": "Visakhapatnam",  "lat": 17.6868, "lon": 83.2185, "state": "Andhra Pradesh"},
    {"name": "Paradip",        "lat": 20.3167, "lon": 86.6086, "state": "Odisha"},
    {"name": "Jharia",         "lat": 23.7500, "lon": 86.4167, "state": "Jharkhand"},
    {"name": "Korba",          "lat": 22.3595, "lon": 82.7501, "state": "Chhattisgarh"},
    {"name": "Singrauli",      "lat": 24.2004, "lon": 82.6697, "state": "MP"},
    {"name": "Chandrapur",     "lat": 19.9615, "lon": 79.2961, "state": "Maharashtra"},
    # Add remaining 33 clusters from CPCB official list
]

# Stubble burning season months (India-specific)
STUBBLE_SEASON_MONTHS = [10, 11, 12, 1, 2, 3]  # Oct–Mar (Rabi + Kharif seasons)

# Fire Radiative Power thresholds (MW)
FRP_INDUSTRIAL_THRESHOLD = 300   # Very high FRP = likely industrial
FRP_FLARE_MIN = 50               # Gas flares are persistent at medium FRP


async def fetch_firms_india(days: int = 1, sensor: str = "VIIRS_SNPP_NRT") -> pd.DataFrame:
    """
    Fetch active fire detections over India from NASA FIRMS API.

    Sensor options:
      VIIRS_SNPP_NRT    — 375m, best for India, recommended
      MODIS_NRT         — 1km, longer history
      VIIRS_NOAA20_NRT  — additional coverage

    Returns DataFrame with columns:
      latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
      satellite, confidence, version, bright_ti5, frp, daynight, type
    """
    url = (
        f"{settings.FIRMS_BASE_URL}/area/csv"
        f"/{settings.FIRMS_MAP_KEY}/{sensor}"
        f"/{settings.INDIA_BBOX}/{days}"
    )

    async with httpx.AsyncClient(timeout=60, verify=False) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text))
            logger.info("firms_fetch_success", rows=len(df), sensor=sensor, days=days)
            return df
        except Exception as e:
            logger.error("firms_fetch_failed", error=str(e))
            return pd.DataFrame()


def is_near_cpcb_cluster(lat: float, lon: float, radius_km: float = 10.0) -> Tuple[bool, str]:
    """Check if coordinates fall within radius of a CPCB Critically Polluted Area."""
    for cluster in CPCB_CLUSTERS:
        # Rough conversion: 1 degree ≈ 111 km
        dist_deg = ((lat - cluster["lat"]) ** 2 + (lon - cluster["lon"]) ** 2) ** 0.5
        if dist_deg < (radius_km / 111.0):
            return True, cluster["name"]
    return False, ""


def classify_fire(row: dict, land_use: str = "unknown") -> str:
    """
    Classify a FIRMS thermal detection into one of 5 fire types.

    Rules applied in priority order:
    1. Gas flare   — high FRP + night + industrial/petroleum land use
    2. Industrial  — near CPCB cluster OR high FRP + industrial land use
    3. Wildfire    — land use is forest/natural
    4. Stubble     — land use is farmland + stubble season months
    5. Mining      — land use is quarry/mine
    6. Unknown     — fallback

    Returns: "gas_flare" | "industrial" | "wildfire" | "stubble" | "mining" | "unknown"
    """
    lat = row.get("latitude", 0)
    lon = row.get("longitude", 0)
    frp = row.get("frp", 0) or 0
    daynight = row.get("daynight", "D")
    acq_date = row.get("acq_date", "")

    try:
        month = int(str(acq_date)[5:7])
    except Exception:
        month = 0

    near_cpcb, cluster_name = is_near_cpcb_cluster(lat, lon)

    # Priority 1: Gas flare (persistent night source at petroleum/industrial site)
    if frp > FRP_FLARE_MIN and daynight == "N" and land_use in ["industrial", "petroleum"]:
        return "gas_flare"

    # Priority 2: Industrial fire
    if near_cpcb or (frp > FRP_INDUSTRIAL_THRESHOLD and land_use == "industrial"):
        return "industrial"

    # Priority 3: Wildfire
    if land_use in ["forest", "wood", "nature_reserve", "national_park"]:
        return "wildfire"

    # Priority 4: Stubble / agricultural burning
    if land_use in ["farmland", "meadow", "orchard", "agriculture"] and month in STUBBLE_SEASON_MONTHS:
        return "stubble"

    # Priority 5: Mining
    if land_use in ["quarry", "mine", "landfill"]:
        return "mining"

    # Fallback — still flag with high FRP as potential industrial
    if frp > FRP_INDUSTRIAL_THRESHOLD:
        return "industrial"

    return "unknown"


def get_responding_agency(fire_type: str) -> Dict:
    """Return the government agency that should respond to each fire type."""
    agencies = {
        "gas_flare":   {"agency": "PESO + State PCB", "action": "Check permit compliance, issue show-cause notice"},
        "industrial":  {"agency": "State Fire Services + CPCB", "action": "Emergency response + PESO investigation"},
        "wildfire":    {"agency": "State Forest Department", "action": "Deploy firefighting teams via FSI FAST system"},
        "stubble":     {"agency": "CAQM + District Magistrate", "action": "Issue notice under CAQM Act 2021, Section 14"},
        "mining":      {"agency": "IBM + State Directorate of Mines", "action": "Cross-check lease database, file MMDR Act violation"},
        "unknown":     {"agency": "CPCB Monitoring Cell", "action": "Flag for ground verification"},
    }
    return agencies.get(fire_type, agencies["unknown"])
