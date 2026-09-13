# SATVIGIL — High-Level Design (HLD)

## 1. System Overview

SATVIGIL is an AI-powered satellite monitoring platform that predicts and classifies maritime, industrial, geological, and fire-related risks across India before they become disasters.

**Primary PS:** SIH 2026 — PS 143 (NTRO: Oil Spill Detection + AIS Correlation)
**Additional module:** PS 162 (NTRO: Industrial Fire & Thermal Source Classification)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES (Free/Public)                │
│  NASA FIRMS │ AIS (AISHub/GFW) │ Sentinel-1/2 │ OSM/CPCB   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  DATA PIPELINE LAYER                         │
│      Fetchers (APScheduler) → Processors → Validators        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    AI / ML LAYER                             │
│  Fire Classifier (XGBoost) │ Vessel Risk (Isolation Forest) │
│  Spill Detector (U-Net)    │ SAR Deformation (InSAR)        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              BACKEND API (FastAPI + PostGIS)                  │
│  REST API │ WebSockets │ Celery Tasks │ Redis Cache          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              FRONTEND (React + Mapbox GL JS)                  │
│    Live India Map │ 5 Module Layers │ Real-time Alert Panel  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Five Detection Modules

### Module 1: Oil Spill Detection
- **Input:** Sentinel-1 C-SAR radar imagery (IW GRDH) + AIS vessel positions
- **Process:** Vessel behavior risk-scoring (dark transponders, loitering, MPA proximity) + Lee/Otsu SAR segmentation + Kinematic/SVR attribution ensemble
- **Output:** Risk-scored vessel markers on map; spill sheen polygons when SAR confirms
- **Responding agency:** Indian Coast Guard + INCOIS

### Module 2: Illegal Fishing Detection
- **Input:** AIS data (same pipeline as Module 1)
- **Process:** Flag vessels going dark (AIS off) inside Marine Protected Areas
  - Gulf of Kutch MNP, Gulf of Mannar MNP, Sundarbans buffer
- **Output:** Red markers on MPA zones with vessel MMSI and gap duration
- **Responding agency:** Coast Guard + Fisheries Department

### Module 3: Fire Classification
- **Input:** NASA FIRMS (VIIRS 375m NRT) + OSM land use + CPCB cluster list
- **Process:** 5-class classifier (industrial | wildfire | stubble | gas flare | mining)
  - Uses location context + FRP + seasonal timing + recurrence pattern
- **Output:** Color-coded hotspot markers with fire type label + agency routing
- **Responding agency:** Varies by class (PESO / Forest Dept / CAQM / IBM)

### Module 4: Industrial Pollution (Thermal Recurrence)
- **Input:** FIRMS historical data (downloadable bulk archive)
- **Process:** Track recurring hotspots at same coordinates over time
  - Recurrence at CPCB-flagged clusters = enforcement evidence
- **Output:** Heatmap overlay + facility-level recurrence timeline
- **Responding agency:** CPCB + State Pollution Control Boards

### Module 5: Landslide Risk (SAR)
- **Input:** Sentinel-1 SAR image pairs (Copernicus, free)
- **Process:** InSAR change detection — millimeter ground deformation tracking
  - Combined with rainfall forecasts for final risk alert
- **Output:** Deformation heatmap over Himalayan belt + Western Ghats
- **Responding agency:** NDMA + State Disaster Management Authorities

---

## 4. Tech Stack Summary

| Layer | Technology | Reason |
|---|---|---|
| Frontend | React 18 + Mapbox GL JS | WebGL rendering for smooth vessel animations |
| Backend | Python FastAPI | Same language as ML — no serialization overhead |
| Task Queue | Celery + Redis | Heavy ML jobs don't block the API |
| ML | PyTorch + XGBoost | PyTorch for U-Net (spill), XGBoost for fire classifier |
| Geospatial | GeoPandas + PostGIS | Spatial joins + geospatial DB queries |
| Database | PostgreSQL 15 + PostGIS | Enables "alerts within 50km of Mumbai" in one SQL line |
| Scheduler | APScheduler | Periodic fetch jobs inside FastAPI process |
| Deployment | Docker Compose | One command to run entire stack |

---

## 5. Data Flow

```
Every 15 min:  AISHub API → ais_fetcher.py → risk_scorer → Alert DB → WebSocket → Map
Every 3 hours: FIRMS API  → firms_fetcher.py → fire_classifier → Alert DB → WebSocket → Map
Daily:         Copernicus → sentinel_fetcher.py → SAR processor → Deformation DB → Map layer
```

---

## 6. Satellite Behavior — Honest Coverage Model

| Sensor | Revisit Over India | Latency |
|---|---|---|
| MODIS (Terra+Aqua) | 2-4x/day | ~3 hours |
| VIIRS (NPP + NOAA-20 + NOAA-21) | 2-4x/day | ~3 hours |
| Sentinel-2 (optical) | Every 2-3 days (A+B combined) | ~24 hours |
| Sentinel-1 (SAR) | Every 6-12 days | ~24 hours after acquisition |

**This is NOT real-time surveillance** — it is periodic monitoring at satellite physics-limited intervals.

---

## 7. SDG Alignment

- SDG 13: Climate Action (disaster risk reduction)
- SDG 14: Life Below Water (ocean pollution monitoring)
- SDG 15: Life on Land (forest fire + landslide)
- SDG 11: Sustainable Cities & Communities (disaster resilience)
