from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class LandslideAnalyzeRequest(BaseModel):
    coordinates: List[List[float]]  # List of [lon, lat] pairs defining the polygon
    detection_date: str             # e.g. "2024-07-30"
    detection_confidence: float     # e.g. 0.89

class LandslideAnalyzeResponse(BaseModel):
    operation_id: str
    site_id: str
    status: str
    started_at: str
    completed_at: str
    detection: Dict[str, Any]
    monitoring: Dict[str, Any]
    prediction: Dict[str, Any]
    checks: Dict[str, Any]
