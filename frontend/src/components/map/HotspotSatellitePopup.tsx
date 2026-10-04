import React, { useState } from 'react';
import type { ThermalHotspot } from '../../types/fire';

interface HotspotSatellitePopupProps {
  hotspot: ThermalHotspot;
  onClose: () => void;
}

export function HotspotSatellitePopup({ hotspot, onClose }: HotspotSatellitePopupProps) {
  const [enhance, setEnhance] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Uses relative path routed through Vite dev server proxy to FastAPI backend:
  const imageUrl = `/api/v1/satellite/thermal-image?lat=${hotspot.latitude}&lon=${hotspot.longitude}&enhance=${enhance}`;

  React.useEffect(() => {
    setIsLoading(true);
    setHasError(false);
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 12000);
    return () => clearTimeout(timer);
  }, [imageUrl]);

  return (
    <div
      className="absolute top-4 right-4 shadow-2xl z-50 flex flex-col transform transition-transform duration-300"
      style={{
        background: '#040b17',
        border: '1px solid #f59e0b',
        width: '380px',
        borderRadius: '10px',
        boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.8), 0 0 15px rgba(245, 158, 11, 0.2)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3.5 py-2.5 border-b"
        style={{ background: '#071529', borderColor: '#1e293b' }}
      >
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse shadow-[0_0_8px_#f59e0b]" />
          <h2 className="text-white font-mono font-bold text-xs tracking-wider uppercase">
            Sentinel-2 Thermal Reconnaissance
          </h2>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800 text-sm font-bold"
        >
          ✕
        </button>
      </div>

      <div className="p-4 space-y-3.5 font-mono">
        {/* Telemetry info */}
        <div className="grid grid-cols-3 gap-2 bg-[#081b33] p-2.5 rounded-lg border border-slate-700/60 text-[11px]">
          <div>
            <div className="text-slate-400 text-[10px]">COORDINATES</div>
            <div className="text-white font-bold">{hotspot.latitude.toFixed(3)}°N</div>
            <div className="text-white font-bold">{hotspot.longitude.toFixed(3)}°E</div>
          </div>
          <div>
            <div className="text-slate-400 text-[10px]">RADIANCY / TIME</div>
            <div className="text-amber-400 font-bold">{hotspot.frp} MW</div>
            <div className="text-slate-400 text-[9px] truncate" title={hotspot.acquired_at ? new Date(hotspot.acquired_at).toLocaleString() : 'Live'}>
              {hotspot.acquired_at ? new Date(hotspot.acquired_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Live'}
            </div>
          </div>
          <div>
            <div className="text-slate-400 text-[10px]">CLASSIFICATION</div>
            <div className="text-orange-400 font-bold uppercase truncate">{hotspot.fire_type || 'Hotspot'}</div>
            <div className="text-slate-400 text-[10px]">Optical S2</div>
          </div>
        </div>

        {/* Satellite Imagery Frame */}
        <div className="relative w-full h-52 bg-[#020611] rounded-lg overflow-hidden border border-slate-700/80 flex items-center justify-center">
          {isLoading && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#050e1d]/90 gap-2">
              <div className="w-7 h-7 border-2 border-amber-500/30 border-t-amber-400 rounded-full animate-spin" />
              <span className="text-[10px] text-amber-300 font-mono tracking-widest uppercase">
                {enhance ? 'Synthesizing EDSR 4x Raster...' : 'Retrieving Sentinel-2 L2A...'}
              </span>
            </div>
          )}

          {hasError ? (
            <div className="flex flex-col items-center justify-center text-center p-4 gap-2 text-slate-400">
              <span className="text-2xl">🛰️</span>
              <span className="text-xs text-rose-400 font-bold">Optical Scene Pending Pass</span>
              <span className="text-[10px] text-slate-500">Cloud cover or scene ingestion in progress</span>
              <button
                onClick={() => { setHasError(false); setIsLoading(true); }}
                className="mt-1 px-2.5 py-1 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-600"
              >
                Retry Ingestion
              </button>
            </div>
          ) : (
            <img
              key={`${imageUrl}`}
              src={imageUrl}
              alt="Sentinel-2 Optical Hotspot Snapshot"
              className="w-full h-full object-cover transition-opacity duration-300"
              style={{ opacity: isLoading ? 0.3 : 1 }}
              onLoad={() => setIsLoading(false)}
              onError={() => {
                setIsLoading(false);
                setHasError(true);
              }}
            />
          )}

          {/* Badges on top of imagery */}
          <div className="absolute top-2 left-2 flex flex-col gap-1 z-10 pointer-events-none">
            <span className="text-[9px] font-mono bg-black/80 backdrop-blur-sm px-2 py-0.5 rounded text-amber-300 border border-amber-500/40 flex items-center gap-1">
              <span>🛰️</span> COPERNICUS SENTINEL-2 L2A
            </span>
            {enhance ? (
              <span className="text-[9px] font-mono bg-emerald-950/90 backdrop-blur-sm px-2 py-0.5 rounded text-emerald-300 border border-emerald-500/50 flex items-center gap-1 font-bold shadow-[0_0_8px_rgba(16,185,129,0.4)]">
                <span>✨</span> EDSR ENHANCED (4× / 2.5m GSD)
              </span>
            ) : (
              <span className="text-[9px] font-mono bg-slate-900/80 backdrop-blur-sm px-2 py-0.5 rounded text-slate-300 border border-slate-700/60">
                STANDARD RESOLUTION (10m GSD)
              </span>
            )}
          </div>

          <div className="absolute bottom-2 right-2 text-[9px] font-mono text-slate-400 bg-black/70 px-1.5 py-0.5 rounded">
            EPSG:4326 | {enhance ? '1024×1024' : '256×256'}
          </div>
        </div>

        {/* AI Super-Resolution Toggle Controls */}
        <div className="flex justify-between items-center bg-[#07172c] p-2.5 rounded-lg border border-slate-700/80">
          <div className="flex flex-col">
            <span className="text-[11px] font-bold text-slate-200">Deep Learning EDSR 4×</span>
            <span className="text-[10px] text-slate-400">Residual 32-Block Upscaler (CUDA)</span>
          </div>
          <button
            onClick={() => {
              setIsLoading(true);
              setHasError(false);
              setEnhance(!enhance);
            }}
            className={`px-3 py-1.5 text-xs font-bold font-mono rounded transition-all shadow-md flex items-center gap-1.5 ${
              enhance
                ? 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-emerald-500/30'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-600'
            }`}
          >
            <span>{enhance ? '✨ ON (4×)' : 'OFF'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
