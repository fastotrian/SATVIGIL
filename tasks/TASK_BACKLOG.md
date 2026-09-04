# SATVIGIL — Master Task Backlog

> **For Teammates:** If you finish your assigned tasks and your lead (Ravi) is busy or away,
> pick any task marked `[AVAILABLE]` below. Mark it as `[CLAIMED by <Your Name>]` and add it
> to your individual task markdown file.
>
> **Priority order for Sprint 2:**
> Maritime (PS 143) → Fire Classification (PS 162) → Frontend Map → Landslide (last)

---

## 🔴 Sprint 2 Priority: Maritime Pipeline (PS 143 — Core Deliverable)

- [ ] **[AVAILABLE]** **TASK-M01: Pydantic Schemas — Vessel, Alert, Hotspot**
  - **Goal:** Create request/response schemas in `backend/app/schemas/`:
    - `VesselSchema`, `SpillAlertSchema`, `ThermalHotspotSchema`, `AlertListResponse`
  - **Reference:** See `backend/app/models/alert.py` for field names.
  - **Deliverable:** `backend/app/schemas/vessel.py`, `alert.py`, `hotspot.py` with Pydantic v2 models.

- [ ] **[AVAILABLE]** **TASK-M02: Maritime Vessels Endpoint — Real DB Query**
  - **Goal:** Implement `GET /api/v1/maritime/vessels` in `backend/app/api/routes/maritime.py`
    with real SQLAlchemy async query on `vessel_risk_records` table, returning list of vessels
    sorted by `risk_score DESC`.
  - **Reference:** See `.ai/API_REFERENCE.md` for exact response schema expected.
  - **Deliverable:** Working endpoint returning real DB data.

- [ ] **[AVAILABLE]** **TASK-M03: AIS Data Flow — Fetcher → Persist to DB**
  - **Goal:** Connect `ais_fetcher.fetch_ais_vessels()` (already written) to a DB write function
    that upserts vessel data into `vessel_risk_records` table using MMSI as the unique key.
  - **Note:** The fetcher returns raw vessel dicts; you need to call `calculate_vessel_risk_score()`
    and persist the result.
  - **Deliverable:** `backend/app/services/maritime/ais_processor.py` with `process_and_persist_vessels()`.

- [ ] **[AVAILABLE]** **TASK-M04: AIS Mock Data Generator (Dark Vessel Demo)**
  - **Goal:** Write `scripts/simulate_ais_feed.py` — a script that POSTs fake vessel data directly
    to the API, simulating 2–3 "dark transponder" scenarios:
    - Scenario 1: Tanker goes dark 30min near Gulf of Kutch MPA → risk score spikes
    - Scenario 2: Vessel loitering off Mumbai coast near Bombay High for 2 hours
    - Scenario 3: Cargo ship with high AIS gap in JNPT approach zone
  - **Deliverable:** `scripts/simulate_ais_feed.py` that runs standalone and seeds demo data.

- [ ] **[AVAILABLE]** **TASK-M05: Alerts DB Query — Replace Mock Response**
  - **Goal:** In `backend/app/api/routes/alerts.py`, replace the mock return with a real
    SQLAlchemy async query on the `alerts` table supporting:
    - Filter by `alert_type`, `risk_level`
    - Pagination via `limit` + `offset`
    - Order by `created_at DESC`
  - **Deliverable:** Fully working paginated alerts endpoint.

- [ ] **[AVAILABLE]** **TASK-M06: Spatial Radius Search Endpoint**
  - **Goal:** Add `GET /api/v1/alerts/near?lat=...&lon=...&radius_km=...` using PostGIS `ST_DWithin`.
  - **Reference:** See `.ai/DATABASE_AND_MODELS.md` for the correct SQL pattern.
  - **Deliverable:** Fast radius search endpoint, tested with India coordinates.

---

## 🟠 Sprint 2: Fire Classification Pipeline (PS 162)

