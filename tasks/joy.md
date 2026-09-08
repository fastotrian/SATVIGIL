# Task Sheet — Joy

- **Name:** Joy
- **Role:** Data Engineering / FIRMS Sensor Pipeline
- **Branch Format:** `feat/joy-<task-id>` (e.g. `feat/joy-task-f01`)
- **Status:** 🟢 Active — Sprint 3

---

## 🎯 Current Focus & Active Tasks

- [ ] **TASK-F01: FIRMS Live Data Stream Fetcher & DB Ingestion Engine**
  - **Priority:** 🔴 High (PS 162 Data Foundation)
  - **Goal:** Connect `backend/app/services/fire/firms_fetcher.py` to an asynchronous database writer that ingests real-time satellite fire hotspots into the `thermal_hotspots` PostGIS table.
  - **Requirements:**
    - Parse MODIS (1km) and VIIRS (375m) CSV/JSON streams from NASA FIRMS API.
    - Check spatial distance against CPCB polluted clusters and tag `near_cpcb_cluster=True` if within 10 km.
    - Prevent duplicate inserts using `(latitude, longitude, acquired_at)` compound uniqueness.
    - Fallback gracefully to offline sample data if `FIRMS_MAP_KEY` is not provided.
  - **Deliverable:** `backend/app/services/fire/firms_processor.py` with unit tests.

- [ ] **TASK-F05: FIRMS Offline Mock Seed Generator**
  - **Priority:** 🟡 Medium
  - **Goal:** Create a realistic sample dataset of 50+ thermal hotspots across India (stubble burning in Punjab/Haryana, industrial furnaces in Vapi/Ankleshwar, gas flaring at Bombay High, forest fires in Uttarakhand).
  - **Deliverable:** `data/demo/firms_demo_scenario.json` and seeding script in `scripts/seed_hotspots.py`.

---

## 📋 Task History & Queue

| Task ID | Description | Priority | Assigned Date | Status | PR / Notes |
|---|---|---|---|---|---|
| TASK-F01 | FIRMS Live Fetcher → DB Persistence | 🔴 High | 2026-09-08 | 🟡 In Progress | Active assignment |
| TASK-F05 | FIRMS Offline Demo Seed Generator | 🟡 Medium | 2026-09-08 | ⏳ Queued | Up next after F01 |

---

## 🛑 Blockers & Help Needed
*If stuck: Follow the 15-minute rule before pinging Ravi.*

| Date | Issue / Error | What I Tried | Status |
|---|---|---|---|
| — | None | — | — |

---

## 📚 Quick Reference
- Master Task Backlog: [TASK_BACKLOG.md](TASK_BACKLOG.md)
- FIRMS Fetcher Code: [backend/app/services/fire/firms_fetcher.py](../backend/app/services/fire/firms_fetcher.py)
- Hotspot Schema: [backend/app/schemas/hotspot.py](../backend/app/schemas/hotspot.py)
- DB Models: [backend/app/models/alert.py](../backend/app/models/alert.py)
