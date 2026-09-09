/**
 * SATVIGIL — Root Application Component
 * Layout: full-screen map + sidebar alert panel
 */
import { useEffect } from "react";
import { MapView } from "./components/map/MapView";
import { AlertPanel } from "./components/alerts/AlertPanel";
import { DashboardHeader } from "./components/dashboard/DashboardHeader";
import { AlertDetailsDrawer } from "./components/alerts/AlertDetailsDrawer";
import { useAlertStore } from "./store/alertStore";
import { connectWebSocket } from "./services/websocket";
import { playAlarm } from "./services/soundEffects";

export default function App() {
  const { addAlert, isAudioMuted } = useAlertStore();

  useEffect(() => {
    // Connect to backend WebSocket for real-time alerts
    const ws = connectWebSocket((alert) => {
      addAlert(alert);
      if (!isAudioMuted) {
        playAlarm(alert.risk_level === 'CRITICAL' ? 'critical' : 'warning');
      }
    });
    return () => ws.close();
  }, [addAlert, isAudioMuted]);

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white">
      {/* Top header bar */}
      <DashboardHeader />

      {/* Main content: map + sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Full-screen India map */}
        <div className="flex-1 relative">
          <MapView />
        </div>

        {/* Alert sidebar (right) */}
        <div className="w-96 bg-gray-900 border-l border-gray-800 overflow-y-auto">
          <AlertPanel />
        </div>
        
        {/* Slide-in details drawer */}
        <AlertDetailsDrawer />
      </div>
    </div>
  );
}
