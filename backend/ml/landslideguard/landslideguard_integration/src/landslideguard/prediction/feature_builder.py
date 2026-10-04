"""Assemble the EXACT 26 Prediction V1 features from providers.

(latitude, longitude, event_time_utc)
    -> RainfallProvider  -> 23 rainfall features
    -> TerrainProvider   ->  3 terrain features
    -> validated 26-feature vector in the frozen order

The feature vector never contains metadata (site_id, lat, lon, event_time),
Monitoring outputs, or Detection outputs. Provenance is returned SEPARATELY.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..providers.base import (
    RainfallProvider,
    TerrainProvider,
    RAIN_LAG_NAMES,
    RAIN_AGG_NAMES,
    validate_coordinates,
    coerce_event_time,
)
from ..providers.errors import (
    FeatureGenerationError,
    InvalidFeatureVectorError,
    MissingTerrainError,
)

FEATURE_CONTRACT_VERSION = "prediction_v1/26features/1.0"

# The immutable feature order. Identity does NOT rely on dict insertion order.
FROZEN_FEATURE_ORDER: tuple[str, ...] = RAIN_LAG_NAMES + RAIN_AGG_NAMES + (
    "elevation_m", "slope_degrees", "aspect_degrees",
)
assert len(FROZEN_FEATURE_ORDER) == 26, "feature contract must be exactly 26"

_FEATURE_SET = frozenset(FROZEN_FEATURE_ORDER)
# Names that must NEVER appear as model features.
_FORBIDDEN = frozenset({
    "site_id", "latitude", "longitude", "event_time_utc", "event_date",
    "sample_id", "source_id", "sample_type", "label",
    # Monitoring
    "displacement", "velocity", "acceleration", "trend", "trend_slope",
    "pred_disp_t1", "pred_disp_t2", "pred_disp_t3",
    # Detection
    "detection_confidence", "area_m2", "prob_mean", "prob_max",
})


@dataclass
class PredictionFeatures:
    """A validated 26-feature vector plus separate provenance."""
    features: dict[str, float]
    provenance: dict = field(default_factory=dict)

    def as_ordered_list(self) -> list[float]:
        return [self.features[name] for name in FROZEN_FEATURE_ORDER]

    def as_row_dict(self) -> dict[str, float]:
        """Feature dict rebuilt in the frozen order (no metadata)."""
        return {name: self.features[name] for name in FROZEN_FEATURE_ORDER}


class PredictionFeatureBuilder:
    def __init__(self, rainfall_provider: RainfallProvider, terrain_provider: TerrainProvider):
        self.rainfall_provider = rainfall_provider
        self.terrain_provider = terrain_provider

    def build(self, latitude: float, longitude: float, event_time_utc) -> PredictionFeatures:
        lat, lon = validate_coordinates(latitude, longitude)
        event_dt = coerce_event_time(event_time_utc)

        # --- rainfall (23) ---
        rain_feats, rain_prov = self.rainfall_provider.get_prediction_v1_rainfall_features(
            lat, lon, event_dt
        )

        # --- terrain (3) ---
        terr = self.terrain_provider.get_terrain(lat, lon)
        terrain_feats = {
            "elevation_m": terr.elevation_m,
            "slope_degrees": terr.slope_degrees,
            "aspect_degrees": terr.aspect_degrees,
        }

        merged = {**rain_feats, **terrain_feats}
        self._validate_feature_vector(merged)

        provenance = {
            "feature_contract_version": FEATURE_CONTRACT_VERSION,
            "latitude": lat,
            "longitude": lon,
            "event_time_utc": event_dt.isoformat(),
            **rain_prov,
            "terrain_provider": terr.source and self.terrain_provider.provider_name,
            "terrain_dataset_version": terr.dataset_version,
            "terrain_resolution": terr.resolution,
            "terrain_tile": terr.tile,
            "terrain_method": terr.extra.get("method"),
            "terrain_aspect_convention": terr.extra.get("aspect_convention"),
        }
        # Only the ordered 26 features go into the vector.
        ordered = {name: float(merged[name]) for name in FROZEN_FEATURE_ORDER}
        return PredictionFeatures(features=ordered, provenance=provenance)

    @staticmethod
    def _validate_feature_vector(feats: dict[str, float]) -> None:
        keys = set(feats)
        missing = _FEATURE_SET - keys
        if missing:
            raise InvalidFeatureVectorError(f"missing features: {sorted(missing)}")
        extra = keys - _FEATURE_SET
        if extra:
            raise InvalidFeatureVectorError(f"unexpected features: {sorted(extra)}")
        forbidden = keys & _FORBIDDEN
        if forbidden:
            raise InvalidFeatureVectorError(f"forbidden features present: {sorted(forbidden)}")
        if len(keys) != 26:
            raise InvalidFeatureVectorError(f"expected 26 features, got {len(keys)}")
        for name in FROZEN_FEATURE_ORDER:
            v = feats[name]
            if v is None or not math.isfinite(float(v)):
                raise InvalidFeatureVectorError(f"feature {name} is non-finite: {v}", feature=name)


__all__ = [
    "PredictionFeatureBuilder", "PredictionFeatures",
    "FROZEN_FEATURE_ORDER", "FEATURE_CONTRACT_VERSION",
]
