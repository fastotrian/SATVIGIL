"""
SATVIGIL — SVR Oil Spill Attribution Model Training
====================================================
Trains a Support Vector Regressor (SVR) on the synthetic AIS dataset
to predict spill culprit probability from 4 vessel behaviour signals:
  1. Spatial proximity to spill (dist_to_nearest_spill_km)
  2. Vessel type spill prior risk (vessel_type → encoded risk)
  3. Behavioral anomaly (ais_gap_minutes, is_loitering, speed_deviation)
  4. Heading/course alignment (implicit in speed_deviation for now;
     full heading alignment is passed at inference time)

Output:
  ml/models/svr_spill_attribution.pkl  — trained pipeline (scaler + SVR)
  ml/models/model_metadata.json        — training metrics and feature list
"""
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score

# ── Paths ─────────────────────────────────────────────────────────────────────
ML_DIR    = Path(__file__).resolve().parents[1]
DATA_CSV  = ML_DIR / "data" / "raw" / "ais_training_dataset.csv"
MODEL_DIR = ML_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PKL = MODEL_DIR / "svr_spill_attribution.pkl"
META_JSON = MODEL_DIR / "model_metadata.json"

# ── Vessel type → spill risk prior (calibrated from ITOPF 2023) ──────────────
VESSEL_TYPE_RISK = {
    80: 1.00, 81: 0.98, 82: 0.95, 83: 0.92, 84: 0.90,
    85: 0.88, 86: 0.85, 87: 0.83, 88: 0.80, 89: 0.78,
    70: 0.42, 71: 0.40, 72: 0.38, 73: 0.35, 74: 0.32,
    75: 0.30, 76: 0.28, 77: 0.25, 78: 0.22, 79: 0.20,
    30: 0.08, 31: 0.07, 32: 0.06, 33: 0.06, 34: 0.05,
    35: 0.05, 36: 0.04, 37: 0.04, 38: 0.04, 39: 0.04,
    60: 0.05, 50: 0.12,
}

FEATURE_COLS = [
    "vessel_type_risk_encoded",   # float: ITOPF spill prior
    "dist_to_nearest_spill_km",   # float: haversine proximity
    "ais_gap_minutes",            # int:   dark gap duration
    "speed_knots",                # float: current SOG
    "speed_deviation_from_type_mean",  # float: anomaly signal
    "is_loitering",               # binary: loitering flag
    "near_spill_zone",            # binary: inside spill zone radius
]

TARGET_COL = "heuristic_risk_score"   # continuous [0,1] — SVR learns to generalise this


# Operational proximity cutoff: vessels beyond this have 0 spill attribution
CUTOFF_KM = 300.0


