import Link from "next/link";
import { PLANS, fmtINR } from "@/lib/pricing";

// One free-trial card pinned to the left, then the three paid PLANS.
const FREE = {
  id: "trial" as const,
  name: "Free",
  price: 0,
  tagline: "Try DocuMindAI with no card",
  features: [
    "10 free queries",
    "All 7 workspaces",
    "Page-cited answers",
    "Uploads up to 200 MB",
  ],
  ctaLabel: "Start free",
  ctaHref: "/register",
};

export default function PricingPage() {
  return (
    <main style={{ maxWidth: 1180, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <header style={{ textAlign: "center", marginBottom: "2.5rem" }}>
        <h1 style={{ fontSize: "2.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Pricing
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem" }}>
          Start free. Upgrade when you need more.
        </p>
      </header>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "1.25rem",
        }}
      >
        <article style={cardStyle(false)}>
          <h2 style={planNameStyle}>{FREE.name}</h2>
          <div style={priceStyle}>{fmtINR(FREE.price)}</div>
          <div style={tagStyle}>{FREE.tagline}</div>
          <ul style={featuresStyle}>
            {FREE.features.map((f) => (
              <li key={f} style={featureItemStyle}>· {f}</li>
            ))}
          </ul>
          <Link href={FREE.ctaHref} style={ctaStyle(false)}>{FREE.ctaLabel}</Link>
        </article>

        {PLANS.map((p) => (
          <article key={p.id} style={cardStyle(!!p.featured)}>
            <h2 style={planNameStyle}>{p.name}</h2>
            <div style={priceStyle}>
              {fmtINR(p.price)}
              <span style={cadenceStyle}> / month</span>
            </div>
            <div style={tagStyle}>{p.tagline}</div>
            <ul style={featuresStyle}>
              {p.features.map((f) => (
                <li key={f} style={featureItemStyle}>· {f}</li>
              ))}
            </ul>
            <Link href="/billing" style={ctaStyle(!!p.featured)}>
              {p.featured ? `Upgrade to ${p.name}` : `Get ${p.name}`}
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

const cardStyle = (featured: boolean): React.CSSProperties => ({
  padding: "1.75rem 1.5rem",
  border: featured ? "1.5px solid var(--brand)" : "1px solid var(--border)",
  borderRadius: 14,
  background: "var(--surface)",
  boxShadow: featured ? "0 8px 32px rgba(0,0,0,0.06)" : "none",
});

const planNameStyle: React.CSSProperties = {
  fontSize: "1.05rem",
  fontWeight: 600,
  marginBottom: "0.5rem",
  color: "var(--text-primary)",
};

const priceStyle: React.CSSProperties = {
  fontSize: "1.75rem",
  fontWeight: 700,
  marginBottom: "0.25rem",
  color: "var(--text-primary)",
};

const cadenceStyle: React.CSSProperties = {
  fontSize: "0.95rem",
  fontWeight: 400,
  color: "var(--text-secondary)",
};

const tagStyle: React.CSSProperties = {
  color: "var(--text-secondary)",
  fontSize: "0.9rem",
  marginBottom: "1.25rem",
};

const featuresStyle: React.CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: "0 0 1.5rem",
  display: "grid",
  gap: "0.5rem",
};

const featureItemStyle: React.CSSProperties = {
  color: "var(--text-secondary)",
  fontSize: "0.93rem",
};

const ctaStyle = (featured: boolean): React.CSSProperties => ({
  display: "block",
  padding: "0.75rem 1rem",
  borderRadius: 10,
  textAlign: "center",
  background: featured ? "var(--brand)" : "var(--surface)",
  color: featured ? "var(--brand-text, #fff)" : "var(--text-primary)",
  border: featured ? "none" : "1px solid var(--border)",
  fontWeight: 500,
});
