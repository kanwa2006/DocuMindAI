"use client";

/**
 * Phase 9-F — Report Share Modal
 *
 * Two distinct flows triggered from the export dropdown:
 *   1. [📄 Generate Executive Report] → opens full modal → POST /export/{session_id}/report
 *   2. [🔗 Create Review Link]        → opens share panel → POST /sessions/{session_id}/share
 *
 * Both are rendered by this component based on the `mode` prop.
 */

import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import { API_BASE, getCsrfToken } from "@/lib/api";

export type ReportShareMode = "report" | "share";

const WATERMARK_OPTIONS = [
  { value: "", label: "None" },
  { value: "CONFIDENTIAL", label: "Confidential" },
  { value: "DRAFT", label: "Draft" },
  { value: "CLIENT-READY", label: "Client-Ready" },
  { value: "custom", label: "Custom…" },
] as const;

const EXPIRY_OPTIONS = [
  { value: 1, label: "1 day" },
  { value: 3, label: "3 days" },
  { value: 7, label: "7 days" },
  { value: 30, label: "30 days" },
] as const;

const FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export interface ReportShareModalProps {
  sessionId: string;
  workspaceType?: string;
  sessionTitle?: string;
  mode: ReportShareMode;
  onClose: () => void;
}

export default function ReportShareModal({
  sessionId,
  workspaceType = "general",
  sessionTitle = "",
  mode,
  onClose,
}: ReportShareModalProps) {
  return mode === "report" ? (
    <GenerateReportPanel
      sessionId={sessionId}
      workspaceType={workspaceType}
      sessionTitle={sessionTitle}
      onClose={onClose}
    />
  ) : (
    <CreateShareLinkPanel
      sessionId={sessionId}
      onClose={onClose}
    />
  );
}

// ── Generate Report Modal ─────────────────────────────────────────────────────

