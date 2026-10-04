import React, { useState } from 'react';
import type { ThermalHotspot } from '../../types/fire';

interface HotspotSatellitePopupProps {
  hotspot: ThermalHotspot;
  onClose: () => void;
}

export function HotspotSatellitePopup({ hotspot, onClose }: HotspotSatellitePopupProps) {
  const [enhance, setEnhance] = useState(false);

  // Fallback map URL using standard satellite view if our dynamic API fails
  const mapUrl = `https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}`; 
  // We'll primarily load from the backend:
  const imageUrl = `http://localhost:8000/api/v1/satellite/thermal-image?lat=${hotspot.latitude}&lon=${hotspot.longitude}&enhance=${enhance}`;

  return (
    <div
      className="absolute top-4 right-4 shadow-2xl z-50 flex flex-col transform transition-transform duration-300"
      style={{
        background: 'var(--navy-950)',
        border: '1px solid var(--amber-500)',
        width: '360px',
        borderRadius: '8px',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 border-b"
        style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#F97316' }} />
          <h2 className="text-white font-bold text-xs tracking-widest uppercase">Thermal Reconnaissance</h2>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors text-base">✕</button>
      </div>

      <div className="p-4 space-y-4">
        {/* Info */}
        <div className="text-[11px] font-mono text-gray-300 space-y-1">
          <div><span className="text-gray-500">Location:</span> {hotspot.latitude.toFixed(4)}°N, {hotspot.longitude.toFixed(4)}°E</div>
          <div><span className="text-gray-500">Type:</span> <span className="text-amber-400 font-bold">{hotspot.fire_type || 'Unknown'}</span></div>
          <div><span className="text-gray-500">FRP:</span> {hotspot.frp} MW</div>
        </div>

        {/* Image Viewer */}
        <div className="relative w-full h-48 bg-black rounded overflow-hidden border border-navy-600 flex items-center justify-center">
          <img 
            src={imageUrl} 
            alt="Satellite Reconnaissance"
            className="w-full h-full object-cover"
            onError={(e) => {
              // fallback if API takes too long or fails
              (e.target as HTMLImageElement).src = 'https://via.placeholder.com/400x300/0f172a/38bdf8?text=SATELLITE+UNAVAILABLE';
            }}
          />
          
          <div className="absolute top-2 left-2 flex flex-col gap-1">
            <span className="text-[9px] font-mono bg-black/70 px-1.5 py-0.5 rounded text-amber-300 border border-amber-500/40">
              🛰️ SENTINEL-2 L2A
            </span>
            {enhance && (
              <span className="text-[9px] font-mono bg-teal-900/80 px-1.5 py-0.5 rounded text-teal-300 border border-teal-500/40">
                ✨ EDSR ENHANCED (x4)
              </span>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex justify-between items-center bg-navy-800 p-2 rounded border border-navy-600">
          <span className="text-[10px] font-mono text-gray-400 uppercase">AI Super-Resolution</span>
          <button
            onClick={() => setEnhance(!enhance)}
            className={`px-3 py-1 text-[10px] font-bold rounded transition-colors ${
              enhance ? 'bg-teal-500 text-navy-950' : 'bg-navy-600 text-gray-300 hover:text-white'
            }`}
          >
            {enhance ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>
    </div>
  );
}
