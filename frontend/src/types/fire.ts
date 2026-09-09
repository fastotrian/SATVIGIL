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
  land_use: string | null;
  near_cpcb_cluster: boolean;
  recurrence_count: number;
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
