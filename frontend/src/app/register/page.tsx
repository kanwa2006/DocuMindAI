"use client";

import { useState } from "react";
import Link from "next/link";
import { register } from "@/lib/api";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (!email || !password) {
      setError("Email and password are required.");
      setLoading(false);
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      setLoading(false);
      return;
    }

    try {
      await register({ email, password, full_name: fullName || undefined });
      // A1: skip OTP — go straight to /login with the email pre-filled.
      window.location.href = `/login?registered=true&email=${encodeURIComponent(email)}`;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed.";
      setError(message);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Brand panel */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col items-center justify-center relative overflow-hidden"
        style={{ background: "linear-gradient(135deg, #1a1a1a 0%, #050505 100%)" }}
      >
        <div className="max-w-md px-8 text-center">
          <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">
            DocuMind<span className="italic">AI</span>
          </h1>
          <p className="text-lg text-white/90 mb-10" style={{ fontStyle: "italic" }}>
            5 free queries. Full access. No card required.
          </p>
          <div className="space-y-4 text-left">
            {[
              "All 7 workspaces from day one",
              "Answers only from your documents",
              "Every answer cites the exact source page",
            ].map((text) => (
              <div key={text} className="flex items-start gap-3">
                <span className="text-white/90 mt-0.5">✓</span>
                <span className="text-sm text-white/90">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-white dark:bg-[#0C0C0E]">
        <div className="w-full max-w-[380px]">
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-2xl font-bold text-black dark:text-white tracking-tight">
              DocuMind<span className="italic">AI</span>
            </h1>
          </div>

          <div className="mb-8">
            <h2
              className="text-[28px] font-bold text-black dark:text-white"
              style={{ fontFamily: "Georgia, serif" }}
            >
              Create your account
            </h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Start your free trial — 5 queries, all features
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleRegister}>
            {error && (
              <div
                className="px-4 py-3 rounded-lg text-[13px] font-medium"
                style={{
                  backgroundColor: "hsl(40, 90%, 95%)",
                  color: "hsl(40, 80%, 30%)",
                  border: "1px solid hsl(40, 70%, 80%)",
                }}
              >
                ⚠ {error}
              </div>
            )}

            <div>
              <label
                className="block text-xs font-medium mb-1.5 tracking-[0.1em] uppercase text-gray-500 dark:text-gray-400"
                htmlFor="reg-name"
              >
                Full Name (optional)
              </label>
              <input
                id="reg-name"
                type="text"
                className="block w-full h-[44px] px-3 text-sm bg-transparent border rounded-lg transition-all
                           border-gray-200 dark:border-gray-700
                           focus:outline-none focus:border-[#0D0D0D] focus:shadow-[0_0_0_3px_rgba(13,13,13,0.18)]
                           text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-600"
                placeholder="Jane Smith"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            <div>
              <label
                className="block text-xs font-medium mb-1.5 tracking-[0.1em] uppercase text-gray-500 dark:text-gray-400"
                htmlFor="reg-email"
              >
                Email Address
              </label>
              <input
                id="reg-email"
                type="email"
                required
                className="block w-full h-[44px] px-3 text-sm bg-transparent border rounded-lg transition-all
                           border-gray-200 dark:border-gray-700
                           focus:outline-none focus:border-[#0D0D0D] focus:shadow-[0_0_0_3px_rgba(13,13,13,0.18)]
                           text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-600"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label
                className="block text-xs font-medium mb-1.5 tracking-[0.1em] uppercase text-gray-500 dark:text-gray-400"
                htmlFor="reg-password"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="reg-password"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  className="block w-full h-[44px] px-3 pr-11 text-sm bg-transparent border rounded-lg transition-all
                             border-gray-200 dark:border-gray-700
                             focus:outline-none focus:border-[#0D0D0D] focus:shadow-[0_0_0_3px_rgba(13,13,13,0.18)]
                             text-black dark:text-white placeholder-gray-400 dark:placeholder-gray-600"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 w-9 h-9 m-auto mr-1 flex items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0a10.05 10.05 0 015.71-1.29c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0l-3.29-3.29" /></svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                  )}
                </button>
              </div>
              <p className="mt-1.5 text-xs text-gray-400">Minimum 8 characters</p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-[44px] rounded-lg text-[15px] font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: "var(--brand, #0D0D0D)" }}
              onMouseEnter={(e) => { if (!loading) (e.target as HTMLButtonElement).style.filter = "brightness(1.08)"; }}
              onMouseLeave={(e) => { (e.target as HTMLButtonElement).style.filter = "none"; }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 100 8v4a8 8 0 01-8-8z" />
                  </svg>
                </span>
              ) : (
                "Create Account →"
              )}
            </button>

            <p className="text-center text-xs text-gray-400">
              By signing up you agree to our Terms of Service.
            </p>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
            Already have an account?{" "}
            <Link href="/login" className="font-medium" style={{ color: "var(--brand, #0D0D0D)" }}>
              Sign in →
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
