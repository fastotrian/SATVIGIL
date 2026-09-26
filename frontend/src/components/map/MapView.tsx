/**
 * SATVIGIL — Defense-Grade 3D WebGL Command Center Map View (CesiumJS)
 * Features:
 *   - Native WebGL 3D Globe with ESRI Marine World Dark Gray Canvas
 *   - Clustered & tactical AIS vessel fleet rendering (11,000+ vessels)
 *   - Dynamic risk coloring (Normal: Electric Cyan, Dark: Red, High Risk: Amber, MPA: Purple)
 *   - Copernicus Sentinel-1C SAR hydrocarbon slick polygons & Fay spreading drift corridor
 *   - NASA VIIRS thermal anomaly hotspots (174 live detections)
 *   - Marine Protected Area (MPA) conservation zone overlays
 *   - INCOIS-OOSA 72-hour forward ocean drift trajectory simulator
 *   - Top-left collapsible GIS Layer & Sensor Dock with quick sector jumps
 *   - Real-time 3D camera controls (Zoom, Reset North, 3D Horizon Tilt)
 */
import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import {
  Viewer,
  Cartesian3,
  Cartesian2,
  Color,
  GeoJsonDataSource,
  CustomDataSource,
  Entity,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  Math as CesiumMath,
  NearFarScalar,
  PolylineDashMaterialProperty,
  CallbackProperty,
  ColorMaterialProperty,
  ConstantProperty,
  Rectangle as CesiumRectangle,
  SingleTileImageryProvider,
  ImageryLayer,
  defined,
} from 'cesium';

import {
  Ship,
  Navigation,
  Droplets,
  Shield,
  Flame,
  Mountain,
  Radio,
  Waves,
  MapPin,
  AlertTriangle,
  Layers,
  Eye,
  Info,
  Compass,
} from 'lucide-react';

import { useAlertStore } from '../../store/alertStore';
import { RISK_COLORS } from '../../constants/riskColors';
import { DEFAULT_BOMBAY_HIGH_SPILL } from '../../data/seedMaritimeData';
import type { Vessel, SpillEvent, VesselTrack } from '../../types/maritime';
import type { ThermalHotspot } from '../../types/fire';
import { VesselTrackPlayer, TrackPlaybackControls } from './VesselTrackPlayer';
import { SpillSARPopup } from './SpillSARPopup';
import { SpillDriftController } from './SpillDriftController';
import {
  createSatelliteImageryProvider,
  createSatelliteReferenceProvider,
  createDarkBaseImageryProvider,
  createDarkReferenceImageryProvider,
  configureTacticalViewer,
  SECTOR_WAYPOINTS,
  DEFAULT_CAMERA_VIEW,
} from './cesiumConfig';

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

// ── Hardcoded Geological Danger Zones (Landslide Risk Across India) ───────
export const INDIA_GEOLOGICAL_GEOJSON: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        id: 'geo-chamoli',
        name: 'Chamoli & Joshimath Debris Corridor',
        state: 'Uttarakhand',
        risk_level: 'CRITICAL',
        hazard_type: 'High Slope Instability & Flash Rockslide',
        monitoring_agency: 'GSI / NDMA / USAC',
        description: 'Active tectonic fracture zone with steep overburden and recurrent slope displacement along Alaknanda valley.',
        area_km2: 245.8,
        slope_angle: '38°–52°',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [79.45, 30.35],
            [79.75, 30.38],
            [79.88, 30.60],
            [79.65, 30.72],
            [79.38, 30.55],
            [79.45, 30.35],
          ],
        ],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'geo-wayanad',
        name: 'Wayanad Meppadi-Chooralmala Zone',
        state: 'Kerala',
        risk_level: 'CRITICAL',
        hazard_type: 'Monsoon Saturated Soil Slip & Mudslide',
        monitoring_agency: 'GSI / KSDMA',
        description: 'Steep Western Ghats escarpment prone to rapid liquefaction and torrential debris flows during heavy precipitation.',
        area_km2: 132.4,
        slope_angle: '32°–45°',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [76.08, 11.48],
            [76.24, 11.48],
            [76.28, 11.62],
            [76.12, 11.64],
            [76.08, 11.48],
          ],
        ],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'geo-kullu',
        name: 'Kullu-Manali & Beas Valley Slide Zone',
        state: 'Himachal Pradesh',
        risk_level: 'HIGH',
        hazard_type: 'River Cut Bank Slumping & Slope Creep',
        monitoring_agency: 'HPSDMA / GSI',
        description: 'NH-3 corridor affected by toe-erosion and weathered mica-schist slope collapses during heavy runoff.',
        area_km2: 188.0,
        slope_angle: '30°–48°',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [77.05, 31.85],
            [77.28, 31.90],
            [77.35, 32.25],
            [77.10, 32.32],
            [77.05, 31.85],
          ],
        ],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'geo-teesta',
        name: 'Sikkim Teesta River Slide Basin',
        state: 'Sikkim',
        risk_level: 'CRITICAL',
        hazard_type: 'Flash Surcharge & Moraine Dam Slide Failure',
        monitoring_agency: 'SSDMA / CWC',
        description: 'Chungthang to Mangan NH-10 arterial link subjected to repeated rotational slides and slope subsidence.',
        area_km2: 165.2,
        slope_angle: '35°–55°',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [88.42, 27.30],
            [88.65, 27.32],
            [88.70, 27.65],
            [88.48, 27.68],
            [88.42, 27.30],
          ],
        ],
      },
    },
    {
      type: 'Feature',
      properties: {
        id: 'geo-nilgiris',
        name: 'Nilgiris Coonoor Ghat Slopes',
        state: 'Tamil Nadu',
        risk_level: 'HIGH',
        hazard_type: 'Planar Failure & Regolith Slides',
        monitoring_agency: 'TNSDMA / GSI',
        description: 'Narrow hill highway corridors highly susceptible to regolith saturation and slope wash.',
        area_km2: 95.6,
        slope_angle: '28°–40°',
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [76.68, 11.32],
            [76.88, 11.32],
            [76.92, 11.45],
            [76.72, 11.46],
            [76.68, 11.32],
          ],
        ],
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

