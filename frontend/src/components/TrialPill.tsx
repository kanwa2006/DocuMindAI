"use client";

interface TrialPillProps {
  queriesUsed: number;
  queriesRemaining: number;
  trialLimit?: number;
  onClick: () => void;
}

export default function TrialPill({
  queriesUsed,
  queriesRemaining,
  trialLimit,
  onClick,
}: TrialPillProps) {
  // queriesRemaining is authoritative; use trialLimit only for warning thresholds (defaults derived from remaining).
  const isUrgent = queriesRemaining <= 1;
  const isWarning = queriesRemaining <= 3 && !isUrgent;

  const borderColor = isUrgent
    ? "var(--red-500, #ef4444)"
    : isWarning
    ? "var(--amber-500, #f59e0b)"
    : "var(--border, #e5e7eb)";

  const textColor = isUrgent
    ? "var(--red-500, #ef4444)"
    : isWarning
    ? "var(--amber-500, #f59e0b)"
    : "var(--text-secondary)";

  const ariaLabel = trialLimit != null
    ? `Free trial: ${queriesUsed} of ${trialLimit} queries used`
    : `Free trial: ${queriesRemaining} queries left`;

  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel}
      title="Click to upgrade"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-1-5, 6px)",
        padding: "4px 10px",
        background: "var(--surface-raised)",
        border: `1px solid ${borderColor}`,
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: 500,
        color: textColor,
        cursor: "pointer",
        fontFamily: "var(--font-body)",
        transition: "border-color 0.15s, color 0.15s, background 0.15s",
        whiteSpace: "nowrap",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.background = "var(--surface-raised)";
      }}
    >
      <span aria-hidden="true">✦</span>
      Free trial — {Math.max(queriesRemaining, 0)} left
    </button>
  );
}
