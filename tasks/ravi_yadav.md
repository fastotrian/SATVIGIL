# Task Sheet — Ravi Yadav (Team Lead)

- **Name:** Ravi Yadav
- **Role:** Project Lead / System Architecture & Integration
- **Branch Format:** `main` or `feat/ravi-<feature>`
- **Status:** 🟢 Active — Sprint 3

---

## 🎯 Current Focus & Active Tasks

- [x] **PS 143 Maritime Oil Spill Detection Module (End-to-End Complete):**
  - WebGL map layer, 4-signal ML attribution model, AIS dark vessel scenario generator, live alerts panel, threat color matrix.
- [x] Merged Pydantic v2 schemas from teammate Akshar into `main`.
- [ ] **PS 162 Fire Classification Module Architecture Governance:**
  - Guide Joy on FIRMS fetcher DB persistence (`TASK-F01`) and route design (`TASK-F02`).
  - Guide Arayan on CPCB industrial recurrence tracking (`TASK-F03`).
- [ ] **Sentinel-2 PyTorch U-Net Inference Service Integration:**
  - Wrap pretrained U-Net oil slick segmentation model into `backend/app/services/maritime/unet_segmenter.py`.
- [ ] **Docker PostGIS Alembic Migrations Setup (`ARCH-02`).**

---

## 📋 Assigned Tasks

| Task ID | Description | Priority | Target Date | Status | Notes |
|---|---|---|---|---|---|
| ARCH-01 | Architecture design & HLD/LLD docs | Critical | Done | [x] Completed | Committed to git |
| PS143-MVP | End-to-End Oil Spill & AIS Correlation Demo | Critical | Done | [x] Completed | Merged & pushed to main |
| ARCH-02 | Setup PostGIS database schema & Alembic migrations | High | Sprint 3 | [ ] Pending | In progress |
| LEAD-01 | Review teammate PRs & unblock team members | Ongoing | Ongoing | [>] Ongoing | Daily sync |

---

## 📝 Team Coordination Notes
- All 5 team members have active Sprint 3 assignments.
- Master backlog updated with full deliverables, requirements, and branch conventions in [TASK_BACKLOG.md](TASK_BACKLOG.md).
