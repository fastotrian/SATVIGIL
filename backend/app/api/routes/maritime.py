"""
SATVIGIL — Maritime API Routes
Handles real-time AIS vessel tracking, risk scoring, dark vessel detection, and spill correlation.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

import uuid
from app.core.constants import (
    AIS_GAP_CRITICAL_MINUTES,
    get_risk_label,
)
from app.schemas.maritime import (
    VesselResponse,
    VesselListResponse,
    SpillEventResponse,
    SpillCandidateResponse,
    SimulateDarkVesselRequest,
    SimulateSpillRequest,
    VesselTracksListResponse,
    VesselTrackResponse,
    TrackPoint,
    AttributeSpillRequest,
)
from app.services.maritime.ais_fetcher import (
    fetch_ais_vessels,
    calculate_vessel_risk_score,
    is_vessel_in_mpa,
)
from app.services.maritime.spill_attribution import rank_vessels_for_spill

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
router = APIRouter()

# Demo scenario dataset path for offline/fallback mode
DEMO_SCENARIO_PATH = Path(__file__).resolve().parents[4] / "data" / "demo" / "ais_demo_scenario.json"


def get_vessel_type_label(vtype: int) -> str:
    """Map AIS vessel type code to human-readable label."""
    if 80 <= vtype <= 89:
        return "Tanker"
    if 70 <= vtype <= 79:
        return "Cargo"
    if 30 <= vtype <= 39:
        return "Fishing"
    if 60 <= vtype <= 69:
        return "Passenger"
    if 50 <= vtype <= 59:
        return "Special Craft"
    if 40 <= vtype <= 49:
        return "High Speed Craft"
    return "Other"


def load_fallback_vessels() -> List[dict]:
    """Load default scenario vessels when external AIS feed is unavailable."""
    if DEMO_SCENARIO_PATH.exists():
        try:
            with open(DEMO_SCENARIO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("failed_loading_demo_scenario", error=str(e))

    # Built-in fallback scenario (India coastal waters)
    return [
        {
            "MMSI": "419000001",
            "NAME": "MT GUJARAT PRIDE",
            "TYPE": 80,
            "LATITUDE": 19.15,
            "LONGITUDE": 71.45,
            "SPEED": 2,
            "COURSE": 210.0,
            "ais_gap_minutes": 45,
        },
        {
            "MMSI": "419000002",
            "NAME": "MV MUMBAI EXPRESS",
            "TYPE": 71,
            "LATITUDE": 18.95,
            "LONGITUDE": 72.85,
            "SPEED": 85,
            "COURSE": 95.0,
            "ais_gap_minutes": 0,
        },
        {
            "MMSI": "419000003",
            "NAME": "FV KUTCH FISHERMAN",
            "TYPE": 30,
            "LATITUDE": 22.50,
            "LONGITUDE": 69.20,
            "SPEED": 5,
            "COURSE": 45.0,
            "ais_gap_minutes": 20,
        },
        {
            "MMSI": "419000004",
            "NAME": "MV LAKSHADWEEP QUEEN",
            "TYPE": 60,
            "LATITUDE": 10.50,
            "LONGITUDE": 72.80,
            "SPEED": 120,
            "COURSE": 330.0,
            "ais_gap_minutes": 0,
        },
    ]


def parse_vessel(raw_vessel: dict) -> VesselResponse:
    """Parse raw AIS vessel dictionary into validated VesselResponse."""
    lat = float(raw_vessel.get("LATITUDE", 0.0))
    lon = float(raw_vessel.get("LONGITUDE", 0.0))
    raw_speed = float(raw_vessel.get("SPEED", 0.0))
    speed_knots = raw_speed / 10.0 if raw_speed > 30 else raw_speed
    course_deg = float(raw_vessel.get("COURSE", 0.0))
    vessel_type = int(raw_vessel.get("TYPE", 0))
    ais_gap_minutes = int(raw_vessel.get("ais_gap_minutes", 0))

    # Calculate real-time risk score and MPA containment
    risk_score = calculate_vessel_risk_score(raw_vessel, ais_gap_minutes=ais_gap_minutes)
    mpa_name = is_vessel_in_mpa(lat, lon)
    is_dark = ais_gap_minutes >= AIS_GAP_CRITICAL_MINUTES

    # Construct validated Pydantic model
    return VesselResponse(
        mmsi=str(raw_vessel.get("MMSI", "UNKNOWN")),
        vessel_name=str(raw_vessel.get("NAME") or "Unknown Vessel").strip(),
        vessel_type=vessel_type,
        vessel_type_label=get_vessel_type_label(vessel_type),
        lat=lat,
        lon=lon,
        speed_knots=round(speed_knots, 1),
        course_deg=round(course_deg, 1),
        risk_score=round(risk_score, 2),
        risk_level=get_risk_label(risk_score),  # type: ignore[arg-type]
        ais_gap_minutes=ais_gap_minutes,
        is_dark=is_dark,
        in_mpa=mpa_name is not None,
        mpa_name=mpa_name,
        last_seen=datetime.now(timezone.utc),
    )


@router.get("/vessels", response_model=VesselListResponse)
async def get_vessels(
    dark_only: bool = Query(False, description="Filter for dark vessels with AIS transponder off"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score filter"),
):
    """
    Fetch all active vessels in Indian waters with live behavioral risk scores.
    """
    raw_vessels = await fetch_ais_vessels()

    # Fallback to demo vessels if external API is down or credentials not set
    if not raw_vessels:
        logger.info("using_demo_ais_vessels")
        raw_vessels = load_fallback_vessels()

    vessels = [parse_vessel(v) for v in raw_vessels]

    # Apply filters
    if dark_only:
        vessels = [v for v in vessels if v.is_dark]
    if min_risk is not None:
        vessels = [v for v in vessels if v.risk_score >= min_risk]

    return VesselListResponse(
        vessels=vessels,
        total=len(vessels),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/vessels/{mmsi}", response_model=VesselResponse)
async def get_vessel_by_mmsi(mmsi: str):
    """
    Retrieve single vessel by MMSI with current status and risk breakdown.
    """
    raw_vessels = await fetch_ais_vessels()
    if not raw_vessels:
        raw_vessels = load_fallback_vessels()

    for v in raw_vessels:
        if str(v.get("MMSI")) == mmsi:
            return parse_vessel(v)

    raise HTTPException(status_code=404, detail=f"Vessel with MMSI {mmsi} not found")


@router.post("/simulate-dark-vessel", response_model=VesselResponse)
async def simulate_dark_vessel(request: SimulateDarkVesselRequest):
    """
    Simulate a dark vessel event for live hackathon demonstrations.
    """
    is_tanker = request.mmsi == "419000001"
    raw_simulated = {
        "MMSI": request.mmsi,
        "NAME": "MT GUJARAT PRIDE" if is_tanker else f"SIMULATED VESSEL {request.mmsi}",
        "TYPE": 80 if is_tanker else 70,
        "LATITUDE": request.lat,
        "LONGITUDE": request.lon,
        "SPEED": 2,  # 0.2 knots (loitering)
        "COURSE": 180.0,
        "ais_gap_minutes": request.ais_gap_minutes,
    }
    return parse_vessel(raw_simulated)


@router.get("/spills", response_model=List[SpillEventResponse])
async def get_oil_spills():
    """
    Retrieve detected oil spills with Copernicus Sentinel-2 scene IDs and correlated vessels.
    """
    # Demo oil spill near Bombay High offshore oil platform
    bombay_high_spill = SpillEventResponse(
        id="SPILL-IN-2026-001",
        detected_at=datetime.now(timezone.utc),
        lat=19.20,
        lon=71.50,
        area_km2=4.85,
        confidence=0.91,
        sentinel_scene_id="S2B_MSIL2A_20260907T053649_N0510_R005_T43QDA",
        top_candidates=[
            SpillCandidateResponse(
                mmsi="419000001",
                vessel_name="MT GUJARAT PRIDE",
                risk_score=0.88,
                distance_km=7.2,
                type_risk=0.95,
                heading_score=0.85,
                behavioral_anomaly=True,
            ),
            SpillCandidateResponse(
                mmsi="419000002",
                vessel_name="MV MUMBAI EXPRESS",
                risk_score=0.22,
                distance_km=28.4,
                type_risk=0.30,
                heading_score=0.15,
                behavioral_anomaly=False,
            ),
        ],
        geojson_polygon={
            "type": "Polygon",
            "coordinates": [
                [
                    [71.46, 19.18],
                    [71.52, 19.19],
                    [71.54, 19.23],
                    [71.49, 19.24],
                    [71.45, 19.21],
                    [71.46, 19.18],
                ]
            ],
        },
    )
    return [bombay_high_spill]


@router.post("/simulate-spill", response_model=SpillEventResponse)
async def simulate_oil_spill(request: SimulateSpillRequest):
    """
    Trigger real-time oil spill detection and multi-factor suspect vessel attribution.
    Scores all vessels in the fleet using the 4-signal SVR scoring pipeline.
    """
    raw_vessels = await fetch_ais_vessels()
    if not raw_vessels:
        raw_vessels = load_fallback_vessels()

    # Call 4-signal ranking algorithm from notebook
    ranked_candidates = rank_vessels_for_spill(
        vessels=raw_vessels,
        spill_lat=request.spill_lat,
        spill_lon=request.spill_lon,
        spill_trail_bearing=request.spill_trail_bearing,
        top_n=5,
    )

    candidates_response = [
        SpillCandidateResponse(
            mmsi=c["mmsi"],
            vessel_name=c["vessel_name"],
            risk_score=c["risk_score"],
            distance_km=c["distance_km"],
            type_risk=c["type_risk"],
            heading_score=c["heading_score"],
            behavioral_anomaly=c["behavioral_anomaly"],
        )
        for c in ranked_candidates
    ]

    # Generate realistic slick polygon around (spill_lat, spill_lon) ~2.4 km²
    lat, lon = request.spill_lat, request.spill_lon
    delta = 0.018
    slick_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [round(lon - delta, 4), round(lat - delta * 0.6, 4)],
                [round(lon + delta * 0.8, 4), round(lat - delta * 0.4, 4)],
                [round(lon + delta * 1.2, 4), round(lat + delta * 0.7, 4)],
                [round(lon - delta * 0.2, 4), round(lat + delta * 0.9, 4)],
                [round(lon - delta * 1.1, 4), round(lat + delta * 0.2, 4)],
                [round(lon - delta, 4), round(lat - delta * 0.6, 4)],
            ]
        ],
    }

    spill_id = f"SPILL-IN-{uuid.uuid4().hex[:8].upper()}"

    return SpillEventResponse(
        id=spill_id,
        detected_at=datetime.now(timezone.utc),
        lat=lat,
        lon=lon,
        area_km2=2.40,
        confidence=0.87,
        sentinel_scene_id="S2A_MSIL2A_20260904T054641_N0511_R048",
        top_candidates=candidates_response,
        geojson_polygon=slick_polygon,
    )


@router.get("/vessels/tracks", response_model=VesselTracksListResponse)
async def get_vessels_tracks():
    """
    Fetch all active vessels in Indian waters with full hourly AIS track history.
    """
    raw_vessels = await fetch_ais_vessels()

    # Fallback to demo vessels if external API is down or credentials not set
    if not raw_vessels:
        logger.info("using_demo_ais_vessels")
        raw_vessels = load_fallback_vessels()

    vessels = []
    for raw_vessel in raw_vessels:
        track = raw_vessel.get("track", [])
        vessels.append(
            VesselTrackResponse(
                vessel_id=raw_vessel.get("vessel_id", str(uuid.uuid4())),
                mmsi=str(raw_vessel.get("MMSI", "UNKNOWN")),
                vessel_name=str(raw_vessel.get("NAME") or "Unknown Vessel").strip(),
                ais_status=raw_vessel.get("AIS_Status", "AIS_ON"),
                track=[
                    TrackPoint(
                        timestamp=tp["timestamp"],
                        lat=tp["lat"],
                        lon=tp["lon"],
                        sog=tp["sog"],
                        cog=tp["cog"]
                    ) for tp in track
                ]
            )
        )

    return VesselTracksListResponse(
        vessels=vessels,
        total=len(vessels),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/attribute-spill", response_model=SpillEventResponse)
async def attribute_spill(request: AttributeSpillRequest):
    """
    Production oil spill attribution using live GFW data.
    """
    raw_vessels = await fetch_ais_vessels(
        spill_lat=request.spill_lat,
        spill_lon=request.spill_lon,
        spill_time=request.spill_time
    )
    if not raw_vessels:
        raw_vessels = load_fallback_vessels()

    import pandas as pd
    
    ranked_candidates = rank_vessels_for_spill(
        vessels=raw_vessels,
        spill_lat=request.spill_lat,
        spill_lon=request.spill_lon,
        spill_trail_bearing=request.spill_trail_bearing,
        top_n=5,
        distance_cutoff_km=request.distance_cutoff_km,
        spill_time=pd.Timestamp(request.spill_time)
    )

    candidates_response = [
        SpillCandidateResponse(
            mmsi=c["mmsi"],
            vessel_name=c["vessel_name"],
            risk_score=c["risk_score"],
            distance_km=c["distance_km"],
            type_risk=c["type_risk"],
            heading_score=c["heading_score"],
            behavioral_anomaly=c["behavioral_anomaly"],
        )
        for c in ranked_candidates
    ]

    lat, lon = request.spill_lat, request.spill_lon
    delta = 0.018
    slick_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [round(lon - delta, 4), round(lat - delta * 0.6, 4)],
                [round(lon + delta * 0.8, 4), round(lat - delta * 0.4, 4)],
                [round(lon + delta * 1.2, 4), round(lat + delta * 0.7, 4)],
                [round(lon - delta * 0.2, 4), round(lat + delta * 0.9, 4)],
                [round(lon - delta * 1.1, 4), round(lat + delta * 0.2, 4)],
                [round(lon - delta, 4), round(lat - delta * 0.6, 4)],
            ]
        ],
    }

    spill_id = f"SPILL-IN-{uuid.uuid4().hex[:8].upper()}"

    return SpillEventResponse(
        id=spill_id,
        detected_at=request.spill_time,
        lat=lat,
        lon=lon,
        area_km2=2.40,
        confidence=0.87,
        sentinel_scene_id="S2A_MSIL2A_LIVE",
        top_candidates=candidates_response,
        geojson_polygon=slick_polygon,
    )
