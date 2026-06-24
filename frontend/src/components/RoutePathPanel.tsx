"use client";

import React, { useRef, useState } from "react";
import { FullItinerary, Place, TransitOption, ScheduleItem } from "../hooks/useEventStream";
import {
  Calendar,
  Clock,
  Star,
  ArrowRight,
  Compass,
  Layers,
  Plane,
  Car,
  Train,
  MapPin,
  Camera,
  Hotel,
  Utensils,
  Navigation,
} from "lucide-react";

interface RoutePathPanelProps {
  itinerary: FullItinerary | null;
}

interface EventCoord {
  id: string;
  dayIndex: number;
  dayNumber: number;
  itemIndex: number;
  type: "place" | "transit";
  itemData: Place | TransitOption;
  x: number;
  y: number;
  isFirstOfDay: boolean;
  isLastOfDay: boolean;
}

export default function RoutePathPanel({ itinerary }: RoutePathPanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);

  if (!itinerary) {
    return (
      <div className="route-path-empty">
        <div className="route-path-empty-card">
          <div className="route-path-empty-icon">
            <Compass size={40} className="compass-spin" />
          </div>
          <h3>Interactive Route Map</h3>
          <p>
            Once NomadGraph compiles your itinerary, a beautiful illustrative travel map
            of your journey will be plotted here.
          </p>
          <div className="route-path-empty-preview">
            <div className="preview-node" />
            <div className="preview-line" />
            <div className="preview-node" />
            <div className="preview-line" />
            <div className="preview-node" />
          </div>
        </div>
      </div>
    );
  }

  // Helper to extract clean city name
  const getCityName = (place: Place) => {
    const searchString = `${place.name} ${place.location?.address || ""}`.toLowerCase();
    
    const cities = [
      "kochi", "munnar", "alleppey", "alappuzha", "coorg", "madikeri", "mysore", "mysuru",
      "wayanad", "kovalam", "varkala", "dharamshala", "manali", "shimla", "delhi", "leh",
      "ladakh", "kasol", "srinagar", "gulmarg", "pahalgam", "rishikesh", "haridwar", 
      "hyderabad", "bangalore", "bengaluru", "mumbai", "goa", "hampi", "mangalore", "hubli",
      "agra", "jaipur", "udaipur", "jaisalmer", "jodhpur", "rome", "venice", "florence", "milan",
      "dublin", "galway", "cork", "killarney"
    ];
    
    for (const city of cities) {
      if (searchString.includes(city)) {
        return city.charAt(0).toUpperCase() + city.slice(1);
      }
    }
    
    const addr = place.location?.address || "";
    const parts = addr.split(",").map(p => p.trim());
    if (parts.length >= 3) {
      const cityPart = parts[parts.length - 3].replace(/\d+/g, "").trim();
      if (cityPart.length > 2) return cityPart;
    }
    
    return place.name.split(" ")[0];
  };

  // Extract primary city for each day to show in header/jump-bar
  const getDayLocation = (schedule: ScheduleItem[]) => {
    const stays = schedule.filter(
      (item) => item.type === "place" && item.category === "stay"
    ) as Place[];
    if (stays.length > 0) return getCityName(stays[0]);

    const sights = schedule.filter(
      (item) => item.type === "place" && item.category === "sightseeing"
    ) as Place[];
    if (sights.length > 0) return getCityName(sights[0]);

    return "";
  };

  // Serpentine Grid Math Parameters
  const colStep = 240;       // Narrower horizontal spacing between columns
  const verticalStep = 160;  // Tighter vertical spacing
  const startX = 140;        // Left padding
  const startY = 160;        // Top padding
  const nodeOffset = 24;     // Distance of content from the track line

  // 1. Calculate coordinates (x, y) for all items in 2D serpentine grid
  const eventCoords: EventCoord[] = [];
  itinerary.days.forEach((day, d) => {
    const numEvents = day.schedule.length;
    day.schedule.forEach((item, i) => {
      const colX = startX + d * colStep;
      const isEvenDay = d % 2 === 0;
      
      // Y-coordinate:
      // Even columns go down (0 is at top, numEvents-1 is at bottom)
      // Odd columns go up (0 is at bottom, numEvents-1 is at top)
      const y = isEvenDay 
        ? startY + i * verticalStep 
        : startY + (numEvents - 1 - i) * verticalStep;

      eventCoords.push({
        id: item.id,
        dayIndex: d,
        dayNumber: day.day_number,
        itemIndex: i,
        type: item.type,
        itemData: item,
        x: colX,
        y,
        isFirstOfDay: i === 0,
        isLastOfDay: i === numEvents - 1,
      });
    });
  });

  // Calculate canvas dimensions dynamically
  const numDays = itinerary.days.length;
  const maxEvents = Math.max(...itinerary.days.map(d => d.schedule.length));
  
  const canvasWidth = startX + (numDays - 1) * colStep + 200; 
  const canvasHeight = Math.max(650, startY + (maxEvents - 1) * verticalStep + 180); 

  // Scroll to a specific day's column
  const scrollToDay = (dayNumber: number | null) => {
    if (dayNumber === null) {
      setSelectedDay(null);
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollTo({
          left: 0,
          top: 0,
          behavior: "smooth",
        });
      }
      return;
    }

    setSelectedDay(dayNumber);
    
    const dayIndex = dayNumber - 1;
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      const targetX = startX + dayIndex * colStep - 100;
      
      container.scrollTo({
        left: Math.max(0, targetX),
        top: 0,
        behavior: "smooth",
      });
    }
  };

  // Helper to get category-specific color (map style muted tones)
  const getCategoryColor = (coord: EventCoord) => {
    if (coord.type === "transit") {
      const mode = (coord.itemData as TransitOption).mode;
      if (mode === "flight") return "#8b5cf6"; // Purple
      if (mode === "train") return "#f97316"; // Orange
      return "#0ea5e9"; // Sky blue (default/car/bus)
    }
    const place = coord.itemData as Place;
    if (place.category === "stay") return "#ef4444"; // Map Red
    if (place.category === "food") return "#eab308"; // Map Yellow
    if (place.category === "sightseeing") return "#22c55e"; // Map Green
    return "#3b82f6"; // Map Blue
  };

  // Generate SVG path segment connecting Item i to i+1
  const getSegmentPathString = (i: number) => {
    const p1 = eventCoords[i];
    const p2 = eventCoords[i + 1];
    const offset = 12; // offset to stop before the 16px (radius 8px) dot
    
    if (p1.dayIndex === p2.dayIndex) {
      // Straight vertical segment
      const isGoingDown = p2.y > p1.y;
      const startY = isGoingDown ? p1.y + offset : p1.y - offset;
      const endY = isGoingDown ? p2.y - offset : p2.y + offset;
      return `M ${p1.x} ${startY} L ${p2.x} ${endY}`;
    } else {
      // U-turn curve connecting day boundaries
      const dy = 90; // Bulge vertical curve offset
      
      if (p1.dayIndex % 2 === 0) {
        // Even day ending at bottom -> Bottom U-turn
        return `M ${p1.x} ${p1.y + offset} C ${p1.x} ${p1.y + dy}, ${p2.x} ${p2.y + dy}, ${p2.x} ${p2.y + offset}`;
      } else {
        // Odd day ending at top -> Top U-turn
        return `M ${p1.x} ${p1.y - offset} C ${p1.x} ${p1.y - dy}, ${p2.x} ${p2.y - dy}, ${p2.x} ${p2.y - offset}`;
      }
    }
  };

  return (
    <div className="route-path-root map-aesthetic-root">
      {/* ── Day Navigation Jump Bar ── */}
      <div className="route-path-nav">
        <div className="route-path-nav-title">
          <span>The Serpentine Journey</span>
          <span className="route-path-nav-sub">{itinerary.destination}</span>
        </div>
        <div className="route-path-nav-scroll">
          <button
            onClick={() => scrollToDay(null)}
            className={`route-path-nav-btn ${selectedDay === null ? "route-path-nav-btn--active-green" : ""}`}
            style={{ minWidth: "90px" }}
          >
            <Compass size={12} />
            <span className="btn-loc" style={{ color: selectedDay === null ? "#ffffff" : "#44403c" }}>View Map</span>
          </button>

          {itinerary.days.map((day) => {
            const locName = getDayLocation(day.schedule);
            const isActive = selectedDay === day.day_number;
            return (
              <button
                key={day.day_number}
                onClick={() => scrollToDay(day.day_number)}
                className={`route-path-nav-btn map-nav-btn ${isActive ? "map-nav-btn--active" : ""}`}
              >
                <span className="btn-day">Day {day.day_number}</span>
                {locName && <span className="btn-loc">{locName}</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Scrollable Canvas Container ── */}
      <div className="route-path-timeline-outer" ref={scrollContainerRef}>
        <div 
          className="route-path-timeline-inner" 
          style={{ 
            width: `${canvasWidth}px`, 
            height: `${canvasHeight}px`,
            position: "relative"
          }}
        >
          {/* Day Column Separators (Thin vertical lines) */}
          {itinerary.days.map((day, d) => {
            if (d === 0) return null; // No line before Day 1
            const lineX = startX + d * colStep - (colStep / 2);
            return (
              <div 
                key={`sep-${day.day_number}`}
                className="map-column-separator"
                style={{
                  position: "absolute",
                  left: `${lineX}px`,
                  top: "20px",
                  bottom: "20px",
                  width: "1px",
                  backgroundColor: "#d6d3d1",
                  zIndex: 0
                }}
              />
            );
          })}

          {/* Map Track SVG */}
          <svg className="route-path-snake-svg">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#78716c" />
              </marker>
            </defs>

            {/* Render all path segments */}
            {eventCoords.slice(0, -1).map((_, i) => {
              const pathD = getSegmentPathString(i);
              const p1 = eventCoords[i];
              const p2 = eventCoords[i + 1];
              
              const isSegmentActive =
                selectedDay === null ||
                (p1.dayNumber === selectedDay && p2.dayNumber === selectedDay);

              return (
                <path
                  key={`map-path-${i}`}
                  d={pathD}
                  fill="none"
                  stroke="#78716c" /* Dark warm grey for map ink */
                  strokeWidth="2.5"
                  strokeDasharray="6 6"
                  strokeLinecap="round"
                  markerEnd="url(#arrow)"
                  style={{
                    opacity: isSegmentActive ? 1 : 0.2,
                    transition: "opacity 0.4s ease-in-out",
                  }}
                />
              );
            })}
          </svg>

          {/* Map Column Headers */}
          {itinerary.days.map((day, d) => {
            const locName = getDayLocation(day.schedule);
            const colX = startX + d * colStep;
            const isGrayed = selectedDay !== null && selectedDay !== day.day_number;
            
            return (
              <div
                key={`map-header-${day.day_number}`}
                className={`map-day-header ${isGrayed ? "map-grayscale" : ""}`}
                style={{
                  position: "absolute",
                  left: `${colX}px`,
                  top: "40px",
                  transform: "translate(-50%, 0)",
                  zIndex: 3,
                  textAlign: "center"
                }}
              >
                <div className="map-header-title">DAY {day.day_number}</div>
                {locName && <div className="map-header-subtitle">{locName}</div>}
              </div>
            );
          })}

          {/* Absolute Render Layer for Event Checkpoints */}
          {eventCoords.map((coord) => {
            const isPlace = coord.type === "place";
            const isGrayed = selectedDay !== null && selectedDay !== coord.dayNumber;
            const itemColor = getCategoryColor(coord);
            
            // In the reference map, items alternate. Let's place content on the right.
            const contentAlign = "right" as string;

            return (
              <div
                key={`${coord.id}-${coord.dayIndex}-${coord.itemIndex}`}
                className={`map-event-anchor ${isGrayed ? "map-grayscale" : ""}`}
                style={{
                  position: "absolute",
                  left: `${coord.x}px`,
                  top: `${coord.y}px`,
                  width: "0px",
                  height: "0px",
                  zIndex: 4,
                }}
                onClick={() => setSelectedDay(coord.dayNumber)}
              >
                {/* Minimalist Station Dot on Track */}
                <div
                  className="map-node-dot"
                  style={{
                    backgroundColor: itemColor,
                  }}
                />

                {/* Minimalist Content Layer (No Card Box) */}
                <div 
                  className={`map-content-layer align-${contentAlign}`}
                  style={{
                    position: "absolute",
                    top: "50%",
                    transform: "translateY(-50%)",
                    left: contentAlign === "right" ? `${nodeOffset}px` : "auto",
                    right: contentAlign === "left" ? `${nodeOffset}px` : "auto",
                    width: "140px", // narrow column for content
                    display: "flex",
                    flexDirection: "column",
                    alignItems: contentAlign === "left" ? "flex-end" : "flex-start",
                    textAlign: contentAlign === "left" ? "right" : "left",
                  }}
                >
                  {isPlace ? (
                    <>
                      {/* Clean Thumbnail */}
                      {(coord.itemData as Place).photo_url && (
                        <div className="map-thumbnail-container">
                          <img
                            src={(coord.itemData as Place).photo_url}
                            alt={(coord.itemData as Place).name}
                            className="map-thumbnail-image"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        </div>
                      )}
                      
                      {/* Map Text */}
                      <div className="map-text-block">
                        <h4 className="map-title">{(coord.itemData as Place).name}</h4>
                        {(coord.itemData as Place).category && (
                          <div className="map-subtitle">
                            {(coord.itemData as Place).category}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    /* Transit Label */
                    <div className="map-text-block transit-block" style={{ width: "100%", alignItems: "center" }}>
                      <div className="map-transit-icon" style={{ color: itemColor }}>
                        {(coord.itemData as TransitOption).mode === "flight" ? <Plane size={16} /> : 
                         (coord.itemData as TransitOption).mode === "train" ? <Train size={16} /> : <Car size={16} />}
                      </div>
                      <h4 className="map-title" style={{ color: itemColor, textAlign: "center", marginBottom: "4px", fontSize: "12px" }}>
                        {(coord.itemData as TransitOption).mode.toUpperCase()}
                      </h4>
                      <div className="map-subtitle" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px", fontSize: "10px", color: "#292524", fontWeight: 700, width: "100%" }}>
                        <span title={(coord.itemData as TransitOption).origin} style={{ textAlign: "center", width: "100%", whiteSpace: "normal", wordWrap: "break-word" }}>
                          {(coord.itemData as TransitOption).origin.split(",")[0]}
                        </span>
                        <ArrowRight size={12} style={{ color: itemColor, transform: "rotate(90deg)" }} />
                        <span title={(coord.itemData as TransitOption).destination} style={{ textAlign: "center", width: "100%", whiteSpace: "normal", wordWrap: "break-word" }}>
                          {(coord.itemData as TransitOption).destination.split(",")[0]}
                        </span>
                      </div>
                      <div className="map-subtitle" style={{ marginTop: "4px", fontWeight: 600 }}>
                        {Math.floor((coord.itemData as TransitOption).duration_minutes / 60)}h {(coord.itemData as TransitOption).duration_minutes % 60}m
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
