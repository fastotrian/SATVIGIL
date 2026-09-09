# SATVIGIL — Live Project State & Work Log

> **Note to any AI Assistant:** Read this file first to understand where the project stands right now.
> **When you finish any work, update this file with your changes before ending your response!**

---

## 🕒 Last Updated: 2026-09-08 (Sprint 2 — PS 143 COMPLETE: Maritime Oil Spill & AIS Correlation End-to-End)

> **Active Plan:** Full PS 143 build order with color system, Gemini model assignments,
> and part-by-part checkpoints is in `implementation_plan.md` (Antigravity artifact).
> - **PART 1:** ✅ Constants (`riskColors.ts`, `constants.py`) & shared types (`maritime.ts`) complete.
> - **PART 2:** ✅ Schemas, real maritime API routes, and AIS simulator complete (`simulate_ais_feed.py`, `ais_demo_scenario.json`).
> - **PART 3:** ✅ Complete Frontend UI Layer (Map, Header, Alert Panel, Zustand Store; verified Vite build).
> - **PART 4:** ✅ Oil Spill Attribution & Simulation Pipeline:
>   - `spill_attribution.py`: 4-signal multi-factor scoring extracted from ML notebook (40% distance, 25% vessel type, 20% heading, 15% anomaly).
>   - `POST /api/v1/maritime/simulate-spill`: Real-time suspect vessel attribution returning MT GUJARAT PRIDE as #1 suspect (0.95 risk).
>   - `MapView.tsx`: Dynamic spill polygon overlay, interactive suspect attribution popup, camera fly-to, and live demo trigger.
> - **PART 5:** ✅ Polish + Demo Scenario Script:
>   - `StaticPins.tsx`: Converted to high-reliability HTML `<Marker>` components to eliminate WebGL 403 font glyph PBF errors.
>   - `DEMO_TRACKS_GEOJSON`: Route vector lines including orange normal navigation and dashed red 45-min AIS blackout gap.
>   - `docs/demo/DEMO_RUNBOOK.md`: 5-minute SIH live pitch & demo presentation guide with fallback offline contingency.
>   - `MapView.tsx`: Configured clean ESRI Dark Gray Canvas basemap with dark background layer, enabled raster overzooming up to zoom 18, and migrated radar pulse to native CSS hardware-accelerated DOM markers, preventing any WebGL render interrupts on zoom/pan.
>   - `maritime.py`: Fixed missing return statement on `GET /api/v1/maritime/spills`.
> - **ALL PS 143 PARTS COMPLETE & VERIFIED.** Ready for PS 162 (Thermal Hotspots & Fire Classification).

---

## ✅ What is Completed & In Git

### 1. Architecture & Documentation
- Full High-Level Design ([docs/hld/HLD.md](../docs/hld/HLD.md)) — 5 detection modules, data flow.
- Low-Level Design & Algorithms ([docs/lld/LLD.md](../docs/lld/LLD.md)).
- Data Ingestion & Sensors Guide ([docs/data/DATA_GUIDE.md](../docs/data/DATA_GUIDE.md)).
- Deployment Guide ([docs/deployment/DEPLOYMENT.md](../docs/deployment/DEPLOYMENT.md)).
- Testing Guide ([docs/testing/TESTING_GUIDE.md](../docs/testing/TESTING_GUIDE.md)).
- SIH Demo Runbook & Script ([docs/demo/DEMO_RUNBOOK.md](../docs/demo/DEMO_RUNBOOK.md)) — 5-minute pitch script & fallback plan.

### 2. Core Backend — Written & Functional

| File | Status | Notes |
|---|---|---|
| `backend/app/main.py` | ✅ Done | FastAPI app, CORS, 5 router mounts, resilient lifespan hooks with demo fallback |
| `backend/app/api/routes/maritime.py` | ✅ Done | AIS fetcher, risk scoring, dark vessel simulation, spill endpoints |
| `backend/app/core/config.py` | ✅ Done | All env vars (FIRMS, AIS, Copernicus, Mapbox, Redis) |
| `backend/app/core/constants.py` | ✅ Done | Risk thresholds, alert labels, AIS gap limits, India bounds |
| `backend/app/core/database.py` | ✅ Done | Async PostGIS engine, `get_db()` dependency |
| `backend/app/models/alert.py` | ✅ Done | `Alert`, `VesselRiskRecord`, `ThermalHotspot` + `VesselAISHistory`, `CPCBPollutedArea`, `LandslideRiskZone`, `LandslideMonitoringZone` updated per SIH.pdf |
| `backend/app/schemas/maritime.py` | ✅ Done | Pydantic v2 schemas: VesselResponse, SpillEventResponse, AlertResponse |
| `backend/app/schemas/alert.py` | ✅ Done | Pydantic v2 schemas for AlertSummary, AlertResponse, AlertNearResponse |
| `backend/app/schemas/vessel.py` | ✅ Done | Pydantic v2 schemas for VesselSchema, SpillAlertSchema |
| `backend/app/schemas/hotspot.py` | ✅ Done | Pydantic v2 schemas for ThermalHotspotSchema, HotspotListResponse |
| `backend/app/schemas/__init__.py` | ✅ Done | Package re-exports for all domain schemas |
| `backend/app/services/fire/firms_fetcher.py` | ✅ Done | FIRMS API fetcher + 5-class fire classifier + CPCB clusters + agency routing |
| `backend/app/services/maritime/ais_fetcher.py` | ✅ Done | AIS fetcher + vessel risk scorer + India MPA zones |
| `backend/app/services/maritime/spill_attribution.py` | ✅ Done | 4-signal ML attribution: proximity, vessel type, heading alignment, SVR anomaly |
| `backend/app/tasks/scheduler.py` | ✅ Done | APScheduler: AIS 15min, FIRMS 3hr, Sentinel 24hr |
| `backend/requirements.txt` | ✅ Done | All deps pinned |

