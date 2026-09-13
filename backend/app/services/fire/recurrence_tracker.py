import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import structlog
from app.core.config import settings

logger = structlog.get_logger()

# Defaults
DBSCAN_RADIUS_KM = 0.5
MIN_SAMPLES = 3
MIN_RECURRENCES = 3

def run_dbscan_recurrence(df: pd.DataFrame, radius_km=DBSCAN_RADIUS_KM, min_samples=MIN_SAMPLES) -> pd.DataFrame:
    """
    Applies DBSCAN clustering on lat/lon coordinates to find spatial recurrence clusters.
    Returns a DataFrame with 'recurrence_cluster_id' and 'is_recurring_hotspot'.
    """
    if df.empty:
        df["recurrence_cluster_id"] = -1
        df["is_recurring_hotspot"] = False
        return df

    coords = np.radians(df[["latitude", "longitude"]].to_numpy())
    eps = radius_km / 6371.0088
    
    try:
        labels = DBSCAN(
            eps=eps, min_samples=min_samples, metric="haversine"
        ).fit_predict(coords)
        
        out = df.copy()
        out["recurrence_cluster_id"] = labels
        out["is_recurring_hotspot"] = labels >= 0
        
        num_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        logger.info("dbscan_completed", num_clusters=num_clusters, points=len(df))
        return out
    except Exception as e:
        logger.error("dbscan_failed", error=str(e))
        out = df.copy()
        out["recurrence_cluster_id"] = -1
        out["is_recurring_hotspot"] = False
        return out

def compute_cluster_summaries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by cluster_id and returns summaries.
    Not strictly needed for DB upsert (since DB handles row by row), 
    but useful for returning aggregated recurrence clusters.
    """
    if df.empty or "recurrence_cluster_id" not in df.columns:
        return pd.DataFrame()
        
    recurring = df[df["is_recurring_hotspot"]]
    if recurring.empty:
        return pd.DataFrame()
        
    def mode_value(s):
        m = s.mode()
        return m.iloc[0] if not m.empty else "unknown"

    summary = recurring.groupby("recurrence_cluster_id").agg(
        detection_count=("fire_type", "size"),
        center_lat=("latitude", "mean"),
        center_lon=("longitude", "mean"),
        dominant_fire_type=("fire_type", mode_value),
        avg_frp=("frp", "mean"),
    ).reset_index()
    
    return summary[summary.detection_count >= MIN_RECURRENCES].sort_values("detection_count", ascending=False)
