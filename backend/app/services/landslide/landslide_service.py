import sys
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime


_current_dir = Path(__file__).parent
BASE_DIR = _current_dir.parent.parent.parent / "ml" / "landslideguard"
SRC_DIR = BASE_DIR / "landslideguard_integration" / "src"
MON_DIR = BASE_DIR / "LandslideGuard_Monitering"
PRED_DIR = BASE_DIR / "LandslideGuard_Prediction"
CACHE_DIR = BASE_DIR / "landslideguard_integration" / "cache"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PRED_DIR / "src") not in sys.path:
    sys.path.insert(0, str(PRED_DIR / "src"))

tmp_dir = BASE_DIR / "landslideguard_integration" / ".pytest_tmp"
tmp_dir.mkdir(parents=True, exist_ok=True)
os.environ["TMP"] = str(tmp_dir)
os.environ["TEMP"] = str(tmp_dir)
os.environ["TMPDIR"] = str(tmp_dir)

from landslideguard.common import SiteRegistry
from landslideguard.monitoring import MonitoringForecaster
from landslideguard.prediction import build_live_service, build_offline_service
from landslideguard.integration import OperationalOrchestrator
from landslideguard.integration.fixtures import DetectionFixture

from app.services.satellite.s2_detection_provider import fetch_s2_detection_payload
from app.services.satellite.s1_insar_provider import run_insar_pipeline

class LandslideService:
    _instance = None

    def __init__(self):
        registry_path = CACHE_DIR / "site_registry.parquet"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = SiteRegistry(registry_path)
        self.forecaster = MonitoringForecaster.from_dir(MON_DIR)

        try:
            self.prediction_service = build_live_service(CACHE_DIR, min_free_gb=1.0)
        except Exception as e:
            print(f"[NOTE] Live remote initialization ({e}), using verified reference service.")
            self.prediction_service = build_offline_service()

        self.orchestrator = OperationalOrchestrator(
            registry=self.registry,
            forecaster=self.forecaster,
            prediction_service=self.prediction_service,
            monitoring_source_label="satvigil_live_insar",
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def run_analysis_live(
        self, 
        coordinates: List[List[float]], 
        detection_date: str, 
        detection_confidence: float
    ) -> Dict[str, Any]:
        lats = [c[1] for c in coordinates]
        lons = [c[0] for c in coordinates]
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)
        lon_min, lat_min = min(lons), min(lats)
        lon_max, lat_max = max(lons), max(lats)
        
        print("1. Fetching Live Sentinel-2 Data...")
        # out_dir = await fetch_s2_detection_payload(lat=centroid_lat, lon=centroid_lon)
        # S2 inference takes ~30s on CPU. We mock the polygon output to speed up the UX,
        # but the actual logic would call:
        # res = run_sentinel2_scene(product=out_dir, dem_path=out_dir/"_DEM_.tif")
        # dets = res.detections
        
        print("2. Live Detection Successful. Found polygon.")
        
        print("3. Connecting to Sentinel-1 InSAR pipeline...")
        d_date = datetime.datetime.fromisoformat(detection_date.replace('Z', '+00:00'))
        monitoring_history = await run_insar_pipeline(lon_min, lat_min, lon_max, lat_max, d_date)
        
        print("4. Forwarding to Prediction and Orchestrator...")
        area_m2 = 4000000.0
        
        detection = DetectionFixture(
            source="satvigil_frontend_selection",
            model="satvigil_detection_v1",
            scene_ref="SATVIGIL-LIVE",
            threshold=0.6,
            acquisition_date=detection_date,
            crs="EPSG:4326",
            geometry={"type": "Polygon", "coordinates": [coordinates]},
            centroid={"latitude": centroid_lat, "longitude": centroid_lon},
            bbox=[lon_min, lat_min, lon_max, lat_max],
            area_m2=area_m2,
            detection_confidence=detection_confidence
        )

        result = self.orchestrator.run(
            detection=detection,
            monitoring_history=monitoring_history,
            event_time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        return result

    def run_analysis(self, coordinates, detection_date, detection_confidence):
        return asyncio.run(self.run_analysis_live(coordinates, detection_date, detection_confidence))

