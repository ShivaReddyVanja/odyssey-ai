"use client";

import React from "react";
import {
  ShieldCheck,
  BrainCircuit,
  Network,
  PlaneTakeoff,
  Hotel,
  UtensilsCrossed,
  MapPin,
} from "lucide-react";
import { LogMessage, ApiCallEvent } from "../hooks/useEventStream";

/* ─── Types ─────────────────────────────────────────────────────────────── */

export interface PipelinePanelProps {
  activeNode: string | null;
  phase: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  candidates: Record<string, any[]>;
  logs?: LogMessage[];
  activeApiCall?: ApiCallEvent | null;
}

type NodeState = "idle" | "active" | "done" | "error";

/* ─── Brand SVG Icons ────────────────────────────────────────────────────── */

const GoogleFlightsIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21 16V14L13 9V3.5C13 2.67 12.33 2 11.5 2C10.67 2 10 2.67 10 3.5V9L2 14V16L10 13.5V19L8 20.5V22L11.5 21L15 22V20.5L13 19V13.5L21 16Z" fill="#1A73E8"/>
  </svg>
);

const GoogleMapsIcon = () => (
  <svg width="24" height="24" viewBox="0 0 34 50" fill="none" xmlns="http://www.w3.org/2000/svg" transform="scale(0.5) translate(-8, -12)">
    <path d="M17 0C7.6 0 0 7.6 0 17C0 29.8 17 50 17 50C17 50 34 29.8 34 17C34 7.6 26.4 0 17 0Z" fill="#34A853"/>
    <path d="M17 0C7.6 0 0 7.6 0 17C0 20.9 1.4 24.6 3.6 27.5L17 11.2V0Z" fill="#4285F4"/>
    <path d="M17 11.2L3.6 27.5C6.5 31.3 11.2 35.8 17 42.5V11.2Z" fill="#EA4335"/>
    <path d="M17 11.2V42.5C22.8 35.8 27.5 31.3 30.4 27.5L17 11.2Z" fill="#FBBC05"/>
    <circle cx="17" cy="17" r="6" fill="#1A73E8"/>
  </svg>
);

const BookingComIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#003580"/>
    <path d="M5 4H11.5C13.9853 4 16 6.01472 16 8.5C16 10.0827 15.1843 11.4746 13.9472 12.2682C15.1764 12.9649 16 14.2828 16 15.8C16 18.2853 13.9853 20.3 11.5 20.3H5V4ZM8.2V9.8H11.3C12.018 9.8 12.6 9.21797 12.6 8.5C12.6 7.78203 12.018 7.2 11.3 7.2H8.2V9.8ZM8.2 12.5V17.1H11.3C12.018 17.1 12.6 16.518 12.6 15.8C12.6 15.082 12.018 14.5 11.3 14.5H8.2V12.5Z" fill="white"/>
  </svg>
);

const GooglePlacesIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
  </svg>
);

const TripadvisorIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM8.5 15C7.67 15 7 14.33 7 13.5C7 12.67 7.67 12 8.5 12C9.33 12 10 12.67 10 13.5C10 14.33 9.33 15 8.5 15ZM12 18.5C10.5 18.5 9 17.5 9 16.5H15C15 17.5 13.5 18.5 12 18.5ZM15.5 15C14.67 15 14 14.33 14 13.5C14 12.67 14.67 12 15.5 12C16.33 12 17 12.67 17 13.5C17 14.33 16.33 15 15.5 15Z" fill="#34E0A1" />
    <path d="M10 13.5H14" stroke="#000000" strokeWidth="1.5" />
    <path d="M12 14.5L11.5 16H12.5L12 14.5Z" fill="#000000" />
  </svg>
);

const SerpApiIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="11" cy="11" r="6" stroke="#4285F4" strokeWidth="2.5"/>
    <line x1="16" y1="16" x2="22" y2="22" stroke="#EA4335" strokeWidth="3" strokeLinecap="round"/>
    <circle cx="11" cy="11" r="2.5" fill="#FBBC05"/>
  </svg>
);

const TicketmasterIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="6" fill="#026CDF"/>
    <path d="M6 8.5C6 7.67 6.67 7 7.5 7H16.5C17.33 7 18 7.67 18 8.5V10.5C17.17 10.5 16.5 11.17 16.5 12C16.5 12.83 17.17 13.5 18 13.5V15.5C18 16.33 17.33 17 16.5 17H7.5C6.67 17 6 16.33 6 15.5V13.5C6.83 13.5 7.5 12.83 7.5 12C7.5 11.17 6.83 10.5 6 10.5V8.5Z" fill="white"/>
    <line x1="10" y1="9" x2="10" y2="15" stroke="#026CDF" strokeWidth="1.5" strokeDasharray="2 2"/>
  </svg>
);

const SkyscannerIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="6" fill="#00b2d6"/>
    <path d="M12 4.5C7.86 4.5 4.5 7.86 4.5 12C4.5 16.14 7.86 19.5 12 19.5C16.14 19.5 19.5 16.14 19.5 12C19.5 7.86 16.14 4.5 12 4.5ZM12 16.5C9.52 16.5 7.5 14.48 7.5 12C7.5 9.52 9.52 7.5 12 7.5C14.48 7.5 16.5 9.52 16.5 12C16.5 14.48 14.48 16.5 12 16.5Z" fill="white"/>
    <circle cx="12" cy="12" r="2.5" fill="white"/>
  </svg>
);

const UnknownApiIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 4" />
    <path d="M12 8V12L15 15" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

/* ─── Node Configs ──────────────────────────────────────────────────────── */

const MAIN_NODES = [
  {
    id: "gatekeeper",
    name: "Gatekeeper",
    role: "Security & Validation",
    icon: <ShieldCheck size={18} strokeWidth={2.2} />,
    accent: "#e11d48",
    accentBg: "rgba(225,29,72,0.07)",
    accentBorder: "rgba(225,29,72,0.18)",
  },
  {
    id: "planner",
    name: "Master Planner",
    role: "Strategic Reasoning",
    icon: <BrainCircuit size={18} strokeWidth={2.2} />,
    accent: "#4f46e5",
    accentBg: "rgba(79,70,229,0.07)",
    accentBorder: "rgba(79,70,229,0.18)",
  },
  {
    id: "captain",
    name: "Captain",
    role: "Task Orchestration",
    icon: <Network size={18} strokeWidth={2.2} />,
    accent: "#475569",
    accentBg: "rgba(71,85,105,0.07)",
    accentBorder: "rgba(71,85,105,0.18)",
  },
];

const SUB_NODES = [
  {
    id: "travel",
    name: "Transit Agent",
    role: "Logistics",
    icon: <PlaneTakeoff size={16} strokeWidth={2.2} />,
    accent: "#2563eb",
    accentBg: "rgba(37,99,235,0.07)",
    accentBorder: "rgba(37,99,235,0.18)",
  },
  {
    id: "stay",
    name: "Lodging Agent",
    role: "Accommodation",
    icon: <Hotel size={16} strokeWidth={2.2} />,
    accent: "#7c3aed",
    accentBg: "rgba(124,58,237,0.07)",
    accentBorder: "rgba(124,58,237,0.18)",
  },
  {
    id: "food",
    name: "Culinary Agent",
    role: "Dining",
    icon: <UtensilsCrossed size={16} strokeWidth={2.2} />,
    accent: "#ea580c",
    accentBg: "rgba(234,88,12,0.07)",
    accentBorder: "rgba(234,88,12,0.18)",
  },
  {
    id: "sightseeing",
    name: "Experience Agent",
    role: "Activities",
    icon: <MapPin size={16} strokeWidth={2.2} />,
    accent: "#059669",
    accentBg: "rgba(5,150,105,0.07)",
    accentBorder: "rgba(5,150,105,0.18)",
  },
];

/* ─── Helpers ────────────────────────────────────────────────────────────── */

function getNodeState(id: string, activeNode: string | null, phase: string): NodeState {
  if (activeNode === id) return "active";
  if (phase === "error" && activeNode === id) return "error";

  // Mark as done when planning has moved past this node
  const ORDER = ["gatekeeper", "planner", "captain", "travel", "stay", "food", "sightseeing"];
  const activeIdx = ORDER.indexOf(activeNode ?? "");
  const thisIdx = ORDER.indexOf(id);

  if (phase === "completed") return "done";
  if (activeIdx > thisIdx && thisIdx !== -1) return "done";

  return "idle";
}

/* ─── Components ─────────────────────────────────────────────────────────── */

