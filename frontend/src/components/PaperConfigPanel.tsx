"use client";

import { useState } from "react";
import { toast } from "react-hot-toast";
import { apiFetch } from "../lib/api";

// PART 2 — per-question shape. When `questions` is provided + non-empty,
// the backend treats each item as authoritative (its own marks + sub_parts).
export interface QuestionSubPartConfig {
  label: string;
  marks: number;
}
export interface QuestionConfig {
  marks: number;
  sub_parts?: QuestionSubPartConfig[];
}

export interface ExamSectionConfig {
  label: string;
  question_type: string;
  marks_per_question: number;   // float (allow decimals like 2.5)
  count: number;
  allow_subquestions: boolean;
  // derived: total_marks = marks_per_question * count
  // PART 2 — when set, overrides count/marks_per_question/allow_subquestions
  questions?: QuestionConfig[];
}

export interface PaperConfig {
  subject: string;
  board: string;
  total_marks: number;
  duration_minutes: number;
  difficulty: string;
  bloom_distribution: Record<string, number>;
  sections: ExamSectionConfig[];
  instructions: string;
}

interface Props {
  onClose: () => void;
  onGenerated: (result: any) => void;
  // PART 1 — needed so the backend can scope retrieval to THIS chat's
  // uploaded documents. Without it, the backend refuses with a clear
  // "no documents attached" message.
  chatSessionId?: string;
}

const BOARDS = ["CBSE", "ICSE", "State Board", "University", "JEE/NEET Style"];
// B3: MEDIUM added between SHORT and LONG
const QUESTION_TYPES = ["mcq", "short", "medium", "long", "case_study"];
const SECTION_LABELS = ["A", "B", "C", "D", "E"];

// Format a number, trimming trailing zeros: 2.5 -> "2.5", 2.0 -> "2"
function fmt(n: number): string {
  if (!isFinite(n)) return "0";
  return Number.isInteger(n) ? n.toString() : Number(n.toFixed(2)).toString();
}

function BloomSlider({ value, onChange }: {
  value: [number, number, number];
  onChange: (v: [number, number, number]) => void;
}) {
  const [l1, l3, l5] = value;
  const total = l1 + l3 + l5;
  const isValid = total === 100;

  return (
    <div>
      <div style={{ display: "flex", gap: "6px", alignItems: "center", marginBottom: "4px" }}>
        {[["L1-L2", l1, 0], ["L3-L4", l3, 1], ["L5-L6", l5, 2]].map(([label, val, idx]) => (
          <div key={label as string} style={{ flex: 1 }}>
            <label style={{ fontSize: "10px", color: "var(--text-tertiary)", display: "block", marginBottom: "2px" }}>{label as string}</label>
            <input
              type="number" min={0} max={100}
              value={val as number}
              onChange={(e) => {
                const nv = parseInt(e.target.value) || 0;
                const next: [number, number, number] = [...value] as [number, number, number];
                next[idx as number] = nv;
                onChange(next);
              }}
              style={{ width: "100%", height: "32px", border: "1px solid var(--border-default)", borderRadius: "6px", padding: "0 8px", fontSize: "13px", background: "var(--surface-base)", color: "var(--text-primary)", outline: "none" }}
            />
          </div>
        ))}
      </div>
      {/* Visual bar */}
      <div style={{ height: "6px", borderRadius: "3px", overflow: "hidden", background: "var(--border-subtle)", display: "flex" }}>
        <div style={{ width: `${l1}%`, background: "var(--brand)", opacity: 0.6, transition: "width 200ms" }} />
        <div style={{ width: `${l3}%`, background: "var(--brand)", opacity: 0.85, transition: "width 200ms" }} />
        <div style={{ width: `${l5}%`, background: "var(--brand)", transition: "width 200ms" }} />
      </div>
      <div style={{ fontSize: "11px", marginTop: "4px", color: isValid ? "var(--success-text, #22c55e)" : "var(--error-text, #ef4444)" }}>
        Total: {total}/100 {isValid ? "✓" : "⚠ Must equal 100"}
      </div>
    </div>
  );
}

