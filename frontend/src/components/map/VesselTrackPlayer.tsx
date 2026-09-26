/**
 * SATVIGIL — Vessel Track Player (CesiumJS 3D WebGL)
 *
 * Animated AIS route playback using GFW track data on 3D globe.
 * Features:
 *   - Fetches track from /api/v1/maritime/vessels/{vessel_id}/track
 *   - Renders route as 3D Polyline on Cesium Globe
 *   - Highlights AIS dark gap segment in red dashed line
 *   - Animates vessel position frame-by-frame with heading/ping
 *   - Play / Pause / Reset controls with speed selector
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Viewer,
  Entity,
  Cartesian3,
  Color,
  PolylineDashMaterialProperty,
  CallbackProperty,
  NearFarScalar,
} from 'cesium';
import type { VesselTrack, TrackPoint } from '../../types/maritime';

const API_BASE = 'http://localhost:8000/api/v1';

export const DEMO_TRACK_VESSEL_ID = 'gfw-v-419001-kutch-tanker';
export const DEMO_TRACK_MMSI = '419001845';

interface Props {
  /** MMSI or vessel_id to load track for */
  vesselId: string;
  /** Cesium viewer reference */
  viewer: Viewer | null;
  /** Called when a track point is active (frame) */
  onFrameChange?: (point: TrackPoint, index: number, total: number) => void;
  /** Called when track fully loaded */
  onTrackLoaded?: (track: VesselTrack) => void;
}