function NodeCard({
  node,
  state,
  size = "normal",
}: {
  node: typeof MAIN_NODES[0] | typeof SUB_NODES[0];
  state: NodeState;
  size?: "large" | "normal";
}) {
  const isActive = state === "active";
  const isDone = state === "done";
  const isError = state === "error";

  const borderColor =
    isActive ? "transparent" :
    isDone ? "rgba(55,53,47,0.14)" :
    isError ? "#e03e3e" :
    "rgba(55,53,47,0.10)";

  const bgColor =
    isActive ? "transparent" :
    isDone ? "#fafaf9" :
    "#ffffff";

  // Overlay background color for the active card
  const overlayBg = `linear-gradient(${node.accentBg}, ${node.accentBg}), #ffffff`;

  const shadowStyle =
    isActive
      ? "0 10px 25px rgba(0,0,0,0.08), 0 3px 10px rgba(0,0,0,0.04)"
      : "0 1px 3px rgba(15,15,15,0.05)";

  return (
    <div
      id={`${node.id}-agent-card`}
      className={`pipeline-node-card ${isActive ? "state-active" : isDone ? "state-done" : ""}`}
      style={{
        border: `1.5px solid ${borderColor}`,
        background: bgColor,
        boxShadow: shadowStyle,
        width: size === "large" ? 220 : 180,
        height: 64,
        display: "flex",
        alignItems: "center",
        transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)",
        position: "relative",
        transform: isActive ? "scale(1.06)" : "scale(1)",
        zIndex: isActive ? 20 : 1,
        animation: isActive ? "none" : undefined,
        // CSS custom properties for border pulse
        "--active-color": node.accent,
        "--active-color-alpha": `${node.accent}20`,
        "--active-color-alpha-bright": `${node.accent}60`,
      } as React.CSSProperties}
    >
      {/* 1. Inner overflow container for the rainbow border */}
      {isActive && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "inherit",
            overflow: "hidden",
            zIndex: 1,
            pointerEvents: "none",
          }}
        >
          {/* Rotating rainbow background with Google colors */}
          <div
            style={{
              position: "absolute",
              top: "-150%",
              left: "-150%",
              width: "400%",
              height: "400%",
              background: "conic-gradient(#4285F4, #EA4335, #FBBC05, #34A853, #4285F4)",
              animation: "spin 3s linear infinite",
            }}
          />
        </div>
      )}

      {/* 2. Solid overlay covering the center of the card, leaving 1.5px border */}
      {isActive && (
        <div
          style={{
            position: "absolute",
            inset: 1.5,
            background: overlayBg,
            borderRadius: "inherit",
            zIndex: 2,
            pointerEvents: "none",
          }}
        />
      )}

      <div
        className="pipeline-node-inner"
        style={{
          position: "relative",
          zIndex: 3,
          width: "100%",
          height: "100%",
        }}
      >
        <div
          className="pipeline-node-icon"
          style={{
            background: `linear-gradient(${node.accentBg}, ${node.accentBg}), #ffffff`,
            border: `1px solid ${node.accentBorder}`,
            color: node.accent,
          }}
        >
          {node.icon}
        </div>
        <div className="pipeline-node-text">
          <div className="pipeline-node-name" style={{ color: isActive ? node.accent : isDone ? "rgba(55,53,47,0.45)" : "#37352f" }}>
            {node.name}
          </div>
          <div className="pipeline-node-role">{node.role}</div>
        </div>
        
        <div className="pipeline-node-status" />
      </div>

      {node.id === "gatekeeper" && (
        <div
          id="gatekeeper-plug-socket"
          className="gatekeeper-socket"
          style={{
            position: "absolute",
            right: "-7px",
            top: "50%",
            transform: "translateY(-50%)",
            width: "14px",
            height: "14px",
            zIndex: 25, // raised zIndex to sit cleanly over the border layers
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="gk-socket-metal" cx="50%" cy="50%" r="50%" fx="30%" fy="30%">
                <stop offset="0%" stopColor="#ffffff" />
                <stop offset="60%" stopColor="#cbd5e1" />
                <stop offset="100%" stopColor="#475569" />
              </radialGradient>
            </defs>
            <circle cx="7" cy="7" r="6.5" fill="url(#gk-socket-metal)" stroke="#1e293b" strokeWidth="0.5" />
            <circle cx="7" cy="7" r="4.5" fill="#0f172a" stroke="#334155" strokeWidth="0.5" />
            <circle
              cx="7"
              cy="7"
              r="1.8"
              fill={isActive ? "#e11d48" : isDone ? "#10b981" : isError ? "#ef4444" : "#e2e8f0"}
              className={isActive ? "led-glow-active" : isError ? "led-glow-error" : ""}
              style={{
                filter: (isActive || isDone || isError) ? `drop-shadow(0 0 2px ${isActive ? "#e11d48" : isDone ? "#10b981" : isError ? "#ef4444" : "transparent"})` : "none",
              }}
            />
          </svg>
        </div>
      )}
    </div>
  );
}

