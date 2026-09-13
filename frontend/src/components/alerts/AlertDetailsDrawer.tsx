import React, { useState } from 'react';
import { useAlertStore } from '../../store/alertStore';
import { RISK_COLORS } from '../../constants/riskColors';

export function AlertDetailsDrawer() {
  const { selectedVessel, selectVessel, openDossier } = useAlertStore();
  const [vesselSensor, setVesselSensor] = useState<'sentinel1' | 'sentinel2'>('sentinel1');

  if (!selectedVessel) return null;

  return (
    <div
      className="fixed top-0 right-0 h-full w-88 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 translate-x-0"
      style={{
        background: 'var(--navy-950)',
        borderLeft: '1px solid var(--navy-500)',
        width: '340px',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 border-b"
        style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}
      >
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-4 rounded-full" style={{ background: 'var(--teal-500)' }} />
          <h2 className="text-white font-bold text-sm tracking-widest uppercase">Target Dossier</h2>
        </div>
        <button
          type="button"
          onClick={() => selectVessel(null)}
          className="text-gray-400 hover:text-white transition-colors text-base"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Header Block */}
        <div
          className="p-3 rounded-lg border"
          style={{ background: 'var(--navy-800)', borderColor: 'var(--navy-500)' }}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-base font-bold text-white tracking-wide">{selectedVessel.vessel_name || 'UNKNOWN'}</span>
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded tracking-widest uppercase"
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
          <div className="text-xs font-mono" style={{ color: 'var(--text-mono)' }}>
            MMSI: {selectedVessel.mmsi} · {selectedVessel.vessel_type_label || 'Vessel'}
          </div>
        </div>

        {/* Live Satellite Reconnaissance Viewport */}
        <div
          className="rounded-lg border overflow-hidden"
          style={{ background: 'var(--navy-800)', borderColor: 'var(--navy-500)' }}
        >
          <div
            className="flex items-center justify-between px-3 py-1.5 border-b text-[10px] font-mono"
            style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}
          >
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
              <span className="font-bold text-teal-300">
                🛰️ {vesselSensor === 'sentinel1' ? 'SENTINEL-1 C-SAR' : 'SENTINEL-2 OPTICAL'}
              </span>
            </div>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => setVesselSensor('sentinel1')}
                className={`px-1.5 py-0.5 text-[8px] font-mono rounded transition-colors ${
                  vesselSensor === 'sentinel1'
                    ? 'bg-teal-500 text-navy-950 font-bold'
                    : 'text-gray-400 hover:text-white bg-navy-800'
                }`}
              >
                SAR RADAR
              </button>
              <button
                type="button"
                onClick={() => setVesselSensor('sentinel2')}
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

          <div className="relative w-full h-44 bg-[#06101e] flex items-center justify-center overflow-hidden">
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
            {/* Tactical Overlay */}
            <div className="absolute inset-0 pointer-events-none p-2 flex flex-col justify-between">
              <div className="flex justify-between text-[8px] font-mono text-teal-400/90 drop-shadow">
                <span>GSD: 10m · SWATH: 250km</span>
                <span>{selectedVessel.lat.toFixed(4)}°N, {selectedVessel.lon.toFixed(4)}°E</span>
              </div>
              <div className="flex justify-between items-end text-[8px] font-mono">
                <span className="bg-black/70 px-1.5 py-0.5 rounded text-[8px] text-teal-300 border border-teal-500/40">
                  🎯 TARGET ACQUIRED
                </span>
                <span className="text-gray-400 bg-black/60 px-1 rounded text-[7px]">
                  Copernicus Process API
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Pills */}
        <div className="grid grid-cols-2 gap-2">
          <div
            className="p-2.5 rounded border flex flex-col"
            style={{ background: 'var(--navy-800)', borderColor: 'var(--navy-500)' }}
          >
            <span className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Threat Index</span>
            <span className="font-bold text-sm font-mono mt-0.5" style={{ color: selectedVessel.risk_score > 0.7 ? 'var(--red-400)' : 'var(--teal-500)' }}>
              {(selectedVessel.risk_score * 100).toFixed(0)}%
            </span>
          </div>
          <div
            className="p-2.5 rounded border flex flex-col"
            style={{ background: 'var(--navy-800)', borderColor: 'var(--navy-500)' }}
          >
            <span className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>Speed / Course</span>
            <span className="font-bold text-sm text-white font-mono mt-0.5">
              {selectedVessel.speed_knots?.toFixed(1) ?? '0.0'} kts / {selectedVessel.course_deg != null ? `${selectedVessel.course_deg.toFixed(0)}°` : '—'}
            </span>
          </div>
        </div>

        {/* Risk Breakdown */}
        <div className="space-y-3">
          <h3
            className="text-[10px] font-bold uppercase tracking-widest border-b pb-1"
            style={{ color: 'var(--teal-400)', borderColor: 'var(--navy-500)' }}
          >
            4-Signal Risk Decomposition
          </h3>

          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span style={{ color: 'var(--text-secondary)' }}>AIS Dark Gap</span>
              <span className="font-mono font-bold" style={{ color: selectedVessel.is_dark ? 'var(--red-400)' : 'var(--teal-500)' }}>
                {selectedVessel.ais_gap_minutes} min
              </span>
            </div>
            <div className="w-full rounded-full h-1.5 overflow-hidden" style={{ background: 'var(--navy-900)' }}>
              <div
                className="h-1.5 rounded-full"
                style={{
                  width: `${Math.min((selectedVessel.ais_gap_minutes / 60) * 100, 100)}%`,
                  backgroundColor: selectedVessel.ais_gap_minutes > 30 ? 'var(--red-500)' : 'var(--teal-500)',
                }}
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span style={{ color: 'var(--text-secondary)' }}>Vessel Type Threat</span>
              <span className="font-mono text-white">{selectedVessel.vessel_type_label}</span>
            </div>
            <div className="w-full rounded-full h-1.5 overflow-hidden" style={{ background: 'var(--navy-900)' }}>
              <div
                className="h-1.5 rounded-full"
                style={{
                  width: selectedVessel.vessel_type >= 80 && selectedVessel.vessel_type <= 89 ? '85%' : '35%',
                  backgroundColor: selectedVessel.vessel_type >= 80 && selectedVessel.vessel_type <= 89 ? 'var(--amber-500)' : 'var(--teal-500)',
                }}
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span style={{ color: 'var(--text-secondary)' }}>MPA Sanctuary Proximity</span>
              <span className="font-mono" style={{ color: selectedVessel.in_mpa ? 'var(--red-400)' : 'var(--emerald-400)' }}>
                {selectedVessel.in_mpa ? 'Breach' : 'Clear'}
              </span>
            </div>
            <div className="w-full rounded-full h-1.5 overflow-hidden" style={{ background: 'var(--navy-900)' }}>
              <div
                className="h-1.5 rounded-full"
                style={{
                  width: selectedVessel.in_mpa ? '100%' : '10%',
                  backgroundColor: selectedVessel.in_mpa ? 'var(--red-500)' : 'var(--emerald-500)',
                }}
              />
            </div>
          </div>
        </div>

        {/* Telemetry / Observation Info */}
        <div className="space-y-2">
          <h3
            className="text-[10px] font-bold uppercase tracking-widest border-b pb-1"
            style={{ color: 'var(--teal-400)', borderColor: 'var(--navy-500)' }}
          >
            Spatial Telemetry
          </h3>
          <div
            className="p-2.5 rounded border text-xs font-mono space-y-1"
            style={{ background: 'var(--navy-800)', borderColor: 'var(--navy-500)', color: 'var(--text-mono)' }}
          >
            <div className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>LATITUDE:</span>
              <span>{selectedVessel.lat.toFixed(4)}°N</span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>LONGITUDE:</span>
              <span>{selectedVessel.lon.toFixed(4)}°E</span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>LAST REPORT:</span>
              <span>{selectedVessel.last_seen ? new Date(selectedVessel.last_seen).toLocaleTimeString() : 'LIVE'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div
        className="p-3.5 border-t space-y-2"
        style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}
      >
        <button
          type="button"
          onClick={() => openDossier('latest')}
          className="w-full font-bold text-xs py-2 px-3 rounded transition-colors flex justify-center items-center gap-1.5 shadow border"
          style={{
            background: 'linear-gradient(90deg, rgba(0, 212, 232, 0.2), rgba(0, 212, 232, 0.4))',
            borderColor: 'var(--teal-500)',
            color: 'var(--teal-300)',
          }}
        >
          <span>⚖️ Generate Legal Prosecution Dossier</span>
        </button>
        <button
          type="button"
          onClick={() => selectVessel(null)}
          className="w-full font-bold text-xs py-2 px-3 rounded transition-colors flex justify-center items-center gap-1.5 shadow"
          style={{
            background: 'var(--teal-500)',
            color: 'var(--navy-950)',
          }}
        >
          <span>✓ Close Drawer</span>
        </button>
      </div>
    </div>
  );
}

