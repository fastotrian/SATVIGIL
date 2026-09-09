"""
SATVIGIL — Pollution Module: Recurrence Cluster Analyzer
Identifies chronic industrial violators by clustering thermal hotspots spatially over time.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any

async def get_chronic_clusters(db: AsyncSession, min_count: int = 3, days: int = 30) -> List[Dict[str, Any]]:
    """
    Groups thermal hotspots by 0.01° grid bucket.
    Filters for grid cells with recurrence_count >= min_count within the last `days`.
    Returns cluster centroid, bounding box, dominant fire type, total recurrence count.
    """
    
    # We use a pure PostGIS spatial grouping query.
    # We round lat/lon to 2 decimal places (approx 1.1km) to form grid cells.
    # We also join with the most common fire type for that grid cell.
    
    stmt = text("""
        WITH grid_cells AS (
            SELECT 
                ROUND(latitude::numeric, 2) AS grid_lat,
                ROUND(longitude::numeric, 2) AS grid_lon,
                COUNT(*) AS total_recurrence,
                MAX(near_cpcb_cluster::int) AS is_near_cpcb,
                -- We use an array aggregate to later pick the most common type
                MODE() WITHIN GROUP (ORDER BY fire_type) AS dominant_fire_type,
                MIN(latitude) as min_lat,
                MAX(latitude) as max_lat,
                MIN(longitude) as min_lon,
                MAX(longitude) as max_lon
            FROM thermal_hotspots
            WHERE acquired_at >= NOW() - INTERVAL ':days days'
            GROUP BY ROUND(latitude::numeric, 2), ROUND(longitude::numeric, 2)
            HAVING COUNT(*) >= :min_count
        )
        SELECT 
            grid_lat AS centroid_lat,
            grid_lon AS centroid_lon,
            total_recurrence,
            is_near_cpcb = 1 AS near_cpcb_cluster,
            dominant_fire_type,
            min_lat, max_lat, min_lon, max_lon
        FROM grid_cells
        ORDER BY total_recurrence DESC;
    """)
    
    result = await db.execute(stmt, {"days": days, "min_count": min_count})
    rows = result.fetchall()
    
    clusters = []
    for row in rows:
        clusters.append({
            "centroid_lat": float(row.centroid_lat),
            "centroid_lon": float(row.centroid_lon),
            "total_recurrence": int(row.total_recurrence),
            "near_cpcb_cluster": bool(row.near_cpcb_cluster),
            "dominant_fire_type": row.dominant_fire_type,
            "bbox": {
                "min_lat": float(row.min_lat),
                "max_lat": float(row.max_lat),
                "min_lon": float(row.min_lon),
                "max_lon": float(row.max_lon)
            }
        })
        
    return clusters
