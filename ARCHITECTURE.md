# DocuMindAI — System Architecture & Data Flows

Companion to [REPORT.md](REPORT.md). This document describes every subsystem, the folder structure, and the end-to-end execution flows. Everything here is derived from direct source inspection.

---

## 1. Repository Layout

```
DocuMindAI/
├── backend/                         # FastAPI application + Celery workers
│   ├── app/
│   │   ├── main.py                  # ASGI app, middleware stack, Sentry, Gemini key bridge
│   │   ├── api/v1/
│   │   │   ├── api.py               # Router aggregation (all routers mounted here)
│   │   │   └── endpoints/           # 30 endpoint modules (auth, documents, query, hr, …)
│   │   ├── core/                    # config, auth, security, middleware, rate_limiter,
│   │   │                            #   circuit_breaker, telemetry, storage, workspace,
│   │   │                            #   trial_enforcement, gemini_env, json_logger, logging
│   │   ├── db/                      # base, base_class, session (async + sync engines)
│   │   ├── models/                  # ~35 SQLAlchemy model files (~50 tables)
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/                # Business logic (RAG, OCR, LLM, export, veritas, …)
│   │   ├── workers/
│   │   │   ├── celery_app.py        # Celery config, task routes, Beat schedule
│   │   │   └── tasks/               # document/hr/legal/finance/study/research/export/ocr/…
│   │   ├── automation/              # Celery Beat scheduled jobs (auto_*)
│   │   ├── tasks/                   # eval_tasks, report_tasks (separate from workers/tasks)
│   │   └── utils/pii_redactor.py
│   ├── alembic/versions/            # 55 migration files
│   ├── tests/test_api_contracts.py  # 2 smoke tests
│   ├── load_tests/locustfile.py
│   ├── scripts/                     # prestart.sh, seed_dev.py, worker runners, check_db.py
│   └── requirements.txt
│
├── frontend/                        # Next.js 16 App Router
│   ├── src/app/                     # Pages: (marketing), workspaces, auth, admin, account…
│   ├── src/components/              # ~50 shared components (WorkspaceUI is the hub)
│   ├── src/hooks/                   # useOnboarding, useVoiceInput, useSessionExpiry, useTheme…
│   ├── src/lib/                     # api.ts (API client), analytics.ts, pricing.ts, store/
│   ├── src/middleware.ts            # Next middleware (route protection)
│   └── src/styles/                  # tokens.css, components.css, motion.css, typography.css
│
├── infrastructure/                  # Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
├── docs/                            # architecture/project-map.md, deployment/, screenshots/
│   └── marketing/ (untracked)       # devpost, interview-guide, resume, storyboard, etc.
├── .github/workflows/ci.yml
├── .env.example
└── railway.json
```

**Note on `.agents/skills/`:** this large directory (ckm-*, ui-ux-pro-max) is third-party design/agent tooling checked into the repo. It is **not** part of the DocuMindAI application and is out of scope for this audit.

---

## 2. Backend Application Bootstrap (`app/main.py`)

Order of operations at startup:

