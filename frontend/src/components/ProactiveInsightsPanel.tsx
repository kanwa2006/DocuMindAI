"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../lib/api";

interface Insight {
  id: string;
  document_id: string;
  session_id: string | null;
  workspace: string;
  insight_type: string;
  severity: "critical" | "important" | "informational";
  finding: string;
  page_reference: number | null;
  was_clicked: boolean;
  created_at: string;
}

interface InsightsByDocument {
  document_id: string;
  filename: string;
  insights: Insight[];
}

interface Props {
  sessionId: string | null;
  hasDocuments: boolean;
  onAskAbout: (question: string) => void;
}

function severityIcon(s: Insight["severity"]): string {
  if (s === "critical") return "🔴";
  if (s === "important") return "🟡";
  return "🔵";
}

export default function ProactiveInsightsPanel({ sessionId, hasDocuments, onAskAbout }: Props) {
  const [groups, setGroups] = useState<InsightsByDocument[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchInsights = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/insights?session_id=${sessionId}`, {});
      if (res.ok) {
        const data: InsightsByDocument[] = await res.json();
        setGroups(data);
      }
    } catch {
      // non-fatal
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId && hasDocuments) {
      fetchInsights();
    }
  }, [sessionId, hasDocuments, fetchInsights]);

  const allInsights = groups.flatMap((g) => g.insights);
  const criticalCount = allInsights.filter((i) => i.severity === "critical").length;

  if (!hasDocuments || allInsights.length === 0) return null;

  const handleAskAbout = async (insight: Insight) => {
    // Mark as clicked
    try {
      await apiFetch(`/insights/${insight.id}/clicked`, { method: "PATCH" });
    } catch {
      // non-fatal
    }
    onAskAbout(`Tell me more about: ${insight.finding}`);
  };

  return (
    <div
      style={{
        marginBottom: "8px",
        border: "1px solid var(--border-default)",
        borderRadius: "10px",
        background: "var(--surface-raised)",
        overflow: "hidden",
        flexShrink: 0,
      }}
    >
      {/* ── Collapsed header ── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "10px 14px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontSize: "14px" }}>⚡</span>
        <span
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "13px",
            fontWeight: 600,
            color: "var(--text-primary)",
            flex: 1,
          }}
        >
          {allInsights.length} Key Insight{allInsights.length !== 1 ? "s" : ""} from this document
        </span>
        {criticalCount > 0 && (
          <span
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "12px",
              fontWeight: 600,
              color: "#dc2626",
              background: "#fee2e2",
              border: "1px solid #fca5a5",
              borderRadius: "20px",
              padding: "2px 8px",
              flexShrink: 0,
            }}
          >
            ⚠️ {criticalCount} Critical Finding{criticalCount !== 1 ? "s" : ""}
          </span>
        )}
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            color: "var(--text-tertiary)",
            flexShrink: 0,
          }}
        >
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* ── Expanded content ── */}
      {expanded && (
        <div
          style={{
            borderTop: "1px solid var(--border-subtle)",
            padding: "10px 14px",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            maxHeight: "320px",
            overflowY: "auto",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "11px",
              fontWeight: 700,
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: "4px",
            }}
          >
            ⚡ Proactive Insights
          </div>

          {groups.map((group) =>
            group.insights.map((insight) => (
              <div
                key={insight.id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                  padding: "8px 10px",
                  borderRadius: "8px",
                  background: "var(--surface-base)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <span style={{ fontSize: "14px", flexShrink: 0, marginTop: "1px" }}>
                  {severityIcon(insight.severity)}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "12px",
                      fontWeight: 600,
                      color:
                        insight.severity === "critical"
                          ? "#dc2626"
                          : insight.severity === "important"
                          ? "#d97706"
                          : "var(--text-secondary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      marginBottom: "2px",
                    }}
                  >
                    {insight.severity.toUpperCase()}
                    {insight.page_reference != null && (
                      <span
                        style={{
                          marginLeft: "6px",
                          fontWeight: 400,
                          color: "var(--text-tertiary)",
                          fontSize: "11px",
                        }}
                      >
                        [Page {insight.page_reference}]
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "13px",
                      color: "var(--text-primary)",
                      lineHeight: "1.45",
                    }}
                  >
                    {insight.finding}
                  </div>
                </div>
                {insight.severity !== "informational" && (
                  <button
                    onClick={() => handleAskAbout(insight)}
                    style={{
                      flexShrink: 0,
                      height: "28px",
                      padding: "0 10px",
                      fontSize: "11px",
                      fontFamily: "var(--font-body)",
                      background: "var(--surface-raised)",
                      border: "1px solid var(--border-default)",
                      borderRadius: "6px",
                      cursor: "pointer",
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                      transition: "border-color 100ms, color 100ms",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)";
                      (e.currentTarget as HTMLElement).style.color = "var(--brand)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)";
                      (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)";
                    }}
                  >
                    Ask AI about this
                  </button>
                )}
              </div>
            ))
          )}

          <button
            onClick={() => setExpanded(false)}
            style={{
              marginTop: "4px",
              alignSelf: "center",
              background: "none",
              border: "none",
              cursor: "pointer",
              fontFamily: "var(--font-body)",
              fontSize: "12px",
              color: "var(--text-tertiary)",
            }}
          >
            Hide Insights ▲
          </button>
        </div>
      )}
    </div>
  );
}
