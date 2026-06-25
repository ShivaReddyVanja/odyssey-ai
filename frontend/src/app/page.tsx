"use client";

import React, { useState, useEffect, useRef } from "react";
import { useEventStream } from "../hooks/useEventStream";
import PipelinePanel from "../components/PipelinePanel";
import TravelMap from "../components/TravelMap";
import RoutePathPanel from "../components/RoutePathPanel";
import ChatPanel from "../components/ChatPanel";

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
    rateLimitError,
    clearRateLimitError,
    totalGenerated,
  } = useEventStream();

  const [leftTab, setLeftTab] = useState<"pipeline" | "map" | "path">("pipeline");
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);

  // Refs for tracking coordinates and rendering the global wire directly in DOM
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const glowPathRef = useRef<SVGPathElement>(null);
  const chargePathRef = useRef<SVGPathElement>(null);
  const dismissBtnRef = useRef<HTMLButtonElement>(null);

  // Track animation timing states
  const animStateRef = useRef({
    prevPhase: "idle",
    validatingStartTime: 0,
    completedStartTime: 0,
    isCompletedAnimating: false,
  });

  // Focus the dismiss button when rate limit modal opens
  useEffect(() => {
    if (rateLimitError && dismissBtnRef.current) {
      dismissBtnRef.current.focus();
    }
  }, [rateLimitError]);

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

        const isStacked = window.innerWidth <= 960;

        let x1, y1, x2, y2, dStr;

        if (isStacked) {
          // Gatekeeper socket: center of the socket element
          x1 = r1.left + r1.width / 2;
          y1 = r1.top + r1.height / 2;

          // Chat Input plug: center of the plug element, pointing up (top edge)
          x2 = r2.left + r2.width / 2;
          y2 = r2.top;

          // Curve calculations: Vertical S-curve entering Chat Plug from top, leaving Gatekeeper horizontally to the right
          const dx = 50; // comes out 50px to the right of socket
          const dy = Math.max(80, Math.abs(y2 - y1) * 0.45); // pulls up vertically from plug
          dStr = `M ${x2} ${y2} C ${x2} ${y2 - dy}, ${x1 + dx} ${y1}, ${x1} ${y1}`;
        } else {
          // Gatekeeper socket: middle of right edge, offset by 3px for stroke cap
          x1 = r1.right + 3;
          y1 = r1.top + r1.height / 2;

          // Chat Input plug: middle of left edge
          x2 = r2.left;
          y2 = r2.top + r2.height / 2;

          // Curve calculations: Symmetric sweeping Bezier curve
          const dx = Math.abs(x2 - x1) * 0.55;
          dStr = `M ${x2} ${y2} C ${x2 - dx} ${y2}, ${x1 + dx} ${y1}, ${x1} ${y1}`;
        }

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
    <>
      <div className="mobile-block-overlay">
        <div style={{ maxWidth: 360, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(56, 189, 248, 0.1)", color: "#38bdf8", marginBottom: 24, border: "1.5px solid rgba(56, 189, 248, 0.2)" }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.5px", marginBottom: 12 }}>Desktop View Required</h2>
          <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6, marginBottom: 0 }}>
            OdysseyAI's multi-agent mapping interface is designed for larger displays. Please expand your window or view on a desktop screen (at least 1024px wide).
          </p>
        </div>
      </div>

      <main className={`app-root ${isConsoleOpen ? "console-open" : "console-closed"}`}>
      {/* ── Left Panel: Pipeline OR Map (never both at once) ── */}
      <aside className="app-sidebar">
        {/* Unified Top Header */}
        <div className="view-toggle-bar" style={{ display: "flex", alignItems: "center", padding: "10px 16px" }}>
          <div style={{ display: "flex", alignItems: "center" }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", background: "#1e293b", color: "#ffffff", marginRight: 8 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a", lineHeight: 1.2 }}>OdysseyAI</span>
              <span style={{ fontSize: "10px", color: "#64748b", fontWeight: 500 }}>
                {leftTab === "pipeline" ? "Pipeline" : leftTab === "map" ? "Map View" : "Route Path"}
              </span>
            </div>
            {phase !== "idle" && (
              <div 
                className={`pipeline-phase-badge ${phaseIsActive(phase) ? "pipeline-phase-badge--active" : phase === "completed" ? "pipeline-phase-badge--done" : phase === "error" ? "pipeline-phase-badge--error" : ""}`}
                style={{ marginLeft: 12, padding: "2px 8px", fontSize: "10px", height: "fit-content" }}
              >
                {phaseIsActive(phase) && <span className="pipeline-phase-dot" style={{ width: 5, height: 5 }} />}
                {phaseLabel(phase)}
              </div>
            )}
          </div>
          
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
              style={{ marginRight: 4 }}
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

        {/* Bottom tab chooser */}
        <div className="view-toggle-bar-bottom">
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
              style={{ marginRight: 4 }}
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
              style={{ marginRight: 4 }}
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
              style={{ marginRight: 4 }}
            >
              <line x1="4" y1="12" x2="20" y2="12" />
              <circle cx="4" cy="12" r="2.5" fill="currentColor" />
              <circle cx="12" cy="12" r="2.5" fill="currentColor" />
              <circle cx="20" cy="12" r="2.5" fill="currentColor" />
            </svg>
            Path
          </button>
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
          totalGenerated={totalGenerated}
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

      {/* Rate Limit Modal Popup Overlay */}
      {rateLimitError && (
        <div className="rate-limit-modal-overlay">
          <div 
            className="rate-limit-modal-card" 
            role="dialog" 
            aria-modal="true" 
            aria-labelledby="rate-limit-title"
          >
            <div className="rate-limit-modal-icon">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 id="rate-limit-title" className="rate-limit-modal-title">Rate Limit Exceeded</h2>
            <p className="rate-limit-modal-desc">{rateLimitError}</p>
            <button 
              ref={dismissBtnRef} 
              className="rate-limit-modal-btn" 
              onClick={clearRateLimitError}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </main>
    </>
  );
}
