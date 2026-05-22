"use client"
import Link from "next/link"

export default function NotFound() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: 16,
        padding: 32,
        background: "var(--surface-base, #fafafa)",
        textAlign: "center",
      }}
    >
      {/* Large 404 number */}
      <div
        style={{
          fontFamily: "var(--font-display, Georgia, serif)",
          fontSize: 96,
          fontWeight: 400,
          lineHeight: 1,
          color: "var(--text-disabled, #A1A1AA)",
          userSelect: "none",
        }}
      >
        404
      </div>

      <h1
        style={{
          fontFamily: "var(--font-display, Georgia, serif)",
          fontSize: 28,
          fontWeight: 400,
          color: "var(--text-primary, #0a0a0b)",
          margin: 0,
        }}
      >
        Page not found
      </h1>

      <p
        style={{
          fontSize: 14,
          color: "var(--text-secondary, #52525b)",
          margin: 0,
          maxWidth: 40 + "ch",
        }}
      >
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>

      <Link
        href="/"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "10px 20px",
          borderRadius: 8,
          background: "var(--brand, #0D0D0D)",
          color: "var(--brand-text, #fff)",
          textDecoration: "none",
          fontSize: 14,
          fontWeight: 500,
          marginTop: 8,
          transition: "filter 100ms",
        }}
      >
        Go Back Home
      </Link>

      <p
        style={{
          fontSize: 13,
          color: "var(--text-tertiary, #71717a)",
          margin: 0,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
        </svg>
        Or search for what you need
      </p>
    </div>
  )
}
