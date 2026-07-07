"""
Per-IP rate limiter shared across endpoints.

slowapi reads the limiter from `app.state.limiter`; FastAPI route handlers
also need to reference the same Limiter instance to apply the @limit
decorators. Define it once here and let both sides import it.

Usage in an endpoint:

    from fastapi import Request
    from app.core.rate_limiter import limiter

    @router.post("/login")
    @limiter.limit("5/minute")
    async def login(request: Request, ...):
        ...

The `request: Request` parameter is required by slowapi to extract the IP.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Default key is the client IP. Endpoints can pass `key_func=...` to override.
limiter = Limiter(key_func=get_remote_address)
