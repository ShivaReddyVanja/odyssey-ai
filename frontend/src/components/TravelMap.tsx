"use client";

import React, { useEffect, useRef, useState } from "react";
import { FullItinerary, Place, TransitOption } from "../hooks/useEventStream";

interface TravelMapProps {
  itinerary: FullItinerary | null;
}

export default function TravelMap({ itinerary }: TravelMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const pathsRef = useRef<any[]>([]);
  const [leafletLoaded, setLeafletLoaded] = useState(false);

  // Initialize Leaflet Map
  useEffect(() => {
    if (typeof window === "undefined" || !mapContainerRef.current) return;

    const initMap = async () => {
      try {
        const L = (await import("leaflet")).default;

        // Prevent double-initialization in React Strict Mode/concurrent imports
        if (!mapContainerRef.current || (mapContainerRef.current as any)._leaflet_id) {
          return;
        }

        setLeafletLoaded(true);

        // Center on a default location (e.g., Rome)
        const defaultCenter: [number, number] = [41.9028, 12.4964];
        
        const map = L.map(mapContainerRef.current!, {
          center: defaultCenter,
          zoom: 13,
          zoomControl: true,
          attributionControl: false,
        });

        // Add standard OSM tile layer
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
        }).addTo(map);

        mapInstanceRef.current = map;

        // Trigger resize event after creation to avoid layout bugs
        setTimeout(() => {
          map.invalidateSize();
        }, 100);
      } catch (err) {
        console.error("Failed to initialize Leaflet map:", err);
      }
    };

    initMap();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers and Paths when itinerary changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !itinerary || !leafletLoaded) return;

    // Helper function to load Leaflet dynamically
    const updateLayers = async () => {
      const L = (await import("leaflet")).default;

      // 1. Clear existing markers and paths
      markersRef.current.forEach((m) => m.remove());
      pathsRef.current.forEach((p) => p.remove());
      markersRef.current = [];
      pathsRef.current = [];

      // 2. Extract unique places, sequential segments, and transits
      const uniquePlaces = new Map<string, Place & { arrivalTransits?: TransitOption[] }>();
      const segments: { p1: Place; p2: Place; transits: TransitOption[] }[] = [];
      let lastPlace: Place | null = null;
      let pendingTransits: TransitOption[] = [];

      itinerary.days.forEach((day) => {
        day.schedule.forEach((item) => {
          if (item.type === "transit") {
            pendingTransits.push(item as TransitOption);
          } else if (item.type === "place") {
            const placeItem = item as Place;
            const loc = placeItem.location;
            
            if (loc && loc.latitude && loc.longitude) {
              // If it's the very first place, it might have arrival transits
              if (!lastPlace && pendingTransits.length > 0) {
                (placeItem as any).arrivalTransits = [...pendingTransits];
              }

              if (lastPlace) {
                segments.push({ p1: lastPlace, p2: placeItem, transits: [...pendingTransits] });
              }
              
              lastPlace = placeItem;
              pendingTransits = [];

              // Dedup places list
              if (!uniquePlaces.has(placeItem.id)) {
                uniquePlaces.set(placeItem.id, placeItem);
              } else if ((placeItem as any).arrivalTransits) {
                // Update existing if it has new arrival transits
                const existing = uniquePlaces.get(placeItem.id)!;
                (existing as any).arrivalTransits = (placeItem as any).arrivalTransits;
              }
            }
          }
        });
      });

      const placesList = Array.from(uniquePlaces.values());

      // 3. Create Custom Markers
      placesList.forEach((place) => {
        const { latitude, longitude } = place.location;
        
        // Define color and emoji based on category
        let color = "#3b82f6"; // default -> Blue
        let fallbackEmoji = "📍";

        if (place.category === "stay" || place.category === "hotel" || place.category === "accommodation") {
          color = "#ef4444"; // stay -> Map Red
          fallbackEmoji = "🏨";
        } else if (place.category === "food" || place.category === "restaurant" || place.category === "cafe") {
          color = "#eab308"; // food -> Map Yellow
          fallbackEmoji = "🍽️";
        } else if (place.category === "sightseeing" || place.category === "activity" || place.category === "attraction") {
          color = "#22c55e"; // sightseeing -> Map Green
          fallbackEmoji = "🏛️";
        }

        let iconHtml = "";
        if (place.photo_url) {
          iconHtml = `
            <img src="${place.photo_url}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block;" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
            <div style="display: none; width: 100%; height: 100%; align-items: center; justify-content: center; font-size: 14px; color: white;">${fallbackEmoji}</div>
          `;
        } else {
          iconHtml = `<div style="display: flex; width: 100%; height: 100%; align-items: center; justify-content: center; font-size: 14px; color: white;">${fallbackEmoji}</div>`;
        }

        // Custom DivIcon for glowing neon pins
        const customIcon = L.divIcon({
          className: "custom-map-pin-container",
          html: `
            <div class="custom-map-pin-inner" style="
              background: ${place.photo_url ? "#ffffff" : color};
              box-shadow: 0 2px 8px ${color}80, 0 0 0 1.5px ${color};
            ">
              ${iconHtml}
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });

        const ratingString = place.rating ? `⭐ ${place.rating}` : "No rating yet";
        const costString = place.cost_estimate ? "$".repeat(Math.round(place.cost_estimate)) : "$$";

        let arrivalHtml = "";
        if (place.arrivalTransits && place.arrivalTransits.length > 0) {
           const t = place.arrivalTransits[0];
           arrivalHtml = `<div style="margin-bottom: 6px; padding: 6px; background: #f1f5f9; border-radius: 4px; font-size: 11px;">
             <strong style="color: #6366f1;">Arrived via ${t.mode.toUpperCase()}</strong><br/>
             <span style="color: #475569;">${t.origin} ➔ ${t.destination}</span>
           </div>`;
        }

        const popupContent = `
          <div style="font-family: var(--font-sans); padding: 4px;">
            ${arrivalHtml}
            <h4 style="margin: 0 0 4px 0; font-weight: 600; color: #37352f;">${place.name}</h4>
            <p style="margin: 0 0 6px 0; font-size: 11px; color: var(--text-muted);">${place.location.address}</p>
            <div style="display: flex; justify-content: space-between; font-size: 10px; font-weight: bold; color: var(--color-accent);">
              <span>${ratingString}</span>
              <span>Price: ${costString}</span>
            </div>
            <p style="margin: 6px 0 0 0; font-size: 10px; line-height: 1.3; color: #5a5a5a;">${place.description}</p>
          </div>
        `;

        const marker = L.marker([latitude, longitude], { icon: customIcon })
          .addTo(map)
          .bindPopup(popupContent);

        markersRef.current.push(marker);
      });

      // 4. Create Polyline routes and transit segments
      segments.forEach((seg) => {
        const c1: [number, number] = [seg.p1.location.latitude, seg.p1.location.longitude];
        const c2: [number, number] = [seg.p2.location.latitude, seg.p2.location.longitude];

        if (c1[0] === c2[0] && c1[1] === c2[1]) return; // Skip zero-distance lines

        let lineColor = "#37352f"; // Dark grey default
        let tooltipHtml = "";

        if (seg.transits.length > 0) {
          const t = seg.transits[0];
          if (t.mode === "flight") lineColor = "#8b5cf6"; // Purple
          else if (t.mode === "train") lineColor = "#f97316"; // Orange
          else lineColor = "#0ea5e9"; // Sky blue (car/bus)

          tooltipHtml = `
            <div style="font-family: var(--font-sans); text-align: center; font-size: 11px; padding: 2px;">
              <strong style="color: ${lineColor}">${t.mode.toUpperCase()}</strong><br/>
              ${t.origin} ➔ ${t.destination}<br/>
              ⏱️ ${Math.floor(t.duration_minutes / 60)}h ${t.duration_minutes % 60}m
            </div>
          `;
        }

        // Draw casing background line
        const polyBg = L.polyline([c1, c2], {
          color: "#ffffff",
          weight: 6,
          opacity: 0.95,
        }).addTo(map);
        pathsRef.current.push(polyBg);

        // Draw colored segment
        const polyline = L.polyline([c1, c2], {
          color: lineColor,
          weight: 3.2,
          opacity: 0.9,
          dashArray: "8, 6",
        }).addTo(map);

        if (tooltipHtml) {
          polyline.bindTooltip(tooltipHtml, { sticky: false, className: "map-transit-tooltip" });
        }
        
        pathsRef.current.push(polyline);
      });

      // Fit map bounds to contain all coordinates
      const allCoords: [number, number][] = [];
      placesList.forEach(p => allCoords.push([p.location.latitude, p.location.longitude]));
      if (allCoords.length > 1) {
         map.fitBounds(L.latLngBounds(allCoords), { padding: [50, 50] });
      } else if (allCoords.length === 1) {
         map.setView(allCoords[0], 14);
      }
    };

    updateLayers();
  }, [itinerary, leafletLoaded]);

  return (
    <div className="travel-map-root">
      {/* Absolute title panel */}
      <div className="travel-map-overlay">
        <h2 className="travel-map-title">
          🗺️ Route Map
        </h2>
        <p className="travel-map-subtitle">
          {itinerary ? `${itinerary.destination} (${itinerary.duration_days} Days)` : "Real-time travel geometry"}
        </p>
      </div>

      {/* Map Element */}
      <div
        ref={mapContainerRef}
        className="travel-map-container"
        style={{ zIndex: 1 }}
      />
    </div>
  );
}
