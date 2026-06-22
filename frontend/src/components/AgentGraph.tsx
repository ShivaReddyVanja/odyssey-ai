"use client";

import React, { useEffect, useRef, useState } from "react";

/* ─────────────────────────────────────────────────────────────────────────────
   Types
───────────────────────────────────────────────────────────────────────────── */

type NodeState = "idle" | "active" | "done" | "error";

interface Packet {
  id: string;
  pathKey: string;
  color: string;
  dur: number;
  delay?: number;
}

export interface AgentGraphProps {
  activeNode: string | null;
  lastDiscovery: { category: string; timestamp: number } | null;
  phase: string;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Layout — viewBox 800 × 500
   Pipeline: Entry (right) → Gatekeeper (right) → Planner (center) → Captain
             → fan-out to 4 subagents → API circles
───────────────────────────────────────────────────────────────────────────── */

const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

/** Gatekeeper — right side, near the chat panel border */
const GK = { cx: 638, cy: 68, x: 567, y: 45, w: 142, h: 46, rx: 10, label: "Gatekeeper", role: "Validation" };

/** Planner — centered */
const PL = { cx: 390, cy: 185, rx: 100, ry: 34, label: "Planner", role: "Routing" };

/** Captain — centered, below Planner */
const CP = { cx: 390, cy: 295, x: 306, y: 270, w: 168, h: 50, rx: 14, label: "Captain", role: "Orchestrator" };

const BAR_Y = 368;

const SUBAGENTS = [
  { id: "travel",      label: "Travel",  role: "Transit",     cx: 120, cy: 430, x: 65,  y: 408, w: 110, h: 44, rx: 12, apiLabel: "Routes", apiCx: 120, apiCy: 492 },
  { id: "stay",        label: "Stay",    role: "Stays",       cx: 283, cy: 430, x: 228, y: 408, w: 110, h: 44, rx: 12, apiLabel: "Hotels", apiCx: 283, apiCy: 492 },
  { id: "food",        label: "Food",    role: "Dining",      cx: 497, cy: 430, x: 442, y: 408, w: 110, h: 44, rx: 12, apiLabel: "Places", apiCx: 497, apiCy: 492 },
  { id: "sightseeing", label: "Sights",  role: "Activities",  cx: 660, cy: 430, x: 605, y: 408, w: 110, h: 44, rx: 12, apiLabel: "Places", apiCx: 660, apiCy: 492 },
];

/** Edge path definitions — used for both SVG rendering and animateMotion */
const EDGE_PATHS: Record<string, string> = {
  // Entry: from right edge of SVG into Gatekeeper right face
  entry:              `M 800,68 L 710,68`,
  // Gatekeeper bottom → Planner top (smooth diagonal curve)
  "gk-planner":       `M 638,91 C 638,148 390,128 390,151`,
  // Planner bottom → Captain top (vertical)
  "planner-captain":  `M 390,219 L 390,270`,
  // Captain bottom → bar → subagent tops (L-shaped routes)
  "captain-travel":   `M 390,320 L 390,${BAR_Y} L 120,${BAR_Y} L 120,408`,
  "captain-stay":     `M 390,320 L 390,${BAR_Y} L 283,${BAR_Y} L 283,408`,
  "captain-food":     `M 390,320 L 390,${BAR_Y} L 497,${BAR_Y} L 497,408`,
  "captain-sights":   `M 390,320 L 390,${BAR_Y} L 660,${BAR_Y} L 660,408`,
  // Subagent bottom → API circle top
  "travel-api":       `M 120,452 L 120,468`,
  "stay-api":         `M 283,452 L 283,468`,
  "food-api":         `M 497,452 L 497,468`,
  "sights-api":       `M 660,452 L 660,468`,
};

/** Which edge fires when a given node first becomes active */
const NODE_INCOMING_EDGE: Record<string, string> = {
  gatekeeper:  "entry",
  planner:     "gk-planner",
  captain:     "planner-captain",
  travel:      "captain-travel",
  stay:        "captain-stay",
  food:        "captain-food",
  sightseeing: "captain-sights",
};

const CATEGORY_TO_SUBAGENT: Record<string, string> = {
  transit:       "travel",
  accommodation: "stay",
  food:          "food",
  activities:    "sightseeing",
};

/* ─────────────────────────────────────────────────────────────────────────────
   Component
───────────────────────────────────────────────────────────────────────────── */

export default function AgentGraph({ activeNode, lastDiscovery, phase }: AgentGraphProps) {
  /** Per-node animation state */
  const [nodeStates, setNodeStates]   = useState<Record<string, NodeState>>({});
  /** Counter-based keys force edge paths to remount, replaying CSS animations */
  const [edgeKeys, setEdgeKeys]       = useState<Record<string, number>>({});
  /** Edges that have already completed (stay faintly blue) */
  const [doneEdges, setDoneEdges]     = useState<Set<string>>(new Set());
  /** Active flowing edges (bright blue) */
  const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set());
  /** Animated data packets travelling along edges */
  const [packets, setPackets]         = useState<Packet[]>([]);

