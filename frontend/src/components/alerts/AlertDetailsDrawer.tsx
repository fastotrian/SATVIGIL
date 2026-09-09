import React from 'react';
import { useAlertStore } from '../../store/alertStore';
import { RISK_COLORS } from '../../constants/riskColors';

export function AlertDetailsDrawer() {
  const { selectedVessel, selectVessel } = useAlertStore();

  if (!selectedVessel) return null;

  return (
    <div className="fixed top-0 right-0 h-full w-80 bg-gray-900 border-l border-gray-800 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 translate-x-0">
      <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-gray-950">
        <h2 className="text-white font-bold tracking-wider">Vessel Profile</h2>
        <button
          type="button"
          onClick={() => selectVessel(null)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Header Block */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xl font-black text-white">{selectedVessel.vessel_name || 'UNKNOWN'}</span>
          </div>
          <div className="text-sm text-gray-400 font-mono">MMSI: {selectedVessel.mmsi}</div>
        </div>

        {/* Status Pills */}
        <div className="grid grid-cols-2 gap-2">
          <div className={`p-2 rounded flex flex-col ${selectedVessel.risk_level === 'CRITICAL' ? 'bg-red-950/30 border border-red-900/50' : 'bg-gray-800/50'}`}>
            <span className="text-[10px] text-gray-400 uppercase tracking-wide">Risk Level</span>
            <span
              className="font-bold text-sm"
              style={{
                color:
                  selectedVessel.risk_level === 'CRITICAL'
                    ? RISK_COLORS.CRITICAL
                    : selectedVessel.risk_level === 'WARNING'
                    ? RISK_COLORS.HIGH
                    : RISK_COLORS.NORMAL,
              }}
            >
              {selectedVessel.risk_level}
            </span>
          </div>
          <div className="p-2 rounded bg-gray-800/50 flex flex-col border border-gray-700/50">
            <span className="text-[10px] text-gray-400 uppercase tracking-wide">Speed / Course</span>
            <span className="font-bold text-sm text-white">{selectedVessel.speed_knots} kts / {selectedVessel.course_deg}°</span>
          </div>
        </div>

        {/* Risk Breakdown */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800 pb-1">Risk Factors (4-Signal)</h3>
          
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">AIS Dark Gap</span>
              <span className="text-white font-mono">{selectedVessel.ais_gap_minutes} min</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5">
              <div
                className="bg-red-500 h-1.5 rounded-full"
                style={{ width: `${Math.min((selectedVessel.ais_gap_minutes / 60) * 100, 100)}%` }}
              ></div>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-300">Vessel Type Risk</span>
              <span className="text-white font-mono">{selectedVessel.vessel_type_label}</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5">
              <div
                className="bg-orange-500 h-1.5 rounded-full"
                style={{ width: '75%' }}
              ></div>
            </div>
          </div>
        </div>

        {/* Telemetry (Placeholder for Task UI06) */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-gray-800 pb-1">24h Telemetry</h3>
          <div className="h-32 bg-gray-800/50 rounded flex items-center justify-center border border-gray-700/50">
            <span className="text-xs text-gray-500 font-mono">Chart Data Loading...</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-4 border-t border-gray-800 bg-gray-950 space-y-2">
        <button
          type="button"
          className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded transition-colors flex justify-center items-center space-x-2"
        >
          <span>Acknowledge Alert</span>
        </button>
        <a
          href={`mailto:coastguard@gov.in?subject=Alert: ${selectedVessel.vessel_name}`}
          className="w-full bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 font-bold py-2 px-4 rounded transition-colors flex justify-center items-center space-x-2"
        >
          <span>Dispatch Notice</span>
        </a>
      </div>
    </div>
  );
}
