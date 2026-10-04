"""Structured failure taxonomy for operational feature generation.

Every failure carries an explicit `code`. Feature generation NEVER silently
substitutes zeros or imputes missing provider data — it raises one of these.
"""
from __future__ import annotations


class FeatureGenerationError(Exception):
    """Base class for all feature-generation failures."""
    code = "FEATURE_GENERATION_ERROR"

    def __init__(self, message: str = "", **context):
        super().__init__(message)
        self.context = context

    def to_dict(self) -> dict:
        return {"code": self.code, "message": str(self), "context": self.context}


class InvalidCoordinatesError(FeatureGenerationError):
    code = "INVALID_COORDINATES"


class InvalidEventTimeError(FeatureGenerationError):
    code = "INVALID_EVENT_TIME"


class MissingRainfallError(FeatureGenerationError):
    code = "MISSING_RAINFALL"


class MissingTerrainError(FeatureGenerationError):
    code = "MISSING_TERRAIN"


class InsufficientRainfallHistoryError(FeatureGenerationError):
    code = "INSUFFICIENT_RAINFALL_HISTORY"


class ProviderError(FeatureGenerationError):
    code = "PROVIDER_ERROR"


class AuthenticationError(ProviderError):
    code = "AUTHENTICATION_FAILED"


class InvalidFeatureVectorError(FeatureGenerationError):
    code = "INVALID_FEATURE_VECTOR"


__all__ = [
    "FeatureGenerationError",
    "InvalidCoordinatesError",
    "InvalidEventTimeError",
    "MissingRainfallError",
    "MissingTerrainError",
    "InsufficientRainfallHistoryError",
    "ProviderError",
    "AuthenticationError",
    "InvalidFeatureVectorError",
]
