# SATVIGIL — Master Task Backlog & Engineering Roadmap

> **For Team Members:** All tasks are categorized by domain, complexity, and priority.
> - When picking a task, change status from `[AVAILABLE]` to `[CLAIMED by <Your Name>]`.
> - Add the task to your personal file (`tasks/<your_name>.md`).
> - Create a dedicated Git branch: `feat/<your-name>-<task-id>` (e.g., `feat/akshar-task-m05`).
> - Even when accelerating development with AI tools, ensure code meets `.ai/CODING_STANDARDS.md` and passes tests before creating PRs.

---

## ✅ Completed Tasks (Sprint 1 & Sprint 2 PS 143 MVP)

- [x] **[DONE — Akshar]** **TASK-M01: Pydantic v2 Schemas** (`alert.py`, `vessel.py`, `hotspot.py`, `__init__.py`)
- [x] **[DONE — Ravi / AI]** **TASK-M02: Maritime Vessels Endpoint & Scenario Fallback** (`backend/app/api/routes/maritime.py`)
- [x] **[DONE — Ravi / AI]** **TASK-M04: AIS Mock Data Generator & Dark Scenario** (`scripts/simulate_ais_feed.py`, `data/demo/ais_demo_scenario.json`)
- [x] **[DONE — Ravi / AI]** **TASK-ML01: 4-Signal ML Oil Spill Attribution Pipeline** (`backend/app/services/maritime/spill_attribution.py`)
- [x] **[DONE — Ravi / AI]** **TASK-UI01: WebGL Maritime Map Layer with India Base** (`frontend/src/components/map/MapView.tsx`)
- [x] **[DONE — Ravi / AI]** **TASK-UI02: Live Vessel Risk Markers & Animated Pulses** (`frontend/src/components/map/MapView.tsx`, `riskColors.ts`)
- [x] **[DONE — Ravi / AI]** **TASK-UI03: Real-Time Threat Alerts Panel** (`frontend/src/components/alerts/AlertPanel.tsx`)
- [x] **[DONE — Ravi / AI]** **TASK-UI04: Interactive Layer Control Toolbar** (Vessels, Spills, MPAs, Density Heatmap)
- [x] **[DONE — Ravi / AI]** **TASK-D02: SIH 5-Minute Live Presentation Runbook** (`docs/demo/DEMO_RUNBOOK.md`)

---

## 🔴 Sprint 3 Priority: Fire & Thermal Hotspot Classification (PS 162)

- [ ] **[CLAIMED by Joy]** **TASK-F01: FIRMS Live Data Fetcher & Database Ingestion Engine**
  - **Goal:** Connect `firms_fetcher.py` to an asynchronous database writer that upserts real-time satellite fire hotspots into the `thermal_hotspots` PostGIS table.
  - **Requirements:**
    - Parse MODIS (1km) and VIIRS (375m) CSV/JSON streams from NASA FIRMS API.
    - Prevent duplicate inserts using `(latitude, longitude, acquired_at)` compound uniqueness.
    - Check spatial distance against CPCB polluted clusters and tag `near_cpcb_cluster=True` if within 10 km.
    - Fallback gracefully to offline sample data if `FIRMS_MAP_KEY` is not provided.
  - **Deliverable:** `backend/app/services/fire/firms_processor.py` with unit test.

- [ ] **[CLAIMED by Akshar]** **TASK-F02: Fire Classification & Hotspots API Routes**
  - **Goal:** Implement `GET /api/v1/fire/hotspots` and `GET /api/v1/fire/hotspots/{id}` in `backend/app/api/routes/fire.py`.
  - **Requirements:**
    - Support query parameters: `fire_type` (industrial, gas_flare, stubble, wildfire, mining), `min_frp`, `start_date`, `end_date`, and `near_cpcb_only`.
    - Enrich responses with `responding_agency` and `recommended_action` using the decision matrix.
    - Return paginated `HotspotListResponse` (using schemas in `backend/app/schemas/hotspot.py`).
  - **Deliverable:** Functional endpoints with Swagger documentation.

