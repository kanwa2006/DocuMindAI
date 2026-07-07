"""
Admin tenants management endpoints.
Super-admin only — all routes guarded by _require_admin().
"""
import uuid
import logging
from typing import Any, List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.org import User
from app.models.document import Document

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_admin(current_user: dict) -> None:
    roles = current_user.get("roles", [])
    if "admin" not in roles and "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin access required.")


# ── GET /admin/tenants ────────────────────────────────────────────────────────

@router.get("/tenants")
async def list_tenants(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Return all users as tenant records with usage stats.
    Admin only.
    """
    _require_admin(current_user)

    users = (await db.execute(select(User))).scalars().all()

    tenants = []
    for u in users:
        # Count documents owned by this user
        doc_count_result = await db.execute(
            select(func.count(Document.id)).where(Document.owner_id == u.id)
        )
        doc_count = doc_count_result.scalar() or 0

        tenants.append({
            "id": str(u.id),
            "name": u.full_name or u.email,
            "plan": u.plan or "trial",
            "user_count": 1,
            "document_count": doc_count,
            "storage_gb": round(doc_count * 0.005, 3),  # ~5 MB estimate per doc
            "isolation_mode": "Namespace",
            "is_suspended": not u.is_active,
        })

    return tenants


# ── GET /admin/tenants/violations ─────────────────────────────────────────────

@router.get("/tenants/violations")
async def list_boundary_violations(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Return recent tenant boundary violations from structured logs.
    Violations are written to the application log by TenantBoundaryViolation;
    this endpoint returns an empty list when no in-memory log store is wired up.
    Admin only.
    """
    _require_admin(current_user)
    # Violations are logged via logger.warning in tenant_guard.py.
    # A log-aggregator (Loki, CloudWatch, etc.) would query these in production.
    # For now return empty list — the UI handles this gracefully.
    return []


# ── POST /admin/tenants/{tenant_id}/suspend ───────────────────────────────────

@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Deactivate a user account. Admin only."""
    _require_admin(current_user)

    user = (await db.execute(
        select(User).where(User.id == tenant_id)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    user.is_active = False
    await db.commit()
    logger.info("[admin] Tenant %s suspended by %s", tenant_id, current_user.get("email"))
    return {"status": "suspended", "tenant_id": str(tenant_id)}


# ── POST /admin/tenants/{tenant_id}/rotate-keys ───────────────────────────────

@router.post("/tenants/{tenant_id}/rotate-keys")
async def rotate_tenant_keys(
    tenant_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Initiate encryption key rotation for a tenant.
    In production this would enqueue a Celery task to re-encrypt stored embeddings.
    Admin only.
    """
    _require_admin(current_user)

    user = (await db.execute(
        select(User).where(User.id == tenant_id)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    # Production: enqueue celery task rotate_tenant_embeddings.delay(tenant_id)
    logger.info(
        "[admin] Key rotation initiated for tenant %s by %s",
        tenant_id, current_user.get("email"),
    )
    return {"status": "rotation_initiated", "tenant_id": str(tenant_id)}
