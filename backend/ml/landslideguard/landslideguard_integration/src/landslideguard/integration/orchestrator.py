"""Phase-8 operational end-to-end orchestration.

Connects the FROZEN Detection V1 (via controlled fixture/adapter), Monitoring V2,
and Prediction V1 through one controlled orchestration that produces a single
unified `integrated_result/1.0` document with operation metadata, timestamps,
and full provenance.

Reuses (never duplicates or modifies) the existing components:
  * SiteRegistry                    (canonical opaque site_id)
  * adapt_detection_to_monitoring   (Detection -> Monitoring handoff, CRS -> 4326)
  * MonitoringForecaster            (frozen Monitoring V2)
  * LivePredictionService           (PredictionFeatureBuilder + frozen LandslideRiskPredictor)

Scientific boundary (enforced at runtime): Monitoring outputs are NEVER Prediction
V1 model inputs. Prediction receives exactly the 26 frozen features (23 rainfall +
3 terrain); `used_as_prediction_model_input` stays false.

Status semantics:
  SUCCESS  : detection + monitoring + prediction all succeeded
  PARTIAL  : detection succeeded and exactly one of monitoring/prediction succeeded
  FAILED   : detection failed, or neither monitoring nor prediction produced a result
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..schemas import (
    MONITORING_DECISION_SUPPORT_SCHEMA,
    INTEGRATED_RESULT_SCHEMA,
    validate,
)
from ..common import SiteRegistry
from ..monitoring import MonitoringForecaster
from ..prediction import FROZEN_FEATURE_ORDER
from .detection_adapter import adapt_detection_to_monitoring
from .fixtures import DetectionFixture, CONTROLLED_MONITORING_META
from .pipeline import MONITORING_FEATURE_NAMES, MONITORING_PREDICTION_FEATURE_OVERLAP

assert MONITORING_PREDICTION_FEATURE_OVERLAP == set()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _err(component: str, exc: Exception, site_id, operation_id) -> dict:
    return {
        "component": component,
        "code": getattr(exc, "code", exc.__class__.__name__),
        "type": exc.__class__.__name__,
        "message": str(exc)[:200],
        "timestamp": _utc_now(),
        "site_id": site_id,
        "operation_id": operation_id,
        "recoverable": isinstance(exc, Exception),
    }


@dataclass
class OperationalOrchestrator:
    registry: SiteRegistry
    forecaster: MonitoringForecaster
    prediction_service: object       # LivePredictionService (offline or live)
    monitoring_source_label: str = "controlled_test_fixture"

    def run(
        self,
        detection: DetectionFixture,
        monitoring_history: list[float],
        *,
        event_time_utc: Optional[str] = None,
        scene_id: str = "controlled_scene",
        monitoring_time_steps: Optional[list[int]] = None,
    ) -> dict:
        operation_id = "OP-" + uuid.uuid4().hex[:12]
        started = _utc_now()
        site_id = None
        detection_stage = {"status": "skipped", "feature": None, "error": None}
        monitoring_stage = {"status": "skipped", "decision_support": None, "error": None}
        prediction_stage = {"status": "skipped", "alert": None, "error": None}
        provenance = {"detection": None, "monitoring": None, "prediction": None, "cache": None}

        # ---- Detection -> site registration -> handoff ----
        try:
            det_doc = adapt_detection_to_monitoring(detection, self.registry, scene_id=scene_id)
            feature = det_doc["features"][0]
            site_id = feature["site_id"]
            centroid = feature["centroid"]
            evt = event_time_utc or feature.get("acquisition_date")
            detection_stage = {"status": "success", "feature": feature, "error": None}
            provenance["detection"] = {
                "source": feature["source"], "model": feature["model"],
                "threshold": feature["threshold"], "acquisition_date": feature.get("acquisition_date"),
                "source_crs": feature.get("source_crs"), "target_crs": feature["crs"],
                "detection_confidence": feature["detection_confidence"],
                "detection_confidence_is_calibrated": feature["detection_confidence_is_calibrated"],
            }
        except Exception as e:  # noqa: BLE001
            detection_stage = {"status": "failed", "feature": None,
                               "error": _err("detection", e, site_id, operation_id)}
            return self._finalize(operation_id, started, site_id, detection_stage,
                                  monitoring_stage, prediction_stage, provenance)

        # ---- Monitoring (parallel decision-support; controlled input) ----
        try:
            ds = self.forecaster.build_decision_support(
                monitoring_history, site_id=site_id,
                time_steps=monitoring_time_steps or CONTROLLED_MONITORING_META["time_steps"])
            validate(ds, MONITORING_DECISION_SUPPORT_SCHEMA)
            monitoring_stage = {"status": "success", "decision_support": ds, "error": None}
            provenance["monitoring"] = {
                "model": ds["monitoring_model"], "input_source": self.monitoring_source_label,
                "input_window": ds["input_window"], "forecast_horizon": ds["forecast_horizon"],
                "displacement_units": ds["displacement_units"],
                "coherence_proxy": ds["quality"]["coherence_proxy"],
                "used_as_prediction_model_input": ds["usage"]["used_as_prediction_model_input"],
            }
        except Exception as e:  # noqa: BLE001
            monitoring_stage = {"status": "failed", "decision_support": None,
                                "error": _err("monitoring", e, site_id, operation_id)}

        # ---- Prediction (independent inputs: live IMERG + SRTM -> 26 features) ----
        try:
            r = self.prediction_service.predict_location(
                centroid["latitude"], centroid["longitude"], evt)
            row = r["features"]
            # Runtime scientific-boundary assertion.
            overlap = set(row) & MONITORING_FEATURE_NAMES
            if overlap:
                raise ValueError(f"monitoring features leaked into prediction: {sorted(overlap)}")
            if list(row.keys()) != list(FROZEN_FEATURE_ORDER) or len(row) != 26:
                raise ValueError("prediction feature vector does not match the 26-feature contract")

            alert = {
                "schema": "landslideguard.prediction_alert/1.0",
                "generated_at": _utc_now(), "site_id": site_id,
                "event_time_utc": r["event_time_utc"],
                "prediction": {"score": r["risk_score"],
                               "score_kind": r["score_kind"],
                               "threshold": r["threshold"], "flag": r["prediction"]},
                "model": {"name": r["provenance"].get("model_name", "prediction_v1"),
                          "version": r["provenance"].get("model_version", "prediction_v1"),
                          "seed": 42},
                "monitoring_context": {
                    "monitoring_decision_support_ref": (f"{site_id}/monitoring_decision_support"
                                                        if monitoring_stage["status"] == "success" else None),
                    "used_as_model_input": False,
                    "used_as_decision_support": monitoring_stage["status"] == "success"},
                "warnings": [],
                "feature_vector": row,
            }
            prediction_stage = {"status": "success", "alert": alert, "error": None}
            provenance["prediction"] = {
                "model": alert["model"]["name"], "model_version": alert["model"]["version"],
                "threshold": r["threshold"], "score_kind": r["score_kind"],
                "mode": r.get("mode"),
                "rainfall_provider": r["provenance"].get("rainfall_source"),
                "imerg_product": r["provenance"].get("rainfall_product"),
                "imerg_version": r["provenance"].get("rainfall_version"),
                "rainfall_window": r["provenance"].get("rainfall_window"),
                "event_day_excluded": r["provenance"].get("event_day_excluded"),
                "terrain_provider": r["provenance"].get("terrain_source"),
                "srtm_product": r["provenance"].get("terrain_product"),
                "terrain_method": r["provenance"].get("terrain_method"),
                "feature_contract_version": r["provenance"].get("feature_contract_version"),
                "n_features": len(row),
            }
        except Exception as e:  # noqa: BLE001
            prediction_stage = {"status": "failed", "alert": None,
                                "error": _err("prediction", e, site_id, operation_id)}

        return self._finalize(operation_id, started, site_id, detection_stage,
                              monitoring_stage, prediction_stage, provenance)

    def _finalize(self, operation_id, started, site_id, det, mon, pred, provenance) -> dict:
        det_ok = det["status"] == "success"
        mon_ok = mon["status"] == "success"
        pred_ok = pred["status"] == "success"
        if not det_ok:
            status = "failed"
        elif mon_ok and pred_ok:
            status = "success"
        elif mon_ok or pred_ok:
            status = "partial"
        else:
            status = "failed"

        result = {
            "schema": "landslideguard.integrated_result/1.0",
            "generated_at": _utc_now(),
            "operation_id": operation_id,
            "operation_started_at": started,
            "operation_completed_at": _utc_now(),
            "site_id": site_id,
            "integration_status": status,
            "detection": det,
            "monitoring": mon,
            "prediction": pred,
            "checks": {
                "monitoring_prediction_feature_overlap": sorted(MONITORING_PREDICTION_FEATURE_OVERLAP),
                "monitoring_used_as_model_input": False,
                "prediction_threshold": (pred["alert"]["prediction"]["threshold"]
                                         if pred_ok else None),
                "prediction_n_features": (len(pred["alert"]["feature_vector"]) if pred_ok else None),
            },
            "provenance": provenance,
        }
        validate(result, INTEGRATED_RESULT_SCHEMA)
        return result


__all__ = ["OperationalOrchestrator"]
