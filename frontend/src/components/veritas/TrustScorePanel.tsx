"use client";

import { useState, useCallback } from "react";
import { TrustReport, TrustFactor, TrustContradiction, TRUST_LEVEL_CFG } from "./TrustScoreBadge";

interface TrustScorePanelProps {
  trust: TrustReport;
  originalQuery: string;
  onViewPage: (filename: string, page: number) => void;
  onSecondOpinion: (query: string) => Promise<string>;
}

function trackEvent(name: string, props: Record<string, unknown>) {
  if (typeof window !== "undefined") {
    try {
      (window as any).__analytics?.track?.(name, props);
    } catch {}
  }
}

function FactorBar({ factor }: { factor: TrustFactor }) {
  const pct = Math.round(factor.weight * 100);
  const score = Math.round(factor.score);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
      <div
        style={{
          flex: 1,
          fontFamily: "var(--font-body)",
          fontSize: "12px",
          color: "var(--text-secondary)",
          minWidth: 0,
        }}
      >
        {factor.name}
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          color: "var(--text-tertiary)",
          whiteSpace: "nowrap",
        }}
      >
        {pct}% →
      </span>
      <div
        style={{
          width: "60px",
          height: "5px",
          background: "var(--border-subtle)",
          borderRadius: "3px",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: `${score}%`,
            height: "100%",
            background:
              score >= 80 ? "#16a34a" : score >= 55 ? "#b45309" : "#dc2626",
            borderRadius: "3px",
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          color: "var(--text-secondary)",
          width: "36px",
          textAlign: "right",
        }}
      >
        {score}/100
      </span>
    </div>
  );
}

function ContradictionCard({
  c,
  onViewPage,
}: {
  c: TrustContradiction;
  onViewPage: (filename: string, page: number) => void;
}) {
  return (
    <div
      style={{
        border: "1px solid #fecdd3",
        borderRadius: "8px",
        overflow: "hidden",
        marginTop: "8px",
      }}
    >
      <div
        style={{
          padding: "6px 10px",
          background: "#fff1f2",
          fontFamily: "var(--font-body)",
          fontSize: "11px",
          fontWeight: 600,
          color: "#dc2626",
        }}
      >
        🔴 Contradiction Detected
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        {/* Doc A */}
        <div
          style={{
            padding: "10px",
            borderRight: "1px solid #fecdd3",
            fontFamily: "var(--font-body)",
            fontSize: "12px",
          }}
        >
          <div
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: "4px",
              fontSize: "11px",
            }}
          >
            {c.doc_a.filename}, Page {c.doc_a.page}
          </div>
          <div
            style={{
              color: "var(--text-secondary)",
              fontStyle: "italic",
              lineHeight: 1.5,
            }}
          >
            &ldquo;{c.doc_a.text}&rdquo;
          </div>
          <button
            onClick={() => onViewPage(c.doc_a.filename, c.doc_a.page)}
            style={{
              marginTop: "8px",
              padding: "2px 8px",
              border: "1px solid var(--border-default)",
              borderRadius: "4px",
              background: "none",
              cursor: "pointer",
              fontFamily: "var(--font-body)",
              fontSize: "11px",
              color: "var(--brand)",
            }}
          >
            → View Page {c.doc_a.page}
          </button>
        </div>
        {/* Doc B */}
        <div
          style={{
            padding: "10px",
            fontFamily: "var(--font-body)",
            fontSize: "12px",
          }}
        >
          <div
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: "4px",
              fontSize: "11px",
            }}
          >
            {c.doc_b.filename}, Page {c.doc_b.page}
          </div>
          <div
            style={{
              color: "var(--text-secondary)",
              fontStyle: "italic",
              lineHeight: 1.5,
            }}
          >
            &ldquo;{c.doc_b.text}&rdquo;
          </div>
          <button
            onClick={() => onViewPage(c.doc_b.filename, c.doc_b.page)}
            style={{
              marginTop: "8px",
              padding: "2px 8px",
              border: "1px solid var(--border-default)",
              borderRadius: "4px",
              background: "none",
              cursor: "pointer",
              fontFamily: "var(--font-body)",
              fontSize: "11px",
              color: "var(--brand)",
            }}
          >
            → View Page {c.doc_b.page}
          </button>
        </div>
      </div>
    </div>
  );
}

