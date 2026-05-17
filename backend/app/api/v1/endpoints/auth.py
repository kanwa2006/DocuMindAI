import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.org import User
from app.core.security import verify_password, create_access_token
from app.core.config import settings

logger = logging.getLogger(__name__)
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
