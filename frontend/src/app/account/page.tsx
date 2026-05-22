"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch, logout, getBillingStatus } from "@/lib/api";
import type { BillingStatus } from "@/lib/api";
import toast from "react-hot-toast";

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  preferred_language: string;
}

const PLAN_LABELS: Record<string, string> = {
  trial: "Free Trial",
  professional: "Professional",
  business: "Business",
  enterprise: "Enterprise",
};

export default function AccountPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    apiFetch("/users/me")
      .then((r) => {
        if (r.status === 401) { router.push("/login"); return null; }
        return r.json();
      })
      .then((data: UserProfile | null) => { if (data) setProfile(data); })
      .catch(() => setError("Failed to load profile."));

    getBillingStatus().then(setBilling).catch(() => {});
  }, [router]);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      window.location.href = "/login";
    } catch (e: any) {
      toast.error(e?.message || "Logout failed");
      setLoggingOut(false);
    }
  };

  const cardStyle: React.CSSProperties = {
    background: "var(--surface-raised)",
    border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-xl)",
    padding: "24px",
    marginBottom: "16px",
  };

  const rowStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "180px 1fr",
    gap: "12px",
    padding: "12px 0",
    borderBottom: "1px solid var(--border-subtle)",
    alignItems: "center",
  };

  const dtStyle: React.CSSProperties = {
    fontSize: "var(--text-sm)",
    color: "var(--text-secondary)",
    fontFamily: "var(--font-body)",
    fontWeight: "var(--weight-medium)",
  };

  const ddStyle: React.CSSProperties = {
    fontSize: "var(--text-sm)",
    color: "var(--text-primary)",
    fontFamily: "var(--font-body)",
  };

  return (
    <div style={{ maxWidth: "640px", margin: "48px auto", padding: "0 24px", fontFamily: "var(--font-body)" }}>
      <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", color: "var(--text-primary)", marginBottom: "8px" }}>
        Account
      </h1>
      <p style={{ fontSize: "var(--text-sm)", color: "var(--text-secondary)", marginBottom: "32px" }}>
        Your profile, plan, and language.
      </p>

      {error && (
        <div style={{ ...cardStyle, color: "var(--error-text, #dc2626)", border: "1px solid var(--error-border, rgba(239,68,68,0.3))" }}>
          {error}
        </div>
      )}

      {/* Profile */}
      <div style={cardStyle}>
        <div style={{ fontSize: "var(--text-xs)", fontWeight: "var(--weight-semibold)", color: "var(--text-tertiary)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
          Profile
        </div>
        <div style={rowStyle}>
          <span style={dtStyle}>Name</span>
          <span style={ddStyle}>{profile?.full_name || <em style={{ color: "var(--text-tertiary)" }}>Not set</em>}</span>
        </div>
        <div style={rowStyle}>
          <span style={dtStyle}>Email</span>
          <span style={ddStyle}>{profile?.email || "—"}</span>
        </div>
        <div style={{ ...rowStyle, borderBottom: "none" }}>
          <span style={dtStyle}>AI response language</span>
          <span style={ddStyle}>
            {profile?.preferred_language === "auto" ? "Auto-detect" : (profile?.preferred_language ?? "Auto-detect")}
            <Link href="/settings" style={{ marginLeft: "8px", fontSize: "12px", color: "var(--accent, var(--brand))" }}>
              Change →
            </Link>
          </span>
        </div>
      </div>

      {/* Plan */}
      <div style={cardStyle}>
        <div style={{ fontSize: "var(--text-xs)", fontWeight: "var(--weight-semibold)", color: "var(--text-tertiary)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "8px" }}>
          Plan
        </div>
        <div style={rowStyle}>
          <span style={dtStyle}>Current plan</span>
          <span style={ddStyle}>{billing ? (PLAN_LABELS[billing.plan] ?? billing.plan) : "—"}</span>
        </div>
        {billing && billing.plan === "trial" && (
          <div style={rowStyle}>
            <span style={dtStyle}>Trial usage</span>
            <span style={ddStyle}>{billing.trial_queries_used} / {billing.trial_limit} queries used</span>
          </div>
        )}
        <div style={{ ...rowStyle, borderBottom: "none" }}>
          <span style={dtStyle}>Billing</span>
          <Link href="/billing" style={{ fontSize: "13px", color: "var(--accent, var(--brand))" }}>
            Manage billing →
          </Link>
        </div>
      </div>

      {/* Session */}
      <div style={cardStyle}>
        <div style={{ fontSize: "var(--text-xs)", fontWeight: "var(--weight-semibold)", color: "var(--text-tertiary)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "16px" }}>
          Session
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="btn btn-secondary"
          style={{ height: "40px", minWidth: "120px" }}
        >
          {loggingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>
    </div>
  );
}
