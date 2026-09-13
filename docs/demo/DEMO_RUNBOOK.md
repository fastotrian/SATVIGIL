# SATVIGIL Demo Runbook — PS 143 (Oil Spill Detection & Dark Vessel Attribution)
## Smart India Hackathon (SIH 2026) — Final Presentation Guide

---

### ⏱️ Pre-Flight Setup (5 Minutes Before Presentation)

1. **Start Database & Caches (Docker):**
   ```bash
   docker-compose up -d postgres redis
   ```
2. **Launch Backend API:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
3. **Launch Frontend Web App:**
   ```bash
   cd frontend
   npm run dev
   ```
4. **Open Browser:**
   - URL: `http://localhost:5173`
   - Set browser to Full Screen mode (`F11`).
5. **Verify Baseline State:**
   - Live telemetry status shows `AIS LIVE` (pulsing green dot).
   - India maritime view displays vessel vectors across Arabian Sea & Bay of Bengal.
   - Fixed strategic pins visible: `Bombay High (ONGC)`, `JNPT Port`, `Kandla Port`, `Gulf of Kutch MNP`.
   - `MT GUJARAT PRIDE` visible near Bombay High with active **red radar pulse**.

---

### 🎤 5-Minute Live Pitch & Demonstration Script

#### Step 1: The Platform Vision & Live Map [0:00 – 0:45]
> *"Honorable Jury members, this is **SATVIGIL** — India's multi-sensor satellite and maritime AI surveillance platform. What you see on screen is real-time AIS telemetry across Indian territorial waters and Exclusive Economic Zone (EEZ), rendered directly via WebGL."*

- **Visual Action:** Pan across Indian coastline; point out the active commercial vessels navigating shipping lanes.
- **Key Highlight:** Explain that hundreds of ships move through India's waters daily, but traditional monitoring cannot detect ships that deliberately turn off their transponders to dump toxic bilge oil.

#### Step 2: The Color Threat Matrix [0:45 – 1:30]
> *"SATVIGIL classifies all maritime activity using an automated 4-tier threat matrix:*
> - **🟢 Green (Normal):** Verified commercial traffic with active AIS transponders.
> - **🟡 Amber (Watch):** Elevated monitoring required (e.g. vessels near sensitive corridors).
> - **🟠 Orange (Warning):** Rule violations, such as fishing vessels loitering inside Marine Protected Areas.
> - **🔴 Red Blinking (Critical):** Immediate security alarms — dark vessels or active oil slicks."*

- **Visual Action:** Point to the Header status pills showing live counts (`1 Critical`, `1 Warning`, `6 Clear`).

#### Step 3: Dark Vessel Detection near Critical Infrastructure [1:30 – 2:30]
> *"Look at this blinking red marker near Mumbai offshore. This is the crude carrier **MT GUJARAT PRIDE** operating near the critical Bombay High oil fields. Our temporal tracking engine detected an AIS blackout lasting 45 minutes in a designated high-risk zone."*

- **Visual Action:** Click on the blinking red marker.
- **What Appears:** The interactive popup opens showing:
  - MMSI: `419082341` (Indian Flagged Tanker)
  - Speed: `0.2 kts` (Loitering)
  - Risk Score: `0.90` (CRITICAL)
  - `⚠️ Dark Vessel: Gap 45m`
- **Visual Action:** Point out the dashed red track line behind the ship showing where AIS went dark.
- **Sidebar Action:** Point to the corresponding Critical Alert card in the right-hand panel.

#### Step 4: Live Satellite Oil Spill Attribution (The Climax) [2:30 – 4:15]
> *"A dark ship is suspicious, but SATVIGIL provides definitive physical proof by correlating with Copernicus Sentinel-1C C-SAR (IW Swath, VV/VH) radar passes. Watch what happens when a new satellite pass detects an oil sheen."*

- **Visual Action:** Click the **`📡 Ingest SAR Orbit #142 (Sentinel-1C)`** button in the bottom-left overlay.
- **What Happens Automatically:**
  1. The map camera executes a smooth fly-to zoom directly into the Bombay High spill coordinates (`19.2000°N, 71.5000°E`).
  2. A semi-transparent dark red oil slick polygon renders on screen with a pulsing boundary.
  3. The **OIL SPILL DETECTED** popup opens displaying:
     - Area: `4.82 km²`
     - Model Confidence: Derived dynamically via EMSA CleanSeaNet 3-signal standard (backscatter attenuation $\Delta\sigma^0$, area plausibility, mask coherence)
     - Copernicus Sentinel-1C C-SAR Scene ID (`S1C_IW_GRDH_1SDV_20260910T053649_20260910T053714_055591_06C82F_B7E2`).
  4. **The Kinematic Backtracking + SVR Ensemble Attribution breakdown is displayed:**
     - **Top Suspect:** `MT GUJARAT PRIDE` (MMSI: `419082341`)
     - **Forensic Liability Score:** Blended kinematic hydrodynamic backtracking (70%) + SVR behavioral model (30%)
     - **Distance to Spill Center / CPA:** Minimum spatiotemporal approach to backtracked release corridor
     - **AIS Status:** 45-minute transponder blackout detected in proximity to Bombay High assets
- **Visual Action:** Click `"Inspect Suspect Vessel →"` to immediately target the suspect vessel.

#### Step 5: Real-World National Impact & Conclusion [4:15 – 5:00]
> *"In historical incidents like the 2011 MSC Chitra disaster, spill attribution took weeks of manual investigation while hundreds of tons of oil devastated the Konkan mangrove coast. With SATVIGIL, the Indian Coast Guard and Ministry of Ports receive automated evidence packets within minutes of a satellite pass."*
>
> *"SATVIGIL: Seeing the unseen, securing India's coastlines. Thank you."*

---

### 🛡️ Fallback & Offline Contingency Plan
- If internet connectivity drops or AISHub limits are reached, the system **automatically falls back** to the built-in verified scenario in `data/demo/ais_demo_scenario.json`.
- All API routes and map layers operate with zero cloud dependency during presentation.
