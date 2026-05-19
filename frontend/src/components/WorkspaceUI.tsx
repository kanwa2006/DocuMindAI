"use client";

import { useState, useEffect, useRef, useCallback, memo } from "react";
import { Toaster, toast } from "react-hot-toast";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import React from "react";
import {
  uploadDocument, askQuestionStream, listDocuments, getDocument,
  Document, QueryResponse, getChats, createChat, getChatMessages,
  createChatMessage, ChatMessage, updateChat,
} from "../lib/api";

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
  exam:     [{ icon: "📄", label: "Generate Paper" }, { icon: "📖", label: "Question Bank" }, { icon: "🔑", label: "Answer Key" }, { icon: "🖨", label: "Export DOCX" }],
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

// ─── ReactMarkdown: table with Copy+CSV export (Additional req) ───────────────

function TableWithExport({ children }: { children: React.ReactNode }) {
  const tableRef = useRef<HTMLTableElement>(null);
  const [htmlCopied, setHtmlCopied] = useState(false);
  const chipStyle: React.CSSProperties = { height: "26px", padding: "0 10px", fontSize: "11px", background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "6px", cursor: "pointer", color: "var(--text-secondary)", display: "inline-flex", alignItems: "center", gap: "4px", fontFamily: "var(--font-body)", transition: "border-color 100ms" };
  const copyHTML = () => {
    if (tableRef.current) { navigator.clipboard.writeText(tableRef.current.outerHTML); setHtmlCopied(true); setTimeout(() => setHtmlCopied(false), 2000); }
  };
  const downloadCSV = () => {
    if (!tableRef.current) return;
    const rows = Array.from(tableRef.current.querySelectorAll("tr"));
    const csv = rows.map((r) => Array.from(r.querySelectorAll("th,td")).map((c) => `"${(c.textContent || "").replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `documindai_table_${Date.now()}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  };
  return (
    <div style={{ marginBottom: "8px" }}>
      <div style={{ overflowX: "auto" }}>
        <table ref={tableRef} style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>{children}</table>
      </div>
      <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
        <button onClick={copyHTML} style={chipStyle} onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; }} onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}>{htmlCopied ? "✓" : "📋"} Copy Table</button>
        <button onClick={downloadCSV} style={chipStyle} onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; }} onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; }}>📊 CSV</button>
      </div>
    </div>
  );
}

