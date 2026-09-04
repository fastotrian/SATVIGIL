# SATVIGIL — Master Task Backlog

> **For Teammates:** If you finish your assigned tasks and your lead (Ravi) is busy or away, pick any task marked `[AVAILABLE]` below. Mark it as `[CLAIMED by <Your Name>]` and add it to your individual task markdown file.

---

## 🟢 Category A: Junior & Beginner Friendly Tasks
*Ideal for juniors to get hands-on without breaking core architecture.*

- [ ] **[AVAILABLE]** **TASK-J01: Local Environment Setup & Smoke Test**
  - **Goal:** Clone repo, follow [docs/deployment/DEPLOYMENT.md](file:///c:/MY%20Coding/SATVIGIL/docs/deployment/DEPLOYMENT.md), verify `docker-compose up` runs PostgreSQL + PostGIS, Redis, FastAPI, and Frontend.
  - **Deliverable:** Note down any missing setup steps or errors in a setup notes doc.

- [ ] **[AVAILABLE]** **TASK-J02: Unit Tests for Alert Pydantic Schemas**
  - **Goal:** Write unit tests in `backend/tests/unit/` testing valid/invalid input validation for alerts schema (`backend/app/schemas/alert.py`).
  - **Deliverable:** Test file `test_alert_schemas.py` passing with `pytest`.

- [ ] **[AVAILABLE]** **TASK-J03: Sample GeoJSON Boundaries for Marine Protected Areas (MPAs)**
  - **Goal:** Find and collect boundary GeoJSONs for Gulf of Kutch MNP, Gulf of Mannar MNP, and Sundarbans buffer zone into `data_pipeline/data/mpas/`.
  - **Deliverable:** Valid GeoJSON files with proper EPSG:4326 coordinates.

- [ ] **[AVAILABLE]** **TASK-J04: CPCB Industrial Clusters CSV / JSON Lookup**
  - **Goal:** Compile the list of Central Pollution Control Board (CPCB) critically polluted industrial clusters with their lat/long coordinates.
  - **Deliverable:** Clean CSV file in `data_pipeline/data/cpcb_clusters.csv`.

- [ ] **[AVAILABLE]** **TASK-J05: Backend Health Check Route Tests**
  - **Goal:** Write automated API tests for `GET /api/v1/health` and database connectivity check.
  - **Deliverable:** Working test in `backend/tests/integration/test_health.py`.

---

## 🟡 Category B: Frontend & UI Tasks (React + Mapbox GL JS)
*For building interactive dashboard and map components.*

- [ ] **[AVAILABLE]** **TASK-F01: Alert Sidebar List Component**
  - **Goal:** Build the collapsible alerts feed sidebar displaying active alerts with badges for `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
  - **Deliverable:** Component in `frontend/src/components/alerts/AlertSidebar.tsx`.

- [ ] **[AVAILABLE]** **TASK-F02: Map Filter Control Bar**
  - **Goal:** Add filter toggles on top of MapView to switch layers: Oil Spills, Fires, Maritime/AIS, Landslides, Industrial.
  - **Deliverable:** Layer switcher toolbar in `frontend/src/components/map/LayerControls.tsx`.

- [ ] **[AVAILABLE]** **TASK-F03: Alert Detail Modal / Drawer**
  - **Goal:** When a user clicks on an alert marker on the map, open a slide-in drawer showing full alert metadata (FRP, coordinates, confidence, responding agency).
  - **Deliverable:** `AlertDetailsDrawer.tsx`.

- [ ] **[AVAILABLE]** **TASK-F04: WebSocket Auto-Reconnect & Notification Toast**
  - **Goal:** Improve WebSocket handling to show visual alert popups (toasts) whenever a new critical alert is received.
  - **Deliverable:** Notification toast provider in frontend.

---

## 🟠 Category C: Backend & Data Pipeline (FastAPI + PostGIS)
*For core data ingestion, APIs, and geospatial logic.*

- [ ] **[AVAILABLE]** **TASK-B01: NASA FIRMS Fetcher Integration**
  - **Goal:** Implement live fetcher in `backend/app/services/fire/firms_fetcher.py` using NASA FIRMS API (MAP_KEY in `.env`).
  - **Deliverable:** Function to pull VIIRS NRT 24-hour hotspot CSV and parse into `ThermalHotspot` DB rows.

- [ ] **[AVAILABLE]** **TASK-B02: Complete Alerts DB Query in GET /api/v1/alerts**
  - **Goal:** Replace mock return in `backend/app/api/routes/alerts.py` with real SQLAlchemy query with filtering and pagination.
  - **Deliverable:** Fully working query with filtering by `alert_type`, `risk_level`, and time range.

- [ ] **[AVAILABLE]** **TASK-B03: Spatial Query: Alerts Within Radius**
  - **Goal:** Add endpoint `GET /api/v1/alerts/near?lat=...&lon=...&radius_km=...` using PostGIS `ST_DWithin`.
  - **Deliverable:** Fast radius search endpoint.

- [ ] **[AVAILABLE]** **TASK-B04: AIS Mock Data Generator**
  - **Goal:** Write a script to simulate AIS vessel traffic with 2-3 "dark transponder" scenarios off the coast of Gujarat and Mumbai for live demo.
  - **Deliverable:** `scripts/simulate_ais_feed.py`.

---

## 🔵 Category D: Documentation, Presentation & Research
*For team members researching algorithms, datasets, or preparing submission.*

- [ ] **[AVAILABLE]** **TASK-D01: API Documentation & Postman / Bruno Collection**
  - **Goal:** Create an exportable API collection with example requests for all endpoints.
  - **Deliverable:** `docs/api/satvigil_postman_collection.json`.

- [ ] **[AVAILABLE]** **TASK-D02: Demo Script & Architecture Slide Walkthrough**
  - **Goal:** Prepare a 5-minute hackathon demo walkthrough script matching the 5 detection modules.
  - **Deliverable:** `docs/presentation/DEMO_SCRIPT.md`.
