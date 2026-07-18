# CLAUDE.md — DocuMindAI Operating Manual

This is the permanent operating manual for Claude Code sessions in this repository. It is not a README, user guide, or marketing document. Treat every rule here as binding. The governing engineering rules live in [REPAIR_RULEBOOK.md](REPAIR_RULEBOOK.md); this file tells you how to run a session.

---

## Project Identity

- **Name:** DocuMindAI
- **Type:** Full-stack, multi-tenant, grounded RAG platform over user documents.
- **Core promise:** answers are retrieved from the user's documents, cited to a page, and refuse when evidence is absent.
- **Shape:** FastAPI backend + Celery workers + PostgreSQL/pgvector + Redis + Next.js 16 frontend, organized into **seven workspaces** (General, HR, Legal, Finance, Study, Research, Exam).

## Project Overview

Users upload PDFs/DOCX/PPTX or paste text "clips." Documents are extracted (PyMuPDF), chunked, embedded (bge-m3, 1024-dim), and indexed. Queries run hybrid retrieval (vector + lexical, fused by Reciprocal Rank Fusion), cross-encoder reranking, token-budgeted grounding, and Gemini generation, streamed to the browser over Server-Sent Events. Each workspace adds domain models, endpoints, Celery tasks, and prompts. Billing is trial-to-paid via Razorpay.

The project **works in parts and is broken in parts**. Several headline features are partially wired, mislabeled, or dead on the default configuration. Do not assume a feature works because a document says so — verify.

## Current Architecture (invariants — do not break by accident)

- **API base:** all routes under `/api/v1`. Frontend `NEXT_PUBLIC_API_URL` already includes it; `apiFetch` prepends it. Endpoints in `lib/api.ts` start with `/` and **omit** `/api/v1`.
- **Workspace identity:** `core/workspace.resolve_workspace_id()` maps a slug → `uuid5(NAMESPACE_DNS, slug.lower())`. All workspace-scoped queries use it + `owner_id`.
- **RAG pipeline:** `grounding_service` → `retrieval_service` (pgvector *or* in-memory NumPy per `VECTOR_BACKEND`) + lexical FTS → RRF → `reranker_service` → token budget → `llm_service` (Gemini, key rotation) → SSE.
- **Extract-then-compute:** Finance ratios, Legal escalation/consistency, Research citations are computed in **Python** from LLM-extracted fields. Preserve this.
- **Async API / sync workers:** FastAPI + `asyncpg` on the request path; Celery tasks use `SyncSessionLocal` (psycopg2). Blocking model/LLM calls are offloaded via `run_in_executor`.
- **Auth:** HS256 JWT in cookies, bcrypt passwords, CSRF double-submit, device fingerprint, per-user/org vector namespaces, Postgres RLS.
- **SSE events:** `trial_status`, `thinking_stage`, `status`, `metadata`, `token`, `error`, `done` (plus `trust_report`, pending issue C-4). Client and server event names must stay in lockstep.

## Current Tech Stack

- **Backend:** FastAPI ≥0.109, SQLAlchemy 2 (async `asyncpg` + sync `psycopg2`), Alembic (55 migrations), Celery ≥5.3 + Redis, PyMuPDF/python-pptx, sentence-transformers (bge-m3 + cross-encoder), google-generativeai (Gemini), SlowAPI, python-docx, Razorpay, Tavily, OpenTelemetry/Prometheus/Sentry.
- **Frontend:** Next.js 16.2.6 (App Router), React 19.2.4, TypeScript 5, Tailwind 4, react-pdf, recharts, FingerprintJS, PostHog, @sentry/nextjs.
- **Data/infra:** PostgreSQL 16 + pgvector, PgBouncer, Redis 7, Docker Compose, Railway, GitHub Actions.

## Repository Layout

