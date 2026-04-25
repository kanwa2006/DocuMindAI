import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { docsAPI } from "../api/client";
import { useTheme } from "../context/ThemeContext";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const authHdr = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });
const apiFetch = (path, opts = {}) =>
  fetch(`${BASE}${path}`, {
    headers: { ...authHdr(), "Content-Type": "application/json", ...opts.headers },
    ...opts,
  }).then(r => r.json());

const CONF_COLOR = { high: "#22c55e", medium: "#f59e0b", low: "#ef4444" };
const CONF_BG    = { high: "rgba(34,197,94,0.08)", medium: "rgba(245,158,11,0.08)", low: "rgba(239,68,68,0.08)" };

function Badge({ label, color, bg }) {
  return (
    <span style={{ background: bg, color, padding: "2px 9px", borderRadius: 12, fontSize: 11, fontWeight: 700, letterSpacing: "0.3px" }}>
      {label}
    </span>
  );
}

function CopyBtn({ label, onClick, color = "#1f6feb" }) {
  const [copied, setCopied] = useState(false);
  const handle = () => {
    onClick();
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <button onClick={handle} style={{ background: copied ? "#3fb950" : "transparent", border: `1px solid ${copied ? "#3fb950" : color}`, color: copied ? "#fff" : color, padding: "4px 11px", borderRadius: 6, cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "inherit", transition: "all 0.2s" }}>
      {copied ? "✓ Copied!" : label}
    </button>
  );
}

// ── Crop Tool ─────────────────────────────────────────────────────────────────
function CropTool({ imgSrc, pageNum, onClose }) {
  const containerRef = useRef(null);
  const nativeImg    = useRef(new Image());
  const [isDragging, setIsDragging] = useState(false);
  const [start, setStart]   = useState({ x: 0, y: 0 });
  const [end, setEnd]       = useState({ x: 0, y: 0 });
  const [crop, setCrop]     = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => { nativeImg.current.src = imgSrc; }, [imgSrc]);

  const getPos = (e) => {
    const rect = containerRef.current.getBoundingClientRect();
    const src  = e.touches ? e.touches[0] : e;
    return { x: src.clientX - rect.left, y: src.clientY - rect.top };
  };

  const norm = (a, b) => ({ x: Math.min(a.x,b.x), y: Math.min(a.y,b.y), w: Math.abs(b.x-a.x), h: Math.abs(b.y-a.y) });

  const buildCanvas = () => {
    const imgEl = containerRef.current?.querySelector("img");
    if (!imgEl || !crop || crop.w < 5 || crop.h < 5) return null;
    const sx = nativeImg.current.naturalWidth  / imgEl.clientWidth;
    const sy = nativeImg.current.naturalHeight / imgEl.clientHeight;
    const c  = document.createElement("canvas");
    c.width  = crop.w; c.height = crop.h;
    c.getContext("2d").drawImage(nativeImg.current, crop.x*sx, crop.y*sy, crop.w*sx, crop.h*sy, 0, 0, crop.w, crop.h);
    return c;
  };

  const doCopy = () => {
    const c = buildCanvas(); if (!c) return;
    c.toBlob(blob => {
      navigator.clipboard.write([new ClipboardItem({ "image/png": blob })])
        .then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); })
        .catch(() => alert("Copy failed — try Download instead."));
    });
  };

  const doDownload = () => {
    const c = buildCanvas(); if (!c) return;
    const a = document.createElement("a"); a.href = c.toDataURL(); a.download = `crop_pg${pageNum}.png`; a.click();
  };

  const selRect = norm(start, end);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.88)", zIndex: 2000, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: "Inter,sans-serif" }}>
      {/* Controls */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: "#8b949e", fontSize: 12 }}>🖱 Drag to select area on image</span>
        <button onClick={doCopy} disabled={!crop} style={{ background: crop ? (copied ? "#3fb950" : "#1f6feb") : "#30363d", color: "#fff", border: "none", padding: "6px 14px", borderRadius: 7, cursor: crop ? "pointer" : "not-allowed", fontSize: 12, fontWeight: 600, fontFamily: "inherit" }}>
          {copied ? "✓ Copied!" : "📋 Copy Crop"}
        </button>
        <button onClick={doDownload} disabled={!crop} style={{ background: crop ? "#8250df" : "#30363d", color: "#fff", border: "none", padding: "6px 14px", borderRadius: 7, cursor: crop ? "pointer" : "not-allowed", fontSize: 12, fontWeight: 600, fontFamily: "inherit" }}>⬇ Download Crop</button>
        <button onClick={onClose} style={{ background: "transparent", border: "1px solid #636c76", color: "#e6edf3", padding: "6px 14px", borderRadius: 7, cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>✕ Exit Crop</button>
      </div>
      {crop && <div style={{ marginBottom: 8, fontSize: 11, color: "#3fb950" }}>✓ {Math.round(crop.w)} × {Math.round(crop.h)} px selected</div>}
      {/* Image area */}
      <div ref={containerRef} style={{ position: "relative", cursor: "crosshair", userSelect: "none", maxWidth: "90vw", maxHeight: "78vh" }}
        onMouseDown={e => { const p=getPos(e); setStart(p); setEnd(p); setCrop(null); setIsDragging(true); }}
        onMouseMove={e => { if(isDragging) setEnd(getPos(e)); }}
        onMouseUp={e   => { setIsDragging(false); const r=norm(start,getPos(e)); if(r.w>5&&r.h>5) setCrop(r); }}
        onTouchStart={e=>{ const p=getPos(e); setStart(p); setEnd(p); setCrop(null); setIsDragging(true); }}
        onTouchMove={e =>{ if(isDragging) setEnd(getPos(e)); }}
        onTouchEnd={e  =>{ setIsDragging(false); const r=norm(start,end); if(r.w>5&&r.h>5) setCrop(r); }}
      >
        <img src={imgSrc} alt="crop" draggable={false} style={{ display: "block", maxWidth: "90vw", maxHeight: "78vh", borderRadius: 6 }} />
        {/* Live drag rect */}
        {isDragging && selRect.w > 2 && (
          <div style={{ position: "absolute", left: selRect.x, top: selRect.y, width: selRect.w, height: selRect.h, border: "2px solid #1f6feb", background: "rgba(31,111,235,0.15)", pointerEvents: "none" }} />
        )}
        {/* Final selection */}
        {crop && !isDragging && (
          <div style={{ position: "absolute", left: crop.x, top: crop.y, width: crop.w, height: crop.h, border: "2px solid #3fb950", background: "rgba(63,185,80,0.1)", pointerEvents: "none" }}>
            <div style={{ position: "absolute", inset: 0, outline: "1px dashed rgba(63,185,80,0.5)", outlineOffset: -3 }} />
          </div>
        )}
      </div>
    </div>
  );
}

