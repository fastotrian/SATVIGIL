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

---

## 2. Frontend Standards (React + TypeScript)

1. **Strict TypeScript:** No `any` types unless interfacing with dynamic third-party map events.
2. **State Management:** Use Zustand (`frontend/src/store/alertStore.ts`) for global alert states and active filters.
3. **Map Rendering:**
   - Mapbox GL JS map instance must be preserved across renders using `useRef`.
   - Use GeoJSON sources and vector layers (`map.addSource`, `map.addLayer`) for high performance.
   - Do NOT render 1,000 React DOM markers; use Mapbox circle/symbol layers with clustering.

---

## 3. Git & Team Workflow

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
