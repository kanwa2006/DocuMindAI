"use client";

import { useEffect, useRef } from "react";
import EnterpriseDocumentViewer from "./EnterpriseDocumentViewer";
import type { Document } from "@/lib/api";

interface DocumentPreviewPanelProps {
  doc: Document;
  initialPage?: number;
  onClose: () => void;
  onAskAboutSelection?: (text: string) => void;
}

export function DocumentPreviewPanel({
  doc,
  initialPage = 1,
  onClose,
  onAskAboutSelection,
}: DocumentPreviewPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const fileIcon =
    doc.filename?.toLowerCase().endsWith(".pdf")
      ? "📄"
      : doc.filename?.toLowerCase().endsWith(".docx")
      ? "📝"
      : "📄";

  return (
    <div
      ref={panelRef}
      className="panel-enter"
      style={{
        width: "380px",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "var(--surface-raised)",
        borderLeft: "1px solid var(--border-subtle)",
        zIndex: 40,
        overflow: "hidden",
      }}
      aria-label="Document preview panel"
    >
      {/* ── Panel header ── */}
      <div
        style={{
          height: "48px",
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          padding: "0 var(--space-3)",
          borderBottom: "1px solid var(--border-subtle)",
          flexShrink: 0,
        }}
      >
        <button
          onClick={onClose}
          className="btn-icon btn-ghost interactive"
          title="Close preview"
          aria-label="Close document preview"
          style={{ flexShrink: 0 }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>

        <span style={{ flexShrink: 0, fontSize: "16px" }}>{fileIcon}</span>

        <span
          style={{
            flex: 1,
            fontFamily: "var(--font-body)",
            fontSize: "var(--text-xs)",
            color: "var(--text-secondary)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={doc.filename}
        >
          {doc.filename}
        </span>

        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-2xs)",
            color: "var(--text-tertiary)",
            flexShrink: 0,
          }}
        >
          p.{initialPage}
        </span>
      </div>

      {/* ── PDF viewer area ── */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        {doc.status === "READY" ? (
          <EnterpriseDocumentViewer
            pdfUrl={`/api/v1/documents/${doc.id}/file`}
            annotations={[]}
            targetPage={initialPage}
          />
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              gap: "var(--space-3)",
              color: "var(--text-tertiary)",
              fontFamily: "var(--font-body)",
              fontSize: "var(--text-sm)",
            }}
          >
            <span style={{ fontSize: "32px" }}>⏳</span>
            <span>Document is still processing…</span>
            <span
              className="badge badge-warning"
              style={{ fontFamily: "var(--font-body)" }}
            >
              {doc.status}
            </span>
          </div>
        )}
      </div>

      {/* ── Footer — Ask AI about selection ── */}
      {onAskAboutSelection && (
        <div
          style={{
            height: "48px",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            padding: "0 var(--space-3)",
            flexShrink: 0,
          }}
        >
          <button
            className="btn btn-primary"
            style={{ width: "100%", fontSize: "var(--text-xs)" }}
            onClick={() => {
              const selection = window.getSelection()?.toString().trim();
              if (selection) onAskAboutSelection(selection);
            }}
          >
            Ask AI about selection
          </button>
        </div>
      )}
    </div>
  );
}
