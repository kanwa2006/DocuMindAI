"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Sidebar from "./Sidebar";
import WorkspaceDropdown from "./WorkspaceDropdown";
import { Logo, LogoMark } from "./Logo";
import { useTheme } from "@/hooks/useTheme";
import { logout } from "@/lib/api";
import { useOnboarding } from "@/hooks/useOnboarding";
import OnboardingTooltip from "./OnboardingTooltip";
import { TrialProvider, useTrialStore } from "@/lib/store/trialStore";
import TrialPill from "./TrialPill";
import UpgradeModal from "./UpgradeModal";
import CommandPalette from "./CommandPalette";
import NotificationCenter from "./NotificationCenter";
import AutosaveIndicator from "./AutosaveIndicator";
import KeyboardShortcutsModal from "./KeyboardShortcutsModal";
import ShareSessionModal from "./ShareSessionModal";
import { toast } from "react-hot-toast";

// ─── Profile Dropdown ─────────────────────────────────────────────────────────

function ProfileDropdown({ user, onClose }: { user: { name: string; email: string; initials: string; workspace: string }; onClose: () => void }) {
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    const escHandler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", escHandler);
    return () => { document.removeEventListener("mousedown", handler); document.removeEventListener("keydown", escHandler); };
  }, [onClose]);

  const handleLogout = async () => {
    try { await logout(); } catch {}
    router.push("/login");
    onClose();
  };

  const itemStyle: React.CSSProperties = {
    display: "flex", alignItems: "center", gap: "8px",
    padding: "8px 12px", borderRadius: "var(--radius-md)",
    fontFamily: "var(--font-body)", fontSize: "var(--text-sm)",
    color: "var(--text-secondary)", cursor: "pointer", height: "36px",
    background: "none", border: "none", width: "100%", textAlign: "left",
    transition: "background var(--dur-fast) var(--ease-standard), color var(--dur-fast) var(--ease-standard)",
  };

  return (
    <div
      ref={ref}
      className="dropdown-enter"
      style={{
        position: "absolute", top: "calc(100% + 6px)", right: 0,
        background: "var(--surface-overlay)", border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-xl)",
        minWidth: "220px", padding: "8px", zIndex: 200,
      }}
    >
      {/* User info section */}
      <div style={{ padding: "12px 8px", pointerEvents: "none" }}>
        <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)" }}>{user.name}</div>
        <div style={{ fontFamily: "var(--font-body)", fontSize: "var(--text-xs)", color: "var(--text-secondary)", marginTop: "2px" }}>{user.email}</div>
        <div style={{ marginTop: "6px" }}>
          <span style={{ background: "var(--brand-ghost)", color: "var(--text-brand)", border: "1px solid var(--brand-glow)", borderRadius: "var(--radius-full)", fontSize: "var(--text-2xs)", fontWeight: "var(--weight-medium)", padding: "2px 8px", fontFamily: "var(--font-body)" }}>
            {user.workspace}
          </span>
        </div>
      </div>
      <div style={{ height: "1px", background: "var(--border-subtle)", margin: "4px 0" }} />
      {[
        { icon: "⚙️", label: "Settings", href: "/settings" },
        { icon: "📊", label: "Usage Dashboard", href: "/dashboard" },
        { icon: "💳", label: "Billing", href: "/billing" },
      ].map(({ icon, label, href }) => (
        <button key={href} onClick={() => { router.push(href); onClose(); }} style={itemStyle}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)"; (e.currentTarget as HTMLElement).style.color = "var(--text-primary)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)"; }}>
          <span>{icon}</span>{label}
        </button>
      ))}
      <div style={{ height: "1px", background: "var(--border-subtle)", margin: "4px 0" }} />
      <button onClick={handleLogout} style={{ ...itemStyle, color: "#ef4444" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--error-bg)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "none"; }}>
        <span>🚪</span> Log Out
      </button>
    </div>
  );
}

// ─── Theme icon ───────────────────────────────────────────────────────────────

function ThemeIcon({ theme }: { theme: string }) {
  if (theme === "dark") return <span style={{ fontSize: "16px" }} aria-hidden="true">☀️</span>;
  if (theme === "light") return <span style={{ fontSize: "16px" }} aria-hidden="true">🌙</span>;
  return <span style={{ fontSize: "16px" }} aria-hidden="true">💻</span>;
}

// ─── LayoutWrapper ────────────────────────────────────────────────────────────

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  return (
    <TrialProvider>
      <LayoutWrapperInner>{children}</LayoutWrapperInner>
    </TrialProvider>
  );
}

