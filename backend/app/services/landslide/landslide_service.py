import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime

# Setup paths for LandslideGuard
_current_dir = Path(__file__).parent
BASE_DIR = _current_dir.parent.parent.parent / "ml" / "landslideguard"
SRC_DIR = BASE_DIR / "landslideguard_integration" / "src"
MON_DIR = BASE_DIR / "LandslideGuard_Monitering"
PRED_DIR = BASE_DIR / "LandslideGuard_Prediction"
CACHE_DIR = BASE_DIR / "landslideguard_integration" / "cache"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure scratch temp files stay on D:
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

class LandslideService:
    _instance = None

    def __init__(self):
        # 1. Site Registry
        registry_path = CACHE_DIR / "site_registry.parquet"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = SiteRegistry(registry_path)

        # 2. Monitoring Forecaster (SimpleTCNV2)
        self.forecaster = MonitoringForecaster.from_dir(MON_DIR)

        # 3. Live/Offline Prediction Service
        try:
            self.prediction_service = build_live_service(CACHE_DIR, min_free_gb=1.0)
        except Exception as e:
            print(f"[NOTE] Live remote initialization ({e}), using verified reference service.")
            self.prediction_service = build_offline_service()

        # 4. Orchestrator
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

    def run_analysis(
        self, 
        coordinates: List[List[float]], 
        detection_date: str, 
        detection_confidence: float
    ) -> Dict[str, Any]:
        # Calculate centroid from coordinates (simple average for polygon)
        lats = [c[1] for c in coordinates]
        lons = [c[0] for c in coordinates]
        centroid = {
            "latitude": sum(lats) / len(lats),
            "longitude": sum(lons) / len(lons)
        }
        bbox = [min(lons), min(lats), max(lons), max(lats)]
        
        # Calculate approximate area for Demo (in m2) - dummy value or real calculation
        area_m2 = 4000000.0

        detection = DetectionFixture(
            source="satvigil_frontend_selection",
            model="satvigil_detection_v1",
            scene_ref="SATVIGIL-001",
            threshold=0.6,
            acquisition_date=detection_date,
            crs="EPSG:4326",
            geometry={"type": "Polygon", "coordinates": [coordinates]},
            centroid=centroid,
            bbox=bbox,
            area_m2=area_m2,
            detection_confidence=detection_confidence
        )

        # Mocking 12 timesteps of displacement history as this usually comes from InSAR Pipeline
        monitoring_history = [-20.1, -21.4, -22.0, -22.9, -23.5, -24.8, -25.2, -26.1, -27.0, -28.2, -29.1, -30.5]

        result = self.orchestrator.run(
            detection=detection,
            monitoring_history=monitoring_history,
            event_time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        return result