  const prevNodeRef = useRef<string | null>(null);

  /* ── Reset everything when planning resets ── */
  useEffect(() => {
    if (phase === "idle") {
      setNodeStates({});
      setEdgeKeys({});
      setDoneEdges(new Set());
      setActiveEdges(new Set());
      setPackets([]);
      prevNodeRef.current = null;
    }
    if (phase === "completed") {
      const all = ["gatekeeper", "planner", "captain", "travel", "stay", "food", "sightseeing"];
      setNodeStates(Object.fromEntries(all.map(n => [n, "done" as NodeState])));
      setDoneEdges(new Set([
        "entry", "gk-planner", "planner-captain",
        "captain-travel", "captain-stay", "captain-food", "captain-sights",
        "travel-api", "stay-api", "food-api", "sights-api"
      ]));
    }
    if (phase === "error") {
      if (prevNodeRef.current) {
        setNodeStates(p => ({ ...p, [prevNodeRef.current!]: "error" }));
      }
    }
  }, [phase]);

  /* ── React to activeNode transitions ── */
  useEffect(() => {
    const prev = prevNodeRef.current;
    prevNodeRef.current = activeNode;

    if (!activeNode) return;

    // Mark current as active, previous as done
    setNodeStates(p => {
      const next = { ...p, [activeNode]: "active" as NodeState };
      if (prev) next[prev] = "done";
      return next;
    });

    // Animate the incoming edge
    const edgeKey = NODE_INCOMING_EDGE[activeNode];
    if (!edgeKey) return;

    // Increment key to force SVG path remount → CSS animation replays
    setEdgeKeys(p => ({ ...p, [edgeKey]: (p[edgeKey] ?? 0) + 1 }));
    setActiveEdges(p => new Set([...p, edgeKey]));

    // Spawn a data packet along this edge
    const isSubAgent = ["travel", "stay", "food", "sightseeing"].includes(activeNode);
    const dur = edgeKey === "entry" ? 0.65 : edgeKey.startsWith("captain-") ? 1.0 : 0.55;
    const pkt: Packet = {
      id: `pkt-${Date.now()}-${Math.random()}`,
      pathKey: edgeKey,
      color: isSubAgent ? "#2383e2" : "#37352f",  // packet color (small dot, fine to be dark)
      dur,
    };
    setPackets(p => [...p, pkt]);

    const ms = (dur + 0.15) * 1000;
    const cleanup = setTimeout(() => {
      setActiveEdges(p => { const s = new Set(p); s.delete(edgeKey); return s; });
      setDoneEdges(p => new Set([...p, edgeKey]));
      setPackets(p => p.filter(pk => pk.id !== pkt.id));
    }, ms);

    return () => clearTimeout(cleanup);
  }, [activeNode]);

  /* ── Discovery event: animate API edge when data comes in ── */
  useEffect(() => {
    if (!lastDiscovery) return;
    const sub = SUBAGENTS.find(s => s.id === CATEGORY_TO_SUBAGENT[lastDiscovery.category]);
    if (!sub) return;

    const apiEdge = `${sub.id === "sightseeing" ? "sights" : sub.id}-api`;
    const pkt: Packet = {
      id: `api-${lastDiscovery.timestamp}-${Math.random()}`,
      pathKey: apiEdge,
      color: "#0f7b6c",
      dur: 0.5,
    };
    setPackets(p => [...p, pkt]);
    const t = setTimeout(() => setPackets(p => p.filter(pk => pk.id !== pkt.id)), 700);
    return () => clearTimeout(t);
  }, [lastDiscovery]);

  /* ─── Render helpers ───────────────────────────────────────────────────── */

  const ns = (id: string) => nodeStates[id] ?? "idle";
  const isActive = (id: string) => ns(id) === "active";
  const isDone   = (id: string) => ns(id) === "done";
  const isError  = (id: string) => ns(id) === "error";

