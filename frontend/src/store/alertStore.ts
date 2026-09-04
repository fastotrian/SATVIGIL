/**
 * SATVIGIL — Global Alert State (Zustand)
 * Stores all active alerts and selected alert for map drill-down.
 */
import { create } from "zustand";

export interface Alert {
  id: number;
  alert_type: string;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_score: number;
  latitude: number;
  longitude: number;
  title: string;
  description?: string;
  source_dataset?: string;
  confidence?: string;
  is_active: boolean;
  created_at: string;
}

interface AlertStore {
  alerts: Alert[];
  selectedAlert: Alert | null;
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  selectAlert: (alert: Alert | null) => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  selectedAlert: null,

  setAlerts: (alerts) => set({ alerts }),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 500), // Keep last 500 alerts
    })),

  selectAlert: (alert) => set({ selectedAlert: alert }),
}));
