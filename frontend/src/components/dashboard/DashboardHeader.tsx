/**
 * SATVIGIL — Dashboard Header Component
 * Top operational bar with branding, live telemetry counters, and feed status.
 */
import React from 'react';
import { useAlertStore } from '../../store/alertStore';

export function DashboardHeader() {
  const { vessels, isConnected, isAudioMuted, toggleAudio } = useAlertStore();

  const criticalCount = vessels.filter((v) => v.risk_level === 'CRITICAL').length;
  const warningCount = vessels.filter((v) => v.risk_level === 'WARNING').length;
  const normalCount = vessels.filter((v) => v.risk_level === 'NORMAL').length;

  return (
    <header className="h-14 w-full bg-gray-900 border-b border-gray-800 px-4 flex items-center justify-between z-20 shrink-0">
      {/* Left: Branding */}
      <div className="flex items-center space-x-3">
        <span className="text-2xl" role="img" aria-label="satellite">🛰️</span>
        <div className="flex flex-col">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-wider text-white">SATVIGIL</span>
            <span className="text-[10px] font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800 rounded px-1.5 py-0.5">
              SIH 2026
            </span>
          </div>
          <span className="text-xs text-gray-400 -mt-1">Maritime & Geo-Intelligence Platform</span>
        </div>
      </div>

      {/* Center: Live Threat Status Pills */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 bg-red-950/70 border border-red-800/80 rounded-full px-3 py-1 text-xs text-red-300 font-medium">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
          <span>{criticalCount} Critical</span>
        </div>

        <div className="flex items-center space-x-1.5 bg-orange-950/70 border border-orange-800/80 rounded-full px-3 py-1 text-xs text-orange-300 font-medium">
          <span className="w-2 h-2 rounded-full bg-orange-500"></span>
          <span>{warningCount} Warning</span>
        </div>

        <div className="flex items-center space-x-1.5 bg-emerald-950/70 border border-emerald-800/80 rounded-full px-3 py-1 text-xs text-emerald-300 font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>{normalCount} Clear</span>
        </div>
      </div>

      {/* Right: Feeds & Sensor Status */}
      <div className="flex items-center space-x-4 text-xs">
        <div className="flex items-center space-x-1.5 bg-gray-800/80 border border-gray-700/60 rounded px-2.5 py-1 text-gray-300">
          <span className="text-gray-400">🛰️ Sentinel-2</span>
          <span className="text-gray-500">·</span>
          <span className="text-gray-400">Pass: 3h ago</span>
        </div>

        <div className="flex items-center space-x-2">
          {isConnected ? (
            <div className="flex items-center space-x-1.5 text-emerald-400 font-mono">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></span>
              <span>AIS LIVE</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 text-red-400 font-mono">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
              <span>OFFLINE</span>
            </div>
          )}

          {/* Audio Alarm Toggle */}
          <button
            onClick={toggleAudio}
            className={`p-1.5 rounded transition-colors ${
              isAudioMuted ? 'text-red-400 bg-red-950/50 hover:bg-red-900/50' : 'text-emerald-400 bg-emerald-950/50 hover:bg-emerald-900/50'
            }`}
            title={isAudioMuted ? "Unmute Alarms" : "Mute Alarms"}
          >
            {isAudioMuted ? '🔇' : '🔊'}
          </button>
        </div>
      </div>
    </header>
  );
}
