import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import { Activity, X, ArrowUpRight, ArrowRight, CheckCircle2, Loader2, Map as MapIcon } from 'lucide-react';

const mockDeformationData = [
  { month: 'Jan', displacement: 0 },
  { month: 'Feb', displacement: 2 },
  { month: 'Mar', displacement: 4 },
  { month: 'Apr', displacement: 7 },
  { month: 'May', displacement: 12 },
  { month: 'Jun', displacement: 17 },
  { month: 'Jul', displacement: 20 },
  { month: 'Aug', displacement: 23 },
  { month: 'Sep', displacement: 26 },
];

export const LandslideConstraintDashboard = ({
  zoneData,
  onClose,
  onAnalyze,
  isAnalyzing,
  analysisResult
}: any) => {
  if (!zoneData) return null;

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 pointer-events-auto flex flex-col p-3 rounded-xl bg-[#091221]/95 border border-cyan-900/60 shadow-[0_0_40px_rgba(0,0,0,0.8)] backdrop-blur-md animate-in slide-in-from-bottom-10 w-[98%] max-w-[1400px] text-white font-sans">
      
      {/* Header */}
      <div className="flex justify-between items-center px-1 pb-2 mb-3 border-b border-cyan-900/40">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm tracking-wider uppercase text-cyan-50">GEOLOGICAL CONSTRAINTS DASHBOARD</span>
          <span className="text-[10px] bg-rose-950/60 text-rose-400 px-2 py-0.5 rounded border border-rose-500/30 uppercase font-mono">
            {zoneData.risk_level} HAZARD
          </span>
          <span className="text-gray-400 text-[10px] font-mono leading-tight">{zoneData.name}</span>
        </div>
        <div className="flex items-center gap-2">
          {onAnalyze && (
            <button
              onClick={onAnalyze}
              disabled={isAnalyzing}
              className="bg-rose-600/90 hover:bg-rose-500 disabled:opacity-50 text-white font-bold py-1 px-4 rounded text-[11px] flex items-center gap-2 transition-colors shadow-[0_0_10px_rgba(225,29,72,0.3)] border border-rose-500"
            >
              {isAnalyzing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}
              {isAnalyzing ? 'RUNNING AI PIPELINE...' : 'RUN TCN + XGBOOST PIPELINE'}
            </button>
          )}
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors bg-white/5 p-1 rounded hover:bg-white/10">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 4 Panels Grid */}
      <div className="grid grid-cols-4 gap-2">
        
        {/* Panel 1: Live SAR Ingestion */}
        <div className="bg-[#0c182b] border border-[#1e3454] rounded-lg p-2.5 flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-gray-200">Live SAR Ingestion (NISAR)</h3>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/50 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Live Feed
            </span>
          </div>
          <div className="flex gap-2">
            <div className="w-20 h-20 bg-black rounded overflow-hidden flex-shrink-0 relative border border-[#1e3454]">
              <img src="/sar_spill_bombay_high.jpg" alt="SAR" className="w-full h-full object-cover grayscale opacity-80 mix-blend-screen" />
            </div>
            <div className="flex-1 flex flex-col justify-between text-[10px] font-mono leading-tight text-gray-400">
              <div>
                <div className="text-emerald-400 font-bold text-sm mb-1">NISAR S-band</div>
                <div className="mb-0.5">Latest Acquisition</div>
                <div className="text-gray-200 mb-2">7 Sep 2026, 14:12 IST</div>
                <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
                  <span>Mode</span><span className="text-gray-200">Stripmap</span>
                  <span>Polarization</span><span className="text-gray-200">VV</span>
                  <span>Orbit</span><span className="text-gray-200">14237 (D)</span>
                  <span>Coverage</span><span className="text-gray-200">Uttarakhand (AOI)</span>
                  <span>Status</span><span className="text-emerald-400 flex items-center gap-1">Downloaded <CheckCircle2 className="w-3 h-3" /></span>
                </div>
              </div>
            </div>
          </div>
          <div className="mt-3">
            <div className="flex justify-between text-[10px] font-mono mb-1 text-cyan-400">
              <span>Processing</span>
              <span>In Progress (32%)</span>
            </div>
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-cyan-500 w-[32%] shadow-[0_0_8px_#06b6d4]"></div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[#1e3454] flex justify-between items-center text-[11px]">
            <span className="text-gray-400 font-mono">Next pass in: 8 hrs 12 min</span>
            <button className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors">
              View SAR Timeline <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Panel 2: Recent Detected Landslide */}
        <div className="bg-[#0c182b] border border-[#1e3454] rounded-lg p-2.5 flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-gray-200">Recent Detected Landslide <span className="text-gray-500 font-normal text-xs">(Auto-detected)</span></h3>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/50">
              New
            </span>
          </div>
          <div className="flex gap-2">
            <div className="w-20 h-20 bg-slate-800 rounded overflow-hidden flex-shrink-0 relative border border-[#1e3454]">
              <img src="/sar_spill_bombay_high.jpg" alt="Map" className="w-full h-full object-cover sepia-[0.3] hue-rotate-60" />
              {/* Synthetic red polygon overlay */}
              <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                <polygon points="20,80 30,50 60,30 80,40 70,70 40,90" fill="rgba(225,29,72,0.4)" stroke="#f43f5e" strokeWidth="1.5" />
              </svg>
            </div>
            <div className="flex-1 flex flex-col text-[10px] font-mono leading-tight text-gray-400">
              <div className="text-white font-bold text-sm mb-0.5">LS-1042</div>
              <div className="text-gray-400 mb-2">{zoneData.state || 'Uttarakhand'}</div>
              <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1.5">
                <span className="text-gray-500">Detected:</span><span className="text-gray-200">7 Sep 2026, 14:18 IST</span>
                <span className="text-gray-500">Confidence</span><span className="text-white">93.4%</span>
                <span className="text-gray-500">Area</span><span className="text-white">{zoneData.area_km2 || '4.8'} ha</span>
                <span className="text-gray-500">Latitude</span><span className="text-white">30.3165° N</span>
                <span className="text-gray-500">Longitude</span><span className="text-white">78.0321° E</span>
              </div>
            </div>
          </div>
          <div className="mt-auto pt-3 border-t border-[#1e3454] flex justify-between items-center text-[11px] mt-4">
            <button className="text-cyan-400 border border-cyan-800/50 hover:bg-cyan-950/30 px-2 py-1 rounded flex items-center gap-1 transition-colors">
              <MapIcon className="w-3 h-3" /> View on Map
            </button>
            <button className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors">
              See All Detections <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Panel 3: Ground Deformation */}
        <div className="bg-[#0c182b] border border-[#1e3454] rounded-lg p-2.5 flex flex-col">
          <div className="flex justify-between items-center mb-1">
            <h3 className="text-sm font-semibold text-gray-200">Ground Deformation (InSAR)</h3>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/50">
              Updated
            </span>
          </div>
          <div className="text-xs text-gray-400 font-mono mb-2">LS-1042 - {zoneData.state || 'Chamoli'}</div>
          
          <div className="h-28 w-full -ml-3 mb-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockDeformationData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e3454" vertical={false} />
                <XAxis dataKey="month" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e3454', fontSize: '11px', borderRadius: '4px' }}
                  itemStyle={{ color: '#f43f5e' }}
                />
                <Line type="monotone" dataKey="displacement" stroke="#f43f5e" strokeWidth={2} dot={{ r: 3, fill: '#f43f5e' }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          <div className="flex gap-2">
            <div className="bg-[#13233a] p-1.5 rounded flex-1 border border-[#1e3454]">
              <div className="text-white font-bold font-mono text-sm">14.2 mm</div>
              <div className="text-[10px] text-gray-400">Current Disp.</div>
            </div>
            <div className="bg-[#13233a] p-1.5 rounded flex-1 border border-[#1e3454]">
              <div className="text-white font-bold font-mono text-sm">8.2 <span className="text-[10px] font-normal">mm/month</span></div>
              <div className="text-[10px] text-gray-400">Velocity</div>
            </div>
            <div className="bg-[#13233a] p-1.5 rounded flex-1 border border-[#1e3454]">
              <div className="text-rose-400 font-bold font-mono text-sm flex items-center gap-1"><ArrowUpRight className="w-3 h-3" /> Increasing</div>
              <div className="text-[10px] text-gray-400">Trend</div>
            </div>
          </div>

          <div className="mt-auto pt-3 border-t border-[#1e3454] flex justify-end items-center text-[11px] mt-4">
            <button className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors">
              View Full Monitoring <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* Panel 4: Risk Prediction */}
        <div className="bg-[#0c182b] border border-[#1e3454] rounded-lg p-2.5 flex flex-col">
          <div className="flex justify-between items-center mb-1">
            <h3 className="text-sm font-semibold text-gray-200">Risk Prediction (AI Model)</h3>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/50">
              Updated
            </span>
          </div>
          <div className="text-xs text-gray-400 font-mono mb-3">LS-1042 - {zoneData.state || 'Chamoli'}</div>
          
          <div className="flex items-center">
            {/* Circular Gauge */}
            <div className="w-24 flex flex-col items-center relative mr-4">
              <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90 drop-shadow-[0_0_10px_rgba(244,63,94,0.3)]">
                <circle cx="50" cy="50" r="40" stroke="#1e3454" strokeWidth="12" fill="none" strokeLinecap="round" />
                <circle cx="50" cy="50" r="40" stroke="#f43f5e" strokeWidth="12" fill="none" strokeDasharray="251.2" strokeDashoffset={251.2 * (1 - 0.87)} strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center pt-1">
                <span className="text-2xl font-bold text-white leading-none">87%</span>
              </div>
              <div className="text-rose-400 font-bold text-xs mt-2 text-center w-full">High Risk</div>
              <div className="text-[9px] text-gray-500 text-center leading-tight mt-0.5">Prob. in 72h</div>
            </div>

            {/* Contributing Factors */}
            <div className="flex-1 flex flex-col gap-2 border-l border-[#1e3454] pl-4">
              <div className="text-[10px] font-semibold text-gray-300 mb-1">Contributing Factors</div>
              
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-gray-400 w-[60px]">Deformation</span>
                <div className="h-2 flex-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-rose-500 w-[84%]"></div>
                </div>
                <span className="text-[10px] font-mono text-gray-300 w-6 text-right">84%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-gray-400 w-[60px]">Rainfall</span>
                <div className="h-2 flex-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-orange-500 w-[72%]"></div>
                </div>
                <span className="text-[10px] font-mono text-gray-300 w-6 text-right">72%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-gray-400 w-[60px]">Slope</span>
                <div className="h-2 flex-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 w-[78%]"></div>
                </div>
                <span className="text-[10px] font-mono text-gray-300 w-6 text-right">78%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-gray-400 w-[60px]">Soil Moisture</span>
                <div className="h-2 flex-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 w-[61%]"></div>
                </div>
                <span className="text-[10px] font-mono text-gray-300 w-6 text-right">61%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-gray-400 w-[60px]">Landcover</span>
                <div className="h-2 flex-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-500 w-[45%]"></div>
                </div>
                <span className="text-[10px] font-mono text-gray-300 w-6 text-right">45%</span>
              </div>
            </div>
          </div>

          <div className="mt-auto pt-3 border-t border-[#1e3454] flex justify-end items-center text-[11px] mt-4">
            <button className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors">
              View Prediction Details <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