def compute_heuristic_score(row: "pd.Series") -> float:
    """
    Compute reference heuristic score for each training row (SVR learns to generalise this).
    Attribution combines:
      1. Spatial proximity (closer = higher)
      2. Vessel type prior (tankers carry crude, fishing doesn't)
      3. Behavioral anomaly (AIS dark gaps, loitering, speed deviation)
    """
    dist_km   = float(row["dist_to_nearest_spill_km"])
    vtype_r   = float(row["vessel_type_risk_encoded"])
    gap       = float(row["ais_gap_minutes"])
    speed_dev = float(row["speed_deviation_from_type_mean"])
    loiter    = float(row.get("is_loitering", 0))

    dist_score = max(0.0, 1.0 - (dist_km / CUTOFF_KM))
    gap_score  = min(1.0, gap / 60.0)
    sp_dev_s   = min(1.0, speed_dev / 8.0)
    anomaly_s  = max(gap_score, loiter, 0.5 * sp_dev_s)

    # Base culpability risk = 50% prior (tanker) + 50% behavior (gap/speed anomaly)
    base_risk  = 0.50 * vtype_r + 0.50 * anomaly_s

    # Final risk is gated by spatial proximity to spill
    final_risk = dist_score * base_risk

    return round(min(max(final_risk, 0.0), 1.0), 4)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features from raw AIS dataframe."""
    df = df.copy()
    df["vessel_type_risk_encoded"] = df["vessel_type"].map(
        lambda t: VESSEL_TYPE_RISK.get(int(t), 0.15)
    )
    return df


def train():
    print("=" * 60)
    print("SATVIGIL SVR Oil Spill Attribution Model — Training")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────────
    if not DATA_CSV.exists():
        raise FileNotFoundError(
            f"Training data not found: {DATA_CSV}\n"
            "Run: python ml/training/generate_training_data.py"
        )

    print(f"\n[1/6] Loading dataset: {DATA_CSV}")
    df = pd.read_csv(DATA_CSV)
    print(f"      Rows: {len(df):,}")

    # ── Feature engineering + continuous target ──────────────────────────────
    print("[2/6] Engineering features + computing heuristic risk scores ...")
    df = build_features(df)
    df[TARGET_COL] = df.apply(compute_heuristic_score, axis=1)
    print(f"      Target range: [{df[TARGET_COL].min():.3f}, {df[TARGET_COL].max():.3f}]  "
          f"mean={df[TARGET_COL].mean():.3f}")

    # ── Random subsample 30K rows (SVR is O(n^2-n^3)) ────────────────────────
    print("[3/6] Random subsample to 30,000 rows ...")
    df_sample = df.sample(n=min(30000, len(df)), random_state=42).reset_index(drop=True)
    print(f"      Subsample: {len(df_sample):,} rows")

    X = df_sample[FEATURE_COLS].values.astype(np.float32)
    y = df_sample[TARGET_COL].values.astype(np.float32)

    # ── Train / test split ───────────────────────────────────────────────────
    print("[4/6] Splitting train/test (80/20) ...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"      Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # ── Build pipeline: StandardScaler → SVR ─────────────────────────────────
    print("[5/6] Training SVR pipeline (kernel=rbf, C=10, epsilon=0.05) ...")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svr", SVR(kernel="rbf", C=10.0, epsilon=0.05, gamma="scale")),
    ])
    pipeline.fit(X_train, y_train)

    # ── Evaluate ─────────────────────────────────────────────────────────────
    print("[5/6] Evaluating ...")
    y_pred_train = pipeline.predict(X_train)
    y_pred_test  = pipeline.predict(X_test)

    # Clip to [0, 1] for probability interpretation
    y_pred_test_clipped = np.clip(y_pred_test, 0, 1)

    mae_train = float(mean_absolute_error(y_train, y_pred_train))
    mae_test  = float(mean_absolute_error(y_test,  y_pred_test_clipped))
    r2_train  = float(r2_score(y_train, y_pred_train))
    r2_test   = float(r2_score(y_test,  y_pred_test_clipped))

    # 5-fold CV on a 20% subsample (SVR is slow on large datasets)
    subsample_idx = np.random.default_rng(42).choice(len(X_train), size=min(10000, len(X_train)), replace=False)
    cv_scores = cross_val_score(
        pipeline, X_train[subsample_idx], y_train[subsample_idx],
        cv=5, scoring="r2", n_jobs=-1
    )

    print(f"\n      MAE  train={mae_train:.4f}  test={mae_test:.4f}")
    print(f"      R2   train={r2_train:.4f}  test={r2_test:.4f}")
    print(f"      CV R2 (5-fold): {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")

    # ── Save model ───────────────────────────────────────────────────────────
    print(f"\n[6/6] Saving model -> {MODEL_PKL}")
    joblib.dump(pipeline, MODEL_PKL)

    metadata = {
        "model_type": "SVR (RBF kernel, scikit-learn)",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "feature_columns": FEATURE_COLS,
        "target_column": TARGET_COL,
        "hyperparameters": {"kernel": "rbf", "C": 10.0, "epsilon": 0.05, "gamma": "scale"},
        "metrics": {
            "mae_train": round(mae_train, 4),
            "mae_test": round(mae_test, 4),
            "r2_train": round(r2_train, 4),
            "r2_test": round(r2_test, 4),
            "cv_r2_mean": round(float(cv_scores.mean()), 4),
            "cv_r2_std":  round(float(cv_scores.std()),  4),
        },
        "vessel_type_risk_map": VESSEL_TYPE_RISK,
        "dataset_source": (
            "Synthetic Indian Ocean AIS dataset generated from EMSA vessel "
            "behaviour distributions (speed/course/gap) and ITOPF spill "
            "proximity priors. See ml/training/generate_training_data.py."
        ),
    }
    with open(META_JSON, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"      Metadata saved -> {META_JSON}")
    print("\nTraining complete.")
    print(f"    Model: {MODEL_PKL}")
    print(f"    R2 (test): {r2_test:.4f}   MAE (test): {mae_test:.4f}")
    return pipeline, metadata


if __name__ == "__main__":
    train()