1. **Gemini key bridge** (`core/gemini_env.bridge_gemini_keys()`): pydantic-settings loads `.env` into the `settings` object but *not* into `os.environ`. The `GeminiKeyRotator` reads `os.environ` directly, so this bridge copies `GEMINI_API_KEY_*` into the process environment (CWD-independent, resolved relative to the backend root). It runs from `main.py` (web), from `get_key_rotator()` (worker/scripts), and logs a **CRITICAL** error if no keys are found (which would force the mock provider — but see the hard-fail behavior in §6).
2. **Sentry init** (only if `SENTRY_DSN` set): FastAPI + Celery + SQLAlchemy integrations, 5% trace sample, PII scrubbing via `before_send`.
3. **FastAPI app** created with OpenAPI at `/api/v1/openapi.json`.
4. **SlowAPI limiter** registered (`app.state.limiter`) with the shared limiter from `core/rate_limiter.py`.
5. **Middleware stack** (executes in reverse of registration for requests):
   - `CORSMiddleware` (origins from `CORS_ORIGINS`, credentials allowed)
   - `CorrelationIdMiddleware` (X-Correlation-ID in/out)
   - `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options=DENY, X-XSS-Protection, HSTS, CSP `default-src 'self'; connect-src 'self' {FRONTEND_URL}`)
   - `CSRFMiddleware` (double-submit cookie; exempts `/auth/*`, `/csrf-token`, `/health`)
   - `TenantContextMiddleware` (derives `request.state.collection_name` from JWT)
   - `DeviceFingerprintMiddleware` (blocks repeat trial registration by device via Redis)
6. **OpenTelemetry + Prometheus** (`setup_telemetry(app, is_worker=False)`).
7. **Router** mounted at `settings.API_V1_STR` (`/api/v1`).
8. Root `GET /` returns a liveness JSON.

---

## 3. Request Routing

All routers are aggregated in `app/api/v1/api.py` and mounted under `/api/v1`:

| Prefix | Router | Auth |
|--------|--------|------|
| (none) | `health` | public (`/health`, `/health/detailed`) |
| `/documents` | `documents` | JWT cookie |
| `/query` | `query` | JWT cookie |
| `/export` | `export` | JWT cookie |
| `/benchmark` | `benchmark` | JWT / admin |
| `/exams` | `exams` | JWT cookie |
| `/hr` `/legal` `/finance` `/study` `/research` | workspace routers | JWT cookie |
| (none) | `ws` (websocket) | token |
| `/auth` | `auth` | public (login/register/refresh/reset) |
| (none) | `csrf` | public (`/csrf-token`) |
| `/chats` | `chats` | JWT cookie |
| `/corrections` | `corrections` | JWT cookie |
| (none) | `retention`, `reports` | JWT / admin |
| `/billing` | `billing` | JWT cookie |
| `/bookmarks` `/notifications` `/users` | user features | JWT cookie |
| (none) | `feedback` | JWT cookie |
| `/insights` | `insights` | JWT cookie |
| (none) | `shared_router` (from chats) | **public** (share token) |
| `/admin` | `admin` | JWT / admin roles |

The frontend convention (`frontend/src/lib/api.ts`): `NEXT_PUBLIC_API_URL` already ends in `/api/v1`; `apiFetch(endpoint)` performs `` `${API_BASE}${endpoint}` `` so endpoints start with `/` and **omit** the `/api/v1` prefix. (The historical "doubled prefix" bug the `docs/` mention has been resolved in current frontend code — see [API_AUDIT.md](API_AUDIT.md).)

---

## 4. Authentication Pipeline

**Login** (`/auth/login`): credentials verified with **bcrypt** (`core/security.verify_password`). On success, `create_access_token` (HS256, `ACCESS_TOKEN_EXPIRE_MINUTES=60`) and `create_refresh_token` (HS256, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `token_type="refresh"`) are issued and set as cookies (`token`, plus refresh).

**Every protected request:**
1. `get_current_user` (`core/auth.py`) reads the `token` cookie.
2. `AuthProvider.verify_token` decodes with **HS256 only** (`algorithms=[settings.JWT_ALGORITHM]`), `verify_signature=True`. Extracts `sub` (user id), `email`, `workspace_id` (defaults to user id), `roles`.
3. Returns a dict `{id, email, workspace_id, roles}` injected into endpoints.

**Silent refresh** (frontend): on a 401, `apiFetch` calls `/auth/refresh` once and retries; on failure it dispatches a `session:expired` event (handled by `SessionExpiredOverlay`) rather than hard-redirecting.

**CSRF:** double-submit cookie. `apiFetch` fetches `/csrf-token` on boot, echoes it in `X-CSRF-Token` on mutations. `CSRFMiddleware` requires header==cookie for POST/PUT/DELETE/PATCH, exempting bootstrap/auth paths.

**Device fingerprint:** `@fingerprintjs/fingerprintjs` computes a `visitorId`; sent as `X-Device-ID`. `DeviceFingerprintMiddleware` blocks a second trial registration from the same device (Redis key `device_trial:{id}`).

**Tenant context:** `TenantContextMiddleware` decodes the JWT to set `request.state.collection_name = docuMind_{user_id}` (or `docuMind_org_{org_id}` when `VECTOR_ISOLATION_MODE=organization`). ⚠️ It decodes with `algorithms=["HS256","RS256"]`, unlike the hardened `auth.py` — see [SECURITY_AUDIT.md](SECURITY_AUDIT.md).

**Workspace identity** (`core/workspace.resolve_workspace_id`): `User.workspace_id` is a slug string (default `"general"`), but table columns like `ChatSession.workspace_id` are UUIDs. The resolver passes real UUID strings through unchanged and hashes slugs via `uuid.uuid5(NAMESPACE_DNS, slug.lower())` — deterministic, no `Workspace` table needed. `endpoints/documents.py` uses matching `uuid.uuid5(NAMESPACE_DNS, …)` inline fallbacks (a latent casing inconsistency: the resolver lowercases, the inline version does not).

---

## 5. Document Processing Pipeline (Ingestion)

### 5.1 Upload flow
1. **`GET /documents/upload/presigned`** (rate-limited 20/min) validates MIME (PDF/DOCX/PPTX) and size (`MAX_UPLOAD_MB=200`), returns either an S3 presigned PUT URL or a local-upload descriptor (`provider: "local"`).
2. Frontend uploads: **S3 PUT** directly, or **multipart POST `/documents/upload/local`** (XHR with real progress). Local files are written under `STORAGE_PATH/{workspace}/{uuid}_{safe_name}` (filename sanitized against path traversal).
3. **`POST /documents/upload/verify`** creates the `Document` row (with fallbacks for NOT-NULL columns), links `chat_session_id` for per-chat isolation, and **dispatches `process_document.delay(...)`**. If the broker is down, the doc is marked `FAILED` and a 503 is returned.

Text "clips" (`POST /documents/clip`) skip storage/OCR: they MD5-dedupe, create a `Document`, and dispatch `process_clip_document`.

### 5.2 The worker (`workers/tasks/document_tasks.process_document`)
Runs with a **synchronous** SQLAlchemy session (`SyncSessionLocal`):
1. Fetch doc → status `PROCESSING`.
2. Download to a temp file preserving the **real extension** (BUG-017 fix: DOCX/PPTX would otherwise be misrouted).
3. **`OCRService.extract_document_stream(path)`** streams page records:
   - `.pptx` (detected by extension **or** ZIP magic + `ppt/` entries) → `python-pptx`, one record per slide (with speaker notes).
   - Everything else → **PyMuPDF** (`fitz`): per page, `is_text_native` heuristic (>50 chars). Native pages: layout-aware block extraction sorted top-to-bottom. Non-native (scanned) pages: fall back to raw `page.get_text("text")` — **a stub where "Tesseract/EasyOCR would be injected."**
4. Per page → `ChunkingService.chunk_page_text` merges layout blocks (split on `\n\n`) up to `CHUNK_SIZE=1800` with `CHUNK_OVERLAP=300`, keeping big tables whole.
5. Chunks are **batched (50)**, embedded via `embedding_service.generate_embeddings`, and committed.
6. Status → `EXTRACTED` → `READY`.
7. Fire-and-forget **`generate_proactive_insights_task`** (creates a fresh event loop to run the async insights service).
8. On failure: retry with exponential backoff (max 3), then `FAILED` (dead-letter).

**Critical:** the marketed multi-engine OCR (`OCROrchestrator` with `DoclingEngine` + `PaddleOCREngine` + `OCRValidationGateway`) is **not** used here. It is referenced only by `workers/tasks/ocr_tasks.py`, which is routed to `ocr_gpu_queue` (see §8). `extraction_router.route_extraction` (pymupdf4llm-first) also exists but is **not** called by `process_document` (the endpoint comment notes it was intentionally bypassed after documents got stuck in `INDEXING`).

---

## 6. RAG / AI Pipeline (Query)

### 6.1 Retrieval (`services/retrieval_service.py`, "never modify")
`RetrievalService.retrieve_chunks(query, workspace_id, top_k, …, document_ids)`:
- Fetches a fusion pool of `max(top_k*2, 30)` candidates.
- **Semantic branch:** if `VECTOR_BACKEND == "pgvector"` → `DocumentChunk.embedding.cosine_distance(query_vec)` ordered in SQL. Otherwise → load matching chunks and compute **NumPy cosine similarity in memory** (this is the "faiss" default; `import faiss` is attempted but never used).
- **Lexical branch:** Postgres `to_tsvector('english') @@ websearch_to_tsquery` ranked by `ts_rank_cd` (BM25-style). (SQLite fallback uses `ILIKE`.)
- **Reciprocal Rank Fusion:** `score += 1/(60 + rank + 1)` across both lists; sort; truncate to `top_k`. Returns results + tracing (embedding/db timings, candidate counts).

Filters always applied: `Document.status == READY`, optional `workspace_id`, optional `document_ids` (per-chat isolation).

### 6.2 Grounding (`services/grounding_service.py`, "never modify")
`GroundingService.prepare_grounded_context`:
1. Retrieve `retrieval_top_k=30` candidates (short-circuits to empty if `document_ids == []`).
2. Dedupe by chunk id.
3. **Rerank** via `reranker_service.rerank_results` (cross-encoder scores).
4. Filter by `rerank_threshold`, take `final_top_k`.
5. **Sort selected chunks into document order** (filename, page, chunk_index) for linear citations.
6. **Token budget** (`GROUNDING_TOKEN_BUDGET=6000`, ~4 chars/token heuristic): append `<evidence document="…" page="…" chunk_id="…">…</evidence>` blocks until budget hit.
7. `confidence_score` = mean rerank score of accepted evidence.

### 6.3 Reranker (`services/reranker_service.py`)
`LocalCrossEncoder` (singleton, `ms-marco-MiniLM-L-6-v2`, max_len 512), min-max normalized. Chosen when `RERANKER_PROVIDER=="local"` (default). Falls back to `DummyLocalReranker` (fabricated 0.85/0.99 scores) on any import/config error.

### 6.4 Embeddings (`services/embedding_service.py`)
`LocalEmbeddingProvider` (`BAAI/bge-m3`, 1024-dim, normalized) → falls back to `GeminiEmbeddingProvider` (`text-embedding-004`, 768-dim, **zero-padded to 1024**) → `DummyEmbeddingProvider` / zero vectors. Query and document embeddings go through the same chain, but mixing bge-m3 and padded-Gemini vectors in one corpus degrades similarity.

### 6.5 LLM (`services/llm_service.py` + `llm_key_rotation.py`, "never modify")
- `GeminiKeyRotator`: reads `GEMINI_API_KEY_1..N` (+ legacy `GEMINI_API_KEY`) from env, round-robin, tracks `_bad_keys` (403) and `_cooling_keys` (429). `get_key()` sleeps until the soonest cooldown when all keys are cooling — **inside the lock** (blocking).
- `GeminiLLMProvider`: `_execute_with_rotation` classifies errors (429/quota → 300s cooldown; 403 → permanent skip; 500/503 → 30s), model fallback on 404/deprecated. Sync `generate_content` is offloaded via `run_in_executor`.
- `_safe_extract_text`: never crashes on empty parts / `finish_reason` 2 (MAX_TOKENS), 3 (SAFETY), 4 (RECITATION) — returns friendly messages.
- `generate_json`: JSON-repair loop (strip fences → `json.loads` → Pydantic validate → re-prompt on failure, up to 3 attempts).
- **`llm_service = LLMService()`** is a module-level singleton that **raises `RuntimeError` at import time** if no Gemini keys and `ENVIRONMENT != "test"` — so the backend cannot import the query stack without keys.
- **No `get_embedding` method exists** on `LLMService`/`GeminiLLMProvider`, yet several endpoints call it (see [FINAL_AUDIT.md](FINAL_AUDIT.md)).

### 6.6 Veritas (`services/veritas_engine.py`, "never modify")
`compute_trust_score(answer, primary_chunks, query, …)` returns a 0–100 score from five weighted factors with **hardcoded values**:
`dual_retrieval` (30%: 70 or 20), `direct_quote` (25%: first-50-char verbatim match), `contradiction` (20%: 80 if >1 doc else 100 — no real detection), `chunk_consensus` (15%: 75 or 50), `uncertainty` (10%: 100 − 20×phrase count). Grades HIGH/MEDIUM/LOW/VERY_LOW. **Only called by `deep_research_agent.py`.**

### 6.7 Streaming endpoint (`endpoints/query.py: /query/stream`)
SSE, `@limiter.limit("30/minute")`. `event_generator`:
1. Load user; **trial check** (`check_and_increment_trial`, 402 when exhausted); emit `trial_status`.
2. Resolve `workspace_type` retrieval config (`WORKSPACE_RETRIEVAL_CONFIG`); fetch last-8 messages + this chat's attached READY docs.
3. **Summary-intent branch:** if attached docs + `is_summary_intent(query)` → `generate_full_document_summary_stream` (map-reduce over full docs), emit placeholder `metadata{confidence:0.95}`, stream tokens, append disclaimer, done.
4. Otherwise: **Redis retrieval cache** (key includes workspace + query + attached doc ids, TTL 300s) → `GroundingService.prepare_grounded_context`.
5. Emit `metadata` (evidence + `confidence_score` from grounding, `grounded`/`mode` flags).
6. Build system prompt (strict grounded prompt if grounded; a "no documents attached" general-knowledge prompt otherwise), inject workspace response schema + language instruction (+ comparison mode).
7. Stream tokens from `llm_service.provider.generate_stream`; micro-sleep to detect client disconnect; append legal/finance disclaimer; emit `done`.

⚠️ The `metadata.confidence_score` is the **grounding rerank average**, not a Veritas score. Assistant messages are **not persisted here** — persistence happens via `/chats/{id}/messages` and the `/chats` ask path.

---

## 7. Streaming Architecture

Two SSE styles exist:
- **Real token streaming:** `/query/stream`, `/study/tutor/chat`, `/research/copilot/chat` — true async generators from Gemini → grounding → FastAPI `StreamingResponse`, `text/event-stream`.
- **Simulated progress:** `/hr/events/processing/{id}`, `/legal/events/legal/{id}`, `/finance/events/finance/{id}`, `/study/events/study/{id}`, `/research/events/research/{id}` — emit fake `progress: i*10` heartbeats with `asyncio.sleep(2)`; comments say "In production, this would subscribe to a Redis Pub/Sub channel." These do not reflect real task status.

There is also a WebSocket router (`endpoints/ws.py`) mounted at the API root, despite the product describing SSE.

---

## 8. Worker Architecture (`workers/celery_app.py`)

- **Broker/backend:** Redis (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
- **`include`** (modules the worker imports/registers): `document_tasks`, `export_tasks`, `audio_tasks`, `ocr_tasks`, `hr_tasks`, and all seven `automation.auto_*`. **Notably missing:** `legal_tasks`, `finance_tasks`, `study_tasks`, `research_tasks`, `email_tasks`.
- **`task_routes`:**
  - `hr/legal/finance/study/research_tasks.*` → `main-queue`
  - `ocr_tasks.*` → `ocr_gpu_queue`
  - `embedding_tasks.*` → `embedding_queue`
  - `retrieval_tasks.*` → `retrieval_queue`
  - `export_tasks.*` → `export_queue`
  - (`document_tasks` and automation default to the `celery` queue)
- **`beat_schedule`:** `flag_stale_reviews` (8:00), `auto_health_check` (every 5 min), `auto_key_rotation` (hourly), `auto_daily_digest` (02:30), `auto_db_cleanup` (weekly), `auto_subscription_check` (18:30), `auto_gst_notice` / `auto_model_check` (weekly).
- **`worker_max_tasks_per_child=50`** (memory hygiene).

**Docker worker command:** `celery -A app.workers.celery_app worker -Q main-queue,celery`.

**Consequences of the routing + include + queue selection:**
- `document_tasks` (queue `celery`) ✅ consumed.
- `hr_tasks` (queue `main-queue`, in `include`) ✅ consumed.
- `legal/finance/study/research_tasks` (queue `main-queue`, **not in `include`**) ⚠️ not registered by the worker → their `/process` endpoints enqueue tasks that never execute.
- `ocr_tasks` (queue `ocr_gpu_queue`), `export_tasks` (queue `export_queue`), `embedding/retrieval_tasks` (own queues) ⚠️ **not consumed** by `-Q main-queue,celery`.
- **No Celery Beat service** exists in `docker-compose.yml`, so no scheduled automation runs by default.

See [FINAL_AUDIT.md](FINAL_AUDIT.md) for severity.

---

## 9. Data Layer

- **PostgreSQL 16 + pgvector** (`ankane/pgvector:v0.5.1`).
- **Async engine** via `asyncpg` (`settings.async_database_url`); **sync engine** via `psycopg2` (`settings.sync_database_url`, which normalizes `ssl`→`sslmode` and forces `+psycopg2`) for Celery and health checks.
- **PgBouncer** (transaction mode, pool size 20, max 1000 clients) fronts Postgres in Docker; the backend/worker point `POSTGRES_SERVER=pgbouncer`.
- **~50 tables** across `models/` (see [WORKSPACES.md](WORKSPACES.md) §Data Model for the full list). Core: `users`, `organizations`, `user_roles`, `documents`, `document_pages`, `document_chunks` (with `Vector(1024)` embedding), `chat_sessions`, `chat_messages`.
- **Vectors:** `DocumentChunk.embedding` is the retrieval column. Workspace tables (`legal_clauses`, `finance_transactions`, `study_flashcards`, `research_findings`) also declare embedding columns for per-domain semantic search (used by the broken `*/search` endpoints).
- **RLS migrations** exist (`2b3c4d5e6f70_add_rls_user_isolation`, `e253f70b7e95_enable_rls_documents`) enabling Postgres row-level security for user isolation.
- **Migrations:** 55 files with several explicit merge-head revisions (`merge_heads`, `merge_remaining_heads`, `merge_orphaned_migration_head`), indicating a branchy history.

---

## 10. Caching

- **Retrieval cache** (`query.py`): Redis `retrieval:{workspace}:{hash}` (TTL 300s), keyed by workspace + query + attached doc ids. Failures are swallowed (never break the request).
- **JD embedding cache** (`hr.py`): in-process dict keyed by sha256 of JD text.
- **Redis** also stores device-trial keys and the health-check failure streak.
- ⚠️ `delete_document` purges Redis keys matching `retrieval:uid_{uid}:*`, but the retrieval cache is written under `retrieval:{workspace}:*` — the purge pattern does not match, so cache can go stale after deletion.

---

## 11. Rate Limiting

`SlowAPI` (`core/rate_limiter.limiter`, keyed by remote IP). Applied via decorators: `/query/stream` (30/min), `/documents/upload/presigned` (20/min), `/documents/upload/local` (20/min). The shared limiter is registered in `main.py` with a `RateLimitExceeded` handler. Endpoints using it must take `request: Request` as the first parameter (SlowAPI requirement).

---

## 12. Security Controls (summary; full analysis in SECURITY_AUDIT.md)

bcrypt password hashing · HS256 JWT in HTTP-only cookies · access+refresh tokens · CSRF double-submit · HSTS + X-Frame-Options + CSP + nosniff headers · SlowAPI rate limiting · device fingerprinting · email OTP verification (optional) · phone OTP (Twilio, optional) · PII redaction utility · HMAC-signed 15-minute document URLs · Razorpay webhook HMAC verification · per-user/-org vector namespace isolation · Postgres RLS migrations · Sentry PII scrubbing.

---

## 13. Error Handling & Retry

- **Document worker:** try/except with `self.retry(exc, countdown=2**retries, max_retries=3)`; pre-checks `retries >= 3` to force `FAILED` status (so docs never hang in `PROCESSING`); dead-letter handling.
- **LLM:** `_execute_with_rotation` retries across keys (`max_attempts = 2×keys`), model fallback on 404.
- **Circuit breaker:** `core/circuit_breaker.py` exists as a reusable primitive.
- **Redis/cache/email:** failures are logged and swallowed to avoid breaking the request path.
- **SSE:** `event_generator` catches exceptions and emits an `error` SSE event; re-raises `CancelledError`.

---

## 14. Deployment

### Docker Compose (`infrastructure/docker-compose.yml`)
Services: `db` (pgvector), `pgbouncer`, `redis`, `backend` (uvicorn `--reload`, healthcheck on `/api/v1/health`), `worker` (`-Q main-queue,celery`), `frontend`. Backend/worker read `../backend/.env` and override `POSTGRES_SERVER=pgbouncer`. **No Beat service.** Storage is a shared volume `storage_data`.

### CI (`.github/workflows/ci.yml`)
- **backend-validation:** Python 3.11, `pip install -r requirements.txt`, `pip-audit`, `prestart.sh`, `alembic upgrade head`, `pytest tests/ -v` (2 tests) — against a pgvector + Redis service.
- **frontend-validation:** **Node 18** (⚠️ Next.js 16 targets Node ≥20), `npm install`, `npm run lint`, `npm run build`.

### Railway (`railway.json`)
Cloud deployment descriptor. `.env.example` documents a GitHub Student Pack stack: Supabase (Postgres+pgvector), Upstash (Redis), SendGrid (email), Railway/Render hosting.

### Docker images
`Dockerfile.backend` and `Dockerfile.frontend` under `infrastructure/`.

---

## 15. Observability

- **OpenTelemetry:** `core/telemetry.setup_telemetry` instruments FastAPI routes and Celery workers (`OTEL_ENABLED`, default **off** in `.env.example`).
- **Prometheus:** metrics exporter (`PROMETHEUS_ENABLED`, default **off**), `/metrics`.
- **Sentry:** backend (`main.py`) + frontend (`sentry.client.config.ts`), env-gated by DSN.
- **PostHog:** `frontend/src/lib/analytics.ts` + `AnalyticsProvider`.
- **Structured logging:** `core/json_logger.py`, `core/logging.py`; correlation IDs via middleware.
- **Health:** `/health` (db + redis) and `/health/detailed` (adds Gemini key status). `auto_health_check` additionally probes db/redis/gemini/disk/celery and emails `ADMIN_EMAIL` after 3 consecutive failures.

---

## 16. Frontend Architecture

- **App Router pages** (`src/app`): each workspace page is a one-line wrapper, e.g. `general/page.tsx` → `<WorkspaceUI workspaceType="general" />`. All seven workspaces share **`components/WorkspaceUI.tsx`**, the central chat/upload/stream shell.
- **API client** (`src/lib/api.ts`): typed wrappers over `apiFetch`, CSRF bootstrap, device fingerprint, silent JWT refresh, SSE parsing (`askQuestionStream`), upload-with-progress (XHR), document status polling.
- **State:** Zustand trial store (`src/lib/store/trialStore.tsx`); hooks for onboarding, voice input/readback, session expiry, theme.
- **Notable components:** `Sidebar`, `CommandPalette`, `ProactiveInsightsPanel`, `EnterpriseDocumentViewer`, `CandidateRankingsPanel`, `LegalRiskPanel`, `FinanceRatioPanel`, `veritas/TrustScorePanel`, `ShareSessionModal`, `UpgradeModal`, `NotificationCenter`, clip/voice components.
- **Middleware** (`src/middleware.ts`): route gating. **PWA:** `public/manifest.json`, `public/sw.js`, `PWAInstaller`.

---

## 17. Concurrency Model

- **API:** fully async FastAPI + async SQLAlchemy (`asyncpg`) — non-blocking DB I/O on the request path. Blocking model calls (Gemini, sentence-transformers) are offloaded via `run_in_executor`.
- **Workers:** synchronous SQLAlchemy sessions inside Celery tasks; async services invoked via a fresh event loop where needed (proactive insights).
- **Known blocking spots:** `GeminiKeyRotator.get_key()` calls `time.sleep()` while holding its lock; embedding/reranker model loads are heavy and lazy; the NumPy vector fallback materializes all chunk embeddings in memory.

See [QUALITY_AUDIT.md](QUALITY_AUDIT.md) for the full concurrency/performance analysis.
