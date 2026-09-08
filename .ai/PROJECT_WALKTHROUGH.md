# SATVIGIL — Complete Project Walkthrough
### *Read this before touching any code. Easy language, full picture.*

---

## Part 1: What Are We Actually Building?

Imagine Google Maps, but instead of showing traffic jams, it shows:
- 🛢️ Ships that are about to cause an oil spill
- 🚢 Boats illegally fishing inside protected sea zones
- 🔥 Factories that keep catching fire (on purpose or by accident)
- 🌋 Hillsides that are slowly sliding and about to collapse
- 🏭 Industrial areas polluting repeatedly but never getting caught

All of this, detected automatically from **satellites orbiting 700 km above India**.

That's SATVIGIL.

---

## Part 2: Why Does This Matter? (The Real Problem)

Right now, when bad things happen in India's coastal or industrial areas:

| Problem | Current Situation | What's Missing |
|---|---|---|
| Oil spill near Mumbai | Coast Guard finds out **after** someone sees oil on water | Nobody flagged the ship's suspicious movement **before** it spilled |
| Factory illegally burning at night | CPCB finds out months later during inspection | No one was watching from space every 3 hours |
| Hillside in Wayanad collapsing | People know it's risky area, but not **when** it will slide | No system measuring if the ground is already slowly moving |
| Forest fire in Western Ghats | FSI FAST system sends alert — but it also alerts for a farmer's field fire nearby | System can't tell the difference |

**The gap is not detection. The gap is early warning and classification.**

---

## Part 3: Our Solution in Plain English

We are building a **live map dashboard** where government officials can see:

```
[India map on screen]

🔴 Vessel "MV Bhavya" — Risk Score 0.87 — OFF Bombay High
   ↳ This ship turned off its GPS tracker for 2 hours near the Kandla oil terminal.
   ↳ Alert sent to: Indian Coast Guard

🟠 VIIRS Hotspot — Vapi, Gujarat — Industrial Fire
   ↳ This exact location has appeared 7 times in the last 3 months.
   ↳ This is NOT a coincidence. This is a repeat polluter.
   ↳ Alert sent to: CPCB + State Pollution Control Board

🟡 Ground Deformation — Joshimath, Uttarakhand
   ↳ The ground is moving 3.2mm per week. Trend is accelerating.
   ↳ Alert sent to: NDMA + Uttarakhand SDMA
```

The officials see it happening. They act before the disaster.

---

## Part 4: The Five Modules — One by One

---

### Module 1 — Oil Spill Detection 🛢️
**Problem Statement:** PS 143 (NTRO) — This is our PRIMARY deliverable.

**What the satellite sees:**
Oil floating on water absorbs light differently than clean water. When you look at a Sentinel-2
satellite image, an oil spill appears as a dark patch on the ocean surface. Our U-Net deep learning
model is trained to find these patches.

**The extra thing we do:**
We also track ships. Every ship above a certain size must broadcast its location every few minutes
via AIS (like a GPS transponder). When a ship **turns this off** near a sensitive area — that's
suspicious. We give that ship a risk score. If the risk score is high AND we see an oil spill
nearby — we can say with confidence "this ship probably caused it."

**Data sources:**
- Sentinel-2 satellite images → Free from ESA (European Space Agency)
- AIS ship positions → Free from AISHub or Global Fishing Watch

**Honest limitation:**
Sentinel-2 revisits the same spot every 5 days. So we cannot watch every moment. But AIS tracking
IS continuous — ships broadcast their position every few minutes. So vessel risk scoring is real-time,
even though the image confirmation isn't.

---

### Module 2 — Illegal Fishing Detection 🚢
**This is basically free to add** because it uses the same ship tracking data as Module 1.

**What we look for:**
India has Marine Protected Areas (MPAs) — ocean zones where fishing is banned to protect ecosystems.
The most important ones are:
- Gulf of Kutch Marine National Park (Gujarat)
- Gulf of Mannar Marine National Park (Tamil Nadu)
- Sundarbans Buffer Zone (West Bengal)

If a boat goes dark (turns off AIS transponder) **inside one of these zones**, we flag it.
Legitimate fishing boats don't need to hide. Boats doing illegal fishing do.

**Already coded:** The `is_vessel_in_mpa()` function in `backend/app/services/maritime/ais_fetcher.py`
already does this check. We just need to wire it to the database and the map.

---

### Module 3 — Fire Classification 🔥
**Problem Statement:** PS 162 (NTRO) — Secondary deliverable.

