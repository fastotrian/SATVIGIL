# Task Sheet — Saksham

- **Name:** Saksham
- **Role:** Frontend Engineering / Charts & Search UI
- **Branch Format:** `feat/saksham-<task-id>` (e.g. `feat/saksham-task-ui06`)
- **Status:** 🟢 Active — Sprint 3

---

## 🎯 Current Focus & Active Tasks

- [ ] **TASK-UI06: Historical Telemetry & Trend Charts (Recharts)**
  - **Priority:** 🔴 High
  - **Goal:** Build reusable telemetry analytics charts using Recharts for vessel speed profiles and hotspot intensity.
  - **Requirements:**
    - 24-hour Speed vs. Time line chart showing loitering / deceleration thresholds.
    - Fire Radiative Power (FRP) trend bar/area chart for recurring industrial clusters.
    - Responsive dark mode theme matching SATVIGIL design tokens (tooltips, crosshairs, risk-colored strokes).
  - **Deliverable:** `frontend/src/components/analytics/VesselSpeedChart.tsx` and `HotspotFRPChart.tsx`.

- [ ] **TASK-UI09: Global Search & Quick Filter Header Component**
  - **Priority:** 🟡 Medium
  - **Goal:** Add a search bar to `DashboardHeader.tsx` allowing users to search by Vessel Name, MMSI, or State/Region.
  - **Requirements:**
    - Autocomplete dropdown with matching vessels and ports.
    - Selecting a result automatically centers and zooms the map (`flyTo`) onto the target coordinates.
  - **Deliverable:** `frontend/src/components/dashboard/SearchBar.tsx` integrated into `DashboardHeader.tsx`.

---

## 📋 Task History & Queue

| Task ID | Description | Priority | Assigned Date | Status | PR / Notes |
|---|---|---|---|---|---|
| TASK-UI06 | Recharts Telemetry Curves (Speed & FRP) | 🔴 High | 2026-09-08 | 🟡 In Progress | Active assignment |
| TASK-UI09 | Global Search & Autocomplete Toolbar | 🟡 Medium | 2026-09-08 | ⏳ Queued | Up next after UI06 |

---

## 🛑 Blockers & Help Needed
*If stuck: Follow the 15-minute rule before pinging Ravi.*

| Date | Issue / Error | What I Tried | Status |
|---|---|---|---|
| — | None | — | — |

---

## 📚 Quick Reference
- Master Task Backlog: [TASK_BACKLOG.md](TASK_BACKLOG.md)
- Alert Store: [frontend/src/store/alertStore.ts](../frontend/src/store/alertStore.ts)
- Risk Colors: [frontend/src/constants/riskColors.ts](../frontend/src/constants/riskColors.ts)
- Types: [frontend/src/types/maritime.ts](../frontend/src/types/maritime.ts)
