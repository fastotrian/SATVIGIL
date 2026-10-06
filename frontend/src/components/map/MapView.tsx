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
import { LandslideConstraintDashboard } from '../geological/LandslideConstraintDashboard';
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
  ImageMaterialProperty,
  ConstantProperty,
  Rectangle as CesiumRectangle,
  SingleTileImageryProvider,
  ImageryLayer,
  defined,
  HeightReference,
  PropertyBag,
  LabelStyle,
  VerticalOrigin,
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
  Activity,
} from 'lucide-react';

import { useAlertStore } from '../../store/alertStore';
import { RISK_COLORS } from '../../constants/riskColors';
import { DEFAULT_BOMBAY_HIGH_SPILL } from '../../data/seedMaritimeData';
import { DEFAULT_HOTSPOTS } from '../../data/seedThermalData';
import type { Vessel, SpillEvent, VesselTrack } from '../../types/maritime';
import { isPointInIndiaOceanicZone } from '../../utils/geoBounds';
import { getVesselSatelliteApiUrl, generateTacticalSatelliteDataUrl } from '../../utils/satelliteImage';
import type { ThermalHotspot } from '../../types/fire';
import { VesselTrackPlayer, TrackPlaybackControls } from './VesselTrackPlayer';
import { SpillSARPopup } from './SpillSARPopup';
import { SpillDriftController } from './SpillDriftController';
import { HotspotSatellitePopup } from './HotspotSatellitePopup';
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

// Pre-generated 256x256 soft radial alpha gradient for smooth GPU heatmaps
const SOFT_GRADIENT_IMAGE_DATA_URL: string = (() => {
  if (typeof document === 'undefined') return '';
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  if (!ctx) return '';
  const grad = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, 'rgba(255, 255, 255, 1.0)');
  grad.addColorStop(0.20, 'rgba(255, 255, 255, 0.92)');
  grad.addColorStop(0.48, 'rgba(255, 255, 255, 0.60)');
  grad.addColorStop(0.78, 'rgba(255, 255, 255, 0.18)');
  grad.addColorStop(1.0, 'rgba(255, 255, 255, 0.0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 256, 256);
  return canvas.toDataURL('image/png');
})();

