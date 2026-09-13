"""
Unit tests for SATVIGIL Satellite SAR Oil Spill Detection Pipeline
and Copernicus Data Space Ecosystem (CDSE) Ingestion.
"""
import sys
import pytest
import numpy as np
from pathlib import Path

# Ensure backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.services.satellite.sar_spill_detector import (
    apply_lee_speckle_filter,
    compute_otsu_threshold,
    simulate_realistic_sar_backscatter_patch,
    detect_oil_slick_from_sar,
    SAR_FREQUENCY_GHZ,
)
from app.services.satellite.copernicus_cdse import (
    search_sentinel1_scenes,
    INDIAN_SAR_SECTORS,
)


class TestLeeSpeckleFilter:
    def test_filter_preserves_shape_and_range(self):
        rng = np.random.default_rng(123)
        # Synthetic noisy radar patch
        patch = rng.gamma(shape=4.4, scale=1.0, size=(64, 64))
        filtered = apply_lee_speckle_filter(patch, window_size=5, num_looks=4.4)

        assert filtered.shape == patch.shape
        assert np.all(filtered >= 0.0)
        # Speckle filter must reduce variance across homogeneous noise
        assert np.var(filtered) < np.var(patch)

    def test_filter_preserves_mean(self):
        rng = np.random.default_rng(456)
        patch = rng.gamma(shape=4.4, scale=2.0, size=(100, 100))
        filtered = apply_lee_speckle_filter(patch, window_size=7, num_looks=4.4)
        assert abs(np.mean(filtered) - np.mean(patch)) < 0.1


class TestOtsuThreshold:
    def test_bimodal_separation(self):
        # Mixture of two Gaussians: dark slick (mean=10) and bright sea (mean=50)
        rng = np.random.default_rng(789)
        slick_pixels = rng.normal(10.0, 2.0, size=500)
        sea_pixels = rng.normal(50.0, 5.0, size=1500)
        bimodal = np.concatenate([slick_pixels, sea_pixels])

        thresh = compute_otsu_threshold(bimodal)
        assert 15.0 < thresh < 45.0, f"Expected threshold between 15 and 45, got {thresh}"


class TestSARSimulationAndDetection:
    def test_synthetic_patch_physics(self):
        linear, db = simulate_realistic_sar_backscatter_patch(grid_size=128)
        assert linear.shape == (128, 128)
        assert db.shape == (128, 128)
        # Average center (where slick is) should be darker than periphery
        center_slice = db[48:80, 48:80]
        corner_slice = db[:32, :32]
        assert np.mean(center_slice) < np.mean(corner_slice)

    def test_detect_oil_slick_complete_pipeline(self):
        detection = detect_oil_slick_from_sar(center_lat=19.20, center_lon=71.50)

        assert detection["status"] == "DETECTED"
        assert detection["satellite"] == "Sentinel-1C C-SAR"
        assert detection["radar_frequency_ghz"] == SAR_FREQUENCY_GHZ
        assert detection["slick_area_km2"] > 0.5
        assert detection["backscatter_delta_db"] <= -5.0  # Clear backscatter drop
        assert len(detection["evidence_sha256"]) == 64   # Valid SHA-256

        # GeoJSON validation
        geojson = detection["geojson_polygon"]
        assert geojson["type"] == "Polygon"
        coords = geojson["coordinates"][0]
        assert len(coords) >= 4
        assert coords[0] == coords[-1]  # Closed polygon

    def test_real_sar_raster_loading_and_detection(self):
        detection = detect_oil_slick_from_sar(center_lat=19.20, center_lon=71.50, force_simulation=False)
        assert detection["status"] == "DETECTED"
        assert detection["processing_mode"] in [
            "SENTINEL1_CSAR_IW_GRDH_CALIBRATED_RASTER",
            "PHYSICALLY_CALIBRATED_RADAR_EVALUATION"
        ]
        assert "radar_source" in detection
        assert detection["slick_area_km2"] > 0.5
        assert len(detection["evidence_sha256"]) == 64

    def test_forced_simulation_mode(self):
        detection = detect_oil_slick_from_sar(center_lat=19.20, center_lon=71.50, force_simulation=True)
        assert detection["processing_mode"] == "PHYSICALLY_CALIBRATED_RADAR_EVALUATION"
        assert detection["radar_source"] == "SYNTHETIC_CALIBRATED_EMSA_PATCH"
        assert detection["backscatter_delta_db"] <= -5.0


@pytest.mark.asyncio
class TestCopernicusCDSE:
    async def test_search_scenes_structure(self):
        scenes = await search_sentinel1_scenes(sector="bombay_high", days_back=14, limit=2)
        assert len(scenes) >= 1
        first = scenes[0]
        assert "scene_id" in first
        assert "satellite" in first
        assert "sensor_mode" in first
        assert "polarization" in first
        assert "footprint_geojson" in first
        assert first["sensor_mode"].startswith("IW")
