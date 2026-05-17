from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# FIX 0.5: Paths that must never be blocked by CSRF check.
# Login/register require POST but the user has no CSRF token yet.
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
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