function Connector({ active, done }: { active?: boolean; done?: boolean }) {
  const activeColor = "#10b981"; // Vibrant Green for travelled paths
  return (
    <div className="pipeline-connector" style={{ width: 24, height: 48, display: "flex", justifyContent: "center", alignItems: "center", position: "relative" }}>
      <svg width="24" height="48" viewBox="0 0 24 48" style={{ overflow: "visible" }}>
        <line x1="12" y1="3" x2="12" y2="45" stroke="#e2e8f0" strokeWidth="6" strokeLinecap="round" />
        <line x1="12" y1="2" x2="12" y2="46" stroke="#cbd5e1" strokeWidth="4" strokeLinecap="round" />
        {active && (
          <line
            x1="12"
            y1="2"
            x2="12"
            y2="46"
            stroke={activeColor}
            strokeWidth="2"
            strokeLinecap="round"
            style={{
              filter: `drop-shadow(0 0 4px ${activeColor})`,
              strokeDasharray: "8 8",
              animation: "flowPipe 1s linear infinite"
            }}
          />
        )}
        {done && !active && (
          <line x1="12" y1="2" x2="12" y2="46" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
        )}
      </svg>
    </div>
  );
}

function phaseLabel(phase: string): string {
  const map: Record<string, string> = {
    idle: "Idle",
    validating: "Validating…",
    planning: "Planning…",
    discovering: "Discovering…",
    compiling: "Compiling…",
    clarifying: "Needs Clarification",
    completed: "Complete",
    error: "Error",
  };
  return map[phase] ?? phase;
}

function phaseIsActive(phase: string): boolean {
  return ["validating", "planning", "discovering", "compiling"].includes(phase);
}

function CentralLogBox({ activeApiCall, logs, phase }: { activeApiCall: ApiCallEvent | null | undefined, logs?: LogMessage[], phase: string }) {
  const isCompleted = phase === "completed";
  const lastLog = logs?.filter(l => l.type === 'log').slice(-1)[0]?.text || "Waiting for activity...";

  if (isCompleted) {
    return (
      <div style={{
        width: "100%", height: "100%",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        background: "#ffffff", borderRadius: "16px",
        boxShadow: "0 8px 30px rgba(0,0,0,0.06), 0 2px 10px rgba(0,0,0,0.02)",
        border: "1px solid rgba(16,185,129,0.2)",
        padding: "16px",
        textAlign: "center",
        animation: "fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards"
      }}>
        <div style={{
          width: 44, height: 44, borderRadius: "50%",
          background: "rgba(16,185,129,0.1)",
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: 8,
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#10b981", marginBottom: 4 }}>
          Completed
        </div>
        <div style={{
          fontSize: 11, color: "rgba(55,53,47,0.6)",
          maxWidth: "100%", whiteSpace: "nowrap",
          overflow: "hidden", textOverflow: "ellipsis",
          fontFamily: "SFMono-Regular, Consolas, monospace"
        }}>
          {lastLog.includes("compiled") ? lastLog : "Itinerary successfully compiled!"}
        </div>
      </div>
    );
  }

  if (!activeApiCall) return null;

  let Logo = UnknownApiIcon;
  let toolName = activeApiCall.tool;
  if (toolName === "Google Flights") Logo = GoogleFlightsIcon;
  else if (toolName === "Skyscanner") Logo = SkyscannerIcon;
  else if (toolName === "Google Maps") Logo = GoogleMapsIcon;
  else if (toolName === "Booking.com") Logo = BookingComIcon;
  else if (toolName === "Google Places") Logo = GooglePlacesIcon;
  else if (toolName === "TripAdvisor") Logo = TripadvisorIcon;
  else if (toolName === "SerpAPI") Logo = SerpApiIcon;
  else if (toolName === "Ticketmaster") Logo = TicketmasterIcon;

  return (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      background: "#ffffff", borderRadius: "16px",
      boxShadow: "0 8px 30px rgba(0,0,0,0.06), 0 2px 10px rgba(0,0,0,0.02)",
      border: "1px solid rgba(55,53,47,0.08)",
      padding: "16px",
      textAlign: "center",
      animation: "fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards"
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: "50%",
        background: "rgba(55,53,47,0.04)",
        display: "flex", alignItems: "center", justifyContent: "center",
        marginBottom: 8
      }}>
        <Logo />
      </div>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#37352f", marginBottom: 4 }}>
        {toolName}
      </div>
      <div style={{
        fontSize: 11, color: "rgba(55,53,47,0.6)",
        maxWidth: "100%", whiteSpace: "nowrap",
        overflow: "hidden", textOverflow: "ellipsis",
        fontFamily: "SFMono-Regular, Consolas, monospace"
      }}>
        {lastLog}
      </div>
    </div>
  );
}