- [ ] **[AVAILABLE]** **TASK-F01: FIRMS Fetcher — Live Data → DB Persist**
  - **Goal:** The FIRMS fetcher in `backend/app/services/fire/firms_fetcher.py` already fetches
    and classifies fire data. Connect it to a DB write that persists each classified hotspot
    into the `thermal_hotspots` table.
  - **Include:** Set `near_cpcb_cluster` boolean by checking against the `CPCB_CLUSTERS` list in the file.
  - **Deliverable:** `backend/app/services/fire/firms_processor.py` with `process_and_persist_hotspots()`.

- [ ] **[AVAILABLE]** **TASK-F02: Fire Hotspots Endpoint**
  - **Goal:** Implement `GET /api/v1/fire/hotspots` in `backend/app/api/routes/fire.py`
    with filtering by `fire_type` (industrial, wildfire, stubble, gas_flare, mining, unknown)
    and optional `near_cpcb_only=true` query param.
  - **Deliverable:** Working filtered endpoint returning classified hotspot data.

- [ ] **[AVAILABLE]** **TASK-F03: Industrial Recurrence Tracker**
  - **Goal:** Implement logic that groups `thermal_hotspots` by coordinates (rounded to 0.01 degree)
    and counts occurrences per location per month. Expose via `GET /api/v1/pollution/clusters`.
  - **Deliverable:** Query that returns locations with `recurrence_count >= 3` flagged as chronic polluters.

- [ ] **[AVAILABLE]** **TASK-F04: VIIRS Nightfire (Gas Flare) Dataset Integration**
  - **Goal:** Download VIIRS Nightfire (VNF) CSV data from NOAA/Earth Observation Group for
    India (lat 7–36, lon 68–98) for the past 30 days. Parse and cross-reference against
    FIRMS hotspots to improve gas flare vs. industrial fire classification.
  - **Dataset:** https://eogdata.mines.edu/products/vnf/
  - **Deliverable:** Script in `data_pipeline/fetchers/vnf_fetcher.py`.

---

## 🟡 Sprint 2: Frontend Map & UI

- [ ] **[AVAILABLE]** **TASK-UI01: Mapbox GL JS Map — India Base Map**
  - **Goal:** Implement `frontend/src/components/map/MapView.tsx` with Mapbox GL JS:
    - Dark map style (`mapbox://styles/mapbox/dark-v11`)
    - Centered on India `[78.9629, 20.5937]`, zoom 4.5
    - Bounded to India: `[[68.1, 7.9], [97.4, 35.5]]` (disable pan/zoom outside India)
  - **Tech:** Use `react-map-gl` wrapper (already in `package.json`).
  - **Deliverable:** Working India map that renders in the app.

- [ ] **[AVAILABLE]** **TASK-UI02: Vessel Risk Markers on Map**
  - **Goal:** Fetch vessels from `GET /api/v1/maritime/vessels` and render them on the map as
    circle markers colored by risk score (green < 0.3, yellow 0.3–0.7, red > 0.7).
    Use Mapbox `addSource` + `addLayer` (NOT React DOM markers for performance).
  - **Deliverable:** Live vessel layer on the map.

- [ ] **[AVAILABLE]** **TASK-UI03: Alert Sidebar Component**
  - **Goal:** Build `frontend/src/components/alerts/AlertPanel.tsx` — a scrollable sidebar showing
    the 20 most recent alerts from the Zustand store, each showing: alert type icon, title,
    risk badge (CRITICAL/HIGH/MEDIUM/LOW), timestamp, coordinates.
  - **Deliverable:** Working scrollable alert feed.

- [ ] **[AVAILABLE]** **TASK-UI04: Layer Toggle Controls**
  - **Goal:** Build `frontend/src/components/map/LayerControls.tsx` — a toolbar with toggle buttons
    for: Oil Spills, Illegal Fishing, Fire/Thermal, Industrial Pollution, Landslide.
    Toggling a layer shows/hides its Mapbox layer on the map.
  - **Deliverable:** Working layer switcher.

