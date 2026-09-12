"""
SATVIGIL — Maritime Module: Global Fishing Watch (GFW) AIS Fetcher
Fetches high-resolution hourly vessel tracks from the GFW API.
"""
import math
import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from app.core.config import settings

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"
DATASET = "public-global-presence:latest"

REGION_KUTCH = {
    "type": "Polygon",
    "coordinates": [[
        [68.5, 22.0],
        [70.8, 22.0],
        [70.8, 23.1],
        [68.5, 23.1],
        [68.5, 22.0]
    ]]
}


def get_region_polygon():
    if settings.GFW_AIS_REGION == "gulf_of_kutch":
        return REGION_KUTCH
    return REGION_KUTCH


async def get_presence_data(start_date: str, end_date: str) -> dict:
    url = f"{BASE_URL}/4wings/report"
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "HOURLY",
        "group-by": "VESSEL_ID",
        "datasets[0]": DATASET,
        "date-range": f"{start_date},{end_date}",
        "format": "JSON",
        "spatial-aggregation": "false"
    }

    headers = {
        "Authorization": f"Bearer {settings.GFW_API_TOKEN}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            url,
            params=params,
            json={"geojson": get_region_polygon()},
            headers=headers
        )
        response.raise_for_status()
        return response.json()


def extract_rows(report: dict) -> List[dict]:
    rows = []
    entries = report.get("entries", [])
    for entry in entries:
        if isinstance(entry, dict):
            for _, values in entry.items():
                if isinstance(values, list):
                    for row in values:
                        if isinstance(row, dict):
                            rows.append(row)
        elif isinstance(entry, list):
            for row in entry:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def normalize_presence(rows: List[dict]) -> pd.DataFrame:
    output = []
    for row in rows:
        vessel_id = (
            row.get("vesselId") or row.get("vessel_id") or row.get("vesselID") or row.get("id")
        )
        if vessel_id is None:
            vessel_ids = row.get("vesselIDs") or row.get("vesselIds") or row.get("vessel_ids")
            if isinstance(vessel_ids, list) and vessel_ids:
                vessel_id = vessel_ids[0]
            elif vessel_ids is not None:
                vessel_id = vessel_ids

        lat = row.get("lat") if row.get("lat") is not None else row.get("latitude")
        lon = row.get("lon") if row.get("lon") is not None else row.get("longitude")
        date = row.get("date")

        if vessel_id is None or lat is None or lon is None:
            continue

        output.append({
            "vessel_id": str(vessel_id),
            "date": date,
            "latitude": lat,
            "longitude": lon,
            "hours": row.get("hours")
        })

    df = pd.DataFrame(output)
    if df.empty:
        return df

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df = df.dropna(subset=["vessel_id", "latitude", "longitude", "date"])
    return df


def select_vessels(df: pd.DataFrame, max_n: int) -> List[str]:
    stats = (
        df.groupby("vessel_id")
        .agg(observations=("date", "count"))
        .sort_values("observations", ascending=False)
    )
    return stats.head(max_n).index.tolist()