const MARKDOWN_COMPONENTS = {
  code: CodeBlock,
  table: ({ children }: any) => <TableWithExport>{children}</TableWithExport>,
  th: ({ children }: any) => <th style={{ padding: "8px 12px", background: "var(--surface-sunken)", borderBottom: "2px solid var(--border-default)", textAlign: "left", fontWeight: 600, fontSize: "13px" }}>{children}</th>,
  td: ({ children }: any) => <td style={{ padding: "8px 12px", borderBottom: "1px solid var(--border-subtle)", fontSize: "13px" }}>{children}</td>,
};

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
            <span style={{ background: cfg.badge.color + "22", color: cfg.badge.color, border: `1px solid ${cfg.badge.color}55`, borderRadius: "var(--radius-full)", padding: "3px 12px", fontSize: "12px", fontWeight: 500 }}>{cfg.badge.text}</span>
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
}: {
  msg: ChatMessage; chatId: string | null; workspaceType: string;
  isLastAI: boolean; isStreaming: boolean;
  onRegenerate: () => void;
  followUps: string[]; onFollowUpClick: (p: string) => void;
}) => {
  const [hovered, setHovered] = useState(false);
  const [copyDone, setCopyDone] = useState(false);

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
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS as any}>{mainText}</ReactMarkdown>
      </div>

      {/* Citations + confidence */}
      {evidence.length > 0 && (
        <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", textTransform: "uppercase" }}>Sources:</span>
          {evidence.slice(0, 4).map((chunk: any, i: number) => (
            <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", border: "1px solid var(--border-default)", borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "11px", cursor: "default", transition: "border-color 100ms, background 100ms" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; (e.currentTarget as HTMLElement).style.background = "var(--brand-ghost)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.background = ""; }}
            >📄 {chunk.filename} p.{chunk.page_number}</span>
          ))}
          <ConfidenceBadge score={confidence} />
        </div>
      )}
      {evidence.length === 0 && (
        <div style={{ marginTop: "6px" }}><ConfidenceBadge score={confidence} /></div>
      )}

      {/* Disclaimer banner */}
      {disclaimerText && (
        <div style={{ marginTop: "8px", padding: "8px 12px", background: "var(--warning-bg)", border: "1px solid var(--warning-border)", borderRadius: "8px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--warning-text)", fontStyle: "italic" }}>
          ⚠ {disclaimerText}
        </div>
      )}

      {/* Actions row (hover) */}
      <div style={{ display: "flex", gap: "4px", marginTop: "8px", opacity: hovered ? 1 : 0, transition: "opacity 100ms" }}>
        <button className="btn btn-ghost btn-sm" style={{ height: "28px" }}
          onClick={() => { navigator.clipboard.writeText(textContent); setCopyDone(true); setTimeout(() => setCopyDone(false), 2000); toast.success("Copied"); }}
        >{copyDone ? "✓" : "📋"} Copy</button>
        {isLastAI && !isStreaming && (
          <button className="btn btn-ghost btn-sm" style={{ height: "28px" }} onClick={onRegenerate}>🔄 Regenerate</button>
        )}
        <button className="btn btn-ghost btn-sm" style={{ height: "28px" }} onClick={() => toast.success("Thanks for the feedback!")}>👍 Helpful</button>
        <button className="btn btn-ghost btn-sm" style={{ height: "28px" }} onClick={() => toast("Noted — we'll improve.", { icon: "👎" })}>👎 Not Helpful</button>
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

