"use client";

import { useEffect, useState } from "react";
import { API_BASE, getCsrfToken } from "@/lib/api";
import { toast } from "react-hot-toast";

interface Tenant {
  id: string;
  name: string;
  plan: string;
  user_count: number;
  document_count: number;
  storage_gb: number;
  isolation_mode: "Namespace" | "Shared";
  is_suspended: boolean;
}

interface BoundaryViolation {
  time: string;
  request_id: string;
  requesting_tenant: string;
  attempted_scope: string;
  blocked_by: string;
}

type ConfirmAction = { type: "rotate"; tenantId: string; tenantName: string } | null;

export default function AdminTenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [violations, setViolations] = useState<BoundaryViolation[]>([]);
  const [loading, setLoading] = useState(true);
  const [violationsOpen, setViolationsOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [tRes, vRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/admin/tenants`, { credentials: "include" }),
          fetch(`${API_BASE}/api/v1/admin/tenants/violations`, { credentials: "include" }),
        ]);
        if (tRes.ok) setTenants(await tRes.json());
        if (vRes.ok) setViolations(await vRes.json());
      } catch {
        toast.error("Failed to load tenant data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleSuspend(tenantId: string) {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/tenants/${tenantId}/suspend`, {
        method: "POST",
        headers: { "X-CSRF-Token": getCsrfToken() },
        credentials: "include",
      });
      if (!res.ok) throw new Error();
      toast.success("Tenant suspended");
      setTenants((prev) =>
        prev.map((t) => (t.id === tenantId ? { ...t, is_suspended: true } : t))
      );
    } catch {
      toast.error("Failed to suspend tenant");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRotateKeys(tenantId: string) {
    setActionLoading(true);
    setConfirmAction(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/admin/tenants/${tenantId}/rotate-keys`, {
        method: "POST",
        headers: { "X-CSRF-Token": getCsrfToken() },
        credentials: "include",
      });
      if (!res.ok) throw new Error();
      toast.success("Key rotation initiated");
    } catch {
      toast.error("Failed to rotate keys");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <main style={{ padding: "40px 48px" }}>
        <p className="text-body-secondary">Loading tenant data…</p>
      </main>
    );
  }

  return (
    <main style={{ padding: "40px 48px" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1
          style={{
            fontFamily: "Instrument Serif, serif",
            fontSize: 28,
            color: "var(--text-primary)",
            marginBottom: 4,
          }}
        >
          Tenant Management
        </h1>
        <p className="text-body-secondary" style={{ fontSize: 14 }}>
          Enterprise workspace isolation controls
        </p>
      </div>

      {/* Tenant Table */}
      <div className="card" style={{ marginBottom: 32, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border-default)" }}>
              {["Organization", "Plan", "Users", "Documents", "Storage (GB)", "Isolation Mode", "Actions"].map(
                (h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 14px",
                      textAlign: "left",
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--text-tertiary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {tenants.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "24px 14px", color: "var(--text-tertiary)", fontSize: 14 }}>
                  No tenants found.
                </td>
              </tr>
            ) : (
              tenants.map((tenant) => (
                <tr
                  key={tenant.id}
                  style={{ borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <td style={{ padding: "12px 14px", fontSize: 14 }}>
                    <span style={{ fontWeight: 600 }}>{tenant.name}</span>
                    {tenant.is_suspended && (
                      <span className="badge badge-error" style={{ marginLeft: 8, fontSize: 11 }}>
                        Suspended
                      </span>
                    )}
                  </td>
                  <td style={{ padding: "12px 14px", fontSize: 14 }}>{tenant.plan}</td>
                  <td style={{ padding: "12px 14px", fontSize: 14 }}>{tenant.user_count}</td>
                  <td style={{ padding: "12px 14px", fontSize: 14 }}>{tenant.document_count}</td>
                  <td style={{ padding: "12px 14px", fontSize: 14 }}>
                    {tenant.storage_gb.toFixed(2)}
                  </td>
                  <td style={{ padding: "12px 14px" }}>
                    <span
                      className={
                        tenant.isolation_mode === "Namespace" ? "badge badge-success" : "badge badge-warning"
                      }
                      style={{ fontSize: 12 }}
                    >
                      {tenant.isolation_mode}
                    </span>
                  </td>
                  <td style={{ padding: "12px 14px" }}>
                    <div style={{ display: "flex", gap: 8 }}>
                      <a
                        href={`/admin/audit-log?tenant_id=${tenant.id}`}
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: 12 }}
                      >
                        View Audit Log
                      </a>
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: 12 }}
                        onClick={() =>
                          setConfirmAction({
                            type: "rotate",
                            tenantId: tenant.id,
                            tenantName: tenant.name,
                          })
                        }
                        disabled={actionLoading}
                      >
                        Rotate Keys
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: 12, color: "var(--error)" }}
                        onClick={() => handleSuspend(tenant.id)}
                        disabled={actionLoading || tenant.is_suspended}
                      >
                        Suspend
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Isolation Validation Log */}
      <div className="card">
        <button
          onClick={() => setViolationsOpen((p) => !p)}
          style={{
            width: "100%",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "16px 20px",
            fontSize: 14,
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
          aria-expanded={violationsOpen}
        >
          <span>Boundary Violations (last 30 days)</span>
          <span>{violationsOpen ? "▲" : "▾"}</span>
        </button>

        {violationsOpen && (
          <div style={{ padding: "0 20px 20px" }}>
            {violations.length === 0 ? (
              <div
                style={{
                  background: "var(--success-bg, #f0fdf4)",
                  border: "1px solid var(--success-border, #86efac)",
                  borderRadius: 8,
                  padding: "12px 16px",
                  fontSize: 14,
                  color: "var(--success-text, #166534)",
                }}
              >
                ✓ No cross-tenant boundary violations detected
              </div>
            ) : (
              <>
                <div
                  style={{
                    background: "var(--error-bg)",
                    border: "1px solid var(--error-border)",
                    borderRadius: 8,
                    padding: "12px 16px",
                    fontSize: 14,
                    color: "var(--error)",
                    marginBottom: 16,
                  }}
                >
                  ⛔ {violations.length} boundary violation{violations.length !== 1 ? "s" : ""} detected — all were
                  blocked before execution.
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-default)" }}>
                      {["Time", "Request ID", "Requesting Tenant", "Attempted Scope", "Blocked By"].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "8px 12px",
                            textAlign: "left",
                            fontWeight: 600,
                            color: "var(--text-tertiary)",
                            fontSize: 11,
                            textTransform: "uppercase",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {violations.map((v, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "8px 12px" }}>{v.time}</td>
                        <td style={{ padding: "8px 12px", fontFamily: "monospace", fontSize: 11 }}>
                          {v.request_id}
                        </td>
                        <td style={{ padding: "8px 12px" }}>{v.requesting_tenant}</td>
                        <td style={{ padding: "8px 12px" }}>{v.attempted_scope}</td>
                        <td style={{ padding: "8px 12px" }}>{v.blocked_by}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}
      </div>

      {/* Rotate Keys Confirmation Modal */}
      {confirmAction?.type === "rotate" && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="rotate-confirm-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,0,0,0.4)",
          }}
        >
          <div className="modal" style={{ width: 420 }}>
            <div className="modal__header">
              <h2 id="rotate-confirm-title" style={{ fontSize: 16, fontWeight: 600 }}>
                Rotate Encryption Keys
              </h2>
            </div>
            <p style={{ fontSize: 14, marginBottom: 8 }}>
              Rotate encryption keys for <strong>{confirmAction.tenantName}</strong>?
            </p>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 20 }}>
              This will re-encrypt stored embeddings. This cannot be undone.
            </p>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                className="btn btn-ghost"
                onClick={() => setConfirmAction(null)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ background: "var(--error)", borderColor: "var(--error)" }}
                onClick={() => handleRotateKeys(confirmAction.tenantId)}
                disabled={actionLoading}
              >
                {actionLoading ? "Rotating…" : "Confirm Rotation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
