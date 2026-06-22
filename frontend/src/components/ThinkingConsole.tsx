"use client";

import React, { useEffect, useRef } from "react";
import { LogMessage } from "../hooks/useEventStream";

interface ThinkingConsoleProps {
  logs: LogMessage[];
  activeNode: string | null;
}

export default function ThinkingConsole({ logs, activeNode }: ThinkingConsoleProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll to bottom on new logs */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  /* Map log type to left-border class */
  const getLineClass = (type: LogMessage["type"]) => {
    switch (type) {
      case "system": return "log-line log-line--system";
      case "agent":  return "log-line log-line--agent";
      case "error":  return "log-line log-line--error";
      default:       return "log-line log-line--log";
    }
  };

  /* Map log type to text modifier class */
  const getTextClass = (type: LogMessage["type"]) => {
    switch (type) {
      case "system": return "log-text log-text--system";
      case "error":  return "log-text log-text--error";
      default:       return "log-text";
    }
  };

  const formatTime = (d: Date) =>
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  return (
    <div className="thinking-console">

      {/* ── Header ── */}
      <div className="console-header">
        <div className="console-header-left">
          <span className={`console-status-dot ${activeNode ? "console-status-dot--active" : ""}`} />
          <span className="section-label">Agent Reasoning</span>
        </div>
        <div>
          {activeNode ? (
            <span className="console-active-node">{activeNode}</span>
          ) : (
            <span className="console-idle-label">idle</span>
          )}
        </div>
      </div>

      {/* ── Logs Feed ── */}
      <div className="console-logs">
        {logs.length === 0 ? (
          <div className="console-empty">
            <p className="console-empty-text">Waiting for agent activation…</p>
            <p className="console-empty-hint">Submit a destination to begin.</p>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className={getLineClass(log.type)}>
              <div className="log-line-indent" />
              {log.node && (
                <span className="log-node-badge">{log.node}</span>
              )}
              <span className={getTextClass(log.type)}>{log.text}</span>
              <span className="log-timestamp">{formatTime(log.timestamp)}</span>
            </div>
          ))
        )}

        {/* Typing indicator while a node is active */}
        {activeNode && (
          <div className="console-typing-indicator">
            <span>{activeNode} thinking</span>
            <div className="typing-dots">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

    </div>
  );
}
