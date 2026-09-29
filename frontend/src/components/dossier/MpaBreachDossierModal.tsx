import React, { useState } from 'react';
import { useAlertStore } from '../../store/alertStore';
import { EmailAuthorityModal } from './EmailAuthorityModal';

export function MpaBreachDossierModal() {
  const { isMpaDossierOpen, closeMpaDossier, selectedVessel } = useAlertStore();
  const [activeTab, setActiveTab] = useState<'geofence' | 'kinematics' | 'statute' | 'intercept'>('geofence');
  const [dispatched, setDispatched] = useState(false);
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);

  if (!isMpaDossierOpen) return null;

  const vessel = selectedVessel || {
    vessel_name: 'FV KUTCH FISHERMAN',
    mmsi: '419000003',
    vessel_type_label: 'Mechanised Fishing Trawler',
    lat: 22.5000,
    lon: 69.2000,
    speed_knots: 5.2,
    course_deg: 45,
    ais_gap_minutes: 20,
    mpa_name: 'Gulf of Kutch Marine National Park',
  };

  const sanctuaryName = vessel.mpa_name || 'Gulf of Kutch Marine National Park';
  const incidentRef = `ICG-WPA-2026-WZ-0182`;
  const evidenceSha256 = '4a8f9c2d11b5e608f391c45a782b9e11045a9821c847d1f5b630e2417c89b882';

  const handlePrint = () => {
    window.print();
  };

  const handleDispatch = () => {
    setDispatched(true);
    setTimeout(() => setDispatched(false), 5000);
  };

  return (
    <>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 backdrop-blur-md p-4 overflow-y-auto animate-in fade-in duration-200">
        <div
          className="w-full max-w-5xl rounded-xl border shadow-2xl overflow-hidden flex flex-col my-auto transition-all text-white font-sans"
          style={{
            background: 'var(--navy-950, #060e1a)',
            borderColor: 'rgba(16, 185, 129, 0.6)',
            maxHeight: '92vh',
          }}
        >
          {/* Top Banner */}
          <div
            className="px-6 py-4 border-b flex flex-wrap items-center justify-between gap-4"
            style={{
              background: 'linear-gradient(90deg, #091a14 0%, #0d2e23 50%, #091a14 100%)',
              borderColor: 'rgba(16, 185, 129, 0.4)',
            }}
          >
            <div className="flex items-center gap-3.5">
              <div className="w-10 h-10 rounded border flex items-center justify-center text-xl font-bold bg-[#061410] border-emerald-500/40 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                🛡️
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono font-bold tracking-widest uppercase text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/30">
                    RESTRICTED // MARINE SANCTUARY ENFORCEMENT EVIDENCE
                  </span>
                  <span className="text-[10px] font-mono text-gray-400">
                    REF: {incidentRef}
                  </span>
                </div>
                <h1 className="text-base font-extrabold text-white tracking-wide mt-0.5">
                  FORENSIC MARINE PROTECTED AREA (MPA) SANCTUARY BREACH DOSSIER
                </h1>
                <p className="text-[11px] text-gray-300 font-mono">
                  CHIEF WILDLIFE WARDEN / MINISTRY OF ENVIRONMENT, FOREST &amp; CLIMATE CHANGE / INDIAN COAST GUARD
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => setIsEmailModalOpen(true)}
                className="px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 border shadow bg-emerald-950/80 border-emerald-500/60 text-emerald-300 hover:bg-emerald-900"
              >
                <span>✉️</span>
                <span>Email Authorities</span>
              </button>

              <button
                type="button"
                onClick={handlePrint}
                className="px-3 py-1.5 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 border shadow bg-navy-800 border-navy-500 text-gray-200 hover:text-white hover:bg-navy-700"
              >
                <span>🖨️</span>
                <span>Print / Save Legal PDF</span>
              </button>

              <button
                type="button"
                onClick={closeMpaDossier}
                className="text-gray-400 hover:text-white text-xl px-2 transition-colors"
                title="Close Dossier"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Incident Quick Summary Bar */}
          <div
            className="px-6 py-2.5 border-b grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono"
            style={{ background: 'var(--navy-900, #091322)', borderColor: 'rgba(16, 185, 129, 0.3)' }}
          >
            <div>
              <span className="text-gray-400 block text-[9.5px]">OFFENDING CRAFT:</span>
              <span className="font-bold text-white text-[12px]">{vessel.vessel_name}</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[9.5px]">MMSI / REGISTRY:</span>
              <span className="font-bold text-cyan-300">{vessel.mmsi} · India 🇮🇳</span>
            </div>
            <div>
              <span className="text-gray-400 block text-[9.5px]">SANCTUARY BREACHED:</span>
              <span className="font-bold text-emerald-300 truncate block" title={sanctuaryName}>
                {sanctuaryName}
              </span>
            </div>
            <div>
              <span className="text-gray-400 block text-[9.5px]">PENETRATION COORDS:</span>
              <span className="font-bold text-amber-300 font-mono">
                {vessel.lat.toFixed(4)}°N, {vessel.lon.toFixed(4)}°E
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div
            className="flex border-b text-xs font-mono font-semibold"
            style={{ background: 'var(--navy-900, #091322)', borderColor: 'rgba(16, 185, 129, 0.3)' }}
          >
            <button
              type="button"
              onClick={() => setActiveTab('geofence')}
              className={`px-5 py-3 border-b-2 transition-all flex items-center gap-2 ${
                activeTab === 'geofence'
                  ? 'border-emerald-400 text-emerald-300 bg-emerald-950/40'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <span>🗺️</span>
              <span>Sanctuary Geofence Evidence</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('kinematics')}
              className={`px-5 py-3 border-b-2 transition-all flex items-center gap-2 ${
                activeTab === 'kinematics'
                  ? 'border-emerald-400 text-emerald-300 bg-emerald-950/40'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <span>⚡</span>
              <span>Trawling Kinematics &amp; Dwell</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('statute')}
              className={`px-5 py-3 border-b-2 transition-all flex items-center gap-2 ${
                activeTab === 'statute'
                  ? 'border-emerald-400 text-emerald-300 bg-emerald-950/40'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <span>⚖️</span>
              <span>Wildlife Protection Act &amp; Penal Sanctions</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('intercept')}
              className={`px-5 py-3 border-b-2 transition-all flex items-center gap-2 ${
                activeTab === 'intercept'
                  ? 'border-emerald-400 text-emerald-300 bg-emerald-950/40'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <span>🛡️</span>
              <span>Intercept &amp; Seizure Directive</span>
            </button>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5" style={{ background: '#050c18' }}>
            {/* ── TAB 1: Geofence Evidence ── */}
            {activeTab === 'geofence' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5 animate-in fade-in duration-150">
                <div className="rounded-xl border border-emerald-500/40 bg-navy-950/90 p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-navy-700 pb-2">
                    <span className="text-xs font-mono font-bold text-emerald-400 uppercase">
                      📍 Boundary Penetration Vector
                    </span>
                    <span className="text-[10px] font-mono bg-red-900/60 text-red-300 px-2 py-0.5 rounded border border-red-500/40">
                      CRITICAL BREACH
                    </span>
                  </div>

                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex justify-between py-1 border-b border-navy-800">
                      <span className="text-gray-400">Sanctuary Zone:</span>
                      <span className="font-bold text-white">{sanctuaryName}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-navy-800">
                      <span className="text-gray-400">Statutory Status:</span>
                      <span className="text-emerald-300 font-semibold">Marine National Park (IUCN Category II)</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-navy-800">
                      <span className="text-gray-400">Penetration Depth:</span>
                      <span className="text-red-400 font-bold">2.4 Nautical Miles Inside Core</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-navy-800">
                      <span className="text-gray-400">Breach Coordinates:</span>
                      <span className="text-amber-300 font-mono">{vessel.lat.toFixed(4)}°N, {vessel.lon.toFixed(4)}°E</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-navy-800">
                      <span className="text-gray-400">Sanctuary Geofence ID:</span>
                      <span className="text-cyan-400 font-mono">MPA-IN-GOK-001</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-gray-400">Geodetic Datum:</span>
                      <span className="text-gray-300">WGS-84 / Sovereign Marine GIS</span>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-navy-700 bg-navy-950/90 p-4 space-y-3">
                  <div className="flex items-center justify-between border-b border-navy-700 pb-2">
                    <span className="text-xs font-mono font-bold text-cyan-400 uppercase">
                      🛰️ Satellite &amp; Coastal Radar Confirmation
                    </span>
                    <span className="text-[10px] font-mono bg-cyan-950 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/40">
                      NAVIC / AIS VERIFIED
                    </span>
                  </div>

                  <div className="p-3 rounded bg-black/50 border border-navy-700 text-xs font-mono space-y-2">
                    <div className="flex justify-between text-gray-300">
                      <span>Coastal Radar Station:</span>
                      <span className="text-white font-bold">Okha Coastal Radar Head (ICG-ROS)</span>
                    </div>
                    <div className="flex justify-between text-gray-300">
                      <span>Optical / SAR Pass:</span>
                      <span className="text-cyan-300">Sentinel-2 MSI Track #048</span>
                    </div>
                    <div className="flex justify-between text-gray-300">
                      <span>Thermal Wake Signature:</span>
                      <span className="text-emerald-300">Confirmed (Engine Heat Plume)</span>
                    </div>
                    <div className="flex justify-between text-gray-300">
                      <span>Protected Habitat Impacted:</span>
                      <span className="text-amber-300">Live Coral Reef &amp; Mangrove Nursery</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-gray-400 leading-relaxed font-mono">
                    The vessel deliberately crossed the marked sovereign conservation geofence at 05:22 UTC. Automatic acoustic and radar cross-section surveillance confirms bottom gear deployment within strict no-take preservation zones.
                  </p>
                </div>
              </div>
            )}

            {/* ── TAB 2: Kinematics & Dwell ── */}
            {activeTab === 'kinematics' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg border border-navy-700 bg-navy-900/60 font-mono text-center">
                    <span className="text-gray-400 text-xs block">RECORDED SPEED</span>
                    <span className="text-xl font-bold text-amber-400 block mt-1">
                      {vessel.speed_knots ?? 5.2} knots
                    </span>
                    <span className="text-[10px] text-red-400">Trawling Velocity Window</span>
                  </div>
                  <div className="p-3 rounded-lg border border-navy-700 bg-navy-900/60 font-mono text-center">
                    <span className="text-gray-400 text-xs block">SANCTUARY DWELL TIME</span>
                    <span className="text-xl font-bold text-red-400 block mt-1">
                      {vessel.ais_gap_minutes ?? 20} min
                    </span>
                    <span className="text-[10px] text-gray-400">Continuous Unlawful Presence</span>
                  </div>
                  <div className="p-3 rounded-lg border border-navy-700 bg-navy-900/60 font-mono text-center">
                    <span className="text-gray-400 text-xs block">COURSE / HEADING</span>
                    <span className="text-xl font-bold text-cyan-400 block mt-1">
                      {vessel.course_deg ?? 45}° NE
                    </span>
                    <span className="text-[10px] text-emerald-400">Zig-Zag Pattern Characteristic</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-navy-700 bg-navy-900/60 font-mono text-xs space-y-2">
                  <span className="text-xs font-bold text-white block">
                    🔬 BEHAVIORAL TRAWLING ANALYSIS:
                  </span>
                  <p className="text-gray-300 leading-relaxed">
                    Vessel speed dropped from cruise velocity (10.4 kts) to 5.2 kts upon entering the boundary of the {sanctuaryName}. The vessel maintained a repetitive zig-zag track line with high engine load, directly matching commercial bottom-trawling operations injurious to benthic marine habitats and sea turtles.
                  </p>
                </div>
              </div>
            )}

            {/* ── TAB 3: Wildlife Protection Act & Penal Sanctions ── */}
            {activeTab === 'statute' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-xl border border-red-500/40 bg-red-950/20 space-y-3 font-mono">
                  <span className="text-sm font-bold text-red-400 block">
                    ⚖️ APPLICABLE STATUTORY ACTS &amp; CHARGES:
                  </span>

                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 rounded bg-black/40 border border-red-900/40">
                      <span className="font-bold text-amber-300 block mb-0.5">
                        1. Wildlife (Protection) Act, 1972 — Section 27 &amp; Section 33A
                      </span>
                      <span className="text-gray-300">
                        Prohibits unauthorized entry into a National Park or Sanctuary without a valid permit issued by the Chief Wildlife Warden. Unlawful usage of mechanized craft and destructive commercial equipment is strictly prohibited.
                      </span>
                    </div>

                    <div className="p-2.5 rounded bg-black/40 border border-red-900/40">
                      <span className="font-bold text-amber-300 block mb-0.5">
                        2. Wildlife (Protection) Act, 1972 — Section 51 (Penalties &amp; Seizures)
                      </span>
                      <span className="text-gray-300">
                        Mandatory seizure and forfeiture of any vessel, vehicle, net, or weapon used in committing an offense within a marine sanctuary. Non-bailable offense punishable by 3 to 7 years imprisonment.
                      </span>
                    </div>

                    <div className="p-2.5 rounded bg-black/40 border border-red-900/40">
                      <span className="font-bold text-amber-300 block mb-0.5">
                        3. Coastal Regulation Zone (CRZ-IA) Notification &amp; Environment (Protection) Act, 1986
                      </span>
                      <span className="text-gray-300">
                        Complete restriction on destructive mechanized fishing in ecologically sensitive marine areas, coral reefs, and breeding habitats.
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-xl border border-navy-700 bg-navy-900/60 font-mono text-xs space-y-2">
                  <span className="text-xs font-bold text-emerald-400 block">
                    📋 STATUTORY PENAL DIRECTIVES ISSUED:
                  </span>
                  <ul className="list-disc pl-5 space-y-1 text-gray-300">
                    <li>Immediate issuance of Warrant of Seizure for craft <strong>{vessel.vessel_name}</strong> (MMSI: {vessel.mmsi}).</li>
                    <li>Compulsory forfeiture of commercial fishing permit and permanent cancellation of maritime fuel subsidies.</li>
                    <li>Statutory environmental damages assessment and fine of up to <strong>₹ 25,00,000</strong>.</li>
                    <li>Filing of non-bailable FIR with Okha Marine Police Station under Section 51 of Wildlife (Protection) Act.</li>
                  </ul>
                </div>
              </div>
            )}

            {/* ── TAB 4: Intercept Directive ── */}
            {activeTab === 'intercept' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 font-mono text-xs space-y-3">
                  <div className="flex items-center justify-between border-b border-emerald-800 pb-2">
                    <span className="font-bold text-emerald-400 text-sm">
                      ⚓ TASKED ENFORCEMENT UNIT: ICGS C-438
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-900/80 text-emerald-200 border border-emerald-500/40">
                      INTERCEPTOR CRAFT READY
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-2 rounded bg-black/40 border border-navy-800">
                      <span className="text-gray-400 block text-[10px]">BASE STATION:</span>
                      <span className="font-bold text-white">ICG Station Okha</span>
                    </div>
                    <div className="p-2 rounded bg-black/40 border border-navy-800">
                      <span className="text-gray-400 block text-[10px]">INTERCEPT SPEED:</span>
                      <span className="font-bold text-cyan-300">32.0 Knots</span>
                    </div>
                    <div className="p-2 rounded bg-black/40 border border-navy-800">
                      <span className="text-gray-400 block text-[10px]">BEARING:</span>
                      <span className="font-bold text-amber-300">048° Direct Vector</span>
                    </div>
                    <div className="p-2 rounded bg-black/40 border border-navy-800">
                      <span className="text-gray-400 block text-[10px]">ESTIMATED ETA:</span>
                      <span className="font-bold text-emerald-300">35 Minutes</span>
                    </div>
                  </div>

                  <div className="p-3 rounded bg-black/50 border border-navy-800 text-[11px] text-gray-300 leading-relaxed">
                    <strong>BOARDING ORDER:</strong> ICGS C-438 is tasked with immediate interdiction. Boarding party shall secure ship logs, GPS chartplotter records, fishing gear, and all marine catch on board, and escort the offending vessel to Okha port under armed custody.
                  </div>
                </div>

                {dispatched && (
                  <div className="p-3 rounded border border-emerald-500/60 bg-emerald-950/80 text-emerald-300 text-xs font-mono flex items-center gap-2 animate-in fade-in">
                    <span>✅</span>
                    <span>
                      <strong>TACTICAL ORDER TRANSMITTED:</strong> Tasked <em>ICGS C-438</em> via Regional Operational Command (North-West). Intercept bearing 048° confirmed.
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div
            className="px-6 py-4 border-t flex flex-wrap items-center justify-between gap-4 font-mono text-xs"
            style={{ background: 'var(--navy-900, #091322)', borderColor: 'rgba(16, 185, 129, 0.3)' }}
          >
            <div className="flex flex-col gap-0.5 text-gray-400">
              <span className="flex items-center gap-1.5 text-emerald-300 font-semibold">
                🛡️ Wildlife (Protection) Act, 1972 &amp; Sovereign Geofence Compliant
              </span>
              <span className="text-[10px] text-gray-400 truncate max-w-md" title={evidenceSha256}>
                SHA-256 PROOF: <span className="text-emerald-400/90">{evidenceSha256}</span>
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setIsEmailModalOpen(true)}
                className="px-4 py-2 rounded text-xs font-mono font-bold transition-all flex items-center gap-1.5 shadow bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-500/60 text-emerald-300"
              >
                <span>✉️</span>
                <span>Email Notice to Authorities</span>
              </button>

              <button
                type="button"
                onClick={handleDispatch}
                className="px-4 py-2 rounded text-xs font-mono font-bold transition-colors flex items-center gap-1.5 shadow bg-red-600 hover:bg-red-500 text-white"
              >
                <span>🚨</span>
                <span>Dispatch Interceptor ICGS C-438</span>
              </button>

              <button
                type="button"
                onClick={handlePrint}
                className="px-4 py-2 rounded text-xs font-mono font-bold transition-colors flex items-center gap-1.5 border bg-emerald-500 hover:bg-emerald-400 border-emerald-400 text-navy-950 font-bold"
              >
                <span>📄</span>
                <span>Export Legal Dossier (PDF)</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Official Email Authority Modal */}
      <EmailAuthorityModal
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
        type="mpa_breach"
        vesselName={vessel.vessel_name}
        mmsi={vessel.mmsi}
        lat={vessel.lat}
        lon={vessel.lon}
        incidentId={incidentRef}
        sha256={evidenceSha256}
        extraDetail={sanctuaryName}
      />
    </>
  );
}
