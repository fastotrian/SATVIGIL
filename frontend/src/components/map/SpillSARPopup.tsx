/**
 * SATVIGIL — Oil Spill SAR Image Popup
 *
 * Appears when user clicks on an oil spill polygon on the map.
 * Shows:
 *   - Annotated Sentinel-1 SAR image with bounding box
 *   - Spill metadata: ID, area, confidence, scene ID, detected_at
 *   - Top suspect vessel with 4-signal score breakdown
 *   - Dismiss button
 */
import React from 'react';
import type { SpillEvent } from '../../types/maritime';
import { RISK_COLORS } from '../../constants/riskColors';
import { useAlertStore } from '../../store/alertStore';

interface Props {
  spill: SpillEvent;
  onClose: () => void;
  onLaunchDrift?: () => void;
  /** Screen position in px (from map click event) */
  screenX?: number;
  screenY?: number;
}

export function SpillSARPopup({ spill, onClose, onLaunchDrift, screenX, screenY }: Props) {
  const { openDossier } = useAlertStore();
  const topSuspect = spill.top_candidates?.[0];
  const confidencePct = Math.round(spill.confidence * 100);
  const sarImageSrc = spill.sar_image_url ?? '/sar_spill_bombay_high.jpg';

  const detectedDate = new Date(spill.detected_at);
  const dateStr = detectedDate.toUTCString().replace(' GMT', ' UTC');

  return (
    <div
      id={`sar-popup-${spill.id}`}
      className="absolute z-40 w-[420px] max-h-[calc(100vh-36px)] pointer-events-auto flex flex-col"
      style={{
        // Position popup higher up so all bottom action buttons are always clearly visible above screen edge
        top: Math.max(16, Math.min((screenY ?? 100) - 240, window.innerHeight - 660)),
        left: Math.max(16, Math.min(screenX ?? 40, window.innerWidth - 450)),
      }}
    >
      <div className="bg-[#081326]/95 backdrop-blur-xl border border-cyan-500/40 rounded-2xl shadow-2xl overflow-y-auto max-h-full">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-cyan-950 to-blue-950 border-b border-cyan-800/40">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-cyan-300 font-bold text-sm tracking-wider uppercase">
              Oil Spill Detected
            </span>
            <span className="text-gray-500 text-xs font-mono">{spill.id}</span>
          </div>
          <button
            id="sar-popup-close"
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-lg leading-none"
          >
            ×
          </button>
        </div>

        {/* ── SAR Image ── */}
        <div className="relative">
          <img
            src={sarImageSrc}
            alt={`SAR satellite image — ${spill.id}`}
            className="w-full h-40 object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
          {/* Overlay badges */}
          <div className="absolute top-2 left-2 flex flex-col gap-1">
            <span className="bg-black/80 text-cyan-300 text-[10px] font-mono px-2 py-0.5 rounded border border-cyan-500/40">
              🛰️ Sentinel-1C C-SAR (IW Swath, VV/VH)
            </span>
            <span className="bg-black/80 text-emerald-300 text-[9px] font-mono px-2 py-0.5 rounded border border-emerald-500/40">
              📍 19.2000°N, 71.5000°E · Bombay High
            </span>
          </div>
          <div className="absolute top-2 right-2">
            <span className="bg-red-900/80 text-red-300 text-[10px] font-bold font-mono px-2 py-0.5 rounded border border-red-700">
              {confidencePct}% Confidence
            </span>
          </div>
          <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center px-2 py-1 rounded bg-black/80 text-[9px] font-mono text-gray-300 border border-cyan-900/50">
            <span className="truncate max-w-[200px]" title={spill.sentinel_scene_id}>
              {spill.sentinel_scene_id}
            </span>
            <span className="text-cyan-400 font-bold shrink-0">
              Track 142 (Desc)
            </span>
          </div>
        </div>

        {/* ── Spill Metadata ── */}
        <div className="px-4 pt-3 pb-2">
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="bg-gray-800/60 rounded-lg p-2.5 text-center">
              <div className="text-cyan-400 font-bold text-lg">{spill.area_km2.toFixed(2)}</div>
              <div className="text-gray-400 text-xs">km² area</div>
            </div>
            <div className="bg-gray-800/60 rounded-lg p-2.5 text-center">
              <div className="text-yellow-400 font-bold text-lg">{confidencePct}%</div>
              <div className="text-gray-400 text-xs">ML confidence</div>
            </div>
            <div className="bg-gray-800/60 rounded-lg p-2.5 text-center">
              <div className="text-emerald-400 font-bold text-xs leading-tight font-mono">
                {spill.lat.toFixed(4)}°N
              </div>
              <div className="text-emerald-400 font-bold text-xs font-mono">{spill.lon.toFixed(4)}°E</div>
              <div className="text-gray-400 text-[10px]">Bombay High</div>
            </div>
          </div>

          <div className="text-gray-500 text-xs mb-3 font-mono">
            🕐 {dateStr}
          </div>

          {/* ── Top Suspect Vessel ── */}
          {topSuspect && (
            <div className="bg-red-950/50 border border-red-800/50 rounded-xl p-3 mb-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-red-400">🚢</span>
                  <span className="text-white font-semibold text-sm">{topSuspect.vessel_name}</span>
                  <span className="text-gray-500 text-xs">MMSI: {topSuspect.mmsi}</span>
                </div>
                <div
                  className="text-xs font-bold px-2 py-1 rounded-full"
                  style={{
                    backgroundColor: `${RISK_COLORS.CRITICAL}30`,
                    color: RISK_COLORS.CRITICAL,
                    border: `1px solid ${RISK_COLORS.CRITICAL}60`,
                  }}
                >
                  {Math.round(topSuspect.risk_score * 100)}% risk
                </div>
              </div>

              {/* 4-signal score breakdown bars */}
              <div className="space-y-1.5">
                <ScoreBar label="Proximity" value={1 - topSuspect.distance_km / 30} color="#38BDF8" weight="40%" />
                <ScoreBar label="Vessel Type" value={topSuspect.type_risk} color="#F97316" weight="25%" />
                <ScoreBar label="Heading Align" value={topSuspect.heading_score} color="#A78BFA" weight="20%" />
                <ScoreBar
                  label="AIS Anomaly"
                  value={topSuspect.behavioral_anomaly ? 1 : 0}
                  color="#EF4444"
                  weight="15%"
                />
              </div>

              <div className="mt-2 text-xs text-gray-500">
                📍 {topSuspect.distance_km.toFixed(1)} km from spill center
                {topSuspect.behavioral_anomaly && (
                  <span className="ml-2 text-red-400 font-medium">· AIS dark gap detected</span>
                )}
              </div>
            </div>
          )}

          {/* ── Action Buttons ── */}
          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <button
                id="spill-evidence-btn"
                onClick={() => openDossier('latest')}
                className="flex-1 py-1.5 text-xs font-bold font-mono bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/60 text-cyan-300 rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow"
              >
                <span>⚖️ Legal Dossier</span>
              </button>
              {onLaunchDrift && (
                <button
                  id="spill-drift-btn"
                  onClick={onLaunchDrift}
                  className="flex-1 py-1.5 text-xs font-bold font-mono bg-amber-950/80 hover:bg-amber-900 border border-amber-500/60 text-amber-300 rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow"
                >
                  <span>🌊 72h Drift Sim</span>
                </button>
              )}
            </div>

            <button
              id="spill-dispatch-btn"
              onClick={() => {
                alert('🚨 Operational Alert Transmitted to Indian Coast Guard Western Command (ICGS Samudra Prahari tasked).');
              }}
              className="w-full py-1.5 text-xs font-bold font-mono bg-red-900/80 hover:bg-red-800 border border-red-500/60 text-red-200 rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow"
            >
              <span>🚨 Task ICGS Samudra Prahari</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


// ── Score Bar sub-component ───────────────────────────────
function ScoreBar({ label, value, color, weight }: {
  label: string;
  value: number;
  color: string;
  weight: string;
}) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div className="flex items-center gap-2">
      <span className="text-gray-400 text-xs w-24 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct * 100}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-gray-500 text-xs w-8 text-right">{Math.round(pct * 100)}%</span>
      <span className="text-gray-600 text-xs w-8">({weight})</span>
    </div>
  );
}