### 3. Frontend — Fully Implemented UI Layer
 
| File | Status | Notes |
|---|---|---|
| `frontend/src/App.tsx` | ✅ Done | Root layout: header + full-screen map + alert sidebar |
| `frontend/src/store/alertStore.ts` | ✅ Done | Zustand store: alerts, vessels, layer filters, selection |
| `frontend/src/components/map/MapView.tsx` | ✅ Done | Mapbox GL circle layers, radar pulses, spill polygons, MPAs, popups |
| `frontend/src/components/dashboard/DashboardHeader.tsx` | ✅ Done | SATVIGIL header, live threat pills (Critical/Warning/Clear), feeds |
| `frontend/src/components/alerts/AlertPanel.tsx` | ✅ Done | Real-time threat alert cards with vessel click-drilldown |
| `frontend/src/components/map/StaticPins.tsx` | ✅ Done | Strategic fixed pins: Bombay High ONGC, JNPT, Kandla, MPAs |
| `frontend/src/constants/riskColors.ts` | ✅ Done | Single source of truth for risk hex colors & thresholds |
| `frontend/src/types/maritime.ts` | ✅ Done | TypeScript interfaces (Vessel, SpillEvent, SpillCandidate, Alert) |
| `frontend/src/services/websocket.ts` | ✅ Done | WebSocket client with auto-reconnect |
| `frontend/package.json` | ✅ Done | mapbox-gl, zustand, recharts, tailwindcss all declared |

### 4. Infrastructure
- `docker-compose.yml` — PostGIS 15, Redis, FastAPI backend, Celery worker, React frontend, Nginx (production profile).
- `infrastructure/docker/init.sql` — PostGIS extension initialization.
- `infrastructure/redis/redis.conf` — Redis config.
- `.env.example` — Template with all required env vars.

### 5. Team Task Allocation Board
- `tasks/` directory: `README.md`, `TASK_BACKLOG.md` (categorized), individual sheets for all 6 members.

### 6. AI Context System (`./ai/`)
- `README.md`, `CURRENT_STATE.md`, `ARCHITECTURE.md`, `DATABASE_AND_MODELS.md`,
  `CODING_STANDARDS.md`, `TEAM_AND_TASKS.md` — **all updated with confirmed tech stack**.
- **NEW (Sprint 1 end):** `PITCH_AND_PRODUCT.md` — product rationale, PS 143/162, agency routing table,
  all fire type classifications, hackathon build priority order, pitch references.
- **NEW (Sprint 1 end):** `API_REFERENCE.md` — all routes, request/response schemas, WebSocket protocol.
- AI entrypoints: `AGENTS.md`, `CLAUDE.md`, `.cursorrules` at root.
- All paths are repository-relative (not absolute) for cross-platform compatibility.

---

## ❌ What is Confirmed EMPTY / Not Started

- `backend/app/api/routes/*.py` — `maritime.py` implemented with real logic; others return mock data
- `backend/alembic/versions/` — **NO migrations created yet** (tables created via `create_all` on startup)
- `backend/app/services/landslide/` — directory exists, **no code**
- `backend/app/services/pollution/` — directory exists, **no code**
- `backend/app/schemas/` — `maritime.py` and `alert.py` created; other domain schemas pending
- `ml/` — all subdirectories empty except `ml/notebooks/vessel_oil_spill_risk_scoring.ipynb`
- `scripts/simulate_ais_feed.py` — ✅ Created & functional
- `data_pipeline/` — directories exist, **no pipeline code**
- `docs/api/` — **empty**, API collection not created
- `docs/architecture/` — **empty**

---

