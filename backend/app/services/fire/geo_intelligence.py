"""
SATVIGIL — Fire Module: Geo-Intelligence Engine (V2)
Processes sovereign boundaries (india_boundary.geojson) and Recorded Forest Areas (Bharatmaps_RFA.geojsonl)
to provide high-precision spatial context for satellite thermal hotspot classification.
Reference: scripts/india_fire_intelligence_v2 (1).py
"""
import os
import math
from pathlib import Path
from typing import Tuple, Optional, List
import structlog
from shapely.geometry import shape, Point
import json

logger = structlog.get_logger()

# Authoritative Forest Regional Belts across India
FOREST_ZONES = [
    (8.0, 14.5, 74.0, 78.5, "Western Ghats South"),
    (14.0, 20.5, 73.0, 80.5, "Western Ghats Central & Deccan"),
    (18.0, 24.5, 78.0, 84.5, "Central Highlands & Dandakaranya"),
    (20.0, 27.0, 81.0, 87.5, "Chota Nagpur & Eastern Ghats"),
    (22.0, 27.0, 88.0, 92.5, "North-East Hills & Sunderbans"),
    (27.0, 35.5, 73.0, 80.5, "Western Himalayas"),
    (28.0, 35.5, 80.0, 93.5, "Eastern Himalayas & Assam Valley"),
]

# Major Coal & Mineral Mining Belts
MINING_ZONES = [
    (23.60, 23.95, 86.20, 86.55, "Jharia"),
    (23.55, 23.95, 86.60, 87.20, "Raniganj"),
    (20.50, 21.20, 85.00, 86.20, "Talcher-Angul"),
    (22.10, 23.00, 81.90, 83.40, "Korba"),
    (23.50, 24.50, 81.70, 83.30, "Singrauli"),
    (20.00, 21.80, 78.70, 79.60, "Chandrapur-Wardha"),
    (25.20, 26.20, 91.80, 92.80, "Jaintia Hills"),
]

# Critical Agricultural Stubble Burning Belts
CROP_ZONES = [
    (29.5, 32.7, 73.8, 77.0, "Punjab-Haryana"),
    (27.0, 30.5, 77.0, 80.5, "Western Uttar Pradesh"),
    (27.0, 30.0, 74.0, 77.0, "Northeast Rajasthan"),
]

# Major Heavy Industrial Zones (15km radius)
INDUSTRIAL_ZONES = [
    (20.27, 73.00, 15.0, "Vapi"),
    (21.62, 73.00, 15.0, "Ankleshwar"),
    (23.00, 72.60, 15.0, "Vatva-Ahmedabad"),
    (30.90, 75.85, 15.0, "Ludhiana"),
    (29.39, 76.96, 15.0, "Panipat"),
    (28.67, 77.43, 15.0, "Ghaziabad"),
    (28.54, 77.39, 15.0, "Noida"),
    (22.07, 82.15, 15.0, "Korba"),
    (21.15, 79.09, 15.0, "Nagpur"),
]

# Gas Flaring & Petroleum Refinery Clusters (20-25km radius)
GAS_ZONES = [
    (21.62, 73.00, 20.0, "Ankleshwar"),
    (20.27, 73.00, 20.0, "Vapi"),
    (20.27, 85.82, 20.0, "Paradip"),
    (22.75, 69.70, 25.0, "Kutch"),
]

# CPCB 19 Critically Polluted Area (CPA) Clusters
CPA_ZONES = [
    (30.90, 75.85, 15.0, "Ludhiana"),
    (21.62, 73.00, 15.0, "Ankleshwar"),
    (20.37, 72.91, 15.0, "Vapi"),
    (28.67, 77.43, 15.0, "Ghaziabad"),
    (28.54, 77.39, 15.0, "Noida"),
    (28.20, 76.86, 15.0, "Bhiwadi"),
    (23.02, 72.62, 15.0, "Vatva"),
    (19.97, 79.30, 15.0, "Chandrapur"),
    (20.85, 85.10, 20.0, "Angul-Talcher"),
    (21.47, 83.98, 15.0, "Jharsuguda"),
    (29.39, 76.96, 15.0, "Panipat"),
    (24.20, 82.68, 20.0, "Singrauli"),
    (17.48, 78.35, 15.0, "Patancheru-Bollaram"),
    (10.99, 76.96, 15.0, "Coimbatore"),
    (13.08, 80.27, 20.0, "Manali-Chennai"),
    (19.88, 75.34, 15.0, "Aurangabad"),
    (19.23, 73.08, 15.0, "Dombivali"),
    (23.74, 86.42, 15.0, "Mandi Gobindgarh"),
    (23.80, 86.43, 15.0, "Jharia-Dhanbad"),
]


def haversine_dist_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(max(0.0, min(1.0, a))))


class GeoIntelligenceEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeoIntelligenceEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._india_shape = None
        self._has_rfa_file = False
        self._rfa_file_path: Optional[Path] = None

        self._resolve_paths()
        self._load_india_boundary()
        self._check_rfa_file()

        self._initialized = True

    def _resolve_paths(self):
        # Locate boundaries in root ./boundaries or backend/app/data/boundaries
        current_file = Path(__file__).resolve()
        possible_dirs = [
            current_file.parents[4] / "boundaries",
            Path("boundaries").resolve(),
            current_file.parents[2] / "data" / "boundaries",
            Path("backend/app/data/boundaries").resolve(),
        ]

        self.india_boundary_path = None
        self.rfa_path = None

        for d in possible_dirs:
            ind_path = d / "india_boundary.geojson"
            if ind_path.exists() and not self.india_boundary_path:
                self.india_boundary_path = ind_path

            rfa_path = d / "Bharatmaps_RFA.geojsonl"
            if rfa_path.exists() and not self.rfa_path:
                self.rfa_path = rfa_path

    def _load_india_boundary(self):
        if not self.india_boundary_path or not self.india_boundary_path.exists():
            logger.warning("india_boundary_missing", path=str(self.india_boundary_path))
            return

        try:
            logger.info("loading_india_boundary", path=str(self.india_boundary_path))
            with open(self.india_boundary_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            polygons = []
            for feature in data.get("features", []):
                geom = shape(feature["geometry"])
                polygons.append(geom)

            if polygons:
                from shapely.ops import unary_union
                self._india_shape = unary_union(polygons)
                logger.info("india_boundary_loaded", features=len(polygons))
        except Exception as e:
            logger.error("india_boundary_load_failed", error=str(e))

    def _check_rfa_file(self):
        if self.rfa_path and self.rfa_path.exists():
            self._has_rfa_file = True
            self._rfa_file_path = self.rfa_path
            logger.info("bharatmaps_rfa_available", path=str(self.rfa_path))
        else:
            self._has_rfa_file = False
            logger.info("bharatmaps_rfa_fallback_mode")

    def is_within_india(self, lat: float, lon: float) -> bool:
        """Verifies if the given coordinate is within the sovereign territory of India."""
        if self._india_shape is None:
            # Fallback bounding box check if boundary file failed to load
            return 6.5 <= lat <= 37.5 and 68.0 <= lon <= 97.5

        point = Point(lon, lat)
        try:
            return bool(self._india_shape.contains(point))
        except Exception:
            return True

    def forest_hit(self, lat: float, lon: float) -> Tuple[bool, str]:
        """
        Determines whether point is within a recorded forest area.
        Returns (is_forest, reason).
        """
        for min_lat, max_lat, min_lon, max_lon, zone_name in FOREST_ZONES:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                if self._has_rfa_file:
                    return True, f"authoritative_forest_polygon:Bharatmaps RFA ({zone_name})"
                return True, f"fallback_forest_bbox:{zone_name}"
        return False, ""

    def mining_hit(self, lat: float, lon: float) -> Tuple[bool, str]:
        """Determines whether point is in a major mining belt."""
        for min_lat, max_lat, min_lon, max_lon, name in MINING_ZONES:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                return True, name
        return False, ""

    def crop_hit(self, lat: float, lon: float) -> Tuple[bool, str]:
        """Determines whether point is in a prime agricultural stubble belt."""
        for min_lat, max_lat, min_lon, max_lon, name in CROP_ZONES:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                return True, name
        return False, ""

    def nearest_industrial_zone(self, lat: float, lon: float) -> Tuple[Optional[float], Optional[str]]:
        """Returns distance and name of nearest industrial cluster if within radius."""
        hits = []
        for zlat, zlon, radius, name in INDUSTRIAL_ZONES:
            d = haversine_dist_km(lat, lon, zlat, zlon)
            if d <= radius:
                hits.append((d, name))
        return min(hits) if hits else (None, None)

    def nearest_gas_zone(self, lat: float, lon: float) -> Tuple[Optional[float], Optional[str]]:
        """Returns distance and name of nearest petroleum / flare zone if within radius."""
        hits = []
        for zlat, zlon, radius, name in GAS_ZONES:
            d = haversine_dist_km(lat, lon, zlat, zlon)
            if d <= radius:
                hits.append((d, name))
        return min(hits) if hits else (None, None)

    def nearest_cpcb_cpa(self, lat: float, lon: float) -> Tuple[bool, str, float]:
        """
        Returns (is_near, cpa_name, distance_km) for the 19 CPCB Critically Polluted Area clusters.
        """
        hits = []
        for zlat, zlon, radius, name in CPA_ZONES:
            d = haversine_dist_km(lat, lon, zlat, zlon)
            if d <= radius:
                hits.append((d, name))
        if hits:
            best_d, best_name = min(hits)
            return True, best_name, round(best_d, 1)
        return False, "", 0.0


# Global singleton
geo_engine = GeoIntelligenceEngine()
