"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getSharedSession, SharedSession, SharedSessionMessage } from "@/lib/api";

export default function SharedSessionPage() {
  const params = useParams();
  const token = typeof params?.token === "string" ? params.token : Array.isArray(params?.token) ? params.token[0] : "";

  const [session, setSession] = useState<SharedSession | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const fetchSession = async (silent = false) => {
    try {
      const data = await getSharedSession(token);
      setSession(data);
      if (!silent) setLoading(false);
    } catch (err: any) {
      setError(err.message ?? "Session not found");
      if (!silent) setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    if (!token) return;
    fetchSession();
  }, [token]);

  // Poll for new messages every 4 seconds (Supabase Realtime can replace this when SDK is added)
  useEffect(() => {
    if (!token) return;
    pollRef.current = setInterval(() => fetchSession(true), 4000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [token]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages?.length]);

  const handleAsk = async () => {
    if (!question.trim() || asking) return;
    setAsking(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${API_BASE}/shared/${token}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as any).detail ?? "Failed to send question");
      }
      setQuestion("");
      await fetchSession(true);
    } catch (err: any) {
      alert(err.message ?? "Failed to send question");
    } finally {
      setAsking(false);
    }
  };

  // ── Styles ──────────────────────────────────────────────────────────────────

  const pageStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: "var(--surface-base, #0f1117)",
    color: "var(--text-primary, #f1f5f9)",
    fontFamily: "var(--font-body, system-ui, sans-serif)",
    display: "flex", flexDirection: "column", alignItems: "center",
  };

  const bannerStyle: React.CSSProperties = {
    width: "100%", padding: "12px 24px",
    background: "var(--brand-ghost, rgba(99,102,241,0.1))",
    borderBottom: "1px solid var(--brand-glow, rgba(99,102,241,0.3))",
    textAlign: "center",
    fontSize: "var(--text-sm, 14px)",
    color: "var(--text-secondary, #94a3b8)",
  };

  const containerStyle: React.CSSProperties = {
    width: "100%", maxWidth: "780px",
    flex: 1, display: "flex", flexDirection: "column",
    padding: "0 16px 24px",
  };

  const headerStyle: React.CSSProperties = {
    padding: "24px 0 16px",
    borderBottom: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
    marginBottom: "24px",
  };

  const msgContainerStyle: React.CSSProperties = {
    flex: 1, overflowY: "auto",
    display: "flex", flexDirection: "column", gap: "16px",
  };

  // ── Loading / error states ───────────────────────────────────────────────────

  if (loading) {
    return (
      <div style={{ ...pageStyle, alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "var(--text-sm, 14px)" }}>
          Loading shared session…
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div style={{ ...pageStyle, alignItems: "center", justifyContent: "center" }}>
        <div style={{
          background: "var(--surface-overlay, #1e2030)",
          border: "1px solid var(--border-default, rgba(255,255,255,0.12))",
          borderRadius: "var(--radius-xl, 16px)",
          padding: "32px 40px", textAlign: "center", maxWidth: "400px",
        }}>
          <div style={{ fontSize: "40px", marginBottom: "16px" }}>🔗</div>
          <h2 style={{ margin: "0 0 8px", fontSize: "var(--text-lg, 18px)", color: "var(--text-primary, #f1f5f9)" }}>
            Session Not Found
          </h2>
          <p style={{ margin: 0, color: "var(--text-secondary, #94a3b8)", fontSize: "var(--text-sm, 14px)" }}>
            {error || "This shared session does not exist or sharing has been disabled."}
          </p>
        </div>
      </div>
    );
  }

  const canAsk = session.share_permissions === "view_and_ask";

  return (
    <div style={pageStyle}>
      {/* Banner */}
      <div style={bannerStyle}>
        You are viewing a shared session
        <span style={{ color: "var(--text-brand, #818cf8)", fontWeight: 600, marginLeft: "4px" }}>
          {session.title}
        </span>
        {canAsk ? " — you can read and ask questions" : " — read only"}
      </div>

      <div style={containerStyle}>
        {/* Header */}
        <div style={headerStyle}>
          <h1 style={{ margin: "0 0 4px", fontSize: "var(--text-xl, 20px)", fontWeight: 600 }}>
            {session.title}
          </h1>
          <div style={{ fontSize: "var(--text-xs, 12px)", color: "var(--text-secondary, #94a3b8)", display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <span>Workspace: <strong style={{ textTransform: "capitalize" }}>{session.workspace_type}</strong></span>
            <span>{session.messages.length} message{session.messages.length !== 1 ? "s" : ""}</span>
            <span
              style={{
                background: canAsk ? "var(--brand-ghost, rgba(99,102,241,0.12))" : "rgba(148,163,184,0.1)",
                color: canAsk ? "var(--text-brand, #818cf8)" : "var(--text-secondary, #94a3b8)",
                border: `1px solid ${canAsk ? "var(--brand-glow, rgba(99,102,241,0.3))" : "rgba(148,163,184,0.2)"}`,
                borderRadius: "var(--radius-full, 9999px)",
                padding: "1px 8px", fontSize: "var(--text-2xs, 11px)", fontWeight: 500,
              }}
            >
              {canAsk ? "View & Ask" : "View Only"}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div style={msgContainerStyle}>
          {session.messages.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--text-secondary, #94a3b8)", fontSize: "var(--text-sm, 14px)", marginTop: "48px" }}>
              No messages yet in this session.
            </div>
          ) : (
            session.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Ask input */}
        {canAsk && (
          <div
            style={{
              marginTop: "24px",
              borderTop: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
              paddingTop: "20px",
              display: "flex", gap: "10px", alignItems: "flex-end",
            }}
          >
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); }
              }}
              placeholder="Ask a question about this session… (Enter to send)"
              rows={3}
              style={{
                flex: 1, padding: "10px 14px", resize: "none",
                background: "var(--surface-raised, #1a1d2e)",
                border: "1px solid var(--border-default, rgba(255,255,255,0.12))",
                borderRadius: "var(--radius-lg, 12px)",
                color: "var(--text-primary, #f1f5f9)",
                fontSize: "var(--text-sm, 14px)",
                fontFamily: "var(--font-body, system-ui)",
                outline: "none",
                lineHeight: 1.5,
              }}
            />
            <button
              onClick={handleAsk}
              disabled={asking || !question.trim()}
              style={{
                padding: "10px 20px", height: "42px",
                background: "var(--brand, #6366f1)", color: "#fff",
                border: "none", borderRadius: "var(--radius-lg, 12px)",
                cursor: asking || !question.trim() ? "not-allowed" : "pointer",
                fontWeight: 600, fontSize: "var(--text-sm, 14px)",
                opacity: asking || !question.trim() ? 0.5 : 1,
                whiteSpace: "nowrap",
                fontFamily: "var(--font-body, system-ui)",
              }}
            >
              {asking ? "Sending…" : "Ask"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: SharedSessionMessage }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) return null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isUser ? "row-reverse" : "row",
        gap: "10px", alignItems: "flex-start",
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: "32px", height: "32px", borderRadius: "50%", flexShrink: 0,
          background: isUser ? "var(--brand, #6366f1)" : "var(--surface-overlay, #1e2030)",
          border: isUser ? "none" : "1px solid var(--border-default, rgba(255,255,255,0.12))",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "14px",
        }}
      >
        {isUser ? "👤" : "🤖"}
      </div>

      {/* Bubble */}
      <div
        style={{
          maxWidth: "72%",
          padding: "10px 14px",
          borderRadius: isUser ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
          background: isUser
            ? "var(--brand, #6366f1)"
            : "var(--surface-overlay, #1e2030)",
          border: isUser ? "none" : "1px solid var(--border-default, rgba(255,255,255,0.08))",
          color: "var(--text-primary, #f1f5f9)",
          fontSize: "var(--text-sm, 14px)",
          lineHeight: 1.6,
        }}
      >
        {isUser ? (
          <span>{message.content}</span>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        )}
        {message.created_at && (
          <div
            style={{
              marginTop: "4px",
              fontSize: "var(--text-2xs, 11px)",
              color: isUser ? "rgba(255,255,255,0.6)" : "var(--text-tertiary, #64748b)",
              textAlign: "right",
            }}
          >
            {new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </div>
        )}
      </div>
    </div>
  );
}
