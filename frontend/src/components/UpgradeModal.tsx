"use client";

import { useEffect, useRef, useState } from "react";
import type { UpgradeTrigger } from "@/lib/store/trialStore";
import {
  PRO_MONTHLY_PRICE,
  PRO_ANNUAL_MONTHLY_PRICE,
  PRO_ANNUAL_SAVINGS_PER_YEAR,
  PRO_ANNUAL_TOTAL_LABEL,
  fmtINR,
} from "@/lib/pricing";
import { apiFetch } from "@/lib/api";

interface UpgradeModalProps {
  trigger: UpgradeTrigger;
  onClose?: () => void;
}

export default function UpgradeModal({ trigger, onClose }: UpgradeModalProps) {
  const [billingCycle, setBillingCycle] = useState<"annual" | "monthly">("annual");
  const [upgrading, setUpgrading] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  // Per audit C3: never trap the user. Modal is always dismissable; quota-exhausted users fall back to read-only mode.
  const isDismissable = true;
  const isLimitReached = trigger === "limit_reached";

  // ESC key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  // Focus trap into modal on mount
  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  const handleSubscribe = async () => {
    setUpgrading(true);
    try {
      const res = await apiFetch("/billing/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

  // E4: pricing constants live in lib/pricing.ts. Identical numbers + wording
  // are rendered in /pricing, /billing, and the marketing page.
  const monthlyPrice = PRO_MONTHLY_PRICE;
  const annualMonthlyPrice = PRO_ANNUAL_MONTHLY_PRICE;
  const annualSavings = PRO_ANNUAL_SAVINGS_PER_YEAR;

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
      onClick={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
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
          {/* X button — always present (44px tap target). Quota-exhausted users still get a close affordance and fall back to read-only mode. */}
          <button
            onClick={onClose}
            aria-label="Close upgrade modal"
            style={{
              position: "absolute",
              top: "8px",
              right: "8px",
              width: "44px",
              height: "44px",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-secondary)",
              fontSize: "20px",
              lineHeight: 1,
              padding: "0",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--text-primary)"; (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)"; (e.currentTarget as HTMLElement).style.background = "none"; }}
          >
            ✕
          </button>

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
            {isLimitReached ? "Your free trial is complete" : "Upgrade DocuMindAI"}
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
            {isLimitReached
              ? "You can still read past chats. Upgrade to ask new questions."
              : "Unlock unlimited queries and all features."}
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
              border: "2px solid var(--brand, #0D0D0D)",
              borderRadius: "var(--radius-lg, 12px)",
              padding: "20px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: "0.1em", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                Professional Plan
              </span>
              <span style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>
                {fmtINR(billingCycle === "annual" ? annualMonthlyPrice : monthlyPrice)}
                <span style={{ fontSize: "13px", fontWeight: 400, color: "var(--text-secondary)" }}> / month</span>
              </span>
            </div>

            {billingCycle === "annual" && (
              <p style={{ fontSize: "11px", color: "var(--text-secondary)", margin: "0 0 12px" }}>
                {PRO_ANNUAL_TOTAL_LABEL}. Saves {fmtINR(annualSavings)}/year.
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
                    border: `1px solid ${billingCycle === cycle ? "var(--brand, #0D0D0D)" : "var(--border)"}`,
                    background: billingCycle === cycle ? "var(--brand-ghost, rgba(13,13,13,0.05))" : "transparent",
                    color: billingCycle === cycle ? "var(--brand, #0D0D0D)" : "var(--text-secondary)",
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
                "Unlimited documents (uploads up to 200 MB each)",
                "PDF, DOCX, Markdown export",
                "Session sharing + API access",
                "GST & Tax auto-updates",
              ].map((feature) => (
                <li key={feature} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--brand, #0D0D0D)", fontWeight: 600 }}>✓</span>
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
                background: "var(--brand, #0D0D0D)",
                color: "var(--brand-text, #fff)",
                border: "none",
                fontSize: "15px",
                fontWeight: 600,
                cursor: upgrading ? "not-allowed" : "pointer",
                opacity: upgrading ? 0.7 : 1,
                fontFamily: "var(--font-body)",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => { if (!upgrading) (e.currentTarget as HTMLElement).style.background = "var(--brand-dim, #2A2A2A)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--brand, #0D0D0D)"; }}
            >
              {upgrading ? "Activating…" : "Subscribe Now →"}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "16px 32px 28px", textAlign: "center" }}>
          <a
            href="mailto:support@documindai.com?subject=DocuMindAI%20support"
            style={{ fontSize: "13px", color: "var(--brand, #0D0D0D)", textDecoration: "underline" }}
          >
            Questions? Email support@documindai.com
          </a>
          <p style={{ fontSize: "11px", color: "var(--text-tertiary)", margin: "6px 0 0" }}>
            Cancel anytime. No lock-in.
          </p>
        </div>
      </div>
    </div>
  );
}
