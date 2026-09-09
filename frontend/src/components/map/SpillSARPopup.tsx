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

interface Props {
  spill: SpillEvent;
  onClose: () => void;
  /** Screen position in px (from map click event) */
  screenX?: number;
  screenY?: number;
}

export function SpillSARPopup({ spill, onClose, screenX, screenY }: Props) {
  const topSuspect = spill.top_candidates?.[0];
  const confidencePct = Math.round(spill.confidence * 100);
  const sarImageSrc = spill.sar_image_url ?? '/sar_spill_bombay_high.jpg';

  const detectedDate = new Date(spill.detected_at);
  const dateStr = detectedDate.toUTCString().replace(' GMT', ' UTC');

  return (
    <div
      id={`sar-popup-${spill.id}`}
      className="absolute z-40 w-[420px] pointer-events-auto"
      style={{
        // Position near click, clamp to screen edges
        top: Math.min(screenY ?? 120, window.innerHeight - 600),
        left: Math.min(screenX ?? 40, window.innerWidth - 450),
      }}
    >
      <div className="bg-gray-900/97 backdrop-blur-xl border border-cyan-900/60 rounded-2xl shadow-2xl overflow-hidden">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-cyan-950 to-blue-950 border-b border-cyan-800/40">
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
            className="w-full h-48 object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
          {/* Overlay badges */}
          <div className="absolute top-2 left-2 flex gap-1.5">
            <span className="bg-black/70 text-cyan-300 text-xs font-mono px-2 py-1 rounded">
              SENTINEL-1B SAR-C · VV
            </span>
          </div>
          <div className="absolute top-2 right-2">
            <span className="bg-red-900/80 text-red-300 text-xs font-bold px-2 py-1 rounded border border-red-700">
              {confidencePct}% Confidence
            </span>
          </div>
          <div className="absolute bottom-2 left-2">
            <span className="bg-black/70 text-gray-300 text-xs font-mono px-2 py-1 rounded">
              {spill.sentinel_scene_id.slice(0, 26)}…
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
              <div className="text-emerald-400 font-bold text-sm leading-tight">
                {spill.lat.toFixed(2)}°N
              </div>
              <div className="text-emerald-400 font-bold text-sm">{spill.lon.toFixed(2)}°E</div>
              <div className="text-gray-400 text-xs">coordinates</div>
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
          <div className="flex gap-2">
            <button
              id="spill-dispatch-btn"
              className="flex-1 py-2 text-xs font-medium bg-red-800 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              🚨 Dispatch Coast Guard
            </button>
            <button
              id="spill-evidence-btn"
              className="flex-1 py-2 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg transition-colors"
            >
              📄 Download Evidence
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
