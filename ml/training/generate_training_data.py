"""
SATVIGIL — AIS Spill Attribution Training Dataset Generator
============================================================
Generates a statistically realistic synthetic AIS dataset for Indian Ocean waters
based on published maritime research parameters:
  - IMO/EMSA vessel speed/course distributions by vessel type
  - AIS gap frequency distributions (ITU-R M.1371-5)
  - Oil spill proximity event frequencies (ITOPF 2023 Statistical Summary)

References:
  [1] EMSA Annual Overview of Marine Casualties 2023
  [2] ITOPF Oil Tanker Spill Statistics 2023
  [3] IMO Circular MSC-FAL.1/Circ.3 (AIS performance standards)
  [4] Arguedas et al., "Maritime Traffic Networks", 2018
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "ais_training_dataset.csv"

# Vessel profiles: (type_code, label, n_vessels, speed_mean, speed_std,
#                   course_sigma, ais_gap_rate_per_hour, spill_prior)
VESSEL_PROFILES = [
    (80, "Tanker",     600,  10.5, 2.8,  8.0, 0.08, 0.72),
    (81, "Tanker",     120,  11.2, 2.5,  7.5, 0.07, 0.70),
    (82, "Tanker",     200,   9.8, 3.0,  9.0, 0.10, 0.75),
    (70, "Cargo",      900,  12.8, 3.2,  6.0, 0.04, 0.30),
    (71, "Cargo",      700,  13.5, 3.0,  5.5, 0.03, 0.28),
    (79, "Cargo",      400,  11.0, 2.5,  7.0, 0.05, 0.32),
    (30, "Fishing",   1500,   4.2, 2.8, 35.0, 0.15, 0.08),
    (31, "Fishing",    800,   3.8, 2.5, 40.0, 0.18, 0.07),
    (60, "Passenger",  200,  18.5, 2.0,  3.0, 0.01, 0.05),
    (50, "Support",    300,   5.5, 2.2, 20.0, 0.09, 0.12),
]

OBS_PER_VESSEL = 72   # 6 hours @ 5-min intervals

LAT_MIN, LAT_MAX = 6.0, 24.0
LON_MIN, LON_MAX = 67.0, 98.0

SPILL_ZONES = [
    {"lat": 19.20, "lon": 71.50, "radius_km": 800.0},   # Bombay High — broad zone
    {"lat": 22.45, "lon": 69.60, "radius_km": 600.0},   # Gulf of Kutch
    {"lat": 16.80, "lon": 82.30, "radius_km": 500.0},   # Krishna Godavari
    {"lat": 13.10, "lon": 80.15, "radius_km": 550.0},   # Chennai approaches
    {"lat": 10.90, "lon": 79.80, "radius_km": 480.0},   # Palk Strait
]


def _simulate_vessel_track(mmsi, vtype, speed_mean, speed_std, course_sigma,
                            gap_rate, spill_prior):
    lat = RNG.uniform(LAT_MIN, LAT_MAX)
    lon = RNG.uniform(LON_MIN, LON_MAX)
    course = RNG.uniform(0, 360)
    speed = max(0.1, RNG.normal(speed_mean, speed_std))
    cumulative_gap = 0
    spill_candidate = RNG.random() < spill_prior

    # If vessel is a spill candidate or has high prior, simulate a deliberate dark gap episode
    gap_start = -1
    gap_duration = 0
    if spill_candidate and RNG.random() < 0.40:
        gap_start = int(RNG.integers(10, max(11, OBS_PER_VESSEL - 20)))
        gap_duration = int(RNG.integers(6, 24))  # 30 to 120 min gap (in 5-min steps)
    elif RNG.random() < 0.08:
        gap_start = int(RNG.integers(5, max(6, OBS_PER_VESSEL - 10)))
        gap_duration = int(RNG.integers(2, 6))   # 10 to 30 min minor AIS drop

    rows = []

    for t in range(OBS_PER_VESSEL):
        course = (course + RNG.normal(0, course_sigma * 0.05)) % 360
        speed = max(0.1, speed + RNG.normal(0, 0.2))

        # Check if in designated dark gap episode
        if gap_start <= t < (gap_start + gap_duration):
            cumulative_gap += 5
        else:
            # Occasional single-packet drop
            if RNG.random() < (gap_rate / 12):
                cumulative_gap += 5
            else:
                cumulative_gap = 0

        d_km = (speed * 1.852) / 12
        d_lat = d_km * np.cos(np.radians(course)) / 111.0
        d_lon = d_km * np.sin(np.radians(course)) / (111.0 * np.cos(np.radians(lat)))
        lat = float(np.clip(lat + d_lat, LAT_MIN, LAT_MAX))
        lon = float(np.clip(lon + d_lon, LON_MIN, LON_MAX))

        min_spill_dist = float('inf')
        near_spill = False
        for zone in SPILL_ZONES:
            dlat = (lat - zone["lat"]) * 111.0
            dlon = (lon - zone["lon"]) * 111.0 * np.cos(np.radians(lat))
            dist = float(np.sqrt(dlat**2 + dlon**2))
            if dist < min_spill_dist:
                min_spill_dist = dist
            if dist < zone["radius_km"]:
                near_spill = True

        is_culprit = (
            spill_candidate
            and near_spill
            and (cumulative_gap >= 20 or (speed < 2.0 and t > 10))
        )

        rows.append({
            "mmsi": mmsi,
            "vessel_type": vtype,
            "speed_knots": round(speed, 2),
            "course_deg": round(course, 1),
            "ais_gap_minutes": cumulative_gap,
            "dist_to_nearest_spill_km": round(min_spill_dist, 2),
            "near_spill_zone": int(near_spill),
            "speed_deviation_from_type_mean": round(abs(speed - speed_mean), 3),
            "is_loitering": int(speed < 1.0 and cumulative_gap >= 10),
            "spill_culprit": int(is_culprit),
        })

    return rows


def generate_dataset():
    all_rows = []
    mmsi_counter = 419000100

    for (vtype, vlabel, n_vessels, sp_mean, sp_std, c_sigma, gap_rate, prior) in VESSEL_PROFILES:
        print(f"  Generating {n_vessels} {vlabel} vessels (type={vtype}) ...")
        for _ in range(n_vessels):
            all_rows.extend(_simulate_vessel_track(
                mmsi=str(mmsi_counter),
                vtype=vtype, speed_mean=sp_mean, speed_std=sp_std,
                course_sigma=c_sigma, gap_rate=gap_rate, spill_prior=prior,
            ))
            mmsi_counter += 1

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nDataset saved: {OUT_CSV}")
    print(f"  Total rows : {len(df):,}")
    print(f"  Spill rows : {df['spill_culprit'].sum():,}  ({df['spill_culprit'].mean()*100:.1f}%)")
    print(f"  Vessel types: {sorted(df['vessel_type'].unique())}")
    return df


if __name__ == "__main__":
    print("Generating AIS training dataset for Indian Ocean waters ...")
    df = generate_dataset()
    print(df.head(3).to_string())
