"use client";

export default function AdminEvalPage() {
  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body, sans-serif)" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "8px" }}>
        Evaluation Benchmarks
      </h1>
      <p style={{ color: "var(--text-secondary, #6b7280)", marginBottom: "32px" }}>
        Track RAG accuracy, retrieval quality, and LLM response benchmarks.
      </p>
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
        Benchmark results will appear here once evaluation runs are complete.
      </div>
    </main>
  );
}
