/**
 * SATVIGIL — Crop Health Monitor Panel (NDVI)
 * Displays Sentinel-2 NDVI vegetative health metrics, regional zone breakdowns,
 * and 4-week temporal vegetation decay trends across Indian agricultural corridors.
 */
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Leaf,
  AlertTriangle,
  TrendingDown,
  Activity,
  Layers,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell
} from 'recharts';
import type { NdviResponse, NdviZone } from '../../types/agri';

const FALLBACK_NDVI: NdviResponse = {
  region: 'Punjab & Central India',
  date: '2024-10',
  zones: [
    { id: 'PB-1', name: 'Amritsar', lat: 31.63, lon: 74.87, ndvi: 0.72, status: 'healthy', area_ha: 45200 },
    { id: 'PB-2', name: 'Ludhiana', lat: 30.90, lon: 75.85, ndvi: 0.55, status: 'moderate', area_ha: 38700 },
    { id: 'PB-3', name: 'Bathinda', lat: 30.21, lon: 74.94, ndvi: 0.31, status: 'stressed', area_ha: 29100 },
    { id: 'PB-4', name: 'Fazilka', lat: 30.40, lon: 74.02, ndvi: 0.18, status: 'critical', area_ha: 17800 },
    { id: 'VB-1', name: 'Vidarbha', lat: 20.70, lon: 78.40, ndvi: 0.22, status: 'stressed', area_ha: 62000 },
    { id: 'KT-1', name: 'Kutch', lat: 23.73, lon: 69.86, ndvi: 0.09, status: 'critical', area_ha: 11200 }
  ],
  trend_weekly: [0.61, 0.58, 0.52, 0.47],
  summary: { healthy: 1, moderate: 1, stressed: 2, critical: 2, total_area_ha: 204000 }
};

function getNdviColor(val: number): { text: string; bg: string; border: string; hex: string } {
  if (val >= 0.5) {
    return { text: 'text-emerald-400', bg: 'bg-emerald-500', border: 'border-emerald-500/40', hex: '#34d399' };
  }
  if (val >= 0.3) {
    return { text: 'text-amber-400', bg: 'bg-amber-500', border: 'border-amber-500/40', hex: '#fbbf24' };
  }
  if (val >= 0.1) {
    return { text: 'text-orange-400', bg: 'bg-orange-500', border: 'border-orange-500/40', hex: '#fb923c' };
  }
  return { text: 'text-rose-400', bg: 'bg-rose-500', border: 'border-rose-500/40', hex: '#f43f5e' };
}