function PageImage({ src, pageNum, dark }) {
  const [cropMode, setCropMode] = useState(false);

  const copyImage = useCallback(async () => {
    try {
      const res = await fetch(src);
      const blob = await res.blob();
      await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    } catch { alert("Could not copy — right-click the image and choose Copy Image instead."); }
  }, [src]);

  const download = () => {
    const a = document.createElement("a"); a.href = src; a.download = `page_${pageNum}.png`; a.click();
  };

  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
        <CopyBtn label="📋 Copy Image" onClick={copyImage} color="#8250df" />
        <button onClick={() => setCropMode(true)} style={{ background: "transparent", border: "1px solid #d29922", color: "#d29922", padding: "4px 10px", borderRadius: 6, cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "inherit" }}>✂ Crop & Copy</button>
        <button onClick={download} style={{ background: "transparent", border: "1px solid #30363d", color: "#8b949e", padding: "4px 10px", borderRadius: 6, cursor: "pointer", fontSize: 11, fontFamily: "inherit" }}>⬇ Save PNG</button>
      </div>
      <img src={src} alt={`Page ${pageNum}`} style={{ width: "100%", borderRadius: 8, border: `1px solid ${dark ? "#30363d" : "#d0d7de"}`, display: "block" }} />
      {cropMode && <CropTool imgSrc={src} pageNum={pageNum} onClose={() => setCropMode(false)} />}
    </div>
  );
}

