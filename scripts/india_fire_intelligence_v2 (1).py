"""
India Fire & Thermal Hotspot Intelligence — V2
Standalone Python script converted from the final notebook.

Outputs:
- india_fires_raw.csv
- india_fires_classified_v2.csv
- recurring_hotspots_v2.csv
- cpcb_recurring_pollution_hotspots_v2.csv
"""

import sys, subprocess, importlib.util

packages = {
    "requests": "requests",
    "pandas": "pandas",
    "numpy": "numpy",
    "geopandas": "geopandas",
    "shapely": "shapely",
    "sklearn": "scikit-learn",
    "matplotlib": "matplotlib",
}

missing = [pip_name for module, pip_name in packages.items()
           if importlib.util.find_spec(module) is None]

if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

import requests
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from sklearn.cluster import DBSCAN
from pathlib import Path
from io import StringIO
import math

print("Environment ready.")

MAP_KEY = "9ca74ae85bd8209a92c996e03d91fe05"
SENSOR = "VIIRS_SNPP_NRT"
FIRMS_DAYS = 5
CONFIDENCE_MIN = 50

DBSCAN_RADIUS_KM = 0.5
MIN_RECURRENCES = 3
MIN_SAMPLES = 3

INDIA_BBOX = "68.1766451354,7.96553477623,97.4025614766,35.4940095078"

BOUNDARY_DIR = Path("boundaries")
BOUNDARY_DIR.mkdir(exist_ok=True)

INDIA_BOUNDARY_FILE = BOUNDARY_DIR / "india_boundary.geojson"
FOREST_FILE = BOUNDARY_DIR / "india_forest.geojson"
MINING_LEASE_FILE = BOUNDARY_DIR / "legal_mining_leases.geojson"

print("Configuration loaded.")

def get_firms(sensor=SENSOR, days=FIRMS_DAYS):
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{sensor}/{INDIA_BBOX}/{days}"
    )
    print(f"Requesting {sensor} for {days} day(s)...")
    r = requests.get(url, timeout=90)
    print("HTTP status:", r.status_code)
    if r.status_code != 200:
        raise RuntimeError(r.text[:1000])
    return pd.read_csv(StringIO(r.text))

df = get_firms()
df.to_csv("india_fires_raw.csv", index=False)
print(f"Retrieved {len(df):,} raw detections.")
print("Saved: india_fires_raw.csv")

INDIA_BOUNDARY_FILE = Path("boundaries/india_boundary.geojson")

def load_india_boundary():
    if INDIA_BOUNDARY_FILE.exists():
        return gpd.read_file(INDIA_BOUNDARY_FILE).to_crs("EPSG:4326")

    url = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"

    print("Downloading India boundary...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()

    INDIA_BOUNDARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDIA_BOUNDARY_FILE.write_bytes(r.content)

    print("India boundary downloaded.")
    return gpd.read_file(INDIA_BOUNDARY_FILE).to_crs("EPSG:4326")


india_boundary = load_india_boundary()
india_shape = india_boundary.geometry.union_all()

points = gpd.GeoDataFrame(
    df.copy(),
    geometry=[Point(lon, lat) for lon, lat in zip(df.longitude, df.latitude)],
    crs="EPSG:4326"
)

before = len(points)
points = points[points.geometry.within(india_shape)].copy()
after = len(points)

df = pd.DataFrame(points.drop(columns="geometry"))

print(f"Before India filter: {before:,}")
print(f"After India filter:  {after:,}")
print(f"Removed outside India: {before-after:,}")

df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df["frp"] = pd.to_numeric(df.get("frp", np.nan), errors="coerce")

def confidence_score(x):
    if pd.isna(x): return np.nan
    s = str(x).strip().lower()
    if s in {"high","h"}: return 90.0
    if s in {"nominal","n","medium","m"}: return 70.0
    if s in {"low","l"}: return 30.0
    try: return float(x)
    except: return np.nan

df["confidence_score"] = df["confidence"].apply(confidence_score)
df = df.dropna(subset=["latitude","longitude"]).copy()
df = df[df["confidence_score"].fillna(0) >= CONFIDENCE_MIN].copy()

df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")

if "acq_time" in df.columns:
    t = (
        df["acq_time"].astype(str)
        .str.extract(r"(\d{3,6})", expand=False)
        .fillna("0").str.zfill(6)
    )
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"].dt.strftime("%Y-%m-%d") + " " +
        t.str[:2] + ":" + t.str[2:4] + ":" + t.str[4:6],
        errors="coerce"
    )
else:
    df["acq_datetime"] = df["acq_date"]

print(f"Detections after confidence filter: {len(df):,}")

FOREST_FILE = Path("boundaries/Bharatmaps_RFA.geojsonl")

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


