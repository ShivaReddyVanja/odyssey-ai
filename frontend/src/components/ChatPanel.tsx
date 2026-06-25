"use client";

import React, { useState, useEffect, useRef } from "react";
import { LogMessage, DestinationCardData, TransitCardData, BudgetCardData } from "../hooks/useEventStream";

/* ─── Types ─────────────────────────────────────────────────────────────── */

interface ChatPanelProps {
  phase: string;
  logs: LogMessage[];
  thinkingLogs: LogMessage[];
  destinationCard: DestinationCardData | null;
  transitCard: TransitCardData | null;
  budgetCard: BudgetCardData | null;
  activeNode: string | null;
  interruptedQuestions: string[] | null;
  startPlanning: (prompt: string) => void;
  submitClarification: (answers: Record<string, string>) => void;
  reset: () => void;
  totalGenerated: number;
}

interface GroupedMessage {
  id: string;
  type: "user" | "bot" | "system" | "error";
  text: string;
  timestamp: Date;
  node?: string;
}

/* ─── Inline SVG Icons ───────────────────────────────────────────────────── */

function SendIcon({ active }: { active: boolean }) {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        transform: active ? "translate(1px, -1px)" : "none",
        transition: "transform 0.2s",
      }}
    >
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l1.88 5.12L19 10l-5.12 1.88L12 17l-1.88-5.12L5 10l5.12-1.88z" />
      <path d="M5 3l.88 2.12L8 6l-2.12.88L5 9l-.88-2.12L2 6l2.12-.88z" />
      <path d="M19 15l.88 2.12L22 18l-2.12.88L19 21l-.88-2.12L16 18l2.12-.88z" />
    </svg>
  );
}

function MessageIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

/* ─── Constants ──────────────────────────────────────────────────────────── */

const QUICK_SUGGESTIONS = [
  "Plan a 5-day cultural trip to Rome on a mid-range budget.",
  "3 days in Paris focused on food and museums, luxury stay.",
  "Weekend in Delhi — budget travel, local street food focus.",
];

const AGENT_NAMES: Record<string, string> = {
  gatekeeper: "Gatekeeper",
  planner: "Planner",
  captain: "Captain",
  travel: "Travel Agent",
  stay: "Lodging Agent",
  food: "Culinary Agent",
  sightseeing: "Experience Agent",
};

/* ─── Main Component ─────────────────────────────────────────────────────── */

