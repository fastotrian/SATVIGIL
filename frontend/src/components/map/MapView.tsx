/**
 * SATVIGIL — Interactive Command Center Map View
 * Features:
 *   - High-performance Mapbox WebGL canvas with ESRI Marine Bathymetry base
 *   - Mapbox Native Vessel Clustering (aggregates close targets into count bubbles, expanding on zoom)
 *   - Sleek tactical unclustered vessel dots (risk-based coloring, no large overlapping discs)
 *   - Top-left collapsible GIS Layer & Sensor Dock
 *   - Top-right Mapbox Navigation Controls
 *   - Sentinel-1C SAR hydrocarbon slick polygon & Fay spreading drift corridor
 *   - NASA VIIRS thermal anomaly hotspots (174 live detections)
 *   - Marine Protected Area (MPA) conservation zone overlays
 *   - INCOIS-OOSA 72-hour forward ocean drift trajectory simulator
 */
import React, { useEffect, useRef, useState, useMemo, useCallback, memo } from 'react';

import Map, {
  Source,
  Layer,
  Marker,
  Popup,
  NavigationControl,
  type MapRef,
  type CircleLayer,
  type FillLayer,
  type LineLayer,
  type HeatmapLayer,
  type SymbolLayer,
} from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import maplibregl from 'maplibre-gl';

import { useAlertStore } from '../../store/alertStore';
import { RISK_COLORS } from '../../constants/riskColors';
import type { Vessel, SpillEvent, VesselTrack } from '../../types/maritime';
import type { ThermalHotspot } from '../../types/fire';
import { StaticPinsLayer } from './StaticPins';
import { VesselTrackPlayer, TrackPlaybackControls } from './VesselTrackPlayer';
import { SpillSARPopup } from './SpillSARPopup';
import { SpillDriftController } from './SpillDriftController';

// ── Tactical Dark Marine Map Style (ESRI World Dark Gray Canvas) ─────────────

const MAP_STYLE: any = {
  version: 8,
  glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
  sources: {
    'esri-dark-base': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '&copy; Esri, HERE, Garmin, (c) OpenStreetMap contributors',
    },
    'esri-dark-ref': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
    },
  },
  layers: [
    {
      id: 'esri-dark-base-tiles',
      type: 'raster',
      source: 'esri-dark-base',
      minzoom: 0,
      maxzoom: 18,
    },
    {
      id: 'esri-dark-ref-tiles',
      type: 'raster',
      source: 'esri-dark-ref',
      minzoom: 0,
      maxzoom: 18,
      paint: {
        'raster-opacity': 0.85,
      },
    },
  ],
};

// ── Static GeoJSON Boundaries ─────────────────────────────────────────────
const INDIA_MPAS_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Gulf of Kutch Marine National Park' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[69.10, 22.35], [69.80, 22.35], [69.80, 22.65], [69.10, 22.65], [69.10, 22.35]]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Gulf of Mannar Biosphere Reserve' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[78.50, 8.80], [79.30, 8.80], [79.30, 9.25], [78.50, 9.25], [78.50, 8.80]]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Sundarbans Marine Buffer Zone' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[88.60, 21.60], [89.20, 21.60], [89.20, 22.00], [88.60, 22.00], [88.60, 21.60]]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Malvan Marine Sanctuary' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[73.44, 16.02], [73.53, 16.02], [73.53, 16.12], [73.44, 16.12], [73.44, 16.02]]],
      },
    },
  ],
};

const DEMO_TRACKS_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { vessel_mmsi: '419082341', segment: 'normal' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [71.85, 19.85], [71.72, 19.65], [71.60, 19.45], [71.50, 19.25], [71.45, 19.15],
        ],
      },
    },
    {
      type: 'Feature',
      properties: { vessel_mmsi: '419082341', segment: 'dark_gap' },
      geometry: {
        type: 'LineString',
        coordinates: [
          [71.45, 19.15], [71.38, 19.02], [71.30, 18.88], [71.20, 18.70],
        ],
      },
    },
  ],
};

