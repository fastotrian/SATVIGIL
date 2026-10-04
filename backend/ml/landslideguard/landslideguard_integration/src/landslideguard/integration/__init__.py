"""Phase-3 controlled end-to-end integration."""
from .fixtures import (
    DetectionFixture,
    controlled_detection_fixture,
    CONTROLLED_MONITORING_HISTORY,
    CONTROLLED_MONITORING_META,
    CONTROLLED_SOURCE,
)
from .detection_adapter import adapt_detection_to_monitoring
from .pipeline import (
    IntegrationPipeline,
    build_default_pipeline,
    MONITORING_FEATURE_NAMES,
    MONITORING_PREDICTION_FEATURE_OVERLAP,
)
from .verification_locations import (
    VerificationLocation,
    PHASE6_LOCATIONS,
    haversine_km,
    pairwise_distances_km,
)
from .orchestrator import OperationalOrchestrator

__all__ = [
    "DetectionFixture",
    "controlled_detection_fixture",
    "CONTROLLED_MONITORING_HISTORY",
    "CONTROLLED_MONITORING_META",
    "CONTROLLED_SOURCE",
    "adapt_detection_to_monitoring",
    "IntegrationPipeline",
    "build_default_pipeline",
    "MONITORING_FEATURE_NAMES",
    "MONITORING_PREDICTION_FEATURE_OVERLAP",
    "VerificationLocation",
    "PHASE6_LOCATIONS",
    "haversine_km",
    "pairwise_distances_km",
    "OperationalOrchestrator",
]
