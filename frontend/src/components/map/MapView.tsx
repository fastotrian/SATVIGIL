/**
 * SATVIGIL — Maritime MapView Component
 * High-performance WebGL maritime monitoring display for Indian territorial waters and EEZ.
 * Renders vessel vectors, risk-colored circle layers, radar pulses, MPA zones, and oil spill polygons.
 */
import React, { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import Map, { Source, Layer, Popup, Marker, NavigationControl, MapRef } from 'react-map-gl';
import type { CircleLayer, FillLayer, LineLayer, HeatmapLayer } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

import { RISK_COLORS } from '../../constants/riskColors';
import { useAlertStore } from '../../store/alertStore';
import type { Vessel, SpillEvent, VesselTrack } from '../../types/maritime';
import type { ThermalHotspot } from '../../types/fire';
import { StaticPinsLayer } from './StaticPins';
import { VesselTrackPlayer, TrackPlaybackControls, DEMO_TRACK_VESSEL_ID } from './VesselTrackPlayer';
import { SpillSARPopup } from './SpillSARPopup';

// High-performance clean dark maritime GIS style (Esri Dark Gray Canvas)
// 100% free, crisp bathymetry & coastlines, zero watermarks, zero API key required
const ESRI_DARK_STYLE: any = {
  version: 8,
  sources: {
    'esri-dark-base': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    },
    'esri-dark-reference': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
    },
  },
  layers: [
    {
      id: 'background-layer',
      type: 'background',
      paint: {
        'background-color': '#0B1120',
      },
    },
    {
      id: 'esri-dark-base-tiles',
      type: 'raster',
      source: 'esri-dark-base',
      minzoom: 0,
      maxzoom: 22,
    },
    {
      id: 'esri-dark-reference-tiles',
      type: 'raster',
      source: 'esri-dark-reference',
      minzoom: 0,
      maxzoom: 22,
    },
  ],
};

const rawToken = import.meta.env.VITE_MAPBOX_TOKEN;
const hasValidMapboxToken = Boolean(
  rawToken &&
  typeof rawToken === 'string' &&
  rawToken.startsWith('pk.') &&
  !rawToken.includes('placeholder') &&
  rawToken.length > 50
);

const MAPBOX_TOKEN = hasValidMapboxToken
  ? rawToken
  : 'pk.eyJ1Ijoic2F0dmlnaWwiLCJhIjoiY2x5eXk5eXhxMG1zZDJqcXZhbm11cGNtMSJ9.placeholder';

const MAP_STYLE = hasValidMapboxToken ? 'mapbox://styles/mapbox/dark-v11' : ESRI_DARK_STYLE;

// Statically defined Marine Protected Areas (MPAs) along Indian coastline
const INDIA_MPAS_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Gulf of Kutch Marine National Park', state: 'Gujarat' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [[68.5, 22.0], [70.5, 22.0], [70.5, 23.5], [68.5, 23.5], [68.5, 22.0]],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Gulf of Mannar Marine Biosphere', state: 'Tamil Nadu' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [[78.0, 8.5], [79.5, 8.5], [79.5, 9.5], [78.0, 9.5], [78.0, 8.5]],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Sundarbans Marine Eco-Buffer', state: 'West Bengal' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [[88.5, 21.5], [89.5, 21.5], [89.5, 22.5], [88.5, 22.5], [88.5, 21.5]],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Malvan Marine Sanctuary', state: 'Maharashtra' },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [[73.3, 15.9], [73.6, 15.9], [73.6, 16.4], [73.3, 16.4], [73.3, 15.9]],
        ],
      },
    },
  ],
};

// Route track lines showing historical path and AIS blackout segment for MT GUJARAT PRIDE
const DEMO_TRACKS_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { segment: 'normal', label: 'MT GUJARAT PRIDE ROUTE' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [72.9, 18.8],
          [72.3, 18.9],
          [71.8, 19.0],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { segment: 'dark_gap', label: 'AIS BLACKOUT GAP (45m)' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [71.8, 19.0],
          [71.6, 19.08],
          [71.45, 19.15],
        ],
      },
    },
  ],
};

