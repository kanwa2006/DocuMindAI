"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email.trim().toLowerCase());
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  }

  return (
    <main style={{ minHeight: "70vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem 1rem" }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "0.5rem" }}>Reset your password</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
          Enter the email you registered with. If an account exists, we&apos;ll send a reset link.
        </p>

        {submitted ? (
          <div style={{ padding: "1rem", border: "1px solid var(--border)", borderRadius: 10, color: "var(--text-secondary)" }}>
            If an account exists for <strong>{email}</strong>, a reset link is on its way. The link expires in 30 minutes.
            <div style={{ marginTop: "1rem" }}>
              <Link href="/login" style={{ color: "var(--accent, #4f46e5)" }}>
                Back to sign in
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
            <input
              type="email"
              autoComplete="email"
              required
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                padding: "0.75rem 0.875rem",
                border: "1px solid var(--border)",
                borderRadius: 10,
                fontSize: "1rem",
              }}
            />
            <button
              type="submit"
              disabled={loading || !email}
              style={{
                padding: "0.75rem",
                border: "none",
                borderRadius: 10,
                background: "var(--accent, #4f46e5)",
                color: "white",
                fontWeight: 500,
                cursor: loading ? "wait" : "pointer",
              }}
            >
              {loading ? "Sending…" : "Send reset link"}
            </button>
            <Link href="/login" style={{ textAlign: "center", color: "var(--text-tertiary)", fontSize: "0.875rem" }}>
              Back to sign in
            </Link>
          </form>
        )}
      </div>
    </main>
  );
}
