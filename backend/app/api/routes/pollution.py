"""
SATVIGIL — Pollution API Route
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db
from app.services.pollution.cluster_analyzer import get_chronic_clusters

router = APIRouter()

@router.get("/clusters")
async def get_pollution_clusters(
    min_count: int = Query(3, ge=1, description="Minimum recurrence count to be considered a cluster"),
    days: int = Query(30, ge=1, le=365, description="Rolling window in days"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns spatial clusters of recurring thermal hotspots.
    Useful for identifying chronic industrial polluters.
    """
    clusters = await get_chronic_clusters(db, min_count=min_count, days=days)
    return {
        "clusters": clusters,
        "count": len(clusters)
    }

@router.get("/heatmap")
async def get_pollution_heatmap(
    min_count: int = Query(1, ge=1, description="Minimum recurrence count"),
    days: int = Query(30, ge=1, le=365, description="Rolling window in days"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns thermal recurrence heatmap data formatted as GeoJSON FeatureCollection.
    Used by Mapbox GL JS for rendering heatmaps.
    """
    clusters = await get_chronic_clusters(db, min_count=min_count, days=days)
    
    features = []
    for cluster in clusters:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [cluster["centroid_lon"], cluster["centroid_lat"]]
            },
            "properties": {
                "weight": cluster["total_recurrence"],
                "fire_type": cluster["dominant_fire_type"],
                "near_cpcb_cluster": cluster["near_cpcb_cluster"]
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }
