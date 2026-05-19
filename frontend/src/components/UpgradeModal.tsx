"use client";

import { useEffect, useRef, useState } from "react";
import type { UpgradeTrigger } from "@/lib/store/trialStore";

interface UpgradeModalProps {
  trigger: UpgradeTrigger;
  onClose?: () => void;
}

const TRIAL_LIMIT = 5;

export default function UpgradeModal({ trigger, onClose }: UpgradeModalProps) {
  const [billingCycle, setBillingCycle] = useState<"annual" | "monthly">("annual");
  const [upgrading, setUpgrading] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  const isDismissable = trigger !== "limit_reached";

  // ESC key — only when dismissable
  useEffect(() => {
    if (!isDismissable) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isDismissable, onClose]);

  // Focus trap into modal on mount
  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  const handleSubscribe = async () => {
    setUpgrading(true);
    try {
      const { API_BASE, getCsrfToken } = await import("@/lib/api");
      const res = await fetch(`${API_BASE}/billing/upgrade`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify({ plan: "professional", billing_cycle: billingCycle }),
      });
      if (res.ok) {
        window.location.reload();
      }
    } catch {
      // silently ignore — let user retry
    } finally {
      setUpgrading(false);
    }
  };

  const monthlyPrice = 999;
  const annualMonthlyPrice = 799;
  const annualSavings = (monthlyPrice - annualMonthlyPrice) * 12;

  return (
    /* Backdrop */
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-modal-title"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
      onClick={isDismissable ? (e) => { if (e.target === e.currentTarget) onClose?.(); } : undefined}
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        style={{
          background: "var(--surface-base)",
          borderRadius: "var(--radius-xl, 16px)",
          boxShadow: "var(--shadow-2xl, 0 25px 50px rgba(0,0,0,0.4))",
          maxWidth: "480px",
          width: "100%",
          outline: "none",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div style={{ padding: "32px 32px 0", textAlign: "center", position: "relative" }}>
          {/* X button — only for dismissable triggers */}
          {isDismissable && (
            <button
              onClick={onClose}
              aria-label="Close upgrade modal"
              style={{
                position: "absolute",
                top: "16px",
                right: "16px",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--text-secondary)",
                fontSize: "20px",
                lineHeight: 1,
                padding: "4px",
                borderRadius: "var(--radius-sm)",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--text-primary)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)"; }}
            >
              ✕
            </button>
          )}

          {/* Logomark */}
          <div style={{ fontSize: "32px", marginBottom: "12px" }}>✦</div>

          <h2
            id="upgrade-modal-title"
            style={{
              fontFamily: "Georgia, 'Instrument Serif', serif",
              fontSize: "24px",
              fontWeight: 600,
              color: "var(--text-primary)",
              margin: "0 0 8px",
            }}
          >
            Your free trial is complete
          </h2>
          <p
            style={{
              fontSize: "13px",
              color: "var(--text-secondary)",
              maxWidth: "360px",
              margin: "0 auto",
              lineHeight: 1.5,
            }}
          >
            You've experienced DocuMindAI fully. Ready to unlock unlimited access?
          </p>
        </div>

        {/* What you got */}
        <div style={{ padding: "20px 32px 0" }}>
          <div
            style={{
              background: "hsl(40, 90%, 95%)",
              color: "hsl(40, 70%, 30%)",
              borderRadius: "var(--radius-md, 8px)",
              padding: "10px 16px",
              fontSize: "12px",
              fontWeight: 500,
              textAlign: "center",
            }}
          >
            ✓ All 7 workspaces · All features · Export · Preview · Citations
          </div>
        </div>

        {/* Plan card */}
        <div style={{ padding: "20px 32px 0" }}>
          <div
            style={{
              border: "2px solid var(--brand, hsl(220,90%,60%))",
              borderRadius: "var(--radius-lg, 12px)",
              padding: "20px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.1em", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Professional Plan
              </span>
              <span style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>
                ₹{billingCycle === "annual" ? annualMonthlyPrice : monthlyPrice}
                <span style={{ fontSize: "13px", fontWeight: 400, color: "var(--text-secondary)" }}> / month</span>
              </span>
            </div>

            {billingCycle === "annual" && (
              <p style={{ fontSize: "11px", color: "var(--text-secondary)", margin: "0 0 12px" }}>
                Billed annually — saves ₹{annualSavings.toLocaleString("en-IN")}/year
              </p>
            )}

            {/* Billing cycle toggle */}
            <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
              {(["annual", "monthly"] as const).map((cycle) => (
                <button
                  key={cycle}
                  onClick={() => setBillingCycle(cycle)}
                  style={{
                    flex: 1,
                    padding: "6px 12px",
                    borderRadius: "var(--radius-sm, 6px)",
                    border: `1px solid ${billingCycle === cycle ? "var(--brand, hsl(220,90%,60%))" : "var(--border)"}`,
                    background: billingCycle === cycle ? "var(--brand-ghost, hsl(220,90%,95%))" : "transparent",
                    color: billingCycle === cycle ? "var(--brand, hsl(220,90%,60%))" : "var(--text-secondary)",
                    fontSize: "13px",
                    fontWeight: billingCycle === cycle ? 600 : 400,
                    cursor: "pointer",
                    fontFamily: "var(--font-body)",
                  }}
                >
                  {cycle === "annual" ? "Annual — Best Value ✓" : "Monthly"}
                </button>
              ))}
            </div>

            <div style={{ height: "1px", background: "var(--border-subtle, #e5e7eb)", marginBottom: "16px" }} />

            {/* Features */}
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 16px", display: "flex", flexDirection: "column", gap: "8px" }}>
              {[
                "Unlimited queries",
                "All 7 workspaces",
                "Unlimited documents (50MB each)",
                "PDF, DOCX, Markdown export",
                "Session sharing + API access",
                "GST & Tax auto-updates",
              ].map((feature) => (
                <li key={feature} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--brand, hsl(220,90%,60%))", fontWeight: 600 }}>✓</span>
                  {feature}
                </li>
              ))}
            </ul>

            <button
              onClick={handleSubscribe}
              disabled={upgrading}
              style={{
                width: "100%",
                height: "44px",
                borderRadius: "var(--radius-md, 8px)",
                background: "var(--brand, hsl(220,90%,60%))",
                color: "#fff",
                border: "none",
                fontSize: "15px",
                fontWeight: 600,
                cursor: upgrading ? "not-allowed" : "pointer",
                opacity: upgrading ? 0.7 : 1,
                fontFamily: "var(--font-body)",
                transition: "filter 0.15s",
              }}
              onMouseEnter={(e) => { if (!upgrading) (e.currentTarget as HTMLElement).style.filter = "brightness(1.08)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.filter = "none"; }}
            >
              {upgrading ? "Activating…" : "Subscribe Now →"}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "16px 32px 28px", textAlign: "center" }}>
          <a
            href="mailto:support@documindai.com"
            style={{ fontSize: "13px", color: "var(--brand, hsl(220,90%,60%))", textDecoration: "none" }}
          >
            Questions? Chat with us →
          </a>
          <p style={{ fontSize: "11px", color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Cancel anytime. No lock-in.
          </p>
        </div>
      </div>
    </div>
  );
}