function GenerateReportPanel({
  sessionId,
  workspaceType,
  sessionTitle,
  onClose,
}: {
  sessionId: string;
  workspaceType: string;
  sessionTitle: string;
  onClose: () => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const [title, setTitle] = useState(
    sessionTitle
      ? `${sessionTitle} — ${today}`
      : `${workspaceType.charAt(0).toUpperCase() + workspaceType.slice(1)} Analysis — ${today}`
  );
  const [sections, setSections] = useState({
    executive_summary: true,
    key_findings: true,
    citations: true,
    workspace_context: true,
  });
  const [companyName, setCompanyName] = useState("");
  const [watermarkChoice, setWatermarkChoice] = useState("");
  const [customWatermark, setCustomWatermark] = useState("");
  const [showDateUser, setShowDateUser] = useState(true);
  const [showDisclaimer, setShowDisclaimer] = useState(
    workspaceType === "legal" || workspaceType === "finance"
  );
  const [generating, setGenerating] = useState(false);

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
      const first = els[0], last = els[els.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last?.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function toggleSection(key: keyof typeof sections) {
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const effectiveWatermark =
    watermarkChoice === "custom" ? customWatermark : watermarkChoice;

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/export/${sessionId}/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({
          title,
          sections,
          branding: { company_name: companyName || undefined },
          watermark: effectiveWatermark ? { text: effectiveWatermark } : undefined,
          footer_options: { show_date_user: showDateUser, show_disclaimer: showDisclaimer },
        }),
      });

      if (!res.ok) throw new Error("Generation failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_").slice(0, 60)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      toast.success("✓ Report generated successfully.");
      onClose();
    } catch {
      toast.error("Report generation failed. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-modal-title"
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "rgba(0,0,0,0.4)",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={dialogRef}
        className="modal"
        style={{ width: 520, maxHeight: "92vh", overflowY: "auto" }}
      >
        <div className="modal__header">
          <h2
            id="report-modal-title"
            style={{ fontFamily: "Instrument Serif, serif", fontSize: 20 }}
          >
            Generate Executive Report
          </h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">×</button>
        </div>

        <form onSubmit={handleGenerate} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Report title */}
          <div>
            <label className="form-label" htmlFor="report-title">Report title</label>
            <input
              id="report-title"
              className="form-control"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>

          {/* Include sections */}
          <fieldset style={{ border: "none", padding: 0 }}>
            <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Include sections</legend>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {(Object.keys(sections) as (keyof typeof sections)[]).map((key) => (
                <label key={key} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13 }}>
                  <input
                    type="checkbox"
                    checked={sections[key]}
                    onChange={() => toggleSection(key)}
                  />
                  {key === "executive_summary" && "Executive Summary (LLM-generated, 3–4 sentences)"}
                  {key === "key_findings" && "Key Findings (bulleted list from AI responses)"}
                  {key === "citations" && "All Citations (reference list format)"}
                  {key === "workspace_context" && "Workspace Context / Disclaimer"}
                </label>
              ))}
            </div>
          </fieldset>

          {/* Branding */}
          <div>
            <label className="form-label" htmlFor="company-name">Company name (optional)</label>
            <input
              id="company-name"
              className="form-control"
              placeholder="Acme Corp"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
          </div>

          {/* Watermark */}
          <div>
            <label className="form-label" htmlFor="watermark-select">Watermark</label>
            <select
              id="watermark-select"
              className="form-control"
              value={watermarkChoice}
              onChange={(e) => setWatermarkChoice(e.target.value)}
            >
              {WATERMARK_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {watermarkChoice === "custom" && (
              <input
                className="form-control"
                style={{ marginTop: 6 }}
                placeholder="Enter watermark text…"
                value={customWatermark}
                onChange={(e) => setCustomWatermark(e.target.value)}
              />
            )}
          </div>

          {/* Footer options */}
          <fieldset style={{ border: "none", padding: 0 }}>
            <legend style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Footer options</legend>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13 }}>
                <input type="checkbox" checked={showDateUser} onChange={(e) => setShowDateUser(e.target.checked)} />
                Show date and username in footer
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13 }}>
                <input type="checkbox" checked={showDisclaimer} onChange={(e) => setShowDisclaimer(e.target.checked)} />
                Show workspace disclaimer in footer
              </label>
            </div>
          </fieldset>

          {/* Actions */}
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={generating}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={generating}>
              {generating ? "Generating…" : "Generate & Download PDF"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create Share Link Panel ───────────────────────────────────────────────────

function CreateShareLinkPanel({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const [expiryDays, setExpiryDays] = useState(7);
  const [addWatermark, setAddWatermark] = useState(false);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);

  async function handleGenerate() {
    setGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/share`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({
          expiry_days: expiryDays,
          watermark_text: addWatermark ? "CONFIDENTIAL" : null,
        }),
      });
      if (!res.ok) throw new Error("Failed to create link");
      const data = await res.json();
      const base = typeof window !== "undefined" ? window.location.origin : "";
      setGeneratedUrl(`${base}${data.share_url}`);
      setExpiresAt(data.expires_at);
    } catch {
      toast.error("Failed to create review link. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleCopy() {
    if (!generatedUrl) return;
    await navigator.clipboard.writeText(generatedUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const expiryLabel = expiresAt
    ? new Date(expiresAt).toLocaleDateString(undefined, { dateStyle: "medium" })
    : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-link-title"
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: "rgba(0,0,0,0.4)",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="modal" style={{ width: 400, padding: 24 }}>
        <div className="modal__header">
          <h2
            id="share-link-title"
            style={{ fontFamily: "Instrument Serif, serif", fontSize: 18 }}
          >
            Create Secure Review Link
          </h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">×</button>
        </div>

        {!generatedUrl ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Expiry */}
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, display: "block", marginBottom: 6 }}>
                Link expiry
              </label>
              <div style={{ display: "flex", gap: 6 }}>
                {EXPIRY_OPTIONS.map((o) => (
                  <button
                    key={o.value}
                    type="button"
                    className={`btn btn-sm ${expiryDays === o.value ? "btn-primary" : "btn-ghost"}`}
                    onClick={() => setExpiryDays(o.value)}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Access note */}
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              Access: View only — no login required
            </p>

            {/* Watermark */}
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13 }}>
              <input
                type="checkbox"
                checked={addWatermark}
                onChange={(e) => setAddWatermark(e.target.checked)}
              />
              Add &quot;CONFIDENTIAL&quot; watermark
            </label>

            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%" }}
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? "Generating…" : "Generate Link"}
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 6 }}>
              <input
                className="form-control"
                readOnly
                value={generatedUrl}
                style={{ flex: 1, fontFamily: "monospace", fontSize: 12 }}
                aria-label="Generated review link"
                onFocus={(e) => e.target.select()}
              />
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={handleCopy}
                title="Copy link"
                aria-label="Copy link to clipboard"
              >
                {copied ? "✓" : "📋"}
              </button>
            </div>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
              Link expires {expiryLabel} · View-only · No login required
            </p>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