- [ ] **[CLAIMED by Joy]** **TASK-F05: FIRMS Offline Mock Seed Generator**
  - **Goal:** Create a realistic sample dataset of 50+ thermal hotspots across India (stubble burning, industrial furnaces, gas flaring, wildfires).
  - **Deliverable:** `data/demo/firms_demo_scenario.json` and seeding script in `scripts/seed_hotspots.py`.

- [ ] **[CLAIMED by Arayan]** **TASK-F03: Chronic Industrial Pollution & Recurrence Tracker**
  - **Goal:** Build the spatial recurrence clustering engine exposed via `GET /api/v1/pollution/clusters`.
  - **Requirements:**
    - Group hotspots spatially by 0.01° grid cells (~1.1 km resolution).
    - Aggregate recurrence counts over a rolling 30-day window.
    - Flag locations with `recurrence_count >= 3` as chronic industrial violators (e.g. brick kilns, unmonitored furnaces).
    - Return cluster centroids, bounding boxes, dominant fire type, and responsible regional CPCB office.
  - **Deliverable:** `backend/app/services/pollution/cluster_analyzer.py` and connected API route.

- [ ] **[CLAIMED by Arayan]** **TASK-F04: VIIRS Nightfire (Gas Flare) Dataset Integration**
  - **Goal:** Ingest and parse VIIRS Nightfire (VNF) combustion data from NOAA/Colorado School of Mines.
  - **Requirements:**
    - Download and process daily VNF M10/SWIR detections for India offshore & onshore oil refineries (Bombay High, Assam, Gujarat).
    - Calculate combustion temperature (Kelvin) and cross-reference against FIRMS hotspots to distinguish routine gas flaring from unexpected refinery fires.
  - **Deliverable:** `data_pipeline/fetchers/vnf_fetcher.py` and test dataset in `data/vnf/`.

---

## 🟠 Sprint 3 Priority: Maritime DB Persistence & Real PostGIS Flow

- [ ] **[CLAIMED by Akshar]** **TASK-M05: Alerts Database Persistence & Real Query Route**
  - **Goal:** Replace in-memory mock responses in `backend/app/api/routes/alerts.py` with live async SQLAlchemy database queries.
  - **Requirements:**
    - Read from `alerts` table with filters for `alert_type`, `risk_level`, and `is_active`.
    - Implement pagination via `limit` (default 50, max 200) and `offset`.
    - Implement `POST /api/v1/alerts/{id}/acknowledge` to update `acknowledged_at` and `acknowledged_by`.
    - Stream newly created alerts to active WebSocket connections (`/api/v1/alerts/live`).
  - **Deliverable:** Fully functional alerts route with real DB integration and WebSocket push.

- [ ] **[CLAIMED by Akshar]** **TASK-M06: PostGIS Spatial Radius Search Endpoint**
  - **Goal:** Implement `GET /api/v1/alerts/near?lat=...&lon=...&radius_km=...` using PostGIS spatial indexing.
  - **Requirements:**
    - Use `ST_DWithin` with geography cast for precise kilometer radius calculation on WGS84 (SRID 4326).
    - Return matching alerts, vessels, and thermal hotspots within the target zone, sorted by proximity.
  - **Deliverable:** Spatial query function in `alerts.py` and query execution time benchmark (<50ms).

- [ ] **[CLAIMED by Akshar]** **TASK-M07: AIS Pipeline Background Worker & PostGIS Upsert**
  - **Goal:** Connect `ais_fetcher.py` to a Celery or APScheduler background task that runs every 15 minutes.
  - **Requirements:**
    - Ingest live AIS feed (or simulate live feed from `ais_demo_scenario.json`).
    - Compute temporal gap (`ais_gap_minutes`) by comparing current timestamp against last recorded timestamp for the same MMSI.
    - Write/update records into `vessel_risk_records` table with geometry points `ST_SetSRID(ST_MakePoint(lon, lat), 4326)`.
  - **Deliverable:** `backend/app/tasks/ais_worker.py` with automated scheduler integration.

---

## 🟡 Sprint 3 Priority: Frontend Intelligence & Analytics UI

