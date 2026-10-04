"""Provider interfaces + the Prediction V1 rainfall temporal contract.

The rainfall temporal contract is defined ONCE here and reused by every
concrete rainfall provider so the T-1..T-14 window, event-day exclusion, and
aggregate definitions cannot drift between sources.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from .errors import (
    InvalidCoordinatesError,
    InvalidEventTimeError,
    InsufficientRainfallHistoryError,
    MissingRainfallError,
)

# Prediction V1 rainfall contract constants.
N_LAGS = 14                      # rain_t1 .. rain_t14
AGG_WINDOWS = (3, 7, 14)         # 3d / 7d / 14d aggregates
RAIN_LAG_NAMES = tuple(f"rain_t{i}" for i in range(1, N_LAGS + 1))
RAIN_AGG_NAMES = tuple(
    f"rain_{stat}_{w}d" for stat in ("sum", "max", "mean") for w in AGG_WINDOWS
)  # rain_sum_3d, rain_sum_7d, rain_sum_14d, rain_max_3d, ... rain_mean_14d


@dataclass
class TerrainResult:
    elevation_m: float
    slope_degrees: float
    aspect_degrees: float
    source: str
    dataset_version: str
    resolution: str
    tile: str
    extra: dict = field(default_factory=dict)


def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError) as e:
        raise InvalidCoordinatesError(f"non-numeric coordinates: {e}",
                                      latitude=latitude, longitude=longitude) from e
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise InvalidCoordinatesError("non-finite coordinates",
                                      latitude=lat, longitude=lon)
    if not (-90.0 <= lat <= 90.0):
        raise InvalidCoordinatesError(f"latitude out of range: {lat}", latitude=lat)
    if not (-180.0 <= lon <= 180.0):
        raise InvalidCoordinatesError(f"longitude out of range: {lon}", longitude=lon)
    return lat, lon


def coerce_event_time(event_time_utc) -> datetime:
    """Accept a datetime or ISO-8601 string; return a tz-aware UTC datetime."""
    if isinstance(event_time_utc, datetime):
        dt = event_time_utc
    elif isinstance(event_time_utc, date):
        dt = datetime(event_time_utc.year, event_time_utc.month, event_time_utc.day)
    elif isinstance(event_time_utc, str):
        s = event_time_utc.strip()
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                dt = datetime.strptime(s, "%Y-%m-%d")
            except ValueError as e:
                raise InvalidEventTimeError(f"unparseable event_time_utc: {s!r}") from e
    else:
        raise InvalidEventTimeError(f"unsupported event_time type: {type(event_time_utc).__name__}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def prediction_v1_lag_dates(event_time_utc) -> list[date]:
    """Return the T-1 .. T-14 calendar dates (event day T EXCLUDED).

    Index 0 corresponds to rain_t1 (T-1, most recent); index 13 to rain_t14
    (T-14, oldest).
    """
    dt = coerce_event_time(event_time_utc)
    t = dt.date()
    return [t - timedelta(days=n) for n in range(1, N_LAGS + 1)]


def rainfall_features_from_lags(lag_values: list[float]) -> dict[str, float]:
    """Build the 23 rainfall features from ordered lag values [rain_t1..rain_t14]."""
    if len(lag_values) != N_LAGS:
        raise InsufficientRainfallHistoryError(
            f"expected {N_LAGS} lag values, got {len(lag_values)}")
    for i, v in enumerate(lag_values, start=1):
        if v is None or not math.isfinite(float(v)):
            raise MissingRainfallError(f"rain_t{i} is missing/non-finite", lag_index=i)

    feats: dict[str, float] = {name: float(v) for name, v in zip(RAIN_LAG_NAMES, lag_values)}
    # Aggregates over the most-recent w days: rain_t1 .. rain_t{w}.
    for w in AGG_WINDOWS:
        window = [float(v) for v in lag_values[:w]]
        feats[f"rain_sum_{w}d"] = float(sum(window))
        feats[f"rain_max_{w}d"] = float(max(window))
        feats[f"rain_mean_{w}d"] = float(sum(window) / w)
    return feats


class RainfallProvider(ABC):
    """Interface: daily rainfall + the Prediction V1 rainfall feature block."""

    #: Provenance, filled by concrete providers.
    provider_name: str = "abstract"
    product: str = "unspecified"
    version: str = "unspecified"
    resolution: str = "unspecified"
    extraction_method: str = "unspecified"

    @abstractmethod
    def get_daily_rainfall(self, latitude: float, longitude: float,
                           start_date: date, end_date: date) -> dict[date, float]:
        """Return {date: precip_mm} for each day in [start_date, end_date].
        Must raise MissingRainfallError for any unavailable date (never zero-fill)."""

    def get_prediction_v1_rainfall_features(
        self, latitude: float, longitude: float, event_time_utc
    ) -> tuple[dict[str, float], dict]:
        """Return (23 rainfall features, provenance). Event day T excluded."""
        lat, lon = validate_coordinates(latitude, longitude)
        lag_dates = prediction_v1_lag_dates(event_time_utc)
        start, end = min(lag_dates), max(lag_dates)
        daily = self.get_daily_rainfall(lat, lon, start, end)

        lag_values = []
        for i, d in enumerate(lag_dates, start=1):
            if d not in daily:
                raise MissingRainfallError(
                    f"no rainfall for {d.isoformat()} (rain_t{i})",
                    date=d.isoformat(), lag_index=i)
            lag_values.append(daily[d])

        feats = rainfall_features_from_lags(lag_values)
        provenance = {
            "rainfall_provider": self.provider_name,
            "rainfall_product": self.product,
            "rainfall_version": self.version,
            "rainfall_resolution": self.resolution,
            "rainfall_extraction_method": self.extraction_method,
            "rainfall_dates_used": [d.isoformat() for d in lag_dates],
            "event_day_excluded": True,
        }
        return feats, provenance


class TerrainProvider(ABC):
    """Interface: terrain features at a point."""

    provider_name: str = "abstract"
    dataset_version: str = "unspecified"
    resolution: str = "unspecified"

    @abstractmethod
    def get_terrain(self, latitude: float, longitude: float) -> TerrainResult:
        """Return elevation_m / slope_degrees / aspect_degrees + provenance.
        Must raise MissingTerrainError if terrain cannot be obtained."""


__all__ = [
    "N_LAGS", "AGG_WINDOWS", "RAIN_LAG_NAMES", "RAIN_AGG_NAMES",
    "TerrainResult", "RainfallProvider", "TerrainProvider",
    "validate_coordinates", "coerce_event_time",
    "prediction_v1_lag_dates", "rainfall_features_from_lags",
]
