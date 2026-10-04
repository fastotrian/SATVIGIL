"""Controlled end-to-end integration pipeline (Phase 3).

    Detection fixture
      -> canonical site registration (SITE-NNNNNN)
      -> Monitoring V2 decision-support
      -> Prediction V1 feature builder (26 frozen features)
      -> Prediction V1 inference (frozen; threshold 0.30)
      -> validated integrated result

Monitoring is decision-support ONLY: it is never injected into the Prediction
V1 model. The Prediction chain (detection -> features -> inference) is the
required path for a risk result; Monitoring runs in parallel and its failure
degrades the result to "partial", never fabricating a score.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..schemas import (
    MONITORING_DECISION_SUPPORT_SCHEMA,
    PREDICTION_ALERT_SCHEMA,
    INTEGRATED_RESULT_SCHEMA,
    validate,
)
from ..common import SiteRegistry
from ..monitoring import MonitoringForecaster
from ..prediction import PredictionFeatureBuilder, FROZEN_FEATURE_ORDER
from ..providers.errors import FeatureGenerationError
from .detection_adapter import adapt_detection_to_monitoring
from .fixtures import DetectionFixture, CONTROLLED_MONITORING_META

# Monitoring-derived quantity names — must be disjoint from the 26 model features.
MONITORING_FEATURE_NAMES = frozenset({
    "displacement", "forecast_t1", "forecast_t2", "forecast_t3",
    "velocity", "acceleration", "trend", "trend_slope",
    "velocity_t1", "velocity_t2", "velocity_t3",
    "acceleration_t2", "acceleration_t3", "coherence_proxy",
})
# Static invariant: proven once here, asserted again at runtime.
MONITORING_PREDICTION_FEATURE_OVERLAP = MONITORING_FEATURE_NAMES & set(FROZEN_FEATURE_ORDER)
assert MONITORING_PREDICTION_FEATURE_OVERLAP == set(), "monitoring leaked into prediction features"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _err(exc: Exception) -> dict:
    code = getattr(exc, "code", exc.__class__.__name__)
    return {"code": code, "type": exc.__class__.__name__, "message": str(exc)}


@dataclass
class IntegrationPipeline:
    registry: SiteRegistry
    forecaster: MonitoringForecaster
    feature_builder: PredictionFeatureBuilder
    predictor: object              # frozen LandslideRiskPredictor (injected)

    def run(
        self,
        detection: DetectionFixture,
        monitoring_history: list[float],
        *,
        event_time_utc: Optional[str] = None,
        scene_id: str = "controlled_scene",
        monitoring_time_steps: Optional[list[int]] = None,
    ) -> dict:
        detection_stage = {"status": "skipped", "feature": None, "error": None}
        monitoring_stage = {"status": "skipped", "decision_support": None, "error": None}
        prediction_stage = {"status": "skipped", "alert": None, "error": None}
        site_id = None
        warnings: list[str] = []

        # ---- Stage 1: Detection -> site registration ----
        try:
            det_doc = adapt_detection_to_monitoring(detection, self.registry, scene_id=scene_id)
            feature = det_doc["features"][0]
            site_id = feature["site_id"]
            centroid = feature["centroid"]
            evt = event_time_utc or feature.get("acquisition_date")
            detection_stage = {"status": "success", "feature": feature, "error": None}
        except Exception as e:  # noqa: BLE001
            detection_stage = {"status": "failed", "feature": None, "error": _err(e)}
            return self._assemble(site_id, detection_stage, monitoring_stage,
                                  prediction_stage, warnings)

        # ---- Stage 2: Monitoring decision-support (parallel; not required) ----
        try:
            ds = self.forecaster.build_decision_support(
                monitoring_history,
                site_id=site_id,
                time_steps=monitoring_time_steps or CONTROLLED_MONITORING_META["time_steps"],
            )
            validate(ds, MONITORING_DECISION_SUPPORT_SCHEMA)
            monitoring_stage = {"status": "success", "decision_support": ds, "error": None}
        except Exception as e:  # noqa: BLE001
            monitoring_stage = {"status": "failed", "decision_support": None, "error": _err(e)}
            warnings.append("monitoring decision-support unavailable; prediction proceeds without it")

        # ---- Stage 3+4: Prediction feature build + inference (required) ----
        try:
            pf = self.feature_builder.build(centroid["latitude"], centroid["longitude"], evt)
            row = pf.as_row_dict()

            # Runtime proof: monitoring never enters the model feature vector.
            overlap = set(row) & MONITORING_FEATURE_NAMES
            if overlap:
                raise FeatureGenerationError(f"monitoring features leaked: {sorted(overlap)}")

            score = float(self.predictor.predict_proba(row)[0])
            threshold = float(self.predictor.threshold)
            flag = "alert" if score >= threshold else "no_alert"

            alert = {
                "schema": "landslideguard.prediction_alert/1.0",
                "generated_at": _utc_now_iso(),
                "site_id": site_id,
                "event_time_utc": evt,
                "prediction": {
                    "score": score,
                    "score_kind": "risk_ranking_not_calibrated_probability",
                    "threshold": threshold,
                    "flag": flag,
                },
                "model": {
                    "name": "prediction_v1",
                    "version": str(getattr(self.predictor, "metadata", {}).get("model_version", "prediction_v1")),
                    "seed": int(getattr(self.predictor, "metadata", {}).get("random_seed", 42)),
                },
                "monitoring_context": {
                    "monitoring_decision_support_ref": (
                        f"{site_id}/monitoring_decision_support"
                        if monitoring_stage["status"] == "success" else None
                    ),
                    "used_as_model_input": False,
                    "used_as_decision_support": monitoring_stage["status"] == "success",
                },
                "warnings": warnings,
                # provenance (extra; allowed)
                "feature_vector": row,
                "feature_provenance": pf.provenance,
            }
            validate(alert, PREDICTION_ALERT_SCHEMA)
            prediction_stage = {"status": "success", "alert": alert, "error": None}
        except Exception as e:  # noqa: BLE001
            prediction_stage = {"status": "failed", "alert": None, "error": _err(e)}

        return self._assemble(site_id, detection_stage, monitoring_stage,
                              prediction_stage, warnings)

    def _assemble(self, site_id, detection_stage, monitoring_stage,
                  prediction_stage, warnings) -> dict:
        # Required chain for a risk result: detection + prediction.
        required_ok = (detection_stage["status"] == "success"
                       and prediction_stage["status"] == "success")
        if not required_ok:
            status = "failed"
        elif monitoring_stage["status"] != "success":
            status = "partial"
        else:
            status = "success"

        result = {
            "schema": "landslideguard.integrated_result/1.0",
            "generated_at": _utc_now_iso(),
            "site_id": site_id,
            "integration_status": status,
            "detection": detection_stage,
            "monitoring": monitoring_stage,
            "prediction": prediction_stage,
            "checks": {
                "monitoring_prediction_feature_overlap": sorted(MONITORING_PREDICTION_FEATURE_OVERLAP),
                "monitoring_used_as_model_input": False,
                "prediction_threshold": (
                    prediction_stage["alert"]["prediction"]["threshold"]
                    if prediction_stage["status"] == "success" else None
                ),
                "warnings": warnings,
            },
        }
        validate(result, INTEGRATED_RESULT_SCHEMA)
        return result


# ---- convenience wiring with the real frozen artifacts ----

_PRED_DIR = Path(r"D:/LANDSLIDE/LandslideGuard_Prediction")
_MON_DIR = Path(r"D:/LANDSLIDE/LandslideGuard_Monitering")
_POS_DAILY = _PRED_DIR / "imerg_targeted_download" / "extracted" / "glc_event_daily_rainfall.csv"
_CTRL_DAILY = (_PRED_DIR / "prediction_dataset" / "imerg_targeted_download"
               / "control_imerg_extraction" / "control_daily_rainfall.csv")
_TILES = _PRED_DIR / "prediction_dataset" / "terrain_context" / "srtm_30m" / "tiles"
_DOWNLOADS = _PRED_DIR / "prediction_dataset" / "terrain_context" / "srtm_30m" / "downloads"


def build_default_pipeline(registry_path) -> IntegrationPipeline:
    """Wire the pipeline with the frozen Monitoring V2, Phase-2 providers, and
    the frozen Prediction V1 inference engine."""
    import sys
    from ..providers import IMERGFinalV07ReferenceProvider, SRTM30mTerrainProvider

    # Frozen Prediction V1 inference engine (external package).
    pred_src = str(_PRED_DIR / "src")
    if pred_src not in sys.path:
        sys.path.insert(0, pred_src)
    from prediction_v1 import LandslideRiskPredictor

    registry = SiteRegistry(registry_path)
    forecaster = MonitoringForecaster.from_dir(_MON_DIR)
    rain = IMERGFinalV07ReferenceProvider([_POS_DAILY, _CTRL_DAILY], coord_round=5)
    terr = SRTM30mTerrainProvider(_TILES, _DOWNLOADS)
    feature_builder = PredictionFeatureBuilder(rain, terr)
    predictor = LandslideRiskPredictor.from_dir(_PRED_DIR / "models" / "prediction_v1")
    return IntegrationPipeline(registry, forecaster, feature_builder, predictor)


__all__ = [
    "IntegrationPipeline",
    "build_default_pipeline",
    "MONITORING_FEATURE_NAMES",
    "MONITORING_PREDICTION_FEATURE_OVERLAP",
]
