"use client";

import { useState, useRef } from "react";

export interface CitationData {
  filename: string;
  page_number: number;
  text_content: string;
  source_index: number;
}

interface CitedSentenceProps {
  children: React.ReactNode;
  citation: CitationData;
}

function CitedSentence({ children, citation }: CitedSentenceProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const spanRef = useRef<HTMLSpanElement>(null);

  const snippet = citation.text_content
    ? citation.text_content.slice(0, 120) + (citation.text_content.length > 120 ? "…" : "")
    : "";

  return (
    <span
      ref={spanRef}
      style={{
        position: "relative",
        textDecoration: "underline",
        textDecorationStyle: "dotted",
        textDecorationColor: "rgba(var(--brand-rgb, 59, 130, 246), 0.4)",
        textUnderlineOffset: "3px",
        cursor: "help",
      }}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {children}
      {showTooltip && (
        <span
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "0",
            zIndex: 100,
            maxWidth: "300px",
            minWidth: "200px",
            background: "var(--surface-raised)",
            border: "1px solid var(--border-default)",
            borderRadius: "10px",
            boxShadow: "var(--shadow-lg)",
            padding: "10px 12px",
            pointerEvents: "none",
            whiteSpace: "normal",
            lineHeight: 1.5,
          }}
        >
          <span style={{ display: "block", fontFamily: "var(--font-body)", fontSize: "11px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
            📄 {citation.filename} · Page {citation.page_number}
          </span>
          {snippet && (
            <span style={{ display: "block", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)", fontStyle: "italic" }}>
              &ldquo;{snippet}&rdquo;
            </span>
          )}
        </span>
      )}
    </span>
  );
}

interface SentenceMap {
  sentence_start: number;
  sentence_end: number;
  source_index: number;
}

interface CitationHighlighterProps {
  text: string;
  sentenceMap: SentenceMap[];
  citations: CitationData[];
}

export default function CitationHighlighter({ text, sentenceMap, citations }: CitationHighlighterProps) {
  if (!sentenceMap || sentenceMap.length === 0) {
    return <span>{text}</span>;
  }

  // Build segments: non-cited and cited
  type Segment = { start: number; end: number; cited: boolean; sourceIndex?: number };
  const segments: Segment[] = [];
  let pos = 0;

  const sorted = [...sentenceMap].sort((a, b) => a.sentence_start - b.sentence_start);

  for (const entry of sorted) {
    if (entry.sentence_start > pos) {
      segments.push({ start: pos, end: entry.sentence_start, cited: false });
    }
    segments.push({ start: entry.sentence_start, end: entry.sentence_end, cited: true, sourceIndex: entry.source_index });
    pos = entry.sentence_end;
  }
  if (pos < text.length) {
    segments.push({ start: pos, end: text.length, cited: false });
  }

  return (
    <>
      {segments.map((seg, i) => {
        const chunk = text.slice(seg.start, seg.end);
        if (!seg.cited || seg.sourceIndex === undefined) {
          return <span key={i}>{chunk}</span>;
        }
        const citation = citations[seg.sourceIndex];
        if (!citation) return <span key={i}>{chunk}</span>;
        return (
          <CitedSentence key={i} citation={citation}>
            {chunk}
          </CitedSentence>
        );
      })}
    </>
  );
}
