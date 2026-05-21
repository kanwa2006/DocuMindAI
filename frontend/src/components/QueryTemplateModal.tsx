"use client";

/**
 * Phase 9-E — Save Query Template Modal
 *
 * Opened from the [+ Save current query] item in the sidebar Query Templates section.
 * Posts to POST /api/v1/query-templates.
 * On success: calls onSaved() so the sidebar can refresh its template list.
 */

import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { API_BASE, getCsrfToken } from "@/lib/api";

const WORKSPACES = [
  "general", "legal", "finance", "hr", "teacher", "student", "research",
] as const;

const FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export interface QueryTemplateModalProps {
  prefillQuery?: string;
  prefillWorkspace?: string;
  onClose: () => void;
  onSaved: () => void;
}

export default function QueryTemplateModal({
  prefillQuery = "",
  prefillWorkspace = "general",
  onClose,
  onSaved,
}: QueryTemplateModalProps) {
  const [name, setName] = useState("");
  const [queryText, setQueryText] = useState(prefillQuery);
  const [workspace, setWorkspace] = useState(prefillWorkspace);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !queryText.trim()) return;

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/query-templates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({
          name: name.trim().slice(0, 40),
          query_text: queryText.trim(),
          workspace_id: workspace,
          notes: notes.trim() || undefined,
        }),
      });
      if (!res.ok) throw new Error("Save failed");
      toast.success("✓ Template saved. Find it in your sidebar.");
      onSaved();
      onClose();
    } catch {
      toast.error("Failed to save template. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="qtemplate-modal-title"
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
        style={{ width: 440, maxHeight: "90vh", overflowY: "auto" }}
      >
        <div className="modal__header">
          <h2 id="qtemplate-modal-title" style={{ fontSize: 16, fontWeight: 600 }}>
            Save as Query Template
          </h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Template name */}
          <div>
            <label className="form-label" htmlFor="tpl-name">
              Template name <span aria-hidden="true">*</span>
            </label>
            <input
              id="tpl-name"
              className="form-control"
              type="text"
              required
              maxLength={40}
              placeholder="e.g. Compare all clauses"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              {name.length}/40
            </span>
          </div>

          {/* Query text */}
          <div>
            <label className="form-label" htmlFor="tpl-query">
              Query text <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="tpl-query"
              className="form-control"
              required
              rows={3}
              placeholder="The query that will be pasted into chat…"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
            />
          </div>

          {/* Workspace */}
          <div>
            <label className="form-label" htmlFor="tpl-workspace">
              Workspace
            </label>
            <select
              id="tpl-workspace"
              className="form-control"
              value={workspace}
              onChange={(e) => setWorkspace(e.target.value)}
            >
              {WORKSPACES.map((w) => (
                <option key={w} value={w} style={{ textTransform: "capitalize" }}>
                  {w.charAt(0).toUpperCase() + w.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="form-label" htmlFor="tpl-notes">
              Notes (optional)
            </label>
            <textarea
              id="tpl-notes"
              className="form-control"
              rows={2}
              placeholder="When to use this template…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || !name.trim() || !queryText.trim()}
            >
              {submitting ? "Saving…" : "Save Template"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
