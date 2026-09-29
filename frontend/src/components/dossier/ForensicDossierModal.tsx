import React, { useState } from 'react';
import { useAlertStore } from '../../store/alertStore';
import type { ForensicDossier } from '../../types/maritime';

// Hardcoded fallback in case backend is loading
export const DEFAULT_DOSSIER: ForensicDossier = {
  dossier_id: 'ICG-DOS-2026-AR-0941',
  classification: 'RESTRICTED // LAW ENFORCEMENT & MARITIME EVIDENCE',
  issuing_authority: 'DIRECTORATE GENERAL OF SHIPPING / INDIAN COAST GUARD (WESTERN COMMAND)',
  incident_id: 'SPILL-20260907-001',
  compiled_at: '2026-09-10T19:00:00Z',
  evidence_sha256_hash: '7d8f5c3e91b24a6e804f519c23b8e714652a9103c847d1f5b630e2417c89a502',
  location: {
    lat: 19.2000,
    lon: 71.5000,
    zone: 'Arabian Sea — Mumbai High Offshore Sector (28 NM WNW)',
    eez_status: 'Indian Exclusive Economic Zone (200 NM Sovereign Boundary)',
  },
  satellite_sar: {
    satellite: 'Sentinel-1C C-SAR (IW Swath, VV/VH)',
    band: 'C-band (5.405 GHz microwave)',
    acquisition_mode: 'IW (Interferometric Wide Swath)',
    polarization: 'Dual Polarization (VV + VH)',
    orbit_pass: 'Relative Orbit Track #142 / Descending Node',
    scene_id: 'S1C_IW_GRDH_1SDV_20260910T053649_20260910T053714_055591_06C82F_B7E2',
    slick_area_km2: 4.82,
    slick_length_km: 8.4,
    slick_width_max_km: 0.92,
    est_volume_litres: 3850,
    backscatter_clean_db: -12.1,
    backscatter_slick_db: -19.5,
    backscatter_delta_db: -7.4,
    sar_image_url: '/sar_spill_bombay_high.jpg',
  },
  culprit_vessel: {
    name: 'MT GUJARAT PRIDE',
    imo: '9418236',
    mmsi: '419082341',
    call_sign: 'VTAA',
    flag_state: 'India 🇮🇳 (Indian Registry)',
    flag_code: 'IN',
    vessel_type: 'Crude Oil / Chemical Tanker',
    gross_tonnage: 62450,
    deadweight_tonnage: 115000,
    build_year: 2018,
    owner_operator: 'Gujarat Maritime Shipping Corp., Mumbai / Kandla',
    last_port_of_call: 'Fujairah Anchorage, UAE',
    destination: 'JNPT, Mumbai, India',
    pre_incident_speed_kts: 12.4,
    incident_speed_kts: 6.1,
    course_deg: 174.0,
    ais_gap_duration_minutes: 47,
  },
  attribution_ml: {
    composite_confidence: 94.2,
    spatial_proximity_score: 98.5,
    ais_dark_gap_score: 96.0,
    vessel_type_risk_score: 92.0,
    svr_kinematics_anomaly_score: 90.5,
    p_value: '< 0.001 (Statistically Significant)',
  },
  statutory_violations: [
    {
      statute: 'MARPOL 73/78 Annex I',
      regulation: 'Regulation 15 & 34',
      description: 'Unlawful discharge of oily bilge water / slop exceeding 15 ppm into the sea outside permitted en-route discharge thresholds without operating oil filtering equipment.',
    },
    {
      statute: 'Merchant Shipping Act, 1958',
      regulation: 'Section 356J & 356K',
      description: 'Direct civil liability for oil pollution damage and mandatory duty to take oil pollution prevention measures within the Indian Exclusive Economic Zone.',
    },
    {
      statute: 'Environment (Protection) Act, 1986',
      regulation: 'Section 7 & Section 15',
      description: 'Discharge of environmental pollutant in excess of prescribed standards resulting in marine ecological endangerment.',
    },
  ],
  penal_sanctions: {
    detention_order: 'Immediate Port State Control (PSC) Arrest at JNPT / Mumbai Port',
    statutory_fine_inr: '₹ 50,00,000 to ₹ 2,00,00,000',
    statutory_fine_usd: '$60,000 – $240,000 USD',
    cleanup_liability: '100% Comprehensive Ecological Remediation Cost Recovery',
    criminal_proceedings: 'Lodging of FIR against Master & Ship Operator under Merchant Shipping Act Section 356K',
  },
  containment_directive: {
    dispersant_recommended: 'Type 2/3 Concentrated Bio-dispersant (OSD-II)',
    dispersant_litres: 4200,
    boom_perimeter_meters: 2800,
    response_vessel: 'ICGS Samudra Prahari (CG-01)',
    intercept_station: 'ICG Regional HQ (West), Worli, Mumbai',
    intercept_course_deg: 248,
    intercept_speed_kts: 18.0,
    intercept_eta_hours: '2h 18m',
  },
};

