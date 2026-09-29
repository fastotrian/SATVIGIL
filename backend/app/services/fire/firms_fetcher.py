"""
SATVIGIL — Fire Module: NASA FIRMS Fetcher + Fire Classifier V2
Pull VIIRS/MODIS thermal hotspot data for India and classify into:
  industrial | wildfire | stubble | gas_flare | mining | unknown
Ground-truth reference: scripts/india_fire_intelligence_v2 (1).py
"""
import httpx
import pandas as pd
from io import StringIO
from typing import Dict, Tuple, Any
from datetime import datetime
from app.core.config import settings
import structlog
from app.services.fire.geo_intelligence import geo_engine, CPA_ZONES, FOREST_ZONES, MINING_ZONES, INDUSTRIAL_ZONES, GAS_ZONES, CROP_ZONES

logger = structlog.get_logger()

CONFIDENCE_MIN = 50.0


def parse_confidence_score(val: Any) -> float:
    """Standardizes FIRMS categorical / numeric confidence to a 0-100 float."""
    if pd.isna(val) or val is None:
        return 70.0
    s = str(val).strip().lower()
    if s in {"high", "h"}:
        return 90.0
    if s in {"nominal", "n", "medium", "m"}:
        return 70.0
    if s in {"low", "l"}:
        return 30.0
    try:
        return float(val)
    except Exception:
        return 50.0


async def fetch_firms_india(days: int = 1, sensor: str = "VIIRS_SNPP_NRT") -> pd.DataFrame:
    """Fetches active thermal hotspot detections over the Indian subcontinent."""
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


def is_near_cpcb_cluster(lat: float, lon: float, radius_km: float = 15.0) -> Tuple[bool, str]:
    """Checks proximity to 19 CPCB Critically Polluted Area clusters."""
    is_near, cpa_name, _ = geo_engine.nearest_cpcb_cpa(lat, lon)
    return is_near, cpa_name


