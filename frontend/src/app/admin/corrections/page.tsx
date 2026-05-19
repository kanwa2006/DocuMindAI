"use client";

import { useEffect, useState, useCallback } from "react";
import { API_BASE, getCsrfToken } from "@/lib/api";
import { toast } from "react-hot-toast";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Correction {
  id: string;
  created_at: string;
  workspace_id: string;
  issue_type: string;
  status: string;
  reporter_confidence: string;
  incorrect_excerpt: string | null;
  suggested_correction: string | null;
  citation_id: string | null;
  reviewer_id: string | null;
  reviewed_at: string | null;
  eval_query_created: boolean;
  user_id: string;
  session_id: string | null;
}

interface TrendEntry {
  week_start: string;
  issue_type: string;
  count: number;
}

type StatusFilter = "all" | "pending" | "approved" | "rejected" | "escalated";

const STATUS_COLORS: Record<string, string> = {
  pending: "var(--warning, #d97706)",
  approved: "var(--success, #16a34a)",
  rejected: "var(--text-tertiary, #6b7280)",
  escalated: "var(--error, #dc2626)",
};

const ISSUE_LABELS: Record<string, string> = {
  citation_wrong: "Citation Wrong",
  answer_incorrect: "Answer Incorrect",
  missing_info: "Missing Information",
  hallucination: "Hallucination",
  source_not_found: "Source Not Found",
  other: "Other",
  positive_verification: "Positive Verification",
};

