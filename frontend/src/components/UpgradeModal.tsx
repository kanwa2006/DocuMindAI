"use client";

import { useEffect, useRef, useState } from "react";
import type { UpgradeTrigger } from "@/lib/store/trialStore";
import { PLANS, fmtINR, type PlanId } from "@/lib/pricing";
import { apiFetch } from "@/lib/api";

interface UpgradeModalProps {
  trigger: UpgradeTrigger;
  onClose?: () => void;
}

export default function UpgradeModal({ trigger, onClose }: UpgradeModalProps) {
  // W1: three simple monthly tiers — Go / Plus / Pro. Default-select the
  // featured plan (Plus). No annual/monthly cycle toggle anymore.
  const featured = PLANS.find((p) => p.featured) ?? PLANS[0];
  const [selected, setSelected] = useState<PlanId>(featured.id);
  const [upgrading, setUpgrading] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  const isLimitReached = trigger === "limit_reached";
  const selectedPlan = PLANS.find((p) => p.id === selected) ?? featured;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  const handleSubscribe = async () => {
    setUpgrading(true);
    try {
      const res = await apiFetch("/billing/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: selected, billing_cycle: "monthly" }),
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
              fontFamily: "var(--font-display, var(--font-body))",
              fontSize: "22px",
              fontWeight: 600,
              color: "var(--text-primary)",
              margin: "0 0 6px",
            }}
          >
            {isLimitReached ? "Your free trial is complete" : "Upgrade your plan"}
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
              ? "You can still read past chats. Pick a plan to keep asking."
              : "Pick the plan that fits how you work."}
          </p>
        </div>

        {/* Plan selector */}
        <div style={{ padding: "20px 32px 0" }}>
          <div style={{ display: "grid", gridTemplateColumns: `repeat(${PLANS.length}, 1fr)`, gap: "8px", marginBottom: "16px" }}>
            {PLANS.map((p) => {
              const isSelected = selected === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => setSelected(p.id)}
                  aria-pressed={isSelected}
                  style={{
                    padding: "12px 8px",
                    borderRadius: "10px",
                    border: `1.5px solid ${isSelected ? "var(--brand, #0D0D0D)" : "var(--border)"}`,
                    background: isSelected ? "var(--brand-ghost, rgba(13,13,13,0.05))" : "var(--surface-base)",
                    cursor: "pointer",
                    textAlign: "center",
                    fontFamily: "var(--font-body)",
                    transition: "border-color 120ms, background 120ms",
                  }}
                >
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>{p.name}</div>
                  <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                    {fmtINR(p.price)}
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--text-tertiary)" }}>/month</div>
                </button>
              );
            })}
          </div>

          {/* Features for the selected plan */}
          <div
            style={{
              padding: "16px 18px",
              borderRadius: "var(--radius-lg, 12px)",
              background: "var(--surface-raised)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "10px" }}>
              {selectedPlan.tagline}
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
              {selectedPlan.features.map((feature) => (
                <li key={feature} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--brand, #0D0D0D)", fontWeight: 600 }}>✓</span>
                  {feature}
                </li>
              ))}
            </ul>
          </div>

          <button
            onClick={handleSubscribe}
            disabled={upgrading}
            style={{
              width: "100%",
              height: "44px",
              marginTop: "16px",
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
            {upgrading ? "Activating…" : `Upgrade to ${selectedPlan.name} → ${fmtINR(selectedPlan.price)}/mo`}
          </button>
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