function TableView({ table, dark }) {
  const border = dark ? "#30363d" : "#d0d7de";
  const copyTable = () => {
    const rows = [table.headers, ...table.rows];
    navigator.clipboard.writeText(rows.map(r => r.join("\t")).join("\n"));
  };
  const downloadCSV = () => {
    const rows = [table.headers, ...table.rows];
    const csv = rows.map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const a = document.createElement("a"); a.href = `data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`; a.download = "table.csv"; a.click();
  };
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
        <CopyBtn label="📋 Copy Table" onClick={copyTable} color="#d29922" />
        <button onClick={downloadCSV} style={{ background: "transparent", border: `1px solid ${border}`, color: "#8b949e", padding: "4px 10px", borderRadius: 6, cursor: "pointer", fontSize: 11, fontFamily: "inherit" }}>⬇ CSV</button>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>{table.headers.map((h, i) => <th key={i} style={{ padding: "7px 10px", background: dark ? "#21262d" : "#f6f8fa", border: `1px solid ${border}`, color: dark ? "#e6edf3" : "#1f2328", fontWeight: 600, textAlign: "left" }}>{h || "—"}</th>)}</tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => (
              <tr key={ri}>{row.map((cell, ci) => <td key={ci} style={{ padding: "5px 10px", border: `1px solid ${border}`, color: dark ? "#8b949e" : "#636c76", fontSize: 12 }}>{cell || "—"}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProgressBar({ current, total, stage, eta, dark }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  const etaStr = eta > 60 ? `~${Math.ceil(eta / 60)} min` : eta > 0 ? `~${eta}s` : "";
  const stageLabel = { rendering: "Rendering", done_page: "Processing", starting: "Starting…", complete: "Complete", ocr: "OCR" }[stage] || stage;
  return (
    <div style={{ background: dark ? "#161b22" : "#f6f8fa", border: `1px solid ${dark ? "#30363d" : "#d0d7de"}`, borderRadius: 12, padding: "16px 20px", marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: dark ? "#e6edf3" : "#1f2328" }}>
          {stageLabel} — Page {current} of {total}
        </span>
        <span style={{ fontSize: 12, color: dark ? "#8b949e" : "#636c76" }}>{etaStr}</span>
      </div>
      <div style={{ height: 6, background: dark ? "#30363d" : "#d0d7de", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: "linear-gradient(90deg,#1f6feb,#8250df)", borderRadius: 4, transition: "width 0.5s ease" }} />
      </div>
      <p style={{ margin: "6px 0 0", fontSize: 11, color: dark ? "#8b949e" : "#636c76" }}>{pct}% complete — please wait, do not refresh</p>
    </div>
  );
}

export default function DocumentViewer() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { dark } = useTheme();

  const [info, setInfo]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");
  const [tab, setTab]             = useState("pdf");
  const [reconStatus, setReconStatus] = useState(null);
  const [summary, setSummary]     = useState(null);
  const [pageData, setPageData]   = useState(null);
  const [currentPg, setCurrentPg] = useState(1);
  const [pgLoading, setPgLoading] = useState(false);

  // ── KEY FIX: use refs instead of state for timer + initial-load flag ──────────
  const pollTimerRef     = useRef(null);   // avoids stale closure resetting page
  const hasLoadedInitial = useRef(false);  // prevents loadPage(1) firing on nav
  // ─────────────────────────────────────────────────────────────────────────────

  const pdfUrl = docsAPI.getViewUrl(id);

  // ChatGPT-style neutral palette
  const t = dark
    ? { bg: "#212121", card: "#2f2f2f", border: "#3f3f3f", text: "#ececec", sub: "#8e8ea0", input: "#2f2f2f" }
    : { bg: "#f9f9f9", card: "#ffffff", border: "#e5e5e5", text: "#0d0d0d", sub: "#6b6b6b", input: "#ffffff" };

  useEffect(() => {
    docsAPI.info(id)
      .then(r => { setInfo(r.data); setLoading(false); })
      .catch(() => { setError("Document not found."); setLoading(false); });
    return () => {
      // Cleanup timer on unmount
      if (pollTimerRef.current) { clearInterval(pollTimerRef.current); pollTimerRef.current = null; }
    };
  }, [id]);

  // loadPage — loads page N data from backend, no interference with polling
  const loadPage = useCallback(async (n) => {
    setPgLoading(true);
    try {
      const data = await apiFetch(`/recon/${id}/page/${n}`);
      setPageData(data);
      setCurrentPg(n);   // update current page AFTER data is set
    } catch (e) {
      console.error("loadPage error:", e);
    }
    setPgLoading(false);
  }, [id]);

  // pollStatus — checks reconstruction progress, stops when done
  const pollStatus = useCallback(() => {
    apiFetch(`/recon/${id}/status`).then(s => {
      setReconStatus(s);
      if (s.status === "done") {
        // Stop polling
        if (pollTimerRef.current) { clearInterval(pollTimerRef.current); pollTimerRef.current = null; }
        apiFetch(`/recon/${id}/summary`).then(sm => {
          setSummary(sm);
          // Only load page 1 ONCE — not on every poll tick
          if (!hasLoadedInitial.current) {
            hasLoadedInitial.current = true;
            loadPage(1);
          }
        });
      }
      if (s.status === "error") {
        if (pollTimerRef.current) { clearInterval(pollTimerRef.current); pollTimerRef.current = null; }
      }
    });
  }, [id, loadPage]);

  const startReconstruction = useCallback(async () => {
    const s = await apiFetch(`/recon/${id}/status`);
    setReconStatus(s);

    if (s.status === "done") {
      const sm = await apiFetch(`/recon/${id}/summary`);
      setSummary(sm);
      if (!hasLoadedInitial.current) {
        hasLoadedInitial.current = true;
        loadPage(1);
      }
      return;
    }

    // Start the job
    await apiFetch(`/recon/${id}/start`, { method: "POST" });
    // Start polling using ref (not state) to avoid re-renders breaking the interval
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    pollTimerRef.current = setInterval(pollStatus, 2000);
    pollStatus(); // fire immediately
  }, [id, pollStatus, loadPage]);

  const handleTabRecon = () => {
    setTab("recon");
    if (!reconStatus) startReconstruction();
  };

  // Page navigation — direct, no interference
  const goToPage = useCallback((n) => {
    if (pgLoading) return;
    loadPage(n);
  }, [pgLoading, loadPage]);

  const totalPages = summary?.total_pages || 0;
  const isDone    = reconStatus?.status === "done";
  const isRunning = reconStatus?.status === "running";

  if (loading) return (
    <div style={{ minHeight: "100vh", background: t.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: t.sub, fontFamily: "Inter,sans-serif" }}>Loading…</p>
    </div>
  );
  if (error) return (
    <div style={{ minHeight: "100vh", background: t.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16 }}>
      <p style={{ color: "#f85149", fontFamily: "Inter,sans-serif" }}>🚫 {error}</p>
      <button onClick={() => navigate("/documents")} style={{ background: "#1f6feb", color: "#fff", border: "none", padding: "9px 20px", borderRadius: 8, cursor: "pointer", fontFamily: "Inter,sans-serif" }}>← Back</button>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 60px)", background: t.bg, fontFamily: "Inter,sans-serif" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'); .pg-btn:hover{background:rgba(31,111,235,0.1)!important} .pg-btn-active{background:rgba(31,111,235,0.15)!important;border-color:rgba(31,111,235,0.4)!important}`}</style>

      {/* ── Top bar ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 16px", background: t.card, borderBottom: `1px solid ${t.border}`, flexShrink: 0, flexWrap: "wrap" }}>
        <button onClick={() => navigate("/documents")} style={{ background: "transparent", border: `1px solid ${t.border}`, color: t.sub, padding: "6px 12px", borderRadius: 7, cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>← Back</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: t.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>📄 {info?.original_name}</p>
          <p style={{ margin: 0, fontSize: 11, color: t.sub }}>{info?.file_size} · {info?.status}</p>
        </div>
        {[
          { key: "pdf",   label: "📄 PDF View" },
          { key: "recon", label: "🔬 Exact Reconstruction" },
        ].map(tb => (
          <button key={tb.key}
            onClick={tb.key === "recon" ? handleTabRecon : () => setTab("pdf")}
            style={{
          background: tab === tb.key ? (dark ? "#3f3f3f" : "#171717") : "transparent",
          color: tab === tb.key ? "#fff" : t.sub,
          border: `1px solid ${tab === tb.key ? "transparent" : t.border}`,
          padding: "6px 14px", borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: tab === tb.key ? 600 : 400, fontFamily: "inherit", transition: "all 0.15s" }}>
            {tb.label}
          </button>
        ))}
        <a href={pdfUrl} download={info?.original_name} style={{ background: "transparent", border: `1px solid ${t.border}`, color: t.sub, padding: "6px 12px", borderRadius: 7, cursor: "pointer", fontSize: 12, textDecoration: "none" }}>⬇ Download</a>
      </div>

      {/* ── PDF View ── */}
      {tab === "pdf" && <iframe src={pdfUrl} title={info?.original_name} style={{ flex: 1, border: "none", background: "#525659" }} />}

      {/* ── Reconstruction View ── */}
      {tab === "recon" && (
        <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>

          {/* Page list sidebar — only when done */}
          {isDone && summary && (
            <div style={{ width: 120, flexShrink: 0, background: t.card, borderRight: `1px solid ${t.border}`, overflowY: "auto", padding: "8px 6px" }}>
              <p style={{ margin: "0 0 8px 2px", fontSize: 10, fontWeight: 700, color: t.sub, textTransform: "uppercase", letterSpacing: "0.5px" }}>Pages</p>
              {summary.pages.map(pg => {
                const isActive = currentPg === pg.page;
                return (
                  <button key={pg.page}
                    className={`pg-btn${isActive ? " pg-btn-active" : ""}`}
                    onClick={() => goToPage(pg.page)}
                    disabled={pgLoading}
                    style={{
                      width: "100%", display: "flex", flexDirection: "column", alignItems: "flex-start",
                      gap: 3, background: isActive ? "rgba(31,111,235,0.15)" : "transparent",
                      border: `1px solid ${isActive ? "rgba(31,111,235,0.4)" : "transparent"}`,
                      borderRadius: 7, padding: "8px 6px", cursor: pgLoading ? "not-allowed" : "pointer",
                      marginBottom: 3, textAlign: "left", fontFamily: "inherit", opacity: pgLoading && !isActive ? 0.5 : 1,
                    }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: isActive ? "#1f6feb" : t.text }}>Pg {pg.page}</span>
                    <span style={{ fontSize: 9, color: CONF_COLOR[pg.confidence] || t.sub, fontWeight: 700 }}>{(pg.confidence || "?").toUpperCase()}</span>
                    <span style={{ fontSize: 9, color: t.sub }}>{pg.type === "scanned" ? "OCR" : "Digital"}{pg.has_tables ? " · 📊" : ""}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Main panel */}
          <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>

            {/* Not started */}
            {!reconStatus && (
              <div style={{ textAlign: "center", paddingTop: 60 }}>
                <div style={{ fontSize: 52, marginBottom: 16 }}>🔬</div>
                <p style={{ color: t.text, fontWeight: 700, fontSize: 17, marginBottom: 8 }}>Exact Reconstruction</p>
                <p style={{ color: t.sub, fontSize: 13, maxWidth: 420, margin: "0 auto 24px" }}>
                  Extracts every page as image + OCR text + tables. Works on scanned PDFs, handwritten notes, exam papers.
                </p>
                <button onClick={startReconstruction}
                  style={{ background: dark ? "#3f3f3f" : "#171717", color: "#fff", border: "none", padding: "12px 30px", borderRadius: 10, cursor: "pointer", fontSize: 14, fontWeight: 600, fontFamily: "inherit" }}>
                  Start Reconstruction
                </button>
              </div>
            )}

            {/* Running */}
            {isRunning && reconStatus && (
              <ProgressBar current={reconStatus.current_page} total={reconStatus.total_pages} stage={reconStatus.stage} eta={reconStatus.eta_seconds} dark={dark} />
            )}

            {/* Error */}
            {reconStatus?.status === "error" && (
              <div style={{ background: "rgba(248,81,73,0.1)", border: "1px solid rgba(248,81,73,0.3)", borderRadius: 10, padding: 16, color: "#f85149" }}>
                ❌ Reconstruction failed: {reconStatus.error || "Unknown error"}. <button onClick={startReconstruction} style={{ background: "none", border: "none", color: "#1f6feb", cursor: "pointer", textDecoration: "underline", fontFamily: "inherit", fontSize: 13 }}>Try again</button>
              </div>
            )}

            {/* Done — page content */}
            {isDone && pageData && (
              <div style={{ maxWidth: 860, margin: "0 auto" }}>

                {/* Page header + navigation */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
                  <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: t.text }}>Page {pageData.page}</h2>
                  <Badge label={`${(pageData.confidence || "?").toUpperCase()} CONF`} color={CONF_COLOR[pageData.confidence] || "#8b949e"} bg={CONF_BG[pageData.confidence] || "rgba(139,148,158,0.12)"} />
                  <Badge label={pageData.type === "scanned" ? "🔍 OCR" : "📝 Digital"} color={pageData.type === "scanned" ? "#d29922" : "#3fb950"} bg={pageData.type === "scanned" ? "rgba(210,153,34,0.12)" : "rgba(63,185,80,0.12)"} />
                  {pageData.has_tables && <Badge label="📊 Table" color="#8250df" bg="rgba(130,80,223,0.12)" />}

                  {/* ── Navigation buttons — fixed, direct, no state interference ── */}
                  <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
                    <button
                      onClick={() => goToPage(currentPg - 1)}
                      disabled={currentPg <= 1 || pgLoading}
                      style={{ background: "transparent", border: `1px solid ${t.border}`, color: t.sub, padding: "5px 12px", borderRadius: 6, cursor: currentPg > 1 && !pgLoading ? "pointer" : "not-allowed", fontSize: 12, fontFamily: "inherit", opacity: currentPg <= 1 || pgLoading ? 0.4 : 1 }}>
                      ← Prev
                    </button>
                    <span style={{ fontSize: 12, color: t.sub, padding: "4px 8px", fontWeight: 600 }}>
                      {pgLoading ? "Loading…" : `${currentPg} / ${totalPages}`}
                    </span>
                    <button
                      onClick={() => goToPage(currentPg + 1)}
                      disabled={currentPg >= totalPages || pgLoading}
                      style={{ background: currentPg < totalPages && !pgLoading ? (dark ? "#3f3f3f" : "#171717") : "transparent", color: currentPg < totalPages && !pgLoading ? "#fff" : t.sub, border: `1px solid ${currentPg < totalPages && !pgLoading ? "transparent" : t.border}`, padding: "5px 12px", borderRadius: 6, cursor: currentPg < totalPages && !pgLoading ? "pointer" : "not-allowed", fontSize: 12, fontFamily: "inherit", opacity: currentPg >= totalPages || pgLoading ? 0.4 : 1, fontWeight: 600 }}>
                      Next →
                    </button>
                  </div>
                </div>

                {pgLoading && (
                  <div style={{ textAlign: "center", padding: "40px 0", color: t.sub }}>
                    <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
                    Loading page {currentPg}…
                  </div>
                )}

                {!pgLoading && (
                  <>
                    {/* Page Image */}
                    {pageData.has_image && pageData.image_b64 && (
                      <div style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: 12, padding: 16, marginBottom: 16 }}>
                        <p style={{ margin: "0 0 10px", fontSize: 11, fontWeight: 700, color: t.sub, textTransform: "uppercase", letterSpacing: "0.5px" }}>📸 Page Image</p>
                        <PageImage src={`data:image/png;base64,${pageData.image_b64}`} pageNum={pageData.page} dark={dark} />
                      </div>
                    )}

                    {/* Text */}
                    {pageData.has_text && (
                      <div style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: 12, padding: 16, marginBottom: 16 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
                          <p style={{ margin: 0, fontSize: 11, fontWeight: 700, color: t.sub, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                            {pageData.ocr_used ? "🔍 OCR Text" : "📝 Extracted Text"}
                          </p>
                          <CopyBtn label="📋 Copy Text" onClick={() => navigator.clipboard.writeText(pageData.text)} color="#1f6feb" />
                          {pageData.ocr_used && <Badge label="OCR" color="#d29922" bg="rgba(210,153,34,0.12)" />}
                        </div>
                        <pre style={{ margin: 0, fontSize: 13, color: t.text, lineHeight: 1.75, whiteSpace: "pre-wrap", wordBreak: "break-word", background: dark ? "#0d1117" : "#f6f8fa", borderRadius: 8, padding: 12, maxHeight: 380, overflowY: "auto" }}>
                          {pageData.text}
                        </pre>
                      </div>
                    )}

                    {!pageData.has_text && (
                      <div style={{ background: "rgba(248,81,73,0.06)", border: "1px solid rgba(248,81,73,0.2)", borderRadius: 10, padding: 12, marginBottom: 16, fontSize: 13, color: "#f85149" }}>
                        ⚠️ No text extracted from this page. Use the page image above — it is the most faithful copy.
                      </div>
                    )}

                    {/* Tables */}
                    {pageData.has_tables && pageData.tables?.length > 0 && (
                      <div style={{ background: t.card, border: `1px solid ${t.border}`, borderRadius: 12, padding: 16, marginBottom: 16 }}>
                        <p style={{ margin: "0 0 12px", fontSize: 11, fontWeight: 700, color: t.sub, textTransform: "uppercase", letterSpacing: "0.5px" }}>📊 Tables ({pageData.tables.length})</p>
                        {pageData.tables.map((tbl, i) => <TableView key={i} table={tbl} dark={dark} />)}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
