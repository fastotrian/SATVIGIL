# Task Sheet — Akshar

- **Name:** Akshar
- **Role:** Developer / Engineering
- **Branch Format:** `feat/akshar-<feature-name>`
- **Status:** 🟢 Active — Sprint 2

---

## 🎯 Current Focus & Active Tasks

- [ ] **TASK-M05: Alerts DB Query — Replace Mock Response**
  - Implement real SQLAlchemy async query in `backend/app/api/routes/alerts.py`
  - Support filter by `alert_type`, `risk_level`, pagination via `limit`/`offset`, order by `created_at DESC`
  - Use the new `AlertSummary` + `AlertListResponse` schemas (TASK-M01 done ✅)
  - See [TASK_BACKLOG.md](TASK_BACKLOG.md) for full spec

---

## 📋 Task History & Queue

| Task ID | Description | Priority | Assigned Date | Status | PR / Notes |
|---|---|---|---|---|---|
| TASK-M01 | Pydantic v2 Schemas — `alert.py`, `vessel.py`, `hotspot.py`, `__init__.py` | 🔴 High | 2026-09-08 | ✅ Done | Validated with Pydantic 2.13.5. All schemas parse + computed fields verified. |
| TASK-M05 | Alerts DB Query — Replace mock in `routes/alerts.py` | 🔴 High | 2026-09-08 | 🟡 Up Next | Depends on TASK-M01 (done). Use `AlertSummary`, `AlertListResponse`. |

---

## 🛑 Blockers & Help Needed
*If stuck: Note what you tried and error messages before pinging the lead.*

| Date | Issue / Error | What I Tried | Status |
|---|---|---|---|
| — | None | — | — |

---

## 📚 Quick Reference
- System Design: [docs/hld/HLD.md](../docs/hld/HLD.md)
- API Contract: [.ai/API_REFERENCE.md](../.ai/API_REFERENCE.md)
- DB Models: [backend/app/models/alert.py](../backend/app/models/alert.py)
- My Schemas: [backend/app/schemas/](../backend/app/schemas/)
- Available Tasks: [TASK_BACKLOG.md](TASK_BACKLOG.md)
