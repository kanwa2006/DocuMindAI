"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "react-hot-toast";
import { apiFetch } from "../../lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ExtractedTable {
  table_index: number;
  page: number | null;
  rows: string[][];
  has_header: boolean;
  caption: string | null;
  merged_cells: unknown[];
}

interface Props {
  documentId: string | null;
  documentName?: string;
  onClose: () => void;
}

// ── Chip style helpers ────────────────────────────────────────────────────────

const btnChip: React.CSSProperties = {
  height: "28px",
  padding: "0 10px",
  fontSize: "12px",
  background: "var(--surface-raised)",
  border: "1px solid var(--border-default)",
  borderRadius: "6px",
  cursor: "pointer",
  color: "var(--text-secondary)",
  display: "inline-flex",
  alignItems: "center",
  gap: "4px",
  fontFamily: "var(--font-body)",
  transition: "border-color 100ms, color 100ms",
  whiteSpace: "nowrap",
};

function hoverIn(e: React.MouseEvent) {
  const el = e.currentTarget as HTMLElement;
  el.style.borderColor = "var(--brand)";
  el.style.color = "var(--brand)";
}
function hoverOut(e: React.MouseEvent) {
  const el = e.currentTarget as HTMLElement;
  el.style.borderColor = "var(--border-default)";
  el.style.color = "var(--text-secondary)";
}

// ── Sub-component: single table view ─────────────────────────────────────────

