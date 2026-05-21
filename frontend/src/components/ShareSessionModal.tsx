"use client";

import { useEffect, useRef, useState } from "react";
import { shareSession, unshareSession } from "@/lib/api";
import { useTrialStore } from "@/lib/store/trialStore";

interface ShareSessionModalProps {
  sessionId: string;
  onClose: () => void;
}

const PLAN_CONFIG: Record<string, { permissions: string[]; maxCollaborators: number }> = {
  trial:        { permissions: ["view_only"],                    maxCollaborators: 1  },
  professional: { permissions: ["view_only", "view_and_ask"],   maxCollaborators: 3  },
  enterprise:   { permissions: ["view_only", "view_and_ask"],   maxCollaborators: 25 },
};

export default function ShareSessionModal({ sessionId, onClose }: ShareSessionModalProps) {
  const { plan } = useTrialStore();
  const config = PLAN_CONFIG[plan] ?? PLAN_CONFIG["trial"];

  const [permission, setPermission] = useState<"view_only" | "view_and_ask">(
    config.permissions.includes("view_and_ask") ? "view_and_ask" : "view_only"
  );
  const [shareUrl, setShareUrl] = useState("");
  const [isSharing, setIsSharing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [copyLabel, setCopyLabel] = useState("Copy");
  const [error, setError] = useState("");

  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    const click = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("keydown", handler);
    document.addEventListener("mousedown", click);
    return () => { document.removeEventListener("keydown", handler); document.removeEventListener("mousedown", click); };
  }, [onClose]);

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await shareSession(sessionId, permission);
      setShareUrl(result.share_url);
      setIsSharing(true);
    } catch (err: any) {
      setError(err.message ?? "Failed to generate link");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError("");
    try {
      await unshareSession(sessionId);
      setIsSharing(false);
      setShareUrl("");
    } catch (err: any) {
      setError(err.message ?? "Failed to stop sharing");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopyLabel("Copied!");
      setTimeout(() => setCopyLabel("Copy"), 2000);
    });
  };

  const overlay: React.CSSProperties = {
    position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
    display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
  };

  const modal: React.CSSProperties = {
    background: "var(--surface-overlay)", border: "1px solid var(--border-default)",
    borderRadius: "var(--radius-xl)", boxShadow: "var(--shadow-xl)",
    padding: "24px", width: "420px", maxWidth: "calc(100vw - 32px)",
    fontFamily: "var(--font-body)",
  };

  const label: React.CSSProperties = {
    fontSize: "var(--text-sm)", color: "var(--text-secondary)", marginBottom: "6px", display: "block",
  };

  const radioRow: React.CSSProperties = {
    display: "flex", flexDirection: "column", gap: "8px", marginBottom: "20px",
  };

  const radioItem: React.CSSProperties = {
    display: "flex", alignItems: "flex-start", gap: "10px", cursor: "pointer",
  };

  const btnPrimary: React.CSSProperties = {
    padding: "9px 18px", background: "var(--brand)", color: "#fff",
    border: "none", borderRadius: "var(--radius-md)", cursor: loading ? "not-allowed" : "pointer",
    fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)",
    opacity: loading ? 0.6 : 1,
  };

  const btnDanger: React.CSSProperties = {
    padding: "9px 18px", background: "transparent", color: "#ef4444",
    border: "1px solid #ef4444", borderRadius: "var(--radius-md)",
    cursor: loading ? "not-allowed" : "pointer",
    fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)",
    opacity: loading ? 0.6 : 1,
  };

  return (
    <div style={overlay} role="dialog" aria-modal="true" aria-label="Share session">
      <div ref={modalRef} style={modal}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <h2 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)" }}>
            Share This Session
          </h2>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: "20px", lineHeight: 1 }} aria-label="Close">
            ×
          </button>
        </div>

        {/* Share URL */}
        {shareUrl && (
          <div style={{ marginBottom: "20px" }}>
            <span style={label}>Share link:</span>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                readOnly
                value={shareUrl}
                style={{
                  flex: 1, padding: "8px 10px", fontSize: "var(--text-sm)",
                  background: "var(--surface-raised)", border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)", color: "var(--text-primary)",
                  fontFamily: "var(--font-mono)", minWidth: 0,
                }}
              />
              <button onClick={handleCopy} style={btnPrimary}>{copyLabel}</button>
            </div>
          </div>
        )}

        {/* Permissions */}
        <div>
          <span style={label}>Permissions:</span>
          <div style={radioRow}>
            <label style={{ ...radioItem, opacity: 1 }}>
              <input
                type="radio"
                name="permissions"
                value="view_only"
                checked={permission === "view_only"}
                onChange={() => setPermission("view_only")}
                style={{ marginTop: "2px" }}
              />
              <span>
                <span style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", fontWeight: "var(--weight-medium)" }}>View only</span>
                <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>They can read, not ask</span>
              </span>
            </label>

            <label style={{ ...radioItem, opacity: config.permissions.includes("view_and_ask") ? 1 : 0.4 }}>
              <input
                type="radio"
                name="permissions"
                value="view_and_ask"
                checked={permission === "view_and_ask"}
                onChange={() => setPermission("view_and_ask")}
                disabled={!config.permissions.includes("view_and_ask")}
                style={{ marginTop: "2px" }}
              />
              <span>
                <span style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", fontWeight: "var(--weight-medium)" }}>View and ask</span>
                <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
                  They can ask questions
                  {!config.permissions.includes("view_and_ask") && " — upgrade to unlock"}
                </span>
              </span>
            </label>

            {plan === "enterprise" && (
              <label style={{ ...radioItem, opacity: 0.4 }}>
                <input type="radio" name="permissions" disabled style={{ marginTop: "2px" }} />
                <span>
                  <span style={{ fontSize: "var(--text-sm)", color: "var(--text-primary)", fontWeight: "var(--weight-medium)" }}>Password protected</span>
                  <span style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>Coming soon</span>
                </span>
              </label>
            )}
          </div>
        </div>

        {/* Collaborator limit */}
        <div style={{ marginBottom: "20px", fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}>
          Max collaborators: <strong style={{ color: "var(--text-primary)" }}>{config.maxCollaborators}</strong>
          {plan === "trial" && " — upgrade for more"}
        </div>

        {/* Error */}
        {error && (
          <div style={{ marginBottom: "12px", padding: "8px 12px", background: "var(--error-bg, #fee2e2)", color: "#dc2626", borderRadius: "var(--radius-md)", fontSize: "var(--text-sm)" }}>
            {error}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={handleGenerate} disabled={loading} style={btnPrimary}>
            {loading && !isSharing ? "Generating…" : "Generate Share Link"}
          </button>
          {isSharing && (
            <button onClick={handleStop} disabled={loading} style={btnDanger}>
              {loading ? "Stopping…" : "Stop Sharing"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