const VesselMarker = memo(({ vessel, onSelect }: { vessel: Vessel; onSelect: (v: Vessel) => void }) => {
  const isCritical = vessel.risk_level === 'CRITICAL';
  const color =
    vessel.risk_level === 'CRITICAL'
      ? RISK_COLORS.CRITICAL
      : vessel.risk_level === 'WARNING'
      ? RISK_COLORS.HIGH
      : vessel.risk_level === 'WATCH'
      ? RISK_COLORS.CAUTION
      : RISK_COLORS.NORMAL;

  return (
    <Marker
      longitude={vessel.lon}
      latitude={vessel.lat}
      anchor="center"
      onClick={(e) => {
        e.originalEvent.stopPropagation();
        onSelect(vessel);
      }}
    >
      <div className="relative flex items-center justify-center cursor-pointer hover:scale-125 transition-transform" style={{ zIndex: isCritical ? 50 : 10 }}>
        {isCritical && (
          <div className="absolute w-12 h-12 rounded-full border-2 border-red-500 bg-red-500/20 animate-ping pointer-events-none" />
        )}
        <div style={{ transform: `rotate(${vessel.course_deg || 0}deg)` }}>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill={color}
            stroke="#0a0a0a"
            strokeWidth="1.5"
            style={{ filter: 'drop-shadow(0px 1px 3px rgba(0,0,0,0.8))' }}
          >
            <path d="M12 2L22 22L12 17L2 22L12 2Z" />
          </svg>
        </div>
      </div>
    </Marker>
  );
});

