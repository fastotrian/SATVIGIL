/**
 * SATVIGIL — Global Alert & Maritime State (Zustand)
 * Stores active alerts, live vessels, layer filters, and telemetry.
 */
import { create } from "zustand";
import type { Vessel, Alert as MaritimeAlert } from "../types/maritime";

export type { Alert } from "../types/maritime";

export interface ActiveFilters {
  showVessels: boolean;
  showSpillZones: boolean;
  showMPABoundaries: boolean;
  showDensityHeatmap: boolean;
}

interface AlertStore {
  alerts: MaritimeAlert[];
  selectedAlert: MaritimeAlert | null;
  vessels: Vessel[];
  selectedVessel: Vessel | null;
  activeFilters: ActiveFilters;
  isConnected: boolean;

  setAlerts: (alerts: MaritimeAlert[]) => void;
  addAlert: (alert: MaritimeAlert) => void;
  selectAlert: (alert: MaritimeAlert | null) => void;
  acknowledgeAlert: (id: string) => void;
  setVessels: (vessels: Vessel[]) => void;
  selectVessel: (vessel: Vessel | null) => void;
  toggleFilter: (key: keyof ActiveFilters) => void;
  setIsConnected: (connected: boolean) => void;

  // Computed helper getters
  getCriticalCount: () => number;
  getWarningCount: () => number;
  getNormalCount: () => number;
}

export const useAlertStore = create<AlertStore>((set, get) => ({
  alerts: [],
  selectedAlert: null,
  vessels: [],
  selectedVessel: null,
  activeFilters: {
    showVessels: true,
    showSpillZones: true,
    showMPABoundaries: false,
    showDensityHeatmap: false,
  },
  isConnected: true,

  setAlerts: (alerts) => set({ alerts }),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts].slice(0, 500),
    })),

  selectAlert: (alert) => set({ selectedAlert: alert }),

  acknowledgeAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === id ? { ...a, acknowledged: true } : a
      ),
    })),

  setVessels: (vessels) => set({ vessels }),

  selectVessel: (vessel) => set({ selectedVessel: vessel }),

  toggleFilter: (key) =>
    set((state) => ({
      activeFilters: {
        ...state.activeFilters,
        [key]: !state.activeFilters[key],
      },
    })),

  setIsConnected: (isConnected) => set({ isConnected }),

  getCriticalCount: () =>
    get().vessels.filter((v) => v.risk_level === 'CRITICAL').length,
  getWarningCount: () =>
    get().vessels.filter((v) => v.risk_level === 'WARNING').length,
  getNormalCount: () =>
    get().vessels.filter((v) => v.risk_level === 'NORMAL').length,
}));
