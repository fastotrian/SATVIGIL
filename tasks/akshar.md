# Task Sheet — Akshar

- **Name:** Akshar
- **Role:** Core Full-Stack Engineer (Backend API, Database & Frontend UI)
- **Branch Format:** `feat/akshar-<task-id>` (e.g. `feat/akshar-task-m05`)
- **Status:** 🟢 Heavy Active Focus — Sprint 3

---

## 🎯 Active Tasks Queue (Ordered by Priority)

### 🔹 Part 1: Backend & Database Engine

1. [x] **TASK-M05: Alerts Database Persistence & Live Query Route**
   - **Priority:** 🔴 Critical
   - **Goal:** Replace in-memory mocks in `backend/app/api/routes/alerts.py` with live async SQLAlchemy queries.
   - **Requirements:**
     - Query `alerts` table with filters: `alert_type`, `risk_level`, `is_active`.
     - Implement pagination via `limit` (default 50) and `offset`.
     - Implement `POST /api/v1/alerts/{id}/acknowledge` endpoint.
     - Broadcast newly created alerts to active WebSocket connections (`/api/v1/alerts/live`).
   - **Deliverable:** Working `alerts.py` with real DB integration and WebSocket push.

2. [ ] **TASK-M06: PostGIS Spatial Radius Search Endpoint**
   - **Priority:** 🔴 High
   - **Goal:** Implement `GET /api/v1/alerts/near?lat=...&lon=...&radius_km=...` using PostGIS `ST_DWithin`.
   - **Requirements:**
     - Use `ST_DWithin` with geography cast for precise kilometer radius calculation on WGS84 (SRID 4326).
     - Return matching alerts, vessels, and hotspots within the radius, sorted by distance.
   - **Deliverable:** Spatial query function in `alerts.py` with sub-50ms benchmark.

3. [ ] **TASK-F02: Fire Classification & Hotspots API Routes**
   - **Priority:** 🔴 High
   - **Goal:** Implement `GET /api/v1/fire/hotspots` and `GET /api/v1/fire/hotspots/{id}` in `backend/app/api/routes/fire.py`.
   - **Requirements:**
     - Query parameters: `fire_type` (industrial, gas_flare, stubble, wildfire, mining), `min_frp`, `start_date`, `end_date`, and `near_cpcb_only`.
     - Enrich responses with `responding_agency` and `recommended_action` using the decision matrix.
     - Return paginated `HotspotListResponse` using `backend/app/schemas/hotspot.py`.
   - **Deliverable:** Fully functional `fire.py` route connected to PostGIS.

4. [ ] **TASK-M07: AIS Background Worker & PostGIS Upsert**
   - **Priority:** 🟡 Medium
   - **Goal:** Connect `ais_fetcher.py` to APScheduler or Celery to run every 15 minutes.
   - **Requirements:**
     - Ingest live AIS feed or fallback to `data/demo/ais_demo_scenario.json`.
     - Calculate temporal gap (`ais_gap_minutes`) against previous record for same MMSI.
     - Upsert records into `vessel_risk_records` table with PostGIS point geometry.
   - **Deliverable:** `backend/app/tasks/ais_worker.py`.

---

### 🔹 Part 2: Frontend UI & Interactive Analytics

5. [ ] **TASK-UI05: Vessel & Alert Detail Slide-In Drawer**
   - **Priority:** 🔴 High
   - **Goal:** When a user clicks a vessel marker or alert card, slide open a detailed inspection drawer from the right.
   - **Requirements:**
     - Display vessel metadata: Name, Flag, IMO/MMSI, Dimensions, Draft, Speed, Course.
     - Display 4-Signal ML Risk Breakdown bars: Distance (40%), Vessel Type (25%), Course Alignment (20%), Anomaly (15%).
     - Action buttons: `Acknowledge Alert`, `Dispatch Coast Guard Notice`, `Export Incident Report`.
     - Styled with Tailwind CSS v3 with smooth transition animations.
   - **Deliverable:** `frontend/src/components/alerts/AlertDetailsDrawer.tsx`.

6. [ ] **TASK-UI08: Fire & Thermal Hotspots WebGL Map Layer**
   - **Priority:** 🔴 High
   - **Goal:** Render thermal hotspots on `MapView.tsx` when the "Fire/Thermal" layer toggle is enabled.
   - **Requirements:**
     - Color code hotspots by classification: Gas Flare (Violet), Industrial (Orange), Stubble (Yellow), Wildfire (Red).
     - Cluster circles at low zoom levels, individual glowing heat dots at high zoom levels.
     - Hover tooltip displaying fire type, FRP in MW, and satellite confidence.
   - **Deliverable:** Integrated layer in `MapView.tsx`.

7. [ ] **TASK-UI07: Tactical Audio Alarm & Desktop Notifications**
   - **Priority:** 🟡 Medium
   - **Goal:** Provide audible and visual alarms when a `CRITICAL` risk threat is received.
   - **Requirements:**
     - Short tactical sonar pulse audio when a new dark ship or oil spill is pushed via WebSocket.
     - Browser `Notification` API integration with user opt-in toggle in the header.
     - Mute/Unmute audio button in `DashboardHeader.tsx`.
   - **Deliverable:** `frontend/src/services/soundEffects.ts` and header controls.

---

## 📋 Task History & Queue

| Task ID | Description | Priority | Assigned Date | Status | PR / Notes |
|---|---|---|---|---|---|
| TASK-M01 | Pydantic v2 Schemas — `alert.py`, `vessel.py`, `hotspot.py`, `__init__.py` | 🔴 High | 2026-09-08 | ✅ Done | Merged into `main` |
| TASK-M05 | Alerts DB Query & WebSocket broadcast | 🔴 High | 2026-09-08 | ✅ Done | Completed and implemented |
| TASK-M06 | Spatial Radius Search via PostGIS `ST_DWithin` | 🔴 High | 2026-09-08 | ⏳ Queued | Up next after M05 |
| TASK-F02 | Fire Classification & Hotspots API Routes | 🔴 High | 2026-09-08 | ⏳ Queued | Backend API |
| TASK-UI05 | Vessel & Alert Detail Slide-In Drawer | 🔴 High | 2026-09-08 | ⏳ Queued | Frontend UI |
| TASK-UI08 | Thermal Hotspots WebGL Map Layer | 🔴 High | 2026-09-08 | ⏳ Queued | Frontend Mapbox |
| TASK-M07 | AIS Background Worker & PostGIS Upsert | 🟡 Medium | 2026-09-08 | ⏳ Queued | Worker Pipeline |
| TASK-UI07 | Tactical Audio Alarm & Desktop Notifications | 🟡 Medium | 2026-09-08 | ⏳ Queued | Frontend Sound/Push |

---

## 🛑 Blockers & Help Needed
*If stuck: Follow the 15-minute rule before pinging Ravi.*

| Date | Issue / Error | What I Tried | Status |
|---|---|---|---|
| — | None | — | — |

---

## 📚 Quick Reference
- Master Task Backlog: [TASK_BACKLOG.md](TASK_BACKLOG.md)
- API Reference: [.ai/API_REFERENCE.md](../.ai/API_REFERENCE.md)
- DB Models: [backend/app/models/alert.py](../backend/app/models/alert.py)
- Pydantic Schemas: [backend/app/schemas/](../backend/app/schemas/)
- Map Component: [frontend/src/components/map/MapView.tsx](../frontend/src/components/map/MapView.tsx)
