# CLAUDE.md — DocuMindAI Project Context

Stable project context: architecture, stack, commands, conventions, constraints, testing, deployment.

**This file contains no status.** For what is done, in flight, or blocked — including the P0 register and release gate — read **[PROGRESS.md](PROGRESS.md)**, the single source of truth for implementation status.

Engineering process is governed by **[docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md](docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md)** — the canonical engineering handbook. Follow it strictly.

---

## Project Identity

- **Name:** DocuMindAI
- **Type:** Multi-tenant, grounded RAG platform over user documents.
- **Core promise:** answers are retrieved from the user's documents, cited to a page, and refused when evidence is absent.
- **Shape:** FastAPI + Celery workers + PostgreSQL/pgvector + Redis + Next.js 16, organized into **seven workspaces** (General, HR, Legal, Finance, Study, Research, Exam).

Users upload PDFs/DOCX/PPTX or paste text "clips." Documents are extracted (PyMuPDF, with PaddleOCR/Docling for scanned pages), chunked, embedded (bge-m3, 1024-dim), and indexed. Queries run hybrid retrieval (vector + lexical, fused by Reciprocal Rank Fusion), cross-encoder reranking, token-budgeted grounding, and Gemini generation, streamed over Server-Sent Events. Billing is trial-to-paid via Razorpay.

---

## Stack

**Backend** — Python 3.11
FastAPI `==0.136.1` · Starlette `==1.0.0` (both **pinned**; read the note in `requirements.txt` before bumping) · SQLAlchemy 2 (async `asyncpg` + sync `psycopg2`) · Alembic (44 migrations) · Celery ≥5.3 + Redis 7 · pgvector · sentence-transformers (bge-m3 + `ms-marco-MiniLM-L-6-v2` cross-encoder) · google-generativeai · PyMuPDF · PaddleOCR/PaddlePaddle/Docling/LayoutParser · passlib + `bcrypt==4.0.1` (pinned — passlib breaks on ≥4.1) · PyJWT · SlowAPI · Razorpay · boto3 · Sentry · OpenTelemetry + prometheus-client

**Frontend** — Node 20
Next.js `16.2.6` (App Router) · React `19.2.4` · TypeScript 5 · Tailwind 4 · @sentry/nextjs · posthog-js · react-pdf · recharts · FingerprintJS

**Data / infra** — PostgreSQL + pgvector (HNSW) · PgBouncer · Redis 7-alpine · Docker Compose · GitHub Actions

---

## Repository Layout

```
backend/app/
  main.py                  # ASGI app + middleware + Sentry + Gemini key bridge
  api/v1/api.py            # router aggregation
  api/v1/endpoints/*       # auth, documents, query, hr, legal, finance, study,
                           #   research, exams, billing, chats, insights, admin, health
  core/*                   # config, auth, security, middleware, rate_limiter, storage,
                           #   workspace, trial_enforcement, gemini_env, telemetry
  services/*               # retrieval, grounding, reranker, embedding, llm_service,
                           #   llm_key_rotation, veritas_engine, ocr_service,
                           #   ocr_orchestrator, deep_research_agent, export_engine, ...
  models/*                 # ~50 tables      schemas/*  # Pydantic
  workers/celery_app.py    # Celery config, includes, task_routes, beat_schedule
  workers/tasks/*          # document/hr/legal/finance/study/research/export/ocr/audio
  tasks/*                  # async report/eval helpers (NOT Celery tasks — see Pitfalls)
  automation/auto_*        # Beat-scheduled jobs
  alembic/versions/*       # 44 migrations
  tests/                   # 27 test files
frontend/src/
  app/*                    # pages; each workspace page = <WorkspaceUI workspaceType=.../>
  components/*             # WorkspaceUI + panels + shared UI
  hooks/*  lib/api.ts  lib/store/*  middleware.ts  styles/*
infrastructure/            # Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
docs/                      # see Documentation Map below
```

`frontend/CLAUDE.md` (→ `AGENTS.md`) carries Next.js-16-specific instructions that apply when editing the frontend.

---

## Commands

### Run the stack (Docker Compose is the supported path)
```bash
cd infrastructure
docker compose -f docker-compose.yml -f docker-compose.local-test-override.yml up -d
```
The override remaps **only** the host Redis port (6380→6381) because a pre-existing
container holds 6380. Container-to-container traffic is unaffected (`redis:6379`).
Drop the override once that container is gone.

Services: frontend `:3000` · backend `:8000` · Postgres `:5433` · PgBouncer `:6432` · Redis `:6381`

### ⚠️ Frontend edits require a container restart
```bash
docker compose restart frontend
```
**Turbopack does not recompile across the Windows → Docker bind mount.** The container
filesystem receives the edit but the dev server keeps serving the old bundle. This has
already caused one multi-hour false negative — a working fix was measured as failing.
Never verify a frontend change without restarting first.

The Next.js dev **error overlay also caches stale errors** — it can display a traceback
for code that has already been deleted. Check the file before believing it.

