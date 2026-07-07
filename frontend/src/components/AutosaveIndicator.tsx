"use client";

import { useEffect, useRef, useState } from "react";

type SaveState = "idle" | "saving" | "saved" | "error";

interface AutosaveIndicatorProps {}

export default function AutosaveIndicator(_: AutosaveIndicatorProps) {
  const [state, setState] = useState<SaveState>("idle");
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onSaving = () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      setState("saving");
    };
    const onSaved = () => {
      setState("saved");
      hideTimerRef.current = setTimeout(() => setState("idle"), 3000);
    };
    const onError = () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      setState("error");
    };

    window.addEventListener("autosave:saving", onSaving);
    window.addEventListener("autosave:saved", onSaved);
    window.addEventListener("autosave:error", onError);
    return () => {
      window.removeEventListener("autosave:saving", onSaving);
      window.removeEventListener("autosave:saved", onSaved);
      window.removeEventListener("autosave:error", onError);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, []);

  if (state === "idle") return null;

  const config = {
    saving: { text: "Saving...", color: "var(--text-tertiary)", icon: "⟳" },
    saved:  { text: "All changes saved ✓", color: "var(--text-tertiary)", icon: "" },
    error:  { text: "⚠ Save failed", color: "var(--amber-600, #d97706)", icon: "" },
  }[state];

  return (
    <div
      aria-live="polite"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        fontFamily: "var(--font-body)",
        fontSize: "12px",
        color: config.color,
        transition: "opacity 300ms",
        opacity: 1,
        userSelect: "none",
      }}
    >
      {state === "saving" && (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: "spin 1s linear infinite" }}>
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
      )}
      {config.text}
    </div>
  );
}
