import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

// Simple inline renderer — no external dependency needed
function MsgText({ text, color }) {
  return (
    <div style={{ fontSize: 14, color, lineHeight: 1.75, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
      {text}
    </div>
  );
}

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function SharedChat() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { dark } = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [forking, setForking] = useState(false);
  const [forked, setForked] = useState(null);
  const isLoggedIn = !!localStorage.getItem("token");

  const t = dark
    ? { bg: "#0d1117", card: "#161b22", border: "#30363d", text: "#e6edf3", sub: "#8b949e" }
    : { bg: "#f6f8fa", card: "#ffffff", border: "#d0d7de", text: "#1f2328", sub: "#636c76" };

  useEffect(() => {
    fetch(`${BASE}/qa/shared/${token}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(setData)
      .catch(() => setError("This link is invalid or has expired."));
  }, [token]);

  const fork = async () => {
    if (!isLoggedIn) { navigate(`/login?redirect=/shared/${token}`); return; }
    setForking(true);
    try {
      const r = await fetch(`${BASE}/qa/shared/${token}/fork`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });
      const d = await r.json();
      setForked(d.new_session_id);
    } catch { setError("Failed to fork chat."); }
    setForking(false);
  };

  if (error) return (
    <div style={{ minHeight: "100vh", background: t.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: "Inter,sans-serif", gap: 16 }}>
      <div style={{ fontSize: 48 }}>🔗</div>
      <p style={{ color: "#f85149", fontSize: 16, fontWeight: 600 }}>{error}</p>
      <button onClick={() => navigate("/")} style={{ background: "#1f6feb", color: "#fff", border: "none", padding: "9px 22px", borderRadius: 8, cursor: "pointer", fontFamily: "inherit", fontSize: 13 }}>Go Home</button>
    </div>
  );

  if (!data) return (
    <div style={{ minHeight: "100vh", background: t.bg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Inter,sans-serif" }}>
      <p style={{ color: t.sub }}>Loading shared chat…</p>
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", background: t.bg, fontFamily: "Inter,sans-serif" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');`}</style>
      {/* Header */}
      <div style={{ background: t.card, borderBottom: `1px solid ${t.border}`, padding: "14px 24px", display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 32, height: 32, background: "linear-gradient(135deg,#1f6feb,#8250df)", borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>🧠</div>
        <div>
          <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: t.text }}>DocuMind <span style={{ background: "linear-gradient(135deg,#1f6feb,#8250df)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AI</span></p>
          <p style={{ margin: 0, fontSize: 11, color: t.sub }}>Shared Chat — {data.title}</p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          {forked ? (
            <button onClick={() => navigate(`/chat?session=${forked}`)} style={{ background: "#3fb950", color: "#fff", border: "none", padding: "8px 18px", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "inherit" }}>
              ✓ Continue in My Chat →
            </button>
          ) : (
            <button onClick={fork} disabled={forking} style={{ background: "linear-gradient(135deg,#1f6feb,#8250df)", color: "#fff", border: "none", padding: "8px 18px", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "inherit", opacity: forking ? 0.7 : 1 }}>
              {forking ? "Forking…" : isLoggedIn ? "🍴 Continue This Chat" : "🔑 Login to Continue"}
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{ maxWidth: 780, margin: "0 auto", padding: "24px 16px" }}>
        <div style={{ background: "rgba(31,111,235,0.06)", border: "1px solid rgba(31,111,235,0.2)", borderRadius: 10, padding: "10px 16px", marginBottom: 20, fontSize: 12, color: t.sub }}>
          🔗 This is a shared read-only view of a DocuMindAI chat. {isLoggedIn ? 'Click "Continue This Chat" to fork it into your account.' : 'Login to continue this conversation.'}
        </div>

        {data.messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 24 }}>
            {/* Question */}
            <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
              <div style={{ background: "linear-gradient(135deg,#1f6feb,#8250df)", color: "#fff", padding: "10px 16px", borderRadius: "16px 16px 4px 16px", maxWidth: "75%", fontSize: 14, lineHeight: 1.6 }}>
                {msg.question}
              </div>
            </div>
            {/* Answer */}
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg,#1f6feb,#8250df)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, flexShrink: 0, marginTop: 2 }}>🧠</div>
              <div style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: "4px 16px 16px 16px", padding: "12px 16px", flex: 1, fontSize: 14, color: t.text, lineHeight: 1.7 }}>
                <MsgText text={msg.answer} color={t.text} />
                {msg.sources?.length > 0 && (
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${t.border}`, fontSize: 11, color: t.sub }}>
                    📎 Sources: {msg.sources.join(", ")}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
