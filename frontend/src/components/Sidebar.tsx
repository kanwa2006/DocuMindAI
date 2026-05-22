"use client";

import Link from "next/link";
import { useState, useEffect, useRef, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useVirtualizer } from "@tanstack/react-virtual";
import { QuestionMarkCircleIcon } from "@heroicons/react/24/outline";
import LogoutButton from "./LogoutButton";
import FeedbackModal from "./FeedbackModal";
import { toast } from "react-hot-toast";
import { getChats, createChat, updateChat, deleteChat, updateChatTags, ChatSession, getBillingStatus, API_BASE } from "@/lib/api";
import { useOnboarding } from "@/hooks/useOnboarding";
import OnboardingProgress from "./OnboardingProgress";

// ─── Date grouping ────────────────────────────────────────────────────────────

type DateGroup = "TODAY" | "YESTERDAY" | "LAST 7 DAYS" | string;

function groupChatsByDate(chats: ChatSession[]): { label: DateGroup; chats: ChatSession[] }[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday.getTime() - 86400000);
  const startOfLast7 = new Date(startOfToday.getTime() - 6 * 86400000);

  const groups: Record<string, ChatSession[]> = {};
  const order: string[] = [];

  for (const chat of chats) {
    const date = new Date(chat.created_at || 0);
    let label: string;
    if (date >= startOfToday) label = "TODAY";
    else if (date >= startOfYesterday) label = "YESTERDAY";
    else if (date >= startOfLast7) label = "LAST 7 DAYS";
    else {
      label = date.toLocaleString("default", { month: "long", year: "numeric" }).toUpperCase();
    }
    if (!groups[label]) { groups[label] = []; order.push(label); }
    groups[label].push(chat);
  }

  return order.map((label) => ({ label, chats: groups[label] }));
}

// ─── Workspace icon map ───────────────────────────────────────────────────────

const WORKSPACE_ICONS: Record<string, string> = {
  general:  "💬",
  exam:     "📋",
  hr:       "👥",
  study:    "📚",
  research: "🔬",
  legal:    "⚖️",
  finance:  "📊",
};

// ─── Tag Popover ──────────────────────────────────────────────────────────────

function TagPopover({ chat, onClose, onSave }: { chat: ChatSession; onClose: () => void; onSave: (tags: string[]) => void }) {
  const [tags, setTags] = useState<string[]>(chat.tags || []);
  const [input, setInput] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed && !tags.includes(trimmed)) {
      const next = [...tags, trimmed];
      setTags(next);
      onSave(next);
    }
    setInput("");
  };

  const removeTag = (tag: string) => {
    const next = tags.filter((t) => t !== tag);
    setTags(next);
    onSave(next);
  };

  return (
    <div ref={ref} style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)", zIndex: 400, background: "var(--surface-overlay)", border: "1px solid var(--border-default)", borderRadius: "12px", boxShadow: "var(--shadow-xl)", padding: "16px", width: "260px" }}>
      <div style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "10px" }}>🏷 Tags for &ldquo;{chat.title.slice(0, 24)}&rdquo;</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px", minHeight: "24px" }}>
        {tags.map((tag) => (
          <span key={tag} style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", background: "var(--brand-ghost)", color: "var(--brand)", borderRadius: "999px", fontSize: "12px", fontFamily: "var(--font-body)" }}>
            {tag}
            <button onClick={() => removeTag(tag)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--brand)", fontSize: "11px", padding: 0, lineHeight: 1 }}>×</button>
          </span>
        ))}
        {tags.length === 0 && <span style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", fontStyle: "italic" }}>No tags yet</span>}
      </div>
      <div style={{ display: "flex", gap: "6px" }}>
        <input
          autoFocus
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } if (e.key === "Escape") onClose(); }}
          placeholder="Type tag, press Enter"
          style={{ flex: 1, height: "32px", padding: "0 8px", background: "var(--surface-sunken)", border: "1px solid var(--border-default)", borderRadius: "6px", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-primary)", outline: "none" }}
        />
        <button onClick={addTag} style={{ height: "32px", padding: "0 10px", background: "var(--brand)", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "12px" }}>Add</button>
      </div>
      <button onClick={onClose} style={{ marginTop: "10px", width: "100%", height: "28px", background: "none", border: "1px solid var(--border-default)", borderRadius: "6px", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-secondary)" }}>Done</button>
    </div>
  );
}

