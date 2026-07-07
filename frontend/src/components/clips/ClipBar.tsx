"use client";

import { useEffect, useRef } from "react";

interface ClipBarProps {
  rect: DOMRect;
  onAddToSession: () => void;
  onDismiss: () => void;
}

export function ClipBar({ rect, onAddToSession, onDismiss }: ClipBarProps) {
  const barRef = useRef<HTMLDivElement>(null);

  // Position: 8px above the selection, horizontally centered
  const barHeight = 40;
  const gap = 8;
  let top = rect.top - barHeight - gap;
  // If too close to top of viewport, show below instead
  if (top < 4) top = rect.bottom + gap;
  const left = rect.left + rect.width / 2;

  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        onDismiss();
      }
    };

    const handleSelectionChange = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) onDismiss();
    };

    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("selectionchange", handleSelectionChange);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("selectionchange", handleSelectionChange);
    };
  }, [onDismiss]);

  return (
    <div
      ref={barRef}
      style={{
        position: "fixed",
        top,
        left,
        transform: "translateX(-50%)",
        zIndex: 9999,
        background: "var(--surface-overlay, #18181b)",
        border: "1px solid var(--border-default)",
        borderRadius: "999px",
        padding: "4px 12px 4px 8px",
        boxShadow: "var(--shadow-lg, 0 8px 24px rgba(0,0,0,0.3))",
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        whiteSpace: "nowrap",
        fontSize: "12px",
        fontWeight: 500,
        fontFamily: "var(--font-body)",
        userSelect: "none",
        pointerEvents: "auto",
      }}
    >
      <span style={{ fontSize: "14px", color: "var(--text-secondary)" }}>📋</span>
      <button
        onClick={onAddToSession}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--text-primary)",
          fontFamily: "var(--font-body)",
          fontSize: "12px",
          fontWeight: 500,
          padding: 0,
        }}
      >
        Add to session
      </button>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--text-tertiary)",
          fontFamily: "var(--font-body)",
          fontSize: "14px",
          padding: 0,
          lineHeight: 1,
          display: "flex",
          alignItems: "center",
        }}
      >
        ✕
      </button>
    </div>
  );
}
