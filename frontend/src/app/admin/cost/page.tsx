"use client";

export default function AdminCostPage() {
  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body, sans-serif)" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "8px" }}>
        Cost & Usage
      </h1>
      <p style={{ color: "var(--text-secondary, #6b7280)", marginBottom: "32px" }}>
        LLM token consumption, API call costs, and per-tenant usage breakdown.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        {[
          { label: "Total API Spend (MTD)", value: "—" },
          { label: "Tokens Used (MTD)", value: "—" },
          { label: "Avg Cost / Query", value: "—" },
          { label: "Active Tenants", value: "—" },
        ].map(({ label, value }) => (
          <div
            key={label}
            style={{
              background: "var(--surface-secondary, #f9fafb)",
              border: "1px solid var(--border-primary, #e5e7eb)",
              borderRadius: "12px",
              padding: "20px",
            }}
          >
            <p style={{ fontSize: "13px", color: "var(--text-secondary, #6b7280)", marginBottom: "4px" }}>
              {label}
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700 }}>{value}</p>
          </div>
        ))}
      </div>

      <div
        style={{
          background: "var(--surface-secondary, #f9fafb)",
          border: "1px solid var(--border-primary, #e5e7eb)",
          borderRadius: "12px",
          padding: "24px",
          textAlign: "center",
          color: "var(--text-tertiary, #9ca3af)",
          fontSize: "14px",
        }}
      >
        Detailed cost analytics will appear here once the cost tracking pipeline is active.
      </div>
    </main>
  );
}
