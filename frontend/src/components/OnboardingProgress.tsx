"use client";
import React, { useEffect } from "react";

interface OnboardingProgressProps {
  documentsCount: number;
  messagesCount: number;
  onDismiss: () => void;
}

export default function OnboardingProgress({ documentsCount, messagesCount, onDismiss }: OnboardingProgressProps) {
  const items = [
    { label: "Created account", done: true },
    { label: "Uploaded a document", done: documentsCount > 0 },
    { label: "Asked first question", done: messagesCount > 0 },
  ];

  const allDone = items.every((i) => i.done);

  // BF5: auto-dismiss once all three items are checked. Persist so the
  // checklist never reappears even after document/message counters reset
  // (e.g. switching to a fresh workspace).
  useEffect(() => {
    if (allDone) {
      try { localStorage.setItem("dm.onboarding.dismissed", "true"); } catch {}
      onDismiss();
    }
  }, [allDone, onDismiss]);

  if (allDone) return null;

  return (
    <div
      style={{
        margin: "8px 8px 4px",
        background: "var(--surface-sunken)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "10px 12px",
        position: "relative",
        fontFamily: "var(--font-body)",
      }}
    >
      {/* Dismiss */}
      <button
        onClick={onDismiss}
        aria-label="Dismiss onboarding"
        style={{
          position: "absolute", top: "6px", right: "6px",
          background: "none", border: "none", cursor: "pointer",
          color: "var(--text-tertiary)", fontSize: "14px", lineHeight: 1, padding: "2px",
        }}
      >
        ×
      </button>

      <div style={{ fontSize: "11px", fontWeight: "var(--weight-semibold)", color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "8px" }}>
        Getting started
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {items.map(({ label, done }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: done ? "var(--text-secondary)" : "var(--text-primary)" }}>
            <span style={{ fontSize: "14px", flexShrink: 0 }}>
              {done ? (
                <span style={{ color: "var(--success-text)" }}>✅</span>
              ) : (
                <span style={{ opacity: 0.4 }}>⬜</span>
              )}
            </span>
            <span style={{ textDecoration: done ? "line-through" : "none", opacity: done ? 0.6 : 1 }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
