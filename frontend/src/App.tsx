/**
 * SATVIGIL — Root Application Component
 * 4-Zone Clean Command Center Architecture:
 *   - Top: Header Bar (Brand, Live UTC, Sensor Badges, Quick Threat Counters)
 *   - Left / Center: Interactive MapView (Clustered vessel markers, collapsible layer dock, SAR overlays)
 *   - Right: Compact Threat Feed (320px, collapsible with expand toggle)
 *   - Bottom: Fixed Bloomberg-style Ops Log Telemetry Ticker (28px)
 */
import { useEffect, useState } from "react";
import { MapView } from "./components/map/MapView";
import { AlertPanel } from "./components/alerts/AlertPanel";
import { DashboardHeader } from "./components/dashboard/DashboardHeader";
import { OpsLogFooter } from "./components/dashboard/OpsLogFooter";
import { AlertDetailsDrawer } from "./components/alerts/AlertDetailsDrawer";
import { ForensicDossierModal } from "./components/dossier/ForensicDossierModal";
import { MpaBreachDossierModal } from "./components/dossier/MpaBreachDossierModal";
import { AgriIntelView } from "./components/agri/AgriIntelView";
import { DamageAssessmentPanel } from "./components/agri/DamageAssessmentPanel";
import { useAlertStore } from "./store/alertStore";
import { connectWebSocket } from "./services/websocket";
import { playAlarm } from "./services/soundEffects";

export default function App() {
  const { activeNavTab, setAlerts, addAlert, isAudioMuted } = useAlertStore();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    // Connect to backend WebSocket for real-time alerts
    const ws = connectWebSocket({
      onInit: (alerts) => {
        setAlerts(alerts);
      },
      onAlert: (alert) => {
        addAlert(alert);
        if (!isAudioMuted) {
          playAlarm(alert.risk_level === 'CRITICAL' ? 'critical' : 'warning');
        }
      }
    });
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Component unmounted");
      } else if (ws.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => ws.close(1000, "Component unmounted");
      }
    };
  }, [setAlerts, addAlert, isAudioMuted]);

  return (
    <div className="flex flex-col h-screen text-white overflow-hidden" style={{ background: 'var(--navy-950)', fontFamily: 'var(--font-ui)' }}>
      {/* ── Top Bar: Telemetry, Sensors, System Clock ── */}
      <DashboardHeader />

      {/* ── Center Workspace: Map + Collapsible Threat Feed ── */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Full Map Canvas */}
        <div className="flex-1 relative h-full flex flex-col overflow-hidden">
          {activeNavTab === 'agri' ? (
            <AgriIntelView />
          ) : (
            <MapView />
          )}
        </div>

        {/* Right Panel: Threat Feed for Maritime/Thermal/Geological, Crop Damage Assessment for AGRI INTEL */}
        {isSidebarOpen ? (
          <div
            className="w-80 h-full overflow-hidden shrink-0 shadow-2xl z-20 transition-all border-l border-navy-500/80"
            style={{ background: 'var(--navy-950)' }}
          >
            {activeNavTab === 'agri' ? (
              <DamageAssessmentPanel
                isRightDrawer={true}
                onClose={() => setIsSidebarOpen(false)}
              />
            ) : (
              <AlertPanel
                isCollapsed={false}
                onToggleCollapse={() => setIsSidebarOpen(false)}
              />
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setIsSidebarOpen(true)}
            className="absolute top-3 right-3 z-30 px-6 py-1.5 rounded-md font-mono text-xs font-bold border border-cyan-500/50 bg-[#071326]/85 backdrop-blur-md text-cyan-300 shadow-2xl flex items-center gap-1.5 hover:bg-[#0d2244] hover:text-white transition-all pointer-events-auto"
            title={activeNavTab === 'agri' ? 'Expand Crop Damage Assessment' : 'Expand Threat Feed'}
          >
            <span>◀</span>
            <span>{activeNavTab === 'agri' ? 'Crop Damage' : 'Threat Feed'}</span>
          </button>
        )}

        {/* Slide-in details drawer */}
        <AlertDetailsDrawer />
      </div>

      {/* ── Bottom Strip: Single-Line Operational Marquee Ticker ── */}
      <OpsLogFooter />

      {/* Forensic Evidentiary Legal Dossier Modal (Root Level Overlay) */}
      <ForensicDossierModal />

      {/* Forensic Marine Protected Area (MPA) Sanctuary Breach Dossier Modal */}
      <MpaBreachDossierModal />
    </div>
  );
}
