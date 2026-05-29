"use client";

/**
 * Phase 9-E — Notification Center
 *
 * Bell icon (🔔) button positioned at top-right of the sidebar top section.
 * Shows unread count badge (≤9, then "9+").
 * On click: slides open a notification panel (320px).
 * Polls GET /api/v1/notifications on mount and on focus.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationCenterProps {
  onNavigate?: (link: string) => void;
}

export default function NotificationCenter({ onNavigate }: NotificationCenterProps) {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch("/notifications", {});
      if (res.ok) setNotifications(await res.json());
    } catch {
      // network unavailable — keep stale list
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Re-fetch when window regains focus
  useEffect(() => {
    const handleFocus = () => load();
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [load]);

  // Close panel on outside click
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setOpen(false); buttonRef.current?.focus(); }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  async function markRead(id: string) {
    try {
      await apiFetch(`/notifications/${id}/read`, { method: "POST" });
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // silent
    }
  }

  async function markAllRead() {
    try {
      await apiFetch("/notifications/read-all", { method: "POST" });
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // silent
    }
  }

  function handleNotificationClick(n: Notification) {
    if (!n.is_read) markRead(n.id);
    if (n.link && onNavigate) {
      onNavigate(n.link);
      setOpen(false);
    }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;
  const badgeLabel = unreadCount > 9 ? "9+" : unreadCount > 0 ? String(unreadCount) : null;

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      {/* Bell button */}
      <button
        ref={buttonRef}
        className="btn btn-ghost btn-icon"
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        style={{ position: "relative", width: 32, height: 32, padding: 0, flexShrink: 0 }}
      >
        <span aria-hidden="true" style={{ fontSize: 16 }}>🔔</span>

        {badgeLabel && (
          <span
            aria-hidden="true"
            style={{
              position: "absolute",
              top: 2,
              right: 2,
              background: "var(--error, #dc2626)",
              color: "#fff",
              borderRadius: "50%",
              minWidth: 16,
              height: 16,
              fontSize: 10,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1,
              padding: "0 3px",
            }}
          >
            {badgeLabel}
          </span>
        )}
      </button>

      {/* Notification panel */}
      {open && (
        <div
          ref={panelRef}
          role="region"
          aria-label="Notifications"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            right: 0,
            width: 320,
            background: "var(--surface, #fff)",
            border: "1px solid var(--border-default)",
            borderRadius: 10,
            boxShadow: "var(--shadow-xl, 0 10px 40px rgba(0,0,0,0.12))",
            zIndex: 500,
            overflow: "hidden",
          }}
        >
          {/* Panel header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 14px 10px",
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              Notifications
            </span>
            {unreadCount > 0 && (
              <button
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 12, padding: "2px 6px" }}
                onClick={markAllRead}
              >
                Mark all as read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div
            style={{ maxHeight: 360, overflowY: "auto" }}
            role="list"
          >
            {notifications.length === 0 ? (
              <p
                style={{
                  padding: "20px 14px",
                  fontSize: 13,
                  color: "var(--text-tertiary)",
                  textAlign: "center",
                }}
              >
                No new notifications
              </p>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  role="listitem"
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 8,
                    padding: "10px 14px",
                    borderBottom: "1px solid var(--border-subtle)",
                    background: n.is_read
                      ? "transparent"
                      : "var(--surface-active, rgba(99,102,241,0.04))",
                    cursor: n.link ? "pointer" : "default",
                    transition: "background 0.1s",
                  }}
                  onClick={() => handleNotificationClick(n)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") handleNotificationClick(n);
                  }}
                  tabIndex={n.link ? 0 : -1}
                  onMouseEnter={(e) => {
                    if (n.link)
                      (e.currentTarget as HTMLDivElement).style.background =
                        "var(--surface-hover, rgba(0,0,0,0.03))";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.background = n.is_read
                      ? "transparent"
                      : "var(--surface-active, rgba(99,102,241,0.04))";
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: 13,
                        fontWeight: n.is_read ? 400 : 600,
                        color: "var(--text-primary)",
                        marginBottom: 2,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {n.title}
                    </p>
                    <p
                      style={{
                        fontSize: 12,
                        color: "var(--text-secondary)",
                        lineHeight: 1.4,
                      }}
                    >
                      {n.body}
                    </p>
                    {n.link && (
                      <span
                        style={{
                          fontSize: 11,
                          color: "var(--brand, #0D0D0D)",
                          marginTop: 2,
                          display: "block",
                        }}
                      >
                        View →
                      </span>
                    )}
                  </div>

                  <button
                    className="btn btn-ghost"
                    style={{ padding: "2px 4px", fontSize: 12, flexShrink: 0, marginTop: -2 }}
                    aria-label="Dismiss notification"
                    title="Dismiss"
                    onClick={(e) => {
                      e.stopPropagation();
                      markRead(n.id);
                    }}
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
