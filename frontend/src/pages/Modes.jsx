import React, { useState, useEffect, useRef, useCallback } from "react";
import { useTheme } from "../context/ThemeContext";
import { useDoc } from "../context/DocContext";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const api = (path, opts = {}) =>
  fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json", ...opts.headers }, ...opts });
const apiUpload = (file) => {
  const form = new FormData(); form.append("file", file);
  return fetch(`${BASE}/documents/upload`, { method: "POST", headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }, body: form });
};


// ── MultiFileUpload — drag-drop + pick from existing docs ──────────────────
function MultiFileUpload({ docs, selectedIds, onSelectionChange, dark, t, label = "Documents" }) {
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const fileRef = useRef();
  const { refreshDocs } = useDoc();

  const toggle = (id) => onSelectionChange(
    selectedIds.includes(id) ? selectedIds.filter(x => x !== id) : [...selectedIds, id]
  );

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    const newIds = [...selectedIds];
    for (const file of files) {
      if (!file.name.endsWith(".pdf")) { setUploadMsg(`Skipped ${file.name} — only PDFs`); continue; }
      setUploadMsg(`Uploading ${file.name}...`);
      try {
        const r = await apiUpload(file);
        const d = await r.json();
        if (d.doc_id) {
          newIds.push(d.doc_id);
          setUploadMsg(d.reused ? `⚡ ${file.name} — reused instantly (same content)` : `✅ ${file.name} uploaded`);
        }
      } catch { setUploadMsg(`❌ Failed: ${file.name}`); }
    }
    await refreshDocs();
    onSelectionChange(newIds);
    setUploading(false);
    setTimeout(() => setUploadMsg(""), 3000);
  };

  return (
    <div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:6 }}>
        <span style={{ fontSize:11, color:t.sub, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.5px" }}>
          {label} <span style={{ color: selectedIds.length > 0 ? "#3fb950" : t.sub }}>({selectedIds.length} selected)</span>
        </span>
        <button onClick={() => fileRef.current?.click()} disabled={uploading}
          style={{ background:"transparent", border:`1px solid ${dark?"#3f3f3f":"#d0d0d0"}`, color:t.sub, padding:"3px 10px", borderRadius:6, cursor:"pointer", fontSize:11, fontFamily:"inherit" }}>
          {uploading ? "Uploading..." : "➕ Upload PDF(s)"}
        </button>
      </div>
      <input ref={fileRef} type="file" accept=".pdf" multiple style={{ display:"none" }}
        onChange={e => handleFiles(Array.from(e.target.files || []))} />
      {uploadMsg && <div style={{ fontSize:11, color:"#3fb950", marginBottom:6, padding:"4px 8px", background:dark?"rgba(63,185,80,0.1)":"#f0fdf4", borderRadius:6 }}>{uploadMsg}</div>}
      <div style={{ maxHeight:160, overflowY:"auto", border:`1px solid ${t.border}`, borderRadius:8, background:dark?"#1a1a1a":"#fafafa" }}>
        {docs.length === 0 ? (
          <p style={{ padding:"12px 14px", fontSize:12, color:t.sub, margin:0 }}>No documents yet. Upload a PDF above.</p>
        ) : docs.map(d => (
          <div key={d.id} onClick={() => toggle(d.id)}
            style={{ display:"flex", alignItems:"center", gap:8, padding:"7px 12px", cursor:"pointer",
              background: selectedIds.includes(d.id) ? (dark?"rgba(31,111,235,0.15)":"#eff6ff") : "transparent",
              borderBottom:`1px solid ${t.border}` }}>
            <div style={{ width:14, height:14, borderRadius:3, border:`2px solid ${selectedIds.includes(d.id)?"#1f6feb":t.border}`,
              background: selectedIds.includes(d.id) ? "#1f6feb" : "transparent", flexShrink:0,
              display:"flex", alignItems:"center", justifyContent:"center" }}>
              {selectedIds.includes(d.id) && <span style={{ color:"#fff", fontSize:9, fontWeight:700 }}>✓</span>}
            </div>
            <span style={{ fontSize:12, color:t.text, flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{d.original_name || d.filename}</span>
            <span style={{ fontSize:10, color: d.status==="Ready"?"#3fb950":"#d29922" }}>{d.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

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
  const [docIds, setDocIds] = useState([]);
  const [tab, setTab]   = useState("qpaper");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState("");
  const [description, setDescription] = useState("");
  const [examStyle, setExamStyle] = useState("university");
  // Multi-section blueprint
  const defaultSections = [
    { name:"Part A", marks_each:2, num_questions:10, allow_sub:false },
    { name:"Part B", marks_each:10, num_questions:5, allow_sub:true },
    { name:"Part C", marks_each:20, num_questions:2, allow_sub:true },
  ];
  const [sections, setSections] = useState(defaultSections);
  const [cfg, setCfg] = useState({ difficulty:"mixed", include_answers:false, units:"all units" });
  const [bank, setBank] = useState(() => JSON.parse(localStorage.getItem("questionBank") || "[]"));
  const [bankTag, setBankTag] = useState("");
  const abortRef = useRef(null);

  const totalMarks = sections.reduce((s,sec) => s + sec.marks_each * sec.num_questions, 0);

  const updateSection = (i, field, val) =>
    setSections(s => s.map((sec, idx) => idx === i ? {...sec, [field]: val} : sec));
  const addSection = () => setSections(s => [...s, { name:`Part ${String.fromCharCode(65+s.length)}`, marks_each:5, num_questions:5, allow_sub:false }]);
  const removeSection = (i) => setSections(s => s.filter((_,idx) => idx !== i));

  const saveToBank = () => {
    if (!result.trim()) return;
    const entry = { id:Date.now(), text:result, tag:bankTag||"General", doc:`${docIds.length} doc(s)`, ts:new Date().toLocaleString() };
    const updated = [entry, ...bank].slice(0,100);
    setBank(updated); localStorage.setItem("questionBank", JSON.stringify(updated));
    setBankTag("");
  };
  const deleteFromBank = (id) => {
    const updated = bank.filter(e => e.id !== id);
    setBank(updated); localStorage.setItem("questionBank", JSON.stringify(updated));
  };

  const run = async () => {
    if (docIds.length === 0) return;
    setLoading(true); setResult("");
    const ctrl = new AbortController(); abortRef.current = ctrl;
    try {
      let res, d;
      if (tab === "qpaper") {
        // Use multi-doc advanced endpoint if multiple docs selected
        const endpoint = docIds.length > 1 ? "/agents/teacher/question-paper-multi" : "/agents/teacher/question-paper";
        const body = docIds.length > 1
          ? { doc_ids: docIds.map(Number), sections, difficulty: cfg.difficulty, description, include_answers: cfg.include_answers, exam_style: examStyle }
          : { doc_id: +docIds[0], sections, difficulty: cfg.difficulty, description, include_answers: cfg.include_answers, units: cfg.units, total_marks: totalMarks, num_questions: sections.reduce((s,sec)=>s+sec.num_questions,0) };
        res = await api(endpoint, { method:"POST", body: JSON.stringify(body), signal: ctrl.signal });
        d = await res.json(); setResult(d.question_paper || d.detail || JSON.stringify(d));
      } else if (tab === "answers") {
        res = await api(`/agents/teacher/answer-key/${docIds[0]}`, { method:"POST", signal: ctrl.signal });
        d = await res.json(); setResult(d.answer_key || d.detail);
      } else {
        res = await api(`/agents/teacher/syllabus-map/${docIds[0]}`, { method:"POST", signal: ctrl.signal });
        d = await res.json(); setResult(d.syllabus_map || d.detail);
      }
    } catch(e) { if (e.name !== "AbortError") setResult("Error: " + e.message); }
    setLoading(false);
  };

  const stop = () => { abortRef.current?.abort(); setLoading(false); };
  const tabs = [["qpaper","📝 Question Paper"], ["answers","🔑 Answer Key"], ["syllabus","🗺 Syllabus Map"], ["bank",`📚 Bank (${bank.length})`]];
  const canRun = docIds.length > 0 && !loading && tab !== "bank";


  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Generate question papers, answer keys, and syllabus maps from any academic PDF.</p>
      <div style={{ display:"flex", gap:6, marginBottom:16, flexWrap:"wrap" }}>
        {tabs.map(([k,label]) => (
          <button key={k} onClick={()=>{setTab(k);setResult("");}} style={{ padding:"6px 14px", borderRadius:7, border:"none", background: tab===k ? (dark?"#3f3f3f":"#171717") : (dark?"#2f2f2f":"#f0f0f0"), color: tab===k ? "#fff" : t.sub, cursor:"pointer", fontSize:12, fontWeight: tab===k?600:400, fontFamily:"inherit" }}>{label}</button>
        ))}
      </div>
      <MultiFileUpload docs={docs} selectedIds={docIds} onSelectionChange={setDocIds} dark={dark} t={t} label="Source PDFs (upload multiple units/chapters)" />
      {tab === "qpaper" && (
        <div style={{ marginTop:14 }}>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8, marginBottom:10 }}>
            <div>
              <label style={{ fontSize:11, color:t.sub }}>Difficulty</label>
              <select value={cfg.difficulty} onChange={e=>setCfg(c=>({...c,difficulty:e.target.value}))} style={{ width:"100%", padding:"6px 8px", borderRadius:7, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4 }}>
                {["easy","medium","hard","mixed"].map(d=><option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize:11, color:t.sub }}>Exam Style</label>
              <select value={examStyle} onChange={e=>setExamStyle(e.target.value)} style={{ width:"100%", padding:"6px 8px", borderRadius:7, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4 }}>
                {["university","board","internal","entrance","practice"].map(s=><option key={s}>{s}</option>)}
              </select>
            </div>
            <div style={{ display:"flex", alignItems:"flex-end", gap:8, paddingBottom:4 }}>
              <input type="checkbox" id="inclAns2" checked={cfg.include_answers} onChange={e=>setCfg(c=>({...c,include_answers:e.target.checked}))} />
              <label htmlFor="inclAns2" style={{ fontSize:12, color:t.text }}>Include answers</label>
            </div>
          </div>
          {/* Section Blueprint — Part A / B / C */}
          <p style={{ fontSize:11, color:t.sub, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.5px", margin:"12px 0 8px" }}>
            Paper Blueprint — Total: <span style={{ color:"#3fb950" }}>{totalMarks} marks</span>
          </p>
          {sections.map((sec, i) => (
            <div key={i} style={{ display:"grid", gridTemplateColumns:"2fr 1fr 1fr 1fr auto", gap:6, marginBottom:8, alignItems:"center" }}>
              <input value={sec.name} onChange={e=>updateSection(i,"name",e.target.value)} style={{ padding:"5px 8px", borderRadius:6, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit" }} />
              <div>
                <input type="number" min={1} value={sec.num_questions} onChange={e=>updateSection(i,"num_questions",+e.target.value)} placeholder="Qs" style={{ width:"100%", padding:"5px 8px", borderRadius:6, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", boxSizing:"border-box" }} />
              </div>
              <div>
                <input type="number" min={1} value={sec.marks_each} onChange={e=>updateSection(i,"marks_each",+e.target.value)} placeholder="Marks" style={{ width:"100%", padding:"5px 8px", borderRadius:6, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", boxSizing:"border-box" }} />
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:4 }}>
                <input type="checkbox" id={`sub${i}`} checked={sec.allow_sub} onChange={e=>updateSection(i,"allow_sub",e.target.checked)} />
                <label htmlFor={`sub${i}`} style={{ fontSize:11, color:t.sub, whiteSpace:"nowrap" }}>Sub-Qs</label>
              </div>
              <button onClick={()=>removeSection(i)} style={{ background:"transparent", border:"1px solid rgba(248,81,73,0.4)", color:"#f85149", padding:"3px 8px", borderRadius:5, cursor:"pointer", fontSize:11, fontFamily:"inherit" }}>×</button>
            </div>
          ))}
          <button onClick={addSection} style={{ background:"transparent", border:`1px dashed ${t.border}`, color:t.sub, padding:"5px 14px", borderRadius:7, cursor:"pointer", fontSize:12, fontFamily:"inherit", marginBottom:10 }}>+ Add Section</button>
          <textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Special instructions (optional): e.g. Focus on Unit 3, include one table question, avoid repeating topics, more application questions..." rows={2}
            style={{ width:"100%", padding:"8px 10px", borderRadius:7, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"Inter,sans-serif", resize:"vertical", boxSizing:"border-box" }} />
        </div>
      )}
      {tab !== "bank" && (
        <div style={{ display:"flex", gap:8, marginTop:14 }}>
          <button onClick={run} disabled={!canRun} style={{ flex:1, padding:"10px", background:canRun?(dark?"#3f3f3f":"#171717"):(dark?"#2a2a2a":"#e0e0e0"), color:canRun?"#fff":t.sub, border:"none", borderRadius:9, cursor:canRun?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
            {loading ? <><Spinner /> Generating...</> : "Generate"}
          </button>
          {loading && <button onClick={stop} style={{ padding:"10px 16px", background:"rgba(248,81,73,0.15)", border:"1px solid #f85149", color:"#f85149", borderRadius:9, cursor:"pointer", fontSize:13, fontWeight:600, fontFamily:"inherit" }}>⏹ Stop</button>}
        </div>
      )}
      {tab !== "bank" && result && (
        <div style={{ marginTop:12 }}>
          <div style={{ display:"flex", gap:8, alignItems:"center", marginBottom:6 }}>
            <input value={bankTag} onChange={e=>setBankTag(e.target.value)} placeholder="Tag (e.g. Unit 1, Hard)" style={{ flex:1, padding:"6px 10px", borderRadius:7, border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit" }} />
            <button onClick={saveToBank} style={{ padding:"6px 14px", background:"#3fb950", color:"#fff", border:"none", borderRadius:7, cursor:"pointer", fontSize:12, fontWeight:600, fontFamily:"inherit", whiteSpace:"nowrap" }}>💾 Save to Bank</button>
          </div>
          <ResultBox content={result} dark={dark} />
        </div>
      )}
      {tab === "bank" && (
        <div style={{ marginTop:12 }}>
          {bank.length === 0 ? (
            <p style={{ color:t.sub, fontSize:13, textAlign:"center", padding:"30px 0" }}>No saved questions yet. Generate questions and click "Save to Bank".</p>
          ) : bank.map(e => (
            <div key={e.id} style={{ background:dark?"#1a1a1a":"#f5f5f5", border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, borderRadius:10, padding:14, marginBottom:10 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8, flexWrap:"wrap", gap:4 }}>
                <div style={{ display:"flex", gap:6 }}>
                  <span style={{ background:dark?"#2f2f2f":"#efefef", padding:"2px 8px", borderRadius:10, fontSize:11, color:t.text, fontWeight:600 }}>{e.tag}</span>
                  <span style={{ fontSize:11, color:t.sub }}>{e.doc}</span>
                </div>
                <div style={{ display:"flex", gap:6, alignItems:"center" }}>
                  <span style={{ fontSize:10, color:t.sub }}>{e.ts}</span>
                  <button onClick={()=>{navigator.clipboard.writeText(e.text)}} style={{ background:"transparent", border:`1px solid ${dark?"#3f3f3f":"#d0d0d0"}`, color:t.sub, padding:"2px 8px", borderRadius:5, cursor:"pointer", fontSize:10, fontFamily:"inherit" }}>Copy</button>
                  <button onClick={()=>deleteFromBank(e.id)} style={{ background:"transparent", border:"1px solid rgba(248,81,73,0.4)", color:"#f85149", padding:"2px 8px", borderRadius:5, cursor:"pointer", fontSize:10, fontFamily:"inherit" }}>Delete</button>
                </div>
              </div>
              <pre style={{ margin:0, fontSize:12, color:t.text, whiteSpace:"pre-wrap", maxHeight:180, overflowY:"auto", fontFamily:"Inter,monospace" }}>{e.text.slice(0,600)}{e.text.length>600?"…":""}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function HRMode({ docs, dark, t }) {
  const [tab, setTab] = useState("parse"); // parse | match | compare
  const [docId, setDocId] = useState("");
  const [chartData, setChartData] = useState(null);
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
        setChartData(d.comparison || null);
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
      {/* Visual Score Dashboard — shown after compare */}
      {tab === "compare" && chartData && Array.isArray(chartData) && (
        <div style={{ marginTop:16, background:dark?"#1a1a1a":"#f8f8f8", border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, borderRadius:12, padding:16 }}>
          <p style={{ margin:"0 0 14px", fontSize:12, fontWeight:700, color:t.sub, textTransform:"uppercase", letterSpacing:"0.5px" }}>📊 Candidate Score Dashboard</p>
          {chartData.map((c, i) => (
            <div key={i} style={{ marginBottom:14 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                <span style={{ fontSize:13, fontWeight:600, color:t.text }}>{c.candidate || `Candidate ${i+1}`}</span>
                <span style={{ fontSize:13, fontWeight:700, color: c.score>=70?"#3fb950":c.score>=50?"#d29922":"#f85149" }}>{c.score ?? "?"}/100</span>
              </div>
              <div style={{ height:10, background:dark?"#2f2f2f":"#e8e8e8", borderRadius:6, overflow:"hidden" }}>
                <div style={{ height:"100%", width:`${c.score||0}%`, background: c.score>=70?"#3fb950":c.score>=50?"#d29922":"#f85149", borderRadius:6, transition:"width 0.6s ease" }} />
              </div>
              <div style={{ fontSize:11, color:t.sub, marginTop:3 }}>{c.verdict || c.recommendation || ""}</div>
            </div>
          ))}
        </div>
      )}
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

// ── Phase 9: Workflow Mode ─────────────────────────────────────────────────
const WORKFLOW_STEPS = [
  { id:"summarize", label:"📋 Summarize", endpoint: id=>`/agents/summarize/${id}`, key:"summary" },
  { id:"concepts",  label:"💡 Key Concepts", endpoint: id=>`/agents/key-concepts/${id}`, key:"key_concepts" },
  { id:"tables",    label:"📊 Export Tables", endpoint: id=>`/agents/export-table/${id}`, key:"markdown_tables" },
  { id:"qpaper",   label:"📝 Question Paper", endpoint: null, key:"question_paper" },
  { id:"resume",   label:"👤 Parse Resume", endpoint: id=>`/agents/hr/parse-resume/${id}`, key:"parsed_resume" },
  { id:"finance",  label:"💰 Finance Extract", endpoint: id=>`/agents/finance/extract/${id}`, key:"financial_data" },
];

function WorkflowMode({ docs, dark, t }) {
  const [docId, setDocId] = useState("");
  const [selected, setSelected] = useState(["summarize", "concepts"]);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState({});
  const [progress, setProgress] = useState([]);

  const toggle = (id) => setSelected(s => s.includes(id) ? s.filter(x=>x!==id) : [...s, id]);

  const runWorkflow = async () => {
    if (!docId || selected.length === 0) return;
    setRunning(true); setResults({}); setProgress([]);
    for (const stepId of selected) {
      const step = WORKFLOW_STEPS.find(s=>s.id===stepId);
      if (!step || !step.endpoint) { setProgress(p=>[...p, `⚠ ${step?.label} skipped (needs config)`]); continue; }
      setProgress(p=>[...p, `⏳ Running ${step.label}...`]);
      try {
        const res = await api(step.endpoint(docId), { method:"POST" });
        const d = await res.json();
        const val = d[step.key];
        const out = typeof val === "object" ? JSON.stringify(val, null, 2) : (val || d.raw || d.detail || "No output");
        setResults(r=>({...r, [stepId]: out}));
        setProgress(p=>[...p.slice(0,-1), `✅ ${step.label} done`]);
      } catch(e) {
        setProgress(p=>[...p.slice(0,-1), `❌ ${step.label} failed: ${e.message}`]);
      }
    }
    setRunning(false);
  };

  const exportAll = () => {
    const text = Object.entries(results).map(([k,v])=>{
      const label = WORKFLOW_STEPS.find(s=>s.id===k)?.label || k;
      return `${'='.repeat(50)}\n${label}\n${'='.repeat(50)}\n${v}`;
    }).join("\n\n");
    const a = document.createElement("a"); a.href = `data:text/plain;charset=utf-8,${encodeURIComponent(text)}`; a.download = "workflow_result.txt"; a.click();
  };

  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Select a document and chain multiple AI operations in one click. Results are shown step by step.</p>
      <DocSelect docs={docs} value={docId} onChange={setDocId} dark={dark} />
      <p style={{ fontSize:11, color:t.sub, margin:"14px 0 8px", fontWeight:600, textTransform:"uppercase", letterSpacing:"0.5px" }}>Select Steps to Run</p>
      <div style={{ display:"flex", flexWrap:"wrap", gap:8, marginBottom:16 }}>
        {WORKFLOW_STEPS.map(s=>(
          <button key={s.id} onClick={()=>toggle(s.id)}
            style={{ padding:"6px 14px", borderRadius:8, border:`1px solid ${selected.includes(s.id)?(dark?"#3fb950":"#171717"):t.border}`, background:selected.includes(s.id)?(dark?"rgba(63,185,80,0.12)":"#171717"):"transparent", color:selected.includes(s.id)?(dark?"#3fb950":"#fff"):t.sub, cursor:"pointer", fontSize:12, fontFamily:"inherit", fontWeight:selected.includes(s.id)?600:400 }}>
            {s.label}
          </button>
        ))}
      </div>
      <button onClick={runWorkflow} disabled={!docId||running||selected.length===0}
        style={{ width:"100%", padding:"10px", background:docId&&!running&&selected.length>0?(dark?"#3f3f3f":"#171717"):(dark?"#2a2a2a":"#e0e0e0"), color:docId&&!running&&selected.length>0?"#fff":t.sub, border:"none", borderRadius:9, cursor:docId&&!running&&selected.length>0?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
        {running ? <><Spinner /> Running workflow...</> : `▶ Run ${selected.length} Step${selected.length!==1?"s":""}`}
      </button>
      {progress.length > 0 && (
        <div style={{ marginTop:12, background:dark?"#1a1a1a":"#f5f5f5", border:`1px solid ${dark?"#3f3f3f":"#e0e0e0"}`, borderRadius:9, padding:12 }}>
          {progress.map((p,i)=><div key={i} style={{ fontSize:12, color:t.text, padding:"2px 0" }}>{p}</div>)}
        </div>
      )}
      {Object.keys(results).length > 0 && (
        <div style={{ marginTop:8 }}>
          <div style={{ display:"flex", justifyContent:"flex-end", marginBottom:8 }}>
            <button onClick={exportAll} style={{ background:dark?"#3f3f3f":"#171717", color:"#fff", border:"none", padding:"6px 14px", borderRadius:7, cursor:"pointer", fontSize:12, fontWeight:600, fontFamily:"inherit" }}>⬇ Export All Results</button>
          </div>
          {Object.entries(results).map(([k,v])=>(
            <div key={k} style={{ marginBottom:12 }}>
              <p style={{ margin:"0 0 4px", fontSize:11, fontWeight:700, color:t.sub, textTransform:"uppercase" }}>{WORKFLOW_STEPS.find(s=>s.id===k)?.label}</p>
              <ResultBox content={typeof v==="string"?v:JSON.stringify(v,null,2)} dark={dark} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Student Mode ─────────────────────────────────────────────────────────
function StudentMode({ docs, dark, t }) {
  const [docIds, setDocIds] = useState([]);
  const [tab, setTab] = useState("plan");  // plan | flashcards | cheatsheet
  const [timePlan, setTimePlan] = useState("1 day");
  const [focus, setFocus] = useState("");
  const [includeQna, setIncludeQna] = useState(true);
  const [topic, setTopic] = useState("all topics");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const abortRef = useRef(null);

  const run = async () => {
    if (docIds.length === 0) return;
    setLoading(true); setResult("");
    const ctrl = new AbortController(); abortRef.current = ctrl;
    try {
      let res, d;
      if (tab === "plan") {
        res = await api("/agents/student/study-plan",
          { method:"POST", body: JSON.stringify({ doc_ids: docIds.map(Number), time_plan: timePlan, focus, include_qna: includeQna }), signal: ctrl.signal });
        d = await res.json(); setResult(d.study_plan || d.detail);
      } else if (tab === "flashcards") {
        res = await api("/agents/student/flashcards",
          { method:"POST", body: JSON.stringify({ doc_ids: docIds.map(Number), topic, count: 20 }), signal: ctrl.signal });
        d = await res.json(); setResult(d.flashcards || d.detail);
      } else {
        // cheatsheet — re-use study plan with 30 min window
        res = await api("/agents/student/study-plan",
          { method:"POST", body: JSON.stringify({ doc_ids: docIds.map(Number), time_plan: "15 minutes", focus: "only absolute must-know, ultra-concise cheat sheet", include_qna: false }), signal: ctrl.signal });
        d = await res.json(); setResult(d.study_plan || d.detail);
      }
    } catch(e) { if (e.name !== "AbortError") setResult("Error: " + e.message); }
    setLoading(false);
  };

  const stop = () => { abortRef.current?.abort(); setLoading(false); };
  const TIME_OPTIONS = ["15 minutes", "30 minutes", "1 hour", "3 hours", "1 day", "2 days"];
  const TABS = [["plan","📅 Study Plan"], ["flashcards","🎴 Flashcards"], ["cheatsheet","⚡ Cheat Sheet"]];
  const ready = docIds.length > 0 && !loading;
  const BG = (on) => on ? (dark?"#3f3f3f":"#171717") : (dark?"#2f2f2f":"#f0f0f0");

  return (
    <div>
      <p style={{ fontSize:13, color:t.sub, marginBottom:16 }}>Upload your syllabus, notes, and past papers. Get a complete time-based study plan, flashcards, or a last-minute cheat sheet.</p>
      <div style={{ display:"flex", gap:6, marginBottom:16, flexWrap:"wrap" }}>
        {TABS.map(([k,l]) => (
          <button key={k} onClick={() => {setTab(k);setResult("");}} style={{ padding:"6px 14px", borderRadius:7, border:"none", background:BG(tab===k), color:tab===k?"#fff":t.sub, cursor:"pointer", fontSize:12, fontWeight:tab===k?600:400, fontFamily:"inherit" }}>{l}</button>
        ))}
      </div>
      <MultiFileUpload docs={docs} selectedIds={docIds} onSelectionChange={setDocIds} dark={dark} t={t} label="Study Materials (syllabus, notes, past papers)" />
      <div style={{ marginTop:14, display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
        {tab === "plan" && (
          <div>
            <label style={{ fontSize:11, color:t.sub }}>Time Available</label>
            <select value={timePlan} onChange={e=>setTimePlan(e.target.value)} style={{ width:"100%", padding:"7px 10px", borderRadius:7, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4 }}>
              {TIME_OPTIONS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
        )}
        {tab === "flashcards" && (
          <div>
            <label style={{ fontSize:11, color:t.sub }}>Topic / Unit</label>
            <input value={topic} onChange={e=>setTopic(e.target.value)} placeholder="e.g. Unit 3 — Neural Networks" style={{ width:"100%", padding:"7px 10px", borderRadius:7, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"inherit", marginTop:4, boxSizing:"border-box" }} />
          </div>
        )}
        {tab === "plan" && (
          <div style={{ display:"flex", alignItems:"flex-end", gap:8 }}>
            <input type="checkbox" id="incqna" checked={includeQna} onChange={e=>setIncludeQna(e.target.checked)} />
            <label htmlFor="incqna" style={{ fontSize:12, color:t.text }}>Include likely exam Q&amp;A</label>
          </div>
        )}
      </div>
      {tab === "plan" && (
        <textarea value={focus} onChange={e=>setFocus(e.target.value)} placeholder="Special focus (optional): e.g. skip Unit 1, focus on Unit 3 and 4 only..." rows={2}
          style={{ width:"100%", marginTop:10, padding:"8px 10px", borderRadius:7, border:`1px solid ${t.border}`, background:dark?"#2f2f2f":"#fff", color:t.text, fontSize:12, fontFamily:"Inter,sans-serif", resize:"vertical", boxSizing:"border-box" }} />
      )}
      <div style={{ display:"flex", gap:8, marginTop:14 }}>
        <button onClick={run} disabled={!ready} style={{ flex:1, padding:"10px", background:ready?(dark?"#3f3f3f":"#171717"):(dark?"#2a2a2a":"#e0e0e0"), color:ready?"#fff":t.sub, border:"none", borderRadius:9, cursor:ready?"pointer":"not-allowed", fontSize:14, fontWeight:600, fontFamily:"inherit", display:"flex", alignItems:"center", justifyContent:"center", gap:8 }}>
          {loading ? <><Spinner /> Generating...</> : tab==="plan" ? `📅 Create ${timePlan} Plan` : tab==="flashcards" ? "🎴 Generate Flashcards" : "⚡ Generate Cheat Sheet"}
        </button>
        {loading && <button onClick={stop} style={{ padding:"10px 16px", background:"rgba(248,81,73,0.15)", border:"1px solid #f85149", color:"#f85149", borderRadius:9, cursor:"pointer", fontSize:13, fontWeight:600, fontFamily:"inherit" }}>⏹ Stop</button>}
      </div>
      <ResultBox content={result} dark={dark} />
    </div>
  );
}

// ── Main Modes page ────────────────────────────────────────────────────────
const MODES = [
  { key:"teacher",  icon:"🎓", label:"Teacher Mode",   desc:"Question papers, answer keys, syllabus maps, question bank" },
  { key:"hr",       icon:"💼", label:"HR Mode",         desc:"Resume parsing, job match, compare with score chart" },
  { key:"finance",  icon:"📊", label:"Finance Mode",    desc:"Invoice & statement extraction, anomaly detect" },
  { key:"notes",    icon:"✏️", label:"Notes Mode",       desc:"Handwritten notes summary & revision sheets" },
  { key:"student",  icon:"📚", label:"Student Mode",     desc:"Time-based study plans, flashcards, cheat sheets from any PDFs" },
  { key:"workflow", icon:"⚙️", label:"Workflow",         desc:"Chain multiple AI steps in one click, export all" },
];


export default function Modes() {
  const { dark } = useTheme();
  const { docs, refreshDocs } = useDoc();   // ← shared global docs (always in sync)
  const [activeMode, setActiveMode] = useState(null);

  const t = dark
    ? { bg:"#171717", card:"#212121", border:"#2f2f2f", text:"#ececec", sub:"#8e8ea0" }
    : { bg:"#f9f9f9", card:"#ffffff", border:"#e5e5e5", text:"#0d0d0d", sub:"#6b6b6b" };

  useEffect(() => { refreshDocs(); }, []); // eslint-disable-line


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
              {activeMode === "teacher"  && <TeacherMode  docs={docs} dark={dark} t={t} />}
              {activeMode === "hr"       && <HRMode       docs={docs} dark={dark} t={t} />}
              {activeMode === "finance"  && <FinanceMode  docs={docs} dark={dark} t={t} />}
              {activeMode === "notes"    && <NotesMode    docs={docs} dark={dark} t={t} />}
              {activeMode === "student"  && <StudentMode  docs={docs} dark={dark} t={t} />}
              {activeMode === "workflow" && <WorkflowMode docs={docs} dark={dark} t={t} />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
