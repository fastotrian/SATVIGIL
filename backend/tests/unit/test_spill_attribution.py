"""
Unit tests for SATVIGIL oil spill attribution scoring.
Tests both the SVR model path AND the heuristic fallback.
"""
import sys
import os
import pytest
import numpy as np
from pathlib import Path

# Ensure the backend app is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.services.maritime.spill_attribution import (
    haversine,
    heading_alignment_score,
    backtrack_slick_origin,
    calculate_cpa_distance,
    score_vessel_for_spill,
    rank_vessels_for_spill,
    get_model_metadata,
    calculate_behavior_score_from_track,
    VESSEL_TYPE_RISK,
    VESSEL_TYPE_SPEED_MEAN,
)


# ── Haversine distance ────────────────────────────────────────────────────────

class TestHaversine:
    def test_zero_distance(self):
        assert haversine(19.0, 71.0, 19.0, 71.0) == 0.0

    def test_known_distance_bombay_goa(self):
        # Mumbai (18.96, 72.82) to Goa (15.49, 73.82) ≈ 393 km
        dist = haversine(18.96, 72.82, 15.49, 73.82)
        assert 380 < dist < 420, f"Expected ~393 km, got {dist}"

    def test_symmetry(self):
        d1 = haversine(19.0, 71.0, 22.0, 69.0)
        d2 = haversine(22.0, 69.0, 19.0, 71.0)
        assert abs(d1 - d2) < 0.01


# ── Heading alignment ─────────────────────────────────────────────────────────

class TestHeadingAlignment:
    def test_perfect_alignment(self):
        score = heading_alignment_score(250.0, 250.0)
        assert score == 1.0

    def test_opposite_heading(self):
        score = heading_alignment_score(70.0, 250.0)
        assert score < 0.3

    def test_45_degree_offset(self):
        # Exactly at tolerance boundary — should be 0.7
        score = heading_alignment_score(205.0, 250.0)
        assert 0.65 < score < 0.75

    def test_output_bounded(self):
        for hdg in range(0, 360, 30):
            score = heading_alignment_score(float(hdg), 250.0)
            assert 0.0 <= score <= 1.0, f"heading_score out of bounds at {hdg}°"


# ── Vessel type risk encoding ─────────────────────────────────────────────────

class TestVesselTypeRisk:
    def test_tanker_highest(self):
        assert VESSEL_TYPE_RISK[80] == 1.0

    def test_fishing_lowest_category(self):
        assert VESSEL_TYPE_RISK[30] < 0.15

    def test_cargo_between_tanker_and_fishing(self):
        assert VESSEL_TYPE_RISK[30] < VESSEL_TYPE_RISK[70] < VESSEL_TYPE_RISK[80]


# ── score_vessel_for_spill ────────────────────────────────────────────────────

SPILL_LAT, SPILL_LON = 19.20, 71.50

def _make_vessel(mmsi, vtype, lat, lon, speed, course, gap):
    return {
        "MMSI": str(mmsi),
        "NAME": f"TEST-{mmsi}",
        "TYPE": vtype,
        "LATITUDE": lat,
        "LONGITUDE": lon,
        "SPEED": speed,
        "COURSE": course,
        "ais_gap_minutes": gap,
    }


class TestScoreVesselForSpill:
    def test_returns_none_beyond_cutoff(self):
        vessel = _make_vessel("419001001", 80, 12.0, 60.0, 10.0, 180.0, 0)
        result = score_vessel_for_spill(vessel, SPILL_LAT, SPILL_LON, distance_cutoff_km=50.0)
        assert result is None

    def test_returns_dict_within_cutoff(self):
        vessel = _make_vessel("419001002", 80, 19.15, 71.45, 6.0, 174.0, 47)
        result = score_vessel_for_spill(vessel, SPILL_LAT, SPILL_LON, distance_cutoff_km=50.0)
        assert result is not None
        assert "risk_score" in result
        assert "distance_km" in result
        assert "behavioral_anomaly" in result

    def test_risk_score_bounded(self):
        for vtype, lat, lon, gap in [
            (80, 19.15, 71.45, 47),   # tanker near spill, AIS gap
            (30, 22.5,  69.2,   0),   # fishing vessel far
            (70, 18.95, 72.85,  0),   # cargo, normal
        ]:
            vessel = _make_vessel("419001010", vtype, lat, lon, 8.0, 90.0, gap)
            result = score_vessel_for_spill(vessel, SPILL_LAT, SPILL_LON, distance_cutoff_km=500.0)
            if result:
                assert 0.0 <= result["risk_score"] <= 1.0, (
                    f"risk_score {result['risk_score']} out of [0,1] for type={vtype}"
                )

    def test_tanker_with_ais_gap_scores_high(self):
        """Tanker near spill with 47-min AIS gap must score higher than fishing vessel without gap."""
        tanker  = _make_vessel("419001020", 80, 19.15, 71.45, 6.0, 174.0, 47)
        fishing = _make_vessel("419001021", 30, 19.10, 71.48, 5.0, 90.0,   0)

        t_score = score_vessel_for_spill(tanker,  SPILL_LAT, SPILL_LON, distance_cutoff_km=50.0)
        f_score = score_vessel_for_spill(fishing, SPILL_LAT, SPILL_LON, distance_cutoff_km=50.0)

        assert t_score is not None
        assert f_score is not None
        assert t_score["risk_score"] > f_score["risk_score"], (
            f"Tanker {t_score['risk_score']} should > fishing {f_score['risk_score']}"
        )


# ── rank_vessels_for_spill ────────────────────────────────────────────────────

