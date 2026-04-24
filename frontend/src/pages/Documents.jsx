import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { docsAPI } from "../api/client";
import { useTheme } from "../context/ThemeContext";

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [drag, setDrag] = useState(false);
  const [lastUploadedName, setLastUploadedName] = useState("");
  const { dark } = useTheme();
  const navigate = useNavigate();

  const fetchDocs = () => docsAPI.list().then((r) => setDocs(r.data)).catch(() => {});
  useEffect(() => { fetchDocs(); const iv = setInterval(fetchDocs, 5000); return () => clearInterval(iv); }, []);

  const handleUpload = async (files) => {
    const pdfs = Array.from(files).filter(f => f.name.endsWith(".pdf"));
    if (!pdfs.length) return;
    setUploading(true); setMessage("");
    try {
      for (const f of pdfs) await docsAPI.upload(f);
      setLastUploadedName(pdfs[pdfs.length - 1].name);
      setMessage(`✅ ${pdfs.length} file(s) uploaded — indexing in background`);
      fetchDocs();
    } catch (e) { setMessage("❌ " + (e.response?.data?.detail || e.message)); }
    setUploading(false);
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"?`)) return;
    await docsAPI.delete(id); fetchDocs();
  };

  const t = dark
    ? { bg: "#0d1117", card: "#161b22", border: "#30363d", text: "#e6edf3", sub: "#8b949e", row: "#161b22", rowHover: "#1c2128" }
    : { bg: "#f6f8fa", card: "#ffffff", border: "#d0d7de", text: "#1f2328", sub: "#636c76", row: "#ffffff", rowHover: "#f6f8fa" };

  const statusCfg = {
    Processing: { color: "#d29922", bg: "rgba(210,153,34,0.12)", dot: "#d29922" },
    Ready:      { color: "#3fb950", bg: "rgba(63,185,80,0.12)",  dot: "#3fb950" },
    Failed:     { color: "#f85149", bg: "rgba(248,81,73,0.12)",  dot: "#f85149" },
  };

  const ready = docs.filter(d => d.status === "Ready").length;
  const processing = docs.filter(d => d.status === "Processing").length;

  return (
    <div style={{ minHeight: "calc(100vh - 60px)", background: t.bg, padding: "32px 24px", fontFamily: "Inter, sans-serif" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'); .doc-row:hover{background:${t.rowHover} !important} .del-btn:hover{background:rgba(248,81,73,0.18) !important} .view-btn:hover{background:rgba(31,111,235,0.18) !important}`}</style>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: t.text }}>📄 My Documents</h1>
          <p style={{ margin: "6px 0 0", fontSize: 14, color: t.sub }}>Upload, view, and manage your personal knowledge base</p>
        </div>
        <div style={{ background: dark ? "rgba(31,111,235,0.08)" : "rgba(9,105,218,0.05)", border: `1px solid ${dark ? "rgba(31,111,235,0.25)" : "rgba(9,105,218,0.2)"}`, borderRadius: 12, padding: "12px 16px", marginBottom: 20, display: "flex", gap: 10 }}>
          <span style={{ fontSize: 18 }}>🔒</span>
          <div>
            <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: dark ? "#58a6ff" : "#0969da" }}>Your files are completely private</p>
            <p style={{ margin: "3px 0 0", fontSize: 12, color: t.sub }}>All documents stored in your private workspace. No one else can access your files.</p>
          </div>
        </div>
        {docs.length > 0 && (
          <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
            {[{ label: "Total Files", value: docs.length, icon: "📁", color: "#1f6feb" }, { label: "Ready", value: ready, icon: "✅", color: "#3fb950" }, { label: "Processing", value: processing, icon: "⏳", color: "#d29922" }].map(({ label, value, icon, color }) => (
              <div key={label} style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: 12, padding: "14px 20px", flex: 1, display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 22 }}>{icon}</span>
                <div><p style={{ margin: 0, fontSize: 22, fontWeight: 700, color }}>{value}</p><p style={{ margin: 0, fontSize: 12, color: t.sub }}>{label}</p></div>
              </div>
            ))}
          </div>
        )}
        <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={(e) => { e.preventDefault(); setDrag(false); handleUpload(e.dataTransfer.files); }}
          style={{ border: `2px dashed ${drag ? "#1f6feb" : t.border}`, background: drag ? (dark ? "rgba(31,111,235,0.07)" : "rgba(9,105,218,0.04)") : t.card, borderRadius: 16, padding: "36px 24px", textAlign: "center", marginBottom: 8, transition: "all 0.2s" }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>☁️</div>
          <p style={{ margin: "0 0 6px", fontSize: 15, fontWeight: 600, color: t.text }}>Drag & drop PDF files here</p>
          <p style={{ margin: "0 0 18px", fontSize: 13, color: t.sub }}>or click to browse your files</p>
          <label style={{ background: "linear-gradient(135deg,#1f6feb,#8250df)", color: "#fff", padding: "11px 28px", borderRadius: 10, cursor: uploading ? "not-allowed" : "pointer", fontWeight: 600, fontSize: 14, opacity: uploading ? 0.5 : 1, display: "inline-block" }}>
            {uploading ? "⏳ Uploading..." : "📂 Choose PDF Files"}
            <input type="file" accept=".pdf" multiple onChange={(e) => handleUpload(e.target.files)} style={{ display: "none" }} disabled={uploading} />
          </label>
          {message && <p style={{ margin: "14px 0 0", fontSize: 13, color: message.startsWith("✅") ? "#3fb950" : "#f85149" }}>{message}</p>}
        </div>
        {lastUploadedName && (
          <div style={{ background: dark ? "rgba(210,153,34,0.08)" : "rgba(210,153,34,0.06)", border: "1px solid rgba(210,153,34,0.3)", borderRadius: 10, padding: "10px 16px", marginBottom: 20, display: "flex", gap: 10 }}>
            <span>⚠️</span>
            <p style={{ margin: 0, fontSize: 12, color: t.sub }}>If <strong style={{ color: t.text }}>{lastUploadedName}</strong> contains image-based formulas, the AI may not read them fully.</p>
          </div>
        )}
        {docs.length === 0 ? (
          <div style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: 16, padding: "48px 24px", textAlign: "center" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📭</div>
            <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: t.text }}>No documents yet</p>
            <p style={{ margin: "6px 0 0", fontSize: 13, color: t.sub }}>Upload your first PDF above to get started</p>
          </div>
        ) : (
          <div style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: 16, overflow: "hidden" }}>
            <div style={{ padding: "12px 20px", borderBottom: `1px solid ${t.border}`, display: "grid", gridTemplateColumns: "1fr 130px 100px 170px", gap: 12 }}>
              {["File Name", "Uploaded", "Status", "Actions"].map(h => (
                <span key={h} style={{ fontSize: 11, fontWeight: 600, color: t.sub, textTransform: "uppercase", letterSpacing: "0.5px" }}>{h}</span>
              ))}
            </div>
            {docs.map((doc, i) => {
              const s = statusCfg[doc.status] || statusCfg.Processing;
              return (
                <div key={doc.id} className="doc-row" style={{ padding: "14px 20px", borderBottom: i < docs.length - 1 ? `1px solid ${t.border}` : "none", display: "grid", gridTemplateColumns: "1fr 130px 100px 170px", gap: 12, alignItems: "center", background: t.row, transition: "background 0.15s" }}>
                  <div onClick={() => navigate(`/documents/${doc.id}`)} style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0, cursor: "pointer" }}>
                    <div style={{ width: 34, height: 34, background: "rgba(31,111,235,0.1)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 }}>📑</div>
                    <div style={{ minWidth: 0 }}>
                      <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: dark ? "#58a6ff" : "#0969da", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", textDecoration: "underline dotted" }}>{doc.original_name}</p>
                      <p style={{ margin: 0, fontSize: 10, color: t.sub }}>Click to view</p>
                    </div>
                  </div>
                  <span style={{ fontSize: 12, color: t.sub }}>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, background: s.bg, color: s.color, padding: "4px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, width: "fit-content" }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: s.dot, animation: doc.status === "Processing" ? "pulse 1.5s infinite" : "none" }} />
                    {doc.status}
                    <style>{`@keyframes pulse{0%,100%{opacity:0.4}50%{opacity:1}}`}</style>
                  </span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="view-btn" onClick={() => navigate(`/documents/${doc.id}`)}
                      style={{ background: "rgba(31,111,235,0.08)", border: "1px solid rgba(31,111,235,0.2)", color: "#1f6feb", padding: "6px 12px", borderRadius: 7, cursor: "pointer", fontSize: 12, fontWeight: 500, fontFamily: "inherit", transition: "all 0.15s" }}>
                      👁 View
                    </button>
                    <button className="del-btn" onClick={() => handleDelete(doc.id, doc.original_name)}
                      style={{ background: "rgba(248,81,73,0.08)", border: "1px solid rgba(248,81,73,0.2)", color: "#f85149", padding: "6px 12px", borderRadius: 7, cursor: "pointer", fontSize: 12, fontWeight: 500, fontFamily: "inherit", transition: "all 0.15s" }}>
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <p style={{ textAlign: "center", marginTop: 20, fontSize: 11, color: t.sub }}>🔐 All files encrypted in transit · Stored privately · Never shared</p>
      </div>
    </div>
  );
}
