"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBillingStatus, upgradePlan, type BillingStatus } from "@/lib/api";
import { PLANS, fmtINR, type PlanId } from "@/lib/pricing";
import toast from "react-hot-toast";

// Friendly label for whatever DB value comes back from /billing/status.
// Old subscriptions (DB value "professional" / "enterprise") map to the
// new Go/Plus/Pro vocabulary so the UI never shows the legacy names.
const PLAN_LABEL: Record<string, string> = {
  trial: "Free",
  go: "Go",
  plus: "Plus",
  pro: "Pro",
  professional: "Plus",
  business: "Plus",
  enterprise: "Pro",
};

export default function BillingPage() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgrading, setUpgrading] = useState<PlanId | null>(null);

  useEffect(() => {
    getBillingStatus()
      .then((s) => setStatus(s))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load billing"))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpgrade(planId: PlanId) {
    setUpgrading(planId);
    try {
      await upgradePlan(planId, "monthly");
      toast.success(`You're now on ${PLANS.find((p) => p.id === planId)?.name}.`);
      const refreshed = await getBillingStatus();
      setStatus(refreshed);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Upgrade failed");
    } finally {
      setUpgrading(null);
    }
  }

  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: "2.5rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.85rem", fontWeight: 600, marginBottom: "0.25rem" }}>Billing</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "1.75rem" }}>
        Your plan and upgrades.
      </p>

      {loading && <p style={{ color: "var(--text-tertiary)" }}>Loading…</p>}
      {error && <p style={{ color: "var(--accent-danger, #b91c1c)" }}>{error}</p>}

      {status && (
        <>
          <section
            style={{
              padding: "1.25rem",
              border: "1px solid var(--border)",
              borderRadius: 12,
              marginBottom: "2rem",
              background: "var(--surface)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <strong>Current plan</strong>
              <span>{PLAN_LABEL[status.plan] ?? status.plan}</span>
            </div>
            {status.plan === "trial" && (
              <div style={{ color: "var(--text-secondary)" }}>
                {status.trial_queries_used} of {status.trial_limit} free queries used
                {status.queries_remaining !== null && (
                  <> · {status.queries_remaining} remaining</>
                )}
              </div>
            )}
            {status.subscribed_at && (
              <div style={{ color: "var(--text-secondary)" }}>
                Subscribed {new Date(status.subscribed_at).toLocaleDateString()}
                {status.subscription_ends_at && (
                  <> · renews {new Date(status.subscription_ends_at).toLocaleDateString()}</>
                )}
              </div>
            )}
          </section>

          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "0.75rem" }}>Upgrade</h2>
          <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            {PLANS.map((p) => (
              <div
                key={p.id}
                style={{
                  padding: "1.25rem",
                  border: p.featured ? "1.5px solid var(--brand)" : "1px solid var(--border)",
                  borderRadius: 12,
                  background: "var(--surface)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: "1.05rem", color: "var(--text-primary)" }}>{p.name}</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    {fmtINR(p.price)}<span style={{ fontSize: "0.95rem", fontWeight: 400, color: "var(--text-secondary)" }}> / month</span>
                  </div>
                  <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>{p.tagline}</div>
                </div>
                <button
                  onClick={() => handleUpgrade(p.id)}
                  disabled={upgrading !== null}
                  style={{
                    padding: "0.65rem 1rem",
                    borderRadius: 8,
                    border: p.featured ? "none" : "1px solid var(--border)",
                    background: p.featured ? "var(--brand)" : "var(--surface)",
                    color: p.featured ? "var(--brand-text, #fff)" : "var(--text-primary)",
                    cursor: upgrading ? "not-allowed" : "pointer",
                    fontWeight: 500,
                    opacity: upgrading && upgrading !== p.id ? 0.5 : 1,
                  }}
                >
                  {upgrading === p.id ? "Activating…" : `Choose ${p.name}`}
                </button>
              </div>
            ))}
          </div>

          <p style={{ marginTop: "1.5rem", fontSize: "0.875rem", color: "var(--text-tertiary)" }}>
            Secure UPI &amp; card payments. <Link href="/pricing" style={{ color: "var(--text-primary)", textDecoration: "underline" }}>Compare plans →</Link>
          </p>
        </>
      )}
    </main>
  );
}
