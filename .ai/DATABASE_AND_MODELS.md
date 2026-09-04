# SATVIGIL — Database & Schema Specifications

---

## 1. Engine & Extensions
- **RDBMS:** PostgreSQL 15+
- **Extension:** `postgis` (v3.3+)
- **ORM:** SQLAlchemy (Async) + `GeoAlchemy2`
- **Spatial Reference System (SRID):** `4326` (WGS 84 coordinate system)

---

## 2. Core Tables & Enums

### Enums
- **`AlertType`:** `oil_spill`, `illegal_fishing`, `fire_industrial`, `fire_wildfire`, `fire_stubble`, `fire_gas_flare`, `fire_mining`, `industrial_pollution`, `landslide_risk`
- **`RiskLevel`:** `low`, `medium`, `high`, `critical`

### Table 1: `alerts` (Unified Incident Record)
```python
# Defined in backend/app/models/alert.py
id: Integer, Primary Key
alert_type: Enum(AlertType), Indexed
risk_level: Enum(RiskLevel)
risk_score: Float (0.0 to 1.0)
latitude: Float
longitude: Float
location: Geometry("POINT", srid=4326) # PostGIS spatial index
title: String(255)
description: Text
source_dataset: String(100) # "FIRMS", "AIS", "SENTINEL"
confidence: String(20) # "low", "nominal", "high"
is_active: Boolean (default=True)
resolved_at: DateTime(timezone=True)
created_at: DateTime(timezone=True), Indexed
updated_at: DateTime(timezone=True)
```

### Table 2: `vessel_risk_records` (Maritime Behavior Tracking)
```python
id: Integer, Primary Key
mmsi: String(20), Indexed # Maritime Mobile Service Identity
vessel_name: String(255)
vessel_type: String(100)
risk_score: Float (0.0 to 1.0)
is_dark: Boolean # AIS transponder was switched off
is_loitering: Boolean # Speed < 1kt for > 60 minutes
inside_mpa: Boolean # Vessel located inside Marine Protected Area
last_known_lat: Float
last_known_lon: Float
ais_gap_minutes: Integer # Duration AIS transponder was silent
recorded_at: DateTime(timezone=True)
```

### Table 3: `thermal_hotspots` (NASA FIRMS Hotspots)
```python
id: Integer, Primary Key
latitude: Float
longitude: Float
location: Geometry("POINT", srid=4326)
frp: Float # Fire Radiative Power (MW)
brightness: Float # Temperature in Kelvin
confidence: String(20)
satellite: String(50)
acquired_at: DateTime(timezone=True)
fire_type: String(50) # classified category
land_use: String(100) # derived from OpenStreetMap
near_cpcb_cluster: Boolean # within 10km of CPCB polluted zone
recurrence_count: Integer # times cell has fired
created_at: DateTime(timezone=True)
```

---

## 3. Standard Spatial Queries in SATVIGIL
- **Radius Search:**
  ```sql
  SELECT * FROM alerts
  WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_meters);
  ```
- **Containment in Polygon (e.g., Marine Protected Area):**
  ```sql
  SELECT a.* FROM vessel_risk_records a, marine_protected_areas m
  WHERE m.name = 'Gulf of Kutch MNP' AND ST_Within(a.location, m.geom);
  ```