function LayoutWrapperInner({ children }: { children: React.ReactNode }) {
  const { plan, queriesUsed, queriesRemaining, trialLimit, showUpgradeModal, upgradeTrigger, openUpgradeModal, closeUpgradeModal, setTrialStatus } = useTrialStore();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showProfile, setShowProfile] = useState(false);
  const [currentWorkspace, setCurrentWorkspace] = useState("general");
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const { currentStep, isComplete, advance, dismiss } = useOnboarding();

  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme, setTheme } = useTheme();

  // Restore sidebar state from localStorage on mount + load billing status
  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem("sidebar_open");
    if (saved !== null) setIsSidebarOpen(saved === "true");

    // Restore last workspace if landing on root without chat
    if (pathname === "/" && !searchParams.get("chat")) {
      const lastWorkspace = localStorage.getItem("lastActiveWorkspace");
      if (lastWorkspace === "/" || lastWorkspace === "") {
        // Migrate old sessions that stored "/" for general workspace
        router.replace("/general");
      } else if (lastWorkspace) {
        router.replace(lastWorkspace);
      }
    }

    // Load billing status to initialise trial counter (backend is authoritative source)
    import("@/lib/api").then(({ getBillingStatus }) => {
      getBillingStatus().then((status) => {
        if (status.plan === "trial" && typeof status.trial_queries_used === "number") {
          setTrialStatus(
            status.trial_queries_used,
            status.queries_remaining ?? 0,
            status.trial_limit,
          );
        }
      }).catch(() => {});
    });
  }, []);

  // Listen for trial:exhausted (fired by api.ts on HTTP 402)
  useEffect(() => {
    const handler = () => openUpgradeModal("limit_reached");
    window.addEventListener("trial:exhausted", handler);
    return () => window.removeEventListener("trial:exhausted", handler);
  }, [openUpgradeModal]);

  const toggleTheme = useCallback(() => {
    setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark");
  }, [theme, setTheme]);

  // Cmd+D keyboard shortcut for theme toggle (Phase 2 spec)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "d") {
        e.preventDefault();
        toggleTheme();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleTheme]);

  // Phase 14.1 — Cmd+K: command palette
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setShowCommandPalette((v) => !v);
      }
      // Cmd/Ctrl + B — toggle sidebar (added by audit pass)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setIsSidebarOpen((o) => {
          const next = !o;
          try { localStorage.setItem("sidebar_open", String(next)); } catch {}
          return next;
        });
      }
      // "?" opens keyboard shortcuts when textarea is not focused
      if (e.key === "?" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        setShowKeyboardShortcuts((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Persist sidebar state across reloads.
  useEffect(() => {
    try { localStorage.setItem("sidebar_open", String(isSidebarOpen)); } catch {}
  }, [isSidebarOpen]);

  // Phase 14.1 — handle commands from command palette
  useEffect(() => {
    const onToggleTheme = () => toggleTheme();
    const onShortcuts = () => setShowKeyboardShortcuts(true);
    window.addEventListener("cmd:toggle-theme", onToggleTheme);
    window.addEventListener("cmd:shortcuts", onShortcuts);
    return () => {
      window.removeEventListener("cmd:toggle-theme", onToggleTheme);
      window.removeEventListener("cmd:shortcuts", onShortcuts);
    };
  }, [toggleTheme]);

  const activeSessionId = searchParams.get("chat") ?? "";

  const handleShare = () => {
    if (activeSessionId) {
      setShowShareModal(true);
      return;
    }
    if (typeof navigator === "undefined" || !navigator.clipboard) {
      toast.error("Clipboard is not available in this browser.");
      return;
    }
    navigator.clipboard
      .writeText(window.location.href)
      .then(() => toast.success("Link copied!"))
      .catch(() => toast.error("Couldn't copy link."));
  };

  const handleWorkspaceChange = (wsId: string) => {
    setCurrentWorkspace(wsId);
    // C7 — workspace identity is a small dot/monogram, not a UI wash.
    // The previous global `--brand-hue` swap is removed; per-workspace accents
    // are exposed via --ws-*-accent for components that opt in.
    localStorage.setItem("lastActiveWorkspace", `/${wsId}`);
  };

  const isAuthPage = ["/login", "/register", "/forgot-password", "/reset-password"].includes(pathname);
  const isMarketingPage = ["/", "/pricing", "/privacy", "/terms"].includes(pathname);
  const isSharedPage = pathname.startsWith("/shared/");

  if (isAuthPage) {
    return <div className="h-screen bg-[var(--surface-base)]">{children}</div>;
  }

  if (isMarketingPage || isSharedPage) {
    return <>{children}</>;
  }

  // Mock user — replace with real auth context when available
  const user = { name: "DocuMind User", email: "user@documind.ai", initials: "DU", workspace: currentWorkspace };

  return (
    <div style={{ display: "flex", height: "100dvh", overflow: "hidden", background: "var(--surface-base)", color: "var(--text-primary)" }}>
      {/* Sidebar */}
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* ── NAVBAR ── */}
        <header
          className="navbar"
          style={{ position: "sticky", top: 0 }}
        >
          {/* LEFT ZONE */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {/* Logo */}
            <Link
              href="/"
              id="navbar-logo"
              style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", textDecoration: "none", opacity: 1, transition: "opacity var(--dur-fast) var(--ease-standard)" }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.8")}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
              aria-label="DocuMindAI home"
            >
              <LogoMark size={24} />
              <Logo size="sm" />
            </Link>

            {/* Sidebar toggle */}
            <button
              id="sidebar-toggle"
              onClick={() => setIsSidebarOpen((o) => !o)}
              className="btn-icon btn-ghost interactive"
              aria-label="Toggle sidebar"
              aria-expanded={isSidebarOpen}
              title="Toggle sidebar (Ctrl+B)"
              style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: "18px" }}
            >
              {isSidebarOpen ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              )}
            </button>
          </div>

          {/* CENTER ZONE */}
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "12px" }}>
            <WorkspaceDropdown onWorkspaceChange={handleWorkspaceChange} />
            <AutosaveIndicator />
          </div>

          {/* RIGHT ZONE */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {/* Share button */}
            <button
              id="navbar-share"
              onClick={handleShare}
              className="btn-icon btn-ghost interactive"
              aria-label="Copy share link"
              title="Share current session"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8" /><polyline points="16 6 12 2 8 6" /><line x1="12" y1="2" x2="12" y2="15" />
              </svg>
            </button>

            {/* Trial pill — visible only on free trial */}
            {plan === "trial" && (
              <TrialPill
                queriesUsed={queriesUsed}
                queriesRemaining={queriesRemaining}
                trialLimit={trialLimit ?? undefined}
                onClick={() => openUpgradeModal("user_click")}
              />
            )}

            {/* Notification center bell (Phase 14.7) */}
            <NotificationCenter />

            {/* Dark/Light toggle */}
            <button
              id="navbar-theme-toggle"
              onClick={toggleTheme}
              className="btn-icon btn-ghost interactive"
              aria-label={theme === "dark" ? "Switch to light mode" : theme === "light" ? "Switch to system mode" : "Switch to dark mode"}
              title={theme === "dark" ? "Switch to light mode" : theme === "light" ? "Switch to system" : "Switch to dark mode"}
            >
              <ThemeIcon theme={theme} />
            </button>

            {/* Profile avatar */}
            <div ref={profileRef} style={{ position: "relative" }}>
              <button
                id="navbar-profile"
                onClick={() => setShowProfile((p) => !p)}
                style={{
                  width: "32px", height: "32px", borderRadius: "50%",
                  background: "var(--brand)", color: "#fff",
                  border: "none", cursor: "pointer", fontFamily: "var(--font-body)",
                  fontSize: "var(--text-xs)", fontWeight: "var(--weight-semibold)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "filter var(--dur-fast) var(--ease-standard)",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.filter = "brightness(1.1)")}
                onMouseLeave={(e) => (e.currentTarget.style.filter = "")}
                title="Profile"
                aria-haspopup="true"
                aria-expanded={showProfile}
              >
                {user.initials}
              </button>

              {showProfile && (
                <ProfileDropdown user={user} onClose={() => setShowProfile(false)} />
              )}
            </div>
          </div>
        </header>

        {/* PAGE CONTENT */}
        <main id="main" role="main" style={{ flex: 1, overflow: "auto" }}>
          {children}
        </main>
      </div>

      {/* Onboarding tooltip overlay (Steps 1-3) */}
      {!isComplete && currentStep >= 1 && currentStep <= 3 && (
        <OnboardingTooltip
          step={currentStep as 1 | 2 | 3}
          targetSelector={
            currentStep === 1 ? "#workspace-dropdown" :
            currentStep === 2 ? "#upload-trigger" :
            "#chat-textarea"
          }
          onNext={advance}
          onDismiss={dismiss}
        />
      )}

      {/* Upgrade modal — shown after trial exhaustion or user click. Always dismissable: user falls back to read-only mode if quota is exhausted. */}
      {showUpgradeModal && (
        <UpgradeModal
          trigger={upgradeTrigger}
          onClose={closeUpgradeModal}
        />
      )}

      {/* Phase 14.1 — Command palette */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
      />

      {/* Phase 14.8 — Keyboard shortcuts modal */}
      <KeyboardShortcutsModal
        isOpen={showKeyboardShortcuts}
        onClose={() => setShowKeyboardShortcuts(false)}
      />

      {/* Phase 22 — Share session modal */}
      {showShareModal && activeSessionId && (
        <ShareSessionModal
          sessionId={activeSessionId}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
}

// Workspace hue map — kept for reference; the dot/monogram in WorkspaceDropdown
// renders each workspace's accent. No longer mutates --brand-hue (C7).
export const WORKSPACE_HUES: Record<string, string> = {
  general:  "220",
  exam:     "262",
  hr:       "198",
  study:    "160",
  research: "0",
  legal:    "221",
  finance:  "174",
};