export default function WorkspaceUI({ workspaceType = "general" }: { workspaceType?: string }) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [activeDoc, setActiveDoc] = useState<Document | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [showThinkingLabel, setShowThinkingLabel] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollingIntervalsRef = useRef<NodeJS.Timeout[]>([]);
  const thinkingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const chatId = searchParams.get("chat");

  const isStreaming = loading;

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
    if (!activeDoc || activeDoc.status !== "READY") {
      toast.error("Please wait for document to be ready.");
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
          setResponse((prev) => prev ? { ...prev, confidence_score: metadata.confidence_score, evidence: metadata.evidence } : null);
        },
        (token) => {
          if (thinkingTimerRef.current) { clearTimeout(thinkingTimerRef.current); thinkingTimerRef.current = null; }
          setShowThinkingLabel(false);
          setResponse((prev) => prev ? { ...prev, answer: prev.answer + token } : null);
        },
        (err) => {
          if (err !== "Request cancelled.") toast.error(err, { id: toastId });
          setLoading(false);
          abortControllerRef.current = null;
          if (thinkingTimerRef.current) clearTimeout(thinkingTimerRef.current);
        },
        async () => {
          if (!abortControllerRef.current) return;
          toast.success("Response complete.", { id: toastId });
          setLoading(false);
          abortControllerRef.current = null;
          if (thinkingTimerRef.current) clearTimeout(thinkingTimerRef.current);
          setShowThinkingLabel(false);
          setResponse((currentRes) => {
            if (currentRes && chatId) {
              createChatMessage(chatId, "assistant", JSON.stringify(currentRes)).then((savedMsg) => {
                setHistory((prev) => [...prev, savedMsg]);
              });
            }
            return currentRes;
          });
          setTimeout(() => { setResponse(null); }, 120);
        },
        abortControllerRef.current.signal,
        chatId || undefined,
        workspaceType,
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

  const isLegalOrFinance = workspaceType === "legal" || workspaceType === "finance";

  // Derive last AI message index for regenerate button
  const lastAiMsgIdx = history.map((m) => m.role).lastIndexOf("assistant");

  return (
    <div className="h-full flex flex-col px-4 md:px-8 py-6 pb-0 w-full max-w-6xl mx-auto">
      <Toaster position="top-center" toastOptions={{ className: "dark:bg-black dark:text-white border dark:border-white/10 shadow-lg rounded-md text-sm" }} />

      {/* ── Chat area ── */}
      <div className="flex-1 overflow-y-auto mb-4 pr-2" style={{ scrollBehavior: "smooth" }}>

        {/* Welcome state (Task 5.1) */}
        {!response && !loading && history.length === 0 && (
          <WorkspaceWelcome workspaceType={workspaceType} onQuickAction={sendMessage} />
        )}

        {/* No documents empty state (Task 5.2) */}
        {!response && !loading && history.length === 0 && docs.length === 0 && activeDoc === null && (
          <div style={{ position: "absolute", bottom: "180px", left: "50%", transform: "translateX(-50%)", textAlign: "center", pointerEvents: "none", opacity: 0.6 }}>
            <div style={{ fontSize: "48px", marginBottom: "8px" }}>📄</div>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-secondary)" }}>Upload a document to begin</div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "16px", paddingBottom: "40px" }}>
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

              <div style={{ paddingBottom: "8px" }}>
                {/* AI label */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                  <div style={{ width: "16px", height: "16px", borderRadius: "4px", background: "var(--brand)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "10px", fontWeight: 700 }}>D</div>
                  <span style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", animation: loading ? "pulse 1.5s ease-in-out infinite" : "none" }}>DocuMindAI</span>
                </div>

                {/* Thinking label */}
                {showThinkingLabel && !response.answer && (
                  <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", fontStyle: "italic", marginBottom: "8px" }}>
                    DocuMindAI is thinking...
                  </div>
                )}

                {/* Streaming content */}
                <div className="text-response" style={{ fontSize: "15px", lineHeight: "var(--leading-loose)", fontFamily: "var(--font-body)", color: "var(--text-primary)" }}>
                  {(() => {
                    const { main } = splitDisclaimer(response.answer || "");
                    return (
                      <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS as any}>{main || "Thinking..."}</ReactMarkdown>
                        {loading && (
                          <span className="streaming-cursor" style={{ display: "inline-block", width: "2px", height: "1em", background: "var(--brand)", marginLeft: "2px", verticalAlign: "text-bottom", animation: "blink 1s step-end infinite" }}>▍</span>
                        )}
                      </>
                    );
                  })()}
                </div>

                {/* Evidence chips while streaming */}
                {response.evidence.length > 0 && (
                  <div style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", textTransform: "uppercase" }}>Sources:</span>
                    {response.evidence.slice(0, 4).map((chunk, i) => (
                      <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", border: "1px solid var(--border-default)", borderRadius: "4px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
                        📄 {chunk.filename} p.{chunk.page_number}
                      </span>
                    ))}
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
      <div style={{ background: "var(--surface-base)", paddingTop: "8px", paddingBottom: "16px", backdropFilter: "blur(8px)", borderTop: "1px solid var(--border-subtle)", position: "sticky", bottom: 0, zIndex: 10 }}>

        {/* Document tray */}
        <div style={{ marginBottom: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px", padding: "0 2px" }}>
            <span style={{ fontFamily: "var(--font-body)", fontSize: "11px", fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em" }}>Documents</span>
          </div>
          <div style={{ display: "flex", gap: "10px", overflowX: "auto", paddingBottom: "4px" }}>
            <div id="upload-trigger" onClick={handleUploadClick}
              style={{ flexShrink: 0, width: "116px", height: "80px", border: `2px dashed var(--border-default)`, borderRadius: "10px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "border-color 100ms, background 100ms",
                animation: docs.length === 0 ? "bounce 1.5s ease-in-out 2" : "none" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)"; (e.currentTarget as HTMLElement).style.background = "var(--brand-ghost)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.background = ""; }}
            >
              <span style={{ fontSize: "20px", marginBottom: "4px" }}>+</span>
              <span style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)" }}>Upload</span>
            </div>
            <input type="file" className="hidden" accept=".pdf,.docx" ref={fileInputRef} onChange={handleFileChange} />
            {docs.map((d) => (
              <div key={d.id} onClick={() => setActiveDoc(d)}
                style={{ flexShrink: 0, width: "116px", height: "80px", border: `1px solid ${activeDoc?.id === d.id ? "var(--brand)" : "var(--border-default)"}`, borderRadius: "10px", padding: "10px", display: "flex", flexDirection: "column", justifyContent: "space-between", cursor: "pointer", background: activeDoc?.id === d.id ? "var(--brand-ghost)" : "", transition: "border-color 100ms, background 100ms" }}
              >
                <div style={{ fontFamily: "var(--font-body)", fontSize: "11px", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text-primary)" }} title={d.filename}>{d.filename}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: d.status === "READY" ? "var(--success-text)" : d.status === "FAILED" ? "var(--error-text)" : "var(--brand)", opacity: d.status === "READY" || d.status === "FAILED" ? 1 : undefined, animation: d.status !== "READY" && d.status !== "FAILED" ? "pulse 1.5s ease-in-out infinite" : "none" }} />
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "9px", color: "var(--text-tertiary)" }}>{d.status}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Input container (Task 4.11 textarea) */}
        <form onSubmit={handleAsk}>
          <div style={{ background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "16px", boxShadow: "var(--shadow-sm)", padding: "12px 16px", transition: "border-color 100ms, box-shadow 100ms" }}
            onFocusCapture={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-strong)"; (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-md)"; }}
            onBlurCapture={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)"; (e.currentTarget as HTMLElement).style.boxShadow = "var(--shadow-sm)"; }}
          >
            <textarea
              id="chat-textarea"
              ref={textareaRef}
              value={query}
              rows={1}
              onChange={handleTextareaChange}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  sendMessage(query);
                }
              }}
              disabled={!activeDoc || activeDoc.status !== "READY" || loading}
              placeholder={!activeDoc ? "Upload a document to ask anything..." : activeDoc.status !== "READY" ? "Processing document..." : "Ask anything about your documents... (Shift+Enter for new line)"}
              className="chat-input"
              style={{ width: "100%", background: "transparent", border: "none", outline: "none", resize: "none", minHeight: "44px", maxHeight: "200px", fontFamily: "var(--font-body)", fontSize: "14px", lineHeight: "var(--leading-relaxed)", color: "var(--text-primary)", display: "block", overflow: "auto" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px" }}>
              <div style={{ display: "flex", gap: "4px" }}>
                <button type="button" onClick={handleUploadClick} className="btn-icon btn-ghost" style={{ width: "32px", height: "32px" }} title="Attach file">📎</button>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {query.length > 3200 && (
                  <span style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)" }}>{query.length} / 4000</span>
                )}
                {isStreaming ? (
                  <button type="button" onClick={handleStopGenerating} className="btn btn-secondary btn-sm" style={{ height: "36px" }}>⏹ Stop</button>
                ) : (
                  <button type="submit" disabled={!query.trim() || loading} className="btn btn-primary" style={{ height: "36px", minWidth: "64px" }}>Send</button>
                )}
              </div>
            </div>
          </div>
        </form>

        {/* Workspace-specific action buttons */}
        {WORKSPACE_ACTIONS[workspaceType] && (
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
            {WORKSPACE_ACTIONS[workspaceType].map((action) => (
              <button key={action.label} className="btn btn-secondary btn-sm" style={{ height: "32px", fontSize: "12px", gap: "4px" }}>
                <span>{action.icon}</span>{action.label}
              </button>
            ))}
          </div>
        )}

        {/* Sticky disclaimer pill (legal / finance) */}
        {isLegalOrFinance && (
          <div style={{ marginTop: "8px", textAlign: "center" }}>
            <span style={{ background: "var(--warning-bg)", color: "var(--warning-text)", border: "1px solid var(--warning-border)", borderRadius: "var(--radius-full)", padding: "4px 14px", fontFamily: "var(--font-body)", fontSize: "12px", display: "inline-block" }}>
              ⚠ AI analysis — not {workspaceType === "legal" ? "legal" : "financial"} advice. Always verify with a professional.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
