import React, { useState, useRef, useEffect, useCallback } from "react";
import { docsAPI } from "../api/client";
import { useTheme } from "../context/ThemeContext";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const apiFetch = (path, opts = {}) =>
  fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json", ...opts.headers },
    ...opts,
  }).then(r => r.json());

// ── Clean Markdown Renderer — ChatGPT style ───────────────────────────────────
function RenderAnswer({ text, dark }) {
  if (!text) return null;

  const textColor  = dark ? "#ececec" : "#1a1a1a";
  const mutedColor = dark ? "#b0b0b0" : "#444";
  const borderCol  = dark ? "#333"    : "#e0e0e0";
  const thBg       = dark ? "#2a2a2a" : "#f5f5f5";
  const rowAlt     = dark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)";
  const accentCol  = dark ? "#7c8cf8" : "#4f46e5";

  // Process inline: **bold**, `code`
  const inline = (txt) => {
    const parts = txt.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((p, i) => {
      if (p.startsWith("**") && p.endsWith("**"))
        return <strong key={i} style={{ fontWeight: 600, color: textColor }}>{p.slice(2,-2)}</strong>;
      if (p.startsWith("`") && p.endsWith("`"))
        return <code key={i} style={{ background: dark?"#2d2d2d":"#f0f0f0", color: dark?"#e06c75":"#d63384", padding:"1px 5px", borderRadius:4, fontSize:"0.9em", fontFamily:"'Fira Code','Consolas',monospace" }}>{p.slice(1,-1)}</code>;
      return p;
    });
  };

  const lines = text.split("\n");
  const els = [];
  let i = 0;

  // Table buffer
  let tBuf = [], inT = false;
  const flushTable = () => {
    if (tBuf.length < 2) { tBuf = []; inT = false; return; }
    const heads = tBuf[0].split("|").map(h => h.trim()).filter(Boolean);
    const rows  = tBuf.slice(2).map(r => r.split("|").map(x => x.trim()).filter(Boolean));

    // Build proper HTML table for clipboard — pastes as real table in Google Docs & Word
    const htmlForClip = [
      `<table border="1" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px">`,
      `<thead><tr>`,
      heads.map(h => `<th style="padding:8px 12px;background:#f0f0f0;font-weight:600;border:1px solid #ccc">${h}</th>`).join(''),
      `</tr></thead><tbody>`,
      rows.map(r =>
        `<tr>${r.map(c => `<td style="padding:8px 12px;border:1px solid #ccc">${c}</td>`).join('')}</tr>`
      ).join(''),
      `</tbody></table>`
    ].join('');

    // CSV for download
    const csv = [heads.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
    const csvUrl = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`;

    const copyAsHtml = (e) => {
      const btn = e.currentTarget;
      const orig = btn.textContent;
      try {
        if (navigator.clipboard && window.ClipboardItem) {
          const htmlBlob = new Blob([htmlForClip], { type: 'text/html' });
          const txtBlob  = new Blob([rows.map(r => r.join('\t')).join('\n')], { type: 'text/plain' });
          navigator.clipboard.write([new ClipboardItem({ 'text/html': htmlBlob, 'text/plain': txtBlob })]);
        } else {
          // Firefox fallback: select rendered HTML node
          const el = document.createElement('div');
          el.innerHTML = htmlForClip;
          el.style.cssText = 'position:fixed;left:-9999px;top:0';
          document.body.appendChild(el);
          const range = document.createRange();
          range.selectNode(el);
          window.getSelection().removeAllRanges();
          window.getSelection().addRange(range);
          document.execCommand('copy');
          window.getSelection().removeAllRanges();
          document.body.removeChild(el);
        }
        btn.textContent = 'Copied!';
      } catch {
        btn.textContent = 'Error';
      }
      setTimeout(() => { btn.textContent = orig; }, 2200);
    };

    const btnStyle = {
      fontSize:11, padding:"3px 9px", borderRadius:4,
      border:`1px solid ${borderCol}`, background:"transparent",
      color:mutedColor, cursor:"pointer", fontFamily:"inherit"
    };

    els.push(
      <div key={`tbl${i}`} style={{ margin:"16px 0" }}>
        {/* Table toolbar */}
        <div style={{ display:"flex", gap:5, alignItems:"center", marginBottom:6, flexWrap:"wrap" }}>
          <span style={{ fontSize:10, color:mutedColor, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.6px", marginRight:4 }}>Table</span>
          <button onClick={copyAsHtml} style={btnStyle}>Copy Table</button>
          <a href={csvUrl} download="table.csv" style={{ ...btnStyle, textDecoration:"none", display:"inline-block" }}>Download CSV</a>
          <span style={{ fontSize:10, color:mutedColor, fontStyle:"italic" }}>→ Paste into Google Docs or Word as a real table</span>
        </div>
        {/* Table display */}
        <div style={{ overflowX:"auto" }}>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:14, lineHeight:1.6 }}>
            <thead>
              <tr style={{ background: thBg }}>
                {heads.map((h, hi) => (
                  <th key={hi} style={{ padding:"10px 16px", textAlign:"left", borderBottom:`2px solid ${borderCol}`, color:textColor, fontWeight:600, fontSize:13 }}>
                    {inline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri} style={{ background: ri%2===0?"transparent":rowAlt }}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{ padding:"9px 16px", borderBottom:`1px solid ${borderCol}`, color:mutedColor, fontSize:14 }}>
                      {inline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
    tBuf = []; inT = false;
  };

  while (i < lines.length) {
    const raw  = lines[i];
    const line = raw.trimEnd();

    // Table detection
    if (line.includes("|") && line.trim().startsWith("|")) {
      inT = true; tBuf.push(line); i++; continue;
    } else if (inT) { flushTable(); }

    // Empty line → small spacing
    if (!line.trim()) {
      els.push(<div key={i} style={{ height: 10 }} />);
      i++; continue;
    }

    // Horizontal rule
    if (/^[-*]{3,}$/.test(line.trim())) {
      els.push(<hr key={i} style={{ border:"none", borderTop:`1px solid ${borderCol}`, margin:"20px 0" }} />);
      i++; continue;
    }

    // Strip all leading # symbols (remove hashtags completely)
    const hMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const content = hMatch[2];
      const sizes   = [22, 19, 17, 15, 14, 13];
      const margins = ["24px 0 8px","20px 0 6px","18px 0 6px","16px 0 4px","14px 0 4px","12px 0 4px"];
      els.push(
        <p key={i} style={{
          margin: margins[level-1] || "16px 0 6px",
          fontSize: sizes[level-1] || 14,
          fontWeight: 700,
          color: textColor,
          lineHeight: 1.4,
          letterSpacing: level <= 2 ? "-0.3px" : "0",
        }}>
          {inline(content)}
        </p>
      );
      i++; continue;
    }

    // Emoji section headers (lines starting with emoji + **text**)
    const emojiHeader = /^([\u{1F300}-\u{1FFFF}✅❌⚠️📌💡🔗⚙️🌍🎯❓⚡💪🔬💼🏥🏫📖🔍📋📄💬📚🔑📊📝🎯🏆⭐🔥💎🚀📈✨🌟⚡🎓📝🔎💻🛠️⚖️🌐🔐])/u;
    if (emojiHeader.test(line.trim())) {
      // Check if it's bold after emoji
      const stripped = line.trim();
      els.push(
        <p key={i} style={{ margin:"20px 0 6px", fontSize:15, fontWeight:700, color:textColor, lineHeight:1.5 }}>
          {inline(stripped)}
        </p>
      );
      i++; continue;
    }

    // Bullet points — •, -, *
    const bulletMatch = line.match(/^(\s*)([-•*])\s+(.+)/);
    if (bulletMatch) {
      const indent = bulletMatch[1].length;
      const content = bulletMatch[3];
      const isNested = indent >= 2;
      els.push(
        <div key={i} style={{
          display:"flex", gap: isNested ? 8 : 10,
          margin: isNested ? "3px 0 3px 24px" : "4px 0",
          alignItems:"flex-start",
        }}>
          <span style={{
            color: isNested ? mutedColor : accentCol,
            flexShrink:0, marginTop:5,
            fontSize: isNested ? 5 : 7,
            lineHeight:1,
          }}>●</span>
          <span style={{ fontSize:15, color:mutedColor, lineHeight:1.75 }}>
            {inline(content)}
          </span>
        </div>
      );
      i++; continue;
    }

    // Numbered lists
    const numMatch = line.match(/^(\s*)(\d+)[.)]\s+(.+)/);
    if (numMatch) {
      const indent  = numMatch[1].length;
      const num     = numMatch[2];
      const content = numMatch[3];
      els.push(
        <div key={i} style={{
          display:"flex", gap:12,
          margin: indent > 0 ? "3px 0 3px 24px" : "5px 0",
          alignItems:"flex-start",
        }}>
          <span style={{ color:accentCol, fontWeight:600, fontSize:14, minWidth:20, flexShrink:0, marginTop:2 }}>
            {num}.
          </span>
          <span style={{ fontSize:15, color:mutedColor, lineHeight:1.75 }}>
            {inline(content)}
          </span>
        </div>
      );
      i++; continue;
    }

    // Code blocks (```)
    if (line.trim().startsWith("```")) {
      const lang = line.trim().slice(3);
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      els.push(
        <div key={i} style={{ margin:"12px 0", borderRadius:10, overflow:"hidden", border:`1px solid ${borderCol}` }}>
          {lang && <div style={{ background:dark?"#1e1e1e":"#f0f0f0", padding:"6px 14px", fontSize:11, color:mutedColor, fontFamily:"monospace", borderBottom:`1px solid ${borderCol}` }}>{lang}</div>}
          <pre style={{ margin:0, padding:"14px 16px", background:dark?"#1a1a1a":"#f8f8f8", overflowX:"auto", fontSize:13, lineHeight:1.65, fontFamily:"'Fira Code','Consolas','Monaco',monospace", color:dark?"#cdd6f4":"#24292e" }}>
            {codeLines.join("\n")}
          </pre>
        </div>
      );
      i++; continue;
    }

    // Italic or note lines (*text*)
    if (line.trim().startsWith("*") && line.trim().endsWith("*") && !line.trim().slice(1,-1).includes("*")) {
      els.push(
        <p key={i} style={{ margin:"6px 0", fontSize:13, color:dark?"#888":"#888", fontStyle:"italic", lineHeight:1.6 }}>
          {line.trim().slice(1,-1)}
        </p>
      );
      i++; continue;
    }

    // Normal paragraph
    els.push(
      <p key={i} style={{ margin:"4px 0", fontSize:15, color:mutedColor, lineHeight:1.8, letterSpacing:"0.01em" }}>
        {inline(line.trim())}
      </p>
    );
    i++;
  }
  if (inT) flushTable();

  return <div style={{ fontFamily:"'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif" }}>{els}</div>;
}

