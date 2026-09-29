/**
 * SATVIGIL — Client-Side Satellite Reconnaissance Imagery & Fallback Generator
 * Generates calibrated Sentinel-1 C-SAR radar & Sentinel-2 Optical crops with
 * vessel point scattering, hydrodynamic wake, and tactical HUD reticles.
 */
import type { Vessel } from '../types/maritime';

export function getVesselSatelliteApiUrl(vessel: Vessel, sensor: 'sentinel1' | 'sentinel2'): string {
  const course = vessel.course_deg ?? 0;
  const speed = vessel.speed_knots ?? 12;
  return `/api/v1/satellite/vessel-image?lat=${vessel.lat}&lon=${vessel.lon}&mmsi=${vessel.mmsi}&sensor=${sensor}&course=${course}&speed=${speed}`;
}

export function generateTacticalSatelliteDataUrl(
  lat: number,
  lon: number,
  mmsi: string | number,
  sensor: 'sentinel1' | 'sentinel2',
  course = 0,
  speed = 12
): string {
  if (typeof document === 'undefined') return '';

  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  if (!ctx) return '';

  const w = 256;
  const h = 256;
  const cx = 128;
  const cy = 128;

  // Deterministic PRNG seeded by vessel lat/lon/mmsi
  const numMmsi = typeof mmsi === 'number' ? mmsi : parseInt(mmsi, 10) || 419082341;
  let seed = Math.abs(Math.floor(lat * 1000 + lon * 100 + numMmsi)) % 2147483647;
  const random = () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };

  if (sensor === 'sentinel1') {
    // ── Sentinel-1 C-SAR Microwave Radar (Bragg Sea Clutter & Speckle) ──
    const imgData = ctx.createImageData(w, h);
    const d = imgData.data;
    for (let i = 0; i < d.length; i += 4) {
      // Calibrated radar sea backscatter distribution
      const r1 = random();
      const r2 = random();
      const z = Math.sqrt(-2 * Math.log(Math.max(r1, 0.0001))) * Math.cos(2 * Math.PI * r2);
      const val = Math.min(255, Math.max(0, Math.floor(48 + z * 18)));
      d[i] = Math.floor(val * 0.70);     // Red
      d[i + 1] = Math.floor(val * 0.92); // Green
      d[i + 2] = val;                    // Blue (cool microwave hue)
      d[i + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);

    // Vignette
    const vig = ctx.createRadialGradient(cx, cy, 60, cx, cy, 140);
    vig.addColorStop(0, 'rgba(0,0,0,0)');
    vig.addColorStop(1, 'rgba(3,10,20,0.55)');
    ctx.fillStyle = vig;
    ctx.fillRect(0, 0, w, h);
  } else {
    // ── Sentinel-2 MSI True-Color Optical (Arabian Sea Deep Water) ──
    const imgData = ctx.createImageData(w, h);
    const d = imgData.data;
    for (let i = 0; i < d.length; i += 4) {
      const noise = (random() - 0.5) * 16;
      d[i] = Math.floor(Math.max(0, Math.min(255, 14 + noise * 0.4)));     // Red
      d[i + 1] = Math.floor(Math.max(0, Math.min(255, 46 + noise * 0.8))); // Green (emerald-blue)
      d[i + 2] = Math.floor(Math.max(0, Math.min(255, 78 + noise)));       // Blue
      d[i + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);

    // Subtle sun glitter
    const sunGrad = ctx.createLinearGradient(0, 0, w, h);
    sunGrad.addColorStop(0, 'rgba(255,255,255,0.06)');
    sunGrad.addColorStop(0.5, 'rgba(0,0,0,0)');
    sunGrad.addColorStop(1, 'rgba(0,30,50,0.25)');
    ctx.fillStyle = sunGrad;
    ctx.fillRect(0, 0, w, h);
  }

  // ── Vessel Geometry & Kelvin Wake ──
  const rad = ((course - 90) * Math.PI) / 180; // Standard 0° = North, 90° = East
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rad);

  const shipLen = 32;
  const shipHalfW = 6;

  // 1. Hydrodynamic Wake (trailing opposite to heading, pointing left in rotated space)
  const wakeLen = Math.min(Math.max(speed * 3.5, 30), 85);
  const wakeGrad = ctx.createLinearGradient(0, 0, -wakeLen, 0);
  if (sensor === 'sentinel1') {
    wakeGrad.addColorStop(0, 'rgba(220, 245, 255, 0.75)');
    wakeGrad.addColorStop(0.4, 'rgba(160, 220, 255, 0.35)');
    wakeGrad.addColorStop(1, 'rgba(100, 180, 255, 0.0)');
  } else {
    wakeGrad.addColorStop(0, 'rgba(255, 255, 255, 0.85)');
    wakeGrad.addColorStop(0.5, 'rgba(200, 240, 255, 0.40)');
    wakeGrad.addColorStop(1, 'rgba(150, 210, 230, 0.0)');
  }

  ctx.beginPath();
  ctx.moveTo(0, -shipHalfW);
  ctx.lineTo(-wakeLen, -shipHalfW * 3.2);
  ctx.lineTo(-wakeLen, shipHalfW * 3.2);
  ctx.lineTo(0, shipHalfW);
  ctx.closePath();
  ctx.fillStyle = wakeGrad;
  ctx.fill();

  // 2. Hull Shape (pointed bow forward)
  ctx.beginPath();
  ctx.moveTo(shipLen / 2, 0);                       // Bow point
  ctx.lineTo(shipLen / 2 - 8, -shipHalfW);          // Starboard bow
  ctx.lineTo(-shipLen / 2 + 3, -shipHalfW);         // Starboard stern
  ctx.lineTo(-shipLen / 2, -shipHalfW + 2);         // Stern corner
  ctx.lineTo(-shipLen / 2, shipHalfW - 2);          // Stern corner
  ctx.lineTo(-shipLen / 2 + 3, shipHalfW);          // Port stern
  ctx.lineTo(shipLen / 2 - 8, shipHalfW);           // Port bow
  ctx.closePath();

  if (sensor === 'sentinel1') {
    // SAR metallic radar double-bounce reflection (bright white bloom)
    ctx.shadowColor = 'rgba(255, 255, 255, 0.85)';
    ctx.shadowBlur = 6;
    ctx.fillStyle = '#FFFFFF';
    ctx.fill();

    // Superstructure radar echo
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#E2E8F0';
    ctx.fillRect(-2, -shipHalfW + 2, 8, (shipHalfW - 2) * 2);
  } else {
    // Optical true-color hull
    ctx.fillStyle = '#E2E8F0';
    ctx.fill();
    ctx.strokeStyle = '#0F172A';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Red cargo deck markings
    ctx.fillStyle = '#DC2626';
    ctx.fillRect(-6, -shipHalfW + 2, 10, (shipHalfW - 2) * 2);
    // Bridge superstructure
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(-shipLen / 2 + 5, -shipHalfW + 1.5, 6, (shipHalfW - 1.5) * 2);
  }

  ctx.restore();

  // ── Tactical Military Targeting HUD Reticle (Teal #00D4E8) ──
  ctx.strokeStyle = '#00D4E8';
  ctx.fillStyle = '#00D4E8';
  ctx.lineWidth = 1.5;

  const bSize = 24;
  const bLen = 8;
  // Corner brackets
  // Top-left
  ctx.beginPath();
  ctx.moveTo(cx - bSize, cy - bSize + bLen);
  ctx.lineTo(cx - bSize, cy - bSize);
  ctx.lineTo(cx - bSize + bLen, cy - bSize);
  ctx.stroke();

  // Top-right
  ctx.beginPath();
  ctx.moveTo(cx + bSize - bLen, cy - bSize);
  ctx.lineTo(cx + bSize, cy - bSize);
  ctx.lineTo(cx + bSize, cy - bSize + bLen);
  ctx.stroke();

  // Bottom-left
  ctx.beginPath();
  ctx.moveTo(cx - bSize, cy + bSize - bLen);
  ctx.lineTo(cx - bSize, cy + bSize);
  ctx.lineTo(cx - bSize + bLen, cy + bSize);
  ctx.stroke();

  // Bottom-right
  ctx.beginPath();
  ctx.moveTo(cx + bSize - bLen, cy + bSize);
  ctx.lineTo(cx + bSize, cy + bSize);
  ctx.lineTo(cx + bSize, cy + bSize - bLen);
  ctx.stroke();

  // Fine crosshairs
  ctx.lineWidth = 1;
  ctx.strokeStyle = 'rgba(0, 212, 232, 0.65)';
  ctx.beginPath();
  ctx.arc(cx, cy, 32, 0, Math.PI * 2);
  ctx.stroke();

  // Heading vector arrow
  const hRad = ((course - 90) * Math.PI) / 180;
  const hx = cx + Math.cos(hRad) * 44;
  const hy = cy + Math.sin(hRad) * 44;
  ctx.strokeStyle = '#00E5FF';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(hx, hy);
  ctx.stroke();

  return canvas.toDataURL('image/jpeg', 0.92);
}
