/**
 * SATVIGIL — Static Strategic Maritime Pins
 * High-reliability HTML markers for offshore assets, major ports, and marine sanctuaries.
 * Bypasses WebGL glyph font loading to eliminate any 403 font PBF errors.
 */
import React from 'react';
import { Marker } from 'react-map-gl/maplibre';


export interface StrategicPin {
  name: string;
  type: string;
  icon: string;
  coordinates: [number, number]; // [lon, lat]
}

export const STRATEGIC_PINS: StrategicPin[] = [
  {
    name: 'Bombay High (ONGC)',
    type: 'Offshore Oil Field',
    icon: '📍',
    coordinates: [71.5, 19.2],
  },
  {
    name: 'JNPT Port',
    type: 'Major Container Port',
    icon: '⚓',
    coordinates: [72.9, 18.9],
  },
  {
    name: 'Kandla Port',
    type: 'Crude Oil Hub',
    icon: '⚓',
    coordinates: [70.2, 23.0],
  },
  {
    name: 'Gulf of Kutch MNP',
    type: 'Marine Sanctuary',
    icon: '🌊',
    coordinates: [69.2, 22.5],
  },
  {
    name: 'Gulf of Mannar MNP',
    type: 'Biosphere Reserve',
    icon: '🌊',
    coordinates: [78.8, 9.0],
  },
];

export function StaticPinsLayer() {
  return (
    <>
      {STRATEGIC_PINS.map((pin) => (
        <Marker
          key={pin.name}
          longitude={pin.coordinates[0]}
          latitude={pin.coordinates[1]}
          anchor="bottom"
        >
          <div
            className="flex items-center gap-1.5 backdrop-blur-md px-2 py-0.5 rounded shadow-xl text-[10px] font-medium pointer-events-none select-none transition-all"
            style={{
              background: 'rgba(10, 22, 40, 0.88)',
              border: '1px solid var(--navy-500)',
              color: 'var(--text-primary)',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
            }}
          >
            <span className="text-xs">{pin.icon}</span>
            <span className="tracking-wide font-semibold">{pin.name}</span>
          </div>
        </Marker>
      ))}
    </>
  );
}
