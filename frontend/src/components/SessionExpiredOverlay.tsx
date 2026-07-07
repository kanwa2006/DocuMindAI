"use client"
import { useSessionExpiry } from "@/hooks/useSessionExpiry"

export function SessionExpiredOverlay() {
  const { sessionExpired, dismiss } = useSessionExpiry()
  if (!sessionExpired) return null

  return (
    <div
      className="fixed inset-0 z-[200]"
      style={{
        background: "rgba(0,0,0,0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "var(--surface-overlay, #fff)",
          border: "1px solid var(--border-default, #e5e7eb)",
          borderRadius: 16,
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)",
          width: "100%",
          maxWidth: 400,
          padding: 32,
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 48, lineHeight: 1 }}>🔒</div>
        <h2
          style={{
            marginTop: 16,
            fontFamily: "var(--font-display, Georgia, serif)",
            fontSize: 22,
            fontWeight: 400,
            color: "var(--text-primary, #0a0a0b)",
          }}
        >
          Your session has expired
        </h2>
        <p
          style={{
            margin: "12px 0 24px",
            fontSize: 14,
            lineHeight: 1.6,
            color: "var(--text-secondary, #52525b)",
          }}
        >
          For your security, we sign you out after a period of inactivity.
          Your work is saved.
        </p>
        <button
          onClick={dismiss}
          style={{
            display: "block",
            width: "100%",
            height: 44,
            borderRadius: 8,
            background: "var(--brand, #0D0D0D)",
            color: "var(--brand-text, #fff)",
            border: "none",
            fontSize: 15,
            fontWeight: 600,
            cursor: "pointer",
            transition: "filter 100ms",
          }}
          onMouseEnter={(e) => {
            ;(e.currentTarget as HTMLButtonElement).style.filter =
              "brightness(1.08)"
          }}
          onMouseLeave={(e) => {
            ;(e.currentTarget as HTMLButtonElement).style.filter = "none"
          }}
        >
          Sign In Again →
        </button>
      </div>
    </div>
  )
}
