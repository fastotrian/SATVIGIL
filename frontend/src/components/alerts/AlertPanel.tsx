/**
 * SATVIGIL — Threat Intelligence Panel
 * Real-time alert cards with risk priority, type badges, and action buttons.
 * Design: Military command center — navy base, teal accents, amber/red threat colors.
 */
import React from 'react';
import { useAlertStore } from '../../store/alertStore';
import type { Alert } from '../../types/maritime';

// ── Alert type metadata ────────────────────────────────────────────────────
const ALERT_META: Record<string, { icon: string; label: string; color: string; bg: string }> = {
  OIL_SPILL:       { icon: '🛢', label: 'OIL SPILL',    color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
  DARK_VESSEL:     { icon: '📡', label: 'DARK VESSEL',  color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  ILLEGAL_FISHING: { icon: '🎣', label: 'MPA BREACH',   color: '#C084FC', bg: 'rgba(192,132,252,0.15)' },
  FIRE:            { icon: '🔥', label: 'FIRE / HEAT',  color: '#FB923C', bg: 'rgba(251,146,60,0.15)' },
  LANDSLIDE:       { icon: '⛰', label: 'LANDSLIDE',    color: '#A78BFA', bg: 'rgba(167,139,250,0.15)' },
};

function getAlertMeta(type: string) {
  return ALERT_META[type] ?? { icon: '⚠', label: 'ALERT', color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' };
}

// ── Risk level config ─────────────────────────────────────────────────────
const RISK_CFG: Record<string, { border: string; cardClass: string; badge: string; badgeBg: string }> = {
  CRITICAL: { border: '#EF4444', cardClass: 'alert-card-critical', badge: '#EF4444', badgeBg: 'rgba(239,68,68,0.20)' },
  WARNING:  { border: '#F59E0B', cardClass: 'alert-card-warning',  badge: '#F59E0B', badgeBg: 'rgba(245,158,11,0.20)' },
  WATCH:    { border: '#FBBF24', cardClass: 'alert-card-warning',  badge: '#FBBF24', badgeBg: 'rgba(251,191,36,0.20)' },
  NORMAL:   { border: '#00D4E8', cardClass: 'alert-card-normal',   badge: '#00D4E8', badgeBg: 'rgba(0,212,232,0.12)' },
};

function getRiskCfg(level: string) {
  return RISK_CFG[level] ?? RISK_CFG.NORMAL;
}

// ── Relative time ─────────────────────────────────────────────────────────
function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'Just now';
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

// ── Risk Score Bar ─────────────────────────────────────────────────────────
function RiskBar({ score }: { score?: number }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const color = score > 0.75 ? '#EF4444' : score > 0.45 ? '#F59E0B' : '#10B981';
  return (
    <div className="flex items-center gap-2 mt-1.5">
      <span className="text-[9px] tracking-widest" style={{ color: 'var(--text-secondary)', width: 68 }}>RISK SCORE</span>
      <div className="risk-bar-track flex-1">
        <div className="risk-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="font-data text-[10px] font-bold" style={{ color, width: 28, textAlign: 'right' }}>{pct}%</span>
    </div>
  );
}

// ── Single Alert Card ─────────────────────────────────────────────────────
function AlertCard({ alert, onTarget, onAck }: {
  alert: Alert;
  onTarget: () => void;
  onAck: () => void;
}) {
  const meta = getAlertMeta(alert.alert_type);
  const risk = getRiskCfg(alert.risk_level);
  const isCrit = alert.risk_level === 'CRITICAL';

  return (
    <div
      className={`${risk.cardClass} rounded-md border transition-all cursor-default select-none`}
      style={{
        borderColor: 'var(--navy-500)',
        borderLeftColor: alert.acknowledged ? 'var(--text-dim)' : risk.border,
        borderLeftWidth: 3,
        opacity: alert.acknowledged ? 0.4 : 1,
        filter: alert.acknowledged ? 'grayscale(0.7)' : 'none',
      }}
    >
      {/* Card top row: icon chip + title + risk badge */}
      <div className="flex items-start gap-2 p-3 pb-2">
        {/* Type icon chip */}
        <div
          className="shrink-0 flex items-center justify-center w-7 h-7 rounded text-sm font-bold"
          style={{ background: meta.bg, border: `1px solid ${meta.color}30` }}
        >
          {meta.icon}
        </div>

        {/* Title + description */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-1">
            <button
              type="button"
              onClick={onTarget}
              className="text-left font-bold text-[11px] leading-tight hover:underline transition-colors line-clamp-2"
              style={{ color: isCrit ? '#FCA5A5' : 'var(--text-primary)', maxWidth: '75%' }}
            >
              {alert.title}
            </button>

            {/* Risk badge */}
            <span
              className="shrink-0 font-data text-[9px] font-bold px-1.5 py-0.5 rounded tracking-widest"
              style={{ background: risk.badgeBg, color: risk.badge, border: `1px solid ${risk.badge}40` }}
            >
              {alert.risk_level}
            </span>
          </div>

          {/* Type label */}
          <span className="text-[9px] font-bold tracking-widest mt-0.5 block" style={{ color: meta.color }}>
            {meta.label}
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="px-3 text-[10px] leading-relaxed line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
        {alert.description}
      </p>

      {/* Risk bar */}
      <div className="px-3">
        <RiskBar score={(alert as any).risk_score} />
      </div>

      {/* Footer: time + actions */}
      <div className="flex items-center justify-between px-3 pt-2 pb-3">
        <span className="font-data text-[9px]" style={{ color: 'var(--text-dim)' }}>
          {relTime(alert.created_at)}
        </span>

        <div className="flex items-center gap-2">
          {alert.vessel_mmsi && (
            <button
              type="button"
              onClick={onTarget}
              className="text-[10px] font-medium transition-colors hover:underline"
              style={{ color: 'var(--teal-500)' }}
            >
              Target →
            </button>
          )}
          {!alert.acknowledged && (
            <button
              type="button"
              onClick={onAck}
              className="font-data text-[9px] font-bold px-2 py-0.5 rounded border transition-all hover:opacity-80"
              style={{
                background: 'rgba(27,108,168,0.15)',
                borderColor: 'var(--navy-400)',
                color: 'var(--teal-400)',
              }}
            >
              ACK
            </button>
          )}
          {alert.acknowledged && (
            <span className="font-data text-[9px]" style={{ color: 'var(--emerald-500)' }}>
              ✓ ACK
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Panel ────────────────────────────────────────────────────────────
export function AlertPanel() {
  const { alerts, setAlerts, acknowledgeAlert, vessels, selectVessel } = useAlertStore();

  // Seed initial alerts from vessel state
  React.useEffect(() => {
    if (alerts.length === 0 && vessels.length > 0) {
      const seeded: Alert[] = [
        {
          id: 'ALERT-SPILL-001',
          alert_type: 'OIL_SPILL',
          risk_level: 'CRITICAL',
          title: 'Active Oil Slick Detected (4.8 km²)',
          description: 'Sentinel-2 SAR correlation: dark patch 4.8 km² near Bombay High. High-probability suspect: MT GUJARAT PRIDE (MMSI: 419000001).',
          lat: 19.20, lon: 71.50,
          created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
          vessel_mmsi: '419000001',
          acknowledged: false,
        },
      ];

      vessels.forEach((v) => {
        if (v.is_dark) {
          seeded.push({
            id: `ALERT-DARK-${v.mmsi}`,
            alert_type: 'DARK_VESSEL',
            risk_level: 'CRITICAL',
            title: `AIS Transponder Off: ${v.vessel_name}`,
            description: `Vessel ceased AIS broadcast for ${v.ais_gap_minutes}m. Last known position: ${v.lat.toFixed(2)}°N ${v.lon.toFixed(2)}°E near Bombay High Oil Field.`,
            lat: v.lat, lon: v.lon,
            created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
            vessel_mmsi: v.mmsi,
            acknowledged: false,
          });
        }
        if (v.in_mpa) {
          seeded.push({
            id: `ALERT-MPA-${v.mmsi}`,
            alert_type: 'ILLEGAL_FISHING',
            risk_level: 'WARNING',
            title: `Protected Area Breach: ${v.vessel_name}`,
            description: `Loitering pattern detected inside ${v.mpa_name}. Speed ${v.speed_knots} kts for ${v.ais_gap_minutes}+ minutes. Possible illegal fishing.`,
            lat: v.lat, lon: v.lon,
            created_at: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
            vessel_mmsi: v.mmsi,
            acknowledged: false,
          });
        }
      });

      setAlerts(seeded);
    }
  }, [alerts.length, vessels, setAlerts]);

  const sorted = [...alerts].sort((a, b) => {
    const p: Record<string, number> = { CRITICAL: 0, WARNING: 1, WATCH: 2, NORMAL: 3 };
    return (p[a.risk_level] ?? 9) - (p[b.risk_level] ?? 9);
  });

  const unackCount = sorted.filter((a) => !a.acknowledged).length;

  return (
    <div
      className="flex flex-col h-full select-none"
      style={{ background: 'var(--navy-950)', color: 'var(--text-primary)' }}
    >
      {/* ── Panel Header ──────────────────────────────────────────────── */}
      <div
        className="shrink-0 px-4 py-3 flex items-center justify-between"
        style={{ borderBottom: '1px solid var(--navy-500)', background: 'var(--navy-900)' }}
      >
        <div className="flex items-center gap-2.5">
          {/* Teal left accent bar */}
          <div className="w-0.5 h-5 rounded-full" style={{ background: 'var(--teal-500)' }} />
          <span
            className="text-[11px] font-bold tracking-[0.2em] uppercase"
            style={{ color: 'var(--text-primary)' }}
          >
            Threat Intel
          </span>
          {/* Count badge */}
          {unackCount > 0 && (
            <span
              className="font-data text-[9px] font-bold px-1.5 py-0.5 rounded-full animate-pulse-red"
              style={{ background: 'rgba(239,68,68,0.20)', color: 'var(--red-400)', border: '1px solid rgba(239,68,68,0.4)' }}
            >
              {unackCount} LIVE
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={() => setAlerts([])}
          className="text-[10px] transition-colors hover:opacity-80"
          style={{ color: 'var(--text-dim)' }}
        >
          Clear All
        </button>
      </div>

      {/* ── Sort/Filter micro-bar ─────────────────────────────────────── */}
      <div
        className="shrink-0 px-4 py-1.5 flex items-center gap-3"
        style={{ borderBottom: '1px solid var(--navy-500)', background: 'var(--navy-900)' }}
      >
        <span className="text-[9px] tracking-widest uppercase" style={{ color: 'var(--text-dim)' }}>
          Sort: Priority ▾
        </span>
        <span className="text-[9px]" style={{ color: 'var(--navy-500)' }}>|</span>
        <span className="text-[9px] tracking-widest uppercase" style={{ color: 'var(--text-dim)' }}>
          All Types ▾
        </span>
        <span className="ml-auto font-data text-[9px]" style={{ color: 'var(--text-dim)' }}>
          {sorted.length} events
        </span>
      </div>

      {/* ── Alert Cards ──────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-56 gap-3">
            <div className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
              style={{ background: 'rgba(0,212,232,0.08)', border: '1px solid var(--navy-500)' }}>
              🛰
            </div>
            <span className="text-xs tracking-widest" style={{ color: 'var(--text-dim)' }}>
              NO ACTIVE THREATS
            </span>
          </div>
        ) : (
          sorted.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onTarget={() => {
                if (alert.vessel_mmsi) {
                  const v = vessels.find((v) => v.mmsi === alert.vessel_mmsi);
                  if (v) selectVessel(v);
                }
              }}
              onAck={() => acknowledgeAlert(alert.id)}
            />
          ))
        )}
      </div>

      {/* ── Panel Footer: system status ───────────────────────────────── */}
      <div
        className="shrink-0 px-4 py-2 flex items-center justify-between"
        style={{ borderTop: '1px solid var(--navy-500)', background: 'var(--navy-900)' }}
      >
        <span className="font-data text-[9px]" style={{ color: 'var(--text-dim)' }}>
          FEED: GFW / SAR
        </span>
        <span className="font-data text-[9px]" style={{ color: 'var(--emerald-500)' }}>
          ● SYSTEM NOMINAL
        </span>
      </div>
    </div>
  );
}
