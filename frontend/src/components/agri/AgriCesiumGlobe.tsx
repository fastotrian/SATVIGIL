/**
 * SATVIGIL — CesiumJS 3D Globe for AI Cadastral Field Boundary Mapping
 * Full-size 3D WebGL Earth Globe matching Maritime, Thermal, and Geological views.
 * Renders georeferenced agricultural parcels with NDVI color coding,
 * top-left sector waypoints & surveillance layer dock (Crop Health Monitor),
 * top-right camera controls, and parcel telemetry inspection popup.
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  Viewer,
  Cartesian3,
  Color,
  GeoJsonDataSource,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  defined,
  HeightReference,
  ConstantProperty,
  ColorMaterialProperty,
  Math as CesiumMath,
} from 'cesium';
import {
  Layers,
  Sparkles,
  Compass,
  MapPin,
  CheckCircle2,
  X,
  Wheat,
  Activity,
  Globe2
} from 'lucide-react';
import type { AgriField, FieldsResponse, AgriStatusResponse } from '../../types/agri';
import {
  createSatelliteImageryProvider,
  createSatelliteReferenceProvider,
  configureTacticalViewer,
  SECTOR_WAYPOINTS,
} from '../map/cesiumConfig';
import { CropHealthPanel } from './CropHealthPanel';
import axios from 'axios';

interface AgriCesiumGlobeProps {
  fields: AgriField[];
  center: { lat: number; lon: number };
  totalFields: number;
  avgAreaHa: number;
  fragmentedPct: number;
  srEnhanced: boolean;
  onToggleSr: () => void;
  selectedField: AgriField | null;
  onSelectField: (field: AgriField | null) => void;
}

export function AgriCesiumGlobe({
  fields,
  center,
  totalFields,
  avgAreaHa,
  fragmentedPct,
  srEnhanced,
  onToggleSr,
  selectedField,
  onSelectField,
}: AgriCesiumGlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Viewer | null>(null);
  const dataSourceRef = useRef<GeoJsonDataSource | null>(null);
  const [modelTelemetry, setModelTelemetry] = useState<AgriStatusResponse | null>(null);
  const [isLayerDockOpen, setIsLayerDockOpen] = useState<boolean>(true);

  useEffect(() => {
    // Fetch EDSR model live status
    axios.get<AgriStatusResponse>('/api/v1/agri/status')
      .then(res => setModelTelemetry(res.data))
      .catch(() => {});
  }, []);

  const [srParcelEnhanced, setSrParcelEnhanced] = useState<boolean>(false);
  const [isParcelImgLoading, setIsParcelImgLoading] = useState<boolean>(false);

  // Initialize CesiumJS 3D Viewer (Full-Screen Command Center Spec)
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return;

    const satImagery = createSatelliteImageryProvider();
    const satRef = createSatelliteReferenceProvider();

    const viewer = new Viewer(containerRef.current, {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      animation: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      vrButton: false,
      baseLayer: false,
    });

    // Add satellite imagery & reference borders
    viewer.imageryLayers.addImageryProvider(satImagery);
    viewer.imageryLayers.addImageryProvider(satRef);
    configureTacticalViewer(viewer);

    // Initial camera fly-to over agricultural sector (Ludhiana, Punjab) at tactical inspection altitude
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(center.lon, center.lat, 4200),
      orientation: {
        heading: 0.0,
        pitch: CesiumMath.toRadians(-55),
        roll: 0.0,
      },
      duration: 1.5,
    });

    // Handle clicks on field polygons
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click: { position: any }) => {
      const pickedObject = viewer.scene.pick(click.position);
      if (defined(pickedObject) && pickedObject.id && pickedObject.id.properties) {
        const props = pickedObject.id.properties;
        const fieldId = props.id ? props.id.getValue() : null;
        if (fieldId) {
          const match = fields.find(f => f.id === fieldId);
          if (match) {
            onSelectField(match);
            return;
          }
        }
      }
      onSelectField(null);
    }, ScreenSpaceEventType.LEFT_CLICK);

    viewerRef.current = viewer;

    return () => {
      handler.destroy();
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, []);

  // Update GeoJSON layer whenever fields change
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || fields.length === 0) return;

    const geojson = {
      type: 'FeatureCollection',
      features: fields.map(f => ({
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [f.coordinates]
        },
        properties: {
          id: f.id,
          crop: f.crop,
          ndvi: f.ndvi,
          health: f.health,
          area_ha: f.area_ha,
          confidence: f.confidence || 0.88
        }
      }))
    };

    if (dataSourceRef.current) {
      viewer.dataSources.remove(dataSourceRef.current, true);
      dataSourceRef.current = null;
    }

    GeoJsonDataSource.load(geojson, {
      strokeWidth: 3,
      clampToGround: true,
    }).then(dataSource => {
      dataSourceRef.current = dataSource;
      viewer.dataSources.add(dataSource);

      // Colorize parcels by NDVI vegetative vigor with crisp boundaries
      dataSource.entities.values.forEach(entity => {
        if (entity.polygon) {
          const props = entity.properties;
          const ndvi = props && props.ndvi ? props.ndvi.getValue() : 0.5;

          let fillColor = Color.fromCssColorString('rgba(16, 185, 129, 0.40)'); // healthy emerald
          let outlineColor = Color.fromCssColorString('#10b981');

          if (ndvi < 0.2) {
            fillColor = Color.fromCssColorString('rgba(244, 63, 94, 0.40)'); // critical red
            outlineColor = Color.fromCssColorString('#f43f5e');
          } else if (ndvi < 0.35) {
            fillColor = Color.fromCssColorString('rgba(251, 146, 60, 0.40)'); // stressed orange
            outlineColor = Color.fromCssColorString('#fb923c');
          } else if (ndvi < 0.5) {
            fillColor = Color.fromCssColorString('rgba(251, 191, 36, 0.40)'); // moderate amber
            outlineColor = Color.fromCssColorString('#fbbf24');
          }

          entity.polygon.material = new ColorMaterialProperty(fillColor);
          entity.polygon.outline = new ConstantProperty(true);
          entity.polygon.outlineColor = new ConstantProperty(outlineColor);
          entity.polygon.outlineWidth = new ConstantProperty(3);
          entity.polygon.heightReference = new ConstantProperty(HeightReference.CLAMP_TO_GROUND);

          // Add polyline clamped to ground to guarantee sharp, high-contrast borders
          try {
            const hierarchy = entity.polygon.hierarchy?.getValue(CesiumMath.EPSILON7 as any);
            if (hierarchy && hierarchy.positions && hierarchy.positions.length > 0) {
              const boundaryPositions = [...hierarchy.positions, hierarchy.positions[0]];
              entity.polyline = {
                positions: new ConstantProperty(boundaryPositions),
                width: new ConstantProperty(2.5),
                material: new ColorMaterialProperty(outlineColor),
                clampToGround: new ConstantProperty(true),
              } as any;
            }
          } catch {}
        }
      });
    });
  }, [fields]);

  // Sector jump handler
  const jumpToWaypoint = (wp: { longitude: number; latitude: number; height: number; heading: number; pitch: number; roll: number }) => {
    if (!viewerRef.current) return;
    viewerRef.current.camera.flyTo({
      destination: Cartesian3.fromDegrees(wp.longitude, wp.latitude, wp.height),
      orientation: {
        heading: CesiumMath.toRadians(wp.heading),
        pitch: CesiumMath.toRadians(wp.pitch),
        roll: CesiumMath.toRadians(wp.roll),
      },
      duration: 1.5,
    });
  };

  return (
    <div className="relative w-full h-full overflow-hidden select-none" style={{ background: '#02040A' }}>
      {/* ── CesiumJS 3D WebGL Canvas ── */}
      <div ref={containerRef} className="w-full h-full" />

      {/* ── Top-Left Floating Surveillance Dock (Housing CROP HEALTH MONITOR) ── */}
      <div className="absolute top-3 left-3 z-30 flex flex-col gap-2 pointer-events-auto">
        <button
          type="button"
          onClick={() => setIsLayerDockOpen(prev => !prev)}
          className="self-start px-3 py-1.5 rounded-lg font-mono text-xs font-semibold flex items-center gap-2.5 shadow-2xl border border-emerald-500/50 bg-[#071b30]/90 hover:bg-[#0d2a4d]/95 text-emerald-100 hover:text-white transition-all backdrop-blur-md"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10B981]" />
          <span className="tracking-wide">Surveillance Layers (Crop Health)</span>
          <span className="text-[10px] text-emerald-300">{isLayerDockOpen ? '▲' : '▼'}</span>
        </button>

        {/* Collapsible Crop Health Monitor Drawer */}
        {isLayerDockOpen && (
          <div className="w-[335px] h-[calc(100vh-140px)] flex flex-col gap-2 animate-in fade-in zoom-in-95 duration-150">
            {/* Quick Sector Waypoints Bar */}
            <div className="bg-[#071326]/90 border border-emerald-500/30 rounded-xl p-2.5 backdrop-blur-md shadow-xl flex flex-col gap-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-[11px] text-emerald-300 uppercase font-bold px-0.5">
                <span className="flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5 text-emerald-400" />
                  <span>AGRI SECTORS</span>
                </span>
                <span className="text-[10px] text-gray-400">PUNJAB / MAHARASHTRA</span>
              </div>
              <div className="grid grid-cols-3 gap-1 text-[11px]">
                <button
                  type="button"
                  onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.AGRI_LUDHIANA)}
                  className="px-2 py-1.5 rounded bg-[#0c2349]/80 hover:bg-[#123366] border border-emerald-500/30 hover:border-emerald-400 text-left transition-all"
                >
                  <div className="font-bold text-white text-[11px]">Ludhiana</div>
                  <div className="text-[9px] text-emerald-300">Wheat Belt</div>
                </button>
                <button
                  type="button"
                  onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.AGRI_AMRITSAR)}
                  className="px-2 py-1.5 rounded bg-[#0c2349]/80 hover:bg-[#123366] border border-emerald-500/30 hover:border-emerald-400 text-left transition-all"
                >
                  <div className="font-bold text-white text-[11px]">Amritsar</div>
                  <div className="text-[9px] text-emerald-300">Paddy Crop</div>
                </button>
                <button
                  type="button"
                  onClick={() => jumpToWaypoint(SECTOR_WAYPOINTS.AGRI_VIDARBHA)}
                  className="px-2 py-1.5 rounded bg-[#0c2349]/80 hover:bg-[#123366] border border-amber-500/30 hover:border-amber-400 text-left transition-all"
                >
                  <div className="font-bold text-white text-[11px]">Vidarbha</div>
                  <div className="text-[9px] text-amber-300">Cotton / Soy</div>
                </button>
              </div>
            </div>

            {/* Embedded Crop Health Monitor Panel */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <CropHealthPanel
                onClose={() => setIsLayerDockOpen(false)}
                isCompact={true}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Top-Right Tactical Camera Controls ── */}
      <div className="absolute top-12 right-3 z-30 flex flex-col gap-1.5 pointer-events-auto">
        <button
          type="button"
          onClick={() => viewerRef.current?.camera.zoomIn(viewerRef.current.camera.positionCartographic.height * 0.35)}
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 font-mono font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
          title="Zoom In"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => viewerRef.current?.camera.zoomOut(viewerRef.current.camera.positionCartographic.height * 0.45)}
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 font-mono font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
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
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 font-mono text-[11px] font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
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
          className="w-8 h-8 rounded-lg bg-[#071326]/85 hover:bg-[#0c2242]/95 border border-emerald-500/40 hover:border-emerald-400 text-emerald-300 font-mono text-[9px] font-bold flex items-center justify-center shadow-2xl backdrop-blur-md transition-all"
          title="Toggle 3D Tilt Horizon"
        >
          3D
        </button>
      </div>

      {/* ── Bottom-Center Floating Cadastral Telemetry HUD ── */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20 pointer-events-auto flex items-center gap-2 px-3 py-1.5 rounded-xl bg-navy-950/90 border border-emerald-500/40 backdrop-blur-md shadow-2xl font-mono text-xs">
        <div className="flex items-center gap-2 pr-3 border-r border-navy-700">
          <Wheat className="w-4 h-4 text-emerald-400" />
          <span className="font-bold text-white text-[11px]">PARCELS: {totalFields.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-2 pr-3 border-r border-navy-700 text-[11px]">
          <span className="text-gray-400">AVG:</span>
          <span className="text-cyan-300 font-bold">{avgAreaHa} ha</span>
        </div>
        <div className="flex items-center gap-2 pr-3 border-r border-navy-700 text-[11px]">
          <span className="text-gray-400">FRAG:</span>
          <span className="text-amber-300 font-bold">{fragmentedPct}%</span>
        </div>

        {/* SR 4x Toggle Pill */}
        <button
          type="button"
          onClick={onToggleSr}
          className={`flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-bold border transition-all ${
            srEnhanced
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/60 shadow-[0_0_10px_rgba(52,211,153,0.3)]'
              : 'bg-navy-800 text-gray-400 border-navy-700 hover:text-white'
          }`}
        >
          <Sparkles className="w-3 h-3 text-emerald-400" />
          <span>{srEnhanced ? 'EDSR 4x (2.5m/px)' : 'NATIVE (10m/px)'}</span>
        </button>
      </div>

      {/* ── Selected Field Inspection Drawer with Sentinel-2 & EDSR 4x Imagery ── */}
      {selectedField && (
        <div className="absolute bottom-12 left-4 z-30 pointer-events-auto w-88 max-w-[360px] bg-[#040b17]/95 border border-emerald-500/70 rounded-xl p-3 shadow-2xl backdrop-blur-md animate-fadeIn font-mono">
          <div className="flex items-center justify-between pb-2 border-b border-emerald-900/60 mb-2.5">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]" />
              <span className="font-bold text-white text-xs tracking-wider">
                PARCEL CADASTRAL #{selectedField.id}
              </span>
            </div>
            <button
              type="button"
              onClick={() => onSelectField(null)}
              className="text-gray-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800 text-xs font-bold"
            >
              ✕
            </button>
          </div>

          {/* Sentinel-2 / EDSR Optical Reconnaissance Snapshot */}
          <div className="relative w-full h-36 bg-[#020611] rounded-lg overflow-hidden border border-emerald-700/60 mb-2.5 flex items-center justify-center">
            {isParcelImgLoading && (
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#050e1d]/90 gap-1.5">
                <div className="w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-400 rounded-full animate-spin" />
                <span className="text-[9px] text-emerald-300 font-mono tracking-wider uppercase">
                  {srParcelEnhanced ? 'EDSR 4× Synthesizing...' : 'Fetching Sentinel-2 L2A...'}
                </span>
              </div>
            )}
            <img
              key={`parcel-${selectedField.id}-${srParcelEnhanced}`}
              src={`/api/v1/agri/field-image?lat=${selectedField.coordinates[0][1]}&lon=${selectedField.coordinates[0][0]}&enhance=${srParcelEnhanced}`}
              alt={`Sentinel-2 parcel ${selectedField.id}`}
              className="w-full h-full object-cover transition-opacity duration-300"
              style={{ opacity: isParcelImgLoading ? 0.3 : 1 }}
              onLoad={() => setIsParcelImgLoading(false)}
              onError={() => setIsParcelImgLoading(false)}
            />
            <div className="absolute top-1.5 left-1.5 flex flex-col gap-0.5 z-10 pointer-events-none">
              <span className="text-[8px] font-mono bg-black/80 px-1.5 py-0.5 rounded text-amber-300 border border-amber-500/40">
                🛰️ SENTINEL-2 OPTICAL
              </span>
              {srParcelEnhanced && (
                <span className="text-[8px] font-mono bg-emerald-950/90 px-1.5 py-0.5 rounded text-emerald-300 border border-emerald-500/50 font-bold shadow-[0_0_6px_rgba(16,185,129,0.4)]">
                  ✨ EDSR 4× (2.5m GSD)
                </span>
              )}
            </div>
            <div className="absolute bottom-1 right-1 text-[8px] font-mono text-slate-400 bg-black/70 px-1 py-0.5 rounded">
              {srParcelEnhanced ? '1024×1024' : '256×256'}
            </div>
          </div>

          {/* Parcel Agronomic Telemetry Grid */}
          <div className="grid grid-cols-2 gap-2 text-[11px] mb-2.5">
            <div className="bg-[#07172c] p-2 rounded-lg border border-slate-700/60">
              <span className="text-slate-400 block text-[10px]">Crop Classification</span>
              <span className="text-emerald-300 font-bold truncate block">{selectedField.crop}</span>
            </div>
            <div className="bg-[#07172c] p-2 rounded-lg border border-slate-700/60">
              <span className="text-slate-400 block text-[10px]">Cadastral Acreage</span>
              <span className="text-cyan-300 font-bold">{selectedField.area_ha} ha</span>
            </div>
            <div className="bg-[#07172c] p-2 rounded-lg border border-slate-700/60">
              <span className="text-slate-400 block text-[10px]">NDVI Vigor Score</span>
              <span className="text-emerald-400 font-bold">{selectedField.ndvi.toFixed(2)}</span>
            </div>
            <div className="bg-[#07172c] p-2 rounded-lg border border-slate-700/60">
              <span className="text-slate-400 block text-[10px]">Vegetative Health</span>
              <span className="uppercase text-[10px] font-bold text-amber-300">{selectedField.health}</span>
            </div>
          </div>

          {/* AI EDSR Super-Resolution Toggle */}
          <div className="flex items-center justify-between bg-[#071326] p-2 rounded-lg border border-emerald-500/40 mb-2">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-200">Parcel Super-Resolution</span>
              <span className="text-[9px] text-slate-400">Deep Residual 4× Upscaler</span>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsParcelImgLoading(true);
                setSrParcelEnhanced(prev => !prev);
              }}
              className={`px-2.5 py-1 text-[10px] font-bold font-mono rounded transition-all shadow-md flex items-center gap-1 ${
                srParcelEnhanced
                  ? 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-emerald-500/30'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-600'
              }`}
            >
              <Sparkles className="w-3 h-3" />
              <span>{srParcelEnhanced ? 'ON (4×)' : 'OFF'}</span>
            </button>
          </div>

          <div className="flex items-center justify-between text-[10px] text-gray-400 border-t border-slate-800 pt-2">
            <span>Cadastral Conf: <strong className="text-gray-200">{(selectedField.confidence ? selectedField.confidence * 100 : 92).toFixed(0)}%</strong></span>
            <span className="text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              Sentinel-2 L2A Calibrated
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
