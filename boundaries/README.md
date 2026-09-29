# Boundaries Directory

This directory stores geospatial boundaries for SATVIGIL's territorial validation and fire/environmental intelligence engines.

## Files

1. **`india_boundary.geojson`** (Committed)
   - Sovereign political boundary of the Republic of India.
   - Used by `geo_intelligence.py` for terrestrial geofencing and excluding false-positive maritime/extraterrestrial detections.

2. **`Bharatmaps_RFA.geojsonl`** (Local Only / Excluded from Git due to file size >1.5 GB)
   - Recorded Forest Area (RFA) polygons from Bharatmaps.
   - Excluded from Git via `.gitignore` to comply with GitHub's 100 MB file limit.
   - If running forest polygon intersection queries locally, place the `Bharatmaps_RFA.geojsonl` file in this directory. If absent, `geo_intelligence.py` automatically falls back to authoritative regional forest bounding boxes (`FOREST_ZONES`) with zero disruption to functionality.
