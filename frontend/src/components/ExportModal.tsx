"use client";

import { useState, useEffect, useRef } from "react";
import { API_BASE } from "@/lib/api";

type ExportFormat = "pdf" | "docx" | "markdown";

interface ExportModalProps {
  sessionId: string;
  chatTitle?: string;
  messages?: Array<{ role: string; content: string }>;
  onClose: () => void;
}

const FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function ExportModal({
  sessionId,
  chatTitle = "documind-chat",
  messages = [],
  onClose,
}: ExportModalProps) {
  const [format, setFormat] = useState<ExportFormat>("pdf");
  const [includeCitations, setIncludeCitations] = useState(true);
  const [includeConfidence, setIncludeConfidence] = useState(false);
  const [includeDisclaimers, setIncludeDisclaimers] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const errorId = "export-modal-error";

  // Restore focus on unmount
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    return () => {
      previousFocusRef.current?.focus();
    };
  }, []);

  // Focus trap + Escape key
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const els = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE));
    els[0]?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
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

    dialog.addEventListener("keydown", handleKeyDown);
    return () => dialog.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExport = async () => {
    setError(null);

    if (format === "markdown") {
      const md = messages
        .map((msg) => {
          const role = msg.role === "user" ? "**You**" : "**DocuMindAI**";
          let content = msg.content;
          if (msg.role === "assistant") {
            try {
              const parsed = JSON.parse(msg.content);
              content = parsed.answer || msg.content;
            } catch {}
          }
          return `${role}:\n\n${content}\n\n---\n`;
        })
        .join("\n");
      triggerDownload(new Blob([md], { type: "text/markdown" }), `${chatTitle}.md`);
      onClose();
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/export/sessions/${sessionId}/${format}`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            include_citations: includeCitations,
            include_confidence: includeConfidence,
            include_disclaimers: includeDisclaimers,
          }),
        }
      );
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      triggerDownload(blob, `${chatTitle}.${format}`);
      onClose();
    } catch {
      setError("Export failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgb(0 0 0 / 0.5)",
        zIndex: 400, display: "flex", alignItems: "center", justifyContent: "center",
        padding: "16px",
      }}
      onClick={onClose}
      aria-hidden="true"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-modal-title"
        aria-describedby={error ? errorId : undefined}
        style={{
          background: "var(--surface-overlay)", border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-2xl)", boxShadow: "var(--shadow-2xl)",
          width: "100%", maxWidth: "440px", padding: "24px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h2
            id="export-modal-title"
            style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", color: "var(--text-primary)", margin: 0 }}
          >
            Export Session
          </h2>
          <button
            onClick={onClose}
            className="btn-icon btn-ghost"
            aria-label="Close export dialog"
            style={{ width: "32px", height: "32px" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Format selection */}
        <fieldset style={{ border: "none", padding: 0, margin: "0 0 20px" }}>
          <legend style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)", marginBottom: "10px", display: "block", width: "100%" }}>
            Format
          </legend>
          {(
            [
              { value: "pdf" as const, label: "PDF", desc: "Formatted document with headers and footnotes" },
              { value: "docx" as const, label: "DOCX", desc: "Microsoft Word document" },
              { value: "markdown" as const, label: "Markdown", desc: "Instant download — no server call" },
            ] as const
          ).map((opt) => (
            <label
              key={opt.value}
              style={{ display: "flex", alignItems: "flex-start", gap: "10px", marginBottom: "8px", cursor: "pointer" }}
            >
              <input
                type="radio"
                name="export-format"
                value={opt.value}
                checked={format === opt.value}
                onChange={() => setFormat(opt.value)}
                style={{ marginTop: "3px", accentColor: "var(--brand)" }}
              />
              <div>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-primary)", fontWeight: "var(--weight-medium)" }}>
                  {opt.label}
                </div>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
                  {opt.desc}
                </div>
              </div>
            </label>
          ))}
        </fieldset>

        {/* Options */}
        <fieldset style={{ border: "none", padding: 0, margin: "0 0 20px" }}>
          <legend style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)", marginBottom: "10px", display: "block", width: "100%" }}>
            Options
          </legend>
          {[
            { id: "opt-citations", label: "Include citations", checked: includeCitations, onChange: () => setIncludeCitations((v) => !v) },
            { id: "opt-confidence", label: "Include confidence scores", checked: includeConfidence, onChange: () => setIncludeConfidence((v) => !v) },
            { id: "opt-disclaimers", label: "Include disclaimers", checked: includeDisclaimers, onChange: () => setIncludeDisclaimers((v) => !v) },
          ].map((opt) => (
            <label
              key={opt.id}
              htmlFor={opt.id}
              style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px", cursor: "pointer" }}
            >
              <input
                id={opt.id}
                type="checkbox"
                checked={opt.checked}
                onChange={opt.onChange}
                style={{ accentColor: "var(--brand)", width: "16px", height: "16px" }}
              />
              <span style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-primary)" }}>
                {opt.label}
              </span>
            </label>
          ))}
        </fieldset>

        {/* Error banner */}
        {error && (
          <div
            id={errorId}
            role="alert"
            style={{
              background: "var(--error-bg)", border: "1px solid var(--error-border)",
              borderRadius: "var(--radius-md)", padding: "10px 14px", marginBottom: "16px",
              fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--error-text)",
            }}
          >
            {error}
          </div>
        )}

        {/* Loading / actions */}
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: "10px", justifyContent: "center", padding: "8px 0 0" }}>
            <div
              aria-hidden="true"
              style={{
                width: "16px", height: "16px",
                border: "2px solid var(--border-default)", borderTopColor: "var(--brand)",
                borderRadius: "50%", animation: "spin 0.7s linear infinite", flexShrink: 0,
              }}
            />
            <span style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}>
              Preparing your export...
            </span>
          </div>
        ) : (
          <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
            <button onClick={onClose} className="btn btn-ghost btn-sm">Cancel</button>
            <button
              onClick={handleExport}
              className="btn btn-primary btn-sm"
              aria-describedby={error ? errorId : undefined}
            >
              Export {format.toUpperCase()}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