  /*
   * ── Node color philosophy ──────────────────────────────────────────────
   * Nodes are ALWAYS light/white. State is communicated via border color
   * and label color, never by filling the shape solid black.
   * ──────────────────────────────────────────────────────────────────────
   */

  /** Fill for main pipeline nodes — always near-white */
  const mainFill = (id: string): string => {
    if (isActive(id)) return "rgba(55,53,47,0.05)";
    if (isDone(id))   return "rgba(55,53,47,0.02)";
    if (isError(id))  return "rgba(224,62,62,0.04)";
    return "#ffffff";
  };
  /** Border for main pipeline nodes */
  const mainStroke = (id: string): string => {
    if (isActive(id)) return "#37352f";
    if (isDone(id))   return "rgba(55,53,47,0.22)";
    if (isError(id))  return "rgba(224,62,62,0.55)";
    return "rgba(55,53,47,0.16)";
  };
  const mainStrokeWidth = (id: string): number => isActive(id) ? 2 : 1.4;
  /** Label text for main pipeline nodes */
  const mainTextFill = (id: string): string => {
    if (isActive(id)) return "#37352f";
    if (isDone(id))   return "rgba(55,53,47,0.40)";
    return "#37352f";
  };

  /** Fill for subagent nodes — always near-white */
  const subFill = (id: string): string => {
    if (isActive(id)) return "rgba(35,131,226,0.06)";
    if (isDone(id))   return "rgba(35,131,226,0.02)";
    return "#ffffff";
  };
  /** Border for subagent nodes */
  const subStroke = (id: string): string => {
    if (isActive(id)) return "#2383e2";
    if (isDone(id))   return "rgba(35,131,226,0.28)";
    return "rgba(55,53,47,0.14)";
  };
  const subStrokeWidth = (id: string): number => isActive(id) ? 2 : 1.3;
  /** Label text for subagent nodes */
  const subTextFill = (id: string): string => {
    if (isActive(id)) return "#2383e2";
    if (isDone(id))   return "rgba(55,53,47,0.38)";
    return "#37352f";
  };

  /** Edge stroke based on state */
  const edgeStroke = (key: string): string => {
    if (activeEdges.has(key)) return "#2383e2";
    if (doneEdges.has(key))   return "rgba(35,131,226,0.25)";
    return "rgba(55,53,47,0.09)";
  };
  const edgeWidth = (key: string): number => {
    if (activeEdges.has(key)) return 1.8;
    if (doneEdges.has(key))   return 1.2;
    return 1.0;
  };
  const markerId = (key: string): string => {
    if (activeEdges.has(key)) return "url(#arr-blue)";
    if (doneEdges.has(key))   return "url(#arr-faint)";
    return "url(#arr)";
  };

  /** Transition style shared by all shape elements */
  const shapeStyle: React.CSSProperties = {
    transition: "fill 0.35s ease, stroke 0.35s ease, stroke-width 0.25s ease",
  };

  /** Phase label shown in overlay */
  const phaseLabel = (): string => {
    const map: Record<string, string> = {
      idle:       "Waiting for input",
      validating: "Validating request…",
      planning:   "Planning routes…",
      discovering:"Discovering options…",
      compiling:  "Compiling itinerary…",
      clarifying: "Awaiting clarification…",
      completed:  "Itinerary complete",
      error:      "An error occurred",
    };
    return map[phase] ?? phase;
  };

  /* ─── Edge rendering helper: returns the SVG path element for an edge ─── */
  const renderEdge = (key: string, opts?: { marker?: boolean; strokeCap?: string }) => {
    const flowing = activeEdges.has(key);
    const done    = doneEdges.has(key);
    const d       = EDGE_PATHS[key];
    if (!d) return null;
    return (
      <path
        key={`${key}-${edgeKeys[key] ?? 0}`}
        d={d}
        fill="none"
        pathLength="1"
        stroke={edgeStroke(key)}
        strokeWidth={edgeWidth(key)}
        strokeLinecap="round"
        markerEnd={opts?.marker !== false ? markerId(key) : undefined}
        strokeDasharray={flowing ? "1" : undefined}
        strokeDashoffset={flowing ? 1 : undefined}
        style={{
          transition: "stroke 0.4s ease, stroke-width 0.3s ease",
          animation: flowing ? "edgeDraw 0.6s cubic-bezier(0.4,0,0.2,1) forwards" : undefined,
        }}
      />
    );
  };