### Test / verify
```bash
cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q     # backend suite
cd frontend && npx tsc --noEmit                                 # typecheck
cd frontend && npm run build                                    # production build
cd backend && alembic upgrade head                              # migrations
curl http://localhost:8000/api/v1/health                        # {"api","db","redis"}
```

### Seed a dev login
```bash
cd infrastructure && docker compose exec backend python scripts/seed_dev.py
# dev@test.com / devpass123 (admin role)
```

---

## Architecture Invariants

Do not break these accidentally.

- **API base path.** All routes under `/api/v1`. `NEXT_PUBLIC_API_URL` already includes it; endpoint strings in `lib/api.ts` start with `/` and **omit** `/api/v1`.
- **Workspace identity.** `core/workspace.resolve_workspace_id()` is the single derivation: `uuid5(NAMESPACE_DNS, slug.lower())`. It is one-way — you cannot recover the slug from the UUID; store the slug at write time.
- **RAG pipeline.** `grounding_service` → `retrieval_service` (pgvector ANN **or** in-memory NumPy per `VECTOR_BACKEND`) + lexical FTS → RRF → `reranker_service` → token budget → `llm_service` (Gemini, key rotation) → SSE.
- **Extract-then-compute.** The LLM extracts fields; **Python computes every number** — all 15 finance ratios, legal escalation, citation formatting. Preserve this; it is why figures cannot be hallucinated.
- **Async API / sync workers.** FastAPI + `asyncpg` on the request path; Celery uses `SyncSessionLocal` (psycopg2). Never mix. Blocking model/LLM calls are offloaded via `run_in_executor`.
- **Tenant filters.** Every workspace query filters on `owner_id` **and** the workspace UUID.
- **SSE event names** must stay in lockstep between client and server: `trial_status`, `thinking_stage`, `status`, `metadata`, `token`, `error`, `done`, `trust_report`.
- **Worker three-way rule.** A task must be in `celery_app.include` **and** routed in `task_routes` **and** have its queue consumed by a running `-Q`.
- **Auth.** HS256-only JWT decoding, httponly + `samesite=strict` cookies, CSRF double-submit, device fingerprint, per-tenant vector namespaces, Postgres RLS.
- **Loud degradation.** Never introduce a silent fallback (zero vectors, fabricated rerank scores, mock answers presented as real). Failures must be visible.

---

## Files Needing Extra Care

Per `docs/engineering/REPAIR_RULEBOOK.md` §8a — changes here need an authorizing task, a minimal diff, and full regression:

- `services/llm_service.py`, `services/llm_key_rotation.py` — concurrency-sensitive; shared key state
- `services/retrieval_service.py`, `grounding_service.py`, `chunking_service.py` — power every grounded answer; chunking changes imply a re-index
- `workers/celery_app.py` — the three-way rule
- `core/config.py`, `core/auth.py`, `core/middleware.py` — high blast radius
- `frontend/src/lib/api.ts`, `components/WorkspaceUI.tsx` — API contract / all workspaces

---

## Common Pitfalls

1. **Verifying a frontend change without `docker compose restart frontend`** (see Commands).
2. **Trusting the Next.js dev error overlay** — it caches errors from deleted code.
3. Re-introducing a manual `/api/v1` prefix in frontend calls.
4. Trying to reverse a `uuid5` workspace id back to a slug — impossible.
5. Adding a `task_route` for a nonexistent module, or a queue with no consumer.
6. `app/tasks/` vs `app/workers/tasks/` are **two different packages**. The former holds plain async helpers (`report_tasks`, `eval_tasks`); the latter holds real Celery tasks. `app/tasks/` has no `__init__.py` (namespace package).
7. Reusing a helper whose semantics don't match — e.g. marking a model-capability gap as a rate limit would poison a healthy API key.
8. Assuming a fix works because the happy path passes. Force the failure path.
9. Committing build artifacts (`.next/`, `celerybeat-schedule.*`, `.playwright-mcp/`).

---

## Configuration

Settings load via pydantic-settings in `core/config.py` from `$ENV_FILE` (default `backend/.env`).

- **10 fields are required with no defaults** — `AUTH_SECRET_KEY`, `CSRF_SECRET_KEY`, `FRONTEND_URL`, `POSTGRES_SERVER/USER/PASSWORD/DB`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`. Set all of them even when `DATABASE_URL` is also set — validation runs before the override applies.
- **`DATABASE_URL` overrides every `POSTGRES_*` field.** When it targets Supabase, the local PgBouncer container is bypassed by design — Supabase's own Supavisor pooler is the pooler. `db/session.py` detects `pooler.supabase.com` and disables asyncpg's prepared-statement cache accordingly.
- **Gemini keys** are read from `os.environ` by `GeminiKeyRotator`, **not** from `Settings`. Without `GEMINI_API_KEY_1` the app logs CRITICAL and serves `DummyLLMProvider` mock answers.
- Some declared settings are **inert** (declared but never read) and are marked `# INERT` in `.env.example`. Don't assume a setting works because it exists.
- Full variable reference: `docs/deployment/PROJECT_AUDIT_AND_DEPLOYMENT.md` §5.

