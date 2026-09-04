# SATVIGIL — Data Guide

## Registration Checklist (Do First — Before Any Code)

| Service | URL | Time to Activate |
|---|---|---|
| NASA FIRMS MAP_KEY | https://firms.modaps.eosdis.nasa.gov/api/map_key/ | Instant (email) |
| Copernicus Dataspace | https://dataspace.copernicus.eu/ | Minutes |
| AISHub | https://www.aishub.net/ | 1-2 hours (manual approval) |
| Global Fishing Watch | https://globalfishingwatch.org/data/ | Minutes |
| Mapbox | https://account.mapbox.com/ | Instant |

---

## Dataset 1: NASA FIRMS (Fire/Thermal Data)

**URL:** https://firms.modaps.eosdis.nasa.gov/api/
**Cost:** FREE — requires MAP_KEY (email registration, instant)
**Rate limit:** 5,000 transactions / 10-minute window

### API Endpoint (India, near real-time)
```
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/{BBOX}/{DAYS}

Where BBOX = 68.1766451354,7.96553477623,97.4025614766,35.4940095078 (India)
      DAYS = 1 to 10
```

### Response Columns
| Column | Description | Used For |
|---|---|---|
| latitude | Fire latitude | Location |
| longitude | Fire longitude | Location |
| frp | Fire Radiative Power (MW) | Industrial classification |
| bright_ti4 | Brightness temp channel 4 (K) | Fire intensity |
| confidence | low / nominal / high | Filter noise |
| acq_date | YYYY-MM-DD | Seasonal classification |
| acq_time | HHMM | Day/night classification |
| daynight | D or N | Gas flare detection |
| satellite | NPP, NOAA-20, etc. | Source tracking |

### Historical Archive (for training)
URL: https://firms.modaps.eosdis.nasa.gov/download/
- Select: Region=South Asia, Country=India, Sensor=VIIRS, Format=CSV
- Coverage: VIIRS from January 2012 to present
- Use: Download 2020–2024 data for training the classifier + building recurrence history

---

## Dataset 2: AIS Vessel Tracking

### Option A: AISHub (Recommended — Free, needs approval)
**URL:** https://www.aishub.net/
**API:** `https://data.aishub.net/ws.php?username={USER}&format=1&output=json&latmin=6&latmax=24&lonmin=67&lonmax=98`

Key fields: MMSI, LATITUDE, LONGITUDE, SPEED, COURSE, HEADING, TYPE, NAME, TIMESTAMP

### Option B: Global Fishing Watch (Free API token)
**URL:** https://globalfishingwatch.org/data-download/
- Already classifies fishing vs. non-fishing behavior
- Better for the illegal fishing module specifically
- API: https://globalfishingwatch.org/data/

### AIS Vessel Type Codes (relevant to SATVIGIL)
| Code Range | Vessel Type |
|---|---|
| 70-79 | Cargo vessels |
| 80-89 | Tankers (highest spill risk) |
| 30 | Fishing vessels |
| 90-99 | Other (includes dredgers, tugs) |

---

## Dataset 3: Sentinel-2 Optical Imagery (Oil Spill Detection)

**URL:** https://dataspace.copernicus.eu/
**Cost:** FREE — requires Copernicus account
**Resolution:** 10m (Band 2,3,4,8) — 20m (Band 11,12 — best for oil spills)

### What to Download
- Band 11 (SWIR 1640nm) and Band 12 (SWIR 2200nm) for oil slick detection
- Oil appears as a darker anomaly compared to surrounding water
- Download for: India's west coast (Gujarat coast, Mumbai coast, Goa)

### Copernicus Catalog API (programmatic download)
```python
import requests
url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
params = {
    "Collection/Name eq 'SENTINEL-2'",
    "OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((...))')",
    "$top=5"
}
```

---

## Dataset 4: Sentinel-1 SAR (Landslide Module)

**URL:** https://dataspace.copernicus.eu/ (same account as Sentinel-2)
**Cost:** FREE
**Revisit:** ~6-12 days per site

### Pre-selected Validation Sites (download before hackathon)
| Site | Reason | Approximate Coordinates |
|---|---|---|
| Wayanad, Kerala | 2024 landslide event | 11.6°N, 76.1°E |
| Joshimath, Uttarakhand | 2023 subsidence | 30.6°N, 79.6°E |
| Darjeeling, WB | GSI pilot area | 27.0°N, 88.3°E |

### Processing Tool
- **SNAP Toolbox** (free, from ESA): https://step.esa.int/main/toolboxes/snap/
- Used for InSAR processing (co-registration → interferogram → phase unwrapping → deformation map)
- Pre-process BEFORE the hackathon — this takes hours per scene pair

---

## Dataset 5: OpenStreetMap Land Use (Fire Classification Context)

**URL:** https://download.geofabrik.de/asia/india.html
**Cost:** FREE
**Format:** .osm.pbf + .shp
**Updated:** Daily

### Key Land Use Tags for Fire Classification
| OSM Tag | → Fire Classification |
|---|---|
| landuse=industrial | industrial |
| natural=wood, landuse=forest | wildfire |
| landuse=farmland, meadow | stubble |
| landuse=quarry, landuse=mine | mining |
| amenity=fuel + landuse=industrial | gas_flare |

### Spatial Join (Python)
```python
import geopandas as gpd
from shapely.geometry import Point

# Load OSM landuse polygons (download from Geofabrik)
landuse_gdf = gpd.read_file("india_landuse.shp")

# Create GeoDataFrame from FIRMS points
fires_gdf = gpd.GeoDataFrame(
    firms_df,
    geometry=gpd.points_from_xy(firms_df.longitude, firms_df.latitude),
    crs="EPSG:4326"
)

# Spatial join: each fire point gets the land use of the polygon it falls in
fires_with_landuse = gpd.sjoin(fires_gdf, landuse_gdf, how="left", predicate="within")
```

---

## Dataset 6: VIIRS Nightfire (Gas Flare Separation)

**URL:** https://eogdata.mines.edu/products/vnf/
**Cost:** FREE (no API key required — direct download)
**Coverage:** Global, from 2012

Purpose: Separates persistent gas flares from wildfire/stubble using temperature signatures.
VIIRS Nightfire was specifically designed to distinguish high-temperature biomass burning from low-temperature persistent gas flaring.

---

## Data Quality Checks

Run `python data_pipeline/validators/data_checker.py` to verify:

1. **FIRMS data completeness** — check for missing columns, null coordinates, date gaps
2. **AIS position plausibility** — speed > 50 knots = likely erroneous, lat/lon in Indian Ocean bounds
3. **Sentinel scene coverage** — verify scene overlaps your target coastal areas before processing
4. **CPCB cluster coordinates** — cross-check against Google Maps before going live
