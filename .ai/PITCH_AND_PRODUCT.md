# SATVIGIL — Product, Pitch & Problem Statement Reference

> **Purpose for AI Agents:** This file captures the WHY behind every product decision.
> Before implementing any feature, read this to understand the design intent, the real Indian
> government actors involved, and the competitive differentiation over existing solutions.

---

## 1. Problem Statements We Are Targeting

| PS # | Ministry / Body | Title | Status |
|---|---|---|---|
| **PS 143** | NTRO | Real-time Oil Spill Detection + AIS Correlation | 🎯 **PRIMARY** — Core deliverable |
| **PS 162** | NTRO | Industrial Fire & Thermal Source Classification | ✅ Additional module built on same stack |

**Both are NTRO (National Technical Research Organisation) cluster PS.**
The approach: solve PS 143 as the graded deliverable, extend the same satellite data pipeline
to cover PS 162 — giving us a credible "platform" story, not a single-purpose tool.

---

## 2. One-Liner

> *SATVIGIL is an AI-powered satellite monitoring platform that predicts and attributes
> maritime and industrial environmental risks along India's coastline — before they become
> disasters, not just after.*

---

## 3. The Five Detection Modules

### Module 1: Oil Spill Detection (PS 143 Core)
**What it does:** Detects oil spill sheens on water surface using Sentinel-2 optical imagery
(dark patches with distinct spectral signature), then cross-references AIS vessel tracking to
attribute the likely responsible vessel.

**Why it's better than detection-only:**
Every competitor will build "we detected a spill." We build "we flagged the ship BEFORE
it caused a spill" by scoring vessel behavior over time — AIS dark gaps, loitering near
offshore fields, movement patterns historically linked to illegal discharge.

