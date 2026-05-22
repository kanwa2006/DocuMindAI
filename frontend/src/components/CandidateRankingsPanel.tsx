"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "react-hot-toast";
import { API_BASE } from "../lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface JobRole {
  id: string;
  title: string;
  department?: string;
  status: string;
  created_at: string;
}

interface CandidateRow {
  profile: {
    id: string;
    name?: string;
    skills: string[];
    experience_years?: number;
    stage?: string;
  };
  match: {
    id: string;
    fit_score?: number;
    final_score?: number;
    semantic_score?: number;
    match_analysis?: {
      pros?: string[];
      cons?: string[];
      missing_skills?: string[];
    };
    status: string;
  };
}

type SortField = "rank" | "name" | "score" | "experience";
type SortDir = "asc" | "desc";

const VALID_STAGES = [
  "applied", "screened", "shortlisted", "interviewed", "offered", "hired", "rejected",
] as const;

// V2: pipeline stage colors routed through tokens / warm-cool semantics
// so the kanban stripe still reads at a glance without dropping a
// hardcoded indigo/azure into the otherwise neutral ChatGPT-style UI.
const STAGE_COLORS: Record<string, string> = {
  applied:     "var(--text-tertiary)",
  screened:    "var(--text-secondary)",
  shortlisted: "var(--text-primary)",
  interviewed: "var(--warning-text, #d97706)",
  offered:     "var(--success-text, #059669)",
  hired:       "var(--success-text, #16a34a)",
  rejected:    "var(--error-text, #dc2626)",
};

// ── Score pill ────────────────────────────────────────────────────────────────

function ScorePill({ score }: { score: number }) {
  const color = score >= 80 ? "#16a34a" : score >= 60 ? "#d97706" : "#dc2626";
  const bg   = score >= 80 ? "rgba(22,163,74,0.1)" : score >= 60 ? "rgba(217,119,6,0.1)" : "rgba(220,38,38,0.1)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      <div style={{
        display: "inline-block", minWidth: "44px", textAlign: "center",
        background: bg, color, border: `1px solid ${color}40`,
        borderRadius: "20px", padding: "2px 10px",
        fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 600,
      }}>
        {score.toFixed(1)}
      </div>
      {/* Color bar */}
      <div style={{ width: "60px", height: "6px", background: "var(--border-subtle)", borderRadius: "3px", overflow: "hidden" }}>
        <div style={{
          width: `${Math.min(score, 100)}%`, height: "100%",
          background: color, borderRadius: "3px", transition: "width 400ms",
        }} />
      </div>
    </div>
  );
}

// ── Initials avatar ───────────────────────────────────────────────────────────

function Avatar({ name }: { name?: string }) {
  const initials = (name || "?")
    .split(" ").slice(0, 2).map((w) => w[0]?.toUpperCase() || "").join("");
  const hue = (name || "").split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div style={{
      width: "32px", height: "32px", borderRadius: "50%", flexShrink: 0,
      background: `hsl(${hue}, 55%, 55%)`, display: "flex",
      alignItems: "center", justifyContent: "center",
      fontFamily: "var(--font-body)", fontSize: "12px", fontWeight: 600, color: "#fff",
    }}>
      {initials}
    </div>
  );
}

// ── Stage badge ───────────────────────────────────────────────────────────────

