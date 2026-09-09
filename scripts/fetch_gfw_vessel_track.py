"""
SATVIGIL — GFW Vessel Track Fetcher
Script by Akshar (team member)

Fetches real AIS vessel presence data from Global Fishing Watch (GFW) API
for the Gulf of Kutch bounding box, July 2026.

Usage:
    python scripts/fetch_gfw_vessel_track.py

Output:
    gfw_presence_raw_july_2026.json       — full raw API response
    selected_vessel_track_july_2026.csv   — selected vessel track (CSV)
    selected_vessel_track_july_2026.json  — selected vessel track (JSON)

Note: Copy the output JSON to data/demo/gfw_vessel_track_july_2026.json
      for the backend track endpoint to serve it.
"""
import json
import os
import sys
from pathlib import Path
from collections import Counter

import pandas as pd
import requests


# ============================================================
# CONFIG
# ============================================================
API_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImtpZEtleSJ9.eyJkYXRhIjp7Im5hbWUiOiJTQVRWSUdJTCIsInVzZXJJZCI6Njk5MjgsImFwcGxpY2F0aW9uTmFtZSI6IlNBVFZJR0lMIiwiaWQiOjE0MDI1LCJ0eXBlIjoidXNlci1hcHBsaWNhdGlvbiJ9LCJpYXQiOjE3ODg0NzA1NjYsImV4cCI6MjEwMzgzMDU2NiwiYXVkIjoiZ2Z3IiwiaXNzIjoiZ2Z3In0.mGtBnTjmesVPp73HIIf-3f9x6wOTIfmdUUlouuAJyTACOvmaTJtO0RR_g0QMNAbvkEtkE2AvS7veOESpYCq2ky0bm8KQQ9TvKy2JikL6lhBwCXwjLMNH4Sz8eAU7TCbAO15PqU3xHNqJtVyeashiTKL8oSj6uNKMQ_yHMbV624nao8npc_i4nZUFhdwL3mudEV-xXndgGUN42_M-XXJ84esc28KYN_3T2rg7a1oDuM1VtQC67ihb8OaI6_BgZEfW4_oYbz8znLHrMTl1KlE7Hsa4E5sXLZ6Qz3sVWHUJDncThnB8xUY1IlmZZcvprDddXcbVtlfXgciIE7qT_pOoSqlgQKil2cS_tvnjZwjTdzRPQaz5XnJkMuchn5ujIGD-EJb4a_dEakUebwpoPHud_PCxv54DDV2xp2DY4PBlatEoB12yhrrASp2-A2Swg4aRmwIsIwvYCa3_YGxuwo-DRnLMpDAgHZIHuHox6kDJKme9XNbKDexBkzAZOtSDOFIq"

if not API_TOKEN:
    API_TOKEN = input("Paste your GFW API token: ").strip()

if not API_TOKEN:
    print("ERROR: API token is required.")
    sys.exit(1)

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"
START_DATE = "2026-07-01"
END_DATE = "2026-08-01"
DATASET = "public-global-presence:latest"

GULF_OF_KUTCH = {
    "type": "Polygon",
    "coordinates": [[
        [68.5, 22.0],
        [70.8, 22.0],
        [70.8, 23.1],
        [68.5, 23.1],
        [68.5, 22.0]
    ]]
}

RAW_FILE = "gfw_presence_raw_july_2026.json"
TRACK_CSV = "selected_vessel_track_july_2026.csv"
TRACK_JSON = "selected_vessel_track_july_2026.json"

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def check_response(response, name):
    if response.ok:
        return True
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)
    print("HTTP STATUS:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)
    print("=" * 60)
    return False


def get_presence_data():
    print("\n" + "=" * 60)
    print("REQUESTING GFW AIS PRESENCE")
    print("=" * 60)
    print("Dataset :", DATASET)
    print("Period  :", START_DATE, "to", END_DATE)
    print("Region  : Gulf of Kutch")

    url = f"{BASE_URL}/4wings/report"
    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "HOURLY",
        "group-by": "VESSEL_ID",
        "datasets[0]": DATASET,
        "date-range": f"{START_DATE},{END_DATE}",
        "format": "JSON",
        "spatial-aggregation": "false",
    }
    body = {"geojson": GULF_OF_KUTCH}

    response = session.post(url, params=params, json=body, timeout=300)
    if not check_response(response, "GFW PRESENCE REQUEST FAILED"):
        return None

    data = response.json()
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("\nRaw response saved:", Path(RAW_FILE).resolve())
    return data