**Never** read, edit, or commit real `.env*` contents. Confirm gitignore status only.

---

## Documentation Map

| Document | Use for |
|---|---|
| **[PROGRESS.md](PROGRESS.md)** | **Current status, P0 register, release gate** |
| [docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md](docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md) | **Engineering process — canonical handbook** |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | Subsystems, pipelines, flows |
| [docs/architecture/DEPENDENCY_GRAPH.md](docs/architecture/DEPENDENCY_GRAPH.md) | Import graph, change-impact matrix, env table |
| [docs/architecture/WORKSPACES.md](docs/architecture/WORKSPACES.md) | Per-workspace deep dives |
| [docs/architecture/API_AUDIT.md](docs/architecture/API_AUDIT.md) | Endpoint inventory, frontend↔backend contract |
| [docs/engineering/REPAIR_RULEBOOK.md](docs/engineering/REPAIR_RULEBOOK.md) | Binding engineering rules, care levels |
| [docs/deployment/PROJECT_AUDIT_AND_DEPLOYMENT.md](docs/deployment/PROJECT_AUDIT_AND_DEPLOYMENT.md) | Env reference, platform comparison, deployment steps, troubleshooting |
| [docs/deployment/MANUAL_TESTING_GUIDE.md](docs/deployment/MANUAL_TESTING_GUIDE.md) | QA plan (§3.1–§3.7 + Part 4) |
| `docs/audit/*`, `docs/engineering/DEBUG_MASTER_PLAN.md` | Point-in-time history of a **completed** repair phase. Engineering context, **not** current state. |

---

## Engineering Organization

Ten specialists live in [`.claude/agents/`](.claude/agents/). Each carries this project's
real failure history, not generic advice. They **verify, review, and diagnose — they do not
implement.** Root-causing a bug, choosing an ownership boundary, and writing the fix stay in
the main engineering thread.

There is no orchestrator and **no agent can invoke another** — each runs in an isolated
context and reports back to the thread that called it. This table is the delegation policy.

| Situation | Delegate to |
|---|---|
| Starting a new session or phase | `docs-sync-checker` |
| A fix is ready for verification | `test-runner` |
| Reviewing a diff generally | `code-reviewer` |
| About to commit a change touching auth, uploads, or cross-tenant data | `security-reviewer` |
| Changed a service's start command, flags, or env | `infra-health-checker` |
| A RAG answer is wrong or slow, cause unclear | `rag-pipeline-tracer` |
| Before claiming a workspace feature works | `workspace-qa` |
| Before claiming a performance win | `performance-profiler` |
| Before claiming deployment-ready | `release-readiness-checker` |
| Redesigning response formatting | `response-quality-reviewer` |

**Ownership is exclusive.** Where two could plausibly answer the same question, the boundary is:

- `rag-pipeline-tracer` says *which stage*; `performance-profiler` says *how much it costs and whether it's worth fixing*.
- `infra-health-checker` verifies **runtime, now**; `release-readiness-checker` verifies the **artifact, before deploy**.
- `release-readiness-checker` **detects** an exposed secret; `security-reviewer` **adjudicates** its severity.
- `test-runner` reports suite results; **suite-green is not process-healthy** — that's `infra-health-checker`.
- `response-quality-reviewer` owns presentation; anything touching retrieval, prompts, citation derivation, or trust-score computation is substance, not presentation.

**Subagents start cold.** Nothing carries over — the invoking prompt must include every file
path, diff, error message, and prior decision the agent needs. Each agent file lists its
required inputs.

Every agent returns the same 10-section contract (Summary · Evidence · Findings · Root Cause ·
Risks · Recommendations · Confidence · Escalation · Files Reviewed · Additional Verification
Needed), and tags each blocker **agent-actionable** / **owner-access-required** /
**owner-decision-required**.

Editing an agent file requires a session restart to take effect. Don't add an eleventh agent
without an observed recurring responsibility that none of these ten covers.

---

## Severity Definitions

- **P0** — blocks deploy, causes data loss, or is a live security exposure
- **P1** — breaks a core workflow with no workaround
- **P2** — quality/UX issue with a workaround

## Out of Scope

- Retrieval/RAG algorithm changes (working — do not touch without evidence)
- Prompt content changes (directive Phase 8 only)
- Rewriting published git history (requires explicit approval)
- `backend/.env` contents beyond confirming gitignore status

## Deployment Target

Not yet deployed. Candidate: Vercel (frontend) + Railway (API + worker) + Supabase (DB) + Upstash (Redis). Current deployment blockers are tracked in `PROGRESS.md`.

---

*Stable context only. Status lives in [PROGRESS.md](PROGRESS.md); process lives in [the directive](docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md).*