export function MapView() {
  const mapRef = useRef<MapRef>(null);

  const {
    vessels,
    setVessels,
    selectedVessel,
    selectVessel,
    activeFilters,
    toggleFilter,
    setExclusiveLayer,
    addAlert,
    isDriftSimActive,
    toggleDriftSim,
    driftForecast,
    getActiveDriftStep,
  } = useAlertStore();

  const [spills, setSpills] = useState<SpillEvent[]>([]);
  const [activeSpill, setActiveSpill] = useState<SpillEvent | null>(null);
  const [showSpillPopup, setShowSpillPopup] = useState(false);
  const [sarPopupSpill, setSarPopupSpill] = useState<SpillEvent | null>(null);
  const [sarPopupScreenPos, setSarPopupScreenPos] = useState({ x: 100, y: 100 });
  const [isSimulating, setIsSimulating] = useState(false);
  const [isLayerDockOpen, setIsLayerDockOpen] = useState(true);
  const [vesselSensor, setVesselSensor] = useState<'sentinel1' | 'sentinel2'>('sentinel1');

  // GFW vessel track playback state
  const [showTrackPlayer, setShowTrackPlayer] = useState(false);
  const [trackVesselId, setTrackVesselId] = useState<string | null>(null);
  const [vesselTrack, setVesselTrack] = useState<VesselTrack | null>(null);
  const [trackFrame, setTrackFrame] = useState(0);
  const [trackIsPlaying, setTrackIsPlaying] = useState(false);
  const [trackSpeed, setTrackSpeed] = useState(3);

  const handleTrackPlay = useCallback(() => setTrackIsPlaying(true), []);
  const handleTrackPause = useCallback(() => setTrackIsPlaying(false), []);
  const handleTrackReset = useCallback(() => { setTrackIsPlaying(false); setTrackFrame(0); }, []);

  // Trigger oil spill sync / ingestion
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
          duration: 2000,
          essential: true,
        });

        // Push alert to panel
        addAlert({
          id: data.id,
          alert_type: 'OIL_SPILL',
          risk_level: 'CRITICAL',
          title: `Active Oil Slick (${data.area_km2} km²)`,
          description: `Attributed to ${data.top_candidates[0]?.vessel_name} (Risk: ${data.top_candidates[0]?.risk_score}) via Copernicus Sentinel-1C SAR.`,
          lat: data.lat,
          lon: data.lon,
          created_at: data.detected_at,
          vessel_mmsi: data.top_candidates[0]?.mmsi,
          acknowledged: false,
        });
      }
    } catch (err) {
      console.error('Failed to trigger spill ingestion:', err);
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
          if (spillData.length > 0 && !activeSpill) {
            setActiveSpill(spillData[0]);
          }
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
    const interval = setInterval(loadMaritimeData, 45000);

    // Trigger map resize on layout changes
    const timer = setTimeout(() => {
      mapRef.current?.resize();
    }, 200);

    const handleWindowResize = () => mapRef.current?.resize();
    window.addEventListener('resize', handleWindowResize);

    return () => {
      clearInterval(interval);
      clearTimeout(timer);
      window.removeEventListener('resize', handleWindowResize);
    };
  }, [setVessels, setSpills]);

  // Transform vessels array into GeoJSON
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

  // Transform spills array into GeoJSON
  const spillsGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    return {
      type: 'FeatureCollection',
      features: spills.map((s) => ({
        type: 'Feature',
        geometry: s.geojson_polygon as GeoJSON.Geometry,
        properties: {
          id: s.id,
          area_km2: s.area_km2,
          confidence: s.confidence,
          sentinel_scene_id: s.sentinel_scene_id,
        },
      })),
    };
  }, [spills]);

  // Transform hotspots array into GeoJSON
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

  // Active drift step polygon for forward prediction overlay
  const activeDriftStep = getActiveDriftStep();

  const driftStepPolygonGeoJSON = useMemo(() => {
    if (!isDriftSimActive || !activeDriftStep?.geojson_polygon) return null;
    return {
      type: 'Feature',
      geometry: activeDriftStep.geojson_polygon as GeoJSON.Geometry,
      properties: {
        hour: activeDriftStep.time_offset_hours,
        area_km2: activeDriftStep.area_km2,
      },
    };
  }, [isDriftSimActive, activeDriftStep]);

  const driftTrajectoryLineGeoJSON = useMemo(() => {
    if (!isDriftSimActive || !driftForecast?.trajectory_points) return null;
    const coords = driftForecast.trajectory_points.map((p) => [p.lon, p.lat]);
    return {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: coords,
      },
      properties: {},
    };
  }, [isDriftSimActive, driftForecast]);

  // ── Mapbox Clustered Vessel Layers ────────────────────────────────────────
  const clusterLayer: CircleLayer = {
    id: 'clusters',
    type: 'circle',
    source: 'vessels',
    filter: ['has', 'point_count'],
    paint: {
      'circle-color': [
        'step',
        ['get', 'point_count'],
        '#0E7490', // cyan/teal for small clusters (< 25)
        25,
        '#0284C7', // bright blue (25-100)
        100,
        '#1E3A8A', // deep navy-blue (> 100)
      ],
      'circle-radius': [
        'step',
        ['get', 'point_count'],
        14,
        25,
        18,
        100,
        24,
      ],
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#38BDF8',
      'circle-opacity': 0.88,
    },
  };

  const clusterCountLayer: SymbolLayer = {
    id: 'cluster-count',
    type: 'symbol',
    source: 'vessels',
    filter: ['has', 'point_count'],
    layout: {
      'text-field': '{point_count_abbreviated}',
      'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
      'text-size': 11,
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': '#FFFFFF',
    },
  };

  // Mapbox Circle Layer: Unclustered individual tactical vessel dots
  const vesselDotsLayer: CircleLayer = {
    id: 'vessel-dots',
    type: 'circle',
    source: 'vessels',
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-radius': [
        'interpolate', ['linear'], ['zoom'],
        4, 4,
        7, 5.5,
        10, 7.5,
        14, 9,
      ],
      'circle-color': [
        'case',
        ['==', ['get', 'is_dark'], true], '#EF4444',
        ['>=', ['get', 'risk_score'], 0.7], '#F59E0B',
        ['==', ['get', 'in_mpa'], true], '#C084FC',
        '#00E5FF', // High-contrast Electric Cyan
      ],
      'circle-stroke-width': 1.5,
      'circle-stroke-color': '#031726',
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
      'heatmap-weight': ['interpolate', ['linear'], ['get', 'risk_score'], 0, 0.2, 1, 1.0],
      'heatmap-intensity': 1.5,
      'heatmap-color': [
        'interpolate', ['linear'], ['heatmap-density'],
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
      'circle-radius': ['interpolate', ['linear'], ['get', 'frp'], 0, 4, 1000, 14],
      'circle-color': [
        'match',
        ['get', 'fire_type'],
        'gas_flare', '#8B5CF6',
        'industrial', '#F97316',
        'stubble', '#EAB308',
        'wildfire', '#EF4444',
        'mining', '#6B7280',
        '#A1A1AA',
      ],
      'circle-opacity': 0.8,
      'circle-stroke-width': 1,
      'circle-stroke-color': 'rgba(0,0,0,0.8)',
    },
  };



  // Quick jump helper
  const jumpToSector = (lat: number, lon: number, zoom: number) => {
    mapRef.current?.flyTo({ center: [lon, lat], zoom, duration: 1800 });
  };

  return (
    <div className="relative w-full h-full">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 72.5,
          latitude: 19.2,
          zoom: 6.5,
        }}
        minZoom={3}
        maxZoom={18}
        doubleClickZoom={true}
        style={{ width: '100%', height: '100%' }}
        mapStyle={MAP_STYLE}
        mapLib={maplibregl}
        interactiveLayerIds={[
          ...(activeFilters.showVessels ? ['clusters', 'vessel-dots'] : []),
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
          if (feature?.layer.id === 'clusters') {
            const clusterId = feature.properties?.cluster_id;
            const mapboxSource = mapRef.current?.getSource('vessels') as any;
            mapboxSource?.getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
              if (err) return;
              mapRef.current?.easeTo({
                center: (feature.geometry as any).coordinates,
                zoom: zoom,
                duration: 500,
              });
            });
            return;
          }

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
        {/* Navigation Controls positioned cleanly in top-right corner */}
        <NavigationControl position="top-right" />

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

            {/* Active Ingested Spill Layer */}
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

        {/* Layer 2B: INCOIS Forward Drift Simulation (72h Forecast) */}
        {isDriftSimActive && (
          <>
            {/* Trajectory Corridor LineString */}
            {driftTrajectoryLineGeoJSON && (
              <Source id="drift-trajectory-line" type="geojson" data={driftTrajectoryLineGeoJSON as any}>
                <Layer
                  id="drift-line"
                  type="line"
                  paint={{
                    'line-color': '#F59E0B',
                    'line-width': 2.5,
                    'line-dasharray': [2, 2],
                  }}
                />
              </Source>
            )}

            {/* Active Time Step Polygon */}
            {driftStepPolygonGeoJSON && (
              <Source id="drift-step-polygon" type="geojson" data={driftStepPolygonGeoJSON as any}>
                <Layer
                  id="drift-step-fill"
                  type="fill"
                  paint={{
                    'fill-color': '#F59E0B',
                    'fill-opacity': 0.45,
                  }}
                />
                <Layer
                  id="drift-step-outline"
                  type="line"
                  paint={{
                    'line-color': '#FCD34D',
                    'line-width': 2.5,
                  }}
                />
              </Source>
            )}

            {/* Projected Centroid Marker */}
            {activeDriftStep && (
              <Marker
                longitude={activeDriftStep.centroid_lon}
                latitude={activeDriftStep.centroid_lat}
                anchor="center"
              >
                <div className="relative flex items-center justify-center pointer-events-none">
                  <div className="w-6 h-6 rounded-full bg-amber-500/30 animate-ping absolute" />
                  <div className="w-3.5 h-3.5 rounded-full bg-amber-400 border-2 border-black shadow-[0_0_12px_#F59E0B]" />
                  <div className="absolute -top-6 whitespace-nowrap bg-black/85 text-amber-300 text-[10px] font-mono px-1.5 py-0.5 rounded border border-amber-500/50 shadow">
                    T+{activeDriftStep.time_offset_hours}h · {activeDriftStep.area_km2} km²
                  </div>
                </div>
              </Marker>
            )}
          </>
        )}

        {/* Layer 3: Vessel Heatmap */}
        {activeFilters.showDensityHeatmap && (
          <Source id="vessels-heat" type="geojson" data={vesselsGeoJSON}>
            <Layer {...vesselHeatmapLayer} />
          </Source>
        )}

        {/* Layer 4: AIS Real-Time Vessel Traffic (Clustered & Unclustered) */}
        {activeFilters.showVessels && (
          <Source
            id="vessels"
            type="geojson"
            data={vesselsGeoJSON}
            cluster={true}
            clusterMaxZoom={10}
            clusterRadius={40}
          >
            <Layer {...clusterLayer} />
            <Layer {...clusterCountLayer} />
            <Layer {...vesselDotsLayer} />
          </Source>
        )}

        {/* Layer: Strategic Fixed Maritime Pins (Bombay High, Ports, MPAs) */}
        {/* <StaticPinsLayer /> */}

        {/* Selected Vessel Focused Chevron Indicator (Zero clutter on main map) */}
        {selectedVessel && (
          <VesselMarker vessel={selectedVessel} onSelect={selectVessel} />
        )}


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
            <div
              className="p-3.5 rounded-lg shadow-2xl text-xs flex flex-col gap-2 min-w-[260px]"
              style={{
                background: 'var(--navy-800)',
                border: '1px solid var(--navy-400)',
                color: 'var(--text-primary)',
              }}
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b pb-1.5" style={{ borderColor: 'var(--navy-600)' }}>
                <span className="font-bold text-sm tracking-wide text-white">
                  {selectedVessel.vessel_name}
                </span>
                <span
                  className="px-2 py-0.5 rounded text-[10px] font-bold font-data"
                  style={{
                    background:
                      selectedVessel.risk_level === 'CRITICAL'
                        ? 'rgba(239, 68, 68, 0.25)'
                        : selectedVessel.risk_level === 'WARNING'
                        ? 'rgba(245, 158, 11, 0.25)'
                        : 'rgba(0, 212, 232, 0.20)',
                    color:
                      selectedVessel.risk_level === 'CRITICAL'
                        ? '#EF4444'
                        : selectedVessel.risk_level === 'WARNING'
                        ? '#F59E0B'
                        : '#00D4E8',
                    border: `1px solid ${
                      selectedVessel.risk_level === 'CRITICAL'
                        ? '#EF4444'
                        : selectedVessel.risk_level === 'WARNING'
                        ? '#F59E0B'
                        : '#00D4E8'
                    }`,
                  }}
                >
                  {selectedVessel.risk_level}
                </span>
              </div>

              {/* Data Grid */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-data">
                <span style={{ color: 'var(--text-secondary)' }}>MMSI:</span>
                <span className="font-semibold text-white">{selectedVessel.mmsi}</span>

                <span style={{ color: 'var(--text-secondary)' }}>Type:</span>
                <span className="font-semibold text-white">{selectedVessel.vessel_type_label}</span>

                <span style={{ color: 'var(--text-secondary)' }}>Speed:</span>
                <span className="font-semibold text-white">{selectedVessel.speed_knots} kts</span>

                <span style={{ color: 'var(--text-secondary)' }}>Course:</span>
                <span className="font-semibold text-white">{selectedVessel.course_deg}°</span>

                <span style={{ color: 'var(--text-secondary)' }}>Risk Score:</span>
                <span className="font-bold" style={{ color: selectedVessel.risk_score > 0.7 ? '#EF4444' : '#10B981' }}>
                  {(selectedVessel.risk_score * 100).toFixed(0)}%
                </span>

                <span style={{ color: 'var(--text-secondary)' }}>AIS Status:</span>
                <span className={selectedVessel.is_dark ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                  {selectedVessel.is_dark ? `DARK (${selectedVessel.ais_gap_minutes}m)` : 'ACTIVE'}
                </span>
              </div>

              {/* Live Satellite Reconnaissance Viewport */}
              <div className="relative rounded border overflow-hidden mt-1" style={{ borderColor: 'var(--navy-500)', background: '#050c18' }}>
                <div className="flex items-center justify-between px-2 py-1 bg-black/50 border-b border-navy-600/60">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
                    <span className="text-[9px] font-mono font-bold tracking-wider text-teal-300">
                      🛰️ {vesselSensor === 'sentinel1' ? 'SENTINEL-1 C-SAR' : 'SENTINEL-2 OPTICAL'}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setVesselSensor('sentinel1'); }}
                      className={`px-1.5 py-0.5 text-[8px] font-mono rounded transition-colors ${
                        vesselSensor === 'sentinel1'
                          ? 'bg-teal-500 text-navy-950 font-bold'
                          : 'text-gray-400 hover:text-white bg-navy-800'
                      }`}
                    >
                      SAR
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setVesselSensor('sentinel2'); }}
                      className={`px-1.5 py-0.5 text-[8px] font-mono rounded transition-colors ${
                        vesselSensor === 'sentinel2'
                          ? 'bg-teal-500 text-navy-950 font-bold'
                          : 'text-gray-400 hover:text-white bg-navy-800'
                      }`}
                    >
                      OPTICAL
                    </button>
                  </div>
                </div>

                <div className="relative w-full h-32 bg-[#06101e] flex items-center justify-center overflow-hidden">
                  <img
                    key={`${selectedVessel.mmsi}-${vesselSensor}`}
                    src={`http://localhost:8000/api/v1/satellite/vessel-image?lat=${selectedVessel.lat}&lon=${selectedVessel.lon}&mmsi=${selectedVessel.mmsi}&sensor=${vesselSensor}&course=${selectedVessel.course_deg ?? 0}&speed=${selectedVessel.speed_knots ?? 12}`}
                    alt={`Satellite pass of ${selectedVessel.vessel_name}`}
                    className="w-full h-full object-cover transition-opacity duration-300"
                    loading="eager"
                    onError={(e) => {
                      // Gracefully fallback to relative path or placeholder if port 8000 is routed differently
                      const target = e.currentTarget;
                      if (!target.src.includes('/api/v1/satellite/vessel-image')) {
                        target.src = `/api/v1/satellite/vessel-image?lat=${selectedVessel.lat}&lon=${selectedVessel.lon}&mmsi=${selectedVessel.mmsi}&sensor=${vesselSensor}&course=${selectedVessel.course_deg ?? 0}&speed=${selectedVessel.speed_knots ?? 12}`;
                      }
                    }}
                  />
                  {/* Tactical HUD Overlay Elements */}
                  <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-1.5">
                    <div className="flex justify-between text-[7.5px] font-mono text-teal-400/90 drop-shadow">
                      <span>10m/px · SWATH 250km</span>
                      <span>{selectedVessel.lat.toFixed(3)}°N, {selectedVessel.lon.toFixed(3)}°E</span>
                    </div>
                    <div className="flex justify-between items-end text-[7.5px] font-mono">
                      <span className="bg-black/70 px-1 py-0.5 rounded text-[7px] text-teal-300 border border-teal-500/30">
                        🎯 RECON ACQUIRED
                      </span>
                      <span className="text-gray-400 bg-black/60 px-1 rounded text-[6.5px]">
                        Copernicus CDSE
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* GFW Track Replay Button */}
              <button
                type="button"
                onClick={() => {
                  setTrackVesselId(selectedVessel.mmsi);
                  setShowTrackPlayer(true);
                  setTrackFrame(0);
                  setTrackIsPlaying(true);
                }}
                className="mt-1 w-full py-1 px-2 rounded text-[10px] font-mono font-bold flex items-center justify-center gap-1.5 transition-all"
                style={{
                  background: 'rgba(0, 212, 232, 0.15)',
                  border: '1px solid var(--teal-500)',
                  color: 'var(--teal-400)',
                }}
              >
                <span>▶ Replay AIS Track</span>
              </button>
            </div>
          </Popup>
        )}

        {/* Hotspot Hover Tooltip */}
        {hoveredHotspot && (
          <Popup
            longitude={hoveredHotspot.longitude}
            latitude={hoveredHotspot.latitude}
            closeButton={false}
            closeOnClick={false}
            anchor="top"
          >
            <div className="p-2 rounded bg-gray-900 border border-amber-500 text-white font-mono text-[10px]">
              <div className="font-bold text-amber-400 uppercase">{hoveredHotspot.fire_type} Hotspot</div>
              <div>FRP: {(hoveredHotspot.frp ?? 0).toFixed(1)} MW</div>
              <div>Confidence: {hoveredHotspot.confidence}</div>
            </div>
          </Popup>
        )}

        {/* ── Vessel Track Playback Layers (Full Route & Dark Gap) ── */}
        {showTrackPlayer && trackVesselId && (
          <VesselTrackPlayer
            vesselId={trackVesselId}
            onTrackLoaded={(loadedTrack) => {
              setVesselTrack(loadedTrack);
              // Fly camera to first point or track centroid if available
              if (loadedTrack.track_points.length > 0) {
                const p0 = loadedTrack.track_points[0];
                mapRef.current?.flyTo({
                  center: [p0.lon, p0.lat],
                  zoom: 8.5,
                  duration: 1500,
                });
              }
            }}
            onFrameChange={(_point, idx) => setTrackFrame(idx)}
          />
        )}
      </Map>

      {/* ── Top-Left Collapsible GIS Layer & Sensor Dock ── */}
      <div className="absolute top-3 left-3 z-30 flex flex-col gap-2 pointer-events-auto">
        {/* Toggle Button */}
        <button
          type="button"
          onClick={() => setIsLayerDockOpen((prev) => !prev)}
          className="self-start px-2.5 py-1.5 rounded-md font-mono text-xs font-bold flex items-center gap-2 shadow-xl border backdrop-blur-md transition-all hover:bg-navy-700/80"
          style={{
            background: 'rgba(7, 14, 27, 0.92)',
            borderColor: 'var(--navy-400)',
            color: 'var(--teal-300)',
          }}
        >
          <span>☰</span>
          <span>Surveillance Layers</span>
          <span className="text-[10px] text-gray-400">{isLayerDockOpen ? '▲' : '▼'}</span>
        </button>

        {/* Expanded Layer Panel */}
        {isLayerDockOpen && (
          <div
            className="p-3 rounded-lg shadow-2xl flex flex-col gap-2.5 backdrop-blur-md border animate-in fade-in zoom-in-95 duration-150"
            style={{
              background: 'rgba(7, 14, 27, 0.94)',
              borderColor: 'var(--navy-500)',
              width: '240px',
            }}
          >
            {/* Quick Sector Jumps */}
            <div>
              <div className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-widest mb-1.5">
                Quick Sector Jump
              </div>
              <div className="grid grid-cols-2 gap-1 text-[10px] font-mono">
                <button
                  type="button"
                  onClick={() => jumpToSector(20.5, 78.9, 4.8)}
                  className="px-1.5 py-0.5 rounded bg-navy-800 text-gray-300 hover:text-white hover:bg-navy-700 text-left truncate"
                >
                  📍 All India EEZ
                </button>
                <button
                  type="button"
                  onClick={() => jumpToSector(19.20, 71.50, 8.5)}
                  className="px-1.5 py-0.5 rounded bg-navy-800 text-red-300 hover:text-white hover:bg-red-950/60 text-left truncate font-bold"
                >
                  🛢️ Bombay High
                </button>
                <button
                  type="button"
                  onClick={() => jumpToSector(18.95, 72.95, 10.5)}
                  className="px-1.5 py-0.5 rounded bg-navy-800 text-gray-300 hover:text-white hover:bg-navy-700 text-left truncate"
                >
                  ⚓ JNPT Approach
                </button>
                <button
                  type="button"
                  onClick={() => jumpToSector(22.50, 69.45, 9.0)}
                  className="px-1.5 py-0.5 rounded bg-navy-800 text-purple-300 hover:text-white hover:bg-purple-950/60 text-left truncate"
                >
                  🛡️ Kutch Sanctuary
                </button>
              </div>
            </div>

            {/* Layer Controls */}
            <div className="flex flex-col gap-1.5 text-xs pt-2 border-t border-navy-700">
              <div className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-widest mb-0.5">
                LAYER CONTROL
              </div>

              <button
                type="button"
                onClick={() => setExclusiveLayer('showVessels')}
                className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
              >
                <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                  <span className="text-cyan-400">🛥️</span>
                  <span>AIS Vessels</span>
                </span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${activeFilters.showVessels ? 'text-navy-950 bg-cyan-400' : 'text-gray-500 bg-navy-800'}`}>
                  {activeFilters.showVessels ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setExclusiveLayer('showSpillZones')}
                className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
              >
                <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                  <span className="text-red-400">🛢️</span>
                  <span>Spill Zones</span>
                </span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${activeFilters.showSpillZones ? 'text-white bg-red-500' : 'text-gray-500 bg-navy-800'}`}>
                  {activeFilters.showSpillZones ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setExclusiveLayer('showMPABoundaries')}
                className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
              >
                <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                  <span className="text-emerald-400">🛡️</span>
                  <span>MPA Zones</span>
                </span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${activeFilters.showMPABoundaries ? 'text-navy-950 bg-emerald-400' : 'text-gray-500 bg-navy-800'}`}>
                  {activeFilters.showMPABoundaries ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setExclusiveLayer('showDensityHeatmap')}
                className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
              >
                <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                  <span className="text-purple-400">📊</span>
                  <span>Density Heatmap</span>
                </span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${activeFilters.showDensityHeatmap ? 'text-white bg-purple-500' : 'text-gray-500 bg-navy-800'}`}>
                  {activeFilters.showDensityHeatmap ? 'ON' : 'OFF'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setExclusiveLayer('showFireHotspots')}
                className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
              >
                <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                  <span className="text-amber-400">🔥</span>
                  <span>Fire / Thermal</span>
                </span>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${activeFilters.showFireHotspots ? 'text-navy-950 bg-amber-400' : 'text-gray-500 bg-navy-800'}`}>
                  {activeFilters.showFireHotspots ? 'ON' : 'OFF'}
                </span>
              </button>

            </div>

            {/* Autonomous Sentinel-1C Ingestion Status & Sync */}
            <div className="pt-2 border-t border-navy-700 flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-[9px] font-mono text-gray-400">
                <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  S1C STREAM: ACTIVE
                </span>
                <span>15m AUTO</span>
              </div>

              <button
                type="button"
                onClick={handleSimulateSpillDemo}
                disabled={isSimulating}
                className="w-full py-1.5 px-2 rounded text-[11px] font-mono font-bold tracking-wide flex items-center justify-center gap-1.5 transition-all shadow border border-red-500/80 bg-red-950/80 text-red-200 hover:bg-red-900"
                title="Force Sentinel-1C C-SAR Orbit #142 Hydrocarbon Slick Ingestion & ML Attribution Sync"
              >
                <span>📡</span>
                <span>{isSimulating ? 'Syncing Sentinel-1C...' : 'Sync SAR Orbit #142'}</span>
              </button>

              <button
                type="button"
                onClick={() => toggleDriftSim()}
                className="w-full py-1.5 px-2 rounded text-[11px] font-mono font-bold tracking-wide flex items-center justify-center gap-1.5 transition-all border"
                style={{
                  background: isDriftSimActive ? 'rgba(245, 158, 11, 0.25)' : 'rgba(15, 31, 61, 0.8)',
                  borderColor: isDriftSimActive ? 'var(--amber-500)' : 'var(--navy-500)',
                  color: isDriftSimActive ? 'var(--amber-300)' : 'var(--text-secondary)',
                }}
              >
                <span>🌊</span>
                <span>{isDriftSimActive ? 'Close Drift HUD' : 'INCOIS 72h Drift Sim'}</span>
              </button>
            </div>
          </div>
        )}
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
          onClose={() => {
            setShowTrackPlayer(false);
            setTrackIsPlaying(false);
          }}
        />
      )}

      {/* ── SAR Image Popup (spill polygon click) ── */}
      {sarPopupSpill && (
        <SpillSARPopup
          spill={sarPopupSpill}
          screenX={sarPopupScreenPos.x + 20}
          screenY={sarPopupScreenPos.y - 30}
          onLaunchDrift={() => {
            if (!isDriftSimActive) toggleDriftSim();
          }}
          onClose={() => setSarPopupSpill(null)}
        />
      )}

      {/* ── INCOIS 72h Ocean Drift Controller HUD ── */}
      <SpillDriftController />
    </div>
  );
}