# ============================================================
# LOAD FOREST + MINING GIS DATA
# ============================================================

# Bharatmaps RFA forest polygons
if FOREST_FILE.exists():
    try:
        print("Loading Bharatmaps RFA forest polygons...")
        
        forest_gdf = gpd.read_file(
            FOREST_FILE,
            driver="GeoJSONSeq"
        ).to_crs("EPSG:4326")
        
        print(f"Loaded Bharatmaps forest polygons: {len(forest_gdf):,}")
        
    except Exception as e:
        print(f"WARNING: Could not read Bharatmaps forest file: {e}")
        forest_gdf = None
else:
    forest_gdf = None


# Optional legal mining lease polygons
if MINING_LEASE_FILE.exists():
    try:
        mining_lease_gdf = (
            gpd.read_file(MINING_LEASE_FILE)
            .to_crs("EPSG:4326")
        )
        print(f"Loaded legal mining leases: {len(mining_lease_gdf):,}")
    except Exception as e:
        print(f"WARNING: Could not read mining lease file: {e}")
        mining_lease_gdf = None
else:
    mining_lease_gdf = None


print()

print(
    "Forest polygons:",
    "YES — Bharatmaps RFA"
    if forest_gdf is not None
    else "NO — fallback zones"
)

print(
    "Legal mining leases:",
    "YES"
    if mining_lease_gdf is not None
    else "NO — legality unverified"
)

def run_dbscan(data, radius_km=DBSCAN_RADIUS_KM, min_samples=MIN_SAMPLES):
    coords = np.radians(data[["latitude","longitude"]].to_numpy())
    eps = radius_km / 6371.0088
    labels = DBSCAN(
        eps=eps, min_samples=min_samples, metric="haversine"
    ).fit_predict(coords)
    out = data.copy()
    out["recurrence_cluster_id"] = labels
    out["is_recurring_hotspot"] = labels >= 0
    return out

df = run_dbscan(df)

cluster_counts = (
    df[df.is_recurring_hotspot]
    .groupby("recurrence_cluster_id")
    .size()
)

print("Recurring DBSCAN clusters:", len(cluster_counts))
print("Detections in recurring clusters:", int(cluster_counts.sum()) if len(cluster_counts) else 0)

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

def crop_hit(lat,lon):
    for z in CROP_ZONES:
        if bbox_hit(lat,lon,z):
            return True,z[4]
    return False,None

def mining_hit(lat,lon):
    for z in MINING_ZONES:
        if bbox_hit(lat,lon,z):
            return True,z[4]
    return False,None

def forest_hit(lat,lon):
    if forest_gdf is not None:
        p = Point(lon,lat)
        if bool(forest_gdf.geometry.contains(p).any()):
            return True,"authoritative_forest_polygon"
        return False,None
    for z in FOREST_ZONES:
        if bbox_hit(lat,lon,z):
            return True,"fallback_forest_bbox"
    return False,None

def classify(row):
    lat,lon = float(row.latitude),float(row.longitude)
    frp = float(row.frp) if pd.notna(row.frp) else 0.0
    recurring = bool(row.is_recurring_hotspot)

    scores = {
        "stubble_burn":0.0,
        "forest_burn":0.0,
        "industrial_fire":0.0,
        "gas_flare":0.0,
        "mining_thermal":0.0
    }
    reasons = {k:[] for k in scores}

    # Stubble
    crop, crop_name = crop_hit(lat,lon)
    seasonal = pd.notna(row.acq_date) and row.acq_date.month in {4,5,10,11}
    if crop:
        scores["stubble_burn"] += 60
        reasons["stubble_burn"].append(f"crop-region:{crop_name}")
    if seasonal:
        scores["stubble_burn"] += 25
        reasons["stubble_burn"].append("seasonal-window")

    # Forest
    forest, forest_reason = forest_hit(lat,lon)
    if forest:
        add = 75 if forest_reason == "authoritative_forest_polygon" else 45
        scores["forest_burn"] += add
        reasons["forest_burn"].append(forest_reason)

    # Industrial
    ind_d, ind_name = nearest_zone(lat,lon,INDUSTRIAL_ZONES)
    if ind_name:
        scores["industrial_fire"] += 60
        reasons["industrial_fire"].append(f"industrial-proximity:{ind_name}")
    if frp >= 50:
        scores["industrial_fire"] += 25
        reasons["industrial_fire"].append("high-FRP")
    elif frp >= 20:
        scores["industrial_fire"] += 10
        reasons["industrial_fire"].append("elevated-FRP")

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
    mining, mining_name = mining_hit(lat,lon)
    if mining:
        scores["mining_thermal"] += 65
        reasons["mining_thermal"].append(f"mining-belt:{mining_name}")
    if recurring:
        scores["mining_thermal"] += 25
        reasons["mining_thermal"].append("recurring-spatial-cluster")

    best = max(scores,key=scores.get)
    best_score = scores[best]

    if best_score < 60:
        final_type = "unclassified"
        reason = "insufficient-contextual-evidence"
    else:
        final_type = best
        reason = "; ".join(reasons[best]) or "contextual-score"

    return pd.Series({
        "fire_type":final_type,
        "classification_score":round(best_score,1),
        "classification_confidence":round(min(best_score,99),1),
        "classification_reason":reason,
        "stubble_score":scores["stubble_burn"],
        "forest_score":scores["forest_burn"],
        "industrial_score":scores["industrial_fire"],
        "gas_flare_score":scores["gas_flare"],
        "mining_score":scores["mining_thermal"]
    })

