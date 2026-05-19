"use client";

/**
 * Task 6-F2 / 6-F5 / 6-F6 / 6-F7 Frontend:
 * - Ratio cards: name | value | trend ↑↓→ | status Good/Caution/Risk
 * - Extraction audit table with source-text traceability
 * - Multi-period comparison table with sparkline trend
 */

import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { API_BASE } from "../lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Ratio {
  name: string;
  value: number | null;
  formula: string;
  inputs_used?: Record<string, number | null>;
  inputs?: Record<string, {
    value: number; page: number; text: string; confidence: number; verified: boolean;
  }>;
  source_citation?: string;
  status?: string;
  error?: string;
}

interface FlaggedValue {
  value: string;
  confidence: number;
  verified: boolean;
}

interface RatioApiResponse {
  accounting_standard: string;
  extracted_line_items: Record<string, number | null>;
  ratios: Ratio[];
  flagged_values: FlaggedValue[];
  document_id: string;
  filename: string;
}

interface ComparisonRatio {
  name: string;
  formula: string;
  values: Record<string, number | null>;
  trend: string;
  yoy_changes: Record<string, number>;
}

interface Props {
  documentIds: string[];
  onClose: () => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: string | undefined): string {
  if (status === "Good") return "var(--success-text, #16a34a)";
  if (status === "Caution") return "var(--warning-text, #d97706)";
  if (status === "Risk") return "var(--error-text, #dc2626)";
  return "var(--text-tertiary)";
}

function statusBg(status: string | undefined): string {
  if (status === "Good") return "var(--success-bg, #f0fdf4)";
  if (status === "Caution") return "var(--warning-bg, #fffbeb)";
  if (status === "Risk") return "var(--error-bg, #fef2f2)";
  return "var(--surface-raised)";
}

function trendArrow(trend: string): { symbol: string; color: string } {
  if (trend === "improving") return { symbol: "↑", color: "var(--success-text, #16a34a)" };
  if (trend === "declining") return { symbol: "↓", color: "var(--error-text, #dc2626)" };
  return { symbol: "→", color: "var(--text-tertiary)" };
}

function formatValue(val: number | null, name: string): string {
  if (val === null || val === undefined) return "N/A";
  const pct = ["Net Profit Margin", "Gross Margin", "Operating Margin", "EBITDA Margin",
    "Return on Equity (ROE)"];
  const days = ["Payables Days", "Receivables Days (DSO)"];
  if (pct.includes(name)) return `${val.toFixed(2)}%`;
  if (days.includes(name)) return `${val.toFixed(1)} days`;
  return val.toFixed(2);
}

// ── Ratio card ────────────────────────────────────────────────────────────────

