"use client";

import { useState, useRef, useEffect } from "react";
import { verifyEmail, resendVerificationEmail } from "@/lib/api";

interface EmailVerificationScreenProps {
  email: string;
  onVerified: () => void;
}

export default function EmailVerificationScreen({ email, onVerified }: EmailVerificationScreenProps) {
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [resendMessage, setResendMessage] = useState("");
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const otp = digits.join("");

  const handleDigitChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const next = [...digits];
    next[index] = value.slice(-1);
    setDigits(next);
    setError("");
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) {
      setDigits(pasted.split(""));
      inputRefs.current[5]?.focus();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length !== 6) {
      setError("Please enter all 6 digits.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await verifyEmail(otp);
      onVerified();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Verification failed.";
      setError(msg);
      setDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setResendMessage("");
    setError("");
    try {
      await resendVerificationEmail();
      setResendMessage("A new code was sent to your email.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to resend.";
      setError(msg);
    } finally {
      setResending(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "48px",
    height: "56px",
    textAlign: "center",
    fontSize: "24px",
    fontWeight: 700,
    border: "2px solid var(--border, #e5e7eb)",
    borderRadius: "var(--radius-md, 8px)",
    background: "transparent",
    color: "var(--text-primary)",
    outline: "none",
    fontFamily: "var(--font-mono, monospace)",
    caretColor: "var(--brand, hsl(220,90%,60%))",
    transition: "border-color 0.15s",
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4"
         style={{ background: "var(--surface-base, #fff)" }}>
      <div style={{ maxWidth: "400px", width: "100%", textAlign: "center" }}>
        <div style={{ fontSize: "40px", marginBottom: "16px" }}>📧</div>

        <h1 style={{
          fontFamily: "Georgia, 'Instrument Serif', serif",
          fontSize: "26px",
          fontWeight: 600,
          color: "var(--text-primary)",
          margin: "0 0 8px",
        }}>
          Check your email
        </h1>

        <p style={{ fontSize: "14px", color: "var(--text-secondary)", margin: "0 0 32px", lineHeight: 1.6 }}>
          We sent a 6-digit code to<br />
          <strong style={{ color: "var(--text-primary)" }}>{email}</strong>
        </p>

        <form onSubmit={handleSubmit}>
          <div
            style={{ display: "flex", gap: "10px", justifyContent: "center", marginBottom: "24px" }}
            onPaste={handlePaste}
          >
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                aria-label={`Digit ${i + 1} of verification code`}
                style={{
                  ...inputStyle,
                  borderColor: error
                    ? "var(--red-500, #ef4444)"
                    : digit
                    ? "var(--brand, hsl(220,90%,60%))"
                    : "var(--border, #e5e7eb)",
                }}
                onFocus={(e) => {
                  if (!error) (e.currentTarget as HTMLElement).style.borderColor = "var(--brand, hsl(220,90%,60%))";
                }}
                onBlur={(e) => {
                  if (!digit && !error) (e.currentTarget as HTMLElement).style.borderColor = "var(--border, #e5e7eb)";
                }}
              />
            ))}
          </div>

          {error && (
            <p style={{ fontSize: "13px", color: "var(--red-500, #ef4444)", margin: "0 0 16px" }}>
              ⚠ {error}
            </p>
          )}

          {resendMessage && (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 16px" }}>
              ✓ {resendMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || otp.length !== 6}
            style={{
              width: "100%",
              height: "44px",
              borderRadius: "var(--radius-md, 8px)",
              background: "var(--brand, hsl(220,90%,60%))",
              color: "#fff",
              border: "none",
              fontSize: "15px",
              fontWeight: 600,
              cursor: loading || otp.length !== 6 ? "not-allowed" : "pointer",
              opacity: loading || otp.length !== 6 ? 0.6 : 1,
              fontFamily: "var(--font-body)",
              marginBottom: "20px",
            }}
          >
            {loading ? "Verifying…" : "Verify Email"}
          </button>
        </form>

        <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
          Didn&apos;t receive it?{" "}
          <button
            onClick={handleResend}
            disabled={resending}
            style={{
              background: "none",
              border: "none",
              cursor: resending ? "not-allowed" : "pointer",
              color: "var(--brand, hsl(220,90%,60%))",
              fontSize: "13px",
              fontWeight: 500,
              padding: 0,
              fontFamily: "var(--font-body)",
            }}
          >
            {resending ? "Sending…" : "Resend code"}
          </button>
        </p>
        <p style={{ fontSize: "12px", color: "var(--text-tertiary)", marginTop: "8px" }}>
          Code expires in 10 minutes.
        </p>
      </div>
    </div>
  );
}
