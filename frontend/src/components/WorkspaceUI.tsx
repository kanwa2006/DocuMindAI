"use client";

import { useState, useEffect, useRef, useCallback, memo, useMemo } from "react";
import { toast } from "react-hot-toast";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import React from "react";
import {
  uploadDocument, askQuestionStream, listDocuments, getDocument,
  Document, QueryResponse, getChats, createChat, getChatMessages,
  createChatMessage, ChatMessage, updateChat, API_BASE,
} from "../lib/api";
import PaperConfigPanel from "./PaperConfigPanel";
import PomodoroTimer from "./PomodoroTimer";
import CandidateRankingsPanel from "./CandidateRankingsPanel";
import FinanceRatioPanel from "./FinanceRatioPanel";
import LegalRiskPanel from "./LegalRiskPanel";
import ResearchCitationModal from "./ResearchCitationModal";
import ResearchGapsPanel from "./ResearchGapsPanel";
import TableExtractionPanel from "./teacher/TableExtractionPanel";
import VoiceInputButton from "./voice/VoiceInputButton";
import { useVoiceReadback } from "../hooks/useVoiceReadback";
import { useSelectionClip } from "../hooks/useSelectionClip";
import { ClipBar } from "./clips/ClipBar";
import { ClipModal } from "./clips/ClipModal";
import ComparisonToggle from "./ComparisonToggle";
import BookmarkButton from "./BookmarkButton";
import { TrustScoreBadge, TrustReport } from "./veritas/TrustScoreBadge";
import { TrustScorePanel } from "./veritas/TrustScorePanel";
import { DocumentPreviewPanel } from "./DocumentPreviewPanel";
import ProactiveInsightsPanel from "./ProactiveInsightsPanel";

// ─── Workspace configuration (Phase 5) ───────────────────────────────────────

const WORKSPACE_CONFIG: Record<string, {
  icon: string; title: string; subtitle: string;
  badge?: { text: string; color: string };
  disclaimer?: string;
  quickActions: { icon: string; label: string; prompt: string }[];
  featureHighlights?: string[];
}> = {
  general: {
    icon: "💬", title: "Ask anything about your documents",
    subtitle: "Upload a PDF or DOCX and get instant, cited answers from its content.",
    quickActions: [
      { icon: "📋", label: "Summarize this document", prompt: "Please provide a comprehensive executive summary with key points highlighted." },
      { icon: "🔍", label: "Extract key points", prompt: "What are the 5 most important points in this document? List them clearly." },
      { icon: "⚖", label: "Compare documents", prompt: "Compare the uploaded documents and highlight the key differences and similarities." },
    ],
  },
  exam: {
    icon: "📋", title: "Generate Professional Question Papers",
    subtitle: "Upload your syllabus or textbook. AI generates structured, exam-ready papers.",
    badge: { text: "OCR Extraction Available", color: "var(--ws-exam-accent)" },
    quickActions: [
      { icon: "📝", label: "Generate Question Paper", prompt: "Generate a 100-mark CBSE-style paper from this syllabus with sections A, B, C." },
      { icon: "🗂", label: "Build Question Bank", prompt: "Create a question bank of 50 varied questions covering all topics in this document." },
      { icon: "🔑", label: "Create Answer Key", prompt: "Generate a detailed answer key with marking scheme for all sections." },
    ],
    featureHighlights: ["📊 Bloom's Taxonomy tagging", "✅ Mark validation", "🎯 Board templates"],
  },
  hr: {
    icon: "👥", title: "Intelligent Candidate Analysis Pipeline",
    subtitle: "Upload resumes + a job description. AI ranks, scores, and extracts insights.",
    badge: { text: "Batch Processing — up to 1,000 resumes", color: "var(--ws-hr-accent)" },
    quickActions: [
      { icon: "🏆", label: "Rank All Candidates", prompt: "Rank all uploaded candidates for this role with numerical scores and justifications." },
      { icon: "🎯", label: "Match JD to Resumes", prompt: "Compare all resumes against the job description and identify the top 3 matches." },
      { icon: "🗓", label: "Generate Interview Kit", prompt: "Create role-specific interview questions and a scoring rubric for the top candidates." },
    ],
    featureHighlights: ["🔍 ATS scoring", "📊 Skills extraction", "📋 Interview kits"],
  },
  study: {
    icon: "📚", title: "Your Personal AI Study Partner",
    subtitle: "Upload textbooks and notes. Study smarter, not harder.",
    badge: { text: "Supports 30+ PDFs simultaneously", color: "var(--ws-study-accent)" },
    quickActions: [
      { icon: "🗓", label: "Create My Study Plan", prompt: "Create a personalized study plan for the next 30 days based on this material." },
      { icon: "🃏", label: "Generate Flashcards", prompt: "Generate 20 flashcards for the key concepts in this document." },
      { icon: "🎯", label: "Quiz Me", prompt: "Quiz me with 10 MCQ questions on the material in this document." },
    ],
    featureHighlights: ["⏱ Spaced repetition", "📊 Progress tracking", "📝 Formula sheets"],
  },
  research: {
    icon: "🔬", title: "Systematic Literature Review & Analysis",
    subtitle: "Upload research papers. AI synthesizes, finds gaps, and formats citations.",
    badge: { text: "Citation-grounded — every claim traced to source", color: "var(--ws-research-accent)" },
    quickActions: [
      { icon: "📑", label: "Synthesize All Papers", prompt: "Provide a synthesis of all uploaded research papers, highlighting consensus and divergence." },
      { icon: "🔍", label: "Find Research Gaps", prompt: "Identify research gaps and unexplored areas across all uploaded papers." },
      { icon: "📚", label: "Export All Citations", prompt: "List all citations from these papers in APA 7th edition format." },
    ],
    featureHighlights: ["📖 PRISMA support", "🔗 DOI extraction", "⚡ Multi-paper reasoning"],
  },
  legal: {
    icon: "⚖", title: "Contract Analysis & Risk Assessment",
    subtitle: "Upload contracts. AI extracts clauses, flags risks, and maps obligations.",
    disclaimer: "⚠ For informational use only — Not legal advice. Always consult a lawyer.",
    quickActions: [
      { icon: "📋", label: "Extract All Clauses", prompt: "Extract and categorize all key clauses from this contract with page references." },
      { icon: "🚨", label: "Risk Analysis", prompt: "Identify high-risk clauses. Rate each as Critical/High/Medium/Low with justification." },
      { icon: "📊", label: "Map Obligations", prompt: "Create a complete obligation map for each party with deadlines and conditions." },
    ],
    featureHighlights: ["🔴 Risk scoring", "⏰ Deadline extraction", "📋 Clause library"],
  },
  finance: {
    icon: "📊", title: "Financial Document Intelligence",
    subtitle: "Upload P&L, balance sheets, invoices. AI extracts, analyzes, and verifies.",
    disclaimer: "⚠ Verify all figures with source documents. Not financial advice.",
    quickActions: [
      { icon: "💰", label: "Extract Key Figures", prompt: "Extract all key financial figures with exact page citations and context." },
      { icon: "📈", label: "Calculate Ratios", prompt: "Calculate liquidity, profitability, and solvency ratios using the uploaded statements." },
      { icon: "📅", label: "Year-on-Year Analysis", prompt: "Compare financial performance across all uploaded years with percentage changes." },
    ],
    featureHighlights: ["🔢 Numerical validation", "📊 Ratio computation", "🔍 OCR extraction"],
  },
};

const FOLLOW_UP_SUGGESTIONS: Record<string, string[]> = {
  general:  ["Summarize the key points", "What are the next steps?", "Explain this further"],
  exam:     ["Generate more questions", "Add harder variants", "Create marking scheme"],
  legal:    ["What are the key risks?", "Which clauses need attention?", "Compare with standard"],
  finance:  ["Calculate profitability ratios", "Compare with previous year", "Flag anomalies"],
  hr:       ["Rank all candidates", "Who is the best fit?", "Generate interview questions"],
  research: ["Find research gaps", "Summarize findings", "Export citations"],
  study:    ["Quiz me on this", "Create flashcards", "Explain simpler"],
};

const WORKSPACE_ACTIONS: Record<string, { icon: string; label: string }[]> = {
  exam:     [{ icon: "📄", label: "Generate Paper" }, { icon: "📖", label: "Question Bank" }, { icon: "🔑", label: "Answer Key" }, { icon: "🖨", label: "Export DOCX" }, { icon: "⊞", label: "Extract Tables" }],
  hr:       [{ icon: "📂", label: "Batch Upload" }, { icon: "🎯", label: "Set JD Context" }, { icon: "📊", label: "View Rankings" }, { icon: "📋", label: "Export Candidates" }],
  study:    [{ icon: "📖", label: "Study Mode" }, { icon: "🃏", label: "Flashcard Mode" }, { icon: "⏱", label: "Pomodoro Timer" }, { icon: "📊", label: "My Progress" }],
  finance:  [{ icon: "🔢", label: "Extraction Mode" }, { icon: "📊", label: "Table Mode" }, { icon: "✅", label: "Verify" }, { icon: "📈", label: "Ratios" }],
  research: [{ icon: "🔬", label: "Citation Mode" }, { icon: "📝", label: "Review Mode" }, { icon: "📚", label: "Import Papers" }, { icon: "🔍", label: "Find Gaps" }],
  legal:    [{ icon: "⚖", label: "Contract Mode" }, { icon: "🚨", label: "Risk Mode" }, { icon: "📋", label: "Clause Library" }, { icon: "📄", label: "Risk Report" }],
};

