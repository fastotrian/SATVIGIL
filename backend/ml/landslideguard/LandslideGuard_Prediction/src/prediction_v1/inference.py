"""Standalone inference for LandslideGuard Prediction V1.

Loads the frozen XGBoost classifier, its preprocessing pipeline, and the
prediction-time metadata (feature order, operating threshold), then exposes a
small predictor API that takes a pandas DataFrame (or a dict / iterable of
dicts) of rainfall + terrain features and returns positive-class probability
and the thresholded prediction.

The output is a landslide-event-vs-control score from the training problem.
Per the Prediction V1 spec, the raw XGBoost score is NOT a calibrated absolute
probability of landslide occurrence unless the loaded model was explicitly
calibrated (see `LandslideRiskPredictor.calibration_method`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Union

import joblib
import numpy as np
import pandas as pd


PathLike = Union[str, Path]

RAIN_LAG_FEATURES: list[str] = [f"rain_t{i}" for i in range(1, 15)]
RAIN_AGG_FEATURES: list[str] = [
    "rain_sum_3d",  "rain_sum_7d",  "rain_sum_14d",
    "rain_max_3d",  "rain_max_7d",  "rain_max_14d",
    "rain_mean_3d", "rain_mean_7d", "rain_mean_14d",
]
TERRAIN_FEATURES: list[str] = ["elevation_m", "slope_degrees", "aspect_degrees"]
FEATURES: list[str] = RAIN_LAG_FEATURES + RAIN_AGG_FEATURES + TERRAIN_FEATURES


class LandslideRiskPredictor:
    """Prediction V1 inference wrapper.

    Load with `LandslideRiskPredictor.from_dir(models_dir)`, then call
    `predict_proba(...)` for scores in [0, 1] or `predict(...)` for the
    thresholded 0/1 label using the frozen operating threshold.

    Attributes
    ----------
    features : list[str]
        The 26 feature names, in the exact order the preprocessor was fit on.
    threshold : float
        Frozen operating threshold (learned on validation only).
    calibration_method : str
        Which calibrator (if any) was adopted. When this is "none (raw scores
        retained)" or similar, do not describe the score as a calibrated
        probability.
    """

    N_FEATURES = 26

    def __init__(self, model: Any, preprocessor: Any, metadata: Mapping[str, Any]) -> None:
        self._model = model
        self._pre = preprocessor
        self.metadata: dict = dict(metadata)

        self.features: list[str] = list(self.metadata["features"])
        self.threshold: float = float(self.metadata["final_threshold"])
        self.calibration_method: str = str(self.metadata.get("calibration_method", "none"))
        self.model_kind: str = str(
            self.metadata.get("model_kind", self.metadata.get("model_name", "unknown"))
        )

        if len(self.features) != self.N_FEATURES:
            raise ValueError(
                f"Prediction V1 feature contract requires {self.N_FEATURES} features; "
                f"metadata declares {len(self.features)}."
            )

    # ---------- constructors ----------

    @classmethod
    def from_dir(
        cls,
        model_dir: PathLike,
        *,
        model_file: str = "final_model.joblib",
        preprocessor_file: str = "preprocessing.joblib",
        metadata_file: str = "prediction_v1_metadata.json",
    ) -> "LandslideRiskPredictor":
        d = Path(model_dir)
        model = joblib.load(d / model_file)
        pre = joblib.load(d / preprocessor_file)
        metadata = json.loads((d / metadata_file).read_text(encoding="utf-8"))
        return cls(model=model, preprocessor=pre, metadata=metadata)

    # ---------- input coercion ----------

    def _coerce(
        self,
        x: Union[pd.DataFrame, Mapping[str, float], Iterable[Mapping[str, float]]],
    ) -> pd.DataFrame:
        if isinstance(x, pd.DataFrame):
            df = x
        elif isinstance(x, Mapping):
            df = pd.DataFrame([dict(x)])
        else:
            df = pd.DataFrame(list(x))

        missing = [f for f in self.features if f not in df.columns]
        if missing:
            raise ValueError(f"Input is missing required features: {missing}")

        # Enforce exact column order; drop anything else silently so metadata
        # columns (sample_id, latitude, ...) on the caller's frame don't leak
        # into the model input.
        return df[self.features].copy()

    # ---------- prediction ----------

    def predict_proba(self, x) -> np.ndarray:
        """Positive-class probability, one value per input row."""
        X = self._coerce(x)
        X_p = self._pre.transform(X)
        return self._model.predict_proba(X_p)[:, 1]

    def predict(self, x, threshold: float | None = None) -> np.ndarray:
        """Return 0/1 predictions at the frozen operating threshold."""
        t = self.threshold if threshold is None else float(threshold)
        return (self.predict_proba(x) >= t).astype(int)

    def predict_frame(
        self,
        df: pd.DataFrame,
        *,
        id_col: str | None = "sample_id",
        threshold: float | None = None,
    ) -> pd.DataFrame:
        """Return a dataframe with `y_prob` and `y_pred` columns.

        If `id_col` is present in `df`, it is preserved on the output for
        auditability.
        """
        proba = self.predict_proba(df)
        t = self.threshold if threshold is None else float(threshold)
        out = pd.DataFrame({"y_prob": proba, "y_pred": (proba >= t).astype(int)})
        if id_col and id_col in df.columns:
            out.insert(0, id_col, df[id_col].values)
        return out

    def __repr__(self) -> str:
        return (
            f"LandslideRiskPredictor(model_kind={self.model_kind!r}, "
            f"threshold={self.threshold:.2f}, "
            f"calibration={self.calibration_method!r}, "
            f"n_features={len(self.features)})"
        )
