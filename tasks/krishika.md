# Task Sheet — Krishika

- **Name:** Krishika
- **Role:** QA Engineering / Testing & API Automation
- **Branch Format:** `feat/krishika-<task-id>` (e.g. `feat/krishika-task-j02`)
- **Status:** 🟢 Active — Sprint 3

---

## 🎯 Current Focus & Active Tasks

- [ ] **TASK-J02: Automated Pytest Suite for Schemas & API Routes**
  - **Priority:** 🔴 High
  - **Goal:** Build a clean, automated unit and integration test suite using `pytest` and `httpx`.
  - **Requirements:**
    - Test all schema field validators in `backend/app/schemas/` (`alert.py`, `vessel.py`, `hotspot.py`, `maritime.py`).
    - Verify boundary validation: Latitude [-90, 90], Longitude [-180, 180], Risk Score [0.0, 1.0].
    - Test API endpoints with FastAPI TestClient: `/api/v1/health`, `/api/v1/maritime/vessels`, `/api/v1/maritime/simulate-spill`, `/api/v1/alerts`.
    - Ensure 100% test pass rate with `pytest backend/tests/`.
  - **Deliverable:** `backend/tests/unit/test_schemas.py` and `backend/tests/integration/test_api.py`.

- [ ] **TASK-D01: Official Postman & Bruno API Collection**
  - **Priority:** 🟡 Medium
  - **Goal:** Create an exportable, production-ready Postman/Bruno collection covering all SATVIGIL endpoints.
  - **Requirements:**
    - Environment variables: `baseUrl = http://localhost:8000`.
    - Realistic request payloads for `/api/v1/maritime/simulate-spill`, `/api/v1/maritime/simulate-dark-vessel`, `/api/v1/alerts/{id}/acknowledge`.
    - Include saved response samples for demo documentation.
  - **Deliverable:** `docs/api/SATVIGIL_API_Collection.json`.

---

## 📋 Task History & Queue

| Task ID | Description | Priority | Assigned Date | Status | PR / Notes |
|---|---|---|---|---|---|
| TASK-J02 | Pytest Automated Test Suite | 🔴 High | 2026-09-08 | 🟡 In Progress | Active assignment |
| TASK-D01 | Postman / Bruno API Collection | 🟡 Medium | 2026-09-08 | ⏳ Queued | Up next after J02 |

---

## 🛑 Blockers & Help Needed
*If stuck: Check docs and 15-minute rule before pinging Ravi.*

| Date | Issue / Error | What I Tried | Status |
|---|---|---|---|
| — | None | — | — |

---

## 📚 Quick Reference
- Master Task Backlog: [TASK_BACKLOG.md](TASK_BACKLOG.md)
- Testing Guide: [docs/testing/TESTING_GUIDE.md](../docs/testing/TESTING_GUIDE.md)
- API Reference: [.ai/API_REFERENCE.md](../.ai/API_REFERENCE.md)
