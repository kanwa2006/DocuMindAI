"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import EmailVerificationScreen from "@/components/EmailVerificationScreen";

function VerifyEmailInner() {
  const router = useRouter();
  const params = useSearchParams();
  const email = params.get("email") ?? "";

  if (!email) {
    return (
      <main style={{ maxWidth: 480, margin: "4rem auto", padding: "0 1.5rem", textAlign: "center" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Verify your email
        </h1>
        <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem" }}>
          Please open the verification link from your registration email, or
          return to the sign-up flow.
        </p>
        <button
          onClick={() => router.push("/register")}
          className="btn btn-secondary"
          style={{ height: "40px", padding: "0 16px" }}
        >
          Back to sign up
        </button>
      </main>
    );
  }

  return (
    <EmailVerificationScreen
      email={email}
      onVerified={() => router.push("/general")}
    />
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<p style={{ padding: "2rem", color: "var(--text-tertiary)" }}>Loading…</p>}>
      <VerifyEmailInner />
    </Suspense>
  );
}