**Key Indian geography:**
- Bombay High offshore (ONGC's largest field — MSC Chitra 2011 spill is a real case reference)
- JNPT, Kandla, Paradip, Chennai port approach zones
- Sentinel-2 optical imagery (free, ESA Copernicus)

**Real-world case:** MSC Chitra collision near Mumbai, 2011 — two ships collided, one leaked
oil near Mumbai's coast. This is a citable example in the pitch.

---

### Module 2: Illegal Fishing Detection
**What it does:** Flags vessels that switch off AIS transponders inside Marine Protected Areas.
Same AIS pipeline as Module 1 — near-zero extra build cost.

**Logic:**
- Vessel going dark (AIS gap > 30 min) inside Gulf of Kutch MNP / Gulf of Mannar MNP /
  Sundarbans buffer = HIGH RISK flag
- `is_vessel_in_mpa()` function already implemented in `backend/app/services/maritime/ais_fetcher.py`

**Indian MPAs defined in code (bounding boxes — replace with full GeoJSON polygons for production):**
- Gulf of Kutch Marine National Park
- Gulf of Mannar Marine National Park
- Sundarbans Buffer Zone
- Malvan Marine National Park

**Government actor:** Indian Coast Guard + State Fisheries Departments

---

### Module 3: Fire Classification (PS 162 Core)
**The core problem:** NASA FIRMS sees every hotspot as just "heat here." A factory illegally
burning waste, a forest fire, and a farmer burning stubble all look identical as raw thermal data.
Classification turns an unusable firehose into routed, actionable alerts.

**Five classified fire types and responding agencies:**

| Fire Type | Primary Dataset | Responding Agency | Legal Basis |
|---|---|---|---|
| **Industrial fire** (explosion, refinery) | VIIRS 375m + FIRMS | State Fire Services + PESO + CPCB | Petroleum Rules / Static & Mobile Pressure Vessels Rules |
| **Gas flare** (abnormal/excessive) | VIIRS Nightfire (VNF) | State PCB show-cause notice | Air (Prevention & Control of Pollution) Act |
| **Agricultural burning** (stubble) | VIIRS 375m + MODIS NDVI seasonal | CAQM + District Magistrate | CAQM Act 2021, Section 14 |
| **Wildfire** | VIIRS 375m + forest boundary layer | State Forest Department + FSI FAST system | Forest Act |
| **Mining thermal anomaly** | Landsat thermal bands + IBM lease DB | IBM + State Directorate of Mines & Geology | MMDR Act 1957 |

**Classification logic (rule-based + XGBoost — fast to build, judges love explainability):**
1. Location context: is hotspot inside CPCB industrial cluster / forest boundary / cropland?
2. Recurrence pattern: same coordinates repeatedly = industrial (not random wildfire)
3. Seasonal timing: Punjab/Haryana cropland + October-November = stubble burning
4. VIIRS Nightfire data specifically separates gas flares from fires (purpose-built NOAA product)

**India-scale of the problem:**
- Punjab/Haryana/UP recorded ~91,000 stubble fires in a single peak season
- 90% of India's forest fires are human-caused
- CPCB flagged 43 industrial clusters in 17 states as "Critically Polluted Areas"

**Why we're better than FSI's FAST system:**
FSI FAST already detects wildfires. We don't compete with it — we complement it:
1. **False positive reduction:** FAST flags any heat near forest land. A stubble fire adjacent
   to a forest triggers a false wildfire alert. Our multi-class classifier prevents this.
2. **Cross-agency routing:** FAST only talks to the Forest Department. We route the same
   satellite pass's data to five different agencies simultaneously.
3. **Pattern tracking:** FAST alerts per-incident, no memory. We track recurrence across seasons
   giving the Forest Department which forest patches burn repeatedly (for prevention planning).

---

### Module 4: Industrial Pollution Recurrence
**What it does:** Tracks recurring thermal hotspots at the same GPS coordinates over time.
Same FIRMS data as Module 3 — piggybacks on the fire classification pipeline.

**Logic:** One hotspot = incident. Same coordinates firing 4+ times in a quarter = pattern
of violation = legally usable enforcement evidence for CPCB.

**Validation:** CPCB's public "43 Critically Polluted Areas" list is the validation dataset.

**Government actor:** CPCB + State Pollution Control Boards

---

### Module 5: Landslide Risk (SAR — Low Priority, Build Last)
**What it does:** Uses Sentinel-1 SAR InSAR (Interferometric SAR) to detect millimeter-level
ground deformation on slopes — weeks or months before a slope actually fails.

**Why SAR, not optical:** Western Ghats and Himalayas are cloud-covered. Optical satellites
(Sentinel-2) are useless in monsoon season — exactly when landslide risk peaks. SAR penetrates
clouds and works at night.

**Two-layer approach:**
1. SAR/InSAR (slow layer): finds which slopes are already quietly moving weeks ahead
2. Rainfall forecasting (fast layer): when heavy rain hits a pre-flagged weakening slope,
   issue urgent alert — much more precise than rainfall-only systems

**How we're better than GSI's system:**
- GSI system is rainfall-threshold + static susceptibility maps (predicts risk from rain proxy)
- We directly measure actual ground movement (the physical precursor)
- GSI live in only ~3 pilot districts as of 2023. Sentinel-1 covers any site.
- Source: Business Standard/PTI, May 2023
  https://www.business-standard.com/india-news/geological-survey-of-india-plans-to-launch-landslide-warning-system-in-2026-123051100850_1.html

**Pre-selected demo sites:** Wayanad (Kerala) or Joshimath (Uttarakhand)

**Indian landslide scale:** ~22,497 deaths recorded 1980-2019. 12.6% of India's land area
(0.42 million sq km) is landslide-prone.

**Government actor:** NDMA + State Disaster Management Authorities (Kerala, Uttarakhand)

---

## 4. Shared Technical Backbone

A super-resolution deep learning model (ESRGAN) sits underneath Modules 1, 2, and 3.
It upscales medium-resolution satellite imagery so smaller oil sheens, thin spill trails,
and localized hotspots that would be missed at native resolution become detectable.

**Pitch line:** "We didn't build five detectors — we built one shared prediction engine
applied across five risk domains."

---

## 5. Data Sources (All Free / Public)

| Module | Dataset | Source | Update Frequency |
|---|---|---|---|
| Oil spill imagery | Sentinel-2 optical | ESA Copernicus Hub (free) | ~5 day revisit |
| Vessel tracking | AIS data | AISHub free tier / Global Fishing Watch | Near real-time |
| Fire / thermal | VIIRS 375m active fire | NASA FIRMS API (free) | ~3 hour latency |
| Gas flare vs. fire | VIIRS Nightfire (VNF) | NOAA / Colorado School of Mines (free) | Nightly |
| Land cover context | Forest + cropland bounds | Global Forest Watch + MODIS NDVI | Static + seasonal |
| Industrial facilities | CPCB critically polluted areas | CPCB public list (free) | Annual |
| Landslide SAR | Sentinel-1 SAR | ESA Copernicus Hub (free) | 6-12 day revisit |

---

## 6. What is Honest vs. Overclaimed

**Be honest about these in the pitch — judges will test this:**

- Satellite revisit ≠ live CCTV. VIIRS passes India 2-4x/day (~3hr latency). Sentinel-2 every
  ~5 days. Sentinel-1 SAR every 6-12 days. Never say "real-time live satellite feed."
- SAR/InSAR cannot catch a sudden rain-triggered landslide in real time. It catches slow
  chronic instability (weeks/months). This is why we pair it with rainfall forecasting.
- For the hackathon (36 hours): landslide module uses pre-downloaded historical Sentinel-1 pairs,
  not live streaming. State this clearly — it is a valid and honest approach.

---

## 7. Target Users / Government Actors

| User | Module(s) They Use |
|---|---|
| NTRO | All modules (primary sponsor) |
| Indian Coast Guard | Module 1 (spill), Module 2 (illegal fishing) |
| NDMA + State DMAs (Kerala, Uttarakhand, Himachal) | Module 5 (landslide) |
| CPCB + State Pollution Control Boards | Module 3 (fire classification), Module 4 (recurrence) |
| Forest Survey of India / State Forest Depts | Module 3 (wildfire routing via FAST integration) |
| Port Authorities (JNPT, Kandla, Paradip) | Module 1 (vessel risk near ports) |

---

## 8. 36-Hour Hackathon Build Priority Order

1. **Hours 0-3:** Map scaffold with fake markers (all 6 members must see this working first)
2. **Hours 3-12:** AIS pipeline + spill/fishing risk logic (primary PS deliverable — highest priority)
3. **Hours 12-20:** FIRMS pipeline + fire classification (Module 3 + 4)
4. **Hours 20-26:** Pre-process SAR overlay for one site (Wayanad or Joshimath) — parallel track
5. **Hours 26-32:** Alert panel UI, color coding, layer toggles, connecting all modules
6. **Hours 32-36:** Buffer for bugs + demo rehearsal + pitch deck

---

## 9. Key References Used in Pitch

- **Business Standard/PTI (May 2023):** GSI's rainfall-based landslide system, pilot in 3 districts
- **CPCB Comprehensive Environmental Assessment (2009):** 43 critically polluted industrial clusters
- **NASA FIRMS:** https://firms.modaps.eosdis.nasa.gov/api/ — VIIRS 375m NRT, free, ~3hr latency
- **VIIRS Nightfire (VNF):** NOAA/Colorado School of Mines — purpose-built gas flare detector
- **CAQM Act 2021, Section 14:** Legal basis for stubble burning enforcement (DMs can file criminal complaints)
- **MMDR Act 1957:** Legal basis for illegal mining enforcement
- **MSC Chitra spill (2011):** Real Indian oil spill case study near Mumbai coast