function StageBadge({ stage }: { stage?: string }) {
  const s = stage || "applied";
  const color = STAGE_COLORS[s] || "var(--text-tertiary)";
  return (
    <span style={{
      padding: "2px 8px", borderRadius: "10px", fontSize: "11px",
      fontFamily: "var(--font-body)", fontWeight: 500, textTransform: "capitalize",
      background: `${color}18`, color, border: `1px solid ${color}40`,
    }}>
      {s}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  onClose: () => void;
}

export default function CandidateRankingsPanel({ onClose }: Props) {
  const [jobs, setJobs] = useState<JobRole[]>([]);
  const [selectedJob, setSelectedJob] = useState<string>("");
  const [candidates, setCandidates] = useState<CandidateRow[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkStage, setBulkStage] = useState("shortlisted");
  const [sortField, setSortField] = useState<SortField>("rank");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [scoringId, setScoringId] = useState<string | null>(null);

  // Load jobs on mount
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/hr/jobs`, { credentials: "include" });
        if (res.ok) {
          const data: JobRole[] = await res.json();
          setJobs(data);
          if (data.length === 1) setSelectedJob(data[0].id);
        }
      } catch {
        toast.error("Failed to load jobs");
      } finally {
        setLoadingJobs(false);
      }
    })();
  }, []);

  // Load candidates when job selected
  useEffect(() => {
    if (!selectedJob) return;
    setLoadingCandidates(true);
    (async () => {
      try {
        const res = await fetch(
          `${API_BASE}/hr/jobs/${selectedJob}/candidates`,
          { credentials: "include" }
        );
        if (res.ok) {
          const data: CandidateRow[] = await res.json();
          setCandidates(data);
        }
      } catch {
        toast.error("Failed to load candidates");
      } finally {
        setLoadingCandidates(false);
      }
    })();
  }, [selectedJob]);

  const getDisplayScore = (row: CandidateRow) =>
    row.match.final_score ?? row.match.fit_score ?? 0;

  const sorted = [...candidates].sort((a, b) => {
    let av = 0, bv = 0;
    if (sortField === "score" || sortField === "rank") {
      av = getDisplayScore(a); bv = getDisplayScore(b);
    } else if (sortField === "name") {
      av = (a.profile.name || "").localeCompare(b.profile.name || "") as unknown as number;
      return sortDir === "asc" ? (a.profile.name || "").localeCompare(b.profile.name || "") : (b.profile.name || "").localeCompare(a.profile.name || "");
    } else if (sortField === "experience") {
      av = a.profile.experience_years ?? 0; bv = b.profile.experience_years ?? 0;
    }
    return sortDir === "asc" ? av - bv : bv - av;
  });

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortField(field); setSortDir("desc"); }
  };

  const updateStage = useCallback(async (candidateId: string, stage: string) => {
    try {
      const res = await fetch(`${API_BASE}/hr/candidates/${candidateId}/stage`, {
        method: "PATCH", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage }),
      });
      if (!res.ok) throw new Error("Stage update failed");
      setCandidates((prev) =>
        prev.map((c) =>
          c.profile.id === candidateId
            ? { ...c, profile: { ...c.profile, stage } }
            : c
        )
      );
      toast.success(`Stage updated to ${stage}`);
    } catch {
      toast.error("Failed to update stage");
    }
  }, []);

  const triggerScore = useCallback(async (row: CandidateRow) => {
    setScoringId(row.profile.id);
    try {
      const res = await fetch(
        `${API_BASE}/hr/jobs/${selectedJob}/candidates/${row.profile.id}/score`,
        { method: "POST", credentials: "include" }
      );
      if (!res.ok) throw new Error("Scoring failed");
      const data = await res.json();
      setCandidates((prev) =>
        prev.map((c) =>
          c.profile.id === row.profile.id
            ? { ...c, match: { ...c.match, final_score: data.match_score } }
            : c
        )
      );
      toast.success(`Semantic score: ${data.match_score}`);
    } catch {
      toast.error("Failed to compute semantic score");
    } finally {
      setScoringId(null);
    }
  }, [selectedJob]);

  const bulkApply = useCallback(async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    await Promise.all(ids.map((id) => updateStage(id, bulkStage)));
    setSelectedIds(new Set());
  }, [selectedIds, bulkStage, updateStage]);

  const exportCSV = useCallback(() => {
    const headers = ["Rank", "Name", "Score", "Skills", "Experience (yrs)", "Stage", "Status"];
    const rows = sorted.map((c, i) => [
      i + 1,
      c.profile.name || "",
      getDisplayScore(c).toFixed(1),
      (c.profile.skills || []).slice(0, 5).join("; "),
      c.profile.experience_years ?? "",
      c.profile.stage || "applied",
      c.match.status,
    ]);
    const csv = [headers, ...rows]
      .map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `candidates_${selectedJob}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [sorted, selectedJob]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const thStyle: React.CSSProperties = {
    padding: "8px 12px", textAlign: "left",
    fontFamily: "var(--font-body)", fontSize: "11px", fontWeight: 600,
    color: "var(--text-tertiary)", textTransform: "uppercase",
    letterSpacing: "0.05em", background: "var(--surface-sunken)",
    borderBottom: "1px solid var(--border-default)", whiteSpace: "nowrap",
    cursor: "pointer", userSelect: "none",
  };

  const tdStyle: React.CSSProperties = {
    padding: "10px 12px", borderBottom: "1px solid var(--border-subtle)",
    fontFamily: "var(--font-body)", fontSize: "13px",
    color: "var(--text-primary)", verticalAlign: "middle",
  };

  const sortArrow = (field: SortField) =>
    sortField === field ? (sortDir === "desc" ? " ↓" : " ↑") : " ↕";

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 40,
      background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "stretch",
    }}>
      {/* Click-away close */}
      <div style={{ flex: 1 }} onClick={onClose} />

      {/* Panel */}
      <div style={{
        width: "min(900px, 96vw)", background: "var(--surface-base)",
        borderLeft: "1px solid var(--border-subtle)",
        display: "flex", flexDirection: "column", overflow: "hidden",
        boxShadow: "-4px 0 32px rgba(0,0,0,0.18)",
      }}>

        {/* Header */}
        <div style={{
          padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)",
          display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
        }}>
          <span style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" }}>
            📊 Candidate Rankings
          </span>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button onClick={exportCSV} className="btn btn-secondary btn-sm" style={{ height: "32px", fontSize: "12px" }}>
              📥 Export CSV
            </button>
            <button onClick={onClose} style={{ width: "28px", height: "28px", border: "none", background: "none", cursor: "pointer", fontSize: "18px", color: "var(--text-tertiary)" }}>×</button>
          </div>
        </div>

        {/* Job selector */}
        <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
          {loadingJobs ? (
            <div style={{ fontSize: "13px", color: "var(--text-tertiary)" }}>Loading jobs…</div>
          ) : jobs.length === 0 ? (
            <div style={{ fontSize: "13px", color: "var(--text-tertiary)" }}>No jobs found. Create a job role first.</div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", fontFamily: "var(--font-body)", fontWeight: 500 }}>Job Role:</label>
              <select
                value={selectedJob}
                onChange={(e) => setSelectedJob(e.target.value)}
                style={{
                  height: "32px", padding: "0 10px", border: "1px solid var(--border-default)",
                  borderRadius: "6px", fontSize: "13px", background: "var(--surface-raised)",
                  color: "var(--text-primary)", fontFamily: "var(--font-body)", outline: "none",
                }}
              >
                <option value="">— Select a job —</option>
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>{j.title}{j.department ? ` · ${j.department}` : ""}</option>
                ))}
              </select>
              {selectedJob && !loadingCandidates && (
                <span style={{ fontSize: "12px", color: "var(--text-tertiary)" }}>
                  {sorted.length} candidate{sorted.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Bulk actions bar (shown when rows checked) */}
        {selectedIds.size > 0 && (
          <div style={{
            padding: "8px 20px", background: "var(--brand-ghost, rgba(99,102,241,0.06))",
            borderBottom: "1px solid var(--border-default)", display: "flex", alignItems: "center", gap: "10px", flexShrink: 0,
          }}>
            <span style={{ fontSize: "13px", fontFamily: "var(--font-body)", color: "var(--text-primary)", fontWeight: 500 }}>
              {selectedIds.size} selected — Move to:
            </span>
            <select
              value={bulkStage}
              onChange={(e) => setBulkStage(e.target.value)}
              style={{ height: "30px", padding: "0 8px", border: "1px solid var(--border-default)", borderRadius: "6px", fontSize: "12px", background: "var(--surface-raised)", color: "var(--text-primary)", outline: "none" }}
            >
              {VALID_STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button onClick={bulkApply} className="btn btn-primary btn-sm" style={{ height: "30px", fontSize: "12px" }}>Apply</button>
            <button onClick={() => setSelectedIds(new Set())} className="btn btn-ghost btn-sm" style={{ height: "30px", fontSize: "12px" }}>Clear</button>
          </div>
        )}

        {/* Table */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {loadingCandidates ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-tertiary)", fontSize: "14px" }}>
              Loading candidates…
            </div>
          ) : !selectedJob ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-tertiary)", fontSize: "14px" }}>
              Select a job role above to view candidate rankings.
            </div>
          ) : sorted.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center" }}>
              <div style={{ fontSize: "40px", marginBottom: "8px" }}>👥</div>
              <div style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
                No candidates processed yet. Upload resumes and use "Set JD Context" to begin.
              </div>
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead style={{ position: "sticky", top: 0, zIndex: 1 }}>
                <tr>
                  <th style={{ ...thStyle, width: "36px" }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.size === sorted.length && sorted.length > 0}
                      onChange={(e) => setSelectedIds(e.target.checked ? new Set(sorted.map((c) => c.profile.id)) : new Set())}
                    />
                  </th>
                  <th style={thStyle} onClick={() => toggleSort("rank")}>Rank{sortArrow("rank")}</th>
                  <th style={thStyle} onClick={() => toggleSort("name")}>Candidate{sortArrow("name")}</th>
                  <th style={thStyle} onClick={() => toggleSort("score")}>Score{sortArrow("score")}</th>
                  <th style={thStyle}>Skills Match</th>
                  <th style={thStyle} onClick={() => toggleSort("experience")}>Exp.{sortArrow("experience")}</th>
                  <th style={thStyle}>Stage</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((row, idx) => {
                  const score = getDisplayScore(row);
                  const isSelected = selectedIds.has(row.profile.id);
                  const skills = row.profile.skills || [];
                  const isScoring = scoringId === row.profile.id;
                  const hasSemanticScore = row.match.final_score !== undefined && row.match.final_score !== null;

                  return (
                    <tr
                      key={row.match.id}
                      style={{
                        background: isSelected ? "var(--brand-ghost, rgba(99,102,241,0.06))" : undefined,
                        transition: "background 100ms",
                      }}
                      onMouseEnter={(e) => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = "var(--surface-raised)"; }}
                      onMouseLeave={(e) => { if (!isSelected) (e.currentTarget as HTMLElement).style.background = ""; }}
                    >
                      {/* Checkbox */}
                      <td style={tdStyle}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(row.profile.id)}
                        />
                      </td>
                      {/* Rank */}
                      <td style={{ ...tdStyle, fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--text-tertiary)", width: "48px" }}>
                        #{idx + 1}
                      </td>
                      {/* Candidate name + avatar */}
                      <td style={{ ...tdStyle, minWidth: "160px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <Avatar name={row.profile.name} />
                          <div>
                            <div style={{ fontWeight: 500, fontSize: "13px" }}>{row.profile.name || "Unknown"}</div>
                            {!hasSemanticScore && (
                              <div style={{ fontSize: "10px", color: "var(--text-tertiary)" }}>LLM score only</div>
                            )}
                          </div>
                        </div>
                      </td>
                      {/* Score */}
                      <td style={tdStyle}>
                        <ScorePill score={score} />
                      </td>
                      {/* Skills */}
                      <td style={{ ...tdStyle, maxWidth: "200px" }}>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                          {skills.slice(0, 4).map((s) => (
                            <span key={s} style={{
                              padding: "1px 6px", background: "var(--surface-sunken)",
                              border: "1px solid var(--border-subtle)", borderRadius: "4px",
                              fontSize: "11px", color: "var(--text-secondary)",
                            }}>{s}</span>
                          ))}
                          {skills.length > 4 && (
                            <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>+{skills.length - 4}</span>
                          )}
                        </div>
                      </td>
                      {/* Experience */}
                      <td style={{ ...tdStyle, fontFamily: "var(--font-mono)", fontSize: "12px", textAlign: "center", width: "60px" }}>
                        {row.profile.experience_years != null ? `${row.profile.experience_years}y` : "—"}
                      </td>
                      {/* Stage badge */}
                      <td style={tdStyle}>
                        <StageBadge stage={row.profile.stage} />
                      </td>
                      {/* Action buttons */}
                      <td style={tdStyle}>
                        <div style={{ display: "flex", gap: "4px" }}>
                          <button
                            title="Shortlist"
                            onClick={() => updateStage(row.profile.id, "shortlisted")}
                            style={{ width: "28px", height: "28px", border: "1px solid var(--border-default)", borderRadius: "6px", background: "none", cursor: "pointer", fontSize: "14px", display: "flex", alignItems: "center", justifyContent: "center", transition: "border-color 100ms" }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#16a34a"; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}
                          >✓</button>
                          <button
                            title="Reject"
                            onClick={() => updateStage(row.profile.id, "rejected")}
                            style={{ width: "28px", height: "28px", border: "1px solid var(--border-default)", borderRadius: "6px", background: "none", cursor: "pointer", fontSize: "14px", display: "flex", alignItems: "center", justifyContent: "center", transition: "border-color 100ms" }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "#dc2626"; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}
                          >✗</button>
                          <button
                            title={hasSemanticScore ? "Re-score semantically" : "Compute semantic score"}
                            onClick={() => triggerScore(row)}
                            disabled={isScoring}
                            style={{ width: "28px", height: "28px", border: `1px solid ${hasSemanticScore ? "var(--brand)" : "var(--border-default)"}`, borderRadius: "6px", background: "none", cursor: isScoring ? "wait" : "pointer", fontSize: "12px", display: "flex", alignItems: "center", justifyContent: "center", transition: "border-color 100ms", opacity: isScoring ? 0.5 : 1 }}
                          >{isScoring ? "…" : "🎯"}</button>
                          <button
                            title="View Profile"
                            style={{ width: "28px", height: "28px", border: "1px solid var(--border-default)", borderRadius: "6px", background: "none", cursor: "pointer", fontSize: "14px", display: "flex", alignItems: "center", justifyContent: "center", transition: "border-color 100ms" }}
                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; }}
                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}
                          >📋</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
