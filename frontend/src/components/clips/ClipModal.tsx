"use client";

import { useState, useEffect, useRef } from "react";
import { clipText, ClipTextRequest, Document } from "../../lib/api";

type SourceHint = "email" | "message" | "web" | "note" | "other";

const SOURCE_HINTS: { value: SourceHint; label: string; icon: string }[] = [
  { value: "email", label: "Email", icon: "✉️" },
  { value: "message", label: "Message", icon: "💬" },
  { value: "web", label: "Web", icon: "🌐" },
  { value: "note", label: "Note", icon: "📝" },
  { value: "other", label: "Other", icon: "" },
];

interface ClipModalProps {
  initialText?: string;
  onClose: () => void;
  onClipped: (doc: Document) => void;
  chatSessionId?: string;  // P1: bind clip to the current chat session
}

export function ClipModal({ initialText = "", onClose, onClipped, chatSessionId }: ClipModalProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState(initialText);
  const [sourceHint, setSourceHint] = useState<SourceHint | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus textarea on open
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const contentLen = content.length;
  const isValid = contentLen >= 50 && contentLen <= 50000;

  const counterColor =
    contentLen < 50
      ? "var(--red-500, #ef4444)"
      : contentLen > 45000
      ? "var(--amber-500, #f59e0b)"
      : "var(--text-tertiary)";

  const handleSubmit = async () => {
    if (!isValid || loading) return;
    setLoading(true);
    setError(null);
    try {
      const req: ClipTextRequest = {
        content,
        title: title.trim() || undefined,
        source_hint: sourceHint || undefined,
        chat_session_id: chatSessionId,  // P1: per-chat isolation
      };
      const res = await clipText(req);

      // Build an optimistic Document record for the UI
      const optimisticDoc: Document = {
        id: res.document_id,
        filename: res.filename || title.trim() || content.slice(0, 40),
        status: res.status === "deduplicated" ? "READY" : "PROCESSING",
        source: "clip",
        chat_session_id: chatSessionId,
        created_at: new Date().toISOString(),
      };

      onClipped(optimisticDoc);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to clip text. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    // Backdrop
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Modal */}
      <div
        style={{
          maxWidth: "480px",
          width: "calc(100vw - 32px)",
          background: "var(--surface-base)",
          borderRadius: "var(--radius-xl, 16px)",
          boxShadow: "var(--shadow-2xl, 0 24px 64px rgba(0,0,0,0.4))",
          display: "flex",
          flexDirection: "column",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "16px",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            📋 Clip Text as Document
          </span>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              width: "32px",
              height: "32px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-tertiary)",
              fontSize: "18px",
              borderRadius: "6px",
              transition: "background 100ms",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-raised)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div
          style={{
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          {/* Title field */}
          <div>
            <label
              style={{
                display: "block",
                fontFamily: "var(--font-body)",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                marginBottom: "4px",
              }}
            >
              Document title (optional)
            </label>
            <input
              className="form-input"
              type="text"
              maxLength={60}
              placeholder="e.g. Email from client re: contract"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              style={{ width: "100%", boxSizing: "border-box" }}
            />
            <div
              style={{
                textAlign: "right",
                fontFamily: "var(--font-body)",
                fontSize: "11px",
                color: "var(--text-tertiary)",
                marginTop: "2px",
              }}
            >
              {title.length}/60
            </div>
          </div>

          {/* Text area */}
          <div>
            <label
              style={{
                display: "block",
                fontFamily: "var(--font-body)",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                marginBottom: "4px",
              }}
            >
              Text content <span style={{ color: "var(--red-500, #ef4444)" }}>*</span>
            </label>
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => { setContent(e.target.value); setError(null); }}
              placeholder={"Paste or type any text here — emails, messages, notes,\nweb content, anything you want to ask questions about..."}
              style={{
                width: "100%",
                boxSizing: "border-box",
                minHeight: "160px",
                maxHeight: "300px",
                overflowY: "auto",
                resize: "vertical",
                fontFamily: "var(--font-body)",
                fontSize: "13px",
                lineHeight: "1.6",
                padding: "10px 12px",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-md, 8px)",
                background: "var(--surface-sunken)",
                color: "var(--text-primary)",
                outline: "none",
                transition: "border-color 100ms, box-shadow 100ms",
              }}
              onFocus={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border-strong)";
                (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-brand, 0 0 0 3px rgba(99,102,241,0.15))";
              }}
              onBlur={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)";
                (e.currentTarget as HTMLElement).style.boxShadow = "none";
              }}
            />
            <div
              style={{
                textAlign: "right",
                fontFamily: "var(--font-body)",
                fontSize: "11px",
                color: counterColor,
                marginTop: "2px",
              }}
            >
              {contentLen.toLocaleString()} / 50,000 characters
            </div>
            {error && (
              <div
                style={{
                  marginTop: "6px",
                  fontFamily: "var(--font-body)",
                  fontSize: "12px",
                  color: "var(--red-500, #ef4444)",
                }}
              >
                {error}
              </div>
            )}
          </div>

          {/* Source hint pills */}
          <div>
            <label
              style={{
                display: "block",
                fontFamily: "var(--font-body)",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                marginBottom: "4px",
              }}
            >
              Where is this from? (optional)
            </label>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              {SOURCE_HINTS.map(({ value, label, icon }) => {
                const selected = sourceHint === value;
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSourceHint(selected ? null : value)}
                    style={{
                      height: "32px",
                      padding: "0 12px",
                      borderRadius: "999px",
                      border: `1px solid ${selected ? "var(--brand)" : "var(--border-default)"}`,
                      background: selected ? "var(--brand-ghost, rgba(99,102,241,0.08))" : "var(--surface-sunken)",
                      color: selected ? "var(--brand)" : "var(--text-secondary)",
                      fontFamily: "var(--font-body)",
                      fontSize: "12px",
                      fontWeight: selected ? 500 : 400,
                      cursor: "pointer",
                      transition: "all 100ms",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    {icon && <span>{icon}</span>}
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "12px 20px 16px 20px",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            gap: "12px",
            justifyContent: "flex-end",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            className="btn btn-ghost"
            style={{ height: "36px" }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isValid || loading}
            className="btn btn-primary"
            style={{ height: "36px", minWidth: "160px" }}
          >
            {loading ? "Adding…" : "📋 Add to Session →"}
          </button>
        </div>
      </div>
    </div>
  );
}
