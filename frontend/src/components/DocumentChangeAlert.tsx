"use client";

/**
 * Phase 9-E — Document Change Alert
 *
 * Shown below the document chips when a document has been re-uploaded with the
 * same filename as a file previously analysed in another session.
 * Backend: GET /api/v1/documents/{id}/change-detection
 *
 * Usage:
 *   <DocumentChangeAlert
 *     documentId="..."
 *     filename="Q3_Report.pdf"
 *     onReanalyze={() => createNewSession()}
 *   />
 */

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

export interface DocumentChangeAlertProps {
  documentId: string;
  filename: string;
  previousCreatedAt?: string;
  onReanalyze: () => void;
}

interface ChangeDetectionResult {
  newer_version_exists: boolean;
  previous_session_id: string | null;
  previous_doc_id?: string;
  previous_created_at?: string;
}

export default function DocumentChangeAlert({
  documentId,
  filename,
  onReanalyze,
}: DocumentChangeAlertProps) {
  const [result, setResult] = useState<ChangeDetectionResult | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      try {
        const res = await fetch(
          `${API_BASE}/documents/${documentId}/change-detection`,
          { credentials: "include" }
        );
        if (!cancelled && res.ok) {
          setResult(await res.json());
        }
      } catch {
        // silent — alert is best-effort
      }
    }
    check();
    return () => { cancelled = true; };
  }, [documentId]);

  if (dismissed || !result?.newer_version_exists) return null;

  const prevDate = result.previous_created_at
    ? new Date(result.previous_created_at).toLocaleDateString(undefined, { dateStyle: "medium" })
    : "a previous session";

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        background: "var(--info-bg, #eff6ff)",
        border: "1px solid var(--info-border, #93c5fd)",
        borderRadius: 8,
        padding: "10px 12px",
        marginTop: 8,
        fontSize: 13,
        color: "var(--text-primary)",
        lineHeight: 1.5,
      }}
    >
      <span aria-hidden="true" style={{ flexShrink: 0, marginTop: 1 }}>📄</span>

      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ margin: 0, marginBottom: 6 }}>
          <strong>{filename}</strong> appears to be an updated version of a file
          analysed on {prevDate}. Would you like to re-analyse with this new version?
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => {
              setDismissed(true);
              onReanalyze();
            }}
          >
            Re-analyze Now →
          </button>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss this alert"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