function TableView({ table }: { table: ExtractedTable }) {
  const [editMode, setEditMode] = useState(false);
  const [editedRows, setEditedRows] = useState<string[][]>(() =>
    table.rows.map((row) => [...row])
  );
  const [htmlCopied, setHtmlCopied] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);

  const updateCell = useCallback((rowIdx: number, colIdx: number, value: string) => {
    setEditedRows((prev) => {
      const next = prev.map((r) => [...r]);
      if (next[rowIdx]) next[rowIdx][colIdx] = value;
      return next;
    });
  }, []);

  const resetEdits = useCallback(() => {
    setEditedRows(table.rows.map((row) => [...row]));
    setEditMode(false);
  }, [table.rows]);

  const activeRows = editMode ? editedRows : table.rows;

  // ── Current table dict (may have edited rows) ─────────────────────────────
  const buildTableDict = () => ({
    ...table,
    rows: activeRows,
  });

  // ── Copy as HTML ──────────────────────────────────────────────────────────
  const copyAsHtml = async () => {
    try {
      const res = await apiFetch("/exams/export/table", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ table: buildTableDict(), format: "html" }),
      });
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      await navigator.clipboard.writeText(data.html);
      setHtmlCopied(true);
      setTimeout(() => setHtmlCopied(false), 2000);
      toast.success("Table copied! Paste into Google Docs or Word.");
    } catch {
      toast.error("Could not copy HTML");
    }
  };

  // ── Export CSV ────────────────────────────────────────────────────────────
  const exportCSV = () => {
    const rows = activeRows;
    const csvLines = rows.map((row) =>
      row
        .map((cell) => {
          const escaped = String(cell ?? "").replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(",")
    );
    const csv = csvLines.join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `table_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // ── Export DOCX ───────────────────────────────────────────────────────────
  const exportDOCX = async () => {
    if (docxLoading) return;
    setDocxLoading(true);
    try {
      const res = await apiFetch("/exams/export/table", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ table: buildTableDict(), format: "docx" }),
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `table_${Date.now()}.docx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("DOCX export failed");
    } finally {
      setDocxLoading(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div
      style={{
        border: "1px solid var(--border-default)",
        borderRadius: "10px",
        overflow: "hidden",
        background: "var(--surface-base)",
      }}
    >
      {/* Table preview */}
      <div style={{ overflowX: "auto", padding: "12px" }}>
        <table
          style={{
            borderCollapse: "collapse",
            fontSize: "13px",
            minWidth: "100%",
          }}
        >
          <tbody>
            {activeRows.map((row, rowIdx) => {
              const isHeader = rowIdx === 0 && table.has_header;
              return (
                <tr
                  key={rowIdx}
                  style={{
                    background:
                      rowIdx % 2 === 0
                        ? "var(--surface-base)"
                        : "var(--surface-sunken, var(--surface-raised))",
                  }}
                >
                  {row.map((cell, colIdx) => {
                    const Tag = isHeader ? "th" : "td";
                    return (
                      <Tag
                        key={colIdx}
                        contentEditable={editMode}
                        suppressContentEditableWarning
                        onBlur={(e) =>
                          updateCell(
                            rowIdx,
                            colIdx,
                            (e.currentTarget as HTMLElement).textContent ?? ""
                          )
                        }
                        style={{
                          padding: "8px 12px",
                          border: "1px solid var(--border-subtle, #e5e7eb)",
                          fontWeight: isHeader ? 600 : 400,
                          background: isHeader
                            ? "color-mix(in srgb, var(--brand) 10%, transparent)"
                            : "transparent",
                          fontFamily: /^\d+([.,]\d+)?$/.test(cell.trim())
                            ? "var(--font-mono)"
                            : "var(--font-body)",
                          textAlign: "left",
                          outline: editMode ? "none" : undefined,
                        }}
                      >
                        {cell}
                      </Tag>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Caption */}
      {table.caption && (
        <div
          style={{
            padding: "0 12px 8px",
            fontStyle: "italic",
            fontSize: "12px",
            color: "var(--text-secondary)",
          }}
        >
          {table.caption}
        </div>
      )}

      {/* Source page chip */}
      {table.page != null && (
        <div style={{ padding: "0 12px 8px" }}>
          <span
            style={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "999px",
              padding: "2px 8px",
              fontSize: "11px",
              color: "var(--text-tertiary)",
              fontFamily: "var(--font-body)",
            }}
          >
            📍 Found on page {table.page}
          </span>
        </div>
      )}

      {/* Action buttons row */}
      <div
        style={{
          display: "flex",
          gap: "6px",
          flexWrap: "wrap",
          padding: "8px 12px 12px",
          borderTop: "1px solid var(--border-subtle)",
          alignItems: "center",
        }}
      >
        {/* 📋 Copy as HTML */}
        <button
          style={btnChip}
          onMouseEnter={hoverIn}
          onMouseLeave={hoverOut}
          onClick={copyAsHtml}
          title="Copy table as HTML — paste directly into Google Docs or Word"
        >
          {htmlCopied ? "✓ Copied!" : "📋 Copy as HTML"}
        </button>

        {/* 📊 Export CSV */}
        <button
          style={btnChip}
          onMouseEnter={hoverIn}
          onMouseLeave={hoverOut}
          onClick={exportCSV}
          title="Download as CSV for Excel"
        >
          📊 Export CSV
        </button>

        {/* 📄 Export DOCX */}
        <button
          style={{
            ...btnChip,
            opacity: docxLoading ? 0.6 : 1,
            cursor: docxLoading ? "not-allowed" : "pointer",
          }}
          onMouseEnter={hoverIn}
          onMouseLeave={hoverOut}
          onClick={exportDOCX}
          disabled={docxLoading}
          title="Download as DOCX with exact table structure"
        >
          📄 {docxLoading ? "Exporting…" : "Export DOCX"}
        </button>

        {/* ✏ Edit Cells / ✓ Save / ✕ Reset */}
        {!editMode ? (
          <button
            style={btnChip}
            onMouseEnter={hoverIn}
            onMouseLeave={hoverOut}
            onClick={() => setEditMode(true)}
            title="Edit cells inline before exporting"
          >
            ✏ Edit Cells
          </button>
        ) : (
          <>
            <button
              style={{
                ...btnChip,
                background: "var(--brand)",
                color: "var(--brand-text)",
                borderColor: "var(--brand)",
              }}
              onClick={() => setEditMode(false)}
              title="Confirm edits"
            >
              ✓ Save Changes
            </button>
            <button
              style={btnChip}
              onMouseEnter={hoverIn}
              onMouseLeave={hoverOut}
              onClick={resetEdits}
              title="Revert to original OCR output"
            >
              ✕ Reset
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function TableExtractionPanel({ documentId, documentName, onClose }: Props) {
  const [tables, setTables] = useState<ExtractedTable[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const [fetched, setFetched] = useState(false);

  // Fetch tables when the panel opens and a document is selected
  useEffect(() => {
    if (!documentId) return;
    setFetched(false);
    setTables([]);
    setActiveIdx(0);
    setLoading(true);

    apiFetch("/exams/extract-tables", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Extraction failed");
        }
        return res.json();
      })
      .then((data) => {
        setTables(data.tables ?? []);
        setFetched(true);
      })
      .catch((err) => {
        toast.error(err.message || "Table extraction failed");
        setFetched(true);
      })
      .finally(() => setLoading(false));
  }, [documentId]);

  const activeTable = tables[activeIdx] ?? null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Table Extraction Panel"
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "520px",
        maxWidth: "95vw",
        height: "100vh",
        background: "var(--surface-base)",
        borderLeft: "1px solid var(--border-default)",
        boxShadow: "-4px 0 24px rgba(0,0,0,0.12)",
        display: "flex",
        flexDirection: "column",
        zIndex: 50,
        overflow: "hidden",
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border-default)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "12px",
          flexShrink: 0,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "16px",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            📊 Tables Found
          </div>
          <div
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "13px",
              color: "var(--text-secondary)",
              marginTop: "2px",
            }}
          >
            {loading
              ? "Scanning document for tables…"
              : fetched
              ? `${tables.length} table${tables.length !== 1 ? "s" : ""} detected`
              : documentId
              ? "Ready to scan"
              : "No document selected"}
            {documentName && (
              <span style={{ color: "var(--text-tertiary)" }}> · {documentName}</span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Close table extraction panel"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--text-secondary)",
            fontSize: "18px",
            padding: "4px",
            lineHeight: 1,
            flexShrink: 0,
          }}
        >
          ×
        </button>
      </div>

      {/* ── Content ── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {/* Processing state */}
        {loading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "12px",
              paddingTop: "60px",
              color: "var(--text-secondary)",
              fontFamily: "var(--font-body)",
              fontSize: "14px",
            }}
          >
            <div
              style={{
                width: "28px",
                height: "28px",
                border: "3px solid var(--border-default)",
                borderTopColor: "var(--brand)",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            Scanning document for tables…
          </div>
        )}

        {/* No document selected */}
        {!loading && !documentId && (
          <div
            style={{
              textAlign: "center",
              paddingTop: "60px",
              color: "var(--text-secondary)",
              fontFamily: "var(--font-body)",
              fontSize: "14px",
            }}
          >
            <div style={{ fontSize: "40px", marginBottom: "12px" }}>📄</div>
            Select a document from the tray to extract tables.
          </div>
        )}

        {/* Empty state */}
        {!loading && fetched && tables.length === 0 && (
          <div
            style={{
              textAlign: "center",
              paddingTop: "60px",
              color: "var(--text-secondary)",
              fontFamily: "var(--font-body)",
            }}
          >
            <div style={{ fontSize: "40px", marginBottom: "12px" }}>⊞?</div>
            <div
              style={{
                fontSize: "15px",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: "8px",
              }}
            >
              No structured tables detected
            </div>
            <div style={{ fontSize: "13px", maxWidth: "320px", margin: "0 auto", lineHeight: 1.6 }}>
              Try uploading a clearer image or a native PDF with embedded tables. If your table is
              in a scanned image, ensure the image is well-lit and horizontal.
            </div>
          </div>
        )}

        {/* Table selector pills (multiple tables) */}
        {!loading && tables.length > 1 && (
          <div
            style={{
              display: "flex",
              gap: "6px",
              overflowX: "auto",
              paddingBottom: "12px",
              marginBottom: "4px",
            }}
          >
            {tables.map((t, i) => (
              <button
                key={i}
                onClick={() => setActiveIdx(i)}
                style={{
                  flexShrink: 0,
                  height: "28px",
                  padding: "0 12px",
                  fontSize: "12px",
                  borderRadius: "999px",
                  border: `1px solid ${i === activeIdx ? "var(--brand)" : "var(--border-default)"}`,
                  background: i === activeIdx ? "var(--brand)" : "var(--surface-raised)",
                  color: i === activeIdx ? "var(--brand-text)" : "var(--text-secondary)",
                  cursor: "pointer",
                  fontFamily: "var(--font-body)",
                  transition: "background 100ms, color 100ms",
                  whiteSpace: "nowrap",
                }}
              >
                Table {i + 1}
                {t.page != null ? ` · p.${t.page}` : ""}
              </button>
            ))}
          </div>
        )}

        {/* Active table */}
        {!loading && activeTable && (
          <TableView key={activeTable.table_index} table={activeTable} />
        )}
      </div>

      {/* Spinner keyframes injected once */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
