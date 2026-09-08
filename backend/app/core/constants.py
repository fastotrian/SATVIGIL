"""
SATVIGIL — Core Constants
Single source of truth for risk thresholds and zone definitions.
Must match frontend/src/constants/riskColors.ts values.
"""

# ── Vessel Risk Score Thresholds ──────────────────────────────────────────────
RISK_THRESHOLD_CRITICAL = 0.75   # Red blinking — AIS disabled / confirmed spill
RISK_THRESHOLD_HIGH     = 0.55   # Orange pulse — security check failed
RISK_THRESHOLD_CAUTION  = 0.35   # Amber static — watch only
RISK_THRESHOLD_NORMAL   = 0.0    # Green static — all clear

# Alert level labels (matches frontend TypeScript union type)
RISK_LABEL_CRITICAL = "CRITICAL"
RISK_LABEL_HIGH     = "WARNING"
RISK_LABEL_CAUTION  = "WATCH"
RISK_LABEL_NORMAL   = "NORMAL"

def get_risk_label(score: float) -> str:
    """Maps a 0.0–1.0 risk score to a human-readable alert level."""
    if score >= RISK_THRESHOLD_CRITICAL:
        return RISK_LABEL_CRITICAL
    if score >= RISK_THRESHOLD_HIGH:
        return RISK_LABEL_HIGH
    if score >= RISK_THRESHOLD_CAUTION:
        return RISK_LABEL_CAUTION
    return RISK_LABEL_NORMAL

# ── AIS Dark Vessel Detection ─────────────────────────────────────────────────
AIS_GAP_CRITICAL_MINUTES = 30   # Gap > 30 min = dark vessel (CRITICAL flag)
AIS_GAP_WARNING_MINUTES  = 10   # Gap 10–30 min = suspicious (WARNING flag)

# ── Spill Attribution ─────────────────────────────────────────────────────────
SPILL_ATTRIBUTION_RADIUS_KM = 30   # Only consider vessels within 30km of spill

# ── India Maritime Bounding Box ───────────────────────────────────────────────
INDIA_BBOX = {
    "lat_min": 6.0,
    "lat_max": 24.0,
    "lon_min": 67.0,
    "lon_max": 98.0,
}

# ── Map Display Bounds (matches Mapbox fitBounds in frontend) ─────────────────
MAPBOX_INDIA_BOUNDS = [[68.1, 7.9], [97.4, 35.5]]
