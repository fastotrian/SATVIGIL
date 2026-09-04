-- SATVIGIL — PostGIS Initialization
-- Runs once when the PostgreSQL container starts for the first time

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Spatial index on alerts table (created after Alembic migration)
-- This file just ensures PostGIS is enabled
SELECT PostGIS_Version();
