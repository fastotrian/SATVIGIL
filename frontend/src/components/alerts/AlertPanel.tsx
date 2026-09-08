/**
 * SATVIGIL — Real-Time Alert Panel Component
 * Displays incoming threat alerts, oil spills, dark vessels, and critical alarms.
 * Supports acknowledgement, risk priority sorting, and vessel drill-down.
 */
import React from 'react';
import { useAlertStore } from '../../store/alertStore';
import { RISK_COLORS } from '../../constants/riskColors';
import type { Alert } from '../../types/maritime';

export function AlertPanel() {
  const { alerts, setAlerts, acknowledgeAlert, vessels, selectVessel } = useAlertStore();

  // Populate derived alerts from live vessel fleet if alert store is currently empty
  React.useEffect(() => {
    if (alerts.length === 0 && vessels.length > 0) {
      const initialAlerts: Alert[] = [
        {
          id: 'ALERT-SPILL-001',
          alert_type: 'OIL_SPILL',
          risk_level: 'CRITICAL',
          title: 'Active Oil Slick Detected (4.8 km²)',
          description: 'Sentinel-2 SAR correlation with high probability suspect MT GUJARAT PRIDE.',
          lat: 19.20,
          lon: 71.50,
          created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
          vessel_mmsi: '419000001',
          acknowledged: false,
        },
      ];

      vessels.forEach((v) => {
        if (v.is_dark) {
          initialAlerts.push({
            id: `ALERT-DARK-${v.mmsi}`,
            alert_type: 'DARK_VESSEL',
            risk_level: 'CRITICAL',
            title: `AIS Transponder Off: ${v.vessel_name}`,
            description: `Vessel ceased AIS broadcast for ${v.ais_gap_minutes}m near Bombay High.`,
            lat: v.lat,
            lon: v.lon,
            created_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
            vessel_mmsi: v.mmsi,
            acknowledged: false,
          });
        }
        if (v.in_mpa) {
          initialAlerts.push({
            id: `ALERT-MPA-${v.mmsi}`,
            alert_type: 'ILLEGAL_FISHING',
            risk_level: 'WARNING',
            title: `Protected Area Breach: ${v.vessel_name}`,
            description: `Loitering speed detected inside ${v.mpa_name}.`,
            lat: v.lat,
            lon: v.lon,
            created_at: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
            vessel_mmsi: v.mmsi,
            acknowledged: false,
          });
        }
      });

      setAlerts(initialAlerts);
    }
  }, [alerts.length, vessels, setAlerts]);

  // Sort alerts by severity: CRITICAL first, then WARNING, then WATCH, then NORMAL
  const sortedAlerts = [...alerts].sort((a, b) => {
    const priority = { CRITICAL: 0, WARNING: 1, WATCH: 2, NORMAL: 3 };
    return priority[a.risk_level] - priority[b.risk_level];
  });

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'OIL_SPILL':
        return '🛢️';
      case 'DARK_VESSEL':
        return '📡';
      case 'ILLEGAL_FISHING':
        return '🎣';
      case 'FIRE':
        return '🔥';
      case 'LANDSLIDE':
        return '⛰️';
      default:
        return '⚠️';
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-gray-100 select-none">
      {/* Sidebar Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center space-x-2">
          <span className="font-bold text-sm tracking-wider uppercase text-gray-200">Alerts</span>
          <span className="bg-red-950 text-red-400 border border-red-800 text-[11px] font-bold px-2 py-0.5 rounded-full">
            {sortedAlerts.filter((a) => !a.acknowledged).length}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setAlerts([])}
          className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
        >
          Clear All
        </button>
      </div>

      {/* Alerts Scrollable List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {sortedAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-56 text-gray-500 space-y-2">
            <span className="text-3xl">🛰️</span>
            <span className="text-xs font-medium">No active alerts</span>
          </div>
        ) : (
          sortedAlerts.map((alert) => {
            const isCritical = alert.risk_level === 'CRITICAL';
            const isWarning = alert.risk_level === 'WARNING';
            const borderColor = isCritical
              ? RISK_COLORS.CRITICAL
              : isWarning
              ? RISK_COLORS.HIGH
              : RISK_COLORS.CAUTION;

            return (
              <div
                key={alert.id}
                style={{ borderLeftColor: borderColor }}
                className={`p-3 rounded-r-lg border-l-4 border-y border-r border-gray-800 transition-all ${
                  alert.acknowledged
                    ? 'opacity-40 grayscale bg-gray-950/60'
                    : isCritical
                    ? 'bg-red-950/20 hover:bg-red-950/30'
                    : isWarning
                    ? 'bg-orange-950/20 hover:bg-orange-950/30'
                    : 'bg-gray-800/40 hover:bg-gray-800/60'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div
                    className="flex items-center space-x-2 cursor-pointer flex-1 mr-2"
                    onClick={() => {
                      if (alert.vessel_mmsi) {
                        const match = vessels.find((v) => v.mmsi === alert.vessel_mmsi);
                        if (match) selectVessel(match);
                      }
                    }}
                  >
                    <span className="text-base">{getAlertIcon(alert.alert_type)}</span>
                    <span className="font-bold text-xs text-gray-100 hover:text-blue-400 transition-colors">
                      {alert.title}
                    </span>
                  </div>

                  <span
                    className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase shrink-0"
                    style={{
                      backgroundColor: isCritical
                        ? 'rgba(239, 68, 68, 0.2)'
                        : isWarning
                        ? 'rgba(249, 115, 22, 0.2)'
                        : 'rgba(251, 191, 36, 0.2)',
                      color: borderColor,
                    }}
                  >
                    {alert.risk_level}
                  </span>
                </div>

                <p className="mt-1.5 text-xs text-gray-300 line-clamp-2 leading-relaxed">
                  {alert.description}
                </p>

                <div className="mt-2.5 flex items-center justify-between text-[10px] text-gray-400">
                  <span>
                    {new Date(alert.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>

                  <div className="flex items-center space-x-2">
                    {alert.vessel_mmsi && (
                      <button
                        type="button"
                        onClick={() => {
                          const match = vessels.find((v) => v.mmsi === alert.vessel_mmsi);
                          if (match) selectVessel(match);
                        }}
                        className="text-blue-400 font-medium hover:underline"
                      >
                        Target →
                      </button>
                    )}

                    {!alert.acknowledged && (
                      <button
                        type="button"
                        onClick={() => acknowledgeAlert(alert.id)}
                        className="bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 px-2 py-0.5 rounded font-mono text-[10px] transition-colors"
                      >
                        ACK
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