df = pd.concat([df.reset_index(drop=True),
                df.apply(classify,axis=1).reset_index(drop=True)],axis=1)

print("=== CLASSIFICATION SUMMARY ===")
print(df.fire_type.value_counts())

if mining_lease_gdf is not None:
    lease_union = mining_lease_gdf.geometry.union_all()
    df["inside_legal_mining_lease"] = [
        bool(lease_union.contains(Point(lon,lat)))
        for lat,lon in zip(df.latitude,df.longitude)
    ]

    mask = (
        (df.fire_type == "mining_thermal") &
        (~df.inside_legal_mining_lease)
    )
    df.loc[mask,"fire_type"] = "mining_thermal_suspected_unauthorized"
    print("Mining lease legality check applied.")
else:
    df["inside_legal_mining_lease"] = pd.NA
    print("No legal mining lease supplied — legality remains unverified.")

def mode_value(s):
    m = s.mode()
    return m.iloc[0] if not m.empty else "unclassified"

recurring = (
    df[df.is_recurring_hotspot]
    .groupby("recurrence_cluster_id")
    .agg(
        detection_count=("fire_type","size"),
        center_lat=("latitude","mean"),
        center_lon=("longitude","mean"),
        dominant_fire_type=("fire_type",mode_value),
        first_seen=("acq_datetime","min"),
        last_seen=("acq_datetime","max"),
        avg_frp=("frp","mean"),
        max_frp=("frp","max"),
        avg_confidence=("confidence_score","mean")
    )
    .reset_index()
)

recurring = recurring[recurring.detection_count >= MIN_RECURRENCES]
recurring = recurring.sort_values("detection_count",ascending=False)

recurring.to_csv("recurring_hotspots_v2.csv",index=False)

print(f"Saved {len(recurring):,} recurring hotspots.")
print(recurring.head(20).to_string(index=False))

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

def find_cpa(lat,lon):
    hits=[]
    for zlat,zlon,radius,name in CPA_ZONES:
        d=dist_km(lat,lon,zlat,zlon)
        if d<=radius:
            hits.append((d,name))
    return min(hits)[1] if hits else None

df["cpcb_cpa_name"]=[
    find_cpa(lat,lon) for lat,lon in zip(df.latitude,df.longitude)
]

cpa_recurring = (
    df[df.is_recurring_hotspot & df.cpcb_cpa_name.notna()]
    .groupby(["cpcb_cpa_name","recurrence_cluster_id"])
    .agg(
        detection_count=("fire_type","size"),
        center_lat=("latitude","mean"),
        center_lon=("longitude","mean"),
        dominant_fire_type=("fire_type",mode_value),
        first_seen=("acq_datetime","min"),
        last_seen=("acq_datetime","max"),
        avg_frp=("frp","mean"),
        max_frp=("frp","max"),
        avg_confidence=("confidence_score","mean")
    )
    .reset_index()
)

cpa_recurring = cpa_recurring[cpa_recurring.detection_count >= MIN_RECURRENCES]
cpa_recurring.to_csv("cpcb_recurring_pollution_hotspots_v2.csv",index=False)

print("CPA-associated detections:", int(df.cpcb_cpa_name.notna().sum()))
print("Recurring CPA hotspots:", len(cpa_recurring))
print(cpa_recurring.to_string(index=False))

df.to_csv("india_fires_classified_v2.csv",index=False)

print("======================================")
print(" INDIA FIRE INTELLIGENCE V2 COMPLETE ")
print("======================================")
print("Final India detections:",len(df))
print("Recurring clusters:",df.loc[df.is_recurring_hotspot,"recurrence_cluster_id"].nunique())
print("CPA detections:",int(df.cpcb_cpa_name.notna().sum()))
print("\nClassification:")
print(df.fire_type.value_counts())
print("\nFiles:")
print("india_fires_raw.csv")
print("india_fires_classified_v2.csv")
print("recurring_hotspots_v2.csv")
print("cpcb_recurring_pollution_hotspots_v2.csv")
