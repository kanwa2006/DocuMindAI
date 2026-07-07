"use client";

import { memo } from "react";

export interface TrustFactor {
  name: string;
  weight: number;
  score: number;
}

export interface TrustContradiction {
  doc_a: { filename: string; page: number; text: string };
  doc_b: { filename: string; page: number; text: string };
}

export interface TrustReport {
  final_score: number;
  level: "HIGH" | "MEDIUM" | "LOW";
  evidence_items: string[];
  warnings: string[];
  factors: TrustFactor[];
  contradictions: TrustContradiction[];
  summary: string;
}

interface TrustScoreBadgeProps {
  trust: TrustReport;
  expanded: boolean;
  onToggle: () => void;
}

export const TRUST_LEVEL_CFG = {
  HIGH: {
    color: "#16a34a",
    bg: "#f0fdf4",
    border: "#bbf7d0",
    icon: "✅",
    label: "High Confidence",
  },
  MEDIUM: {
    color: "#b45309",
    bg: "#fffbeb",
    border: "#fde68a",
    icon: "⚠️",
    label: "Moderate — Review Cited Pages",
  },
  LOW: {
    color: "#dc2626",
    bg: "#fff1f2",
    border: "#fecdd3",
    icon: "⛔",
    label: "Low — Verify Manually",
  },
} as const;

export const TrustScoreBadge = memo(function TrustScoreBadge({
  trust,
  expanded,
  onToggle,
}: TrustScoreBadgeProps) {
  if (!trust || trust.final_score === undefined) return null;

  const cfg = TRUST_LEVEL_CFG[trust.level] ?? TRUST_LEVEL_CFG.MEDIUM;
  const pct = Math.min(100, Math.max(0, Math.round(trust.final_score)));

  return (
    <button
      onClick={onToggle}
      aria-expanded={expanded}
      aria-label={`Trust Score: ${pct}/100 — ${cfg.label}. Click to ${expanded ? "collapse" : "expand"} details.`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        padding: "4px 10px",
        borderRadius: "8px",
        cursor: "pointer",
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        color: cfg.color,
        fontFamily: "var(--font-body)",
        fontSize: "12px",
        fontWeight: 500,
        transition: "opacity 120ms",
        userSelect: "none",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.opacity = "0.8";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.opacity = "1";
      }}
    >
      {/* Score bar */}
      <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
        <div
          style={{
            width: "60px",
            height: "6px",
            background: `${cfg.color}33`,
            borderRadius: "3px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${pct}%`,
              height: "100%",
              background: cfg.color,
              borderRadius: "3px",
              transition: "width 300ms ease",
            }}
          />
        </div>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            fontWeight: 600,
            minWidth: "44px",
          }}
        >
          {pct} / 100
        </span>
      </div>
      <span>{cfg.icon}</span>
      <span>{cfg.label}</span>
      <span style={{ fontSize: "10px", opacity: 0.7 }}>{expanded ? "▲" : "▼"}</span>
    </button>
  );
});
