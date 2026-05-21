import uuid
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.core.middleware import CSRFMiddleware, TenantContextMiddleware, DeviceFingerprintMiddleware

setup_logging()
logger = logging.getLogger(__name__)

# --- Gemini API key bridge -------------------------------------------------
# The .env convention in this project is `GEMINI_API_KEYS=k1,k2,k3` (plural,
# comma-separated). The stable GeminiKeyRotator in services/llm_key_rotation.py
# reads `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, ... (numbered). Without this
# bridge, pydantic-settings parses the comma form into settings.GEMINI_API_KEYS
# but the rotator finds nothing in os.environ and the system silently falls
# back to DummyLLMProvider. Bridging here keeps the rotator file untouched
# (it's marked STABLE in CLAUDE.md) while still picking up either pattern.
import os as _os
_keys = settings.gemini_keys_list  # parsed from GEMINI_API_KEYS plural form
for _i, _k in enumerate(_keys, start=1):
    _os.environ.setdefault(f"GEMINI_API_KEY_{_i}", _k)

# Also pick up any GEMINI_API_KEY_N values pydantic-settings ignored (they
# live in .env but Settings doesn't list them as fields; they may still need
# to be promoted from the .env file if python-dotenv isn't doing it).
try:
    from dotenv import dotenv_values as _dotenv_values
    for _k_name, _k_val in (_dotenv_values(".env") or {}).items():
        if _k_name and _k_name.startswith("GEMINI_API_KEY_") and _k_val:
            _os.environ.setdefault(_k_name, _k_val)
except ImportError:
    pass

_loaded_keys = [
    _v for _n, _v in _os.environ.items()
    if _n.startswith("GEMINI_API_KEY_") and _v
]
if not _loaded_keys and not _os.environ.get("GEMINI_API_KEY"):
    logger.error("=" * 70)
    logger.error("CRITICAL: No Gemini API keys configured.")
    logger.error("LLM calls will fall back to DummyLLMProvider (mock responses).")
    logger.error("Set GEMINI_API_KEY_1 (and _2, _3, ...) OR GEMINI_API_KEYS=k1,k2,k3 in .env, then restart.")
    logger.error("=" * 70)
else:
    logger.info("[startup] Gemini keys available: %d", len(_loaded_keys) or 1)

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.05,
        profiles_sample_rate=0.01,
        send_default_pii=False,
        before_send=lambda event, hint: (
            {**event, 'request': {
                k: v for k, v in event.get('request', {}).items()
                if k not in ['data', 'body']
            }} if event else None
        ),
    )

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Strict CORS Hardening
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS, # Environment variable
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Observability: Request Correlation ID Middleware
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

app.add_middleware(CorrelationIdMiddleware)

# 3. Security: Secure HTTP Headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff" # Prevent MIME-sniffing
        response.headers["X-Frame-Options"] = "DENY" # Prevent Clickjacking
        response.headers["X-XSS-Protection"] = "1; mode=block" # Legacy XSS protection
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains" # HSTS
        response.headers["Content-Security-Policy"] = f"default-src 'self'; connect-src 'self' {settings.FRONTEND_URL}"
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(DeviceFingerprintMiddleware)

# Initialize OpenTelemetry and Prometheus Metrics
setup_telemetry(app, is_worker=False)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "DocuMindAI API is running"}