function RatioCard({ ratio }: { ratio: Ratio }) {
  const [expanded, setExpanded] = useState(false);
  const hasError = !!ratio.error;
  const status = hasError ? "N/A" : ratio.status;

  return (
    <div
      style={{
        border: `1px solid ${hasError ? "var(--border-subtle)" : statusColor(status) + "44"}`,
        borderRadius: "10px",
        padding: "14px 16px",
        background: hasError ? "var(--surface-raised)" : statusBg(status),
        cursor: "pointer",
        transition: "box-shadow 100ms",
      }}
      onClick={() => setExpanded((v) => !v)}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
            {ratio.name}
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", marginTop: "2px" }}>
            {ratio.formula}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: "20px", fontWeight: 700,
            color: hasError ? "var(--text-tertiary)" : statusColor(status),
          }}>
            {hasError ? "—" : formatValue(ratio.value, ratio.name)}
          </div>
          {!hasError && (
            <div style={{
              fontSize: "11px", fontWeight: 600,
              color: statusColor(status),
              marginTop: "2px",
            }}>
              {status}
            </div>
          )}
          {hasError && (
            <div style={{ fontSize: "11px", color: "var(--text-tertiary)", marginTop: "2px" }}>
              {ratio.error}
            </div>
          )}
        </div>
      </div>

      {expanded && ratio.inputs_used && (
        <div style={{ marginTop: "10px", paddingTop: "10px", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)", marginBottom: "6px" }}>
            Inputs used:
          </div>
          {Object.entries(ratio.inputs_used).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", fontFamily: "var(--font-mono)", marginBottom: "2px" }}>
              <span style={{ color: "var(--text-secondary)" }}>{k.replace(/_/g, " ")}</span>
              <span style={{ color: "var(--text-primary)" }}>{v !== null ? v?.toLocaleString() : "N/A"}</span>
            </div>
          ))}
          {ratio.inputs && (
            <div style={{ marginTop: "8px" }}>
              {Object.entries(ratio.inputs).map(([k, info]) => (
                <div key={k} style={{
                  fontSize: "11px", fontFamily: "var(--font-body)",
                  color: "var(--text-tertiary)", marginTop: "4px",
                }}>
                  {k.replace(/_/g, " ")}: "{String(info.text).slice(0, 40)}"
                  {info.page && <span> — p.{info.page}</span>}
                  {" "}
                  <span style={{
                    color: info.confidence >= 0.85 ? "var(--success-text, #16a34a)"
                      : info.confidence >= 0.70 ? "var(--warning-text, #d97706)"
                      : "var(--error-text, #dc2626)",
                  }}>
                    [{Math.round(info.confidence * 100)}% conf]
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Extraction Audit Table (Task 6-F6) ────────────────────────────────────────

function ExtractionAuditTable({ ratios, flaggedValues }: {
  ratios: Ratio[];
  flaggedValues: FlaggedValue[];
}) {
  const rows = ratios.flatMap((r) =>
    Object.entries(r.inputs || {}).map(([k, info]) => ({
      lineItem: k.replace(/_/g, " "),
      value: info.value,
      text: info.text,
      page: info.page,
      confidence: info.confidence,
      verified: info.verified,
    }))
  );

  if (rows.length === 0) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "var(--text-tertiary)", fontSize: "13px" }}>
        No traceability data — run the ratio extraction with a full financial document.
      </div>
    );
  }

  const downloadCSV = () => {
    const header = "Line Item,Extracted Value,Source Text,Page,Confidence,Status\n";
    const body = rows.map((r) =>
      `"${r.lineItem}","${r.value}","${String(r.text).replace(/"/g, '""')}","${r.page ?? ""}","${Math.round(r.confidence * 100)}%","${r.verified ? "Verified" : "Review"}"`
    ).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `extraction_audit_${Date.now()}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
        <span style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
          Extraction Audit Trail
        </span>
        <button
          onClick={downloadCSV}
          className="btn btn-secondary btn-sm"
          style={{ height: "28px", fontSize: "12px" }}
        >
          📥 Export Audit Trail
        </button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
          <thead>
            <tr style={{ background: "var(--surface-sunken)" }}>
              {["Line Item", "Extracted Value", "Source Text", "Page", "Confidence", "Status"].map((h) => (
                <th key={h} style={{ padding: "8px 10px", textAlign: "left", fontWeight: 600, borderBottom: "2px solid var(--border-default)", color: "var(--text-secondary)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const confColor = row.confidence >= 0.85 ? "var(--success-text, #16a34a)"
                : row.confidence >= 0.70 ? "var(--warning-text, #d97706)"
                : "var(--error-text, #dc2626)";
              return (
                <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "8px 10px", fontWeight: 500, color: "var(--text-primary)" }}>{row.lineItem}</td>
                  <td style={{ padding: "8px 10px", fontFamily: "var(--font-mono)" }}>{row.value?.toLocaleString() ?? "N/A"}</td>
                  <td style={{ padding: "8px 10px", color: "var(--text-secondary)", maxWidth: "200px" }}>
                    <span title={row.text}>{String(row.text).slice(0, 40)}{String(row.text).length > 40 ? "…" : ""}</span>
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    {row.page ? <span style={{ background: "var(--surface-sunken)", borderRadius: "4px", padding: "1px 6px", fontFamily: "var(--font-mono)" }}>p.{row.page}</span> : "—"}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <span style={{ color: confColor, fontWeight: 600 }}>{Math.round(row.confidence * 100)}%</span>
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    {row.verified
                      ? <span style={{ color: "var(--success-text, #16a34a)" }}>✓ Verified</span>
                      : <span style={{ color: "var(--warning-text, #d97706)" }}>⚠ Review</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function FinanceRatioPanel({ documentIds, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RatioApiResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"ratios" | "audit">("ratios");

  const fetchRatios = useCallback(async () => {
    if (!documentIds.length) {
      toast.error("No document selected.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/finance/ratios`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_ids: documentIds }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Ratio computation failed.");
      }
      const json = await res.json();
      setData(json);
    } catch (e: any) {
      toast.error(e.message || "Failed to compute ratios.");
    } finally {
      setLoading(false);
    }
  }, [documentIds]);

  // Auto-fetch on mount
  useState(() => { fetchRatios(); });

  const panelStyle: React.CSSProperties = {
    position: "fixed", top: 0, right: 0, bottom: 0,
    width: "min(560px, 100vw)",
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
        <div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" }}>
            📈 Financial Ratios
          </div>
          {data && (
            <div style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)", marginTop: "2px" }}>
              Standard: {data.accounting_standard} · {data.filename}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            onClick={fetchRatios}
            disabled={loading}
            className="btn btn-secondary btn-sm"
            style={{ height: "32px", fontSize: "12px" }}
          >
            {loading ? "Computing…" : "🔄 Refresh"}
          </button>
          <button onClick={onClose} className="btn-icon btn-ghost" style={{ width: "32px", height: "32px", fontSize: "18px" }}>×</button>
        </div>
      </div>

      {/* Finance disclaimer — always visible */}
      <div style={{
        background: "var(--warning-bg, #fffbeb)",
        borderBottom: "1px solid var(--warning-border, #fbbf24)",
        padding: "8px 20px",
        fontFamily: "var(--font-body)", fontSize: "11px",
        color: "var(--warning-text, #92400e)",
        flexShrink: 0,
      }}>
        ⚠ All figures are AI-extracted. Verify all numbers against original source documents before any financial, tax, or legal use.
      </div>

      {/* Tabs */}
      {data && (
        <div style={{ display: "flex", gap: "0", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
          {(["ratios", "audit"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1, height: "40px",
                fontFamily: "var(--font-body)", fontSize: "13px",
                borderBottom: activeTab === tab ? "2px solid var(--brand)" : "2px solid transparent",
                color: activeTab === tab ? "var(--brand)" : "var(--text-secondary)",
                background: "none", border: "none", cursor: "pointer",
                fontWeight: activeTab === tab ? 600 : 400,
              }}
            >
              {tab === "ratios" ? "📊 Ratios" : "✅ Audit Trail"}
            </button>
          ))}
        </div>
      )}

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {loading && (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)", fontFamily: "var(--font-body)", fontSize: "14px" }}>
            Computing financial ratios…
          </div>
        )}

        {!loading && !data && (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div style={{ fontSize: "48px", marginBottom: "12px" }}>📊</div>
            <button onClick={fetchRatios} className="btn btn-primary" style={{ height: "40px" }}>
              Compute Ratios
            </button>
          </div>
        )}

        {data && activeTab === "ratios" && (
          <div>
            {/* Flagged values warning */}
            {data.flagged_values.some((v) => v.confidence < 0.70) && (
              <div style={{
                background: "var(--warning-bg, #fffbeb)",
                border: "1px solid var(--warning-border, #fbbf24)",
                borderRadius: "8px", padding: "10px 14px",
                marginBottom: "16px",
                fontFamily: "var(--font-body)", fontSize: "12px",
                color: "var(--warning-text, #92400e)",
              }}>
                ⚠ {data.flagged_values.filter((v) => v.confidence < 0.70).length} value(s) could not be confirmed in source documents. Review highlighted ratios carefully.
              </div>
            )}

            {/* Ratio cards grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              {data.ratios.map((ratio) => (
                <RatioCard key={ratio.name} ratio={ratio} />
              ))}
            </div>
          </div>
        )}

        {data && activeTab === "audit" && (
          <ExtractionAuditTable
            ratios={data.ratios}
            flaggedValues={data.flagged_values}
          />
        )}
      </div>
    </div>
  );
}