- [ ] **[AVAILABLE]** **TASK-UI05: Alert Detail Drawer**
  - **Goal:** When user clicks a map marker, show a slide-in drawer with full alert details:
    fire type, FRP, agency responsible, recommended action, coordinates, timestamp.
  - **Deliverable:** `frontend/src/components/alerts/AlertDetailsDrawer.tsx`.

- [ ] **[AVAILABLE]** **TASK-UI06: WebSocket Notification Toasts**
  - **Goal:** When a new `critical` or `high` risk alert comes in via WebSocket, show a toast
    notification (brief popup, top-right corner) with the alert title and type icon.
  - **Deliverable:** Toast notification provider integrated into App.tsx.

---

## 🟢 Category A: Junior & Beginner Friendly Tasks

- [ ] **[AVAILABLE]** **TASK-J01: Local Environment Setup & Smoke Test**
  - **Goal:** Clone repo, follow [docs/deployment/DEPLOYMENT.md](../docs/deployment/DEPLOYMENT.md),
    verify `docker-compose up` runs PostgreSQL + PostGIS, Redis, FastAPI, and Frontend.
  - **Deliverable:** Note down any missing setup steps or errors in a setup notes doc.

- [ ] **[AVAILABLE]** **TASK-J02: Unit Tests for Alert Pydantic Schemas**
  - **Goal:** Write unit tests in `backend/tests/unit/` testing valid/invalid input validation.
  - **Deliverable:** Test file `test_alert_schemas.py` passing with `pytest`.

- [ ] **[AVAILABLE]** **TASK-J03: Sample GeoJSON Boundaries for Marine Protected Areas**
  - **Goal:** Find and collect full GeoJSON polygon boundaries (not just bounding boxes) for:
    Gulf of Kutch MNP, Gulf of Mannar MNP, Sundarbans buffer zone.
  - **Deliverable:** Valid GeoJSON files in `data_pipeline/data/mpas/` with EPSG:4326 coordinates.

- [ ] **[AVAILABLE]** **TASK-J04: CPCB Industrial Clusters — Expand to All 43**
  - **Goal:** The `firms_fetcher.py` currently has only 10 of the 43 CPCB critically polluted
    clusters. Compile the remaining 33 from public CPCB data.
  - **Deliverable:** Full 43-entry list added to `CPCB_CLUSTERS` in `firms_fetcher.py` + a CSV
    backup in `data_pipeline/data/cpcb_clusters.csv`.

- [ ] **[AVAILABLE]** **TASK-J05: Backend Health Check Route Tests**
  - **Goal:** Write automated API tests for `GET /api/v1/health` and database connectivity check.
  - **Deliverable:** Working test in `backend/tests/integration/test_health.py`.

---

## 🔵 Category D: Documentation & Presentation

- [ ] **[AVAILABLE]** **TASK-D01: API Documentation & Postman Collection**
  - **Goal:** Create an exportable Postman/Bruno collection with example requests for all endpoints.
  - **Reference:** See `.ai/API_REFERENCE.md` for all routes.
  - **Deliverable:** `docs/api/satvigil_postman_collection.json`.

- [ ] **[AVAILABLE]** **TASK-D02: Demo Script & Walkthrough**
  - **Goal:** Prepare a 5-minute hackathon demo walkthrough script. Should cover:
    1. Open map → show India coastline
    2. Point out a dark-vessel risk alert off Bombay High
    3. Zoom to a recurring industrial hotspot near Vapi (CPCB cluster)
    4. Show fire classification sidebar: industrial vs. stubble vs. wildfire
    5. Show the Wayanad/Joshimath SAR deformation overlay
  - **Deliverable:** `docs/presentation/DEMO_SCRIPT.md`.

- [ ] **[AVAILABLE]** **TASK-D03: Collect Sentinel-1 Historical Pairs for Joshimath/Wayanad**
  - **Goal:** Download 2–3 Sentinel-1 SAR image pairs (same area, different dates, 1–3 months apart)
    for either Joshimath (Uttarakhand) or Wayanad (Kerala) from ESA Copernicus Hub.
  - **Deliverable:** Files in `ml/data/sar_pairs/` with metadata note on acquisition dates.
