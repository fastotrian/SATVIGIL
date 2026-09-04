# SATVIGIL — System Architecture Reference

---

## 1. High-Level Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION SOURCES                          │
│   NASA FIRMS API │ AISHub / GFW │ Sentinel-1 SAR │ Sentinel-2 Optical │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    DATA PIPELINE & SCHEDULER                           │
│   FastAPI APScheduler (15m AIS, 3h FIRMS) → Processors → GeoPandas    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                           AI / ML ENGINES                              │
│   • Fire 5-Class Classifier (XGBoost + FRP + OSM Land Use)            │
│   • Vessel Risk Scorer (Isolation Forest + AIS Gap Analysis)           │
│   • Oil Spill Segmentation (PyTorch U-Net on Sentinel-2)               │
│   • Super-Resolution Backbone (ESRGAN — shared across optical modules) │
│   • Landslide Deformation (Sentinel-1 InSAR + Rainfall Thresholds)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                      STORAGE & CACHE LAYER                             │
│   • PostgreSQL 15 + PostGIS (Spatial indexing, Geometries, ACID)      │
│   • Redis (Pub/Sub for WebSockets, Celery task queue, Rate limiting)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                     BACKEND APPLICATION (FastAPI)                      │
│   • REST API (/api/v1/alerts, /api/v1/fire, /api/v1/maritime)         │
│   • WebSocket Server (/api/v1/alerts/live) for real-time broadcasts    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FRONTEND DASHBOARD                               │
│   • React 18 + TypeScript + Vite + Tailwind CSS                        │
│   • Mapbox GL JS (WebGL 60fps) — 5 toggleable hazard layers           │
│   • Zustand global alert state + Socket.io real-time updates          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Confirmed Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite | Initialized, working |
| **Styling** | Tailwind CSS (v3) | Already in use — `App.tsx` uses Tailwind classes |
| **Map Engine** | Mapbox GL JS + react-map-gl | WebGL rendering, handles 1000s of moving vessel markers |
| **State** | Zustand (`alertStore.ts`) | Global alert state, active layer filters |
| **Charts** | Recharts | Risk score timelines, recurrence graphs |
| **Backend** | Python FastAPI (async) | All endpoints use `async def` + `AsyncSession` |
| **Task Queue** | Celery + Redis | Heavy ML jobs (satellite image processing) |
| **Scheduler** | APScheduler | AIS every 15min, FIRMS every 3hr, Sentinel every 24hr |
| **ML Vision** | PyTorch | U-Net (spill), ESRGAN (super-res) |
| **ML Tabular** | XGBoost | Fire 5-class classifier (FIRMS data is tabular) |
| **Anomaly** | Isolation Forest | Vessel behavioral risk scoring |
| **Geospatial** | GeoPandas + Shapely + Rasterio | Spatial joins, point-in-polygon, GeoTIFF processing |
| **Database** | PostgreSQL 15 + PostGIS | All spatial queries via `ST_*` functions |
| **Cache** | Redis | Latest AIS positions, WebSocket pub/sub |
| **Containers** | Docker Compose | Single `docker-compose up` spins everything |

---

## 3. Five Detection Modules & Agency Routing

| Module | Sensor / Input | Algorithm | Output | Target Indian Agency |
|---|---|---|---|---|
| **1. Oil Spill Detection** | Sentinel-2 + AIS | U-Net sheen segmenter + vessel proximity correlation | Polygon sheen + Risk-scored ship | Indian Coast Guard + INCOIS |
| **2. Illegal Fishing** | AIS feeds (AISHub) | Dark transponder gap inside MPA + vessel loitering | Red marker + MMSI + Gap duration | Indian Coast Guard + State Fisheries |
| **3. Fire Classification** | NASA FIRMS (VIIRS 375m NRT) | XGBoost 5-class: Industrial/Wildfire/Stubble/Gas Flare/Mining + CPCB spatial join | Classified alert + FRP MW + responding agency | PESO / Forest Dept / CAQM / IBM |
| **4. Industrial Pollution** | FIRMS historical archives | Spatial recurrence aggregation within 10km of CPCB clusters | Thermal recurrence heatmap | CPCB + State PCBs |
| **5. Landslide Risk** | Sentinel-1 SAR | InSAR ground phase interferometry + IMD rainfall overlay | Millimeter deformation heatmap | NDMA + SDMAs |

---

## 4. Folder → Layer Mapping (Who Owns What)