- [ ] **[CLAIMED by Akshar]** **TASK-UI05: Vessel & Alert Detail Slide-In Drawer**
  - **Goal:** When a user clicks a vessel, spill polygon, or alert card, slide open a detailed inspection drawer from the right.
  - **Requirements:**
    - Display vessel metadata: Name, Flag, IMO/MMSI, Dimensions, Draft, Speed, Course.
    - Risk Factor Breakdown bars: Distance (40%), Vessel Type (25%), Course Alignment (20%), Anomaly (15%).
    - Action buttons: `Acknowledge Alert`, `Dispatch Coast Guard Notice`, `Download Evidence PDF`.
    - Use Tailwind CSS v3 with smooth transition animations.
  - **Deliverable:** `frontend/src/components/alerts/AlertDetailsDrawer.tsx`.

- [ ] **[CLAIMED by Akshar]** **TASK-UI08: Fire & Thermal Hotspots WebGL Map Layer**
  - **Goal:** Render thermal hotspots on `MapView.tsx` when the "Fire/Thermal" layer toggle is enabled.
  - **Requirements:**
    - Color code hotspots by classification: Gas Flare (Violet), Industrial (Orange), Stubble (Yellow), Wildfire (Red).
    - Clustered circles at low zoom levels, individual glowing heat dots at high zoom levels.
    - Hover tooltip displaying fire type, FRP in MW, and satellite confidence.
  - **Deliverable:** Integrated layer in `MapView.tsx`.

- [ ] **[CLAIMED by Akshar]** **TASK-UI07: Audio Alarm & Desktop Notification System**
  - **Goal:** Provide audible and visual alarms when a `CRITICAL` risk threat is detected.
  - **Requirements:**
    - Short tactical sonar pulse audio when a new dark ship or oil spill is pushed via WebSocket.
    - Browser `Notification` API integration with user opt-in toggle in the header.
    - Mute/Unmute audio button in `DashboardHeader.tsx`.
  - **Deliverable:** `frontend/src/services/soundEffects.ts` and header controls.

- [ ] **[CLAIMED by Saksham]** **TASK-UI06: Historical Telemetry & Trend Charts (Recharts)**
  - **Goal:** Add graphical telemetry analytics inside the inspection drawer using Recharts.
  - **Requirements:**
    - 24-hour Speed vs. Time line chart showing deceleration / loitering zones.
    - Fire Radiative Power (FRP) trend chart for recurring industrial clusters.
    - Dark mode styled axes, tooltips, and custom risk-colored stroke lines.
  - **Deliverable:** `frontend/src/components/analytics/VesselSpeedChart.tsx` and `HotspotFRPChart.tsx`.

- [ ] **[CLAIMED by Saksham]** **TASK-UI09: Global Search & Autocomplete Header Bar**
  - **Goal:** Add a search bar to `DashboardHeader.tsx` allowing users to search by Vessel Name, MMSI, or Port.
  - **Requirements:**
    - Autocomplete dropdown with matching vessels and ports.
    - Selecting a result automatically centers and zooms the map (`flyTo`) onto the target coordinates.
  - **Deliverable:** `frontend/src/components/dashboard/SearchBar.tsx`.

---

## 🟢 Testing, QA & Delivery Assets

- [ ] **[CLAIMED by Krishika]** **TASK-J02: Automated Pytest Suite for Pydantic Models & API Routes**
  - **Goal:** Write comprehensive unit and integration tests using `pytest` and `httpx`.
  - **Requirements:**
    - Validate all schema field validators in `backend/app/schemas/`.
    - Test boundary checks: Latitude [-90, 90], Longitude [-180, 180], Risk Score [0.0, 1.0].
    - Test API endpoints: `/health`, `/maritime/vessels`, `/maritime/simulate-spill`, `/alerts`.
    - Ensure 100% test pass rate with `pytest backend/tests/`.
  - **Deliverable:** `backend/tests/unit/test_schemas.py` and `backend/tests/integration/test_api.py`.

- [ ] **[CLAIMED by Krishika]** **TASK-D01: Official Postman / Bruno API Collection**
  - **Goal:** Create an exportable, production-ready Postman/Bruno collection covering all SATVIGIL endpoints.
  - **Requirements:**
    - Include environment variables (`baseUrl = http://localhost:8000`).
    - Include realistic request bodies for `/simulate-spill`, `/simulate-dark-vessel`, and `/alerts/{id}/acknowledge`.
    - Include saved response examples for demo documentation.
  - **Deliverable:** `docs/api/SATVIGIL_API_Collection.json`.
