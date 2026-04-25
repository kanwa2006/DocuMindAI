import React, { useState, useEffect, useCallback } from "react";
import { useTheme } from "../context/ThemeContext";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const api = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json", ...opts.headers }, ...opts });

// ── Shared helpers ─────────────────────────────────────────────────────────
function Spinner() {
  return <div style={{ display:"inline-block", width:18, height:18, border:"2px solid rgba(255,255,255,0.3)", borderTop:"2px solid #fff", borderRadius:"50%", animation:"spin 0.7s linear infinite" }} />;
}

function ResultBox({ content, dark }) {
  const [copied, setCopied] = useState(false);
  if (!content) return null;
  const doCopy = () => { navigator.clipboard.writeText(content); setCopied(true); setTimeout(()=>setCopied(false),1800); };
  return (
    <div style={{ marginTop:16, background: dark ? "#1a1a1a" : "#f5f5f5", border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, borderRadius:10, padding:16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
        <span style={{ fontSize:11, color: dark?"#8e8ea0":"#6b6b6b", fontWeight:600 }}>RESULT</span>
        <button onClick={doCopy} style={{ background:"transparent", border:`1px solid ${dark?"#3f3f3f":"#d0d0d0"}`, color: dark?"#ececec":"#333", padding:"3px 10px", borderRadius:6, cursor:"pointer", fontSize:11, fontFamily:"inherit" }}>
          {copied ? "✓ Copied" : "📋 Copy"}
        </button>
      </div>
      <pre style={{ margin:0, fontSize:13, color: dark?"#ececec":"#111", whiteSpace:"pre-wrap", wordBreak:"break-word", fontFamily:"Inter, monospace", lineHeight:1.7 }}>{content}</pre>
    </div>
  );
}

function DocSelect({ docs, value, onChange, dark }) {
  return (
    <select value={value} onChange={e=>onChange(e.target.value)}
      style={{ width:"100%", padding:"8px 12px", borderRadius:8, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background: dark?"#2f2f2f":"#fff", color: dark?"#ececec":"#111", fontSize:13, fontFamily:"inherit" }}>
      <option value="">— Select a document —</option>
      {docs.map(d => <option key={d.id} value={d.id}>{d.original_name || d.filename}</option>)}
    </select>
  );
}

// ── Mode panels ────────────────────────────────────────────────────────────

function TeacherMode({ docs, dark, t }) {
  const [docId, setDocId] = useState("");
  const [tab, setTab] = useState("qpaper"); // qpaper | answers | syllabus
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [cfg, setCfg] = useState({ difficulty:"mixed", total_marks:100, num_questions:20, include_answers:false, units:"all units" });

  const run = async () => {
    if (!docId) return;
    setLoading(true); setResult("");
    try {
      let res;
      if (tab === "qpaper") {
        res = await api("/agents/teacher/question-paper", { method:"POST", body: JSON.stringify({ doc_id:+docId, ...cfg }) });
        const d = await res.json(); setResult(d.question_paper || d.detail || JSON.stringify(d));
      } else if (tab === "answers") {
        res = await api(`/agents/teacher/answer-key/${docId}`, { method:"POST" });
        const d = await res.json(); setResult(d.answer_key || d.detail);
      } else {
        res = await api(`/agents/teacher/syllabus-map/${docId}`, { method:"POST" });
        const d = await res.json(); setResult(d.syllabus_map || d.detail);
      }
    } catch(e) { setResult("Error: " + e.message); }
    setLoading(false);
  };

  const tabs = [["qpaper","📝 Question Paper"], ["answers","🔑 Answer Key"], ["syllabus","🗺 Syllabus Map"]];

  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Generate question papers, answer keys, and syllabus maps from any academic PDF.</p>
      <div style={{ display:"flex", gap:6, marginBottom:16, flexWrap:"wrap" }}>
        {tabs.map(([k,label]) => (
          <button key={k} onClick={()=>{setTab(k);setResult("");}} style={{ padding:"6px 14px", borderRadius:7, border:"none", background: tab===k ? (dark?"#3f3f3f":"#171717") : (dark?"#2f2f2f":"#f0f0f0"), color: tab===k ? "#fff" : t.sub, cursor:"pointer", fontSize:12, fontWeight: tab===k?600:400, fontFamily:"inherit" }}>{label}</button>
        ))}
      </div>
      <DocSelect docs={docs} value={docId} onChange={setDocId} dark={dark} />
      {tab === "qpaper" && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginTop:12 }}>
          <div>
            <label style={{ fontSize:11, color:t.sub }}>Difficulty</label>
            <select value={cfg.difficulty} onChange={e=>setCfg(c=>({...c,difficulty:e.target.value}))} style={{ width:"100%", padding:"6px 8px", borderRadius:7, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4 }}>
              {["easy","medium","hard","mixed"].map(d=><option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize:11, color:t.sub }}>Total Marks</label>
            <input type="number" value={cfg.total_marks} onChange={e=>setCfg(c=>({...c,total_marks:+e.target.value}))} style={{ width:"100%", padding:"6px 8px", borderRadius:7, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4, boxSizing:"border-box" }} />
          </div>
          <div>
            <label style={{ fontSize:11, color:t.sub }}>No. of Questions</label>
            <input type="number" value={cfg.num_questions} onChange={e=>setCfg(c=>({...c,num_questions:+e.target.value}))} style={{ width:"100%", padding:"6px 8px", borderRadius:7, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4, boxSizing:"border-box" }} />
          </div>
          <div>
            <label style={{ fontSize:11, color:t.sub }}>Units/Topics</label>
            <input value={cfg.units} onChange={e=>setCfg(c=>({...c,units:e.target.value}))} placeholder="e.g. Unit 1, Unit 2" style={{ width:"100%", padding:"6px 8px", borderRadius:7, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4, boxSizing:"border-box" }} />
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:4 }}>
            <input type="checkbox" id="inclAns" checked={cfg.include_answers} onChange={e=>setCfg(c=>({...c,include_answers:e.target.checked}))} />
            <label htmlFor="inclAns" style={{ fontSize:12, color:t.text }}>Include model answers</label>
          </div>
        </div>
      )}
      <button onClick={run} disabled={!docId||loading} style={{ marginTop:14, width:"100%", padding:"10px", background: docId&&!loading ? (dark?"#3f3f3f":"#171717") : (dark?"#2a2a2a":"#e0e0e0"), color: docId&&!loading?"#fff":t.sub, border:"none", borderRadius:9, cursor: docId&&!loading?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
        {loading ? <><Spinner /> Generating...</> : "Generate"}
      </button>
      <ResultBox content={result} dark={dark} />
    </div>
  );
}

