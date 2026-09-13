"""
SATVIGIL — Fire Module: NASA FIRMS Fetcher + Fire Classifier V2

Pulls VIIRS/MODIS thermal hotspot data for India.
Classifies each hotspot as: industrial | wildfire | stubble | gas_flare | mining
Uses a competitive scoring engine (V2) and falls back to geo_intelligence boundaries.
"""
import httpx
import pandas as pd
from io import StringIO
import math
from typing import Dict, Tuple
from app.core.config import settings
import structlog
from app.services.fire.geo_intelligence import geo_engine

logger = structlog.get_logger()

# ── CPCB Critically Polluted Industrial Clusters (19 V2 CPA zones) ───────────
CPA_ZONES = [
    (30.90,75.85,15,"Ludhiana"),
    (21.62,73.00,15,"Ankleshwar"),
    (20.37,72.91,15,"Vapi"),
    (28.67,77.43,15,"Ghaziabad"),
    (28.54,77.39,15,"Noida"),
    (28.20,76.86,15,"Bhiwadi"),
    (23.02,72.62,15,"Vatva"),
    (19.97,79.30,15,"Chandrapur"),
    (20.85,85.10,20,"Angul-Talcher"),
    (21.47,83.98,15,"Jharsuguda"),
    (29.39,76.96,15,"Panipat"),
    (24.20,82.68,20,"Singrauli"),
    (17.48,78.35,15,"Patancheru-Bollaram"),
    (10.99,76.96,15,"Coimbatore"),
    (13.08,80.27,20,"Manali-Chennai"),
    (19.88,75.34,15,"Aurangabad"),
    (19.23,73.08,15,"Dombivali"),
    (23.74,86.42,15,"Mandi Gobindgarh"),
    (23.80,86.43,15,"Jharia-Dhanbad")
]

FOREST_ZONES = [
    (8.0,14.5,74.0,78.5), (14.0,20.5,73.0,80.5),
    (18.0,24.5,78.0,84.5), (20.0,27.0,81.0,87.5),
    (22.0,27.0,88.0,92.5), (27.0,35.5,73.0,80.5),
    (28.0,35.5,80.0,93.5)
]

MINING_ZONES = [
    (23.60,23.95,86.20,86.55,"Jharia"),
    (23.55,23.95,86.60,87.20,"Raniganj"),
    (20.50,21.20,85.00,86.20,"Talcher-Angul"),
    (22.10,23.00,81.90,83.40,"Korba"),
    (23.50,24.50,81.70,83.30,"Singranuli"),
    (20.00,21.80,78.70,79.60,"Chandrapur-Wardha"),
    (25.20,26.20,91.80,92.80,"Jaintia Hills")
]

INDUSTRIAL_ZONES = [
    (20.27,73.00,15,"Vapi"),
    (21.62,73.00,15,"Ankleshwar"),
    (23.00,72.60,15,"Vatva-Ahmedabad"),
    (30.90,75.85,15,"Ludhiana"),
    (29.39,76.96,15,"Panipat"),
    (28.67,77.43,15,"Ghaziabad"),
    (28.54,77.39,15,"Noida"),
    (22.07,82.15,15,"Korba"),
    (21.15,79.09,15,"Nagpur")
]

GAS_ZONES = [
    (21.62,73.00,20,"Ankleshwar"),
    (20.27,73.00,20,"Vapi"),
    (20.27,85.82,20,"Paradip"),
    (22.75,69.70,25,"Kutch")
]

CROP_ZONES = [
    (29.5,32.7,73.8,77.0,"Punjab-Haryana"),
    (27.0,30.5,77.0,80.5,"Western Uttar Pradesh"),
    (27.0,30.0,74.0,77.0,"Northeast Rajasthan")
]

async def fetch_firms_india(days: int = 1, sensor: str = "VIIRS_SNPP_NRT") -> pd.DataFrame:
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

def dist_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def bbox_hit(lat, lon, z):
    return z[0] <= lat <= z[1] and z[2] <= lon <= z[3]

def nearest_zone(lat, lon, zones):
    hits = []
    for zlat,zlon,radius,name in zones:
        d = dist_km(lat,lon,zlat,zlon)
        if d <= radius:
            hits.append((d,name))
    return min(hits) if hits else (None,None)

def is_near_cpcb_cluster(lat: float, lon: float, radius_km: float = 15.0) -> Tuple[bool, str]:
    hits = []
    for zlat,zlon,rad,name in CPA_ZONES:
        d = dist_km(lat,lon,zlat,zlon)
        if d <= radius_km:
            hits.append((d,name))
    if hits:
        return True, min(hits)[1]
    return False, ""

