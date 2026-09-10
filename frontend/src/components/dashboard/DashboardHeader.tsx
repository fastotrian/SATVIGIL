/**
 * SATVIGIL — Dashboard Header
 * Military command center top bar with branding, live threat counters, and feed status.
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
    <span className="font-data text-xs tracking-widest" style={{ color: 'var(--text-mono)' }}>
      {time.toUTCString().split(' ').slice(4, 5).join('')} UTC
    </span>
  );
}

// ── Satellite SVG Icon ─────────────────────────────────────────────────────
function SatIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden>
      {/* Satellite body */}
      <rect x="11" y="11" width="6" height="6" rx="1" fill="var(--teal-500)" />
      {/* Solar panels */}
      <rect x="2"  y="12.5" width="7" height="3" rx="1" fill="var(--navy-400)" />
      <rect x="19" y="12.5" width="7" height="3" rx="1" fill="var(--navy-400)" />
      {/* Antenna */}
      <line x1="14" y1="11" x2="14" y2="5"  stroke="var(--teal-400)" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="14" cy="4" r="1.5" fill="var(--teal-500)" />
      {/* Signal rings */}
      <circle cx="14" cy="14" r="11" stroke="var(--teal-500)" strokeWidth="0.75" strokeOpacity="0.25" />
      <circle cx="14" cy="14" r="7"  stroke="var(--teal-500)" strokeWidth="0.75" strokeOpacity="0.40" />
    </svg>
  );
}

