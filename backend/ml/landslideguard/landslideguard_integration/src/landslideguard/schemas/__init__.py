"""Versioned integration contract schemas + a dependency-free validator.

Three wire contracts (authoritative source: integration_contract_audit.md):

    1. detection_monitoring       Detection -> Monitoring
    2. monitoring_decision_support Monitoring -> Decision Support
    3. prediction_alert           Prediction -> Alert

Design rules enforced by these schemas:

  * Monitoring output is NEVER a Prediction V1 model input. The
    monitoring_decision_support schema pins `used_as_model_input` to the
    constant `false`.
  * Displacement units are `unresolved` until independently verified.
  * The Prediction score is a risk-ranking score, not a calibrated
    probability (`score_kind` is constrained accordingly).
  * Detection confidence is explicitly non-calibrated.
"""
from .contracts import (
    DETECTION_MONITORING_SCHEMA,
    MONITORING_DECISION_SUPPORT_SCHEMA,
    PREDICTION_ALERT_SCHEMA,
    INTEGRATED_RESULT_SCHEMA,
    SCHEMAS,
)
from .validator import SchemaError, validate

__all__ = [
    "DETECTION_MONITORING_SCHEMA",
    "MONITORING_DECISION_SUPPORT_SCHEMA",
    "PREDICTION_ALERT_SCHEMA",
    "INTEGRATED_RESULT_SCHEMA",
    "SCHEMAS",
    "SchemaError",
    "validate",
]
