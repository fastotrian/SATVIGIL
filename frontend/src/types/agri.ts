export interface NdviZone {
  id: string;
  name: string;
  lat: number;
  lon: number;
  ndvi: number;
  status: 'healthy' | 'moderate' | 'stressed' | 'critical';
  area_ha: number;
}

export interface NdviResponse {
  region: string;
  date: string;
  zones: NdviZone[];
  trend_weekly: number[];
  summary: { healthy: number; moderate: number; stressed: number; critical: number; total_area_ha: number };
}

export interface AgriField {
  id: string;
  coordinates: number[][];
  area_ha: number;
  crop: string;
  ndvi: number;
  health: 'healthy' | 'moderate' | 'stressed';
}

export interface FieldsResponse {
  center: { lat: number; lon: number };
  total_fields: number;
  avg_area_ha: number;
  fragmented_pct: number;
  fields: AgriField[];
}

export interface CropBreakdown {
  crop: string;
  affected_ha: number;
  loss_pct: number;
}

export interface DamageResponse {
  event: string;
  district: string;
  date_before: string;
  date_after: string;
  affected_area_ha: number;
  total_area_ha: number;
  affected_pct: number;
  estimated_loss_crore: number;
  crop_breakdown: CropBreakdown[];
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}
