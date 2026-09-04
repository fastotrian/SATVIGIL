# SATVIGIL — Live Project State & Work Log

> **Note to any AI Assistant:** Read this file first to understand where the project stands right now. **When you finish any work, update this file with your changes!**

---

## 🕒 Last Updated: 2026-09-05 (Sprint 1 — Architecture & Foundation)

---

## ✅ What is Completed & In Git

1. **Architecture & Documentation:**
   - Full High-Level Design ([docs/hld/HLD.md](../docs/hld/HLD.md)) covering 5 detection modules.
   - Low-Level Design & Algorithms ([docs/lld/LLD.md](../docs/lld/LLD.md)).
   - Data Ingestion & Sensors Guide ([docs/data/DATA_GUIDE.md](../docs/data/DATA_GUIDE.md)).
   - Deployment Guide ([docs/deployment/DEPLOYMENT.md](../docs/deployment/DEPLOYMENT.md)).
   - Testing Guide ([docs/testing/TESTING_GUIDE.md](../docs/testing/TESTING_GUIDE.md)).

2. **Core Backend Foundation:**
   - FastAPI app initialized with CORS, router mounts (`backend/app/main.py`).
   - Async SQLAlchemy session and PostGIS engine configured (`backend/app/core/database.py`).
   - Database models written with `GeoAlchemy2`:
     - `Alert` with `Geometry("POINT", srid=4326)`
     - `VesselRiskRecord` (AIS dark vessel tracking)
     - `ThermalHotspot` (FIRMS thermal radiation)
   - Route stubs for alerts, fire, maritime, landslide, pollution, and health.

3. **Infrastructure & Containers:**
   - Multi-container `docker-compose.yml` (PostGIS 15, Redis, FastAPI backend, React frontend).
   - PostGIS extension automated initialization script (`infrastructure/docker/init.sql`).
   - Redis cache config (`infrastructure/redis/redis.conf`).

4. **Team Task Allocation Board:**
   - Created `tasks/` directory with `README.md`, `TASK_BACKLOG.md` (categorized for juniors/seniors).
   - Individual task sheets for Ravi Yadav, Joy, Saksham, Arayan, Krishika, Akshar.

5. **Cleaned Repository Structure:**
   - Removed accidental duplicate nested `SATVIGIL/` subfolder. Clean root structure maintained.

6. **AI Context System & Cross-Platform Relative Paths:**
   - Created `.ai/` directory (`README.md`, `CURRENT_STATE.md`, `ARCHITECTURE.md`, `DATABASE_AND_MODELS.md`, `CODING_STANDARDS.md`, `TEAM_AND_TASKS.md`).
   - Added entrypoints `AGENTS.md`, `CLAUDE.md`, `.cursorrules`.
   - All links converted to repository-relative paths (`.ai/...`, `../docs/...`, `TASK_BACKLOG.md`) so teammates on Windows, Mac, or Linux have working links regardless of folder location.

---

## 🟡 What is In Progress / Ready to Build

1. **Real PostGIS DB Queries:**
   - Implement real queries in `backend/app/api/routes/alerts.py` replacing the mock response.
   - Add radius / bounding-box filter using PostGIS `ST_DWithin`.
2. **Data Pipeline Fetchers:**
   - Implement live fetch in `backend/app/services/fire/firms_fetcher.py`.
   - Implement AIS simulator in `scripts/simulate_ais_feed.py` for dark ship demo.
3. **Frontend Map UI:**
   - Mapbox GL JS map view in `frontend/src/components/map/MapView.tsx`.
   - Alert feed sidebar & layer toggles.

---

## 🎯 Immediate Next Priority
- [ ] Connect `backend/app/api/routes/alerts.py` to the actual PostgreSQL database.
- [ ] Add Alembic database migrations or auto-table creation on FastAPI startup.
- [ ] Test local docker container startup (`docker-compose up -d db redis`).
