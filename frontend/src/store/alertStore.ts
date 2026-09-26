/**
 * SATVIGIL — Global Alert & Maritime State (Zustand)
 * Stores active alerts, live vessels, layer filters, and telemetry.
 */
import { create } from "zustand";
import type { Vessel, Alert as MaritimeAlert, ForensicDossier, SpillDriftForecast, DriftStepForecast } from "../types/maritime";

export type { Alert } from "../types/maritime";

export type NavTab = 'maritime' | 'thermal' | 'geological';

export interface ActiveFilters {
  showVessels: boolean;
  showSpillZones: boolean;
  showMPABoundaries: boolean;
  showDensityHeatmap: boolean;
  showFireHotspots: boolean;
  showGeologicalZones: boolean;
}

interface AlertStore {
  activeNavTab: NavTab;
  setNavTab: (tab: NavTab) => void;
  alerts: MaritimeAlert[];
  selectedAlert: MaritimeAlert | null;
  vessels: Vessel[];
  selectedVessel: Vessel | null;
  activeFilters: ActiveFilters;
  isConnected: boolean;
  isAudioMuted: boolean;
  activeDossier: ForensicDossier | null;
  isDossierOpen: boolean;

  // INCOIS-OOSA Drift Simulation
  driftForecast: SpillDriftForecast | null;
  selectedDriftHour: number;
  isDriftSimActive: boolean;
  isDriftPlaying: boolean;

  setAlerts: (alerts: MaritimeAlert[]) => void;
  addAlert: (alert: MaritimeAlert) => void;
  selectAlert: (alert: MaritimeAlert | null) => void;
  acknowledgeAlert: (id: string) => void;
  setVessels: (vessels: Vessel[]) => void;
  selectVessel: (vessel: Vessel | null) => void;
  toggleFilter: (key: keyof ActiveFilters) => void;
  setExclusiveLayer: (key: keyof ActiveFilters) => void;
  setIsConnected: (connected: boolean) => void;
  toggleAudio: () => void;
  openDossier: (dossierId?: string) => Promise<void>;
  closeDossier: () => void;
  loadDriftForecast: (spillId?: string) => Promise<void>;
  setSelectedDriftHour: (hour: number) => void;
  toggleDriftSim: (active?: boolean) => void;
  toggleDriftPlaying: () => void;
  getActiveDriftStep: () => DriftStepForecast | null;

  // Computed helper getters
  getCriticalCount: () => number;
  getWarningCount: () => number;
  getNormalCount: () => number;
}

import { SEED_ALERTS, SEED_VESSELS } from "../data/seedMaritimeData";

export const useAlertStore = create<AlertStore>((set, get) => ({
  activeNavTab: 'maritime',
  alerts: SEED_ALERTS,
  selectedAlert: null,
  vessels: SEED_VESSELS,
  selectedVessel: null,
  activeFilters: {
    showVessels: true,
    showSpillZones: true,
    showMPABoundaries: true,
    showDensityHeatmap: false,
    showFireHotspots: false,
    showGeologicalZones: false,
  },
  isConnected: true,
  isAudioMuted: false,
  activeDossier: null,
  isDossierOpen: false,
  driftForecast: null,
  selectedDriftHour: 0,
  isDriftSimActive: false,
  isDriftPlaying: false,

  setNavTab: (tab) =>
    set((state) => {
      if (tab === 'maritime') {
        return {
          activeNavTab: 'maritime',
          activeFilters: {
            ...state.activeFilters,
            showVessels: true,
            showSpillZones: true,
            showMPABoundaries: true,
            showFireHotspots: false,
            showGeologicalZones: false,
          },
        };
      } else if (tab === 'thermal') {
        return {
          activeNavTab: 'thermal',
          activeFilters: {
            ...state.activeFilters,
            showVessels: false,
            showSpillZones: false,
            showMPABoundaries: false,
            showFireHotspots: true,
            showGeologicalZones: false,
          },
        };
      } else {
        // geological
        return {
          activeNavTab: 'geological',
          activeFilters: {
            ...state.activeFilters,
            showVessels: false,
            showSpillZones: false,
            showMPABoundaries: false,
            showFireHotspots: false,
            showGeologicalZones: true,
          },
        };
      }
    }),

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

  setExclusiveLayer: (key) =>
    set((state) => {
      const isAlreadyExclusive =
        state.activeFilters[key] === true &&
        (Object.keys(state.activeFilters) as Array<keyof ActiveFilters>).every(
          (k) => k === key || state.activeFilters[k] === false
        );

      const nextFilters = {
        showVessels: false,
        showSpillZones: false,
        showMPABoundaries: false,
        showDensityHeatmap: false,
        showFireHotspots: false,
        showGeologicalZones: false,
      };

      if (!isAlreadyExclusive) {
        nextFilters[key] = true;
      }

      return {
        activeFilters: nextFilters,
      };
    }),

  setIsConnected: (isConnected) => set({ isConnected }),
  
  toggleAudio: () => set((state) => ({ isAudioMuted: !state.isAudioMuted })),

  openDossier: async (dossierId = "latest") => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/maritime/dossier/${dossierId}`);
      if (res.ok) {
        const data = await res.json();
        set({ activeDossier: data, isDossierOpen: true });
      } else {
        set({ isDossierOpen: true });
      }
    } catch {
      set({ isDossierOpen: true });
    }
  },

  closeDossier: () => set({ isDossierOpen: false }),

  loadDriftForecast: async (spillId = "latest") => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/maritime/spills/${spillId}/drift-forecast`);
      if (res.ok) {
        const data = await res.json();
        set({ driftForecast: data, isDriftSimActive: true });
      }
    } catch (err) {
      console.error("Failed to load drift forecast:", err);
    }
  },

  setSelectedDriftHour: (hour) => set({ selectedDriftHour: hour }),

  toggleDriftSim: (active) =>
    set((state) => {
      const nextActive = active !== undefined ? active : !state.isDriftSimActive;
      if (nextActive && !state.driftForecast) {
        // trigger load if missing
        get().loadDriftForecast();
      }
      return { isDriftSimActive: nextActive, isDriftPlaying: false };
    }),

  toggleDriftPlaying: () =>
    set((state) => ({ isDriftPlaying: !state.isDriftPlaying })),

  getActiveDriftStep: () => {
    const { driftForecast, selectedDriftHour } = get();
    if (!driftForecast || !driftForecast.steps.length) return null;
    return (
      driftForecast.steps.find((s) => s.time_offset_hours === selectedDriftHour) ||
      driftForecast.steps[0]
    );
  },

  getCriticalCount: () =>
    get().vessels.filter((v) => v.risk_level === 'CRITICAL').length,
  getWarningCount: () =>
    get().vessels.filter((v) => v.risk_level === 'WARNING').length,
  getNormalCount: () =>
    get().vessels.filter((v) => v.risk_level === 'NORMAL').length,
}));
