import React, { useState, useRef, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

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
  const pdfRef  = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) setShowProfile(false);
      if (pdfRef.current  && !pdfRef.current.contains(e.target))  setShowPdfTools(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // ChatGPT-style neutral palette — no purple, no blue gradients
  const t = dark
    ? { bg: "#212121", border: "#2f2f2f", text: "#ececec", sub: "#8e8ea0", hover: "#2a2a2a", drop: "#2f2f2f", dropBorder: "#3f3f3f", active: "#2a2a2a", activeText: "#ececec" }
    : { bg: "#ffffff", border: "#e5e5e5", text: "#0d0d0d", sub: "#6b6b6b", hover: "#f5f5f5", drop: "#ffffff", dropBorder: "#e5e5e5", active: "#f0f0f0", activeText: "#0d0d0d" };

  const initials = username.slice(0, 2).toUpperCase();

  return (
    <nav style={{ background: t.bg, borderBottom: `1px solid ${t.border}`, height: 56, display: "flex", alignItems: "center", padding: "0 16px", gap: 2, fontFamily: "Inter, sans-serif", position: "sticky", top: 0, zIndex: 200 }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        .nav-link { transition: background 0.12s; }
        .nav-link:hover { background: ${t.hover} !important; }
        .drop-item:hover { background: ${t.hover} !important; }
        .theme-btn:hover { background: ${t.hover} !important; }
        .pdf-tool-item:hover { background: ${t.hover} !important; }
        .pdf-panel { animation: slideDown 0.15s ease; }
        @keyframes slideDown { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }
      `}</style>

      {/* Logo — simple, text-based like ChatGPT */}
      <Link to="/chat" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, marginRight: 14 }}>
        <div style={{ width: 30, height: 30, background: dark ? "#424242" : "#171717", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15 }}>🧠</div>
        <span style={{ fontWeight: 600, fontSize: 15, color: t.text, letterSpacing: "-0.01em" }}>DocuMind AI</span>
      </Link>

      {/* Nav links — neutral, no color on active */}
      {[{ to: "/chat", label: "Chat" }, { to: "/documents", label: "Documents" }].map(({ to, label }) => {
        const active = loc.pathname.startsWith(to);
        return (
          <Link key={to} to={to} className="nav-link"
            style={{ textDecoration: "none", padding: "5px 11px", borderRadius: 7, fontSize: 13, fontWeight: active ? 600 : 400, color: active ? t.activeText : t.sub, background: active ? t.active : "transparent" }}>
            {label}
          </Link>
        );
      })}

      {/* PDF Tools dropdown — neutral styling */}
      <div ref={pdfRef} style={{ position: "relative" }}>
        <button
          onMouseEnter={() => setShowPdfTools(true)}
          onClick={() => setShowPdfTools(s => !s)}
          style={{ display: "flex", alignItems: "center", gap: 5, background: "transparent", border: "none", borderRadius: 7, padding: "5px 11px", cursor: "pointer", fontSize: 13, fontWeight: 400, color: t.sub, fontFamily: "inherit", transition: "all 0.12s" }}
          className="nav-link">
          PDF Tools
          <span style={{ fontSize: 9, opacity: 0.6 }}>▼</span>
        </button>

        {showPdfTools && (
          <div className="pdf-panel" onMouseLeave={() => setShowPdfTools(false)}
            style={{ position: "absolute", left: 0, top: "calc(100% + 6px)", background: t.drop, border: `1px solid ${t.dropBorder}`, borderRadius: 12, padding: "10px", width: 320, boxShadow: dark ? "0 8px 32px rgba(0,0,0,0.4)" : "0 8px 32px rgba(0,0,0,0.12)", zIndex: 400 }}>
            <div style={{ padding: "4px 8px 10px", borderBottom: `1px solid ${t.border}`, marginBottom: 8 }}>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: t.text }}>PDF Tools</p>
              <p style={{ margin: "2px 0 0", fontSize: 11, color: t.sub }}>Free tools · Opens in new tab</p>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 3 }}>
              {PDF_TOOLS.map(({ icon, label, url, desc }) => (
                <a key={label} href={url} target="_blank" rel="noopener noreferrer" className="pdf-tool-item"
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, padding: "8px 4px", borderRadius: 7, textDecoration: "none", transition: "all 0.12s", cursor: "pointer" }}>
                  <span style={{ fontSize: 17 }}>{icon}</span>
                  <span style={{ fontSize: 10, fontWeight: 500, color: t.text, textAlign: "center", lineHeight: 1.2 }}>{label}</span>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ flex: 1 }} />

      {/* Theme toggle — minimal icon button */}
      <button className="theme-btn" onClick={toggle}
        style={{ background: "transparent", border: `1px solid ${t.border}`, borderRadius: 7, padding: "5px 9px", cursor: "pointer", fontSize: 14, color: t.sub, transition: "all 0.12s", marginRight: 6 }}>
        {dark ? "☀" : "☾"}
      </button>

      {/* Profile avatar — neutral circle with initials */}
      <div ref={dropRef} style={{ position: "relative" }}>
        <button onClick={() => setShowProfile(s => !s)}
          style={{ display: "flex", alignItems: "center", gap: 7, background: showProfile ? t.hover : "transparent", border: `1px solid ${showProfile ? t.border : "transparent"}`, borderRadius: 8, padding: "4px 8px 4px 4px", cursor: "pointer", transition: "all 0.12s" }}>
          <div style={{ width: 27, height: 27, borderRadius: "50%", background: dark ? "#424242" : "#171717", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 11, fontWeight: 600, letterSpacing: "0.02em" }}>
            {initials}
          </div>
          <span style={{ fontSize: 13, fontWeight: 500, color: t.text }}>{username}</span>
          <span style={{ fontSize: 9, color: t.sub }}>{showProfile ? "▲" : "▼"}</span>
        </button>

        {showProfile && (
          <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: t.drop, border: `1px solid ${t.dropBorder}`, borderRadius: 10, padding: "6px", minWidth: 190, boxShadow: dark ? "0 8px 24px rgba(0,0,0,0.4)" : "0 8px 24px rgba(0,0,0,0.1)", zIndex: 300 }}>
            <div style={{ padding: "8px 10px 8px", borderBottom: `1px solid ${t.border}`, marginBottom: 4 }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: t.text }}>{username}</p>
              <p style={{ margin: "2px 0 0", fontSize: 11, color: t.sub }}>Signed in</p>
            </div>
            {[
              { label: "Profile & Settings", action: () => { nav("/profile"); setShowProfile(false); } },
              { label: "My Documents",       action: () => { nav("/documents"); setShowProfile(false); } },
            ].map(({ label, action }) => (
              <button key={label} className="drop-item" onClick={action}
                style={{ width: "100%", display: "flex", alignItems: "center", background: "transparent", border: "none", borderRadius: 7, padding: "8px 10px", cursor: "pointer", fontSize: 13, color: t.text, fontFamily: "Inter, sans-serif", textAlign: "left", transition: "all 0.12s" }}>
                {label}
              </button>
            ))}
            <div style={{ borderTop: `1px solid ${t.border}`, marginTop: 4, paddingTop: 4 }}>
              <button className="drop-item" onClick={onLogout}
                style={{ width: "100%", display: "flex", alignItems: "center", background: "transparent", border: "none", borderRadius: 7, padding: "8px 10px", cursor: "pointer", fontSize: 13, color: "#ef4444", fontFamily: "Inter, sans-serif", textAlign: "left", transition: "all 0.12s" }}>
                Sign Out
              </button>
            </div>
          </div>
        )}
      </div>

      <span style={{ fontSize: 9, opacity: 0.28, color: t.sub, fontFamily: "Inter, sans-serif", letterSpacing: "0.03em", userSelect: "none", pointerEvents: "none", marginLeft: 10 }}>
        crafted by kanwa
      </span>
    </nav>
  );
}
