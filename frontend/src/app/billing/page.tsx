"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBillingStatus, upgradePlan, type BillingStatus } from "@/lib/api";
import toast from "react-hot-toast";

export default function BillingPage() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [upgrading, setUpgrading] = useState(false);

  useEffect(() => {
    getBillingStatus()
      .then((s) => setStatus(s))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load billing"))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpgrade(plan: "professional" | "business" | "enterprise", cycle: "monthly" | "annual") {
    setUpgrading(true);
    try {
      const r = await upgradePlan(plan, cycle);
      toast.success(r.message || "Upgrade started.");
      const refreshed = await getBillingStatus();
      setStatus(refreshed);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Upgrade failed");
    } finally {
      setUpgrading(false);
    }
  }

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "2rem 1.5rem" }}>
      <h1 style={{ fontSize: "1.75rem", fontWeight: 600, marginBottom: "0.25rem" }}>Billing</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
        Manage your plan, view trial usage, and upgrade.
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
              marginBottom: "1.5rem",
              background: "var(--surface)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <strong>Current plan</strong>
              <span style={{ textTransform: "capitalize" }}>{status.plan}</span>
            </div>
            {status.plan === "trial" && (
              <div style={{ color: "var(--text-secondary)" }}>
                {status.trial_queries_used} of {status.trial_limit} trial queries used
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
          <div style={{ display: "grid", gap: "0.75rem", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
            <button
              onClick={() => handleUpgrade("professional", "annual")}
              disabled={upgrading}
              style={planBtn}
            >
              Professional — ₹799/mo (annual)
            </button>
            <button
              onClick={() => handleUpgrade("professional", "monthly")}
              disabled={upgrading}
              style={planBtn}
            >
              Professional — ₹999/mo (monthly)
            </button>
            <button
              onClick={() => handleUpgrade("enterprise", "monthly")}
              disabled={upgrading}
              style={planBtn}
            >
              Enterprise — ₹2,999/mo
            </button>
          </div>

          <p style={{ marginTop: "1.5rem", fontSize: "0.875rem", color: "var(--text-tertiary)" }}>
            Secure UPI &amp; card payments. <Link href="/pricing" style={{ color: "var(--accent)" }}>Compare plans →</Link>
          </p>
        </>
      )}
    </main>
  );
}

const planBtn: React.CSSProperties = {
  padding: "0.75rem 1rem",
  border: "1px solid var(--border)",
  borderRadius: 10,
  background: "var(--surface)",
  color: "var(--text-primary)",
  cursor: "pointer",
  textAlign: "left",
  fontSize: "0.95rem",
};