def extract_rows(report):
    if not report:
        return []
    entries = report.get("entries", [])
    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            if not isinstance(value, list):
                continue
            for row in value:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def normalize_rows(rows):
    clean = []
    for row in rows:
        vessel_id = row.get("vesselId") or row.get("vessel_id")
        lat = row.get("lat")
        lon = row.get("lon")
        if vessel_id is None or lat is None or lon is None:
            continue
        clean.append({
            "date": row.get("date"),
            "vessel_id": vessel_id,
            "mmsi": row.get("mmsi"),
            "ship_name": row.get("shipName"),
            "flag": row.get("flag"),
            "vessel_type": row.get("vesselType"),
            "latitude": lat,
            "longitude": lon,
            "presence_hours": row.get("hours"),
        })
    return clean


def select_vessel(rows):
    print("\n" + "=" * 60)
    print("FINDING MOST OBSERVED VESSEL IN GULF OF KUTCH")
    print("=" * 60)
    if not rows:
        return None, []
    vessel_counter = Counter(r["vessel_id"] for r in rows)
    print("Unique vessels found:", len(vessel_counter))
    print("\nTop vessels by number of observations:")
    for vessel_id, count in vessel_counter.most_common(10):
        first = next(r for r in rows if r["vessel_id"] == vessel_id)
        print(f"\n  Vessel ID : {vessel_id}")
        print(f"  MMSI      : {first['mmsi']}")
        print(f"  Name      : {first['ship_name']}")
        print(f"  Flag      : {first['flag']}")
        print(f"  Observ.   : {count}")

    selected_vessel_id = vessel_counter.most_common(1)[0][0]
    selected_rows = [r for r in rows if r["vessel_id"] == selected_vessel_id]
    first = selected_rows[0]
    print("\n" + "=" * 60)
    print("SELECTED VESSEL:", first["ship_name"], "(", selected_vessel_id, ")")
    print("=" * 60)
    return selected_vessel_id, selected_rows


def create_dataframe(selected_rows):
    if not selected_rows:
        return pd.DataFrame()
    df = pd.DataFrame(selected_rows)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["presence_hours"] = pd.to_numeric(df["presence_hours"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    if "date" in df.columns:
        df = df.sort_values("date")
    df = df.drop_duplicates(subset=["date", "latitude", "longitude"])
    return df.reset_index(drop=True)


def save_track(df):
    if df.empty:
        return
    df.to_csv(TRACK_CSV, index=False, encoding="utf-8")
    records = df.to_dict(orient="records")
    with open(TRACK_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False, default=str)

    # Also save to demo folder for backend to serve
    demo_path = Path(__file__).parent.parent / "data" / "demo" / "gfw_vessel_track_july_2026.json"
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    with open(demo_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False, default=str)

    print("\n" + "=" * 60)
    print("FILES CREATED")
    print("=" * 60)
    print("CSV :", Path(TRACK_CSV).resolve())
    print("JSON:", Path(TRACK_JSON).resolve())
    print("Demo:", demo_path.resolve())


def main():
    print("\n" + "=" * 60)
    print("GFW VESSEL TRACK - GULF OF KUTCH JULY 2026")
    print("=" * 60)

    report = get_presence_data()
    if report is None:
        return

    raw_rows = extract_rows(report)
    print("\nRaw records:", len(raw_rows))

    rows = normalize_rows(raw_rows)
    print("Usable records:", len(rows))

    if not rows:
        print("\nNo usable AIS presence records.")
        return

    vessel_id, selected_rows = select_vessel(rows)
    if not selected_rows:
        print("\nCould not identify a vessel.")
        return

    df = create_dataframe(selected_rows)

    print("\n" + "=" * 60)
    print("TRACK PREVIEW (first 20 rows)")
    print("=" * 60)
    cols = [c for c in ["date", "latitude", "longitude", "presence_hours", "mmsi", "ship_name", "flag"] if c in df.columns]
    print(df[cols].head(20).to_string(index=False))

    print("\n" + "=" * 60)
    print("TRACK SUMMARY")
    print("=" * 60)
    print("Observations :", len(df))
    print("Lat range    :", df["latitude"].min(), "→", df["latitude"].max())
    print("Lon range    :", df["longitude"].min(), "→", df["longitude"].max())
    if "date" in df.columns:
        print("Start        :", df["date"].iloc[0])
        print("End          :", df["date"].iloc[-1])

    save_track(df)
    print("\n" + "=" * 60)
    print("DONE — Copy output JSON to data/demo/ for SATVIGIL backend")
    print("=" * 60)


if __name__ == "__main__":
    main()
