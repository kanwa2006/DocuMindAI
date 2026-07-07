"use client";

// P9 — OTP-based password reset. Three steps, single page, no
// reset-link emails: enter email → enter the 6-digit code we mailed →
// set a new password.
//
// The component keeps the older "Send reset link" copy off-screen so
// any user with a stale tab gets the new UX after a refresh.

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { forgotPassword, verifyResetOtp, resetPassword } from "@/lib/api";

type Step = "email" | "otp" | "password" | "done";

const RESEND_COOLDOWN_SECONDS = 30;

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resendIn, setResendIn] = useState(0);

  // Resend countdown.
  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((s) => Math.max(0, s - 1)), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  async function sendOtp(targetEmail: string) {
    setLoading(true);
    setError(null);
    try {
      const r = await forgotPassword(targetEmail);
      setResendIn(typeof r.resend_in === "number" ? r.resend_in : RESEND_COOLDOWN_SECONDS);
    } catch (e: unknown) {
      // Still advance so the page doesn't leak whether the email exists.
      setResendIn(RESEND_COOLDOWN_SECONDS);
      // Silently ignore the error text.
      void e;
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleaned = email.trim().toLowerCase();
    if (!cleaned) return;
    setEmail(cleaned);
    await sendOtp(cleaned);
    setStep("otp");
  }

  async function handleOtpSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!/^\d{6}$/.test(otp.trim())) {
      setError("Enter the 6-digit code from your email.");
      return;
    }
    setLoading(true);
    try {
      await verifyResetOtp(email, otp.trim());
      setStep("password");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid or expired code.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (resendIn > 0) return;
    await sendOtp(email);
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
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
      await resetPassword(email, otp.trim(), password);
      setStep("done");
      setTimeout(() => router.replace("/login?reset=true"), 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "70vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem 1rem" }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "0.5rem" }}>Reset your password</h1>

        {step === "email" && (
          <>
            <p style={{ color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Enter the email you registered with. We&apos;ll mail you a 6-digit code.
            </p>
            <form onSubmit={handleEmailSubmit} style={{ display: "grid", gap: "0.75rem" }}>
              <input
                type="email" autoComplete="email" required placeholder="you@example.com"
                value={email} onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
              />
              <button type="submit" disabled={loading || !email} style={primaryBtnStyle(loading)}>
                {loading ? "Sending…" : "Send code"}
              </button>
              <Link href="/login" style={muted}>Back to sign in</Link>
            </form>
          </>
        )}

        {step === "otp" && (
          <>
            <p style={{ color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              If an account exists for <strong>{email}</strong>, we just sent it a 6-digit code.
              The code expires in 10 minutes.
            </p>
            <form onSubmit={handleOtpSubmit} style={{ display: "grid", gap: "0.75rem" }}>
              <input
                inputMode="numeric" autoComplete="one-time-code" required
                maxLength={6} pattern="\d{6}" placeholder="123456"
                value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                style={{ ...inputStyle, textAlign: "center", letterSpacing: "0.4em", fontVariantNumeric: "tabular-nums" }}
              />
              {error && <p style={errStyle}>{error}</p>}
              <button type="submit" disabled={loading || otp.length !== 6} style={primaryBtnStyle(loading)}>
                {loading ? "Verifying…" : "Verify code"}
              </button>
              <button
                type="button"
                onClick={handleResend}
                disabled={resendIn > 0 || loading}
                style={{ ...secondaryBtnStyle, opacity: resendIn > 0 ? 0.6 : 1 }}
              >
                {resendIn > 0 ? `Resend code in ${resendIn}s` : "Resend code"}
              </button>
              <button
                type="button"
                onClick={() => { setStep("email"); setOtp(""); setError(null); }}
                style={muted}
              >
                Use a different email
              </button>
            </form>
          </>
        )}

        {step === "password" && (
          <>
            <p style={{ color: "var(--text-secondary)", marginBottom: "1.25rem" }}>
              Code verified. Choose a new password (at least 8 characters).
            </p>
            <form onSubmit={handlePasswordSubmit} style={{ display: "grid", gap: "0.75rem" }}>
              <input
                type="password" autoComplete="new-password" required placeholder="New password"
                value={password} onChange={(e) => setPassword(e.target.value)}
                style={inputStyle}
              />
              <input
                type="password" autoComplete="new-password" required placeholder="Confirm new password"
                value={confirm} onChange={(e) => setConfirm(e.target.value)}
                style={inputStyle}
              />
              {error && <p style={errStyle}>{error}</p>}
              <button type="submit" disabled={loading || !password || !confirm} style={primaryBtnStyle(loading)}>
                {loading ? "Updating…" : "Set new password"}
              </button>
            </form>
          </>
        )}

        {step === "done" && (
          <p style={{ color: "var(--text-secondary)" }}>
            Password updated. Redirecting to sign in…
          </p>
        )}
      </div>
    </main>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "0.75rem 0.875rem",
  border: "1px solid var(--border)",
  borderRadius: 10,
  fontSize: "1rem",
};

const errStyle: React.CSSProperties = {
  color: "var(--accent-danger, #b91c1c)",
  fontSize: "0.875rem",
  margin: 0,
};

const muted: React.CSSProperties = {
  textAlign: "center",
  color: "var(--text-tertiary)",
  fontSize: "0.875rem",
  background: "transparent",
  border: "none",
  cursor: "pointer",
};

function primaryBtnStyle(loading: boolean): React.CSSProperties {
  return {
    padding: "0.75rem",
    border: "none",
    borderRadius: 10,
    background: "var(--brand)",
    color: "var(--brand-text, #fff)",
    fontWeight: 500,
    cursor: loading ? "wait" : "pointer",
  };
}

const secondaryBtnStyle: React.CSSProperties = {
  padding: "0.55rem",
  border: "1px solid var(--border)",
  borderRadius: 10,
  background: "transparent",
  color: "var(--text-primary)",
  fontWeight: 400,
  cursor: "pointer",
};
