"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE, getCsrfToken } from "@/lib/api";

interface Bookmark {
  id: string;
  session_id: string;
  message_id: string;
  message_content: string;
  citations: any[] | null;
  tags: string[];
  workspace: string;
  created_at: string;
}

const WORKSPACE_ICONS: Record<string, string> = {
  general: "💬", exam: "📋", hr: "👥", study: "📚",
  research: "🔬", legal: "⚖️", finance: "📊",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function BookmarksPage() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch(`${API_BASE}/bookmarks`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => { setBookmarks(data || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const allTags = Array.from(new Set(bookmarks.flatMap((b) => b.tags || [])));
  const filtered = selectedTag
    ? bookmarks.filter((b) => b.tags?.includes(selectedTag))
    : bookmarks;

  // Group by workspace
  const byWorkspace: Record<string, Bookmark[]> = {};
  for (const bm of filtered) {
    const ws = bm.workspace || "general";
    if (!byWorkspace[ws]) byWorkspace[ws] = [];
    byWorkspace[ws].push(bm);
  }

  const removeBookmark = async (id: string) => {
    await fetch(`${API_BASE}/bookmarks/${id}`, {
      method: "DELETE",
      credentials: "include",
      headers: { "X-CSRF-Token": getCsrfToken() },
    });
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  };

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 0 }}>
      {/* Tag cloud sidebar */}
      <aside style={{ width: "220px", flexShrink: 0, borderRight: "1px solid var(--border-subtle)", padding: "24px 12px", overflowY: "auto" }}>
        <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "12px" }}>Filter by tag</div>
        <button
          onClick={() => setSelectedTag(null)}
          style={{
            display: "block", width: "100%", textAlign: "left", padding: "6px 10px",
            borderRadius: "6px", border: "none", cursor: "pointer",
            background: selectedTag === null ? "var(--brand-ghost)" : "transparent",
            color: selectedTag === null ? "var(--brand)" : "var(--text-secondary)",
            fontFamily: "var(--font-body)", fontSize: "13px", marginBottom: "4px",
          }}
        >
          All bookmarks
        </button>
        {allTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
            style={{
              display: "block", width: "100%", textAlign: "left", padding: "6px 10px",
              borderRadius: "6px", border: "none", cursor: "pointer", marginBottom: "2px",
              background: selectedTag === tag ? "var(--brand-ghost)" : "transparent",
              color: selectedTag === tag ? "var(--brand)" : "var(--text-secondary)",
              fontFamily: "var(--font-body)", fontSize: "13px",
            }}
          >
            🏷 {tag}
          </button>
        ))}
        {allTags.length === 0 && (
          <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", fontStyle: "italic" }}>No tags yet</div>
        )}
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
        <div style={{ maxWidth: "800px" }}>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: "24px", color: "var(--text-primary)", margin: "0 0 4px", fontWeight: 400 }}>
            🔖 Saved Responses
          </h1>
          <p style={{ fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 24px" }}>
            {bookmarks.length} bookmark{bookmarks.length !== 1 ? "s" : ""} saved
          </p>

          {loading && (
            <div style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-secondary)" }}>Loading...</div>
          )}

          {!loading && filtered.length === 0 && (
            <div style={{ padding: "64px 16px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
              <div style={{ fontSize: "40px", opacity: 0.35 }}>🔖</div>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "14px", color: "var(--text-secondary)" }}>
                {selectedTag ? `No bookmarks tagged "${selectedTag}"` : "No bookmarks yet."}
              </div>
              {!selectedTag && (
                <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)" }}>
                  Save any AI response with the 🔖 button to find it here later.
                </div>
              )}
            </div>
          )}

          {Object.entries(byWorkspace).map(([ws, items]) => (
            <section key={ws} style={{ marginBottom: "32px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                <span style={{ fontSize: "18px" }}>{WORKSPACE_ICONS[ws] || "💬"}</span>
                <span style={{ fontFamily: "var(--font-body)", fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", textTransform: "capitalize" }}>{ws} Workspace</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-tertiary)" }}>{items.length}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {items.map((bm) => (
                  <div key={bm.id} style={{ background: "var(--surface-raised)", border: "1px solid var(--border-default)", borderRadius: "12px", padding: "16px" }}>
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px", marginBottom: "8px" }}>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                        <span style={{ fontFamily: "var(--font-body)", fontSize: "11px", color: "var(--text-tertiary)" }}>{timeAgo(bm.created_at)}</span>
                        {(bm.tags || []).map((tag) => (
                          <span key={tag} style={{ padding: "2px 8px", background: "var(--brand-ghost)", color: "var(--brand)", borderRadius: "999px", fontSize: "11px", fontFamily: "var(--font-body)" }}>
                            {tag}
                          </span>
                        ))}
                      </div>
                      <div style={{ display: "flex", gap: "6px", flexShrink: 0 }}>
                        <button
                          onClick={() => router.push(`/${ws === "general" ? "" : ws}?chat=${bm.session_id}`)}
                          style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", color: "var(--brand)", fontFamily: "var(--font-body)", padding: "2px 6px", borderRadius: "4px" }}
                        >
                          Open →
                        </button>
                        <button
                          onClick={() => removeBookmark(bm.id)}
                          style={{ background: "none", border: "none", cursor: "pointer", fontSize: "12px", color: "var(--text-tertiary)", fontFamily: "var(--font-body)", padding: "2px 6px", borderRadius: "4px" }}
                          title="Remove bookmark"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    <div style={{
                      fontFamily: "var(--font-body)", fontSize: "13px", color: "var(--text-primary)",
                      lineHeight: 1.6, maxHeight: "80px", overflow: "hidden",
                      display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical",
                    }}>
                      {(() => {
                        try { return JSON.parse(bm.message_content).answer || bm.message_content; } catch { return bm.message_content; }
                      })()}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </main>
    </div>
  );
}
