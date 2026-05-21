"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { resetPassword } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      router.replace("/login?reset=true");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reset failed.");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <p style={{ color: "var(--text-secondary)" }}>
        This link is missing a reset token.{" "}
        <Link href="/forgot-password" style={{ color: "var(--accent, #4f46e5)" }}>
          Request a new one →
        </Link>
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
      <input
        type="password"
        autoComplete="new-password"
        required
        placeholder="New password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={inputStyle}
      />
      <input
        type="password"
        autoComplete="new-password"
        required
        placeholder="Confirm new password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        style={inputStyle}
      />
      {error && (
        <p style={{ color: "var(--accent-danger, #b91c1c)", fontSize: "0.875rem" }}>
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading || !password || !confirm}
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
        {loading ? "Updating…" : "Set new password"}
      </button>
    </form>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "0.75rem 0.875rem",
  border: "1px solid var(--border)",
  borderRadius: 10,
  fontSize: "1rem",
};

export default function ResetPasswordPage() {
  return (
    <main style={{ minHeight: "70vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem 1rem" }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "0.5rem" }}>Choose a new password</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: "1.25rem" }}>At least 8 characters.</p>
        <Suspense fallback={<p style={{ color: "var(--text-tertiary)" }}>Loading…</p>}>
          <ResetForm />
        </Suspense>
      </div>
    </main>
  );
}