// ─── Disclaimer detection ─────────────────────────────────────────────────────

const DISCLAIMER_PREFIXES = ["⚠️ **Legal Disclaimer**", "⚠️ **Financial Disclaimer**"];

function splitDisclaimer(text: string): { main: string; disclaimer: string | null } {
  for (const prefix of DISCLAIMER_PREFIXES) {
    const marker = "\n\n---\n" + prefix;
    const idx = text.indexOf(marker);
    if (idx !== -1) {
      return { main: text.substring(0, idx), disclaimer: text.substring(idx + "\n\n---\n".length) };
    }
  }
  return { main: text, disclaimer: null };
}

// ─── Confidence badge (Task 4.6) ──────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  if (score >= 0.85) return <span className="badge badge-success">✓ High Confidence</span>;
  if (score >= 0.70) return <span className="badge badge-warning">~ Moderate Confidence</span>;
  if (score >= 0.50) return <span className="badge badge-error">⚠ Low Confidence — verify</span>;
  return <span className="badge badge-error">⚠ Please verify answer</span>;
}

// ─── ReactMarkdown: code block with copy button (Additional req) ──────────────

function CodeBlock({ node, inline, className, children, ...props }: any) {
  const [copied, setCopied] = useState(false);
  const codeText = String(children).replace(/\n$/, "");
  if (inline) {
    return <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.875em", background: "var(--surface-sunken)", padding: "2px 5px", borderRadius: "4px" }}>{children}</code>;
  }
  const handleCopy = () => {
    navigator.clipboard.writeText(codeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div style={{ position: "relative", margin: "8px 0" }}>
      <button onClick={handleCopy}
        style={{ position: "absolute", top: "8px", right: "8px", zIndex: 1, height: "28px", padding: "0 10px", fontSize: "11px", background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "6px", cursor: "pointer", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px", fontFamily: "var(--font-body)", transition: "border-color 100ms, color 100ms" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; (e.currentTarget as HTMLElement).style.color = "var(--brand)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)"; }}
      >{copied ? "✓ Copied!" : "📋 Copy code"}</button>
      <pre style={{ fontFamily: "var(--font-mono)", fontSize: "13px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "8px", padding: "16px", overflowX: "auto", margin: 0 }}>
        <code className={className} {...props}>{children}</code>
      </pre>
    </div>
  );
}

// ─── ReactMarkdown: table with Copy+CSV+DOCX export ───────────────────────────

function TableWithExport({ children, workspaceType }: { children: React.ReactNode; workspaceType?: string }) {
  const tableRef = useRef<HTMLTableElement>(null);
  const [htmlCopied, setHtmlCopied] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);
  const isTeacher = workspaceType === "exam";

  const chipStyle: React.CSSProperties = {
    height: "26px", padding: "0 10px", fontSize: "11px",
    background: "var(--surface-raised)", border: "1px solid var(--border-default)",
    borderRadius: "6px", cursor: "pointer", color: "var(--text-secondary)",
    display: "inline-flex", alignItems: "center", gap: "4px",
    fontFamily: "var(--font-body)", transition: "border-color 100ms",
  };
  const hoverIn = (e: React.MouseEvent) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; };
  const hoverOut = (e: React.MouseEvent) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; };

  const copyHTML = () => {
    if (tableRef.current) {
      navigator.clipboard.writeText(tableRef.current.outerHTML);
      setHtmlCopied(true); setTimeout(() => setHtmlCopied(false), 2000);
    }
  };

  const downloadCSV = () => {
    if (!tableRef.current) return;
    const rows = Array.from(tableRef.current.querySelectorAll("tr"));
    const csv = rows.map((r) =>
      Array.from(r.querySelectorAll("th,td"))
        .map((c) => `"${(c.textContent || "").replace(/"/g, '""')}"`)
        .join(",")
    ).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `table_${Date.now()}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadDOCX = async () => {
    if (!tableRef.current || docxLoading) return;
    setDocxLoading(true);
    try {
      const rows = Array.from(tableRef.current.querySelectorAll("tr"));
      const headers = Array.from(rows[0]?.querySelectorAll("th,td") ?? []).map((c) => c.textContent || "");
      const dataRows = rows.slice(1).map((r) =>
        Array.from(r.querySelectorAll("td")).map((c) => c.textContent || "")
      );
      const res = await fetch(`${API_BASE}/exams/export/table-docx`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Table Export", headers, rows: dataRows }),
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `table_${Date.now()}.docx`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e: any) {
      toast.error("DOCX export failed");
    } finally {
      setDocxLoading(false);
    }
  };

  return (
    <div style={{ marginBottom: "8px" }}>
      <div style={{ overflowX: "auto" }}>
        <table ref={tableRef} style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>{children}</table>
      </div>
      <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
        <button onClick={copyHTML} style={chipStyle} onMouseEnter={hoverIn} onMouseLeave={hoverOut}>
          {htmlCopied ? "✓" : "📋"} Copy as HTML
        </button>
        <button onClick={downloadCSV} style={chipStyle} onMouseEnter={hoverIn} onMouseLeave={hoverOut}>
          📊 Export CSV
        </button>
        {isTeacher && (
          <button onClick={downloadDOCX} disabled={docxLoading} style={chipStyle} onMouseEnter={hoverIn} onMouseLeave={hoverOut}>
            📄 {docxLoading ? "Exporting…" : "Export DOCX"}
          </button>
        )}
      </div>
    </div>
  );
}

function buildMarkdownComponents(workspaceType: string) {
  return {
    code: CodeBlock,
    table: ({ children }: any) => <TableWithExport workspaceType={workspaceType}>{children}</TableWithExport>,
    th: ({ children }: any) => <th style={{ padding: "8px 12px", background: "var(--surface-sunken)", borderBottom: "2px solid var(--border-default)", textAlign: "left", fontWeight: 600, fontSize: "13px" }}>{children}</th>,
    td: ({ children }: any) => <td style={{ padding: "8px 12px", borderBottom: "1px solid var(--border-subtle)", fontSize: "13px" }}>{children}</td>,
  };
}

// Kept for back-compat if anything references it directly
const MARKDOWN_COMPONENTS = buildMarkdownComponents("general");

// ─── Workspace welcome state (Task 5.1) ───────────────────────────────────────

function WorkspaceWelcome({ workspaceType, onQuickAction }: { workspaceType: string; onQuickAction: (prompt: string) => void }) {
  const cfg = WORKSPACE_CONFIG[workspaceType] || WORKSPACE_CONFIG.general;
  return (
    <div className="message-enter" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", padding: "40px 16px", textAlign: "center" }}>
      <div style={{ maxWidth: "560px", width: "100%" }}>
        <div style={{ fontSize: "64px", marginBottom: "16px", lineHeight: 1 }}>{cfg.icon}</div>
        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-2xl)", color: "var(--text-primary)", margin: "0 0 8px", fontWeight: 400 }}>{cfg.title}</h1>
        <p style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-secondary)", margin: "0 0 12px", lineHeight: "var(--leading-relaxed)" }}>{cfg.subtitle}</p>
        {cfg.badge && (
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "12px" }}>
            <span style={{ background: "var(--surface-raised)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-full)", padding: "4px 12px", fontSize: "12px", fontWeight: 500, textDecoration: "none" }}>{cfg.badge.text}</span>
          </div>
        )}
        {cfg.disclaimer && (
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
            <span style={{ background: "var(--warning-bg)", color: "var(--warning-text)", border: "1px solid var(--warning-border)", borderRadius: "var(--radius-full)", padding: "5px 14px", fontSize: "13px" }}>{cfg.disclaimer}</span>
          </div>
        )}
        <div style={{ display: "flex", gap: "10px", justifyContent: "center", flexWrap: "wrap", marginTop: "24px" }}>
          {cfg.quickActions.map((a) => (
            <button key={a.label} onClick={() => onQuickAction(a.prompt)} className="btn btn-secondary"
              style={{ borderRadius: "20px", height: "36px", padding: "0 16px", fontSize: "13px", gap: "6px" }}>
              <span>{a.icon}</span>{a.label}
            </button>
          ))}
        </div>
        {cfg.featureHighlights && (
          <div style={{ display: "flex", gap: "8px", justifyContent: "center", flexWrap: "wrap", marginTop: "20px" }}>
            {cfg.featureHighlights.map((f) => (
              <div key={f} style={{ border: "1px solid var(--border-subtle)", borderRadius: "10px", padding: "8px 12px", fontSize: "12px", color: "var(--text-secondary)", background: "var(--surface-raised)" }}>{f}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Enhanced message component ───────────────────────────────────────────────

const MemoizedMessage = memo(({
  msg, chatId, workspaceType, isLastAI, isStreaming, onRegenerate, followUps, onFollowUpClick,
  trustData, isTrustExpanded, onTrustToggle, onViewPage, onSecondOpinion, originalQuery, voiceLang,
}: {
  msg: ChatMessage; chatId: string | null; workspaceType: string;
  isLastAI: boolean; isStreaming: boolean;
  onRegenerate: () => void;
  followUps: string[]; onFollowUpClick: (p: string) => void;
  trustData?: TrustReport;
  isTrustExpanded?: boolean;
  onTrustToggle?: () => void;
  onViewPage?: (filename: string, page: number) => void;
  onSecondOpinion?: (query: string) => Promise<string>;
  originalQuery?: string;
  voiceLang?: string;
}) => {
  const [hovered, setHovered] = useState(false);
  const [copyDone, setCopyDone] = useState(false);
  const { speak, stop, isSpeaking, isSupported: readbackSupported } = useVoiceReadback();

  const mdComponents = useMemo(() => buildMarkdownComponents(workspaceType), [workspaceType]);

  let parsedRes: any = null;
  let textContent = msg.content;
  if (msg.role === "assistant") {
    try { parsedRes = JSON.parse(msg.content); textContent = parsedRes.answer || ""; } catch {}
  }

  if (msg.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div style={{ maxWidth: "75%", background: "var(--brand)", color: "#fff", borderRadius: "16px 16px 4px 16px", padding: "12px 16px", fontFamily: "var(--font-body)", fontSize: "14px", lineHeight: "var(--leading-relaxed)" }}>
          {msg.content}
        </div>
      </div>
    );
  }

  const { main: mainText, disclaimer: disclaimerText } = splitDisclaimer(textContent);
  const confidence = parsedRes?.confidence_score ?? 0;
  const evidence = parsedRes?.evidence ?? [];
  const suggestions = followUps.length > 0 ? followUps : (FOLLOW_UP_SUGGESTIONS[workspaceType] || FOLLOW_UP_SUGGESTIONS.general);

  return (
    <div
      style={{ paddingBottom: "8px" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* AI label row */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
        <div style={{ width: "16px", height: "16px", borderRadius: "4px", background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "10px", fontWeight: 700, flexShrink: 0 }}>D</div>
        <span style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)" }}>DocuMindAI · {workspaceType.charAt(0).toUpperCase() + workspaceType.slice(1)} Workspace</span>
      </div>

      {/* Content */}
      <div className="text-response" style={{ fontSize: "15px", lineHeight: "var(--leading-loose)", fontFamily: "var(--font-body)", color: "var(--text-primary)" }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents as any}>{mainText}</ReactMarkdown>
      </div>

      {/* Citations + confidence */}
      {evidence.length > 0 && (
        <div className="no-clip-zone" style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", textTransform: "uppercase" }}>Sources:</span>
          {evidence.slice(0, 4).map((chunk: any, i: number) => {
            // Phase 28: detect clip source by looking up doc in outer docs list
            // chunk.document_source comes from backend if available, else use chunk_index heuristic
            const isClip = chunk.document_source === "clip";
            const citationLabel = isClip
              ? `Clipped text, part ${(chunk.chunk_index ?? i) + 1}`
              : `p.${chunk.page_number}`;
            return (
              <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", border: "1px solid var(--border-default)", borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "11px", cursor: "default", transition: "border-color 100ms, background 100ms" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; (e.currentTarget as HTMLElement).style.background = "var(--brand-ghost)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.background = ""; }}
              >{isClip ? "📋" : "📄"} {chunk.filename} {citationLabel}</span>
            );
          })}
          <ConfidenceBadge score={confidence} />
        </div>
      )}
      {evidence.length === 0 && (
        <div style={{ marginTop: "6px" }}><ConfidenceBadge score={confidence} /></div>
      )}

      {/* Trust Score badge + expanded panel */}
      {trustData && (
        <div className="no-clip-zone" style={{ marginTop: "8px" }}>
          <TrustScoreBadge
            trust={trustData}
            expanded={isTrustExpanded ?? false}
            onToggle={() => onTrustToggle?.()}
          />
          {isTrustExpanded && onViewPage && onSecondOpinion && (
            <TrustScorePanel
              trust={trustData}
              originalQuery={originalQuery ?? ""}
              onViewPage={onViewPage}
              onSecondOpinion={onSecondOpinion}
            />
          )}
        </div>
      )}

      {/* Disclaimer banner */}
      {disclaimerText && (
        <div style={{ marginTop: "8px", padding: "8px 12px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius: "8px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--warning-text)", fontStyle: "italic" }}>
          ⚠ {disclaimerText}
        </div>
      )}

      {/* Actions row (hover) */}
      <div className="no-clip-zone" style={{ display: "flex", gap: "4px", marginTop: "8px", opacity: hovered ? 1 : 0, transition: "opacity 100ms", flexWrap: "wrap" }}>
        <button
          className="btn btn-ghost btn-sm"
          aria-label="Copy response to clipboard"
          style={{ height: "28px" }}
          onClick={() => { navigator.clipboard.writeText(textContent); setCopyDone(true); setTimeout(() => setCopyDone(false), 2000); toast.success("Copied"); }}
        >
          <span aria-hidden="true">{copyDone ? "✓" : "📋"}</span> Copy
        </button>
        {chatId && (
          <BookmarkButton
            messageId={msg.id}
            sessionId={chatId}
            content={msg.content}
            citations={evidence}
            workspace={workspaceType}
          />
        )}
        {isLastAI && !isStreaming && (
          <button className="btn btn-ghost btn-sm" aria-label="Regenerate response" style={{ height: "28px" }} onClick={onRegenerate}>
            <span aria-hidden="true">🔄</span> Regenerate
          </button>
        )}
        <button className="btn btn-ghost btn-sm" aria-label="Mark response as helpful" style={{ height: "28px" }} onClick={() => toast.success("Thanks for the feedback!")}>
          <span aria-hidden="true">👍</span> Helpful
        </button>
        <button className="btn btn-ghost btn-sm" aria-label="Mark response as not helpful" style={{ height: "28px" }} onClick={() => toast("Noted — we'll improve.", { icon: "👎" })}>
          <span aria-hidden="true">👎</span> Not Helpful
        </button>
        {readbackSupported && (
          <button
            className="btn btn-ghost btn-sm"
            aria-label={isSpeaking ? "Stop reading aloud" : "Read answer aloud"}
            style={{ height: "28px" }}
            onClick={() => isSpeaking ? stop() : speak(mainText, voiceLang || "en-IN")}
          >
            <span aria-hidden="true">{isSpeaking ? "⏹" : "🔊"}</span> {isSpeaking ? "Stop" : "Read"}
          </button>
        )}
      </div>

      {/* Follow-up suggestion chips (Task 4.10) */}
      {!isStreaming && (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "10px" }}>
          {suggestions.slice(0, 3).map((s) => (
            <button key={s} onClick={() => onFollowUpClick(s)}
              style={{ border: "1px solid var(--border-default)", borderRadius: "20px", padding: "4px 12px", height: "28px", fontFamily: "var(--font-body)", fontSize: "13px", cursor: "pointer", background: "none", color: "var(--text-secondary)", transition: "border-color 100ms, color 100ms" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; (e.currentTarget as HTMLElement).style.color = "var(--brand)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)"; }}
            >{s}</button>
          ))}
        </div>
      )}
    </div>
  );
});
MemoizedMessage.displayName = "MemoizedMessage";

// ─── Main component ───────────────────────────────────────────────────────────

// ─── Flashcard Mode overlay for Student workspace ─────────────────────────────

function FlashcardMode({
  decks, onClose, onReview,
}: {
  decks: any[];
  onClose: () => void;
  onReview: (cardId: string, quality: number) => Promise<void>;
}) {
  const allCards = decks.flatMap((d) => d.cards || []);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const card = allCards[idx];

  const handleReview = async (quality: number) => {
    if (!card || reviewing) return;
    setReviewing(true);
    await onReview(card.id, quality);
    setFlipped(false);
    setIdx((prev) => Math.min(prev + 1, allCards.length - 1));
    setReviewing(false);
  };

  if (allCards.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: "16px" }}>
        <div style={{ fontSize: "48px" }}>🃏</div>
        <div style={{ fontFamily: "var(--font-body)", color: "var(--text-secondary)", fontSize: "14px" }}>No flashcards yet. Generate some via the chat first.</div>
        <button onClick={onClose} className="btn btn-secondary">← Back to chat</button>
      </div>
    );
  }

  const correct = 0;
  const remaining = allCards.length - idx;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", padding: "24px", gap: "20px" }}>
      {/* Progress */}
      <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-secondary)" }}>
        Card {idx + 1} of {allCards.length} · {remaining} remaining today
      </div>

      {/* Flip card */}
      <div
        onClick={() => setFlipped((f) => !f)}
        style={{
          width: "min(480px, 100%)", height: "260px", cursor: "pointer",
          perspective: "1000px",
        }}
      >
        <div style={{
          width: "100%", height: "100%", position: "relative",
          transformStyle: "preserve-3d",
          transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
          transition: "transform 300ms ease",
        }}>
          {/* Front */}
          <div style={{
            position: "absolute", inset: 0, backfaceVisibility: "hidden",
            background: "var(--surface-raised)", border: "1px solid var(--border-default)",
            borderRadius: "16px", padding: "32px", display: "flex",
            alignItems: "center", justifyContent: "center", textAlign: "center",
          }}>
            <div>
              <div style={{ fontSize: "11px", color: "var(--text-tertiary)", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.07em" }}>Question</div>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "16px", color: "var(--text-primary)", lineHeight: 1.5 }}>{card?.front}</div>
              <div style={{ marginTop: "20px", fontSize: "12px", color: "var(--text-tertiary)" }}>Tap to reveal answer</div>
            </div>
          </div>
          {/* Back */}
          <div style={{
            position: "absolute", inset: 0, backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
            background: "var(--brand-ghost, var(--surface-raised))", border: "1px solid var(--brand)",
            borderRadius: "16px", padding: "32px", display: "flex",
            alignItems: "center", justifyContent: "center", textAlign: "center",
          }}>
            <div>
              <div style={{ fontSize: "11px", color: "var(--brand)", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.07em" }}>Answer</div>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "15px", color: "var(--text-primary)", lineHeight: 1.6 }}>{card?.back}</div>
              {card?.citation && (
                <div style={{ marginTop: "12px", fontSize: "11px", color: "var(--text-tertiary)", fontStyle: "italic" }}>{card.citation}</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quality rating buttons — only after flip */}
      {flipped && (
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", justifyContent: "center" }}>
          {[
            { label: "😵 Forgot", quality: 0 },
            { label: "😕 Hard", quality: 2 },
            { label: "😊 OK", quality: 4 },
            { label: "🎯 Easy", quality: 5 },
          ].map(({ label, quality }) => (
            <button
              key={quality}
              onClick={() => handleReview(quality)}
              disabled={reviewing}
              className="btn btn-secondary"
              style={{ height: "40px", fontSize: "13px", gap: "4px" }}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <button onClick={onClose} className="btn btn-ghost btn-sm" style={{ marginTop: "8px" }}>← Back to chat</button>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function WorkspaceUI({ workspaceType = "general" }: { workspaceType?: string }) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [showThinkingLabel, setShowThinkingLabel] = useState(false);
  const [thinkingStage, setThinkingStage] = useState<{ stage: string; detail: string } | null>(null);
  const [comparisonMode, setComparisonMode] = useState(false);

  // ── Workspace-specific state ──────────────────────────────────────────────
  const [showPaperConfig, setShowPaperConfig] = useState(false);
  const [generatedPaper, setGeneratedPaper] = useState<any | null>(null);
  const [showAnswerKey, setShowAnswerKey] = useState(false);
  const [showPomodoro, setShowPomodoro] = useState(false);
  const [flashcardMode, setFlashcardMode] = useState(false);
  const [flashcardDecks, setFlashcardDecks] = useState<any[]>([]);
  // Phase 11 — Table Extraction Panel (exam/teacher workspace)
  const [showTablePanel, setShowTablePanel] = useState(false);
  const [tablePanelDocId, setTablePanelDocId] = useState<string | null>(null);

  // ── Finance workspace state ───────────────────────────────────────────────
  const [showRatioPanel, setShowRatioPanel] = useState(false);

  // ── Legal workspace state ─────────────────────────────────────────────────
  const [showLegalRisk, setShowLegalRisk] = useState(false);

  // ── Research workspace state ──────────────────────────────────────────────
  const [showCitationModal, setShowCitationModal] = useState(false);
  const [showGapsPanel, setShowGapsPanel] = useState(false);

  // ── HR workspace state ────────────────────────────────────────────────────
  const [showRankings, setShowRankings] = useState(false);
  // Per-file progress: { [filename]: { progress: 0-100, status: "uploading"|"done"|"error" } }
  const [batchProgress, setBatchProgress] = useState<Record<string, { progress: number; status: string }>>({});
  const batchFileInputRef = useRef<HTMLInputElement>(null);

  // ── Disclaimer dismissal (C6) ─────────────────────────────────────────────
  const [disclaimerDismissed, setDisclaimerDismissed] = useState(true); // start true to avoid SSR flash; corrected in effect
  useEffect(() => {
    if (typeof window === "undefined") return;
    const dismissed = localStorage.getItem(`dm.disclaimer.dismissed.${workspaceType}`) === "true";
    setDisclaimerDismissed(dismissed);
  }, [workspaceType]);
  const dismissDisclaimer = useCallback(() => {
    setDisclaimerDismissed(true);
    try { localStorage.setItem(`dm.disclaimer.dismissed.${workspaceType}`, "true"); } catch {}
  }, [workspaceType]);

  // ── Phase 28: Text Clip state ─────────────────────────────────────────────
  const [clipBarState, setClipBarState] = useState<{ text: string; rect: DOMRect } | null>(null);
  const [clipModalOpen, setClipModalOpen] = useState(false);
  const [clipInitialText, setClipInitialText] = useState("");

  // ── Trust Score state (Phase 18-B) ─────────────────────────────────────────
  const [trustDataMap, setTrustDataMap] = useState<Record<string, TrustReport>>({});
  const [expandedTrustMsgId, setExpandedTrustMsgId] = useState<string | null>(null);
  const [docPreviewState, setDocPreviewState] = useState<{ doc: Document; page: number } | null>(null);
  const latestTrustRef = useRef<TrustReport | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollingIntervalsRef = useRef<NodeJS.Timeout[]>([]);
  const thinkingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Voice state
  const [voiceLang, setVoiceLang] = useState("en-IN");
  const [voiceInterim, setVoiceInterim] = useState("");
  const queryRef = useRef(query);
  queryRef.current = query;

  const mdComponents = useMemo(() => buildMarkdownComponents(workspaceType), [workspaceType]);

  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const chatId = searchParams.get("chat");

  const isStreaming = loading;

  // Phase 11 — Cmd+Shift+T → open/close Extract Tables panel (exam workspace only)
  useEffect(() => {
    if (workspaceType !== "exam") return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toUpperCase() === "T") {
        e.preventDefault();
        setTablePanelDocId(activeDoc?.id ?? null);
        setShowTablePanel((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [workspaceType, activeDoc]);

  // Scroll to bottom when new content arrives
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, response?.answer]);

  // Load chat history or create new session
  useEffect(() => {
    const initChat = async () => {
      try {
        if (chatId) {
          const msgs = await getChatMessages(chatId);
          setHistory(msgs);
        } else {
          const chats = await getChats(workspaceType);
          if (chats.length > 0) {
            router.replace(`${pathname}?chat=${chats[0].id}`);
          } else {
            const newChat = await createChat(`New ${workspaceType} chat`, workspaceType);
            router.replace(`${pathname}?chat=${newChat.id}`);
          }
        }
      } catch (err) {
        console.error("Failed to init chat", err);
      }
    };
    initChat();
    return () => {
      pollingIntervalsRef.current.forEach(clearInterval);
      abortControllerRef.current?.abort();
    };
  }, [chatId, workspaceType, pathname, router]);

  // Restore draft when switching chats
  useEffect(() => {
    if (chatId) {
      const saved = sessionStorage.getItem(`draft_${chatId}`);
      if (saved) setQuery(saved);
      else setQuery("");
    }
  }, [chatId]);

  useEffect(() => {
    localStorage.setItem("lastActiveWorkspace", pathname || "/");
  }, [pathname]);

  useEffect(() => {
    const saved = localStorage.getItem("documind_voice_lang");
    if (saved) setVoiceLang(saved);
  }, []);

  // Workspace document sync
  useEffect(() => {
    const syncWorkspace = async () => {
      try {
        const fetchedDocs = await listDocuments();
        const wsDocs = JSON.parse(localStorage.getItem(`docs_${workspaceType}`) || "[]");
        const filteredDocs = fetchedDocs.filter((d) => wsDocs.includes(d.id));
        setDocs(filteredDocs);
        setActiveDoc(filteredDocs.length > 0 ? filteredDocs[0] : null);
      } catch { toast.error("Failed to sync workspace"); }
    };
    syncWorkspace();
  }, [workspaceType]);

  const handleQueryChange = (val: string) => {
    setQuery(val);
    if (chatId) sessionStorage.setItem(`draft_${chatId}`, val);
  };

  // ── Core send function ─────────────────────────────────────────────────────
  const sendMessage = useCallback(async (queryText: string) => {
    if (!queryText.trim()) return;
    window.speechSynthesis?.cancel?.();
    // C10 — no-document mode: allow asking without an attached doc. If a doc IS
    // attached but still processing, silently bail. The Send button is already
    // disabled in this state and there's an inline hint below the input — no
    // need to stack a blocking toast on every Enter keypress.
    if (activeDoc && activeDoc.status !== "READY") {
      return;
    }

    setLoading(true);
    setShowThinkingLabel(false);
    thinkingTimerRef.current = setTimeout(() => setShowThinkingLabel(true), 1500);
    abortControllerRef.current = new AbortController();

    if (chatId) {
      await createChatMessage(chatId, "user", queryText);
      setHistory((prev) => [...prev, { id: Date.now().toString(), role: "user", content: queryText }]);

      if (history.length === 0) {
        const newTitle = queryText.length > 40 ? queryText.substring(0, 37) + "..." : queryText;
        updateChat(chatId, { title: newTitle }).then(() => {
          window.dispatchEvent(new CustomEvent("chat-title-updated", { detail: { id: chatId, title: newTitle } }));
        }).catch(console.error);
      }
    }

    if (chatId) sessionStorage.removeItem(`draft_${chatId}`);
    setQuery("");

    setResponse({
      query: queryText, answer: "", confidence_score: 0, evidence: [],
      diagnostics: { embedding_time_sec: 0, database_time_sec: 0, reranking_time_sec: 0, generation_time_sec: 0, total_time_sec: 0, candidates_retrieved: 0, evidence_accepted: 0, estimated_tokens: 0 },
    });

    const toastId = toast.loading("Initializing secure stream...");

    try {
      await askQuestionStream(
        queryText, 5,
        (msg) => toast.loading(msg, { id: toastId }),
        (metadata) => {
          setResponse((prev) => prev ? {
            ...prev,
            confidence_score: metadata.confidence_score,
            evidence: metadata.evidence,
            grounded: metadata.grounded,
            mode: metadata.mode,
          } : null);
        },
        (token) => {
          if (thinkingTimerRef.current) { clearTimeout(thinkingTimerRef.current); thinkingTimerRef.current = null; }
          setShowThinkingLabel(false);
          setThinkingStage(null);
          setResponse((prev) => prev ? { ...prev, answer: prev.answer + token } : null);
        },
        (err) => {
          if (err !== "Request cancelled.") toast.error(err, { id: toastId });
          setLoading(false);
          setThinkingStage(null);
          abortControllerRef.current = null;
          if (thinkingTimerRef.current) clearTimeout(thinkingTimerRef.current);
        },
        async () => {
          if (!abortControllerRef.current) return;
          toast.success("Response complete.", { id: toastId });
          setLoading(false);
          setThinkingStage(null);
          abortControllerRef.current = null;
          if (thinkingTimerRef.current) clearTimeout(thinkingTimerRef.current);
          setShowThinkingLabel(false);
          setResponse((currentRes) => {
            if (currentRes && chatId) {
              window.dispatchEvent(new CustomEvent("autosave:saving"));
              createChatMessage(chatId, "assistant", JSON.stringify(currentRes)).then((savedMsg) => {
                setHistory((prev) => [...prev, savedMsg]);
                window.dispatchEvent(new CustomEvent("autosave:saved"));
                if (latestTrustRef.current) {
                  setTrustDataMap((prev) => ({ ...prev, [savedMsg.id]: latestTrustRef.current! }));
                  latestTrustRef.current = null;
                }
              }).catch(() => window.dispatchEvent(new CustomEvent("autosave:error")));
            }
            return currentRes;
          });
          setTimeout(() => { setResponse(null); }, 120);
        },
        abortControllerRef.current.signal,
        chatId || undefined,
        workspaceType,
        undefined, // onTrialStatus
        (stage) => setThinkingStage(stage), // onThinkingStage
        comparisonMode,
        (trust) => { latestTrustRef.current = trust; }, // onTrustReport
      );
    } catch (err: any) {
      toast.error(err.message || "Query failed.", { id: toastId });
      setLoading(false);
    }
  }, [activeDoc, chatId, history.length, workspaceType]);

  const handleAsk = (e: React.FormEvent) => { e.preventDefault(); sendMessage(query); };

  // Task 4.5 — Regenerate last response
  const regenerateLastResponse = useCallback(async () => {
    const lastUserIdx = [...history].reverse().findIndex((m) => m.role === "user");
    if (lastUserIdx === -1) return;
    const lastUserMsg = history[history.length - 1 - lastUserIdx];
    const lastAiIdx = history.map((m) => m.role).lastIndexOf("assistant");
    if (lastAiIdx !== -1) setHistory((prev) => prev.filter((_, i) => i !== lastAiIdx));
    await sendMessage(lastUserMsg.content);
  }, [history, sendMessage]);

  const handleStopGenerating = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setLoading(false);
    if (thinkingTimerRef.current) clearTimeout(thinkingTimerRef.current);
    setShowThinkingLabel(false);
    toast("Generation stopped.", { icon: "🛑" });
    setResponse((currentRes) => {
      if (currentRes && chatId) {
        createChatMessage(chatId, "assistant", JSON.stringify(currentRes)).then((savedMsg) => {
          setHistory((prev) => [...prev, savedMsg]);
        });
      }
      return null;
    });
  };

  const handleVoiceLangChange = useCallback((lang: string) => {
    setVoiceLang(lang);
    localStorage.setItem("documind_voice_lang", lang);
  }, []);

  const handleInterimText = useCallback((text: string) => {
    setVoiceInterim(text);
  }, []);

  const handleVoiceTranscript = useCallback((text: string) => {
    setVoiceInterim("");
    setQuery(text);
    const lang = localStorage.getItem("documind_voice_lang") || "en-IN";
    window.dispatchEvent(new CustomEvent("voice_query_used", { detail: { workspace: workspaceType, lang } }));
    setTimeout(() => { sendMessage(text); }, 300);
  }, [sendMessage, workspaceType]);

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;
    setLoading(true);
    const toastId = toast.loading("Uploading document securely...");
    try {
      const uploadedDoc = await uploadDocument(selectedFile);
      const wsDocs = JSON.parse(localStorage.getItem(`docs_${workspaceType}`) || "[]");
      wsDocs.push(uploadedDoc.id);
      localStorage.setItem(`docs_${workspaceType}`, JSON.stringify(wsDocs));
      setDocs((prev) => [uploadedDoc, ...prev]);
      setActiveDoc(uploadedDoc);

      if (uploadedDoc.status === "DEDUPLICATED") {
        toast.success(`📄 This document matches '${uploadedDoc.duplicate_of}'. Using cached embeddings — instant processing!`, { id: toastId });
        setLoading(false);
      } else {
        toast.success("Document uploaded. Starting pipeline...", { id: toastId });
        const interval = setInterval(async () => {
          try {
            const statusDoc = await getDocument(uploadedDoc.id);
            setActiveDoc(statusDoc);
            setDocs((prev) => prev.map((d) => d.id === statusDoc.id ? statusDoc : d));
            if (statusDoc.status === "READY") { toast.success("Extraction complete!", { id: toastId }); clearInterval(interval); setLoading(false); }
            else if (statusDoc.status === "FAILED") { toast.error("Extraction failed.", { id: toastId }); clearInterval(interval); setLoading(false); }
          } catch { /* transient */ }
        }, 2000);
        pollingIntervalsRef.current.push(interval);
      }
    } catch (err: any) {
      toast.error(err.message || "Upload failed.", { id: toastId });
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Task 4.11 — auto-expand textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    handleQueryChange(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + "px";
  };

  // Phase 28 — selection clip hook
  useSelectionClip({
    onSelection: (text, rect) => {
      setClipBarState({ text, rect });
    },
  });

  const handleClipBarAdd = () => {
    if (!clipBarState) return;
    if (clipBarState.text.length < 50) {
      toast("Select more text (minimum 50 characters)", { icon: "⚠️" });
      setClipBarState(null);
      return;
    }
    setClipInitialText(clipBarState.text);
    setClipBarState(null);
    setClipModalOpen(true);
  };

  const handleClipped = (doc: Document) => {
    const wsDocs = JSON.parse(localStorage.getItem(`docs_${workspaceType}`) || "[]");
    wsDocs.push(doc.id);
    localStorage.setItem(`docs_${workspaceType}`, JSON.stringify(wsDocs));
    setDocs((prev) => [doc, ...prev]);
    if (!activeDoc) setActiveDoc(doc);
    toast.success("📋 Text clipped — processing…");
    // Analytics: clip_text_used
    window.dispatchEvent(new CustomEvent("clip_text_used", { detail: { workspace: workspaceType } }));
    // Poll until READY (reuses existing pattern)
    if (doc.status === "PROCESSING") {
      const interval = setInterval(async () => {
        try {
          const updated = await getDocument(doc.id);
          setDocs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
          if (updated.status === "READY") {
            toast.success("📋 Clip ready — you can now ask questions!", { duration: 4000 });
            clearInterval(interval);
          } else if (updated.status === "FAILED") {
            toast.error("Clip processing failed.");
            clearInterval(interval);
          }
        } catch { /* transient */ }
      }, 2000);
      pollingIntervalsRef.current.push(interval);
    }
  };

  const isLegalOrFinance = workspaceType === "legal" || workspaceType === "finance";

  // Derive last AI message index for regenerate button
  const lastAiMsgIdx = history.map((m) => m.role).lastIndexOf("assistant");

  // ── Handle workspace action button clicks ─────────────────────────────────
  const handleWorkspaceAction = useCallback(async (label: string) => {
    if (workspaceType === "finance") {
      if (label === "Ratios" || label === "Verify") {
        setShowRatioPanel((v) => !v);
        return;
      }
    }
    if (workspaceType === "legal") {
      if (label === "Risk Report" || label === "Risk Mode") {
        setShowLegalRisk((v) => !v);
        return;
      }
    }
    if (workspaceType === "exam") {
      if (label === "Generate Paper") { setShowPaperConfig(true); return; }
      if (label === "Answer Key") { setShowAnswerKey((v) => !v); return; }
      if (label === "Extract Tables") {
        setTablePanelDocId(activeDoc?.id ?? null);
        setShowTablePanel((v) => !v);
        return;
      }
    }
    if (workspaceType === "hr") {
      if (label === "View Rankings") { setShowRankings(true); return; }
      if (label === "Batch Upload") { batchFileInputRef.current?.click(); return; }
    }
    if (workspaceType === "research") {
      if (label === "Citation Mode" || label === "Export Citations") {
        setShowCitationModal((v) => !v);
        return;
      }
      if (label === "Find Gaps") {
        setShowGapsPanel((v) => !v);
        return;
      }
    }
    if (workspaceType === "study") {
      if (label === "Pomodoro Timer") { setShowPomodoro((v) => !v); return; }
      if (label === "Flashcard Mode") {
        if (!flashcardMode) {
          // Load decks from API
          try {
            const res = await fetch(`${API_BASE}/study/decks`, { credentials: "include" });
            if (res.ok) {
              const deckList = await res.json();
              // Load cards per deck
              const decksWithCards = await Promise.all(
                deckList.map(async (d: any) => {
                  const cr = await fetch(`${API_BASE}/study/decks/${d.id}/flashcards`, { credentials: "include" });
                  const cards = cr.ok ? await cr.json() : [];
                  return { ...d, cards };
                })
              );
              setFlashcardDecks(decksWithCards);
            }
          } catch { toast.error("Failed to load flashcards"); }
        }
        setFlashcardMode((v) => !v);
        return;
      }
    }
  }, [workspaceType, flashcardMode]);

  const handleFlashcardReview = useCallback(async (cardId: string, quality: number) => {
    try {
      await fetch(`${API_BASE}/study/flashcards/${cardId}/review`, {
        method: "PATCH", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quality }),
      });
    } catch { /* non-fatal */ }
  }, []);

  const handleSecondOpinion = useCallback(async (query: string): Promise<string> => {
    try {
      const res = await fetch(`${API_BASE}/query/ask`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          top_k: 5,
          similarity_threshold: 0.35,
          second_opinion: true,
          workspace_type: workspaceType,
        }),
      });
      if (!res.ok) return "Alternative retrieval unavailable.";
      const data = await res.json();
      return data?.answer || "No alternative answer found.";
    } catch {
      return "Alternative retrieval unavailable.";
    }
  }, [workspaceType]);

  const handleViewPage = useCallback((filename: string, page: number) => {
    const doc = docs.find((d) => d.filename === filename);
    if (doc) setDocPreviewState({ doc, page });
  }, [docs]);

  // ── HR: Batch upload with per-file progress ───────────────────────────────
  const handleBatchFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    const initial: Record<string, { progress: number; status: string }> = {};
    files.forEach((f) => { initial[f.name] = { progress: 0, status: "uploading" }; });
    setBatchProgress(initial);

    await Promise.all(
      files.map(async (file) => {
        try {
          // Simulate progress during upload
          setBatchProgress((prev) => ({ ...prev, [file.name]: { progress: 30, status: "uploading" } }));
          const uploadedDoc = await uploadDocument(file);
          setBatchProgress((prev) => ({ ...prev, [file.name]: { progress: 60, status: "uploading" } }));

          const wsDocs = JSON.parse(localStorage.getItem(`docs_${workspaceType}`) || "[]");
          wsDocs.push(uploadedDoc.id);
          localStorage.setItem(`docs_${workspaceType}`, JSON.stringify(wsDocs));
          setDocs((prev) => [uploadedDoc, ...prev]);
          setBatchProgress((prev) => ({ ...prev, [file.name]: { progress: 100, status: "done" } }));
        } catch {
          setBatchProgress((prev) => ({ ...prev, [file.name]: { progress: 0, status: "error" } }));
        }
      })
    );

    if (batchFileInputRef.current) batchFileInputRef.current.value = "";
    setTimeout(() => setBatchProgress({}), 3000);
  }, [workspaceType]);

  const handlePaperGenerated = useCallback((data: any) => {
    setGeneratedPaper(data);
    // Display paper as an AI message in chat
    const paperText = formatPaperAsMarkdown(data);
    setHistory((prev) => [...prev, {
      id: Date.now().toString(), role: "assistant",
      content: JSON.stringify({ answer: paperText, confidence_score: 1, evidence: [] }),
    }]);
  }, []);

  function formatPaperAsMarkdown(data: any): string {
    const meta = data.metadata || {};
    let md = `## ${meta.subject || "Exam"} Paper — ${meta.board || ""}\n`;
    md += `**Total Marks:** ${meta.total_marks}  |  **Duration:** ${meta.duration_minutes} min  |  `;
    md += `**Generated:** ${new Date(data.generated_at).toLocaleString()}\n\n`;

    const sections = data.paper?.sections || [];
    for (const sec of sections) {
      md += `### SECTION ${sec.label}`;
      if (sec.question_type) md += ` — ${sec.question_type.toUpperCase()}`;
      md += "\n\n";
      for (const q of sec.questions || []) {
        md += `**${q.num}.** ${q.text}  **[${q.marks}]**\n`;
        if (q.options?.length) {
          q.options.forEach((opt: string, i: number) => {
            md += `   ${String.fromCharCode(65 + i)}. ${opt}\n`;
          });
        }
        md += "\n";
      }
    }
    return md;
  }

  return (
    <div className="h-full flex flex-col px-4 md:px-8 py-6 pb-0 w-full max-w-6xl mx-auto" style={{ position: "relative" }}>
      {/* Toaster is mounted globally in app/layout.tsx. Rendering a second
          one here doubled every toast (e.g. 6 stacked 'Failed to fetch'
          banners from a single failure). */}

      {/* ── Phase 28: Selection Clip Bar ── */}
      {clipBarState && (
        <ClipBar
          rect={clipBarState.rect}
          onAddToSession={handleClipBarAdd}
          onDismiss={() => setClipBarState(null)}
        />
      )}

      {/* ── Phase 28: Clip Modal ── */}
      {clipModalOpen && (
        <ClipModal
          initialText={clipInitialText}
          onClose={() => { setClipModalOpen(false); setClipInitialText(""); }}
          onClipped={handleClipped}
        />
      )}

      {/* ── Document Preview Panel (Trust Score contradiction "View Page") ── */}
      {docPreviewState && (
        <DocumentPreviewPanel
          doc={docPreviewState.doc}
          initialPage={docPreviewState.page}
          onClose={() => setDocPreviewState(null)}
        />
      )}

      {/* ── Paper Config Panel (Teacher workspace) ── */}
      {showPaperConfig && (
        <PaperConfigPanel
          onClose={() => setShowPaperConfig(false)}
          onGenerated={handlePaperGenerated}
        />
      )}

      {/* ── Phase 11: Table Extraction Panel (Teacher/Exam workspace) ── */}
      {workspaceType === "exam" && showTablePanel && (
        <TableExtractionPanel
          documentId={tablePanelDocId}
          documentName={activeDoc?.filename}
          onClose={() => setShowTablePanel(false)}
        />
      )}

      {/* ── Finance Ratio Panel ── */}
      {workspaceType === "finance" && showRatioPanel && (
        <FinanceRatioPanel
          documentIds={docs.filter((d) => d.status === "READY").map((d) => d.id)}
          onClose={() => setShowRatioPanel(false)}
        />
      )}

      {/* ── Legal Risk Panel ── */}
      {workspaceType === "legal" && showLegalRisk && (
        <LegalRiskPanel
          contractId={null}
          documentId={activeDoc?.id ?? null}
          activeDocumentId={activeDoc?.id ?? null}
          onClose={() => setShowLegalRisk(false)}
          onFetchContracts={async () => {
            try {
              const res = await fetch(`${API_BASE}/legal/contracts`, { credentials: "include" });
              if (res.ok) return await res.json();
            } catch { /* non-fatal */ }
            return [];
          }}
        />
      )}

      {/* ── Research Citation Modal ── */}
      {workspaceType === "research" && showCitationModal && (
        <ResearchCitationModal
          documentIds={docs.filter((d) => d.status === "READY").map((d) => d.id)}
          onClose={() => setShowCitationModal(false)}
        />
      )}

      {/* ── Research Gaps Panel ── */}
      {workspaceType === "research" && showGapsPanel && (
        <ResearchGapsPanel
          documentIds={docs.filter((d) => d.status === "READY").map((d) => d.id)}
          onClose={() => setShowGapsPanel(false)}
        />
      )}

      {/* ── Candidate Rankings Panel (HR workspace) ── */}
      {workspaceType === "hr" && showRankings && (
        <CandidateRankingsPanel onClose={() => setShowRankings(false)} />
      )}

      {/* ── Batch file input (HR workspace, multiple files) ── */}
      {workspaceType === "hr" && (
        <input
          type="file"
          multiple
          accept=".pdf,.docx"
          ref={batchFileInputRef}
          className="hidden"
          onChange={handleBatchFileChange}
        />
      )}

      {/* ── Amber disclaimer banner — TOP of chat area, sticky, dismissable. Dismissal persisted per workspace via localStorage (`dm.disclaimer.dismissed.{slug}`). ── */}
      {(workspaceType === "legal" || workspaceType === "finance") && !disclaimerDismissed && (
        <div style={{
          background: "var(--warning-bg, #fffbeb)",
          borderBottom: "1px solid var(--warning-border, #fbbf24)",
          padding: "9px 40px 9px 16px",
          fontFamily: "var(--font-body)", fontSize: "12px",
          color: "var(--warning-text, #92400e)",
          flexShrink: 0,
          lineHeight: "var(--leading-relaxed)",
          position: "relative",
        }}>
          {workspaceType === "legal"
            ? "⚠ This analysis is AI-generated for informational purposes only. It does not constitute legal advice. Always consult a qualified legal professional."
            : "⚠ All figures are AI-extracted. Verify all numbers against original source documents before any financial, tax, or legal use."}
          <button
            onClick={dismissDisclaimer}
            aria-label="Dismiss disclaimer"
            title="Dismiss"
            style={{
              position: "absolute",
              top: "50%",
              right: "8px",
              transform: "translateY(-50%)",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--warning-text, #92400e)",
              fontSize: "16px",
              lineHeight: 1,
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              opacity: 0.7,
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = "1"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = "0.7"; }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Flashcard Mode overlay (Student workspace) ── */}
      {flashcardMode ? (
        <div className="flex-1 overflow-hidden" style={{ display: "flex", flexDirection: "column" }}>
          <FlashcardMode
            decks={flashcardDecks}
            onClose={() => setFlashcardMode(false)}
            onReview={handleFlashcardReview}
          />
        </div>
      ) : null}

      {/* ── Phase 21: Proactive Insights Panel (above chat messages) ── */}
      {!flashcardMode && (
        <ProactiveInsightsPanel
          sessionId={chatId}
          hasDocuments={docs.length > 0}
          onAskAbout={(question) => {
            setQuery(question);
            if (textareaRef.current) {
              textareaRef.current.style.height = "auto";
              textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px";
              textareaRef.current.focus();
            }
          }}
        />
      )}

      {/* ── Chat area ── */}
      <div className="flex-1 overflow-y-auto mb-4 pr-2" style={{ scrollBehavior: "smooth", display: flashcardMode ? "none" : undefined }}>

        {/* Welcome state (Task 5.1) */}
        {!response && !loading && history.length === 0 && (
          <WorkspaceWelcome workspaceType={workspaceType} onQuickAction={sendMessage} />
        )}

        {/* No documents hint — softened in C10. Asking without a doc is allowed; this is a nudge, not a gate. */}
        {!response && !loading && history.length === 0 && docs.length === 0 && activeDoc === null && (
          <div style={{ position: "absolute", bottom: "180px", left: "50%", transform: "translateX(-50%)", textAlign: "center", pointerEvents: "none", opacity: 0.55 }}>
            <div style={{ fontSize: "40px", marginBottom: "6px" }}>📎</div>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-secondary)" }}>Attach a document for grounded answers — or just ask.</div>
          </div>
        )}

        <div
          role="log"
          aria-label="Chat messages"
          aria-live="polite"
          style={{ display: "flex", flexDirection: "column", gap: "16px", paddingBottom: "40px" }}
        >
          {/* History messages */}
          {history.map((msg, idx) => (
            <MemoizedMessage
              key={msg.id || idx}
              msg={msg}
              chatId={chatId}
              workspaceType={workspaceType}
              isLastAI={idx === lastAiMsgIdx && msg.role === "assistant"}
              isStreaming={isStreaming}
              onRegenerate={regenerateLastResponse}
              followUps={[]}
              onFollowUpClick={sendMessage}
              trustData={msg.role === "assistant" ? trustDataMap[msg.id] : undefined}
              isTrustExpanded={expandedTrustMsgId === msg.id}
              onTrustToggle={() => setExpandedTrustMsgId((prev) => prev === msg.id ? null : msg.id)}
              onViewPage={handleViewPage}
              onSecondOpinion={handleSecondOpinion}
              originalQuery={idx > 0 && history[idx - 1]?.role === "user" ? history[idx - 1].content : ""}
              voiceLang={voiceLang}
            />
          ))}

          {/* Active streaming response */}
          {response && (
            <>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <div style={{ maxWidth: "75%", background: "var(--brand)", color: "#fff", borderRadius: "16px 16px 4px 16px", padding: "12px 16px", fontFamily: "var(--font-body)", fontSize: "14px", lineHeight: "var(--leading-relaxed)" }}>
                  {response.query}
                </div>
              </div>

              <div aria-live="polite" aria-atomic="false" style={{ paddingBottom: "8px" }}>
                {/* AI label */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                  <div style={{ width: "16px", height: "16px", borderRadius: "4px", background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "10px", fontWeight: 700 }}>D</div>
                  <span style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", animation: loading ? "pulse 1.5s ease-in-out infinite" : "none" }}>DocuMindAI</span>
                  {response.mode === "general" && (
                    <span title="Answered without documents — general knowledge only" style={{ background: "var(--surface-sunken)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-full)", padding: "1px 8px", fontSize: "10px", fontWeight: 500, letterSpacing: "0.02em" }}>
                      Ungrounded
                    </span>
                  )}
                </div>

                {/* C10 — no-document mode banner */}
                {response.mode === "general" && (
                  <div style={{ marginBottom: "8px", padding: "8px 12px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "8px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)", lineHeight: "var(--leading-snug)" }}>
                    Answering without documents. Upload one for grounded, cited responses.
                  </div>
                )}

                {/* Thinking label — Phase 14.10 */}
                {(showThinkingLabel || thinkingStage) && !response.answer && (
                  <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", fontStyle: "italic", marginBottom: "8px", transition: "opacity 200ms" }}>
                    {thinkingStage ? (
                      <span>
                        {thinkingStage.stage === "searching" && "🔍 "}
                        {thinkingStage.stage === "reranking" && "📊 "}
                        {thinkingStage.stage === "generating" && "✍ "}
                        {thinkingStage.detail}
                      </span>
                    ) : "DocuMindAI is thinking..."}
                  </div>
                )}

                {/* Streaming content */}
                <div className="text-response" style={{ fontSize: "15px", lineHeight: "var(--leading-loose)", fontFamily: "var(--font-body)", color: "var(--text-primary)" }}>
                  {(() => {
                    const { main } = splitDisclaimer(response.answer || "");
                    return (
                      <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents as any}>{main || "Thinking..."}</ReactMarkdown>
                        {loading && (
                          <span className="streaming-cursor" style={{ display: "inline-block", width: "2px", height: "1em", background: "var(--brand)", marginLeft: "2px", verticalAlign: "text-bottom", animation: "blink 1s step-end infinite" }}>▍</span>
                        )}
                      </>
                    );
                  })()}
                </div>

                {/* Evidence chips while streaming */}
                {response.evidence.length > 0 && (
                  <div className="no-clip-zone" style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", textTransform: "uppercase" }}>Sources:</span>
                    {response.evidence.slice(0, 4).map((chunk: any, i) => {
                      const isClip = chunk.document_source === "clip";
                      const citationLabel = isClip
                        ? `Clipped text, part ${(chunk.chunk_index ?? i) + 1}`
                        : `p.${chunk.page_number}`;
                      return (
                        <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", border: "1px solid var(--border-default)", borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
                          {isClip ? "📋" : "📄"} {chunk.filename} {citationLabel}
                        </span>
                      );
                    })}
                    {response.confidence_score > 0 && <ConfidenceBadge score={response.confidence_score} />}
                  </div>
                )}

                {/* Stop button */}
                {loading && (
                  <button onClick={handleStopGenerating} className="btn btn-secondary btn-sm" style={{ marginTop: "8px", height: "28px" }}>
                    ⏹ Stop generating
                  </button>
                )}
              </div>
            </>
          )}

          <div ref={chatEndRef} />
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div style={{ background: "var(--surface-base)", paddingTop: "8px", paddingBottom: "max(16px, env(safe-area-inset-bottom))", backdropFilter: "blur(8px)", borderTop: "1px solid var(--border-subtle)", position: "sticky", bottom: 0, zIndex: 10 }}>

        {/* Hidden file input — triggered by the paperclip in the input bar */}
        <input id="upload-trigger" type="file" className="hidden" accept=".pdf,.docx" ref={fileInputRef} onChange={handleFileChange} />

        {/* Comparison toggle row (shown only when 2+ docs are READY) */}
        {docs.filter((d) => d.status === "READY").length >= 2 && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "6px", padding: "0 2px" }}>
            <ComparisonToggle
              enabled={comparisonMode}
              documentCount={docs.filter((d) => d.status === "READY").length}
              onToggle={setComparisonMode}
            />
          </div>
        )}

        {/* Input container — refactored (C9): paperclip + clipboard live in the input bar; attached docs render as removable chips. */}
        <form onSubmit={handleAsk}>
          <div style={{ background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "16px", boxShadow: "var(--shadow-sm)", padding: "12px 16px", transition: "border-color 100ms, box-shadow 100ms" }}
            onFocusCapture={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-strong)"; (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-md)"; }}
            onBlurCapture={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-sm)"; }}
          >
            {/* Attached document chips — above the textarea, scrollable horizontally if many */}
            {docs.length > 0 && (
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "8px" }}>
                {docs.map((d) => {
                  const isActive = activeDoc?.id === d.id;
                  const statusColor =
                    d.status === "READY" ? "var(--success-text)" :
                    d.status === "FAILED" ? "var(--error-text)" :
                    "var(--brand)";
                  const isLoading = d.status !== "READY" && d.status !== "FAILED" && d.status !== "DEDUPLICATED";
                  return (
                    <div
                      key={d.id}
                      role="button"
                      tabIndex={0}
                      title={d.filename + (d.status !== "READY" ? ` · ${d.status}` : "")}
                      onClick={() => setActiveDoc(d)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setActiveDoc(d); } }}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        height: "28px",
                        padding: "0 6px 0 10px",
                        background: isActive ? "var(--brand-ghost)" : "var(--surface-sunken)",
                        border: `1px solid ${isActive ? "var(--brand)" : "var(--border-subtle)"}`,
                        borderRadius: "var(--radius-full)",
                        cursor: "pointer",
                        fontFamily: "var(--font-body)",
                        fontSize: "12px",
                        color: "var(--text-primary)",
                        maxWidth: "240px",
                        transition: "border-color 100ms, background 100ms",
                      }}
                    >
                      {d.source === "clip" && <span aria-hidden="true" style={{ fontSize: "11px" }}>📋</span>}
                      {d.source === "scan" && <span aria-hidden="true" style={{ fontSize: "11px" }}>📷</span>}
                      <span
                        style={{
                          display: "inline-block",
                          width: "7px",
                          height: "7px",
                          borderRadius: "50%",
                          background: statusColor,
                          animation: isLoading ? "pulse 1.5s ease-in-out infinite" : "none",
                          flexShrink: 0,
                        }}
                        aria-hidden="true"
                      />
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "160px" }}>
                        {d.filename}
                      </span>
                      {/* Phase 11: Extract Tables quick-action on exam workspace */}
                      {workspaceType === "exam" && d.status === "READY" && (
                        <button
                          type="button"
                          title="Extract tables"
                          aria-label={`Extract tables from ${d.filename}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveDoc(d);
                            setTablePanelDocId(d.id);
                            setShowTablePanel(true);
                          }}
                          style={{
                            background: "transparent",
                            border: "none",
                            cursor: "pointer",
                            color: "var(--text-tertiary)",
                            fontSize: "11px",
                            padding: "2px 4px",
                            borderRadius: "var(--radius-sm)",
                            lineHeight: 1,
                          }}
                        >
                          ⊞
                        </button>
                      )}
                      <button
                        type="button"
                        aria-label={`Remove ${d.filename}`}
                        title="Remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDocs((prev) => prev.filter((x) => x.id !== d.id));
                          if (activeDoc?.id === d.id) setActiveDoc(null);
                        }}
                        style={{
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          color: "var(--text-tertiary)",
                          fontSize: "14px",
                          lineHeight: 1,
                          padding: "2px 4px",
                          borderRadius: "var(--radius-sm)",
                        }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--text-primary)"; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--text-tertiary)"; }}
                      >
                        ×
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            <textarea
              id="chat-textarea"
              ref={textareaRef}
              value={voiceInterim || query}
              rows={1}
              aria-label="Message input"
              onChange={(e) => {
                if (voiceInterim) setVoiceInterim("");
                handleTextareaChange(e);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  sendMessage(voiceInterim || query);
                }
              }}
              disabled={loading}
              placeholder={
                loading
                  ? "Thinking…"
                  : activeDoc && activeDoc.status !== "READY"
                  ? "Type your question — we'll send it once the document is ready."
                  : docs.length === 0
                  ? "Ask anything, or attach a document for grounded answers... (Shift+Enter for new line)"
                  : "Ask anything about your documents... (Shift+Enter for new line)"
              }
              className="chat-input"
              style={{ width: "100%", background: "transparent", border: "none", outline: "none", resize: "none", minHeight: "44px", maxHeight: "200px", fontFamily: "var(--font-body)", fontSize: "14px", lineHeight: "var(--leading-relaxed)", color: voiceInterim ? "var(--text-tertiary)" : "var(--text-primary)", fontStyle: voiceInterim ? "italic" : "normal", display: "block", overflow: "auto" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px" }}>
              <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
                <button type="button" onClick={handleUploadClick} className="btn-icon btn-ghost" aria-label="Attach file" style={{ width: "32px", height: "32px" }} title="Attach file (PDF, DOCX)">
                  <span aria-hidden="true">📎</span>
                </button>
                <button type="button" onClick={() => { setClipInitialText(""); setClipModalOpen(true); }} className="btn-icon btn-ghost" aria-label="Paste text as document" style={{ width: "32px", height: "32px" }} title="Paste text as document">
                  <span aria-hidden="true">📋</span>
                </button>
                <VoiceInputButton
                  voiceLang={voiceLang}
                  onLangChange={handleVoiceLangChange}
                  onTranscript={handleVoiceTranscript}
                  onInterimText={handleInterimText}
                  disabled={loading}
                />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {activeDoc != null && activeDoc.status !== "READY" && !loading && (
                  <span
                    aria-live="polite"
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "12px",
                      color: "var(--text-tertiary)",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <span
                      aria-hidden="true"
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        background: "var(--warning, #f59e0b)",
                        animation: "pulse 1.4s ease-in-out infinite",
                        display: "inline-block",
                      }}
                    />
                    Document processing…
                  </span>
                )}
                {query.length > 3200 && (
                  <span style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)" }}>{query.length} / 4000</span>
                )}
                {isStreaming ? (
                  <button type="button" onClick={handleStopGenerating} className="btn btn-secondary btn-sm" aria-label="Stop generating" style={{ height: "36px" }}>
                    <span aria-hidden="true">⏹</span> Stop
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!query.trim() || loading || (activeDoc != null && activeDoc.status !== "READY")}
                    className="btn btn-primary"
                    aria-label="Send message"
                    title={activeDoc != null && activeDoc.status !== "READY" ? "Waiting for document to finish processing…" : undefined}
                    style={{ height: "36px", minWidth: "64px" }}
                  >Send</button>
                )}
              </div>
            </div>
          </div>
        </form>

        {/* ── HR Batch upload per-file progress ── */}
        {workspaceType === "hr" && Object.keys(batchProgress).length > 0 && (
          <div style={{ marginTop: "8px", display: "flex", flexDirection: "column", gap: "4px" }}>
            {Object.entries(batchProgress).map(([filename, state]) => (
              <div key={filename} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-secondary)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={filename}>
                  {state.status === "done" ? "✓" : state.status === "error" ? "✗" : "⟳"} {filename}
                </span>
                <div style={{ width: "80px", height: "4px", background: "var(--border-subtle)", borderRadius: "2px", flexShrink: 0 }}>
                  <div style={{
                    width: `${state.progress}%`, height: "100%", borderRadius: "2px", transition: "width 300ms",
                    background: state.status === "error" ? "var(--error-text, #dc2626)" : state.status === "done" ? "var(--success-text, #16a34a)" : "var(--brand)",
                  }} />
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", color: "var(--text-tertiary)", width: "32px", textAlign: "right" }}>
                  {state.status === "done" ? "Done" : state.status === "error" ? "Err" : `${state.progress}%`}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Workspace-specific action buttons */}
        {WORKSPACE_ACTIONS[workspaceType] && (
          <div className="no-clip-zone" style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px", alignItems: "center" }}>
            {WORKSPACE_ACTIONS[workspaceType].map((action) => {
              const isActive =
                (action.label === "Generate Paper" && showPaperConfig) ||
                (action.label === "Answer Key" && showAnswerKey) ||
                (action.label === "Extract Tables" && showTablePanel) ||
                (action.label === "Flashcard Mode" && flashcardMode) ||
                (action.label === "Pomodoro Timer" && showPomodoro) ||
                (action.label === "View Rankings" && showRankings) ||
                ((action.label === "Ratios" || action.label === "Verify") && showRatioPanel) ||
                ((action.label === "Risk Report" || action.label === "Risk Mode") && showLegalRisk) ||
                ((action.label === "Citation Mode" || action.label === "Export Citations") && showCitationModal) ||
                (action.label === "Find Gaps" && showGapsPanel);
              return (
                <button
                  key={action.label}
                  onClick={() => handleWorkspaceAction(action.label)}
                  className="btn btn-secondary btn-sm"
                  style={{
                    height: "32px", fontSize: "12px", gap: "4px",
                    borderColor: isActive ? "var(--brand)" : undefined,
                    color: isActive ? "var(--brand)" : undefined,
                  }}
                >
                  <span>{action.icon}</span>{action.label}
                </button>
              );
            })}

            {/* Pomodoro Timer inline (Study workspace) */}
            {workspaceType === "study" && showPomodoro && (
              <PomodoroTimer />
            )}
          </div>
        )}

        {/* Answer Key panel (Teacher workspace) */}
        {workspaceType === "exam" && showAnswerKey && generatedPaper?.answer_key && (
          <div style={{ marginTop: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "10px", padding: "12px", maxHeight: "240px", overflowY: "auto" }}>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "8px" }}>Answer Key</div>
            {generatedPaper.answer_key.map((entry: any) => (
              <div key={entry.question_number} style={{ padding: "6px 0", borderBottom: "1px solid var(--border-subtle)", fontFamily: "var(--font-body)", fontSize: "12px" }}>
                <span style={{ fontWeight: 600 }}>Q{entry.question_number}:</span>{" "}
                {entry.correct_answer}
                <span style={{ color: "var(--text-tertiary)", marginLeft: "8px" }}>
                  [{entry.bloom_level} · {entry.difficulty}]
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Bottom disclaimer banner removed (C6). The top dismissable banner is the single canonical instance. */}
      </div>
    </div>
  );
}
