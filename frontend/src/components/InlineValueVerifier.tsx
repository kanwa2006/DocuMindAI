"use client";

/**
 * Phase 9-G2 — Inline Value Verifier (Finance workspace)
 *
 * After a Finance workspace AI message is fully streamed, this hook
 * scans the rendered message text for monetary/percentage values and
 * returns annotated segments that the parent component renders as
 * clickable `.finance-value-chip` spans.
 *
 * On chip click:
 *   1. Look up the value in the message's citation data.
 *   2. If found: call onVerifyValue(citation) — parent opens DocumentPreviewPanel.
 *   3. If not found: show a small "no source span" tooltip.
 *
 * Usage:
 *   const { annotate } = useInlineValueVerifier({ citations, onVerifyValue });
 *   // annotate(rawText) → React nodes with chips interspersed
 */

import { useCallback, useState, useRef } from "react";

export interface Citation {
  id: string;
  label: string;
  page_number?: number;
  raw_value?: string;
}

export interface InlineValueVerifierProps {
  citations?: Citation[];
  onVerifyValue?: (citation: Citation) => void;
}

// Patterns that match financial figures in Indian/global notation:
//   ₹ 12,345.67 crore | Rs 500 lakh | 24.5% | $1.2 million | 42 billion
const VALUE_PATTERN =
  /((?:₹|Rs\.?\s*)[\d,]+(?:\.\d+)?\s*(?:crore|cr\.?|lakh|lakhs|thousand)?|\b\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\s*(?:%|million|billion|crore|lakh|lakhs|cr\.?))/gi;

export interface AnnotatedSegment {
  text: string;
  isValue: boolean;
  matchedCitation?: Citation;
}

function annotateText(text: string, citations: Citation[]): AnnotatedSegment[] {
  const segments: AnnotatedSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(VALUE_PATTERN.source, "gi");

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, match.index), isValue: false });
    }

    const valueText = match[0];
    // Try to match this text to one of the citations by raw_value or label
    const citation = citations.find(
      (c) =>
        (c.raw_value && valueText.includes(c.raw_value)) ||
        (c.label && c.label.includes(valueText.replace(/\s+/g, "")))
    );
    segments.push({ text: valueText, isValue: true, matchedCitation: citation });
    lastIndex = re.lastIndex;
  }

  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), isValue: false });
  }

  return segments;
}

export function useInlineValueVerifier({
  citations = [],
  onVerifyValue,
}: InlineValueVerifierProps) {
  const annotate = useCallback(
    (text: string): AnnotatedSegment[] => annotateText(text, citations),
    [citations]
  );

  return { annotate };
}

// ── FinanceValueChip — renders a single clickable financial value ────────────

interface FinanceValueChipProps {
  text: string;
  citation?: Citation;
  onVerify?: (citation: Citation) => void;
}

export function FinanceValueChip({ text, citation, onVerify }: FinanceValueChipProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const chipRef = useRef<HTMLSpanElement>(null);

  function handleClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (citation && onVerify) {
      onVerify(citation);
    } else {
      setShowTooltip(true);
      setTimeout(() => setShowTooltip(false), 3000);
    }
  }

  return (
    <span style={{ position: "relative", display: "inline" }}>
      <span
        ref={chipRef}
        className="finance-value-chip"
        role="button"
        tabIndex={0}
        aria-label={`Verify source for ${text}`}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") handleClick(e as unknown as React.MouseEvent);
        }}
        style={{
          cursor: "pointer",
          borderBottom: "1px dashed var(--brand, #6366f1)",
          color: "var(--brand, #6366f1)",
          transition: "background 0.1s, border-radius 0.1s",
        }}
        onMouseEnter={(e) =>
          Object.assign((e.currentTarget as HTMLSpanElement).style, {
            background: "var(--brand-ghost, rgba(99,102,241,0.08))",
            borderRadius: "3px",
          })
        }
        onMouseLeave={(e) =>
          Object.assign((e.currentTarget as HTMLSpanElement).style, {
            background: "transparent",
            borderRadius: "0",
          })
        }
      >
        {text}
      </span>

      {showTooltip && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            bottom: "calc(100% + 6px)",
            left: "50%",
            transform: "translateX(-50%)",
            background: "var(--surface-overlay, #1f2937)",
            color: "#fff",
            fontSize: 11,
            borderRadius: 6,
            padding: "5px 8px",
            whiteSpace: "nowrap",
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            zIndex: 100,
            pointerEvents: "none",
            animation: "fadeIn 0.2s ease",
          }}
        >
          No source span found. Verify against original document.
        </span>
      )}
    </span>
  );
}

// ── AnnotatedMessage — renders a full message with Finance value chips ────────

export interface AnnotatedMessageProps {
  text: string;
  citations?: Citation[];
  onVerifyValue?: (citation: Citation) => void;
}

export default function AnnotatedMessage({
  text,
  citations = [],
  onVerifyValue,
}: AnnotatedMessageProps) {
  const { annotate } = useInlineValueVerifier({ citations, onVerifyValue });
  const segments = annotate(text);

  return (
    <>
      {segments.map((seg, i) =>
        seg.isValue ? (
          <FinanceValueChip
            key={i}
            text={seg.text}
            citation={seg.matchedCitation}
            onVerify={onVerifyValue}
          />
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </>
  );
}
