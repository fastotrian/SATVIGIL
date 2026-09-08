/**
 * SATVIGIL — Maritime Module TypeScript Types
 * These must match the Pydantic response schemas in backend/app/schemas/
 */

export type RiskLevel = 'CRITICAL' | 'WARNING' | 'WATCH' | 'NORMAL';

export interface Vessel {
  mmsi: string;
  vessel_name: string;
  vessel_type: number;       // AIS vessel type code (80–89 = Tanker, 70–79 = Cargo)
  vessel_type_label: string; // Human-readable: "Tanker", "Cargo", "Fishing", etc.
  lat: number;
  lon: number;
  speed_knots: number;
  course_deg: number;
  risk_score: number;        // 0.0 to 1.0
  risk_level: RiskLevel;
  ais_gap_minutes: number;   // 0 = no gap, >30 = dark vessel
  is_dark: boolean;          // true if AIS gap > 30 min
  in_mpa: boolean;           // true if inside Marine Protected Area
  mpa_name: string | null;   // name of the MPA if in_mpa is true
  last_seen: string;         // ISO 8601 datetime string
}

export interface SpillEvent {
  id: string;
  detected_at: string;        // ISO 8601
  lat: number;
  lon: number;
  area_km2: number;           // Estimated spill area in km²
  confidence: number;         // U-Net model confidence 0.0–1.0
  sentinel_scene_id: string;  // Copernicus scene identifier
  top_candidates: SpillCandidate[];  // Ranked vessel candidates
  geojson_polygon: object;    // GeoJSON Polygon for map overlay
}

export interface SpillCandidate {
  mmsi: string;
  vessel_name: string;
  risk_score: number;         // Combined 4-signal score from notebook
  distance_km: number;
  type_risk: number;
  heading_score: number;
  behavioral_anomaly: boolean;
}

export interface Alert {
  id: string;
  alert_type: 'OIL_SPILL' | 'DARK_VESSEL' | 'ILLEGAL_FISHING' | 'FIRE' | 'LANDSLIDE';
  risk_level: RiskLevel;
  title: string;
  description: string;
  lat: number;
  lon: number;
  created_at: string;
  vessel_mmsi?: string;
  acknowledged: boolean;
}