def crop_hit(lat,lon):
    for z in CROP_ZONES:
        if bbox_hit(lat,lon,z):
            return True,z[4]
    return False,None

def mining_fallback_hit(lat,lon):
    for z in MINING_ZONES:
        if bbox_hit(lat,lon,z):
            return True,z[4]
    return False,None

def forest_fallback_hit(lat,lon):
    for z in FOREST_ZONES:
        if bbox_hit(lat,lon,z):
            return True,"fallback_forest_bbox"
    return False,None

def classify_fire_v2(row: dict) -> dict:
    try:
        lat = float(row.get("latitude", 0))
        lon = float(row.get("longitude", 0))
        frp = float(row.get("frp", 0) or 0)
    except:
        lat, lon, frp = 0.0, 0.0, 0.0
        
    recurring = bool(row.get("is_recurring_hotspot", False))
    acq_date = row.get("acq_date", "")
    
    try:
        month = int(str(acq_date)[5:7])
    except Exception:
        month = 0

    scores = {
        "stubble": 0.0,
        "wildfire": 0.0,
        "industrial": 0.0,
        "gas_flare": 0.0,
        "mining": 0.0
    }
    reasons = {k:[] for k in scores}

    # Stubble
    crop, crop_name = crop_hit(lat,lon)
    seasonal = month in {4,5,10,11,12,1,2,3}
    if crop:
        scores["stubble"] += 60
        reasons["stubble"].append(f"crop-region:{crop_name}")
    if seasonal:
        scores["stubble"] += 25
        reasons["stubble"].append("seasonal-window")

    # Forest
    if geo_engine.forest_hit(lat, lon):
        scores["wildfire"] += 75
        reasons["wildfire"].append("authoritative_forest_polygon")
    else:
        forest, forest_reason = forest_fallback_hit(lat,lon)
        if forest:
            scores["wildfire"] += 45
            reasons["wildfire"].append(forest_reason)

    # Industrial
    ind_d, ind_name = nearest_zone(lat,lon,INDUSTRIAL_ZONES)
    if ind_name:
        scores["industrial"] += 60
        reasons["industrial"].append(f"industrial-proximity:{ind_name}")
    if frp >= 50:
        scores["industrial"] += 25
        reasons["industrial"].append("high-FRP")
    elif frp >= 20:
        scores["industrial"] += 10
        reasons["industrial"].append("elevated-FRP")

    # Gas flare
    gas_d, gas_name = nearest_zone(lat,lon,GAS_ZONES)
    if gas_name:
        scores["gas_flare"] += 60
        reasons["gas_flare"].append(f"gas-oil-proximity:{gas_name}")
    if recurring:
        scores["gas_flare"] += 25
        reasons["gas_flare"].append("recurring-spatial-cluster")
    if 10 <= frp <= 100:
        scores["gas_flare"] += 15
        reasons["gas_flare"].append("FRP-compatible-thermal-pattern")

    # Mining
    if geo_engine.mining_hit(lat, lon):
        scores["mining"] += 75
        reasons["mining"].append("authoritative_mining_polygon")
    else:
        mining, mining_name = mining_fallback_hit(lat,lon)
        if mining:
            scores["mining"] += 65
            reasons["mining"].append(f"mining-belt:{mining_name}")
    if recurring:
        scores["mining"] += 25
        reasons["mining"].append("recurring-spatial-cluster")

    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score < 60:
        final_type = "unknown"
        reason = "insufficient-contextual-evidence"
    else:
        final_type = best
        reason = "; ".join(reasons[best]) or "contextual-score"

    return {
        "fire_type": final_type,
        "classification_score": round(best_score, 1),
        "classification_reason": reason
    }

def classify_fire(row: dict, land_use: str = "unknown") -> str:
    """Legacy wrapper for backwards compatibility."""
    res = classify_fire_v2(row)
    return res["fire_type"]

def get_responding_agency(fire_type: str) -> Dict:
    agencies = {
        "gas_flare":   {"agency": "PESO + State PCB", "action": "Check permit compliance, issue show-cause notice"},
        "industrial":  {"agency": "State Fire Services + CPCB", "action": "Emergency response + PESO investigation"},
        "wildfire":    {"agency": "State Forest Department", "action": "Deploy firefighting teams via FSI FAST system"},
        "stubble":     {"agency": "CAQM + District Magistrate", "action": "Issue notice under CAQM Act 2021, Section 14"},
        "mining":      {"agency": "IBM + State Directorate of Mines", "action": "Cross-check lease database, file MMDR Act violation"},
        "unknown":     {"agency": "CPCB Monitoring Cell", "action": "Flag for ground verification"},
    }
    return agencies.get(fire_type, agencies["unknown"])