export function MapView() {
  const mapRef = useRef<MapRef | null>(null);
  const { vessels, setVessels, activeFilters, toggleFilter, selectedVessel, selectVessel, addAlert } = useAlertStore();

  const [spills, setSpills] = useState<SpillEvent[]>([]);
  const [activeSpill, setActiveSpill] = useState<SpillEvent | null>(null);
  const [showSpillPopup, setShowSpillPopup] = useState<boolean>(true);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  // ── SAR Popup state (click on spill polygon) ────────────────────────────
  const [sarPopupSpill, setSarPopupSpill] = useState<SpillEvent | null>(null);
  const [sarPopupScreenPos, setSarPopupScreenPos] = useState({ x: 40, y: 120 });

  // ── Track Playback state ────────────────────────────────────────────────
  const [showTrackPlayer, setShowTrackPlayer] = useState(false);
  const [trackVesselId, setTrackVesselId] = useState<string>(DEMO_TRACK_VESSEL_ID);
  const [vesselTrack, setVesselTrack] = useState<VesselTrack | null>(null);
  const [trackIsPlaying, setTrackIsPlaying] = useState(false);
  const [trackFrame, setTrackFrame] = useState(0);
  const [trackSpeed, setTrackSpeed] = useState(3);

  const handleTrackPlay = useCallback(() => setTrackIsPlaying(true), []);
  const handleTrackPause = useCallback(() => setTrackIsPlaying(false), []);
  const handleTrackReset = useCallback(() => { setTrackIsPlaying(false); setTrackFrame(0); }, []);

  // Trigger oil spill simulation demo
  async function handleSimulateSpillDemo() {
    setIsSimulating(true);
    try {
      const resp = await fetch('http://localhost:8000/api/v1/maritime/simulate-spill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spill_lat: 19.15,
          spill_lon: 71.45,
          spill_trail_bearing: 250.0,
          time_window_hours: 12,
        }),
      });

      if (resp.ok) {
        const data: SpillEvent = await resp.json();
        setActiveSpill(data);
        setShowSpillPopup(true);

        // Smooth camera fly-to Bombay High spill area
        mapRef.current?.flyTo({
          center: [data.lon, data.lat],
          zoom: 8.5,
          duration: 2200,
          essential: true,
        });

        // Push alert to panel
        addAlert({
          id: data.id,
          alert_type: 'OIL_SPILL',
          risk_level: 'CRITICAL',
          title: `Active Oil Slick (${data.area_km2} km²)`,
          description: `Attributed to ${data.top_candidates[0]?.vessel_name} (Risk: ${data.top_candidates[0]?.risk_score}) via Copernicus SAR.`,
          lat: data.lat,
          lon: data.lon,
          created_at: data.detected_at,
          vessel_mmsi: data.top_candidates[0]?.mmsi,
          acknowledged: false,
        });
      }
    } catch (err) {
      console.error('Failed to trigger spill simulation:', err);
    } finally {
      setIsSimulating(false);
    }
  }

  const [hotspots, setHotspots] = useState<ThermalHotspot[]>([]);
  const [hoveredHotspot, setHoveredHotspot] = useState<ThermalHotspot | null>(null);

  // Fetch vessels, spills, hotspots periodically
  useEffect(() => {
    async function loadMaritimeData() {
      try {
        const resp = await fetch('http://localhost:8000/api/v1/maritime/vessels');
        if (resp.ok) {
          const data = await resp.json();
          if (data.vessels) {
            setVessels(data.vessels);
          }
        }
      } catch (err) {
        console.warn('Unable to connect to maritime vessels API:', err);
      }

      try {
        const spillResp = await fetch('http://localhost:8000/api/v1/maritime/spills');
        if (spillResp.ok) {
          const spillData = await spillResp.json();
          setSpills(spillData);
        }
      } catch (err) {
        console.warn('Unable to connect to maritime spills API:', err);
      }

      try {
        const hotResp = await fetch('http://localhost:8000/api/v1/fire/hotspots?limit=200');
        if (hotResp.ok) {
          const hotData = await hotResp.json();
          setHotspots(hotData.hotspots || []);
        }
      } catch (err) {
        console.warn('Unable to connect to fire hotspots API:', err);
      }
    }

    loadMaritimeData();
    const interval = setInterval(loadMaritimeData, 30000);
    return () => clearInterval(interval);
  }, [setVessels]);

  // Convert vessel list to GeoJSON
  const vesselsGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    return {
      type: 'FeatureCollection',
      features: vessels.map((v) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [v.lon, v.lat],
        },
        properties: {
          ...v,
        },
      })),
    };
  }, [vessels]);

  // Convert spills list to GeoJSON
  const spillsGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    return {
      type: 'FeatureCollection',
      features: spills.map((s) => ({
        type: 'Feature',
        geometry: s.geojson_polygon as GeoJSON.Geometry,
        properties: {
          id: s.id,
          detected_at: s.detected_at,
          area_km2: s.area_km2,
          confidence: s.confidence,
          sentinel_scene_id: s.sentinel_scene_id,
        },
      })),
    };
  }, [spills]);

  // Convert hotspots list to GeoJSON
  const hotspotsGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    return {
      type: 'FeatureCollection',
      features: hotspots.map((h) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [h.longitude, h.latitude],
        },
        properties: {
          ...h,
        },
      })),
    };
  }, [hotspots]);

  // Mapbox Circle Layer: Fixed subtle glow halo for CRITICAL threats
  const vesselPulseLayer: CircleLayer = {
    id: 'vessel-pulse',
    type: 'circle',
    source: 'vessels',
    filter: ['==', ['get', 'risk_level'], 'CRITICAL'],
    paint: {
      'circle-radius': 16,
      'circle-color': RISK_COLORS.CRITICAL,
      'circle-opacity': 0.2,
      'circle-stroke-width': 1.5,
      'circle-stroke-color': RISK_COLORS.CRITICAL,
      'circle-stroke-opacity': 0.7,
    },
  };

  // Mapbox Circle Layer: Main colored vessel markers
  const vesselDotsLayer: CircleLayer = {
    id: 'vessel-dots',
    type: 'circle',
    source: 'vessels',
    paint: {
      'circle-radius': [
        'case',
        ['==', ['get', 'vessel_type'], 80], 11,
        ['==', ['get', 'vessel_type'], 82], 11,
        8,
      ],
      'circle-color': [
        'case',
        ['==', ['get', 'risk_level'], 'CRITICAL'], RISK_COLORS.CRITICAL,
        ['==', ['get', 'risk_level'], 'WARNING'], RISK_COLORS.HIGH,
        ['==', ['get', 'risk_level'], 'WATCH'], RISK_COLORS.CAUTION,
        RISK_COLORS.NORMAL,
      ],
      'circle-stroke-width': 2,
      'circle-stroke-color': '#FFFFFF',
      'circle-stroke-opacity': 0.8,
      'circle-opacity': 0.95,
    },
  };

  // Mapbox Heatmap Layer: Vessel density
  const vesselHeatmapLayer: HeatmapLayer = {
    id: 'vessel-heatmap',
    type: 'heatmap',
    source: 'vessels',
    maxzoom: 9,
    paint: {
      'heatmap-weight': [
        'interpolate',
        ['linear'],
        ['get', 'risk_score'],
        0, 0.2,
        1, 1.0,
      ],
      'heatmap-intensity': 1.5,
      'heatmap-color': [
        'interpolate',
        ['linear'],
        ['heatmap-density'],
        0, 'rgba(0, 255, 0, 0)',
        0.2, 'rgba(34, 197, 94, 0.4)',
        0.5, 'rgba(251, 191, 36, 0.6)',
        0.8, 'rgba(249, 115, 22, 0.8)',
        1.0, 'rgba(239, 68, 68, 0.95)',
      ],
      'heatmap-radius': 30,
      'heatmap-opacity': 0.75,
    },
  };

  // Spill Polygon Fill & Outline Layers
  const spillFillLayer: FillLayer = {
    id: 'spills-fill',
    type: 'fill',
    source: 'spills',
    paint: {
      'fill-color': RISK_COLORS.SPILL_ZONE,
      'fill-opacity': 0.45,
    },
  };

  const spillLineLayer: LineLayer = {
    id: 'spills-outline',
    type: 'line',
    source: 'spills',
    paint: {
      'line-color': RISK_COLORS.CRITICAL,
      'line-width': 2.5,
      'line-dasharray': [2, 1],
    },
  };

  // Route Tracks Layers (MT GUJARAT PRIDE Historical Route & Dark Gap)
  const trackNormalLayer: LineLayer = {
    id: 'track-normal',
    type: 'line',
    source: 'vessel-tracks',
    filter: ['==', ['get', 'segment'], 'normal'],
    paint: {
      'line-color': RISK_COLORS.HIGH,
      'line-width': 3,
      'line-opacity': 0.85,
    },
  };

  const trackDarkLayer: LineLayer = {
    id: 'track-dark',
    type: 'line',
    source: 'vessel-tracks',
    filter: ['==', ['get', 'segment'], 'dark_gap'],
    paint: {
      'line-color': RISK_COLORS.CRITICAL,
      'line-width': 2.5,
      'line-dasharray': [2, 2],
    },
  };

  // MPA Fill & Outline Layers
  const mpaFillLayer: FillLayer = {
    id: 'mpa-fill',
    type: 'fill',
    source: 'mpas',
    paint: {
      'fill-color': RISK_COLORS.MPA_BOUNDARY,
      'fill-opacity': 0.2,
    },
  };

  const mpaLineLayer: LineLayer = {
    id: 'mpa-outline',
    type: 'line',
    source: 'mpas',
    paint: {
      'line-color': RISK_COLORS.MPA_BOUNDARY,
      'line-width': 1.5,
    },
  };

  // Hotspots Layer
  const hotspotsLayer: CircleLayer = {
    id: 'hotspots-layer',
    type: 'circle',
    source: 'hotspots',
    paint: {
      'circle-radius': [
        'interpolate', ['linear'], ['get', 'frp'],
        0, 4,
        1000, 14
      ],
      'circle-color': [
        'match', ['get', 'fire_type'],
        'gas_flare', '#8B5CF6',
        'industrial', '#F97316',
        'stubble', '#EAB308',
        'wildfire', '#EF4444',
        'mining', '#6B7280',
        '#A1A1AA' // unknown
      ],
      'circle-opacity': 0.8,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#FFFFFF'
    }
  };

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 78.9,
          latitude: 20.5,
          zoom: 4.8,
        }}
        minZoom={3}
        maxZoom={18}
        doubleClickZoom={true}
        style={{ width: '100%', height: '100%' }}
        mapStyle={MAP_STYLE}
        mapboxAccessToken={MAPBOX_TOKEN}
        interactiveLayerIds={[
          ...(activeFilters.showVessels ? ['vessel-dots'] : []),
          ...(activeFilters.showFireHotspots ? ['hotspots-layer'] : []),
          ...(activeFilters.showSpillZones ? ['spills-fill'] : []),
        ]}
        onMouseEnter={(e) => {
          const feature = e.features && e.features[0];
          if (feature?.layer.id === 'hotspots-layer') {
            setHoveredHotspot(feature.properties as ThermalHotspot);
          }
        }}
        onMouseLeave={() => setHoveredHotspot(null)}
        onClick={(e) => {
          const feature = e.features && e.features[0];
          if (feature?.layer.id === 'vessel-dots') {
            selectVessel(feature.properties as Vessel);
            setSarPopupSpill(null);
          } else if (feature?.layer.id === 'spills-fill') {
            const spillId = feature.properties?.id;
            const clickedSpill = spills.find((s) => s.id === spillId) ?? spills[0] ?? activeSpill;
            if (clickedSpill) {
              setSarPopupSpill(clickedSpill);
              setSarPopupScreenPos({ x: e.point.x, y: e.point.y });
            }
          } else {
            selectVessel(null);
          }
        }}
      >
        <NavigationControl position="bottom-right" />

        {/* Layer 1: Marine Protected Area Boundaries */}
        {activeFilters.showMPABoundaries && (
          <Source id="mpas" type="geojson" data={INDIA_MPAS_GEOJSON}>
            <Layer {...mpaFillLayer} />
            <Layer {...mpaLineLayer} />
          </Source>
        )}

        {/* Layer 2: Oil Spill Polygons */}
        {activeFilters.showSpillZones && (
          <>
            <Source id="spills" type="geojson" data={spillsGeoJSON}>
              <Layer {...spillFillLayer} />
              <Layer {...spillLineLayer} />
            </Source>

            {/* Active Simulated Spill Layer */}
            {activeSpill && (
              <Source
                id="active-simulated-spill"
                type="geojson"
                data={{
                  type: 'Feature',
                  geometry: activeSpill.geojson_polygon as GeoJSON.Geometry,
                  properties: {},
                }}
              >
                <Layer
                  id="active-spill-fill"
                  type="fill"
                  paint={{
                    'fill-color': RISK_COLORS.SPILL_ZONE,
                    'fill-opacity': 0.45,
                  }}
                />
                <Layer
                  id="active-spill-outline"
                  type="line"
                  paint={{
                    'line-color': RISK_COLORS.CRITICAL,
                    'line-width': 3,
                    'line-dasharray': [2, 1],
                  }}
                />
              </Source>
            )}
          </>
        )}

        {/* Layer 3: Vessel Heatmap */}
        {activeFilters.showDensityHeatmap && (
          <Source id="vessels-heat" type="geojson" data={vesselsGeoJSON}>
            <Layer {...vesselHeatmapLayer} />
          </Source>
        )}

        {/* Layer 4: AIS Real-Time Vessel Traffic Dots & Glow */}
        {activeFilters.showVessels && (
          <Source id="vessels" type="geojson" data={vesselsGeoJSON}>
            <Layer {...vesselPulseLayer} />
            <Layer {...vesselDotsLayer} />
          </Source>
        )}

        {/* Layer: Strategic Fixed Maritime Pins (Bombay High, Ports, MPAs) */}
        <StaticPinsLayer />

        {/* Animated Radar Pulse Rings for Critical Vessels */}
        {activeFilters.showVessels &&
          vessels
            .filter((v) => v.risk_level === 'CRITICAL')
            .map((v) => (
              <Marker
                key={`radar-${v.mmsi}`}
                longitude={v.lon}
                latitude={v.lat}
                anchor="center"
              >
                <div className="relative flex items-center justify-center pointer-events-none -ml-4 -mt-4 w-8 h-8">
                  <div className="absolute w-12 h-12 rounded-full border-2 border-red-500 bg-red-500/20 animate-ping opacity-75" />
                  <div className="w-4 h-4 rounded-full border border-red-400/80" />
                </div>
              </Marker>
            ))}

        {/* Layer: Historical Routes & AIS Blackout Gap Line */}
        {activeFilters.showVessels && (
          <Source id="vessel-tracks" type="geojson" data={DEMO_TRACKS_GEOJSON}>
            <Layer {...trackNormalLayer} />
            <Layer {...trackDarkLayer} />
          </Source>
        )}

        {/* Layer 5: Fire Hotspots */}
        {activeFilters.showFireHotspots && (
          <Source id="hotspots" type="geojson" data={hotspotsGeoJSON}>
            <Layer {...hotspotsLayer} />
          </Source>
        )}

        {/* Layer 6: GFW AIS Vessel Track (animated playback) */}
        {showTrackPlayer && (
          <VesselTrackPlayer
            vesselId={trackVesselId}
            onTrackLoaded={(t) => { setVesselTrack(t); }}
            onFrameChange={(point, idx) => setTrackFrame(idx)}
          />
        )}

        {/* Selected Vessel Interactive Popup — Command Center Design */}
        {selectedVessel && (
          <Popup
            longitude={selectedVessel.lon}
            latitude={selectedVessel.lat}
            anchor="bottom"
            onClose={() => selectVessel(null)}
            closeOnClick={false}
            className="satvigil-popup"
          >
            <div
              className="p-3.5 rounded-lg shadow-2xl text-xs flex flex-col gap-2 min-w-[260px]"
              style={{
                background: 'var(--navy-800)',
                border: '1px solid var(--navy-400)',
                color: 'var(--text-primary)',
              }}
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b pb-1.5" style={{ borderColor: 'var(--navy-500)' }}>
                <div className="flex items-center gap-1.5">
                  <span className="text-base">🛥️</span>
                  <div>
                    <div className="font-bold text-sm tracking-wide text-white">
                      {selectedVessel.vessel_name || 'UNKNOWN VESSEL'}
                    </div>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--text-mono)' }}>
                      MMSI: {selectedVessel.mmsi} · {selectedVessel.vessel_type_label || 'Vessel'}
                    </div>
                  </div>
                </div>
                <span
                  className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                  style={{
                    backgroundColor:
                      selectedVessel.risk_level === 'CRITICAL' ? 'rgba(239, 68, 68, 0.25)' :
                      selectedVessel.risk_level === 'WARNING' ? 'rgba(245, 158, 11, 0.25)' :
                      'rgba(0, 212, 232, 0.2)',
                    color:
                      selectedVessel.risk_level === 'CRITICAL' ? 'var(--red-400)' :
                      selectedVessel.risk_level === 'WARNING' ? 'var(--amber-400)' :
                      'var(--teal-500)',
                    border: `1px solid ${
                      selectedVessel.risk_level === 'CRITICAL' ? 'var(--red-500)' :
                      selectedVessel.risk_level === 'WARNING' ? 'var(--amber-500)' :
                      'var(--teal-500)'
                    }`,
                  }}
                >
                  {selectedVessel.risk_level}
                </span>
              </div>

              {/* Threat / Risk Score Bar */}
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span style={{ color: 'var(--text-secondary)' }}>Threat Index</span>
                  <span className="font-mono font-bold" style={{ color: selectedVessel.risk_score > 0.7 ? 'var(--red-400)' : 'var(--teal-500)' }}>
                    {(selectedVessel.risk_score * 100).toFixed(0)}% ({selectedVessel.risk_score.toFixed(2)})
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--navy-950)' }}>
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(100, Math.max(5, selectedVessel.risk_score * 100))}%`,
                      backgroundColor:
                        selectedVessel.risk_score > 0.7 ? 'var(--red-500)' :
                        selectedVessel.risk_score > 0.4 ? 'var(--amber-500)' :
                        'var(--teal-500)',
                    }}
                  />
                </div>
              </div>

              {/* Data Grid */}
              <div className="grid grid-cols-2 gap-2 text-[11px] bg-black/25 p-2 rounded border" style={{ borderColor: 'var(--navy-500)' }}>
                <div>
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>SPEED (SOG)</span>
                  <span className="font-mono font-semibold">{selectedVessel.speed_knots?.toFixed(1) ?? '—'} kts</span>
                </div>
                <div>
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>COURSE (COG)</span>
                  <span className="font-mono font-semibold">{selectedVessel.course_deg != null ? `${selectedVessel.course_deg.toFixed(0)}°` : '—'}</span>
                </div>
                <div>
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>TYPE</span>
                  <span className="font-semibold text-white capitalize">{selectedVessel.vessel_type_label || 'Vessel'}</span>
                </div>
                <div>
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>COORDINATES</span>
                  <span className="font-mono text-[10px]" style={{ color: 'var(--text-mono)' }}>
                    {selectedVessel.lat.toFixed(3)}°N, {selectedVessel.lon.toFixed(3)}°E
                  </span>
                </div>
              </div>

              {/* Anomaly Badge if Dark / Anomaly */}
              {selectedVessel.is_dark && (
                <div className="p-1.5 rounded bg-red-950/40 border border-red-500/40 text-[10px] text-red-300 flex items-center gap-1">
                  <span>⚠️</span>
                  <span><strong>Dark Vessel Alert:</strong> AIS Gap of {selectedVessel.ais_gap_minutes} mins</span>
                </div>
              )}

              {selectedVessel.in_mpa && (
                <div className="p-1.5 rounded bg-amber-950/40 border border-amber-500/40 text-[10px] text-amber-300 flex items-center gap-1">
                  <span>🛡️</span>
                  <span><strong>MPA Zone:</strong> Inside {selectedVessel.mpa_name || 'Protected Sanctuary'}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-1.5 mt-0.5">
                <button
                  type="button"
                  onClick={() => {
                    setShowTrackPlayer(true);
                    setTrackVesselId(DEMO_TRACK_VESSEL_ID);
                  }}
                  className="flex-1 py-1.5 px-2 rounded text-[10px] font-semibold flex items-center justify-center gap-1 transition-colors"
                  style={{
                    background: 'var(--navy-600)',
                    border: '1px solid var(--teal-500)',
                    color: 'var(--teal-500)',
                  }}
                >
                  📡 GFW Track Replay
                </button>
                <button
                  type="button"
                  onClick={() => {
                    mapRef.current?.flyTo({
                      center: [selectedVessel.lon, selectedVessel.lat],
                      zoom: 11,
                      duration: 1500,
                    });
                  }}
                  className="py-1.5 px-2.5 rounded text-[10px] font-semibold transition-colors"
                  style={{
                    background: 'var(--teal-500)',
                    color: 'var(--navy-950)',
                  }}
                >
                  🎯 Focus
                </button>
              </div>
            </div>
          </Popup>
        )}

        {/* Active Simulated Spill Popup */}
        {activeSpill && showSpillPopup && (
          <Popup
            longitude={activeSpill.lon}
            latitude={activeSpill.lat}
            anchor="top"
            onClose={() => setShowSpillPopup(false)}
            closeOnClick={false}
            className="satvigil-popup"
          >
            <div
              className="p-3.5 rounded-lg shadow-2xl text-xs flex flex-col gap-2 min-w-[270px]"
              style={{
                background: 'var(--navy-800)',
                border: '1px solid var(--red-500)',
                color: 'var(--text-primary)',
              }}
            >
              <div className="flex items-center justify-between border-b pb-1.5" style={{ borderColor: 'var(--navy-500)' }}>
                <div className="flex items-center gap-1.5">
                  <span className="text-base">🛢️</span>
                  <div>
                    <div className="font-bold text-sm tracking-wide text-red-400">OIL SPILL DETECTED</div>
                    <div className="text-[10px] font-mono" style={{ color: 'var(--text-secondary)' }}>
                      ID: {activeSpill.id}
                    </div>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-600/30 text-red-300 border border-red-500 animate-pulse-red">
                  CRITICAL
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] bg-black/25 p-2 rounded border" style={{ borderColor: 'var(--navy-500)' }}>
                <div>
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>SLICK AREA</span>
                  <span className="font-mono font-bold text-white">{activeSpill.area_km2} km²</span>
                </div>
                <div>
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>SAR CONFIDENCE</span>
                  <span className="font-mono font-bold text-amber-400">{Math.round(activeSpill.confidence * 100)}%</span>
                </div>
                <div className="col-span-2">
                  <span className="block text-[10px]" style={{ color: 'var(--text-secondary)' }}>SENSOR / SCENE</span>
                  <span className="font-mono text-[10px] text-gray-300">{activeSpill.sentinel_scene_id}</span>
                </div>
              </div>

              {activeSpill.top_candidates && activeSpill.top_candidates.length > 0 && (
                <div className="p-2 rounded bg-red-950/40 border border-red-500/50">
                  <div className="text-[10px] font-bold text-red-300 uppercase tracking-wider mb-1">
                    🎯 Primary Suspect Attributed
                  </div>
                  <div className="flex justify-between font-bold text-white text-xs">
                    <span>{activeSpill.top_candidates[0].vessel_name}</span>
                    <span className="text-red-400">Risk: {activeSpill.top_candidates[0].risk_score}</span>
                  </div>
                  <div className="text-[10px] flex justify-between mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                    <span>Distance: {activeSpill.top_candidates[0].distance_km} km</span>
                    <span>Heading Align: {Math.round(activeSpill.top_candidates[0].heading_score * 100)}%</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const suspect = vessels.find((v) => v.mmsi === activeSpill.top_candidates[0].mmsi);
                      if (suspect) {
                        selectVessel(suspect);
                      }
                      setSarPopupSpill(activeSpill);
                    }}
                    className="w-full mt-2 py-1 px-2 rounded text-[10px] font-bold uppercase tracking-wider bg-red-600 hover:bg-red-500 text-white transition-colors"
                  >
                    View Forensic SAR Evidence →
                  </button>
                </div>
              )}
            </div>
          </Popup>
        )}

        {/* Hovered Hotspot Interactive Popup */}
        {hoveredHotspot && activeFilters.showFireHotspots && (
          <Popup
            longitude={hoveredHotspot.longitude}
            latitude={hoveredHotspot.latitude}
            anchor="bottom"
            closeButton={false}
            closeOnClick={false}
            className="satvigil-popup"
          >
            <div
              className="p-2.5 rounded shadow-xl min-w-[200px] text-xs flex flex-col gap-1"
              style={{
                background: 'var(--navy-800)',
                border: '1px solid var(--navy-400)',
                color: 'var(--text-primary)',
              }}
            >
              <div className="font-bold text-xs uppercase border-b pb-1 flex justify-between items-center" style={{ borderColor: 'var(--navy-500)' }}>
                <span>🔥 {hoveredHotspot.fire_type}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono">
                  {hoveredHotspot.confidence}
                </span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-secondary)' }}>FRP (MW):</span>
                <span className="font-mono font-bold text-amber-400">{hoveredHotspot.frp?.toFixed(1) || 'N/A'}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span style={{ color: 'var(--text-secondary)' }}>Agency:</span>
                <span className="truncate max-w-[110px]" title={hoveredHotspot.responding_agency || ''}>
                  {hoveredHotspot.responding_agency || 'Unknown'}
                </span>
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* ── Layer Control Panel — Bottom Left, Navy Glass Command Panel ── */}
      <div
        className="absolute bottom-6 left-4 z-10 rounded-lg shadow-2xl flex flex-col gap-2 p-3 backdrop-blur-md"
        style={{
          background: 'rgba(15, 31, 61, 0.92)',
          border: '1px solid var(--navy-500)',
          minWidth: '220px',
        }}
      >
        <div className="flex items-center justify-between border-b pb-1.5" style={{ borderColor: 'var(--navy-500)' }}>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse-teal" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-300">
              Surveillance Layers
            </span>
          </div>
          <span className="text-[9px] font-mono text-cyan-500">LIVE GIS</span>
        </div>

        <div className="flex flex-col gap-1.5 text-xs">
          <label className="flex items-center gap-2 cursor-pointer select-none py-0.5 px-1 rounded hover:bg-white/5 transition-colors">
            <input
              type="checkbox"
              checked={activeFilters.showVessels}
              onChange={() => toggleFilter('showVessels')}
              className="accent-cyan-400 rounded cursor-pointer"
            />
            <span className="flex items-center gap-1.5">
              <span className="text-cyan-300">🛥️</span>
              <span className="text-gray-200 text-[11px]">AIS Vessel Traffic</span>
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none py-0.5 px-1 rounded hover:bg-white/5 transition-colors">
            <input
              type="checkbox"
              checked={activeFilters.showSpillZones}
              onChange={() => toggleFilter('showSpillZones')}
              className="accent-red-500 rounded cursor-pointer"
            />
            <span className="flex items-center gap-1.5">
              <span className="text-red-400">🛢️</span>
              <span className="text-gray-200 text-[11px]">Sentinel-1/2 SAR Spills</span>
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none py-0.5 px-1 rounded hover:bg-white/5 transition-colors">
            <input
              type="checkbox"
              checked={activeFilters.showFireHotspots}
              onChange={() => toggleFilter('showFireHotspots')}
              className="accent-amber-400 rounded cursor-pointer"
            />
            <span className="flex items-center gap-1.5">
              <span className="text-amber-400">🔥</span>
              <span className="text-gray-200 text-[11px]">FIRMS Gas Flares / Fires</span>
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none py-0.5 px-1 rounded hover:bg-white/5 transition-colors">
            <input
              type="checkbox"
              checked={activeFilters.showDensityHeatmap}
              onChange={() => toggleFilter('showDensityHeatmap')}
              className="accent-cyan-400 rounded cursor-pointer"
            />
            <span className="flex items-center gap-1.5">
              <span>🌊</span>
              <span className="text-gray-200 text-[11px]">Traffic Density Heatmap</span>
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer select-none py-0.5 px-1 rounded hover:bg-white/5 transition-colors">
            <input
              type="checkbox"
              checked={activeFilters.showMPABoundaries}
              onChange={() => toggleFilter('showMPABoundaries')}
              className="accent-emerald-400 rounded cursor-pointer"
            />
            <span className="flex items-center gap-1.5">
              <span className="text-emerald-400">🛡️</span>
              <span className="text-gray-200 text-[11px]">Marine Protected Areas</span>
            </span>
          </label>
        </div>

        {/* Action / Simulation Controls */}
        <div className="pt-2 border-t flex flex-col gap-1.5" style={{ borderColor: 'var(--navy-500)' }}>
          <button
            type="button"
            onClick={handleSimulateSpillDemo}
            disabled={isSimulating}
            className="w-full py-1.5 px-2.5 rounded text-[11px] font-bold tracking-wide flex items-center justify-center gap-1.5 transition-all shadow-lg"
            style={{
              background: 'linear-gradient(135deg, rgba(220, 38, 38, 0.9), rgba(185, 28, 28, 0.9))',
              border: '1px solid var(--red-500)',
              color: '#FFFFFF',
            }}
          >
            <span className="text-sm">🚨</span>
            <span>{isSimulating ? 'Simulating Incident...' : 'Simulate Spill Event'}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setShowTrackPlayer((prev) => !prev);
              setTrackVesselId(DEMO_TRACK_VESSEL_ID);
            }}
            className="w-full py-1.5 px-2.5 rounded text-[11px] font-bold tracking-wide flex items-center justify-center gap-1.5 transition-all"
            style={{
              background: showTrackPlayer ? 'rgba(0, 212, 232, 0.2)' : 'var(--navy-700)',
              border: `1px solid ${showTrackPlayer ? 'var(--teal-500)' : 'var(--navy-500)'}`,
              color: showTrackPlayer ? 'var(--teal-500)' : 'var(--text-secondary)',
            }}
          >
            <span>📡</span>
            <span>{showTrackPlayer ? 'Close Track Player' : 'Play GFW AIS Track'}</span>
          </button>
        </div>
      </div>

      {/* ── Playback Controls Panel ── */}
      {showTrackPlayer && (
        <TrackPlaybackControls
          track={vesselTrack}
          isPlaying={trackIsPlaying}
          frameIndex={trackFrame}
          speed={trackSpeed}
          onPlay={handleTrackPlay}
          onPause={handleTrackPause}
          onReset={handleTrackReset}
          onSpeedChange={setTrackSpeed}
          onSeek={setTrackFrame}
        />
      )}

      {/* ── SAR Image Popup (spill polygon click) ── */}
      {sarPopupSpill && (
        <SpillSARPopup
          spill={sarPopupSpill}
          screenX={sarPopupScreenPos.x + 20}
          screenY={sarPopupScreenPos.y - 30}
          onClose={() => setSarPopupSpill(null)}
        />
      )}
    </div>
  );
}
