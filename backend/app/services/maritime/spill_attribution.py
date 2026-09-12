"""
SATVIGIL — Maritime Oil Spill Attribution Service
Extracts the 4-signal multi-factor scoring methodology from ml/notebooks/vessel_oil_spill_risk_scoring.ipynb:
1. Spatial Proximity (Haversine distance to spill center) - 40%
2. Vessel Type Prior Risk (Tanker vs Cargo vs Fishing) - 25%
3. Heading / Course Alignment with Spill Trail Bearing - 20%
4. Behavioral Anomaly (AIS gaps, loitering, speed deviation) - 15%
"""
import math
from typing import Dict, List, Optional
import structlog
import pandas as pd
import numpy as np

logger = structlog.get_logger()

# Configured scoring weights matching research notebook
W_DISTANCE = 0.40
W_TYPE = 0.25
W_HEADING = 0.20
W_ANOMALY = 0.15
DEFAULT_DISTANCE_CUTOFF_KM = 30.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance in kilometers between two geographic coordinates.
    """
    R = 6371.0  # Earth mean radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def vessel_type_risk(vessel_type: int) -> float:
    """
    Calculate prior spill risk score based on AIS vessel type code.
    - 80–89: Tanker (Crude/Oil/Chemical) -> 1.0 (Highest Risk)
    - 70–79: Cargo (Container/Bulk)     -> 0.7 (High Risk)
    - 30–39: Fishing                    -> 0.2 (Low Risk)
    - Other/Unknown                     -> 0.3 (Neutral-Low)
    """
    try:
        vt = int(vessel_type)
    except (ValueError, TypeError):
        return 0.3

    if 80 <= vt <= 89:
        return 1.0
    if 70 <= vt <= 79:
        return 0.7
    if 30 <= vt <= 39:
        return 0.2
    return 0.3


def heading_alignment_score(vessel_cog: float, trail_bearing: float, tolerance: float = 45.0) -> float:
    """
    Assess how closely vessel Course Over Ground (COG) aligns with the oil slick's
    drift/trail orientation from satellite SAR imagery.
    """
    diff = abs((vessel_cog - trail_bearing + 180.0) % 360.0 - 180.0)
    if diff <= tolerance:
        return round(1.0 - (diff / tolerance) * 0.3, 3)
    return round(max(0.0, 1.0 - (diff / 180.0)), 3)


def calculate_behavior_score_from_track(track: List[Dict], spill_time: pd.Timestamp, time_window_hours: int = 12) -> float:
    window_start = spill_time - pd.Timedelta(hours=time_window_hours)
    window_end = spill_time + pd.Timedelta(hours=time_window_hours)

    valid_speeds = []
    for point in track:
        pt_time = pd.Timestamp(point["timestamp"])
        if window_start <= pt_time <= window_end:
            speed = point.get("sog", 0.0)
            if speed > 0 and not pd.isna(speed):
                valid_speeds.append(speed)

    if len(valid_speeds) < 3:
        return 0.0

    mean_speed = np.mean(valid_speeds)
    std_speed = np.std(valid_speeds)

    if std_speed == 0 or pd.isna(std_speed):
        return 0.0

    z_scores = [abs(s - mean_speed) / std_speed for s in valid_speeds]
    max_z = max(z_scores)

    if max_z >= 3:
        return 1.0
    if max_z >= 2:
        return 0.7
    if max_z >= 1.5:
        return 0.4
    return 0.0


def score_vessel_for_spill(
    vessel: Dict,
    spill_lat: float,
    spill_lon: float,
    spill_trail_bearing: float = 250.0,
    distance_cutoff_km: float = DEFAULT_DISTANCE_CUTOFF_KM,
    spill_time: Optional[pd.Timestamp] = None,
) -> Optional[Dict]:
    """
    Compute combined 4-signal oil spill attribution score for a candidate vessel.
    Returns None if vessel exceeds the distance cutoff radius.
    """
    lat = float(vessel.get("LATITUDE", 0.0))
    lon = float(vessel.get("LONGITUDE", 0.0))
    mmsi = str(vessel.get("MMSI", "UNKNOWN"))
    vessel_name = str(vessel.get("NAME") or "Unknown Vessel").strip()
    vessel_type = int(vessel.get("TYPE", 0))
    cog = float(vessel.get("COURSE", vessel.get("HEADING", 0.0)))
    raw_speed = float(vessel.get("SPEED", 0.0))
    speed_knots = raw_speed / 10.0 if raw_speed > 30 else raw_speed
    ais_gap_minutes = int(vessel.get("ais_gap_minutes", 0))
    track = vessel.get("track", [])

    # Signal 1: Proximity
    dist_km = haversine(lat, lon, spill_lat, spill_lon)
    if dist_km > distance_cutoff_km:
        return None

    distance_score = 1.0 - (dist_km / distance_cutoff_km)

    # Signal 2: Vessel Type Prior
    type_score = vessel_type_risk(vessel_type)

    # Signal 3: Course / Heading Alignment
    heading_score = heading_alignment_score(cog, spill_trail_bearing)

    # Signal 4: Behavioral Anomaly (Dark AIS transponder gap or loitering, or z-score)
    if track and spill_time:
        anomaly_score = calculate_behavior_score_from_track(track, spill_time)
        has_anomaly = anomaly_score > 0.0
    else:
        has_anomaly = (ais_gap_minutes >= 30) or (speed_knots < 1.0 and ais_gap_minutes >= 10)
        anomaly_score = 1.0 if has_anomaly else 0.0

    # Weighted composite score (0.0 to 1.0)
    composite_risk = (
        W_DISTANCE * distance_score
        + W_TYPE * type_score
        + W_HEADING * heading_score
        + W_ANOMALY * anomaly_score
    )

    return {
        "mmsi": mmsi,
        "vessel_name": vessel_name,
        "risk_score": round(min(composite_risk, 1.0), 2),
        "distance_km": dist_km,
        "type_risk": type_score,
        "heading_score": heading_score,
        "behavioral_anomaly": has_anomaly,
    }


def rank_vessels_for_spill(
    vessels: List[Dict],
    spill_lat: float,
    spill_lon: float,
    spill_trail_bearing: float = 250.0,
    top_n: int = 5,
    distance_cutoff_km: float = DEFAULT_DISTANCE_CUTOFF_KM,
    spill_time: Optional[pd.Timestamp] = None,
) -> List[Dict]:
    """
    Score and rank candidate vessels for a detected oil spill event.
    Returns sorted list of highest-probability suspect vessels.
    """
    candidates = []
    for v in vessels:
        score_record = score_vessel_for_spill(v, spill_lat, spill_lon, spill_trail_bearing, distance_cutoff_km, spill_time)
        if score_record:
            candidates.append(score_record)

    candidates.sort(key=lambda x: x["risk_score"], reverse=True)
    return candidates[:top_n]
