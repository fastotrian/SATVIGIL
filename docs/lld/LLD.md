# SATVIGIL — Low-Level Design (LLD)

## 1. Database Schema

### Table: `alerts`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| alert_type | ENUM | oil_spill, illegal_fishing, fire_*, industrial_pollution, landslide_risk |
| risk_level | ENUM | low, medium, high, critical |
| risk_score | FLOAT | 0.0–1.0 |
| latitude | FLOAT | |
| longitude | FLOAT | |
| location | GEOMETRY(POINT, 4326) | PostGIS spatial index |
| title | VARCHAR(255) | Human-readable alert title |
| description | TEXT | Detailed alert info |
| source_dataset | VARCHAR | "FIRMS", "AIS", "SENTINEL-1" |
| confidence | VARCHAR | "low", "nominal", "high" |
| is_active | BOOLEAN | |
| created_at | TIMESTAMPTZ | Indexed |

### Table: `vessel_risk_records`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| mmsi | VARCHAR(20) | AIS vessel identifier |
| vessel_name | VARCHAR | |
| risk_score | FLOAT | 0.0–1.0 (composite behavioral score) |
| is_dark | BOOLEAN | AIS transponder was off |
| is_loitering | BOOLEAN | Speed < 1kt for > 60min |
| inside_mpa | BOOLEAN | Inside Marine Protected Area |
| last_known_lat/lon | FLOAT | |
| ais_gap_minutes | INT | Duration AIS was off |
| recorded_at | TIMESTAMPTZ | |

### Table: `thermal_hotspots`
| Column | Type | Description |
|---|---|---|
| id | SERIAL PK | |
| latitude/longitude | FLOAT | |
| location | GEOMETRY(POINT, 4326) | |
| frp | FLOAT | Fire Radiative Power in MW |
| brightness | FLOAT | Brightness temperature (K) |
| confidence | VARCHAR | FIRMS confidence level |
| satellite | VARCHAR | S-NPP, NOAA-20, etc. |
| acquired_at | TIMESTAMPTZ | When satellite detected |
| fire_type | VARCHAR | industrial/wildfire/stubble/gas_flare/mining |
| land_use | VARCHAR | From OSM lookup |
| near_cpcb_cluster | BOOLEAN | Within 10km of CPCB zone |
| recurrence_count | INT | Times same cell has fired |

---

## 2. Fire Classification Algorithm

```
Input: FIRMS detection row (lat, lon, frp, daynight, acq_date, confidence)
       + OSM land_use lookup at (lat, lon)

Step 1: is_near_cpcb_cluster(lat, lon, radius=10km)?
  YES + daynight=N + frp > 50 → fire_type = "gas_flare"
  YES + frp > 300             → fire_type = "industrial"

Step 2: land_use == forest/wood?
  YES → fire_type = "wildfire"

Step 3: land_use == farmland AND month in [10,11,12,1,2,3]?
  YES → fire_type = "stubble"

Step 4: land_use == quarry/mine?
  YES → fire_type = "mining"

Step 5: frp > 300 (fallback high-energy)?
  YES → fire_type = "industrial"

Default → fire_type = "unknown"

Output: fire_type + responding_agency + risk_score
```

---

## 3. Vessel Risk Scoring Algorithm

```
Input: AIS vessel record + AIS gap history

risk_score = 0.0

if ais_gap_minutes > 30:  risk_score += 0.40
if ais_gap_minutes > 10:  risk_score += 0.20  (else)

if vessel inside MPA:     risk_score += 0.30

if speed < 1kt AND gap > 60min:  risk_score += 0.20 (loitering)

if vessel_type in [80-89] (tanker):  risk_score += 0.10

risk_score = min(risk_score, 1.0)

Risk level:
  0.0 - 0.3 → LOW (green marker)
  0.3 - 0.6 → MEDIUM (yellow marker)
  0.6 - 0.8 → HIGH (orange marker)
  0.8 - 1.0 → CRITICAL (red marker)
```

---

## 4. API Endpoints

### Alerts
```
GET  /api/v1/alerts/              — List all active alerts (filterable)
GET  /api/v1/alerts/{id}          — Single alert details
WS   /api/v1/alerts/live          — WebSocket: real-time new alert push
```

### Maritime
```
GET  /api/v1/maritime/vessels     — Current vessel risk scores
GET  /api/v1/maritime/vessel/{mmsi} — Vessel history + risk timeline
GET  /api/v1/maritime/mpas        — Marine Protected Area GeoJSON
```

### Fire
```
GET  /api/v1/fire/hotspots        — Current classified fire hotspots
GET  /api/v1/fire/recurrence      — Recurring hotspot analysis by coordinates
GET  /api/v1/fire/agencies        — Agency routing for each fire type
```

### Landslide
```
GET  /api/v1/landslide/zones      — SAR deformation zones (GeoJSON)
GET  /api/v1/landslide/history    — Historical deformation trend at location
```

### Pollution
```
GET  /api/v1/pollution/clusters   — CPCB cluster locations + hotspot counts
GET  /api/v1/pollution/timeline   — Thermal recurrence timeline for a facility
```

---

## 5. Frontend Component Tree

```
App
├── DashboardHeader          (logo, module toggle, alert count badge)
├── MapView                  (Mapbox GL JS full-screen map)
│   ├── VesselLayer          (ship markers color-coded by risk score)
│   ├── FireLayer            (hotspot markers with type icon)
│   ├── PollutionLayer       (recurring hotspot heatmap)
│   ├── LandslideLayer       (SAR deformation polygon overlay)
│   ├── MPALayer             (Marine Protected Area boundaries)
│   └── LayerToggle          (on/off switches per module)
└── AlertPanel               (right sidebar)
    ├── AlertList            (scrollable, newest first)
    │   └── AlertCard        (title, type badge, risk badge, timestamp)
    └── AlertDetail          (expanded view when alert clicked)
        ├── AlertMap         (mini-map zoomed to alert location)
        ├── RiskTimeline     (recurrence chart for this location)
        └── AgencyInfo       (which agency to notify + action)
```

---

## 6. Celery Task Queue

```
Task: classify_firms_batch
  Input: List of FIRMS rows (from APScheduler job)
  Process: OSM lookup → classify each → check recurrence → persist → broadcast WebSocket
  Queue: "fire"

Task: score_vessel_batch
  Input: List of AIS vessel positions
  Process: Score each → check MPA → persist → broadcast WebSocket
  Queue: "maritime"

Task: process_sentinel_scene
  Input: Sentinel-1 C-SAR IW GRDH GeoTIFF path
  Process: Despeckling (Lee 7x7) → Otsu thresholding → morphological boundary extraction → backscatter delta verification → broadcast
  Queue: "imagery" (radar processing)
```
