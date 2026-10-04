"""Send one hand-crafted sample through the Prediction V1 inference engine.

Usage (from anywhere):
    python D:/LANDSLIDE/LandslideGuard_Prediction/scripts/try_inference.py

Edit the SAMPLE dict below to test other inputs. All 26 features must be present.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"D:\LANDSLIDE\LandslideGuard_Prediction")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from prediction_v1 import LandslideRiskPredictor

# Real test-set row: POS_35 (a positive landslide event on 2007-03-12, Kashmir).
# Truth label = 1. The predictor should score this well above the frozen threshold.
SAMPLE = {
    # 14 daily rainfall lags (mm) — T-1 through T-14
    "rain_t1":  8.355,
    "rain_t2":  4.030,
    "rain_t3":  3.925,
    "rain_t4":  1.075,
    "rain_t5":  0.000,
    "rain_t6":  0.000,
    "rain_t7":  0.000,
    "rain_t8":  0.000,
    "rain_t9":  0.000,
    "rain_t10": 0.000,
    "rain_t11": 0.000,
    "rain_t12": 24.645,
    "rain_t13": 8.680,
    "rain_t14": 8.410,
    # 9 rainfall aggregates
    "rain_sum_3d":   16.310,
    "rain_sum_7d":   17.385,
    "rain_sum_14d":  59.120,
    "rain_max_3d":    8.355,
    "rain_max_7d":    8.355,
    "rain_max_14d":  24.645,
    "rain_mean_3d":   5.437,
    "rain_mean_7d":   3.118,
    "rain_mean_14d":  4.223,
    # 3 terrain features
    "elevation_m":    1964.0,
    "slope_degrees":  17.38,
    "aspect_degrees": 265.54,
}

MODELS_DIR = PROJECT_ROOT / "models" / "prediction_v1"

predictor = LandslideRiskPredictor.from_dir(MODELS_DIR)
print(predictor)
print(f"Frozen threshold: {predictor.threshold:.2f}")
print(f"Calibration     : {predictor.calibration_method}")
print()

prob = float(predictor.predict_proba(SAMPLE)[0])
pred = int(predictor.predict(SAMPLE)[0])

print(f"P(landslide event) : {prob:.4f}")
print(f"Predicted class    : {pred}  ({'positive event' if pred == 1 else 'control'})")
print(f"Decision           : {'ALERT (>= threshold)' if pred == 1 else 'no alert (< threshold)'}")