```
SATVIGIL/
│
├── backend/                    ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py             ← App entry point, router mounts, lifespan hooks
│   │   ├── core/
│   │   │   ├── config.py       ← All env vars (FIRMS key, AIS, Copernicus, Mapbox)
│   │   │   └── database.py     ← Async SQLAlchemy + PostGIS engine
│   │   ├── models/             ← SQLAlchemy ORM models (Alert, VesselRisk, ThermalHotspot)
│   │   ├── schemas/            ← Pydantic request/response schemas
│   │   ├── api/routes/         ← FastAPI route handlers per module
│   │   │   ├── alerts.py       ← Unified alerts endpoint
│   │   │   ├── maritime.py     ← Spill + fishing routes
│   │   │   ├── fire.py         ← Fire classification routes
│   │   │   ├── landslide.py    ← SAR deformation routes
│   │   │   ├── pollution.py    ← Industrial recurrence routes
│   │   │   └── health.py       ← Health check
│   │   ├── services/           ← Business logic per module
│   │   │   ├── fire/
│   │   │   │   └── firms_fetcher.py    ← FIRMS fetcher + 5-class fire classifier (WRITTEN)
│   │   │   └── maritime/
│   │   │       └── ais_fetcher.py      ← AIS fetcher + vessel risk scorer (WRITTEN)
│   │   ├── tasks/
│   │   │   └── scheduler.py    ← APScheduler job definitions (WRITTEN)
│   │   └── utils/              ← Shared helpers (geo validation, logging)
│   ├── alembic/                ← DB migration files (versions/ is EMPTY — migrations not created yet)
│   ├── tests/                  ← pytest test suite
│   └── requirements.txt        ← Pinned Python dependencies
│
├── frontend/                   ← React + TypeScript + Vite + Tailwind
│   ├── src/
│   │   ├── App.tsx             ← Root layout: map + alert sidebar (WRITTEN)
│   │   ├── components/
│   │   │   ├── map/            ← MapView.tsx (Mapbox GL JS India map)
│   │   │   ├── alerts/         ← AlertPanel.tsx
│   │   │   ├── dashboard/      ← DashboardHeader.tsx
│   │   │   └── shared/         ← Reusable UI components
│   │   ├── store/
│   │   │   └── alertStore.ts   ← Zustand state (WRITTEN)
│   │   ├── services/
│   │   │   └── websocket.ts    ← WebSocket client with auto-reconnect (WRITTEN)
│   │   ├── hooks/              ← Custom React hooks
│   │   ├── pages/              ← Route-level page components
│   │   └── types/              ← TypeScript type definitions
│   └── package.json            ← Dependencies including mapbox-gl, zustand, recharts
│
├── ml/                         ← ML model training/inference code (MOSTLY EMPTY)
│   ├── models/                 ← Empty — model architecture files go here
│   ├── training/               ← Empty — training scripts go here
│   ├── inference/              ← Empty — inference wrappers go here
│   ├── notebooks/              ← Jupyter notebooks for experimentation
│   └── data/                   ← Training data, sample images
│
├── data_pipeline/              ← Satellite data fetching & preprocessing
│   ├── fetchers/               ← Data source clients (Sentinel, FIRMS, AIS)
│   ├── processors/             ← Image preprocessing, feature extraction
│   ├── schedulers/             ← Cron/APScheduler definitions
│   └── validators/             ← Data quality checks
│
├── infrastructure/             ← Docker, Nginx, Redis configs
│   ├── docker/
│   │   └── init.sql            ← PostGIS extension initialization
│   ├── nginx/
│   │   └── nginx.conf          ← Reverse proxy config (production profile)
│   └── redis/
│       └── redis.conf          ← Redis persistence + security config
│
├── docs/                       ← Architecture, API, deployment docs
│   ├── hld/HLD.md              ← High-level design
│   ├── lld/LLD.md              ← Low-level design + algorithms
│   ├── api/                    ← Empty — API reference / Postman collection
│   ├── data/DATA_GUIDE.md      ← Dataset sources + API reference
│   ├── deployment/DEPLOYMENT.md
│   └── testing/TESTING_GUIDE.md
│
├── scripts/                    ← Utility scripts (EMPTY — AIS simulator pending)
├── tasks/                      ← Team task management
├── .ai/                        ← AI context system (this directory)
├── docker-compose.yml          ← Multi-container orchestration (WRITTEN)
├── .env.example                ← Environment template
└── .gitignore
```

---

## 5. Satellite Physics & Honest Latency Model

When asked to implement or document data pipelines, remember that satellites are governed by orbital physics:

- **MODIS (Terra & Aqua):** Revisit India 2–4 times/day. Latency ~3 hours.
- **VIIRS (Suomi-NPP & NOAA-20):** Revisit India 2–4 times/day (375m resolution). Latency ~3 hours.
- **Sentinel-2 (Optical):** Revisit every 2–3 days. Latency ~24 hours. (Requires clear skies / daytime)
- **Sentinel-1 (SAR Radar):** Revisit every 6–12 days. Latency ~24 hours. (Works through clouds and night)
- **AIS (Vessel tracking):** Continuous near real-time — ships broadcast every few minutes. **This is the only truly live feed.**

**NEVER claim "real-time live satellite video." Always frame as "near real-time, bounded by orbital revisit physics."**

---

## 6. What is Written vs. Empty (As of Sprint 1)

| Component | Status | Notes |
|---|---|---|
| `backend/app/main.py` | ✅ Written | App entry, all routers mounted |
| `backend/app/core/config.py` | ✅ Written | All env vars configured |
| `backend/app/core/database.py` | ✅ Written | Async PostGIS engine |
| `backend/app/models/` | ✅ Written | Alert, VesselRisk, ThermalHotspot models |
| `backend/app/services/fire/firms_fetcher.py` | ✅ Written | FIRMS fetcher + 5-class classifier |
| `backend/app/services/maritime/ais_fetcher.py` | ✅ Written | AIS fetcher + vessel risk scorer |
| `backend/app/tasks/scheduler.py` | ✅ Written | APScheduler jobs |
| `backend/app/api/routes/*.py` | 🟡 Stub | Route files exist but return mock data |
| `backend/alembic/versions/` | ❌ Empty | No migrations yet — tables via `create_all` |
| `backend/app/services/landslide/` | ❌ Empty | Not started |
| `backend/app/services/pollution/` | ❌ Empty | Not started |
| `frontend/src/App.tsx` | ✅ Written | Layout skeleton |
| `frontend/src/store/alertStore.ts` | ✅ Written | Zustand store |
| `frontend/src/services/websocket.ts` | ✅ Written | WS client |
| `frontend/src/components/map/` | 🟡 Exists | MapView structure exists, needs Mapbox wiring |
| `frontend/src/components/alerts/` | 🟡 Exists | AlertPanel structure exists, needs content |
| `ml/` | ❌ Empty | All subdirs empty — models not written yet |
| `scripts/` | ❌ Empty | AIS simulator pending |
| `data_pipeline/` | ❌ Empty | Dirs exist, no files |