// ─── Context Menu ─────────────────────────────────────────────────────────────

interface ContextMenuProps {
  x: number;
  y: number;
  chat: ChatSession;
  plan: string;
  onClose: () => void;
  onRename: (chat: ChatSession) => void;
  onPin: (chat: ChatSession) => void;
  onShare: (chat: ChatSession) => void;
  onDelete: (chat: ChatSession) => void;
  onTag: (chat: ChatSession) => void;
  onExportAudit: (chat: ChatSession) => void;
}

function ContextMenu({ x, y, chat, plan, onClose, onRename, onPin, onShare, onDelete, onTag, onExportAudit }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const escHandler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", escHandler);
    return () => { document.removeEventListener("mousedown", handler); document.removeEventListener("keydown", escHandler); };
  }, [onClose]);

  // Adjust position to stay within viewport
  const menuStyle: React.CSSProperties = {
    position: "fixed",
    top: y,
    left: x,
    background: "var(--surface-overlay)",
    border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-lg)",
    boxShadow: "var(--shadow-xl)",
    minWidth: "160px",
    padding: "4px",
    zIndex: 300,
  };

  const itemStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 12px",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    fontFamily: "var(--font-body)",
    color: "var(--text-secondary)",
    cursor: "pointer",
    height: "32px",
    transition: "background var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard)",
  };

  const hoverStyle = (isDelete = false) => ({
    ...itemStyle,
    "&:hover": { background: "var(--surface-hover)", color: isDelete ? "var(--error-text)" : "var(--text-primary)" },
  });

  return (
    <div ref={ref} style={menuStyle} className="dropdown-enter">
      {[
        { icon: "✏️", label: "Rename", action: () => { onRename(chat); onClose(); } },
        { icon: chat.is_pinned ? "⭐" : "☆", label: chat.is_pinned ? "Unpin" : "Pin", action: () => { onPin(chat); onClose(); } },
        { icon: "🏷", label: "Add Tags", action: () => { onTag(chat); onClose(); } },
        { icon: "🔗", label: "Share", action: () => { onShare(chat); onClose(); } },
        {
          icon: plan === "trial" ? "🔒" : "📋",
          label: "Export Audit Report",
          action: () => { onExportAudit(chat); onClose(); },
          locked: plan === "trial",
        },
      ].map(({ icon, label, action, locked }) => (
        <button
          key={label}
          onClick={locked ? undefined : action}
          title={locked ? "Available on Professional plan" : undefined}
          style={{
            ...itemStyle,
            opacity: locked ? 0.55 : 1,
            cursor: locked ? "default" : "pointer",
          }}
          className="sidebar-item"
          onMouseEnter={(e) => {
            if (!locked) {
              (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)";
              (e.currentTarget as HTMLElement).style.color = "var(--text-primary)";
            }
          }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; (e.currentTarget as HTMLElement).style.color = ""; }}
        >
          <span>{icon}</span> {label}
        </button>
      ))}
      <div style={{ height: "1px", background: "var(--border-subtle)", margin: "4px 0" }} />
      <button
        onClick={() => { onDelete(chat); onClose(); }}
        style={{ ...itemStyle, color: "var(--error-text)" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--error-bg)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
      >
        <span>🗑</span> Delete
      </button>
    </div>
  );
}

// ─── Delete confirmation modal ────────────────────────────────────────────────

function DeleteConfirmModal({ chatTitle, onConfirm, onCancel }: { chatTitle: string; onConfirm: () => void; onCancel: () => void }) {
  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgb(0 0 0 / 0.5)", zIndex: 400,
        display: "flex", alignItems: "center", justifyContent: "center", padding: "16px",
      }}
      className="modal-backdrop-enter"
      aria-hidden="true"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        style={{
          background: "var(--surface-overlay)", border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-2xl)", boxShadow: "var(--shadow-2xl)", width: "100%", maxWidth: "360px",
          padding: "24px",
        }}
        className="modal-content-enter"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="delete-modal-title" style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-base)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)", margin: "0 0 8px" }}>
          Delete Chat?
        </h2>
        <p style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-secondary)", margin: "0 0 20px" }}>
          &ldquo;{chatTitle}&rdquo; will be permanently deleted.
        </p>
        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
          <button onClick={onCancel} className="btn btn-secondary btn-sm">Cancel</button>
          <button onClick={onConfirm} className="btn btn-sm" style={{ background: "var(--error-text)", color: "#fff" }}>Delete</button>
        </div>
      </div>
    </div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

