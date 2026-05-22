"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

const LANGUAGE_OPTIONS = [
  { value: "auto",      label: "Auto-detect" },
  { value: "english",   label: "English" },
  { value: "hindi",     label: "Hindi (हिंदी)" },
  { value: "tamil",     label: "Tamil (தமிழ்)" },
  { value: "telugu",    label: "Telugu (తెలుగు)" },
  { value: "kannada",   label: "Kannada (ಕನ್ನಡ)" },
  { value: "malayalam", label: "Malayalam (മലയാളം)" },
  { value: "gujarati",  label: "Gujarati (ગુજરાતી)" },
  { value: "marathi",   label: "Marathi (मराठी)" },
  { value: "bengali",   label: "Bengali (বাংলা)" },
];

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  preferred_language: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [language, setLanguage] = useState("auto");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/users/me")
      .then((r) => {
        if (r.status === 401) { router.push("/login"); return null; }
        return r.json();
      })
      .then((data: UserProfile | null) => {
        if (!data) return;
        setProfile(data);
        setLanguage(data.preferred_language || "auto");
      })
      .catch(() => setError("Failed to load profile."));
  }, [router]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const res = await apiFetch("/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferred_language: language }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Save failed");
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e: any) {
      setError(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const cardStyle: React.CSSProperties = {
    background: "var(--surface-raised)",
    border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-xl)",
    padding: "24px",
    marginBottom: "16px",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--weight-semibold)",
    color: "var(--text-primary)",
    fontFamily: "var(--font-body)",
    marginBottom: "4px",
  };

  const descStyle: React.CSSProperties = {
    fontSize: "var(--text-xs)",
    color: "var(--text-secondary)",
    fontFamily: "var(--font-body)",
    marginBottom: "10px",
  };

  const selectStyle: React.CSSProperties = {
    width: "100%",
    maxWidth: "320px",
    padding: "8px 12px",
    background: "var(--surface-base)",
    border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-md)",
    color: "var(--text-primary)",
    fontSize: "var(--text-sm)",
    fontFamily: "var(--font-body)",
    outline: "none",
    cursor: "pointer",
  };

  return (
    <div
      style={{
        maxWidth: "640px",
        margin: "48px auto",
        padding: "0 24px",
        fontFamily: "var(--font-body)",
      }}
    >
      <h1
        style={{
          fontSize: "var(--text-2xl)",
          fontWeight: "var(--weight-bold)",
          color: "var(--text-primary)",
          marginBottom: "8px",
        }}
      >
        Settings
      </h1>
      <p
        style={{
          fontSize: "var(--text-sm)",
          color: "var(--text-secondary)",
          marginBottom: "32px",
        }}
      >
        Manage your account preferences.
      </p>

      {/* General section */}
      <div style={cardStyle}>
        <div
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: "var(--weight-semibold)",
            color: "var(--text-tertiary)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            marginBottom: "20px",
          }}
        >
          General
        </div>

        {/* Account info */}
        {profile && (
          <div style={{ marginBottom: "24px" }}>
            <span style={labelStyle}>Account</span>
            <div
              style={{
                fontSize: "var(--text-sm)",
                color: "var(--text-secondary)",
              }}
            >
              {profile.full_name && (
                <span style={{ color: "var(--text-primary)", marginRight: "8px" }}>
                  {profile.full_name}
                </span>
              )}
              {profile.email}
            </div>
          </div>
        )}

        {/* AI Response Language */}
        <div>
          <label htmlFor="response-language" style={labelStyle}>
            AI Response Language
          </label>
          <p style={descStyle}>
            DocuMindAI auto-detects your question language. Set a preference to always
            respond in your language.
          </p>
          <select
            id="response-language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={selectStyle}
            aria-label="Select AI response language"
          >
            {LANGUAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error / success */}
      {error && (
        <p
          style={{
            fontSize: "var(--text-sm)",
            color: "var(--red-500, #ef4444)",
            marginBottom: "12px",
          }}
        >
          {error}
        </p>
      )}
      {saved && (
        <p
          style={{
            fontSize: "var(--text-sm)",
            color: "var(--green-500, #22c55e)",
            marginBottom: "12px",
          }}
        >
          Settings saved.
        </p>
      )}

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="btn btn-primary"
        style={{ minWidth: "120px", height: "40px" }}
        aria-label="Save settings"
      >
        {saving ? "Saving…" : "Save Changes"}
      </button>
    </div>
  );
}