export default function ChatPanel({
  phase,
  logs,
  thinkingLogs,
  destinationCard,
  transitCard,
  budgetCard,
  activeNode,
  interruptedQuestions,
  startPlanning,
  submitClarification,
  reset,
  totalGenerated,
}: ChatPanelProps) {
  const [inputPrompt, setInputPrompt] = useState("");
  const [inputFocused, setInputFocused] = useState(false);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>({});
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(true);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const thinkingContainerRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll to bottom */
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, interruptedQuestions, activeNode, thinkingLogs, destinationCard, transitCard, budgetCard]);

  /* Auto-scroll the thinking drawer container */
  useEffect(() => {
    if (thinkingContainerRef.current) {
      thinkingContainerRef.current.scrollTop = thinkingContainerRef.current.scrollHeight;
    }
  }, [thinkingLogs, isThinkingExpanded]);

  /* Reset input on idle */
  useEffect(() => {
    if (phase === "idle") {
      setInputPrompt("");
      setClarificationAnswers({});
    }
  }, [phase]);

  /* Init clarification answers map */
  useEffect(() => {
    if (interruptedQuestions) {
      const init: Record<string, string> = {};
      interruptedQuestions.forEach((q) => { init[q] = ""; });
      setClarificationAnswers(init);
    }
  }, [interruptedQuestions]);

  /* Auto-resize textarea */
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 128) + "px";
    }
  }, [inputPrompt]);

  /* Handlers */
  const handleSubmitPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    const query = inputPrompt.trim();
    if (!query) return;
    if (phase !== "idle" && phase !== "completed" && phase !== "error") return;
    startPlanning(query);
    setInputPrompt("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitPrompt(e as unknown as React.FormEvent);
    }
  };

  const handleClarificationChange = (question: string, value: string) => {
    setClarificationAnswers((prev) => ({ ...prev, [question]: value }));
  };

  const handleSubmitClarifications = (e: React.FormEvent) => {
    e.preventDefault();
    submitClarification(clarificationAnswers);
    setClarificationAnswers({});
  };

  const isBusy =
    phase !== "idle" &&
    phase !== "completed" &&
    phase !== "clarifying" &&
    phase !== "error";

  const canSend = !isBusy && !!inputPrompt.trim();

  /* Group messages */
  const groupedMessages: GroupedMessage[] = [];
  logs.forEach((log) => {
    if (log.type === "user") {
      groupedMessages.push({ id: log.id, type: "user", text: log.text, timestamp: log.timestamp });
    } else if (log.type === "error") {
      groupedMessages.push({ id: log.id, type: "error", text: log.text, timestamp: log.timestamp });
    } else if (log.type === "system") {
      groupedMessages.push({ id: log.id, type: "system", text: log.text, timestamp: log.timestamp });
    } else {
      const last = groupedMessages[groupedMessages.length - 1];
      if (last && last.type === "bot" && last.node === log.node) {
        last.text += "\n" + log.text;
      } else {
        groupedMessages.push({ id: log.id, type: "bot", text: log.text, timestamp: log.timestamp, node: log.node });
      }
    }
  });

  /* Phase display */
  const phaseBadgeClass = `phase-badge phase-badge--${phase}`;

  const isActive = ["validating", "planning", "discovering", "compiling"].includes(phase);
  const isDone = phase === "completed";
  const isError = phase === "error";

  return (
    <div className="chat-panel" style={{ position: "relative" }}>
      {/* Visual Plug Connector */}
      <div
        id="chat-input-plug-connector"
        className={`chat-plug-connector ${phase === "idle" ? "state-idle" : "state-active"}`}
      >
        {/* Double pins inside plug */}
        <div className="chat-plug-connector-pins">
          <div className="chat-plug-connector-pin" />
          <div className="chat-plug-connector-pin" />
        </div>
      </div>

      {/* ── Header ── */}
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon">
            <TerminalIcon />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div className="chat-header-title">Interaction Console</div>
              {totalGenerated > 0 && (
                <span
                  style={{
                    fontSize: "10px",
                    backgroundColor: "rgba(35, 131, 226, 0.08)",
                    color: "#2383e2",
                    padding: "2px 8px",
                    borderRadius: "12px",
                    fontWeight: 600,
                    border: "1px solid rgba(35, 131, 226, 0.15)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    animation: "fadeIn 0.3s ease-in-out",
                  }}
                >
                  <span
                    style={{
                      width: "5px",
                      height: "5px",
                      borderRadius: "50%",
                      backgroundColor: "#2383e2",
                      display: "inline-block",
                    }}
                  />
                  {totalGenerated} {totalGenerated === 1 ? "journey" : "journeys"} designed
                </span>
              )}
            </div>
            <div className="chat-header-sub">
              {phase === "idle" ? "Awaiting Instructions" : "Planning in progress…"}
            </div>
          </div>
        </div>
        <div className="chat-header-right">
          <span className={phaseBadgeClass}>{phase}</span>
          {phase !== "idle" && (
            <button className="reset-btn" onClick={reset}>Reset</button>
          )}
        </div>
      </div>

      {/* ── Messages Area ── */}
      <div className="chat-messages">
        {logs.length === 0 ? (
          /* Empty state — matches the OdysseyAI console aesthetic */
          <div className="chat-empty-state">
            <div className="chat-empty-sparkle">
              <SparkleIcon />
            </div>
            <h3 className="chat-empty-title">Design Your Expedition</h3>
            <p className="chat-empty-desc">
              Describe your ideal journey. The OdysseyAI swarm will autonomously research, plan, and orchestrate a comprehensive itinerary.
            </p>
            <p className="chat-suggestions-label">Suggested Prompts</p>
            <div className="chat-suggestions-list">
              {QUICK_SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="chat-suggestion-chip"
                  onClick={() => !isBusy && setInputPrompt(s)}
                >
                  <span className="chat-suggestion-icon"><MessageIcon /></span>
                  <span className="chat-suggestion-text">{s}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message history */
          groupedMessages.map((msg) => {
            if (msg.type === "system") {
              return (
                <div key={msg.id} className="chat-system-message">
                  {msg.text}
                </div>
              );
            }
            const isUser = msg.type === "user";
            const isError = msg.type === "error";
            return (
              <div
                key={msg.id}
                className={`chat-message-row ${isUser ? "chat-message-row--user" : "chat-message-row--agent"}`}
              >
                <div
                  className={`chat-bubble ${
                    isUser ? "chat-bubble--user" :
                    isError ? "chat-bubble--error" :
                    "chat-bubble--agent"
                  }`}
                >
                  {!isUser && !isError && msg.node && (
                    <div className="chat-bubble-agent-header">
                      {AGENT_NAMES[msg.node] ?? msg.node}
                    </div>
                  )}
                  {msg.text}
                </div>
              </div>
            );
          })
        )}

        {/* Active thinking indicator */}
        {activeNode && isActive && (
          <div className="chat-message-row chat-message-row--agent">
            <div className="chat-bubble chat-bubble--agent chat-bubble--thinking">
              <div className="chat-bubble-agent-header">
                {AGENT_NAMES[activeNode] ?? activeNode}
              </div>
              <div className="chat-thinking-body">
                <span>thinking</span>
                <div className="typing-dots">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Clarification form */}
        {interruptedQuestions && (
          <div className="clarification-form-wrapper">
            <div className="clarification-header">
              <span className="clarification-title">Clarification needed</span>
            </div>
            <form onSubmit={handleSubmitClarifications}>
              <div className="clarification-questions">
                {interruptedQuestions.map((q, idx) => (
                  <div key={idx}>
                    <label className="clarification-field-label">{q}</label>
                    <input
                      type="text"
                      required
                      value={clarificationAnswers[q] || ""}
                      onChange={(e) => handleClarificationChange(q, e.target.value)}
                      className="clarification-input"
                      placeholder="Your answer…"
                    />
                  </div>
                ))}
              </div>
              <button type="submit" className="clarification-submit-btn">
                Submit &amp; Resume Planning
              </button>
            </form>
          </div>
        )}

        {/* Structured Destinations Card */}
        {destinationCard && (
          <div className="chat-message-row chat-message-row--agent" style={{ margin: "8px 0" }}>
            <div
              style={{
                width: "100%",
                maxWidth: "500px",
                padding: "16px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))",
                border: "1px solid rgba(56, 189, 248, 0.25)",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.25)",
                color: "#f1f5f9",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", paddingBottom: "8px" }}>
                <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "#38bdf8", display: "flex", alignItems: "center", gap: "6px" }}>
                  🗺️ Destinations Decided
                </h4>
                <span style={{ fontSize: "11px", backgroundColor: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", padding: "2px 8px", borderRadius: "12px", fontWeight: 600 }}>
                  {destinationCard.summary_text}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
                {destinationCard.destinations.map((dest, idx) => (
                  <div key={idx} style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", padding: "6px 8px", background: "rgba(255, 255, 255, 0.03)", borderRadius: "6px" }}>
                    <span style={{ fontWeight: 500 }}>{idx + 1}. {dest.destination}</span>
                    <span style={{ color: "#94a3b8" }}>{dest.duration_days} days</span>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: "12px", color: "#94a3b8", borderTop: "1px solid rgba(255, 255, 255, 0.05)", paddingTop: "8px" }}>
                <div style={{ fontWeight: 600, color: "#cbd5e1", marginBottom: "4px" }}>Theme: {destinationCard.theme}</div>
                <div style={{ fontStyle: "italic", lineHeight: "1.4" }}>{destinationCard.explanation}</div>
              </div>
            </div>
          </div>
        )}

        {/* Structured Transit Route Card */}
        {transitCard && (
          <div className="chat-message-row chat-message-row--agent" style={{ margin: "8px 0" }}>
            <div
              style={{
                width: "100%",
                maxWidth: "500px",
                padding: "16px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))",
                border: "1px solid rgba(244, 63, 94, 0.25)",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.25)",
                color: "#f1f5f9",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", paddingBottom: "8px" }}>
                <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "#f43f5e", display: "flex", alignItems: "center", gap: "6px" }}>
                  ✈️ Transit Route
                </h4>
                <span style={{ fontSize: "11px", backgroundColor: "rgba(244, 63, 94, 0.15)", color: "#f43f5e", padding: "2px 8px", borderRadius: "12px", fontWeight: 600 }}>
                  Route Fixed
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {transitCard.segments.map((seg, idx) => {
                  const formatDuration = (mins: number) => {
                    const h = Math.floor(mins / 60);
                    const m = mins % 60;
                    return h > 0 ? `${h}h ${m}m` : `${m}m`;
                  };
                  return (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: "12px",
                        padding: "8px",
                        background: "rgba(255, 255, 255, 0.03)",
                        borderRadius: "6px",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", flex: 1, minWidth: 0 }}>
                        <span style={{ fontWeight: 600, color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{seg.origin}</span>
                        <span style={{ color: "#64748b" }}>➔</span>
                        <span style={{ fontWeight: 600, color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{seg.destination}</span>
                      </div>
                      
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "10px",
                            backgroundColor: seg.mode_label === "Flight" ? "rgba(56, 189, 248, 0.15)" : "rgba(34, 197, 94, 0.15)",
                            color: seg.mode_label === "Flight" ? "#38bdf8" : "#22c55e",
                            padding: "1px 6px",
                            borderRadius: "4px",
                            fontWeight: 600,
                          }}
                        >
                          {seg.mode_label || (seg.mode === "flight" ? "Flight" : "Drive")}
                        </span>
                        
                        <span style={{ color: "#94a3b8", fontSize: "11px", whiteSpace: "nowrap" }}>
                          {formatDuration(seg.duration_minutes)}
                        </span>
                        
                        {seg.estimated_price > 0 ? (
                          <span style={{ fontWeight: 600, color: "#e2e8f0", fontSize: "11px", whiteSpace: "nowrap" }}>
                            ₹{seg.estimated_price.toLocaleString()}
                          </span>
                        ) : (
                          <span style={{ color: "#64748b", fontSize: "11px" }}>Free</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Structured Budget Summary Card */}
        {budgetCard && (
          <div className="chat-message-row chat-message-row--agent" style={{ margin: "8px 0" }}>
            <div
              style={{
                width: "100%",
                maxWidth: "500px",
                padding: "16px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))",
                border: budgetCard.verdict === "within_budget" 
                  ? "1px solid rgba(34, 197, 94, 0.35)" 
                  : budgetCard.verdict === "over_budget" 
                    ? "1px solid rgba(239, 68, 68, 0.35)" 
                    : "1px solid rgba(245, 158, 11, 0.35)",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.25)",
                color: "#f1f5f9",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)", paddingBottom: "8px" }}>
                <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "#22c55e", display: "flex", alignItems: "center", gap: "6px" }}>
                  💰 Estimated Budget
                </h4>
                <span
                  style={{
                    fontSize: "11px",
                    backgroundColor: budgetCard.verdict === "within_budget" 
                      ? "rgba(34, 197, 94, 0.15)" 
                      : budgetCard.verdict === "over_budget" 
                        ? "rgba(239, 68, 68, 0.15)" 
                        : "rgba(245, 158, 11, 0.15)",
                    color: budgetCard.verdict === "within_budget" 
                      ? "#22c55e" 
                      : budgetCard.verdict === "over_budget" 
                        ? "#ef4444" 
                        : "#f59e0b",
                    padding: "2px 8px",
                    borderRadius: "12px",
                    fontWeight: 600
                  }}
                >
                  {budgetCard.verdict === "within_budget" ? "Within Budget" : budgetCard.verdict === "over_budget" ? "Over Budget" : "Estimate"}
                </span>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                  <span style={{ color: "#94a3b8" }}>Transit Cost</span>
                  <span style={{ fontWeight: 500 }}>₹{budgetCard.transit_cost_inr.toLocaleString()}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                  <span style={{ color: "#94a3b8" }}>Accommodation</span>
                  <span style={{ fontWeight: 500 }}>₹{budgetCard.accommodation_cost_inr.toLocaleString()}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                  <span style={{ color: "#94a3b8" }}>Food + Sightseeing</span>
                  <span style={{ fontWeight: 500 }}>₹{budgetCard.food_activities_cost_inr.toLocaleString()}</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "14px",
                    fontWeight: 700,
                    borderTop: "1px solid rgba(255, 255, 255, 0.1)",
                    paddingTop: "8px",
                    marginTop: "4px",
                    color: "#cbd5e1"
                  }}
                >
                  <span>Total Estimated</span>
                  <span style={{ color: "#22c55e" }}>₹{budgetCard.total_estimated_inr.toLocaleString()}</span>
                </div>
              </div>
              
              <div
                style={{
                  fontSize: "12px",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  backgroundColor: budgetCard.verdict === "within_budget" 
                    ? "rgba(34, 197, 94, 0.1)" 
                    : budgetCard.verdict === "over_budget" 
                      ? "rgba(239, 68, 68, 0.1)" 
                      : "rgba(245, 158, 11, 0.1)",
                  color: budgetCard.verdict === "within_budget" 
                    ? "#4ade80" 
                    : budgetCard.verdict === "over_budget" 
                      ? "#f87171" 
                      : "#fbbf24",
                  lineHeight: "1.4",
                  fontWeight: 500,
                }}
              >
                {budgetCard.verdict === "within_budget" ? "✓" : budgetCard.verdict === "over_budget" ? "⚠️" : "ℹ️"} {budgetCard.message}
              </div>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* ── Collapsible Swarm Thinking Drawer ── */}
      {thinkingLogs.length > 0 && (
        <div
          className="thinking-drawer"
          style={{
            margin: "0 16px 12px 16px",
            background: "rgba(30, 41, 59, 0.75)",
            backdropFilter: "blur(8px)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderLeft: isActive ? "4px solid #38bdf8" : "4px solid rgba(148, 163, 184, 0.5)",
            borderRadius: "8px",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            boxShadow: isActive ? "0 4px 20px rgba(56, 189, 248, 0.15)" : "none",
            animation: isActive ? "pulse-border 2s infinite alternate" : "none",
          }}
        >
          <style dangerouslySetInnerHTML={{__html: `
            @keyframes pulse-border {
              0% { border-left-color: #38bdf8; }
              100% { border-left-color: #f43f5e; }
            }
          `}} />
          
          <div
            style={{
              padding: "8px 12px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              cursor: "pointer",
              userSelect: "none",
              borderBottom: isThinkingExpanded ? "1px solid rgba(255, 255, 255, 0.06)" : "none",
              background: "rgba(15, 23, 42, 0.4)",
            }}
            onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: isActive ? "#38bdf8" : "#94a3b8",
                  display: "inline-block",
                  animation: isActive ? "blink 1.5s infinite" : "none",
                }}
              />
              <style dangerouslySetInnerHTML={{__html: `
                @keyframes blink {
                  0%, 100% { opacity: 0.3; }
                  50% { opacity: 1; }
                }
              `}} />
              <span style={{ fontSize: "11px", fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                {isActive ? "Swarm Thinking Process" : "Swarm Thinking History"}
              </span>
            </div>
            <span style={{ display: "flex", alignItems: "center", color: "#94a3b8", fontSize: "14px" }}>
              {isThinkingExpanded ? "▼" : "▲"}
            </span>
          </div>

          {isThinkingExpanded && (
            <div
              ref={thinkingContainerRef}
              style={{
                maxHeight: "140px",
                overflowY: "auto",
                padding: "8px 12px",
                fontFamily: "monospace",
                fontSize: "11px",
                color: "#cbd5e1",
                lineHeight: "1.5",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
                backgroundColor: "rgba(15, 23, 42, 0.6)",
              }}
            >
              {thinkingLogs.slice(-8).map((log) => (
                <div key={log.id} style={{ display: "flex", gap: "8px" }}>
                  <span style={{ color: "#64748b" }}>[{log.timestamp.toLocaleTimeString()}]</span>
                  {log.node && (
                    <span style={{ color: "#38bdf8", fontWeight: "bold" }}>
                      [{AGENT_NAMES[log.node] ?? log.node}]
                    </span>
                  )}
                  <span>{log.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Premium Input Bar ── */}
      <div className="chat-input-bar">
        {phase === "completed" ? (
          <button
            onClick={reset}
            className="plan-another-btn"
            style={{
              width: "100%",
              height: "44px",
              borderRadius: "12px",
              background: "#1e293b",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: "0 4px 12px rgba(15, 23, 42, 0.15)",
              border: "1.5px solid #0f172a",
              cursor: "pointer",
              transition: "transform 0.1s, background-color 0.2s",
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.background = "#0f172a";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = "#1e293b";
            }}
            onMouseDown={(e) => {
              e.currentTarget.style.transform = "scale(0.98)";
            }}
            onMouseUp={(e) => {
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Plan Another Trip
          </button>
        ) : (
          <>
            <div
              className={`chat-input-wrap ${inputFocused || inputPrompt ? "chat-input-wrap--focused" : ""}`}
            >
              <textarea
                ref={textareaRef}
                className="chat-input-textarea"
                disabled={isBusy}
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
                placeholder={
                  isBusy
                    ? "Planning in progress…"
                    : "E.g., Plan a 3-day trip to Tokyo focused on street food and temples…"
                }
                rows={1}
              />
              <button
                className={`chat-send-btn-new ${canSend ? "chat-send-btn-new--active" : ""}`}
                onClick={handleSubmitPrompt}
                disabled={!canSend}
                aria-label="Send"
              >
                <SendIcon active={canSend} />
              </button>
            </div>

            <div className="chat-input-footer" style={{ justifyContent: "flex-end" }}>
              <p className="chat-input-hint">
                <kbd>Enter ↵</kbd> to dispatch · <kbd>Shift+Enter</kbd> for newline
              </p>
            </div>
          </>
        )}
      </div>

    </div>
  );
}
