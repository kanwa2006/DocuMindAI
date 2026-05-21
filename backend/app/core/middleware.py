from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

from app.core.config import settings


async def _middleware_get_redis():
    try:
        import aioredis
        return await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    except Exception:
        return None

logger = logging.getLogger(__name__)

# FIX 0.5: Paths that must never be blocked by CSRF check.
# Login/register require POST but the user has no CSRF token yet.
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/send-phone-otp",
    "/api/v1/auth/verify-phone",
    # STEP 7 added password-reset; both are pre-auth so the client cannot have a CSRF cookie yet.
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/csrf/csrf-token",
    "/api/v1/csrf-token",
    "/api/v1/health",
    "/api/v1/health/detailed",
    "/health",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF VALIDATION MIDDLEWARE — Double-Submit Cookie pattern.
    Enforces X-CSRF-Token header matches csrf_token cookie for all mutations.
    Login and other bootstrap endpoints are explicitly exempted.
    """
    async def dispatch(self, request: Request, call_next):
        # Only validate state-changing methods
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:

            # FIX 0.5: Allow bootstrap paths through without CSRF check
            if request.url.path in CSRF_EXEMPT_PATHS:
                return await call_next(request)

            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")

            if not csrf_cookie or not csrf_header:
                logger.warning(
                    f"CSRF blocked: Missing token "
                    f"(Cookie: {bool(csrf_cookie)}, Header: {bool(csrf_header)}) "
                    f"path={request.url.path}"
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed. Missing token."}
                )

            if csrf_cookie != csrf_header:
                logger.warning(f"CSRF blocked: Token mismatch path={request.url.path}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed. Token mismatch."}
                )

        response = await call_next(request)
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    9-C3: Attaches tenant_collection_name to request.state before each request.
    The collection name is derived from VECTOR_ISOLATION_MODE + JWT claims.
    This value CANNOT be overridden by user input.
    Query endpoints MUST read request.state.collection_name for all vector calls.
    """

    async def dispatch(self, request: Request, call_next):
        user_id = "anonymous"
        org_id: str | None = None

        token = request.cookies.get("token")
        if token:
            try:
                import jwt as _jwt
                claims = _jwt.decode(
                    token,
                    settings.AUTH_SECRET_KEY,
                    algorithms=["HS256", "RS256"],
                    options={"verify_signature": True},
                )
                user_id = claims.get("sub", "anonymous")
                org_id = claims.get("organization_id")
            except Exception:
                pass

        if settings.VECTOR_ISOLATION_MODE == "organization" and org_id:
            request.state.collection_name = f"docuMind_org_{org_id}"
        else:
            request.state.collection_name = f"docuMind_{user_id}"

        return await call_next(request)


class DeviceFingerprintMiddleware(BaseHTTPMiddleware):
    """
    Layer 2 abuse prevention: checks X-Device-ID on registration.
    If the device has already been used for a trial, returns 409.
    Persistence after successful registration is handled in the register endpoint.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/v1/auth/register" and request.method == "POST":
            device_id = request.headers.get("X-Device-ID", "").strip()
            if device_id:
                redis = await _middleware_get_redis()
                if redis:
                    try:
                        existing = await redis.get(f"device_trial:{device_id}")
                        if existing:
                            logger.warning(
                                "[abuse] Registration blocked — device fingerprint already used: device_id=REDACTED"
                            )
                            return JSONResponse(
                                status_code=409,
                                content={"detail": "Trial already used on this device"},
                            )
                    finally:
                        await redis.close()
        return await call_next(request)