export default function PaperConfigPanel({ onClose, onGenerated, chatSessionId }: Props) {
  // B5: sensible defaults — Total 100, Duration 180, Difficulty Mixed are already defaults.
  const [subject, setSubject] = useState("");
  const [board, setBoard] = useState("CBSE");
  const [totalMarks, setTotalMarks] = useState(100);
  const [duration, setDuration] = useState(180);
  const [difficulty, setDifficulty] = useState<"easy" | "mixed" | "hard">("mixed");
  const [bloom, setBloom] = useState<[number, number, number]>([30, 40, 30]);
  const [instructions, setInstructions] = useState("");
  const [sections, setSections] = useState<ExamSectionConfig[]>([
    { label: "A", question_type: "mcq",   marks_per_question: 2, count: 20, allow_subquestions: false },
    { label: "B", question_type: "short", marks_per_question: 5, count: 6,  allow_subquestions: false },
    { label: "C", question_type: "long",  marks_per_question: 10, count: 3, allow_subquestions: false },
  ]);
  const [generating, setGenerating] = useState(false);

  // PART 2: section total derives from per-question marks (if set) OR
  // marks_per_question × count (legacy section-level shape).
  const sectionTotalFor = (s: ExamSectionConfig): number => {
    if (s.questions && s.questions.length > 0) {
      return s.questions.reduce(
        (acc, q) => acc + (q.sub_parts && q.sub_parts.length > 0
          ? q.sub_parts.reduce((a, sp) => a + sp.marks, 0)
          : q.marks),
        0,
      );
    }
    return s.marks_per_question * s.count;
  };
  const sectionTotals = sections.map(sectionTotalFor);
  const sectionTotal = sectionTotals.reduce((a, b) => a + b, 0);
  const bloomTotal = bloom[0] + bloom[1] + bloom[2];
  const marksOk = Math.abs(sectionTotal - totalMarks) < 0.01;
  const bloomOk = bloomTotal === 100;
  const canGenerate = subject.trim().length > 0 && marksOk && bloomOk && sections.length > 0;
  const marksDelta = totalMarks - sectionTotal;

  const addSection = () => {
    const nextLabel = SECTION_LABELS[sections.length] || String.fromCharCode(65 + sections.length);
    setSections((prev) => [...prev, { label: nextLabel, question_type: "mcq", marks_per_question: 2, count: 5, allow_subquestions: false }]);
  };

  const removeSection = (idx: number) =>
    setSections((prev) => prev.filter((_, i) => i !== idx));

  const updateSection = (idx: number, field: keyof ExamSectionConfig, val: any) =>
    setSections((prev) => prev.map((s, i) => i === idx ? { ...s, [field]: val } : s));

  // PART 2 — per-question helpers. "Custom questions" turns ON when the
  // user wants per-question sub-parts; turning it OFF clears the per-Q list.
  const enableCustomQuestions = (idx: number) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== idx) return s;
      if (s.questions && s.questions.length > 0) return s;
      const seed: QuestionConfig[] = Array.from({ length: s.count }, () => ({
        marks: s.marks_per_question,
      }));
      return { ...s, questions: seed };
    }));
  };
  const disableCustomQuestions = (idx: number) => {
    setSections((prev) => prev.map((s, i) => i === idx ? { ...s, questions: undefined } : s));
  };
  const updateQuestion = (sIdx: number, qIdx: number, patch: Partial<QuestionConfig>) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== sIdx || !s.questions) return s;
      const next = s.questions.map((q, j) => j === qIdx ? { ...q, ...patch } : q);
      return { ...s, questions: next, count: next.length };
    }));
  };
  const addQuestion = (sIdx: number) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== sIdx || !s.questions) return s;
      const next = [...s.questions, { marks: s.marks_per_question || 1 }];
      return { ...s, questions: next, count: next.length };
    }));
  };
  const removeQuestion = (sIdx: number, qIdx: number) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== sIdx || !s.questions) return s;
      const next = s.questions.filter((_, j) => j !== qIdx);
      return { ...s, questions: next, count: next.length };
    }));
  };
  const addSubPart = (sIdx: number, qIdx: number) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== sIdx || !s.questions) return s;
      const next = s.questions.map((q, j) => {
        if (j !== qIdx) return q;
        const existing = q.sub_parts || [];
        const half = (q.marks || 2) / Math.max(existing.length + 1, 1);
        const nextLabel = String.fromCharCode("a".charCodeAt(0) + existing.length);
        return { ...q, sub_parts: [...existing, { label: nextLabel, marks: Number(half.toFixed(2)) }] };
      });
      return { ...s, questions: next };
    }));
  };
  const updateSubPart = (sIdx: number, qIdx: number, spIdx: number, patch: Partial<QuestionSubPartConfig>) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== sIdx || !s.questions) return s;
      const next = s.questions.map((q, j) => {
        if (j !== qIdx || !q.sub_parts) return q;
        return { ...q, sub_parts: q.sub_parts.map((sp, k) => k === spIdx ? { ...sp, ...patch } : sp) };
      });
      return { ...s, questions: next };
    }));
  };
  const removeSubPart = (sIdx: number, qIdx: number, spIdx: number) => {
    setSections((prev) => prev.map((s, i) => {
      if (i !== sIdx || !s.questions) return s;
      const next = s.questions.map((q, j) => {
        if (j !== qIdx || !q.sub_parts) return q;
        const filtered = q.sub_parts.filter((_, k) => k !== spIdx);
        return { ...q, sub_parts: filtered.length > 0 ? filtered : undefined };
      });
      return { ...s, questions: next };
    }));
  };

  const handleGenerate = async () => {
    if (!canGenerate) return;
    setGenerating(true);
    const toastId = toast.loading("Generating exam paper…");
    try {
      // Translate panel state into the backend contract. When `questions`
      // is present (PART 2 per-question control), forward it verbatim;
      // total_marks/count derive from the questions array on the backend.
      const sectionsPayload = sections.map((s) => {
        if (s.questions && s.questions.length > 0) {
          const sectionTotal = s.questions.reduce(
            (acc, q) => acc + (q.sub_parts && q.sub_parts.length > 0
              ? q.sub_parts.reduce((a, sp) => a + sp.marks, 0)
              : q.marks),
            0,
          );
          return {
            label: s.label,
            question_type: s.question_type,
            total_marks: Number(sectionTotal.toFixed(2)),
            count: s.questions.length,
            marks_per_question: s.marks_per_question,  // legacy hint
            allow_subquestions: s.allow_subquestions,
            questions: s.questions.map((q) => ({
              marks: q.marks,
              sub_parts: q.sub_parts && q.sub_parts.length > 0 ? q.sub_parts : undefined,
            })),
          };
        }
        // Section-level fallback (existing UI shape).
        return {
          label: s.label,
          question_type: s.question_type,
          total_marks: Number((s.marks_per_question * s.count).toFixed(2)),
          count: s.count,
          marks_per_question: s.marks_per_question,
          allow_subquestions: s.allow_subquestions,
        };
      });

      // P4: switch from raw fetch() to apiFetch() so the CSRF token and
      // auto-refresh logic are applied. The previous raw fetch was missing
      // the X-CSRF-Token header — the backend middleware bounced it with a
      // 403, and the browser surfaced "Failed to fetch" because the
      // response body wasn't parseable as JSON. apiFetch handles all of
      // that uniformly.
      const res = await apiFetch(`/exams/generate/paper`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          board,
          total_marks: totalMarks,
          duration_minutes: duration,
          difficulty,
          instructions,
          bloom_distribution: {
            "L1-L2": bloom[0],
            "L3-L4": bloom[1],
            "L5-L6": bloom[2],
          },
          sections: sectionsPayload,
          // PART 1 — bind generation to THIS chat so the backend can
          // retrieve from the uploaded docs and refuse cleanly if none.
          chat_session_id: chatSessionId || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const msgs: string[] = err?.detail?.validation_errors || [err?.detail || `Generation failed (HTTP ${res.status})`];
        toast.error(msgs[0], { id: toastId });
        return;
      }
      const data = await res.json();
      toast.success("Paper generated!", { id: toastId });
      onGenerated(data);
      onClose();
    } catch (e: any) {
      toast.error(e.message || "Generation failed", { id: toastId });
    } finally {
      setGenerating(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%", height: "40px", border: "1px solid var(--border-default)",
    borderRadius: "8px", padding: "0 12px", fontSize: "13px",
    background: "var(--surface-base)", color: "var(--text-primary)",
    fontFamily: "var(--font-body)", outline: "none",
  };
  const labelStyle: React.CSSProperties = {
    fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)",
    fontWeight: 500, marginBottom: "4px", display: "block",
  };

  return (
    <div style={{
      position: "fixed", top: 0, right: 0, bottom: 0, width: "360px",
      background: "var(--surface-raised)", borderLeft: "1px solid var(--border-subtle)",
      zIndex: 50, display: "flex", flexDirection: "column", overflow: "hidden",
      boxShadow: "-4px 0 24px rgba(0,0,0,0.12)",
    }}>
      {/* Header */}
      <div style={{ padding: "16px", borderBottom: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <span style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" }}>Paper Configuration</span>
        <button onClick={onClose} aria-label="Close" style={{ width: "32px", height: "32px", border: "none", background: "none", cursor: "pointer", fontSize: "20px", color: "var(--text-tertiary)", display: "flex", alignItems: "center", justifyContent: "center" }}>×</button>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "14px" }}>

        {/* Subject */}
        <div>
          <label style={labelStyle}>Subject</label>
          <input value={subject} onChange={(e) => setSubject(e.target.value)}
            placeholder="Mathematics / Physics / Chemistry…" style={inputStyle} />
        </div>

        {/* Board */}
        <div>
          <label style={labelStyle}>Board</label>
          <select value={board} onChange={(e) => setBoard(e.target.value)} style={{ ...inputStyle, appearance: "none" }}>
            {BOARDS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </div>

        {/* Total Marks + Duration */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          <div>
            <label style={labelStyle}>Total Marks</label>
            <input type="number" value={totalMarks} min={1} step={0.5}
              onChange={(e) => setTotalMarks(parseFloat(e.target.value) || 0)} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Duration (min)</label>
            <input type="number" value={duration} min={1}
              onChange={(e) => setDuration(parseInt(e.target.value) || 0)} style={inputStyle} />
          </div>
        </div>

        {/* Difficulty */}
        <div>
          <label style={labelStyle}>Difficulty</label>
          <div style={{ display: "flex", border: "1px solid var(--border-default)", borderRadius: "8px", overflow: "hidden" }}>
            {(["easy", "mixed", "hard"] as const).map((d) => (
              <button key={d} onClick={() => setDifficulty(d)} style={{
                flex: 1, height: "36px", border: "none", cursor: "pointer", fontSize: "12px",
                fontFamily: "var(--font-body)", fontWeight: difficulty === d ? 600 : 400,
                background: difficulty === d ? "var(--accent, var(--brand))" : "transparent",
                color: difficulty === d ? "var(--brand-text)" : "var(--text-secondary)",
                textTransform: "capitalize", transition: "background 150ms, color 150ms",
              }}>{d}</button>
            ))}
          </div>
        </div>

        {/* Bloom's Distribution */}
        <div>
          <label style={labelStyle}>Bloom's Distribution (%)</label>
          <BloomSlider value={bloom} onChange={setBloom} />
        </div>

        {/* Instructions */}
        <div>
          <label style={labelStyle}>Instructions (optional)</label>
          <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)}
            placeholder="All questions are compulsory…"
            rows={2}
            style={{ ...inputStyle, height: "auto", padding: "8px 12px", resize: "none" }} />
        </div>

        {/* Section Builder */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <label style={labelStyle}>Sections</label>
            <button onClick={addSection} className="btn btn-secondary btn-sm" style={{ height: "28px", fontSize: "12px" }}>+ Add Section</button>
          </div>

          {sections.map((sec, idx) => {
            const secTotal = sectionTotalFor(sec);
            const customQuestions = !!sec.questions && sec.questions.length > 0;
            return (
              <div key={idx} style={{ border: "1px solid var(--border-default)", borderRadius: "8px", padding: "12px", marginBottom: "10px", background: "var(--surface-base)" }}>
                <div style={{ display: "grid", gridTemplateColumns: "40px 1fr 28px", gap: "6px", marginBottom: "10px", alignItems: "center" }}>
                  <input value={sec.label} maxLength={2}
                    aria-label="Section label"
                    onChange={(e) => updateSection(idx, "label", e.target.value.toUpperCase())}
                    style={{ ...inputStyle, textAlign: "center", fontWeight: 600 }} />
                  <select value={sec.question_type} onChange={(e) => updateSection(idx, "question_type", e.target.value)}
                    aria-label="Section question type"
                    style={{ ...inputStyle, appearance: "none" }}>
                    {QUESTION_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ").toUpperCase()}</option>)}
                  </select>
                  <button onClick={() => removeSection(idx)} aria-label="Remove section" style={{ width: "28px", height: "28px", border: "none", background: "none", cursor: "pointer", fontSize: "16px", color: "var(--error-text, #ef4444)" }}>×</button>
                </div>

                {!customQuestions && (
                  <>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", alignItems: "center" }}>
                      <div>
                        <label style={{ ...labelStyle, fontSize: "10px" }}>Marks / Question</label>
                        <input type="number" min={0.5} step={0.5} value={sec.marks_per_question}
                          onChange={(e) => updateSection(idx, "marks_per_question", parseFloat(e.target.value) || 0)}
                          style={{ ...inputStyle, fontSize: "12px", height: "32px" }} />
                      </div>
                      <div>
                        <label style={{ ...labelStyle, fontSize: "10px" }}># of Questions</label>
                        <input type="number" min={1} value={sec.count}
                          onChange={(e) => updateSection(idx, "count", parseInt(e.target.value) || 1)}
                          style={{ ...inputStyle, fontSize: "12px", height: "32px" }} />
                      </div>
                    </div>

                    <div style={{ fontSize: "11px", color: "var(--text-tertiary)", marginTop: "6px" }}>
                      {sec.count} × {fmt(sec.marks_per_question)} marks = <strong style={{ color: "var(--text-secondary)" }}>{fmt(secTotal)}</strong>
                    </div>

                    <label style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "8px", cursor: "pointer", fontSize: "12px", color: "var(--text-secondary)" }}>
                      <input type="checkbox" checked={sec.allow_subquestions}
                        onChange={(e) => updateSection(idx, "allow_subquestions", e.target.checked)} />
                      Allow sub-parts (a, b, c) in this section
                    </label>
                  </>
                )}

                {/* PART 2 — per-question editor. Lets the teacher mix questions
                    that have sub-parts with ones that don't, inside a single
                    section. Toggle ON to expand into per-Q rows. */}
                <div style={{ marginTop: "10px", borderTop: "1px dashed var(--border-subtle)", paddingTop: "10px" }}>
                  {!customQuestions ? (
                    <button
                      type="button"
                      onClick={() => enableCustomQuestions(idx)}
                      className="btn btn-ghost btn-sm"
                      style={{ height: "26px", fontSize: "11px", padding: "0 8px" }}
                    >
                      + Customise questions individually (per-question sub-parts)
                    </button>
                  ) : (
                    <>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 500 }}>
                          Per-question setup ({sec.questions!.length} question{sec.questions!.length === 1 ? "" : "s"} · {fmt(secTotal)} marks total)
                        </span>
                        <button
                          type="button"
                          onClick={() => disableCustomQuestions(idx)}
                          className="btn btn-ghost btn-sm"
                          style={{ height: "22px", fontSize: "10px", padding: "0 6px" }}
                          title="Switch back to uniform-marks shortcut"
                        >
                          ← uniform marks
                        </button>
                      </div>
                      {sec.questions!.map((q, qIdx) => {
                        const qMarks = q.sub_parts && q.sub_parts.length > 0
                          ? q.sub_parts.reduce((a, sp) => a + sp.marks, 0)
                          : q.marks;
                        return (
                          <div key={qIdx} style={{ padding: "8px", marginBottom: "6px", border: "1px solid var(--border-subtle)", borderRadius: "6px", background: "var(--surface-sunken)" }}>
                            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                              <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-secondary)", minWidth: "28px" }}>Q{qIdx + 1}</span>
                              {!(q.sub_parts && q.sub_parts.length > 0) && (
                                <>
                                  <label style={{ fontSize: "10px", color: "var(--text-tertiary)" }}>Marks</label>
                                  <input
                                    type="number" min={0.5} step={0.5} value={q.marks}
                                    onChange={(e) => updateQuestion(idx, qIdx, { marks: parseFloat(e.target.value) || 0 })}
                                    style={{ width: "64px", height: "26px", fontSize: "12px", padding: "0 6px", border: "1px solid var(--border-default)", borderRadius: "4px", background: "var(--surface-base)", color: "var(--text-primary)" }}
                                  />
                                </>
                              )}
                              {q.sub_parts && q.sub_parts.length > 0 && (
                                <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>
                                  total {fmt(qMarks)} marks (sum of sub-parts)
                                </span>
                              )}
                              <button
                                type="button"
                                onClick={() => addSubPart(idx, qIdx)}
                                className="btn btn-ghost btn-sm"
                                style={{ height: "22px", fontSize: "10px", padding: "0 6px", marginLeft: "auto" }}
                              >
                                + sub-part
                              </button>
                              <button
                                type="button"
                                onClick={() => removeQuestion(idx, qIdx)}
                                aria-label="Remove question"
                                style={{ width: "22px", height: "22px", border: "none", background: "none", cursor: "pointer", color: "var(--error-text, #ef4444)", fontSize: "14px" }}
                              >
                                ×
                              </button>
                            </div>

                            {q.sub_parts && q.sub_parts.map((sp, spIdx) => (
                              <div key={spIdx} style={{ display: "flex", gap: "6px", alignItems: "center", marginTop: "6px", paddingLeft: "32px" }}>
                                <span style={{ fontSize: "11px", color: "var(--text-tertiary)" }}>({sp.label})</span>
                                <label style={{ fontSize: "10px", color: "var(--text-tertiary)" }}>Marks</label>
                                <input
                                  type="number" min={0.5} step={0.5} value={sp.marks}
                                  onChange={(e) => updateSubPart(idx, qIdx, spIdx, { marks: parseFloat(e.target.value) || 0 })}
                                  style={{ width: "64px", height: "24px", fontSize: "11px", padding: "0 6px", border: "1px solid var(--border-default)", borderRadius: "4px", background: "var(--surface-base)", color: "var(--text-primary)" }}
                                />
                                <input
                                  value={sp.label}
                                  onChange={(e) => updateSubPart(idx, qIdx, spIdx, { label: e.target.value.slice(0, 2) })}
                                  style={{ width: "36px", height: "24px", fontSize: "11px", padding: "0 6px", border: "1px solid var(--border-default)", borderRadius: "4px", background: "var(--surface-base)", color: "var(--text-primary)", textAlign: "center" }}
                                  aria-label="Sub-part label"
                                />
                                <button
                                  type="button"
                                  onClick={() => removeSubPart(idx, qIdx, spIdx)}
                                  aria-label="Remove sub-part"
                                  style={{ width: "22px", height: "22px", border: "none", background: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: "12px", marginLeft: "auto" }}
                                >
                                  ×
                                </button>
                              </div>
                            ))}
                          </div>
                        );
                      })}
                      <button
                        type="button"
                        onClick={() => addQuestion(idx)}
                        className="btn btn-secondary btn-sm"
                        style={{ height: "26px", fontSize: "11px", padding: "0 10px" }}
                      >
                        + Add question
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}

          {/* Live total helper — B2/B5 friendly wording */}
          <div style={{
            padding: "10px 12px", borderRadius: "8px",
            background: marksOk ? "rgba(34,197,94,0.08)" : "rgba(245,158,11,0.08)",
            border: `1px solid ${marksOk ? "rgba(34,197,94,0.3)" : "rgba(245,158,11,0.3)"}`,
            fontSize: "12px",
            color: marksOk ? "var(--success-text, #16a34a)" : "var(--warning-text, #d97706)",
          }}>
            Total so far: <strong>{fmt(sectionTotal)} / {fmt(totalMarks)}</strong>
            {marksOk
              ? " ✓"
              : marksDelta > 0
                ? <> · add <strong>{fmt(marksDelta)}</strong> more marks to reach the paper total.</>
                : <> · over by <strong>{fmt(-marksDelta)}</strong>. Lower a section.</>}
          </div>
        </div>
      </div>

      {/* Generate button */}
      <div style={{ padding: "16px", borderTop: "1px solid var(--border-subtle)", flexShrink: 0 }}>
        {!canGenerate && subject.trim() === "" && (
          <div style={{ fontSize: "12px", color: "var(--error-text, #dc2626)", marginBottom: "8px" }}>Enter a subject to generate the paper.</div>
        )}
        {!bloomOk && (
          <div style={{ fontSize: "12px", color: "var(--error-text, #dc2626)", marginBottom: "8px" }}>Bloom's distribution must sum to 100.</div>
        )}
        <button onClick={handleGenerate} disabled={!canGenerate || generating}
          className="btn btn-primary" style={{ width: "100%", height: "40px", fontSize: "14px", fontWeight: 600 }}>
          {generating ? "Generating…" : "Generate Paper →"}
        </button>
      </div>
    </div>
  );
}