**The real problem:**
NASA already gives us a free fire detection service called FIRMS (Fire Information for Resource
Management System). It uses VIIRS and MODIS sensors on weather satellites. Every 3 hours, it tells
us where in India there is heat detected from space.

**The problem:** It gives us a dot on a map. It doesn't tell us:
- Is this a factory illegally burning waste?
- Is this a forest fire?
- Is this a farmer burning crop stubble in Punjab?
- Is this a natural gas flare from a refinery?
- Is this illegal coal mining activity?

**All of these look identical as a raw "thermal hotspot."**

**What we do differently:**
We apply a classification layer on top. Our system checks:

1. **Where is this hotspot?** (inside a forest? near a CPCB-flagged industrial area? on farmland?)
2. **When is it?** (October-November on farmland in Punjab = almost certainly stubble burning)
3. **How hot and how persistent?** (VIIRS Nightfire dataset can separate gas flares from actual fires)
4. **Has this location appeared before?** (same coordinates 7 times this quarter = repeat polluter)

**Result:** Instead of "there's heat here," we say:
> "This is an **industrial fire** at the Vapi Chemical Cluster. This same location has appeared
> 7 times in 3 months. Notify: **State Fire Services + CPCB + PESO**."

**Five fire types we classify:**
| Type | Example | Who Responds |
|---|---|---|
| Industrial fire | Refinery explosion in Visakhapatnam | PESO + State Fire Services |
| Gas flare | Routine/abnormal flaring at ONGC terminal | State Pollution Control Board |
| Stubble burning | Farmer burning crop waste in Amritsar | CAQM + District Magistrate |
| Wildfire | Forest fire in Uttarakhand | State Forest Department |
| Mining anomaly | Coal seam fire in Jharia, Jharkhand | IBM + State Mines Directorate |

---

### Module 4 — Industrial Pollution Recurrence 🏭
**This is built on top of Module 3** — same FIRMS data, extra logic layer.

**The insight:**
One fire = accident. Same location firing repeatedly = pattern of violation.

CPCB (Central Pollution Control Board) has publicly listed 43 "Critically Polluted Industrial
Clusters" across India — places like Vapi (Gujarat), Ludhiana (Punjab), Singrauli (MP), Jharia
(Jharkhand). These are areas CPCB has already flagged as chronically polluted.

Our system tracks: does a thermal hotspot keep appearing at the same GPS coordinates inside these
known industrial zones? If yes — we generate a "recurrence alert" with a timeline chart showing
how many times that exact location has been detected. This is legally usable evidence for CPCB
to take enforcement action.

**Already coded:** The `CPCB_CLUSTERS` list in `firms_fetcher.py` has 10 of the 43 clusters.
**Pending:** Someone needs to add the remaining 33 (Task J04 in the backlog).

---

### Module 5 — Landslide Risk (SAR) 🌋
**Priority: Build last. Use historical data, not live.**

**Why this is different from everything else:**
All other modules use optical satellites (they take pictures like a camera). Landslide detection
uses SAR — Synthetic Aperture Radar. Instead of light, SAR bounces radio waves off the Earth.
This means:
- Works through clouds (very important for Kerala/Himalayas in monsoon season)
- Works at night
- Can detect movement of **millimeters** over weeks

**InSAR technique explained simply:**
The satellite takes a radar "image" of a hillside on Day 1. Then again on Day 30. If the ground
has moved — even by 2-3 millimeters — the two images won't perfectly overlap. By comparing them,
we can make a "deformation map" showing which parts of the hill are moving.

**Why this beats the current government system (GSI):**
GSI (Geological Survey of India) predicts landslide risk based on rainfall — "it's raining heavily
in a risky zone, so be careful." Our system actually **measures if the ground is already moving**.
A slope can fail slowly over months with no rain. GSI's system would miss that. Ours wouldn't.

**What we'll demo:**
Pre-downloaded Sentinel-1 SAR images of Joshimath (Uttarakhand — the famous 2022-2023 subsidence
crisis) or Wayanad (Kerala). We process them offline BEFORE the hackathon, produce a deformation
heatmap, and show it as a static overlay on the map. We're honest that this is historical data,
not live — and that's fine for demonstrating the concept.

---

## Part 5: How the Whole System Works Together