class TestRankVesselsForSpill:
    def test_returns_top_n(self):
        vessels = [
            _make_vessel(f"4190010{i:02d}", 80 if i < 3 else 30,
                         19.0 + i * 0.1, 71.0 + i * 0.1, 8.0, 180.0, 10 * i)
            for i in range(10)
        ]
        ranked = rank_vessels_for_spill(vessels, SPILL_LAT, SPILL_LON, top_n=5)
        assert len(ranked) <= 5

    def test_sorted_descending(self):
        vessels = [
            _make_vessel("419002001", 80, 19.15, 71.45, 6.0, 174.0, 47),
            _make_vessel("419002002", 30, 22.5,  69.2,   5.0, 45.0,   0),
            _make_vessel("419002003", 70, 18.95, 72.85, 12.0, 95.0,   0),
        ]
        ranked = rank_vessels_for_spill(vessels, SPILL_LAT, SPILL_LON,
                                        distance_cutoff_km=500.0, top_n=5)
        scores = [r["risk_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True), f"Not sorted: {scores}"

    def test_empty_fleet(self):
        result = rank_vessels_for_spill([], SPILL_LAT, SPILL_LON)
        assert result == []


# ── Hydrodynamic Backtracking ────────────────────────────────────────────────

class TestBacktrackSlickOrigin:
    def test_backtracking_moves_updrift(self):
        # Slick at (19.20, 71.50) with ESE current (115 deg) + SE wind (120 deg)
        # Backtracking backwards in time must move WNW (lat increases, lon decreases)
        orig_lat, orig_lon, drift_km = backtrack_slick_origin(19.20, 71.50, elapsed_hours=4.0)
        assert drift_km > 0.0
        assert orig_lon < 71.50, f"Expected origin to be west of slick, got {orig_lon}"
        assert orig_lat > 19.20, f"Expected origin to be north of slick, got {orig_lat}"

    def test_zero_elapsed_hours(self):
        orig_lat, orig_lon, drift_km = backtrack_slick_origin(19.20, 71.50, elapsed_hours=0.0)
        assert drift_km == 0.0
        assert abs(orig_lat - 19.20) < 1e-4
        assert abs(orig_lon - 71.50) < 1e-4


# ── Closest Point of Approach (CPA) ──────────────────────────────────────────

class TestCPACalculation:
    def test_point_on_segment_has_near_zero_cpa(self):
        # Midpoint of segment from (19.25, 71.35) to (19.20, 71.50)
        mid_lat = (19.25 + 19.20) / 2.0
        mid_lon = (71.35 + 71.50) / 2.0
        cpa = calculate_cpa_distance(mid_lat, mid_lon, 19.20, 71.50, 19.25, 71.35)
        assert cpa < 0.2, f"Expected CPA near 0 km, got {cpa} km"

    def test_point_far_has_large_cpa(self):
        cpa = calculate_cpa_distance(20.50, 72.50, 19.20, 71.50, 19.25, 71.35)
        assert cpa > 50.0, f"Expected CPA > 50 km, got {cpa} km"


# ── Engine Metadata ──────────────────────────────────────────────────────────

class TestModelMetadata:
    def test_metadata_structure(self):
        meta = get_model_metadata()
        assert "engine_name" in meta
        assert "physics_formulation" in meta
        assert "statutory_standards" in meta
        assert "telemetry_provenance" in meta
        assert "validation_metrics" in meta
        assert meta["validation_metrics"]["reproducibility"] == "100% Deterministic (Admissible in Admiralty Court)"


# ── Track-based Behavior Scoring ──────────────────────────────────────────────

class TestTrackBehaviorScore:
    def test_empty_track(self):
        spill_time = np.datetime64("2026-09-12T10:00:00")
        score = calculate_behavior_score_from_track([], spill_time)
        assert score == 0.0

    def test_insufficient_points(self):
        spill_time = np.datetime64("2026-09-12T10:00:00")
        track = [
            {"timestamp": "2026-09-12T09:00:00", "sog": 12.0},
            {"timestamp": "2026-09-12T10:00:00", "sog": 12.2},
        ]
        score = calculate_behavior_score_from_track(track, spill_time)
        assert score == 0.0

    def test_uniform_speed_no_anomaly(self):
        spill_time = np.datetime64("2026-09-12T10:00:00")
        track = [
            {"timestamp": "2026-09-12T08:00:00", "sog": 12.0},
            {"timestamp": "2026-09-12T09:00:00", "sog": 12.0},
            {"timestamp": "2026-09-12T10:00:00", "sog": 12.0},
            {"timestamp": "2026-09-12T11:00:00", "sog": 12.0},
        ]
        score = calculate_behavior_score_from_track(track, spill_time)
        assert score == 0.0

    def test_anomalous_speed_spike_or_drop(self):
        spill_time = np.datetime64("2026-09-12T10:00:00")
        # 10 points cruising at 12 knots, sudden drop to 1.5 knots
        track = [{"timestamp": f"2026-09-12T0{i}:00:00", "sog": 12.0} for i in range(1, 9)]
        track.append({"timestamp": "2026-09-12T09:00:00", "sog": 1.0})
        score = calculate_behavior_score_from_track(track, spill_time)
        assert score >= 0.7, f"Expected anomaly >= 0.7 for severe speed drop, got {score}"

    def test_points_outside_window_filtered(self):
        spill_time = np.datetime64("2026-09-12T10:00:00")
        # All points 48 hours earlier (window is 12 hours)
        track = [
            {"timestamp": "2026-09-10T01:00:00", "sog": 12.0},
            {"timestamp": "2026-09-10T02:00:00", "sog": 12.0},
            {"timestamp": "2026-09-10T03:00:00", "sog": 1.0},
        ]
        score = calculate_behavior_score_from_track(track, spill_time, time_window_hours=12)
        assert score == 0.0