## 🟡 What is In Progress / Immediately Ready to Build

### Sprint 2 Priority Order (Maritime First, Per Hackathon Plan):

**Track 1: Maritime Module (Spill + Fishing) — PRIMARY PS 143**
1. Wire real AIS data flow into the already-written `ais_fetcher.py` → persist to DB
2. Implement `GET /api/v1/maritime/vessels` with real PostGIS queries
3. Implement `GET /api/v1/maritime/spills` with Sentinel-2 spill detection
4. Write Pydantic schemas in `backend/app/schemas/`
5. Write AIS mock data generator (`scripts/simulate_ais_feed.py`) for dark ship demo

**Track 2: Frontend Map (parallel with Track 1)**
1. Wire Mapbox GL JS into `frontend/src/components/map/MapView.tsx`
2. Add vessel markers from real AIS API data
3. Implement layer toggles (oil spill / illegal fishing / fire / landslide / pollution)
4. Build Alert sidebar with real-time WebSocket updates

**Track 3: Fire Classification (PS 162 — after Track 1)**
1. Connect FIRMS fetcher → DB write → classification query
2. Implement `GET /api/v1/fire/hotspots` with real data + classification
3. Add recurrence tracking logic in `GET /api/v1/pollution/clusters`

---

## 🎯 Immediate Next Tasks (Sprint 3 Active Allocations)

- [x] **PS 143 (Oil Spill & Dark Vessel Attribution):** 100% Complete, Verified End-to-End, and merged to `main`.
- [ ] **Track 1: Core Full-Stack Engineering (Akshar — Heavy Focus):**
  - **Backend:**
    - [x] `TASK-M05`: Live SQLAlchemy async queries in `routes/alerts.py` with pagination + WebSocket broadcast.
    - [x] `TASK-M06`: Spatial radius search endpoint using PostGIS `ST_DWithin` (`/api/v1/alerts/near`).
    - [x] `TASK-F02`: `GET /api/v1/fire/hotspots` with 5-class filtering and responding agency routing.
    - [x] `TASK-M07`: AIS Background Worker & PostGIS upsert task.
  - **Frontend:**
    - [x] `TASK-UI05`: Vessel & Alert slide-in detail drawer in Tailwind CSS.
    - [x] `TASK-UI08`: Fire & Thermal Hotspots WebGL Map Layer on `MapView.tsx`.
    - [x] `TASK-UI07`: Tactical audio alarms & browser push notifications for critical threats.
- [ ] **Track 2: FIRMS Sensor Ingestion Pipeline (Joy):**
  - [x] `TASK-F01`: FIRMS live data stream fetcher → PostGIS DB upsert with CPCB 10km proximity tag.
  - [x] `TASK-F05`: FIRMS offline demo dataset generator (`scripts/seed_hotspots.py`).
- [ ] **Track 3: Industrial Pollution & Gas Flaring (Arayan):**
  - [x] `TASK-F03`: 30-day spatial recurrence tracker (`GET /api/v1/pollution/clusters`).
  - [ ] `TASK-F04`: VIIRS Nightfire combustion temperature integration.
- [ ] **Track 4: Frontend Telemetry & Global Search (Saksham):**
  - [ ] `TASK-UI06`: Recharts telemetry curves (speed over time, FRP trends).
  - [ ] `TASK-UI09`: Global Search & Autocomplete toolbar in `DashboardHeader.tsx`.
- [ ] **Track 5: QA Automation & Documentation (Krishika):**
  - [ ] `TASK-J02`: Pytest automated suite for schemas and API integration.
  - [ ] `TASK-D01`: Production Postman/Bruno API Collection.

---

## 📋 Key Decisions Made (Do Not Revisit Without Team Discussion)

| Decision | Choice | Reason |
|---|---|---|
| Primary PS | PS 143 (Oil Spill) | Best public data availability, visually impressive demo |
| Secondary PS | PS 162 (Fire Classification) | Reuses same FIRMS pipeline |
| Map library | **Mapbox GL JS** (over Leaflet) | WebGL handles hundreds of moving vessel markers |
| Styling | **Tailwind CSS v3** | Already in use in App.tsx — do not change |
| Fire classifier | **XGBoost** (not deep learning) | FIRMS data is tabular CSV, rule-based + XGBoost is faster & explainable |
| Vessel risk | **Isolation Forest + rules** | AIS behavioral features, not image data |
| Spill detection | **PyTorch U-Net** | Pixel-level segmentation on Sentinel-2 |
| Super-res | **ESRGAN pretrained** | Don't train from scratch during hackathon |
| Landslide | **SAR InSAR — build last** | Sentinel-1 revisit 6-12 days, use historical pairs for demo |
| DB migrations | `create_all` for now | Will add Alembic migrations when schema stabilizes |