const CHART_COLORS = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"];

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export default function AdminCorrectionsPage() {
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [trends, setTrends] = useState<TrendEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [noteInput, setNoteInput] = useState<Record<string, string>>({});
  const [showNoteFor, setShowNoteFor] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [workspaceFilter, setWorkspaceFilter] = useState("all");
  const [issueTypeFilter, setIssueTypeFilter] = useState("all");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  // Stats
  const pendingCount = corrections.filter((c) => c.status === "pending").length;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (workspaceFilter !== "all") params.set("workspace_id", workspaceFilter);
      if (issueTypeFilter !== "all") params.set("issue_type", issueTypeFilter);
      if (fromDate) params.set("from_date", fromDate);
      if (toDate) params.set("to_date", toDate);
      params.set("page_size", "50");

      const [cRes, tRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/corrections/admin?${params}`, { credentials: "include" }),
        fetch(`${API_BASE}/api/v1/corrections/admin/trends`, { credentials: "include" }),
      ]);
      if (cRes.ok) setCorrections(await cRes.json());
      if (tRes.ok) setTrends(await tRes.json());
    } catch {
      toast.error("Failed to load corrections");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, workspaceFilter, issueTypeFilter, fromDate, toDate]);

  useEffect(() => { load(); }, [load]);

  async function handleAction(
    correctionId: string,
    action: "approve" | "reject" | "escalate",
    note?: string
  ) {
    setActionLoading(correctionId);
    try {
      const res = await fetch(`${API_BASE}/api/v1/corrections/admin/${correctionId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({ action, note: note || undefined }),
      });
      if (!res.ok) throw new Error();
      const updated = await res.json();
      setCorrections((prev) =>
        prev.map((c) => (c.id === correctionId ? { ...c, status: updated.status } : c))
      );
      toast.success(
        action === "approve"
          ? updated.eval_query_id
            ? "✓ Approved — added to evaluation benchmarks"
            : "✓ Approved"
          : action === "reject"
          ? "Rejected"
          : "Escalated to senior review"
      );
    } catch {
      toast.error("Action failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleAddNote(correctionId: string) {
    const note = noteInput[correctionId]?.trim();
    if (!note) return;
    setActionLoading(correctionId);
    try {
      const res = await fetch(`${API_BASE}/api/v1/corrections/admin/${correctionId}/note`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({ note_text: note }),
      });
      if (!res.ok) throw new Error();
      toast.success("Note added");
      setNoteInput((p) => ({ ...p, [correctionId]: "" }));
      setShowNoteFor(null);
    } catch {
      toast.error("Failed to add note");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleExport() {
    const params = new URLSearchParams();
    if (workspaceFilter !== "all") params.set("workspace_id", workspaceFilter);
    if (fromDate) params.set("from_date", fromDate);
    if (toDate) params.set("to_date", toDate);
    window.location.href = `${API_BASE}/api/v1/corrections/admin/export?${params}`;
  }

  // Build chart data — aggregate by week
  const chartData = (() => {
    const byWeek: Record<string, Record<string, number>> = {};
    for (const entry of trends) {
      const week = entry.week_start.slice(0, 10);
      if (!byWeek[week]) byWeek[week] = {};
      byWeek[week][entry.issue_type] = (byWeek[week][entry.issue_type] || 0) + entry.count;
    }
    return Object.entries(byWeek)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([week, counts]) => ({ week, ...counts }));
  })();

  const allIssueTypes = [...new Set(trends.map((t) => t.issue_type))];
  const allWorkspaces = [...new Set(corrections.map((c) => c.workspace_id))];

  return (
    <main style={{ padding: "40px 48px" }}>
      {/* Header */}
      <div
        style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}
      >
        <div>
          <h1
            style={{
              fontFamily: "Instrument Serif, serif",
              fontSize: 28,
              color: "var(--text-primary)",
              marginBottom: 6,
            }}
          >
            Correction Review Queue
          </h1>
          <div style={{ display: "flex", gap: 8 }}>
            {pendingCount > 0 && (
              <span
                className="badge"
                style={{ background: "var(--warning-bg, #fef3c7)", color: "var(--warning, #d97706)", fontSize: 12 }}
              >
                {pendingCount} pending review
              </span>
            )}
            <span
              className="badge badge-success"
              style={{ fontSize: 12 }}
            >
              {corrections.filter((c) => c.status === "approved").length} resolved this week
            </span>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={handleExport}>
          ⬇ Export CSV
        </button>
      </div>

      {/* Filter Bar */}
      <div
        className="card"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          padding: "16px 20px",
          marginBottom: 24,
          alignItems: "center",
        }}
      >
        <div>
          <label style={{ fontSize: 12, color: "var(--text-tertiary)", display: "block", marginBottom: 4 }}>
            Status
          </label>
          <div style={{ display: "flex", gap: 4 }}>
            {(["all", "pending", "approved", "rejected", "escalated"] as StatusFilter[]).map((s) => (
              <button
                key={s}
                className={`btn btn-sm ${statusFilter === s ? "btn-primary" : "btn-ghost"}`}
                style={{ textTransform: "capitalize" }}
                onClick={() => setStatusFilter(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label htmlFor="ws-filter" style={{ fontSize: 12, color: "var(--text-tertiary)", display: "block", marginBottom: 4 }}>
            Workspace
          </label>
          <select
            id="ws-filter"
            className="form-control"
            style={{ fontSize: 13 }}
            value={workspaceFilter}
            onChange={(e) => setWorkspaceFilter(e.target.value)}
          >
            <option value="all">All workspaces</option>
            {allWorkspaces.map((w) => (
              <option key={w} value={w}>
                {w}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="type-filter" style={{ fontSize: 12, color: "var(--text-tertiary)", display: "block", marginBottom: 4 }}>
            Issue Type
          </label>
          <select
            id="type-filter"
            className="form-control"
            style={{ fontSize: 13 }}
            value={issueTypeFilter}
            onChange={(e) => setIssueTypeFilter(e.target.value)}
          >
            <option value="all">All types</option>
            {allIssueTypes.map((t) => (
              <option key={t} value={t}>
                {ISSUE_LABELS[t] ?? t}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 12, color: "var(--text-tertiary)", display: "block", marginBottom: 4 }}>
            Date Range
          </label>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              type="date"
              className="form-control"
              style={{ fontSize: 13 }}
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              aria-label="From date"
            />
            <span style={{ color: "var(--text-tertiary)", fontSize: 13 }}>to</span>
            <input
              type="date"
              className="form-control"
              style={{ fontSize: 13 }}
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              aria-label="To date"
            />
          </div>
        </div>
      </div>

      {/* Corrections Table */}
      <div className="card" style={{ marginBottom: 32, overflowX: "auto" }}>
        {loading ? (
          <p style={{ padding: 24, color: "var(--text-tertiary)", fontSize: 14 }}>Loading…</p>
        ) : corrections.length === 0 ? (
          <p style={{ padding: 24, color: "var(--text-tertiary)", fontSize: 14 }}>
            No corrections match the current filters.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-default)" }}>
                {["Time", "Workspace", "Issue Type", "Status", "Reporter", "Actions"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 14px",
                      textAlign: "left",
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--text-tertiary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {corrections.map((c) => (
                <>
                  <tr
                    key={c.id}
                    style={{
                      borderBottom: expanded === c.id ? "none" : "1px solid var(--border-subtle)",
                      cursor: "pointer",
                    }}
                    onClick={() => setExpanded((p) => (p === c.id ? null : c.id))}
                  >
                    <td style={{ padding: "12px 14px", fontSize: 13 }}>{formatDate(c.created_at)}</td>
                    <td style={{ padding: "12px 14px", fontSize: 13 }}>{c.workspace_id}</td>
                    <td style={{ padding: "12px 14px", fontSize: 13 }}>
                      {ISSUE_LABELS[c.issue_type] ?? c.issue_type}
                    </td>
                    <td style={{ padding: "12px 14px" }}>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          color: STATUS_COLORS[c.status] ?? "inherit",
                          textTransform: "capitalize",
                        }}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td style={{ padding: "12px 14px", fontSize: 12, color: "var(--text-tertiary)", fontFamily: "monospace" }}>
                      {c.user_id.slice(0, 8)}…
                    </td>
                    <td
                      style={{ padding: "12px 14px" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {c.status === "pending" && (
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: 12, color: "var(--success, #16a34a)" }}
                            onClick={() => handleAction(c.id, "approve")}
                            disabled={actionLoading === c.id}
                            title="Approve → Add to Benchmarks"
                          >
                            ✓ Approve
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: 12, color: "var(--error, #dc2626)" }}
                            onClick={() => handleAction(c.id, "reject")}
                            disabled={actionLoading === c.id}
                            title="Reject"
                          >
                            ✗ Reject
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: 12 }}
                            onClick={() => handleAction(c.id, "escalate")}
                            disabled={actionLoading === c.id}
                            title="Escalate to senior review"
                          >
                            → Escalate
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: 12 }}
                            onClick={() => setShowNoteFor((p) => (p === c.id ? null : c.id))}
                            title="Add internal note"
                          >
                            💬 Note
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>

                  {/* Expanded detail row */}
                  {expanded === c.id && (
                    <tr key={`${c.id}-detail`} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td
                        colSpan={6}
                        style={{
                          padding: "0 14px 16px 14px",
                          background: "var(--surface-hover, #f9fafb)",
                        }}
                      >
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, paddingTop: 12 }}>
                          <div>
                            <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 4 }}>
                              INCORRECT EXCERPT
                            </p>
                            <p style={{ fontSize: 13 }}>{c.incorrect_excerpt || "—"}</p>
                          </div>
                          <div>
                            <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 4 }}>
                              SUGGESTED CORRECTION
                            </p>
                            <p style={{ fontSize: 13 }}>{c.suggested_correction || "—"}</p>
                          </div>
                          <div>
                            <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 4 }}>
                              CITED SOURCE
                            </p>
                            <p style={{ fontSize: 13 }}>{c.citation_id || "—"}</p>
                          </div>
                          <div>
                            <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", marginBottom: 4 }}>
                              REPORTER CONFIDENCE
                            </p>
                            <p style={{ fontSize: 13, textTransform: "capitalize" }}>{c.reporter_confidence}</p>
                          </div>
                          {c.eval_query_created && (
                            <div style={{ gridColumn: "1 / -1" }}>
                              <span
                                className="badge badge-success"
                                style={{ fontSize: 11 }}
                              >
                                ✓ Eval benchmark query created
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Inline note form */}
                        {showNoteFor === c.id && (
                          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                            <input
                              className="form-control"
                              style={{ flex: 1, fontSize: 13 }}
                              placeholder="Add internal reviewer note…"
                              value={noteInput[c.id] || ""}
                              onChange={(e) =>
                                setNoteInput((p) => ({ ...p, [c.id]: e.target.value }))
                              }
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleAddNote(c.id);
                              }}
                            />
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handleAddNote(c.id)}
                              disabled={actionLoading === c.id}
                            >
                              Save Note
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Feedback Trend Chart */}
      {chartData.length > 0 && (
        <div className="card" style={{ padding: "24px 20px" }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>
            Feedback Trends (last 8 weeks)
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Legend />
              {allIssueTypes.map((type, i) => (
                <Bar
                  key={type}
                  dataKey={type}
                  name={ISSUE_LABELS[type] ?? type}
                  stackId="a"
                  fill={CHART_COLORS[i % CHART_COLORS.length]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </main>
  );
}