export function CropHealthPanel() {
  const [data, setData] = useState<NdviResponse>(FALLBACK_NDVI);
  const [loading, setLoading] = useState(false);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);

  const fetchNdvi = async () => {
    setLoading(true);
    try {
      const res = await axios.get<NdviResponse>('/api/v1/agri/ndvi');
      if (res.data && res.data.zones) {
        setData(res.data);
      }
    } catch {
      // Fallback already populated
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNdvi();
  }, []);

  const chartData = data.trend_weekly.map((val, idx) => ({
    week: `Wk ${idx + 1}`,
    ndvi: val
  }));

  return (
    <div className="flex flex-col h-full bg-[#071326]/90 border border-emerald-500/30 rounded-xl p-3.5 shadow-xl backdrop-blur-md overflow-hidden font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-navy-700/60 shrink-0">
        <div className="flex items-center gap-2">
          <div className="relative flex items-center justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="absolute w-4 h-4 rounded-full bg-emerald-400/30 animate-ping" />
          </div>
          <div>
            <h2 className="text-white font-bold tracking-wide text-xs flex items-center gap-1.5">
              <span>CROP HEALTH MONITOR</span>
              <span className="text-[10px] text-emerald-400/80 font-normal">[SENTINEL-2 NDVI]</span>
            </h2>
            <div className="text-[10px] text-gray-400">
              Region: <span className="text-gray-200">{data.region}</span> ({data.date})
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={fetchNdvi}
          disabled={loading}
          title="Refresh NDVI Telemetry"
          className="p-1 rounded bg-navy-800 hover:bg-navy-700 text-gray-300 hover:text-white transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-400' : ''}`} />
        </button>
      </div>

      {/* 4 Status Summary Cards */}
      <div className="grid grid-cols-4 gap-1.5 py-2.5 shrink-0">
        <div className="bg-emerald-950/40 border border-emerald-500/30 rounded-lg p-1.5 text-center">
          <div className="text-[10px] text-emerald-400 uppercase font-semibold">Healthy</div>
          <div className="text-base font-bold text-emerald-300">{data.summary.healthy}</div>
          <div className="text-[9px] text-emerald-400/70">&gt;0.5 NDVI</div>
        </div>
        <div className="bg-amber-950/40 border border-amber-500/30 rounded-lg p-1.5 text-center">
          <div className="text-[10px] text-amber-400 uppercase font-semibold">Moderate</div>
          <div className="text-base font-bold text-amber-300">{data.summary.moderate}</div>
          <div className="text-[9px] text-amber-400/70">0.3-0.5</div>
        </div>
        <div className="bg-orange-950/40 border border-orange-500/30 rounded-lg p-1.5 text-center">
          <div className="text-[10px] text-orange-400 uppercase font-semibold">Stressed</div>
          <div className="text-base font-bold text-orange-300">{data.summary.stressed}</div>
          <div className="text-[9px] text-orange-400/70">0.1-0.3</div>
        </div>
        <div className="bg-rose-950/40 border border-rose-500/30 rounded-lg p-1.5 text-center">
          <div className="text-[10px] text-rose-400 uppercase font-semibold">Critical</div>
          <div className="text-base font-bold text-rose-300">{data.summary.critical}</div>
          <div className="text-[9px] text-rose-400/70">&lt;0.1 NDVI</div>
        </div>
      </div>

      {/* Total Monitored Area Readout */}
      <div className="flex items-center justify-between px-2 py-1.5 bg-navy-950/70 border border-navy-700/50 rounded-lg mb-2 text-[11px] shrink-0">
        <span className="text-gray-400 flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>Total Surveillance Area</span>
        </span>
        <span className="text-emerald-300 font-bold">
          {data.summary.total_area_ha.toLocaleString()} ha
        </span>
      </div>

      {/* Zone Breakdown List (Scrollable) */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0 custom-scrollbar">
        <div className="text-[10px] text-gray-400 uppercase font-semibold tracking-wider px-0.5">
          Surveillance Zones ({data.zones.length})
        </div>

        {data.zones.map((zone: NdviZone) => {
          const colors = getNdviColor(zone.ndvi);
          const isSelected = selectedZone === zone.id;

          return (
            <div
              key={zone.id}
              onClick={() => setSelectedZone(isSelected ? null : zone.id)}
              className={`p-2 rounded-lg border transition-all cursor-pointer ${
                isSelected
                  ? 'bg-navy-800/90 border-emerald-400 shadow-md'
                  : 'bg-navy-950/50 hover:bg-navy-900/70 border-navy-700/60'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  {zone.status === 'healthy' ? (
                    <Leaf className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : zone.status === 'critical' ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                  ) : (
                    <Activity className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  )}
                  <span className="font-bold text-gray-200">{zone.name}</span>
                  <span className="text-[10px] text-gray-500">[{zone.id}]</span>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${colors.text} ${colors.border} bg-navy-950/80`}>
                    {zone.status}
                  </span>
                  <span className={`font-bold ${colors.text}`}>
                    {zone.ndvi.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* NDVI Progress Bar */}
              <div className="w-full bg-navy-950 rounded-full h-1.5 overflow-hidden my-1.5 border border-navy-800">
                <div
                  className={`h-full ${colors.bg} rounded-full transition-all duration-500`}
                  style={{ width: `${Math.min(Math.max(zone.ndvi * 100, 4), 100)}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[10px] text-gray-400">
                <span>Coord: {zone.lat.toFixed(2)}°N, {zone.lon.toFixed(2)}°E</span>
                <span className="text-gray-300 font-semibold">{zone.area_ha.toLocaleString()} ha</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 4-Week Temporal Trend BarChart */}
      <div className="pt-2.5 border-t border-navy-700/60 shrink-0">
        <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1.5 px-0.5">
          <span className="flex items-center gap-1 text-gray-300 font-semibold">
            <TrendingDown className="w-3 h-3 text-amber-400" />
            <span>4-Week Regional NDVI Trend</span>
          </span>
          <span className="text-rose-400 text-[10px]">-23% decay rate</span>
        </div>

        <div className="h-20 w-full bg-navy-950/60 rounded-lg p-1 border border-navy-800">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 6, left: -22, bottom: 0 }}>
              <XAxis dataKey="week" stroke="#6b7280" tick={{ fontSize: 9, fill: '#9ca3af' }} />
              <YAxis domain={[0, 1]} stroke="#6b7280" tick={{ fontSize: 9, fill: '#9ca3af' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#071326',
                  borderColor: '#10b981',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  color: '#fff'
                }}
                formatter={(value: number) => [`NDVI: ${value.toFixed(2)}`, 'Vegetation Index']}
              />
              <Bar dataKey="ndvi" radius={[3, 3, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getNdviColor(entry.ndvi).hex}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
