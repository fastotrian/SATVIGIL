"""Production inference wrapper for the FROZEN Monitoring V2 model.

Loads ONLY the frozen artifacts:
    monitoring_v2_tcn_best.pth       (weights + embedded config)
    monitoring_v2_config.json        (human-readable config; cross-checked)
    monitoring_v2_scaler.json        (train-only z-score parameters)

Nothing is retrained, re-saved, or regenerated. The scaler is loaded, never
recomputed. The SimpleTCNV2 architecture is reproduced byte-for-byte from the
training definition (verified against the checkpoint state_dict shapes and the
899-parameter count).

Units: displacement units are UNRESOLVED. This wrapper never assigns mm/day or
mm/day^2. Coherence is NOT produced by this model; the quality block leaves
`coherence_proxy = None` for a future InSAR/data provider to fill.

Monitoring output is decision-support only. It is NEVER a Prediction V1 model
input — the emitted handoff pins `used_as_prediction_model_input = False`.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import torch
import torch.nn as nn

INPUT_WINDOW = 12
FORECAST_HORIZON = 3
DISPLACEMENT_UNITS = "unresolved"
_EXPECTED_PARAM_COUNT = 899
_TREND_EPS = 1e-6


class MonitoringInputError(ValueError):
    """Raised when a displacement history fails validation."""


# ---------------------------------------------------------------------------
# Exact architecture (reproduced from monitoring_v2_development.ipynb).
# ---------------------------------------------------------------------------

class CausalConv1d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int,
                 kernel_size: int, dilation: int = 1):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(
            in_channels, out_channels,
            kernel_size=kernel_size, dilation=dilation, padding=self.padding,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        if self.padding > 0:
            x = x[:, :, : -self.padding]
        return x


class SimpleTCNV2(nn.Module):
    def __init__(self, input_channels: int = 1, hidden_channels: int = 16,
                 forecast_horizon: int = 3, dropout: float = 0.1):
        super().__init__()
        self.conv1 = CausalConv1d(input_channels, hidden_channels, kernel_size=3, dilation=1)
        self.conv2 = CausalConv1d(hidden_channels, hidden_channels, kernel_size=3, dilation=2)
        self.activation = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_channels, forecast_horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = self.conv2(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = x[:, :, -1]
        return self.head(x)


@dataclass(frozen=True)
class MonitoringForecast:
    t1: float
    t2: float
    t3: float

    def as_list(self) -> list[float]:
        return [self.t1, self.t2, self.t3]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class MonitoringForecaster:
    """Frozen Monitoring V2 inference.

    Construct with `from_dir(monitoring_dir)`, then call:
        predict_forecast(history)  -> MonitoringForecast (raw displacement)
        derive_summary(history, forecast) -> dict of kinematics
        build_decision_support(history, site_id=...) -> handoff dict
    """

    def __init__(self, model: nn.Module, train_mean: float, train_std: float,
                 config: dict, checkpoint_path: Path, scaler_path: Path,
                 config_path: Optional[Path]):
        self._model = model
        self.train_mean = float(train_mean)
        self.train_std = float(train_std)
        self.config = config
        self.checkpoint_path = Path(checkpoint_path)
        self.scaler_path = Path(scaler_path)
        self.config_path = Path(config_path) if config_path else None

        if self.train_std <= 0:
            raise ValueError("train_std must be positive")

        self.param_count = sum(p.numel() for p in self._model.parameters())
        if self.param_count != _EXPECTED_PARAM_COUNT:
            raise ValueError(
                f"Unexpected parameter count {self.param_count} "
                f"(expected {_EXPECTED_PARAM_COUNT}); architecture mismatch."
            )
        self._model.eval()

    # ---- construction ----

    @classmethod
    def from_dir(
        cls,
        monitoring_dir: str | Path,
        *,
        checkpoint_file: str = "models/monitoring_v2_tcn_best.pth",
        scaler_file: str = "outputs/monitoring_v2_scaler.json",
        config_file: str = "outputs/monitoring_v2_config.json",
    ) -> "MonitoringForecaster":
        base = Path(monitoring_dir)
        ckpt_path = base / checkpoint_file
        scaler_path = base / scaler_file
        config_path = base / config_file

        if not ckpt_path.exists():
            raise FileNotFoundError(f"Monitoring V2 checkpoint not found: {ckpt_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"Monitoring V2 scaler not found: {scaler_path}")

        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        if "model_state_dict" not in ckpt:
            raise ValueError("Checkpoint missing 'model_state_dict'.")

        # Build architecture strictly from the checkpoint's own recorded config.
        model = SimpleTCNV2(
            input_channels=int(ckpt.get("input_channels", 1)),
            hidden_channels=int(ckpt.get("hidden_channels", 16)),
            forecast_horizon=int(ckpt.get("forecast_horizon", FORECAST_HORIZON)),
            dropout=float(ckpt.get("dropout", 0.1)),
        )
        model.load_state_dict(ckpt["model_state_dict"])

        # Scaler comes from the frozen scaler.json (not recomputed).
        scaler = json.loads(scaler_path.read_text(encoding="utf-8"))
        train_mean = float(scaler["train_mean"])
        train_std = float(scaler["train_std"])

        config = {}
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # Cross-check the checkpoint scaler against the config's scaler if present.
            cfg_norm = config.get("normalization", {})
            if "train_mean" in cfg_norm:
                if not math.isclose(float(cfg_norm["train_mean"]), train_mean, rel_tol=0, abs_tol=1e-9):
                    raise ValueError("Config train_mean disagrees with scaler.json.")
            if "train_std" in cfg_norm:
                if not math.isclose(float(cfg_norm["train_std"]), train_std, rel_tol=0, abs_tol=1e-9):
                    raise ValueError("Config train_std disagrees with scaler.json.")

        # Cross-check embedded checkpoint scaler too, if present.
        if "train_mean" in ckpt and not math.isclose(float(ckpt["train_mean"]), train_mean, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Checkpoint train_mean disagrees with scaler.json.")
        if "train_std" in ckpt and not math.isclose(float(ckpt["train_std"]), train_std, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Checkpoint train_std disagrees with scaler.json.")

        return cls(model, train_mean, train_std, config, ckpt_path, scaler_path,
                   config_path if config_path.exists() else None)

    # ---- input validation ----

    @staticmethod
    def _validate_history(history: Sequence[float]) -> np.ndarray:
        if isinstance(history, (str, bytes)):
            raise MonitoringInputError("history must be a sequence of numbers, not a string.")
        try:
            arr = np.asarray(history, dtype=np.float64)
        except (TypeError, ValueError) as e:
            raise MonitoringInputError(f"history is not numeric: {e}") from e
        if arr.ndim != 1:
            raise MonitoringInputError(f"history must be 1-D, got shape {arr.shape}.")
        if arr.shape[0] != INPUT_WINDOW:
            raise MonitoringInputError(
                f"history must have exactly {INPUT_WINDOW} values, got {arr.shape[0]}."
            )
        if not np.all(np.isfinite(arr)):
            raise MonitoringInputError("history contains non-finite values (NaN/Inf).")
        return arr

    # ---- inference ----

    def _predict_norm_batch(self, X_norm: np.ndarray) -> np.ndarray:
        """X_norm: (N, 12) normalized. Returns (N, 3) normalized predictions."""
        t = torch.tensor(X_norm, dtype=torch.float32).unsqueeze(1)
        with torch.no_grad():
            out = self._model(t).cpu().numpy()
        return out

    def predict_forecast(self, history: Sequence[float]) -> MonitoringForecast:
        """Forecast t+1, t+2, t+3 in RAW displacement units from a 12-value
        raw displacement history."""
        arr = self._validate_history(history)
        x_norm = (arr - self.train_mean) / self.train_std
        pred_norm = self._predict_norm_batch(x_norm.reshape(1, INPUT_WINDOW))[0]
        pred = pred_norm.astype(np.float64) * self.train_std + self.train_mean
        return MonitoringForecast(float(pred[0]), float(pred[1]), float(pred[2]))

    def predict_forecast_batch(self, histories: np.ndarray) -> np.ndarray:
        """histories: (N, 12) raw. Returns (N, 3) raw predictions. For
        verification / bulk use; per-row validation is the caller's job."""
        histories = np.asarray(histories, dtype=np.float64)
        if histories.ndim != 2 or histories.shape[1] != INPUT_WINDOW:
            raise MonitoringInputError(f"histories must be (N, {INPUT_WINDOW}).")
        x_norm = (histories - self.train_mean) / self.train_std
        pred_norm = self._predict_norm_batch(x_norm)
        return pred_norm.astype(np.float64) * self.train_std + self.train_mean

    # ---- derived kinematics (matches training-notebook Step 10/12 logic) ----

    def derive_summary(self, history: Sequence[float],
                       forecast: Optional[MonitoringForecast] = None) -> dict:
        arr = self._validate_history(history)
        if forecast is None:
            forecast = self.predict_forecast(arr)
        last_observed = float(arr[-1])
        t1, t2, t3 = forecast.t1, forecast.t2, forecast.t3

        v1 = t1 - last_observed
        v2 = t2 - t1
        v3 = t3 - t2
        # a1 is undefined by construction (needs two velocities) -> None
        a2 = v2 - v1
        a3 = v3 - v2

        slope = float(np.polyfit(np.array([1, 2, 3]), np.array([t1, t2, t3]), 1)[0])
        if slope > _TREND_EPS:
            trend = "increasing"
        elif slope < -_TREND_EPS:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "last_observed": last_observed,
            "velocity": [v1, v2, v3],
            "acceleration": [None, a2, a3],
            "trend": trend,
            "trend_slope": slope,
            "displacement_units": DISPLACEMENT_UNITS,
        }

    # ---- handoff builder (matches monitoring_decision_support schema) ----

    def build_decision_support(
        self,
        history: Sequence[float],
        *,
        site_id: Optional[str] = None,
        time_steps: Optional[Sequence[int]] = None,
        used_as_decision_support: bool = True,
        coherence_proxy: Optional[float] = None,
        quality_notes: Optional[list[str]] = None,
    ) -> dict:
        """Produce a monitoring_decision_support/1.0 payload.

        `coherence_proxy` defaults to None: Monitoring V2 does not produce
        coherence. Only a real InSAR/data provider may supply it.
        """
        arr = self._validate_history(history)
        forecast = self.predict_forecast(arr)
        summary = self.derive_summary(arr, forecast)

        return {
            "schema": "landslideguard.monitoring_decision_support/1.0",
            "generated_at": _utc_now_iso(),
            "site_id": site_id,
            "monitoring_model": "monitoring_v2",
            "input_window": INPUT_WINDOW,
            "forecast_horizon": FORECAST_HORIZON,
            "displacement_units": DISPLACEMENT_UNITS,
            "history": {
                "time_steps": list(time_steps) if time_steps is not None else None,
                "values": [float(v) for v in arr],
            },
            "forecast": {
                "t1": {"value": forecast.t1, "quantile_low": None, "quantile_high": None},
                "t2": {"value": forecast.t2, "quantile_low": None, "quantile_high": None},
                "t3": {"value": forecast.t3, "quantile_low": None, "quantile_high": None},
            },
            "derived": {
                "velocity": summary["velocity"],
                "acceleration": summary["acceleration"],
                "trend": summary["trend"],
                "trend_slope": summary["trend_slope"],
            },
            "quality": {
                "n_available_steps": int(arr.shape[0]),
                "n_expected_steps": INPUT_WINDOW,
                "input_ok": True,
                "coherence_proxy": coherence_proxy,  # None unless a provider supplies it
                "notes": quality_notes or [
                    "Displacement units unresolved.",
                    "Coherence not produced by Monitoring V2; supply via InSAR/data provider.",
                ],
            },
            "usage": {
                "used_as_prediction_model_input": False,
                "used_as_decision_support": bool(used_as_decision_support),
            },
        }

    def __repr__(self) -> str:
        return (
            f"MonitoringForecaster(model=SimpleTCNV2, params={self.param_count}, "
            f"window={INPUT_WINDOW}, horizon={FORECAST_HORIZON}, "
            f"train_mean={self.train_mean:.6f}, train_std={self.train_std:.6f}, "
            f"units={DISPLACEMENT_UNITS!r})"
        )
