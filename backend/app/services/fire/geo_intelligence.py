"""
SATVIGIL — Fire Module: Geo-Intelligence Engine
Loads and caches static GeoJSON boundary files to provide spatial context.
"""
import os
import structlog
from shapely.geometry import shape, Point
import json

logger = structlog.get_logger()

class GeoIntelligenceEngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeoIntelligenceEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        self._india_shape = None
        self._forest_shape = None
        self._mining_shape = None
        
        # Determine paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.boundaries_dir = os.path.join(base_dir, "data", "boundaries")
        
        self.india_boundary_path = os.path.join(self.boundaries_dir, "india_boundary.geojson")
        self.forest_boundary_path = os.path.join(self.boundaries_dir, "india_forest.geojson")
        self.mining_boundary_path = os.path.join(self.boundaries_dir, "legal_mining_leases.geojson")
        
        self._load_india_boundary()
        self._load_forest_boundary()
        self._load_mining_boundary()
        
        self._initialized = True

    def _load_india_boundary(self):
        if not os.path.exists(self.india_boundary_path):
            logger.warning("india_boundary_missing", path=self.india_boundary_path)
            return
            
        try:
            logger.info("loading_india_boundary")
            with open(self.india_boundary_path, 'r', encoding='utf-8') as f:
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

    def _load_forest_boundary(self):
        if not os.path.exists(self.forest_boundary_path):
            return
            
        try:
            logger.info("loading_forest_boundary")
            with open(self.forest_boundary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            polygons = []
            for feature in data.get("features", []):
                geom = shape(feature["geometry"])
                polygons.append(geom)
                
            if polygons:
                from shapely.ops import unary_union
                self._forest_shape = unary_union(polygons)
                logger.info("forest_boundary_loaded", features=len(polygons))
        except Exception as e:
            logger.error("forest_boundary_load_failed", error=str(e))

    def _load_mining_boundary(self):
        if not os.path.exists(self.mining_boundary_path):
            return
            
        try:
            logger.info("loading_mining_boundary")
            with open(self.mining_boundary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            polygons = []
            for feature in data.get("features", []):
                geom = shape(feature["geometry"])
                polygons.append(geom)
                
            if polygons:
                from shapely.ops import unary_union
                self._mining_shape = unary_union(polygons)
                logger.info("mining_boundary_loaded", features=len(polygons))
        except Exception as e:
            logger.error("mining_boundary_load_failed", error=str(e))

    def is_within_india(self, lat: float, lon: float) -> bool:
        if self._india_shape is None:
            return True # Fallback if missing
        
        point = Point(lon, lat)
        return self._india_shape.contains(point)

    def forest_hit(self, lat: float, lon: float) -> bool:
        if self._forest_shape is None:
            return False
            
        point = Point(lon, lat)
        return self._forest_shape.contains(point)

    def mining_hit(self, lat: float, lon: float) -> bool:
        if self._mining_shape is None:
            return False
            
        point = Point(lon, lat)
        return self._mining_shape.contains(point)

# Global singleton
geo_engine = GeoIntelligenceEngine()
