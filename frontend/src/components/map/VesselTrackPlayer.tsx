/**
 * SATVIGIL — Vessel Track Player
 *
 * Animated AIS route playback using GFW track data.
 * Features:
 *   - Fetches track from /api/v1/maritime/vessels/{vessel_id}/track
 *   - Shows full route as dashed line on map
 *   - Animates vessel position frame-by-frame through observations
 *   - Highlights AIS dark gap segment in red dashed line
 *   - Play / Pause / Reset controls with speed selector
 *   - Dark gap warning banner when vessel goes silent
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Source, Layer, Marker } from 'react-map-gl/maplibre';
import type { LineLayer } from 'react-map-gl/maplibre';
import type { VesselTrack, TrackPoint } from '../../types/maritime';

const API_BASE = 'http://localhost:8000/api/v1';

// ─────────────────────────────────────────────────────────
// Demo vessel IDs that have track data available
// ─────────────────────────────────────────────────────────
export const DEMO_TRACK_VESSEL_ID = 'gfw-v-419001-kutch-tanker';
export const DEMO_TRACK_MMSI = '419001845';

interface Props {
  /** MMSI or vessel_id to load track for */
  vesselId: string;
  /** Called when a track point is active (frame) */
  onFrameChange?: (point: TrackPoint, index: number, total: number) => void;
  /** Called when track fully loaded */
  onTrackLoaded?: (track: VesselTrack) => void;
}

export function VesselTrackPlayer({ vesselId, onFrameChange, onTrackLoaded }: Props) {
  const [track, setTrack] = useState<VesselTrack | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const [speed, setSpeed] = useState(3); // frames per second
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Fetch track data ─────────────────────────────────────
  useEffect(() => {
    if (!vesselId) return;
    setIsLoading(true);
    setError(null);
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
      .catch((e) => setError(e.message))
      .finally(() => setIsLoading(false));
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

  // ── Current animated position ────────────────────────────
  const currentPoint = track?.track_points[frameIndex];
  const isDarkGap = (currentPoint?.ais_gap_minutes ?? 0) > 30;

  // ── Build route geometry up to current frame ─────────────
  const trailCoords = track
    ? track.track_points.slice(0, frameIndex + 1).map((p) => [p.lon, p.lat])
    : [];

  // ── Detect dark gap segment in full track ────────────────
  const darkGapCoords: number[][] = [];
  if (track?.dark_gap_event) {
    const gap = track.dark_gap_event;
    darkGapCoords.push([gap.lon, gap.lat], [gap.reappear_lon, gap.reappear_lat]);
  }

  // ── GeoJSON for trail layer ──────────────────────────────
  const trailGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features:
      trailCoords.length >= 2
        ? [
            {
              type: 'Feature',
              geometry: { type: 'LineString', coordinates: trailCoords },
              properties: {},
            },
          ]
        : [],
  };

  // ── GeoJSON for AIS dark gap segment ────────────────────
  const darkGapGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features:
      darkGapCoords.length >= 2
        ? [
            {
              type: 'Feature',
              geometry: { type: 'LineString', coordinates: darkGapCoords },
              properties: {},
            },
          ]
        : [],
  };

  const trailLayer: LineLayer = {
    id: 'vessel-trail',
    type: 'line',
    source: 'vessel-trail',
    paint: {
      'line-color': '#38BDF8',   // sky-blue trail
      'line-width': 2,
      'line-opacity': 0.8,
      'line-dasharray': [2, 1],
    },
  };

  const darkGapLayer: LineLayer = {
    id: 'vessel-dark-gap',
    type: 'line',
    source: 'vessel-dark-gap',
    paint: {
      'line-color': '#EF4444',   // red — AIS signal lost
      'line-width': 3,
      'line-opacity': 0.9,
      'line-dasharray': [3, 2],
    },
  };

  if (isLoading) return null;
  if (error || !track) return null;

  return (
    <>
      {/* ── Map Layers ── */}
      <Source id="vessel-trail" type="geojson" data={trailGeoJSON}>
        <Layer {...trailLayer} />
      </Source>

      {darkGapCoords.length >= 2 && (
        <Source id="vessel-dark-gap" type="geojson" data={darkGapGeoJSON}>
          <Layer {...darkGapLayer} />
        </Source>
      )}

      {/* ── Animated vessel dot ── */}
      {currentPoint && (
        <Marker longitude={currentPoint.lon} latitude={currentPoint.lat} anchor="center">
          <div className="relative flex items-center justify-center">
            {isDarkGap && (
              <div className="absolute w-10 h-10 rounded-full border-2 border-red-500 bg-red-500/20 animate-ping opacity-75" />
            )}
            <div
              className={`w-5 h-5 rounded-full border-2 shadow-lg ${
                isDarkGap
                  ? 'bg-red-600 border-red-300'
                  : 'bg-sky-400 border-white'
              }`}
              title={isDarkGap ? '⚠️ AIS Dark Gap — Vessel Signal Lost' : `Position at ${currentPoint.date}`}
            />
          </div>
        </Marker>
      )}

      {/* ── Dark gap warning banner (rendered outside Map, handled by parent) ── */}
    </>
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// Track Playback Controls Panel (rendered in UI, outside the Map)
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
  track, isPlaying, frameIndex, speed,
  onPlay, onPause, onReset, onSpeedChange, onSeek, onClose,
}: ControlsProps) {
  if (!track) return null;

  const total = track.track_points.length;
  const current = track.track_points[frameIndex];
  const isDarkGap = (current?.ais_gap_minutes ?? 0) > 30;
  const progress = total > 1 ? (frameIndex / (total - 1)) * 100 : 0;

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
            max={total - 1}
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
            🔴 Dark gap recorded: <span className="text-red-400 font-medium">{track.dark_gap_event.duration_minutes}min</span> at {track.dark_gap_event.lat.toFixed(3)}°N, {track.dark_gap_event.lon.toFixed(3)}°E
          </div>
        )}
      </div>
    </div>
  );
}
