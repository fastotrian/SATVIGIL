/**
 * SATVIGIL — Global Alert & Maritime State (Zustand)
 * Stores active alerts, live vessels, layer filters, and telemetry.
 */
import { create } from "zustand";
import type { Vessel, Alert as MaritimeAlert, ForensicDossier, SpillDriftForecast, DriftStepForecast } from "../types/maritime";
import { DEFAULT_DOSSIER } from "../components/dossier/ForensicDossierModal";
import { generateLocalSpillDriftForecast } from "../utils/driftPhysics";

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
  isMpaDossierOpen: boolean;

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
  openMpaDossier: () => void;
  closeMpaDossier: () => void;
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
  isMpaDossierOpen: false,
  driftForecast: generateLocalSpillDriftForecast(),
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
    // 1. Immediately activate modal for 0ms latency feedback
    const vessel = get().selectedVessel;
    if (vessel) {
      set({
        isDossierOpen: true,
        activeDossier: {
          ...DEFAULT_DOSSIER,
          culprit_vessel: {
            ...DEFAULT_DOSSIER.culprit_vessel,
            name: vessel.vessel_name || DEFAULT_DOSSIER.culprit_vessel.name,
            mmsi: vessel.mmsi || DEFAULT_DOSSIER.culprit_vessel.mmsi,
            vessel_type: vessel.vessel_type_label || DEFAULT_DOSSIER.culprit_vessel.vessel_type,
            incident_speed_kts: vessel.speed_knots ?? DEFAULT_DOSSIER.culprit_vessel.incident_speed_kts,
            course_deg: vessel.course_deg ?? DEFAULT_DOSSIER.culprit_vessel.course_deg,
            ais_gap_duration_minutes: vessel.ais_gap_minutes ?? DEFAULT_DOSSIER.culprit_vessel.ais_gap_duration_minutes,
          },
          location: {
            lat: vessel.lat ?? DEFAULT_DOSSIER.location.lat,
            lon: vessel.lon ?? DEFAULT_DOSSIER.location.lon,
            zone: 'Arabian Sea — Mumbai High Offshore Sector (28 NM WNW)',
            eez_status: 'Indian Exclusive Economic Zone (200 NM Sovereign Boundary)',
          },
        },
      });
    } else {
      set({
        isDossierOpen: true,
        activeDossier: get().activeDossier || DEFAULT_DOSSIER,
      });
    }

    // 2. Fetch live official dossier from backend with 2s timeout
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const url = `/api/v1/maritime/dossier/${dossierId}`;
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        set({ activeDossier: data });
      }
    } catch {
      // Seamless fallback: modal is already open with pre-seeded evidentiary dossier
    }
  },

  closeDossier: () => set({ isDossierOpen: false }),

  openMpaDossier: () => set({ isMpaDossierOpen: true }),

  closeMpaDossier: () => set({ isMpaDossierOpen: false }),

  loadDriftForecast: async (spillId = "latest") => {
    // 1. Ensure local forecast is active immediately
    if (!get().driftForecast) {
      set({ driftForecast: generateLocalSpillDriftForecast(), isDriftSimActive: true });
    }
    // 2. Fetch live data from backend with 2s timeout
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`/api/v1/maritime/spills/${spillId}/drift-forecast`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        set({ driftForecast: data, isDriftSimActive: true });
      }
    } catch {
      // Seamlessly keep client-computed hydrodynamic forecast
    }
  },

  setSelectedDriftHour: (hour) => set({ selectedDriftHour: hour }),

  toggleDriftSim: (active) =>
    set((state) => {
      const nextActive = active !== undefined ? active : !state.isDriftSimActive;
      const forecast = state.driftForecast || generateLocalSpillDriftForecast();
      return {
        isDriftSimActive: nextActive,
        driftForecast: forecast,
        isDriftPlaying: false,
      };
    }),

  toggleDriftPlaying: () =>
    set((state) => ({ isDriftPlaying: !state.isDriftPlaying })),

  getActiveDriftStep: () => {
    const { driftForecast, selectedDriftHour } = get();
    const forecast = driftForecast || generateLocalSpillDriftForecast();
    return (
      forecast.steps.find((s) => s.time_offset_hours === selectedDriftHour) ||
      forecast.steps[0]
    );
  },

  getCriticalCount: () =>
    get().vessels.filter((v) => v.risk_level === 'CRITICAL').length,
  getWarningCount: () =>
    get().vessels.filter((v) => v.risk_level === 'WARNING').length,
  getNormalCount: () =>
    get().vessels.filter((v) => v.risk_level === 'NORMAL').length,
}));
