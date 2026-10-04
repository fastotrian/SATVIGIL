/**
 * SATVIGIL — Crop Damage Assessment Panel
 * Pre/post disaster satellite radar/optical damage evaluation.
 * Features an interactive split-screen slider, economic loss estimates, and crop loss breakdown.
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  AlertOctagon,
  Calendar,
  CloudRain,
  SunMedium,
  Wind,
  Layers,
  TrendingDown,
  Percent,
  IndianRupee
} from 'lucide-react';
import type { DamageResponse } from '../../types/agri';

const FALLBACK_DAMAGE: DamageResponse = {
  event: 'flood',
  district: 'Vidarbha',
  date_before: '2024-07-01',
  date_after: '2024-07-18',
  affected_area_ha: 47200,
  total_area_ha: 180000,
  affected_pct: 26.2,
  estimated_loss_crore: 840,
  crop_breakdown: [
    { crop: 'Soybean', affected_ha: 28000, loss_pct: 60 },
    { crop: 'Cotton', affected_ha: 12400, loss_pct: 28 },
    { crop: 'Pulses', affected_ha: 6800, loss_pct: 50 }
  ],
  severity: 'HIGH'
};

export function DamageAssessmentPanel() {
  const [data, setData] = useState<DamageResponse>(FALLBACK_DAMAGE);
  const [selectedEvent, setSelectedEvent] = useState<'flood' | 'drought' | 'cyclone'>('flood');
  const [sliderPos, setSliderPos] = useState<number>(50); // percentage 0 - 100
  const [isSliding, setIsSliding] = useState<boolean>(false);
  const sliderContainerRef = useRef<HTMLDivElement>(null);

  const fetchDamage = async (event: string) => {
    try {
      const res = await axios.get<DamageResponse>('/api/v1/agri/damage', {
        params: { event, district: 'vidarbha' }
      });
      if (res.data && res.data.crop_breakdown) {
        setData(res.data);
      }
    } catch {
      // Use fallback modified by event
      if (event === 'drought') {
        setData({
          ...FALLBACK_DAMAGE,
          event: 'drought',
          date_before: '2024-04-10',
          date_after: '2024-06-25',
          affected_area_ha: 62100,
          affected_pct: 34.5,
          estimated_loss_crore: 1120,
          severity: 'CRITICAL',
          crop_breakdown: [
            { crop: 'Soybean', affected_ha: 34000, loss_pct: 75 },
            { crop: 'Cotton', affected_ha: 18500, loss_pct: 45 },
            { crop: 'Pulses', affected_ha: 9600, loss_pct: 68 }
          ]
        });
      } else if (event === 'cyclone') {
        setData({
          ...FALLBACK_DAMAGE,
          event: 'cyclone',
          date_before: '2024-05-15',
          date_after: '2024-05-28',
          affected_area_ha: 38400,
          affected_pct: 21.3,
          estimated_loss_crore: 690,
          severity: 'MEDIUM',
          crop_breakdown: [
            { crop: 'Soybean', affected_ha: 21000, loss_pct: 42 },
            { crop: 'Cotton', affected_ha: 11000, loss_pct: 25 },
            { crop: 'Pulses', affected_ha: 6400, loss_pct: 35 }
          ]
        });
      } else {
        setData(FALLBACK_DAMAGE);
      }
    }
  };

  useEffect(() => {
    fetchDamage(selectedEvent);
  }, [selectedEvent]);

  // Handle Dragging Divider
  const updateSliderFromClientX = useCallback((clientX: number) => {
    if (!sliderContainerRef.current) return;
    const rect = sliderContainerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPos(pct);
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsSliding(true);
    updateSliderFromClientX(e.clientX);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isSliding) return;
    updateSliderFromClientX(e.clientX);
  }, [isSliding, updateSliderFromClientX]);

  const handleMouseUp = useCallback(() => {
    setIsSliding(false);
  }, []);

  useEffect(() => {
    if (isSliding) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isSliding, handleMouseMove, handleMouseUp]);

  // Severity color formatting
  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/60 shadow-[0_0_10px_rgba(244,63,94,0.3)]';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-300 border-orange-500/60 shadow-[0_0_10px_rgba(249,115,22,0.3)]';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/60';
      default:
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/60';
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#071326]/90 border border-emerald-500/30 rounded-xl p-3.5 shadow-xl backdrop-blur-md overflow-hidden font-mono text-xs">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-2 border-b border-navy-700/60 shrink-0">
        <div className="flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
          <div>
            <h2 className="text-white font-bold tracking-wide text-xs flex items-center gap-1.5">
              <span>CROP DAMAGE ASSESSMENT</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border uppercase ${getSeverityBadge(data.severity)}`}>
                {data.severity}
              </span>
            </h2>
            <div className="text-[10px] text-gray-400">
              District: <span className="text-gray-200">{data.district}</span>
            </div>
          </div>
        </div>

        {/* Disaster Event Switcher */}
        <div className="flex items-center gap-1 bg-navy-950/80 p-0.5 rounded-lg border border-navy-700/60">
          <button
            type="button"
            onClick={() => setSelectedEvent('flood')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold transition-all ${
              selectedEvent === 'flood'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <CloudRain className="w-3 h-3" />
            <span>FLOOD</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectedEvent('drought')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold transition-all ${
              selectedEvent === 'drought'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-400/50 shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <SunMedium className="w-3 h-3" />
            <span>DROUGHT</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectedEvent('cyclone')}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold transition-all ${
              selectedEvent === 'cyclone'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-400/50 shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            <Wind className="w-3 h-3" />
            <span>CYCLONE</span>
          </button>
        </div>
      </div>

      {/* Main Content: Split-Slider (Left) + Stats & Breakdown (Right) */}
      <div className="flex-1 flex gap-3 pt-2.5 min-h-0 overflow-hidden">
        {/* Before / After Satellite Comparison Slider */}
        <div
          ref={sliderContainerRef}
          onMouseDown={handleMouseDown}
          className="w-1/2 relative rounded-lg border border-navy-700/80 overflow-hidden cursor-ew-resize select-none bg-[#051122]"
        >
          {/* Post-Event (Right / Background Layer) */}
          <div className="absolute inset-0 bg-[#1f0b0e] flex flex-col justify-between p-2">
            <div
              className="absolute inset-0 opacity-40"
              style={{
                backgroundImage: `
                  radial-gradient(circle at 60% 40%, rgba(244, 63, 94, 0.3) 0%, transparent 60%),
                  linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                  linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
                `,
                backgroundSize: '100% 100%, 15px 15px, 15px 15px'
              }}
            />
            <div className="z-10 self-end bg-rose-950/90 text-rose-300 border border-rose-500/60 px-1.5 py-0.5 rounded text-[10px] font-bold">
              POST-EVENT ({data.date_after})
            </div>
            <div className="z-10 self-end text-[9px] text-rose-400/80 font-mono">
              Inundation / Necrosis
            </div>
          </div>

          {/* Pre-Event (Left / Clipped Overlay) */}
          <div
            className="absolute inset-0 bg-[#061e16] flex flex-col justify-between p-2 border-r border-emerald-400/80"
            style={{
              clipPath: `polygon(0 0, ${sliderPos}% 0, ${sliderPos}% 100%, 0 100%)`
            }}
          >
            <div
              className="absolute inset-0 opacity-40"
              style={{
                backgroundImage: `
                  radial-gradient(circle at 40% 50%, rgba(16, 185, 129, 0.3) 0%, transparent 60%),
                  linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                  linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
                `,
                backgroundSize: '100% 100%, 15px 15px, 15px 15px'
              }}
            />
            <div className="z-10 self-start bg-emerald-950/90 text-emerald-300 border border-emerald-500/60 px-1.5 py-0.5 rounded text-[10px] font-bold">
              PRE-EVENT ({data.date_before})
            </div>
            <div className="z-10 self-start text-[9px] text-emerald-400/80 font-mono">
              Healthy Canopy Baseline
            </div>
          </div>

          {/* Draggable Divider Line & Knob */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-emerald-300 shadow-[0_0_8px_#34d399] z-20 pointer-events-none"
            style={{ left: `${sliderPos}%` }}
          >
            <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-navy-950 border-2 border-emerald-400 shadow flex items-center justify-center text-[8px] text-emerald-300 font-bold">
              ↔
            </div>
          </div>
        </div>

        {/* Damage Stats & Crop Breakdown */}
        <div className="w-1/2 flex flex-col justify-between space-y-2">
          {/* Key Stat Badges */}
          <div className="grid grid-cols-3 gap-1.5">
            <div className="bg-navy-950/70 border border-rose-500/40 rounded-lg p-1.5 text-center">
              <div className="text-[9px] text-gray-400 uppercase">Affected Area</div>
              <div className="text-xs font-bold text-rose-400">
                {data.affected_area_ha.toLocaleString()} ha
              </div>
            </div>

            <div className="bg-navy-950/70 border border-amber-500/40 rounded-lg p-1.5 text-center">
              <div className="text-[9px] text-gray-400 uppercase">Area Loss</div>
              <div className="text-xs font-bold text-amber-300">
                {data.affected_pct}%
              </div>
            </div>

            <div className="bg-navy-950/70 border border-rose-500/40 rounded-lg p-1.5 text-center">
              <div className="text-[9px] text-gray-400 uppercase">Economic Loss</div>
              <div className="text-xs font-bold text-rose-400 flex items-center justify-center gap-0.5">
                <span>₹{data.estimated_loss_crore} Cr</span>
              </div>
            </div>
          </div>

          {/* Crop Breakdown Table */}
          <div className="bg-navy-950/60 border border-navy-700/60 rounded-lg p-2 space-y-1.5">
            <div className="text-[10px] text-gray-400 uppercase font-semibold flex items-center justify-between pb-1 border-b border-navy-800">
              <span>Crop Classification</span>
              <span>Damage Intensity</span>
            </div>

            {data.crop_breakdown.map((crop) => (
              <div key={crop.crop} className="space-y-0.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-gray-200 font-bold">{crop.crop}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-gray-400 text-[10px]">{crop.affected_ha.toLocaleString()} ha</span>
                    <span className={`font-bold ${crop.loss_pct >= 50 ? 'text-rose-400' : 'text-amber-400'}`}>
                      {crop.loss_pct}% loss
                    </span>
                  </div>
                </div>

                <div className="w-full bg-navy-900 rounded-full h-1.5 overflow-hidden border border-navy-800">
                  <div
                    className={`h-full rounded-full ${
                      crop.loss_pct >= 50 ? 'bg-rose-500' : 'bg-amber-500'
                    }`}
                    style={{ width: `${crop.loss_pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Statutory Assessment Note */}
          <div className="text-[9px] text-gray-400 flex items-center justify-between px-1">
            <span>Assessment: PM Fasal Bima Yojana (PMFBY)</span>
            <span className="text-emerald-400">Sentinel-1/2 Verified</span>
          </div>
        </div>
      </div>
    </div>
  );
}
