export interface ThermalHotspot {
  id: number;
  latitude: number;
  longitude: number;
  frp: number | null;
  brightness: number | null;
  confidence: string | null;
  satellite: string | null;
  acquired_at: string;
  fire_type: 'industrial' | 'gas_flare' | 'wildfire' | 'stubble' | 'mining' | 'unknown' | null;
  classification_score?: number | null;
  classification_reason?: string | null;
  land_use: string | null;
  near_cpcb_cluster: boolean;
  cpcb_cpa_name?: string | null;
  recurrence_count: number;
  recurrence_cluster_id?: number | null;
  created_at: string;
  responding_agency: string | null;
  recommended_action: string | null;
}

export interface HotspotListResponse {
  hotspots: ThermalHotspot[];
  total: number;
  limit: number;
  offset: number;
}

export interface CPCBRecurringHotspot {
  cpcb_cpa_name: string;
  recurrence_cluster_id: number;
  detection_count: number;
  center_lat: number;
  center_lon: number;
  dominant_fire_type: string;
  first_seen?: string | null;
  last_seen?: string | null;
  avg_frp: number;
  max_frp: number;
  avg_confidence: number;
}

export interface FireStats {
  total_hotspots: number;
  by_fire_type: Record<string, number>;
  recurring_clusters: number;
  cpcb_cpa_associated: number;
  sensor: string;
  data_source: string;
}