export function DashboardHeader() {
  const { vessels, alerts, isConnected, isAudioMuted, toggleAudio } = useAlertStore();

  const criticalCount = alerts.filter((a) => a.risk_level === 'CRITICAL' && !a.acknowledged).length;
  const warningCount  = alerts.filter((a) => a.risk_level === 'WARNING'  && !a.acknowledged).length;
  const darkCount     = vessels.filter((v) => v.is_dark).length;
  const mpaCount      = vessels.filter((v) => v.in_mpa).length;
  const totalVessels  = vessels.length;

  return (
    <header
      className="shrink-0 z-20 flex flex-col"
      style={{ background: 'var(--navy-950)', borderBottom: '1px solid var(--navy-500)' }}
    >
      {/* ── Main Header Row ──────────────────────────────────────────────── */}
      <div className="h-14 px-4 flex items-center justify-between">

        {/* Left: Branding */}
        <div className="flex items-center gap-3">
          <SatIcon />
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span
                className="font-bold text-lg tracking-[0.15em] uppercase"
                style={{ color: 'var(--teal-500)', fontFamily: 'var(--font-ui)', letterSpacing: '0.18em' }}
              >
                SATVIGIL
              </span>
              <span
                className="text-[9px] font-bold px-1.5 py-0.5 rounded tracking-widest border"
                style={{
                  background: 'rgba(0,212,232,0.08)',
                  borderColor: 'rgba(0,212,232,0.35)',
                  color: 'var(--teal-500)',
                }}
              >
                SIH 2026
              </span>
            </div>
            <span className="text-[10px] tracking-wider" style={{ color: 'var(--text-secondary)' }}>
              Maritime &amp; Geo-Intelligence Platform
            </span>
          </div>
        </div>

        {/* Center: Live Threat Stat Chips */}
        <div className="flex items-center gap-2">

          {/* Vessels Tracked */}
          <div
            className="stat-chip"
            style={{ borderColor: 'rgba(0,212,232,0.3)', color: 'var(--teal-500)', background: 'rgba(0,212,232,0.08)' }}
          >
            <span>🛥</span>
            <span className="font-data">{totalVessels > 0 ? `${(totalVessels / 1000).toFixed(0)}K` : '--'}</span>
            <span style={{ color: 'var(--text-secondary)' }}>Vessels</span>
          </div>

          {/* Active Spills */}
          <div
            className="stat-chip animate-pulse-red"
            style={{ borderColor: 'rgba(239,68,68,0.5)', color: 'var(--red-400)', background: 'rgba(239,68,68,0.10)' }}
          >
            <span>🛢</span>
            <span className="font-data">1</span>
            <span>Spill</span>
          </div>

          {/* Dark Vessels */}
          <div
            className="stat-chip"
            style={{
              borderColor: darkCount > 0 ? 'rgba(245,158,11,0.5)' : 'var(--navy-500)',
              color:       darkCount > 0 ? 'var(--amber-400)' : 'var(--text-dim)',
              background:  darkCount > 0 ? 'rgba(245,158,11,0.08)' : 'transparent',
            }}
          >
            <span>📡</span>
            <span className="font-data">{darkCount}</span>
            <span>Dark</span>
          </div>

          {/* MPA Breaches */}
          <div
            className="stat-chip"
            style={{
              borderColor: mpaCount > 0 ? 'rgba(168,85,247,0.5)' : 'var(--navy-500)',
              color:       mpaCount > 0 ? '#C084FC' : 'var(--text-dim)',
              background:  mpaCount > 0 ? 'rgba(168,85,247,0.08)' : 'transparent',
            }}
          >
            <span>🏊</span>
            <span className="font-data">{mpaCount}</span>
            <span>MPA</span>
          </div>

          {/* Divider */}
          <div className="w-px h-6 mx-1" style={{ background: 'var(--navy-500)' }} />

          {/* Critical Badge */}
          {criticalCount > 0 && (
            <div
              className="stat-chip animate-pulse-red"
              style={{ borderColor: 'var(--red-500)', color: 'var(--red-400)', background: 'rgba(239,68,68,0.15)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping inline-block" />
              <span className="font-data">{criticalCount}</span>
              <span>CRITICAL</span>
            </div>
          )}

          {/* Warning Badge */}
          {warningCount > 0 && (
            <div
              className="stat-chip"
              style={{ borderColor: 'rgba(245,158,11,0.4)', color: 'var(--amber-400)', background: 'rgba(245,158,11,0.08)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
              <span className="font-data">{warningCount}</span>
              <span>WARN</span>
            </div>
          )}
        </div>

        {/* Right: Feed Status + Controls */}
        <div className="flex items-center gap-3">

          {/* Sentinel-2 feed status */}
          <div
            className="flex items-center gap-1.5 text-[10px] px-2 py-1 rounded border"
            style={{ background: 'rgba(15,31,61,0.8)', borderColor: 'var(--navy-500)', color: 'var(--text-secondary)' }}
          >
            <span style={{ color: 'var(--teal-400)' }}>🛰</span>
            <span>Sentinel-2</span>
            <span style={{ color: 'var(--text-dim)' }}>·</span>
            <span>Pass: 3h ago</span>
          </div>

          {/* GFW feed status */}
          <div
            className="flex items-center gap-1.5 text-[10px] px-2 py-1 rounded border"
            style={{ background: 'rgba(15,31,61,0.8)', borderColor: 'var(--navy-500)', color: 'var(--text-secondary)' }}
          >
            <span style={{ color: 'var(--emerald-400)' }}>🌊</span>
            <span>GFW</span>
            <span style={{ color: 'var(--text-dim)' }}>·</span>
            <span style={{ color: 'var(--emerald-400)', fontFamily: 'var(--font-data)' }}>LIVE</span>
          </div>

          {/* WebSocket connection */}
          <div className="flex items-center gap-1.5 text-[10px]">
            <span
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-ping' : 'bg-red-500'}`}
            />
            <span
              className="font-data tracking-widest text-[10px]"
              style={{ color: isConnected ? 'var(--emerald-400)' : 'var(--red-400)' }}
            >
              {isConnected ? 'AIS LIVE' : 'OFFLINE'}
            </span>
          </div>

          {/* Clock */}
          <LiveClock />

          {/* Audio mute */}
          <button
            id="audio-mute-btn"
            onClick={toggleAudio}
            title={isAudioMuted ? 'Unmute Alarms' : 'Mute Alarms'}
            className="p-1.5 rounded border transition-all"
            style={{
              background:   isAudioMuted ? 'rgba(220,38,38,0.15)'   : 'rgba(16,185,129,0.10)',
              borderColor:  isAudioMuted ? 'rgba(220,38,38,0.4)'    : 'rgba(16,185,129,0.3)',
              color:        isAudioMuted ? 'var(--red-400)'           : 'var(--emerald-400)',
            }}
          >
            {isAudioMuted ? '🔇' : '🔊'}
          </button>
        </div>
      </div>

      {/* ── Ops Ticker Bar ───────────────────────────────────────────────── */}
      <div
        className="h-7 flex items-center overflow-hidden px-4 gap-4 shrink-0"
        style={{ background: 'var(--navy-900)', borderTop: '1px solid var(--navy-500)' }}
      >
        {/* Static left label */}
        <span
          className="text-[9px] font-bold tracking-widest uppercase shrink-0 pr-3 border-r"
          style={{ color: 'var(--teal-500)', borderColor: 'var(--navy-500)' }}
        >
          OPS LOG
        </span>

        {/* Scrolling ticker */}
        <div className="flex-1 overflow-hidden relative h-full flex items-center">
          <p className="animate-ticker text-[10px] font-data absolute whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
            <span style={{ color: 'var(--amber-400)' }}>⚠ 19:00 UTC</span> — MT GUJARAT PRIDE entered AIS dark zone near Bombay High (MMSI: 419000001)&nbsp;&nbsp;
            <span style={{ color: 'var(--red-400)' }}>🛢 19:00 UTC</span> — Oil slick detected 4.8 km², Sentinel-2 SAR scene S2A_T43RCQ&nbsp;&nbsp;
            <span style={{ color: 'var(--text-mono)' }}>● 18:45 UTC</span> — GFW fetch complete: {totalVessels > 0 ? `${(totalVessels/1000).toFixed(0)}K` : 'N/A'} vessels indexed in Indian EEZ&nbsp;&nbsp;
            <span style={{ color: '#C084FC' }}>🏊 18:32 UTC</span> — FV KUTCH FISHERMAN loitering inside Gulf of Kutch MNP boundary
          </p>
        </div>

        {/* Right side: Sector + Status */}
        <div className="flex items-center gap-3 shrink-0 pl-3 border-l" style={{ borderColor: 'var(--navy-500)' }}>
          <span className="text-[9px] tracking-widest" style={{ color: 'var(--text-dim)' }}>
            SECTOR: BOMBAY HIGH EEZ
          </span>
          <span
            className="text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(16,185,129,0.12)', color: 'var(--emerald-400)', border: '1px solid rgba(16,185,129,0.3)' }}
          >
            OPERATIONAL
          </span>
        </div>
      </div>
    </header>
  );
}
