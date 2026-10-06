/**
 * SATVIGIL — WebSocket Client
 * Connects to backend /api/v1/alerts/live for real-time alert push.
 */
import { Alert } from "../store/alertStore";

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = import.meta.env.VITE_WS_URL && !import.meta.env.VITE_WS_URL.includes('backend') ? import.meta.env.VITE_WS_URL : `${protocol}//${window.location.host}`;

export function connectWebSocket({
  onInit,
  onAlert
}: {
  onInit: (alerts: Alert[]) => void;
  onAlert: (alert: Alert) => void;
}): WebSocket {
  const ws = new WebSocket(`${WS_URL}/api/v1/alerts/live`);

  ws.onopen = () => {
    console.log("[SATVIGIL] WebSocket connected — listening for alerts");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event === "ping") return;          // keepalive, ignore
      if (data.event === "init") {
        onInit(data.data as Alert[]);
      } else if (data.event === "new_alert") {
        onAlert(data.data as Alert);
      }
    } catch (err) {
      console.error("[SATVIGIL] WebSocket parse error:", err);
    }
  };

  ws.onerror = (err) => {
    console.error("[SATVIGIL] WebSocket error:", err);
  };

  ws.onclose = (e) => {
    if (e.code !== 1000) {
      console.log("[SATVIGIL] WebSocket disconnected — reconnecting in 5s...");
      setTimeout(() => connectWebSocket({ onInit, onAlert }), 5000);
    }
  };

  return ws;
}
