import os
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.org import User
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.core.auth import get_current_user

logger = logging.getLogger("audit.auth")
router = APIRouter()

# FIX 0.4: Environment-aware secure flag — False on localhost HTTP, True in production
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates user and returns HTTP-Only cookie.
    secure=False in dev (HTTP localhost), secure=True in production (HTTPS).
    """
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    workspace_id = str(user.workspace_id) if user.workspace_id else "general"
    roles = [r.role for r in (user.roles or [])]

    access_token = create_access_token(
        subject=user.email,
        user_id=str(user.id),
        workspace_id=workspace_id,
        roles=roles
    )

    refresh_token = create_access_token(
        subject=user.email,
        user_id=str(user.id),
        workspace_id=workspace_id,
        roles=roles
    )

    # FIX 0.4: Use IS_PRODUCTION so cookies are accepted on HTTP localhost
    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=15 * 60,
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth/refresh"
    )

    return {"message": "Successfully logged in. Session secured."}


@router.post("/refresh")
async def refresh_session(request: Request, response: Response):
    """Silently rotates the access token if the user has a valid refresh cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token found")

    from app.core.auth import AuthProvider
    try:
        user = AuthProvider.verify_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(
        subject=user["email"],
        user_id=user["id"],
        workspace_id=user["workspace_id"],
        roles=user["roles"]
    )

    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=15 * 60,
        path="/"
    )

    return {"success": True, "message": "Session refreshed."}


@router.post("/logout")
async def logout(response: Response):
    """Invalidates the session by clearing the cookie."""
    response.delete_cookie(
        key="token",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        path="/"
    )
    return {"message": "Successfully logged out."}


# ── Admin Impersonation (9-C5) ────────────────────────────────────────────────

class ImpersonateRequest(BaseModel):
    reason: str


def _require_super_admin(current_user: dict) -> dict:
    roles = current_user.get("roles", [])
    if "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    return current_user


@router.post("/admin/impersonate/{user_id}")
async def impersonate_user(
    user_id: str,
    body: ImpersonateRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Issue a 1-hour impersonation token for the target user.
    Super-admin only. Reason is mandatory. Fully audit-logged.
    Impersonated queries are tagged with impersonated_by in all logs.
    CRITICAL: Token cannot access other organizations.
    """
    _require_super_admin(current_user)

    if not body.reason or not body.reason.strip():
        raise HTTPException(status_code=422, detail="reason is required and must be non-empty")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    logger.warning(
        "[AUDIT] event=admin_impersonation_start admin_id=%s target_user_id=%s reason=%s ts=%s",
        current_user["id"],
        user_id,
        body.reason.strip(),
        datetime.utcnow().isoformat(),
    )

    workspace_id = str(target_user.workspace_id) if target_user.workspace_id else "general"
    target_roles = [r.role for r in (target_user.roles or [])]

    import jwt
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "exp": expire,
        "sub": str(target_user.id),
        "email": target_user.email,
        "workspace_id": workspace_id,
        "roles": target_roles,
        "impersonated_by": current_user["id"],
    }
    token = jwt.encode(payload, settings.AUTH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=3600,
        path="/",
    )

    return {
        "message": f"Impersonating {target_user.email}. Session expires in 1 hour.",
        "impersonated_user_id": str(target_user.id),
        "expires_at": expire.isoformat(),
    }


@router.post("/admin/impersonation/end")
async def end_impersonation(
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Explicitly end impersonation session and write audit log entry."""
    impersonated_by = current_user.get("impersonated_by")
    logger.warning(
        "[AUDIT] event=admin_impersonation_end admin_id=%s target_user_id=%s ts=%s",
        impersonated_by or "unknown",
        current_user["id"],
        datetime.utcnow().isoformat(),
    )
    response.delete_cookie(key="token", httponly=True, secure=IS_PRODUCTION, samesite="strict", path="/")
    return {"message": "Impersonation ended. Please log in again."}