export function TrustScorePanel({
  trust,
  originalQuery,
  onViewPage,
  onSecondOpinion,
}: TrustScorePanelProps) {
  const [secondOpinionState, setSecondOpinionState] = useState<
    "idle" | "loading" | "done"
  >("idle");
  const [secondAnswer, setSecondAnswer] = useState<string | null>(null);

  const cfg = TRUST_LEVEL_CFG[trust.level] ?? TRUST_LEVEL_CFG.MEDIUM;

  const hasContradictions = trust.contradictions?.length > 0;

  // Track analytics on mount
  useState(() => {
    trackEvent("trust_score_expanded", {
      trust_level: trust.level,
      score: trust.final_score,
    });
    if (hasContradictions) {
      trackEvent("contradiction_viewed", {
        num_contradictions: trust.contradictions.length,
      });
    }
  });

  const handleSecondOpinion = useCallback(async () => {
    if (secondOpinionState !== "idle") return;
    trackEvent("second_opinion_requested", { original_score: trust.final_score });
    setSecondOpinionState("loading");
    try {
      const answer = await onSecondOpinion(originalQuery);
      setSecondAnswer(answer);
      setSecondOpinionState("done");
    } catch {
      setSecondOpinionState("idle");
    }
  }, [secondOpinionState, onSecondOpinion, originalQuery, trust.final_score]);

  return (
    <div
      style={{
        marginTop: "8px",
        border: `1px solid ${cfg.border}`,
        borderRadius: "10px",
        background: "var(--surface-raised)",
        overflow: "hidden",
        fontFamily: "var(--font-body)",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "10px 14px",
          borderBottom: `1px solid ${cfg.border}`,
          background: cfg.bg,
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <span style={{ fontSize: "16px" }}>{cfg.icon}</span>
        <span
          style={{
            fontWeight: 700,
            fontSize: "14px",
            color: cfg.color,
          }}
        >
          Trust Score: {Math.round(trust.final_score)}/100 —{" "}
          {trust.level.toUpperCase()} CONFIDENCE
        </span>
      </div>

      <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: "12px" }}>
        {/* Evidence */}
        {trust.evidence_items?.length > 0 && (
          <div>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "#16a34a",
                marginBottom: "6px",
              }}
            >
              ✅ Evidence Supporting This Answer:
            </div>
            {trust.evidence_items.map((e, i) => (
              <div
                key={i}
                style={{
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  display: "flex",
                  gap: "6px",
                  marginBottom: "3px",
                }}
              >
                <span style={{ color: "#16a34a", flexShrink: 0 }}>•</span>
                {e}
              </div>
            ))}
          </div>
        )}

        {/* Warnings */}
        {trust.warnings?.length > 0 && (
          <div>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "#b45309",
                marginBottom: "6px",
              }}
            >
              ⚠️ Warnings:
            </div>
            {trust.warnings.map((w, i) => (
              <div
                key={i}
                style={{
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  display: "flex",
                  gap: "6px",
                  marginBottom: "3px",
                }}
              >
                <span style={{ color: "#b45309", flexShrink: 0 }}>•</span>
                {w}
              </div>
            ))}
          </div>
        )}

        {/* Factor breakdown */}
        {trust.factors?.length > 0 && (
          <div>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: "8px",
              }}
            >
              📊 Score Breakdown:
            </div>
            {trust.factors.map((f, i) => (
              <FactorBar key={i} factor={f} />
            ))}
          </div>
        )}

        {/* Contradictions */}
        {hasContradictions && (
          <div>
            {trust.contradictions.map((c, i) => (
              <ContradictionCard key={i} c={c} onViewPage={onViewPage} />
            ))}
          </div>
        )}

        {/* Summary */}
        {trust.summary && (
          <div
            style={{
              padding: "8px 12px",
              background: `${cfg.color}11`,
              border: `1px solid ${cfg.border}`,
              borderRadius: "6px",
              fontSize: "12px",
              color: cfg.color,
              fontStyle: "italic",
              lineHeight: 1.5,
            }}
          >
            💡 {trust.summary}
          </div>
        )}

        {/* Second Opinion */}
        <div style={{ paddingTop: "4px", borderTop: "1px solid var(--border-subtle)" }}>
          {secondOpinionState === "idle" && (
            <button
              onClick={handleSecondOpinion}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 14px",
                border: "1px solid var(--border-default)",
                borderRadius: "6px",
                background: "none",
                cursor: "pointer",
                fontFamily: "var(--font-body)",
                fontSize: "13px",
                color: "var(--text-secondary)",
                transition: "border-color 120ms, color 120ms",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--brand)";
                (e.currentTarget as HTMLElement).style.color = "var(--brand)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border-default)";
                (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)";
              }}
            >
              🔄 Get Second Opinion
            </button>
          )}

          {secondOpinionState === "loading" && (
            <div
              style={{
                fontSize: "12px",
                color: "var(--text-tertiary)",
                fontStyle: "italic",
                padding: "6px 0",
              }}
            >
              🔄 Re-analyzing with different approach...
            </div>
          )}

          {secondOpinionState === "done" && secondAnswer && (
            <div>
              <div
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginBottom: "8px",
                }}
              >
                🔄 Second Opinion (Alternative Retrieval):
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    padding: "10px",
                    border: "1px solid var(--border-default)",
                    borderRadius: "8px",
                    background: "var(--surface-sunken)",
                    fontSize: "12px",
                    color: "var(--text-primary)",
                    lineHeight: 1.5,
                  }}
                >
                  <div
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      color: "var(--text-tertiary)",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                    }}
                  >
                    Original Answer
                  </div>
                  (See response above)
                </div>
                <div
                  style={{
                    padding: "10px",
                    border: "1px solid var(--brand)",
                    borderRadius: "8px",
                    background: "var(--brand-ghost)",
                    fontSize: "12px",
                    color: "var(--text-primary)",
                    lineHeight: 1.5,
                  }}
                >
                  <div
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      color: "var(--brand)",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                    }}
                  >
                    Alternative Retrieval
                  </div>
                  {secondAnswer}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