/* ─── Main Component ─────────────────────────────────────────────────────── */

export default function PipelinePanel({ activeNode, phase, candidates, logs, activeApiCall }: PipelinePanelProps) {
  const [visitedNodes, setVisitedNodes] = React.useState<Set<string>>(new Set());
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [scale, setScale] = React.useState(1);

  React.useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        const minWidthNeeded = 720;
        if (width < minWidthNeeded) {
          setScale(Math.max(0.45, width / minWidthNeeded));
        } else {
          setScale(1);
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  React.useEffect(() => {
    if (activeNode) {
      setVisitedNodes(prev => {
        const next = new Set(prev);
        next.add(activeNode);
        return next;
      });
    }
  }, [activeNode]);

  React.useEffect(() => {
    if (phase === "idle") {
      setVisitedNodes(new Set());
    }
  }, [phase]);

  const ns = (id: string): NodeState => {
    if (activeNode === id) return "active";
    if (phase === "error" && activeNode === id) return "error";
    if (phase === "completed") return "done";
    
    // If this node has been visited in the past and is not active, it is done
    if (visitedNodes.has(id)) {
      return "done";
    }

    // Fallback: gatekeeper, planner, and captain are also marked done if we have advanced beyond them
    const ORDER = ["gatekeeper", "planner", "captain", "travel", "stay", "food", "sightseeing"];
    const activeIdx = ORDER.indexOf(activeNode ?? "");
    const thisIdx = ORDER.indexOf(id);
    if (activeIdx > thisIdx && thisIdx !== -1) {
      return "done";
    }

    return "idle";
  };

  const connectorDone = (aboveId: string) => ns(aboveId) === "done";
  const connectorActive = (aboveId: string) => ns(aboveId) === "active";

  const wireColor = (fromId: string, toId: string) => {
    const toState = ns(toId);

    // Special case for return path: sightseeing -> captain
    if (fromId === "sightseeing" && toId === "captain") {
      const allSubagentsDone = ns("travel") === "done" && ns("stay") === "done" && ns("food") === "done" && ns("sightseeing") === "done";
      const isCompilingOrDone = phase === "compiling" || phase === "completed";
      if (allSubagentsDone && (ns("captain") === "active" || isCompilingOrDone)) {
        return "#10b981"; // Vibrant Green
      }
      return "#cbd5e1"; // Base grey
    }

    // For any other connection, it should only be green if the target node is active or done
    if (toState === "active" || toState === "done") {
      return "#10b981"; // Vibrant Green
    }
    return "#cbd5e1"; // Base grey
  };

  const isFlowing = (toId: string) => {
    // Special case for return path: sightseeing -> captain
    if (toId === "captain_final") {
      const allSubagentsDone = ns("travel") === "done" && ns("stay") === "done" && ns("food") === "done" && ns("sightseeing") === "done";
      return allSubagentsDone && ns("captain") === "active";
    }
    return ns(toId) === "active";
  };

  const FlowingWire = ({ d, targetNode }: { d: string, targetNode: string }) => {
    const active = isFlowing(targetNode);
    if (!active) return null;
    return (
      <path
        d={d} fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 4px #10b981)`, strokeDasharray: "6 12", animation: "flowPipe 1s linear infinite" }}
      />
    );
  };

  return (
    <div className="pipeline-panel-root" ref={containerRef}>
      <div className="pipeline-grid-bg" />



      <div className="pipeline-body" style={{ overflow: "hidden" }}>
        <div
          className="pipeline-chain"
          style={{
            transform: `scale(${scale})`,
            transformOrigin: "center center",
            transition: "transform 0.1s ease-out",
          }}
        >
          {/* Gatekeeper */}
          <NodeCard node={MAIN_NODES[0]} state={ns("gatekeeper")} size="large" />
          <Connector active={connectorActive("gatekeeper")} done={connectorDone("gatekeeper")} />

          {/* Planner */}
          <NodeCard node={MAIN_NODES[1]} state={ns("planner")} size="large" />
          <Connector active={connectorActive("planner")} done={connectorDone("planner")} />

          {/* Captain */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <NodeCard node={MAIN_NODES[2]} state={ns("captain")} size="large" />
          </div>

          {/* The Loop Container: Perfectly symmetric dimensions */}
          <div style={{ position: "relative", width: 680, height: 280, marginTop: 40, marginBottom: 20 }}>
            {/* SVG Wires Layer (zIndex 0 to run behind NodeCards) */}
            <svg width="100%" height="100%" style={{ position: "absolute", top: 0, left: 0, zIndex: 0, overflow: "visible" }}>
              {/* Captain (center: 340, -72, bottom: 340, -40) -> Travel (center: 90, 32) */}
              <path d="M 340 -44 L 340 -15 C 340 5, 90 10, 90 32" fill="none" stroke={wireColor("captain", "travel")} strokeWidth="2.5" strokeLinecap="round" />
              <FlowingWire d="M 340 -44 L 340 -15 C 340 5, 90 10, 90 32" targetNode="travel" />

              {/* Travel (center: 90, 32) -> Stay (center: 90, 248) */}
              <path d="M 90 32 L 90 248" fill="none" stroke={wireColor("travel", "stay")} strokeWidth="2.5" strokeLinecap="round" />
              <FlowingWire d="M 90 32 L 90 248" targetNode="stay" />

              {/* Stay (center: 90, 248) -> Food (center: 590, 248) */}
              <path d="M 90 248 L 590 248" fill="none" stroke={wireColor("stay", "food")} strokeWidth="2.5" strokeLinecap="round" />
              <FlowingWire d="M 90 248 L 590 248" targetNode="food" />

              {/* Food (center: 590, 248) -> Sightseeing (center: 590, 32) */}
              <path d="M 590 248 L 590 32" fill="none" stroke={wireColor("food", "sightseeing")} strokeWidth="2.5" strokeLinecap="round" />
              <FlowingWire d="M 590 248 L 590 32" targetNode="sightseeing" />

              {/* Sightseeing (center: 590, 32) -> Captain (center: 340, -72, bottom: 340, -40) */}
              <path d="M 590 32 C 590 10, 340 5, 340 -15 L 340 -44" fill="none" stroke={wireColor("sightseeing", "captain")} strokeWidth="2.5" strokeLinecap="round" />
              <FlowingWire d="M 590 32 C 590 10, 340 5, 340 -15 L 340 -44" targetNode="captain_final" />
            </svg>

            {/* Central Log Box */}
            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: 280, height: 120, zIndex: 10 }}>
              <CentralLogBox activeApiCall={activeApiCall} logs={logs} phase={phase} />
            </div>

            {/* Sub-agents placed absolutely with zIndex 10 so wires run cleanly behind them */}
            <div style={{ position: "absolute", top: 0, left: 0, zIndex: 10 }}>
              <NodeCard node={SUB_NODES[0]} state={ns("travel")} />
            </div>
            <div style={{ position: "absolute", bottom: 0, left: 0, zIndex: 10 }}>
              <NodeCard node={SUB_NODES[1]} state={ns("stay")} />
            </div>
            <div style={{ position: "absolute", bottom: 0, right: 0, zIndex: 10 }}>
              <NodeCard node={SUB_NODES[2]} state={ns("food")} />
            </div>
            <div style={{ position: "absolute", top: 0, right: 0, zIndex: 10 }}>
              <NodeCard node={SUB_NODES[3]} state={ns("sightseeing")} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
