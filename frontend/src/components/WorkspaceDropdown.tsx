"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";

interface Workspace {
  id: string;
  label: string;
  icon: string;
  route: string;
  badge?: string;
  description: string;
}

const WORKSPACES: Workspace[] = [
  { id: "general",  label: "General",      icon: "💬", route: "/general", description: "Chat with any document" },
  { id: "exam",     label: "Teacher",      icon: "📋", route: "/exam",    badge: "OCR",       description: "Generate question papers & assessments" },
  { id: "hr",       label: "HR",           icon: "👥", route: "/hr",      badge: "Batch",     description: "Resume analysis & candidate pipeline" },
  { id: "study",    label: "Student",      icon: "📚", route: "/study",   badge: "30+ PDFs",  description: "Personalized study & exam preparation" },
  { id: "research", label: "Research",     icon: "🔬", route: "/research", badge: "Citations", description: "Literature review & paper synthesis" },
  { id: "legal",    label: "Legal",        icon: "⚖️", route: "/legal",   badge: "Risk",      description: "Contract analysis & risk scoring" },
  { id: "finance",  label: "CA / Finance", icon: "📊", route: "/finance", badge: "Precision", description: "Financial documents & ratio analysis" },
];

// C7 — workspace identity dot color. Matches --ws-*-accent in tokens.css.
const WORKSPACE_DOT_COLORS: Record<string, string> = {
  general:  "var(--ws-general-accent)",
  exam:     "var(--ws-exam-accent)",
  hr:       "var(--ws-hr-accent)",
  study:    "var(--ws-study-accent)",
  research: "var(--ws-research-accent)",
  legal:    "var(--ws-legal-accent)",
  finance:  "var(--ws-finance-accent)",
};

function getActiveWorkspace(pathname: string): Workspace {
  // Match longest prefix first
  const sorted = [...WORKSPACES].sort((a, b) => b.route.length - a.route.length);
  return sorted.find((w) => pathname === w.route || pathname.startsWith(w.route + "/")) || WORKSPACES[0];
}

interface WorkspaceDropdownProps {
  onWorkspaceChange?: (workspaceId: string) => void;
}

export default function WorkspaceDropdown({ onWorkspaceChange }: WorkspaceDropdownProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIdx, setFocusedIdx] = useState(-1);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const active = getActiveWorkspace(pathname);

  const close = useCallback(() => {
    setIsOpen(false);
    setFocusedIdx(-1);
  }, []);

  const open = useCallback(() => {
    setIsOpen(true);
    setFocusedIdx(WORKSPACES.findIndex((w) => w.id === active.id));
  }, [active.id]);

  const selectWorkspace = useCallback(
    (ws: Workspace) => {
      close();
      router.push(ws.route);
      onWorkspaceChange?.(ws.id);
    },
    [close, router, onWorkspaceChange]
  );

  // Close on outside mousedown
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (
        triggerRef.current?.contains(e.target as Node) ||
        dropdownRef.current?.contains(e.target as Node)
      )
        return;
      close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen, close]);

  // Keyboard nav
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        open();
      }
      return;
    }
    if (e.key === "Escape") { close(); triggerRef.current?.focus(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); setFocusedIdx((i) => (i + 1) % WORKSPACES.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setFocusedIdx((i) => (i - 1 + WORKSPACES.length) % WORKSPACES.length); }
    else if (e.key === "Enter" && focusedIdx >= 0) { selectWorkspace(WORKSPACES[focusedIdx]); }
  };

  return (
    <div className="relative flex justify-center" onKeyDown={handleKeyDown}>
      {/* Trigger */}
      <button
        ref={triggerRef}
        id="workspace-dropdown-trigger"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => (isOpen ? close() : open())}
        style={{
          background: "var(--surface-sunken)",
          border: `1px solid ${isOpen ? "var(--brand)" : "var(--border-default)"}`,
          borderRadius: "var(--radius-md)",
          padding: "8px 12px",
          height: "36px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          cursor: "pointer",
          transition: "all var(--dur-fast) var(--ease-standard)",
          minWidth: "180px",
          maxWidth: "280px",
          fontFamily: "var(--font-body)",
          fontSize: "var(--text-sm)",
          fontWeight: "var(--weight-medium)",
          color: "var(--text-primary)",
        }}
      >
        {/* C7 — workspace identity dot (NOT a UI wash) */}
        <span
          aria-hidden="true"
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: WORKSPACE_DOT_COLORS[active.id] || "var(--ws-general-accent)",
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: "16px", lineHeight: 1 }}>{active.icon}</span>
        <span style={{ flex: 1, textAlign: "left", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {active.label}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          style={{
            flexShrink: 0,
            color: "var(--text-tertiary)",
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform var(--dur-fast) var(--ease-standard)",
          }}
        >
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          ref={dropdownRef}
          role="listbox"
          aria-label="Switch Workspace"
          className="dropdown-enter"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: "50%",
            transform: "translateX(-50%)",
            background: "var(--surface-overlay)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-xl)",
            minWidth: "280px",
            padding: "8px",
            zIndex: 200,
          }}
        >
          {/* Panel header */}
          <div
            style={{
              padding: "8px 12px 4px",
              fontFamily: "var(--font-body)",
              fontSize: "11px",
              fontWeight: "var(--weight-medium)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
            }}
          >
            Switch Workspace
          </div>

          {/* Workspace list */}
          {WORKSPACES.map((ws, idx) => {
            const isActive = ws.id === active.id;
            const isFocused = idx === focusedIdx;
            return (
              <div
                key={ws.id}
                role="option"
                aria-selected={isActive}
                id={`workspace-option-${ws.id}`}
                onClick={() => selectWorkspace(ws)}
                onMouseEnter={() => setFocusedIdx(idx)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-md)",
                  cursor: "pointer",
                  height: "44px",
                  background: isActive
                    ? "var(--brand-ghost)"
                    : isFocused
                    ? "var(--surface-hover)"
                    : "transparent",
                  borderLeft: isActive ? "2px solid var(--brand)" : "2px solid transparent",
                  transition: "background var(--dur-fast) var(--ease-standard)",
                }}
              >
                <span style={{ fontSize: "20px", lineHeight: 1, flexShrink: 0 }}>{ws.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "var(--text-sm)",
                      fontWeight: "var(--weight-medium)",
                      color: "var(--text-primary)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {ws.label}
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "var(--text-xs)",
                      color: "var(--text-secondary)",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {ws.description}
                  </div>
                </div>
                {ws.badge && (
                  <span
                    style={{
                      flexShrink: 0,
                      background: "var(--brand-ghost)",
                      color: "var(--text-brand)",
                      border: "1px solid var(--brand-glow)",
                      borderRadius: "var(--radius-full)",
                      fontSize: "var(--text-2xs)",
                      fontWeight: "var(--weight-medium)",
                      padding: "2px 8px",
                      fontFamily: "var(--font-body)",
                    }}
                  >
                    {ws.badge}
                  </span>
                )}
                {isFocused && !isActive && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0, color: "var(--text-tertiary)" }}>
                    <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
            );
          })}

          {/* Divider */}
          <div style={{ height: "1px", background: "var(--border-subtle)", margin: "4px 0" }} />

          {/* Footer */}
          <div
            style={{
              padding: "8px 12px",
              fontFamily: "var(--font-body)",
              fontSize: "var(--text-xs)",
              color: "var(--text-tertiary)",
            }}
          >
            More workspaces coming soon
          </div>
        </div>
      )}
    </div>
  );
}