async def get_vessel_identity(vessel_id: str) -> dict:
    url = f"{BASE_URL}/vessels/{vessel_id}"
    params = {"dataset": "public-global-vessel-identity:latest"}
    headers = {
        "Authorization": f"Bearer {settings.GFW_API_TOKEN}",
        "Accept": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.warning("gfw_identity_fetch_failed", vessel_id=vessel_id, error=str(e))
            return {"MMSI": "", "VesselName": "", "VesselType": "OTHER"}

    info = data.get("selfReportedInfo", [])
    if isinstance(info, list):
        info = info[0] if info else {}
    if not isinstance(info, dict):
        info = {}

    mmsi = info.get("ssvid") or info.get("mmsi") or ""
    name = info.get("shipname") or ""
    vessel_type = info.get("shiptype") or "OTHER"

    return {
        "MMSI": str(mmsi),
        "VesselName": name,
        "VesselType": vessel_type
    }


def normalize_vessel_type(vessel_type: str) -> str:
    if vessel_type is None:
        return "OTHER"
    value = str(vessel_type).upper()
    if "TANKER" in value: return "TANKER"
    if "CARGO" in value: return "CARGO"
    if "FISH" in value: return "FISHING"
    if "PASSENGER" in value: return "PASSENGER"
    if "CARRIER" in value: return "CARRIER"
    return "OTHER"


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lat2 = map(math.radians, [lat1, lat2])
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def build_track(vessel_df: pd.DataFrame, identity: dict) -> pd.DataFrame:
    vessel_df = vessel_df.sort_values("date").drop_duplicates(subset=["date"]).copy()
    if vessel_df.empty:
        return pd.DataFrame()

    vessel_df["MMSI"] = identity["MMSI"]
    vessel_df["VesselName"] = identity["VesselName"]
    vessel_df["VesselType"] = normalize_vessel_type(identity["VesselType"])
    vessel_df["vessel_id"] = vessel_df["vessel_id"].astype(str)
    vessel_df["AIS_Status"] = "AIS_ON"
    vessel_df["DataSource"] = "GFW_AIS"

    vessel_df = vessel_df.set_index("date")
    full_hours = pd.date_range(
        start=vessel_df.index.min().floor("h"),
        end=vessel_df.index.max().floor("h"),
        freq="1h",
        tz="UTC",
    )

    vessel_df = vessel_df.reindex(full_hours)
    vessel_df.index.name = "date"

    for col, value in {
        "MMSI": identity["MMSI"],
        "VesselName": identity["VesselName"],
        "VesselType": normalize_vessel_type(identity["VesselType"]),
        "vessel_id": str(vessel_df["vessel_id"].dropna().iloc[0]) if vessel_df["vessel_id"].notna().any() else "",
        "AIS_Status": "AIS_ON",
        "DataSource": "GFW_AIS",
    }.items():
        vessel_df[col] = vessel_df[col].ffill().bfill()
        vessel_df[col] = vessel_df[col].fillna(value)

    vessel_df["latitude"] = pd.to_numeric(vessel_df["latitude"], errors="coerce").interpolate(method="time", limit_area="inside")
    vessel_df["longitude"] = pd.to_numeric(vessel_df["longitude"], errors="coerce").interpolate(method="time", limit_area="inside")
    vessel_df = vessel_df.dropna(subset=["latitude", "longitude"]).reset_index()

    sog_values = [np.nan]
    cog_values = [np.nan]
    for i in range(1, len(vessel_df)):
        previous = vessel_df.iloc[i - 1]
        current = vessel_df.iloc[i]
        time_diff_hours = (current["date"] - previous["date"]).total_seconds() / 3600.0
        if time_diff_hours <= 0:
            sog_values.append(np.nan)
            cog_values.append(np.nan)
            continue
        distance_km = haversine_km(previous["latitude"], previous["longitude"], current["latitude"], current["longitude"])
        speed_knots = distance_km / time_diff_hours / 1.852
        bearing = calculate_bearing(previous["latitude"], previous["longitude"], current["latitude"], current["longitude"])
        sog_values.append(speed_knots)
        cog_values.append(bearing)

    vessel_df["SOG"] = sog_values
    vessel_df["COG"] = cog_values
    vessel_df = vessel_df.rename(columns={"date": "BaseDateTime", "latitude": "LAT", "longitude": "LON"})

    return vessel_df[["vessel_id", "MMSI", "BaseDateTime", "LAT", "LON", "SOG", "COG", "VesselType", "VesselName", "AIS_Status", "DataSource"]]


def _destination_point(lat, lon, distance_km, bearing_deg):
    R = 6371.0
    bearing = math.radians(bearing_deg)
    lat1, lon1 = map(math.radians, [lat, lon])
    angular_distance = distance_km / R

    lat2 = math.asin(math.sin(lat1) * math.cos(angular_distance) + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing))
    lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1), math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2))
    return math.degrees(lat2), math.degrees(lon2)


def build_virtual_ais_off_tracks(start_time: pd.Timestamp, end_time: pd.Timestamp, anchor_lat: float, anchor_lon: float, anchor_time: pd.Timestamp) -> pd.DataFrame:
    AIS_OFF_VIRTUAL_CONFIG = [
        {
            "vessel_id": "AIS_OFF_VIRTUAL_01",
            "MMSI": "999000001",
            "VesselName": "AIS-OFF-VIRTUAL-01",
            "VesselType": "TANKER",
            "lat_offset_km": 1.5,
            "lon_offset_km": 0.0,
            "speed_knots": 9.0,
            "heading_deg": 250.0,
        },
        {
            "vessel_id": "AIS_OFF_VIRTUAL_02",
            "MMSI": "999000002",
            "VesselName": "AIS-OFF-VIRTUAL-02",
            "VesselType": "CARGO",
            "lat_offset_km": 10.0,
            "lon_offset_km": 5.0,
            "speed_knots": 7.0,
            "heading_deg": 70.0,
        },
    ]

    times = pd.date_range(start=start_time.floor("h"), end=end_time.ceil("h"), freq="1h", tz="UTC")
    rows = []

    for cfg in AIS_OFF_VIRTUAL_CONFIG:
        start_lat, start_lon = _destination_point(
            anchor_lat, anchor_lon,
            math.hypot(cfg["lat_offset_km"], cfg["lon_offset_km"]),
            math.degrees(math.atan2(cfg["lon_offset_km"], cfg["lat_offset_km"])) if (cfg["lat_offset_km"] or cfg["lon_offset_km"]) else 0.0,
        )
        speed_kmh = cfg["speed_knots"] * 1.852
        heading = cfg["heading_deg"]

        for timestamp in times:
            hours_from_anchor = (timestamp - anchor_time).total_seconds() / 3600.0
            distance_from_anchor = speed_kmh * hours_from_anchor
            lat, lon = _destination_point(
                start_lat, start_lon,
                abs(distance_from_anchor),
                (heading + 180.0) % 360.0 if hours_from_anchor < 0 else heading,
            )

            rows.append({
                "vessel_id": cfg["vessel_id"],
                "MMSI": cfg["MMSI"],
                "BaseDateTime": timestamp,
                "LAT": lat,
                "LON": lon,
                "SOG": cfg["speed_knots"],
                "COG": heading,
                "VesselType": cfg["VesselType"],
                "VesselName": cfg["VesselName"],
                "AIS_Status": "AIS_OFF",
                "DataSource": "VIRTUAL",
            })

    return pd.DataFrame(rows)


