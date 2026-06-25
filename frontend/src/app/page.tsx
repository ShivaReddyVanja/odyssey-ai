"use client";

import React, { useState, useEffect, useRef } from "react";
import { useEventStream } from "../hooks/useEventStream";
import PipelinePanel from "../components/PipelinePanel";
import TravelMap from "../components/TravelMap";
import RoutePathPanel from "../components/RoutePathPanel";
import ChatPanel from "../components/ChatPanel";

export default function Home() {
  const {
    phase,
    logs,
    thinkingLogs,
    destinationCard,
    transitCard,
    budgetCard,
    activeNode,
    candidates,
    finalItinerary,
    validationWarnings,
    interruptedQuestions,
    activeApiCall,
    startPlanning,
    submitClarification,
    reset,
  } = useEventStream();

  const [leftTab, setLeftTab] = useState<"pipeline" | "map" | "path">("pipeline");
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);

  // Refs for tracking coordinates and rendering the global wire directly in DOM
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const glowPathRef = useRef<SVGPathElement>(null);
  const chargePathRef = useRef<SVGPathElement>(null);

  // Track animation timing states
  const animStateRef = useRef({
    prevPhase: "idle",
    validatingStartTime: 0,
    completedStartTime: 0,
    isCompletedAnimating: false,
  });

  // Auto-switch to path once planning completes, back to pipeline on reset
  useEffect(() => {
    if (phase === "completed" && finalItinerary) {
      setLeftTab("path");
      setIsConsoleOpen(false); // Auto-close chat console
    } else if (phase === "idle") {
      setLeftTab("pipeline");
      setIsConsoleOpen(true); // Re-open chat console on reset
    }
  }, [phase, finalItinerary]);

  // Viewport-wide coordinate tracking & animation update loop
  useEffect(() => {
    let animFrameId: number;

    const updateWire = () => {
      const gatekeeper = document.getElementById("gatekeeper-plug-socket");
      const chatInput = document.getElementById("chat-input-plug-connector");

      if (
        gatekeeper &&
        chatInput &&
        pathRef.current &&
        glowPathRef.current &&
        chargePathRef.current &&
        leftTab === "pipeline" &&
        isConsoleOpen
      ) {
        // Show wire
        if (svgRef.current) svgRef.current.style.opacity = "1";

        const r1 = gatekeeper.getBoundingClientRect();
        const r2 = chatInput.getBoundingClientRect();

        // Gatekeeper socket: middle of right edge, offset by 3px for stroke cap
        const x1 = r1.right + 3;
        const y1 = r1.top + r1.height / 2;

        // Chat Input plug: middle of left edge
        const x2 = r2.left;
        const y2 = r2.top + r2.height / 2;

        // Curve calculations: Symmetric sweeping Bezier curve
        const dx = Math.abs(x2 - x1) * 0.55;
        const dStr = `M ${x2} ${y2} C ${x2 - dx} ${y2}, ${x1 + dx} ${y1}, ${x1} ${y1}`;

        pathRef.current.setAttribute("d", dStr);
        glowPathRef.current.setAttribute("d", dStr);
        chargePathRef.current.setAttribute("d", dStr);

        // Dynamically track the Experience Agent card coordinates to mask the wire behind it
        const expAgent = document.getElementById("sightseeing-agent-card");
        const maskCutout = document.getElementById("mask-cutout");
        if (maskCutout && expAgent) {
          const r = expAgent.getBoundingClientRect();
          maskCutout.setAttribute("x", String(r.left - 4));
          maskCutout.setAttribute("y", String(r.top - 4));
          maskCutout.setAttribute("width", String(r.width + 8));
          maskCutout.setAttribute("height", String(r.height + 8));
        }

        // Calculate path length for laser charge beam animation
        const len = pathRef.current.getTotalLength();
        chargePathRef.current.style.strokeDasharray = `50 ${len}`;

        const state = animStateRef.current;
        const now = Date.now();

        // Detect state transitions to reset timers
        if (phase === "validating" && state.prevPhase === "idle") {
          state.validatingStartTime = now;
        }
        if (phase === "completed" && state.prevPhase !== "completed") {
          state.completedStartTime = now;
          state.isCompletedAnimating = true;
        }
        state.prevPhase = phase;

        let offset = len + 50; // Off-screen initially

        if (
          phase === "validating" ||
          phase === "planning" ||
          phase === "discovering" ||
          phase === "compiling"
        ) {
          // Charge moves from Input box to Gatekeeper
          const elapsed = now - state.validatingStartTime;
          const duration = 1000; // 1 second travel duration
          const progress = Math.min(elapsed / duration, 1);

          // Easing: easeInOutQuad
          const easeProgress =
            progress < 0.5
              ? 2 * progress * progress
              : 1 - Math.pow(-2 * progress + 2, 2) / 2;

          offset = len + 50 - easeProgress * (len + 50);
        } else if (phase === "completed" && state.isCompletedAnimating) {
          // Charge moves in reverse back to Input box
          const elapsed = now - state.completedStartTime;
          const duration = 1200; // 1.2 seconds return duration
          const progress = Math.min(elapsed / duration, 1);

          const easeProgress =
            progress < 0.5
              ? 2 * progress * progress
              : 1 - Math.pow(-2 * progress + 2, 2) / 2;

          offset = easeProgress * (len + 50);

          if (progress >= 1) {
            state.isCompletedAnimating = false;
          }
        }

        chargePathRef.current.style.strokeDashoffset = `${offset}`;
      } else {
        // Hide wire if components are unmounted or map is visible
        if (svgRef.current) svgRef.current.style.opacity = "0";
      }

      animFrameId = requestAnimationFrame(updateWire);
    };

    updateWire();

    return () => {
      cancelAnimationFrame(animFrameId);
    };
  }, [phase, leftTab, isConsoleOpen]);

  return (
    <main className={`app-root ${isConsoleOpen ? "console-open" : "console-closed"}`}>
      {/* ── Left Panel: Pipeline OR Map (never both at once) ── */}
      <aside className="app-sidebar">
        {/* Full-height toggle bar — always visible */}
        <div className="view-toggle-bar">
          <button
            onClick={() => setLeftTab("pipeline")}
            className={`view-toggle-btn ${
              leftTab === "pipeline" ? "view-toggle-btn--active-dark" : ""
            }`}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
            Pipeline
          </button>
          <button
            onClick={() => setLeftTab("map")}
            className={`view-toggle-btn ${leftTab === "map" ? "view-toggle-btn--active-blue" : ""}`}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
            Map
          </button>
          <button
            onClick={() => setLeftTab("path")}
            className={`view-toggle-btn ${leftTab === "path" ? "view-toggle-btn--active-green" : ""}`}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="4" y1="12" x2="20" y2="12" />
              <circle cx="4" cy="12" r="2.5" fill="currentColor" />
              <circle cx="12" cy="12" r="2.5" fill="currentColor" />
              <circle cx="20" cy="12" r="2.5" fill="currentColor" />
            </svg>
            Path
          </button>
          
          {/* Toggle Console Button */}
          <button
            onClick={() => setIsConsoleOpen(!isConsoleOpen)}
            className="view-toggle-btn"
            style={{ marginLeft: "auto" }}
            title={isConsoleOpen ? "Hide Interaction Console" : "Show Interaction Console"}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            {isConsoleOpen ? "Hide Console" : "Show Console"}
          </button>
        </div>

        {/* Full-height content — pipeline, map, or path, exclusively */}
        <div className="sidebar-content">
          {leftTab === "pipeline" && (
            <PipelinePanel activeNode={activeNode} phase={phase} candidates={candidates} logs={logs} activeApiCall={activeApiCall} />
          )}
          {leftTab === "map" && (
            <TravelMap itinerary={finalItinerary} />
          )}
          {leftTab === "path" && (
            <RoutePathPanel itinerary={finalItinerary} />
          )}
        </div>
      </aside>

      {/* ── Right Panel: Console only (no candidates) ── */}
      <div className="app-right-panel">
        <ChatPanel
          phase={phase}
          logs={logs}
          thinkingLogs={thinkingLogs}
          destinationCard={destinationCard}
          transitCard={transitCard}
          budgetCard={budgetCard}
          activeNode={activeNode}
          interruptedQuestions={interruptedQuestions}
          startPlanning={startPlanning}
          submitClarification={submitClarification}
          reset={reset}
        />

        {/* Validation warnings footer */}
        {phase === "completed" && validationWarnings.length > 0 && (
          <div className="validation-banner">
            <span className="validation-banner-icon">⚠</span>
            <div className="validation-banner-body">
              {validationWarnings.map((w, idx) => (
                <div key={idx} className="validation-banner-line">
                  {w}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Global SVG Wire Overlay ── */}
      <svg
        ref={svgRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100vw",
          height: "100vh",
          pointerEvents: "none",
          zIndex: 9999,
          opacity: 0,
          transition: "opacity 0.3s",
        }}
      >
        {/* Main solid pipe-like wire base */}
        <path
          ref={pathRef}
          fill="none"
          stroke="#cbd5e1"
          strokeWidth="6"
          strokeLinecap="round"
          mask="url(#wire-mask)"
          style={{
            filter: "drop-shadow(0 2px 4px rgba(15,23,42,0.15))",
          }}
        />

        {/* Inner glow core */}
        <path
          ref={glowPathRef}
          fill="none"
          stroke="#38bdf8"
          strokeWidth="2"
          strokeLinecap="round"
          mask="url(#wire-mask)"
          style={{
            opacity: phase !== "idle" ? 1 : 0.25,
            transition: "opacity 0.3s",
          }}
        />

        {/* Laser Charge Beam */}
        <path
          ref={chargePathRef}
          fill="none"
          stroke="url(#wire-gradient)"
          strokeWidth="2.5"
          strokeLinecap="round"
          mask="url(#wire-mask)"
          className={phase !== "idle" ? "wire-charge-anim" : ""}
        />

        <defs>
          <linearGradient id="wire-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0" />
            <stop offset="50%" stopColor="#f43f5e" stopOpacity="1" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
          </linearGradient>
          
          <mask id="wire-mask">
            {/* Everything white is fully visible */}
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {/* The black rect hides the wire where it overlaps the Experience Agent card */}
            <rect id="mask-cutout" x="0" y="0" width="0" height="0" fill="black" rx="16" ry="16" />
          </mask>
        </defs>
      </svg>
    </main>
  );
}
