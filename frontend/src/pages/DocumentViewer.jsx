import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { docsAPI, qaAPI } from "../api/client";
import { useTheme } from "../context/ThemeContext";

export default function DocumentViewer() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { dark } = useTheme();
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState("");
  const pdfUrl = docsAPI.getViewUrl(id);

  const t = dark
    ? { bg: "#0d1117", card: "#161b22", border: "#30363d", text: "#e6edf3", sub: "#8b949e", input: "#21262d" }
    : { bg: "#f6f8fa", card: "#ffffff", border: "#d0d7de", text: "#1f2328", sub: "#636c76", input: "#ffffff" };

  useEffect(() => {
    docsAPI.info(id)
      .then(r => { setInfo(r.data); setLoading(false); })
      .catch(() => { setError("Document not found or access denied."); setLoading(false); });
  }, [id]);

  const askQuestion = async () => {
    if (!question.trim() || asking) return;
    setAsking(true);
    setAnswer("");
    try {
      const res = await qaAPI.ask(question);
      setAnswer(res.data.answer);
    } catch {
      setAnswer("❌ Error getting answer. Please try again.");
    }
    setAsking(false);
  };

  if (loading) return (
    <div style={{ minHeight: "100vh", background: t.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: t.sub, fontFamily: "Inter, sans-serif" }}>Loading document...</p>
    </div>
  );

  if (error) return (
    <div style={{ minHeight: "100vh", background: t.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16 }}>
      <p style={{ color: "#f85149", fontFamily: "Inter, sans-serif", fontSize: 15 }}>🚫 {error}</p>
      <button onClick={() => navigate("/documents")} style={{ background: "#1f6feb", color: "#fff", border: "none", padding: "9px 20px", borderRadius: 8, cursor: "pointer", fontFamily: "Inter, sans-serif" }}>← Back to Documents</button>
    </div>
  );

  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)", background: t.bg, fontFamily: "Inter, sans-serif", overflow: "hidden" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');`}</style>

      {/* ── Left: PDF Viewer ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", background: t.card, borderBottom: `1px solid ${t.border}`, flexShrink: 0 }}>
          <button onClick={() => navigate("/documents")}
            style={{ background: "transparent", border: `1px solid ${t.border}`, color: t.sub, padding: "6px 12px", borderRadius: 7, cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>
            ← Back
          </button>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: t.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              📄 {info?.original_name}
            </p>
            <p style={{ margin: 0, fontSize: 11, color: t.sub }}>
              {info?.file_size} · Uploaded {new Date(info?.uploaded_at).toLocaleDateString()} · Status: {info?.status}
            </p>
          </div>
          <a href={pdfUrl} download={info?.original_name}
            style={{ background: "transparent", border: `1px solid ${t.border}`, color: t.sub, padding: "6px 12px", borderRadius: 7, cursor: "pointer", fontSize: 12, textDecoration: "none" }}>
            ⬇ Download
          </a>
        </div>

        {/* PDF iframe */}
        <iframe
          src={pdfUrl}
          title={info?.original_name}
          style={{ flex: 1, border: "none", background: "#525659" }}
        />
      </div>

      {/* ── Right: Info + Q&A Sidebar ── */}
      <div style={{ width: 340, flexShrink: 0, background: t.card, borderLeft: `1px solid ${t.border}`, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Document Info */}
        <div style={{ padding: "16px", borderBottom: `1px solid ${t.border}` }}>
          <p style={{ margin: "0 0 12px", fontSize: 13, fontWeight: 700, color: t.text }}>📋 Document Info</p>
          {[
            { label: "File name", value: info?.original_name },
            { label: "Size", value: info?.file_size },
            { label: "Uploaded", value: new Date(info?.uploaded_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }) },
            { label: "Status", value: info?.status },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: t.sub }}>{label}</span>
              <span style={{ fontSize: 12, color: t.text, fontWeight: 500, textAlign: "right", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{value}</span>
            </div>
          ))}
        </div>

        {/* Quick Q&A on this document */}
        <div style={{ padding: "16px", flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <p style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 700, color: t.text }}>💬 Ask about this document</p>
          <p style={{ margin: "0 0 12px", fontSize: 11, color: t.sub }}>Ask a quick question about this PDF while viewing it</p>

          {/* Suggested questions */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
            {["Summarize this document", "What are the main topics?", "Predict exam questions", "List key formulas"].map(q => (
              <button key={q} onClick={() => setQuestion(q)}
                style={{ background: dark ? "rgba(31,111,235,0.1)" : "rgba(9,105,218,0.06)", border: `1px solid ${dark ? "rgba(31,111,235,0.2)" : "rgba(9,105,218,0.15)"}`, color: dark ? "#58a6ff" : "#0969da", padding: "4px 10px", borderRadius: 20, cursor: "pointer", fontSize: 11, fontFamily: "inherit" }}>
                {q}
              </button>
            ))}
          </div>

          {/* Input */}
          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === "Enter" && askQuestion()}
              placeholder="Type your question..."
              style={{ flex: 1, background: t.input, border: `1px solid ${t.border}`, borderRadius: 8, padding: "8px 12px", color: t.text, fontFamily: "inherit", fontSize: 13, outline: "none" }}
            />
            <button onClick={askQuestion} disabled={asking || !question.trim()}
              style={{ background: "#1f6feb", color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", cursor: asking ? "not-allowed" : "pointer", fontSize: 12, fontWeight: 600, opacity: asking ? 0.5 : 1, fontFamily: "inherit", flexShrink: 0 }}>
              {asking ? "..." : "Ask"}
            </button>
          </div>

          {/* Answer */}
          {answer && (
            <div style={{ flex: 1, overflowY: "auto", background: dark ? "#0d1117" : "#f6f8fa", border: `1px solid ${t.border}`, borderRadius: 10, padding: "12px", fontSize: 13, color: t.text, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
              {answer}
            </div>
          )}
          {!answer && (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: t.sub, fontSize: 12, textAlign: "center", padding: "0 20px" }}>
              Ask a question above to get answers directly from this document
            </div>
          )}
        </div>

        {/* Privacy footer */}
        <div style={{ padding: "10px 16px", borderTop: `1px solid ${t.border}`, textAlign: "center" }}>
          <p style={{ margin: 0, fontSize: 10, color: t.sub }}>🔒 Only you can view this document</p>
        </div>
      </div>
    </div>
  );
}
