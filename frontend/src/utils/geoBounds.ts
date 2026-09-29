/**
 * SATVIGIL — Indian Oceanic Maritime Zone Geofencing
 * Validates whether a given latitude/longitude lies strictly within the Indian Oceanic Zone:
 *   - Arabian Sea & Lakshadweep Sea (West Coast)
 *   - Bay of Bengal & Coromandel Coast (East Coast)
 *   - Andaman & Nicobar Sea (Southeast)
 *   - Indian Ocean Southern Transit Corridor (South of Kanyakumari / Sri Lanka)
 * Strictly excludes any terrestrial points on the Indian landmass or foreign land.
 */

export function isPointInIndiaOceanicZone(lat: number, lon: number): boolean {
  // 1. Overall bounding envelope for Indian maritime waters
  if (lat < 4.5 || lat > 24.5 || lon < 66.0 || lon > 95.0) {
    return false;
  }

  // 2. North of 23.8° N is northern terrestrial mainland (Pakistan / Rajasthan)
  if (lat > 23.8) {
    if (lat > 23.6 || lon > 68.8) return false;
  }

  // 3. Central & Southern Indian landmass (lat 8.2°N to 20.5°N)
  // Define western and eastern coastlines as functions of latitude
  if (lat >= 8.2 && lat <= 20.5) {
    let coastWest = 72.8;
    if (lat < 10.0) {
      // Kanyakumari (8.2°N, 77.5°E) to Kochi (10.0°N, 76.1°E)
      coastWest = 77.5 - ((lat - 8.2) / 1.8) * (77.5 - 76.1);
    } else if (lat < 13.0) {
      // Kochi to Mangalore (13.0°N, 74.7°E)
      coastWest = 76.1 - ((lat - 10.0) / 3.0) * (76.1 - 74.7);
    } else if (lat < 15.5) {
      // Mangalore to Goa (15.5°N, 73.7°E)
      coastWest = 74.7 - ((lat - 13.0) / 2.5) * (74.7 - 73.7);
    } else if (lat < 18.5) {
      // Goa to Ratnagiri/Alibaug
      coastWest = 73.7 - ((lat - 15.5) / 3.0) * (73.7 - 72.9);
    } else if (lat < 19.3) {
      // Mumbai / JNPT harbor approach: water extends to 73.05°E
      coastWest = 73.05;
    } else {
      // Mumbai to Daman/Surat
      coastWest = 72.9 - ((lat - 19.3) / 1.2) * (72.9 - 72.7);
    }

    let coastEast = 80.0;
    if (lat < 10.0) {
      // Kanyakumari to Point Calimere (10.0°N, 79.8°E)
      coastEast = 77.5 + ((lat - 8.2) / 1.8) * (79.8 - 77.5);
    } else if (lat < 13.0) {
      // Point Calimere to Chennai (13.0°N, 80.3°E)
      coastEast = 79.8 + ((lat - 10.0) / 3.0) * (80.2 - 79.8);
    } else if (lat < 16.5) {
      // Chennai to Kakinada (16.5°N, 82.2°E)
      coastEast = 80.2 + ((lat - 13.0) / 3.5) * (82.2 - 80.2);
    } else if (lat < 18.0) {
      // Kakinada to Visakhapatnam (17.7°N, 83.3°E)
      coastEast = 82.2 + ((lat - 16.5) / 1.5) * (83.3 - 82.2);
    } else {
      // Visakhapatnam to Paradip (20.3°N, 86.7°E)
      coastEast = 83.3 + ((lat - 18.0) / 2.5) * (86.7 - 83.3);
    }

    // Points between the west and east coastlines are inland on the Indian subcontinent
    if (lon > coastWest && lon < coastEast) {
      return false;
    }
  }

  // 4. Northern Gujarat & Central-East India (20.5°N to 23.5°N)
  if (lat > 20.5 && lat <= 23.5) {
    // East of Surat/Khambhat (73.1°E) and west of Odisha/Dhamra (86.8°E) is inland India
    if (lon > 73.1 && lon < 86.8) {
      return false;
    }
    // Saurashtra interior land: 21.1°-22.2°N, 70.3°-71.8°E
    if (lat >= 21.1 && lat <= 22.2 && lon >= 70.3 && lon <= 71.8) {
      return false;
    }
    // Kutch mainland interior: 23.1°-23.8°N, 69.4°-71.5°E
    if (lat >= 23.1 && lon >= 69.4 && lon <= 71.5) {
      return false;
    }
  }

  // 5. Inland Bangladesh & West Bengal (lat > 22.0°N and 89.2°E < lon < 92.5°E)
  if (lat > 22.0 && lon > 89.2 && lon < 92.5) {
    return false;
  }

  // 6. Mainland Myanmar (lat > 16.0°N and lon > 94.0°E)
  if (lat > 16.0 && lon > 94.0) {
    return false;
  }

  // 7. Sri Lanka island interior (lat 6.8°N to 9.2°N, lon 80.0°E to 81.3°E)
  if (lat >= 6.8 && lat <= 9.2 && lon >= 80.0 && lon <= 81.3) {
    return false;
  }

  return true;
}
