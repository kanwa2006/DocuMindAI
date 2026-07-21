from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import ClassVar, Optional, List, Dict, Any
import os

# H-9: hosts that never get forced SSL (local dev, docker-compose services).
# Shared policy with alembic/env.py (H-8).
LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "pgbouncer", "postgres"}


def _is_local_db_host(url: str) -> bool:
    from urllib.parse import urlsplit
    try:
        return (urlsplit(url).hostname or "").lower() in LOCAL_DB_HOSTS
    except ValueError:
        return False


class Settings(BaseSettings):
    ENVIRONMENT: str = "development" # local, development, production
    PROJECT_NAME: str = "DocuMindAI"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Security
    AUTH_SECRET_KEY: str
    CSRF_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Frontend
    FRONTEND_URL: str

    # Database
    POSTGRES_SERVER: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    # Redis / Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Storage
    STORAGE_PROVIDER: str = "local"
    STORAGE_PATH: str = "./storage"

    S3_BUCKET: Optional[str] = None
    S3_REGION: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # OCR / Extraction
    CHUNK_SIZE: int = 1800
    CHUNK_OVERLAP: int = 300
    OCR_CONFIDENCE_THRESHOLD: float = 0.80
    # C-3: route scanned/image pages through the PaddleOCR/Docling
    # orchestrator during ingestion. Rollback toggle for the heavy engines —
    # disabling falls back to raw PyMuPDF text (loudly logged, usually empty).
    OCR_SCANNED_ENABLED: bool = True
    MAX_UPLOAD_MB: int = 200

    # Gemini / LLM
    # Phase 12: keys are now sourced via GEMINI_API_KEY_1, _2, _3, ... by GeminiKeyRotator.
    # GEMINI_API_KEYS (comma-separated) is kept for legacy single-key backward compatibility only.
    GEMINI_API_KEYS: Optional[str] = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_FALLBACK_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_TOP_P: float = 0.8
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_CONTINUATION_ROUNDS: int = 2
    TOP_K_RESULTS: int = 20

    # Vector Backend
    # H-1: pgvector is the default — the "faiss" option never used FAISS (it
    # is an in-memory NumPy scan, dev-only fallback; O(N) per query).
    VECTOR_BACKEND: str = "pgvector"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # 9-C3: Tenant vector namespace isolation
    # "user" — each user gets docuMind_{user_id}
    # "organization" — each org gets docuMind_org_{org_id}
    VECTOR_ISOLATION_MODE: str = "user"
    ENABLE_ORG_ISOLATION: bool = False

    # 9-B: Cost guard — per-workspace daily token budgets
    TOKEN_LIMIT_GENERAL: int = 50000
    TOKEN_LIMIT_LEGAL: int = 80000
    TOKEN_LIMIT_FINANCE: int = 80000
    TOKEN_LIMIT_HR: int = 60000
    TOKEN_LIMIT_TEACHER: int = 40000
    TOKEN_LIMIT_STUDENT: int = 40000
    TOKEN_LIMIT_RESEARCH: int = 60000
    SLOW_QUERY_THRESHOLD_MS: int = 8000
    MAX_CHUNKS_PER_QUERY: int = 12
    LARGE_DOC_PAGE_THRESHOLD: int = 200
    TOKEN_COST_PER_MTK: float = 3.0  # estimated cost per 1M tokens (display only)

    # 9-F: Report generation
    DEPLOY_EVAL_SECRET: Optional[str] = None
    EVAL_SLACK_WEBHOOK_URL: Optional[str] = None

    # Twilio — phone OTP
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Email / SMTP
    # Primary: SendGrid (Student Pack) — set SMTP_HOST=smtp.sendgrid.net, SMTP_USER=apikey
    # Fallback: Brevo — set BREVO_SMTP_* vars below
    # Both are optional; OTP emails are skipped gracefully when unconfigured.
    SMTP_HOST: str = "smtp.sendgrid.net"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey"   # SendGrid always uses literal "apikey" as user
    SMTP_PASSWORD: str = ""     # Set to SG.xxx SendGrid API key
    EMAIL_FROM: str = ""

    # Brevo SMTP — fallback transactional email provider
    BREVO_SMTP_HOST: str = "smtp-relay.brevo.com"
    BREVO_SMTP_PORT: int = 587
    BREVO_SMTP_USER: str = ""
    BREVO_SMTP_PASSWORD: str = ""
    EMAILS_FROM_NAME: str = "DocuMindAI"
    EMAILS_FROM_ADDRESS: str = "noreply@documindai.com"

    # Phase 20 — Admin alert email for automation scripts
    ADMIN_EMAIL: Optional[str] = None

    # Sentry
    SENTRY_DSN: Optional[str] = None

    # Monitoring — M-7: defaults are OFF (opt-in). config.py said True while
    # .env.example said false; and a stack without an OTLP collector spams
    # span-export errors. Production deployments enable these explicitly.
    OTEL_ENABLED: bool = False
    PROMETHEUS_ENABLED: bool = False
    LOG_LEVEL: str = "INFO"

    # Reranker
    RERANKER_PROVIDER: str = "local"

    # L-11: hard server-side cap on non-streaming LLM calls. A slow upstream
    # otherwise pins a worker thread indefinitely (the client AbortSignal
    # only frees the browser). Streaming keeps client-side cancellation.
    LLM_TIMEOUT_SECONDS: int = 120

    # Workspace-specific retrieval config (Task 4.8)
    # PHASE 2: top_k bumped across the board to give the LLM more coverage of
    # the document. The "answers only cover the first pages" symptom was
    # mostly top_k=5–8 truncating the evidence set on multi-page docs. Each
    # bump stays within the 6000-token grounding budget (chunk ≈ 1800 chars
    # ≈ 450 tokens; top_k=12 = ~5400 tokens).
    WORKSPACE_RETRIEVAL_CONFIG: ClassVar[Dict[str, Any]] = {
        "exam":     {"top_k": 12, "rerank_n": 8,  "chunk_pref": "medium"},
        "hr":       {"top_k": 18, "rerank_n": 12, "chunk_pref": "small"},
        "legal":    {"top_k": 10, "rerank_n": 6,  "chunk_pref": "large"},
        "finance":  {"top_k": 14, "rerank_n": 8,  "chunk_pref": "small"},
        "research": {"top_k": 16, "rerank_n": 10, "chunk_pref": "large"},
        "study":    {"top_k": 12, "rerank_n": 8,  "chunk_pref": "medium"},
        "general":  {"top_k": 12, "rerank_n": 8,  "chunk_pref": "medium"},
    }

    # PHASE 2: grounding token budget. Was 4000 — bumped to fit the higher
    # top_k values above. Still leaves ~2k tokens of headroom under the
    # default 8192 max_output_tokens for the answer itself.
    GROUNDING_TOKEN_BUDGET: int = 6000

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def sync_database_url(self) -> str:
        """
        Build a psycopg2-safe sync DSN. Strips asyncpg driver tag, forces
        +psycopg2, and normalizes any 'ssl' param to 'sslmode' (which psycopg2
        requires — it rejects bare 'ssl' as an invalid connection option).
        Every sync engine and psycopg2.connect() in the codebase MUST use this.
        """
        url = self.DATABASE_URL or (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        # Drop asyncpg driver tag — psycopg2 cannot use it
        url = url.replace("+asyncpg", "")
        # Force explicit psycopg2 driver
        if "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        # Normalize ssl variants → sslmode=require (psycopg2's accepted form)
        url = url.replace("?ssl=true", "?sslmode=require")
        url = url.replace("&ssl=true", "&sslmode=require")
        url = url.replace("?ssl=require", "?sslmode=require")
        url = url.replace("&ssl=require", "&sslmode=require")
        # H-9: only force SSL for non-local hosts (Supabase et al.). The old
        # unconditional append made every sync connection — health checks,
        # Celery workers — fail against non-SSL Postgres, including the
        # project's own docker-compose stack. Same policy as alembic (H-8).
        if "sslmode=" not in url and not _is_local_db_host(url):
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return url

    @property
    def gemini_keys_list(self) -> List[str]:
        if not self.GEMINI_API_KEYS:
            return []
        return [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]

    @model_validator(mode='after')
    def validate_settings(self) -> 'Settings':
        if self.STORAGE_PROVIDER not in ['local', 's3']:
            raise ValueError("STORAGE_PROVIDER must be 'local' or 's3'")
            
        if self.STORAGE_PROVIDER == 's3':
            if not self.S3_BUCKET:
                raise ValueError("S3_BUCKET must be set when STORAGE_PROVIDER is 's3'")
            if not self.AWS_ACCESS_KEY_ID or not self.AWS_SECRET_ACCESS_KEY:
                raise ValueError("AWS credentials must be set when STORAGE_PROVIDER is 's3'")

        if self.VECTOR_BACKEND not in ['faiss', 'qdrant', 'pgvector']:
            raise ValueError("VECTOR_BACKEND must be 'faiss', 'qdrant', or 'pgvector'")

        if not self.REDIS_URL.startswith("redis://") and not self.REDIS_URL.startswith("rediss://"):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
            
        if self.MAX_UPLOAD_MB <= 0 or self.MAX_UPLOAD_MB > 1000:
            raise ValueError("MAX_UPLOAD_MB must be between 1 and 1000")
            
        if self.OCR_CONFIDENCE_THRESHOLD < 0.0 or self.OCR_CONFIDENCE_THRESHOLD > 1.0:
            raise ValueError("OCR_CONFIDENCE_THRESHOLD must be between 0.0 and 1.0")

        return self

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), case_sensitive=True, extra="ignore")

settings = Settings()
