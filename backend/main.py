import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.db.database import Base, engine
from backend.auth.routes import router as auth_router
from backend.auth.password_reset import router as otp_router
from backend.documents.routes import router as docs_router
from backend.qa.routes import router as qa_router
from backend.agents.routes import router as agents_router
from backend.export.routes import router as export_router
from backend.config import STORAGE_BASE

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DocuMind AI",
    description="AI-powered document Q&A system with hybrid retrieval, table extraction, and agent tools. Built by M.S Kanwa, IcfaiTech Hyderabad",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)
    # also accept www. variant if user forgets
    if FRONTEND_URL.startswith("https://") and not FRONTEND_URL.startswith("https://www."):
        ALLOWED_ORIGINS.append(FRONTEND_URL.replace("https://", "https://www.", 1))

# Only open to all origins in local development
if os.getenv("ENV", "production") == "development":
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(otp_router)
app.include_router(docs_router)
app.include_router(qa_router)
app.include_router(agents_router)
app.include_router(export_router)


@app.get("/")
def root():
    return {
        "app": "DocuMind AI",
        "status": "running",
        "version": "2.0.0",
        "features": [
            "hybrid-retrieval",
            "cross-encoder-reranking",
            "table-extraction",
            "agents",
            "page-citations",
        ],
    }


@app.get("/health")
def health():
    """
    Production health check — verified by Railway before marking deployment live.
    Checks: DB connection, storage directory accessibility.
    """
    checks: dict = {}
    overall = "healthy"

    # 1. Database ping
    try:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        overall = "degraded"

    # 2. Storage directory
    try:
        storage_ok = os.path.isdir(STORAGE_BASE)
        checks["storage"] = "ok" if storage_ok else "missing"
        if not storage_ok:
            os.makedirs(STORAGE_BASE, exist_ok=True)
            checks["storage"] = "created"
    except Exception as exc:
        checks["storage"] = f"error: {exc}"
        overall = "degraded"

    status_code = 200 if overall == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks, "version": "2.0.0"},
    )
