"""Operational single-location prediction entry point.

    predict_location(latitude, longitude, event_time)
        -> rainfall (T-14..T-1) + terrain
        -> existing PredictionFeatureBuilder (EXACT 26 features)
        -> existing frozen LandslideRiskPredictor
        -> risk-ranking score + alert flag + full provenance

This wraps — never replaces — the frozen builder and predictor. Monitoring
outputs are not involved. The score is a risk ranking, not a calibrated
probability; the threshold and score_kind come from the frozen model metadata.

Two wiring modes:
  * offline / reference : Phase-2 reference IMERG CSVs + local SRTM tiles
                          (deterministic, no network)
  * live remote         : IMERGFinalV07LiveProvider + SRTM30mLiveTerrainProvider
                          (real NASA Earthdata; needs credentials)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..providers import (
    IMERGFinalV07ReferenceProvider,
    IMERGFinalV07LiveProvider,
    SRTM30mTerrainProvider,
    SRTM30mLiveTerrainProvider,
)
from ..providers.base import RainfallProvider, TerrainProvider, coerce_event_time
from .feature_builder import PredictionFeatureBuilder, FROZEN_FEATURE_ORDER

# Frozen locations (consistent with Phase 2 / Phase 3).
_CURRENT_DIR = Path(__file__).parent.resolve()
_BASE_DIR = _CURRENT_DIR.parent.parent.parent.parent
_PRED_DIR = _BASE_DIR / "LandslideGuard_Prediction"
_MODEL_DIR = _PRED_DIR / "models" / "prediction_v1"
_POS_DAILY = _PRED_DIR / "imerg_targeted_download" / "extracted" / "glc_event_daily_rainfall.csv"
_CTRL_DAILY = (_PRED_DIR / "prediction_dataset" / "imerg_targeted_download"
               / "control_imerg_extraction" / "control_daily_rainfall.csv")
_TILES = _PRED_DIR / "prediction_dataset" / "terrain_context" / "srtm_30m" / "tiles"
_DOWNLOADS = _PRED_DIR / "prediction_dataset" / "terrain_context" / "srtm_30m" / "downloads"

_DEFAULT_CACHE = _BASE_DIR / "landslideguard_integration" / "cache"


def _load_frozen_predictor():
    import sys
    src = str(_PRED_DIR / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from prediction_v1 import LandslideRiskPredictor
    return LandslideRiskPredictor.from_dir(_MODEL_DIR)


class LivePredictionService:
    """Wires providers -> frozen feature builder -> frozen predictor."""

    def __init__(self, rainfall_provider: RainfallProvider,
                 terrain_provider: TerrainProvider, predictor=None,
                 mode: str = "unspecified"):
        self.builder = PredictionFeatureBuilder(rainfall_provider, terrain_provider)
        self.predictor = predictor or _load_frozen_predictor()
        self.mode = mode

    def predict_location(self, latitude: float, longitude: float, event_time) -> dict:
        event_dt = coerce_event_time(event_time)

        # Steps 1-4: validate + resolve rainfall/terrain + build EXACT 26 features.
        pf = self.builder.build(latitude, longitude, event_dt)
        row = pf.as_row_dict()
        assert len(row) == 26 and list(row) == list(FROZEN_FEATURE_ORDER)

        # Step 5: frozen prediction.
        score = float(self.predictor.predict_proba(row)[0])
        threshold = float(self.predictor.threshold)
        score_kind = str(getattr(self.predictor, "calibration_method", ""))
        # Preserve the frozen score semantics: a raw XGBoost score is a ranking.
        score_kind_label = "risk_ranking_not_calibrated_probability"
        flag = "alert" if score >= threshold else "no_alert"
        meta = getattr(self.predictor, "metadata", {})

        prov = pf.provenance
        return {
            "schema": "landslideguard.location_prediction/1.0",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "latitude": prov["latitude"],
            "longitude": prov["longitude"],
            "event_time_utc": prov["event_time_utc"],
            "mode": self.mode,
            "features": row,
            "risk_score": score,
            "threshold": threshold,
            "prediction": flag,
            "score_kind": score_kind_label,
            "calibration_method": score_kind,
            "provenance": {
                "rainfall_source": prov.get("rainfall_provider"),
                "rainfall_product": prov.get("rainfall_product"),
                "rainfall_version": prov.get("rainfall_version"),
                "rainfall_run": getattr(self.builder.rainfall_provider, "run", None),
                "rainfall_units": "mm/day",
                "rainfall_resolution": prov.get("rainfall_resolution"),
                "rainfall_window": prov.get("rainfall_dates_used"),
                "rainfall_extraction_method": prov.get("rainfall_extraction_method"),
                "event_day_excluded": prov.get("event_day_excluded"),
                "terrain_source": prov.get("terrain_provider"),
                "terrain_product": prov.get("terrain_dataset_version"),
                "terrain_version": prov.get("terrain_dataset_version"),
                "terrain_tile": prov.get("terrain_tile"),
                "terrain_resolution": prov.get("terrain_resolution"),
                "terrain_method": prov.get("terrain_method"),
                "feature_contract_version": prov.get("feature_contract_version"),
                "model_name": meta.get("model_name", "prediction_v1"),
                "model_version": meta.get("model_version", "prediction_v1"),
            },
        }


def build_offline_service() -> LivePredictionService:
    """Deterministic reference wiring (no network): Phase-2 reference IMERG +
    local SRTM tiles."""
    rain = IMERGFinalV07ReferenceProvider([_POS_DAILY, _CTRL_DAILY], coord_round=5)
    terr = SRTM30mTerrainProvider(_TILES, _DOWNLOADS)
    return LivePredictionService(rain, terr, mode="offline_reference")


# Conservative disk-safety threshold for live downloads (configurable).
MIN_FREE_DISK_GB = 5.0


def build_live_service(cache_dir: str | Path = _DEFAULT_CACHE,
                       *, min_free_gb: float = MIN_FREE_DISK_GB,
                       cache_manager: Optional[object] = None,
                       manage_cache: bool = True) -> LivePredictionService:
    """Live NASA Earthdata wiring (needs credentials). Enforces a conservative
    minimum-free-disk threshold before any download and, by default, attaches the
    Phase-7 bounded CacheManager so downloads make room within policy or refuse."""
    min_free_mb = float(min_free_gb) * 1024.0
    if cache_manager is None and manage_cache:
        from ..cache import CacheManager, CachePolicy
        cache_manager = CacheManager(cache_dir, CachePolicy(min_free_disk_gb=min_free_gb))
    rain = IMERGFinalV07LiveProvider(cache_dir, min_free_mb=min_free_mb, cache_manager=cache_manager)
    terr = SRTM30mLiveTerrainProvider(cache_dir, min_free_mb=min_free_mb, cache_manager=cache_manager)
    return LivePredictionService(rain, terr, mode="live_remote")


def predict_location(latitude: float, longitude: float, event_time, *,
                     mode: str = "offline", cache_dir: str | Path = _DEFAULT_CACHE) -> dict:
    """Convenience one-call entry point. mode: 'offline' | 'live'."""
    svc = build_offline_service() if mode == "offline" else build_live_service(cache_dir)
    return svc.predict_location(latitude, longitude, event_time)


__all__ = [
    "LivePredictionService", "predict_location",
    "build_offline_service", "build_live_service",
]
