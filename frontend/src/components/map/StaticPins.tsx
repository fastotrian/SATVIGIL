/**
 * SATVIGIL — Static Strategic Maritime Pins
 * High-reliability coordinates for offshore assets, major ports, and marine sanctuaries.
 */
import { Cartesian3, Color, Entity, VerticalOrigin, HorizontalOrigin } from 'cesium';

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

/**
 * Creates Cesium Entity objects for strategic pins
 */
export function createStrategicPinEntities(): Entity[] {
  return STRATEGIC_PINS.map((pin) => {
    return new Entity({
      name: pin.name,
      position: Cartesian3.fromDegrees(pin.coordinates[0], pin.coordinates[1], 50),
      point: {
        pixelSize: 8,
        color: Color.fromCssColorString('#00D4E8'),
        outlineColor: Color.fromCssColorString('#060E1C'),
        outlineWidth: 2,
      },
      label: {
        text: `${pin.icon} ${pin.name}`,
        font: 'bold 11px JetBrains Mono, monospace',
        fillColor: Color.WHITE,
        outlineColor: Color.fromCssColorString('#0A1628'),
        outlineWidth: 2,
        style: 2, // FILL_AND_OUTLINE
        verticalOrigin: VerticalOrigin.BOTTOM,
        horizontalOrigin: HorizontalOrigin.CENTER,
        pixelOffset: { x: 0, y: -12 } as any,
        scaleByDistance: undefined,
      },
    });
  });
}
