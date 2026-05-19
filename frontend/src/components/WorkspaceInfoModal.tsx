"use client";

/**
 * Phase 9-E + 9-G3 — Workspace Info Modal
 *
 * Opened by the ℹ button in the navbar (right of workspace dropdown).
 * Shows plain-language description of what the workspace does/doesn't do.
 * The grounding-constraint amber card is REQUIRED in ALL workspace variants.
 * The phrase "answers ONLY from your uploaded documents" must appear verbatim.
 */

import { useEffect, useRef } from "react";

export interface WorkspaceInfoModalProps {
  workspaceType: string;
  onClose: () => void;
}

interface WorkspaceContent {
  icon: string;
  title: string;
  description: string;
  canDo: string[];
  cannotDo: string[];
  extraDisclaimer?: string;
}

const WORKSPACE_INFO: Record<string, WorkspaceContent> = {
  general: {
    icon: "📄",
    title: "General",
    description:
      "A flexible workspace for analysing any documents you upload. Ask questions, extract information, and summarise content from your files.",
    canDo: [
      "Answer questions from your uploaded documents",
      "Summarise, compare, and extract information",
      "Cite the exact source page for every claim",
    ],
    cannotDo: [
      "Access the internet or external databases",
      "Answer questions without a supporting document",
    ],
  },
  legal: {
    icon: "⚖️",
    title: "Legal",
    description:
      "Analyses contracts and legal documents you upload. Identifies risks, flags non-standard clauses, and compares provisions across multiple documents.",
    canDo: [
      "Identify risk clauses and flag non-standard terms",
      "Compare provisions across multiple contracts",
      "Extract key obligations, dates, and parties",
    ],
    cannotDo: [
      "Provide legal advice or opinion",
      "Access case law, legislation, or external legal databases",
    ],
    extraDisclaimer:
      "This workspace does not constitute legal advice. Always consult a qualified solicitor before relying on any analysis.",
  },
  finance: {
    icon: "📊",
    title: "Finance",
    description:
      "Extracts and validates financial data from your documents. Computes financial ratios using Python (not AI estimation) for accuracy.",
    canDo: [
      "Extract revenue, profit, and balance-sheet figures",
      "Compute ratios using Python (not AI estimation)",
      "Flag anomalies and audit findings in financial statements",
    ],
    cannotDo: [
      "Access live market data or accounting systems",
      "Provide investment advice or valuations",
    ],
    extraDisclaimer:
      "All financial ratios shown are computed by Python from extracted figures. They are not estimates. Verify against source documents before making financial decisions.",
  },
  hr: {
    icon: "👥",
    title: "HR",
    description:
      "Analyses HR documents such as CVs, job descriptions, and employment contracts. Helps match candidates to roles based on your uploaded documents.",
    canDo: [
      "Match candidate profiles to job requirements",
      "Extract skills, experience, and qualifications from CVs",
      "Identify compliance issues in employment contracts",
    ],
    cannotDo: [
      "Access external job boards or candidate databases",
      "Make hiring decisions — analysis is advisory only",
    ],
  },
  teacher: {
    icon: "🎓",
    title: "Teacher",
    description:
      "Assists educators in creating exam papers, lesson materials, and assessments from uploaded course content.",
    canDo: [
      "Generate exam questions from your uploaded materials",
      "Create structured question papers with mark schemes",
      "Summarise course content for revision aids",
    ],
    cannotDo: [
      "Access external curriculum resources or textbooks",
      "Guarantee exam-board alignment without source documents",
    ],
  },
  student: {
    icon: "📚",
    title: "Student",
    description:
      "Helps students understand, revise, and test themselves on uploaded study materials using flashcards and quizzes.",
    canDo: [
      "Create flashcards and quizzes from your notes",
      "Explain concepts using your uploaded materials",
      "Test recall with spaced-repetition sessions",
    ],
    cannotDo: [
      "Access external study resources or syllabuses",
      "Complete assignments on your behalf",
    ],
  },
  research: {
    icon: "🔬",
    title: "Research",
    description:
      "Supports literature review, synthesis, and contradiction detection across research papers you upload.",
    canDo: [
      "Synthesise findings across multiple papers",
      "Detect contradictions between sources",
      "Generate structured citation references",
    ],
    cannotDo: [
      "Access external databases (PubMed, arXiv) or paywalled journals",
      "Produce original research — only analyses what you upload",
    ],
  },
};

const FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function WorkspaceInfoModal({
  workspaceType,
  onClose,
}: WorkspaceInfoModalProps) {
  const info = WORKSPACE_INFO[workspaceType] ?? WORKSPACE_INFO.general;
  const dialogRef = useRef<HTMLDivElement>(null);
  const prevFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    prevFocusRef.current = document.activeElement as HTMLElement;
    return () => prevFocusRef.current?.focus();
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const els = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE));
    els[0]?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab") return;
      const first = els[0];
      const last = els[els.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last?.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="wsinfo-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.4)",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={dialogRef}
        className="modal"
        style={{ width: 480, maxHeight: "90vh", overflowY: "auto" }}
      >
        {/* Header */}
        <div className="modal__header">
          <h2
            id="wsinfo-modal-title"
            style={{
              fontFamily: "Instrument Serif, serif",
              fontSize: 20,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span aria-hidden="true">{info.icon}</span>
            {info.title} Workspace
          </h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        {/* Description */}
        <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 16, lineHeight: 1.6 }}>
          {info.description}
        </p>

        {/* What it can do */}
        <div style={{ marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>What it can do</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 4 }}>
            {info.canDo.map((item, i) => (
              <li key={i} style={{ fontSize: 13, display: "flex", gap: 6, alignItems: "flex-start" }}>
                <span aria-hidden="true" style={{ color: "var(--success, #16a34a)", flexShrink: 0 }}>✓</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* What it cannot do */}
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>What it cannot do</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 4 }}>
            {info.cannotDo.map((item, i) => (
              <li key={i} style={{ fontSize: 13, display: "flex", gap: 6, alignItems: "flex-start" }}>
                <span aria-hidden="true" style={{ color: "var(--text-tertiary)", flexShrink: 0 }}>✗</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Grounding constraint amber card — REQUIRED in ALL workspaces */}
        <div
          role="note"
          aria-label="Grounding constraint"
          style={{
            background: "var(--warning-bg, #fffbeb)",
            border: "1px solid var(--warning-border, #d97706)",
            borderRadius: 8,
            padding: "10px 12px",
            marginBottom: 16,
            fontSize: 13,
            color: "var(--warning-text, #92400e)",
            lineHeight: 1.55,
          }}
        >
          <strong>⚡ Grounding constraint:</strong> This workspace{" "}
          <strong>answers ONLY from your uploaded documents</strong>. It does not access
          the internet, legal databases, or financial APIs.
          {info.extraDisclaimer && (
            <span> {info.extraDisclaimer}</span>
          )}
        </div>

        {/* Close */}
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-primary" onClick={onClose}>
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