export function VesselTrackPlayer({ vesselId, viewer, onFrameChange, onTrackLoaded }: Props) {
  const [track, setTrack] = useState<VesselTrack | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const [speed, setSpeed] = useState(3); // frames per second
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Keep ref to frameIndex for animation callback
  const frameIndexRef = useRef(frameIndex);
  frameIndexRef.current = frameIndex;

  const trackRef = useRef<VesselTrack | null>(null);
  trackRef.current = track;

  // ── Fetch track data ─────────────────────────────────────
  useEffect(() => {
    if (!vesselId) return;
    setIsPlaying(false);
    setFrameIndex(0);

    fetch(`${API_BASE}/maritime/vessels/${encodeURIComponent(vesselId)}/track`)
      .then((r) => {
        if (!r.ok) throw new Error(`Track not found (${r.status})`);
        return r.json();
      })
      .then((data: VesselTrack) => {
        setTrack(data);
        onTrackLoaded?.(data);
      })
      .catch((e) => console.error('Track fetch error:', e));
  }, [vesselId]);

  // ── Animation loop ───────────────────────────────────────
  const stopPlayback = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  useEffect(() => {
    if (!isPlaying || !track) return;

    intervalRef.current = setInterval(() => {
      setFrameIndex((prev) => {
        const next = prev + 1;
        if (next >= track.track_points.length) {
          stopPlayback();
          return prev;
        }
        const point = track.track_points[next];
        onFrameChange?.(point, next, track.track_points.length);
        return next;
      });
    }, 1000 / speed);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, speed, track, stopPlayback, onFrameChange]);

  // ── Cesium Entities Management ───────────────────────────
  useEffect(() => {
    if (!viewer || !track) return;

    const entities: Entity[] = [];

    // 1. Trail Polyline up to current frame
    const trailEntity = viewer.entities.add({
      name: `track-trail-${vesselId}`,
      polyline: {
        positions: new CallbackProperty(() => {
          const t = trackRef.current;
          if (!t || t.track_points.length === 0) return [];
          const endIdx = Math.min(frameIndexRef.current + 1, t.track_points.length);
          const points = t.track_points.slice(0, Math.max(endIdx, 2));
          return points.map((p) => Cartesian3.fromDegrees(p.lon, p.lat, 20));
        }, false),
        width: 2.5,
        material: Color.fromCssColorString('#38BDF8'),
        clampToGround: false,
      },
    });
    entities.push(trailEntity);

    // 2. Dark Gap Polyline if event exists
    if (track.dark_gap_event) {
      const gap = track.dark_gap_event;
      const darkGapEntity = viewer.entities.add({
        name: `track-dark-gap-${vesselId}`,
        polyline: {
          positions: [
            Cartesian3.fromDegrees(gap.lon, gap.lat, 25),
            Cartesian3.fromDegrees(gap.reappear_lon, gap.reappear_lat, 25),
          ],
          width: 3.5,
          material: new PolylineDashMaterialProperty({
            color: Color.fromCssColorString('#EF4444'),
            dashLength: 16.0,
          }),
        },
      });
      entities.push(darkGapEntity);
    }

    // 3. Animated Vessel Dot Marker
    const vesselMarkerEntity = viewer.entities.add({
      name: `track-marker-${vesselId}`,
      position: new CallbackProperty(() => {
        const t = trackRef.current;
        if (!t || t.track_points.length === 0) return Cartesian3.ZERO;
        const pt = t.track_points[frameIndexRef.current] || t.track_points[0];
        return Cartesian3.fromDegrees(pt.lon, pt.lat, 40);
      }, false) as any,
      point: {
        pixelSize: 12,
        color: new CallbackProperty(() => {
          const t = trackRef.current;
          const pt = t?.track_points[frameIndexRef.current];
          const isDark = (pt?.ais_gap_minutes ?? 0) > 30;
          return isDark ? Color.fromCssColorString('#EF4444') : Color.fromCssColorString('#00E5FF');
        }, false) as any,
        outlineColor: Color.fromCssColorString('#060E1C'),
        outlineWidth: 2,
        scaleByDistance: new NearFarScalar(1.5e2, 1.5, 8.0e6, 0.7),
      },
    });
    entities.push(vesselMarkerEntity);

    return () => {
      // Clean up track entities when unmounted
      for (const e of entities) {
        viewer.entities.remove(e);
      }
    };
  }, [viewer, track, vesselId]);

  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Track Playback Controls Panel (rendered in UI, outside the 3D canvas)
// ─────────────────────────────────────────────────────────────────────────────

interface ControlsProps {
  track: VesselTrack | null;
  isPlaying: boolean;
  frameIndex: number;
  speed: number;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
  onSpeedChange: (s: number) => void;
  onSeek: (i: number) => void;
  onClose?: () => void;
}

export function TrackPlaybackControls({
  track,
  isPlaying,
  frameIndex,
  speed,
  onPlay,
  onPause,
  onReset,
  onSpeedChange,
  onSeek,
  onClose,
}: ControlsProps) {
  if (!track) return null;

  const total = track.track_points.length;
  const current = track.track_points[frameIndex];
  const isDarkGap = (current?.ais_gap_minutes ?? 0) > 30;

  return (
    <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-30 w-[480px]">
      <div className="bg-gray-900/95 backdrop-blur-md border border-gray-700 rounded-2xl p-4 shadow-2xl">
        {/* Vessel info header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isDarkGap ? 'bg-red-500 animate-pulse' : 'bg-sky-400'}`} />
            <span className="text-white font-semibold text-sm">{track.ship_name}</span>
            <span className="text-gray-400 text-xs font-mono">MMSI: {track.mmsi}</span>
            <span className="text-gray-500 text-xs">🏳️ {track.flag}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-xs font-mono">
              {frameIndex + 1}/{total} obs
            </span>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="w-5 h-5 flex items-center justify-center rounded text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                title="Close track player"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Dark gap alert */}
        {isDarkGap && (
          <div className="mb-3 flex items-center gap-2 bg-red-900/50 border border-red-700 rounded-lg px-3 py-2">
            <span className="text-red-400 animate-pulse">⚠️</span>
            <span className="text-red-300 text-xs font-medium">
              AIS DARK GAP — {current?.ais_gap_minutes}min signal loss detected at this position
            </span>
          </div>
        )}

        {/* Timeline scrubber */}
        <div className="mb-3">
          <input
            id="track-scrubber"
            type="range"
            min={0}
            max={Math.max(total - 1, 0)}
            value={frameIndex}
            onChange={(e) => onSeek(Number(e.target.value))}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-gray-700 accent-sky-400"
          />
          <div className="flex justify-between text-gray-500 text-xs mt-1">
            <span>{track.track_points[0]?.date?.slice(0, 10)}</span>
            <span>{current?.date?.slice(0, 16).replace('T', ' ')} UTC</span>
            <span>{track.track_points[total - 1]?.date?.slice(0, 10)}</span>
          </div>
        </div>

        {/* Playback controls */}
        <div className="flex items-center gap-3">
          <button
            id="track-reset-btn"
            onClick={onReset}
            className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
            title="Reset to start"
          >
            ⏮
          </button>

          <button
            id="track-play-pause-btn"
            onClick={isPlaying ? onPause : onPlay}
            className={`flex-1 py-2 rounded-lg font-medium text-sm transition-colors ${
              isPlaying
                ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                : 'bg-sky-600 hover:bg-sky-500 text-white'
            }`}
          >
            {isPlaying ? '⏸ Pause' : '▶ Play AIS Track'}
          </button>

          {/* Speed selector */}
          <select
            id="track-speed-select"
            value={speed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="bg-gray-700 text-gray-200 text-xs rounded-lg px-2 py-2 border-0 outline-none"
          >
            <option value={1}>1×</option>
            <option value={3}>3×</option>
            <option value={6}>6×</option>
            <option value={12}>12×</option>
          </select>
        </div>

        {/* Dark gap event summary */}
        {track.dark_gap_event && (
          <div className="mt-3 border-t border-gray-700 pt-2 text-xs text-gray-400">
            🔴 Dark gap recorded:{' '}
            <span className="text-red-400 font-medium">
              {track.dark_gap_event.duration_minutes}min
            </span>{' '}
            at {track.dark_gap_event.lat.toFixed(3)}°N, {track.dark_gap_event.lon.toFixed(3)}°E
          </div>
        )}
      </div>
    </div>
  );
}
