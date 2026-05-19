"use client";

/**
 * Phase 9-E — Pinned Sessions Rail
 *
 * Renders the "PINNED" section above date-grouped sessions in the sidebar.
 * Pinning state lives on ChatSession.is_pinned (PATCH /chats/{id}).
 * Max 5 pinned sessions enforced client-side with a toast on violation.
 */

import { toast } from "react-hot-toast";
import type { ChatSession } from "@/lib/api";
import { API_BASE, getCsrfToken } from "@/lib/api";

export interface PinnedSessionsRailProps {
  sessions: ChatSession[];
  activeSessionId?: string;
  onSelectSession: (id: string) => void;
  onSessionsChange: (updated: ChatSession[]) => void;
}

const MAX_PINNED = 5;

export async function pinSession(
  sessionId: string,
  allSessions: ChatSession[]
): Promise<boolean> {
  const alreadyPinned = allSessions.filter((s) => s.is_pinned).length;
  if (alreadyPinned >= MAX_PINNED) {
    toast.error(`You can pin up to ${MAX_PINNED} sessions. Unpin one to continue.`);
    return false;
  }
  const res = await fetch(`${API_BASE}/api/v1/chats/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": getCsrfToken() },
    credentials: "include",
    body: JSON.stringify({ is_pinned: true }),
  });
  return res.ok;
}

export async function unpinSession(sessionId: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/api/v1/chats/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": getCsrfToken() },
    credentials: "include",
    body: JSON.stringify({ is_pinned: false }),
  });
  return res.ok;
}

export default function PinnedSessionsRail({
  sessions,
  activeSessionId,
  onSelectSession,
  onSessionsChange,
}: PinnedSessionsRailProps) {
  const pinned = sessions.filter((s) => s.is_pinned);

  if (pinned.length === 0) return null;

  async function handleUnpin(e: React.MouseEvent, session: ChatSession) {
    e.stopPropagation();
    const ok = await unpinSession(session.id);
    if (ok) {
      onSessionsChange(
        sessions.map((s) => (s.id === session.id ? { ...s, is_pinned: false } : s))
      );
    } else {
      toast.error("Failed to unpin session");
    }
  }

  return (
    <div
      className="pinned-sessions-rail"
      style={{ marginBottom: 8 }}
      aria-label="Pinned sessions"
    >
      {/* Section header */}
      <p
        style={{
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          color: "var(--text-tertiary)",
          padding: "0 12px",
          marginBottom: 4,
          userSelect: "none",
        }}
      >
        Pinned
      </p>

      {pinned.map((session) => {
        const isActive = session.id === activeSessionId;
        return (
          <div
            key={session.id}
            role="button"
            tabIndex={0}
            aria-current={isActive ? "page" : undefined}
            onClick={() => onSelectSession(session.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onSelectSession(session.id);
            }}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "6px 12px",
              borderRadius: 6,
              cursor: "pointer",
              background: isActive ? "var(--surface-active, rgba(99,102,241,0.08))" : "transparent",
              transition: "background 0.1s",
            }}
            onMouseEnter={(e) => {
              if (!isActive)
                (e.currentTarget as HTMLDivElement).style.background =
                  "var(--surface-hover, rgba(0,0,0,0.04))";
            }}
            onMouseLeave={(e) => {
              if (!isActive)
                (e.currentTarget as HTMLDivElement).style.background = "transparent";
            }}
          >
            <span
              style={{
                fontSize: 13,
                color: isActive ? "var(--brand, #6366f1)" : "var(--text-primary)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                flex: 1,
              }}
              title={session.title}
            >
              ★ {session.title || "Untitled session"}
            </span>

            <button
              className="btn btn-ghost"
              style={{ padding: "2px 4px", fontSize: 12, marginLeft: 4, flexShrink: 0 }}
              aria-label={`Unpin ${session.title}`}
              onClick={(e) => handleUnpin(e, session)}
              title="Unpin session"
            >
              ×
            </button>
          </div>
        );
      })}

      <div
        style={{
          height: 1,
          background: "var(--border-subtle, rgba(0,0,0,0.06))",
          margin: "8px 12px 4px",
        }}
        aria-hidden="true"
      />
    </div>
  );
}