def convert_vessel_type_to_code(vessel_type: str) -> int:
    if vessel_type == "TANKER": return 80
    if vessel_type == "CARGO": return 70
    if vessel_type == "FISHING": return 30
    if vessel_type == "PASSENGER": return 60
    return 0


async def fetch_gfw_vessels(spill_lat: Optional[float] = None, spill_lon: Optional[float] = None, spill_time: Optional[datetime] = None) -> List[Dict]:
    """
    Fetch vessels from GFW API and return in schema compatible with existing endpoints.
    Includes full tracks for attribution analysis.
    """
    if not settings.GFW_API_TOKEN:
        logger.warning("no_gfw_token_configured")
        return []

    now = datetime.now(timezone.utc)
    end_date_dt = now
    start_date_dt = now - timedelta(days=settings.GFW_AIS_LOOKBACK_DAYS)

    start_date = start_date_dt.strftime("%Y-%m-%d")
    end_date = end_date_dt.strftime("%Y-%m-%d")

    try:
        report = await get_presence_data(start_date, end_date)
        raw_rows = extract_rows(report)
        presence_df = normalize_presence(raw_rows)
        if presence_df.empty:
            return []

        vessel_ids = select_vessels(presence_df, settings.GFW_AIS_MAX_VESSELS)

        identities = await asyncio.gather(*[get_vessel_identity(vid) for vid in vessel_ids])
        
        tracks = []
        for vid, identity in zip(vessel_ids, identities):
            vessel_rows = presence_df[presence_df["vessel_id"] == vid]
            if not vessel_rows.empty:
                track_df = build_track(vessel_rows, identity)
                if not track_df.empty:
                    tracks.append(track_df)

        if not tracks:
            return []

        result_df = pd.concat(tracks, ignore_index=True)

        # Build virtual tracks if spill location provided, otherwise anchor to center of region
        if spill_lat is None or spill_lon is None:
            spill_lat, spill_lon = 22.5, 69.5
        if spill_time is None:
            spill_time = pd.Timestamp(now)
        else:
            spill_time = pd.Timestamp(spill_time)

        virtual_tracks = build_virtual_ais_off_tracks(pd.Timestamp(start_date_dt), pd.Timestamp(end_date_dt), spill_lat, spill_lon, spill_time)
        result_df = pd.concat([result_df, virtual_tracks], ignore_index=True)

        result_df = result_df.sort_values(["vessel_id", "BaseDateTime"]).reset_index(drop=True)

        # Convert back to list of dicts grouped by vessel_id
        final_vessels = []
        for vessel_id, group in result_df.groupby("vessel_id"):
            last_row = group.iloc[-1]
            
            # Format to match existing AISHub format
            track_points = []
            for _, r in group.iterrows():
                track_points.append({
                    "timestamp": r["BaseDateTime"],
                    "lat": r["LAT"],
                    "lon": r["LON"],
                    "sog": r["SOG"] if not pd.isna(r["SOG"]) else 0.0,
                    "cog": r["COG"] if not pd.isna(r["COG"]) else 0.0,
                })

            vessel_dict = {
                "MMSI": last_row["MMSI"],
                "NAME": last_row["VesselName"],
                "TYPE": convert_vessel_type_to_code(last_row["VesselType"]),
                "LATITUDE": last_row["LAT"],
                "LONGITUDE": last_row["LON"],
                "SPEED": float(last_row["SOG"] if not pd.isna(last_row["SOG"]) else 0.0),
                "COURSE": float(last_row["COG"] if not pd.isna(last_row["COG"]) else 0.0),
                "ais_gap_minutes": 60 if last_row["AIS_Status"] == "AIS_OFF" else 0, # simulated gap
                "vessel_id": vessel_id,
                "AIS_Status": last_row["AIS_Status"],
                "DataSource": last_row["DataSource"],
                "track": track_points
            }
            final_vessels.append(vessel_dict)

        return final_vessels

    except Exception as e:
        logger.error("gfw_fetch_failed", error=str(e))
        return []
