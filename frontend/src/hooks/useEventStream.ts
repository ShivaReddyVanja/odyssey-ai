import { useState, useCallback, useRef } from "react";

export interface Location {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
}

export interface Place {
  type: "place";
  id: string;
  name: string;
  category: "food" | "stay" | "sightseeing";
  location: Location;
  rating?: number;
  cost_estimate?: number;
  description: string;
  photo_url?: string;
}

export interface TransitOption {
  type: "transit";
  id: string;
  origin: string;
  destination: string;
  departure_time?: string;
  arrival_time?: string;
  mode: "flight" | "train" | "bus" | "car_rental" | "walking" | "driving" | "transit";
  duration_minutes: number;
  estimated_price: number;
  carrier?: string;
}

export type ScheduleItem = Place | TransitOption;

export interface DayPlan {
  day_number: number;
  date: string;
  schedule: ScheduleItem[];
}

export interface FullItinerary {
  destination: string;
  duration_days: number;
  theme: string;
  start_date: string;
  days: DayPlan[];
}

export type StreamPhase = "idle" | "validating" | "clarifying" | "planning" | "discovering" | "compiling" | "completed" | "error";

export interface LogMessage {
  id: string;
  text: string;
  timestamp: Date;
  type: "log" | "system" | "error" | "agent" | "user";
  node?: string;
}

export interface CandidateDiscovery {
  category: string;
  candidates: (Place | TransitOption)[];
  timestamp: number;
}

export function useEventStream() {
  const [phase, setPhase] = useState<StreamPhase>("idle");
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Record<string, (Place | TransitOption)[]>>({
    transit: [],
    accommodation: [],
    food: [],
    activities: [],
  });
  const [finalItinerary, setFinalItinerary] = useState<FullItinerary | null>(null);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  const [interruptedQuestions, setInterruptedQuestions] = useState<string[] | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [lastDiscovery, setLastDiscovery] = useState<CandidateDiscovery | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const addLog = useCallback((text: string, type: "log" | "system" | "error" | "agent" | "user" = "log", node?: string) => {
    setLogs((prev) => [
      ...prev,
      {
        id: Math.random().toString(36).substring(2, 9),
        text,
        timestamp: new Date(),
        type,
        node: node || undefined,
      },
    ]);
  }, []);

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setPhase("idle");
    setLogs([]);
    setActiveNode(null);
    setCandidates({
      transit: [],
      accommodation: [],
      food: [],
      activities: [],
    });
    setFinalItinerary(null);
    setValidationWarnings([]);
    setInterruptedQuestions(null);
    setThreadId(null);
    setLastDiscovery(null);
  }, []);

  const processStream = async (url: string, requestBody: any) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      addLog("Connecting to agent planning stream...", "system");
      
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP error ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body received from stream.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last partial line in the buffer
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data:")) continue;

          const jsonStr = trimmed.replace(/^data:\s*/, "");
          try {
            const event = JSON.parse(jsonStr);
            handleStreamEvent(event);
          } catch (err) {
            console.error("Failed to parse SSE event JSON:", err, jsonStr);
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        addLog("Planning request cancelled by user.", "system");
      } else {
        console.error("Stream reader error:", err);
        addLog(`Error: ${err.message}`, "error");
        setPhase("error");
      }
    }
  };

  const handleStreamEvent = (event: any) => {
    switch (event.type) {
      case "node_start":
        setActiveNode(event.node);
        // Map node to client phases
        if (event.node === "gatekeeper") {
          setPhase("validating");
          addLog("Gatekeeper analyzing travel criteria...", "agent", event.node);
        } else if (event.node === "planner") {
          setPhase("planning");
          addLog("Planner formulating routing strategy...", "agent", event.node);
        } else if (["travel", "stay", "food", "sightseeing"].includes(event.node)) {
          setPhase("discovering");
          addLog(`Gathering options from ${event.node} agents...`, "agent", event.node);
        } else if (event.node === "captain") {
          setPhase("compiling");
          addLog("Captain sequencing days and compiling itinerary...", "agent", event.node);
        }
        break;

      case "node_end":
        setActiveNode((current) => (current === event.node ? null : current));
        break;

      case "log":
        addLog(event.message, "log");
        break;

      case "candidates_discovered":
        setCandidates((prev) => ({
          ...prev,
          [event.category]: event.candidates,
        }));
        setLastDiscovery({
          category: event.category,
          candidates: event.candidates,
          timestamp: Date.now(),
        });
        addLog(`Found ${event.candidates.length} options for ${event.category}!`, "system");
        break;

      case "interrupt":
        setPhase("clarifying");
        setThreadId(event.thread_id);
        setInterruptedQuestions(event.questions);
        addLog("Clarification required to continue planning.", "system");
        break;

      case "completed":
        setPhase("completed");
        setThreadId(event.thread_id);
        setFinalItinerary(event.itinerary);
        setValidationWarnings(event.validation_warnings || []);
        setInterruptedQuestions(null);
        addLog("Travel itinerary successfully compiled!", "system");
        break;

      case "error":
        setPhase("error");
        addLog(event.message, "error");
        break;

      default:
        console.warn("Unknown event type:", event);
    }
  };

  const startPlanning = useCallback((prompt: string) => {
    reset();
    setPhase("validating");
    addLog(prompt, "user");
    // Connect to local backend API
    processStream("http://localhost:8000/api/plan/run", { user_prompt: prompt });
  }, [reset, addLog]);

  const submitClarification = useCallback((answers: Record<string, string>) => {
    if (!threadId) {
      addLog("Error: No active planning session to resume.", "error");
      return;
    }
    setInterruptedQuestions(null);
    setPhase("validating");

    const answersText = Object.entries(answers)
      .map(([q, a]) => `${q}\n  → ${a || "(skipped)"}`)
      .join("\n");
    addLog(`Answers submitted:\n${answersText}`, "user");

    processStream("http://localhost:8000/api/plan/resume", {
      thread_id: threadId,
      answers,
    });
  }, [threadId, addLog]);

  return {
    phase,
    logs,
    activeNode,
    candidates,
    finalItinerary,
    validationWarnings,
    interruptedQuestions,
    threadId,
    lastDiscovery,
    startPlanning,
    submitClarification,
    reset,
  };
}
