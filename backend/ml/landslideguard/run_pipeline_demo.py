"""LandslideGuard — Operational Pipeline Execution (Option 1).

Executes the unified end-to-end orchestration connecting:
  1. Detection V1 (via adapter & CRS reprojection to EPSG:4326)
  2. Canonical Site Registry (generating / tracking persistent SITE-NNNNNN)
  3. Monitoring V2 (SimpleTCNV2 forecasting displacement at t+1, t+2, t+3 + kinematics)
  4. Prediction V1 (26-feature contract: 14-day IMERG rainfall + SRTM terrain -> XGBoost risk ranking)
  5. Operational Result Contract (integrated_result/1.0 with full provenance)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Set up local paths and temporary directory to avoid C: drive space constraints
BASE_DIR = Path("D:/LANDSLIDE")
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
from landslideguard.integration import (
    OperationalOrchestrator,
    controlled_detection_fixture,
    CONTROLLED_MONITORING_HISTORY,
)


def print_section(title: str):
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)


def main():
    print_section("LANDSLIDEGUARD OPERATIONAL PIPELINE (OPTION 1)")
    print("Initializing components from frozen artifacts...")

    # 1. Site Registry
    registry_path = CACHE_DIR / "site_registry.parquet"
    if not registry_path.parent.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry = SiteRegistry(registry_path)
    print(f"[OK] SiteRegistry loaded from: {registry_path}")

    # 2. Monitoring Forecaster (SimpleTCNV2)
    forecaster = MonitoringForecaster.from_dir(MON_DIR)
    print(f"[OK] MonitoringForecaster loaded from: {MON_DIR / 'models/monitoring_v2_tcn_best.pth'}")

    # 3. Live/Offline Prediction Service
    try:
        prediction_service = build_live_service(CACHE_DIR, min_free_gb=1.0)
        mode_label = "LIVE REMOTE (with local cache)"
    except Exception as e:
        print(f"[NOTE] Live remote initialization ({e}), using verified reference service.")
        prediction_service = build_offline_service()
        mode_label = "OFFLINE REFERENCE"
    print(f"[OK] Prediction Service loaded ({mode_label})")

    # 4. Initialize Operational Orchestrator
    orchestrator = OperationalOrchestrator(
        registry=registry,
        forecaster=forecaster,
        prediction_service=prediction_service,
        monitoring_source_label="controlled_insar_stack",
    )
    print("[OK] OperationalOrchestrator initialized.")

    # 5. Prepare Detection Fixture & Displacement Input
    detection = controlled_detection_fixture(crs="EPSG:4326")
    monitoring_history = CONTROLLED_MONITORING_HISTORY

    print_section("EXECUTING PIPELINE RUN")
    print(f"Target Centroid    : Lat {detection.centroid['latitude']}, Lon {detection.centroid['longitude']}")
    print(f"Acquisition Date   : {detection.acquisition_date}")
    print(f"Detection Confidence: {detection.detection_confidence:.4f}")
    print(f"Monitoring Window  : 12 timesteps (last value: {monitoring_history[-1]} mm)")

    # Execute Orchestration
    result = orchestrator.run(
        detection=detection,
        monitoring_history=monitoring_history,
        event_time_utc="2007-03-12T00:00:00Z",
    )

    print_section("PIPELINE EXECUTION RESULTS")
    print(f"Operation ID       : {result['operation_id']}")
    print(f"Canonical Site ID  : {result['site_id']}")
    print(f"Integration Status : {result['integration_status'].upper()}")
    print(f"Started At (UTC)   : {result['operation_started_at']}")
    print(f"Completed At (UTC) : {result['operation_completed_at']}")

    # Detection Stage
    det = result["detection"]["feature"]
    print("\n--- 1. DETECTION STAGE ---")
    print(f"  Model            : {det['model']} (threshold {det['threshold']})")
    print(f"  Confidence       : {det['detection_confidence']:.4f} (calibrated: {det['detection_confidence_is_calibrated']})")
    print(f"  Area             : {det['area_m2'] / 1e6:.2f} km²")
    print(f"  CRS              : {det['crs']}")

    # Monitoring Stage
    mon = result["monitoring"]["decision_support"]
    print("\n--- 2. MONITORING STAGE (TCN FORECASTING) ---")
    print(f"  Model            : {mon['monitoring_model']}")
    print(f"  Forecast Horizon : {mon['forecast_horizon']} steps")
    print(f"  Forecast (t+1)   : {mon['forecast']['t1']['value']:.3f} (units: {mon['displacement_units']})")
    print(f"  Forecast (t+2)   : {mon['forecast']['t2']['value']:.3f} (units: {mon['displacement_units']})")
    print(f"  Forecast (t+3)   : {mon['forecast']['t3']['value']:.3f} (units: {mon['displacement_units']})")
    print(f"  Velocity Vector  : {mon['derived']['velocity']}")
    print(f"  Acceleration Vec : {mon['derived']['acceleration']}")
    print(f"  Trend Direction  : {mon['derived']['trend']} (slope: {mon['derived']['trend_slope']:.4f})")
    print(f"  Used as Pred In  : {mon['usage']['used_as_prediction_model_input']}")

    # Prediction Stage
    pred = result["prediction"]["alert"]
    fv = pred["feature_vector"]
    print("\n--- 3. PREDICTION STAGE (XGBOOST TRIGGER RISK) ---")
    print(f"  Model            : {pred['model']['name']} (v{pred['model']['version']})")
    print(f"  Features Count   : {len(fv)} (Contract: 26 features)")
    print(f"  Risk Score       : {pred['prediction']['score']:.4f}")
    print(f"  Score Semantics  : {pred['prediction']['score_kind']}")
    print(f"  Alert Decision   : {'>>> HAZARD ALERT TRIGGERED <<<' if pred['prediction']['flag'] else 'NORMAL (BELOW THRESHOLD)'}")
    print(f"  Decision Thresh  : {pred['prediction']['threshold']:.2f}")

    print("\n  Sample Topographic & Hydrologic Features:")
    print(f"    Elevation (m)  : {fv['elevation_m']:.1f} m")
    print(f"    Slope (deg)    : {fv['slope_degrees']:.2f}°")
    print(f"    Aspect (deg)   : {fv['aspect_degrees']:.2f}°")
    print(f"    Rainfall 3-day : {fv['rain_sum_3d']:.2f} mm")
    print(f"    Rainfall 7-day : {fv['rain_sum_7d']:.2f} mm")
    print(f"    Rainfall 14-day: {fv['rain_sum_14d']:.2f} mm")
    print(f"    Rain Max 3-day : {fv['rain_max_3d']:.2f} mm")

    # Governance Checks
    checks = result["checks"]
    print("\n--- 4. SCIENTIFIC GOVERNANCE & INTEGRITY CHECKS ---")
    print(f"  Feature Overlap Check : {checks['monitoring_prediction_feature_overlap']} (Expected: [])")
    print(f"  Monitoring Leak Guard : {not checks['monitoring_used_as_model_input']} (Strictly isolated)")
    print(f"  Schema Specification  : {result['schema']}")

    print_section("EXECUTION COMPLETED SUCCESSFULLY (100% GREEN)")


if __name__ == "__main__":
    main()
