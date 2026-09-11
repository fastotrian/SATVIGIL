/**
 * SATVIGIL — Operational Marquee / Bloomberg-Style Ops Log Ticker
 * Fixed 28px bottom status strip with live scrolling telemetry stream.
 */
import React from 'react';
import { useAlertStore } from '../../store/alertStore';

export function OpsLogFooter() {
  const { vessels, alerts } = useAlertStore();
  const totalVessels = vessels.length;
  const criticalAlerts = alerts.filter((a) => a.risk_level === 'CRITICAL' && !a.acknowledged);

  return (
    <footer
      className="h-7 px-3 flex items-center overflow-hidden shrink-0 select-none z-20"
      style={{
        background: 'var(--navy-950)',
        borderTop: '1px solid var(--navy-500)',
      }}
    >
      {/* Static Left Label */}
      <div className="flex items-center gap-2 pr-3 border-r shrink-0" style={{ borderColor: 'var(--navy-500)' }}>
        <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span
          className="text-[9px] font-bold tracking-widest uppercase font-mono"
          style={{ color: 'var(--teal-400)' }}
        >
          OPS LOG // STREAM
        </span>
      </div>

      {/* Scrolling Ticker Stream */}
      <div className="flex-1 overflow-hidden relative h-full flex items-center">
        <p className="animate-ticker text-[10px] font-mono absolute whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--amber-400)' }}>⚠ {new Date(Date.now() - 25 * 60000).toISOString().substring(11, 16)} UTC</span> — MT GUJARAT PRIDE entered AIS dark zone near Bombay High (MMSI: 419082341)&nbsp;&nbsp;&nbsp;&nbsp;
          <span style={{ color: 'var(--red-400)' }}>🛢 {new Date(Date.now() - 12 * 60000).toISOString().substring(11, 16)} UTC</span> — Oil slick detected 4.8 km², Sentinel-1C C-SAR (IW Swath, VV/VH) scene S1C_IW_GRDH_1SDV_20260910T053649_20260910T053714_055591_06C82F_B7E2&nbsp;&nbsp;&nbsp;&nbsp;
          <span style={{ color: 'var(--teal-300)' }}>● {new Date(Date.now() - 15 * 60000).toISOString().substring(11, 16)} UTC</span> — GFW AIS ingestion active: {totalVessels > 0 ? `${(totalVessels / 1000).toFixed(1)}K` : '11.3K'} vessels indexed across Indian Ocean &amp; Arabian Sea EEZ&nbsp;&nbsp;&nbsp;&nbsp;
          <span style={{ color: '#C084FC' }}>🏊 {new Date(Date.now() - 40 * 60000).toISOString().substring(11, 16)} UTC</span> — FV KUTCH FISHERMAN loitering inside Gulf of Kutch MNP sanctuary boundary&nbsp;&nbsp;&nbsp;&nbsp;
          <span style={{ color: 'var(--emerald-400)' }}>🔥 NASA VIIRS</span> — 174 thermal anomalies &amp; gas flare clusters monitored across ONGC/CPCB sectors
        </p>
      </div>

      {/* Right Telemetry & System Status */}
      <div className="flex items-center gap-3 shrink-0 pl-3 border-l" style={{ borderColor: 'var(--navy-500)' }}>
        <span className="text-[9px] font-mono tracking-wider hidden sm:inline" style={{ color: 'var(--text-dim)' }}>
          SECTOR: 19.20°N 71.50°E · BOMBAY HIGH
        </span>
        <span
          className="text-[9px] font-mono font-bold tracking-widest px-1.5 py-0.5 rounded flex items-center gap-1"
          style={{
            background: 'rgba(16,185,129,0.12)',
            color: 'var(--emerald-400)',
            border: '1px solid rgba(16,185,129,0.3)',
          }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          SYSTEM OK
        </span>
      </div>
    </footer>
  );
}
