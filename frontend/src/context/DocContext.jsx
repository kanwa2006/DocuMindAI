import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const DocContext = createContext(null);

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const authHdr = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

export function DocProvider({ children }) {
  // ── Persistent active doc (survives tab switches) ────────────────────────
  const [activeDocId, _setActiveDocId] = useState(() => {
    const v = localStorage.getItem("activeDocId");
    return v ? parseInt(v, 10) : null;
  });
  const [activeDocName, _setActiveDocName] = useState(
    () => localStorage.getItem("activeDocName") || ""
  );
  const [activeDocStatus, setActiveDocStatus] = useState(
    () => localStorage.getItem("activeDocStatus") || ""
  );

  // ── All user documents (shared across all pages) ─────────────────────────
  const [docs, setDocs] = useState([]);
  const [docsLoaded, setDocsLoaded] = useState(false);

  const setActiveDoc = useCallback((id, name, status = "") => {
    _setActiveDocId(id);
    _setActiveDocName(name || "");
    setActiveDocStatus(status);
    if (id) {
      localStorage.setItem("activeDocId", String(id));
      localStorage.setItem("activeDocName", name || "");
      localStorage.setItem("activeDocStatus", status);
    } else {
      localStorage.removeItem("activeDocId");
      localStorage.removeItem("activeDocName");
      localStorage.removeItem("activeDocStatus");
    }
  }, []);

  const clearActiveDoc = useCallback(() => setActiveDoc(null, "", ""), [setActiveDoc]);

  // ── Refresh documents list (called after any upload) ─────────────────────
  const refreshDocs = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
      const r = await fetch(`${BASE}/documents/list`, { headers: authHdr() });
      if (r.ok) {
        const data = await r.json();
        const list = Array.isArray(data) ? data : [];
        setDocs(list);
        setDocsLoaded(true);
        // Keep active doc status in sync
        if (activeDocId) {
          const found = list.find(d => d.id === activeDocId);
          if (found) {
            localStorage.setItem("activeDocStatus", found.status || "");
            setActiveDocStatus(found.status || "");
          }
        }
        return list;
      }
    } catch { /* silent */ }
    return [];
  }, [activeDocId]);

  // ── Upload a file directly (used by Modes) ───────────────────────────────
  const uploadFile = useCallback(async (file) => {
    const token = localStorage.getItem("token");
    if (!token || !file) throw new Error("Not logged in or no file");
    const form = new FormData();
    form.append("file", file);
    const r = await fetch(`${BASE}/documents/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Upload failed");
    await refreshDocs();
    return data; // { doc_id, filename, reused, status }
  }, [refreshDocs]);

  // ── Auto-refresh on login ─────────────────────────────────────────────────
  useEffect(() => {
    if (localStorage.getItem("token")) refreshDocs();
  }, []); // eslint-disable-line

  return (
    <DocContext.Provider value={{
      activeDocId, activeDocName, activeDocStatus,
      setActiveDoc, clearActiveDoc,
      docs, docsLoaded, refreshDocs, uploadFile,
    }}>
      {children}
    </DocContext.Provider>
  );
}

export function useDoc() {
  const ctx = useContext(DocContext);
  if (!ctx) throw new Error("useDoc must be used inside DocProvider");
  return ctx;
}
