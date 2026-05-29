"use client";

// PART 6 Phase 1 — Editable paper view.
//
// Renders a generated exam paper as an inline contentEditable rich-text
// region the teacher can directly type into. Save persists the edited
// content back to the ExamPaper row via PUT /exams/{id}; Export DOCX
// uses the existing GET /exams/{id}/export/docx flow.
//
// Phase 2 (image upload + richer toolbar) and Phase 3 (AI image
// generation) are intentionally out of scope here — captured in
// KNOWN_REMAINING_ISSUES.md as a design note.

import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { apiFetch } from "../lib/api";

interface Props {
  /** The full /exams/generate/paper payload (data.paper, data.metadata, data.exam_id). */
  paper: any;
  /** Called when the user closes the editor. */
  onClose: () => void;
  /** Called with the updated paper payload after a successful Save. */
  onSaved?: (updated: any) => void;
}

function paperToEditableHtml(paper: any): string {
  const meta = paper?.metadata || {};
  const parts: string[] = [];
  parts.push(
    `<h2 data-role="title">${escapeHtml(meta.subject || "Exam")} Paper — ${escapeHtml(meta.board || "")}</h2>`,
  );
  parts.push(
    `<p data-role="meta"><strong>Total Marks:</strong> ${meta.total_marks ?? ""} · ` +
      `<strong>Duration:</strong> ${meta.duration_minutes ?? ""} min · ` +
      `<strong>Difficulty:</strong> ${escapeHtml(meta.difficulty || "")}</p>`,
  );
  const sections = paper?.paper?.sections || [];
  for (const sec of sections) {
    parts.push(
      `<h3 data-role="section">SECTION ${escapeHtml(sec.label || "")}` +
        (sec.question_type ? ` — ${escapeHtml(String(sec.question_type).toUpperCase())}` : "") +
        `</h3>`,
    );
    for (const q of sec.questions || []) {
      parts.push(
        `<p data-role="question"><strong>${q.num}.</strong> ${escapeHtml(q.text || "")} ` +
          `<em>[${q.marks ?? ""}]</em></p>`,
      );
      if (q.subparts && q.subparts.length) {
        parts.push(`<ul data-role="subparts">`);
        for (const sp of q.subparts) {
          parts.push(
            `<li data-role="subpart"><strong>(${escapeHtml(sp.label || "")})</strong> ` +
              `${escapeHtml(sp.text || "")} <em>[${sp.marks ?? ""}]</em></li>`,
          );
        }
        parts.push(`</ul>`);
      }
      if (q.options && q.options.length) {
        parts.push(`<ol data-role="options" type="A">`);
        for (const opt of q.options) {
          parts.push(`<li>${escapeHtml(opt || "")}</li>`);
        }
        parts.push(`</ol>`);
      }
    }
  }
  return parts.join("\n");
}

