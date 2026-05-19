from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import ClassVar, Optional, List, Dict, Any
import os

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
    MAX_UPLOAD_MB: int = 50

    # Gemini / LLM
    GEMINI_API_KEYS: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_TOP_P: float = 0.8
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_CONTINUATION_ROUNDS: int = 2
    TOP_K_RESULTS: int = 20

    # Vector Backend
    VECTOR_BACKEND: str = "faiss"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    # Monitoring
    OTEL_ENABLED: bool = True
    PROMETHEUS_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"

    # Reranker
    RERANKER_PROVIDER: str = "local"

    # Workspace-specific retrieval config (Task 4.8)
    WORKSPACE_RETRIEVAL_CONFIG: ClassVar[Dict[str, Any]] = {
        "exam":     {"top_k": 8,  "rerank_n": 5,  "chunk_pref": "medium"},
        "hr":       {"top_k": 15, "rerank_n": 10, "chunk_pref": "small"},
        "legal":    {"top_k": 6,  "rerank_n": 4,  "chunk_pref": "large"},
        "finance":  {"top_k": 10, "rerank_n": 6,  "chunk_pref": "small"},
        "research": {"top_k": 12, "rerank_n": 8,  "chunk_pref": "large"},
        "study":    {"top_k": 8,  "rerank_n": 5,  "chunk_pref": "medium"},
        "general":  {"top_k": 8,  "rerank_n": 5,  "chunk_pref": "medium"},
    }

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace('+asyncpg', '')
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

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

        if not self.gemini_keys_list:
            raise ValueError("GEMINI_API_KEYS cannot be empty. Must provide at least one key.")

        if not self.REDIS_URL.startswith("redis://") and not self.REDIS_URL.startswith("rediss://"):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
            
        if self.MAX_UPLOAD_MB <= 0 or self.MAX_UPLOAD_MB > 1000:
            raise ValueError("MAX_UPLOAD_MB must be between 1 and 1000")
            
        if self.OCR_CONFIDENCE_THRESHOLD < 0.0 or self.OCR_CONFIDENCE_THRESHOLD > 1.0:
            raise ValueError("OCR_CONFIDENCE_THRESHOLD must be between 0.0 and 1.0")

        return self

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), case_sensitive=True, extra="ignore")

settings = Settings()
