"use client";

/**
 * Task 6-R2: Research Gap Identification panel.
 * 3-tab panel: Gaps | Conflicts | Consensus
 * Gaps section: yellow-tinted left border (3px solid var(--warning-border)),
 *   header "🔍 Research Gaps Identified:", numbered list.
 */

import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { API_BASE } from "../lib/api";

type TabKey = "gaps" | "conflicts" | "consensus";

interface GapsData {
  gaps: string[];
  conflicts: string[];
  consensus: string[];
}

interface Props {
  documentIds: string[];
  onClose: () => void;
}

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "gaps",      label: "Gaps",      icon: "🔍" },
  { key: "conflicts", label: "Conflicts", icon: "⚡" },
  { key: "consensus", label: "Consensus", icon: "✅" },
];

function GapsList({ items }: { items: string[] }) {
  if (!items.length) {
    return (
      <div style={{ padding: "24px 0", textAlign: "center", color: "var(--text-tertiary)", fontFamily: "var(--font-body)", fontSize: "13px" }}>
        No gaps identified in the uploaded papers.
      </div>
    );
  }
  return (
    <div>
      {/* Yellow-tinted left border section with header */}
      <div style={{
        borderLeft: "3px solid var(--warning-border, #fbbf24)",
        background: "var(--warning-bg, #fffbeb)",
        borderRadius: "0 8px 8px 0",
        padding: "14px 16px",
        marginBottom: "16px",
      }}>
        <div style={{
          fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 700,
          color: "var(--warning-text, #92400e)", marginBottom: "12px",
        }}>
          🔍 Research Gaps Identified:
        </div>
        <ol style={{ margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "10px" }}>
          {items.map((gap, i) => (
            <li key={i} style={{
              fontFamily: "var(--font-body)", fontSize: "13px",
              color: "var(--text-primary)", lineHeight: 1.65,
            }}>
              {gap}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function ItemList({ items, icon, emptyText }: { items: string[]; icon: string; emptyText: string }) {
  if (!items.length) {
    return (
      <div style={{ padding: "24px 0", textAlign: "center", color: "var(--text-tertiary)", fontFamily: "var(--font-body)", fontSize: "13px" }}>
        {emptyText}
      </div>
    );
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {items.map((item, i) => (
        <div key={i} style={{
          padding: "12px 14px",
          background: "var(--surface-raised)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "8px",
          fontFamily: "var(--font-body)", fontSize: "13px",
          color: "var(--text-primary)", lineHeight: 1.65,
          display: "flex", gap: "10px", alignItems: "flex-start",
        }}>
          <span style={{ flexShrink: 0, fontSize: "15px" }}>{icon}</span>
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}

export default function ResearchGapsPanel({ documentIds, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<GapsData | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("gaps");

  const fetchGaps = useCallback(async () => {
    if (!documentIds.length) {
      toast.error("Upload documents first to identify research gaps.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/research/gaps`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_ids: documentIds }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Gap analysis failed.");
      }
      const json = await res.json();
      setData({ gaps: json.gaps || [], conflicts: json.conflicts || [], consensus: json.consensus || [] });
    } catch (e: any) {
      toast.error(e.message || "Failed to identify research gaps.");
    } finally {
      setLoading(false);
    }
  }, [documentIds]);

  const panelStyle: React.CSSProperties = {
    position: "fixed", top: 0, right: 0, bottom: 0,
    width: "min(560px, 100vw)",
    background: "var(--surface-base)",
    borderLeft: "1px solid var(--border-default)",
    boxShadow: "-8px 0 32px rgba(0,0,0,0.12)",
    zIndex: 50,
    display: "flex", flexDirection: "column",
    overflowY: "hidden",
  };

  const currentItems = data ? data[activeTab] : [];

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{
        padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)",
        display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0,
      }}>
        <div style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" }}>
          🔬 Research Gap Analysis
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={fetchGaps}
            disabled={loading}
            className="btn btn-secondary btn-sm"
            style={{ height: "32px", fontSize: "12px" }}
          >
            {loading ? "Analyzing…" : data ? "🔄 Re-analyze" : "🔍 Analyze"}
          </button>
          <button
            onClick={onClose}
            className="btn-icon btn-ghost"
            style={{ width: "32px", height: "32px", fontSize: "18px" }}
          >
            ×
          </button>
        </div>
      </div>

      {/* Tabs */}
      {data && (
        <div style={{ display: "flex", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                flex: 1, height: "42px",
                fontFamily: "var(--font-body)", fontSize: "13px",
                borderTop: "none", borderLeft: "none", borderRight: "none",
                borderBottom: activeTab === tab.key ? "2px solid var(--brand)" : "2px solid transparent",
                color: activeTab === tab.key ? "var(--brand)" : "var(--text-secondary)",
                background: "none",
                cursor: "pointer",
                fontWeight: activeTab === tab.key ? 600 : 400,
                display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
              }}
            >
              {tab.icon} {tab.label}
              {data[tab.key].length > 0 && (
                <span style={{
                  background: activeTab === tab.key ? "var(--brand)" : "var(--border-default)",
                  color: activeTab === tab.key ? "#fff" : "var(--text-secondary)",
                  borderRadius: "999px", fontSize: "10px", fontWeight: 600,
                  padding: "0 6px", minWidth: "18px", textAlign: "center",
                }}>
                  {data[tab.key].length}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {loading && (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-tertiary)", fontFamily: "var(--font-body)", fontSize: "14px" }}>
            Analyzing research papers…
          </div>
        )}

        {!loading && !data && (
          <div style={{ textAlign: "center", padding: "48px 16px" }}>
            <div style={{ fontSize: "52px", marginBottom: "16px" }}>🔍</div>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px" }}>
              Identify gaps, conflicts, and consensus across your uploaded research papers.
            </div>
            <button onClick={fetchGaps} className="btn btn-primary" style={{ height: "40px" }}>
              Analyze Research Gaps
            </button>
          </div>
        )}

        {data && !loading && (
          <>
            {activeTab === "gaps" && (
              <GapsList items={data.gaps} />
            )}
            {activeTab === "conflicts" && (
              <ItemList
                items={data.conflicts}
                icon="⚡"
                emptyText="No conflicting findings identified across the uploaded papers."
              />
            )}
            {activeTab === "consensus" && (
              <ItemList
                items={data.consensus}
                icon="✅"
                emptyText="No strong consensus areas identified across the uploaded papers."
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