```
backend/app/
  main.py                  # ASGI app + middleware + Sentry + Gemini key bridge
  api/v1/api.py            # router aggregation
  api/v1/endpoints/*       # auth, documents, query, hr, legal, finance, study,
                           #   research, exams, billing, chats, insights, admin, health, ws, ...
  core/*                   # config, auth, security, middleware, rate_limiter, storage,
                           #   workspace, trial_enforcement, gemini_env, telemetry
  services/*               # retrieval, grounding, reranker, embedding, llm_service,
                           #   llm_key_rotation, veritas_engine, ocr_service, ocr_orchestrator,
                           #   deep_research_agent, export_engine, financial_table_extractor, ...
  models/*                 # ~50 tables
  schemas/*                # Pydantic
  workers/celery_app.py    # Celery config, includes, task_routes, beat_schedule
  workers/tasks/*          # document/hr/legal/finance/study/research/export/ocr/audio tasks
  automation/auto_*        # Beat-scheduled jobs
  alembic/versions/*       # migrations
  tests/                   # only 2 smoke tests today
frontend/src/
  app/*                    # pages; each workspace page = <WorkspaceUI workspaceType=.../>
  components/*             # WorkspaceUI + panels + shared UI
  hooks/*  lib/api.ts  lib/store/*  middleware.ts  styles/*
infrastructure/            # Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
docs/                      # architecture/project-map.md (STALE in places), marketing/ (overstated)
```
Note: `.agents/skills/**` is third-party design tooling, **not** part of the app. `frontend/CLAUDE.md` (→ `AGENTS.md`) carries Next.js-16-specific instructions that apply when editing the frontend.

## Important Documents

| Document | Use for |
|----------|---------|
| [PROJECT_KNOWLEDGE_BASE.md](PROJECT_KNOWLEDGE_BASE.md) | Index + one-paragraph summary |
| [REPORT.md](REPORT.md) | Executive overview, scorecard, marketing-vs-reality gaps |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Subsystems, pipelines, flows |
| [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) | Structure, import graph, change-impact, env table, flows |
| [DEBUG_MASTER_PLAN.md](DEBUG_MASTER_PLAN.md) | The issue backlog (C-1..L-13) + phases + safe order |
| [FINAL_AUDIT.md](FINAL_AUDIT.md) | Verified findings with evidence |
| [REPAIR_RULEBOOK.md](REPAIR_RULEBOOK.md) | Binding engineering rules |
| WORKSPACES / API_AUDIT / INTEGRATIONS / SECURITY_AUDIT / QUALITY_AUDIT / INTERVIEW_GUIDE | Deep references |

## How Claude Should Start Every Session

1. Read this file fully.
2. Read the required documents (order below) enough to locate the task.
3. Identify the exact `DEBUG_MASTER_PLAN.md` issue in play (or ask the user which one).
4. **Verify the relevant code against the docs before doing anything** — the repository is the source of truth.
5. Trace dependencies before editing. Then follow the Implementation Rules.

### Required reading order
1. [PROJECT_KNOWLEDGE_BASE.md](PROJECT_KNOWLEDGE_BASE.md)
2. [REPORT.md](REPORT.md)
3. [ARCHITECTURE.md](ARCHITECTURE.md)
4. [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md)
5. [DEBUG_MASTER_PLAN.md](DEBUG_MASTER_PLAN.md)
6. [FINAL_AUDIT.md](FINAL_AUDIT.md)
7. [REPAIR_RULEBOOK.md](REPAIR_RULEBOOK.md)

(For a focused fix you may read the issue-relevant sections rather than every doc end-to-end, but always verify against code.)

## Repository Rules

- Never guess architecture. Always inspect the code.
- The repository is the source of truth; docs can be stale or overstated.
- Read before changing.
- Never refactor unrelated code.
- Never optimize unless the task is a performance task.
- Never rewrite working code to a different style.
- Never trust README/marketing claims (trust score, multi-engine OCR, pgvector default are overstated).

## Debugging Rules

