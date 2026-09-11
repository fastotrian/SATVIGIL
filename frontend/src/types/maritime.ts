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
  sar_image_url?: string;     // Annotated SAR satellite image URL
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

/** Single AIS position observation from GFW track data */
export interface TrackPoint {
  lat: number;
  lon: number;
  date: string;                // ISO 8601 datetime
  presence_hours: number;
  ais_gap_minutes: number;     // >30 = vessel was dark at this timestamp
}

export interface SatelliteSarEvidence {
  satellite: string;
  band: string;
  acquisition_mode: string;
  polarization: string;
  orbit_pass: string;
  scene_id?: string;
  slick_area_km2: number;
  slick_length_km: number;
  slick_width_max_km: number;
  est_volume_litres: number;
  backscatter_clean_db: number;
  backscatter_slick_db: number;
  backscatter_delta_db: number;
  sar_image_url: string;
}

export interface CulpritVesselProfile {
  name: string;
  imo: string;
  mmsi: string;
  call_sign: string;
  flag_state: string;
  flag_code: string;
  vessel_type: string;
  gross_tonnage: number;
  deadweight_tonnage: number;
  build_year: number;
  owner_operator: string;
  last_port_of_call: string;
  destination: string;
  pre_incident_speed_kts: number;
  incident_speed_kts: number;
  course_deg: number;
  ais_gap_duration_minutes: number;
}

export interface AttributionMLBreakdown {
  composite_confidence: number;
  spatial_proximity_score: number;
  ais_dark_gap_score: number;
  vessel_type_risk_score: number;
  svr_kinematics_anomaly_score: number;
  p_value: string;
}

export interface StatutoryViolation {
  statute: string;
  regulation: string;
  description: string;
}

export interface PenalSanctions {
  detention_order: string;
  statutory_fine_inr: string;
  statutory_fine_usd: string;
  cleanup_liability: string;
  criminal_proceedings: string;
}

export interface ContainmentDirective {
  dispersant_recommended: string;
  dispersant_litres: number;
  boom_perimeter_meters: number;
  response_vessel: string;
  intercept_station: string;
  intercept_course_deg: number;
  intercept_speed_kts: number;
  intercept_eta_hours: string;
}

export interface ForensicDossier {
  dossier_id: string;
  classification: string;
  issuing_authority: string;
  incident_id: string;
  compiled_at: string;
  evidence_sha256_hash?: string;
  location: {
    lat: number;
    lon: number;
    zone: string;
    eez_status: string;
  };
  satellite_sar: SatelliteSarEvidence;
  culprit_vessel: CulpritVesselProfile;
  attribution_ml: AttributionMLBreakdown;
  statutory_violations: StatutoryViolation[];
  penal_sanctions: PenalSanctions;
  containment_directive: ContainmentDirective;
}

/** Single AIS position observation from GFW track data */
export interface TrackPoint {
  lat: number;
  lon: number;
  date: string;                // ISO 8601 datetime
  presence_hours: number;
  ais_gap_minutes: number;     // >30 = vessel was dark at this timestamp
}

/** Full vessel AIS track response from /api/v1/maritime/vessels/{id}/track */
export interface VesselTrack {
  vessel_id: string;
  mmsi: string;
  ship_name: string;
  flag: string;
  total_observations: number;
  dark_gap_event: {
    start: string;
    duration_minutes: number;
    lat: number;
    lon: number;
    reappear_lat: number;
    reappear_lon: number;
  } | null;
  geojson: object;             // Full GeoJSON FeatureCollection
  track_points: TrackPoint[];  // Flat array for animation playback
}

export interface AssetImpactWarning {
  asset_name: string;
  asset_type: 'ONGC_PLATFORM' | 'MPA_SANCTUARY' | 'PORT' | 'COASTLINE';
  distance_nm: number;
  time_to_impact_hours: number | null;
  threat_level: 'HIGH' | 'MEDIUM' | 'WATCH';
  coordinates: [number, number]; // [lon, lat]
}

export interface DriftStepForecast {
  time_offset_hours: number;
  forecast_time: string;
  centroid_lat: number;
  centroid_lon: number;
  area_km2: number;
  drift_speed_knots: number;
  drift_heading_deg: number;
  wind_speed_knots: number;
  wind_heading_deg: number;
  current_speed_knots: number;
  current_heading_deg: number;
  geojson_polygon: object;
  active_warnings: AssetImpactWarning[];
  containment_recommendation: string;
}

export interface SpillDriftForecast {
  spill_id: string;
  base_time: string;
  initial_area_km2: number;
  drift_model: string;
  trajectory_points: Array<{
    hours: number;
    lat: number;
    lon: number;
    area_km2: number;
  }>;
  steps: DriftStepForecast[];
}



