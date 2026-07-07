"use client";

/**
 * Task 6-R1 + 6-X1: Citation export modal.
 * Formats: APA | MLA | IEEE | Chicago | BibTeX | Vancouver
 * Downloads as .txt (all formats) or .bib (BibTeX only).
 */

import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { apiFetch } from "../lib/api";

const FORMATS = [
  { value: "APA",       label: "APA 7th Edition" },
  { value: "MLA",       label: "MLA" },
  { value: "Chicago",   label: "Chicago" },
  { value: "BibTeX",    label: "BibTeX (.bib)" },
  { value: "Vancouver", label: "Vancouver" },
  { value: "IEEE",      label: "IEEE" },
];

interface Props {
  documentIds: string[];
  onClose: () => void;
}

export default function ResearchCitationModal({ documentIds, onClose }: Props) {
  const [selectedFormat, setSelectedFormat] = useState<string>("APA");
  const [loading, setLoading] = useState(false);
  const [citations, setCitations] = useState<string[]>([]);
  const [fetchedFormat, setFetchedFormat] = useState<string>("");

  const fetchCitations = useCallback(async (fmt: string) => {
    if (!documentIds.length) {
      toast.error("No documents available to cite.");
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch("/research/citations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_ids: documentIds, format: fmt }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Citation export failed.");
      }
      const data = await res.json();
      setCitations(data.citations || []);
      setFetchedFormat(fmt);
    } catch (e: any) {
      toast.error(e.message || "Failed to export citations.");
    } finally {
      setLoading(false);
    }
  }, [documentIds]);

  const handleFormatChange = (fmt: string) => {
    setSelectedFormat(fmt);
    setCitations([]);
    setFetchedFormat("");
  };

  const handleExport = () => fetchCitations(selectedFormat);

  const copyAll = () => {
    if (!citations.length) return;
    navigator.clipboard.writeText(citations.join("\n\n"));
    toast.success("Citations copied to clipboard!");
  };

  const downloadFile = () => {
    if (!citations.length) return;
    const isBib = fetchedFormat === "BibTeX";
    const content = citations.join("\n\n");
    const ext = isBib ? "bib" : "txt";
    const mime = isBib ? "application/x-bibtex" : "text/plain";
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `citations_${fetchedFormat.toLowerCase()}_${Date.now()}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const overlayStyle: React.CSSProperties = {
    position: "fixed", inset: 0, zIndex: 100,
    background: "rgba(0,0,0,0.45)",
    display: "flex", alignItems: "center", justifyContent: "center",
    padding: "16px",
  };

  const modalStyle: React.CSSProperties = {
    background: "var(--surface-base)",
    border: "1px solid var(--border-default)",
    borderRadius: "16px",
    boxShadow: "0 24px 64px rgba(0,0,0,0.2)",
    width: "min(560px, 100%)",
    maxHeight: "80vh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  };

  const isBibTex = selectedFormat === "BibTeX";

  return (
    <div style={overlayStyle} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={modalStyle}>
        {/* Header */}
        <div style={{
          padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)",
          display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0,
        }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--text-primary)" }}>
            📚 Export Citations
          </div>
          <button
            onClick={onClose}
            className="btn-icon btn-ghost"
            style={{ width: "32px", height: "32px", fontSize: "18px" }}
          >
            ×
          </button>
        </div>

        {/* Format selector */}
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", flexShrink: 0 }}>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "10px" }}>
            Citation Format
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {FORMATS.map((f) => (
              <button
                key={f.value}
                onClick={() => handleFormatChange(f.value)}
                className="btn btn-secondary btn-sm"
                style={{
                  height: "32px", fontSize: "12px",
                  borderColor: selectedFormat === f.value ? "var(--brand)" : undefined,
                  color: selectedFormat === f.value ? "var(--brand)" : undefined,
                  background: selectedFormat === f.value ? "var(--brand-ghost, rgba(var(--brand-rgb), 0.08))" : undefined,
                  fontWeight: selectedFormat === f.value ? 600 : 400,
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          <button
            onClick={handleExport}
            disabled={loading || !documentIds.length}
            className="btn btn-primary"
            style={{ marginTop: "12px", height: "36px", width: "100%" }}
          >
            {loading ? "Extracting citations…" : `Generate ${selectedFormat} Citations`}
          </button>
        </div>

        {/* Citations list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {!citations.length && !loading && (
            <div style={{
              textAlign: "center", padding: "32px 0",
              color: "var(--text-tertiary)", fontFamily: "var(--font-body)", fontSize: "13px",
            }}>
              {documentIds.length === 0
                ? "Upload documents first to generate citations."
                : "Select a format and click Generate to export citations."}
            </div>
          )}

          {citations.length > 0 && (
            <>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "12px", color: "var(--text-tertiary)", marginBottom: "12px" }}>
                {citations.length} citation{citations.length !== 1 ? "s" : ""} in {fetchedFormat} format
              </div>
              {citations.map((cite, i) => (
                <div key={i} style={{
                  padding: "12px 14px",
                  marginBottom: "8px",
                  background: "var(--surface-raised)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  fontFamily: isBibTex ? "var(--font-mono)" : "var(--font-body)",
                  fontSize: isBibTex ? "11px" : "13px",
                  lineHeight: 1.65,
                  color: "var(--text-primary)",
                  whiteSpace: isBibTex ? "pre" : "normal",
                  overflowX: isBibTex ? "auto" : undefined,
                }}>
                  {cite}
                </div>
              ))}
            </>
          )}
        </div>

        {/* Footer actions */}
        {citations.length > 0 && (
          <div style={{
            padding: "12px 20px",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex", gap: "8px", flexShrink: 0,
          }}>
            <button
              onClick={copyAll}
              className="btn btn-secondary"
              style={{ height: "36px", fontSize: "13px", flex: 1 }}
            >
              📋 Copy All to Clipboard
            </button>
            <button
              onClick={downloadFile}
              className="btn btn-primary"
              style={{ height: "36px", fontSize: "13px", flex: 1 }}
            >
              {isBibTex ? "⬇ Download .bib" : "⬇ Download .txt"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
