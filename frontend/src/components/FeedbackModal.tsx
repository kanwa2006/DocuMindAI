"use client";

import { useState, useEffect, useRef } from "react";

type FeedbackType = "Bug Report" | "Feature Request" | "General Feedback" | "Payment Issue";

const FEEDBACK_TYPES: FeedbackType[] = [
  "Bug Report",
  "Feature Request",
  "General Feedback",
  "Payment Issue",
];

interface FeedbackModalProps {
  onClose: () => void;
}

export default function FeedbackModal({ onClose }: FeedbackModalProps) {
  const [type, setType] = useState<FeedbackType>("General Feedback");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstInputRef = useRef<HTMLSelectElement>(null);

  // Focus the type select on open
  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const isPaymentIssue = type === "Payment Issue";
  const charCount = message.trim().length;
  const isMessageValid = charCount >= 20;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isMessageValid) {
      setError("Message must be at least 20 characters.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          type,
          message: message.trim(),
          email: email.trim() || undefined,
          page_url: typeof window !== "undefined" ? window.location.href : undefined,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to submit feedback.");
      }
      if (typeof window !== "undefined" && (window as any).__toastSuccess) {
        (window as any).__toastSuccess("Thank you! We'll review within 24 hours.");
      }
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to submit feedback. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed", inset: 0,
        background: "rgba(0, 0, 0, 0.55)",
        zIndex: 500,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "16px",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="feedback-modal-title"
        style={{
          background: "var(--surface-overlay)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-2xl)",
          boxShadow: "var(--shadow-2xl)",
          width: "100%",
          maxWidth: "460px",
          padding: "24px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
          <h2
            id="feedback-modal-title"
            style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-lg)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)", margin: 0 }}
          >
            Help & Feedback
          </h2>
          <button
            onClick={onClose}
            aria-label="Close feedback modal"
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: "18px", padding: "2px 6px", lineHeight: 1, borderRadius: "4px" }}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

          {/* Type */}
          <div>
            <label
              htmlFor="feedback-type"
              style={{ display: "block", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Type
            </label>
            <select
              id="feedback-type"
              ref={firstInputRef}
              value={type}
              onChange={(e) => setType(e.target.value as FeedbackType)}
              style={{ width: "100%", height: "40px", padding: "0 12px", background: "var(--surface-sunken)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-primary)", outline: "none", cursor: "pointer" }}
            >
              {FEEDBACK_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {/* Payment Issue note */}
          {isPaymentIssue && (
            <div style={{ background: "var(--surface-sunken)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: "12px 14px" }}>
              <p style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                For urgent payment issues, email us directly at{" "}
                <a
                  href="mailto:support@documindai.com"
                  style={{ color: "var(--brand)", textDecoration: "underline" }}
                >
                  support@documindai.com
                </a>{" "}
                for faster resolution. You can also submit the form below.
              </p>
            </div>
          )}

          {/* Message */}
          <div>
            <label
              htmlFor="feedback-message"
              style={{ display: "block", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Message{" "}
              <span style={{ color: "var(--text-tertiary)", fontWeight: "normal" }}>(min 20 characters)</span>
            </label>
            <textarea
              id="feedback-message"
              value={message}
              onChange={(e) => { setMessage(e.target.value); if (error) setError(null); }}
              placeholder="Describe your issue or idea in detail..."
              rows={4}
              style={{
                width: "100%",
                padding: "10px 12px",
                background: "var(--surface-sunken)",
                border: `1px solid ${message.length > 0 && !isMessageValid ? "var(--error-text, #dc2626)" : "var(--border-default)"}`,
                borderRadius: "var(--radius-md)",
                fontFamily: "var(--font-body)",
                fontSize: "var(--text-sm)",
                color: "var(--text-primary)",
                outline: "none",
                resize: "vertical",
                boxSizing: "border-box",
                lineHeight: 1.5,
              }}
            />
            <div style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: isMessageValid ? "var(--brand)" : "var(--text-tertiary)", marginTop: "4px", textAlign: "right" }}>
              {charCount} / 20 minimum{isMessageValid ? " ✓" : ""}
            </div>
          </div>

          {/* Email */}
          <div>
            <label
              htmlFor="feedback-email"
              style={{ display: "block", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Email{" "}
              <span style={{ color: "var(--text-tertiary)", fontWeight: "normal" }}>(optional — for follow-up)</span>
            </label>
            <input
              id="feedback-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={{ width: "100%", height: "40px", padding: "0 12px", background: "var(--surface-sunken)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }}
            />
          </div>

          {/* Error */}
          {error && (
            <div
              role="alert"
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
                padding: "10px 12px",
                background: "var(--error-bg, #fef2f2)",
                border: "1px solid var(--error-border, #fecaca)",
                borderRadius: "var(--radius-md)",
                fontFamily: "var(--font-body)",
                fontSize: "var(--text-sm)",
                color: "var(--error-text, #b91c1c)",
                margin: 0,
              }}
            >
              <span aria-hidden="true" style={{ lineHeight: "var(--leading-snug)" }}>⚠</span>
              <span style={{ lineHeight: "var(--leading-snug)" }}>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", paddingTop: "4px" }}>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary btn-sm"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !isMessageValid}
              className="btn btn-primary btn-sm"
              style={{ opacity: submitting || !isMessageValid ? 0.6 : 1, cursor: submitting || !isMessageValid ? "not-allowed" : "pointer" }}
            >
              {submitting ? "Sending..." : "Send Feedback"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