export default function Sidebar({ isOpen, setIsOpen }: { isOpen: boolean; setIsOpen: (val: boolean) => void }) {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; chat: ChatSession } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ChatSession | null>(null);
  const [tagTarget, setTagTarget] = useState<ChatSession | null>(null);
  const [selectedTagFilter, setSelectedTagFilter] = useState<string | null>(null);
  const [showTagFilter, setShowTagFilter] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [is401, setIs401] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [plan, setPlan] = useState<string>("trial");
  const { isComplete, dismiss } = useOnboarding();

  useEffect(() => {
    getBillingStatus().then((s) => setPlan(s.plan)).catch(() => {});
  }, []);

  const parentRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const isOpenRef = useRef(isOpen);
  const pathname = usePathname();
  const router = useRouter();

  // Keep isOpenRef in sync with prop
  useEffect(() => { isOpenRef.current = isOpen; }, [isOpen]);

  // Current workspace type from pathname
  const workspaceType = pathname === "/dashboard" ? "general" : pathname.replace("/", "").split("/")[0] || "general";

  // ─── Mobile detection ───────────────────────────────────────────────────────
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // ─── Persist sidebar state ─────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem("sidebar_open");
    if (saved !== null) setIsOpen(saved === "true");
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") localStorage.setItem("sidebar_open", String(isOpen));
  }, [isOpen]);

  // ─── Load chats ─────────────────────────────────────────────────────────────
  const loadChats = useCallback(async (overrideSearch?: string) => {
    setLoadError(null);
    setIs401(false);
    try {
      const q = overrideSearch !== undefined ? overrideSearch : searchQuery;
      const fetched = await getChats(workspaceType, 100, 0, q);
      const sorted = [...fetched].sort((a, b) => {
        if (a.is_pinned !== b.is_pinned) return Number(b.is_pinned) - Number(a.is_pinned);
        return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      });
      setChats(sorted);
    } catch (err: any) {
      const status = err?.status ?? err?.response?.status ?? 0;
      if (!navigator.onLine) {
        setLoadError("No connection. Check your internet.");
      } else if (status === 401 || err?.message?.includes("Session expired")) {
        setIs401(true);
        setLoadError("Session expired. Please sign in.");
      } else if (status >= 500) {
        setLoadError("Server error. Please try again.");
      } else if (err?.name === "TimeoutError" || err?.code === "ECONNABORTED") {
        setLoadError("Taking too long. Try refreshing.");
      } else {
        setLoadError("Couldn't load your chats.");
      }
    }
  }, [workspaceType, searchQuery]);

  useEffect(() => {
    const timer = setTimeout(() => loadChats(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery, workspaceType]);

  // ─── Event bus ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const refresh = () => loadChats();
    const titleUpdated = (e: any) => {
      setChats((prev) => prev.map((c) => (c.id === e.detail.id ? { ...c, title: e.detail.title } : c)));
    };
    window.addEventListener("chats-updated", refresh);
    window.addEventListener("chat-title-updated", titleUpdated);
    return () => { window.removeEventListener("chats-updated", refresh); window.removeEventListener("chat-title-updated", titleUpdated); };
  }, [loadChats]);

  // ─── Keyboard shortcuts ──────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "b") { e.preventDefault(); setIsOpen(!isOpenRef.current); }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); searchRef.current?.focus(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setIsOpen]);

  // ─── Filtered & grouped chats ────────────────────────────────────────────────
  const allTags = Array.from(new Set(chats.flatMap((c) => c.tags || [])));

  const filtered = chats.filter((c) => {
    const matchesSearch = !searchQuery || c.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTag = !selectedTagFilter || (c.tags || []).includes(selectedTagFilter);
    return matchesSearch && matchesTag;
  });

  const grouped = groupChatsByDate(filtered);

  // Flat list for virtualizer
  type FlatItem = { type: "group"; label: string } | { type: "chat"; chat: ChatSession };
  const flatItems: FlatItem[] = [];
  for (const g of grouped) {
    flatItems.push({ type: "group", label: g.label });
    for (const c of g.chats) flatItems.push({ type: "chat", chat: c });
  }

  const rowVirtualizer = useVirtualizer({
    count: flatItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (i) => (flatItems[i]?.type === "group" ? 32 : 40),
    overscan: 8,
  });

  // ─── Handlers ────────────────────────────────────────────────────────────────
  const handleNewChat = async () => {
    try {
      const chat = await createChat("New Chat", workspaceType);
      setChats((prev) => [chat, ...prev].sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned)));
      router.push(`${pathname}?chat=${chat.id}`);
      if (isMobile) setIsOpen(false);
    } catch (err) { console.error(err); }
  };

  const handlePin = async (chat: ChatSession) => {
    try {
      const updated = await updateChat(chat.id, { is_pinned: !chat.is_pinned });
      setChats((prev) =>
        prev.map((c) => (c.id === chat.id ? updated : c)).sort((a, b) => {
          if (a.is_pinned !== b.is_pinned) return Number(b.is_pinned) - Number(a.is_pinned);
          return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
        })
      );
    } catch (err) { console.error(err); }
  };

  const handleRename = (chat: ChatSession) => {
    setRenamingId(chat.id);
    setRenameValue(chat.title);
  };

  const commitRename = async (chatId: string) => {
    if (!renameValue.trim()) { setRenamingId(null); return; }
    try {
      const updated = await updateChat(chatId, { title: renameValue.trim() });
      setChats((prev) => prev.map((c) => (c.id === chatId ? updated : c)));
    } catch (err) { console.error(err); }
    setRenamingId(null);
  };

  const handleShare = (chat: ChatSession) => {
    const url = `${window.location.origin}${pathname}?chat=${chat.id}`;
    navigator.clipboard.writeText(url).then(() => {
      if (typeof window !== "undefined" && (window as any).__toastSuccess) {
        (window as any).__toastSuccess("Link copied!");
      }
    });
  };

  const handleTagSave = async (chat: ChatSession, tags: string[]) => {
    try {
      await updateChatTags(chat.id, tags);
      setChats((prev) => prev.map((c) => c.id === chat.id ? { ...c, tags } : c));
    } catch { /* non-fatal */ }
  };

  const handleExportAudit = async (chat: ChatSession) => {
    const toastId = toast.loading("Generating audit report…");
    try {
      const res = await fetch(
        `${API_BASE}/export/sessions/${chat.id}/audit-report?format=pdf`,
        { credentials: "include" },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail || {};
        if (detail.upgrade_required || res.status === 402) {
          toast.error("Upgrade to Professional to export audit reports.", { id: toastId });
        } else {
          toast.error("Export failed.", { id: toastId });
        }
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit_${chat.title.slice(0, 40).replace(/[^a-z0-9_-]/gi, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Audit report downloaded.", { id: toastId });
    } catch {
      toast.error("Export failed.", { id: toastId });
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteChat(deleteTarget.id);
      setChats((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      if (window.location.search.includes(`chat=${deleteTarget.id}`)) router.push(pathname);
    } catch (err) { console.error(err); }
    setDeleteTarget(null);
  };

  const openContextMenu = (e: React.MouseEvent, chat: ChatSession) => {
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY, chat });
  };

  const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const activeChatId = searchParams?.get("chat");

  // ─── Overlay backdrop (mobile) ───────────────────────────────────────────────
  const showOverlay = isMobile && isOpen;

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <>
      {/* Mobile backdrop */}
      {showOverlay && (
        <div
          onClick={() => setIsOpen(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
            zIndex: 59, pointerEvents: "auto",
          }}
        />
      )}

      <nav
        aria-label="Chat history"
        className={`sidebar ${isOpen ? "" : "collapsed"}`}
        aria-hidden={!isOpen && !isMobile}
        style={{
          position: isMobile ? "fixed" : "sticky",
          top: isMobile ? 0 : "52px",
          left: 0,
          zIndex: isMobile ? 60 : undefined,
          height: "100vh",
          // Mobile: slide off-screen with translateX; keeps width so internal layout doesn't reflow.
          // Desktop: collapse width to 0 so the main content reclaims the space.
          transform: isMobile && !isOpen ? "translateX(-100%)" : "translateX(0)",
          width: isMobile ? "260px" : isOpen ? "260px" : "0px",
          minWidth: 0,
          flexShrink: 0,
          transition: isMobile
            ? "transform 300ms var(--ease-decel)"
            : "width var(--dur-slow) var(--ease-standard)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          // When collapsed, prevent clicks/tab focus landing on now-invisible children.
          pointerEvents: !isOpen ? "none" : "auto",
        }}
      >
        {/* ── TOP SECTION ── */}
        <div style={{ padding: "12px", flexShrink: 0 }}>
          {/* New Chat button */}
          <button
            id="sidebar-new-chat"
            onClick={handleNewChat}
            className="btn btn-primary"
            style={{ width: "100%", height: "44px", borderRadius: "10px", marginBottom: "8px", gap: "8px" }}
          >
            <span style={{ fontSize: "14px" }}>✏️</span>
            <span style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)" }}>New Chat</span>
          </button>

          {/* Onboarding progress checklist */}
          {!isComplete && (
            <OnboardingProgress
              documentsCount={0}
              messagesCount={chats.length > 0 ? 1 : 0}
              onDismiss={dismiss}
            />
          )}

          {/* Search + Tag Filter */}
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1 }}>
            <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", fontSize: "12px", color: "var(--text-tertiary)" }}>🔍</span>
            <input
              ref={searchRef}
              id="sidebar-search"
              type="text"
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                height: "36px",
                background: "var(--surface-sunken)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-md)",
                paddingLeft: "32px",
                paddingRight: searchQuery ? "32px" : "12px",
                fontFamily: "var(--font-body)",
                fontSize: "var(--text-sm)",
                color: "var(--text-primary)",
                outline: "none",
                transition: "border-color var(--dur-fast) var(--ease-standard), box-shadow var(--dur-fast) var(--ease-standard)",
                boxSizing: "border-box",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--brand)"; e.currentTarget.style.boxShadow = "var(--shadow-brand)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border-default)"; e.currentTarget.style.boxShadow = "none"; }}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
                style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", fontSize: "14px", padding: "2px", lineHeight: 1 }}
              >
                <span aria-hidden="true">✕</span>
              </button>
            )}
          </div>
          {/* Tag filter button */}
          <div style={{ position: "relative", flexShrink: 0 }}>
            <button
              onClick={() => setShowTagFilter((v) => !v)}
              aria-label="Filter by tag"
              title="Filter by tag"
              style={{
                width: "36px", height: "36px", border: `1px solid ${selectedTagFilter ? "var(--brand)" : "var(--border-default)"}`,
                borderRadius: "var(--radius-md)", background: selectedTagFilter ? "var(--brand-ghost)" : "var(--surface-sunken)",
                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "13px", flexShrink: 0,
              }}
            >⊡</button>
            {showTagFilter && (
              <div style={{ position: "absolute", top: "calc(100% + 4px)", right: 0, background: "var(--surface-overlay)", border: "1px solid var(--border-default)", borderRadius: "10px", boxShadow: "var(--shadow-lg)", padding: "8px", minWidth: "160px", zIndex: 200 }}>
                <button onClick={() => { setSelectedTagFilter(null); setShowTagFilter(false); }}
                  style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 10px", borderRadius: "6px", border: "none", cursor: "pointer", background: !selectedTagFilter ? "var(--brand-ghost)" : "transparent", color: !selectedTagFilter ? "var(--brand)" : "var(--text-secondary)", fontFamily: "var(--font-body)", fontSize: "12px", marginBottom: "2px" }}>
                  All sessions
                </button>
                {allTags.length === 0 && <div style={{ padding: "6px 10px", fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)", fontStyle: "italic" }}>No tags yet</div>}
                {allTags.map((tag) => (
                  <button key={tag} onClick={() => { setSelectedTagFilter(tag === selectedTagFilter ? null : tag); setShowTagFilter(false); }}
                    style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 10px", borderRadius: "6px", border: "none", cursor: "pointer", background: selectedTagFilter === tag ? "var(--brand-ghost)" : "transparent", color: selectedTagFilter === tag ? "var(--brand)" : "var(--text-secondary)", fontFamily: "var(--font-body)", fontSize: "12px", marginBottom: "2px" }}>
                    🏷 {tag}
                  </button>
                ))}
              </div>
            )}
          </div>
          </div>
        </div>

        {/* ── MIDDLE SECTION (sessions list) ── */}
        <div ref={parentRef} style={{ flex: 1, overflowY: "auto", padding: "0 8px", minHeight: 0 }}>
          {/* Error state */}
          {loadError && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "32px 16px", textAlign: "center", gap: "10px" }}>
              <span style={{ fontSize: "22px" }}>⚠</span>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-xs)", color: "var(--text-secondary)", lineHeight: "var(--leading-relaxed)" }}>
                {loadError}
              </div>
              {is401 ? (
                <a href="/login" style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-xs)", color: "var(--brand)", textDecoration: "none" }}>Sign in →</a>
              ) : (
                <button onClick={() => loadChats()} className="btn btn-ghost btn-sm" style={{ fontSize: "var(--text-xs)" }}>Retry</button>
              )}
            </div>
          )}

          {/* Empty state (no chats / no search results) */}
          {!loadError && flatItems.length === 0 && (
            searchQuery ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "40px 16px", textAlign: "center", gap: "8px" }}>
                <span style={{ fontSize: "28px", opacity: 0.4 }}>🔍</span>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
                  No sessions matching &ldquo;{searchQuery}&rdquo;
                </div>
                <button onClick={() => setSearchQuery("")} style={{ background: "none", border: "none", cursor: "pointer", fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--brand)", padding: 0 }}>
                  Clear search
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "48px 16px", textAlign: "center", gap: "10px" }}>
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none" style={{ opacity: 0.25 }}>
                  <rect x="6" y="8" width="20" height="26" rx="3" stroke="currentColor" strokeWidth="1.5"/>
                  <rect x="14" y="4" width="20" height="26" rx="3" stroke="currentColor" strokeWidth="1.5"/>
                  <line x1="11" y1="16" x2="21" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <line x1="11" y1="21" x2="19" y2="21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>No chats yet.</div>
                <button onClick={handleNewChat} className="btn btn-secondary btn-sm" style={{ fontSize: "var(--text-xs)", marginTop: "4px" }}>
                  Start a new chat →
                </button>
              </div>
            )
          )}

          <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: "100%", position: "relative" }}>
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const item = flatItems[virtualRow.index];
              if (!item) return null;

              if (item.type === "group") {
                return (
                  <div
                    key={`group-${item.label}`}
                    style={{ position: "absolute", top: 0, left: 0, width: "100%", height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--font-body)",
                        fontSize: "10px",
                        fontWeight: "var(--weight-medium)",
                        textTransform: "uppercase",
                        letterSpacing: "0.1em",
                        color: "var(--text-tertiary)",
                        padding: "12px 4px 4px",
                      }}
                    >
                      {item.label}
                    </div>
                  </div>
                );
              }

              // Chat item
              const chat = item.chat;
              const isActive = chat.id === activeChatId;
              const isRenaming = renamingId === chat.id;

              return (
                <div
                  key={chat.id}
                  style={{ position: "absolute", top: 0, left: 0, width: "100%", height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)`, padding: "2px 0" }}
                >
                  <div
                    className={`sidebar-item ${isActive ? "active" : ""}`}
                    style={{ height: "36px", minHeight: "36px", display: "flex", alignItems: "center", gap: "8px", position: "relative", cursor: "pointer" }}
                    onClick={() => { if (!isRenaming) { router.push(`${pathname}?chat=${chat.id}`); if (isMobile) setIsOpen(false); } }}
                  >
                    {/* Workspace icon */}
                    <span style={{ fontSize: "14px", flexShrink: 0, lineHeight: 1 }}>
                      {WORKSPACE_ICONS[chat.workspace_type || "general"] || "💬"}
                    </span>

                    {/* Title / rename input */}
                    {isRenaming ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitRename(chat.id);
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        onBlur={() => setRenamingId(null)}
                        onClick={(e) => e.stopPropagation()}
                        style={{ flex: 1, background: "var(--surface-sunken)", border: "1px solid var(--brand)", borderRadius: "4px", padding: "2px 6px", fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-primary)", outline: "none" }}
                      />
                    ) : (
                      <span style={{ flex: 1, fontFamily: "var(--font-body)", fontSize: "13px", color: isActive ? "var(--text-brand)" : "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {chat.title}
                        {chat.is_pinned && <span style={{ marginLeft: "4px", fontSize: "10px" }}>📌</span>}
                      </span>
                    )}

                    {/* Context menu trigger — shows on hover via group */}
                    {!isRenaming && (
                      <button
                        id={`chat-menu-${chat.id}`}
                        onClick={(e) => { e.stopPropagation(); openContextMenu(e, chat); }}
                        style={{ flexShrink: 0, width: "28px", height: "28px", display: "flex", alignItems: "center", justifyContent: "center", background: "none", border: "none", borderRadius: "var(--radius-md)", cursor: "pointer", color: "var(--text-tertiary)", opacity: 0, transition: "opacity var(--dur-fast) var(--ease-standard)", }}
                        className="chat-menu-btn"
                        aria-label={`Options for ${chat.title}`}
                        title="More options"
                        onMouseEnter={(e) => { e.currentTarget.style.opacity = "1"; e.currentTarget.style.background = "var(--surface-hover)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.opacity = "0"; e.currentTarget.style.background = "none"; }}
                      >
                        <span aria-hidden="true">⋯</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── BOTTOM SECTION ── */}
        <div style={{ flexShrink: 0, borderTop: "1px solid var(--border-subtle)", padding: "8px" }}>
          {[
            { icon: "📋", label: "All Sessions", href: "/sessions" },
            { icon: "🔖", label: "Saved", href: "/bookmarks" },
            { icon: "⚙️", label: "Settings", href: "/settings" },
            { icon: "👤", label: "Account", href: "/account" },
          ].map(({ icon, label, href }) => (
            <Link
              key={href}
              href={href}
              className="sidebar-item"
              style={{ height: "36px", display: "flex", alignItems: "center", gap: "8px", textDecoration: "none", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-secondary)" }}
            >
              <span style={{ fontSize: "14px" }}>{icon}</span>
              {label}
            </Link>
          ))}
          <button
            onClick={() => setShowFeedback(true)}
            className="sidebar-item"
            style={{ height: "36px", display: "flex", alignItems: "center", gap: "8px", border: "none", background: "none", cursor: "pointer", width: "100%", textAlign: "left", fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", color: "var(--text-secondary)", padding: "0 8px", borderRadius: "var(--radius-md)" }}
          >
            <span style={{ fontSize: "14px", display: "flex", alignItems: "center", flexShrink: 0 }}>
              <QuestionMarkCircleIcon style={{ width: "16px", height: "16px" }} />
            </span>
            Help & Feedback
          </button>
          <div style={{ marginTop: "4px" }}>
            <LogoutButton />
          </div>
        </div>
      </nav>

      {/* Context menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          chat={contextMenu.chat}
          plan={plan}
          onClose={() => setContextMenu(null)}
          onRename={handleRename}
          onPin={handlePin}
          onShare={handleShare}
          onDelete={(chat) => { setDeleteTarget(chat); }}
          onTag={(chat) => { setTagTarget(chat); }}
          onExportAudit={handleExportAudit}
        />
      )}

      {tagTarget && (
        <TagPopover
          chat={tagTarget}
          onClose={() => setTagTarget(null)}
          onSave={(tags) => handleTagSave(tagTarget, tags)}
        />
      )}

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <DeleteConfirmModal
          chatTitle={deleteTarget.title}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {showFeedback && <FeedbackModal onClose={() => setShowFeedback(false)} />}
    </>
  );
}
