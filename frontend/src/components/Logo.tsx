"use client";
import React from "react";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = {
  sm: { docu: "var(--text-lg)", mind: "var(--text-lg)" },
  md: { docu: "var(--text-xl)", mind: "var(--text-xl)" },
  lg: { docu: "var(--text-2xl)", mind: "var(--text-2xl)" },
};

export function Logo({ size = "md", className = "" }: LogoProps) {
  const s = sizeMap[size];
  return (
    <span
      className={`inline-flex items-baseline gap-0 select-none ${className}`}
      aria-label="DocuMindAI"
    >
      {/* "Docu" — Instrument Serif italic for document trust */}
      <span
        style={{
          fontFamily: "var(--font-display)",
          fontStyle: "italic",
          color: "var(--text-primary)",
          letterSpacing: "var(--tracking-snug)",
          lineHeight: 1,
          fontSize: s.docu,
        }}
      >
        Docu
      </span>
      {/* "Mind" — DM Sans semibold in brand color */}
      <span
        style={{
          fontFamily: "var(--font-body)",
          fontWeight: 600,
          color: "var(--brand)",
          letterSpacing: "var(--tracking-wide)",
          lineHeight: 1,
          fontSize: s.mind,
        }}
      >
        Mind
      </span>
      {/* "AI" — superscript, tertiary */}
      <span
        style={{
          fontFamily: "var(--font-body)",
          fontWeight: 500,
          color: "var(--text-tertiary)",
          fontSize: "0.6em",
          verticalAlign: "super",
          lineHeight: 1,
          letterSpacing: "var(--tracking-widest)",
        }}
      >
        AI
      </span>
    </span>
  );
}

export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* D letterform — document metaphor */}
      <rect
        x="4" y="4" width="14" height="24" rx="3"
        fill="none" stroke="currentColor" strokeWidth="2"
      />
      <path
        d="M4 4 C4 4 14 4 18 10 C22 16 18 28 18 28 L4 28 Z"
        fill="var(--brand-ghost)"
      />
      {/* Dot — the "intelligence" point */}
      <circle cx="24" cy="8" r="4" fill="var(--brand)" />
    </svg>
  );
}