  return (
    <div className="agent-graph-root">

      {/* ── Overlay label top-left ── */}
      <div className="agent-graph-overlay">
        <div className="agent-graph-title">Agent Pipeline</div>
        <div className="agent-graph-subtitle">{phaseLabel()}</div>
      </div>

      <svg
        className="agent-graph-svg"
        viewBox="0 0 800 516"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* ── Subtle glow filter — applied to active nodes via <use> trick ── */}
          <filter id="glow-main" x="-40%" y="-40%" width="180%" height="180%" colorInterpolationFilters="sRGB">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
            <feColorMatrix in="blur" type="matrix"
              values="0 0 0 0 0.21   0 0 0 0 0.21   0 0 0 0 0.18   0 0 0 0.6 0"
              result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-blue" x="-40%" y="-40%" width="180%" height="180%" colorInterpolationFilters="sRGB">
            <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
            <feColorMatrix in="blur" type="matrix"
              values="0 0 0 0 0.14   0 0 0 0 0.51   0 0 0 0 0.89   0 0 0 0.55 0"
              result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>

          {/* ── Arrowhead markers ── */}
          <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0,2 L8,5 L0,8 z" fill="rgba(55,53,47,0.13)" />
          </marker>
          <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0,2 L8,5 L0,8 z" fill="#2383e2" />
          </marker>
          <marker id="arr-faint" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0,2 L8,5 L0,8 z" fill="rgba(35,131,226,0.25)" />
          </marker>
        </defs>

        {/* ════════════════════════════════════════════════════════════════
            EDGES — rendered below nodes so nodes sit on top
        ════════════════════════════════════════════════════════════════ */}

        {/* Entry arrow from right edge → Gatekeeper
            "From chat" visual connection — rightmost node is Gatekeeper  */}
        {renderEdge("entry")}

        {/* Main pipeline */}
        {renderEdge("gk-planner")}
        {renderEdge("planner-captain")}

        {/* Captain fan-out backbone (stem + bar) — no individual arrows */}
        <line
          x1="390" y1="320" x2="390" y2={BAR_Y}
          stroke={edgeStroke("captain-travel")}
          strokeWidth={edgeWidth("captain-travel")}
          strokeLinecap="round"
          style={{ transition: "stroke 0.4s ease" }}
        />
        <line
          x1="120" y1={BAR_Y} x2="660" y2={BAR_Y}
          stroke={edgeStroke("captain-travel")}
          strokeWidth={edgeWidth("captain-travel")}
          strokeLinecap="round"
          style={{ transition: "stroke 0.4s ease" }}
        />

        {/* Fan-out drops to each subagent */}
        {SUBAGENTS.map(sub => {
          const ek = `captain-${sub.id === "sightseeing" ? "sights" : sub.id}`;
          return (
            <line
              key={`drop-${sub.id}`}
              x1={sub.cx} y1={BAR_Y}
              x2={sub.cx} y2={sub.y}
              stroke={edgeStroke(ek)}
              strokeWidth={edgeWidth(ek)}
              strokeLinecap="round"
              markerEnd={markerId(ek)}
              style={{ transition: "stroke 0.4s ease" }}
            />
          );
        })}

        {/* Subagent → API faint connectors */}
        {SUBAGENTS.map(sub => (
          <line
            key={`api-line-${sub.id}`}
            x1={sub.cx} y1={sub.y + sub.h}
            x2={sub.apiCx} y2={sub.apiCy - 24}
            stroke="rgba(55,53,47,0.07)"
            strokeWidth="1"
            strokeLinecap="round"
            markerEnd="url(#arr)"
          />
        ))}

        {/* ════════════════════════════════════════════════════════════════
            DATA PACKETS — travel along edge paths via animateMotion
        ════════════════════════════════════════════════════════════════ */}
        {packets.map(pkt => {
          const path = EDGE_PATHS[pkt.pathKey];
          if (!path) return null;
          return (
            <g key={pkt.id}>
              {/* Glow halo */}
              <circle r="9" fill={pkt.color} opacity="0" style={{ filter: `blur(4px)` }}>
                <animateMotion path={path} dur={`${pkt.dur}s`} fill="freeze" begin="0s" />
                <animate attributeName="opacity" values="0;0.35;0.35;0" keyTimes="0;0.1;0.85;1" dur={`${pkt.dur}s`} fill="freeze" />
              </circle>
              {/* Core dot */}
              <circle r="4.5" fill={pkt.color} opacity="0">
                <animateMotion path={path} dur={`${pkt.dur}s`} fill="freeze" begin="0s" />
                <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.88;1" dur={`${pkt.dur}s`} fill="freeze" />
              </circle>
            </g>
          );
        })}

