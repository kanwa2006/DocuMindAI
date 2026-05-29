"use client";

/**
 * Task 6-L2 + 6-L3 + 6-L4 + 6-L5 frontend:
 * - Risk score circle (0-100) with ring color
 * - Clause list: risk color pill | clause type | confidence indicator | page chip
 * - Missing clauses red pill list
 * - Consistency warnings banner (Task 6-L4)
 * - Escalation banner — NOT dismissable (Task 6-L5)
 * - Legal disclaimer — always visible (Task 6-L1)
 */

import { useState, useCallback, useEffect } from "react";
import { toast } from "react-hot-toast";
import { apiFetch } from "../lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ClauseRisk {
  clause_type: string;
  text_excerpt: string;
  risk_level: "Low" | "Medium" | "High" | "Critical" | "Unassessable";
  risk_reason: string;
  confidence_score: number;
  confidence_basis: string;
  page: number | null;
  recommendation: string;
}

interface ConsistencyWarning {
  clause_type: string;
  previous_level: string;
  current_level: string;
  warning: string;
}

interface RiskReport {
  disclaimer: string;
  overall_risk_score: number;
  overall_risk_level: string;
  summary: string;
  clause_risks: ClauseRisk[];
  missing_clauses: string[];
  consistency_warnings: ConsistencyWarning[];
  escalation_required: boolean;
  escalation_reason: string | null;
  analysis_id: string | null;
}

