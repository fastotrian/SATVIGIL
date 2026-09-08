/**
 * SATVIGIL Risk Color System
 * Single source of truth for all color values used in map, markers, and alerts.
 * DO NOT hardcode these values anywhere else in the codebase.
 */

export const RISK_COLORS = {
  // Vessel marker colors (by risk score range)
  CRITICAL: '#EF4444',    // risk >= 0.75  → red blinking
  HIGH:     '#F97316',    // risk 0.55–0.74 → orange slow pulse
  CAUTION:  '#FBBF24',   // risk 0.35–0.54 → amber static
  NORMAL:   '#22C55E',   // risk 0.0–0.34  → green static

  // Area overlay colors
  SPILL_ZONE:    '#DC2626',  // confirmed spill polygon
  HIGH_RISK_AREA:'#EA580C',  // high-risk zone overlay
  TRAFFIC_DENSE: '#D97706',  // ship density heatmap peak
  MONITORING:    '#0891B2',  // satellite active scan zone
  MPA_BOUNDARY:  '#7C3AED',  // marine protected area fill

  // Track/route line colors
  TRACK_NORMAL:     '#6B7280',
  TRACK_SUSPICIOUS: '#F97316',
  TRACK_DARK_GAP:   '#EF4444',
} as const;

export const RISK_THRESHOLDS = {
  CRITICAL: 0.75,
  HIGH:     0.55,
  CAUTION:  0.35,
  NORMAL:   0.0,
} as const;

/**
 * Given a risk score (0.0 to 1.0), returns the correct hex color string.
 */
export function getRiskColor(score: number): string {
  if (score >= RISK_THRESHOLDS.CRITICAL) return RISK_COLORS.CRITICAL;
  if (score >= RISK_THRESHOLDS.HIGH)     return RISK_COLORS.HIGH;
  if (score >= RISK_THRESHOLDS.CAUTION)  return RISK_COLORS.CAUTION;
  return RISK_COLORS.NORMAL;
}

/**
 * Given a risk score, returns the alert level label.
 */
export function getRiskLabel(score: number): 'CRITICAL' | 'WARNING' | 'WATCH' | 'NORMAL' {
  if (score >= RISK_THRESHOLDS.CRITICAL) return 'CRITICAL';
  if (score >= RISK_THRESHOLDS.HIGH)     return 'WARNING';
  if (score >= RISK_THRESHOLDS.CAUTION)  return 'WATCH';
  return 'NORMAL';
}

/**
 * Returns whether a vessel at this risk score should have a blinking animation.
 */
export function isBlinking(score: number): boolean {
  return score >= RISK_THRESHOLDS.CRITICAL;
}
