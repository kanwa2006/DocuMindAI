import React, { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

// All tools from Fast PDF Bharat
const PDF_TOOLS = [
  { icon: "🔗", label: "Merge PDF",     url: "https://fastpdf.yuvakishore.com/tool/merge",        desc: "Combine multiple PDFs" },
  { icon: "🗜️", label: "Compress PDF",  url: "https://fastpdf.yuvakishore.com/tool/compress",     desc: "Reduce file size" },
  { icon: "✂️", label: "Split PDF",     url: "https://fastpdf.yuvakishore.com/tool/split",        desc: "Extract pages" },
  { icon: "📄", label: "PDF to Word",   url: "https://fastpdf.yuvakishore.com/tool/pdf-to-word",  desc: "Convert to DOCX" },
  { icon: "📝", label: "Word to PDF",   url: "https://fastpdf.yuvakishore.com/tool/word-to-pdf",  desc: "Convert DOCX to PDF" },
  { icon: "📊", label: "PDF to Excel",  url: "https://fastpdf.yuvakishore.com/tool/pdf-to-excel", desc: "Extract tables" },
  { icon: "📈", label: "Excel to PDF",  url: "https://fastpdf.yuvakishore.com/tool/excel-to-pdf", desc: "Spreadsheet to PDF" },
  { icon: "🖼️", label: "IMG to PDF",    url: "https://fastpdf.yuvakishore.com/tool/img-to-pdf",   desc: "Images to PDF" },
  { icon: "🖼️", label: "PDF to IMG",    url: "https://fastpdf.yuvakishore.com/tool/pdf-to-img",   desc: "Pages to JPG/PNG" },
  { icon: "📑", label: "PPT to PDF",    url: "https://fastpdf.yuvakishore.com/tool/ppt-to-pdf",   desc: "Presentation to PDF" },
  { icon: "🔒", label: "Protect PDF",   url: "https://fastpdf.yuvakishore.com/tool/protect",      desc: "Add password" },
  { icon: "🔓", label: "Unlock PDF",    url: "https://fastpdf.yuvakishore.com/tool/unlock",       desc: "Remove password" },
  { icon: "🔄", label: "Rotate PDF",    url: "https://fastpdf.yuvakishore.com/tool/rotate",       desc: "Flip pages" },
  { icon: "📋", label: "Organize PDF",  url: "https://fastpdf.yuvakishore.com/tool/organize",     desc: "Reorder & remove pages" },
  { icon: "📱", label: "QR Generator",  url: "https://fastpdf.yuvakishore.com/tool/qr-generator", desc: "Create QR codes" },
];

export default function Navbar({ onLogout }) {
  const loc = useLocation();
  const nav = useNavigate();
  const { dark, toggle } = useTheme();
  const [showProfile, setShowProfile] = useState(false);
  const [showPdfTools, setShowPdfTools] = useState(false);
  const username = localStorage.getItem("username") || "User";
  const dropRef = useRef(null);
  const pdfRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) setShowProfile(false);
      if (pdfRef.current && !pdfRef.current.contains(e.target)) setShowPdfTools(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const t = dark
    ? { bg: "#0d1117", border: "#21262d", text: "#e6edf3", sub: "#8b949e", hover: "#161b22", drop: "#161b22", dropBorder: "#30363d" }
    : { bg: "#ffffff", border: "#d0d7de", text: "#1f2328", sub: "#636c76", hover: "#f6f8fa", drop: "#ffffff", dropBorder: "#d0d7de" };

  return (
    <nav style={{ background: t.bg, borderBottom: `1px solid ${t.border}`, height: 60, display: "flex", alignItems: "center", padding: "0 20px", gap: 4, fontFamily: "Inter, sans-serif", position: "sticky", top: 0, zIndex: 200 }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        .nav-link{transition:all 0.15s} .nav-link:hover{background:${t.hover} !important}
        .drop-item:hover{background:${t.hover} !important}
        .theme-btn:hover{background:${t.hover} !important}
        .pdf-tool-item:hover{background:${dark ? "rgba(31,111,235,0.12)" : "rgba(9,105,218,0.06)"} !important}
        .pdf-panel{animation:slideDown 0.18s ease}
        @keyframes slideDown{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
      `}</style>

      {/* Logo */}
      <Link to="/chat" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, marginRight: 12 }}>
        <div style={{ width: 32, height: 32, background: "linear-gradient(135deg,#1f6feb,#8250df)", borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>🧠</div>
        <span style={{ fontWeight: 700, fontSize: 15, color: t.text }}>DocuMind <span style={{ background: "linear-gradient(135deg,#1f6feb,#8250df)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AI</span></span>
      </Link>

      {/* Nav Links */}
      {[{ to: "/chat", label: "💬 Chat" }, { to: "/documents", label: "📄 Documents" }].map(({ to, label }) => (
        <Link key={to} to={to} className="nav-link" style={{ textDecoration: "none", padding: "6px 12px", borderRadius: 8, fontSize: 13, fontWeight: 500, color: loc.pathname.startsWith(to) ? "#1f6feb" : t.sub, background: loc.pathname.startsWith(to) ? (dark ? "rgba(31,111,235,0.12)" : "rgba(31,111,235,0.08)") : "transparent" }}>
          {label}
        </Link>
      ))}

      {/* ── Fast PDF Bharat Tools Button ── */}
      <div ref={pdfRef} style={{ position: "relative" }}>
        <button
          onMouseEnter={() => setShowPdfTools(true)}
          onClick={() => setShowPdfTools(s => !s)}
          style={{ display: "flex", alignItems: "center", gap: 6, background: showPdfTools ? (dark ? "rgba(255,165,0,0.1)" : "rgba(255,140,0,0.08)") : "transparent", border: `1px solid ${showPdfTools ? "rgba(255,140,0,0.3)" : "transparent"}`, borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 13, fontWeight: 500, color: "#f0a500", fontFamily: "inherit", transition: "all 0.15s" }}>
          ⚡ PDF Tools
          <span style={{ fontSize: 9, opacity: 0.7 }}>▼</span>
        </button>

        {showPdfTools && (
          <div className="pdf-panel" onMouseLeave={() => setShowPdfTools(false)}
            style={{ position: "absolute", left: 0, top: "calc(100% + 8px)", background: t.drop, border: `1px solid ${t.dropBorder}`, borderRadius: 14, padding: "10px", width: 340, boxShadow: "0 12px 40px rgba(0,0,0,0.2)", zIndex: 400 }}>

            {/* Header */}
            <div style={{ padding: "6px 10px 10px", borderBottom: `1px solid ${t.border}`, marginBottom: 8 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 700, color: t.text }}>⚡ Fast PDF Bharat</p>
              <p style={{ margin: "2px 0 0", fontSize: 11, color: t.sub }}>Free PDF tools by Yuva Kishore · Opens in new tab</p>
            </div>

            {/* Tools grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4 }}>
              {PDF_TOOLS.map(({ icon, label, url, desc }) => (
                <a key={label} href={url} target="_blank" rel="noopener noreferrer" className="pdf-tool-item"
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, padding: "8px 6px", borderRadius: 8, textDecoration: "none", transition: "all 0.15s", cursor: "pointer" }}>
                  <span style={{ fontSize: 18 }}>{icon}</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: t.text, textAlign: "center", lineHeight: 1.2 }}>{label}</span>
                  <span style={{ fontSize: 9, color: t.sub, textAlign: "center", lineHeight: 1.2 }}>{desc}</span>
                </a>
              ))}
            </div>

            {/* Footer link */}
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${t.border}`, textAlign: "center" }}>
              <a href="https://fastpdf.yuvakishore.com" target="_blank" rel="noopener noreferrer"
                style={{ fontSize: 11, color: "#f0a500", textDecoration: "none", fontWeight: 600 }}>
                View all tools at fastpdf.yuvakishore.com →
              </a>
            </div>
          </div>
        )}
      </div>

      <div style={{ flex: 1 }} />

      {/* Dark/Light Toggle */}
      <button className="theme-btn" onClick={toggle}
        style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 8, padding: "6px 10px", cursor: "pointer", fontSize: 16, marginRight: 8, transition: "all 0.15s" }}>
        {dark ? "☀️" : "🌙"}
      </button>

      {/* Profile Dropdown */}
      <div ref={dropRef} style={{ position: "relative" }}>
        <button onClick={() => setShowProfile(s => !s)}
          style={{ display: "flex", alignItems: "center", gap: 8, background: showProfile ? t.hover : "transparent", border: `1px solid ${showProfile ? t.border : "transparent"}`, borderRadius: 10, padding: "5px 10px 5px 6px", cursor: "pointer", transition: "all 0.15s" }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg,#1f6feb,#8250df)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 700 }}>
            {username[0]?.toUpperCase()}
          </div>
          <span style={{ fontSize: 13, fontWeight: 500, color: t.text }}>{username}</span>
          <span style={{ fontSize: 10, color: t.sub }}>{showProfile ? "▲" : "▼"}</span>
        </button>

        {showProfile && (
          <div style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", background: t.drop, border: `1px solid ${t.dropBorder}`, borderRadius: 12, padding: "8px", minWidth: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.15)", zIndex: 300 }}>
            <div style={{ padding: "8px 12px", borderBottom: `1px solid ${t.border}`, marginBottom: 4 }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: t.text }}>{username}</p>
              <p style={{ margin: "2px 0 0", fontSize: 11, color: t.sub }}>Signed in</p>
            </div>
            {[
              { icon: "👤", label: "Profile & Settings", action: () => { nav("/profile"); setShowProfile(false); } },
              { icon: "📄", label: "My Documents",       action: () => { nav("/documents"); setShowProfile(false); } },
            ].map(({ icon, label, action }) => (
              <button key={label} className="drop-item" onClick={action}
                style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, background: "transparent", border: "none", borderRadius: 8, padding: "9px 12px", cursor: "pointer", fontSize: 13, color: t.text, fontFamily: "Inter, sans-serif", textAlign: "left", transition: "all 0.15s" }}>
                <span>{icon}</span>{label}
              </button>
            ))}
            <div style={{ borderTop: `1px solid ${t.border}`, marginTop: 4, paddingTop: 4 }}>
              <button className="drop-item" onClick={onLogout}
                style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, background: "transparent", border: "none", borderRadius: 8, padding: "9px 12px", cursor: "pointer", fontSize: 13, color: "#f85149", fontFamily: "Inter, sans-serif", textAlign: "left", transition: "all 0.15s" }}>
                <span>🚪</span> Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
      {/* Subtle author credit — non-interactive, barely visible */}
      <span style={{
        fontSize: 9,
        opacity: 0.35,
        color: t.sub,
        fontFamily: "Inter, sans-serif",
        letterSpacing: "0.03em",
        userSelect: "none",
        pointerEvents: "none",
        marginLeft: 10,
        whiteSpace: "nowrap",
      }}>
        crafted by kanwa
      </span>
    </nav>
  );
}
