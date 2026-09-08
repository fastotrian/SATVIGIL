"""
SATVIGIL — AIS Vessel Feed Simulator
Generates realistic AIS telemetry scenarios in Indian waters for hackathon demos and testing.
Outputs: data/demo/ais_demo_scenario.json
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone


def generate_ais_demo_scenario(output_path: Path):
    """
    Generate the primary SIH 2026 maritime demo scenario:
    - Dark tanker MT GUJARAT PRIDE loitering near Bombay High offshore oil fields
    - FV KUTCH FISHERMAN loitering inside Gulf of Kutch Marine Protected Area
    - Legitimate commercial and passenger traffic across major Indian shipping lanes
    """
    now = datetime.now(timezone.utc).isoformat()

    vessels = [
        # Vessel 1 — The dark tanker (Primary Suspect near Bombay High)
        {
            "MMSI": "419000001",
            "NAME": "MT GUJARAT PRIDE",
            "TYPE": 80,
            "LATITUDE": 19.15,
            "LONGITUDE": 71.45,
            "SPEED": 2,           # 0.2 knots
            "COURSE": 210.0,
            "HEADING": 208.0,
            "ais_gap_minutes": 45, # Dark for 45 mins
            "TIME": now,
        },
        # Vessel 2 — Normal cargo ship in JNPT approach
        {
            "MMSI": "419000002",
            "NAME": "MV MUMBAI EXPRESS",
            "TYPE": 71,
            "LATITUDE": 18.95,
            "LONGITUDE": 72.85,
            "SPEED": 85,          # 8.5 knots
            "COURSE": 95.0,
            "HEADING": 96.0,
            "ais_gap_minutes": 0,
            "TIME": now,
        },
        # Vessel 3 — Fishing vessel suspicious inside Gulf of Kutch MNP
        {
            "MMSI": "419000003",
            "NAME": "FV KUTCH FISHERMAN",
            "TYPE": 30,
            "LATITUDE": 22.50,
            "LONGITUDE": 69.20,
            "SPEED": 5,           # 0.5 knots (loitering in MPA)
            "COURSE": 45.0,
            "HEADING": 42.0,
            "ais_gap_minutes": 20,
            "TIME": now,
        },
        # Vessel 4 — Normal passenger ferry near Lakshadweep
        {
            "MMSI": "419000004",
            "NAME": "MV LAKSHADWEEP QUEEN",
            "TYPE": 60,
            "LATITUDE": 10.50,
            "LONGITUDE": 72.80,
            "SPEED": 120,         # 12.0 knots
            "COURSE": 330.0,
            "HEADING": 332.0,
            "ais_gap_minutes": 0,
            "TIME": now,
        },
        # Vessel 5 — Tanker en route to Kandla Port
        {
            "MMSI": "419000005",
            "NAME": "MT CHENNAI SPIRIT",
            "TYPE": 82,
            "LATITUDE": 21.80,
            "LONGITUDE": 69.10,
            "SPEED": 105,         # 10.5 knots
            "COURSE": 25.0,
            "HEADING": 24.0,
            "ais_gap_minutes": 0,
            "TIME": now,
        },
        # Vessel 6 — Container carrier off Goa Coast
        {
            "MMSI": "419000006",
            "NAME": "MV KONKAN TRADER",
            "TYPE": 70,
            "LATITUDE": 15.40,
            "LONGITUDE": 73.60,
            "SPEED": 140,         # 14.0 knots
            "COURSE": 160.0,
            "HEADING": 158.0,
            "ais_gap_minutes": 0,
            "TIME": now,
        },
        # Vessel 7 — Bulk carrier approaching Paradip Port (Bay of Bengal)
        {
            "MMSI": "419000007",
            "NAME": "MV BENGAL GLORY",
            "TYPE": 72,
            "LATITUDE": 20.15,
            "LONGITUDE": 86.85,
            "SPEED": 60,          # 6.0 knots
            "COURSE": 310.0,
            "HEADING": 310.0,
            "ais_gap_minutes": 0,
            "TIME": now,
        },
        # Vessel 8 — Coastal patrol boat off Kochi
        {
            "MMSI": "419000008",
            "NAME": "ICGS VARUNA",
            "TYPE": 55,
            "LATITUDE": 9.90,
            "LONGITUDE": 76.15,
            "SPEED": 180,         # 18.0 knots
            "COURSE": 190.0,
            "HEADING": 192.0,
            "ais_gap_minutes": 0,
            "TIME": now,
        },
    ]

    # Ensure parent directories exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(vessels, f, indent=2)

    print(f" Successfully generated AIS scenario with {len(vessels)} vessels.")
    print(f" Output saved to: {output_path.resolve()}")
    print("\nKey Demo Vessels:")
    print(" 1. MT GUJARAT PRIDE (MMSI 419000001) -> Dark Tanker near Bombay High (CRITICAL)")
    print(" 2. FV KUTCH FISHERMAN (MMSI 419000003) -> Loitering inside Gulf of Kutch MPA (WARNING)")
    print(" 3. MV MUMBAI EXPRESS (MMSI 419000002) -> Legitimate JNPT traffic (NORMAL)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Indian waters AIS feed")
    repo_root = Path(__file__).resolve().parents[1]
    default_out = repo_root / "data" / "demo" / "ais_demo_scenario.json"
    parser.add_argument("--output", type=Path, default=default_out, help="Output JSON path")
    args = parser.parse_args()

    generate_ais_demo_scenario(args.output)
