/**
 * SATVIGIL — Dashboard Header
 * Command center top bar with telemetry indicators, sensor badges, quick sector jump pills, and live UTC clock.
 */
import React, { useEffect, useState } from 'react';
import { useAlertStore } from '../../store/alertStore';

// ── Live UTC Clock ─────────────────────────────────────────────────────────
function LiveClock() {
  const [time, setTime] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-navy-800/80 border border-navy-500/60">
      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
      <span className="font-mono text-xs font-bold tracking-wider text-cyan-300">
        {time.toUTCString().split(' ').slice(4, 5).join('')} UTC
      </span>
    </div>
  );
}

// ── Satellite SVG Icon ─────────────────────────────────────────────────────
function SatIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 28 28" fill="none" aria-hidden>
      <rect x="11" y="11" width="6" height="6" rx="1" fill="var(--teal-500)" />
      <rect x="2"  y="12.5" width="7" height="3" rx="1" fill="var(--navy-400)" />
      <rect x="19" y="12.5" width="7" height="3" rx="1" fill="var(--navy-400)" />
      <line x1="14" y1="11" x2="14" y2="5" stroke="var(--teal-400)" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="14" cy="4" r="1.5" fill="var(--teal-500)" />
      <circle cx="14" cy="14" r="11" stroke="var(--teal-500)" strokeWidth="0.75" strokeOpacity="0.25" />
      <circle cx="14" cy="14" r="7" stroke="var(--teal-500)" strokeWidth="0.75" strokeOpacity="0.40" />
    </svg>
  );
}

export function DashboardHeader({ onJumpSector }: { onJumpSector?: (sector: string) => void }) {
  const { vessels, alerts, isConnected, isAudioMuted, toggleAudio } = useAlertStore();

  const criticalCount = alerts.filter((a) => a.risk_level === 'CRITICAL' && !a.acknowledged).length;
  const warningCount  = alerts.filter((a) => a.risk_level === 'WARNING'  && !a.acknowledged).length;
  const darkCount     = vessels.filter((v) => v.is_dark).length;
  const mpaCount      = vessels.filter((v) => v.in_mpa).length;
  const totalVessels  = vessels.length;

  return (
    <header
      className="shrink-0 z-20 flex flex-col select-none"
      style={{ background: 'var(--navy-950)', borderBottom: '1px solid var(--navy-500)' }}
    >
      {/* ── Top Bar ──────────────────────────────────────────────────────── */}
      <div className="h-13 px-3.5 py-1.5 flex items-center justify-between gap-3">

        {/* Left: Branding + Sensor Badges */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5">
            <SatIcon />
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span
                  className="font-bold text-base tracking-[0.16em] uppercase"
                  style={{ color: 'var(--teal-400)', letterSpacing: '0.18em' }}
                >
                  SATVIGIL
                </span>
                <span
                  className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded tracking-widest border"
                  style={{
                    background: 'rgba(0,212,232,0.08)',
                    borderColor: 'rgba(0,212,232,0.35)',
                    color: 'var(--teal-400)',
                  }}
                >
                  DEFENSE &amp; MARITIME INTEL
                </span>
              </div>
              <span className="text-[10px] text-gray-400 tracking-wide">
                Autonomous Satellite Hydrocarbon &amp; Dark Vessel Detection
              </span>
            </div>
          </div>

          {/* Vertical Separator */}
          <div className="w-px h-7 bg-navy-600/80 mx-1 hidden lg:block" />

          {/* Sensor Telemetry Badges */}
          <div className="hidden xl:flex items-center gap-2 text-[10px] font-mono">
            {/* Sentinel-1C C-SAR */}
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 rounded border"
              style={{ background: 'rgba(15,31,61,0.8)', borderColor: 'var(--navy-500)', color: 'var(--text-secondary)' }}
            >
              <span className="text-cyan-400">🛰️</span>
              <span className="font-semibold text-gray-200">Sentinel-1C C-SAR</span>
              <span className="text-emerald-400 font-bold">● ACTIVE</span>
            </div>

            {/* GFW AIS */}
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 rounded border"
              style={{ background: 'rgba(15,31,61,0.8)', borderColor: 'var(--navy-500)', color: 'var(--text-secondary)' }}
            >
              <span className="text-emerald-400">🚢</span>
              <span className="font-semibold text-gray-200">GFW AIS</span>
              <span className="text-cyan-400 font-bold">{totalVessels > 0 ? `${(totalVessels / 1000).toFixed(1)}K` : '11.3K'}</span>
            </div>

            {/* NASA VIIRS */}
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 rounded border"
              style={{ background: 'rgba(15,31,61,0.8)', borderColor: 'var(--navy-500)', color: 'var(--text-secondary)' }}
            >
              <span className="text-amber-400">🔥</span>
              <span className="font-semibold text-gray-200">NASA VIIRS</span>
              <span className="text-amber-400 font-bold">174 Hotspots</span>
            </div>
          </div>
        </div>

        {/* Center/Right: Quick Threat Pills */}
        <div className="flex items-center gap-2">
          {/* Active Spills */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-bold border transition-all"
            style={{
              borderColor: 'rgba(239,68,68,0.6)',
              color: '#FCA5A5',
              background: 'rgba(239,68,68,0.15)',
            }}
          >
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            <span>1 SPILL (4.8 km²)</span>
          </div>

          {/* Dark Vessels */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-bold border"
            style={{
              borderColor: darkCount > 0 ? 'rgba(245,158,11,0.6)' : 'var(--navy-500)',
              color: darkCount > 0 ? '#FDE68A' : 'var(--text-dim)',
              background: darkCount > 0 ? 'rgba(245,158,11,0.12)' : 'transparent',
            }}
          >
            <span>📡</span>
            <span>{darkCount} DARK</span>
          </div>

          {/* MPA Breaches */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-bold border"
            style={{
              borderColor: mpaCount > 0 ? 'rgba(192,132,252,0.6)' : 'var(--navy-500)',
              color: mpaCount > 0 ? '#E9D5FF' : 'var(--text-dim)',
              background: mpaCount > 0 ? 'rgba(192,132,252,0.12)' : 'transparent',
            }}
          >
            <span>🏊</span>
            <span>{mpaCount} MPA</span>
          </div>

          {/* Audio toggle */}
          <button
            id="audio-mute-btn"
            onClick={toggleAudio}
            title={isAudioMuted ? 'Unmute Alarms' : 'Mute Alarms'}
            className="p-1.5 rounded border transition-all hover:opacity-80 ml-1"
            style={{
              background: isAudioMuted ? 'rgba(220,38,38,0.15)' : 'rgba(16,185,129,0.10)',
              borderColor: isAudioMuted ? 'rgba(220,38,38,0.4)' : 'rgba(16,185,129,0.3)',
              color: isAudioMuted ? 'var(--red-400)' : 'var(--emerald-400)',
            }}
          >
            {isAudioMuted ? '🔇' : '🔊'}
          </button>

          {/* Clock */}
          <LiveClock />
        </div>
      </div>
    </header>
  );
}
