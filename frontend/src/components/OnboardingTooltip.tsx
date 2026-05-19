"use client";
import React, { useEffect, useRef, useState } from "react";

interface OnboardingTooltipProps {
  step: 1 | 2 | 3;
  targetSelector: string;
  onNext: () => void;
  onDismiss: () => void;
}

const STEP_TEXT: Record<number, { title: string; body: string; cta: string }> = {
  1: { title: "Choose your workspace", body: "Select Teacher, HR, Student, Legal, Finance, or Research to unlock AI features tuned for your role.", cta: "Got it →" },
  2: { title: "Upload a document", body: "Upload your first document — PDF or DOCX. AI will index it and answer questions from its content only.", cta: "Got it →" },
  3: { title: "Ask a question", body: "Ask any question about your document. AI answers from it only — fully cited.", cta: "Got it!" },
};

export default function OnboardingTooltip({ step, targetSelector, onNext, onDismiss }: OnboardingTooltipProps) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const text = STEP_TEXT[step];

  // Position tooltip below the target element
  useEffect(() => {
    const el = document.querySelector(targetSelector) as HTMLElement | null;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    setPos({ top: rect.bottom + 12, left: rect.left + rect.width / 2 });

    // Add pulsing ring overlay
    el.style.boxShadow = "0 0 0 3px hsl(220,90%,60%), 0 0 0 6px hsl(220,90%,60%/0.25)";
    el.style.borderRadius = "10px";
    el.style.transition = "box-shadow 200ms";

    return () => {
      el.style.boxShadow = "";
      el.style.borderRadius = "";
    };
  }, [targetSelector]);

  // Dismiss on Escape or outside click
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onDismiss(); };
    const onClick = (e: MouseEvent) => {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target as Node)) onDismiss();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [onDismiss]);

  if (!pos || !text) return null;

  return (
    <div
      ref={tooltipRef}
      style={{
        position: "fixed",
        top: pos.top,
        left: pos.left,
        transform: "translateX(-50%)",
        zIndex: 9999,
        background: "var(--surface-overlay)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-xl)",
        padding: "16px 20px",
        maxWidth: "280px",
        fontFamily: "var(--font-body)",
        animation: "fadeIn 150ms var(--ease-decel) both",
      }}
    >
      {/* Arrow pointing up */}
      <div style={{
        position: "absolute", top: "-7px", left: "50%", transform: "translateX(-50%)",
        width: "14px", height: "7px", overflow: "hidden",
      }}>
        <div style={{
          width: "10px", height: "10px", background: "var(--surface-overlay)",
          border: "1px solid var(--border-default)", transform: "rotate(45deg) translate(-2px, 3px)",
          borderRadius: "2px",
        }} />
      </div>

      <div style={{ fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)", marginBottom: "6px" }}>
        {text.title}
      </div>
      <div style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: "var(--leading-relaxed)", marginBottom: "14px" }}>
        {text.body}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button onClick={onDismiss} style={{ background: "none", border: "none", cursor: "pointer", fontSize: "var(--text-xs)", color: "var(--text-tertiary)", padding: 0, fontFamily: "var(--font-body)" }}>
          Skip all
        </button>
        <button
          onClick={onNext}
          style={{
            background: "var(--brand)", color: "#fff", border: "none", cursor: "pointer",
            borderRadius: "var(--radius-md)", padding: "6px 14px",
            fontSize: "var(--text-xs)", fontWeight: "var(--weight-semibold)",
            fontFamily: "var(--font-body)", transition: "filter var(--dur-fast)",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.filter = "brightness(1.1)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.filter = ""; }}
        >
          {text.cta}
        </button>
      </div>
      <div style={{ marginTop: "10px", display: "flex", gap: "5px", justifyContent: "center" }}>
        {[1, 2, 3].map((s) => (
          <div key={s} style={{ width: "6px", height: "6px", borderRadius: "50%", background: s === step ? "var(--brand)" : "var(--border-default)", transition: "background 200ms" }} />
        ))}
      </div>
    </div>
  );
}