interface Props {
  contractId: string | null;
  documentId: string | null;
  onClose: () => void;
  onFetchContracts: () => Promise<{ id: string; document_id: string }[]>;
  activeDocumentId: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function riskColor(level: string): string {
  if (level === "Critical")    return "#991b1b";
  if (level === "High")        return "#c2410c";
  if (level === "Medium")      return "#d97706";
  if (level === "Low")         return "#16a34a";
  if (level === "Unassessable") return "#6b7280";
  return "var(--text-tertiary)";
}

function riskBg(level: string): string {
  if (level === "Critical")    return "#fef2f2";
  if (level === "High")        return "#fff7ed";
  if (level === "Medium")      return "#fffbeb";
  if (level === "Low")         return "#f0fdf4";
  if (level === "Unassessable") return "#f9fafb";
  return "var(--surface-raised)";
}

function scoreRingColor(score: number): string {
  if (score <= 30) return "#16a34a";
  if (score <= 60) return "#d97706";
  if (score <= 80) return "#dc2626";
  return "#7f1d1d";
}

/** SVG ring for the overall risk score. */
function ScoreRing({ score, level }: { score: number; level: string }) {
  const r = 44;
  const circumference = 2 * Math.PI * r;
  const filled = circumference * (score / 100);
  const color = scoreRingColor(score);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg width="110" height="110" viewBox="0 0 110 110">
        <circle cx="55" cy="55" r={r} fill="none" stroke="var(--border-subtle)" strokeWidth="8" />
        <circle
          cx="55" cy="55" r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${filled} ${circumference}`}
          strokeLinecap="round"
          transform="rotate(-90 55 55)"
        />
        <text x="55" y="52" textAnchor="middle" fontFamily="var(--font-display)" fontSize="22" fontWeight="700" fill={color}>{score}</text>
        <text x="55" y="68" textAnchor="middle" fontFamily="var(--font-body)" fontSize="10" fill="var(--text-secondary)">/100</text>
      </svg>
      <div style={{
        marginTop: "6px",
        fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 700,
        color,
      }}>
        {level} Risk
      </div>
    </div>
  );
}

/** Single clause row with confidence indicators. */
function ClauseRow({ clause }: { clause: ClauseRisk }) {
  const [expanded, setExpanded] = useState(false);
  const color = riskColor(clause.risk_level);
  const bg = riskBg(clause.risk_level);
  const conf = clause.confidence_score ?? 1;
  const lowConf = conf < 0.60;
  const midConf = conf >= 0.60 && conf < 0.80;
  const isUnassessable = clause.risk_level === "Unassessable";

  return (
    <div
      style={{
        border: `1px solid ${lowConf ? "var(--warning-border, #fbbf24)" : "var(--border-subtle)"}`,
        borderRadius: "8px",
        marginBottom: "8px",
        background: bg,
        cursor: "pointer",
      }}
      onClick={() => setExpanded((v) => !v)}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 12px" }}>
        {/* Risk pill */}
        <span style={{
          background: color + "22", color, border: `1px solid ${color}44`,
          borderRadius: "var(--radius-full, 999px)",
          padding: "1px 8px", fontSize: "11px", fontWeight: 600,
          whiteSpace: "nowrap", flexShrink: 0,
        }}>
          {lowConf ? "? " : midConf ? "~ " : ""}
          {isUnassessable ? "Unassessable" : clause.risk_level}
        </span>

        <span style={{
          fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 500,
          color: "var(--text-primary)", flex: 1,
        }}>
          {clause.clause_type}
        </span>

        {clause.page != null && (
          <span style={{
            background: "var(--surface-sunken)", borderRadius: "4px",
            padding: "1px 7px", fontFamily: "var(--font-mono)", fontSize: "10px",
            color: "var(--text-tertiary)", flexShrink: 0,
          }}>
            p.{clause.page}
          </span>
        )}

        {lowConf && (
          <span
            title="Low confidence — AI is uncertain"
            style={{ color: "var(--warning-text, #d97706)", fontSize: "14px", flexShrink: 0 }}
          >
            ⚠
          </span>
        )}
      </div>

      {expanded && (
        <div style={{ padding: "0 12px 12px", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)", marginTop: "8px", lineHeight: 1.6 }}>
            <strong>Reason:</strong> {clause.risk_reason}
          </div>
          {clause.text_excerpt && (
            <div style={{ marginTop: "6px", fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", background: "var(--surface-sunken)", padding: "6px 8px", borderRadius: "6px", lineHeight: 1.5 }}>
              "{clause.text_excerpt.slice(0, 200)}{clause.text_excerpt.length > 200 ? "…" : ""}"
            </div>
          )}
          {clause.recommendation && (
            <div style={{ marginTop: "8px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-primary)" }}>
              <strong>Recommendation:</strong> {clause.recommendation}
            </div>
          )}
          <div style={{ marginTop: "6px", fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--text-tertiary)" }}>
            Confidence: {Math.round(conf * 100)}% · Basis: {clause.confidence_basis || "—"}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function LegalRiskPanel({
  contractId: initialContractId,
  onClose,
  onFetchContracts,
  activeDocumentId,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<RiskReport | null>(null);
  const [resolvedContractId, setResolvedContractId] = useState<string | null>(initialContractId);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      let cid = resolvedContractId;

      // If no contract ID yet, try to find one from the active document
      if (!cid && activeDocumentId) {
        const contracts = await onFetchContracts();
        const match = contracts.find((c) => c.document_id === activeDocumentId);
        if (!match) {
          toast.error("No contract found for this document. Process it first.");
          setLoading(false);
          return;
        }
        cid = match.id;
        setResolvedContractId(cid);
      }

      if (!cid) {
        toast.error("No contract selected.");
        setLoading(false);
        return;
      }

      const res = await apiFetch(`/legal/contracts/${cid}/risk-report`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Risk report failed.");
      }
      const data = await res.json();
      setReport(data);
    } catch (e: any) {
      toast.error(e.message || "Failed to generate risk report.");
    } finally {
      setLoading(false);
    }
  }, [resolvedContractId, activeDocumentId, onFetchContracts]);

  // Auto-fetch on mount. Previously called `useState(() => fetchReport())`,
  // which runs the initializer during render and triggers
  // "Cannot update a component while rendering a different component".
  useEffect(() => {
    fetchReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const panelStyle: React.CSSProperties = {
    position: "fixed", top: 0, right: 0, bottom: 0,
    width: "min(600px, 100vw)",
    background: "var(--surface-base)",
    borderLeft: "1px solid var(--border-default)",
    boxShadow: "-8px 0 32px rgba(0,0,0,0.12)",
    zIndex: 50,
    display: "flex", flexDirection: "column",
    overflowY: "hidden",
  };

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{
        padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)",
        display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0,
      }}>
        <div style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" }}>
          🚨 Contract Risk Report
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={fetchReport} disabled={loading} className="btn btn-secondary btn-sm" style={{ height: "32px", fontSize: "12px" }}>
            {loading ? "Analyzing…" : "🔄 Re-analyze"}
          </button>
          <button onClick={onClose} className="btn-icon btn-ghost" style={{ width: "32px", height: "32px", fontSize: "18px" }}>×</button>
        </div>
      </div>

      {/* Legal disclaimer — Task 6-L1 — always visible, never dismissable */}
      <div style={{
        background: "var(--warning-bg, #fffbeb)",
        borderBottom: "1px solid var(--warning-border, #fbbf24)",
        padding: "8px 20px",
        fontFamily: "var(--font-body)", fontSize: "11px",
        color: "var(--warning-text, #92400e)",
        flexShrink: 0,
      }}>
        ⚠ This analysis is AI-generated for informational purposes only. It does not constitute legal advice. Always consult a qualified legal professional.
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {loading && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)", fontFamily: "var(--font-body)", fontSize: "14px" }}>
            Analyzing contract…
          </div>
        )}

        {!loading && !report && (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ fontSize: "48px", marginBottom: "12px" }}>⚖</div>
            <button onClick={fetchReport} className="btn btn-primary" style={{ height: "40px" }}>
              Generate Risk Report
            </button>
          </div>
        )}

        {report && (
          <>
            {/* Task 6-L5: Escalation banner — NOT dismissable */}
            {report.escalation_required && (
              <div style={{
                background: "var(--error-bg, #fef2f2)",
                border: "1px solid var(--error-border, #fca5a5)",
                borderRadius: "10px",
                padding: "14px 16px",
                marginBottom: "16px",
              }}>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "14px", fontWeight: 700, color: "var(--error-text, #dc2626)", marginBottom: "6px" }}>
                  🚨 Human Legal Review Required
                </div>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--error-text, #dc2626)", marginBottom: "8px" }}>
                  {report.escalation_reason}
                </div>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)", fontStyle: "italic" }}>
                  This contract requires review by a qualified legal professional before any action is taken.
                  DocuMindAI identifies risk signals — it does not provide legal advice.
                </div>
              </div>
            )}

            {/* Task 6-L4: Consistency warnings */}
            {report.consistency_warnings.length > 0 && (
              <div style={{
                background: "#fffbeb",
                border: "1px solid #fbbf24",
                borderRadius: "10px",
                padding: "12px 16px",
                marginBottom: "16px",
              }}>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "#92400e", marginBottom: "6px" }}>
                  ⚠ Some clause risk levels differ from the previous analysis of this document. Review flagged clauses carefully.
                </div>
                {report.consistency_warnings.map((w, i) => (
                  <div key={i} style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "#78350f", marginTop: "4px" }}>
                    • {w.clause_type}: {w.previous_level} → {w.current_level}
                  </div>
                ))}
              </div>
            )}

            {/* Score circle + summary */}
            <div style={{ display: "flex", gap: "20px", alignItems: "flex-start", marginBottom: "20px" }}>
              <ScoreRing score={report.overall_risk_score} level={report.overall_risk_level} />
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                  {report.summary}
                </div>
                <div style={{ marginTop: "10px", display: "flex", gap: "8px" }}>
                  <button className="btn btn-secondary btn-sm" style={{ height: "28px", fontSize: "12px" }}>
                    📄 Export Risk Report PDF
                  </button>
                </div>
              </div>
            </div>

            {/* Clause risks */}
            {report.clause_risks.length > 0 && (
              <div style={{ marginBottom: "20px" }}>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "10px" }}>
                  Clause Analysis ({report.clause_risks.length})
                </div>
                {report.clause_risks.map((clause, i) => (
                  <ClauseRow key={i} clause={clause} />
                ))}
              </div>
            )}

            {/* Missing clauses */}
            {report.missing_clauses.length > 0 && (
              <div style={{ marginBottom: "16px" }}>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "8px" }}>
                  Missing Standard Clauses
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {report.missing_clauses.map((clause, i) => (
                    <span key={i} style={{
                      background: "#fef2f2", color: "#dc2626",
                      border: "1px solid #fca5a5",
                      borderRadius: "var(--radius-full, 999px)",
                      padding: "3px 10px", fontSize: "12px",
                    }}>
                      ✗ {clause}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
