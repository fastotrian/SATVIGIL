import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import random

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.alert import ThermalHotspot
from sqlalchemy import text

DEMO_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'demo', 'firms_demo_scenario.json')

def generate_demo_data():
    now = datetime.now(timezone.utc)
    hotspots = []
    
    # 1. Industrial (near Vapi, Gujarat)
    for i in range(5):
        lat = 20.3733 + random.uniform(-0.05, 0.05)
        lon = 72.9050 + random.uniform(-0.05, 0.05)
        hotspots.append({
            "latitude": lat,
            "longitude": lon,
            "frp": random.uniform(300, 800),
            "brightness": random.uniform(320, 360),
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": (now - timedelta(hours=random.uniform(1, 48))).isoformat(),
            "fire_type": "industrial",
            "land_use": "industrial",
            "near_cpcb_cluster": True,
            "recurrence_count": random.randint(3, 10)
        })
        
    # 2. Gas Flare (Bombay High Offshore)
    for i in range(3):
        lat = 19.38 + random.uniform(-0.02, 0.02)
        lon = 71.33 + random.uniform(-0.02, 0.02)
        hotspots.append({
            "latitude": lat,
            "longitude": lon,
            "frp": random.uniform(50, 150),
            "brightness": random.uniform(300, 330),
            "confidence": "nominal",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": (now - timedelta(hours=random.uniform(1, 48))).isoformat(),
            "fire_type": "gas_flare",
            "land_use": "petroleum",
            "near_cpcb_cluster": False,
            "recurrence_count": random.randint(10, 30)
        })

    # 3. Stubble Burning (Punjab/Haryana grid)
    for i in range(30):
        lat = 30.9 + random.uniform(-1.0, 1.0)
        lon = 75.8 + random.uniform(-1.0, 1.0)
        hotspots.append({
            "latitude": lat,
            "longitude": lon,
            "frp": random.uniform(10, 50),
            "brightness": random.uniform(290, 310),
            "confidence": random.choice(["nominal", "high"]),
            "satellite": "MODIS_NRT",
            "acquired_at": (now - timedelta(hours=random.uniform(1, 48))).isoformat(),
            "fire_type": "stubble",
            "land_use": "farmland",
            "near_cpcb_cluster": False,
            "recurrence_count": random.randint(1, 3)
        })

    # 4. Wildfire (Wayanad / Western Ghats)
    for i in range(10):
        lat = 11.6 + random.uniform(-0.2, 0.2)
        lon = 76.0 + random.uniform(-0.2, 0.2)
        hotspots.append({
            "latitude": lat,
            "longitude": lon,
            "frp": random.uniform(50, 200),
            "brightness": random.uniform(310, 340),
            "confidence": random.choice(["nominal", "high"]),
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": (now - timedelta(hours=random.uniform(1, 48))).isoformat(),
            "fire_type": "wildfire",
            "land_use": "forest",
            "near_cpcb_cluster": False,
            "recurrence_count": 1
        })
        
    # 5. Mining (Jharia, Jharkhand)
    for i in range(5):
        lat = 23.75 + random.uniform(-0.05, 0.05)
        lon = 86.41 + random.uniform(-0.05, 0.05)
        hotspots.append({
            "latitude": lat,
            "longitude": lon,
            "frp": random.uniform(30, 100),
            "brightness": random.uniform(300, 320),
            "confidence": "high",
            "satellite": "VIIRS_SNPP_NRT",
            "acquired_at": (now - timedelta(hours=random.uniform(1, 48))).isoformat(),
            "fire_type": "mining",
            "land_use": "quarry",
            "near_cpcb_cluster": True,
            "recurrence_count": random.randint(5, 15)
        })

    with open(DEMO_FILE_PATH, 'w') as f:
        json.dump(hotspots, f, indent=2)
    print(f"Generated {len(hotspots)} demo hotspots in {DEMO_FILE_PATH}")
    return hotspots

async def seed_database():
    hotspots = generate_demo_data()
    
    async with AsyncSessionLocal() as session:
        try:
            for item in hotspots:
                point = f"SRID=4326;POINT({item['longitude']} {item['latitude']})"
                
                # Check for existing
                stmt = text("""
                    SELECT id FROM thermal_hotspots 
                    WHERE latitude = :lat AND longitude = :lon AND acquired_at = :acq
                """)
                res = await session.execute(stmt, {
                    "lat": item["latitude"],
                    "lon": item["longitude"],
                    "acq": datetime.fromisoformat(item["acquired_at"])
                })
                
                if res.scalar() is None:
                    hotspot_obj = ThermalHotspot(
                        latitude=item["latitude"],
                        longitude=item["longitude"],
                        location=point,
                        frp=item["frp"],
                        brightness=item["brightness"],
                        confidence=item["confidence"],
                        satellite=item["satellite"],
                        acquired_at=datetime.fromisoformat(item["acquired_at"]),
                        fire_type=item["fire_type"],
                        land_use=item["land_use"],
                        near_cpcb_cluster=item["near_cpcb_cluster"],
                        recurrence_count=item["recurrence_count"]
                    )
                    session.add(hotspot_obj)
            
            await session.commit()
            print("Successfully seeded database with thermal hotspots.")
        except Exception as e:
            await session.rollback()
            print(f"Failed to seed database: {e}")

if __name__ == "__main__":
    asyncio.run(seed_database())
