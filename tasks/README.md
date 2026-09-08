# SATVIGIL — Team Task Allocation & Coordination Board

Welcome to the task coordination center for **SATVIGIL** (Smart India Hackathon 2026). This directory maintains clear ownership, prevents merge bottlenecks, and guarantees every team member always has productive, impactful work.

---

## 👥 Team Roster & Sprint 3 Active Assignments

| # | Name | Role / Domain | Active Assignments | Task Sheet | Status |
|---|---|---|---|---|---|
| 1 | **Ravi Yadav** | Team Lead / Architecture | PS 162 Governance & PyTorch U-Net Inference | [ravi_yadav.md](ravi_yadav.md) | 🟢 Active |
| 2 | **Akshar** | Core Full-Stack Engineer (Backend & Frontend) | **Backend:** TASK-M05 (Alerts DB), TASK-M06 (Spatial), TASK-F02 (Fire APIs), TASK-M07 (AIS Worker)<br>**Frontend:** TASK-UI05 (Detail Drawer), TASK-UI08 (Thermal Map Layer), TASK-UI07 (Audio Alarms) | [akshar.md](akshar.md) | 🟢 Heavy Active |
| 3 | **Joy** | Backend / FIRMS Sensor Pipeline | TASK-F01 (FIRMS Stream DB Ingestion) + TASK-F05 (Demo Hotspot Seeder) | [joy.md](joy.md) | 🟢 Active |
| 4 | **Saksham** | Frontend / Charts & Search | TASK-UI06 (Recharts Analytics) + TASK-UI09 (Global Search & Autocomplete) | [saksham.md](saksham.md) | 🟢 Active |
| 5 | **Arayan** | Data Engineering / Pollution | TASK-F03 (CPCB Recurrence Clustering) + TASK-F04 (VIIRS Nightfire) | [arayan.md](arayan.md) | 🟢 Active |
| 6 | **Krishika** | QA Automation & API Docs | TASK-J02 (Pytest Automated Suite) + TASK-D01 (Postman/Bruno Collection) | [krishika.md](krishika.md) | 🟢 Active |

---

## 🛑 Ground Rules for Teammates (Read First)

1. **Git Workflow:**
   - Always create a dedicated branch from updated `main`: `feat/<your-name>-<task-id>` (e.g. `feat/akshar-task-m05`).
   - Never commit directly to `main`.
   - Run tests (`pytest` for backend, `npm run build` for frontend) before creating a Pull Request.

2. **Finished your task? Never sit idle!**
   - Mark your task `[x]` in your individual task sheet and [TASK_BACKLOG.md](TASK_BACKLOG.md).
   - Pick the next queued task from your personal sheet or claim any unassigned `[AVAILABLE]` task from the master backlog.

3. **Stuck / Facing a blocker? Follow the 15-Minute Rule:**
   - 1. Read the error message carefully.
   - 2. Consult the project docs in [docs/](../docs) (HLD, LLD, DATA_GUIDE).
   - 3. Attempt debugging for 15 minutes.
   - 4. If still unresolved, record the exact error and steps in your task sheet under `Blockers` and reach out to Ravi during sync.

---

## 📚 Quick Reference Links
- High Level Design: [docs/hld/HLD.md](../docs/hld/HLD.md)
- Low Level Design & Algorithms: [docs/lld/LLD.md](../docs/lld/LLD.md)
- Database & Models: [.ai/DATABASE_AND_MODELS.md](../.ai/DATABASE_AND_MODELS.md)
- API Reference: [.ai/API_REFERENCE.md](../.ai/API_REFERENCE.md)
- Master Task Backlog: [TASK_BACKLOG.md](TASK_BACKLOG.md)
- Demo Runbook: [docs/demo/DEMO_RUNBOOK.md](../docs/demo/DEMO_RUNBOOK.md)
