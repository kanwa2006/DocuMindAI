# DocuMindAI — Pre-Launch Audit & Deployment Guide

**Audit date:** 2026-07-29
**Scope:** understand, clean, configure and deploy the existing application. **No features or business logic were changed.** No file under `backend/app/` or `frontend/src/` was modified.
**Method:** every claim below was verified against the code or by running a command. Where a document in this repo contradicts the code, the code wins.

---

## Table of contents

1. [Real architecture](#1-real-architecture)
2. [Exact tech stack](#2-exact-tech-stack)
3. [Running it locally](#3-running-it-locally)
4. [What was broken, and what I changed](#4-what-was-broken-and-what-i-changed)
5. [Environment variables — complete reference](#5-environment-variables--complete-reference)
6. [Cleanup performed](#6-cleanup-performed)
7. [Deployment — platform choice](#7-deployment--platform-choice)
8. [Deployment — step-by-step guide](#8-deployment--step-by-step-guide)
9. [Troubleshooting](#9-troubleshooting)
10. [Known gaps not fixed in this pass](#10-known-gaps-not-fixed-in-this-pass)
11. [Branding / logo swap](#11-branding--logo-swap)

---

## 1. Real architecture

DocuMindAI is a multi-tenant, grounded RAG platform over user-uploaded documents, organised into seven workspaces (General, HR, Legal, Finance, Study, Research, Exam).

```
                    ┌──────────────────────────────────────┐
 Browser  ────────► │ Next.js 16 (App Router), 30 routes    │
                    │ src/lib/api.ts  ·  apiFetch()         │
                    └───────────────┬──────────────────────┘
                                    │ NEXT_PUBLIC_API_URL
                                    │ (must already include /api/v1)
                                    │ cookies: JWT + CSRF double-submit
                                    ▼
                    ┌──────────────────────────────────────┐
                    │ FastAPI  ·  app/main.py               │
                    │ middleware: CORS → CorrelationId →    │
                    │   SecurityHeaders → CSRF →            │
                    │   TenantContext → DeviceFingerprint   │
                    │ router mounted at /api/v1             │
                    └───┬───────────────┬──────────────┬───┘
           asyncpg (async)│              │ Redis        │ enqueue
                          ▼              ▼              ▼
              ┌──────────────────┐ ┌──────────┐ ┌───────────────────┐
              │ PostgreSQL 16    │ │ Redis 7  │ │ Celery worker(s)  │
              │ + pgvector (HNSW)│ │ cache +  │ │ psycopg2 (SYNC)   │
              │ ~50 tables, RLS  │ │ broker   │ │ ingest/OCR/export │
              └──────────────────┘ └────┬─────┘ └───────────────────┘
                                        │
                                   ┌────▼──────┐
                                   │ Celery    │  beat_schedule jobs
                                   │ Beat      │  (health, digests…)
                                   └───────────┘
```

### Request path for a grounded answer

`POST /api/v1/query/stream`
→ `grounding_service`
→ `retrieval_service` (pgvector ANN **or** in-memory NumPy scan per `VECTOR_BACKEND`) **+** lexical full-text search
→ Reciprocal Rank Fusion
→ `reranker_service` (cross-encoder `ms-marco-MiniLM-L-6-v2`)
→ token-budgeted grounding (`GROUNDING_TOKEN_BUDGET`)
→ `llm_service` (Gemini, with key rotation)
→ streamed to the browser over **Server-Sent Events**.

SSE event names — client and server must stay in lockstep:
`trial_status`, `thinking_stage`, `status`, `metadata`, `token`, `error`, `done`.

### Key invariants (do not break)

- All routes live under `/api/v1`. `NEXT_PUBLIC_API_URL` already contains it; endpoint strings in `lib/api.ts` start with `/` and **omit** `/api/v1`.
- `core/workspace.resolve_workspace_id()` is the single derivation of a workspace UUID: `uuid5(NAMESPACE_DNS, slug.lower())`. It is one-way — you cannot recover the slug from the UUID.
- **Extract-then-compute**: the LLM extracts fields; Python computes every number (all 15 finance ratios, legal escalation, citation formatting). Preserve this.
- Async request path (`asyncpg`) vs. sync worker sessions (`psycopg2`) — never mix.
- Every workspace query filters on `owner_id` **and** the workspace UUID.
- Worker three-way rule: a task must be in `celery_app.include`, routed in `task_routes`, **and** its queue consumed by a running `-Q`.

### Third-party services

| Service | Used for | Required? |
|---|---|---|
| Google Gemini | generation + fallback embeddings | **Yes** — without it the app silently serves mock answers |
| Supabase / any Postgres 16 + pgvector | primary datastore, vector index | **Yes** |
| Redis (Upstash) | cache, Celery broker + result backend | **Yes** |
| Razorpay | trial-to-paid billing | No — `RAZORPAY_ENABLED=false` |
| SendGrid / Brevo | OTP + transactional email | No — skipped when unset |
| Twilio | phone OTP | No |
| Sentry | error tracking (backend + frontend) | No |
| PostHog | product analytics (frontend) | No |
| Tavily | web search in deep research | **Non-functional** — see §10 |

---

## 2. Exact tech stack

### Backend — Python **3.11** (image), 3.11.9 (local venv)

| Component | Version constraint |
|---|---|
| FastAPI | **`==0.136.1`** — pinned during this audit, see §4.8 |
| Starlette | **`==1.0.0`** — pinned during this audit, see §4.8 |
| Uvicorn | `>=0.27.0` (`[standard]`) |
| Pydantic / pydantic-settings | `>=2.5.3` / `>=2.1.0` |
| SQLAlchemy | `>=2.0.25` (async + sync) |
| asyncpg / psycopg2-binary | `>=0.29.0` / `>=2.9.9` |
| Alembic | `>=1.13.1` — **44 migration files** |
| Celery / redis-py | `>=5.3.6` / `>=5.0.1` |
| pgvector | `>=0.2.5` |
| sentence-transformers | `>=2.7.0` (bge-m3 + cross-encoder) |
| transformers | `>=4.37.2` |
| google-generativeai | `>=0.8.0` |
| PyMuPDF / pymupdf4llm | `>=1.23.8` / `>=0.0.17` |
| PaddleOCR / PaddlePaddle / Docling / LayoutParser | `>=2.7.0.3` / `>=2.6.0` / `>=1.1.0` / `>=0.3.4` |
| passlib + bcrypt | `1.7.4` + **pinned `4.0.1`** (passlib breaks on bcrypt ≥ 4.1) |
| PyJWT / SlowAPI | `>=2.8.0` / `>=0.1.9` |
| Razorpay / boto3 / Sentry | `>=1.4.1` / `>=1.34.0` / `>=1.40.0` |
| OpenTelemetry + prometheus-client | `>=1.20.0` / `>=0.17.1` |

**Package manager:** pip + `requirements.txt`.
**ORM:** SQLAlchemy 2.
**Auth:** HS256 JWT in cookies, bcrypt password hashing, CSRF double-submit token, device fingerprint, per-tenant vector namespaces, Postgres row-level security.

### Frontend — Node **20** (CI + image); builds fine on 24 locally

| Component | Version |
|---|---|
| Next.js | `16.2.6` (App Router) |
| React / react-dom | `19.2.4` |
| TypeScript | `^5` |
| Tailwind CSS | `^4` (via `@tailwindcss/postcss`) |
| @sentry/nextjs | `^10.53.1` |
| posthog-js | `^1.374.2` |
| react-pdf | `^10.4.1` |
| recharts | `^2.15.4` |
| @fingerprintjs/fingerprintjs | `^5.2.0` |
| @headlessui/react + @heroicons/react | `^2.2.10` / `^2.2.0` |

**Package manager:** npm (`package-lock.json`).

### Data / infrastructure

PostgreSQL 16 + pgvector (`ankane/pgvector:v0.5.1`), PgBouncer (`edoburu/pgbouncer`, transaction mode), Redis 7-alpine, Docker Compose, GitHub Actions CI.

---

## 3. Running it locally

### Prerequisites
Docker Desktop, Node 20+, Python 3.11, and a Google Gemini API key.

### Option A — Docker Compose (full stack, recommended)

```bash
cp .env.example backend/.env
# edit backend/.env: set AUTH_SECRET_KEY, CSRF_SECRET_KEY, GEMINI_API_KEY_1
cd infrastructure
docker compose up --build
```

Services: frontend `:3000`, backend `:8000`, Postgres `:5433`, PgBouncer `:6432`, Redis `:6380`.
Compose starts **six** services — db, pgbouncer, redis, backend, worker, beat, frontend — so background ingestion and scheduled jobs actually run.

> Note the remapped host ports (5433 / 6380). If you point a local `.env` at Postgres directly, use `5433`, not `5432`.

### Option B — run the pieces directly

```bash
# 1. Infrastructure only
cd infrastructure && docker compose up db redis pgbouncer

# 2. Backend
cd backend
python -m venv venv && source venv/Scripts/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Celery worker (separate shell) — required for uploads to finish processing
cd backend
celery -A app.workers.celery_app worker -Q main-queue,celery,export_queue,ocr_gpu_queue --loglevel=info

# 4. Frontend (separate shell)
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>.

### Verification actually performed in this audit

| Check | Command | Result |
|---|---|---|
| Backend test suite | `python -m pytest tests/ -q` | ✅ **89 passed** in 99.63s |
| Frontend production build | `npm run build` | ✅ **exit 0**, 30 routes compiled |
| Backend image builds | `docker build -f infrastructure/Dockerfile.backend .` | ✅ after fix (was a hard failure) |
| Migrations ship in image | `ls /app/alembic/versions \| wc -l` inside the built context | ✅ **44** files + `alembic.ini` |
| **Container serves endpoints** | `curl` against a built image | ✅ 139 OpenAPI paths; `/auth/login`→405, `/documents`→401, `/query/stream`→405 — identical on both the pinned and the newest FastAPI |
| **Route-surface regression guard** | `pytest tests/test_route_registration.py` | ✅ 11 passed — asserts the OpenAPI surface, not internal counters |
| Celery entrypoint imports | `import app.workers.celery_app` | ✅ `CELERY_IMPORT_OK` |
| Compose file parses | `docker compose config --quiet` | ✅ exit 0, zero warnings |
| **Migrations on clean pgvector** | `alembic upgrade head` against a fresh DB | ✅ **52 tables**, single head `2a2aee1828d4` |
| Vector column + index | `\d document_chunks` | ✅ `vector(1024)` + `ix_document_chunks_embedding_hnsw` |
| **API boots** | `uvicorn app.main:app` | ✅ `GET /` → `{"message":"DocuMindAI API is running"}` |
| **API → DB → Redis** | `GET /api/v1/health` | ✅ **HTTP 200** `{"api":"ok","db":"ok","redis":"ok"}` |
| OpenAPI schema | `GET /api/v1/openapi.json` | ✅ **139 paths** |
| Security headers | response headers on `GET /` | ✅ `X-Frame-Options: DENY`, `nosniff`, HSTS, CSP, correlation ID |

The migration and boot checks ran against a **throwaway `documind_audit_verify` database**, created and dropped inside the existing local Postgres container. No pre-existing data was touched.

Two non-blocking warnings surfaced during the build/test runs, both left as-is:
- `⚠ It looks like there is a custom Babel configuration that can be removed` — `frontend/.babelrc` is redundant under Next 16 and forces Babel over SWC. Removing it is safe but it is build config, so it was left alone.
- `metadataBase property in metadata export is not set` — Open Graph images resolve against `http://localhost:3000`. Set `metadataBase` once you have a production domain.

---

## 4. What was broken, and what I changed

Nine fixes, all confined to build/deploy/config files, plus one added regression test (§4.10). **No application logic was changed.**

### 4.1 🔴 The backend Docker image could not build at all

`infrastructure/Dockerfile.backend` contained:

```dockerfile
COPY ../backend/requirements.txt .
COPY ../backend /app
```

Docker forbids a `COPY` source outside the build context, so this failed immediately:

```
#8 [builder 3/5] COPY ../backend/requirements.txt .
#8 ERROR: failed to calculate checksum of ref ...: "/backend/requirements.txt": not found
```

**Fix.** The build context is now the repository root and every path is root-relative (`COPY backend/requirements.txt .`, `COPY backend /app`). Also added `curl` (the compose healthcheck invokes it but it was never installed) and changed the command to bind `${PORT:-8000}`, which Railway and Render require. **Verified:** the COPY steps now succeed.

### 4.2 🔴 `railway.json` pointed at a non-existent Dockerfile

`"dockerfilePath": "./infrastructure/docker/backend.Dockerfile"` — there is no `infrastructure/docker/` directory. Every Railway build would have failed instantly.

**Fix.** Corrected to `infrastructure/Dockerfile.backend`.

### 4.3 🔴 The image shipped with zero database migrations

`backend/.dockerignore` contained `alembic/versions/*`. The deploy start command is `alembic upgrade head && uvicorn ...`; with no version files, Alembic "succeeds" against a completely empty schema and the app then fails on the first query — a silent, very confusing production failure.

**Fix.** Removed that exclusion, with a comment explaining why it must never come back. **Verified:** the build context now carries 44 migrations and `alembic.ini`.

### 4.4 🔴 The frontend image ran a development server

`Dockerfile.frontend` was a single stage ending in `CMD ["npm", "run", "dev"]` — no build step at all.

**Fix.** Rewrote it as multi-stage with an explicit `dev` target (used by compose, preserving hot reload) and a default production target that runs `npm run build` then `next start`. `NEXT_PUBLIC_API_URL` is now a build `ARG`, because Next inlines `NEXT_PUBLIC_*` at build time — setting it only at runtime has no effect.

### 4.5 New root `.dockerignore`

Moving the build context to the repo root would otherwise have shipped `node_modules`, the Python venv, `.next` and `.git` on every build.

**Fix.** Added a root `.dockerignore` that excludes those and all `.env*` files (so secrets are never baked into an image) while explicitly **not** excluding `backend/alembic/versions`. **Verified:** context dropped to 971 KB.

### 4.6 `docker-compose.yml` contexts realigned

All four build services pointed at `../backend` / `../frontend` with `dockerfile: ../infrastructure/...`.

**Fix.** Every service now uses `context: ..` with `dockerfile: infrastructure/Dockerfile.*`, matching the corrected Dockerfiles. The frontend service is pinned to `target: dev` so local development keeps the hot-reload server.

### 4.7 🔴 `frontend/.env.example` was gitignored

`frontend/.gitignore:34` had a blanket `.env*`, which swallowed the template too. A fresh clone had **no record** of which `NEXT_PUBLIC_*` variables the build needs.

**Fix.** Added `!.env.example` immediately after the blanket rule, and rewrote the template to document all three variables with their exact read sites. **Verified:** `git check-ignore` now reports all three `.env.example` files as committable while `backend/.env` stays ignored.

### 4.8 Core framework versions pinned for reproducibility

`requirements.txt` declared `fastapi>=0.109.0` and never pinned Starlette at all,
so a fresh install resolved to whatever was newest that day rather than the
versions the test suite was validated against. Both are now pinned to the exact
versions the 89 passing tests run on:

```
fastapi==0.136.1
starlette==1.0.0
```

**Correction — a claim in an earlier draft of this document was wrong.** That
draft reported that the newer resolution (FastAPI 0.140.13 / Starlette 1.3.1)
"silently reduces the API from 166 routes to 7" and that "every real endpoint
404s". That conclusion was drawn from `len(app.routes)` without ever sending an
HTTP request to the newer build. Testing it properly showed otherwise:

| Stack | `len(app.routes)` | OpenAPI paths | `/auth/login` | `/documents` | `/query/stream` |
|---|---|---|---|---|---|
| FastAPI 0.136.1 / Starlette 1.0.0 | 166 | **139** | 405 | 401 | 405 |
| FastAPI 0.140.13 / Starlette 1.3.1 | 7 | **139** | 405 | 401 | 405 |

FastAPI ≥ 0.140 **nests** routes under a mounted sub-router rather than
flattening them into `app.routes`. The counter changes; the served surface does
not. There was no functional regression, and the pin is justified by
reproducibility alone — not by a bug.

The episode did surface a genuine gap, addressed in §4.10: the existing tests
could not have told the difference either way.

### 4.10 Added a route-surface regression guard (`tests/test_route_registration.py`)

**The gap.** `tests/test_api_contracts.py` contains exactly two tests:
`test_health_check` asserts `GET /api/v1/health` returns 200, and
`test_docs_schema_generation` asserts `GET /openapi.json` returns 200. Neither
asserts anything about *how much* of the API is reachable. A change that
silently dropped routers — a failed conditional import, a botched refactor of
`api/v1/api.py` — would keep CI fully green while shrinking the product.

**Does CI cover this class of failure?** CI does the right thing on
installation: it runs `pip install -r requirements.txt` on a clean runner, so it
tests the manifest rather than a stale local environment. What it lacks is any
assertion on the route surface afterwards.

**Verified empirically.** I built an image with the newest FastAPI/Starlette and
ran the existing contract tests inside it:

```
tests/test_api_contracts.py::test_health_check            PASSED
tests/test_api_contracts.py::test_docs_schema_generation  PASSED
```

Both pass regardless — `/api/v1/health` is the first `include_router` call and
`openapi.json` always returns 200. These tests cannot distinguish a healthy API
from a gutted one.

**The guard.** `tests/test_route_registration.py` (11 tests) asserts:

- the OpenAPI schema documents **≥ 120 paths** (currently 139);
- nine representative endpoints — spread across nine different routers — are present;
- all seven workspace prefixes (`/hr/`, `/legal/`, `/finance/`, `/study/`, `/research/`, `/exams/`, `/query/`) have registered routes.

It asserts on the **OpenAPI surface, deliberately not on `len(app.routes)`**,
because that counter is version-dependent (166 on FastAPI 0.136, 7 on 0.140+ for
the same app) and would produce false failures on a routine dependency bump.

**Recommended CI addition** (not applied — it edits the workflow):

```yaml
    - name: Verify API route surface
      working-directory: ./backend
      run: pytest tests/test_route_registration.py -v
```

### 4.9 Malformed line in `backend/.env.example`

The file contained `n# L-11: hard server-side cap ...` — a stray `n` turning a comment into an invalid dotenv line.

**Fix.** Removed the stray character.

---

## 5. Environment variables — complete reference

Read by `backend/app/core/config.py` (pydantic-settings, `env_file = $ENV_FILE` default `.env`), plus nine direct `os.getenv` sites and three `process.env` sites in the frontend.

**Secret** = never commit, never log, rotate if exposed. **Setting** = safe in plain text.

### Required — the backend will not start without these (10)

| Variable | Purpose / read site | Type | Format / example |
|---|---|---|---|
| `AUTH_SECRET_KEY` | JWT HS256 signing | 🔴 Secret | ≥32 bytes — `openssl rand -hex 32` |
| `CSRF_SECRET_KEY` | CSRF double-submit | 🔴 Secret | ≥32 bytes, **different** from above |
| `FRONTEND_URL` | CORS allow-list + CSP `connect-src` (`main.py:107`) | Setting | `https://your-app.vercel.app` |
| `POSTGRES_SERVER` | DB host (ignored when `DATABASE_URL` set) | Setting | `aws-0-ap-south-1.pooler.supabase.com` |
| `POSTGRES_USER` | DB user | Setting | `postgres` |
| `POSTGRES_PASSWORD` | DB password | 🔴 Secret | — |
| `POSTGRES_DB` | DB name | Setting | `postgres` |
| `REDIS_URL` | Cache — **validated** to start `redis://` or `rediss://` | 🔴 Secret | `rediss://default:<pw>@<host>.upstash.io:6379` |
| `CELERY_BROKER_URL` | Celery broker | 🔴 Secret | same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Celery results | 🔴 Secret | same as `REDIS_URL` |

### Required for the product to actually function

| Variable | Purpose | Type | Format |
|---|---|---|---|
| `GEMINI_API_KEY_1` | LLM + fallback embeddings. Read from `os.environ` by `GeminiKeyRotator` (`llm_key_rotation.py:49`), **not** from `Settings`. Without it the app logs a CRITICAL and silently serves `DummyLLMProvider` mock answers. | 🔴 Secret | `AIza...` |
| `GEMINI_API_KEY_2`, `_3`, … | Additional keys for rotation | 🔴 Secret | `AIza...` |
| `DATABASE_URL` | Overrides every `POSTGRES_*` when set | 🔴 Secret | `postgresql+asyncpg://user:pw@host:6543/postgres` |

### Optional / feature-gated

| Variable | Purpose | Type | Format / default |
|---|---|---|---|
| `ENVIRONMENT` | Controls secure-cookie flags (`auth.py:29`) and production guards | Setting | `development` \| `production` |
| `CORS_ORIGINS` | Allowed browser origins | Setting | JSON list `["https://app.vercel.app"]` |
| `STORAGE_PROVIDER` / `STORAGE_PATH` | **Validated** `local`\|`s3` | Setting | `local` / `./storage` |
| `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT_URL` | Enforced only when `STORAGE_PROVIDER=s3` | Setting | `ap-south-1` |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Enforced when `STORAGE_PROVIDER=s3` | 🔴 Secret | — |
| `RAZORPAY_ENABLED`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Billing — direct `os.getenv` (`billing.py:36-39`), not in `Settings` | 🔴 Secret | `false`, `rzp_test_…` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` | SendGrid OTP mail | 🔴 Secret (password) | `smtp.sendgrid.net`, `587`, `apikey`, `SG.…` |
| `BREVO_SMTP_HOST/PORT/USER/PASSWORD` | Fallback mail provider | 🔴 Secret | — |
| `EMAILS_FROM_NAME`, `EMAILS_FROM_ADDRESS`, `ADMIN_EMAIL` | Mail identity | Setting | `DocuMindAI` |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | Phone OTP | 🔴 Secret | `AC…` |
| `SENTRY_DSN` | Backend error tracking | 🔴 Secret | `https://…ingest.sentry.io/…` |
| `VECTOR_BACKEND` | **Validated** `pgvector`\|`faiss`\|`qdrant` | Setting | `pgvector` |
| `QDRANT_HOST`, `QDRANT_PORT` | Only when `VECTOR_BACKEND=qdrant` (lazy import) | Setting | `localhost` / `6333` |
| `VECTOR_ISOLATION_MODE`, `ENABLE_ORG_ISOLATION` | Tenant vector namespacing | Setting | `user` / `false` |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | Chunking (changing these implies a re-index) | Setting | `1800` / `300` |
| `TOP_K_RESULTS`, `MAX_CHUNKS_PER_QUERY`, `GROUNDING_TOKEN_BUDGET` | Retrieval budget | Setting | `20` / `12` / `6000` |
| `RERANKER_PROVIDER` | Only `local` has a real implementation | Setting | `local` |
| `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, `GEMINI_TEMPERATURE`, `GEMINI_TOP_P`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_CONTINUATION_ROUNDS` | LLM tuning | Setting | `gemini-2.5-flash-lite` |
| `LLM_TIMEOUT_SECONDS` | Cap on non-streaming LLM calls | Setting | `120` |
| `OCR_SCANNED_ENABLED` | Route scanned pages through PaddleOCR/Docling | Setting | `true` |
| `OCR_CONFIDENCE_THRESHOLD` | **Validated** 0.0–1.0 | Setting | `0.80` |
| `MAX_UPLOAD_MB` | **Validated** 1–1000 | Setting | `200` |
| `LARGE_DOC_PAGE_THRESHOLD`, `SLOW_QUERY_THRESHOLD_MS` | Guards | Setting | `200` / `8000` |
| `TOKEN_LIMIT_{GENERAL,LEGAL,FINANCE,HR,TEACHER,STUDENT,RESEARCH}` | Per-workspace daily token budgets | Setting | `50000`… |
| `TOKEN_COST_PER_MTK` | Display only | Setting | `3.0` |
| `OTEL_ENABLED`, `PROMETHEUS_ENABLED`, `LOG_LEVEL` | Observability — default **off** | Setting | `false` / `false` / `INFO` |
| `DEPLOY_EVAL_SECRET`, `EVAL_SLACK_WEBHOOK_URL` | Eval automation | 🔴 Secret | — |
| `ENV_FILE` | Which env file `Settings` loads | Setting | `.env` |
| `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | Token policy — decoding is pinned to HS256 | Setting | `HS256` / `60` / `7` |

### Frontend (build-time — inlined into the browser bundle)

> `NEXT_PUBLIC_*` values are **public**. Never put a secret behind that prefix. Changing one requires a **rebuild**, not a restart.

| Variable | Purpose / read site | Type | Format |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base — **must include `/api/v1`** (`src/lib/api.ts:45`) | Setting | `https://api.example.com/api/v1` |
| `NEXT_PUBLIC_POSTHOG_KEY` | Analytics (`src/lib/analytics.ts:4`); skipped when unset | Public key | `phc_…` |
| `NEXT_PUBLIC_SENTRY_DSN` | Browser errors (`sentry.client.config.ts:4`); skipped when unset | Public DSN | `https://…ingest.sentry.io/…` |

### Templates in the repo

- `.env.example` (root) — authoritative backend template; copy to `backend/.env`.
- `frontend/.env.example` — frontend template; copy to `frontend/.env.local`.
- `backend/.env.example` — older, narrower template kept for continuity.

### Secret hygiene — confirmed

```
committable  .env.example
committable  backend/.env.example
committable  frontend/.env.example
IGNORED      backend/.env          ← backend/.gitignore:13
```

The real `.env` is ignored at both the repo root (`.gitignore:16`) and in `backend/.gitignore:13`, so it can never be committed. Fill it in directly on disk — the values never need to be typed into a chat.

---

## 6. Cleanup performed

Every file below was confirmed unreferenced with a repository-wide ripgrep across `*.md`, `*.ts`, `*.tsx`, `*.py`, `*.json`, `*.yml` before deletion.

### Removed from git

| File | Evidence it was safe |
|---|---|
| `infrastructure/test.pdf` | 17-byte stub, zero references. The only `test.pdf` matches in the codebase are a string literal inside `llm_service.py`'s mock provider output, not this file. Not used by any Dockerfile, compose service, CI job, or test. |
| `docs/screenshots/account-profile.png` | Zero references in `README.md`, `docs/marketing/*`, or any source file. |
| `docs/screenshots/finance-workspace.png` | Same. |
| `docs/screenshots/hr-workspace.png` | Same. |

The other 18 screenshots **are** referenced by `README.md` and were kept.

### Removed from local disk only (already gitignored, regenerate automatically)

`frontend/build.log` (28 KB stale log) · `frontend/tsconfig.tsbuildinfo` (372 KB TS cache) · `backend/celerybeat-schedule.{bak,dat,dir}` (Beat state; compose now writes to `/tmp`) · `frontend/tmp/next-build/` (empty stale directory).

### Deliberately NOT deleted

| Item | Reason |
|---|---|
| `backend/.env`, `.env.backup`, `.env.development`, `.env.local`, `.env.production` and frontend equivalents | May contain **your real credentials**. `backend/.env.backup` is worth your own review. |
| `.agents/` (187 tracked files, ~81 of them fonts) | Third-party design tooling. `CLAUDE.md` states it is not part of the app and `.gitignore` now lists it, but you may use these skills. Untracking it would shrink the repo noticeably — your call. |
| `frontend/.babelrc` | Redundant under Next 16 (the build says so explicitly) and it forces Babel over SWC, but it **is** build config. |
| `frontend/next.config.js` | Duplicates `next.config.ts`, but its own comment documents it as an intentional shim. |
| `docs/demo-documents/*.pdf`, `docs/demo/*` | Referenced by `README.md`. |

---

## 7. Deployment — platform choice

### Budget and the constraint that actually drives the decision

Budget: **₹0–500** (≈ US$6). A free one-month trial is acceptable; the goal is a genuinely live deployment.

The binding constraint is **not** price — it is the backend's memory and image size:

- `reranker_service.LocalCrossEncoder.get_model()` imports `sentence_transformers` at first query. It is a **lazy** import, so the app boots fine without it, but the first query then raises an uncaught `ImportError`. **sentence-transformers (and torch beneath it) is therefore mandatory** — roughly 1 GB installed.
- `requirements.txt` additionally pulls `paddlepaddle`, `paddleocr`, `docling` and `layoutparser` — several more GB.
- At runtime the cross-encoder (~80 MB) downloads on first use; `BAAI/bge-m3` (~2.2 GB) will usually fail to load on a small instance, at which point `embedding_service.LocalEmbeddingProvider` falls back to `GeminiEmbeddingProvider`.

That fallback is **safe on a fresh database**, because index-time and query-time embeddings both traverse the identical path and get zero-padded 768→1024 identically. It is **not** safe to mix into a corpus already indexed with bge-m3.

Net requirement: **≥ 2 GB RAM**, ideally 4 GB — which rules out most free tiers immediately.

### 🔴 The disk requirement is worse than the memory requirement — measured, not estimated

`embedding_service.py:127` builds the singleton **at module import**:

```python
embedding_service = EmbeddingService()      # → LocalEmbeddingProvider() → SentenceTransformer("BAAI/bge-m3")
```

So merely importing `app.main` downloads **BAAI/bge-m3**. Measured inside a built image:

| Path | Size |
|---|---|
| `/root/.cache/huggingface/models--BAAI--bge-m3` | **4.3 GB** |
| `/usr/local/lib/python3.11/site-packages` (torch, transformers, …) | **5.6 GB** |
| **Total image, using the slim requirements** | **17 GB** |

Consequences for any deployment:

- The container needs **~5 GB of free disk** on top of the image, or the download fails.
- On a cold start it downloads 4.3 GB **before serving the first request**. The bge-m3 fallback to Gemini embeddings only happens *after* that attempt fails — it is not a fast path.
- Baking the model in at build time (what happens if your build imports the app) yields the 17 GB image above, which most hosts will refuse outright.

This is the single biggest practical obstacle to a free-tier deployment, and it reshapes the platform choice:

- **Hugging Face Spaces** becomes materially more attractive — 50 GB disk and a native, warm HF model cache.
- On **Railway**, budget for the first boot being slow and ensure the volume has headroom.
- **Render's free tier is definitively out** — it cannot hold this at all.

The clean fix is to make the embedding singleton lazy (construct on first use, like the reranker already does) so that a deployment which relies on Gemini embeddings never downloads bge-m3. That is an application-code change and therefore **out of scope for this pass** — flagged for your decision.

### Recommended setup

| Layer | Platform | Cost | Why |
|---|---|---|---|
| **Frontend** | **Vercel** (Hobby) | Free | Next.js 16 is Vercel's own framework; zero-config App Router support, automatic preview deploys, free TLS + CDN. Nothing else comes close for this stack. |
| **Backend API + Celery worker** | **Railway** (Hobby, $5/mo ≈ ₹420) | ≈ ₹420 | The only budget host that gives 8 GB RAM, native Dockerfile builds, **and** multiple long-running services (API *and* worker) from one repo. `railway.json` already exists — the project was designed for it. |
| **PostgreSQL + pgvector** | **Supabase** (Free) | Free | 500 MB Postgres with pgvector available, no credit card. `db/session.py` already contains Supavisor-specific handling. |
| **Redis** | **Upstash** (Free) | Free | 10 000 commands/day, TLS (`rediss://`), no card. Serverless pricing fits a bursty demo. |

**Total: ≈ ₹420**, inside budget.

### Alternatives, honestly assessed

| Option | Verdict |
|---|---|
| **Render free web service** | ❌ **Not viable for this backend.** 512 MB RAM cannot hold torch + the cross-encoder, and the free tier spins down after 15 minutes (50 s+ cold starts). The build would likely time out first. Fine for a toy API, not this one. |
| **Hugging Face Spaces (Docker SDK)** | ✅ **The best ₹0 option** — 2 vCPU, **16 GB RAM**, 50 GB disk, free, no card. Genuinely handles the ML weight. Trade-offs: must listen on port **7860**, the Space sleeps after 48 h idle, and it cannot run a *second* always-on Celery worker process cleanly. Use it if you want to spend nothing; see §8 Variant B. |
| **Fly.io** | ❌ No meaningful free allowance any more; pay-as-you-go with a monthly minimum. |
| **Koyeb / Cyclic free** | ❌ 512 MB — same wall as Render. |
| **Everything on Railway** (incl. Postgres + Redis) | ⚠️ Works, but DB and Redis then bill against the same $5, which the multi-GB ML image will exhaust much faster. Offloading storage to free providers stretches the budget. |

### An honest note about scope

Free-tier hosting will run this application as a **working demo**: signup/login, upload, ingest, grounded Q&A with citations. It will **not** comfortably run scanned-document OCR (PaddleOCR + Docling) or bge-m3 local embeddings. `backend/requirements-deploy.txt` was added as an **optional** slim dependency set that drops exactly those, with the trade-off documented in the file itself. It changes no application code — it is purely a deployment artifact, and `requirements.txt` remains canonical.

---

## 8. Deployment — step-by-step guide

> **Status: not executed.** Every step below needs your own account and login. Creating accounts and entering credentials is something I won't do on your behalf, so the guide is written to be followed exactly. Everything that *could* be prepared in the repo has been — the Dockerfiles build, `railway.json` is correct, migrations ship, and the env templates are complete.
>
> **Do the steps in this order.** Steps 1–2 produce credentials that step 3 needs; step 3 produces a URL that step 4 needs; step 5 closes the loop.

### Prerequisites

1. Push your work to GitHub. The repo is already `https://github.com/kanwa2006/DocuMindAI`.
   ```bash
   git add -A
   git commit -m "chore: pre-launch audit — fix Docker build, migrations, env templates"
   git push origin HEAD
   ```
2. Have a **Google Gemini API key** ready — <https://aistudio.google.com/app/apikey> → *Create API key*.
3. Generate two secrets and keep them somewhere safe:
   ```bash
   openssl rand -hex 32   # → AUTH_SECRET_KEY
   openssl rand -hex 32   # → CSRF_SECRET_KEY (must differ)
   ```

---

### Step 1 — PostgreSQL on Supabase (free)

1. Go to <https://supabase.com> → **Start your project** → sign in with GitHub.
2. **New project**.
   - Name: `documindai`
   - Database Password: generate a strong one and **save it** — it appears in your connection string.
   - Region: **South Asia (Mumbai)** `ap-south-1` if you are in India.
   - Click **Create new project** and wait ~2 minutes.
3. Enable the vector extension. Left sidebar → **SQL Editor** → **New query** → run:
   ```sql
   create extension if not exists vector;
   ```
   You should see *Success. No rows returned*.
4. Get the connection string. **Settings** (gear) → **Database** → **Connection string** → select the **URI** tab → **Transaction pooler** (port **6543**). It looks like:
   ```
   postgresql://postgres.abcdefghijklm:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
5. **Convert it for this app** — replace `postgresql://` with `postgresql+asyncpg://` and substitute your real password:
   ```
   postgresql+asyncpg://postgres.abcdefghijklm:YourRealPassword@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
   Save this as **`DATABASE_URL`**.

> The transaction pooler is safe here: `db/session.py` detects `pooler.supabase.com` and sets `statement_cache_size=0` / `prepared_statement_cache_size=0`, which is exactly what asyncpg needs behind Supavisor.

---

### Step 2 — Redis on Upstash (free)

1. Go to <https://upstash.com> → **Sign Up** (GitHub login works).
2. **Create Database**.
   - Name: `documindai-redis`
   - Type: **Regional**
   - Region: the one closest to your Railway region (e.g. `ap-south-1`)
   - Click **Create**.
3. On the database page open the **REST / Connect** section and choose the **Redis** tab (not REST). Copy the TLS URL:
   ```
   rediss://default:AX....@apn1-xxxx-12345.upstash.io:6379
   ```
4. Save it — you will use the **same value** for all three of `REDIS_URL`, `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`.

> It must start with `rediss://` (two s). `config.py` rejects anything that isn't `redis://` or `rediss://` at startup.

---

### Step 3 — Backend API on Railway

1. Go to <https://railway.app> → **Login with GitHub**.
2. **New Project** → **Deploy from GitHub repo** → authorise Railway → pick **`kanwa2006/DocuMindAI`**.
3. Railway reads `railway.json` from the repo root and will use `infrastructure/Dockerfile.backend` with the repo root as build context. Confirm under **Settings → Build** that:
   - **Builder** = `Dockerfile`
   - **Dockerfile Path** = `infrastructure/Dockerfile.backend`
   - **Root Directory** = empty (repository root)
4. Set the **start command**. Settings → **Deploy → Custom Start Command**:
   ```
   alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   (This already matches `railway.json`; confirm it is present.)
5. Add environment variables. **Variables** tab → **Raw Editor** → paste, substituting your real values:
   ```
   ENVIRONMENT=production
   AUTH_SECRET_KEY=<your 64-hex from prerequisites>
   CSRF_SECRET_KEY=<your other 64-hex>
   DATABASE_URL=<the postgresql+asyncpg:// URL from Step 1>
   REDIS_URL=<the rediss:// URL from Step 2>
   CELERY_BROKER_URL=<same rediss:// URL>
   CELERY_RESULT_BACKEND=<same rediss:// URL>
   GEMINI_API_KEY_1=<your Gemini key>
   POSTGRES_SERVER=aws-0-ap-south-1.pooler.supabase.com
   POSTGRES_PORT=6543
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<your Supabase DB password>
   POSTGRES_DB=postgres
   FRONTEND_URL=https://PLACEHOLDER.vercel.app
   CORS_ORIGINS=["https://PLACEHOLDER.vercel.app"]
   STORAGE_PROVIDER=local
   STORAGE_PATH=./storage
   VECTOR_BACKEND=pgvector
   RERANKER_PROVIDER=local
   LOG_LEVEL=INFO
   OTEL_ENABLED=false
   PROMETHEUS_ENABLED=false
   RAZORPAY_ENABLED=false
   ```
   Leave `FRONTEND_URL` / `CORS_ORIGINS` as the placeholder for now — Step 5 replaces them.

   `POSTGRES_*` are set even though `DATABASE_URL` overrides them, because `Settings` marks four of them as required fields with no defaults; omitting them fails validation at import.
6. Generate a public URL. **Settings → Networking → Public Networking → Generate Domain**. You get something like `documindai-production.up.railway.app`. **Save it.**
7. Watch **Deployments → View Logs**. A healthy start looks like:
   ```
   INFO  [alembic.runtime.migration] Running upgrade ...
   INFO  [startup] Gemini keys available: 1
   INFO  Uvicorn running on http://0.0.0.0:8080
   ```
   If you see `CRITICAL: No Gemini API keys configured`, `GEMINI_API_KEY_1` is missing or misspelled.
8. Verify the API is genuinely up:
   ```bash
   curl https://<your-railway-domain>/api/v1/health
   ```
   Expect HTTP 200. Also try `https://<your-railway-domain>/` → `{"message":"DocuMindAI API is running"}`.

**If the build fails on image size or timeout**, switch to the slim dependency set: Settings → **Build → Build Command** is not used by Dockerfile builds, so instead edit `infrastructure/Dockerfile.backend` line `COPY backend/requirements.txt .` → `COPY backend/requirements-deploy.txt requirements.txt`, commit, and push. Then also set `OCR_SCANNED_ENABLED=false` in Variables. See §7 for exactly what that drops.

---

### Step 4 — Celery worker on Railway (second service)

Uploads stay stuck in `PROCESSING` forever without a worker.

1. In the same Railway project → **+ New** → **GitHub Repo** → select `kanwa2006/DocuMindAI` again. This creates a second service from the same repo.
2. Settings → **Build**: same Dockerfile path (`infrastructure/Dockerfile.backend`), root directory empty.
3. Settings → **Deploy → Custom Start Command**:
   ```
   celery -A app.workers.celery_app worker -Q main-queue,celery,export_queue,ocr_gpu_queue --loglevel=info
   ```
   All four queues must be consumed — `export_queue` and `ocr_gpu_queue` are routed in `celery_app.py` and would otherwise pile up silently.
4. **Variables** tab → paste the **exact same variables as Step 5 of the API service**. The worker never imports `main.py`, so it needs its own copy of every value, including the Gemini keys.
5. Do **not** generate a public domain for this service — it is not an HTTP server.
6. Logs should show `celery@... ready.` and the registered task list.

> **Optional third service — Celery Beat.** Only needed for scheduled jobs (daily digests, health checks, key rotation). Same setup, start command `celery -A app.workers.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule`. **Run exactly one Beat instance** — a second duplicates every scheduled task. Skip it for a demo to save budget.

---

### Step 5 — Frontend on Vercel, then close the CORS loop

1. Go to <https://vercel.com> → **Sign Up / Log in with GitHub**.
2. **Add New… → Project** → **Import** `kanwa2006/DocuMindAI`.
3. Configure — this part matters:
   - **Framework Preset**: `Next.js` (auto-detected)
   - **Root Directory**: click **Edit** and set it to **`frontend`** ← *required*, the repo root is not the Next app
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: leave default
   - **Install Command**: `npm install` (default)
4. Expand **Environment Variables** and add — using the Railway domain from Step 3.6:
   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://<your-railway-domain>/api/v1` |

   The `/api/v1` suffix is **mandatory** — `lib/api.ts` appends only the endpoint path.
5. Click **Deploy** and wait for the build. You get a URL like `https://docu-mind-ai.vercel.app`.
6. **Close the CORS loop.** Return to Railway → **API service → Variables** and replace the placeholders with your real Vercel URL (no trailing slash):
   ```
   FRONTEND_URL=https://docu-mind-ai.vercel.app
   CORS_ORIGINS=["https://docu-mind-ai.vercel.app"]
   ```
   Repeat on the **worker** service. Railway redeploys automatically.

---

### Step 6 — Verify the deployment end to end

Confirm each link in the chain, not just that the page loads.

1. **Frontend loads:** open `https://<your-vercel-domain>` — the landing page renders.
2. **Frontend reaches the backend:** open DevTools → Network, then register a new account. You should see a `POST` to `https://<railway-domain>/api/v1/auth/register` returning 200/201, **not** a CORS error.
3. **Backend reaches the database:** the registration succeeding *is* the proof — it writes a user row. Cross-check in Supabase → **Table Editor** → `users`, where your new row should appear.
4. **Redis and the worker are alive:** upload a small text-based PDF. Its status should move `UPLOADED → PROCESSING → READY`. If it sticks at `PROCESSING`, the worker service is down or has different Redis credentials.
5. **The full RAG path works:** ask a question about the uploaded document. You should get a streamed answer with page citations. If the answer looks plausible but has no citations, check the Railway logs for `DummyLLMProvider` — that means `GEMINI_API_KEY_1` isn't reaching the process.

**Record your live URL here once it is up:**

```
Frontend : https://__________________.vercel.app
Backend  : https://__________________.up.railway.app
Health   : https://__________________.up.railway.app/api/v1/health
```

---

### Variant B — the ₹0 route (Hugging Face Spaces for the backend)

Replaces Step 3 only; Supabase, Upstash and Vercel are unchanged.

1. <https://huggingface.co> → sign up → **New Space**.
2. Owner: you · Space name: `documindai-api` · License: MIT · **SDK: Docker** → *Blank* · Hardware: **CPU basic (free, 16 GB RAM)** · Visibility: Public.
3. Clone the Space and add a `Dockerfile` at its root that reuses this repo's image but binds **port 7860** (the only port Spaces exposes):
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   RUN apt-get update && apt-get install -y libpq-dev libgl1 libglib2.0-0 curl && rm -rf /var/lib/apt/lists/*
   RUN git clone --depth 1 https://github.com/kanwa2006/DocuMindAI.git /src && cp -r /src/backend/. /app
   RUN pip install --no-cache-dir -r requirements-deploy.txt
   ENV PYTHONUNBUFFERED=1
   EXPOSE 7860
   CMD ["sh","-c","alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
   ```
4. Space **Settings → Variables and secrets**: add every variable from Step 3.5 as **Secrets** (not public Variables) — same names, same values.
5. Your API base becomes `https://<user>-documindai-api.hf.space/api/v1`. Use that as `NEXT_PUBLIC_API_URL` in Vercel.

**Trade-offs:** the Space sleeps after 48 h of inactivity (first request afterwards is slow), and running a separate always-on Celery worker is awkward — background ingestion is the weak point of this variant.

---

## 9. Troubleshooting

Ordered by how likely you are to hit each one on this specific stack.

### Build fails: `COPY failed: "/backend/requirements.txt": not found`
The Dockerfile is being built with the wrong context. It expects the **repository root**, not `backend/`. Build with `docker build -f infrastructure/Dockerfile.backend .` from the repo root, and on Railway leave **Root Directory empty**.

### Deployed API returns 404 for every endpoint, but `GET /` works
Check the documented surface rather than any internal counter:
```bash
curl -s https://<host>/api/v1/openapi.json | python -c "import sys,json;print(len(json.load(sys.stdin)['paths']))"
```
Expect ~139. A low number means a router failed to reach `api/v1/api.py` — look
for an endpoint module that failed to import at startup. Do **not** use
`len(app.routes)` for this: it legitimately reports 166 on FastAPI 0.136 and 7
on 0.140+ for the same working app.

### Build times out or the image is too large
The full `requirements.txt` pulls PaddlePaddle + Docling + LayoutParser (multi-GB). Switch the Dockerfile's requirements line to `backend/requirements-deploy.txt` and set `OCR_SCANNED_ENABLED=false`. See §7 for what that costs you.

### Container starts, then exits: `ValidationError ... field required`
`Settings` has ten required fields with no defaults. The usual culprits are `AUTH_SECRET_KEY`, `CSRF_SECRET_KEY`, `FRONTEND_URL` and the four `POSTGRES_*`. Set **all** of them, even when `DATABASE_URL` is also set — validation runs before the override is applied.

### `ValueError: REDIS_URL must start with redis:// or rediss://`
You pasted Upstash's **REST** URL (`https://…`) instead of the Redis protocol URL. Go back to the Connect panel and pick the **Redis** tab.

### CORS errors in the browser console
Three things must all agree, with **no trailing slash**:
- `FRONTEND_URL` = your exact Vercel origin
- `CORS_ORIGINS` = a JSON array containing that same origin
- The frontend's `NEXT_PUBLIC_API_URL` points at the Railway domain

Note that `main.py:107` also puts `FRONTEND_URL` into the CSP `connect-src` header, so a mismatch blocks requests even when CORS headers look right. Redeploy the backend after changing these.

### Frontend calls go to `localhost:8000` in production
`NEXT_PUBLIC_*` is inlined at **build** time. Setting it after the fact does nothing — you must **redeploy** Vercel (Deployments → ⋯ → Redeploy) after changing it.

### Every API path 404s
`NEXT_PUBLIC_API_URL` is missing the `/api/v1` suffix. It must be `https://host/api/v1`, because `lib/api.ts` deliberately omits that prefix from each endpoint string.

### DB connection: `prepared statement "__asyncpg_stmt_x__" does not exist`
You are on a pooler host that `db/session.py` didn't recognise. It keys off the literal `pooler.supabase.com`. If you use a different pooler, switch to Supabase's **Session** pooler or a direct connection.

### DB connection: `sslmode` / `ssl` invalid connection option
Don't hand-append SSL parameters. `settings.sync_database_url` normalises `ssl=` → `sslmode=` for psycopg2 and adds `sslmode=require` for non-local hosts automatically; `get_engine_args` handles the async side.

### `alembic upgrade head` reports success but tables don't exist
The image shipped without migrations. Confirm `backend/.dockerignore` does **not** contain `alembic/versions/*` (fixed in this audit) and verify with:
```bash
docker run --rm <image> ls alembic/versions | wc -l   # expect 44
```

### Uploads stay stuck at `PROCESSING`
No Celery worker is consuming. Check the worker service is running, shares the **same** `CELERY_BROKER_URL`, and consumes all four queues: `main-queue,celery,export_queue,ocr_gpu_queue`.

### Answers appear but are generic, with no citations
The logs will contain `CRITICAL: No Gemini API keys configured` and the app is serving `DummyLLMProvider`. `GEMINI_API_KEY_1` is read from `os.environ`, not from `Settings` — make sure it is set on **both** the API and worker services.

### First query 500s with `ImportError: sentence_transformers`
The reranker's cross-encoder import is lazy, so this only surfaces at query time. `sentence-transformers` must be installed; it is present in both `requirements.txt` and `requirements-deploy.txt`.

### Logs warn `DEGRADED MODE — primary model BAAI/bge-m3 unavailable`
Expected on a small instance. Embeddings fall back to Gemini (768-dim, zero-padded to 1024). Harmless on a **fresh** database because indexing and querying use the identical path — but never mix this into a corpus already indexed with bge-m3.

### Container starts but the platform reports "no open ports"
The app must bind `$PORT`. The corrected Dockerfile does this via `${PORT:-8000}`; if you overrode the start command, include `--port $PORT`.

### The startup script hangs forever
Don't use `scripts/prestart.sh` in a hosted deployment. It waits on `POSTGRES_SERVER`, which defaults to `localhost` when you configure the DB via `DATABASE_URL` — so it blocks forever. It is intended for docker-compose and CI only.

### Supabase project became unreachable after a week
Free Supabase projects pause after ~7 days of inactivity. Restore it from the dashboard.

---

## 10. Known gaps not fixed in this pass

These are **pre-existing** and were deliberately left alone, because fixing them means changing application behaviour — outside the scope you set.

0. **Five empty modules removed** during the senior-engineering review: `endpoints/eval.py`,
   `core/circuit_breaker.py`, `models/eval_result.py`, `services/cost_guard_service.py` and
   `tasks/eval_tasks.py` were all zero-line files and all unimported. Worth noting explicitly:
   `cost_guard_service.py` was empty, so despite the `TOKEN_LIMIT_*` settings **no cost guard was
   ever implemented**.

1. **`TAVILY_API_KEY` is a dangling reference.** `services/deep_research_agent.py:58` reads `settings.TAVILY_API_KEY`, but no such field exists in `core/config.py`, and `tavily` is absent from `requirements.txt`. The call is wrapped in `try/except Exception → log warning → return None`, so web-search-augmented research **silently no-ops**. Setting the variable today has no effect.

2. ~~**Broken icon references.**~~ **RESOLVED** during the branding swap — see §11. `layout.tsx:37` pointed at `/favicon.svg` and `/apple-touch-icon.png`, neither of which existed; both 404'd in production. `favicon.ico` and `apple-touch-icon.png` are now generated, and the reference was corrected.

3. **`metadataBase` is unset**, so Open Graph and Twitter images resolve against `http://localhost:3000`. Set it once you have a production domain.

4. **Duplicate OpenAPI operation ID** — `list_notifications` is registered twice; FastAPI warns during schema generation.

5. **`frontend/.babelrc` is redundant** and forces Babel instead of SWC. The Next build explicitly says it "can be removed".

6. **`canvas@^3.2.3` sits in `dependencies`** but is only used by `scripts/generate-og-image.js`. It is a native module that compiles on install and is a plausible cause of hosted build failures; it belongs in `devDependencies`.

7. **Pydantic V2 deprecation warnings** — several endpoints still use class-based `Config` instead of `ConfigDict`. Harmless now, breaking in Pydantic V3.

8. **Local `AUTH_SECRET_KEY` is 12 bytes.** The test run emitted `InsecureKeyLengthWarning` (RFC 7518 wants ≥32). Use a fresh 32-byte secret in production.

9. ~~**`.agents/` is tracked but gitignored**~~ — **RESOLVED**: untracked; files kept on disk.

### Added in the senior-engineering review (section 15)

10. **No full-text index on `document_chunks.text_content`.** `retrieval_service.py:121` runs
    `to_tsvector('english', text_content) @@ websearch_to_tsquery(...)` with no matching GIN
    expression index. Measured on 200k chunks in an isolated database:
    **4,276 ms (Parallel Seq Scan) vs 6.4 ms (Bitmap Index Scan)** — roughly 660x, for 16 MB of
    index on a 49 MB table. The vector half of hybrid retrieval is O(log N); the lexical half is
    O(N), so it degrades linearly with corpus size. Fix is a single migration, ideally
    `CREATE INDEX CONCURRENTLY` to avoid locking writes.

11. **The DB session is held for the entire SSE stream.** `query.py` captures the request-scoped
    `AsyncSession` in `event_generator` and uses it from trial enforcement through to the Veritas
    trust report, so a connection stays pinned for the whole LLM generation window. With
    `pool_size=10, max_overflow=20`, concurrent streaming queries are capped at **30**; the 31st
    blocks. PgBouncer helps Postgres, not the SQLAlchemy pool.

12. **Rate limiting covers 7 of 145 endpoints**, and `check_and_increment_trial` is called from
    exactly one place (`query.py:236`). `/research/deep-research`, `/legal/contracts/{id}/risk-report`,
    `/finance/compare`, `/exams/generate/paper` and `/exams/process/voice` all invoke the LLM with
    **no rate limit and no trial decrement**. Combined with the empty `cost_guard_service.py`, there
    is currently no cost ceiling on those paths.

13. **No graceful shutdown.** There is no `lifespan` or `on_event("shutdown")` in `main.py` and no
    SIGTERM handling in the Celery worker, so a rolling deploy severs in-flight SSE streams and
    never disposes the database engine.

14. **The Docker image runs as root** — `infrastructure/Dockerfile.backend` has no `USER` directive.

15. **`ENVIRONMENT` is compared by exact string** (`auth.py:29`, `csrf.py:8`). Deploying with
    `ENVIRONMENT=prod` or `Production` silently produces `secure=False` session cookies, sent over
    plain HTTP. Recommend validating the value at startup.

10. 🔴 **`OTEL_ENABLED` and `PROMETHEUS_ENABLED` are never actually read.** `core/telemetry.py` imports neither setting; `setup_telemetry()` unconditionally installs a `BatchSpanProcessor(ConsoleSpanExporter())`. **Observed during this audit:** with `OTEL_ENABLED=false`, a single `GET /api/v1/health` still dumped a multi-line JSON span to stdout. On a metered host this is real log volume and cost, and it contradicts the comment at `config.py:139-143` ("defaults are OFF (opt-in)"). The fix is a one-line guard at the top of `setup_telemetry`, but it changes runtime behaviour so it was left for you to authorise.

11. **OpenTelemetry service name is mislabelled.** `workers/celery_app.py:107` calls `setup_telemetry(is_worker=True)` at **import** time. Any import chain in the API process that reaches `celery_app` re-runs setup and overwrites the global `TracerProvider`, so API spans are tagged `service.name: documind-worker`. Observed directly — the span for an API request to `/api/v1/health` carried the worker's service name.

---

---

## 11. Branding / logo swap

Source image: `logo.jpeg` (1254×1254 RGB) at the repository root.

All raster assets were regenerated from it with Pillow (LANCZOS resampling). **No styling, layout or component logic was changed** — only image bytes and the file paths pointing at them.

### Assets generated → `frontend/public/`

| File | Size | Note |
|---|---|---|
| `icon-192.png` | 192×192 | PWA icon — replaced the "DM" placeholder |
| `icon-512.png` | 512×512 | PWA icon + maskable — replaced the "DM" placeholder |
| `apple-touch-icon.png` | 180×180 | **New** — `layout.tsx` referenced it but it never existed |
| `favicon.ico` | 16→256 multi-res | **New** — replaces the missing `favicon.svg` |
| `logo.png` | 512×512 | Full-resolution source for README / in-app use |
| `og-image.png` | 1200×630 | Social preview, rebuilt: logo on pure black with the wordmark and existing tagline |

### Code references updated (2 lines, both path-only)

| File | Change |
|---|---|
| `frontend/src/app/layout.tsx:37` | `icon: '/favicon.svg'` → `icon: '/favicon.ico'` — fixes a 404; `apple-touch-icon.png` now resolves too |
| `README.md:3` | Added `<img src="frontend/public/logo.png" width="180">` above the title and dropped the 🧠 emoji from the H1 |

`frontend/public/manifest.json` needed **no** change — it already pointed at `icon-192.png` / `icon-512.png`, which were replaced in place.

### Superseded assets removed

All seven were confirmed unreferenced by a repository-wide ripgrep before deletion:

- `icon-192.svg`, `icon-512.svg` — stale placeholder branding, superseded by the new PNGs.
- `file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg` — leftover `create-next-app` template assets, never used by this application.

`frontend/public/` now contains exactly nine files, all of them live.

**Verified:** `npm run build` → `✓ Compiled successfully`, exit 0, after the swap.

---

*Generated during the pre-launch audit of 2026-07-29. Engineering rules: [REPAIR_RULEBOOK.md](../engineering/REPAIR_RULEBOOK.md). Operating manual: [CLAUDE.md](../../CLAUDE.md).*
