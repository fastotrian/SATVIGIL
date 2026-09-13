"""
SATVIGIL — End-to-End API Integration Test Suite
Tests HTTP routes, PostGIS alert persistence, radar processing, and WebSocket handshake.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """Shared TestClient instance across integration test suite."""
    with TestClient(app) as c:
        yield c


class TestHealthAndAlertsIntegration:
    def test_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "satvigil-api"

    def test_list_alerts_endpoint(self, client):
        response = client.get("/api/v1/alerts/")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total" in data
        assert len(data["alerts"]) >= 1

    def test_filter_alerts_by_type(self, client):
        response = client.get("/api/v1/alerts/?alert_type=oil_spill")
        assert response.status_code == 200
        data = response.json()
        for alert in data["alerts"]:
            assert alert["alert_type"] == "oil_spill"

    def test_get_alert_by_id(self, client):
        response = client.get("/api/v1/alerts/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "alert_type" in data
        assert "risk_level" in data
        assert "risk_score" in data

    def test_get_alert_dossier(self, client):
        response = client.get("/api/v1/alerts/1/dossier")
        assert response.status_code == 200
        dossier = response.json()
        assert "dossier_id" in dossier
        assert "satellite_sar" in dossier
        assert "culprit_vessel" in dossier
        assert "statutory_violations" in dossier
        assert dossier["culprit_vessel"]["mmsi"] == "419082341"  # MT GUJARAT PRIDE
        assert len(dossier["evidence_sha256_hash"]) == 64


class TestMaritimeIntegration:
    def test_maritime_vessels_list(self, client):
        response = client.get("/api/v1/maritime/vessels")
        assert response.status_code == 200
        data = response.json()
        assert "vessels" in data
        assert len(data["vessels"]) >= 1
        vessel = data["vessels"][0]
        assert "mmsi" in vessel
        assert "lat" in vessel
        assert "lon" in vessel

    def test_maritime_spills_detection(self, client):
        response = client.get("/api/v1/maritime/spills")
        assert response.status_code == 200
        spills = response.json()
        assert isinstance(spills, list)
        assert len(spills) >= 1
        spill = spills[0]
        assert 0.0 < spill["confidence"] <= 1.0
        assert "geojson_polygon" in spill
        assert spill["geojson_polygon"]["type"] == "Polygon"

    def test_model_status_endpoint(self, client):
        response = client.get("/api/v1/maritime/model-status")
        assert response.status_code == 200
        data = response.json()
        assert "engine_name" in data
        assert "methodology" in data
        assert "feature_signals" in data
        assert len(data["feature_signals"]) == 4

    def test_simulate_spill_triggers_persistence(self, client):
        payload = {
            "spill_lat": 19.20,
            "spill_lon": 71.50,
            "spill_trail_bearing": 250.0
        }
        response = client.post("/api/v1/maritime/simulate-spill", json=payload)
        assert response.status_code == 200
        spill = response.json()
        assert spill["id"].startswith("SPILL-IN-")
        assert len(spill["top_candidates"]) >= 1

        # Check that the simulated spill was persisted and is returned by the alerts endpoint
        alerts_resp = client.get("/api/v1/alerts/")
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()["alerts"]
        assert len(alerts) >= 1
        # The latest alert should be the newly dispatched spill alert
        assert "SAR Oil Spill Alert" in alerts[0]["title"]


class TestSatelliteIntegration:
    def test_satellite_scenes(self, client):
        response = client.get("/api/v1/satellite/scenes?sector=bombay_high&days_back=14&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert "scenes" in data
        assert len(data["scenes"]) >= 1
        assert "scene_id" in data["scenes"][0]
        assert "satellite" in data["scenes"][0]

    def test_satellite_detect_spills(self, client):
        payload = {"lat": 19.20, "lon": 71.50}
        response = client.post("/api/v1/satellite/detect-spills", json=payload)
        assert response.status_code == 200
        detection = response.json()
        assert detection["status"] == "DETECTED"
        assert detection["satellite"] == "Sentinel-1C C-SAR"
        assert detection["backscatter_delta_db"] <= -4.0
        assert len(detection["evidence_sha256"]) == 64

    def test_satellite_subsystem_status(self, client):
        response = client.get("/api/v1/satellite/status")
        assert response.status_code == 200
        status = response.json()
        assert status["status"] == "OPERATIONAL"
        assert "subsystem" in status
        assert "5.405 GHz" in status["instrument"]


class TestFireIntegration:
    def test_fire_hotspots(self, client):
        response = client.get("/api/v1/fire/hotspots")
        assert response.status_code == 200
        data = response.json()
        assert "hotspots" in data
        assert len(data["hotspots"]) >= 1


class TestWebSocketLiveAlerts:
    def test_websocket_alerts_handshake(self, client):
        """Test WebSocket client connection and initial alert synchronization."""
        with client.websocket_connect("/api/v1/alerts/live") as websocket:
            data = websocket.receive_json()
            assert data["event"] == "init"
            assert isinstance(data["data"], list)
            assert len(data["data"]) >= 1
