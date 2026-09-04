# SATVIGIL — Deployment Guide

## Hackathon Demo (Local Docker Compose)

### Prerequisites
- Docker Desktop installed and running
- Git

### Steps

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd SATVIGIL

# 2. Set up environment
cp .env.example .env
# Open .env and fill in:
#   FIRMS_MAP_KEY, AISHUB_USERNAME, AISHUB_PASSWORD, VITE_MAPBOX_TOKEN

# 3. Start all services
docker-compose up --build

# 4. Verify everything is running
docker-compose ps
# Should show: postgres, redis, backend, celery_worker, frontend — all "Up"

# 5. Access the app
open http://localhost:3000        # Frontend dashboard
open http://localhost:8000/docs   # Backend API docs (FastAPI auto-generated)
```

### Stopping
```bash
docker-compose down
docker-compose down -v   # Also remove volumes (wipes DB data)
```

---

## Local Development (Without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run FastAPI dev server (auto-reloads on code change)
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Services needed locally
```bash
# PostgreSQL with PostGIS (using Docker just for this)
docker run -d --name satvigil_pg \
  -e POSTGRES_DB=satvigil \
  -e POSTGRES_USER=satvigil_user \
  -e POSTGRES_PASSWORD=satvigil_pass \
  -p 5432:5432 \
  postgis/postgis:15-3.3

# Redis
docker run -d --name satvigil_redis -p 6379:6379 redis:7-alpine
```

---

## Database Migrations (Alembic)

```bash
cd backend

# Create a new migration (after changing models)
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Demo Preparation Checklist (Night Before)

- [ ] All 5 API keys registered and in `.env`
- [ ] `docker-compose up` runs cleanly on your demo machine
- [ ] FIRMS data loads (test: `/api/v1/fire/hotspots`)
- [ ] AIS data loads (test: `/api/v1/maritime/vessels`)
- [ ] Map renders centered on India with markers visible
- [ ] Alert panel shows at least 1 real alert
- [ ] WebSocket connection established (check browser console)
- [ ] Pre-downloaded historical FIRMS data loaded for recurrence demo
- [ ] Landslide SAR overlay pre-processed and ready (static file)
- [ ] Backup: screenshots/screen recording if live demo fails

---

## Port Reference

| Service | Port |
|---|---|
| Frontend (React) | 3000 |
| Backend (FastAPI) | 8000 |
| API Docs (Swagger) | 8000/docs |
| PostgreSQL | 5432 |
| Redis | 6379 |
