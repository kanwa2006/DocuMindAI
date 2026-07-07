"use client";

import { useEffect } from "react";

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  {
    section: "NAVIGATION",
    items: [
      { keys: ["⌘", "K"], label: "Command palette" },
      { keys: ["⌘", "B"], label: "Toggle sidebar" },
      { keys: ["⌘", "D"], label: "Toggle dark / light mode" },
    ],
  },
  {
    section: "CHAT",
    items: [
      { keys: ["⌘", "↵"], label: "Send message" },
      { keys: ["⇧", "↵"], label: "New line in message" },
      { keys: ["⌘", "/"], label: "Open template library" },
    ],
  },
  {
    section: "TEACHER",
    items: [
      { keys: ["⌘", "⇧", "T"], label: "Extract tables" },
    ],
  },
  {
    section: "EXPORT",
    items: [
      { keys: ["⌘", "⇧", "E"], label: "Export chat" },
    ],
  },
  {
    section: "SEARCH",
    items: [
      { keys: ["⌘", "F"], label: "Focus session search" },
    ],
  },
  {
    section: "GENERAL",
    items: [
      { keys: ["?"], label: "Show this shortcuts panel" },
      { keys: ["Esc"], label: "Close any open panel" },
    ],
  },
];

function KbdKey({ k }: { k: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      minWidth: "22px", height: "22px", padding: "0 5px",
      background: "var(--surface-sunken)", border: "1px solid var(--border-default)",
      borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "11px",
      color: "var(--text-secondary)", lineHeight: 1,
    }}>
      {k}
    </span>
  );
}

export default function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 500, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div
        style={{ width: "min(480px, 95vw)", background: "var(--surface-overlay)", border: "1px solid var(--border-default)", borderRadius: "16px", boxShadow: "var(--shadow-2xl)", overflow: "hidden" }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)" }}>
          <span style={{ fontFamily: "var(--font-body)", fontSize: "15px", fontWeight: 600, color: "var(--text-primary)" }}>⌨️ Keyboard Shortcuts</span>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: "18px", padding: "2px", lineHeight: 1 }}>✕</button>
        </div>

        {/* Shortcuts grid */}
        <div style={{ padding: "16px 20px", maxHeight: "60vh", overflowY: "auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px 16px" }}>
            {SHORTCUTS.map((sec) => (
              <div key={sec.section}>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-tertiary)", marginBottom: "8px" }}>
                  {sec.section}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {sec.items.map((item, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
                      <span style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)", flex: 1 }}>{item.label}</span>
                      <div style={{ display: "flex", gap: "3px", flexShrink: 0 }}>
                        {item.keys.map((k, ki) => <KbdKey key={ki} k={k} />)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border-subtle)", fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)", textAlign: "center" }}>
          Shortcuts work everywhere except when typing in a text field
        </div>
      </div>
    </div>
  );
}
