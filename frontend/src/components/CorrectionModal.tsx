"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { apiFetch } from "@/lib/api";
import type { Citation } from "./FeedbackBar";

interface CorrectionModalProps {
  sessionId: string;
  messageId?: string;
  workspaceId: string;
  citations?: Citation[];
  prefillIssueType?: string;
  onClose: () => void;
}

type IssueType =
  | "citation_wrong"
  | "answer_incorrect"
  | "missing_info"
  | "hallucination"
  | "source_not_found"
  | "other"
  | "";

type Confidence = "certain" | "likely" | "unsure";

const ISSUE_TYPES: { value: IssueType; label: string }[] = [
  { value: "citation_wrong", label: "Citation Wrong" },
  { value: "answer_incorrect", label: "Answer Incorrect" },
  { value: "missing_info", label: "Missing Information" },
  { value: "hallucination", label: "Hallucination" },
  { value: "source_not_found", label: "Source Not Found" },
  { value: "other", label: "Other" },
];

const FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

const HOW_IT_WORKS =
  "Corrections are reviewed by our team. They update test datasets, never production retrieval directly.";

export default function CorrectionModal({
  sessionId,
  messageId,
  workspaceId,
  citations = [],
  prefillIssueType = "",
  onClose,
}: CorrectionModalProps) {
  const [issueType, setIssueType] = useState<IssueType>(
    (prefillIssueType as IssueType) || ""
  );
  const [incorrectExcerpt, setIncorrectExcerpt] = useState("");
  const [suggestedCorrection, setSuggestedCorrection] = useState("");
  const [selectedCitationId, setSelectedCitationId] = useState("");
  const [correctSource, setCorrectSource] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [confidence, setConfidence] = useState<Confidence>("unsure");
  const [submitting, setSubmitting] = useState(false);
  const [showHowItWorks, setShowHowItWorks] = useState(false);

  const dialogRef = useRef<HTMLDivElement>(null);
  const prevFocusRef = useRef<HTMLElement | null>(null);

  // Restore focus on unmount
  useEffect(() => {
    prevFocusRef.current = document.activeElement as HTMLElement;
    return () => prevFocusRef.current?.focus();
  }, []);

  // Focus trap + Escape
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!issueType) return;
    setSubmitting(true);

    const payload = {
      session_id: sessionId || null,
      message_id: messageId || null,
      workspace_id: workspaceId,
      issue_type: issueType,
      incorrect_excerpt: incorrectExcerpt || null,
      suggested_correction: suggestedCorrection || correctSource || null,
      citation_id: selectedCitationId || null,
      reporter_confidence: confidence,
    };

    try {
      const res = await apiFetch("/corrections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Submission failed");
      toast.success("✓ Correction submitted. Our team will review it. Thank you.");
      onClose();
    } catch {
      toast.error("Failed to submit correction. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="correction-modal-title"
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
        style={{ width: 520, maxHeight: "90vh", overflowY: "auto" }}
      >
        {/* Header */}
        <div className="modal__header">
          <h2
            id="correction-modal-title"
            style={{ fontSize: 16, fontWeight: 600, fontFamily: "DM Sans, sans-serif" }}
          >
            Report an Issue
          </h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
          Your feedback improves DocuMindAI&apos;s accuracy.{" "}
          <button
            type="button"
            className="btn-link"
            style={{ fontSize: 13 }}
            onClick={() => setShowHowItWorks((p) => !p)}
            aria-expanded={showHowItWorks}
          >
            How corrections work →
          </button>
          {showHowItWorks && (
            <span
              role="tooltip"
              style={{
                display: "block",
                marginTop: 6,
                padding: "8px 12px",
                background: "var(--surface-hover)",
                borderRadius: 6,
                fontSize: 12,
                color: "var(--text-secondary)",
              }}
            >
              {HOW_IT_WORKS}
            </span>
          )}
        </p>

        <form onSubmit={handleSubmit}>
          {/* Section 1 — Issue Type */}
          <fieldset style={{ border: "none", padding: 0, marginBottom: 20 }}>
            <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
              Issue Type
            </legend>
            <div
              role="group"
              aria-label="Issue type"
              style={{ display: "flex", flexWrap: "wrap", gap: 8 }}
            >
              {ISSUE_TYPES.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  className={`btn btn-sm ${issueType === value ? "btn-primary" : "btn-ghost"}`}
                  onClick={() => setIssueType(value)}
                  aria-pressed={issueType === value}
                >
                  {label}
                </button>
              ))}
            </div>
          </fieldset>

          {/* Section 2 — Contextual fields */}
          {issueType === "citation_wrong" && (
            <div style={{ marginBottom: 16 }}>
              <label className="form-label" htmlFor="citation-select">
                Which citation is wrong?
              </label>
              {citations.length > 0 ? (
                <select
                  id="citation-select"
                  className="form-control"
                  value={selectedCitationId}
                  onChange={(e) => setSelectedCitationId(e.target.value)}
                >
                  <option value="">Select a citation…</option>
                  {citations.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id="citation-select"
                  className="form-control"
                  placeholder="Describe the citation…"
                  value={selectedCitationId}
                  onChange={(e) => setSelectedCitationId(e.target.value)}
                />
              )}
              <label className="form-label" htmlFor="correct-source" style={{ marginTop: 12 }}>
                What is the correct source? (optional)
              </label>
              <input
                id="correct-source"
                className="form-control"
                value={correctSource}
                onChange={(e) => setCorrectSource(e.target.value)}
                placeholder="Correct source or page reference…"
              />
            </div>
          )}

          {issueType === "answer_incorrect" && (
            <div style={{ marginBottom: 16 }}>
              <label className="form-label" htmlFor="incorrect-excerpt">
                What is incorrect? <span aria-hidden="true">*</span>
              </label>
              <textarea
                id="incorrect-excerpt"
                className="form-control"
                rows={3}
                required
                value={incorrectExcerpt}
                onChange={(e) => setIncorrectExcerpt(e.target.value)}
                placeholder="Describe what is wrong…"
              />
              <label className="form-label" htmlFor="suggested-correction" style={{ marginTop: 12 }}>
                What is the correct answer? (optional)
              </label>
              <textarea
                id="suggested-correction"
                className="form-control"
                rows={3}
                value={suggestedCorrection}
                onChange={(e) => setSuggestedCorrection(e.target.value)}
                placeholder="Correct answer or explanation…"
              />
            </div>
          )}

          {issueType === "hallucination" && (
            <div style={{ marginBottom: 16 }}>
              <label className="form-label" htmlFor="hallucinated-claim">
                Paste the specific claim that is hallucinated: <span aria-hidden="true">*</span>
              </label>
              <textarea
                id="hallucinated-claim"
                className="form-control"
                rows={3}
                required
                value={incorrectExcerpt}
                onChange={(e) => setIncorrectExcerpt(e.target.value)}
                placeholder="Paste the hallucinated claim here…"
              />
            </div>
          )}

          {issueType && !["citation_wrong", "answer_incorrect", "hallucination"].includes(issueType) && (
            <div style={{ marginBottom: 16 }}>
              <label className="form-label" htmlFor="issue-description">
                Describe the issue
              </label>
              <textarea
                id="issue-description"
                className="form-control"
                rows={3}
                value={incorrectExcerpt}
                onChange={(e) => setIncorrectExcerpt(e.target.value)}
                placeholder="Describe the issue…"
              />
            </div>
          )}

          {/* All types — common fields */}
          {issueType && (
            <>
              <div style={{ marginBottom: 16 }}>
                <label className="form-label" htmlFor="reviewer-notes">
                  Reviewer notes (optional)
                </label>
                <textarea
                  id="reviewer-notes"
                  className="form-control"
                  rows={2}
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  placeholder="Any additional context…"
                />
              </div>

              <fieldset style={{ border: "none", padding: 0, marginBottom: 20 }}>
                <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                  Your confidence in this correction
                </legend>
                <div style={{ display: "flex", gap: 16 }}>
                  {(["certain", "likely", "unsure"] as Confidence[]).map((c) => (
                    <label key={c} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="confidence"
                        value={c}
                        checked={confidence === c}
                        onChange={() => setConfidence(c)}
                      />
                      <span style={{ textTransform: "capitalize" }}>{c}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </>
          )}

          {/* Section 3 — Actions */}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || !issueType}
            >
              {submitting ? "Submitting…" : "Submit Correction"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
