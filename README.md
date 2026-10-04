# SATVIGIL — AI-Powered Satellite Monitoring Platform

> **Satellite + Vigil** — *Watching from orbit, acting before disaster.*

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

SATVIGIL is an AI-powered satellite monitoring platform that **predicts, classifies, and flags** maritime, industrial, geological, and fire-related risks across India — before they become disasters, not after.

Built for **Smart India Hackathon 2026**
Primary PS: **PS 143** — Oil Spill Detection with AIS Correlation (NTRO)
Additional: **PS 162** — Industrial Fire Classification using NASA FIRMS (NTRO)

---

## What It Does

Most satellite tools detect something *after* it happens. SATVIGIL scores risk *before* the incident.

| Module | Watches | Data |
|--------|---------|------|
| **Oil Spill Detection** | Vessel risk-scoring: dark AIS, loitering near ports | Sentinel-1 C-SAR + AIS |
| **Illegal Fishing** | Vessels going dark inside Marine Protected Areas | AIS (same pipeline) |
| **Fire Classification** | 5-class: industrial / wildfire / stubble / gas flare / mining | NASA FIRMS + OSM |
| **Industrial Pollution** | Recurring thermal hotspots at CPCB-flagged clusters | FIRMS historical |
| **Landslide Risk** | SAR ground deformation + rainfall threshold overlay | Sentinel-1 SAR |

---

## Quick Start

### 1. Clone & Configure
```bash
git clone <your-repo-url> && cd SATVIGIL
cp .env.example .env
```

### 2. Local Development Mode (Recommended)

**Terminal 1 — Backend (FastAPI):**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*Backend API:* [http://localhost:8000](http://localhost:8000) · *Interactive Swagger Docs:* [http://localhost:8000/docs](http://localhost:8000/docs)

**Terminal 2 — Frontend (React + Vite + MapLibre):**
```bash
cd frontend
npm install
npm run dev
```
*Frontend Tactical Dashboard:* [http://localhost:5173](http://localhost:5173)

---

### 3. Containerized Stack (Docker Compose)
```bash
docker-compose up --build
```
*Frontend:* [http://localhost:3001](http://localhost:3001) · *Backend:* [http://localhost:8000](http://localhost:8000)

See [Deployment Guide](docs/deployment/DEPLOYMENT.md) for full setup.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Mapbox GL JS + Tailwind CSS |
| Backend | Python 3.11 + FastAPI + WebSockets |
| Task Queue | Celery + Redis |
| ML | XGBoost (fire classifier) + Isolation Forest (vessel anomaly) + PyTorch (U-Net spill) |
| Geospatial | GeoPandas + Shapely + Rasterio + PostGIS |
| Database | PostgreSQL 15 + PostGIS |
| Scheduler | APScheduler |
| Deployment | Docker Compose |

---

## Project Structure

```
SATVIGIL/
├── backend/                   # FastAPI Python backend
│   ├── app/
│   │   ├── api/routes/        # REST + WebSocket endpoints
│   │   ├── core/              # Config, database connection
│   │   ├── models/            # SQLAlchemy ORM models (PostGIS)
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── maritime/      # AIS fetcher + vessel risk scorer
│   │   │   ├── fire/          # FIRMS fetcher + 5-class fire classifier
│   │   │   ├── landslide/     # SAR deformation service
│   │   │   └── pollution/     # Thermal recurrence tracker
│   │   └── tasks/             # Celery tasks + APScheduler jobs
│   └── tests/                 # Unit + integration + data quality tests
│
├── frontend/                  # React application
│   └── src/
│       ├── components/
│       │   ├── map/           # Mapbox map + 5 module layers
│       │   ├── alerts/        # Alert panel + cards
│       │   └── dashboard/     # Header, module toggles
│       ├── store/             # Zustand global state
│       └── services/          # API client + WebSocket client
│
├── ml/                        # ML models and training scripts
│   ├── models/                # U-Net (spill), XGBoost (fire), Isolation Forest
│   ├── training/              # Training scripts
│   └── notebooks/             # Jupyter exploration
│
├── data_pipeline/             # Data fetchers + processors
│   ├── fetchers/              # AIS, FIRMS, Sentinel fetchers
│   ├── processors/            # Classification + spatial join logic
│   └── validators/            # Data quality checks
│
├── docs/                      # Full documentation
│   ├── hld/HLD.md             # High-Level Design
│   ├── lld/LLD.md             # Low-Level Design + DB schema + algorithms
│   ├── data/DATA_GUIDE.md     # All datasets, how to get them, schemas
│   ├── testing/TESTING_GUIDE.md
│   └── deployment/DEPLOYMENT.md
│
└── docker-compose.yml         # One command to run everything
```

---

## Data Sources (All Free)

| Source | URL | Used For |
|--------|-----|----------|
| NASA FIRMS | https://firms.modaps.eosdis.nasa.gov/api/ | Fire/thermal hotspots |
| ESA Copernicus | https://dataspace.copernicus.eu/ | Sentinel-1 SAR + Sentinel-2 optical |
| Global Fishing Watch | https://globalfishingwatch.org/data/ | AIS + fishing classification |
| AISHub | https://www.aishub.net/ | AIS vessel tracking |
| VIIRS Nightfire | https://eogdata.mines.edu/products/vnf/ | Gas flare separation |
| OpenStreetMap/Geofabrik | https://download.geofabrik.de/asia/india.html | Land use context |

---

## Documentation

| Document | Description |
|----------|-------------|
| [HLD](docs/hld/HLD.md) | System architecture, 5-module overview, data flow |
| [LLD](docs/lld/LLD.md) | DB schema, algorithms, API endpoints, component tree |
| [Data Guide](docs/data/DATA_GUIDE.md) | Every dataset: URL, how to get it, schema, sample code |
| [Testing Guide](docs/testing/TESTING_GUIDE.md) | How to run tests, test examples, coverage targets |
| [Deployment](docs/deployment/DEPLOYMENT.md) | Docker setup, local dev, demo checklist |

---

## Fire Classification Reference

| Fire Type | Responding Agency | Legal Basis |
|-----------|------------------|-------------|
| Industrial fire | State Fire Services + PESO | Petroleum Rules / SMPV Rules |
| Gas flare | State PCB + PESO | Emission permit compliance |
| Wildfire | State Forest Department | Via FSI FAST system |
| Stubble burning | CAQM + District Magistrate | CAQM Act 2021, Section 14 |
| Mining thermal | IBM + State Directorate of Mines | MMDR Act 1957 |

---

## SDG Alignment

SDG 13 (Climate Action) · SDG 14 (Life Below Water) · SDG 15 (Life on Land) · SDG 11 (Sustainable Cities)

---

## Team Roles

| Role | Responsibility |
|------|---------------|
| AI/ML | Sentinel-1 C-SAR Lee filter + Otsu segmentation + SVR attribution ensemble |
| Data Science | XGBoost fire classifier + Isolation Forest vessel anomaly + spatial joins |
| Backend | FastAPI + APScheduler + PostGIS |
| Frontend | React + MapLibre GL + Tailwind + WebSocket client |
| Full Stack | Docker Compose + Redis + integration + deployment |
| Presenter | Demo flow + pitch narrative |

---

## License

MIT License — see [LICENSE](LICENSE).

---

*SATVIGIL — Built for SIH 2026 | NTRO PS 143 + PS 162*
