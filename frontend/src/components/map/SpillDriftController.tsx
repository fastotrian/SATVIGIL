import React, { useEffect } from 'react';
import { useAlertStore } from '../../store/alertStore';

const TIME_STEPS = [0, 6, 12, 18, 24, 36, 48, 72];

export function SpillDriftController() {
  const {
    driftForecast,
    selectedDriftHour,
    isDriftSimActive,
    isDriftPlaying,
    loadDriftForecast,
    setSelectedDriftHour,
    toggleDriftSim,
    toggleDriftPlaying,
    getActiveDriftStep,
    openDossier,
  } = useAlertStore();

  // Load forecast on mount or when activated
  useEffect(() => {
    if (isDriftSimActive && !driftForecast) {
      loadDriftForecast();
    }
  }, [isDriftSimActive, driftForecast, loadDriftForecast]);

  // Autoplay animation loop
  useEffect(() => {
    if (!isDriftPlaying || !isDriftSimActive) return;

    const interval = setInterval(() => {
      setSelectedDriftHour(
        (() => {
          const currentIndex = TIME_STEPS.indexOf(selectedDriftHour);
          const nextIndex = (currentIndex + 1) % TIME_STEPS.length;
          return TIME_STEPS[nextIndex];
        })()
      );
    }, 1400);

    return () => clearInterval(interval);
  }, [isDriftPlaying, isDriftSimActive, selectedDriftHour, setSelectedDriftHour]);

  if (!isDriftSimActive) {
    return null;
  }

  const activeStep = getActiveDriftStep();
  const initialArea = driftForecast?.initial_area_km2 ?? 4.82;
  const currentArea = activeStep?.area_km2 ?? initialArea;
  const expansionPct = Math.round(((currentArea - initialArea) / initialArea) * 100);

  return (
    <div
      className="absolute bottom-5 left-1/2 -translate-x-1/2 z-30 w-[94%] max-w-4xl rounded-xl border shadow-2xl overflow-hidden pointer-events-auto backdrop-blur-xl animate-in fade-in slide-in-from-bottom-5 duration-300"
      style={{
        background: 'rgba(6, 14, 28, 0.92)',
        borderColor: 'var(--amber-500)',
        boxShadow: '0 0 30px rgba(0, 0, 0, 0.8), 0 0 15px rgba(245, 158, 11, 0.2)',
      }}
    >
      {/* Top Banner Header */}
      <div
        className="px-4 py-2 border-b flex items-center justify-between gap-3 text-xs font-mono"
        style={{
          background: 'linear-gradient(90deg, rgba(15, 31, 61, 0.9), rgba(245, 158, 11, 0.15))',
          borderColor: 'rgba(245, 158, 11, 0.3)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-amber-300 font-bold uppercase tracking-wider">
            INCOIS-OOSA 72h Forward Spill Trajectory Simulator
          </span>
          <span className="text-[10px] text-gray-400 hidden sm:inline">
            (Arabian Sea ECMWF/ROMS Surface Currents + 3% Wind Drag)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => openDossier('latest')}
            className="px-2 py-0.5 rounded text-[10px] font-bold text-cyan-300 bg-cyan-950/80 border border-cyan-500/40 hover:bg-cyan-900 transition-colors"
          >
            ⚖️ Legal Dossier
          </button>
          <button
            type="button"
            onClick={() => toggleDriftSim(false)}
            className="text-gray-400 hover:text-white text-sm px-1.5 transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Main Control Scrubber & Step Bar */}
      <div className="p-3.5 space-y-3 font-mono">
        {/* Timeline Scrubber Controls */}
        <div className="flex items-center gap-3">
          {/* Play/Pause Button */}
          <button
            type="button"
            onClick={toggleDriftPlaying}
            className="px-3 py-1.5 rounded text-xs font-bold font-mono transition-all flex items-center gap-1.5 border shadow"
            style={{
              background: isDriftPlaying ? 'var(--amber-500)' : 'var(--navy-800)',
              color: isDriftPlaying ? 'var(--navy-950)' : 'var(--amber-400)',
              borderColor: 'var(--amber-500)',
            }}
          >
            <span>{isDriftPlaying ? '⏸ Pause' : '▶ Play Drift'}</span>
          </button>

          {/* Time Step Buttons */}
          <div className="flex-1 grid grid-cols-8 gap-1">
            {TIME_STEPS.map((hr) => {
              const isSelected = selectedDriftHour === hr;
              return (
                <button
                  key={hr}
                  type="button"
                  onClick={() => {
                    setSelectedDriftHour(hr);
                  }}
                  className="py-1 px-1 rounded text-[10px] font-bold transition-all border text-center"
                  style={{
                    background: isSelected
                      ? 'var(--amber-500)'
                      : hr === 0
                      ? 'rgba(0, 212, 232, 0.15)'
                      : 'rgba(15, 31, 61, 0.6)',
                    color: isSelected ? 'var(--navy-950)' : isSelected || hr === 0 ? 'var(--teal-400)' : '#E2E8F0',
                    borderColor: isSelected
                      ? 'var(--amber-400)'
                      : hr === 0
                      ? 'rgba(0, 212, 232, 0.4)'
                      : 'var(--navy-600)',
                    transform: isSelected ? 'scale(1.04)' : 'scale(1)',
                  }}
                >
                  {hr === 0 ? 'NOW' : `+${hr}h`}
                </button>
              );
            })}
          </div>
        </div>

        {/* Dynamic Telemetry Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {/* 1. Time Offset */}
          <div className="p-2 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
            <span className="text-[9px] text-gray-400 block">FORECAST TIMELINE</span>
            <span className="font-bold text-amber-400 text-sm block">
              {selectedDriftHour === 0 ? 'T+0 HOURS (DETECTION)' : `T+${selectedDriftHour} HOURS FORWARD`}
            </span>
            <span className="text-[10px] text-gray-400 block">
              {activeStep?.forecast_time ? new Date(activeStep.forecast_time).toLocaleTimeString() : 'UTC'}
            </span>
          </div>

          {/* 2. Projected Slick Area */}
          <div className="p-2 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
            <span className="text-[9px] text-gray-400 block">PROJECTED SLICK FOOTPRINT</span>
            <span className="font-bold text-cyan-400 text-sm block">
              {currentArea.toFixed(2)} km²
            </span>
            <span className="text-[10px] text-amber-300 block">
              {expansionPct > 0 ? `+${expansionPct}% Spreading Expansion` : 'Origin Baseline'}
            </span>
          </div>

          {/* 3. Drift Physics */}
          <div className="p-2 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
            <span className="text-[9px] text-gray-400 block">HYDRODYNAMIC VECTORS</span>
            <span className="font-bold text-white text-xs block">
              Drift: {activeStep?.drift_speed_knots ?? 1.15} kts @ {activeStep?.drift_heading_deg ?? 118}°
            </span>
            <span className="text-[10px] text-gray-400 block">
              Wind: {activeStep?.wind_speed_knots ?? 15.2} kts WSW
            </span>
          </div>

          {/* 4. Centroid Coordinates */}
          <div className="p-2 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
            <span className="text-[9px] text-gray-400 block">SLICK CORE CENTROID</span>
            <span className="font-bold text-emerald-400 text-xs block">
              {activeStep?.centroid_lat !== undefined && activeStep?.centroid_lon !== undefined
                ? `${activeStep.centroid_lat.toFixed(3)}°N, ${activeStep.centroid_lon.toFixed(3)}°E`
                : '19.200°N, 71.500°E'}
            </span>
            <span className="text-[10px] text-gray-400 block">Arabian Sea Sector</span>
          </div>
        </div>

        {/* Threat Warning Banner if close to assets */}
        {activeStep && activeStep.active_warnings.length > 0 && (
          <div className="p-2.5 rounded border border-red-500/60 bg-red-950/70 text-xs space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-red-400 font-bold animate-pulse">⚠️ CRITICAL ASSET DRIFT IMPACT WARNING:</span>
            </div>
            <div className="flex flex-wrap gap-2 text-[11px]">
              {activeStep.active_warnings.map((w, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded font-bold border"
                  style={{
                    background: w.threat_level === 'HIGH' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)',
                    borderColor: w.threat_level === 'HIGH' ? 'var(--red-500)' : 'var(--amber-500)',
                    color: w.threat_level === 'HIGH' ? '#FCA5A5' : '#FDE68A',
                  }}
                >
                  {w.asset_name}: {w.distance_nm} NM {w.time_to_impact_hours ? `· ETA: ${w.time_to_impact_hours}h` : ''}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Actionable Containment Recommendation */}
        {activeStep?.containment_recommendation && (
          <div className="text-[11px] text-gray-300 flex items-center justify-between gap-2 border-t pt-2" style={{ borderColor: 'var(--navy-700)' }}>
            <div className="flex items-center gap-1.5">
              <span className="text-amber-400">🛡️ ICG Action:</span>
              <span>{activeStep.containment_recommendation}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