export function ForensicDossierModal() {
  const { isDossierOpen, activeDossier, closeDossier } = useAlertStore();
  const [activeTab, setActiveTab] = useState<'evidence' | 'attribution' | 'legal' | 'tactical'>('evidence');
  const [dispatched, setDispatched] = useState(false);

  if (!isDossierOpen) return null;

  const dossier = activeDossier || DEFAULT_DOSSIER;

  const handlePrint = () => {
    window.print();
  };

  const handleDispatch = () => {
    setDispatched(true);
    setTimeout(() => setDispatched(false), 5000);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      {/* Modal Container */}
      <div
        className="w-full max-w-5xl rounded-xl border shadow-2xl overflow-hidden flex flex-col my-auto transition-all animate-in fade-in zoom-in-95 duration-200"
        style={{
          background: 'var(--navy-950)',
          borderColor: 'var(--navy-500)',
          maxHeight: '92vh',
        }}
      >
        {/* Top Government Emblem Banner */}
        <div
          className="px-6 py-4 border-b flex flex-wrap items-center justify-between gap-4"
          style={{
            background: 'linear-gradient(90deg, #0A1628 0%, #0F2347 50%, #0A1628 100%)',
            borderColor: 'var(--navy-500)',
          }}
        >
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded border flex items-center justify-center text-xl font-bold bg-[#060E1C] border-cyan-500/40 text-cyan-400 shadow-[0_0_15px_rgba(0,212,232,0.3)]">
              ⚖️
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold tracking-widest uppercase text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
                  {dossier.classification}
                </span>
                <span className="text-[10px] font-mono text-gray-400">
                  REF: {dossier.dossier_id}
                </span>
              </div>
              <h1 className="text-base font-extrabold text-white tracking-wide mt-0.5">
                FORENSIC OIL SPILL EVIDENTIARY DOSSIER
              </h1>
              <p className="text-[11px] text-gray-300 font-mono">
                {dossier.issuing_authority}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handlePrint}
              className="px-3.5 py-1.5 rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors border"
              style={{
                background: 'rgba(0, 212, 232, 0.15)',
                borderColor: 'var(--teal-500)',
                color: 'var(--teal-400)',
              }}
            >
              <span>🖨️</span>
              <span>Print / Save Legal PDF</span>
            </button>
            <button
              type="button"
              onClick={closeDossier}
              className="w-8 h-8 rounded flex items-center justify-center text-gray-400 hover:text-white bg-navy-900 hover:bg-navy-800 transition-colors border border-navy-700"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Executive Target Banner */}
        <div
          className="px-6 py-3 border-b flex flex-wrap items-center justify-between gap-4 text-xs font-mono"
          style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}
        >
          <div className="flex items-center gap-4">
            <div>
              <span className="text-gray-400 text-[10px] block">CULPRIT IDENTIFIED:</span>
              <span className="text-white font-bold text-sm tracking-wide text-red-400">
                {dossier.culprit_vessel.name}
              </span>
            </div>
            <div className="h-6 w-px bg-navy-700" />
            <div>
              <span className="text-gray-400 text-[10px] block">IMO / MMSI:</span>
              <span className="text-gray-200">
                {dossier.culprit_vessel.imo} / {dossier.culprit_vessel.mmsi}
              </span>
            </div>
            <div className="h-6 w-px bg-navy-700" />
            <div>
              <span className="text-gray-400 text-[10px] block">FLAG STATE:</span>
              <span className="text-gray-200">{dossier.culprit_vessel.flag_state}</span>
            </div>
            <div className="h-6 w-px bg-navy-700" />
            <div>
              <span className="text-gray-400 text-[10px] block">DISCHARGE LOCATION:</span>
              <span className="text-cyan-400">
                {dossier.location.lat.toFixed(4)}°N, {dossier.location.lon.toFixed(4)}°E
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[10px]">ML ATTRIBUTION CERTAINTY:</span>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/70 border border-red-500/50">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-red-400 font-bold text-xs font-mono">
                {dossier.attribution_ml.composite_confidence}% (P &lt; 0.001)
              </span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          className="flex border-b px-6 gap-2"
          style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}
        >
          {[
            { key: 'evidence', label: '🛰️ SAR Satellite Evidence' },
            { key: 'attribution', label: '⚡ 4-Signal Forensic Attribution' },
            { key: 'legal', label: '⚖️ MARPOL & Statutory Sanctions' },
            { key: 'tactical', label: '🛡️ ICG Intercept & Containment' },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key as any)}
              className="py-2.5 px-3 text-xs font-bold transition-all border-b-2 font-mono tracking-wide"
              style={{
                borderColor: activeTab === tab.key ? 'var(--teal-500)' : 'transparent',
                color: activeTab === tab.key ? 'var(--teal-400)' : 'var(--text-secondary)',
                background: activeTab === tab.key ? 'rgba(0, 212, 232, 0.06)' : 'transparent',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Modal Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: SATELLITE SAR EVIDENCE */}
          {activeTab === 'evidence' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                {/* Left: SAR Image Preview & Telemetry Overlay */}
                <div
                  className="rounded-lg border overflow-hidden relative group shadow-lg"
                  style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}
                >
                  <div className="p-2.5 border-b flex justify-between items-center text-xs font-mono" style={{ borderColor: 'var(--navy-600)' }}>
                    <span className="text-cyan-400 font-bold">Sentinel-1 C-SAR (IW Swath, VV/VH)</span>
                    <span className="text-gray-400 text-[10px]">C-band 5.405 GHz</span>
                  </div>
                  <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
                    <img
                      src={dossier.satellite_sar.sar_image_url}
                      alt="Sentinel-1 C-SAR Radar Slick Footprint"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Fallback styling if local image path fails
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    {/* Top Left Telemetry Overlay */}
                    <div className="absolute top-2 left-2 flex flex-col gap-1">
                      <span className="bg-black/80 text-cyan-300 text-[10px] font-mono px-2 py-0.5 rounded border border-cyan-500/40">
                        🛰️ Sentinel-1C C-SAR (IW Swath, VV/VH)
                      </span>
                      <span className="bg-black/80 text-emerald-300 text-[9px] font-mono px-2 py-0.5 rounded border border-emerald-500/40">
                        📍 19.2000°N, 71.5000°E · Bombay High
                      </span>
                    </div>
                    {/* Top Right Scene ID Badge */}
                    <div className="absolute top-2 right-2">
                      <span className="bg-black/85 text-amber-300 text-[9px] font-mono px-2 py-0.5 rounded border border-amber-500/40">
                        {dossier.satellite_sar.scene_id || 'S1C_IW_GRDH_1SDV_20260910T053649_20260910T053714_055591_06C82F_B7E2'}
                      </span>
                    </div>
                    {/* Bottom Telemetry Strip */}
                    <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center px-2 py-1 rounded bg-black/85 text-[10px] font-mono text-cyan-300 border border-cyan-500/30">
                      <span>Area: {dossier.satellite_sar.slick_area_km2} km² · Length: {dossier.satellite_sar.slick_length_km} km</span>
                      <span className="text-red-400 font-bold">Δσ₀: {dossier.satellite_sar.backscatter_delta_db} dB</span>
                    </div>
                  </div>
                  <div className="p-3 text-xs text-gray-300 space-y-1 font-mono">
                    <p>
                      <strong className="text-white">Hydrocarbon Signature:</strong> Strong capillary wave damping observed under C-band microwave radar at 19.2000°N, 71.5000°E.
                    </p>
                    <p className="text-[10px] text-gray-400">
                      Track Geometry: Relative Orbit #142 (Descending) · Incidence Angle 38.4° · Spatial Resolution: 10m Ground Range
                    </p>
                  </div>
                </div>

                {/* Right: Radar Cross-Section Metrics */}
                <div className="space-y-3 font-mono">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-cyan-400 border-b pb-1" style={{ borderColor: 'var(--navy-600)' }}>
                    Radar Backscatter Cross-Section (dB Profile)
                  </h3>

                  <div className="p-3.5 rounded-lg border space-y-2.5" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-400">Surrounding Clean Ocean Backscatter (σ₀):</span>
                      <span className="text-emerald-400 font-bold">{dossier.satellite_sar.backscatter_clean_db} dB</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-400">Oil Slick Core Minimum Backscatter (σ₀):</span>
                      <span className="text-red-400 font-bold">{dossier.satellite_sar.backscatter_slick_db} dB</span>
                    </div>
                    <div className="flex justify-between items-center text-xs pt-1 border-t" style={{ borderColor: 'var(--navy-700)' }}>
                      <span className="text-white font-bold">Relative Radar Contrast (Dampening Delta):</span>
                      <span className="text-cyan-400 font-extrabold text-sm">{dossier.satellite_sar.backscatter_delta_db} dB</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-3 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                      <span className="text-[10px] text-gray-400 block">ESTIMATED VOLUME</span>
                      <span className="text-base font-bold text-amber-400 font-mono mt-0.5 block">
                        ~{dossier.satellite_sar.est_volume_litres.toLocaleString()} Litres
                      </span>
                      <span className="text-[10px] text-gray-500">Heavy Fuel Oil / Slop</span>
                    </div>

                    <div className="p-3 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                      <span className="text-[10px] text-gray-400 block">SATELLITE ORBIT PASS</span>
                      <span className="text-xs font-bold text-white font-mono mt-0.5 block">
                        {dossier.satellite_sar.orbit_pass}
                      </span>
                      <span className="text-[10px] text-cyan-400">Copernicus Sentinel-1 C-SAR</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: 4-SIGNAL FORENSIC ATTRIBUTION */}
          {activeTab === 'attribution' && (
            <div className="space-y-6">
              <div className="p-4 rounded-lg border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-bold text-white font-mono">
                    Multi-Factor Forensic Attribution Matrix
                  </h3>
                  <span className="text-xs font-mono text-cyan-400 font-bold bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
                    Statistically Verified (P &lt; 0.001)
                  </span>
                </div>
                <p className="text-xs text-gray-300 mb-4">
                  The SATVIGIL Attribution Engine cross-references Sentinel-1 SAR acquisition geometry with backwards ocean current drift modeling and AIS kinematic variance to identify the source polluter.
                </p>

                <div className="space-y-3.5">
                  {[
                    {
                      label: '1. Spatial Proximity & Reverse Drift Trajectory',
                      score: dossier.attribution_ml.spatial_proximity_score,
                      desc: 'Back-projected spill trail coincides with vessel GPS coordinates at 18:42 UTC (0.42 km error envelope).',
                    },
                    {
                      label: '2. AIS Dark Gap Temporal Coincidence',
                      score: dossier.attribution_ml.ais_dark_gap_score,
                      desc: `Vessel disabled AIS transponder for ${dossier.culprit_vessel.ais_gap_duration_minutes} minutes during passage over the discharge coordinates.`,
                    },
                    {
                      label: '3. Vessel Type & Cargo Risk Weighting',
                      score: dossier.attribution_ml.vessel_type_risk_score,
                      desc: `${dossier.culprit_vessel.vessel_type} (DWT: ${dossier.culprit_vessel.deadweight_tonnage.toLocaleString()} MT) carrying persistent hydrocarbon cargo.`,
                    },
                    {
                      label: '4. Hydrodynamic Kinematic Trajectory Anomaly',
                      score: dossier.attribution_ml.svr_kinematics_anomaly_score,
                      desc: `Speed dropped from ${dossier.culprit_vessel.pre_incident_speed_kts} kts to ${dossier.culprit_vessel.incident_speed_kts} kts during intentional bilge pump cycle.`,
                    },
                  ].map((sig, i) => (
                    <div key={i} className="space-y-1">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-gray-200 font-semibold">{sig.label}</span>
                        <span className="text-cyan-400 font-bold">{sig.score.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-navy-950 h-2 rounded-full overflow-hidden border border-navy-700">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${sig.score}%`,
                            background: sig.score > 95 ? 'linear-gradient(90deg, #00D4E8, #22C55E)' : 'var(--teal-500)',
                          }}
                        />
                      </div>
                      <p className="text-[11px] text-gray-400 font-mono">{sig.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: MARPOL & LEGAL SANCTIONS */}
          {activeTab === 'legal' && (
            <div className="space-y-5 font-mono">
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-widest text-cyan-400 border-b pb-1" style={{ borderColor: 'var(--navy-600)' }}>
                  Statutory Violations & Applicable Maritime Law
                </h3>

                <div className="space-y-2.5">
                  {dossier.statutory_violations.map((violation, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg border text-xs space-y-1"
                      style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-red-400 font-bold">{violation.statute} — {violation.regulation}</span>
                        <span className="text-[10px] text-gray-400 bg-red-950/60 px-1.5 py-0.5 rounded border border-red-500/30">
                          CRIMINAL INFRACTION
                        </span>
                      </div>
                      <p className="text-gray-300">{violation.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-widest text-red-400 border-b pb-1" style={{ borderColor: 'var(--navy-600)' }}>
                  Recommended Penal Sanctions & Enforcement Directives
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                    <span className="text-[10px] text-gray-400 block">VESSEL DETENTION ORDER:</span>
                    <span className="text-white font-bold block mt-1">{dossier.penal_sanctions.detention_order}</span>
                  </div>

                  <div className="p-3 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                    <span className="text-[10px] text-gray-400 block">STATUTORY PENALTY:</span>
                    <span className="text-amber-400 font-bold block mt-1">
                      {dossier.penal_sanctions.statutory_fine_inr} ({dossier.penal_sanctions.statutory_fine_usd})
                    </span>
                  </div>

                  <div className="p-3 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                    <span className="text-[10px] text-gray-400 block">CLEANUP COST RECOVERY:</span>
                    <span className="text-emerald-400 font-bold block mt-1">{dossier.penal_sanctions.cleanup_liability}</span>
                  </div>

                  <div className="p-3 rounded border" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}>
                    <span className="text-[10px] text-gray-400 block">LEGAL PROCEEDINGS:</span>
                    <span className="text-red-300 font-bold block mt-1">{dossier.penal_sanctions.criminal_proceedings}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: ICG TACTICAL DIRECTIVE */}
          {activeTab === 'tactical' && (
            <div className="space-y-5 font-mono">
              <div className="p-4 rounded-lg border space-y-4" style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-500)' }}>
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white">
                    Indian Coast Guard (ICG) Tactical Response Directive
                  </h3>
                  <span className="text-xs text-cyan-400 font-bold bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-500/30">
                    OP-ORDER: ICG-WEST-POLLUTION-01
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="space-y-2">
                    <div className="p-3 rounded border" style={{ background: 'var(--navy-950)', borderColor: 'var(--navy-700)' }}>
                      <span className="text-[10px] text-gray-400 block">ASSIGNED POLLUTION RESPONSE VESSEL:</span>
                      <span className="text-white font-bold text-sm block mt-0.5">
                        {dossier.containment_directive.response_vessel}
                      </span>
                      <span className="text-[11px] text-cyan-400">Stationed at {dossier.containment_directive.intercept_station}</span>
                    </div>

                    <div className="p-3 rounded border" style={{ background: 'var(--navy-950)', borderColor: 'var(--navy-700)' }}>
                      <span className="text-[10px] text-gray-400 block">INTERCEPT VECTOR:</span>
                      <span className="text-emerald-400 font-bold block mt-0.5">
                        Heading {dossier.containment_directive.intercept_course_deg}° True @ {dossier.containment_directive.intercept_speed_kts} kts
                      </span>
                      <span className="text-[11px] text-gray-300">Estimated Intercept ETA: <strong className="text-white">{dossier.containment_directive.intercept_eta_hours}</strong></span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="p-3 rounded border" style={{ background: 'var(--navy-950)', borderColor: 'var(--navy-700)' }}>
                      <span className="text-[10px] text-gray-400 block">RECOMMENDED DISPERSANT:</span>
                      <span className="text-amber-400 font-bold block mt-0.5">
                        {dossier.containment_directive.dispersant_litres.toLocaleString()} Litres ({dossier.containment_directive.dispersant_recommended})
                      </span>
                    </div>

                    <div className="p-3 rounded border" style={{ background: 'var(--navy-950)', borderColor: 'var(--navy-700)' }}>
                      <span className="text-[10px] text-gray-400 block">CONTAINMENT BOOM PERIMETER:</span>
                      <span className="text-cyan-400 font-bold block mt-0.5">
                        {dossier.containment_directive.boom_perimeter_meters.toLocaleString()} Meters Offshore Heavy Duty Boom
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {dispatched && (
                <div className="p-3 rounded border border-emerald-500/50 bg-emerald-950/70 text-emerald-300 text-xs font-mono flex items-center gap-2 animate-in fade-in">
                  <span>✅</span>
                  <span><strong>TACTICAL ORDER TRANSMITTED:</strong> Tasked <em>{dossier.containment_directive.response_vessel}</em> via Indian Coast Guard Western Operational Command. Intercept course set to {dossier.containment_directive.intercept_course_deg}°.</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div
          className="px-6 py-4 border-t flex flex-wrap items-center justify-between gap-4"
          style={{ background: 'var(--navy-900)', borderColor: 'var(--navy-600)' }}
        >
          <div className="flex flex-col gap-0.5 text-xs font-mono text-gray-400">
            <span className="flex items-center gap-1.5 text-gray-300 font-semibold">
              🛡️ Indian Merchant Shipping Act 1958 & MARPOL Annex I Compliant
            </span>
            <span className="text-[10px] text-gray-400 font-mono truncate max-w-md" title={dossier.evidence_sha256_hash}>
              SHA-256 PROOF: <span className="text-cyan-400/90">{dossier.evidence_sha256_hash || '7d8f5c3e91b24a6e804f519c23b8e714652a9103c847d1f5b630e2417c89a502'}</span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDispatch}
              className="px-4 py-2 rounded text-xs font-mono font-bold transition-colors flex items-center gap-1.5 shadow"
              style={{
                background: 'var(--red-600)',
                color: '#ffffff',
              }}
            >
              <span>🚨</span>
              <span>Dispatch Intercept to ICGS Samudra Prahari</span>
            </button>

            <button
              type="button"
              onClick={handlePrint}
              className="px-4 py-2 rounded text-xs font-mono font-bold transition-colors flex items-center gap-1.5 border"
              style={{
                background: 'var(--teal-500)',
                borderColor: 'var(--teal-400)',
                color: 'var(--navy-950)',
              }}
            >
              <span>📄</span>
              <span>Export Legal Dossier (PDF)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