        {/* ════════════════════════════════════════════════════════════════
            NODES
        ════════════════════════════════════════════════════════════════ */}

        {/* ── Gatekeeper — rightmost, entry point from chat ── */}
        <g style={{ filter: isActive("gatekeeper") ? "drop-shadow(0 0 8px rgba(55,53,47,0.20))" : "none" }}>
          {/* Pulsing halo when active */}
          {isActive("gatekeeper") && (
            <rect
              x={GK.x - 12} y={GK.y - 12}
              width={GK.w + 24} height={GK.h + 24}
              rx={GK.rx + 10}
              fill="rgba(55,53,47,0.05)"
              className="node-pulse-ring--main"
            />
          )}
          <rect
            x={GK.x} y={GK.y}
            width={GK.w} height={GK.h}
            rx={GK.rx}
            fill={mainFill("gatekeeper")}
            stroke={mainStroke("gatekeeper")}
            strokeWidth={mainStrokeWidth("gatekeeper")}
            style={shapeStyle}
          />
          {/* Status icon */}
          {isDone("gatekeeper") && <text x={GK.x + GK.w - 16} y={GK.cy + 4.5} textAnchor="middle" fontSize="11" fill="rgba(55,53,47,0.35)" fontFamily={FONT} style={{ pointerEvents: "none", userSelect: "none" }}>✓</text>}
          {isError("gatekeeper") && <text x={GK.x + GK.w - 16} y={GK.cy + 4.5} textAnchor="middle" fontSize="11" fill="rgba(224,62,62,0.6)" fontFamily={FONT} style={{ pointerEvents: "none", userSelect: "none" }}>✕</text>}
          {/* Node name */}
          <text
            x={GK.cx} y={GK.cy + 1}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="12" fontWeight="600" fill={mainTextFill("gatekeeper")} fontFamily={FONT}
            style={{ pointerEvents: "none", userSelect: "none", transition: "fill 0.3s" }}
          >{GK.label}</text>
          {/* Role label below */}
          <text
            x={GK.cx} y={GK.y + GK.h + 13}
            textAnchor="middle"
            fontSize="9" fill="rgba(55,53,47,0.38)" fontFamily={FONT}
            style={{ pointerEvents: "none", userSelect: "none" }}
          >{GK.role}</text>
        </g>

        {/* ── Planner — ellipse in center ── */}
        <g style={{ filter: isActive("planner") ? "drop-shadow(0 0 8px rgba(55,53,47,0.18))" : "none" }}>
          {isActive("planner") && (
            <ellipse
              cx={PL.cx} cy={PL.cy}
              rx={PL.rx + 14} ry={PL.ry + 14}
              fill="rgba(55,53,47,0.04)"
              className="node-pulse-ring--main"
            />
          )}
          <ellipse
            cx={PL.cx} cy={PL.cy}
            rx={PL.rx} ry={PL.ry}
            fill={mainFill("planner")}
            stroke={mainStroke("planner")}
            strokeWidth={mainStrokeWidth("planner")}
            style={shapeStyle}
          />
          {isDone("planner") && <text x={PL.cx + PL.rx - 12} y={PL.cy + 4} textAnchor="middle" fontSize="11" fill="rgba(55,53,47,0.35)" fontFamily={FONT} style={{ pointerEvents: "none", userSelect: "none" }}>✓</text>}
          <text
            x={PL.cx} y={PL.cy + 1}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="12" fontWeight="600" fill={mainTextFill("planner")} fontFamily={FONT}
            style={{ pointerEvents: "none", userSelect: "none", transition: "fill 0.3s" }}
          >{PL.label}</text>
          <text
            x={PL.cx} y={PL.cy + PL.ry + 13}
            textAnchor="middle"
            fontSize="9" fill="rgba(55,53,47,0.38)" fontFamily={FONT}
            style={{ pointerEvents: "none", userSelect: "none" }}
          >{PL.role}</text>
        </g>

