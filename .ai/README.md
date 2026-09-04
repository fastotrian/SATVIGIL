# 🤖 SATVIGIL AI Context System (`.ai/`)

> **MANDATORY INSTRUCTION FOR ANY AI ASSISTANT (Antigravity, Cursor, Claude, ChatGPT, Copilot, Windsurf):**
> You are working on **SATVIGIL**. Before taking any action, writing code, or answering questions, **read this directory**.
> 
> **CRITICAL RULE:** Whenever you modify any architecture, database model, API contract, or complete a task, you **MUST** update [CURRENT_STATE.md](CURRENT_STATE.md) before ending your response.

---

## 🛰️ 1. Project Identity & Elevator Pitch

- **Project Name:** SATVIGIL
- **Core Mission:** AI-powered satellite monitoring and multi-hazard early warning platform that predicts and classifies maritime, industrial, geological, and wildfire risks across India before they turn into disasters.
- **Problem Statements:**
  - **SIH 2026 — PS 143 (NTRO):** Real-time Oil Spill Detection & AIS Correlation.
  - **SIH 2026 — PS 162 (NTRO):** Industrial Fire & Thermal Source Classification.
- **Lead / Owner:** Ravi Yadav
- **Team Size:** 6 members (Ravi, Joy, Saksham, Arayan, Krishika, Akshar)

---

## 📂 2. AI Context Sitemap (Read What You Need)

| File | Purpose / What It Contains |
|---|---|
| 📌 **[CURRENT_STATE.md](CURRENT_STATE.md)** | **Start here!** Live project status, what is finished, what is currently being built, next immediate priorities. |
| 🏛️ **[ARCHITECTURE.md](ARCHITECTURE.md)** | System architecture, confirmed tech stack, folder-to-layer mapping, 5 detection modules, what is written vs. empty. |
| 🗄️ **[DATABASE_AND_MODELS.md](DATABASE_AND_MODELS.md)** | PostgreSQL + PostGIS schemas, spatial indexes, tables (`alerts`, `vessel_risk_records`, `thermal_hotspots`). |
| 📏 **[CODING_STANDARDS.md](CODING_STANDARDS.md)** | Code conventions (FastAPI, React, Tailwind CSS, GeoPandas), role-to-tech mapping, security. |
| 👥 **[TEAM_AND_TASKS.md](TEAM_AND_TASKS.md)** | Team structure, task delegation in `tasks/`, junior guidance protocol. |
| 🎯 **[PITCH_AND_PRODUCT.md](PITCH_AND_PRODUCT.md)** | **WHY** behind every feature: PS 143/162 rationale, fire classification agency routing, data sources, government actors, pitch references. |
| 🔌 **[API_REFERENCE.md](API_REFERENCE.md)** | All API endpoints, request/response schemas, WebSocket protocol. Single source of truth for routes. |

---

## ⚡ 3. Non-Negotiable Project Rules

1. **Database:** Always use **PostgreSQL 15 + PostGIS**. Never propose MongoDB or plain MySQL. Spatial queries must use PostGIS functions (`ST_DWithin`, `ST_Contains`).
2. **Backend:** Python 3.10+ with **FastAPI** (asynchronous endpoints with `async def`, SQLAlchemy async sessions).
3. **Frontend:** React 18 + TypeScript + **Tailwind CSS (v3)**. Do NOT add plain CSS or styled-components. Mapbox GL JS for the map (WebGL, handles moving vessel markers at scale).
4. **ML Stack:** PyTorch (U-Net spill detection, ESRGAN super-res) + XGBoost (fire classification) + Isolation Forest (vessel risk scoring). Do NOT switch ML frameworks without discussion.
5. **Task Queue:** Celery + Redis for asynchronous ML / satellite raster processing.
6. **No Hallucinated Surveillance:** Satellite revisit over India is physics-limited (Sentinel: 2–5 days, VIIRS/MODIS: 2–4x/day). Never claim "real-time optical live video streaming".
7. **Task Board:** All task assignments live in [`../tasks/`](../tasks). Always check `../tasks/TASK_BACKLOG.md` before inventing new tasks.
8. **Product Context:** Before implementing any feature, read [`PITCH_AND_PRODUCT.md`](PITCH_AND_PRODUCT.md) to understand WHY it exists and which government agency it targets.

---

## 🔄 4. How to Update This Folder (For AI Agents)

Whenever you:
- Complete a feature or task → Update `Completed Work` in [CURRENT_STATE.md](CURRENT_STATE.md).
- Add or change an API route / DB table → Update [DATABASE_AND_MODELS.md](DATABASE_AND_MODELS.md) or [ARCHITECTURE.md](ARCHITECTURE.md).
- Encounter a blocker or define next steps → Add them to [CURRENT_STATE.md](CURRENT_STATE.md).
