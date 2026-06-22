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
  Database,
  Globe,
  Search,
} from "lucide-react";

/* ─── Types ─────────────────────────────────────────────────────────────── */

export interface PipelinePanelProps {
  activeNode: string | null;
  phase: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  candidates: Record<string, any[]>;
}

type NodeState = "idle" | "active" | "done" | "error";

/* ─── Brand SVG Icons ────────────────────────────────────────────────────── */

const GoogleFlightsIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M21 16V14L13 9V3.5C13 2.67 12.33 2 11.5 2C10.67 2 10 2.67 10 3.5V9L2 14V16L10 13.5V19L8 20.5V22L11.5 21L15 22V20.5L13 19V13.5L21 16Z" fill="#1A73E8"/>
  </svg>
);

const GoogleMapsIcon = () => (
  <svg width="13" height="13" viewBox="0 0 34 50" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M17 0C7.6 0 0 7.6 0 17C0 29.8 17 50 17 50C17 50 34 29.8 34 17C34 7.6 26.4 0 17 0Z" fill="#34A853"/>
    <path d="M17 0C7.6 0 0 7.6 0 17C0 20.9 1.4 24.6 3.6 27.5L17 11.2V0Z" fill="#4285F4"/>
    <path d="M17 11.2L3.6 27.5C6.5 31.3 11.2 35.8 17 42.5V11.2Z" fill="#EA4335"/>
    <path d="M17 11.2V42.5C22.8 35.8 27.5 31.3 30.4 27.5L17 11.2Z" fill="#FBBC05"/>
    <circle cx="17" cy="17" r="6" fill="#1A73E8"/>
  </svg>
);

const BookingComIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#003580"/>
    <path d="M5 4H11.5C13.9853 4 16 6.01472 16 8.5C16 10.0827 15.1843 11.4746 13.9472 12.2682C15.1764 12.9649 16 14.2828 16 15.8C16 18.2853 13.9853 20.3 11.5 20.3H5V4ZM8.2V9.8H11.3C12.018 9.8 12.6 9.21797 12.6 8.5C12.6 7.78203 12.018 7.2 11.3 7.2H8.2V9.8ZM8.2 12.5V17.1H11.3C12.018 17.1 12.6 16.518 12.6 15.8C12.6 15.082 12.018 14.5 11.3 14.5H8.2V12.5Z" fill="white"/>
  </svg>
);

const GooglePlacesIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
  </svg>
);

const TripadvisorIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM8.5 15C7.67 15 7 14.33 7 13.5C7 12.67 7.67 12 8.5 12C9.33 12 10 12.67 10 13.5C10 14.33 9.33 15 8.5 15ZM12 18.5C10.5 18.5 9 17.5 9 16.5H15C15 17.5 13.5 18.5 12 18.5ZM15.5 15C14.67 15 14 14.33 14 13.5C14 12.67 14.67 12 15.5 12C16.33 12 17 12.67 17 13.5C17 14.33 16.33 15 15.5 15Z" fill="#34E0A1" />
    <path d="M10 13.5H14" stroke="#000000" strokeWidth="1.5" />
    <path d="M12 14.5L11.5 16H12.5L12 14.5Z" fill="#000000" />
  </svg>
);

const SerpApiIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="11" cy="11" r="6" stroke="#4285F4" strokeWidth="2.5"/>
    <line x1="16" y1="16" x2="22" y2="22" stroke="#EA4335" strokeWidth="3" strokeLinecap="round"/>
    <circle cx="11" cy="11" r="2.5" fill="#FBBC05"/>
  </svg>
);

const TicketmasterIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#006CFF"/>
    <path d="M8 8V11H10V17H13V11H16V8H13V6.2C13 5.7 13.4 5.3 13.9 5.3H16V2.5H13.5C11.2 2.5 9.5 3.9 9.5 6.2V8H8Z" fill="white"/>
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
    candidateKey: "transit",
    icon: <PlaneTakeoff size={16} strokeWidth={2.2} />,
    accent: "#2563eb",
    accentBg: "rgba(37,99,235,0.07)",
    accentBorder: "rgba(37,99,235,0.18)",
    tools: [
      { name: "Google Flights", icon: <GoogleFlightsIcon /> },
      { name: "Google Maps", icon: <GoogleMapsIcon /> },
    ],
  },
  {
    id: "stay",
    name: "Lodging Agent",
    role: "Accommodation",
    candidateKey: "accommodation",
    icon: <Hotel size={16} strokeWidth={2.2} />,
    accent: "#7c3aed",
    accentBg: "rgba(124,58,237,0.07)",
    accentBorder: "rgba(124,58,237,0.18)",
    tools: [
      { name: "Booking.com", icon: <BookingComIcon /> },
    ],
  },
  {
    id: "food",
    name: "Culinary Agent",
    role: "Dining",
    candidateKey: "food",
    icon: <UtensilsCrossed size={16} strokeWidth={2.2} />,
    accent: "#ea580c",
    accentBg: "rgba(234,88,12,0.07)",
    accentBorder: "rgba(234,88,12,0.18)",
    tools: [
      { name: "Google Places", icon: <GooglePlacesIcon /> },
      { name: "TripAdvisor", icon: <TripadvisorIcon /> },
    ],
  },
  {
    id: "sightseeing",
    name: "Experience Agent",
    role: "Activities",
    candidateKey: "activities",
    icon: <MapPin size={16} strokeWidth={2.2} />,
    accent: "#059669",
    accentBg: "rgba(5,150,105,0.07)",
    accentBorder: "rgba(5,150,105,0.18)",
    tools: [
      { name: "SerpAPI", icon: <SerpApiIcon /> },
      { name: "Ticketmaster", icon: <TicketmasterIcon /> },
    ],
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

/* ─── Node Card ──────────────────────────────────────────────────────────── */

function NodeCard({
  node,
  state,
  size = "normal",
  candidateCount,
}: {
  node: typeof MAIN_NODES[0] | Omit<typeof SUB_NODES[0], "tools">;
  state: NodeState;
  size?: "large" | "normal";
  candidateCount?: number;
}) {
  const isActive = state === "active";
  const isDone = state === "done";
  const isError = state === "error";

  const borderColor =
    isActive ? node.accent :
    isDone ? "rgba(55,53,47,0.14)" :
    isError ? "#e03e3e" :
    "rgba(55,53,47,0.10)";

  const bgColor =
    isActive ? node.accentBg :
    isDone ? "#fafaf9" :
    "#ffffff";

  const shadowStyle =
    isActive
      ? `0 0 16px ${node.accent}60, 0 0 0 1.5px ${node.accent}`
      : "0 1px 3px rgba(15,15,15,0.05)";

  return (
    <div
      id={`${node.id}-agent-card`}
      className={`pipeline-node-card ${isActive ? "state-active" : isDone ? "state-done" : ""}`}
      style={{
        border: `1.5px solid ${borderColor}`,
        background: bgColor,
        boxShadow: shadowStyle,
        width: "100%",
        minWidth: size === "large" ? 220 : 130,
        maxWidth: size === "large" ? 220 : 180,
        height: 64,
        display: "flex",
        alignItems: "center",
        transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)",
        position: "relative",
        // CSS custom properties for border pulse
        "--active-color": node.accent,
        "--active-color-alpha": `${node.accent}20`,
        "--active-color-alpha-bright": `${node.accent}60`,
      } as React.CSSProperties}
    >
      {/* Active pulse ring */}
      {isActive && (
        <div
          className="pipeline-node-pulse"
          style={{ borderColor: node.accent }}
        />
      )}

      <div className="pipeline-node-inner">
        <div
          className="pipeline-node-icon"
          style={{
            background: node.accentBg,
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

        {/* Status indicator */}
        <div className="pipeline-node-status">
          {isActive && (
            <span className="pipeline-status-dot" style={{ background: node.accent }} />
          )}
          {isDone && (
            <span className="pipeline-status-check">✓</span>
          )}
          {candidateCount !== undefined && candidateCount > 0 && (
            <span className="pipeline-candidate-count" style={{ background: node.accentBg, color: node.accent, borderColor: node.accentBorder }}>
              {candidateCount}
            </span>
          )}
        </div>
      </div>

      {/* Gatekeeper socket (connected to the plug wire) */}
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
            zIndex: 10,
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
            {/* Outer metallic bezel */}
            <circle cx="7" cy="7" r="6.5" fill="url(#gk-socket-metal)" stroke="#1e293b" strokeWidth="0.5" />
            
            {/* Dark inner socket core */}
            <circle cx="7" cy="7" r="4.5" fill="#0f172a" stroke="#334155" strokeWidth="0.5" />
            
            {/* Central contact pin (status-colored glowing LED) */}
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

/* ─── Connector Line ─────────────────────────────────────────────────────── */

function Connector({ active, done }: { active?: boolean; done?: boolean }) {
  const activeColor = "#2383e2"; // Active charge color (blue)
  return (
    <div className="pipeline-connector" style={{ width: 24, height: 48, display: "flex", justifyContent: "center", alignItems: "center", position: "relative" }}>
      <svg width="24" height="48" viewBox="0 0 24 48" style={{ overflow: "visible" }}>
        {/* Outer thick pipe */}
        <line x1="12" y1="0" x2="12" y2="48" stroke="#e2e8f0" strokeWidth="6" strokeLinecap="round" />
        <line x1="12" y1="0" x2="12" y2="48" stroke="#cbd5e1" strokeWidth="4" strokeLinecap="round" />
        
        {/* Active glowing inner core */}
        {active && (
          <line
            x1="12"
            y1="0"
            x2="12"
            y2="48"
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
        {/* Done solid core */}
        {done && !active && (
          <line x1="12" y1="0" x2="12" y2="48" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
        )}
      </svg>
    </div>
  );
}

/* ─── Phase Label ────────────────────────────────────────────────────────── */

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

/* ─── Main Component ─────────────────────────────────────────────────────── */

export default function PipelinePanel({ activeNode, phase, candidates }: PipelinePanelProps) {
  const ns = (id: string) => getNodeState(id, activeNode, phase);

  const captainDone = ns("captain") === "done";
  const captainActive = ns("captain") === "active";

  const connectorDone = (aboveId: string) => ns(aboveId) === "done";
  const connectorActive = (aboveId: string) => ns(aboveId) === "active";

  return (
    <div className="pipeline-panel-root">
      {/* Grid background overlay */}
      <div className="pipeline-grid-bg" />

      {/* Header */}
      <div className="pipeline-header">
        <div className="pipeline-header-left">
          <div className="pipeline-header-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div>
            <span className="pipeline-header-title">NomadGraph</span>
            <span className="pipeline-header-sub"> Pipeline</span>
          </div>
        </div>
        <div className={`pipeline-phase-badge ${phaseIsActive(phase) ? "pipeline-phase-badge--active" : phase === "completed" ? "pipeline-phase-badge--done" : phase === "error" ? "pipeline-phase-badge--error" : ""}`}>
          {phaseIsActive(phase) && <span className="pipeline-phase-dot" />}
          {phaseLabel(phase)}
        </div>
      </div>

      {/* Scrollable pipeline body */}
      <div className="pipeline-body">
        {/* ── Main Pipeline Chain ── */}
        <div className="pipeline-chain">

          {/* Gatekeeper */}
          <NodeCard node={MAIN_NODES[0]} state={ns("gatekeeper")} size="large" />
          <Connector active={connectorActive("gatekeeper")} done={connectorDone("gatekeeper")} />

          {/* Planner */}
          <NodeCard node={MAIN_NODES[1]} state={ns("planner")} size="large" />
          <Connector active={connectorActive("planner")} done={connectorDone("planner")} />

          {/* Captain */}
          <NodeCard node={MAIN_NODES[2]} state={ns("captain")} size="large" />

          {/* Curvy wires from Captain to Subagents */}
          <div className="pipeline-dispatcher-wires" style={{ width: "100%", maxWidth: 860, height: 48, position: "relative", zIndex: 1 }}>
            <svg width="100%" height="48" viewBox="0 0 800 48" style={{ overflow: "visible" }}>
              {SUB_NODES.map((sub, idx) => {
                const subState = ns(sub.id);
                const isActiveNode = subState === "active";
                const isDoneNode = subState === "done";
                const isFlowing = captainActive || isActiveNode;
                
                const xEnd = 100 + idx * 200;
                const pathD = `M 400 0 C 400 24, ${xEnd} 12, ${xEnd} 48`;
                
                return (
                  <g key={sub.id}>
                    {/* Base Casing Wire */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke="#cbd5e1"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />
                    {/* Glowing Active Inner Core */}
                    {isFlowing && (
                      <path
                        d={pathD}
                        fill="none"
                        stroke={sub.accent}
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        style={{
                          filter: `drop-shadow(0 0 3px ${sub.accent})`,
                          strokeDasharray: "6 12",
                          animation: "flowPipe 1s linear infinite"
                        }}
                      />
                    )}
                    {/* Done Static Color */}
                    {isDoneNode && !isActiveNode && (
                      <path
                        d={pathD}
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        style={{ opacity: 0.7 }}
                      />
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Sub-agents row */}
          <div className="pipeline-subagents-row">
            {SUB_NODES.map((sub, i) => {
              const subState = ns(sub.id);
              const count = candidates[sub.candidateKey]?.length ?? 0;
              const isActiveNode = subState === "active";

              return (
                <div key={sub.id} className="pipeline-subagent-col">
                  <NodeCard
                    node={sub}
                    state={subState}
                    size="normal"
                    candidateCount={count}
                  />

                  {/* API Tools Chain */}
                  <div className="pipeline-tools-col">
                    {sub.tools.map((tool, idx) => (
                      <React.Fragment key={idx}>
                        <div
                          className="pipeline-tool-drop"
                          style={{
                            background: isActiveNode ? "rgba(35,131,226,0.25)" : "rgba(55,53,47,0.10)",
                          }}
                        />
                        <div className="pipeline-tool-chip">
                          <span className="pipeline-tool-icon">
                            {tool.icon}
                          </span>
                          {tool.name}
                        </div>
                      </React.Fragment>
                    ))}
                  </div>

                </div>
              );
            })}
          </div>

        </div>
      </div>
    </div>
  );
}
