/**
 * SATVIGIL — Dashboard Header
 * Command center top bar with telemetry indicators, sensor badges, quick sector jump pills, and live UTC clock.
 */
import React, { useEffect, useState } from 'react';
import { Ship, Flame, Mountain, Volume2, VolumeX } from 'lucide-react';
import { useAlertStore } from '../../store/alertStore';

// ── Live UTC Clock ─────────────────────────────────────────────────────────
function LiveClock() {
  const [time, setTime] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-navy-800/80 border border-navy-500/60 shadow-sm">
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

export function DashboardHeader() {
  const { activeNavTab, setNavTab, activeFilters, toggleFilter, isAudioMuted, toggleAudio } = useAlertStore();

  return (
    <header
      className="shrink-0 z-20 flex flex-col select-none shadow-md"
      style={{ background: 'var(--navy-950)', borderBottom: '1px solid var(--navy-500)' }}
    >
      {/* ── Top Bar with Brand, Central 3-Tab Navigation, and Utilities ── */}
      <div className="relative h-14 px-4 py-1.5 flex items-center justify-between gap-2 sm:gap-4">

        {/* Left: Branding */}
        <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
          <SatIcon />
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span
                className="font-bold text-xl sm:text-base tracking-[0.16em] uppercase"
                style={{ color: 'var(--teal-400)', letterSpacing: '0.18em' }}
              >
                SATVIGIL
              </span>
            </div>
            
          </div>
        </div>

        {/* Center: 3 Navigation Bar Buttons (Mathematically centered, zero shifting) */}
        <nav className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-1 sm:gap-1.5 p-1 rounded-lg border border-navy-700 bg-navy-900/90 shadow-inner z-10 pointer-events-auto">
          <button
            type="button"
            onClick={() => setNavTab('maritime')}
            className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-md font-mono text-[11px] sm:text-xs font-bold transition-all ${
              activeNavTab === 'maritime'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 shadow-[0_0_12px_rgba(6,182,212,0.25)]'
                : 'text-gray-400 hover:text-gray-200 hover:bg-navy-800 border border-transparent'
            }`}
          >
            <Ship className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span>MARITIME</span>
          </button>

          <button
            type="button"
            onClick={() => setNavTab('thermal')}
            className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-md font-mono text-[11px] sm:text-xs font-bold transition-all ${
              activeNavTab === 'thermal'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-400/60 shadow-[0_0_12px_rgba(245,158,11,0.25)]'
                : 'text-gray-400 hover:text-gray-200 hover:bg-navy-800 border border-transparent'
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>THERMAL ZONE</span>
          </button>

          <button
            type="button"
            onClick={() => setNavTab('geological')}
            className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-md font-mono text-[11px] sm:text-xs font-bold transition-all ${
              activeNavTab === 'geological'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-400/60 shadow-[0_0_12px_rgba(244,63,94,0.25)]'
                : 'text-gray-400 hover:text-gray-200 hover:bg-navy-800 border border-transparent'
            }`}
          >
            <Mountain className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <span>GEOLOGICAL</span>
          </button>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3 shrink-0 ml-auto">
          {/* Live Clock */}
          <LiveClock />
        </div>
      </div>
    </header>
  );
}
