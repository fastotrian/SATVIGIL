# LandslideGuard — AI Framework for Landslide Detection, Monitoring & Prediction

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![PyTorch 2.0+](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![Tests](https://img.shields.io/badge/integration_tests-185_passed-brightgreen.svg)]()
[![Artifact Integrity](https://img.shields.io/badge/frozen_artifacts-15%2F15_verified-success.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

**LandslideGuard** is a multi-tier, end-to-end artificial intelligence and Earth Observation (EO) platform engineered for comprehensive landslide risk assessment. The system coordinates three specialized domains into an operational workflow:

1. **Detection (V1/V2):** Deep-learning semantic segmentation for mapping landslide scars using 14-channel multispectral Sentinel-2 and ALOS PALSAR satellite data.
2. **Monitoring (V1/V2):** Deep sequence modeling utilizing Temporal Convolutional Networks (TCN) to forecast slope deformation trends from InSAR displacement time series.
3. **Prediction (V1):** Tree-based machine learning (XGBoost) quantifying landslide trigger risk using multi-day antecedent precipitation dynamics (NASA GPM IMERG) and high-resolution topographic terrain metrics (NASA SRTM).
4. **Operational Integration Layer:** A decoupled, schema-enforced orchestration system featuring a canonical site registry, bounded live caching, end-to-end provenance, and strict fail-loud scientific governance.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Repository Organization](#repository-organization)
- [Module Deep-Dives](#module-deep-dives)
  - [1. Detection Module (`LandslideGuard`)](#1-detection-module-landslideguard)
  - [2. Monitoring Module (`LandslideGuard_Monitering`)](#2-monitoring-module-landslideguard_monitering)
  - [3. Prediction Module (`LandslideGuard_Prediction`)](#3-prediction-module-landslideguard_prediction)
  - [4. Operational Integration (`landslideguard_integration`)](#4-operational-integration-landslideguard_integration)
- [Earth Observation Data Sources](#earth-observation-data-sources)
- [Scientific Discipline & Integrity Principles](#scientific-discipline--integrity-principles)
- [Installation & Environment Setup](#installation--environment-setup)
- [Quickstart & Usage](#quickstart--usage)
- [Verification & Test Suite](#verification--test-suite)
- [Phase Status & Roadmap (Phases 1–9A)](#phase-status--roadmap-phases-19a)

---

## System Architecture

```
                                 EARTH OBSERVATION / REMOTE SENSING
              ┌───────────────────────────────┬───────────────────────────────┐
              │                               │                               │
        Sentinel-2 (12 Bands)           Sentinel-1 SAR              NASA GPM IMERG &
       + ALOS PALSAR DEM/Slope            (SLC Pairs)                 NASA SRTMGL1
              │                               │                               │
              ▼                               ▼                               ▼
      ┌────────────────┐             ┌─────────────────┐             ┌─────────────────┐
      │  DETECTION V1  │             │  MONITORING V2  │             │  PREDICTION V1  │
      │  (U-Net 14-ch) │             │  (SimpleTCNV2)  │             │    (XGBoost)    │
      └───────┬────────┘             └────────┬────────┘             └────────┬────────┘
              │ Landslide Polygons            │ t+1..t+3 Forecast             │ 26 Features
              │ + Non-calibrated Score        │ + Velocity/Acceleration       │ + Risk Ranking
              ▼                               ▼                               ▼
    ┌───────────────────┐           ┌───────────────────┐           ┌───────────────────┐
    │ Detection Adapter │           │ Monitoring Wrapper│           │  Live Prediction  │
    │  (CRS Reproject)  │           │ (Units:Unresolved)│           │  Service + Cache  │
    └─────────┬─────────┘           └─────────┬─────────┘           └─────────┬─────────┘
              │                               │                               │
              └───────────────────────┬───────┴───────────────────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │   CANONICAL SITE REGISTRY │  --> Generates SITE-NNNNNN
                        │   (Geohash Persistence)   │
                        └─────────────┬─────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │ OPERATIONAL ORCHESTRATOR  │  --> Full Provenance Tracking
                        │ (Status: SUCCESS/PARTIAL) │  --> ISO-8601 UTC Timestamps
                        └─────────────┬─────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │  UNIFIED OUTPUT RESULT    │
                        │  (integrated_result/1.0)  │
                        └───────────────────────────┘
```

---

## Repository Organization

The repository is structured into isolated, decoupled packages to maintain frozen model artifact integrity while enabling clean integration:

```
D:\LANDSLIDE\
├── LandslideGuard/                   # [Detection Module]
│   ├── configs/                      # Dataset & normalization YAML configurations
│   ├── docs/                         # Kaggle setup & workflow documentation
│   ├── notebooks/                    # 00_kaggle_setup, 01_data_prep, 02_model_dev
│   ├── src/detection/                # U-Net architecture, dataset loader, losses, metrics, inference
│   ├── outputs/detection/            # Data verification stats, figures, PASS/FAIL logs
│   ├── checkpoints/detection/        # Frozen best model checkpoints (best_model.pth)
│   └── requirements.txt              # Core computer vision & remote sensing requirements
│
├── LandslideGuard_Monitering/        # [Monitoring Module]
│   ├── data/Displacement/            # InSAR displacement time series (DESC_MEAN_TREND.csv)
│   ├── models/                       # SimpleTCNV2 PyTorch checkpoints (v1 & v2_best.pth)
│   ├── outputs/                      # Training history, scalar configs, test metrics & predictions
│   ├── monitoring_v1_inference.py    # V1 inference baseline
│   └── models/monitoring_v2_dev.ipynb# V2 TCN training and evaluation pipeline
│
├── LandslideGuard_Prediction/        # [Prediction Module]
│   ├── prediction_dataset/           # Frozen train/val/test splits (2,063 samples, 26 features)
│   ├── models/prediction_v1/         # Frozen XGBoost classifier & scikit-learn preprocessor
│   ├── outputs/prediction_v1/        # Validation comparisons, calibration curves, test metrics
│   ├── src/prediction_v1/            # PredictionV1 predictor & feature contract specifications
│   ├── imerg_targeted_download/      # Historical NASA GPM IMERG retrieval utilities
│   └── notebooks/                    # 01_targeted_imerg_prep, 02_model_development
│
├── landslideguard_integration/       # [Unified System Integration]
│   ├── configs/                      # SAR & system execution configs
│   ├── src/landslideguard/
│   │   ├── common/                   # SiteRegistry, geohashing, coordinate utilities
│   │   ├── schemas/                  # JSON-Schema specifications and validators
│   │   ├── cache/                    # BoundedCacheManager (IMERG & SRTM disk storage)
│   │   ├── providers/                # Live IMERG & SRTM Earth Observation data providers
│   │   ├── monitoring/               # MonitoringForecaster (V2 production wrapper)
│   │   ├── prediction/               # FeatureBuilder & LivePredictionService
│   │   ├── integration/              # OperationalOrchestrator, adapters, pipeline DAG
│   │   └── sar/                      # Phase 9 SAR / InSAR engine specifications
│   ├── tests/                        # 185 unit, contract, and operational integration tests
│   └── pyproject.toml                # Integration package metadata & test configurations
│
├── outputs/                          # [Cross-Module Documentation & Reports]
│   ├── integration/                  # Phase 1 through Phase 9A comprehensive architectural reports
│   └── satellite/                    # Wayanad case study Sentinel-1 metadata & InSAR pairs
│
└── transfer/                         # Git bundles for repository portability across environments
```

---

## Module Deep-Dives

### 1. Detection Module (`LandslideGuard`)
* **Objective:** Semantic segmentation of landslide boundaries from multi-sensor satellite imagery.
* **Benchmark Dataset:** `Landslide4Sense` (3,799 training, 245 validation, 800 test patches of shape `128×128`).
* **Input Channels (14 Channels):**
  - Bands 0–11: Sentinel-2 Multispectral (B1 Coastal, B2 Blue, B3 Green, B4 Red, B5–B7 Red Edge, B8 NIR, B8A Narrow NIR, B9 Water Vapor, B10 Cirrus, B11 SWIR 1).
  - Bands 12–13: ALOS PALSAR Topographic Slope and Digital Elevation Model (DEM).
* **Model Architecture:** Fully convolutional PyTorch U-Net (~7.77M parameters at `base_features=32`).
* **Loss Functions:** Compound loss configurations (BCE + Dice, Focal + Dice) to address severe positive-class pixel sparsity (~2.32% positive pixels).
* **Validation & Metrics:** Pixel-level exact Dice, Intersection over Union (IoU), Precision, Recall, and PR-AUC.
* **Status:** Stage 1 data verification 100% complete (28/28 checks PASS). Stage 2 model pipeline prepared for distributed Kaggle GPU training.

### 2. Monitoring Module (`LandslideGuard_Monitering`)
* **Objective:** Temporal forecasting of ground displacement and slope deformation kinematics from InSAR time series.
* **Dataset:** Line-of-sight (LOS) mean trend displacement stacks over slope units (`DESC_MEAN_TREND.csv`).
* **Model Architecture:** `SimpleTCNV2` (Temporal Convolutional Network, PyTorch):
  - Parameters: 899
  - Input Window: 12 historical timesteps
  - Forecast Horizon: 3 future timesteps ($t+1, t+2, t+3$)
  - Objective: Huber Loss with AdamW optimization and training-only Z-score scaling.
* **Evaluation & Benchmark:**
  - **MAE:** `7.88` (vs. persistence baseline `13.82` — **43.0% improvement**)
  - **RMSE:** `8.95` (vs. persistence baseline `15.10` — **40.7% improvement**)
  - **$R^2$:** `0.8745` (vs. persistence baseline `0.6433` — **+0.2312 absolute gain**)
  - Per-horizon $R^2$: $t+1: 0.981$, $t+2: 0.903$, $t+3: 0.730$.
* **Kinematic Derivations:** Calculates instantaneous velocity, acceleration, trend direction, and trend slope.
* **Scientific Guardrail:** Physical displacement units are designated as `"unresolved"` pending ground sensor calibration. Outputs serve as standalone decision-support indicators and are strictly prevented from contaminating Prediction V1 feature vectors.

### 3. Prediction Module (`LandslideGuard_Prediction`)
* **Objective:** Assessing regional trigger probability based on antecedent hydrometeorological stress and topographic susceptibility.
* **Ground Truth Dataset:** 2,063 verified samples from the NASA Global Landslide Catalog (GLC) across India:
  - 1,265 positive landslide trigger events.
  - 798 spatio-temporally matched control non-events.
  - Train/Val/Test Split: 1,443 / 310 / 310 samples (frozen, zero leakage).
* **Earth Observation Ingestion:**
  - **Precipitation:** NASA GPM IMERG Final V07 daily rainfall (0.1° spatial resolution). Features a strict 14-day lookback ($T-14$ to $T-1$). Event day $T$ is strictly excluded to prevent target leakage.
  - **Topography:** NASA SRTMGL1 V003 (1 arc-second / 30m resolution). Topographic parameters derived via Horn's 8-neighbourhood algorithm.
* **Feature Contract (26 Strictly Ordered Features):**
  - Daily Precipitation Lags: `rain_t1` through `rain_t14`
  - Cumulative Aggregates: `rain_sum_3d`, `rain_sum_7d`, `rain_sum_14d`, `rain_std_14d`
  - Antecedent Precipitation Index: `api_3d`, `api_7d` (decay factor $\lambda = 0.85$)
  - Topographic Morphology: `elevation`, `slope`, `aspect`, `curvature_plan`, `curvature_profile`
* **Model & Final Test Metrics (XGBoost Classifier):**
  - **PR-AUC:** `0.9946`
  - **ROC-AUC:** `0.9910`
  - **Precision:** `0.9212`
  - **Recall:** `0.9842`
  - **F1 Score:** `0.9517`
  - **Balanced Accuracy:** `0.9254`
  - Decision Threshold: `0.30` (optimized on validation set for maximum F1).
  - Score Semantics: Raw ranking score (`risk_ranking_not_calibrated_probability`). Explicit post-calibration was evaluated and rejected on validation data to preserve monotonic discrimination.

### 4. Operational Integration (`landslideguard_integration`)
* **Architecture:** Decoupled adapter layer connecting the three frozen domains.
* **Canonical Site Registry (`SiteRegistry`):** Assigns persistent, write-once identifiers (`SITE-NNNNNN`) keyed by geographic coordinates and detection date, ensuring longitudinal tracking across repeated satellite overpasses.
* **Live Ingestion Providers:**
  - `IMERGRainfallProvider`: Remote HTTP/NASA Earthdata client with bounding box extraction and date-window verification.
  - `SRTM30mTerrainProvider`: High-efficiency terrain derivation caching raw `int16` DEM tiles to eliminate memory overhead.
* **Disk-Safety & Bounded Cache (`CacheManager`):** Enforces strict disk limits (requires $\ge 5\text{ GB}$ host free space), TTL invalidation, zero-byte corrupt file isolation, and atomic file replacement.
* **Operational Orchestrator (`OperationalOrchestrator`):**
  - Coordinates detection polygon handoff $\rightarrow$ monitoring displacement $\rightarrow$ live remote feature extraction $\rightarrow$ prediction risk scoring.
  - Generates unified result contract (`integrated_result/1.0`) with unique `operation_id`, ISO-8601 UTC timestamps, and granular execution status (`SUCCESS`, `PARTIAL`, `FAILED`).
  - Implements complete provenance capturing all model versions, thresholds, CRS transformations, and data source products.

---

## Earth Observation Data Sources

| Domain | Dataset / Sensor | Provider | Resolution | Role |
|---|---|---|---|---|
| **Optical / NIR / Red Edge** | Sentinel-2 MSI | ESA / Copernicus | 10m / 20m | Spectral scar identification |
| **SAR Topography** | ALOS PALSAR | JAXA | 12.5m | Baseline DEM and slope layers |
| **Radar Interferometry** | Sentinel-1 C-SAR (SLC) | ESA / Copernicus | 5m $\times$ 20m | InSAR surface displacement |
| **Global Precipitation** | GPM_3IMERGDF V07 (Final) | NASA / JAXA | 0.1° (~10km) / Daily | Multi-day antecedent rainfall |
| **Digital Elevation Model** | SRTMGL1 V003 | NASA / USGS | 1 arc-second (~30m) | Local slope, aspect, curvature |
| **Landslide Ground Truth** | Global Landslide Catalog (GLC) | NASA | Point coordinates | Historic positive trigger events |

---

## Scientific Discipline & Integrity Principles

1. **Zero Data Leakage:** In prediction modeling, the event day precipitation ($T=0$) is strictly omitted from feature construction ($T-14$ to $T-1$). Models predict trigger vulnerability prior to event day culmination.
2. **Strict Module Isolation:** Monitoring kinematics (velocity/acceleration) are strictly prohibited from feeding into Prediction V1. The 26-feature prediction contract is immutable.
3. **No Fabricated Data / Fail Loud:** Missing satellite tiles or rainfall anomalies raise explicit structured error codes (`MISSING_RAINFALL`, `MISSING_TERRAIN`) rather than interpolating synthetic defaults.
4. **Honest Probability Framing:** Raw classifier outputs are explicitly typed as `risk_ranking_not_calibrated_probability`. Uncalibrated outputs are never presented as true statistical probabilities.
5. **Frozen Artifact Governance:** All model weights, normalization scalers, and dataset splits are locked with cryptographic SHA-256 signatures (15/15 artifacts tracked and verified against drift).

---

## Installation & Environment Setup

### Prerequisites
- **Operating System:** Windows 10/11, Linux, or macOS.
- **Python:** Version 3.10, 3.11, or 3.12 (Python 3.13 supported for integration layer; 3.10–3.11 recommended for full geospatial stacks).
- **Hardware:** Minimum 8 GB RAM (16 GB recommended). GPU required only for Detection model training.

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone <REPO_URL> landslide-guard
cd landslide-guard

# Create and activate a clean virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

Install the core integration package in editable mode along with testing requirements:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install the integration package and test suite
pip install -e landslideguard_integration/

# Install scientific, geospatial, and ML libraries
pip install numpy scipy pandas scikit-learn xgboost lightgbm torch torchvision h5py pyproj requests pydantic
```

For working directly on the Detection module:
```bash
pip install -r LandslideGuard/requirements.txt
```

---

## Quickstart & Usage

### 1. Execute the Operational Orchestrator

The `OperationalOrchestrator` allows running a controlled or live risk assessment across the integrated pipeline:

```python
from pathlib import Path
from landslideguard.integration.orchestrator import OperationalOrchestrator
from landslideguard.common.site_registry import SiteRegistry
from landslideguard.monitoring.inference_v2 import MonitoringForecaster
from landslideguard.prediction.live_prediction import build_live_service

# Initialize base paths
base_dir = Path("D:/LANDSLIDE")
monitoring_dir = base_dir / "LandslideGuard_Monitering"
prediction_dir = base_dir / "LandslideGuard_Prediction"
cache_dir = base_dir / "landslideguard_integration/cache"

# 1. Initialize Site Registry
registry = SiteRegistry(base_dir / "landslideguard_integration/cache/site_registry.parquet")

# 2. Load Frozen Monitoring Forecaster (SimpleTCNV2)
forecaster = MonitoringForecaster.from_dir(monitoring_dir)

# 3. Build Live Prediction Service with Bounded Cache
live_pred_service = build_live_service(
    prediction_dir=prediction_dir,
    cache_root=cache_dir,
    offline_fallback=True
)

# 4. Initialize Orchestrator
orchestrator = OperationalOrchestrator(
    site_registry=registry,
    monitoring_forecaster=forecaster,
    prediction_service=live_pred_service
)

# 5. Execute Pipeline for a Detected Hazard Area
result = orchestrator.run_pipeline(
    detection_polygon=[[76.12, 11.55], [76.13, 11.55], [76.13, 11.56], [76.12, 11.56]],
    detection_date="2024-07-30",
    detection_confidence=0.89,
    source_crs="EPSG:4326"
)

print(f"Site ID:      {result.site_id}")
print(f"Status:       {result.status}")
print(f"Risk Score:   {result.prediction.risk_score:.4f} (Alert: {result.prediction.is_alert})")
print(f"Displacement: t+1={result.monitoring.forecast_t1:.2f}, t+2={result.monitoring.forecast_t2:.2f}")
```

### 2. Standalone Monitoring Inference (TCN)

```python
from landslideguard.monitoring.inference_v2 import MonitoringForecaster

forecaster = MonitoringForecaster.from_dir("D:/LANDSLIDE/LandslideGuard_Monitering")

# Provide 12 timesteps of historical displacement
history_12 = [-20.1, -21.4, -22.0, -22.9, -23.5, -24.8, -25.2, -26.1, -27.0, -28.2, -29.1, -30.5]
forecast = forecaster.predict(history_12)

print(f"Forecasted displacement [t+1, t+2, t+3]: {forecast.forecast_values}")
print(f"Derived velocity: {forecast.velocity:.3f} | Acceleration: {forecast.acceleration:.3f}")
```

### 3. Standalone Prediction Inference (XGBoost)

```python
from landslideguard.prediction.feature_builder import PredictionFeatureBuilder
from prediction_v1.inference import LandslideRiskPredictor

# Initialize feature builder and predictor
builder = PredictionFeatureBuilder()
predictor = LandslideRiskPredictor.from_dir("D:/LANDSLIDE/LandslideGuard_Prediction/models/prediction_v1")

# Build 26 features from 14-day rainfall lag array + terrain attributes
features = builder.build_features(
    rainfall_14d=[12.4, 8.1, 0.0, 0.0, 5.2, 18.9, 45.2, 32.1, 10.4, 2.0, 0.0, 14.5, 65.2, 88.0],
    elevation=1250.0,
    slope=28.5,
    aspect=185.0,
    curvature_plan=0.04,
    curvature_profile=-0.02
)

alert = predictor.predict(features)
print(f"Risk Ranking Score: {alert['risk_score']:.4f} | Alert Triggered: {alert['alert']}")
```

---

## Verification & Test Suite

The integration package includes an exhaustive, automated regression test suite validating schema boundaries, cross-module isolation, CRS reprojection, live API responses, cache bounds, and frozen hash preservation.

To run the complete test suite:

```bash
cd landslideguard_integration
pytest -v
```

### Summary of Passing Test Suites

| Test Suite | File | Tests | Focus Area |
|---|---|---|---|
| **Schemas & Contracts** | `test_schemas.py` | 15 | Validation of all JSON schemas and dataclass models |
| **Site Registry** | `test_site_registry.py` | 14 | Site ID generation, geohashing, persistence |
| **Detection Adapter** | `test_detection_adapter.py` | 12 | Reprojection from UTM/local CRS to EPSG:4326 |
| **Monitoring Forecaster** | `test_monitoring_forecaster.py` | 16 | TCN forward pass, scaler alignment, metric fidelity |
| **Feature Builder** | `test_feature_builder.py` | 18 | 26-feature ordering, rolling sums, API calculation |
| **Rainfall Provider** | `test_rainfall_provider.py`, `test_imerg_live.py` | 24 | IMERG coordinate indexing, T-0 exclusion guard |
| **Terrain Provider** | `test_terrain_provider.py`, `test_srtm_live.py` | 22 | SRTM tile fetching, Horn 8-neighbourhood derivatives |
| **Cache Management** | `test_phase7_cache_policy.py` | 22 | Disk limits, TTL invalidation, atomic file write |
| **Orchestrator** | `test_phase8_orchestration.py` | 20 | Unified result creation, failure matrices, provenance |
| **Failure Handling** | `test_integration_failures.py` | 10 | Structured errors on network or data absence |
| **Environment Safety** | `test_phase9a_environment.py` | 12 | Host disk space audits and safe environment probes |
| **Total** | | **185 Passed** | **0 Failures · 100% Green** |

---

## Phase Status & Roadmap (Phases 1–9A)

The LandslideGuard system has been developed through a structured, multi-phase engineering protocol:

- [x] **Phase 1: Detection $\rightarrow$ Monitoring Handoff:** Canonical CRS conversion, boundary extraction, and handoff schema definition.
- [x] **Phase 2: Prediction Feature Providers:** Construction of the strict 26-feature vector from IMERG and SRTM data sources.
- [x] **Phase 3: Controlled End-to-End Integration:** Deterministic golden-sample validation across all three modules.
- [x] **Phase 4: Live Prediction Providers:** Production client architecture for remote Earth Observation APIs.
- [x] **Phase 5: Real Live Retrieval:** Verified real-world live retrieval against NASA GPM IMERG and SRTM repositories.
- [x] **Phase 6: Multi-Location Validation:** Multi-site spatial robustness tests covering diverse geological terrains across India.
- [x] **Phase 7: Bounded Cache Policy:** Implemented disk usage caps, eviction policies, and corrupt-download safeguards.
- [x] **Phase 8: Operational Orchestrator:** Complete unified pipeline execution, full execution provenance, and structured error reporting.
- [x] **Phase 9A: SAR/InSAR Environment Audit:** Comprehensive assessment of host compute/disk resources and preparation for local ISCE3/MintPy execution using Sentinel-1 SLC data (Wayanad dataset).
- [ ] **Phase 9B: Production InSAR Pipeline (Upcoming):** Full execution of interferometric phase unwrapping and automated displacement time series generation via ISCE3 and MintPy on dedicated storage.
- [ ] **Phase 10: Operational Web API & Dashboard:** FastAPI service surface and interactive GIS monitoring dashboard.

---

## Scientific Citation & References

If using LandslideGuard in academic or industrial research, please reference the corresponding source catalogs and foundational works:

- **Landslide4Sense Benchmark:** Ghorbanzadeh et al., *Landslide4Sense: Reference dataset and deep learning benchmark for landslide detection*, IEEE GRSL.
- **NASA GPM IMERG:** Huffman, G.J., et al., *Integrated Multi-satellitE Retrievals for GPM (IMERG)*, NASA Goddard Earth Sciences Data and Information Services Center (GES DISC).
- **NASA SRTMGL1:** Farr, T. G., et al., *The Shuttle Radar Topography Mission*, Reviews of Geophysics, 45, RG2004.
- **NASA Global Landslide Catalog:** Kirschbaum, D. B., et al., *A global landslide catalog for hazard applications*, Natural Hazards, 52(3), 561-575.
- **MintPy InSAR:** Yunjun, Z., et al., *Small baseline InSAR time series analysis: Unwrapping error correction and noise reduction*, Computers & Geosciences.