def classify_fire_v2(row: dict) -> dict:
    """
    Competitive 5-class scoring engine grounded in scripts/india_fire_intelligence_v2 (1).py:
    - Stubble burn (crop regions + seasonal window)
    - Wildfire / Forest burn (Bharatmaps RFA authoritative polygons + regional forest bboxes)
    - Industrial fire (15km proximity to major heavy industrial zones + high FRP)
    - Gas flare (petroleum / flare zones + recurring DBSCAN cluster + FRP 10-100 MW)
    - Mining thermal (coal & mineral belts + recurring DBSCAN cluster)
    """
    try:
        lat = float(row.get("latitude", 0))
        lon = float(row.get("longitude", 0))
        frp = float(row.get("frp", 0) or 0)
    except Exception:
        lat, lon, frp = 0.0, 0.0, 0.0

    recurring = bool(row.get("is_recurring_hotspot", False))
    acq_date = str(row.get("acq_date", ""))

    try:
        month = int(acq_date[5:7]) if len(acq_date) >= 7 else datetime.utcnow().month
    except Exception:
        month = datetime.utcnow().month

    scores = {
        "stubble": 0.0,
        "wildfire": 0.0,
        "industrial": 0.0,
        "gas_flare": 0.0,
        "mining": 0.0,
    }
    reasons = {k: [] for k in scores}

    # 1. Stubble burning evaluation
    crop, crop_name = geo_engine.crop_hit(lat, lon)
    seasonal = month in {4, 5, 10, 11, 12, 1, 2, 3}  # Kharif & Rabi residue windows
    if crop:
        scores["stubble"] += 60.0
        reasons["stubble"].append(f"crop-region:{crop_name}")
    if seasonal:
        scores["stubble"] += 25.0
        reasons["stubble"].append("seasonal-window")

    # 2. Wildfire / Forest burning evaluation (Bharatmaps RFA + Forest Belts)
    is_forest, forest_reason = geo_engine.forest_hit(lat, lon)
    if is_forest:
        if "authoritative_forest_polygon" in forest_reason:
            scores["wildfire"] += 75.0
        else:
            scores["wildfire"] += 45.0
        reasons["wildfire"].append(forest_reason)

    # 3. Industrial fire evaluation
    ind_d, ind_name = geo_engine.nearest_industrial_zone(lat, lon)
    if ind_name:
        scores["industrial"] += 60.0
        reasons["industrial"].append(f"industrial-proximity:{ind_name} ({ind_d:.1f}km)")
    if frp >= 50.0:
        scores["industrial"] += 25.0
        reasons["industrial"].append("high-FRP(>=50MW)")
    elif frp >= 20.0:
        scores["industrial"] += 10.0
        reasons["industrial"].append("elevated-FRP(>=20MW)")

    # 4. Gas flare evaluation
    gas_d, gas_name = geo_engine.nearest_gas_zone(lat, lon)
    if gas_name:
        scores["gas_flare"] += 60.0
        reasons["gas_flare"].append(f"gas-oil-proximity:{gas_name} ({gas_d:.1f}km)")
    if recurring:
        scores["gas_flare"] += 25.0
        reasons["gas_flare"].append("recurring-spatial-cluster")
    if 10.0 <= frp <= 100.0:
        scores["gas_flare"] += 15.0
        reasons["gas_flare"].append("FRP-compatible-thermal-pattern(10-100MW)")

    # 5. Mining thermal anomaly evaluation
    is_mining, mining_name = geo_engine.mining_hit(lat, lon)
    if is_mining:
        scores["mining"] += 65.0
        reasons["mining"].append(f"mining-belt:{mining_name}")
    if recurring:
        scores["mining"] += 25.0
        reasons["mining"].append("recurring-spatial-cluster")

    # Competitive winner decision rule: threshold >= 60.0
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 60.0:
        final_type = "unknown"
        final_reason = "insufficient-contextual-evidence"
    else:
        final_type = best_type
        final_reason = "; ".join(reasons[best_type]) or "contextual-score"

    # CPCB CPA proximity check
    is_near_cpcb, cpcb_name, cpcb_dist = geo_engine.nearest_cpcb_cpa(lat, lon)
    agency_info = get_responding_agency(final_type)

    return {
        "fire_type": final_type,
        "classification_score": round(best_score, 1),
        "classification_confidence": round(min(best_score, 99.0), 1),
        "classification_reason": final_reason,
        "near_cpcb_cluster": is_near_cpcb,
        "cpcb_cpa_name": cpcb_name if is_near_cpcb else None,
        "cpcb_distance_km": cpcb_dist if is_near_cpcb else None,
        "stubble_score": round(scores["stubble"], 1),
        "wildfire_score": round(scores["wildfire"], 1),
        "industrial_score": round(scores["industrial"], 1),
        "gas_flare_score": round(scores["gas_flare"], 1),
        "mining_score": round(scores["mining"], 1),
        "responding_agency": agency_info.get("agency"),
        "recommended_action": agency_info.get("action"),
    }


def classify_fire(row: dict, land_use: str = "unknown") -> str:
    """Legacy wrapper returning classified string category."""
    res = classify_fire_v2(row)
    return res["fire_type"]


def get_responding_agency(fire_type: str) -> Dict[str, str]:
    """Authoritative Indian statutory enforcement mapping."""
    agencies = {
        "stubble": {
            "agency": "CAQM + District Magistrate",
            "action": "Issue notice under Commission for Air Quality Management Act 2021, Section 14",
        },
        "wildfire": {
            "agency": "State Forest Department",
            "action": "Deploy frontline forest range squads via FSI FAST 3.0 alerting system",
        },
        "industrial": {
            "agency": "State Fire Services + CPCB",
            "action": "Initiate emergency fire containment + PESO hazardous chemicals audit",
        },
        "gas_flare": {
            "agency": "PESO + State PCB",
            "action": "Verify flare emission permit compliance; issue Air Act 1981 Section 31A notice",
        },
        "mining": {
            "agency": "Indian Bureau of Mines + State Directorate of Mines",
            "action": "Cross-check IBM lease boundaries; initiate MMDR Act 1957 Section 4(1) enforcement",
        },
        "unknown": {
            "agency": "CPCB Surveillance Cell",
            "action": "Flag for ground-truth verification and drone reconnaissance",
        },
    }
    return agencies.get(fire_type, agencies["unknown"])
