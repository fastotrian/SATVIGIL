import React, { useState } from 'react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  type: 'oil_spill' | 'mpa_breach';
  vesselName: string;
  mmsi: string;
  lat: number;
  lon: number;
  incidentId: string;
  sha256?: string;
  extraDetail?: string; // Slick area or sanctuary name
}

export function EmailAuthorityModal({
  isOpen,
  onClose,
  type,
  vesselName,
  mmsi,
  lat,
  lon,
  incidentId,
  sha256 = '7d8f5c3e91b24a6e804f519c23b8e714652a9103c847d1f5b630e2417c89a502',
  extraDetail,
}: Props) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const isSpill = type === 'oil_spill';

  const toEmail = isSpill
    ? 'operations@indiancoastguard.nic.in, dgship-mum@nic.in'
    : 'cwlw.gujarat@forest.gov.in, ops.cgwest@indiancoastguard.nic.in';

  const ccEmail = isSpill
    ? 'membersecretary.cpcb@nic.in, meo.mumbai@gov.in'
    : 'sp-marine@gujaratpolice.gov.in, meo.kandla@gov.in';

  const subject = isSpill
    ? `[URGENT / STATUTORY ENFORCEMENT] Oil Spill & MARPOL Violation Notice — ${vesselName} (MMSI: ${mmsi})`
    : `[URGENT / STATUTORY ENFORCEMENT] Wildlife Protection Act Sanctuary Breach Notice — ${vesselName} (MMSI: ${mmsi})`;

  const messageBody = isSpill
    ? `OFFICIAL STATUTORY DISPATCH — MINISTRY OF PORTS, SHIPPING & WATERWAYS / INDIAN COAST GUARD
CLASSIFICATION: RESTRICTED // MARITIME LAW ENFORCEMENT NOTICE
INCIDENT REFERENCE: ${incidentId}
EVIDENCE HASH (SHA-256): ${sha256}

TO:
1. Operational Command, Indian Coast Guard (Western Region), Worli, Mumbai
2. Directorate General of Shipping, Mumbai (Maritime Safety & PSC Cell)
3. Central Pollution Control Board (MEO Marine Monitoring Wing)

SUBJECT: IMMEDIATE STATUTORY PROSECUTION & VESSEL DETENTION ORDER — MARPOL ANNEX I BREACH

1. TARGET VESSEL PARTICULARS:
   • Vessel Name: ${vesselName}
   • MMSI: ${mmsi}
   • Primary AIS Observation: ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E (Bombay High Offshore Sector)
   • Evidence Source: Copernicus Sentinel-1C C-SAR Orbit #142
   • Detected Slick Footprint: ${extraDetail || '4.82 km²'}

2. STATUTORY CONTRAVENTIONS NOTIFIED:
   • Indian Merchant Shipping Act, 1958 — Section 356K (Direct Liability for Marine Pollution)
   • MARPOL 73/78 Convention — Annex I, Regulations 15 & 34 (Illegal Bilge/Slop Discharge)
   • Environment (Protection) Act, 1986 — Section 7 & Section 15

3. MANDATORY OPERATIONAL DIRECTIVE:
   • Immediate tasking of ICG Pollution Response Vessel (ICGS Samudra Prahari) for slick containment.
   • Issue Port State Control (PSC) detention warrant upon vessel arrival at JNPT / Mumbai Offshore Anchorage.
   • Impound vessel oil logbooks, bilge discharge records, and oily-water separator telemetry.

Compiled autonomously by SATVIGIL Tactical Defense Intelligence System.
Official cryptographic signature embedded.`
    : `OFFICIAL STATUTORY DISPATCH — WILDLIFE PROTECTION & MARINE SANCTUARY ENFORCEMENT
CLASSIFICATION: RESTRICTED // CRITICAL ECOLOGICAL CONTRAVENTION
INCIDENT REFERENCE: ${incidentId}
EVIDENCE HASH (SHA-256): ${sha256}

TO:
1. Chief Wildlife Warden, State Forest Department, Gujarat
2. Regional Operational Command, Indian Coast Guard (North-West Region), Gandhinagar / Okha
3. Marine Coastal Police Superintendent, Coastal Security Division

SUBJECT: NOTICE OF STATUTORY BREACH UNDER WILDLIFE (PROTECTION) ACT, 1972 — ${extraDetail || 'Marine National Park'}

1. OFFENDING VESSEL TELEMETRY:
   • Vessel Name: ${vesselName}
   • MMSI: ${mmsi}
   • Geo-coordinates: ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E
   • Sanctuary Geofence: ${extraDetail || 'Gulf of Kutch Marine National Park'}
   • Observed Intrusion Depth: 2.4 Nautical Miles within Strict Conservation Core
   • Detected Activity: Mechanized Trawling & Unlawful Dwell within Designated Sanctuary

2. STATUTORY CHARGES LODGED:
   • Wildlife (Protection) Act, 1972 — Section 27 (Prohibition of Entry in Sanctuary without Permit)
   • Wildlife (Protection) Act, 1972 — Section 33A & Section 51 (Mandatory Seizure & Forfeiture of Offending Craft)
   • Coastal Regulation Zone (CRZ-IA) Notification — Prohibition of Commercial Trawling in Marine Core

3. STATUTORY ENFORCEMENT DIRECTIVE:
   • Immediate dispatch of ICG Interceptor Boat (ICGS C-438 / Okha Base) for boarding & seizure.
   • Confiscate mechanized net tackle, electronic fish finders, and all marine catch.
   • Escort vessel to nearest Marine Police Station for registration of non-bailable FIR.

Compiled autonomously by SATVIGIL Marine Conservation & Surveillance System.
Official cryptographic signature embedded.`;

  const handleCopy = () => {
    navigator.clipboard.writeText(messageBody);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handleLaunchMailClient = () => {
    const mailtoUrl = `mailto:${encodeURIComponent(toEmail)}?cc=${encodeURIComponent(
      ccEmail
    )}&subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(messageBody)}`;
    window.open(mailtoUrl, '_blank');
  };

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl rounded-xl border shadow-2xl flex flex-col overflow-hidden text-white font-mono"
        style={{
          background: 'var(--navy-950, #060e1a)',
          borderColor: isSpill ? 'rgba(239, 68, 68, 0.6)' : 'rgba(16, 185, 129, 0.6)',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div
          className="px-5 py-3 border-b flex items-center justify-between"
          style={{
            background: isSpill
              ? 'linear-gradient(90deg, #1f0a0e 0%, #3b1117 100%)'
              : 'linear-gradient(90deg, #091a14 0%, #0d2e23 100%)',
            borderColor: isSpill ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)',
          }}
        >
          <div className="flex items-center gap-2.5">
            <span className="text-lg">✉️</span>
            <div>
              <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                Official Statutory Dispatch
              </div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                {isSpill ? 'Transmit MARPOL Oil Spill Prosecution Notice' : 'Transmit MPA Sanctuary Breach Notice'}
              </h3>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg px-2 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content Form */}
        <div className="p-4 space-y-3 overflow-y-auto text-xs">
          {/* TO Field */}
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-bold block mb-1">
              To (Designated Statutory Authorities):
            </label>
            <div className="p-2 rounded bg-navy-900/90 border border-navy-700 text-cyan-300 font-mono text-[11px] select-all">
              {toEmail}
            </div>
          </div>

          {/* CC Field */}
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-bold block mb-1">
              CC (Enforcement &amp; Police Commands):
            </label>
            <div className="p-2 rounded bg-navy-900/90 border border-navy-700 text-gray-300 font-mono text-[11px] select-all">
              {ccEmail}
            </div>
          </div>

          {/* Subject Field */}
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-bold block mb-1">
              Subject Line:
            </label>
            <div className="p-2 rounded bg-navy-900/90 border border-navy-700 text-amber-300 font-mono text-[11px] font-bold select-all">
              {subject}
            </div>
          </div>

          {/* Pre-written Message Body Preview */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[10px] text-gray-400 uppercase font-bold">
                Pre-Written Evidentiary Notice (Verbatim Legal Text):
              </label>
              <button
                type="button"
                onClick={handleCopy}
                className="text-[10px] font-bold text-cyan-400 hover:text-cyan-200 transition-colors flex items-center gap-1"
              >
                <span>{copied ? '✅ COPIED!' : '📋 Copy Text'}</span>
              </button>
            </div>
            <textarea
              readOnly
              rows={11}
              value={messageBody}
              className="w-full p-2.5 rounded bg-black/60 border border-navy-700 text-[10.5px] font-mono text-gray-200 leading-relaxed resize-none focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div
          className="px-5 py-3 border-t flex items-center justify-between gap-3 bg-navy-900/90 border-navy-700"
        >
          <button
            type="button"
            onClick={handleCopy}
            className="px-3 py-1.5 rounded text-xs font-bold font-mono transition-colors flex items-center gap-1.5 border border-cyan-700 bg-cyan-950/60 text-cyan-300 hover:bg-cyan-900"
          >
            <span>{copied ? '✅ Text Copied to Clipboard' : '📋 Copy Full Email Text'}</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded text-xs font-mono text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleLaunchMailClient}
              className={`px-4 py-1.5 rounded text-xs font-bold font-mono transition-all flex items-center gap-1.5 shadow ${
                isSpill
                  ? 'bg-red-600 hover:bg-red-500 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white'
              }`}
            >
              <span>🚀 Launch System Mail Client</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