function HRMode({ docs, dark, t }) {
  const [tab, setTab] = useState("parse"); // parse | match | compare
  const [docId, setDocId] = useState("");
  const [docId2, setDocId2] = useState("");
  const [docId3, setDocId3] = useState("");
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");

  const run = async () => {
    if (!docId) return;
    setLoading(true); setResult("");
    try {
      let res, d;
      if (tab === "parse") {
        res = await api(`/agents/hr/parse-resume/${docId}`, { method:"POST" });
        d = await res.json();
        setResult(d.parsed_resume ? JSON.stringify(d.parsed_resume, null, 2) : d.raw || d.detail);
      } else if (tab === "match") {
        if (!jd.trim()) { setResult("Please paste a job description."); setLoading(false); return; }
        res = await api("/agents/hr/job-match", { method:"POST", body: JSON.stringify({ doc_id:+docId, job_description:jd }) });
        d = await res.json();
        setResult(d.match_analysis ? JSON.stringify(d.match_analysis, null, 2) : d.raw || d.detail);
      } else {
        const ids = [docId, docId2, docId3].filter(Boolean).map(Number);
        if (ids.length < 2) { setResult("Select at least 2 resumes."); setLoading(false); return; }
        res = await api("/agents/hr/compare-resumes", { method:"POST", body: JSON.stringify({ doc_ids:ids, job_description:jd }) });
        d = await res.json();
        setResult(d.comparison ? JSON.stringify(d.comparison, null, 2) : d.raw || d.detail);
      }
    } catch(e) { setResult("Error: " + e.message); }
    setLoading(false);
  };

  const tabs = [["parse","👤 Parse Resume"], ["match","🎯 Job Match"], ["compare","⚖ Compare"]];

  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Parse resumes, match against job descriptions, compare candidates side-by-side.</p>
      <div style={{ display:"flex", gap:6, marginBottom:16, flexWrap:"wrap" }}>
        {tabs.map(([k,label]) => (
          <button key={k} onClick={()=>{setTab(k);setResult("");}} style={{ padding:"6px 14px", borderRadius:7, border:"none", background: tab===k?(dark?"#3f3f3f":"#171717"):(dark?"#2f2f2f":"#f0f0f0"), color:tab===k?"#fff":t.sub, cursor:"pointer", fontSize:12, fontWeight:tab===k?600:400, fontFamily:"inherit" }}>{label}</button>
        ))}
      </div>
      <label style={{ fontSize:11, color:t.sub }}>Resume / CV Document</label>
      <div style={{ marginTop:4, marginBottom:10 }}><DocSelect docs={docs} value={docId} onChange={setDocId} dark={dark} /></div>
      {tab === "compare" && (
        <>
          <label style={{ fontSize:11, color:t.sub }}>Resume 2</label>
          <div style={{ marginTop:4, marginBottom:10 }}><DocSelect docs={docs} value={docId2} onChange={setDocId2} dark={dark} /></div>
          <label style={{ fontSize:11, color:t.sub }}>Resume 3 (optional)</label>
          <div style={{ marginTop:4, marginBottom:10 }}><DocSelect docs={docs} value={docId3} onChange={setDocId3} dark={dark} /></div>
        </>
      )}
      {(tab === "match" || tab === "compare") && (
        <textarea value={jd} onChange={e=>setJd(e.target.value)} placeholder="Paste the Job Description here..." rows={5}
          style={{ width:"100%", padding:"10px", borderRadius:8, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:13, fontFamily:"Inter,sans-serif", resize:"vertical", boxSizing:"border-box" }} />
      )}
      <button onClick={run} disabled={!docId||loading} style={{ marginTop:12, width:"100%", padding:"10px", background:docId&&!loading?(dark?"#3f3f3f":"#171717"):(dark?"#2a2a2a":"#e0e0e0"), color:docId&&!loading?"#fff":t.sub, border:"none", borderRadius:9, cursor:docId&&!loading?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
        {loading ? <><Spinner /> Processing...</> : "Run Analysis"}
      </button>
      <ResultBox content={result} dark={dark} />
    </div>
  );
}

function FinanceMode({ docs, dark, t }) {
  const [docId, setDocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");

  const run = async () => {
    if (!docId) return;
    setLoading(true); setResult("");
    try {
      const res = await api(`/agents/finance/extract/${docId}`, { method:"POST" });
      const d = await res.json();
      setResult(d.financial_data ? JSON.stringify(d.financial_data, null, 2) : d.raw || d.detail);
    } catch(e) { setResult("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Extract financial data from invoices, statements, receipts — dates, totals, line items, vendor details, anomalies.</p>
      <DocSelect docs={docs} value={docId} onChange={setDocId} dark={dark} />
      <button onClick={run} disabled={!docId||loading} style={{ marginTop:12, width:"100%", padding:"10px", background:docId&&!loading?(dark?"#3f3f3f":"#171717"):(dark?"#2a2a2a":"#e0e0e0"), color:docId&&!loading?"#fff":t.sub, border:"none", borderRadius:9, cursor:docId&&!loading?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
        {loading ? <><Spinner /> Extracting...</> : "Extract Financial Data"}
      </button>
      {result && (
        <div style={{ marginTop:16 }}>
          <ResultBox content={result} dark={dark} />
        </div>
      )}
    </div>
  );
}

function NotesMode({ docs, dark, t }) {
  const [docId, setDocId] = useState("");
  const [tab, setTab] = useState("summary");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");

  const run = async () => {
    if (!docId) return;
    setLoading(true); setResult("");
    try {
      const endpoint = tab === "summary" ? `/agents/notes/summarize/${docId}` : `/agents/notes/revision/${docId}`;
      const res = await api(endpoint, { method:"POST" });
      const d = await res.json();
      setResult(d.notes_summary || d.revision_sheet || d.detail);
    } catch(e) { setResult("Error: " + e.message); }
    setLoading(false);
  };

  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Summarize handwritten notes, extract key concepts, and generate revision flashcards.</p>
      <div style={{ display:"flex", gap:6, marginBottom:16 }}>
        {[["summary","📝 Summary & Concepts"], ["revision","🔁 Revision Sheet"]].map(([k,l])=>(
          <button key={k} onClick={()=>{setTab(k);setResult("");}} style={{ padding:"6px 14px", borderRadius:7, border:"none", background:tab===k?(dark?"#3f3f3f":"#171717"):(dark?"#2f2f2f":"#f0f0f0"), color:tab===k?"#fff":t.sub, cursor:"pointer", fontSize:12, fontWeight:tab===k?600:400, fontFamily:"inherit" }}>{l}</button>
        ))}
      </div>
      <DocSelect docs={docs} value={docId} onChange={setDocId} dark={dark} />
      <button onClick={run} disabled={!docId||loading} style={{ marginTop:12, width:"100%", padding:"10px", background:docId&&!loading?(dark?"#3f3f3f":"#171717"):(dark?"#2a2a2a":"#e0e0e0"), color:docId&&!loading?"#fff":t.sub, border:"none", borderRadius:9, cursor:docId&&!loading?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
        {loading ? <><Spinner /> Generating...</> : "Generate"}
      </button>
      <ResultBox content={result} dark={dark} />
    </div>
  );
}

// ── Main Modes page ────────────────────────────────────────────────────────
const MODES = [
  { key:"teacher",  icon:"🎓", label:"Teacher Mode",   desc:"Question papers, answer keys, syllabus maps" },
  { key:"hr",       icon:"💼", label:"HR Mode",         desc:"Resume parsing, job matching, candidate compare" },
  { key:"finance",  icon:"📊", label:"Finance Mode",    desc:"Invoice & statement extraction, anomaly detect" },
  { key:"notes",    icon:"✏️", label:"Notes Mode",       desc:"Handwritten notes summary & revision sheets" },
];

export default function Modes() {
  const { dark } = useTheme();
  const [activeMode, setActiveMode] = useState(null);
  const [docs, setDocs] = useState([]);

  const t = dark
    ? { bg:"#171717", card:"#212121", border:"#2f2f2f", text:"#ececec", sub:"#8e8ea0" }
    : { bg:"#f9f9f9", card:"#ffffff", border:"#e5e5e5", text:"#0d0d0d", sub:"#6b6b6b" };

  useEffect(() => {
    api("/documents/list").then(r=>r.json()).then(d=>setDocs(Array.isArray(d)?d:[])).catch(()=>{});
  }, []);

  return (
    <div style={{ minHeight:"100vh", background:t.bg, fontFamily:"Inter,sans-serif", padding:"32px 20px" }}>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <div style={{ maxWidth:860, margin:"0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom:32 }}>
          <h1 style={{ margin:0, fontSize:24, fontWeight:700, color:t.text }}>Professional Modes</h1>
          <p style={{ margin:"6px 0 0", fontSize:14, color:t.sub }}>Specialized AI tools for teachers, HR professionals, finance teams, and students.</p>
        </div>

        {/* Mode tiles */}
        {!activeMode ? (
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(200px, 1fr))", gap:16 }}>
            {MODES.map(m => (
              <div key={m.key} onClick={()=>setActiveMode(m.key)}
                style={{ background:t.card, border:`1px solid ${t.border}`, borderRadius:14, padding:"28px 20px", cursor:"pointer", transition:"all 0.15s" }}
                onMouseEnter={e=>e.currentTarget.style.transform="translateY(-2px)"}
                onMouseLeave={e=>e.currentTarget.style.transform="translateY(0)"}>
                <div style={{ fontSize:36, marginBottom:12 }}>{m.icon}</div>
                <div style={{ fontSize:15, fontWeight:700, color:t.text, marginBottom:6 }}>{m.label}</div>
                <div style={{ fontSize:12, color:t.sub, lineHeight:1.5 }}>{m.desc}</div>
                <div style={{ marginTop:16, fontSize:12, color: dark?"#5a5a5a":"#c0c0c0" }}>Click to open →</div>
              </div>
            ))}
          </div>
        ) : (
          <div>
            <button onClick={()=>setActiveMode(null)} style={{ background:"transparent", border:`1px solid ${t.border}`, color:t.sub, padding:"6px 14px", borderRadius:8, cursor:"pointer", fontSize:12, fontFamily:"inherit", marginBottom:20 }}>
              ← Back to Modes
            </button>
            <div style={{ background:t.card, border:`1px solid ${t.border}`, borderRadius:14, padding:28 }}>
              <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:20 }}>
                <span style={{ fontSize:28 }}>{MODES.find(m=>m.key===activeMode)?.icon}</span>
                <div>
                  <h2 style={{ margin:0, fontSize:18, fontWeight:700, color:t.text }}>{MODES.find(m=>m.key===activeMode)?.label}</h2>
                  <p style={{ margin:0, fontSize:12, color:t.sub }}>{MODES.find(m=>m.key===activeMode)?.desc}</p>
                </div>
              </div>
              {docs.length === 0 && (
                <div style={{ background: dark?"#2a2a2a":"#fff8e1", border:`1px solid ${dark?"#3f3f3f":"#ffe082"}`, borderRadius:8, padding:"10px 14px", marginBottom:16, fontSize:12, color: dark?"#f59e0b":"#b45309" }}>
                  ⚠ No indexed documents found. Upload and index a PDF first from the Documents page.
                </div>
              )}
              {activeMode === "teacher"  && <TeacherMode docs={docs} dark={dark} t={t} />}
              {activeMode === "hr"       && <HRMode      docs={docs} dark={dark} t={t} />}
              {activeMode === "finance"  && <FinanceMode docs={docs} dark={dark} t={t} />}
              {activeMode === "notes"    && <NotesMode   docs={docs} dark={dark} t={t} />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
