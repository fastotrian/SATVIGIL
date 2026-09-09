# SATVIGIL — API Reference

> **For AI Agents:** This is the single source of truth for all backend API endpoints.
> When adding a new route, update this file immediately.

Base URL (local dev): `http://localhost:8000`
API Prefix: `/api/v1`
Interactive docs: `http://localhost:8000/docs` (FastAPI auto-generated Swagger UI)

---

## 1. Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Returns `{"status": "ok", "database": "connected"}` |

---

## 2. Alerts (Unified — All Modules)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/alerts` | List all active alerts (paginated) |
| `GET` | `/api/v1/alerts/near` | Alerts within radius of a coordinate |
| `GET` | `/api/v1/alerts/{id}` | Get single alert details |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Mark alert as resolved and broadcast to WS |
| `WS` | `/api/v1/alerts/live` | WebSocket — push new alerts to connected clients |

**Query params for `GET /api/v1/alerts`:**
- `alert_type`: `oil_spill` | `illegal_fishing` | `fire_industrial` | `fire_wildfire` | `fire_stubble` | `fire_gas_flare` | `fire_mining` | `industrial_pollution` | `landslide_risk`
- `risk_level`: `low` | `medium` | `high` | `critical`
- `is_active`: bool (default `true`)
- `limit`: int (default 50)
- `offset`: int (default 0)

**Query params for `GET /api/v1/alerts/near`:**
- `lat`: float (decimal degrees)
- `lon`: float (decimal degrees)
- `radius_km`: float (kilometers)

---

## 3. Maritime (Spill + Fishing)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/maritime/vessels` | List currently tracked vessels with risk scores |
| `GET` | `/api/v1/maritime/vessels/{mmsi}` | Single vessel detail + AIS history |
| `GET` | `/api/v1/maritime/spills` | Active oil spill detections |
| `GET` | `/api/v1/maritime/risk-zones` | High-risk zones (MPAs, offshore fields) as GeoJSON |

**Vessel risk score schema:**
```json
{
  "mmsi": "string",
  "vessel_name": "string",
  "risk_score": 0.0,
  "is_dark": false,
  "is_loitering": false,
  "inside_mpa": false,
  "ais_gap_minutes": 0,
  "last_known_lat": 0.0,
  "last_known_lon": 0.0
}
```

---

## 4. Fire Classification

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/fire/hotspots` | All classified thermal hotspots |
| `GET` | `/api/v1/fire/hotspots?type=industrial` | Filtered by fire type |
| `GET` | `/api/v1/fire/recurrence` | Locations with recurring hotspot pattern |

**Fire type enum values:** `industrial` | `gas_flare` | `wildfire` | `stubble` | `mining` | `unknown`

**Hotspot schema:**
```json
{
  "id": 1,
  "latitude": 20.37,
  "longitude": 72.90,
  "frp": 312.5,
  "brightness": 340.2,
  "fire_type": "industrial",
  "land_use": "industrial",
  "near_cpcb_cluster": true,
  "cpcb_cluster_name": "Vapi",
  "confidence": "high",
  "acquired_at": "2026-09-05T00:00:00Z",
  "recurrence_count": 7,
  "responding_agency": "State Fire Services + CPCB",
  "recommended_action": "Emergency response + PESO investigation"
}
```

---

## 5. Landslide

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/landslide/deformation` | SAR-derived deformation zones as GeoJSON |
| `GET` | `/api/v1/landslide/risk-areas` | Pre-classified high-risk zones with metadata |

---

## 6. Industrial Pollution

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/pollution/heatmap` | Thermal recurrence heatmap data (GeoJSON) |
| `GET` | `/api/v1/pollution/clusters` | CPCB clusters with recurrence stats |

---

## 7. Route Files Location

All routes are in `backend/app/api/routes/`:
- [`alerts.py`](../backend/app/api/routes/alerts.py)
- [`maritime.py`](../backend/app/api/routes/maritime.py)
- [`fire.py`](../backend/app/api/routes/fire.py)
- [`landslide.py`](../backend/app/api/routes/landslide.py)
- [`pollution.py`](../backend/app/api/routes/pollution.py)
- [`health.py`](../backend/app/api/routes/health.py)

---

## 8. WebSocket Protocol

**Endpoint:** `ws://localhost:8000/api/v1/alerts/live`

**Server → Client message format:**
```json
{
  "event": "new_alert",
  "data": {
    "id": 1,
    "alert_type": "oil_spill",
    "risk_level": "critical",
    "risk_score": 0.87,
    "latitude": 19.2,
    "longitude": 71.5,
    "title": "Suspected vessel discharge near Bombay High",
    "source_dataset": "AIS",
    "created_at": "2026-09-05T02:00:00Z"
  }
}
```

Client connects, receives all current active alerts on connect, then receives push messages as new alerts are created.
