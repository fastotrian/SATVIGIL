/**
 * SATVIGIL — WebSocket Client
 * Connects to backend /api/v1/alerts/live for real-time alert push.
 */
import { Alert } from "../store/alertStore";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export function connectWebSocket(onAlert: (alert: Alert) => void): WebSocket {
  const ws = new WebSocket(`${WS_URL}/api/v1/alerts/live`);

  ws.onopen = () => {
    console.log("[SATVIGIL] WebSocket connected — listening for alerts");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "ping") return;          // keepalive, ignore
      if (data.type === "new_alert") {
        onAlert(data.alert as Alert);
      }
    } catch (err) {
      console.error("[SATVIGIL] WebSocket parse error:", err);
    }
  };

  ws.onerror = (err) => {
    console.error("[SATVIGIL] WebSocket error:", err);
  };

  ws.onclose = () => {
    console.log("[SATVIGIL] WebSocket disconnected — reconnecting in 5s...");
    setTimeout(() => connectWebSocket(onAlert), 5000);
  };

  return ws;
}
