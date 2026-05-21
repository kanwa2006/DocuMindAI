"use client";

interface ComparisonToggleProps {
  enabled: boolean;
  documentCount: number;
  onToggle: (enabled: boolean) => void;
}

export default function ComparisonToggle({ enabled, documentCount, onToggle }: ComparisonToggleProps) {
  if (documentCount < 2) return null;

  return (
    <button
      type="button"
      onClick={() => onToggle(!enabled)}
      aria-pressed={enabled}
      aria-label={enabled ? "Disable comparison mode" : "Enable comparison mode — compare all documents"}
      title={enabled ? "Comparison mode ON — click to disable" : "Compare all uploaded documents side by side"}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        height: "32px",
        padding: "0 12px",
        border: `1px solid ${enabled ? "var(--amber-500, #f59e0b)" : "var(--border-default)"}`,
        borderRadius: "8px",
        background: enabled ? "rgba(245, 158, 11, 0.1)" : "var(--surface-raised)",
        cursor: "pointer",
        fontFamily: "var(--font-body)",
        fontSize: "12px",
        fontWeight: 500,
        color: enabled ? "var(--amber-600, #d97706)" : "var(--text-secondary)",
        transition: "border-color 120ms, background 120ms, color 120ms",
        flexShrink: 0,
      }}
    >
      <span aria-hidden="true">⇄</span>
      Compare Mode
      {enabled && (
        <span style={{
          background: "var(--amber-500, #f59e0b)",
          color: "#fff",
          borderRadius: "999px",
          padding: "1px 6px",
          fontSize: "10px",
          fontWeight: 600,
        }}>
          {documentCount} docs
        </span>
      )}
    </button>
  );
}