function escapeHtml(s: string): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export default function EditablePaperPanel({ paper, onClose, onSaved }: Props) {
  const initialHtml = useMemo(() => paperToEditableHtml(paper), [paper]);
  const editorRef = useRef<HTMLDivElement>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Seed the editor once on mount. React-managed innerHTML would clobber
  // caret position on each keystroke, so we set it imperatively.
  useEffect(() => {
    if (editorRef.current) {
      editorRef.current.innerHTML = initialHtml;
    }
  }, [initialHtml]);

  const examId: string | null = paper?.exam_id || null;

  async function handleSave() {
    if (!editorRef.current) return;
    if (!examId) {
      toast.error("This paper wasn't auto-saved — regenerate first.");
      return;
    }
    setSaving(true);
    const toastId = toast.loading("Saving paper…");
    try {
      // Store the edited HTML alongside the original structured paper so
      // the export flow can render the EDITED version. The ExamPaper.content
      // column is JSON, so we add an `edited_html` field next to `paper`.
      const updatedContent = {
        ...(paper || {}),
        edited_html: editorRef.current.innerHTML,
        edited_at: new Date().toISOString(),
      };
      // PART 6 Phase 1 — use the dedicated edit-save endpoint that accepts
      // an arbitrary content blob (free-form JSON with edited_html, original
      // paper structure, metadata). The generic PUT /exams/{id} validates
      // through the strict ExamPaperContent schema and would 422.
      const res = await apiFetch(`/exams/${examId}/save-edits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: updatedContent }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `Save failed (HTTP ${res.status})`);
      }
      toast.success("Saved.", { id: toastId });
      setDirty(false);
      onSaved?.(updatedContent);
    } catch (e: any) {
      toast.error(e.message || "Save failed.", { id: toastId });
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    if (!examId) {
      toast.error("Save the paper first, then Export.");
      return;
    }
    if (dirty) {
      const wantSave = window.confirm("You have unsaved edits. Save before exporting?");
      if (wantSave) {
        await handleSave();
      }
    }
    try {
      const res = await apiFetch(`/exams/${examId}/export/docx`, {});
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `exam_paper_${examId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      toast.error(e.message || "Export failed.");
    }
  }

  function handleClose() {
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    onClose();
  }

  // Simple toolbar — execCommand is the lowest-friction way to get
  // bold/italic/headings/lists without pulling in a heavy editor lib.
  // It's "deprecated" but still works in all major browsers and is fine
  // for a Phase-1 contentEditable experience.
  function exec(cmd: string, value?: string) {
    document.execCommand(cmd, false, value);
    editorRef.current?.focus();
    setDirty(true);
  }

  return (
    <div style={{
      position: "fixed", top: 0, right: 0, bottom: 0, width: "560px",
      background: "var(--surface-raised)", borderLeft: "1px solid var(--border-subtle)",
      zIndex: 60, display: "flex", flexDirection: "column", overflow: "hidden",
      boxShadow: "-4px 0 24px rgba(0,0,0,0.12)",
    }}>
      {/* Header */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <span style={{ fontFamily: "var(--font-display, var(--font-body))", fontSize: "14px", fontWeight: 600, color: "var(--text-primary)" }}>
          Edit Paper{dirty ? " ·" : ""}
        </span>
        <button
          onClick={handleClose}
          aria-label="Close editor"
          style={{ width: "28px", height: "28px", border: "none", background: "transparent", cursor: "pointer", fontSize: "20px", color: "var(--text-tertiary)" }}
        >
          ×
        </button>
      </div>

      {/* Toolbar */}
      <div style={{ padding: "6px 12px", borderBottom: "1px solid var(--border-subtle)", display: "flex", gap: "4px", flexWrap: "wrap", flexShrink: 0, background: "var(--surface-sunken)" }}>
        <ToolbarBtn onClick={() => exec("bold")} title="Bold (Ctrl+B)"><strong>B</strong></ToolbarBtn>
        <ToolbarBtn onClick={() => exec("italic")} title="Italic (Ctrl+I)"><em>I</em></ToolbarBtn>
        <ToolbarBtn onClick={() => exec("underline")} title="Underline (Ctrl+U)"><span style={{ textDecoration: "underline" }}>U</span></ToolbarBtn>
        <ToolbarSep />
        <ToolbarBtn onClick={() => exec("formatBlock", "<h2>")} title="Heading">H2</ToolbarBtn>
        <ToolbarBtn onClick={() => exec("formatBlock", "<h3>")} title="Sub-heading">H3</ToolbarBtn>
        <ToolbarBtn onClick={() => exec("formatBlock", "<p>")} title="Paragraph">P</ToolbarBtn>
        <ToolbarSep />
        <ToolbarBtn onClick={() => exec("insertUnorderedList")} title="Bulleted list">•</ToolbarBtn>
        <ToolbarBtn onClick={() => exec("insertOrderedList")} title="Numbered list">1.</ToolbarBtn>
        <ToolbarSep />
        <ToolbarBtn onClick={() => exec("undo")} title="Undo (Ctrl+Z)">↶</ToolbarBtn>
        <ToolbarBtn onClick={() => exec("redo")} title="Redo">↷</ToolbarBtn>
      </div>

      {/* Editor */}
      <div style={{ flex: 1, overflow: "auto", padding: "16px 20px", background: "var(--surface-base)" }}>
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={() => setDirty(true)}
          spellCheck
          style={{
            outline: "none",
            fontFamily: "var(--font-body)",
            fontSize: "14px",
            lineHeight: 1.6,
            color: "var(--text-primary)",
            minHeight: "100%",
          }}
        />
      </div>

      {/* Footer */}
      <div style={{ padding: "10px 16px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0, background: "var(--surface-raised)" }}>
        <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>
          {examId ? `Exam ID ${examId.slice(0, 8)}…` : "Unsaved paper"} {dirty ? " · unsaved edits" : ""}
        </span>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleSave}
            disabled={saving || !dirty || !examId}
            className="btn btn-secondary btn-sm"
            style={{ height: "30px", fontSize: "12px" }}
          >
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            onClick={handleExport}
            disabled={!examId}
            className="btn btn-primary btn-sm"
            style={{ height: "30px", fontSize: "12px" }}
          >
            Export DOCX
          </button>
        </div>
      </div>
    </div>
  );
}

function ToolbarBtn({ onClick, title, children }: { onClick: () => void; title: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        height: "28px", minWidth: "28px", padding: "0 6px",
        border: "1px solid transparent", background: "transparent", cursor: "pointer",
        color: "var(--text-secondary)", fontSize: "12px", borderRadius: "6px",
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-raised)"; }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
    >
      {children}
    </button>
  );
}

function ToolbarSep() {
  return <span style={{ width: "1px", background: "var(--border-default)", margin: "2px 4px" }} />;
}