// ── Directional Vessel Navigation Arrow Icons ─────────────────────────────
function createVesselArrowSvg(colorHex: string, outlineHex = '#031726'): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
    <path d="M16 2 L28 28 L16 22 L4 28 Z" fill="${colorHex}" stroke="${outlineHex}" stroke-width="2" stroke-linejoin="round"/>
  </svg>`;
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

const ARROW_ICONS = {
  CYAN: createVesselArrowSvg('#00E5FF'),
  CRIMSON: createVesselArrowSvg('#EF4444'),
  AMBER: createVesselArrowSvg('#F59E0B'),
  PURPLE: createVesselArrowSvg('#C084FC'),
  GREEN: createVesselArrowSvg('#10B981'),
};

// ── Smooth Organic Marine Traffic Heatmap Canvas Generator (Image 1 Style) ──
function generateSmoothHeatmapCanvas(vessels: Vessel[]): string {
  const width = 1024;
  const height = 768;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return '';

  const minLon = 64.0;
  const maxLon = 96.0;
  const minLat = 4.0;
  const maxLat = 26.0;

  const project = (lon: number, lat: number) => ({
    x: ((lon - minLon) / (maxLon - minLon)) * width,
    y: ((maxLat - lat) / (maxLat - minLat)) * height,
  });

  ctx.clearRect(0, 0, width, height);

  // 1. Broad soft emerald-green maritime traffic wash (as seen in Image 1 over Bay of Bengal)
  for (const v of vessels) {
    if (v.lon < minLon || v.lon > maxLon || v.lat < minLat || v.lat > maxLat) continue;
    const { x, y } = project(v.lon, v.lat);
    const grad = ctx.createRadialGradient(x, y, 0, x, y, 110);
    grad.addColorStop(0, 'rgba(16, 185, 129, 0.42)');
    grad.addColorStop(0.45, 'rgba(5, 150, 105, 0.24)');
    grad.addColorStop(0.8, 'rgba(4, 120, 87, 0.08)');
    grad.addColorStop(1, 'rgba(4, 120, 87, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, 110, 0, Math.PI * 2);
    ctx.fill();
  }

  // 2. Luminous amber/yellow concentrated traffic corridors & choke points
  for (const v of vessels) {
    if (v.lon < minLon || v.lon > maxLon || v.lat < minLat || v.lat > maxLat) continue;
    const { x, y } = project(v.lon, v.lat);
    const grad = ctx.createRadialGradient(x, y, 0, x, y, 55);
    grad.addColorStop(0, 'rgba(234, 179, 8, 0.58)');
    grad.addColorStop(0.5, 'rgba(202, 138, 4, 0.32)');
    grad.addColorStop(0.85, 'rgba(161, 98, 7, 0.10)');
    grad.addColorStop(1, 'rgba(161, 98, 7, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, 55, 0, Math.PI * 2);
    ctx.fill();
  }

  // 3. High-intensity orange & crimson hazard/fast-traffic hot nodes
  for (const v of vessels) {
    if (v.lon < minLon || v.lon > maxLon || v.lat < minLat || v.lat > maxLat) continue;
    if (v.speed_knots > 7 || v.risk_score > 0.4 || v.is_dark) {
      const { x, y } = project(v.lon, v.lat);
      const grad = ctx.createRadialGradient(x, y, 0, x, y, 32);
      grad.addColorStop(0, 'rgba(239, 68, 68, 0.65)');
      grad.addColorStop(0.45, 'rgba(249, 115, 22, 0.38)');
      grad.addColorStop(0.85, 'rgba(249, 115, 22, 0.08)');
      grad.addColorStop(1, 'rgba(249, 115, 22, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, 32, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  return canvas.toDataURL('image/png');
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Viewer | null>(null);

  const {
    activeNavTab,
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

  const [spills, setSpills] = useState<SpillEvent[]>([DEFAULT_BOMBAY_HIGH_SPILL]);
  const [activeSpill, setActiveSpill] = useState<SpillEvent | null>(DEFAULT_BOMBAY_HIGH_SPILL);
  const [sarPopupSpill, setSarPopupSpill] = useState<SpillEvent | null>(null);
  const [sarPopupScreenPos, setSarPopupScreenPos] = useState({ x: 100, y: 100 });
  const [popupScreenPos, setPopupScreenPos] = useState<{ x: number; y: number } | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isLayerDockOpen, setIsLayerDockOpen] = useState(true);
  const [vesselSensor, setVesselSensor] = useState<'sentinel1' | 'sentinel2'>('sentinel1');
  const [isZoomedOut, setIsZoomedOut] = useState(false);
  const [selectedHazardZone, setSelectedHazardZone] = useState<any | null>(null);

  // GFW vessel track playback state
  const [showTrackPlayer, setShowTrackPlayer] = useState(false);
  const [trackVesselId, setTrackVesselId] = useState<string | null>(null);
  const [vesselTrack, setVesselTrack] = useState<VesselTrack | null>(null);
  const [trackFrame, setTrackFrame] = useState(0);
  const [trackIsPlaying, setTrackIsPlaying] = useState(false);
  const [trackSpeed, setTrackSpeed] = useState(3);

  const [hotspots, setHotspots] = useState<ThermalHotspot[]>([]);
  const [hoveredHotspot, setHoveredHotspot] = useState<ThermalHotspot | null>(null);
  const [hoveredHotspotPos, setHoveredHotspotPos] = useState<{ x: number; y: number } | null>(null);

  // Data sources references
  const vesselsDataSourceRef = useRef<CustomDataSource | null>(null);
  const hotspotsDataSourceRef = useRef<CustomDataSource | null>(null);
  const spillsDataSourceRef = useRef<GeoJsonDataSource | null>(null);
  const activeSpillDataSourceRef = useRef<GeoJsonDataSource | null>(null);
  const mpasDataSourceRef = useRef<GeoJsonDataSource | null>(null);
  const demoTracksDataSourceRef = useRef<GeoJsonDataSource | null>(null);
  const driftCorridorDataSourceRef = useRef<CustomDataSource | null>(null);
  const heatmapLayerRef = useRef<ImageryLayer | null>(null);
  const geologicalDataSourceRef = useRef<GeoJsonDataSource | null>(null);

  // Basemap style state: 'satellite' (Google Earth style) or 'dark' (Tactical Dark Canvas)
  const [basemapTheme, setBasemapTheme] = useState<'satellite' | 'dark'>('satellite');

  // ── 1. Initialize Cesium 3D WebGL Viewer ──────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    // Create high-resolution satellite imagery (Google Earth look & feel)
    const satImagery = createSatelliteImageryProvider();
    const satRef = createSatelliteReferenceProvider();

    const viewer = new Viewer(containerRef.current, {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      baseLayer: false,
      skyAtmosphere: undefined,
    });

    // Add Google Earth optical satellite imagery & reference borders
    viewer.imageryLayers.addImageryProvider(satImagery);
    viewer.imageryLayers.addImageryProvider(satRef);

    // Apply military command center visual parameters
    configureTacticalViewer(viewer);

    // Set camera to Bombay High / Arabian Sea
    viewer.camera.setView(DEFAULT_CAMERA_VIEW);

    viewerRef.current = viewer;

    // Create DataSources - clustering disabled to remove vessel count numbers
    const vesselsDS = new CustomDataSource('vessels');
    vesselsDS.clustering.enabled = false;
    viewer.dataSources.add(vesselsDS);
    vesselsDataSourceRef.current = vesselsDS;

    const hotspotsDS = new CustomDataSource('hotspots');
    viewer.dataSources.add(hotspotsDS);
    hotspotsDataSourceRef.current = hotspotsDS;

    const driftDS = new CustomDataSource('drift');
    viewer.dataSources.add(driftDS);
    driftCorridorDataSourceRef.current = driftDS;

    // Setup MPAs & Demo Tracks
    GeoJsonDataSource.load(INDIA_MPAS_GEOJSON, {
      stroke: Color.fromCssColorString('#10B981'),
      fill: Color.fromCssColorString('#10B981').withAlpha(0.18),
      strokeWidth: 2,
    }).then((ds) => {
      viewer.dataSources.add(ds);
      mpasDataSourceRef.current = ds;
      ds.show = activeFilters.showMPABoundaries;
    });

    GeoJsonDataSource.load(DEMO_TRACKS_GEOJSON, {
      stroke: Color.fromCssColorString('#F59E0B'),
      strokeWidth: 3,
    }).then((ds) => {
      viewer.dataSources.add(ds);
      demoTracksDataSourceRef.current = ds;
      ds.show = activeFilters.showVessels;
    });

    // Setup Geological Hazard Danger Zones
    GeoJsonDataSource.load(INDIA_GEOLOGICAL_GEOJSON, {
      stroke: Color.fromCssColorString('#EF4444'),
      fill: Color.fromCssColorString('#EF4444').withAlpha(0.28),
      strokeWidth: 2.5,
      clampToGround: true,
    }).then((ds) => {
      viewer.dataSources.add(ds);
      geologicalDataSourceRef.current = ds;
      ds.show = activeNavTab === 'geological';
    });

    // ── Mouse Interaction Handlers ──
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);

    // Left Click: select vessel, spill, or geological hazard
    handler.setInputAction((click: any) => {
      const picked = viewer.scene.pick(click.position);
      if (defined(picked) && picked.id) {
        const entity = picked.id as Entity;

        // Clicked a cluster: zoom in
        if (picked.primitive && picked.primitive._cluster) {
          const cartesian = viewer.scene.pickPosition(click.position);
          if (cartesian) {
            viewer.camera.flyTo({
              destination: Cartesian3.multiplyByScalar(cartesian, 0.85, new Cartesian3()),
              duration: 1.0,
            });
          }
          return;
        }

        // Clicked a vessel
        if (entity.properties && entity.properties.hasProperty('vessel_data')) {
          const v = entity.properties.getValue(viewer.clock.currentTime).vessel_data as Vessel;
          selectVessel(v);
          setSarPopupSpill(null);
          setSelectedHazardZone(null);
          return;
        }

        // Clicked a spill
        if (entity.properties && entity.properties.hasProperty('spill_data')) {
          const s = entity.properties.getValue(viewer.clock.currentTime).spill_data as SpillEvent;
          setSarPopupSpill(s);
          setSarPopupScreenPos({ x: click.position.x, y: click.position.y });
          setSelectedHazardZone(null);
          return;
        }

        // Clicked a geological landslide zone
        if (entity.properties && entity.properties.hasProperty('hazard_type')) {
          const rawProps = entity.properties.getValue(viewer.clock.currentTime);
          setSelectedHazardZone(rawProps);
          selectVessel(null);
          setSarPopupSpill(null);
          return;
        }
      } else {
        selectVessel(null);
        setSarPopupSpill(null);
        setSelectedHazardZone(null);
      }
    }, ScreenSpaceEventType.LEFT_CLICK);

    // Mouse Move: hotspot hover tooltip
    handler.setInputAction((movement: any) => {
      const picked = viewer.scene.pick(movement.endPosition);
      if (defined(picked) && picked.id && picked.id.properties?.hasProperty('hotspot_data')) {
        const h = picked.id.properties.getValue(viewer.clock.currentTime).hotspot_data as ThermalHotspot;
        setHoveredHotspot(h);
        setHoveredHotspotPos({ x: movement.endPosition.x, y: movement.endPosition.y });
      } else {
        setHoveredHotspot(null);
        setHoveredHotspotPos(null);
      }
    }, ScreenSpaceEventType.MOUSE_MOVE);

    // Dynamic screen coordinate updater & zoom-out detector
    const removePostRenderListener = viewer.scene.postRender.addEventListener(() => {
      const camHeight = viewer.camera.positionCartographic.height;
      const zoomedOut = camHeight > 1600000;
      setIsZoomedOut((prev) => (prev !== zoomedOut ? zoomedOut : prev));

      const storeState = useAlertStore.getState();
      const currentSelectedVessel = storeState.selectedVessel;
      if (currentSelectedVessel) {
        const pos3D = Cartesian3.fromDegrees(currentSelectedVessel.lon, currentSelectedVessel.lat, 20);
        const canvasCoords = viewer.scene.cartesianToCanvasCoordinates(pos3D);
        if (canvasCoords) {
          setPopupScreenPos({ x: canvasCoords.x, y: canvasCoords.y });
        }
      } else {
        setPopupScreenPos(null);
      }
    });

    return () => {
      removePostRenderListener();
      handler.destroy();
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  // ── Dynamic Basemap Switcher (Google Earth vs Tactical Dark) ─────────────
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    viewer.imageryLayers.removeAll();

    if (basemapTheme === 'satellite') {
      const satImagery = createSatelliteImageryProvider();
      const satRef = createSatelliteReferenceProvider();
      viewer.imageryLayers.addImageryProvider(satImagery);
      viewer.imageryLayers.addImageryProvider(satRef);
    } else {
      const darkImagery = createDarkBaseImageryProvider();
      const darkRef = createDarkReferenceImageryProvider();
      viewer.imageryLayers.addImageryProvider(darkImagery);
      viewer.imageryLayers.addImageryProvider(darkRef);
    }
  }, [basemapTheme]);

  // ── 2. Periodic Backend Data Fetching ──────────────────────────────────────
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
    return () => clearInterval(interval);
  }, [setVessels]);

  // ── Synchronize Navigation Tabs to Active Layer Visibility ──────────────
  useEffect(() => {
    const isMaritime = activeNavTab === 'maritime';
    const isThermal = activeNavTab === 'thermal';
    const isGeological = activeNavTab === 'geological';

    if (vesselsDataSourceRef.current) {
      vesselsDataSourceRef.current.show = isMaritime && activeFilters.showVessels;
    }
    if (spillsDataSourceRef.current) {
      spillsDataSourceRef.current.show = isMaritime && activeFilters.showSpillZones;
    }
    if (mpasDataSourceRef.current) {
      mpasDataSourceRef.current.show = isMaritime && activeFilters.showMPABoundaries;
    }
    if (demoTracksDataSourceRef.current) {
      demoTracksDataSourceRef.current.show = isMaritime && activeFilters.showVessels;
    }
    if (hotspotsDataSourceRef.current) {
      hotspotsDataSourceRef.current.show = isThermal && activeFilters.showFireHotspots;
    }
    if (geologicalDataSourceRef.current) {
      geologicalDataSourceRef.current.show = isGeological && activeFilters.showGeologicalZones;
    }
  }, [activeNavTab, activeFilters, isZoomedOut]);

  // ── 3. Render Vessels on Cesium Globe (Directional Arrows) ─────────────────
  useEffect(() => {
    const ds = vesselsDataSourceRef.current;
    if (!ds) return;

    ds.entities.removeAll();
    const isMaritime = activeNavTab === 'maritime';
    ds.show = isMaritime && activeFilters.showVessels;

    if (!isMaritime || !activeFilters.showVessels || vessels.length === 0) return;

    ds.entities.suspendEvents();

    for (const v of vessels) {
      const isDark = v.is_dark;
      const isCritical = v.risk_level === 'CRITICAL';
      const isWarning = v.risk_level === 'WARNING';
      const inMpa = v.in_mpa;

      let arrowIcon = ARROW_ICONS.CYAN; // Normal Electric Cyan
      if (isDark || isCritical) {
        arrowIcon = ARROW_ICONS.CRIMSON; // Red
      } else if (isWarning || v.risk_score >= 0.7) {
        arrowIcon = ARROW_ICONS.AMBER; // Amber
      } else if (inMpa) {
        arrowIcon = ARROW_ICONS.PURPLE; // Purple
      }

      // Render as directional navigation arrow billboard
      ds.entities.add({
        name: v.vessel_name || `MMSI: ${v.mmsi}`,
        position: Cartesian3.fromDegrees(v.lon, v.lat, 18),
        billboard: {
          image: arrowIcon,
          rotation: CesiumMath.toRadians(-(v.course_deg ?? 0)),
          width: isCritical ? 20 : 16,
          height: isCritical ? 20 : 16,
          scaleByDistance: new NearFarScalar(1.0e2, 1.4, 8.0e6, 0.65),
        },
        properties: {
          vessel_data: v,
        },
      });
    }

    ds.entities.resumeEvents();
  }, [vessels, activeFilters.showVessels, activeNavTab]);

  // ── 4. Render Zoom-Out Organic Continuous Gradient Heat Map (Image 1) ───
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (heatmapLayerRef.current) {
      viewer.imageryLayers.remove(heatmapLayerRef.current, false);
      heatmapLayerRef.current = null;
    }

    const isMaritime = activeNavTab === 'maritime';
    const shouldShow = isMaritime && isZoomedOut && activeFilters.showVessels;
    if (!shouldShow || vessels.length === 0) return;

    const dataUrl = generateSmoothHeatmapCanvas(vessels);
    if (!dataUrl) return;

    let active = true;
    SingleTileImageryProvider.fromUrl(dataUrl, {
      rectangle: CesiumRectangle.fromDegrees(64.0, 4.0, 96.0, 26.0),
    }).then((provider) => {
      if (!active) return;
      const v = viewerRef.current;
      if (!v || v.isDestroyed()) return;
      const layer = v.imageryLayers.addImageryProvider(provider);
      layer.alpha = 0.82;
      heatmapLayerRef.current = layer;
    }).catch((err) => {
      console.warn('Failed to load traffic heatmap layer:', err);
    });

    return () => {
      active = false;
      const v = viewerRef.current;
      if (v && !v.isDestroyed() && heatmapLayerRef.current) {
        v.imageryLayers.remove(heatmapLayerRef.current, false);
        heatmapLayerRef.current = null;
      }
    };
  }, [vessels, isZoomedOut, activeNavTab, activeFilters.showVessels]);

  // ── 5. Render Oil Spills on Cesium Globe (Blinking in Red - Image 2) ──────
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (spillsDataSourceRef.current) {
      viewer.dataSources.remove(spillsDataSourceRef.current);
      spillsDataSourceRef.current = null;
    }

    if (!activeFilters.showSpillZones || spills.length === 0) return;

    const spillsGeoJSON: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: spills.map((s) => ({
        type: 'Feature',
        geometry: s.geojson_polygon as GeoJSON.Geometry,
        properties: {
          spill_data: s,
        },
      })),
    };

    GeoJsonDataSource.load(spillsGeoJSON, {
      stroke: Color.fromCssColorString('#EF4444'),
      strokeWidth: 3,
      clampToGround: true,
    }).then((ds) => {
      // Dynamic pulsating/blinking red fill for detected hydrocarbon slick
      for (const entity of ds.entities.values) {
        if (entity.polygon) {
          entity.polygon.material = new ColorMaterialProperty(
            new CallbackProperty(() => {
              const alpha = 0.25 + 0.65 * Math.abs(Math.sin(Date.now() / 250));
              return Color.fromCssColorString('#EF4444').withAlpha(alpha);
            }, false)
          );
          entity.polygon.outline = new ConstantProperty(true);
          entity.polygon.outlineColor = new ConstantProperty(Color.fromCssColorString('#FECACA'));
          entity.polygon.outlineWidth = new ConstantProperty(2.5);
        }
      }
      viewer.dataSources.add(ds);
      spillsDataSourceRef.current = ds;
      ds.show = activeFilters.showSpillZones;
    });
  }, [spills, activeFilters.showSpillZones]);

  // ── 6. Render Simulated Active Spill (Blinking in Red - Image 2) ──────────
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (activeSpillDataSourceRef.current) {
      viewer.dataSources.remove(activeSpillDataSourceRef.current);
      activeSpillDataSourceRef.current = null;
    }

    if (!activeFilters.showSpillZones || !activeSpill?.geojson_polygon) return;

    const activeGeoJSON: GeoJSON.Feature = {
      type: 'Feature',
      geometry: activeSpill.geojson_polygon as GeoJSON.Geometry,
      properties: {
        spill_data: activeSpill,
      },
    };

    GeoJsonDataSource.load(activeGeoJSON, {
      stroke: Color.fromCssColorString('#EF4444'),
      strokeWidth: 3,
      clampToGround: true,
    }).then((ds) => {
      // Dynamic pulsating/blinking red fill for active oil slick
      for (const entity of ds.entities.values) {
        if (entity.polygon) {
          entity.polygon.material = new ColorMaterialProperty(
            new CallbackProperty(() => {
              const alpha = 0.25 + 0.65 * Math.abs(Math.sin(Date.now() / 250));
              return Color.fromCssColorString('#EF4444').withAlpha(alpha);
            }, false)
          );
          entity.polygon.outline = new ConstantProperty(true);
          entity.polygon.outlineColor = new ConstantProperty(Color.fromCssColorString('#FECACA'));
          entity.polygon.outlineWidth = new ConstantProperty(3);
        }
      }
      viewer.dataSources.add(ds);
      activeSpillDataSourceRef.current = ds;
    });
  }, [activeSpill, activeFilters.showSpillZones]);

  // ── 6. Render Thermal Fire Hotspots ───────────────────────────────────────
  useEffect(() => {
    const ds = hotspotsDataSourceRef.current;
    if (!ds) return;

    ds.entities.removeAll();
    ds.show = activeFilters.showFireHotspots;

    if (!activeFilters.showFireHotspots || hotspots.length === 0) return;

    ds.entities.suspendEvents();

    for (const h of hotspots) {
      let color = Color.fromCssColorString('#A1A1AA');
      if (h.fire_type === 'gas_flare') color = Color.fromCssColorString('#8B5CF6');
      else if (h.fire_type === 'industrial') color = Color.fromCssColorString('#F97316');
      else if (h.fire_type === 'stubble') color = Color.fromCssColorString('#EAB308');
      else if (h.fire_type === 'wildfire') color = Color.fromCssColorString('#EF4444');
      else if (h.fire_type === 'mining') color = Color.fromCssColorString('#6B7280');

      const radius = Math.max(5, Math.min(14, 4 + (h.frp ?? 0) / 100));

      ds.entities.add({
        name: `${h.fire_type} Hotspot`,
        position: Cartesian3.fromDegrees(h.longitude, h.latitude, 10),
        point: {
          pixelSize: radius,
          color: color.withAlpha(0.85),
          outlineColor: Color.fromCssColorString('#060E1C'),
          outlineWidth: 1.5,
        },
        properties: {
          hotspot_data: h,
        },
      });
    }

    ds.entities.resumeEvents();
  }, [hotspots, activeFilters.showFireHotspots]);

  // ── 7. Render INCOIS 72h Ocean Drift Simulation ───────────────────────────
  const activeDriftStep = getActiveDriftStep();

  useEffect(() => {
    const ds = driftCorridorDataSourceRef.current;
    if (!ds) return;

    ds.entities.removeAll();
    ds.show = isDriftSimActive;

    if (!isDriftSimActive || !driftForecast) return;

    // A. Trajectory line
    if (driftForecast.trajectory_points?.length > 1) {
      const linePositions = driftForecast.trajectory_points.map((p) =>
        Cartesian3.fromDegrees(p.lon, p.lat, 20)
      );

      ds.entities.add({
        name: 'drift-trajectory-corridor',
        polyline: {
          positions: linePositions,
          width: 3.0,
          material: new PolylineDashMaterialProperty({
            color: Color.fromCssColorString('#F59E0B'),
            dashLength: 14.0,
          }),
        },
      });
    }

    // B. Active time step polygon
    if (activeDriftStep?.geojson_polygon) {
      const coords = (activeDriftStep.geojson_polygon as any).coordinates[0];
      if (coords?.length) {
        const polyPositions = coords.map((c: number[]) => Cartesian3.fromDegrees(c[0], c[1], 10));

        ds.entities.add({
          name: `drift-step-${activeDriftStep.time_offset_hours}`,
          polygon: {
            hierarchy: polyPositions,
            material: Color.fromCssColorString('#F59E0B').withAlpha(0.45),
            outline: true,
            outlineColor: Color.fromCssColorString('#FCD34D'),
            outlineWidth: 2.5,
          },
        });
      }

      // C. Centroid Pulse Marker
      ds.entities.add({
        name: 'drift-centroid-pulse',
        position: Cartesian3.fromDegrees(
          activeDriftStep.centroid_lon,
          activeDriftStep.centroid_lat,
          35
        ),
        point: {
          pixelSize: 12,
          color: Color.fromCssColorString('#FBBF24'),
          outlineColor: Color.fromCssColorString('#060E1C'),
          outlineWidth: 2,
        },
      });
    }
  }, [isDriftSimActive, driftForecast, activeDriftStep]);

  // ── 8. Visibility updates for MPAs & Demo Tracks ───────────────────────────
  useEffect(() => {
    if (mpasDataSourceRef.current) {
      mpasDataSourceRef.current.show = activeFilters.showMPABoundaries;
    }
    if (demoTracksDataSourceRef.current) {
      demoTracksDataSourceRef.current.show = activeFilters.showVessels;
    }
  }, [activeFilters.showMPABoundaries, activeFilters.showVessels]);

  // ── Quick Camera Jumps ────────────────────────────────────────────────────
  const jumpToWaypoint = (waypoint: typeof SECTOR_WAYPOINTS.ALL_INDIA) => {
    viewerRef.current?.camera.flyTo({
      destination: Cartesian3.fromDegrees(waypoint.longitude, waypoint.latitude, waypoint.height),
      orientation: {
        heading: CesiumMath.toRadians(waypoint.heading),
        pitch: CesiumMath.toRadians(waypoint.pitch),
        roll: 0,
      },
      duration: 1.8,
    });
  };

  // ── Trigger Oil Spill Simulation / CDSE Sync ──────────────────────────────
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

        // Fly 3D camera to Bombay High spill
        viewerRef.current?.camera.flyTo({
          destination: Cartesian3.fromDegrees(data.lon, data.lat, 180000),
          orientation: {
            pitch: CesiumMath.toRadians(-60),
          },
          duration: 2.0,
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

  return (
    <div className="relative w-full h-full overflow-hidden select-none bg-[#040812]">
      {/* ── 3D WebGL Cesium Container ── */}
      <div ref={containerRef} className="w-full h-full" />

      {/* ── Top-Right Tactical Camera Controls ── */}
      <div className="absolute top-3 right-3 z-30 flex flex-col gap-1.5 pointer-events-auto">
        <button
          type="button"
          onClick={() => viewerRef.current?.camera.zoomIn(viewerRef.current.camera.positionCartographic.height * 0.35)}
          className="w-8 h-8 rounded-lg bg-navy-900/90 border border-navy-500 hover:border-cyan-400 text-cyan-300 font-mono font-bold flex items-center justify-center shadow-lg transition-all"
          title="Zoom In"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => viewerRef.current?.camera.zoomOut(viewerRef.current.camera.positionCartographic.height * 0.45)}
          className="w-8 h-8 rounded-lg bg-navy-900/90 border border-navy-500 hover:border-cyan-400 text-cyan-300 font-mono font-bold flex items-center justify-center shadow-lg transition-all"
          title="Zoom Out"
        >
          −
        </button>
        <button
          type="button"
          onClick={() => {
            if (!viewerRef.current) return;
            const cam = viewerRef.current.camera;
            cam.flyTo({
              destination: cam.position,
              orientation: {
                heading: 0,
                pitch: cam.pitch,
                roll: 0,
              },
              duration: 1.0,
            });
          }}
          className="w-8 h-8 rounded-lg bg-navy-900/90 border border-navy-500 hover:border-cyan-400 text-cyan-300 font-mono text-[11px] font-bold flex items-center justify-center shadow-lg transition-all"
          title="Reset North"
        >
          ▲ N
        </button>
        <button
          type="button"
          onClick={() => {
            if (!viewerRef.current) return;
            const cam = viewerRef.current.camera;
            const newPitch = cam.pitch > -1.0 ? CesiumMath.toRadians(-88) : CesiumMath.toRadians(-45);
            cam.flyTo({
              destination: cam.position,
              orientation: {
                heading: cam.heading,
                pitch: newPitch,
                roll: 0,
              },
              duration: 1.2,
            });
          }}
          className="w-8 h-8 rounded-lg bg-navy-900/90 border border-navy-500 hover:border-cyan-400 text-teal-300 font-mono text-[9px] font-bold flex items-center justify-center shadow-lg transition-all"
          title="Toggle 3D Tilt Horizon"
        >
          3D
        </button>
      </div>

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
              width: '250px',
            }}
          >
            {/* ── Tab 1: MARITIME CONTROLS ── */}
            {activeNavTab === 'maritime' && (
              <>
                {/* Quick Sector Jumps */}
                <div>
                  <div className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                    <Compass className="w-3 h-3 text-cyan-400" />
                    <span>Maritime Sectors (3D)</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[10px] font-mono">
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.ALL_INDIA)}
                      className="px-1.5 py-1 rounded bg-navy-800 text-gray-300 hover:text-white hover:bg-navy-700 text-left truncate flex items-center gap-1"
                    >
                      <MapPin className="w-2.5 h-2.5 text-cyan-400 shrink-0" />
                      <span className="truncate">All India EEZ</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.BOMBAY_HIGH)}
                      className="px-1.5 py-1 rounded bg-navy-800 text-red-300 hover:text-white hover:bg-red-950/60 text-left truncate font-bold flex items-center gap-1"
                    >
                      <Droplets className="w-2.5 h-2.5 text-red-400 shrink-0" />
                      <span className="truncate">Bombay High</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.JNPT_APPROACH)}
                      className="px-1.5 py-1 rounded bg-navy-800 text-gray-300 hover:text-white hover:bg-navy-700 text-left truncate flex items-center gap-1"
                    >
                      <Navigation className="w-2.5 h-2.5 text-teal-400 shrink-0" />
                      <span className="truncate">JNPT Approach</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.KUTCH_SANCTUARY)}
                      className="px-1.5 py-1 rounded bg-navy-800 text-purple-300 hover:text-white hover:bg-purple-950/60 text-left truncate flex items-center gap-1"
                    >
                      <Shield className="w-2.5 h-2.5 text-purple-400 shrink-0" />
                      <span className="truncate">Kutch Sanctuary</span>
                    </button>
                  </div>
                </div>

                {/* Layer Controls (Maritime Only - Fire/Thermal removed) */}
                <div className="flex flex-col gap-1.5 text-xs pt-2 border-t border-navy-700">
                  <div className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-widest mb-0.5 flex items-center justify-between">
                    <span>MARITIME LAYERS</span>
                    <span className="text-[8px] text-cyan-400 font-mono">
                      {isZoomedOut ? '● HEAT MAP VIEW' : '● TACTICAL ARROWS'}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => toggleFilter('showVessels')}
                    className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
                  >
                    <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                      <Navigation className="w-3.5 h-3.5 text-cyan-400" />
                      <span>AIS Vessels (3D Arrows)</span>
                    </span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        activeFilters.showVessels
                          ? 'text-navy-950 bg-cyan-400'
                          : 'text-gray-500 bg-navy-800'
                      }`}
                    >
                      {activeFilters.showVessels ? 'ON' : 'OFF'}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleFilter('showSpillZones')}
                    className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
                  >
                    <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                      <Droplets className="w-3.5 h-3.5 text-red-400" />
                      <span>Spill Zones (Blinking Slick)</span>
                    </span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        activeFilters.showSpillZones
                          ? 'text-white bg-red-500'
                          : 'text-gray-500 bg-navy-800'
                      }`}
                    >
                      {activeFilters.showSpillZones ? 'ON' : 'OFF'}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleFilter('showMPABoundaries')}
                    className="flex items-center justify-between cursor-pointer select-none py-1 px-1.5 rounded hover:bg-white/5 transition-colors w-full"
                  >
                    <span className="flex items-center gap-1.5 text-[11px] text-gray-200">
                      <Shield className="w-3.5 h-3.5 text-emerald-400" />
                      <span>MPA Zones</span>
                    </span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                        activeFilters.showMPABoundaries
                          ? 'text-navy-950 bg-emerald-400'
                          : 'text-gray-500 bg-navy-800'
                      }`}
                    >
                      {activeFilters.showMPABoundaries ? 'ON' : 'OFF'}
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
                    <Radio className="w-3.5 h-3.5 text-red-400" />
                    <span>{isSimulating ? 'Syncing Sentinel-1C...' : 'Sync SAR Orbit #142'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleDriftSim()}
                    className="w-full py-1.5 px-2 rounded text-[11px] font-mono font-bold tracking-wide flex items-center justify-center gap-1.5 transition-all border"
                    style={{
                      background: isDriftSimActive
                        ? 'rgba(245, 158, 11, 0.25)'
                        : 'rgba(15, 31, 61, 0.8)',
                      borderColor: isDriftSimActive ? 'var(--amber-500)' : 'var(--navy-500)',
                      color: isDriftSimActive ? 'var(--amber-300)' : 'var(--text-secondary)',
                    }}
                  >
                    <Waves className="w-3.5 h-3.5 text-amber-400" />
                    <span>{isDriftSimActive ? 'Close Drift HUD' : 'INCOIS 72h Drift Sim'}</span>
                  </button>
                </div>
              </>
            )}

            {/* ── Tab 2: THERMAL ZONE CONTROLS (Only Fire/Thermal toggle) ── */}
            {activeNavTab === 'thermal' && (
              <>
                <div>
                  <div className="text-[9px] font-mono font-bold text-amber-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                    <Flame className="w-3 h-3 text-amber-400" />
                    <span>THERMAL ZONE INTELLIGENCE</span>
                  </div>
                  <p className="text-[10px] text-gray-400 leading-tight">
                    NASA VIIRS active thermal hotspots and industrial gas flaring classification.
                  </p>
                </div>

                {/* Only this toggle in thermal zone */}
                <div className="pt-2 border-t border-navy-700 flex flex-col gap-2">
                  <div className="flex items-center justify-between p-2 rounded bg-navy-800/90 border border-amber-500/40">
                    <div className="flex items-center gap-2">
                      <Flame className="w-4 h-4 text-amber-400" />
                      <div>
                        <div className="text-[11px] font-bold text-white">Fire / Thermal Layer</div>
                        <div className="text-[9px] text-amber-300/80">174 Active Hotspots</div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleFilter('showFireHotspots')}
                      className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold transition-all shadow ${
                        activeFilters.showFireHotspots
                          ? 'bg-amber-400 text-navy-950 font-bold'
                          : 'bg-navy-900 text-gray-400 border border-navy-600'
                      }`}
                    >
                      {activeFilters.showFireHotspots ? 'ON' : 'OFF'}
                    </button>
                  </div>

                  <div className="p-2 rounded bg-navy-900/60 border border-navy-700 text-[10px] font-mono flex flex-col gap-1 text-gray-300">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Sensor:</span>
                      <span className="text-amber-300 font-bold">NASA VIIRS NRT</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Max FRP:</span>
                      <span className="text-red-400 font-bold">482 MW</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Classes:</span>
                      <span className="text-cyan-300">Industrial, Flare, Stubble</span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* ── Tab 3: GEOLOGICAL CONTROLS (Landslide Danger Zones) ── */}
            {activeNavTab === 'geological' && (
              <>
                <div>
                  <div className="text-[9px] font-mono font-bold text-rose-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5">
                    <Mountain className="w-3 h-3 text-rose-400" />
                    <span>GEOLOGICAL HAZARD ZONES</span>
                  </div>
                  <p className="text-[10px] text-gray-400 leading-tight">
                    Critical landslide and debris-flow risk zones mapped across India (GSI/NDMA).
                  </p>
                </div>

                <div className="flex flex-col gap-1.5 pt-2 border-t border-navy-700">
                  <div className="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-widest mb-0.5">
                    LANDSLIDE SECTORS
                  </div>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.CHAMOLI_LANDSLIDE)}
                    className="px-2 py-1.5 rounded bg-navy-800/90 hover:bg-rose-950/60 text-left border border-navy-600 hover:border-rose-500/60 transition-all flex items-center justify-between"
                  >
                    <div>
                      <div className="text-[11px] font-bold text-rose-300">Chamoli &amp; Joshimath</div>
                      <div className="text-[9px] text-gray-400">Uttarakhand · Flash Rockslide</div>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      CRITICAL
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.WAYANAD_LANDSLIDE)}
                    className="px-2 py-1.5 rounded bg-navy-800/90 hover:bg-rose-950/60 text-left border border-navy-600 hover:border-rose-500/60 transition-all flex items-center justify-between"
                  >
                    <div>
                      <div className="text-[11px] font-bold text-rose-300">Wayanad Meppadi</div>
                      <div className="text-[9px] text-gray-400">Kerala · Monsoon Mudslide</div>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      CRITICAL
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.KULLU_LANDSLIDE)}
                    className="px-2 py-1.5 rounded bg-navy-800/90 hover:bg-amber-950/60 text-left border border-navy-600 hover:border-amber-500/60 transition-all flex items-center justify-between"
                  >
                    <div>
                      <div className="text-[11px] font-bold text-amber-300">Kullu-Manali Valley</div>
                      <div className="text-[9px] text-gray-400">Himachal · Bank Slumping</div>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      HIGH
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.SIKKIM_LANDSLIDE)}
                    className="px-2 py-1.5 rounded bg-navy-800/90 hover:bg-rose-950/60 text-left border border-navy-600 hover:border-rose-500/60 transition-all flex items-center justify-between"
                  >
                    <div>
                      <div className="text-[11px] font-bold text-rose-300">Sikkim Teesta Basin</div>
                      <div className="text-[9px] text-gray-400">Sikkim · Moraine Dam Failure</div>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      CRITICAL
                    </span>
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* ── Geological Hazard Zone Popup (when a danger zone is clicked) ── */}
      {selectedHazardZone && (
        <div className="absolute bottom-12 left-4 z-30 pointer-events-auto max-w-sm p-4 rounded-lg bg-navy-900/95 border border-rose-500/60 shadow-2xl backdrop-blur-md animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between border-b border-navy-700 pb-2 mb-2">
            <div className="flex items-center gap-2">
              <Mountain className="w-4 h-4 text-rose-400" />
              <span className="font-bold text-sm text-white">{selectedHazardZone.name}</span>
            </div>
            <button
              type="button"
              onClick={() => setSelectedHazardZone(null)}
              className="text-gray-400 hover:text-white font-bold px-1"
            >
              ✕
            </button>
          </div>
          <div className="flex flex-col gap-1.5 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-gray-400">Risk Level:</span>
              <span className="text-rose-400 font-bold px-1.5 py-0.2 rounded bg-rose-950/60 border border-rose-500/40">
                {selectedHazardZone.risk_level}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Hazard Type:</span>
              <span className="text-amber-300">{selectedHazardZone.hazard_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Monitoring Agency:</span>
              <span className="text-cyan-300">{selectedHazardZone.monitoring_agency}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Slope Gradient:</span>
              <span className="text-white">{selectedHazardZone.slope_angle}</span>
            </div>
            <p className="text-[11px] text-gray-300 mt-1 leading-normal font-sans border-t border-navy-800 pt-1.5">
              {selectedHazardZone.description}
            </p>
          </div>
        </div>
      )}

      {/* ── Selected Vessel Interactive Popup (Anchored in 3D Screen Space) ── */}
      {selectedVessel && popupScreenPos && (
        <div
          className="satvigil-cesium-popup"
          style={{
            left: `${popupScreenPos.x}px`,
            top: `${popupScreenPos.y}px`,
          }}
        >
          <div
            className="p-3.5 rounded-lg shadow-2xl text-xs flex flex-col gap-2 min-w-[260px] animate-in fade-in zoom-in-95 duration-100"
            style={{
              background: 'var(--navy-800)',
              border: '1px solid var(--navy-400)',
              color: 'var(--text-primary)',
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between border-b pb-1.5"
              style={{ borderColor: 'var(--navy-600)' }}
            >
              <span className="font-bold text-sm tracking-wide text-white">
                {selectedVessel.vessel_name}
              </span>
              <div className="flex items-center gap-2">
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
                <button
                  type="button"
                  onClick={() => selectVessel(null)}
                  className="text-gray-400 hover:text-white text-xs font-bold leading-none px-1"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Telemetry Grid */}
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
              <span
                className="font-bold"
                style={{ color: selectedVessel.risk_score > 0.7 ? '#EF4444' : '#10B981' }}
              >
                {(selectedVessel.risk_score * 100).toFixed(0)}%
              </span>

              <span style={{ color: 'var(--text-secondary)' }}>AIS Status:</span>
              <span className={selectedVessel.is_dark ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                {selectedVessel.is_dark
                  ? `DARK (${selectedVessel.ais_gap_minutes}m)`
                  : 'ACTIVE'}
              </span>
            </div>

            {/* Live Satellite Reconnaissance Viewport */}
            <div
              className="relative rounded border overflow-hidden mt-1"
              style={{ borderColor: 'var(--navy-500)', background: '#050c18' }}
            >
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
                    onClick={(e) => {
                      e.stopPropagation();
                      setVesselSensor('sentinel1');
                    }}
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
                    onClick={(e) => {
                      e.stopPropagation();
                      setVesselSensor('sentinel2');
                    }}
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
                    const target = e.currentTarget;
                    if (!target.src.includes('/api/v1/satellite/vessel-image')) {
                      target.src = `/api/v1/satellite/vessel-image?lat=${selectedVessel.lat}&lon=${selectedVessel.lon}&mmsi=${selectedVessel.mmsi}&sensor=${vesselSensor}&course=${selectedVessel.course_deg ?? 0}&speed=${selectedVessel.speed_knots ?? 12}`;
                    }
                  }}
                />
                <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-1.5">
                  <div className="flex justify-between text-[7.5px] font-mono text-teal-400/90 drop-shadow">
                    <span>10m/px · SWATH 250km</span>
                    <span>
                      {selectedVessel.lat.toFixed(3)}°N, {selectedVessel.lon.toFixed(3)}°E
                    </span>
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
              <span>▶ Replay AIS Track (3D)</span>
            </button>
          </div>
        </div>
      )}

      {/* ── Hotspot Hover Tooltip ── */}
      {hoveredHotspot && hoveredHotspotPos && (
        <div
          className="absolute z-40 pointer-events-none -translate-x-1/2 -translate-y-full mb-2"
          style={{
            left: `${hoveredHotspotPos.x}px`,
            top: `${hoveredHotspotPos.y}px`,
          }}
        >
          <div className="p-2 rounded bg-gray-900 border border-amber-500 text-white font-mono text-[10px] shadow-xl backdrop-blur-md">
            <div className="font-bold text-amber-400 uppercase">
              {hoveredHotspot.fire_type} Hotspot
            </div>
            <div>FRP: {(hoveredHotspot.frp ?? 0).toFixed(1)} MW</div>
            <div>Confidence: {hoveredHotspot.confidence}</div>
          </div>
        </div>
      )}

      {/* ── Vessel Track Playback Entity Layer ── */}
      {showTrackPlayer && trackVesselId && (
        <VesselTrackPlayer
          vesselId={trackVesselId}
          viewer={viewerRef.current}
          onTrackLoaded={(loadedTrack) => {
            setVesselTrack(loadedTrack);
            if (loadedTrack.track_points.length > 0) {
              const p0 = loadedTrack.track_points[0];
              viewerRef.current?.camera.flyTo({
                destination: Cartesian3.fromDegrees(p0.lon, p0.lat, 120000),
                orientation: {
                  pitch: CesiumMath.toRadians(-60),
                },
                duration: 1.5,
              });
            }
          }}
          onFrameChange={(_point, idx) => setTrackFrame(idx)}
        />
      )}

      {/* ── Playback Controls Panel ── */}
      {showTrackPlayer && (
        <TrackPlaybackControls
          track={vesselTrack}
          isPlaying={trackIsPlaying}
          frameIndex={trackFrame}
          speed={trackSpeed}
          onPlay={() => setTrackIsPlaying(true)}
          onPause={() => setTrackIsPlaying(false)}
          onReset={() => {
            setTrackIsPlaying(false);
            setTrackFrame(0);
          }}
          onSpeedChange={setTrackSpeed}
          onSeek={setTrackFrame}
          onClose={() => {
            setShowTrackPlayer(false);
            setTrackIsPlaying(false);
          }}
        />
      )}

      {/* ── SAR Image Popup (spill click) ── */}
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
