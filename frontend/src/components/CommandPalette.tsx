"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Command {
  id: string;
  icon: string;
  title: string;
  subtitle?: string;
  kbd?: string;
  section: "COMMANDS" | "WORKSPACES" | "SESSIONS" | "DOCUMENTS";
  action: () => void;
}

const WORKSPACE_LIST = [
  { id: "general", label: "General", icon: "💬" },
  { id: "exam",    label: "Teacher / Exam", icon: "📋" },
  { id: "legal",   label: "Legal", icon: "⚖️" },
  { id: "finance", label: "Finance", icon: "📊" },
  { id: "hr",      label: "HR", icon: "👥" },
  { id: "study",   label: "Student", icon: "📚" },
  { id: "research",label: "Research", icon: "🔬" },
];

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const buildCommands = useCallback((): Command[] => {
    const cmds: Command[] = [
      {
        id: "new-chat", icon: "✏️", title: "New Chat",
        subtitle: "Start a fresh conversation", section: "COMMANDS",
        action: () => { window.dispatchEvent(new CustomEvent("cmd:new-chat")); onClose(); },
      },
      {
        id: "upload", icon: "📎", title: "Upload Document",
        subtitle: "Attach a PDF or DOCX", section: "COMMANDS",
        action: () => { window.dispatchEvent(new CustomEvent("cmd:upload")); onClose(); },
      },
      {
        id: "export", icon: "📤", title: "Export Chat as PDF",
        subtitle: "Download this session", kbd: "⇧⌘E", section: "COMMANDS",
        action: () => { window.dispatchEvent(new CustomEvent("cmd:export")); onClose(); },
      },
      {
        id: "dark-mode", icon: "🌙", title: "Toggle Dark Mode",
        subtitle: "Switch light / dark / system", kbd: "⌘D", section: "COMMANDS",
        action: () => { window.dispatchEvent(new CustomEvent("cmd:toggle-theme")); onClose(); },
      },
      {
        id: "settings", icon: "⚙️", title: "Open Settings",
        subtitle: "Preferences and account", section: "COMMANDS",
        action: () => { router.push("/settings"); onClose(); },
      },
      {
        id: "dashboard", icon: "📊", title: "Open Dashboard",
        subtitle: "Usage and analytics", section: "COMMANDS",
        action: () => { router.push("/dashboard"); onClose(); },
      },
      {
        id: "shortcuts", icon: "⌨️", title: "Keyboard Shortcuts",
        subtitle: "View all shortcuts", kbd: "?", section: "COMMANDS",
        action: () => { window.dispatchEvent(new CustomEvent("cmd:shortcuts")); onClose(); },
      },
      ...WORKSPACE_LIST.map((ws) => ({
        id: `ws-${ws.id}`,
        icon: ws.icon,
        title: `Switch to ${ws.label}`,
        subtitle: `${ws.label} workspace`,
        section: "WORKSPACES" as const,
        action: () => {
          router.push(ws.id === "general" ? "/" : `/${ws.id}`);
          onClose();
        },
      })),
    ];
    return cmds;
  }, [router, onClose]);

  const filtered = buildCommands().filter((cmd) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return cmd.title.toLowerCase().includes(q) || (cmd.subtitle || "").toLowerCase().includes(q);
  });

  // Group into sections
  const sections = ["COMMANDS", "WORKSPACES"] as const;
  const grouped = sections
    .map((sec) => ({ label: sec, items: filtered.filter((c) => c.section === sec) }))
    .filter((g) => g.items.length > 0);

  const flatFiltered = grouped.flatMap((g) => g.items);

  useEffect(() => { setSelectedIdx(0); }, [query]);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, flatFiltered.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, 0)); }
    if (e.key === "Enter")     { e.preventDefault(); flatFiltered[selectedIdx]?.action(); }
    if (e.key === "Escape")    { onClose(); }
  };

  if (!isOpen) return null;

  let itemOffset = 0;

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 500, backdropFilter: "blur(4px)", display: "flex", alignItems: "flex-start", justifyContent: "center", paddingTop: "20vh" }}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        style={{ width: "min(560px, 90vw)", background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "16px", boxShadow: "var(--shadow-2xl)", overflow: "hidden" }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 16px", borderBottom: "1px solid var(--border-subtle)" }}>
          <span style={{ fontSize: "16px", flexShrink: 0 }}>🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Search sessions, run commands, switch workspace..."
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontFamily: "var(--font-body)", fontSize: "16px", color: "var(--text-primary)" }}
          />
          <span style={{ padding: "2px 6px", background: "var(--surface-sunken)", borderRadius: "4px", fontSize: "11px", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)", flexShrink: 0 }}>ESC</span>
        </div>

        {/* Results */}
        <div style={{ maxHeight: "320px", overflowY: "auto" }}>
          {grouped.length === 0 ? (
            <div style={{ padding: "40px 16px", textAlign: "center", fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-tertiary)" }}>
              <div style={{ fontSize: "32px", marginBottom: "8px" }}>🔍</div>
              No results for &ldquo;{query}&rdquo;
            </div>
          ) : (
            grouped.map((group) => {
              const startOffset = itemOffset;
              itemOffset += group.items.length;
              return (
                <div key={group.label}>
                  <div style={{ padding: "8px 16px 4px", fontFamily: "var(--font-body)", fontSize: "10px", fontWeight: 600, letterSpacing: "0.08em", color: "var(--text-tertiary)", textTransform: "uppercase" }}>
                    {group.label}
                  </div>
                  {group.items.map((item, i) => {
                    const globalIdx = startOffset + i;
                    const isSelected = globalIdx === selectedIdx;
                    return (
                      <button
                        key={item.id}
                        onClick={item.action}
                        onMouseEnter={() => setSelectedIdx(globalIdx)}
                        style={{
                          width: "100%", height: "44px", display: "flex", alignItems: "center", gap: "12px",
                          padding: "0 16px", background: isSelected ? "var(--surface-sunken)" : "transparent",
                          border: "none", borderLeft: isSelected ? "2px solid var(--brand)" : "2px solid transparent",
                          cursor: "pointer", textAlign: "left", transition: "background 80ms",
                        }}
                      >
                        <span style={{ fontSize: "18px", flexShrink: 0, lineHeight: 1 }}>{item.icon}</span>
                        <span style={{ flex: 1, minWidth: 0 }}>
                          <span style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-primary)", display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.title}</span>
                          {item.subtitle && <span style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)" }}>{item.subtitle}</span>}
                        </span>
                        {item.kbd && (
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)", background: "var(--surface-sunken)", padding: "2px 6px", borderRadius: "4px", flexShrink: 0 }}>{item.kbd}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