function DocIcon({ size=56 }) {
  return (
    <div style={{ width:size, height:size, borderRadius:14, background: "rgba(99,102,241,0.1)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:size*0.5, margin:"0 auto", border:"1px solid rgba(99,102,241,0.2)" }}>🧠</div>
  );
}

function ProcessingBar({ files, dark }) {
  if (!files || files.length === 0) return null;
  return (
    <div style={{ marginBottom:10 }}>
      {files.map((f, fi) => (
        <div key={fi} style={{ display:"flex", alignItems:"center", gap:10, background:dark?"rgba(99,102,241,0.1)":"rgba(99,102,241,0.06)", border:`1px solid rgba(99,102,241,0.2)`, borderRadius:12, padding:"10px 14px", marginBottom:6 }}>
          <div style={{ width:32, height:32, borderRadius:8, background:"rgba(99,102,241,0.12)", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, fontSize:16 }}>📄</div>
          <div style={{ flex:1, minWidth:0 }}>
            <p style={{ margin:0, fontSize:13, fontWeight:600, color:dark?"#a5b4fc":"#4338ca", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{f.name}</p>
            <div style={{ display:"flex", alignItems:"center", gap:6, marginTop:4 }}>
              {(f.status==="uploading"||f.status==="processing") && <>
                <div style={{ width:100, height:3, background:"rgba(99,102,241,0.15)", borderRadius:4, overflow:"hidden" }}>
                  <div style={{ height:"100%", background:"linear-gradient(90deg,#6366f1,#7c3aed)", borderRadius:4, animation:"progress 2s ease-in-out infinite" }}/>
                </div>
                <span style={{ fontSize:11, color:"#818cf8", fontWeight:500 }}>{f.status==="uploading"?"Uploading...":"Indexing..."}</span>
              </>}
              {f.status==="ready" && <><span style={{ fontSize:12 }}>✅</span><span style={{ fontSize:11, color:"#10b981", fontWeight:600 }}>Ready — ask anything!</span></>}
              {f.status==="failed" && <><span style={{ fontSize:12 }}>❌</span><span style={{ fontSize:11, color:"#ef4444", fontWeight:600 }}>Failed</span></>}
            </div>
          </div>
          {f.status==="ready" && <button onClick={f.onRemove} style={{ background:"none", border:"none", color:"#666", cursor:"pointer", fontSize:18, padding:"0 4px" }}>×</button>}
        </div>
      ))}
      <style>{`@keyframes progress{0%{width:0%;margin-left:0}50%{width:60%;margin-left:20%}100%{width:0%;margin-left:100%}}`}</style>
    </div>
  );
}

export default function Chat() {
  const { dark } = useTheme();
  const [sessions, setSessions]     = useState([]);
  const [activeSession, setActive]  = useState(null);
  const [messages, setMessages]     = useState([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [drag, setDrag]             = useState(false);
  const [sidebarOpen, setSidebar]   = useState(true);
  const [renamingId, setRenamingId] = useState(null);
  const [renameVal, setRenameVal]   = useState("");
  const [trackedFiles, setTracked]  = useState([]);
  const [allDocs, setAllDocs]       = useState([]);
  // Per-session uploaded doc IDs — key: session_id, value: [doc_id, ...]
  const [sessionDocIds, setSessionDocIds] = useState({});
  const pollingRef = useRef({});
  const activeSessionRef = useRef(null); // ref to track current session in callbacks
  const isProcessing = trackedFiles.some(f => f.status==="uploading"||f.status==="processing");
  // Mobile detection — sidebar overlays on small screens
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener("resize", onResize);
    // Auto-close sidebar on initial mobile load
    if (window.innerWidth <= 768) setSidebar(false);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);

  // Theme colors
  const bg      = dark ? "#111111" : "#ffffff";
  const sideCol = dark ? "#1c1c1c" : "#f4f4f5";
  const cardCol = dark ? "#1c1c1c" : "#ffffff";
  const border  = dark ? "#2a2a2a" : "#e4e4e7";
  const textCol = dark ? "#f4f4f5" : "#09090b";
  const subCol  = dark ? "#a1a1aa" : "#52525b";
  const dimCol  = dark ? "#52525b" : "#a1a1aa";
  const inputBg = dark ? "#1c1c1c" : "#fafafa";
  const accent  = "#2563eb";

  useEffect(() => { loadSessions(); loadAllDocs(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages, loading]);
  useEffect(() => () => { Object.values(pollingRef.current).forEach(clearInterval); }, []);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [input]);

  const loadSessions = async () => { const d = await apiFetch("/qa/sessions"); if (Array.isArray(d)) setSessions(d); };
  const loadAllDocs  = async () => {
    try { const r = await fetch(`${BASE}/documents/list`, { headers:{ Authorization:`Bearer ${localStorage.getItem("token")}` } }); const d = await r.json(); if (Array.isArray(d)) setAllDocs(d); } catch {}
  };

  const openSession = async (s) => {
    setActive(s); activeSessionRef.current = s; setMessages([]);
    const msgs = await apiFetch(`/qa/sessions/${s.id}/messages`);
    if (Array.isArray(msgs)) setMessages(msgs.flatMap(m => [{ role:"user", text:m.question }, { role:"assistant", text:m.answer, sources:m.sources }]));
    // Restore session doc_ids from DB into state
    if (s.doc_ids && s.doc_ids.length > 0) {
      setSessionDocIds(prev => ({ ...prev, [s.id]: s.doc_ids }));
    }
    // On mobile, close sidebar after selecting a session
    if (isMobile) setSidebar(false);
  };
  const newChat = async () => { const s = await apiFetch("/qa/sessions", { method:"POST" }); setSessions(p => [s,...p]); setActive(s); activeSessionRef.current = s; setMessages([]); setTracked([]); };
  const deleteSession = async (e, id) => { e.stopPropagation(); await apiFetch(`/qa/sessions/${id}`, { method:"DELETE" }); setSessions(p => p.filter(s => s.id !== id)); if (activeSession?.id===id) { setActive(null); setMessages([]); } };
  const submitRename = async (id) => { if (!renameVal.trim()) { setRenamingId(null); return; } await apiFetch(`/qa/sessions/${id}`, { method:"PATCH", body:JSON.stringify({ title:renameVal }) }); setSessions(p => p.map(s => s.id===id ? {...s,title:renameVal} : s)); setRenamingId(null); };

  const pollDocStatus = useCallback((docId) => {
    if (pollingRef.current[docId]) clearInterval(pollingRef.current[docId]);
    pollingRef.current[docId] = setInterval(async () => {
      try {
        const docs = await apiFetch("/documents/list");
        if (!Array.isArray(docs)) return;
        const doc = docs.find(d => d.id === docId);
        if (!doc) return;
        if (doc.status === "Ready") {
          clearInterval(pollingRef.current[docId]); delete pollingRef.current[docId];
          setTracked(prev => prev.map(f => f.docId===docId ? {...f,status:"ready"} : f));
          setAllDocs(docs);
          // Add docId to current active session's doc list
          setSessionDocIds(prev => {
            const currentSid = activeSessionRef.current?.id || "pending";
            const existing = prev[currentSid] || [];
            if (existing.includes(docId)) return prev;
            return { ...prev, [currentSid]: [...existing, docId] };
          });
        } else if (doc.status === "Failed") {
          clearInterval(pollingRef.current[docId]); delete pollingRef.current[docId];
          setTracked(prev => prev.map(f => f.docId===docId ? {...f,status:"failed"} : f));
        }
      } catch {}
    }, 2000);
  }, []);

  const handleFiles = async (files) => {
    const pdfs = Array.from(files).filter(f => f.name.endsWith(".pdf"));
    if (!pdfs.length) return;
    for (const file of pdfs) {
      const tempId = `temp_${Date.now()}_${file.name}`;
      setTracked(prev => [...prev, { name:file.name, status:"uploading", docId:null, tempId, onRemove:()=>setTracked(p=>p.filter(f=>f.tempId!==tempId)) }]);
      try {
        const res = await docsAPI.upload(file);
        const docId = res.data?.doc_id;
        setTracked(prev => prev.map(f => f.tempId===tempId ? {...f,status:"processing",docId,onRemove:()=>setTracked(p=>p.filter(x=>x.docId!==docId))} : f));
        if (docId) pollDocStatus(docId);
      } catch { setTracked(prev => prev.map(f => f.tempId===tempId ? {...f,status:"failed"} : f)); }
    }
  };

  const send = async () => {
    if (!input.trim() || loading || isProcessing) return;
    const q = input.trim(); setInput("");
    setMessages(p => [...p, { role:"user", text:q }]); setLoading(true);
    try {
      const currentSid = activeSession?.id || null;
      const docIds = currentSid ? (sessionDocIds[currentSid] || []) : (sessionDocIds["pending"] || []);
      const body = { question:q, session_id:currentSid };
      if (docIds.length > 0) body.uploaded_doc_ids = docIds;
      const res = await apiFetch("/qa/ask", { method:"POST", body:JSON.stringify(body) });
      setMessages(p => [...p, { role:"assistant", text:res.answer, sources:res.sources }]);
      if (res.session_id) {
        if (!activeSession) {
          await loadSessions();
          const newSess = { id:res.session_id, title:q.slice(0,40) };
          setActive(newSess); activeSessionRef.current = newSess;
          // Transfer any pending docs to the new session ID
          setSessionDocIds(prev => {
            const pending = prev["pending"] || [];
            if (pending.length === 0) return prev;
            const updated = { ...prev, [res.session_id]: [...(prev[res.session_id]||[]), ...pending] };
            delete updated["pending"];
            return updated;
          });
        } else {
          activeSessionRef.current = activeSession;
          setSessions(p => p.map(s => s.id===res.session_id ? {...s,updated_at:new Date().toISOString()} : s));
        }
      }
    } catch { setMessages(p => [...p, { role:"assistant", text:"Something went wrong. Please try again.", sources:[] }]); }
    setLoading(false);
  };

  const canSend = input.trim() && !loading && !isProcessing;
  const CHIPS = ["Summarize this document","Predict exam questions","List all key concepts","Explain the main topic","What are the important formulas?","Compare main concepts"];

  return (
    <div style={{ display:"flex", height:"calc(100vh - 60px)", background:bg, fontFamily:"'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", overflow:"hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        .sess-item{transition:background 0.1s;border-radius:6px;cursor:pointer}
        .sess-item:hover{background:${dark?"rgba(255,255,255,0.05)":"rgba(0,0,0,0.04)"}!important}
        .sess-item:hover .sess-act{opacity:1!important}
        .chip-btn{transition:background 0.12s;cursor:pointer;font-family:'Inter',sans-serif}
        .chip-btn:hover{background:${dark?"#252525":"#e9e9eb"}!important}
        .send-btn{transition:opacity 0.12s}
        .send-btn:hover:not(:disabled){opacity:.85}
        .copy-btn{opacity:0;transition:opacity 0.12s}.ai-msg:hover .copy-btn{opacity:1}
        .new-btn:hover{opacity:.85}
        .src-link{transition:opacity 0.12s}.src-link:hover{opacity:.7}
        .main-scroll::-webkit-scrollbar{width:4px}.main-scroll::-webkit-scrollbar-thumb{background:rgba(128,128,128,0.15);border-radius:4px}
        .side-scroll::-webkit-scrollbar{width:3px}.side-scroll::-webkit-scrollbar-thumb{background:rgba(128,128,128,0.12);border-radius:2px}
        textarea{resize:none!important;outline:none!important;font-family:'Inter',-apple-system,sans-serif}
        @keyframes msgIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
        @keyframes bounce{0%,60%,100%{transform:translateY(0);opacity:0.3}30%{transform:translateY(-5px);opacity:1}}
      `}</style>

      {/* Mobile backdrop — tap to close sidebar */}
      {sidebarOpen && isMobile && (
        <div onClick={() => setSidebar(false)}
          style={{ position:"fixed", inset:0, top:60, background:"rgba(0,0,0,0.4)", zIndex:140, backdropFilter:"blur(2px)" }}
        />
      )}

      {/* SIDEBAR */}
      {sidebarOpen && (
        <div className="chat-sidebar-overlay" style={{ width:240, flexShrink:0, background:sideCol, borderRight:`1px solid ${border}`, display:"flex", flexDirection:"column", overflow:"hidden" }}>
          <div style={{ padding:"12px 8px 6px" }}>
            <button className="new-btn" onClick={newChat}
              style={{ width:"100%", background:accent, color:"#fff", border:"none", borderRadius:6, padding:"8px 12px", cursor:"pointer", fontSize:13, fontWeight:500, fontFamily:"inherit", display:"flex", alignItems:"center", gap:6, justifyContent:"center" }}>
              + New Chat
            </button>
          </div>
          <div style={{ padding:"8px 12px 4px", fontSize:10, fontWeight:600, color:dimCol, textTransform:"uppercase", letterSpacing:"1px" }}>Recent</div>
          <div className="side-scroll" style={{ flex:1, overflowY:"auto", padding:"0 6px 12px" }}>
            {sessions.length===0 && <div style={{ textAlign:"center", padding:"32px 12px" }}><p style={{ margin:0, fontSize:12, color:dimCol, lineHeight:1.6 }}>No chats yet.<br/>Start a conversation.</p></div>}
            {sessions.map(s => (
              <div key={s.id} className="sess-item" onClick={() => openSession(s)}
                style={{ padding:"7px 8px", marginBottom:1, background:activeSession?.id===s.id?(dark?"rgba(37,99,235,0.15)":"rgba(37,99,235,0.08)"):"transparent", borderRadius:6, position:"relative" }}>
                {renamingId===s.id ? (
                  <input autoFocus value={renameVal} onChange={e=>setRenameVal(e.target.value)}
                    onBlur={()=>submitRename(s.id)} onKeyDown={e=>{if(e.key==="Enter")submitRename(s.id);if(e.key==="Escape")setRenamingId(null);}} onClick={e=>e.stopPropagation()}
                    style={{ width:"100%", background:inputBg, border:`1.5px solid ${accent}`, borderRadius:5, padding:"3px 7px", color:textCol, fontFamily:"inherit", fontSize:12, outline:"none" }}/>
                ) : (
                  <>
                    <p style={{ margin:0, fontSize:12, fontWeight:activeSession?.id===s.id?600:400, color:activeSession?.id===s.id?accent:subCol, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap", paddingRight:40 }}>{s.title||"New Chat"}</p>
                    <p style={{ margin:"1px 0 0", fontSize:10, color:dimCol }}>{s.message_count} msgs</p>
                    <div className="sess-act" style={{ opacity:0, position:"absolute", right:4, top:"50%", transform:"translateY(-50%)", display:"flex", gap:1 }}>
                      <button onClick={e=>{e.stopPropagation();setRenamingId(s.id);setRenameVal(s.title||"");}} style={{ background:"none", border:"none", cursor:"pointer", padding:"3px 5px", fontSize:11, color:subCol }}>✏️</button>
                      <button onClick={e=>deleteSession(e,s.id)} style={{ background:"none", border:"none", cursor:"pointer", padding:"3px 5px", fontSize:11, color:subCol }}>🗑</button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MAIN */}
      <div className="chat-main" style={{ flex:1, display:"flex", flexDirection:"column", minWidth:0, overflow:"hidden" }}>
        {/* Sidebar toggle */}
        <button className="sidebar-toggle-btn" onClick={() => setSidebar(s => !s)}
          style={{ position:"absolute", top:72, left:sidebarOpen&&!isMobile?268:8, zIndex:20, background:cardCol, border:`1px solid ${border}`, color:subCol, width:26, height:26, borderRadius:6, cursor:"pointer", fontSize:11, display:"flex", alignItems:"center", justifyContent:"center", transition:"left 0.2s" }}>
          {sidebarOpen?"◀":"▶"}
        </button>

        {/* Messages area */}
        <div className="chat-messages-area main-scroll" style={{ flex:1, overflowY:"auto", padding:`24px ${sidebarOpen&&!isMobile?"48px":"72px"} 200px` }}>

          {/* Empty state */}
          {messages.length===0 && (
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", minHeight:"55vh", gap:20, textAlign:"center" }}>
              <DocIcon size={60}/>
              <div>
                <h2 style={{ margin:"0 0 6px", fontSize:22, fontWeight:600, color:textCol, letterSpacing:"-0.3px" }}>
                  {activeSession?.title && activeSession.title!=="New Chat" ? activeSession.title : "Ask me anything"}
                </h2>
                <p style={{ margin:0, fontSize:14, color:subCol }}>Upload a PDF and ask detailed questions about it</p>
              </div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6, justifyContent:"center", maxWidth:540 }}>
                {CHIPS.map(c => (
                  <button key={c} className="chip-btn" onClick={() => setInput(c)}
                    style={{ background:dark?"#1c1c1c":"#f4f4f5", border:`1px solid ${border}`, color:subCol, padding:"7px 14px", borderRadius:6, fontSize:13, fontWeight:400, cursor:"pointer" }}>
                    {c}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((msg, idx) => (
            <div key={idx} style={{ marginBottom:28, animation:"msgIn 0.2s ease" }}>
              {msg.role==="user" && (
                <div style={{ display:"flex", justifyContent:"flex-end", marginBottom:4 }}>
                  <div style={{ maxWidth:"70%", background:accent, color:"#fff", padding:"11px 16px", borderRadius:"16px 16px 4px 16px", fontSize:14, lineHeight:1.7, fontWeight:400 }}>
                    {msg.text}
                  </div>
                </div>
              )}
              {msg.role==="assistant" && (
                <div className="ai-msg" style={{ display:"flex", gap:12, alignItems:"flex-start" }}>
                  {/* Avatar */}
                  <div style={{ width:28, height:28, borderRadius:8, background:`rgba(99,102,241,0.12)`, border:`1px solid rgba(99,102,241,0.2)`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, flexShrink:0, marginTop:4 }}>🧠</div>
                  {/* Answer — NO box, clean like ChatGPT */}
                  <div style={{ flex:1, position:"relative", paddingTop:4 }}>
                    <RenderAnswer text={msg.text} dark={dark}/>
                    {/* Sources */}
                    {msg.sources?.length > 0 && (
                      <div style={{ marginTop:12, paddingTop:10, borderTop:`1px solid ${dark?"#2a2a2a":"#ebebeb"}`, display:"flex", alignItems:"center", gap:6, flexWrap:"wrap" }}>
                        <span style={{ fontSize:11, color:dimCol, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.5px" }}>Sources</span>
                        {[...new Set(msg.sources)].map((s, si) => {
                          const matchDoc = allDocs.find(d => d.original_name===s || s.includes(d.original_name.replace(".pdf","").replace(".PDF","")));
                          const chip = { background:dark?"rgba(99,102,241,0.1)":"rgba(99,102,241,0.07)", border:`1px solid rgba(99,102,241,0.2)`, borderRadius:6, padding:"3px 10px", fontSize:11, fontWeight:500 };
                          if (matchDoc) {
                            const viewUrl = `${BASE}/documents/view/${matchDoc.id}?token=${localStorage.getItem("token")}`;
                            return (
                              <a key={si} href={viewUrl} target="_blank" rel="noopener noreferrer" className="src-link"
                                style={{ ...chip, color:accent, textDecoration:"none", display:"inline-flex", alignItems:"center", gap:4 }}>
                                📄 {s}
                              </a>
                            );
                          }
                          return <span key={si} style={{ ...chip, color:dimCol }}>📄 {s}</span>;
                        })}
                      </div>
                    )}
                    {/* Action buttons — Copy text + Export DOCX */}
                    <div className="copy-btn" style={{ position:"absolute", top:0, right:0, display:"flex", gap:4 }}>
                      <button onClick={() => navigator.clipboard.writeText(msg.text)}
                        style={{ background:"none", border:`1px solid ${border}`, color:dimCol, padding:"3px 9px", borderRadius:6, cursor:"pointer", fontSize:11, fontFamily:"inherit" }}>
                        Copy
                      </button>
                      <button onClick={async () => {
                        try {
                          // Find matching question for this message
                          const msgIdx = messages.indexOf(msg);
                          const question = msgIdx > 0 && messages[msgIdx-1].role==='user' ? messages[msgIdx-1].text : '';
                          const res = await fetch(`${BASE}/export/docx`, {
                            method:'POST',
                            headers:{'Content-Type':'application/json','Authorization':`Bearer ${localStorage.getItem('token')}`},
                            body: JSON.stringify({ answer: msg.text, question, sources: msg.sources || [] })
                          });
                          if (!res.ok) throw new Error('Export failed');
                          const blob = await res.blob();
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          const cd = res.headers.get('content-disposition') || '';
                          const fn = cd.match(/filename="?([^"]+)"?/)?.[1] || 'DocuMindAI_Answer.docx';
                          a.download = fn;
                          a.click();
                          URL.revokeObjectURL(url);
                        } catch(e) { alert('Export failed: ' + e.message); }
                      }}
                        style={{ background:accent, border:"none", color:"#fff", padding:"3px 9px", borderRadius:6, cursor:"pointer", fontSize:11, fontFamily:"inherit" }}>
                        Export DOCX
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Loading dots */}
          {loading && (
            <div style={{ display:"flex", gap:12, alignItems:"flex-start", marginBottom:24, animation:"msgIn 0.2s ease" }}>
              <div style={{ width:28, height:28, borderRadius:8, background:`rgba(99,102,241,0.12)`, border:`1px solid rgba(99,102,241,0.2)`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, flexShrink:0, marginTop:4 }}>🧠</div>
              <div style={{ paddingTop:10, display:"flex", gap:5 }}>
                {[0,1,2].map(n => <div key={n} style={{ width:7, height:7, borderRadius:"50%", background:subCol, animation:`bounce 1.2s ${n*0.18}s ease-in-out infinite` }}/>)}
              </div>
            </div>
          )}
          <div ref={bottomRef}/>
        </div>

        {/* INPUT */}
        <div className="chat-input-area" style={{ flexShrink:0, padding:"8px 48px 16px", background:`linear-gradient(to top,${bg} 80%,transparent)` }}>
          <ProcessingBar files={trackedFiles} dark={dark}/>
          {isProcessing && (
            <div style={{ marginBottom:8, padding:"7px 12px", background:dark?"rgba(234,179,8,0.08)":"rgba(234,179,8,0.07)", border:"1px solid rgba(234,179,8,0.25)", borderRadius:9, fontSize:12, color:dark?"#fbbf24":"#92400e", display:"flex", alignItems:"center", gap:7 }}>
              ⏳ PDF is being processed — input will unlock automatically when ready
            </div>
          )}
          <div
            onDragOver={e=>{e.preventDefault();setDrag(true)}} onDragLeave={()=>setDrag(false)}
            onDrop={e=>{e.preventDefault();setDrag(false);handleFiles(e.dataTransfer.files)}}
            style={{ background:drag?`rgba(37,99,235,0.03)`:cardCol, border:`1.5px solid ${drag?accent:isProcessing?"rgba(234,179,8,0.3)":border}`, borderRadius:10, padding:"8px 10px 8px 12px", display:"flex", gap:8, alignItems:"flex-end", boxShadow:dark?"0 2px 12px rgba(0,0,0,0.3)":"0 1px 8px rgba(0,0,0,0.06)", transition:"border-color 0.15s" }}>
            <label style={{ cursor:"pointer", flexShrink:0 }}>
              <div style={{ width:34, height:34, borderRadius:9, background:"transparent", border:`1.5px solid ${border}`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:17, color:subCol, transition:"all 0.15s" }}>📎</div>
              <input type="file" accept=".pdf" multiple onChange={e=>handleFiles(e.target.files)} style={{ display:"none" }}/>
            </label>
            <textarea ref={textareaRef} value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key==="Enter" && !e.shiftKey && canSend) { e.preventDefault(); send(); } }}
              placeholder={isProcessing ? "⏳ Processing PDF..." : trackedFiles.some(f=>f.status==="ready") ? "PDF ready! Try: Summarize this document, Predict exam questions…" : "Ask anything about your documents…"}
              disabled={isProcessing} rows={1}
              style={{ flex:1, background:"transparent", border:"none", color:isProcessing?subCol:textCol, fontSize:15, lineHeight:1.65, padding:"6px 0", minHeight:34 }}/>
            <button className="send-btn" onClick={send} disabled={!canSend}
              style={{ background:canSend?accent:"transparent", color:canSend?"#fff":dimCol, border:canSend?"none":`1.5px solid ${border}`, borderRadius:8, padding:"8px 18px", cursor:canSend?"pointer":"not-allowed", fontWeight:500, fontSize:13, fontFamily:"inherit", flexShrink:0, minWidth:72 }}>
              {loading?"…":isProcessing?"Wait":"Send"}
            </button>
          </div>
          <p style={{ textAlign:"center", margin:"6px 0 0", fontSize:11, color:dimCol }}>📎 Attach · Drag & drop · Click sources to open PDF · Shift+Enter for new line</p>
        </div>
      </div>
    </div>
  );
}