// ── Smooth Organic Marine Traffic Heatmap Canvas Generator ──
// - Low vessel density: Green
// - High vessel density: Yellow
// - Bombay High oil spill incident zone: Ambient Yellow halo (dynamic blinking red & yellow handled by entity layer)
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

  // 1. Calculate local vessel density to differentiate less vs more
  const neighborCounts: number[] = new Array(vessels.length).fill(0);
  for (let i = 0; i < vessels.length; i++) {
    for (let j = i + 1; j < vessels.length; j++) {
      const dLon = vessels[i].lon - vessels[j].lon;
      const dLat = vessels[i].lat - vessels[j].lat;
      if (dLon * dLon + dLat * dLat < 1.44) {
        neighborCounts[i]++;
        neighborCounts[j]++;
      }
    }
  }

  // 2. Areas with fewer vessels: GREEN
  for (let i = 0; i < vessels.length; i++) {
    const v = vessels[i];
    if (v.lon < minLon || v.lon > maxLon || v.lat < minLat || v.lat > maxLat) continue;
    const { x, y } = project(v.lon, v.lat);
    const count = neighborCounts[i];

    const radius = 70 + Math.min(count * 5, 40);
    const alpha = count <= 1 ? 0.48 : 0.30;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
    grad.addColorStop(0, `rgba(16, 185, 129, ${alpha})`);
    grad.addColorStop(0.45, 'rgba(5, 150, 105, 0.22)');
    grad.addColorStop(0.8, 'rgba(4, 120, 87, 0.06)');
    grad.addColorStop(1, 'rgba(4, 120, 87, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  // 3. Areas with more vessels: YELLOW
  for (let i = 0; i < vessels.length; i++) {
    const v = vessels[i];
    if (v.lon < minLon || v.lon > maxLon || v.lat < minLat || v.lat > maxLat) continue;
    const count = neighborCounts[i];
    if (count >= 2) {
      const { x, y } = project(v.lon, v.lat);
      const intensity = Math.min(1.0, count / 6.0);
      const radius = 45 + Math.min(count * 6, 45);
      const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
      grad.addColorStop(0, `rgba(234, 179, 8, ${0.45 + 0.35 * intensity})`);
      grad.addColorStop(0.45, `rgba(202, 138, 4, ${0.25 + 0.20 * intensity})`);
      grad.addColorStop(0.8, 'rgba(161, 98, 7, 0.08)');
      grad.addColorStop(1, 'rgba(161, 98, 7, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // 4. In "that specific region" (Bombay High Oil Spill Zone & Blackout Corridor):
  // Warm yellow ambient traffic halo on the base tile (active blinking red & yellow is driven by dynamic entity layer)
  const incidentPoints = [
    { lon: 71.50, lat: 19.20, r: 85 }, // Bombay High slick centroid
    { lon: 71.45, lat: 19.15, r: 75 }, // dark gap boundary
    { lon: 71.60, lat: 19.45, r: 70 }, // corridor north
    { lon: 71.30, lat: 18.85, r: 70 }, // corridor south
    { lon: 71.72, lat: 19.65, r: 65 },
  ];

  for (const pt of incidentPoints) {
    const { x, y } = project(pt.lon, pt.lat);
    const grad = ctx.createRadialGradient(x, y, 0, x, y, pt.r);
    grad.addColorStop(0, 'rgba(234, 179, 8, 0.65)');
    grad.addColorStop(0.45, 'rgba(245, 158, 11, 0.40)');
    grad.addColorStop(0.8, 'rgba(217, 119, 6, 0.12)');
    grad.addColorStop(1, 'rgba(217, 119, 6, 0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(x, y, pt.r, 0, Math.PI * 2);
    ctx.fill();
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
  const [isAnalyzingLandslide, setIsAnalyzingLandslide] = useState(false);
  const [landslideAnalysisResult, setLandslideAnalysisResult] = useState<any | null>(null);

  // GFW vessel track playback state
  const [showTrackPlayer, setShowTrackPlayer] = useState(false);
  const [trackVesselId, setTrackVesselId] = useState<string | null>(null);
  const [vesselTrack, setVesselTrack] = useState<VesselTrack | null>(null);
  const [trackFrame, setTrackFrame] = useState(0);
  const [trackIsPlaying, setTrackIsPlaying] = useState(false);
  const [trackSpeed, setTrackSpeed] = useState(3);

  const [hotspots, setHotspots] = useState<ThermalHotspot[]>(DEFAULT_HOTSPOTS);
  const [thermalCategoryFilter, setThermalCategoryFilter] = useState<string>('all');
  const [hoveredHotspot, setHoveredHotspot] = useState<ThermalHotspot | null>(null);
  const [hoveredHotspotPos, setHoveredHotspotPos] = useState<{ x: number; y: number } | null>(null);
  const [selectedHotspot, setSelectedHotspot] = useState<ThermalHotspot | null>(null);

  const filteredHotspots = useMemo(() => {
    // Strictly filter out any thermal hotspots located in the oceanic / marine zone
    const landHotspots = hotspots.filter(
      (h) => !isPointInIndiaOceanicZone(h.latitude, h.longitude)
    );
    if (thermalCategoryFilter === 'all') return landHotspots;
    if (thermalCategoryFilter === 'cpcb') return landHotspots.filter((h) => h.near_cpcb_cluster);
    return landHotspots.filter((h) => h.fire_type === thermalCategoryFilter);
  }, [hotspots, thermalCategoryFilter]);

  const thermalCounts = useMemo(() => {
    const counts = { industrial: 0, wildfire: 0, stubble: 0, gas_flare: 0, mining: 0, cpcb: 0 };
    for (const h of hotspots) {
      if (isPointInIndiaOceanicZone(h.latitude, h.longitude)) continue;
      if (h.fire_type && h.fire_type in counts) {
        counts[h.fire_type as keyof typeof counts]++;
      }
      if (h.near_cpcb_cluster) counts.cpcb++;
    }
    return counts;
  }, [hotspots]);

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

  const handleAnalyzeLandslide = async () => {
    if (!selectedHazardZone) return;
    setIsAnalyzingLandslide(true);
    setLandslideAnalysisResult(null);

    // Find the matching feature in the GeoJSON to get its coordinates
    const feature = INDIA_GEOLOGICAL_GEOJSON.features.find((f: any) => f.properties.id === selectedHazardZone.id);
    const coordinates = feature && feature.geometry.type === 'Polygon' 
      ? feature.geometry.coordinates[0] 
      : [
          [79.45, 30.35],
          [79.60, 30.35],
          [79.60, 30.60],
          [79.45, 30.60],
          [79.45, 30.35]
        ];

    try {
      const resp = await fetch('/api/v1/landslide/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          coordinates: coordinates,
          detection_date: new Date().toISOString().split('T')[0],
          detection_confidence: 0.92
        })
      });
      if (resp.ok) {
        const data = await resp.json();
        setLandslideAnalysisResult(data);
      } else {
        console.error('Failed to analyze landslide risk');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsAnalyzingLandslide(false);
    }
  };

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
      if (!viewer || viewer.isDestroyed()) return; viewer.dataSources.add(ds);
      mpasDataSourceRef.current = ds;
      ds.show = activeFilters.showMPABoundaries;
    });

    GeoJsonDataSource.load(DEMO_TRACKS_GEOJSON, {
      stroke: Color.fromCssColorString('#F59E0B'),
      strokeWidth: 4,
      clampToGround: true,
    }).then((ds) => {
      // Clean static trajectory corridor (hidden while zoomed out, visible when zoomed in)
      for (const entity of ds.entities.values) {
        if (entity.polyline) {
          entity.polyline.material = new ColorMaterialProperty(
            Color.fromCssColorString('#F59E0B').withAlpha(0.70)
          );
          entity.polyline.width = new ConstantProperty(3.0);
          entity.polyline.clampToGround = new ConstantProperty(true);
        }
        entity.properties = entity.properties || new PropertyBag();
        entity.properties.addProperty('spill_corridor', new ConstantProperty(true));
      }
      if (!viewer || viewer.isDestroyed()) return; viewer.dataSources.add(ds);
      demoTracksDataSourceRef.current = ds;
      const camHeight = viewer.camera.positionCartographic?.height ?? 3000000;
      const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
      ds.show = activeFilters.showVessels && heatFactor < 0.98;
    });

    // High-visibility dynamic heat gradient at Bombay High (19.20°N, 71.50°E)
    // Pulsing & blinking between RED and YELLOW across the incident region
    viewer.entities.add({
      name: 'bombay-high-blinking-gradient-halo',
      position: Cartesian3.fromDegrees(71.50, 19.20, 10),
      ellipse: {
        show: new CallbackProperty(() => {
          const storeState = useAlertStore.getState();
          if (storeState.activeNavTab !== 'maritime' || !storeState.activeFilters.showVessels) {
            return false;
          }
          const camHeight = viewer.camera.positionCartographic?.height ?? 3000000;
          const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
          return heatFactor > 0.01;
        }, false),
        semiMajorAxis: new ConstantProperty(125000), // 125 km radius outer halo
        semiMinorAxis: new ConstantProperty(125000),
        heightReference: new ConstantProperty(HeightReference.CLAMP_TO_GROUND),
        material: new ImageMaterialProperty({
          image: SOFT_GRADIENT_IMAGE_DATA_URL,
          color: new CallbackProperty(() => {
            const camHeight = viewer.camera.positionCartographic?.height ?? 3000000;
            const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
            const isRed = Math.sin(Date.now() / 240) > 0;
            const baseColor = isRed
              ? Color.fromCssColorString('#EF4444')
              : Color.fromCssColorString('#F59E0B');
            const targetAlpha = (isRed ? 0.88 : 0.82) * Math.max(0, heatFactor);
            return new Color(baseColor.red, baseColor.green, baseColor.blue, targetAlpha);
          }, false),
          transparent: true,
        }),
      },
      properties: {
        spill_beacon: true,
        spill_data: DEFAULT_BOMBAY_HIGH_SPILL,
      },
    });

    viewer.entities.add({
      name: 'bombay-high-blinking-gradient-core',
      position: Cartesian3.fromDegrees(71.50, 19.20, 20),
      ellipse: {
        show: new CallbackProperty(() => {
          const storeState = useAlertStore.getState();
          if (storeState.activeNavTab !== 'maritime' || !storeState.activeFilters.showVessels) {
            return false;
          }
          const camHeight = viewer.camera.positionCartographic?.height ?? 3000000;
          const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
          return heatFactor > 0.01;
        }, false),
        semiMajorAxis: new ConstantProperty(75000), // 75 km radius intense core
        semiMinorAxis: new ConstantProperty(75000),
        heightReference: new ConstantProperty(HeightReference.CLAMP_TO_GROUND),
        material: new ImageMaterialProperty({
          image: SOFT_GRADIENT_IMAGE_DATA_URL,
          color: new CallbackProperty(() => {
            const camHeight = viewer.camera.positionCartographic?.height ?? 3000000;
            const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
            const isRed = Math.sin(Date.now() / 240) > 0;
            const baseColor = isRed
              ? Color.fromCssColorString('#DC2626')
              : Color.fromCssColorString('#FEF08A');
            const targetAlpha = (isRed ? 0.96 : 0.92) * Math.max(0, heatFactor);
            return new Color(baseColor.red, baseColor.green, baseColor.blue, targetAlpha);
          }, false),
          transparent: true,
        }),
      },
      properties: {
        spill_beacon: true,
        spill_data: DEFAULT_BOMBAY_HIGH_SPILL,
      },
    });


    // Setup Geological Hazard Danger Zones
    GeoJsonDataSource.load(INDIA_GEOLOGICAL_GEOJSON, {
      stroke: Color.fromCssColorString('#EF4444'),
      fill: Color.fromCssColorString('#EF4444').withAlpha(0.28),
      strokeWidth: 2.5,
      clampToGround: true,
    }).then((ds) => {
      if (!viewer || viewer.isDestroyed()) return; viewer.dataSources.add(ds);
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

        // Clicked the oil spill, trajectory corridor, or pulsing hazard beacon: ZOOM IN!
        const isSpillClick =
          (entity.properties && (
            entity.properties.hasProperty('spill_data') ||
            entity.properties.hasProperty('spill_beacon') ||
            entity.properties.hasProperty('spill_corridor') ||
            (entity.properties.hasProperty('vessel_mmsi') &&
              entity.properties.getValue(viewer.clock.currentTime).vessel_mmsi === '419082341')
          )) ||
          (entity.name && (
            entity.name.includes('spill') ||
            entity.name.includes('drift') ||
            entity.name.includes('corridor') ||
            entity.name.includes('beacon')
          ));

        if (isSpillClick) {
          const s = (entity.properties?.hasProperty('spill_data')
            ? entity.properties.getValue(viewer.clock.currentTime).spill_data
            : DEFAULT_BOMBAY_HIGH_SPILL) as SpillEvent;

          // 1. Smoothly fly camera to zoom in on Bombay High spill (altitude ~160,000m) centered exactly at target
          viewer.camera.flyTo({
            destination: Cartesian3.fromDegrees(71.50, 19.20, 160000),
            orientation: {
              heading: CesiumMath.toRadians(0),
              pitch: CesiumMath.toRadians(-88),
              roll: 0,
            },
            duration: 1.8,
          });

          // 2. Open SAR Spill Popup
          setSarPopupSpill(s);
          setSarPopupScreenPos({ x: click.position.x || window.innerWidth / 2, y: click.position.y || window.innerHeight / 2 });
          setSelectedHazardZone(null);

          // 3. Highlight culprit vessel MT GUJARAT PRIDE
          const culprit = vessels.find((v) => v.mmsi === '419082341');
          if (culprit) {
            selectVessel(culprit);
          }
          return;
        }

        // Clicked a vessel
        if (entity.properties && entity.properties.hasProperty('vessel_data')) {
          const v = entity.properties.getValue(viewer.clock.currentTime).vessel_data as Vessel;
          selectVessel(v);
          setSarPopupSpill(null);
          setSelectedHazardZone(null);

          if (v.mmsi === '419082341') {
            // Also zoom in on Bombay High spill if suspect vessel clicked centered
            viewer.camera.flyTo({
              destination: Cartesian3.fromDegrees(v.lon, v.lat, 160000),
              orientation: {
                pitch: CesiumMath.toRadians(-88),
              },
              duration: 1.8,
            });
            setSarPopupSpill(DEFAULT_BOMBAY_HIGH_SPILL);
          }
          return;
        }

                  // Clicked a thermal hotspot
          if (entity.properties && entity.properties.hasProperty('hotspot_data')) {
            const h = entity.properties.getValue(viewer.clock.currentTime).hotspot_data as ThermalHotspot;
            setSelectedHotspot(h);
            selectVessel(null);
            setSarPopupSpill(null);
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

    // Dynamic screen coordinate updater & smooth zoom transition cross-fader
    const removePostRenderListener = viewer.scene.postRender.addEventListener(() => {
      const camHeight = viewer.camera.positionCartographic.height;
      const zoomedOut = camHeight > 1600000;
      setIsZoomedOut((prev) => (prev !== zoomedOut ? zoomedOut : prev));

      // Continuous cross-fade factor:
      // heatFactor: 1.0 at >= 2,200,000m (fully zoomed out), 0.0 at <= 900,000m (zoomed in)
      const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));

      // 1. Smoothly fade the oceanic heat gradient (disappears slowly as user zooms in)
      if (heatmapLayerRef.current) {
        const storeState = useAlertStore.getState();
        const isMaritime = storeState.activeNavTab === 'maritime';
        const showVessels = storeState.activeFilters.showVessels;
        if (isMaritime && showVessels && heatFactor > 0.01) {
          heatmapLayerRef.current.show = true;
          try {
            heatmapLayerRef.current.alpha = 0.85 * heatFactor;
          } catch {
            // Ignore if alpha property is non-writable
          }
        } else {
          heatmapLayerRef.current.show = false;
        }
      }

      // 2. Control tactical vessel fleet visibility (hidden when fully zoomed out)
      if (vesselsDataSourceRef.current) {
        const storeState = useAlertStore.getState();
        const isMaritime = storeState.activeNavTab === 'maritime';
        const showVessels = storeState.activeFilters.showVessels;
        // Vessels and trajectory tracks only appear as you zoom in (camHeight < 2,200,000m)
        vesselsDataSourceRef.current.show = isMaritime && showVessels && heatFactor < 0.98;
      }

      if (demoTracksDataSourceRef.current) {
        const storeState = useAlertStore.getState();
        const isMaritime = storeState.activeNavTab === 'maritime';
        const showVessels = storeState.activeFilters.showVessels;
        demoTracksDataSourceRef.current.show = isMaritime && showVessels && heatFactor < 0.98;
      }

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
        const resp = await fetch('/api/v1/maritime/vessels');
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
        const spillResp = await fetch('/api/v1/maritime/spills');
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
        const hotResp = await fetch('/api/v1/fire/hotspots?limit=200');
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
      const camHeight = viewerRef.current?.camera.positionCartographic.height ?? 3000000;
      const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
      vesselsDataSourceRef.current.show = isMaritime && activeFilters.showVessels && heatFactor < 0.98;
    }
    if (spillsDataSourceRef.current) {
      spillsDataSourceRef.current.show = isMaritime && activeFilters.showSpillZones;
    }
    if (mpasDataSourceRef.current) {
      mpasDataSourceRef.current.show = isMaritime && activeFilters.showMPABoundaries;
    }
    if (demoTracksDataSourceRef.current) {
      const camHeight = viewerRef.current?.camera.positionCartographic.height ?? 3000000;
      const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
      demoTracksDataSourceRef.current.show = isMaritime && activeFilters.showVessels && heatFactor < 0.98;
    }
    if (hotspotsDataSourceRef.current) {
      hotspotsDataSourceRef.current.show = isThermal && activeFilters.showFireHotspots;
    }
    if (geologicalDataSourceRef.current) {
      geologicalDataSourceRef.current.show = isGeological && activeFilters.showGeologicalZones;
    }
  }, [activeNavTab, activeFilters, isZoomedOut]);

  // ── Indian Oceanic Zone Filtering & Fleet Volume Control (100 - 200 vessels) ──
  const oceanicVessels = useMemo(() => {
    // 1. Strictly retain only vessels inside the Indian Oceanic Zone
    const valid = vessels.filter((v) => isPointInIndiaOceanicZone(v.lat, v.lon));

    // 2. Prioritize: Suspect vessel (MT GUJARAT PRIDE), dark vessels, critical/high-risk targets
    const prioritized = [...valid].sort((a, b) => {
      const aSuspect = a.mmsi === '419082341' ? 1 : 0;
      const bSuspect = b.mmsi === '419082341' ? 1 : 0;
      if (aSuspect !== bSuspect) return bSuspect - aSuspect;
      const aDark = a.is_dark ? 1 : 0;
      const bDark = b.is_dark ? 1 : 0;
      if (aDark !== bDark) return bDark - aDark;
      return b.risk_score - a.risk_score;
    });

    // 3. Limit to 100 - 200 vessels (target ~140-160 vessels for clear tactical display)
    if (prioritized.length > 160) {
      const critical = prioritized.filter(
        (v) => v.is_dark || v.risk_score >= 0.6 || v.mmsi === '419082341'
      );
      const regular = prioritized.filter((v) => !critical.includes(v));
      const targetCount = 150;
      const neededRegular = Math.max(70, Math.min(130, targetCount - critical.length));
      const stride = Math.max(1, Math.floor(regular.length / neededRegular));
      const sampledRegular = regular
        .filter((_, idx) => idx % stride === 0)
        .slice(0, neededRegular);
      return [...critical, ...sampledRegular];
    }
    return prioritized;
  }, [vessels]);

  // ── 3. Render Vessels on Cesium Globe (Directional Arrows) ─────────────────
  useEffect(() => {
    const ds = vesselsDataSourceRef.current;
    if (!ds) return;

    ds.entities.removeAll();
    const isMaritime = activeNavTab === 'maritime';
    const viewer = viewerRef.current;
    const camHeight = viewer?.camera.positionCartographic.height ?? 3000000;
    const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));

    // Vessels are hidden when zoomed out (heatFactor >= 0.98)
    ds.show = isMaritime && activeFilters.showVessels && heatFactor < 0.98;

    if (!isMaritime || !activeFilters.showVessels || oceanicVessels.length === 0) return;

    ds.entities.suspendEvents();

    for (const v of oceanicVessels) {
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

      // Render as directional navigation arrow billboard with smooth altitude translucency
      ds.entities.add({
        name: v.vessel_name || `MMSI: ${v.mmsi}`,
        position: Cartesian3.fromDegrees(v.lon, v.lat, 18),
        billboard: {
          image: arrowIcon,
          rotation: CesiumMath.toRadians(-(v.course_deg ?? 0)),
          width: isCritical ? 20 : 16,
          height: isCritical ? 20 : 16,
          scaleByDistance: new NearFarScalar(1.0e2, 1.4, 8.0e6, 0.65),
          translucencyByDistance: new NearFarScalar(900000, 1.0, 2200000, 0.0),
        },
        properties: {
          vessel_data: v,
        },
      });
    }

    ds.entities.resumeEvents();
  }, [oceanicVessels, activeFilters.showVessels, activeNavTab]);

  // ── 4. Render Zoom-Out Organic Continuous Gradient Heat Map ───────────────
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (heatmapLayerRef.current) {
      viewer.imageryLayers.remove(heatmapLayerRef.current, false);
      heatmapLayerRef.current = null;
    }

    const isMaritime = activeNavTab === 'maritime';
    const shouldShow = isMaritime && activeFilters.showVessels;
    if (!shouldShow || oceanicVessels.length === 0) return;

    const dataUrl = generateSmoothHeatmapCanvas(oceanicVessels);
    if (!dataUrl) return;

    let active = true;
    SingleTileImageryProvider.fromUrl(dataUrl, {
      rectangle: CesiumRectangle.fromDegrees(64.0, 4.0, 96.0, 26.0),
    }).then((provider) => {
      if (!active) return;
      const v = viewerRef.current;
      if (!v || v.isDestroyed()) return;
      const layer = v.imageryLayers.addImageryProvider(provider);
      // Calculate current alpha from camera height
      const camHeight = v.camera.positionCartographic.height;
      const heatFactor = Math.max(0, Math.min(1, (camHeight - 900000) / (2200000 - 900000)));
      layer.alpha = 0.85 * heatFactor;
      layer.show = heatFactor > 0.01;
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
  }, [oceanicVessels, activeNavTab, activeFilters.showVessels]);

  // ── 5. Render Oil Spills on Cesium Globe (Blinking in Red - Image 2) ──────
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (spillsDataSourceRef.current) {
      if (!viewer.isDestroyed()) viewer.dataSources.remove(spillsDataSourceRef.current);
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
      // Dynamic high-intensity pulsating/blinking red fill for detected hydrocarbon slick
      for (const entity of ds.entities.values) {
        if (entity.polygon) {
          entity.polygon.material = new ColorMaterialProperty(
            new CallbackProperty(() => {
              const flash = Math.sin(Date.now() / 150) > 0;
              const alpha = flash ? 0.95 : 0.30;
              return Color.fromCssColorString('#EF4444').withAlpha(alpha);
            }, false)
          );
          entity.polygon.outline = new ConstantProperty(true);
          entity.polygon.outlineColor = new CallbackProperty(() => {
            const flash = Math.sin(Date.now() / 150) > 0;
            return flash ? Color.WHITE : Color.fromCssColorString('#FECACA');
          }, false);
          entity.polygon.outlineWidth = new ConstantProperty(3.5);
        }
      }
      if (!viewer || viewer.isDestroyed()) return; viewer.dataSources.add(ds);
      spillsDataSourceRef.current = ds;
      ds.show = activeFilters.showSpillZones;
    });
  }, [spills, activeFilters.showSpillZones]);

  // ── 6. Render Simulated Active Spill (Blinking in Red - Image 2) ──────────
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (activeSpillDataSourceRef.current) {
      if (!viewer.isDestroyed()) viewer.dataSources.remove(activeSpillDataSourceRef.current);
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
      // Dynamic high-intensity pulsating/blinking red fill for active oil slick
      for (const entity of ds.entities.values) {
        if (entity.polygon) {
          entity.polygon.material = new ColorMaterialProperty(
            new CallbackProperty(() => {
              const flash = Math.sin(Date.now() / 150) > 0;
              const alpha = flash ? 0.95 : 0.30;
              return Color.fromCssColorString('#EF4444').withAlpha(alpha);
            }, false)
          );
          entity.polygon.outline = new ConstantProperty(true);
          entity.polygon.outlineColor = new CallbackProperty(() => {
            const flash = Math.sin(Date.now() / 150) > 0;
            return flash ? Color.WHITE : Color.fromCssColorString('#FECACA');
          }, false);
          entity.polygon.outlineWidth = new ConstantProperty(3.5);
        }
      }
      if (!viewer || viewer.isDestroyed()) return; viewer.dataSources.add(ds);
      activeSpillDataSourceRef.current = ds;
    });
  }, [activeSpill, activeFilters.showSpillZones]);

  // ── 6. Render Thermal Fire Hotspots ───────────────────────────────────────
  useEffect(() => {
    const ds = hotspotsDataSourceRef.current;
    if (!ds) return;

    ds.entities.removeAll();
    ds.show = activeFilters.showFireHotspots;

    if (!activeFilters.showFireHotspots || filteredHotspots.length === 0) return;

    ds.entities.suspendEvents();

    for (const h of filteredHotspots) {
      let color = Color.fromCssColorString('#9CA3AF');
      if (h.fire_type === 'gas_flare') color = Color.fromCssColorString('#A855F7');
      else if (h.fire_type === 'industrial') color = Color.fromCssColorString('#F97316');
      else if (h.fire_type === 'stubble') color = Color.fromCssColorString('#EAB308');
      else if (h.fire_type === 'wildfire') color = Color.fromCssColorString('#EF4444');
      else if (h.fire_type === 'mining') color = Color.fromCssColorString('#EA580C');

      const radius = Math.max(7, Math.min(16, 6 + (h.frp ?? 0) / 40));

      ds.entities.add({
        name: `${h.fire_type} Hotspot`,
        position: Cartesian3.fromDegrees(h.longitude, h.latitude, 20),
        point: {
          pixelSize: radius,
          color: color.withAlpha(0.95),
          outlineColor: Color.fromCssColorString('#FFFFFF').withAlpha(0.85),
          outlineWidth: 2.0,
          scaleByDistance: new NearFarScalar(1.0e2, 1.4, 8.0e6, 0.85),
          heightReference: HeightReference.CLAMP_TO_GROUND,
        },
        properties: {
          hotspot_data: h,
        },
      });
    }

    ds.entities.resumeEvents();
  }, [filteredHotspots, activeFilters.showFireHotspots]);

  // ── 7. Render INCOIS 72h Ocean Drift Simulation ───────────────────────────
  const activeDriftStep = getActiveDriftStep();

  useEffect(() => {
    const ds = driftCorridorDataSourceRef.current;
    if (!ds) return;

    ds.entities.removeAll();
    ds.show = isDriftSimActive;

    // Toggle static spills visibility so only the active moving drift slick is shown
    if (spillsDataSourceRef.current) {
      spillsDataSourceRef.current.show = !isDriftSimActive && activeFilters.showSpillZones;
    }
    if (activeSpillDataSourceRef.current) {
      activeSpillDataSourceRef.current.show = !isDriftSimActive && activeFilters.showSpillZones;
    }

    if (!isDriftSimActive || !driftForecast) return;

    // A. Trajectory line corridor
    if (driftForecast.trajectory_points?.length > 1) {
      const linePositions = driftForecast.trajectory_points.map((p) =>
        Cartesian3.fromDegrees(p.lon, p.lat, 20)
      );

      ds.entities.add({
        name: 'drift-trajectory-corridor',
        polyline: {
          positions: linePositions,
          width: 3.5,
          material: new PolylineDashMaterialProperty({
            color: Color.fromCssColorString('#F59E0B'),
            dashLength: 16.0,
          }),
        },
      });
    }

    // B. Active moving time-step slick polygon
    if (activeDriftStep?.geojson_polygon) {
      const coords = (activeDriftStep.geojson_polygon as any).coordinates[0];
      if (coords?.length) {
        const polyPositions = coords.map((c: number[]) => Cartesian3.fromDegrees(c[0], c[1], 15));

        ds.entities.add({
          name: `drift-step-${activeDriftStep.time_offset_hours}`,
          polygon: {
            hierarchy: polyPositions,
            material: new ColorMaterialProperty(
              new CallbackProperty(() => {
                const flash = Math.sin(Date.now() / 180) > 0;
                return flash
                  ? Color.fromCssColorString('#EF4444').withAlpha(0.85)
                  : Color.fromCssColorString('#DC2626').withAlpha(0.60);
              }, false)
            ),
            outline: new ConstantProperty(true),
            outlineColor: new ConstantProperty(Color.fromCssColorString('#F59E0B')),
            outlineWidth: new ConstantProperty(3.5),
          },
        });
      }

      // C. Centroid Pulse Marker & Dynamic Telemetry Label
      ds.entities.add({
        name: 'drift-centroid-pulse',
        position: Cartesian3.fromDegrees(
          activeDriftStep.centroid_lon,
          activeDriftStep.centroid_lat,
          35
        ),
        point: {
          pixelSize: 14,
          color: Color.fromCssColorString('#F59E0B'),
          outlineColor: Color.fromCssColorString('#FFFFFF'),
          outlineWidth: 2,
        },
        label: {
          text: `DRIFT T+${activeDriftStep.time_offset_hours}H · ${activeDriftStep.area_km2.toFixed(2)} km²\n${activeDriftStep.centroid_lat.toFixed(3)}°N, ${activeDriftStep.centroid_lon.toFixed(3)}°E`,
          font: 'bold 11px monospace',
          fillColor: Color.fromCssColorString('#FCD34D'),
          outlineColor: Color.fromCssColorString('#0B132B'),
          outlineWidth: 3,
          style: LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: VerticalOrigin.BOTTOM,
          pixelOffset: new Cartesian2(0, -18),
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
      const resp = await fetch('/api/v1/maritime/simulate-spill', {
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

        // Fly 3D camera to Bombay High spill directly centered
        viewerRef.current?.camera.flyTo({
          destination: Cartesian3.fromDegrees(data.lon, data.lat, 180000),
          orientation: {
            pitch: CesiumMath.toRadians(-88),
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

      {/* ── Top-Right Tactical Camera Controls (Positioned cleanly below Threat Feed toggle) ── */}
      <div className="absolute top-12 right-3 z-30 flex flex-col gap-1.5 pointer-events-auto">
        <button
          type="button"
          onClick={() => viewerRef.current?.camera.zoomIn(viewerRef.current.camera.positionCartographic.height * 0.35)}
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 font-mono font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
          title="Zoom In"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => viewerRef.current?.camera.zoomOut(viewerRef.current.camera.positionCartographic.height * 0.45)}
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 font-mono font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
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
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-cyan-500/40 hover:border-cyan-400 text-cyan-300 font-mono text-[11px] font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
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
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-cyan-500/40 hover:border-cyan-400 text-teal-300 font-mono text-[9px] font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
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
          className="self-start px-3 py-1.5 rounded-lg font-mono text-xs font-semibold flex items-center gap-2.5 shadow-2xl border border-cyan-500/50 bg-[#091b38]/90 hover:bg-[#0e2a56]/95 text-cyan-100 hover:text-white transition-all backdrop-blur-md"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#00E5FF]" />
          <span className="tracking-wide">Surveillance Layers</span>
          <span className="text-[10px] text-cyan-300">{isLayerDockOpen ? '▲' : '▼'}</span>
        </button>

        {/* Expanded Defense Command Panel */}
        {isLayerDockOpen && (
          <div className="w-[305px] p-3.5 rounded-xl bg-[#081b38]/90 backdrop-blur-2xl border border-cyan-500/40 border-t-cyan-400/90 shadow-[0_16px_40px_rgba(0,0,0,0.85)] flex flex-col gap-3.5 animate-in fade-in zoom-in-95 duration-150 max-h-[calc(100vh-60px)] overflow-y-auto">
            {/* ── Tab 1: MARITIME CONTROLS ── */}
            {activeNavTab === 'maritime' && (
              <>
                {/* Sector Waypoints */}
                <div>
                  <div className="flex items-center justify-between text-[11px] font-mono tracking-wider text-cyan-300 uppercase font-bold mb-2">
                    <span className="flex items-center gap-1.5">
                      <Compass className="w-3.5 h-3.5 text-cyan-400" />
                      <span>SECTOR WAYPOINTS (3D)</span>
                    </span>
                    <span className="text-[9.5px] text-cyan-400 font-mono font-semibold">WGS-84</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.ALL_INDIA)}
                      className="px-2.5 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-cyan-800/40 hover:border-cyan-400/60 text-left transition-all group"
                    >
                      <div className="text-[12px] font-bold text-white group-hover:text-cyan-200 flex items-center gap-1.5">
                        <MapPin className="w-3 h-3 text-cyan-400 shrink-0" />
                        <span className="truncate">All India EEZ</span>
                      </div>
                      <div className="text-[9.5px] font-mono text-cyan-200/80 pl-4">Overview</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.BOMBAY_HIGH)}
                      className="px-2.5 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-rose-900/40 hover:border-rose-400/60 text-left transition-all group"
                    >
                      <div className="text-[12px] font-bold text-white group-hover:text-rose-200 flex items-center gap-1.5">
                        <Droplets className="w-3 h-3 text-rose-400 shrink-0" />
                        <span className="truncate">Bombay High</span>
                      </div>
                      <div className="text-[9.5px] font-mono text-rose-300 pl-4">Incident Zone</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.JNPT_APPROACH)}
                      className="px-2.5 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-cyan-800/40 hover:border-cyan-400/60 text-left transition-all group"
                    >
                      <div className="text-[12px] font-bold text-white group-hover:text-cyan-200 flex items-center gap-1.5">
                        <Navigation className="w-3 h-3 text-teal-400 shrink-0" />
                        <span className="truncate">JNPT Approach</span>
                      </div>
                      <div className="text-[9.5px] font-mono text-cyan-200/80 pl-4">Port Channel</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.KUTCH_SANCTUARY)}
                      className="px-2.5 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-purple-900/40 hover:border-purple-400/60 text-left transition-all group"
                    >
                      <div className="text-[12px] font-bold text-white group-hover:text-purple-200 flex items-center gap-1.5">
                        <Shield className="w-3 h-3 text-purple-400 shrink-0" />
                        <span className="truncate">Kutch Sanctuary</span>
                      </div>
                      <div className="text-[9.5px] font-mono text-purple-200/80 pl-4">Sanctuary</div>
                    </button>
                  </div>
                </div>

                {/* Layer Hardware-Style Micro-Switches */}
                <div className="flex flex-col gap-2 pt-2.5 border-t border-cyan-900/40">
                  <div className="flex items-center justify-between text-[11px] font-mono tracking-wider text-cyan-300 uppercase font-bold">
                    <span>SURVEILLANCE LAYERS</span>
                    <span className="text-[10px] text-cyan-400 font-mono font-semibold">
                      {isZoomedOut ? 'HEAT GRADIENT' : 'TACTICAL FLEET'}
                    </span>
                  </div>

                  {/* AIS Vessels Switch */}
                  <div
                    onClick={() => toggleFilter('showVessels')}
                    className="flex items-center justify-between py-2 px-2.5 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-cyan-900/40 hover:border-cyan-500/50 transition-all cursor-pointer select-none group"
                  >
                    <div className="flex items-center gap-2.5">
                      <Navigation className="w-4 h-4 text-cyan-400" />
                      <div>
                        <div className="text-[13px] font-semibold text-white group-hover:text-cyan-200">AIS Vessels</div>
                        <div className="text-[10.5px] font-mono text-cyan-200/80">Directional Vectors</div>
                      </div>
                    </div>
                    <div className={`w-8 h-4 rounded-full transition-colors relative flex items-center p-0.5 ${
                      activeFilters.showVessels ? 'bg-cyan-500/30 border border-cyan-400' : 'bg-slate-800 border border-slate-700'
                    }`}>
                      <div className={`w-3 h-3 rounded-full transition-transform ${
                        activeFilters.showVessels ? 'translate-x-4 bg-cyan-400 shadow-[0_0_8px_#00E5FF]' : 'translate-x-0 bg-slate-500'
                      }`} />
                    </div>
                  </div>

                  {/* Spill Zones Switch */}
                  <div
                    onClick={() => toggleFilter('showSpillZones')}
                    className="flex items-center justify-between py-2 px-2.5 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-cyan-900/40 hover:border-rose-500/50 transition-all cursor-pointer select-none group"
                  >
                    <div className="flex items-center gap-2.5">
                      <Droplets className="w-4 h-4 text-rose-400" />
                      <div>
                        <div className="text-[13px] font-semibold text-white group-hover:text-rose-200">Oil Spill Slicks</div>
                        <div className="text-[10.5px] font-mono text-rose-300/90">Sentinel-1 Radar</div>
                      </div>
                    </div>
                    <div className={`w-8 h-4 rounded-full transition-colors relative flex items-center p-0.5 ${
                      activeFilters.showSpillZones ? 'bg-rose-500/30 border border-rose-400' : 'bg-slate-800 border border-slate-700'
                    }`}>
                      <div className={`w-3 h-3 rounded-full transition-transform ${
                        activeFilters.showSpillZones ? 'translate-x-4 bg-rose-400 shadow-[0_0_8px_#EF4444]' : 'translate-x-0 bg-slate-500'
                      }`} />
                    </div>
                  </div>

                  {/* MPA Zones Switch */}
                  <div
                    onClick={() => toggleFilter('showMPABoundaries')}
                    className="flex items-center justify-between py-2 px-2.5 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-cyan-900/40 hover:border-emerald-500/50 transition-all cursor-pointer select-none group"
                  >
                    <div className="flex items-center gap-2.5">
                      <Shield className="w-4 h-4 text-emerald-400" />
                      <div>
                        <div className="text-[13px] font-semibold text-white group-hover:text-emerald-200">MPA Zones</div>
                        <div className="text-[10.5px] font-mono text-emerald-300/90">Marine Reserves</div>
                      </div>
                    </div>
                    <div className={`w-8 h-4 rounded-full transition-colors relative flex items-center p-0.5 ${
                      activeFilters.showMPABoundaries ? 'bg-emerald-500/30 border border-emerald-400' : 'bg-slate-800 border border-slate-700'
                    }`}>
                      <div className={`w-3 h-3 rounded-full transition-transform ${
                        activeFilters.showMPABoundaries ? 'translate-x-4 bg-emerald-400 shadow-[0_0_8px_#10B981]' : 'translate-x-0 bg-slate-500'
                      }`} />
                    </div>
                  </div>
                </div>

                {/* Autonomous Sentinel-1C Ingestion Status & Actions */}
                <div className="pt-2.5 border-t border-cyan-900/40 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-[11px] font-mono text-cyan-300 px-0.5">
                    <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#10B981] animate-pulse" />
                      S1C STREAM: ACTIVE
                    </span>
                    <span className="text-[10px] text-cyan-400 font-semibold font-mono">15m AUTO</span>
                  </div>

                  <button
                    type="button"
                    onClick={handleSimulateSpillDemo}
                    disabled={isSimulating}
                    className="w-full py-2 px-3 rounded-lg text-[11.5px] font-mono font-bold tracking-wider flex items-center justify-between transition-all bg-[#0c2349]/80 hover:bg-[#123366] border border-cyan-900/40 hover:border-rose-500/60 text-white hover:text-rose-200 group"
                    title="Force Sentinel-1C C-SAR Orbit #142 Hydrocarbon Slick Ingestion & ML Attribution Sync"
                  >
                    <span className="flex items-center gap-2">
                      <Radio className="w-4 h-4 text-rose-400 group-hover:animate-pulse" />
                      <span>{isSimulating ? 'SYNCING S-1C...' : 'SYNC SAR ORBIT #142'}</span>
                    </span>
                    <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      LIVE
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleDriftSim()}
                    className={`w-full py-2 px-3 rounded-lg text-[11.5px] font-mono font-bold tracking-wider flex items-center justify-between transition-all border ${
                      isDriftSimActive
                        ? 'bg-amber-500/20 border-amber-400 text-amber-200 shadow-[0_0_12px_rgba(245,158,11,0.35)]'
                        : 'bg-[#0c2349]/80 hover:bg-[#123366] border-cyan-900/40 hover:border-amber-500/50 text-white'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <Waves className="w-4 h-4 text-amber-400" />
                      <span>INCOIS 72H DRIFT SIM</span>
                    </span>
                    <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded ${
                      isDriftSimActive ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}>
                      {isDriftSimActive ? 'RUNNING' : 'STANDBY'}
                    </span>
                  </button>
                </div>
              </>
            )}

            {/* ── Tab 2: THERMAL ZONE CONTROLS (V2 Intelligence Engine) ── */}
            {activeNavTab === 'thermal' && (
              <>
                <div>
                  <div className="text-[12px] font-mono font-bold text-amber-300 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Flame className="w-4 h-4 text-amber-400" />
                    <span>THERMAL ZONE INTELLIGENCE V2</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-normal">
                    NASA VIIRS active hotspots + Sovereign Boundary + Bharatmaps RFA Forest &amp; Mining Belts.
                  </p>
                </div>

                {/* Primary Layer Toggle */}
                <div className="pt-2.5 border-t border-cyan-900/40 flex flex-col gap-2">
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] border border-amber-500/40 transition-all">
                    <div className="flex items-center gap-2.5">
                      <Flame className="w-4 h-4 text-amber-400 shrink-0" />
                      <div>
                        <div className="text-[13px] font-semibold text-white">Fire / Thermal Layer</div>
                        <div className="text-[10.5px] font-mono text-amber-200/90">
                          {filteredHotspots.length} / {hotspots.length} Active Hotspots
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleFilter('showFireHotspots')}
                      className={`px-3 py-1.5 rounded-md text-[11px] font-mono font-bold transition-all shadow ${
                        activeFilters.showFireHotspots
                          ? 'bg-amber-400 text-slate-950 font-bold'
                          : 'bg-slate-800 text-slate-400 border border-slate-600'
                      }`}
                    >
                      {activeFilters.showFireHotspots ? 'ON' : 'OFF'}
                    </button>
                  </div>

                  {/* V2 Category Filter Chips */}
                  <div className="flex flex-col gap-1.5">
                    <div className="text-[11px] font-mono font-bold text-cyan-300 uppercase tracking-wider">
                      V2 Context Filters
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono">
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('all')}
                        className={`px-2.5 py-1.5 rounded-lg text-left transition-all border ${
                          thermalCategoryFilter === 'all'
                            ? 'bg-amber-500/25 border-amber-400 text-amber-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        ALL ({hotspots.length})
                      </button>
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('industrial')}
                        className={`px-2.5 py-1.5 rounded-lg text-left transition-all border flex items-center ${
                          thermalCategoryFilter === 'industrial'
                            ? 'bg-orange-500/25 border-orange-400 text-orange-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        <span className="inline-block w-2 h-2 rounded-full bg-orange-500 mr-1.5 shrink-0" />
                        <span className="truncate">INDUSTRIAL ({thermalCounts.industrial})</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('wildfire')}
                        className={`px-2.5 py-1.5 rounded-lg text-left transition-all border flex items-center ${
                          thermalCategoryFilter === 'wildfire'
                            ? 'bg-red-500/25 border-red-400 text-red-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1.5 shrink-0" />
                        <span className="truncate">FOREST ({thermalCounts.wildfire})</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('stubble')}
                        className={`px-2.5 py-1.5 rounded-lg text-left transition-all border flex items-center ${
                          thermalCategoryFilter === 'stubble'
                            ? 'bg-yellow-500/25 border-yellow-400 text-yellow-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        <span className="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1.5 shrink-0" />
                        <span className="truncate">STUBBLE ({thermalCounts.stubble})</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('gas_flare')}
                        className={`px-2.5 py-1.5 rounded-lg text-left transition-all border flex items-center ${
                          thermalCategoryFilter === 'gas_flare'
                            ? 'bg-purple-500/25 border-purple-400 text-purple-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        <span className="inline-block w-2 h-2 rounded-full bg-purple-400 mr-1.5 shrink-0" />
                        <span className="truncate">FLARE ({thermalCounts.gas_flare})</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('mining')}
                        className={`px-2.5 py-1.5 rounded-lg text-left transition-all border flex items-center ${
                          thermalCategoryFilter === 'mining'
                            ? 'bg-amber-700/25 border-amber-500 text-amber-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        <span className="inline-block w-2 h-2 rounded-full bg-amber-600 mr-1.5 shrink-0" />
                        <span className="truncate">MINING ({thermalCounts.mining})</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setThermalCategoryFilter('cpcb')}
                        className={`col-span-2 px-2.5 py-2 rounded-lg text-left transition-all border flex items-center justify-between ${
                          thermalCategoryFilter === 'cpcb'
                            ? 'bg-rose-500/25 border-rose-400 text-rose-200 font-bold'
                            : 'bg-[#0c2349]/80 border-cyan-900/40 text-slate-300 hover:text-white hover:bg-[#123366]'
                        }`}
                      >
                        <span className="flex items-center gap-1.5">
                          <span className="inline-block w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                          <span className="text-[11px] font-bold">CPCB CRITICALLY POLLUTED</span>
                        </span>
                        <span className="text-[11px] font-bold font-mono">({thermalCounts.cpcb})</span>
                      </button>
                    </div>
                  </div>

                  {/* Telemetry metadata */}
                  <div className="p-2.5 rounded-lg bg-[#071328]/80 border border-cyan-900/50 text-[11px] font-mono flex flex-col gap-1.5 text-slate-200">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Sensors:</span>
                      <span className="text-amber-300 font-bold">NASA VIIRS SNPP + N20</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Forest GIS:</span>
                      <span className="text-emerald-300 font-bold">Bharatmaps RFA (422k Polygons)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Boundary:</span>
                      <span className="text-cyan-300 font-semibold">Sovereign India Geofence</span>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* ── Tab 3: GEOLOGICAL CONTROLS (Landslide Danger Zones) ── */}
            {activeNavTab === 'geological' && (
              <>
                <div>
                  <div className="text-[12px] font-mono font-bold text-rose-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Mountain className="w-4 h-4 text-rose-400" />
                    <span>GEOLOGICAL HAZARD ZONES</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-normal">
                    Critical landslide and debris-flow risk zones mapped across India (GSI/NDMA).
                  </p>
                </div>

                <div className="flex flex-col gap-2 pt-2.5 border-t border-cyan-900/40">
                  <div className="text-[11px] font-mono font-bold text-cyan-300 uppercase tracking-wider mb-0.5">
                    LANDSLIDE SECTORS
                  </div>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.CHAMOLI_LANDSLIDE)}
                    className="px-3 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] text-left border border-cyan-900/40 hover:border-rose-500/60 transition-all flex items-center justify-between group"
                  >
                    <div>
                      <div className="text-[12.5px] font-bold text-white group-hover:text-rose-200">Chamoli &amp; Joshimath</div>
                      <div className="text-[10.5px] font-mono text-cyan-200/80">Uttarakhand · Flash Rockslide</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      CRITICAL
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.WAYANAD_LANDSLIDE)}
                    className="px-3 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] text-left border border-cyan-900/40 hover:border-rose-500/60 transition-all flex items-center justify-between group"
                  >
                    <div>
                      <div className="text-[12.5px] font-bold text-white group-hover:text-rose-200">Wayanad Meppadi</div>
                      <div className="text-[10.5px] font-mono text-cyan-200/80">Kerala · Monsoon Mudslide</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      CRITICAL
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.KULLU_LANDSLIDE)}
                    className="px-3 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] text-left border border-cyan-900/40 hover:border-amber-500/60 transition-all flex items-center justify-between group"
                  >
                    <div>
                      <div className="text-[12.5px] font-bold text-white group-hover:text-amber-200">Kullu-Manali Valley</div>
                      <div className="text-[10.5px] font-mono text-cyan-200/80">Himachal · Bank Slumping</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      HIGH
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.SIKKIM_LANDSLIDE)}
                    className="px-3 py-2 rounded-lg bg-[#0c2349]/80 hover:bg-[#123366] text-left border border-cyan-900/40 hover:border-rose-500/60 transition-all flex items-center justify-between group"
                  >
                    <div>
                      <div className="text-[12.5px] font-bold text-white group-hover:text-rose-200">Sikkim Teesta Basin</div>
                      <div className="text-[10.5px] font-mono text-cyan-200/80">Sikkim · Moraine Dam Failure</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/40">
                      CRITICAL
                    </span>
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* 🛑 Geological Constraint Dashboard (when a danger zone is clicked) 🛑 */}
      <LandslideConstraintDashboard
        zoneData={selectedHazardZone}
        onClose={() => setSelectedHazardZone(null)}
        onAnalyze={handleAnalyzeLandslide}
        isAnalyzing={isAnalyzingLandslide}
        analysisResult={landslideAnalysisResult}
      />


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

              {(() => {
                const fallbackDataUrl = generateTacticalSatelliteDataUrl(
                  selectedVessel.lat,
                  selectedVessel.lon,
                  selectedVessel.mmsi,
                  vesselSensor,
                  selectedVessel.course_deg ?? 0,
                  selectedVessel.speed_knots ?? 12
                );
                return (
                  <div
                    className="relative w-full h-32 bg-[#06101e] flex items-center justify-center overflow-hidden"
                    style={{
                      backgroundImage: `url(${fallbackDataUrl})`,
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                    }}
                  >
                    <img
                      key={`${selectedVessel.mmsi}-${vesselSensor}`}
                      src={getVesselSatelliteApiUrl(selectedVessel, vesselSensor)}
                      alt={`Satellite pass of ${selectedVessel.vessel_name}`}
                      className="w-full h-full object-cover transition-opacity duration-300"
                      loading="eager"
                      onError={(e) => {
                        const target = e.currentTarget;
                        if (target.src !== fallbackDataUrl) {
                          target.src = fallbackDataUrl;
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
                );
              })()}
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

      {/* ── Hotspot Hover Tooltip (V2 Spatial Intelligence) ── */}
      {hoveredHotspot && hoveredHotspotPos && (
        <div
          className="absolute z-40 pointer-events-none -translate-x-1/2 -translate-y-full mb-3 max-w-xs w-72"
          style={{
            left: `${hoveredHotspotPos.x}px`,
            top: `${hoveredHotspotPos.y}px`,
          }}
        >
          <div className="p-3 rounded-lg bg-navy-950/95 border border-amber-500/70 text-white font-mono text-[11px] shadow-2xl backdrop-blur-md space-y-1.5">
            {/* Header Badge */}
            <div className="flex items-center justify-between pb-1.5 border-b border-navy-700">
              <div className="flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full animate-pulse"
                  style={{
                    backgroundColor:
                      hoveredHotspot.fire_type === 'wildfire'
                        ? '#EF4444'
                        : hoveredHotspot.fire_type === 'industrial'
                        ? '#F97316'
                        : hoveredHotspot.fire_type === 'stubble'
                        ? '#EAB308'
                        : hoveredHotspot.fire_type === 'gas_flare'
                        ? '#A855F7'
                        : '#EA580C',
                  }}
                />
                <span className="font-bold text-amber-300 uppercase tracking-wider text-[11px]">
                  {hoveredHotspot.fire_type === 'wildfire'
                    ? 'FOREST / WILDFIRE'
                    : hoveredHotspot.fire_type === 'industrial'
                    ? 'INDUSTRIAL BLAZE'
                    : hoveredHotspot.fire_type === 'stubble'
                    ? 'STUBBLE BURNING'
                    : hoveredHotspot.fire_type === 'gas_flare'
                    ? 'GAS FLARING'
                    : hoveredHotspot.fire_type === 'mining'
                    ? 'MINING THERMAL'
                    : 'THERMAL ANOMALY'}
                </span>
              </div>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {hoveredHotspot.classification_score ? `${hoveredHotspot.classification_score}%` : '85%'}
              </span>
            </div>

            {/* FRP & Brightness Grid */}
            <div className="grid grid-cols-2 gap-1 text-[10px] text-gray-300">
              <div>
                <span className="text-gray-400">FRP: </span>
                <span className="font-bold text-rose-400">{(hoveredHotspot.frp ?? 0).toFixed(1)} MW</span>
              </div>
              <div>
                <span className="text-gray-400">Temp: </span>
                <span className="font-bold text-white">{(hoveredHotspot.brightness ?? 320).toFixed(1)} K</span>
              </div>
              <div>
                <span className="text-gray-400">Sensor: </span>
                <span className="font-semibold text-cyan-300">{hoveredHotspot.satellite || 'VIIRS'}</span>
              </div>
              <div>
                <span className="text-gray-400">Time: </span>
                <span className="font-semibold text-gray-200">{hoveredHotspot.acquired_at ? new Date(hoveredHotspot.acquired_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Live'}</span>
              </div>
              <div>
                <span className="text-gray-400">Conf: </span>
                <span className="font-semibold text-emerald-400 uppercase">{hoveredHotspot.confidence || 'HIGH'}</span>
              </div>
            </div>

            {/* V2 Classification Context / Reason */}
            {hoveredHotspot.classification_reason && (
              <div className="pt-1 text-[10px] text-amber-200/90 bg-black/40 p-1.5 rounded border border-navy-700/60 leading-tight">
                <span className="text-gray-400 font-bold block mb-0.5">PREDICTED CONTEXT:</span>
                <span>{hoveredHotspot.classification_reason}</span>
              </div>
            )}

            {/* CPCB CPA Cluster Proximity */}
            {hoveredHotspot.near_cpcb_cluster && (
              <div className="text-[10px] text-rose-300 bg-rose-950/40 p-1.5 rounded border border-rose-500/40 flex items-center justify-between">
                <span>CPCB CRITICAL CLUSTER:</span>
                <span className="font-bold text-rose-200">{hoveredHotspot.cpcb_cpa_name || 'Active CPA'}</span>
              </div>
            )}

            {/* Statutory Enforcement Agency & Recommended Action */}
            {hoveredHotspot.responding_agency && (
              <div className="pt-1 text-[9px] border-t border-navy-700/80 space-y-0.5 text-gray-300">
                <div>
                  <span className="text-gray-400">Enforcement: </span>
                  <span className="text-emerald-300 font-semibold">{hoveredHotspot.responding_agency}</span>
                </div>
                {hoveredHotspot.recommended_action && (
                  <div className="text-gray-400 text-[8.5px] italic leading-tight">
                    {hoveredHotspot.recommended_action}
                  </div>
                )}
              </div>
            )}
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

      {/* ── Thermal Hotspot Satellite Popup ── */}
      {selectedHotspot && (
        <HotspotSatellitePopup hotspot={selectedHotspot} onClose={() => setSelectedHotspot(null)} />
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
