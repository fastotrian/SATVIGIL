"""Operational feature providers for Prediction V1."""
from .base import (
    RainfallProvider,
    TerrainProvider,
    TerrainResult,
    RAIN_LAG_NAMES,
    RAIN_AGG_NAMES,
    prediction_v1_lag_dates,
    rainfall_features_from_lags,
)
from .rainfall_imerg import (
    IMERGFinalV07NetCDFProvider,
    IMERGFinalV07ReferenceProvider,
    IMERGFinalV07LiveProvider,
)
from .terrain_srtm import (
    SRTM30mTerrainProvider,
    SRTM30mLiveTerrainProvider,
    tile_name,
    validate_hgt_zip,
)
from .download import DiskSpaceError, free_mb, ensure_free_space, cache_stats
from .errors import (
    FeatureGenerationError,
    InvalidCoordinatesError,
    InvalidEventTimeError,
    MissingRainfallError,
    MissingTerrainError,
    InsufficientRainfallHistoryError,
    ProviderError,
    AuthenticationError,
    InvalidFeatureVectorError,
)

__all__ = [
    "RainfallProvider", "TerrainProvider", "TerrainResult",
    "RAIN_LAG_NAMES", "RAIN_AGG_NAMES",
    "prediction_v1_lag_dates", "rainfall_features_from_lags",
    "IMERGFinalV07NetCDFProvider", "IMERGFinalV07ReferenceProvider",
    "IMERGFinalV07LiveProvider",
    "SRTM30mTerrainProvider", "SRTM30mLiveTerrainProvider", "tile_name",
    "validate_hgt_zip",
    "DiskSpaceError", "free_mb", "ensure_free_space", "cache_stats",
    "FeatureGenerationError", "InvalidCoordinatesError", "InvalidEventTimeError",
    "MissingRainfallError", "MissingTerrainError", "InsufficientRainfallHistoryError",
    "ProviderError", "AuthenticationError", "InvalidFeatureVectorError",
]
