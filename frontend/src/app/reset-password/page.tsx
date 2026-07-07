"use client";

// P9 — Password reset switched from email-link to OTP flow. This page
// remains so any in-flight email from before P9 lands on a soft fallback
// instead of a 404, and points the user at the new /forgot-password
// entry point. Once no historical links remain in the wild this file
// can be deleted outright.

import Link from "next/link";

export default function ResetPasswordPage() {
  return (
    <main style={{ minHeight: "70vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem 1rem" }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "0.5rem" }}>Reset link no longer used</h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
          We now send a 6-digit code instead of a reset link. Request a new
          code on the password-reset page.
        </p>
        <Link
          href="/forgot-password"
          style={{
            display: "inline-block",
            padding: "0.75rem 1rem",
            borderRadius: 10,
            background: "var(--brand)",
            color: "var(--brand-text, #fff)",
            fontWeight: 500,
            textDecoration: "none",
          }}
        >
          Reset password →
        </Link>
      </div>
    </main>
  );
}
