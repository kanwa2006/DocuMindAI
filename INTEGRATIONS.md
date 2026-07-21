# DocuMindAI — Integrations, API Keys & External Services Audit

Companion to [ARCHITECTURE.md](ARCHITECTURE.md). Every external dependency, its configuration surface, how it is wired, and its actual execution status. Sources: `core/config.py`, `.env.example`, and the service/endpoint code that consumes each.

**Wiring status legend:** ✅ fully wired · ⚠️ conditionally wired / needs credentials or config · ❌ referenced but broken/incomplete · 💤 dependency present but effectively unused on the default path.

---

## 1. Configuration Surface (`core/config.py`)

`Settings` (pydantic-settings, `env_file` = `$ENV_FILE` or `.env`, `case_sensitive=True`, `extra="ignore"`). Required (no default → must be set): `AUTH_SECRET_KEY`, `CSRF_SECRET_KEY`, `FRONTEND_URL`, `POSTGRES_*`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`. Everything else has defaults.

Because `extra="ignore"`, several env vars in `.env.example` are **not** declared in `Settings` and are read elsewhere via `os.getenv` (notably `RAZORPAY_*`, `GEMINI_API_KEY_*`, `NEXT_PUBLIC_API_URL`, `TAVILY_API_KEY`).

---

## 2. LLM & AI Providers

### Google Gemini (generation) — ✅
- **Keys:** `GEMINI_API_KEY_1..N` (+ legacy `GEMINI_API_KEY`, and legacy CSV `GEMINI_API_KEYS`). Read from `os.environ` by `GeminiKeyRotator`; bridged from `.env` by `core/gemini_env.bridge_gemini_keys()`.
- **Models:** `GEMINI_MODEL=gemini-2.5-flash-lite`, `GEMINI_FALLBACK_MODEL=gemini-2.0-flash`; temp 0.2, top_p 0.8, max_output 8192.
- **Wiring:** `services/llm_service.py` (`GeminiLLMProvider`) with round-robin rotation, 429/403/500 handling, model fallback, JSON repair, safe text extraction. Used by `/query/stream`, exams, legal, finance, research, study.
- **Caveat:** module-level `llm_service` **raises at import** if no keys and `ENVIRONMENT != test`. The `DummyLLMProvider` (mock answers) is only allowed in `ENVIRONMENT=test`.

### Google Gemini (embeddings) — ⚠️ fallback only
- `services/embedding_service.GeminiEmbeddingProvider` uses `models/text-embedding-004` (768-dim, **zero-padded to 1024**) only as a fallback when `sentence-transformers` fails to load `BAAI/bge-m3`.

### BAAI/bge-m3 (primary embeddings) — ✅
- `sentence-transformers` local model, 1024-dim, normalized. Primary vectorizer for ingestion + retrieval.

### cross-encoder/ms-marco-MiniLM-L-6-v2 (reranker) — ✅
- `services/reranker_service.LocalCrossEncoder` (downloads ~80MB on first use). Falls back to a **fabricated-score** dummy on failure.

### all-MiniLM-L6-v2 (HR JD scoring) — ✅
- Loaded directly in `endpoints/hr.py` for JD↔resume similarity (384-dim). A second, separate embedding model from the main pipeline.

### Tavily (web search, Research) — ⚠️
- `deep_research_agent.py` → `TavilyClient(api_key=settings.TAVILY_API_KEY)`. `TAVILY_API_KEY` is **not declared in `Settings`** (read via attribute access → would raise if referenced without the var). Restricted to gov/academic domains. The agent's document step is broken (see below), so Tavily runs against empty/partial context.

### OpenAI / Anthropic — ❌ not integrated
- Mentioned in comments as "hot-swappable" providers; **no code path** exists. The provider abstraction (`BaseLLMProvider`) would allow it, but only Gemini + Dummy are implemented.

---

## 3. Data Stores

### PostgreSQL + pgvector — ✅ (but not the default vector path)
- Async via `asyncpg`, sync via `psycopg2`. `ankane/pgvector` image in Docker/CI. `DocumentChunk.embedding = Vector(1024)`.
- **Vector backend selection:** `VECTOR_BACKEND` defaults to **`faiss`**, whose retrieval code path is an **in-memory NumPy cosine scan** (not pgvector, not FAISS). True pgvector cosine runs only when `VECTOR_BACKEND=pgvector`. Qdrant is a third option (used only in `delete_document` vector purge).

### FAISS — 💤 / misleading
- `retrieval_service.py` does `try: import faiss except ImportError: faiss=None` but **never uses `faiss`**; `faiss` is **not in `requirements.txt`**. The "faiss" backend is really NumPy brute force.

### Qdrant — ⚠️ partial
- `qdrant-client` in requirements; `QDRANT_HOST/PORT` config. Only wired in `documents.py delete_document` (deletes points when `VECTOR_BACKEND=qdrant`). No Qdrant ingestion/retrieval path exists — so choosing `qdrant` would not populate or query vectors.

### Redis / Upstash — ✅
- Broker + result backend for Celery; retrieval cache; device-trial keys; health failure streak. `REDIS_URL` validated to start with `redis://`/`rediss://`.

### PgBouncer — ✅ (Docker)
- Transaction-mode pooler between backend/worker and Postgres in Compose.

