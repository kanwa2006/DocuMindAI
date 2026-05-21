"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getChats, type ChatSession } from "@/lib/api";

const WORKSPACE_LABELS: Record<string, string> = {
  general: "General",
  hr: "HR",
  legal: "Legal",
  finance: "Finance",
  research: "Research",
  study: "Study",
  exam: "Exam",
};

export default function SessionsPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const all: ChatSession[] = [];
        for (const ws of Object.keys(WORKSPACE_LABELS)) {
          try {
            const rows = await getChats(ws, 50, 0, "");
            all.push(...rows);
          } catch {
            /* skip workspaces that error individually */
          }
        }
        all.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
        setSessions(all);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load sessions");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: "2rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 600, marginBottom: "0.25rem" }}>All sessions</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
        Every chat across every workspace, sorted by most recent.
      </p>

      {loading && <p style={{ color: "var(--text-tertiary)" }}>Loading…</p>}
      {error && (
        <div role="alert" style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "48px 16px", textAlign: "center", gap: "10px", color: "var(--error-text)" }}>
          <span style={{ fontSize: "32px" }}>⚠</span>
          <p style={{ margin: 0 }}>{error}</p>
          <button onClick={() => window.location.reload()} className="btn btn-ghost btn-sm">Retry</button>
        </div>
      )}
      {!loading && !error && sessions.length === 0 && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "64px 16px", textAlign: "center", gap: "12px" }}>
          <span style={{ fontSize: "40px", opacity: 0.35 }}>💬</span>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>No chats yet.</p>
          <Link href="/general" className="btn btn-secondary btn-sm" style={{ textDecoration: "none" }}>
            Start a new chat →
          </Link>
        </div>
      )}

      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {sessions.map((s) => (
          <li
            key={s.id}
            style={{
              padding: "0.875rem 0",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <Link
              href={`/${s.workspace_type}?session=${s.id}`}
              style={{ display: "flex", justifyContent: "space-between", gap: "1rem", color: "var(--text-primary)" }}
            >
              <span style={{ fontWeight: 500 }}>{s.title || "Untitled chat"}</span>
              <span style={{ color: "var(--text-tertiary)", fontSize: "0.875rem" }}>
                {WORKSPACE_LABELS[s.workspace_type] ?? s.workspace_type}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
