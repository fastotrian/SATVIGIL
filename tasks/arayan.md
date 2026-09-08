# Task Sheet — Arayan

- **Name:** Arayan
- **Role:** Data Engineering / Pollution & Flaring Analytics
- **Branch Format:** `feat/arayan-<task-id>` (e.g. `feat/arayan-task-f03`)
- **Status:** 🟢 Active — Sprint 3

---

## 🎯 Current Focus & Active Tasks

- [ ] **TASK-F03: Chronic Industrial Pollution & Recurrence Tracker**
  - **Priority:** 🔴 High
  - **Goal:** Build the spatial recurrence clustering engine exposed via `GET /api/v1/pollution/clusters`.
  - **Requirements:**
    - Group thermal hotspots spatially by 0.01° grid cells (~1.1 km resolution).
    - Aggregate recurrence counts over a rolling 30-day window.
    - Flag locations with `recurrence_count >= 3` as chronic industrial violators (e.g., unmonitored brick kilns, illegal smelters).
    - Return cluster centroids, bounding boxes, dominant fire type, and responsible regional CPCB office.
  - **Deliverable:** `backend/app/services/pollution/cluster_analyzer.py` and connected API route.

- [ ] **TASK-F04: VIIRS Nightfire (Gas Flare) Dataset Integration**
  - **Goal:** Ingest and parse VIIRS Nightfire (VNF) combustion data from NOAA/Colorado School of Mines.
  - **Requirements:**
    - Download and process daily VNF M10/SWIR detections for India offshore & onshore oil refineries (Bombay High, Assam, Gujarat).
    - Calculate combustion temperature (Kelvin) and cross-reference against FIRMS hotspots to distinguish routine gas flaring from unexpected refinery fires.
  - **Deliverable:** `data_pipeline/fetchers/vnf_fetcher.py` and test dataset in `data/vnf/`.

---

## 📋 Task History & Queue

| Task ID | Description | Priority | Assigned Date | Status | PR / Notes |
|---|---|---|---|---|---|
| TASK-F03 | Chronic Pollution Recurrence Clustering | 🔴 High | 2026-09-08 | 🟡 In Progress | Active assignment |
| TASK-F04 | VIIRS Nightfire Ingestion Script | 🟡 Medium | 2026-09-08 | ⏳ Queued | Up next after F03 |

---

## 🛑 Blockers & Help Needed
*If stuck: Check docs and 15-minute rule before pinging Ravi.*

| Date | Issue / Error | What I Tried | Status |
|---|---|---|---|
| — | None | — | — |

---

## 📚 Quick Reference
- Master Task Backlog: [TASK_BACKLOG.md](TASK_BACKLOG.md)
- FIRMS Fetcher: [backend/app/services/fire/firms_fetcher.py](../backend/app/services/fire/firms_fetcher.py)
- Models: [backend/app/models/alert.py](../backend/app/models/alert.py)
- Data Guide: [docs/data/DATA_GUIDE.md](../docs/data/DATA_GUIDE.md)