- Reproduce the current behavior first.
- **Fix one issue. Then stop. Then wait** for the user before starting another.
- Fix the root cause, not the symptom (e.g., add `get_embedding` once, not six patches).
- Never "fix" by widening a `try/except`; log failures loudly.

## Dependency Rules

Before editing, always inspect:
- The **import chain** (who imports this module).
- **API consumers** (`frontend/src/lib/api.ts` + components).
- **Workers** (registration in `celery_app.py include`, `task_routes`, and the running `-Q`).
- **Models** (table shapes/relationships).
- **Migrations** (does a schema change need Alembic?).
- **Environment variables** (`DEPENDENCY_GRAPH.md` §7).

Known dangling references — do not add more, and expect them when tracing: ~~`llm_service.get_embedding`~~ (fixed, C-1), `retrieval_service.query`/singleton (missing), ~~`embedding_tasks`/`retrieval_tasks` routes~~ (removed, H-3), `settings.AWS_REGION` (missing), `doc.workspace_type` (missing).

## Documentation Rules

- Always update documentation after implementation, in the same change: mark the `DEBUG_MASTER_PLAN.md` issue done, add an implementation note, update `DEPENDENCY_GRAPH.md`/`API_AUDIT.md`/`INTEGRATIONS.md` if a contract changed, and annotate the `FINAL_AUDIT.md` finding as RESOLVED (don't delete it).

## Testing Rules

- Run every relevant test; never skip verification.
- Add a regression test that fails before and passes after the fix.
- Never remove tests. Keep `pytest tests/ -v` green and `alembic upgrade head` succeeding on clean pgvector.

## Regression Rules

- Describe the possible regressions (use the issue's regression areas + `DEPENDENCY_GRAPH.md` §10 change-impact matrix).
- Verify each named regression scenario, not just the happy path.

## Implementation Rules (per issue)

```
Read the issue → Trace dependencies → Implement (minimal diff) →
Verify end-to-end → Update docs → Mark issue complete → STOP.
```
- One `DEBUG_MASTER_PLAN.md` issue per change unless explicitly told otherwise.
- Honor dependency order (strict chain: `C-1 → C-2 → H-3`; producers before consumers).
- If you discover a new bug, record it as a new issue — do not fold it in.

## Repository Knowledge (workspaces, brief)

- **General** — universal document Q&A via `/query/stream`; the reference grounded-answer path.
- **HR** — resume parsing, candidate ranking (`hr_tasks` registered ✅), JD↔resume MiniLM scoring, CSV export.
- **Legal** — clause/risk analysis; `/risk-report` is synchronous and solid (LLM extract + Python escalation + audit log); `clauses/search` broken (C-1); async `legal_tasks` unregistered (C-2).
- **Finance** — LLM extracts line items, **Python computes all 15 ratios** (exemplary); `transactions/search` broken (C-1); async `finance_tasks` unregistered (C-2).
- **Study** — flashcards (SM-2), quizzes (anti-cheat), tutor chat; `study/search` broken (C-1); async `study_tasks` unregistered (C-2).
- **Research** — citations (Python formatters), gaps; `synthesis` returns hardcoded fake data (H-4); deep-research step 1 broken (C-5); `research/search` broken (C-1); async `research_tasks` unregistered (C-2).
- **Exam** — grounded paper generation with answer keys, honest refusal, DOCX export, table extraction — the most complete workspace.

## Architecture Rules (must never accidentally break)

- The `/api/v1` base-path convention and `apiFetch` behavior.
- `resolve_workspace_id` as the single workspace-UUID derivation.
- The grounded prompt contract (evidence-only + refusal) on the grounded path.
- Extract-then-compute for numbers/formatting.
- Async request path / sync worker sessions.
- Tenant filters (`owner_id` + workspace UUID) on every workspace query.
- SSE event names.
- Worker three-way rule: a task must be in `include` **and** routed **and** its queue consumed.
- HS256-only JWT decoding.

## Safe Modification Rules (files needing extra care)

Per [REPAIR_RULEBOOK.md](REPAIR_RULEBOOK.md) §8a. The old "never modify" label is superseded by a graded process; touching these requires an authorizing issue, minimal diff, full regression, and an implementation note:

- `services/llm_service.py` — **additive only** (adding `get_embedding` for C-1 is allowed; don't alter generation/rotation). Raises at import without keys (H-7).
- `services/llm_key_rotation.py` — additive + the authorized M-9 fix (sleep-under-lock). Concurrency-sensitive.
- `services/veritas_engine.py` — additive; wire into the stream via the caller (C-4).
- `services/retrieval_service.py`, `grounding_service.py`, `chunking_service.py` — **extra care**: power every grounded answer; changes require full retrieval regression (chunking changes imply re-index).
- `workers/celery_app.py` — **extra care**, but C-2/H-3 require surgical edits to `include`/`task_routes`.
- `workers/tasks/hr_tasks.py` — extra care; only via its issue.
- `core/config.py`, `core/auth.py`, `core/middleware.py`, `frontend/src/lib/api.ts`, `components/WorkspaceUI.tsx` — high blast radius (config/auth/contract/all-workspaces).

## Common Pitfalls (repository-specific)

1. Registering a worker task (C-2) without adding the missing `get_embedding` (C-1) → the task still crashes. Do C-1 first.
2. Trusting doc line numbers or README claims. Verify against live code.
3. Re-introducing a manual `/api/v1` prefix in frontend calls.
4. Trying to reverse a `uuid5` workspace id back to a slug (M-11) — impossible; store the slug at write time.
5. Renaming an env var in one module only (`AWS_REGION` vs `S3_REGION`, H-5).
6. Adding a `task_route` for a nonexistent module, or a queue with no consumer (H-3).
7. Introducing a new silent fallback (zero vectors, dummy scores).
8. Editing `WorkspaceUI.tsx` or a service and breaking the SSE/API contract without updating `lib/api.ts`.
9. Assuming Beat runs (it doesn't in compose — H-2), or that scanned-document OCR works (it doesn't — C-3).
10. Committing `celerybeat-schedule.*` / build artifacts.

## Session Checklist

**At the beginning of every coding session**
- [ ] Read CLAUDE.md; skim the required-reading docs for the task.
- [ ] Identify the exact `DEBUG_MASTER_PLAN.md` issue.
- [ ] Confirm the current behavior in the live code.

**Before every implementation**
- [ ] Trace imports, API consumers, workers, models, migrations, env.
- [ ] Confirm dependency order (is a prerequisite issue done?).
- [ ] Note the file's care level (extra-care requires the §8a process).
- [ ] List the regression areas you will verify.

**After every implementation**
- [ ] Verify the real behavior end-to-end (drive the flow, read the SSE frames / DB state / query results).
- [ ] Run relevant tests + `alembic upgrade head` if schema touched; add a regression test.
- [ ] Check each named regression scenario.

**Before finishing**
- [ ] Mark the issue done + implementation note; update dep graph/contracts; annotate FINAL_AUDIT.
- [ ] Confirm no new silent fallback, no dangling reference, no committed artifacts, CI-green expectations.
- [ ] **Stop.** Report what changed and what was verified. Do not start the next issue unprompted.

## Definition of Success

A successful Claude coding session:
- Resolves **exactly one** authorized `DEBUG_MASTER_PLAN.md` issue at its **root cause**, with the **smallest** correct diff.
- Preserves every architecture invariant and public contract (or breaks one only with explicit approval + migration).
- Adds a regression test; leaves all tests green and migrations applying cleanly.
- Introduces **no** new silent failure and **no** new dangling reference.
- Updates documentation in the same change (issue status, implementation note, dependency/contract docs, FINAL_AUDIT annotation).
- Ends with a clear report of what changed, what was verified, and what regressions were checked — then **stops and waits**.

*Operating manual only. No source code is modified by this file. Engineering rules: [REPAIR_RULEBOOK.md](REPAIR_RULEBOOK.md).*
