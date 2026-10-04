/**
 * SATVIGIL — CesiumJS WebGL 3D Command Center Configuration
 * Provides dark marine imagery providers, zero-token setup, camera presets,
 * and military command center viewing parameters.
 */
import {
  Ion,
  UrlTemplateImageryProvider,
  Cartesian3,
  Viewer,
  Color,
} from 'cesium';

// Disable default Cesium Ion access token requirement (prevents 401 warnings)
Ion.defaultAccessToken = '';

/**
 * Photorealistic Satellite Imagery (Google Earth look & feel)
 * ESRI High-Resolution World Imagery (True-Color Optical Satellite)
 */
export function createSatelliteImageryProvider(): UrlTemplateImageryProvider {
  return new UrlTemplateImageryProvider({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    credit: '© Esri, Maxar, Earthstar Geographics, CNES/Airbus DS, USGS, AeroGRID, IGN, and the GIS User Community',
    maximumLevel: 19,
  });
}

/**
 * Photorealistic Satellite Reference Layer (Borders, Cities, Maritime Boundaries)
 */
export function createSatelliteReferenceProvider(): UrlTemplateImageryProvider {
  return new UrlTemplateImageryProvider({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
    credit: '© Esri',
    maximumLevel: 19,
  });
}

/**
 * ESRI World Dark Gray Canvas Base Imagery (Alternative Tactical Mode)
 */
export function createDarkBaseImageryProvider(): UrlTemplateImageryProvider {
  return new UrlTemplateImageryProvider({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    credit: '© Esri, HERE, Garmin, OpenStreetMap contributors',
    maximumLevel: 18,
  });
}

/**
 * ESRI World Dark Gray Reference Layer
 */
export function createDarkReferenceImageryProvider(): UrlTemplateImageryProvider {
  return new UrlTemplateImageryProvider({
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
    credit: '© Esri',
    maximumLevel: 18,
  });
}

/**
 * Tactical Sector Camera Waypoints
 */
export const SECTOR_WAYPOINTS = {
  ALL_INDIA: {
    longitude: 78.9629,
    latitude: 20.5937,
    height: 3800000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  BOMBAY_HIGH: {
    longitude: 71.5000,
    latitude: 19.2000,
    height: 250000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  JNPT_APPROACH: {
    longitude: 72.9500,
    latitude: 18.9500,
    height: 120000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  KUTCH_SANCTUARY: {
    longitude: 69.4500,
    latitude: 22.5000,
    height: 180000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  CHAMOLI_LANDSLIDE: {
    longitude: 79.6000,
    latitude: 30.5000,
    height: 140000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  WAYANAD_LANDSLIDE: {
    longitude: 76.1800,
    latitude: 11.5500,
    height: 90000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  KULLU_LANDSLIDE: {
    longitude: 77.2000,
    latitude: 32.1000,
    height: 150000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  SIKKIM_LANDSLIDE: {
    longitude: 88.5500,
    latitude: 27.4800,
    height: 130000,
    heading: 0,
    pitch: -88,
    roll: 0,
  },
  AGRI_LUDHIANA: {
    longitude: 75.8500,
    latitude: 30.9000,
    height: 25000,
    heading: 0,
    pitch: -65,
    roll: 0,
  },
  AGRI_AMRITSAR: {
    longitude: 74.8700,
    latitude: 31.6300,
    height: 35000,
    heading: 0,
    pitch: -65,
    roll: 0,
  },
  AGRI_VIDARBHA: {
    longitude: 78.4000,
    latitude: 20.7000,
    height: 60000,
    heading: 0,
    pitch: -65,
    roll: 0,
  },
};

/**
 * Initial Tactical Camera Viewport (Bombay High, Arabian Sea)
 */
export const DEFAULT_CAMERA_VIEW = {
  destination: Cartesian3.fromDegrees(72.5, 19.2, 1400000),
  orientation: {
    heading: 0.0,
    pitch: -1.25, // slight tilt for 3D horizon perspective
    roll: 0.0,
  },
};

/**
 * Apply military command center rendering preferences to a Cesium Viewer instance
 */
export function configureTacticalViewer(viewer: Viewer) {
  const scene = viewer.scene;
  const globe = scene.globe;

  // Realistic Earth aesthetics (Google Earth optical realism)
  globe.baseColor = Color.fromCssColorString('#0B1B3D'); // Deep oceanic blue
  scene.backgroundColor = Color.fromCssColorString('#02040A'); // Deep cosmic space black

  // Atmosphere & lighting
  if (scene.skyAtmosphere) {
    scene.skyAtmosphere.show = true;
    scene.skyAtmosphere.brightnessShift = 0.08;
    scene.skyAtmosphere.saturationShift = 0.05;
  }
  globe.showGroundAtmosphere = true;
  globe.enableLighting = false; // Uniform illumination for crystal-clear satellite imagery
  globe.depthTestAgainstTerrain = false;

  // Maximize WebGL frame rate & memory efficiency
  scene.fog.enabled = true;
  scene.fog.density = 0.00012;

  // Hide default credit container from obstructing UI controls
  const creditContainer = viewer.bottomContainer;
  if (creditContainer && (creditContainer as HTMLElement).style) {
    (creditContainer as HTMLElement).style.display = 'none';
  }
}
