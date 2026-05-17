import uuid
import logging
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
from app.core.middleware import CSRFMiddleware

setup_logging()
logger = logging.getLogger(__name__)

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

# Initialize OpenTelemetry and Prometheus Metrics
setup_telemetry(app, is_worker=False)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "DocuMindAI API is running"}
