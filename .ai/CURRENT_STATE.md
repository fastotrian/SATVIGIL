# SATVIGIL — Live Project State & Work Log

> **Note to any AI Assistant:** Read this file first to understand where the project stands right now.
> **When you finish any work, update this file with your changes before ending your response!**

---

## 🕒 Last Updated: 2026-09-05 (Sprint 1 — Architecture, Foundation & AI Context)

---

## ✅ What is Completed & In Git

### 1. Architecture & Documentation
- Full High-Level Design ([docs/hld/HLD.md](../docs/hld/HLD.md)) — 5 detection modules, data flow.
- Low-Level Design & Algorithms ([docs/lld/LLD.md](../docs/lld/LLD.md)).
- Data Ingestion & Sensors Guide ([docs/data/DATA_GUIDE.md](../docs/data/DATA_GUIDE.md)).
- Deployment Guide ([docs/deployment/DEPLOYMENT.md](../docs/deployment/DEPLOYMENT.md)).
- Testing Guide ([docs/testing/TESTING_GUIDE.md](../docs/testing/TESTING_GUIDE.md)).

### 2. Core Backend — Written & Functional

| File | Status | Notes |
|---|---|---|
| `backend/app/main.py` | ✅ Done | FastAPI app, CORS, 5 router mounts, lifespan hooks |
| `backend/app/core/config.py` | ✅ Done | All env vars (FIRMS, AIS, Copernicus, Mapbox, Redis) |
| `backend/app/core/database.py` | ✅ Done | Async PostGIS engine, `get_db()` dependency |
| `backend/app/models/alert.py` | ✅ Done | `Alert`, `VesselRiskRecord`, `ThermalHotspot` with GeoAlchemy2 |
| `backend/app/services/fire/firms_fetcher.py` | ✅ Done | FIRMS API fetcher + 5-class fire classifier + CPCB clusters + agency routing |
| `backend/app/services/maritime/ais_fetcher.py` | ✅ Done | AIS fetcher + vessel risk scorer + India MPA zones |
| `backend/app/tasks/scheduler.py` | ✅ Done | APScheduler: AIS 15min, FIRMS 3hr, Sentinel 24hr |
| `backend/requirements.txt` | ✅ Done | All deps pinned |

### 3. Frontend — Skeleton Written

| File | Status | Notes |
|---|---|---|
| `frontend/src/App.tsx` | ✅ Done | Root layout: map + alert sidebar using Tailwind |
| `frontend/src/store/alertStore.ts` | ✅ Done | Zustand global alert state |
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

- `backend/app/api/routes/*.py` — route files exist but **all return mock data**, no real DB queries
- `backend/alembic/versions/` — **NO migrations created yet** (tables created via `create_all` on startup)
- `backend/app/services/landslide/` — directory exists, **no code**
- `backend/app/services/pollution/` — directory exists, **no code**
- `backend/app/schemas/` — exists, **no Pydantic schemas written yet**
- `ml/` — all subdirectories empty, **no model code**
- `scripts/` — **empty**, AIS simulator not created
- `data_pipeline/` — directories exist, **no pipeline code**
- `docs/api/` — **empty**, API collection not created
- `docs/architecture/` — **empty**
- `frontend/src/components/map/MapView.tsx` — **needs Mapbox GL JS implementation**
- `frontend/src/components/alerts/AlertPanel.tsx` — **needs real implementation**
- `frontend/src/components/dashboard/DashboardHeader.tsx` — **needs implementation**

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

## 🎯 Immediate Next Task (What to Do RIGHT NOW)

- [ ] Create Pydantic schemas in `backend/app/schemas/` (vessel, alert, hotspot)
- [ ] Implement real DB query in `backend/app/api/routes/alerts.py` replacing mock response
- [ ] Implement `backend/app/api/routes/maritime.py` with vessel list endpoint
- [ ] Test local docker container startup: `docker-compose up -d postgres redis`
- [ ] Create `scripts/simulate_ais_feed.py` for demo scenarios (dark vessel off Gujarat coast)

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
