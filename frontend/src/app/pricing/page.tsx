import Link from "next/link";
import {
  fmtINR,
  PRO_MONTHLY_PRICE,
  PRO_ANNUAL_MONTHLY_PRICE,
  ENTERPRISE_MONTHLY_PRICE,
  PRO_ANNUAL_TOTAL_LABEL,
} from "@/lib/pricing";

const PLANS = [
  {
    name: "Trial",
    price: "Free",
    cadence: "10 queries included",
    features: [
      "Up to 10 grounded queries",
      "All 7 workspaces (General, HR, Legal, Finance, Research, Study, Exam)",
      "PDF & DOCX uploads up to 200 MB",
      "Inline citations with page numbers",
    ],
    cta: { label: "Start free", href: "/register" },
  },
  {
    name: "Professional",
    price: `${fmtINR(PRO_ANNUAL_MONTHLY_PRICE)} /mo`,
    cadence: `billed annually · ${fmtINR(PRO_MONTHLY_PRICE)} /mo billed monthly`,
    annualNote: PRO_ANNUAL_TOTAL_LABEL,
    features: [
      "Unlimited queries",
      "All workspaces + Veritas trust reports",
      "Up to 3 collaborators per session",
      "Priority email support",
    ],
    cta: { label: "Upgrade", href: "/billing" },
    highlight: true,
  },
  {
    name: "Enterprise",
    price: `${fmtINR(ENTERPRISE_MONTHLY_PRICE)} /mo`,
    cadence: "billed monthly · SLA included",
    features: [
      "Everything in Professional",
      "Up to 25 collaborators per session",
      "Tenant isolation & SSO",
      "Dedicated onboarding & 99.9% uptime SLA",
    ],
    cta: { label: "Contact sales", href: "mailto:sales@documindai.com" },
  },
];

export default function PricingPage() {
  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <header style={{ textAlign: "center", marginBottom: "2.5rem" }}>
        <h1 style={{ fontSize: "2.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Simple, transparent pricing
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem" }}>
          Start free. No credit card. Upgrade when you need more.
        </p>
      </header>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "1.25rem",
        }}
      >
        {PLANS.map((p) => (
          <article
            key={p.name}
            style={{
              padding: "1.75rem 1.5rem",
              border: p.highlight
                ? "1px solid var(--accent, #4f46e5)"
                : "1px solid var(--border)",
              borderRadius: 14,
              background: "var(--surface)",
              boxShadow: p.highlight ? "0 8px 32px rgba(79, 70, 229, 0.12)" : "none",
            }}
          >
            <h2 style={{ fontSize: "1.15rem", fontWeight: 600, marginBottom: "0.5rem" }}>{p.name}</h2>
            <div style={{ fontSize: "1.75rem", fontWeight: 600, marginBottom: "0.25rem" }}>{p.price}</div>
            <div style={{ color: "var(--text-tertiary)", fontSize: "0.875rem", marginBottom: p.annualNote ? "0.25rem" : "1.25rem" }}>
              {p.cadence}
            </div>
            {p.annualNote && (
              <div style={{ color: "var(--text-tertiary)", fontSize: "0.8125rem", marginBottom: "1.25rem" }}>
                {p.annualNote}
              </div>
            )}
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 1.5rem", display: "grid", gap: "0.5rem" }}>
              {p.features.map((f) => (
                <li key={f} style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                  · {f}
                </li>
              ))}
            </ul>
            <Link
              href={p.cta.href}
              style={{
                display: "block",
                padding: "0.75rem 1rem",
                borderRadius: 10,
                textAlign: "center",
                background: p.highlight ? "var(--accent, #4f46e5)" : "var(--surface)",
                color: p.highlight ? "white" : "var(--text-primary)",
                border: p.highlight ? "none" : "1px solid var(--border)",
                fontWeight: 500,
              }}
            >
              {p.cta.label}
            </Link>
          </article>
        ))}
      </section>

      <p style={{ marginTop: "2.5rem", textAlign: "center", color: "var(--text-tertiary)", fontSize: "0.875rem" }}>
        Secure UPI &amp; card payments. Cancel any time.
      </p>
    </main>
  );
}
