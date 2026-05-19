"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "react-hot-toast";

type Phase = "focus" | "short_break" | "long_break";

interface TimerState {
  phase: Phase;
  minutesLeft: number;
  secondsLeft: number;
  sessionCount: number;
  isRunning: boolean;
}

const PHASE_DURATIONS: Record<Phase, number> = {
  focus: 25,
  short_break: 5,
  long_break: 15,
};

const PHASE_LABELS: Record<Phase, string> = {
  focus: "Focus",
  short_break: "Short Break",
  long_break: "Long Break",
};

const STORAGE_KEY = "pomodoro_state";

function loadState(): TimerState {
  if (typeof window === "undefined") return defaultState();
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved) as TimerState;
  } catch {}
  return defaultState();
}

function defaultState(): TimerState {
  return {
    phase: "focus",
    minutesLeft: PHASE_DURATIONS.focus,
    secondsLeft: 0,
    sessionCount: 0,
    isRunning: false,
  };
}

export default function PomodoroTimer() {
  const [state, setState] = useState<TimerState>(loadState);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const saveState = useCallback((s: TimerState) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch {}
  }, []);

  const totalSeconds = (s: TimerState) =>
    PHASE_DURATIONS[s.phase] * 60;
  const elapsedSeconds = (s: TimerState) =>
    totalSeconds(s) - s.minutesLeft * 60 - s.secondsLeft;

  // SVG ring
  const RADIUS = 16;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
  const progress = elapsedSeconds(state) / totalSeconds(state);
  const dashOffset = CIRCUMFERENCE * (1 - Math.min(progress, 1));

  const advancePhase = useCallback((current: TimerState): TimerState => {
    let nextPhase: Phase;
    let nextSession = current.sessionCount;

    if (current.phase === "focus") {
      nextSession = current.sessionCount + 1;
      nextPhase = nextSession % 4 === 0 ? "long_break" : "short_break";
      toast.success(nextPhase === "long_break" ? "Long break time! ☕" : "Time for a break! ☕");
    } else {
      nextPhase = "focus";
      toast.success("Back to work! 📖");
    }

    return {
      phase: nextPhase,
      minutesLeft: PHASE_DURATIONS[nextPhase],
      secondsLeft: 0,
      sessionCount: nextSession,
      isRunning: false,
    };
  }, []);

  useEffect(() => {
    if (!state.isRunning) {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      return;
    }
    intervalRef.current = setInterval(() => {
      setState((prev) => {
        let next: TimerState;
        if (prev.secondsLeft > 0) {
          next = { ...prev, secondsLeft: prev.secondsLeft - 1 };
        } else if (prev.minutesLeft > 0) {
          next = { ...prev, minutesLeft: prev.minutesLeft - 1, secondsLeft: 59 };
        } else {
          next = advancePhase(prev);
        }
        saveState(next);
        return next;
      });
    }, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [state.isRunning, advancePhase, saveState]);

  const toggle = () => setState((prev) => { const next = { ...prev, isRunning: !prev.isRunning }; saveState(next); return next; });
  const reset = () => {
    const next: TimerState = { ...state, minutesLeft: PHASE_DURATIONS[state.phase], secondsLeft: 0, isRunning: false };
    setState(next); saveState(next);
  };

  const mm = String(state.minutesLeft).padStart(2, "0");
  const ss = String(state.secondsLeft).padStart(2, "0");

  const ringColor = state.phase === "focus"
    ? "var(--brand)"
    : state.phase === "short_break"
    ? "var(--success-text, #22c55e)"
    : "var(--warning-text, #f59e0b)";

  const btnStyle: React.CSSProperties = {
    width: "28px", height: "28px", border: "1px solid var(--border-default)",
    borderRadius: "6px", background: "none", cursor: "pointer",
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    fontSize: "14px", color: "var(--text-secondary)", transition: "border-color 100ms",
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: "10px",
      background: "var(--surface-raised)", border: "1px solid var(--border-default)",
      borderRadius: "10px", padding: "6px 12px", userSelect: "none",
    }}>
      {/* SVG progress ring */}
      <svg width="40" height="40" viewBox="0 0 40 40" style={{ flexShrink: 0 }}>
        <circle cx="20" cy="20" r={RADIUS} fill="none" stroke="var(--border-subtle)" strokeWidth="3" />
        <circle
          cx="20" cy="20" r={RADIUS} fill="none"
          stroke={ringColor} strokeWidth="3"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{ transform: "rotate(-90deg)", transformOrigin: "center", transition: "stroke-dashoffset 0.9s linear" }}
        />
      </svg>

      {/* Time + phase */}
      <div style={{ lineHeight: 1 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)", letterSpacing: "0.05em" }}>
          {mm}:{ss}
        </div>
        <div style={{ fontFamily: "var(--font-body)", fontSize: "10px", color: "var(--text-tertiary)", marginTop: "2px" }}>
          {PHASE_LABELS[state.phase]} · Session {state.sessionCount + 1}
        </div>
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: "4px" }}>
        <button onClick={toggle} style={btnStyle} title={state.isRunning ? "Pause" : "Start"}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}>
          {state.isRunning ? "⏸" : "▶"}
        </button>
        <button onClick={reset} style={btnStyle} title="Reset"
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}>
          ⟳
        </button>
      </div>
    </div>
  );
}
