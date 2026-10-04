"""
Unit tests for SATVIGIL Agricultural Intelligence API routes (PS 26142).
Verifies NDVI vegetative health stats, AI field boundaries, and crop damage assessments.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_ndvi_summary():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/agri/ndvi")
        assert response.status_code == 200
        data = response.json()
        assert data["region"] == "Punjab"
        assert "zones" in data
        assert len(data["zones"]) >= 6
        assert "trend_weekly" in data
        assert len(data["trend_weekly"]) == 4
        assert "summary" in data
        assert data["summary"]["total_area_ha"] > 0
        
        # Verify zone structure
        first_zone = data["zones"][0]
        assert "id" in first_zone
        assert "name" in first_zone
        assert "ndvi" in first_zone
        assert "status" in first_zone
        assert "area_ha" in first_zone


@pytest.mark.asyncio
async def test_get_field_boundaries():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/agri/fields", params={"lat": 30.90, "lon": 75.85})
        assert response.status_code == 200
        data = response.json()
        assert "center" in data
        assert data["center"]["lat"] == 30.90
        assert data["center"]["lon"] == 75.85
        assert data["total_fields"] > 0
        assert data["avg_area_ha"] > 0
        assert data["fragmented_pct"] >= 0
        assert len(data["fields"]) > 0

        # Verify field structure
        field = data["fields"][0]
        assert "id" in field
        assert "coordinates" in field
        assert "area_ha" in field
        assert "crop" in field
        assert "ndvi" in field
        assert "health" in field


@pytest.mark.asyncio
async def test_get_damage_assessment():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/agri/damage", params={"event": "flood", "district": "vidarbha"})
        assert response.status_code == 200
        data = response.json()
        assert data["event"] == "flood"
        assert data["district"] == "Vidarbha"
        assert data["affected_area_ha"] > 0
        assert data["estimated_loss_crore"] > 0
        assert len(data["crop_breakdown"]) > 0
        assert data["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        # Verify crop breakdown
        crop = data["crop_breakdown"][0]
        assert "crop" in crop
        assert "affected_ha" in crop
        assert "loss_pct" in crop