```
[Every 15 minutes]
AIS Ship Data (AISHub API)
    ↓
ais_fetcher.py → calculate_vessel_risk_score()
    ↓
PostgreSQL (vessel_risk_records table)
    ↓
FastAPI route → /api/v1/maritime/vessels
    ↓
React frontend → Vessel dots on Mapbox GL map (color = risk score)


[Every 3 hours]
NASA FIRMS API (VIIRS thermal data)
    ↓
firms_fetcher.py → classify_fire() → get_responding_agency()
    ↓
PostgreSQL (thermal_hotspots table, recurrence_count updated)
    ↓
FastAPI route → /api/v1/fire/hotspots
    ↓
React frontend → Fire markers on map (icon = fire type)


[Every ~5 days, when new image available]
Sentinel-2 image (ESA Copernicus Hub)
    ↓
ESRGAN super-resolution model (upscale image quality)
    ↓
U-Net segmentation model (find oil slick pixels)
    ↓
Cross-reference with AIS vessel positions
    ↓
PostgreSQL (alerts table)
    ↓
FastAPI WebSocket broadcast → /api/v1/alerts/live
    ↓
React frontend → Toast notification + new alert in sidebar


[Pre-processed, static for demo]
Sentinel-1 SAR pairs (Joshimath or Wayanad)
    ↓
InSAR processing (SNAP toolbox — done offline)
    ↓
GeoTIFF deformation map
    ↓
Frontend → Raster overlay layer on map
```

---

## Part 6: The Tech Stack and Who Does What

Think of the project like a restaurant:

| Role | In the Restaurant | In SATVIGIL | Person |
|---|---|---|---|
| **Team Lead** | Head Chef | Designs architecture, connects all parts | Ravi |
| **Full Stack** | Kitchen Manager | Docker setup, glue code, deployment | Joy |
| **Backend** | Cook (dishes) | FastAPI routes, data fetchers, schedulers | Akshar |
| **ML/AI** | Pastry Chef (specialized) | PyTorch models (U-Net, ESRGAN), XGBoost classifier | Saksham |
| **Frontend** | Waiter + Interior Design | Mapbox map, React components, Tailwind UI | Arayan |
| **Data / Testing** | Ingredient Sourcer + Quality Control | GeoPandas spatial joins, test coverage, data pipeline | Krishika |
| **Presenter** | Front-of-House Manager | Demo script, slide narrative, pitch delivery | (Ravi or designated) |

**The actual technologies:**

```
Frontend:  React 18 + TypeScript + Vite
           Tailwind CSS (dark theme — bg-gray-950, text-white)
           Mapbox GL JS (the map engine — WebGL, handles moving vessels smoothly)
           Zustand (stores the list of alerts in browser memory)
           Recharts (risk score graphs and charts)
           Socket.io (receives live alerts pushed from backend)

Backend:   Python + FastAPI (all endpoints are async)
           SQLAlchemy + GeoAlchemy2 (talks to the database)
           APScheduler (runs the AIS/FIRMS fetch jobs on a timer)
           Celery + Redis (runs heavy ML jobs without blocking the API)
           structlog (structured logging — every event logged as key-value pairs)

ML:        PyTorch — U-Net for oil spill segmentation, ESRGAN for super-resolution
           XGBoost — Fire type classifier (FIRMS data is tabular, not images)
           Isolation Forest — Vessel behavioral anomaly detection

Geo:       GeoPandas — spatial joins (is this hotspot inside this polygon?)
           Shapely — geometry operations
           Rasterio — read/write satellite GeoTIFF image files
           PostGIS — spatial queries in PostgreSQL (ST_DWithin, ST_Within)

Database:  PostgreSQL 15 + PostGIS extension
           Redis — caches latest AIS positions (vessels update every 15 min)

Deploy:    Docker Compose — one command starts everything
```

---

## Part 7: What's Already Written vs. What Needs to Be Built

### ✅ Already Written and Working

**Backend logic:**
- `firms_fetcher.py` — fetches FIRMS data + classifies into 5 fire types + maps to agencies ✅
- `ais_fetcher.py` — fetches AIS data + scores vessel risk + checks MPA zones ✅
- `scheduler.py` — runs all fetch jobs on schedule ✅
- `database.py` — connects to PostgreSQL + PostGIS ✅
- `config.py` — reads all API keys from `.env` file ✅
- `main.py` — starts the FastAPI app with all routes ✅

**Database models:**
- `Alert` table (all hazard types unified) ✅
- `VesselRiskRecord` table (AIS tracking) ✅
- `ThermalHotspot` table (FIRMS data) ✅

