/**
 * SATVIGIL — Actionable Threat Intelligence Feed
 * Refactored into a sleek, compact command center drawer with collapsible cards and zero visual clutter.
 */
import React, { useState } from 'react';
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
const RISK_CFG: Record<string, { border: string; badge: string; badgeBg: string }> = {
  CRITICAL: { border: '#EF4444', badge: '#EF4444', badgeBg: 'rgba(239,68,68,0.20)' },
  WARNING:  { border: '#F59E0B', badge: '#F59E0B', badgeBg: 'rgba(245,158,11,0.20)' },
  WATCH:    { border: '#FBBF24', badge: '#FBBF24', badgeBg: 'rgba(251,191,36,0.20)' },
  NORMAL:   { border: '#00D4E8', badge: '#00D4E8', badgeBg: 'rgba(0,212,232,0.12)' },
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

// ── Compact Expandable Alert Card ─────────────────────────────────────────
function CompactAlertCard({
  alert,
  isSelected,
  onToggleExpand,
  onTarget,
  onAck,
  onDossier,
}: {
  alert: Alert;
  isSelected: boolean;
  onToggleExpand: () => void;
  onTarget: () => void;
  onAck: () => void;
  onDossier: () => void;
}) {
  const meta = getAlertMeta(alert.alert_type);
  const risk = getRiskCfg(alert.risk_level);
  const isSpillOrDark = alert.alert_type === 'OIL_SPILL' || alert.alert_type === 'DARK_VESSEL';

  return (
    <div
      className="rounded border transition-all select-none overflow-hidden"
      style={{
        background: isSelected ? 'var(--navy-800)' : 'var(--navy-900)',
        borderColor: isSelected ? 'var(--teal-500)' : 'var(--navy-500)',
        borderLeftColor: alert.acknowledged ? 'var(--text-dim)' : risk.border,
        borderLeftWidth: 3,
        opacity: alert.acknowledged ? 0.45 : 1,
      }}
    >
      {/* ── Summary Row (Always Visible ~52px) ── */}
      <div
        onClick={onToggleExpand}
        className="p-2.5 flex items-center justify-between gap-2 cursor-pointer hover:bg-navy-700/50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <div
            className="w-6 h-6 rounded flex items-center justify-center shrink-0 text-xs font-bold"
            style={{ background: meta.bg, border: `1px solid ${meta.color}40` }}
          >
            {meta.icon}
          </div>
          <div className="flex flex-col min-w-0 flex-1">
            <span className="text-[11px] font-bold text-gray-100 truncate leading-tight">
              {alert.title}
            </span>
            <span className="text-[9px] font-mono text-gray-400 truncate">
              {meta.label} · {relTime(alert.created_at)}
            </span>
          </div>
        </div>

        {/* Risk Badge */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded tracking-wider"
            style={{ background: risk.badgeBg, color: risk.badge, border: `1px solid ${risk.badge}50` }}
          >
            {alert.risk_level}
          </span>
          <span className="text-gray-500 text-xs">
            {isSelected ? '▲' : '▼'}
          </span>
        </div>
      </div>

      {/* ── Expanded Detail Drawer ── */}
      {isSelected && (
        <div className="px-3 pt-1 pb-3 border-t border-navy-700/80 bg-navy-950/60 flex flex-col gap-2 text-xs">
          <p className="text-[10px] text-gray-300 leading-relaxed">
            {alert.description}
          </p>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[9px] font-mono text-gray-400">
              {alert.lat.toFixed(4)}°N, {alert.lon.toFixed(4)}°E
            </span>

            <div className="flex items-center gap-1.5">
              {isSpillOrDark && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onDossier(); }}
                  className="font-mono text-[9px] font-bold px-2 py-0.5 rounded border border-teal-500/50 bg-teal-950/60 text-teal-300 hover:bg-teal-900/80 transition-colors"
                >
                  ⚖️ Dossier
                </button>
              )}

              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onTarget(); }}
                className="font-mono text-[9px] font-bold px-2 py-0.5 rounded border border-navy-400 bg-navy-800 text-cyan-300 hover:bg-navy-700 transition-colors"
              >
                Target →
              </button>

              {!alert.acknowledged ? (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onAck(); }}
                  className="font-mono text-[9px] font-bold px-2 py-0.5 rounded border border-navy-500 bg-navy-900 text-gray-300 hover:text-white transition-colors"
                >
                  ACK
                </button>
              ) : (
                <span className="text-[9px] font-mono text-emerald-400 font-bold">
                  ✓ ACK
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Threat Panel ─────────────────────────────────────────────────────
export function AlertPanel({ isCollapsed, onToggleCollapse }: { isCollapsed?: boolean; onToggleCollapse?: () => void }) {
  const { alerts, setAlerts, acknowledgeAlert, vessels, selectVessel, openDossier } = useAlertStore();
  const [filterType, setFilterType] = useState<string>('ALL');
  const [expandedAlertId, setExpandedAlertId] = useState<string | null>('ALERT-SPILL-001');

  // Seed initial alerts from vessel state
  React.useEffect(() => {
    if (alerts.length === 0 && vessels.length > 0) {
      const seeded: Alert[] = [
        {
          id: 'ALERT-SPILL-001',
          alert_type: 'OIL_SPILL',
          risk_level: 'CRITICAL',
          title: 'Active Oil Slick Detected (4.8 km²)',
          description: 'Sentinel-1C C-SAR (IW Swath, VV/VH) correlation: dark patch 4.8 km² near Bombay High (19.2000°N, 71.5000°E). High-probability suspect: MT GUJARAT PRIDE (MMSI: 419082341).',
          lat: 19.2000, lon: 71.5000,
          created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
          vessel_mmsi: '419082341',
          acknowledged: false,
        },
      ];

      vessels.forEach((v) => {
        if (v.is_dark && v.ais_gap_minutes >= 30) {
          seeded.push({
            id: `ALERT-DARK-${v.mmsi}`,
            alert_type: 'DARK_VESSEL',
            risk_level: 'CRITICAL',
            title: `AIS Transponder Off: ${v.vessel_name}`,
            description: `Vessel ceased AIS broadcast for ${v.ais_gap_minutes}m. Position: ${v.lat.toFixed(4)}°N ${v.lon.toFixed(4)}°E.`,
            lat: v.lat, lon: v.lon,
            created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
            vessel_mmsi: v.mmsi,
            acknowledged: false,
          });
        }
        const isFishingVessel = (v.vessel_type >= 30 && v.vessel_type <= 39) || v.vessel_name.toUpperCase().startsWith('FV');
        if (v.in_mpa && isFishingVessel && v.ais_gap_minutes >= 10) {
          seeded.push({
            id: `ALERT-MPA-${v.mmsi}`,
            alert_type: 'ILLEGAL_FISHING',
            risk_level: 'WARNING',
            title: `Protected Area Breach: ${v.vessel_name}`,
            description: `Suspicious loitering pattern detected inside ${v.mpa_name}. Speed ${v.speed_knots.toFixed(1)} kts for ${v.ais_gap_minutes}m in marine sanctuary.`,
            lat: v.lat, lon: v.lon,
            created_at: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
            vessel_mmsi: v.mmsi,
            acknowledged: false,
          });
        }
      });

      setAlerts(seeded);
    }
  }, [vessels, alerts.length, setAlerts]);

  const filtered = alerts.filter((a) => {
    if (filterType === 'CRITICAL') return a.risk_level === 'CRITICAL';
    if (filterType === 'OIL_SPILL') return a.alert_type === 'OIL_SPILL';
    if (filterType === 'DARK_VESSEL') return a.alert_type === 'DARK_VESSEL';
    if (filterType === 'MPA') return a.alert_type === 'ILLEGAL_FISHING';
    return true;
  });

  return (
    <div className="flex flex-col h-full select-none" style={{ background: 'var(--navy-950)' }}>
      {/* ── Header ── */}
      <div className="p-3 border-b border-navy-500/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-gray-200">
            Threat Feed ({filtered.length})
          </h2>
        </div>

        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="text-[10px] font-mono px-2 py-0.5 rounded border border-navy-500 text-gray-400 hover:text-white hover:bg-navy-800 transition-all"
            title="Toggle Threat Panel"
          >
            {isCollapsed ? '◀ Expand' : '▶ Hide'}
          </button>
        )}
      </div>

      {/* ── Filter Pills ── */}
      <div className="p-2 border-b border-navy-600/50 flex gap-1 overflow-x-auto text-[10px] font-mono">
        {['ALL', 'CRITICAL', 'OIL_SPILL', 'DARK_VESSEL', 'MPA'].map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setFilterType(tab)}
            className={`px-2 py-0.5 rounded transition-all whitespace-nowrap ${
              filterType === tab
                ? 'bg-teal-500 text-black font-bold'
                : 'bg-navy-800 text-gray-400 hover:text-white'
            }`}
          >
            {tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* ── Card Feed ── */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1.5">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-xs font-mono text-gray-500">
            No threats detected for selected filter.
          </div>
        ) : (
          filtered.map((alert) => (
            <CompactAlertCard
              key={alert.id}
              alert={alert}
              isSelected={expandedAlertId === alert.id}
              onToggleExpand={() =>
                setExpandedAlertId((prev) => (prev === alert.id ? null : alert.id))
              }
              onTarget={() => {
                const v = vessels.find((ves) => ves.mmsi === alert.vessel_mmsi);
                if (v) selectVessel(v);
              }}
              onAck={() => acknowledgeAlert(alert.id)}
              onDossier={() => openDossier(alert.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
