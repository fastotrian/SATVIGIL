/**
 * SATVIGIL — Maritime MapView Component
 * High-performance WebGL maritime monitoring display for Indian territorial waters and EEZ.
 * Renders vessel vectors, risk-colored circle layers, radar pulses, MPA zones, and oil spill polygons.
 */
import React, { useEffect, useState, useRef, useMemo } from 'react';
import Map, { Source, Layer, Popup, Marker, NavigationControl, MapRef } from 'react-map-gl';
import type { CircleLayer, FillLayer, LineLayer, HeatmapLayer } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

import { RISK_COLORS } from '../../constants/riskColors';
import { useAlertStore } from '../../store/alertStore';
import type { Vessel, SpillEvent } from '../../types/maritime';
import { StaticPinsLayer } from './StaticPins';

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

// Spatial boundaries for Indian maritime search region
const INDIA_BOUNDS: [[number, number], [number, number]] = [
  [60.0, 4.0],  // Southwest coordinates (Arabian Sea / Lakshadweep)
  [102.0, 38.0], // Northeast coordinates (Bay of Bengal / Andaman & Nicobar)
];

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

  // Fetch vessels & spills periodically
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
        interactiveLayerIds={activeFilters.showVessels ? ['vessel-dots'] : []}
        onClick={(e) => {
          const feature = e.features && e.features[0];
          if (feature && feature.properties) {
            selectVessel(feature.properties as Vessel);
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

        {/* Layer: Strategic Fixed Maritime Pins (Bombay High, Ports, MPAs) */}
        <StaticPinsLayer />

        {/* Animated Radar Pulse Rings for Critical Vessels (Hardware-accelerated CSS on DOM) */}
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

        {/* Layer 4: Vessel Vectors & Radar Pulse */}
        {activeFilters.showVessels && (
          <Source id="vessels" type="geojson" data={vesselsGeoJSON}>
            <Layer {...vesselPulseLayer} />
            <Layer {...vesselDotsLayer} />
          </Source>
        )}

        {/* Selected Vessel Interactive Popup */}
        {selectedVessel && (
          <Popup
            longitude={selectedVessel.lon}
            latitude={selectedVessel.lat}
            anchor="bottom"
            onClose={() => selectVessel(null)}
            closeOnClick={false}
            className="satvigil-popup"
          >
            <div className="p-3 bg-gray-900 text-white rounded-lg shadow-xl border border-gray-700 min-w-[240px] text-xs">
              <div className="flex items-center justify-between border-b border-gray-800 pb-2 mb-2">
                <div className="font-bold text-sm text-gray-100">{selectedVessel.vessel_name}</div>
                <span
                  className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wide"
                  style={{
                    backgroundColor:
                      selectedVessel.risk_level === 'CRITICAL'
                        ? 'rgba(239, 68, 68, 0.25)'
                        : selectedVessel.risk_level === 'WARNING'
                        ? 'rgba(249, 115, 22, 0.25)'
                        : 'rgba(34, 197, 94, 0.25)',
                    color:
                      selectedVessel.risk_level === 'CRITICAL'
                        ? RISK_COLORS.CRITICAL
                        : selectedVessel.risk_level === 'WARNING'
                        ? RISK_COLORS.HIGH
                        : RISK_COLORS.NORMAL,
                    border: `1px solid ${
                      selectedVessel.risk_level === 'CRITICAL'
                        ? RISK_COLORS.CRITICAL
                        : selectedVessel.risk_level === 'WARNING'
                        ? RISK_COLORS.HIGH
                        : RISK_COLORS.NORMAL
                    }`,
                  }}
                >
                  {selectedVessel.risk_level}
                </span>
              </div>

              <div className="space-y-1.5 text-gray-300">
                <div className="flex justify-between">
                  <span className="text-gray-400">MMSI:</span>
                  <span className="font-mono text-gray-200">{selectedVessel.mmsi}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Type:</span>
                  <span>{selectedVessel.vessel_type_label}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Speed:</span>
                  <span>{selectedVessel.speed_knots} kts</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Risk Score:</span>
                  <span className="font-bold">{selectedVessel.risk_score}</span>
                </div>
                {selectedVessel.is_dark && (
                  <div className="flex justify-between text-red-400 font-semibold bg-red-950/50 p-1 rounded">
                    <span>⚠️ Dark Vessel:</span>
                    <span>Gap: {selectedVessel.ais_gap_minutes}m</span>
                  </div>
                )}
                {selectedVessel.in_mpa && (
                  <div className="flex justify-between text-purple-400 font-semibold bg-purple-950/50 p-1 rounded">
                    <span>Protected Area:</span>
                    <span>{selectedVessel.mpa_name}</span>
                  </div>
                )}
              </div>

              <button
                type="button"
                className="w-full mt-3 bg-blue-600 hover:bg-blue-500 text-white font-medium py-1 px-2 rounded transition-colors"
                onClick={() => alert(`Tracking vessel ${selectedVessel.mmsi} telemetry.`)}
              >
                Correlate Spill Tracks
              </button>
            </div>
          </Popup>
        )}

        {/* Active Oil Spill Interactive Attribution Popup */}
        {activeSpill && showSpillPopup && activeFilters.showSpillZones && (
          <Popup
            longitude={activeSpill.lon}
            latitude={activeSpill.lat}
            anchor="top"
            onClose={() => setShowSpillPopup(false)}
            closeOnClick={false}
            className="satvigil-popup"
          >
            <div className="p-3 bg-gray-950 text-white rounded-lg shadow-2xl border border-red-700 min-w-[260px] text-xs">
              <div className="flex items-center justify-between border-b border-red-900/60 pb-2 mb-2">
                <span className="font-bold text-sm text-red-400 flex items-center space-x-1.5">
                  <span>🛢️</span>
                  <span>OIL SPILL DETECTED</span>
                </span>
                <span className="text-[10px] bg-red-900 text-red-200 px-1.5 py-0.5 rounded font-mono font-bold">
                  {activeSpill.id}
                </span>
              </div>
              <div className="space-y-1.5 text-gray-300">
                <div className="flex justify-between">
                  <span className="text-gray-400">Area:</span>
                  <span className="font-bold text-white">{activeSpill.area_km2} km²</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Confidence:</span>
                  <span className="font-bold text-emerald-400">{Math.round(activeSpill.confidence * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Sentinel Scene:</span>
                  <span className="font-mono text-[10px] text-gray-400 truncate max-w-[130px]" title={activeSpill.sentinel_scene_id}>
                    {activeSpill.sentinel_scene_id}
                  </span>
                </div>
                {activeSpill.top_candidates && activeSpill.top_candidates[0] && (
                  <div className="mt-2 pt-2 border-t border-gray-800 bg-red-950/40 p-2 rounded">
                    <span className="text-gray-400 block text-[10px] uppercase font-semibold">Top Suspect (4-Signal SVR):</span>
                    <div className="flex justify-between font-bold text-red-300 mt-0.5">
                      <span>{activeSpill.top_candidates[0].vessel_name}</span>
                      <span>Score: {activeSpill.top_candidates[0].risk_score}</span>
                    </div>
                    <div className="text-[10px] text-gray-400 flex justify-between mt-0.5">
                      <span>Dist: {activeSpill.top_candidates[0].distance_km} km</span>
                      <span>Align: {Math.round(activeSpill.top_candidates[0].heading_score * 100)}%</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        const suspect = vessels.find((v) => v.mmsi === activeSpill.top_candidates[0].mmsi);
                        if (suspect) selectVessel(suspect);
                      }}
                      className="mt-2 w-full bg-red-600 hover:bg-red-500 text-white font-bold py-1 px-2 rounded text-[11px] transition-colors"
                    >
                      Inspect Suspect Vessel →
                    </button>
                  </div>
                )}
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* Layer Toggle Control Overlay */}
      <div className="absolute top-4 right-4 z-10 bg-gray-900/90 backdrop-blur border border-gray-800 rounded-lg p-2.5 shadow-2xl flex flex-col space-y-1.5">
        <span className="text-[11px] font-semibold tracking-wider text-gray-400 uppercase px-1 pb-1 border-b border-gray-800">
          Layer Control
        </span>

        <button
          type="button"
          onClick={() => toggleFilter('showVessels')}
          className={`flex items-center justify-between space-x-3 px-2.5 py-1.5 rounded text-xs transition-colors ${
            activeFilters.showVessels
              ? 'bg-blue-600/30 text-blue-300 border border-blue-500/40'
              : 'bg-gray-800/40 text-gray-400 border border-transparent hover:bg-gray-800'
          }`}
        >
          <span className="flex items-center space-x-1.5">
            <span>🛥️</span>
            <span>AIS Vessels</span>
          </span>
          <span className="text-[10px] font-bold">{activeFilters.showVessels ? 'ON' : 'OFF'}</span>
        </button>

        <button
          type="button"
          onClick={() => toggleFilter('showSpillZones')}
          className={`flex items-center justify-between space-x-3 px-2.5 py-1.5 rounded text-xs transition-colors ${
            activeFilters.showSpillZones
              ? 'bg-red-600/30 text-red-300 border border-red-500/40'
              : 'bg-gray-800/40 text-gray-400 border border-transparent hover:bg-gray-800'
          }`}
        >
          <span className="flex items-center space-x-1.5">
            <span>🌊</span>
            <span>Spill Zones</span>
          </span>
          <span className="text-[10px] font-bold">{activeFilters.showSpillZones ? 'ON' : 'OFF'}</span>
        </button>

        <button
          type="button"
          onClick={() => toggleFilter('showMPABoundaries')}
          className={`flex items-center justify-between space-x-3 px-2.5 py-1.5 rounded text-xs transition-colors ${
            activeFilters.showMPABoundaries
              ? 'bg-purple-600/30 text-purple-300 border border-purple-500/40'
              : 'bg-gray-800/40 text-gray-400 border border-transparent hover:bg-gray-800'
          }`}
        >
          <span className="flex items-center space-x-1.5">
            <span>🏊</span>
            <span>MPA Zones</span>
          </span>
          <span className="text-[10px] font-bold">{activeFilters.showMPABoundaries ? 'ON' : 'OFF'}</span>
        </button>

        <button
          type="button"
          onClick={() => toggleFilter('showDensityHeatmap')}
          className={`flex items-center justify-between space-x-3 px-2.5 py-1.5 rounded text-xs transition-colors ${
            activeFilters.showDensityHeatmap
              ? 'bg-amber-600/30 text-amber-300 border border-amber-500/40'
              : 'bg-gray-800/40 text-gray-400 border border-transparent hover:bg-gray-800'
          }`}
        >
          <span className="flex items-center space-x-1.5">
            <span>🌡️</span>
            <span>Density Heatmap</span>
          </span>
          <span className="text-[10px] font-bold">{activeFilters.showDensityHeatmap ? 'ON' : 'OFF'}</span>
        </button>

        {/* Hackathon Live Demo Button */}
        <button
          type="button"
          disabled={isSimulating}
          onClick={handleSimulateSpillDemo}
          className="w-full mt-2 bg-gradient-to-r from-red-700 to-rose-700 hover:from-red-600 hover:to-rose-600 active:scale-95 text-white font-bold px-2.5 py-2 rounded text-xs shadow-lg transition-all flex items-center justify-center space-x-1.5 border border-red-500/50"
        >
          <span>🛢️</span>
          <span>{isSimulating ? 'Correlating...' : 'Simulate Spill (Demo)'}</span>
        </button>
      </div>
    </div>
  );
}
