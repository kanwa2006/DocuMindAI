import os
from dotenv import load_dotenv

load_dotenv()

# ── Storage ───────────────────────────────────────────────────────────────────
STORAGE_BASE = os.getenv(
    "STORAGE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "storage")
)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'documind.db')}"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Auth ──────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ── Embeddings ────────────────────────────────────────────────────────────────
# Upgraded from all-MiniLM-L6-v2 to BAAI/bge-small-en-v1.5
# Same dimension (384) — no FAISS index rebuild needed
# Better retrieval quality on BEIR benchmarks
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# ── RAG Settings ──────────────────────────────────────────────────────────────
# Defaults tuned for stronger long-form answers; override from .env when needed.
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "15"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "250"))

# ── Gemini API Keys (multi-key rotation) ─────────────────────────────────────
GEMINI_API_KEYS = [
    key.strip()
    for key in os.getenv("GEMINI_API_KEYS", "").split(",")
    if key.strip()
]
if not GEMINI_API_KEYS and os.getenv("GEMINI_API_KEY"):
    GEMINI_API_KEYS = [os.getenv("GEMINI_API_KEY")]

def _normalize_model_name(raw: str) -> str:
    raw = (raw or "").strip()
    return raw.split("/", 1)[1] if raw.startswith("models/") else raw

# Safer default than deprecated/limited families
GEMINI_MODEL = _normalize_model_name(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
GEMINI_TOP_P = float(os.getenv("GEMINI_TOP_P", "0.8"))
# High default to avoid truncation on long summaries/photo OCR answers.
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))
# Number of follow-up continuation calls when output appears truncated.
GEMINI_CONTINUATION_ROUNDS = int(os.getenv("GEMINI_CONTINUATION_ROUNDS", "2"))

# Legacy Groq (kept for backward compatibility only)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"