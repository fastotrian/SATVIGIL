"""JSON-Schema definitions for the three integration wire contracts.

Draft-2020-12-flavored, restricted to the subset understood by
`landslideguard.schemas.validator`. Each schema carries a `schema_id` and a
semantic `version` so producers and consumers can detect drift.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Detection -> Monitoring
# ---------------------------------------------------------------------------
# Superset of Detection's existing MonitoringHandoff (adds site_id +
# event_time_utc). Geometry is GeoJSON in EPSG:4326. detection_confidence is
# explicitly NOT a calibrated occurrence probability.

_GEOJSON_GEOMETRY = {
    "type": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"type": "string", "enum": ["Polygon", "MultiPolygon"]},
        "coordinates": {"type": "array"},
    },
}

_CENTROID = {
    "type": "object",
    "required": ["latitude", "longitude"],
    "properties": {
        "latitude": {"type": "number", "minimum": -90, "maximum": 90},
        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
    },
}

DETECTION_MONITORING_SCHEMA = {
    "schema_id": "landslideguard.detection_monitoring",
    "version": "1.0",
    "type": "object",
    "required": ["schema", "generated_at", "scene_id", "features"],
    "properties": {
        "schema": {"const": "landslideguard.detection_monitoring/1.0"},
        "generated_at": {"type": "string"},
        "scene_id": {"type": "string"},
        "event_time_utc": {"type": ["string", "null"]},
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "site_id", "geometry", "centroid", "area_m2",
                    "detection_confidence", "detection_confidence_is_calibrated",
                    "source", "model", "threshold", "crs",
                ],
                "additionalProperties": True,
                "properties": {
                    "site_id": {"type": "string"},
                    "detection_scene_ref": {"type": ["string", "null"]},
                    "geometry": _GEOJSON_GEOMETRY,
                    "centroid": _CENTROID,
                    "area_m2": {"type": "number", "minimum": 0},
                    "detection_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    # Detection score is not a calibrated occurrence probability.
                    "detection_confidence_is_calibrated": {"const": False},
                    "source": {"type": "string"},
                    "acquisition_date": {"type": ["string", "null"]},
                    "model": {"type": "string"},
                    "threshold": {"type": "number"},
                    "crs": {"type": "string"},
                },
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 2. Monitoring -> Decision Support
# ---------------------------------------------------------------------------
# The forecast, the derived kinematics, quality metadata, units, and the
# hard constraint that Monitoring is NOT a Prediction V1 model input.

_FORECAST_POINT = {
    "type": "object",
    "required": ["value"],
    "properties": {
        "value": {"type": "number"},
        "quantile_low": {"type": ["number", "null"]},
        "quantile_high": {"type": ["number", "null"]},
    },
}

MONITORING_DECISION_SUPPORT_SCHEMA = {
    "schema_id": "landslideguard.monitoring_decision_support",
    "version": "1.0",
    "type": "object",
    "required": [
        "schema", "generated_at", "site_id", "monitoring_model",
        "input_window", "forecast_horizon", "displacement_units",
        "history", "forecast", "derived", "quality", "usage",
    ],
    "additionalProperties": True,
    "properties": {
        "schema": {"const": "landslideguard.monitoring_decision_support/1.0"},
        "generated_at": {"type": "string"},
        "site_id": {"type": ["string", "null"]},
        "monitoring_model": {"type": "string"},
        "input_window": {"const": 12},
        "forecast_horizon": {"const": 3},
        # Units are unresolved until independently verified. Pinned as a const
        # so nobody can silently assert mm/day etc. downstream.
        "displacement_units": {"const": "unresolved"},
        "history": {
            "type": "object",
            "required": ["values"],
            "properties": {
                "time_steps": {"type": ["array", "null"]},
                "values": {"type": "array", "items": {"type": "number"},
                           "minItems": 12, "maxItems": 12},
            },
        },
        "forecast": {
            "type": "object",
            "required": ["t1", "t2", "t3"],
            "properties": {"t1": _FORECAST_POINT, "t2": _FORECAST_POINT, "t3": _FORECAST_POINT},
        },
        "derived": {
            "type": "object",
            "required": ["velocity", "acceleration", "trend", "trend_slope"],
            "properties": {
                # velocity per forecast step: [v1, v2, v3]
                "velocity": {"type": "array", "items": {"type": ["number", "null"]}},
                # acceleration: [null, a2, a3] (a1 undefined by construction)
                "acceleration": {"type": "array", "items": {"type": ["number", "null"]}},
                "trend": {"type": "string", "enum": ["increasing", "decreasing", "stable"]},
                "trend_slope": {"type": "number"},
            },
        },
        "quality": {
            "type": "object",
            "required": ["n_available_steps", "n_expected_steps", "input_ok", "coherence_proxy"],
            "properties": {
                "n_available_steps": {"type": "integer", "minimum": 0},
                "n_expected_steps": {"const": 12},
                "input_ok": {"type": "boolean"},
                # Monitoring V2 does NOT produce coherence; a future InSAR/data
                # provider must supply it. Null here means "not provided",
                # never a fabricated value.
                "coherence_proxy": {"type": ["number", "null"]},
                "notes": {"type": "array", "items": {"type": "string"}},
            },
        },
        "usage": {
            "type": "object",
            "required": ["used_as_prediction_model_input", "used_as_decision_support"],
            "properties": {
                # HARD CONSTRAINT for V1 integration: monitoring is never a
                # Prediction V1 model input.
                "used_as_prediction_model_input": {"const": False},
                "used_as_decision_support": {"type": "boolean"},
            },
        },
    },
}

# ---------------------------------------------------------------------------
# 3. Prediction -> Alert
# ---------------------------------------------------------------------------
# The Prediction score is a risk-ranking score, NOT a calibrated probability.

PREDICTION_ALERT_SCHEMA = {
    "schema_id": "landslideguard.prediction_alert",
    "version": "1.0",
    "type": "object",
    "required": ["schema", "generated_at", "site_id", "prediction", "model", "monitoring_context"],
    "additionalProperties": True,
    "properties": {
        "schema": {"const": "landslideguard.prediction_alert/1.0"},
        "generated_at": {"type": "string"},
        "site_id": {"type": ["string", "null"]},
        "event_time_utc": {"type": ["string", "null"]},
        "prediction": {
            "type": "object",
            "required": ["score", "score_kind", "threshold", "flag"],
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                # Pinned: the raw XGBoost score is a ranking, not a probability.
                "score_kind": {"const": "risk_ranking_not_calibrated_probability"},
                "threshold": {"type": "number"},
                "flag": {"type": ["string", "null"], "enum": ["alert", "no_alert", None]},
            },
        },
        "model": {
            "type": "object",
            "required": ["name", "version"],
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "seed": {"type": ["integer", "null"]},
            },
        },
        "monitoring_context": {
            "type": "object",
            "required": ["used_as_model_input", "used_as_decision_support"],
            "properties": {
                "monitoring_decision_support_ref": {"type": ["string", "null"]},
                # Mirror of the monitoring-side constraint.
                "used_as_model_input": {"const": False},
                "used_as_decision_support": {"type": "boolean"},
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}

# ---------------------------------------------------------------------------
# 4. Integrated result (Phase 3)
# ---------------------------------------------------------------------------
# Composite envelope that COMPOSES the three contracts above (it does not
# duplicate their field definitions). Each stage carries a status; the embedded
# payloads are validated by their own schemas. `integration_status` is SUCCESS
# only when every required stage succeeded.

_STAGE_STATUS = {"type": "string", "enum": ["success", "failed", "skipped"]}

INTEGRATED_RESULT_SCHEMA = {
    "schema_id": "landslideguard.integrated_result",
    "version": "1.0",
    "type": "object",
    "required": ["schema", "generated_at", "site_id", "integration_status",
                 "detection", "monitoring", "prediction"],
    "additionalProperties": True,
    "properties": {
        "schema": {"const": "landslideguard.integrated_result/1.0"},
        "generated_at": {"type": "string"},
        "site_id": {"type": ["string", "null"]},
        "integration_status": {"type": "string", "enum": ["success", "failed", "partial"]},
        # Phase-8 operation metadata (optional -> Phase-3 results still validate).
        "operation_id": {"type": ["string", "null"]},
        "operation_started_at": {"type": ["string", "null"]},
        "operation_completed_at": {"type": ["string", "null"]},
        "provenance": {"type": ["object", "null"]},
        "detection": {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": _STAGE_STATUS,
                "feature": {"type": ["object", "null"]},   # detection_monitoring feature
                "error": {"type": ["object", "null"]},
            },
        },
        "monitoring": {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": _STAGE_STATUS,
                "decision_support": {"type": ["object", "null"]},  # monitoring_decision_support doc
                "error": {"type": ["object", "null"]},
            },
        },
        "prediction": {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": _STAGE_STATUS,
                "alert": {"type": ["object", "null"]},   # prediction_alert doc
                "error": {"type": ["object", "null"]},
            },
        },
    },
}

SCHEMAS = {
    "detection_monitoring": DETECTION_MONITORING_SCHEMA,
    "monitoring_decision_support": MONITORING_DECISION_SUPPORT_SCHEMA,
    "prediction_alert": PREDICTION_ALERT_SCHEMA,
    "integrated_result": INTEGRATED_RESULT_SCHEMA,
}