**Frontend skeleton:**
- `App.tsx` — layout with map area and sidebar ✅
- `alertStore.ts` — Zustand state for alerts ✅
- `websocket.ts` — WebSocket client (receives real-time alerts) ✅

**Infrastructure:**
- `docker-compose.yml` — full stack in one command ✅
- `.env.example` — template for all secrets ✅

### ❌ Not Built Yet (Sprint 2 Tasks)

- Real database queries in the route files (currently all return fake/empty data)
- Pydantic schemas (request/response data validation)
- Mapbox GL JS map (the actual map in the browser)
- Alert sidebar component
- Layer toggles (switching between oil spill / fire / fishing views)
- AIS data → actually saving to database
- FIRMS data → actually saving to database
- ML models (U-Net, ESRGAN — these are the hardest parts, done last)
- Landslide SAR pre-processing (done offline before hackathon day)

---

## Part 8: The Build Order (What to Do First)

The rule: **always have something working on screen.** Never be in a state where nothing runs.

### Step 1 (Do this right now): Get the map on screen
Get a blank India map rendering in the browser. Put 5 fake marker dots on it.
One for each module. This is the scaffold. Everything else plugs in here.
**Who:** Arayan

### Step 2: Get AIS data flowing (Hours 3–12)
- Write the Pydantic schemas
- Call the AIS API → save to DB → fetch from DB → show on map as colored dots
- This is the PS 143 core. It must work end-to-end.
**Who:** Akshar (API) + Saksham (risk scoring) + Arayan (map markers)

### Step 3: Get FIRMS fire data flowing (Hours 12–20)
- Call NASA FIRMS API → classify each hotspot → save to DB → show on map as fire icons
- Add recurrence count logic
**Who:** Akshar (API + DB) + Saksham (classifier tuning)

### Step 4: Connect UI (Hours 20–28)
- Real alert sidebar (not fake data)
- Layer toggles working
- Click a vessel → see its risk history
- Click a fire → see which agency is alerted
**Who:** Arayan + Joy

### Step 5: Add landslide overlay (Hours 28–32)
- Load the pre-processed SAR deformation GeoTIFF
- Show as a color-gradient overlay on the map over Joshimath/Wayanad
**Who:** Krishika (data prep) + Arayan (overlay)

### Step 6: Polish + Demo rehearsal (Hours 32–36)
- Fix bugs, smooth animations
- Rehearse the demo flow
- Ensure all five modules visible on one screen
**Who:** Everyone

---

## Part 9: The Honest Pitch (What to Say to Judges)

**What we detect:** Not just incidents — we predict risk BEFORE they happen.

**What makes us different from what already exists:**

| Existing System | What it does | What it can't do | We fix this by... |
|---|---|---|---|
| NASA FIRMS | Detects heat from space | Can't tell factory from forest fire from stubble | 5-class XGBoost classifier |
| FSI FAST | Alerts forest officers to fires | Only talks to Forest Dept, can't distinguish fire types | We route to all 5 agencies |
| GSI Landslide Maps | Shows historically risky zones | Doesn't watch ground in real-time | SAR InSAR deformation monitoring |
| AIS Ship Tracking | Shows where ships are | Doesn't score risk or flag suspicious patterns | Behavioral risk scoring + MPA check |
| CPCB Inspections | Periodic ground inspections | Misses repeated pollution between inspections | Satellite recurrence tracking with evidence |

**One sentence for judges:**
> *"We don't just tell you what happened — we tell you what's about to happen, and who's responsible, before it becomes a disaster."*

---

## Part 10: Quick Reference — Where is Everything?

| You want to... | Go to... |
|---|---|
| Understand WHY a feature exists | `.ai/PITCH_AND_PRODUCT.md` |
| See all API routes | `.ai/API_REFERENCE.md` |
| Know the full tech stack | `.ai/ARCHITECTURE.md` |
| Know what's already written | `.ai/CURRENT_STATE.md` |
| Pick up a task | `tasks/TASK_BACKLOG.md` |
| Understand DB schema | `.ai/DATABASE_AND_MODELS.md` |
| Know coding rules | `.ai/CODING_STANDARDS.md` |
| Set up local environment | `docs/deployment/DEPLOYMENT.md` |
| Run the backend | `cd backend && uvicorn app.main:app --reload` |
| Run everything | `docker-compose up -d` |
| Fill in API keys | Copy `.env.example` → `.env`, fill values |