        {/* ── Captain — wide rounded rect, center ── */}
        <g style={{ filter: isActive("captain") ? "drop-shadow(0 0 9px rgba(55,53,47,0.20))" : "none" }}>
          {isActive("captain") && (
            <rect
              x={CP.x - 12} y={CP.y - 12}
              width={CP.w + 24} height={CP.h + 24}
              rx={CP.rx + 10}
              fill="rgba(55,53,47,0.05)"
              className="node-pulse-ring--main"
            />
          )}
          <rect
            x={CP.x} y={CP.y}
            width={CP.w} height={CP.h}
            rx={CP.rx}
            fill={mainFill("captain")}
            stroke={mainStroke("captain")}
            strokeWidth={mainStrokeWidth("captain")}
            style={shapeStyle}
          />
          {isDone("captain") && <text x={CP.x + CP.w - 16} y={CP.cy + 4} textAnchor="middle" fontSize="11" fill="rgba(55,53,47,0.35)" fontFamily={FONT} style={{ pointerEvents: "none", userSelect: "none" }}>✓</text>}
          <text
            x={CP.cx} y={CP.cy + 1}
            textAnchor="middle" dominantBaseline="middle"
            fontSize="12" fontWeight="600" fill={mainTextFill("captain")} fontFamily={FONT}
            style={{ pointerEvents: "none", userSelect: "none", transition: "fill 0.3s" }}
          >{CP.label}</text>
          <text
            x={CP.cx} y={CP.y + CP.h + 13}
            textAnchor="middle"
            fontSize="9" fill="rgba(55,53,47,0.38)" fontFamily={FONT}
            style={{ pointerEvents: "none", userSelect: "none" }}
          >{CP.role}</text>
        </g>

        {/* ── Subagents — 4 rounded rects at bottom ── */}
        {SUBAGENTS.map(sub => (
          <g
            key={sub.id}
            style={{ filter: isActive(sub.id) ? "drop-shadow(0 0 8px rgba(35,131,226,0.28))" : "none" }}
          >
            {isActive(sub.id) && (
              <rect
                x={sub.x - 10} y={sub.y - 10}
                width={sub.w + 20} height={sub.h + 20}
                rx={sub.rx + 8}
                fill="rgba(35,131,226,0.06)"
                className="node-pulse-ring"
              />
            )}
            <rect
              x={sub.x} y={sub.y}
              width={sub.w} height={sub.h}
              rx={sub.rx}
              fill={subFill(sub.id)}
              stroke={subStroke(sub.id)}
              strokeWidth={subStrokeWidth(sub.id)}
              style={shapeStyle}
            />
            {isDone(sub.id) && (
              <text x={sub.x + sub.w - 13} y={sub.cy + 4} textAnchor="middle" fontSize="10"
                fill="rgba(35,131,226,0.45)" fontFamily={FONT}
                style={{ pointerEvents: "none", userSelect: "none" }}>✓</text>
            )}
            {/* Name inside node */}
            <text
              x={sub.cx} y={sub.cy + 1}
              textAnchor="middle" dominantBaseline="middle"
              fontSize="11" fontWeight="600" fill={subTextFill(sub.id)} fontFamily={FONT}
              style={{ pointerEvents: "none", userSelect: "none", transition: "fill 0.3s" }}
            >{sub.label}</text>
            {/* Role label below */}
            <text
              x={sub.cx} y={sub.y + sub.h + 12}
              textAnchor="middle"
              fontSize="8.5" fill="rgba(55,53,47,0.35)" fontFamily={FONT}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >{sub.role}</text>
          </g>
        ))}

        {/* ── API circles — faint, below each subagent ── */}
        {SUBAGENTS.map(sub => (
          <g key={`api-${sub.id}`}>
            <circle
              cx={sub.apiCx} cy={sub.apiCy} r="22"
              fill="#f7f6f3"
              stroke="rgba(55,53,47,0.09)"
              strokeWidth="1"
            />
            <text
              x={sub.apiCx} y={sub.apiCy + 1}
              textAnchor="middle" dominantBaseline="middle"
              fontSize="8.5" fontWeight="500" fill="rgba(55,53,47,0.50)" fontFamily={FONT}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >{sub.apiLabel}</text>
            <text
              x={sub.apiCx} y={sub.apiCy + 32}
              textAnchor="middle"
              fontSize="8" fill="rgba(55,53,47,0.30)" fontFamily={FONT}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >API</text>
          </g>
        ))}

        {/* ── Entry label: "← from chat" indicator at right edge ── */}
        <text
          x="798" y="57"
          textAnchor="end"
          fontSize="8.5" fill="rgba(55,53,47,0.28)" fontFamily={FONT}
          style={{ pointerEvents: "none", userSelect: "none" }}
        >chat →</text>

      </svg>
    </div>
  );
}
