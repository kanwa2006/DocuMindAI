import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "DocuMindAI — Document Intelligence for Indian Professionals",
  description:
    "Ask questions about your PDFs, contracts & notes. Get verified answers with exact page citations. Built for CAs, Lawyers, Teachers & HR professionals in India.",
  keywords: [
    "RAG",
    "document AI",
    "PDF chat",
    "Indian AI tool",
    "document intelligence",
    "CA tool",
    "legal AI India",
  ],
  openGraph: {
    title: "DocuMindAI — Ask Anything About Your Documents",
    description:
      "Ask questions about your PDFs, contracts & notes. Get verified answers with exact page citations. Built for CAs, Lawyers, Teachers & HR professionals in India.",
    url: "https://documindai.com",
    siteName: "DocuMindAI",
    images: ["/og-image.png"],
    type: "website",
    locale: "en_IN",
  },
  twitter: {
    card: "summary_large_image",
    title: "DocuMindAI",
    description:
      "Ask questions about your PDFs, contracts & notes. Get verified answers with exact page citations.",
  },
  robots: { index: true, follow: true },
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <style>{`
        html { scroll-behavior: smooth; }
        @media (max-width: 480px) {
          .marketing-nav { padding-left: 16px !important; padding-right: 16px !important; }
          .marketing-nav .nav-pricing { display: none; }
        }
      `}</style>

      {/* ── MARKETING NAV ── */}
      <nav
        className="marketing-nav"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          background: "var(--surface-overlay)",
          borderBottom: "1px solid var(--border-subtle)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "64px",
          padding: "0 max(24px, calc((100% - 1200px) / 2))",
        }}
      >
        <Link
          href="/"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.4rem",
            color: "var(--text-primary)",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span style={{ fontSize: "1.5rem" }}>🧠</span>
          <span style={{ color: "var(--brand)", fontWeight: "var(--weight-bold)" }}>DocuMind</span>
          <span>AI</span>
        </Link>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Link
            href="/pricing"
            className="nav-pricing"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "var(--text-sm)",
              color: "var(--text-secondary)",
              textDecoration: "none",
              padding: "8px 16px",
              borderRadius: "var(--radius-md)",
            }}
          >
            Pricing
          </Link>
          <Link
            href="/login"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "var(--text-sm)",
              color: "var(--text-secondary)",
              textDecoration: "none",
              padding: "8px 16px",
              borderRadius: "var(--radius-md)",
            }}
          >
            Log In
          </Link>
          <Link
            href="/register"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "var(--text-sm)",
              color: "var(--brand-text)",
              background: "var(--brand)",
              textDecoration: "none",
              padding: "8px 20px",
              borderRadius: "var(--radius-md)",
              fontWeight: "var(--weight-semibold)",
            }}
          >
            Start Free
          </Link>
        </div>
      </nav>

      <main id="main">{children}</main>
    </>
  );
}