### Supabase — ⚠️ (documented target)
- `.env.example` documents Supabase as the Postgres+pgvector host and Supabase Storage (S3 API) as an option. No Supabase-specific SDK; used as a plain Postgres/S3 endpoint.

---

## 4. Storage

### Local storage — ✅
- `core/storage.LocalStorageProvider` (default, `STORAGE_PATH=./storage`). Handles `local://`, absolute, and relative paths (BUG-011 fix). Used by uploads + worker download.

### S3 / Supabase Storage — ❌ broken init
- `S3StorageProvider.__init__` reads **`settings.AWS_REGION`**, which is **not defined** in `Settings` (the real setting is `S3_REGION`). Selecting `STORAGE_PROVIDER=s3` → `AttributeError` on init. `documents.py` (which builds its own boto3 client) correctly uses `settings.S3_REGION`, so the two disagree. S3 presigned-URL generation in `documents.py` would work; the worker's `storage_service` S3 provider would not.

---

## 5. Payments

### Razorpay — ⚠️ (feature-flagged, insecure default)
- `endpoints/billing.py`: `RAZORPAY_ENABLED` (default **false**), `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET` via `os.getenv`. `razorpay` in requirements.
- **Production flow:** `/billing/create-order` → Razorpay checkout → `/billing/webhook` (HMAC-SHA256 `compare_digest` verification) → `_activate_plan`. This part is correctly implemented.
- **Default flow:** with `RAZORPAY_ENABLED=false`, `/billing/upgrade` activates any plan (incl. enterprise) **for free** — a self-upgrade risk if deployed with the default. See [SECURITY_AUDIT.md](SECURITY_AUDIT.md).
- Plan prices are in INR paise (`go` ₹799, `plus` ₹999, `pro` ₹2999).

---

## 6. Communications

### Email (SendGrid primary, Brevo fallback) — ⚠️
- `services/email_service.send_email`. `SMTP_HOST=smtp.sendgrid.net`, `SMTP_USER=apikey`, `SMTP_PASSWORD=SG.…`; Brevo SMTP fallback vars. Used for OTP verification, password reset, trial nudges, upgrade reminders, health alerts, daily digest. **OTP emails are skipped gracefully when SMTP is unconfigured** (so registration works without email in dev).

### Twilio (phone OTP) — ⚠️
- `TWILIO_ACCOUNT_SID/AUTH_TOKEN/PHONE_NUMBER` (optional). Used by `/auth/send-phone-otp` and `/auth/verify-phone`. No-op without credentials.

---

## 7. Observability

| Service | Config | Status |
|---|---|---|
| **Sentry** | `SENTRY_DSN` | ✅ backend (`main.py`) + frontend (`sentry.client.config.ts`); PII scrubbed; off without DSN |
| **OpenTelemetry** | `OTEL_ENABLED` (default **false** in `.env.example`, **true** in `config.py`) | ⚠️ instrumentation present; default differs between config and env template |
| **Prometheus** | `PROMETHEUS_ENABLED` (same default mismatch), `/metrics` | ⚠️ |
| **PostHog** | frontend `analytics.ts` + `AnalyticsProvider` | ✅ (client-side) |

> Config/env mismatch: `config.py` defaults `OTEL_ENABLED=True`, `PROMETHEUS_ENABLED=True`, `LOG_LEVEL=INFO`, but `.env.example` sets them to `false`. Effective behavior depends on which the deployment uses.

---

## 8. Auth / Identity

- **JWT:** self-issued HS256 (`AUTH_SECRET_KEY`). Comments reference Auth0/Clerk/JWKS/RS256 as a future direction; **not implemented**.
- **CSRF:** self-managed double-submit (`CSRF_SECRET_KEY`).
- **Device fingerprint:** FingerprintJS (frontend) + Redis (backend).

---

## 9. Integration Health Summary

| Integration | Declared in Settings | Consumed | Status |
|---|:---:|:---:|---|
| Gemini (generation) | via env bridge | ✅ | ✅ core dependency |
| Gemini (embeddings) | via env | fallback | ⚠️ |
| BAAI/bge-m3 | n/a (model dl) | ✅ | ✅ |
| Cross-encoder reranker | `RERANKER_PROVIDER` | ✅ | ✅ (dummy fallback) |
| Tavily | ❌ (not in Settings) | research | ⚠️ + broken doc step |
| PostgreSQL/pgvector | ✅ | ✅ | ✅ (but faiss default) |
| FAISS | `VECTOR_BACKEND` | ❌ imported-unused | 💤 misleading |
| Qdrant | ✅ | delete only | ⚠️ partial |
| Redis | ✅ | ✅ | ✅ |
| Local storage | ✅ | ✅ | ✅ |
| S3 | partial | worker path | ❌ `AWS_REGION` bug |
| Razorpay | ❌ (os.getenv) | billing | ⚠️ insecure default |
| SendGrid/Brevo | ✅ | email | ⚠️ needs creds |
| Twilio | ✅ | phone OTP | ⚠️ optional |
| Sentry | ✅ | ✅ | ✅ (DSN-gated) |
| OTel/Prometheus | ✅ | ✅ | ⚠️ default mismatch |
| PostHog | frontend | ✅ | ✅ |

**Dead/aspirational integrations:** OpenAI, Anthropic, Auth0/Clerk (comments only); FAISS (imported, unused); Qdrant ingestion/retrieval (delete-only).
