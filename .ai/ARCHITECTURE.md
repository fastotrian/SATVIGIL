# SATVIGIL — System Architecture Reference

---

## 1. High-Level Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION SOURCES                          │
│   NASA FIRMS API │ AISHub / GFW │ Sentinel-1 SAR │ Sentinel-2 Optical │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                    DATA PIPELINE & SCHEDULER                           │
│   FastAPI APScheduler (15m AIS, 3h FIRMS) → Processors → GeoPandas     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                           AI / ML ENGINES                              │
│   • Fire 5-Class Classifier (XGBoost + FRP + OSM Land Use)             │
│   • Vessel Risk Scorer (Isolation Forest + AIS Gap Analysis)          │
│   • Oil Spill Segmentation (PyTorch U-Net on Sentinel-2)               │
│   • Landslide Deformation (Sentinel-1 InSAR + Rainfall Thresholds)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                      STORAGE & CACHE LAYER                             │
│   • PostgreSQL 15 + PostGIS (Spatial indexing, Geometries, ACID)      │
│   • Redis (Pub/Sub for WebSockets, Celery task queue, Rate limiting)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                     BACKEND APPLICATION (FastAPI)                      │
│   • REST API (/api/v1/alerts, /api/v1/fire, /api/v1/maritime)         │
│   • WebSocket Server (/api/v1/alerts/live) for real-time broadcasts    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       FRONTEND DASHBOARD                               │
│   • React 18 + TypeScript + Vite + Mapbox GL JS (WebGL 60fps)          │
│   • 5 Multi-hazard Layer Switchers, Critical Alert Banner              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Five Detection Modules & Agency Routing

| Module | Sensor / Input | Algorithm | Output | Target Indian Agency |
|---|---|---|---|---|
| **1. Oil Spill Detection** | Sentinel-2 + AIS | U-Net sheen segmenter + vessel proximity correlation | Polygon sheen + Risk-scored ship | Indian Coast Guard + INCOIS |
| **2. Illegal Fishing** | AIS feeds (AISHub) | Geofencing inside Marine Protected Areas + Dark transponder gap detection | Red marker + MMSI + Gap duration | Indian Coast Guard + State Fisheries |
| **3. Fire Classification** | NASA FIRMS (VIIRS 375m NRT) | 5-class XGBoost: Industrial, Wildfire, Stubble, Gas Flare, Mining | Classified alert marker + FRP MW | PESO / Forest Dept / CAQM / IBM |
| **4. Industrial Pollution** | FIRMS historical archives | Spatial recurrence aggregation within 10km of CPCB clusters | Thermal recurrence heatmap | CPCB + State PCBs |
| **5. Landslide Risk** | Sentinel-1 SAR | InSAR ground phase interferometry + IMD rainfall overlay | Millimeter deformation heatmap | NDMA + SDMAs |

---

## 3. Satellite Physics & Honest Latency Model

When asked to implement or document data pipelines, remember that satellites are governed by orbital physics:
- **MODIS (Terra & Aqua):** Revisit India 2–4 times/day. Latency ~3 hours.
- **VIIRS (Suomi-NPP & NOAA-20):** Revisit India 2–4 times/day (375m resolution). Latency ~3 hours.
- **Sentinel-2 (Optical):** Revisit every 2–3 days. Latency ~24 hours. (Requires clear skies / daytime).
- **Sentinel-1 (SAR Radar):** Revisit every 6–12 days. Latency ~24 hours. (Works through clouds and night).
