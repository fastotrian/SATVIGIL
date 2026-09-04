# SATVIGIL — Coding & Engineering Standards

---

## 1. Python & FastAPI Standards

1. **Async by Default:** Use `async def` for FastAPI endpoints and DB queries with `AsyncSession`.
2. **Schema Separation:**
   - Database models live in `backend/app/models/`.
   - Pydantic request/response schemas live in `backend/app/schemas/`.
   - Never return raw SQLAlchemy model instances without converting through a Pydantic schema.
3. **Environment & Secrets:**
   - Never hardcode API keys (NASA FIRMS, Mapbox tokens, database passwords).
   - Use `backend/app/core/config.py` with `pydantic-settings` to load from `.env`.
4. **Error Handling:**
   - Raise `fastapi.HTTPException` with meaningful `status_code` and `detail`.
   - Validate geospatial coordinates (`-90 <= lat <= 90`, `-180 <= lon <= 180`).
5. **Structured Logging:** Use `structlog` (already configured). Log events with key-value pairs,
   not f-strings. e.g., `logger.info("firms_fetch_success", rows=len(df), sensor=sensor)`.

---

## 2. Frontend Standards (React + TypeScript + Tailwind)

1. **Strict TypeScript:** No `any` types unless interfacing with dynamic third-party map events.
2. **Styling: Tailwind CSS (v3)** — This project uses Tailwind CSS. Do NOT add plain CSS files or
   inline `style={{}}` props for layout/theme. Use Tailwind utility classes.
   - Dark theme: `bg-gray-950`, `bg-gray-900`, `text-white`, `border-gray-800`
   - Responsive: use Tailwind breakpoint prefixes (`sm:`, `lg:` etc.)
3. **State Management:** Use Zustand (`frontend/src/store/alertStore.ts`) for global alert states and active filters.
4. **Map Rendering:**
   - Mapbox GL JS map instance must be preserved across renders using `useRef`.
   - Use GeoJSON sources and vector layers (`map.addSource`, `map.addLayer`) for high performance.
   - Do NOT render 1,000 React DOM markers; use Mapbox circle/symbol layers with clustering.
   - India map bounds: `[[68.1, 7.9], [97.4, 35.5]]` — restrict zoom to not go below city level
     (native resolution of satellite data won't support building-level zoom).
5. **No placeholder images:** Use real data or clearly labeled "No data" empty states.

---

## 3. Geospatial Standards

1. **Always use SRID 4326 (WGS 84)** — all coordinates in decimal degrees, all PostGIS geometries
   with `srid=4326`. Never store coordinates in any other CRS without explicit conversion.
2. **Spatial queries must use PostGIS functions:**
   ```sql
   -- Radius search (always use geography cast for meter-accurate results)
   SELECT * FROM alerts
   WHERE ST_DWithin(
       location::geography,
       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
       :radius_meters
   );
   ```
3. **Point-in-polygon for MPA / CPCB zones:** Use `ST_Within` or GeoPandas `sjoin` — never
   manually check bounding-box corners for production code (the bounding-box lookup in
   `ais_fetcher.py` is a temporary stub for demo; replace with GeoJSON polygon for accuracy).
4. **GeoTIFF processing:** Use `rasterio` for reading Sentinel imagery. Always close file handles
   with context managers (`with rasterio.open(...) as src:`).

---

## 4. ML & Classification Standards

1. **Fire classifier is XGBoost (tabular), not deep learning** — FIRMS data is CSV rows with
   numeric features (lat, lon, FRP, brightness, confidence). Use scikit-learn-compatible XGBoost
   pipeline, not a neural network. This is intentional for explainability and speed.
2. **Vessel risk score is 0.0–1.0** — already implemented in `ais_fetcher.py`. Do not change the
   scoring scale without updating all downstream consumers (API responses, frontend color thresholds).
3. **Super-resolution:** ESRGAN pretrained weights are available at inference time — do NOT train
   from scratch during hackathon. Use pretrained weights, fine-tune only if time permits.
4. **Never hallucinate model outputs:** If a model isn't loaded / data isn't available, return
   `confidence: "low"` and `risk_score: null` — don't return fake values.

---

## 5. Git & Team Workflow

1. **Branches:**
   - Main branch: `main` (protected for stable releases).
   - Feature branches: `feat/<your-name>-<feature>` (e.g., `feat/joy-firms-fetcher`).
   - Fixes: `fix/<your-name>-<bug>`.
2. **Commit Messages:** Follow conventional commits:
   - `feat: ...` for new features
   - `fix: ...` for bug fixes
   - `docs: ...` for documentation
   - `chore: ...` for refactoring or dependencies
3. **Before Pushing:**
   - Run tests (`pytest` in backend).
   - Check formatting.

---

## 6. Role → Tech Stack Quick Reference

| Team Member | Primary Stack | Focus |
|---|---|---|
| **Ravi Yadav** | Architecture + FastAPI + PostGIS + Integration | System design, connecting all modules |
| **Joy** | Full Stack (FastAPI + React + Docker) | Glue layer, deployment, Docker Compose wiring |
| **Saksham** | PyTorch + XGBoost + GeoPandas | ML models: U-Net (spill), fire classifier |
| **Arayan** | React + Mapbox GL JS + Tailwind | Frontend map, layer toggles, alert UI |
| **Krishika** | Python + GeoPandas + pytest | Data pipeline, spatial joins, test coverage |
| **Akshar** | FastAPI routes + APScheduler + Redis | Backend API implementation, data fetchers |

---

## 7. Security Notes

- `.env` file is **gitignored** — never commit it.
- `.env.example` is committed — always update it when adding new env vars.
- API keys to keep secret: `FIRMS_MAP_KEY`, `AISHUB_USERNAME`, `COPERNICUS_CLIENT_ID/SECRET`,
  `VITE_MAPBOX_TOKEN`, `POSTGRES_PASSWORD`.
