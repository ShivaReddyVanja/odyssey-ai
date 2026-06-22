"use client";

import React, { useState, useEffect, useRef } from "react";
import { LogMessage } from "../hooks/useEventStream";

/* ─── Types ─────────────────────────────────────────────────────────────── */

interface ChatPanelProps {
  phase: string;
  logs: LogMessage[];
  activeNode: string | null;
  interruptedQuestions: string[] | null;
  startPlanning: (prompt: string) => void;
  submitClarification: (answers: Record<string, string>) => void;
  reset: () => void;
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
  "A relaxing week in Bali, emphasizing wellness and nature.",
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
  activeNode,
  interruptedQuestions,
  startPlanning,
  submitClarification,
  reset,
}: ChatPanelProps) {
  const [inputPrompt, setInputPrompt] = useState("");
  const [inputFocused, setInputFocused] = useState(false);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, string>>({});
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* Auto-scroll to bottom */
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, interruptedQuestions, activeNode]);

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
      {/* Visual Plug Connector in the middle of the left border */}
      <div
        id="chat-input-plug-connector"
        className="chat-plug-connector"
        style={{
          position: "absolute",
          left: "-8px",
          top: "50%",
          transform: "translateY(-50%)",
          width: "16px",
          height: "20px",
          backgroundColor: "#1e293b",
          borderRadius: "3px 0 0 3px",
          borderLeft: "2px solid #38bdf8",
          boxShadow: phase !== "idle"
            ? "0 0 10px rgba(56, 189, 248, 0.7), 0 0 20px rgba(244, 63, 94, 0.4)"
            : "0 0 6px rgba(56, 189, 248, 0.3)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
          transition: "box-shadow 0.3s",
        }}
      >
        {/* Double pins inside plug */}
        <div style={{ width: "4px", height: "2px", backgroundColor: "#94a3b8", borderRadius: "1px 0 0 1px", marginBottom: "2px" }} />
        <div style={{ width: "4px", height: "2px", backgroundColor: "#94a3b8", borderRadius: "1px 0 0 1px" }} />
      </div>

      {/* ── Header ── */}
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon">
            <TerminalIcon />
          </div>
          <div>
            <div className="chat-header-title">Interaction Console</div>
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
          /* Empty state — matches the NomadGraph console aesthetic */
          <div className="chat-empty-state">
            <div className="chat-empty-sparkle">
              <SparkleIcon />
            </div>
            <h3 className="chat-empty-title">Design Your Expedition</h3>
            <p className="chat-empty-desc">
              Describe your ideal journey. The NomadGraph swarm will autonomously research, plan, and orchestrate a comprehensive itinerary.
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

        <div ref={chatBottomRef} />
      </div>

      {/* ── Premium Input Bar ── */}
      <div className="chat-input-bar">
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

        <div className="chat-input-footer">
          <div className="chat-input-footer-left">
            <span className="chat-model-badge">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 9h6M9 12h6M9 15h4" /></svg>
              GPT-4 Core
            </span>
            <span className="chat-model-badge">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>
              Live Data
            </span>
          </div>
          <p className="chat-input-hint">
            <kbd>Enter ↵</kbd> to dispatch · <kbd>Shift+Enter</kbd> for newline
          </p>
        </div>
      </div>

    </div>
  );
}
