/**
 * SATVIGIL — Main Map Component
 *
 * Shows India centered map with 5 toggleable layers:
 *  - Oil Spill / Vessel Risk (ships color-coded by risk score)
 *  - Illegal Fishing (vessels inside MPAs)
 *  - Fire Classification (hotspots with type icon)
 *  - Industrial Pollution (recurring hotspot heatmap)
 *  - Landslide Risk (SAR deformation zones)
 */
import { useRef, useEffect, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { LayerToggle } from "./LayerToggle";
import { useAlertStore } from "../../store/alertStore";

// Get token from Vite env
mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;

// India map center and zoom bounds
const INDIA_CENTER: [number, number] = [82.8, 22.5];
const INDIA_MIN_ZOOM = 4;
const INDIA_MAX_ZOOM = 12;

// Fire type → icon color mapping
const FIRE_COLORS: Record<string, string> = {
  industrial:  "#ef4444",   // red
  wildfire:    "#f97316",   // orange
  stubble:     "#eab308",   // yellow
  gas_flare:   "#a855f7",   // purple
  mining:      "#6b7280",   // gray
  unknown:     "#94a3b8",   // slate
};

// Risk level → marker color
const RISK_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high:     "#ea580c",
  medium:   "#ca8a04",
  low:      "#16a34a",
};

export function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const { alerts } = useAlertStore();

  const [activeLayers, setActiveLayers] = useState({
    oil_spill: true,
    illegal_fishing: true,
    fire: true,
    pollution: true,
    landslide: true,
  });

  // Initialize Mapbox map
  useEffect(() => {
    if (map.current || !mapContainer.current) return;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: INDIA_CENTER,
      zoom: 4.5,
      minZoom: INDIA_MIN_ZOOM,
      maxZoom: INDIA_MAX_ZOOM,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), "top-left");

    map.current.on("load", () => {
      // Add Marine Protected Areas as boundary polygons
      addMPALayer();
      // Add empty alert sources (filled when alerts load)
      addAlertSources();
    });

    return () => map.current?.remove();
  }, []);

  // Update markers when alerts change
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;
    updateAlertMarkers();
  }, [alerts]);

  function addMPALayer() {
    if (!map.current) return;
    // MPA zones shown as semi-transparent green polygons
    // In production, load from GeoJSON file or API
  }

  function addAlertSources() {
    if (!map.current) return;
    map.current.addSource("alerts", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }

  function updateAlertMarkers() {
    if (!map.current) return;
    const source = map.current.getSource("alerts") as mapboxgl.GeoJSONSource;
    if (!source) return;

    const features = alerts
      .filter((a) => {
        // Only show markers for active layers
        if (a.alert_type.startsWith("fire") && !activeLayers.fire) return false;
        if (a.alert_type === "oil_spill" && !activeLayers.oil_spill) return false;
        if (a.alert_type === "illegal_fishing" && !activeLayers.illegal_fishing) return false;
        if (a.alert_type === "industrial_pollution" && !activeLayers.pollution) return false;
        if (a.alert_type === "landslide_risk" && !activeLayers.landslide) return false;
        return true;
      })
      .map((a) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [a.longitude, a.latitude] },
        properties: {
          id: a.id,
          title: a.title,
          alert_type: a.alert_type,
          risk_level: a.risk_level,
          risk_score: a.risk_score,
          color: RISK_COLORS[a.risk_level] || "#94a3b8",
        },
      }));

    source.setData({ type: "FeatureCollection", features });
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Layer toggles overlay (top right of map) */}
      <div className="absolute top-4 right-4 z-10">
        <LayerToggle activeLayers={activeLayers} onChange={setActiveLayers} />
      </div>
    </div>
  );
}
