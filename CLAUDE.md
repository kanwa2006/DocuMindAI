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
FastAPI `==0.136.1` · Starlette `==1.0.0` (both **pinned**; read the note in `requirements.txt` before bumping) · SQLAlchemy 2 (async `asyncpg` + sync `psycopg2`) · Alembic · Celery ≥5.3 + Redis 7 · pgvector · sentence-transformers (bge-m3 + `ms-marco-MiniLM-L-6-v2` cross-encoder) · google-generativeai · PyMuPDF · PaddleOCR/PaddlePaddle/Docling/LayoutParser · passlib + `bcrypt==4.0.1` (pinned — passlib breaks on ≥4.1) · PyJWT · SlowAPI · Razorpay · boto3 · Sentry · OpenTelemetry + prometheus-client

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
  alembic/versions/*       # migrations (count drifts; `alembic heads` is truth)
  tests/                   # pytest suite (see backend/pytest.ini)
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
- **Tenant key is `owner_id`, never `workspace_id`.** `workspace_id` is a *category* slug (`uuid5` of "legal"/"finance"/…) and is identical for every user — it is not a tenant discriminator. Owner-scoped models inherit `TenantScoped` (`core/tenant_scope.py`) and a `do_orm_execute` hook injects `owner_id = <current owner>` into every ORM SELECT; with no scope established it **raises** rather than returning unfiltered rows. Writes still set `owner_id` explicitly (`NOT NULL` makes a miss fail loudly). Raw `text()` queries bypass the hook — scope them by hand.
- **SSE event names** must stay in lockstep between client and server: `trial_status`, `thinking_stage`, `status`, `metadata`, `token`, `error`, `done`, `trust_report`.
- **Worker three-way rule.** A task must be in `celery_app.include` **and** routed in `task_routes` **and** have its queue consumed by a running `-Q`.
- **Auth.** HS256-only JWT decoding, httponly + `samesite=strict` cookies, CSRF double-submit, device fingerprint. **Postgres RLS is present but inert** — the app connects as `postgres` with `rolbypassrls=true`, RLS is disabled on the `legal_*`/`finance_*`/`study_*`/`research_*` tables, and the `app.current_workspace_id` setting its policies key on is never set. Do not count it as a control; `TenantScoped` is the enforcement.
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

## Engineering Orchestration

The repository's execution model. **This section is the only source of truth for how work
flows.** Permanent principles and the Release Gate live in
[the Directive](docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md); status and evidence
live in [PROGRESS.md](PROGRESS.md). Never duplicate across the three — move, don't copy.

### Responsibility hierarchy

**The main engineering thread owns** planning, implementation, debugging, architectural
decisions, prioritization, integration, and commits. **It is the only writer of production
code.**

**Specialist agents own** verification, review, diagnosis, measurement, and quality gates.
**No specialist implements.** They run in isolated contexts, cannot invoke each other, and
report back to the thread that called them.

### Session startup

Read three documents — `CLAUDE.md`, `PROGRESS.md`, the Directive — plus `final_audit.md` when
the session's work is defect repair. Then **discover** the organization rather than trusting a
hardcoded list (files change; this section may lag):

```bash
ls .claude/agents/*.md          # specialists — tracked, shared, authoritative
ls .claude/skills/*/SKILL.md    # skills — UNTRACKED local tooling, see policy below
```

`.agents/skills/` and `.claude/skills/` are **byte-identical copies** of the same seven skills,
both gitignored. Listing either is sufficient; do not classify a skill twice because it appears
in both paths.

Build the map once. **Do not reload agents or skills before every task** — load a
specialist's file only when delegating to it, and a skill only when its domain is in play.

### Agent registry

Discovered from `.claude/agents/`. Each carries this project's real failure history, not
generic advice. Full trigger/scope/inputs/escalation live in the agent's own file — read it
when delegating, not before.

Each agent answers **one question no other agent may answer.** If you cannot state an agent's
question in a single sentence that no sibling could also claim, the roster is wrong — fix the
roster, not the prompt.

| Agent | The one question it answers | Invoke when | Do NOT invoke when |
|---|---|---|---|
| `docs-sync-checker` | Do the 3 governing docs still match the repo? | Session/phase start; after updating docs | Judging whether code is *correct* |
| `test-runner` | Did the suite pass, is the failure path covered, **and does the guard bite**? | A fix is ready; before any "tests pass" claim; after adding a guard | Asking whether a service is healthy |
| `code-reviewer` | Is this decision in the layer that owns it — and are its readers still symmetric? | Before committing a non-trivial diff; on a standing finding | Security severity; perf ranking |
| `integrity-auditor` | **Does this code do what it claims?** | A feature reports success; a number reaches a user; a docstring asserts "always" | A change is what's in question → `code-reviewer` |
| `security-reviewer` | Is this an exposure, and how bad? | Auth, tenancy, uploads, secrets, prompt injection | General code quality |
| `infra-health-checker` | Did it come up healthy, and what did it leave behind? | Changed a start command, flags, or env | Judging the shippable artifact |
| `release-readiness-checker` | Is the **artifact** shippable? | Before any deployment claim | Adjudicating a secret's severity |
| `rag-pipeline-tracer` | **Which stage** produced this bad answer? | Answer wrong, ungrounded, uncited, or unfindable | Deciding whether to optimize it |
| `performance-profiler` | **What does it cost**, and is it worth fixing? | Before any performance claim | Correctness attribution |
| `workspace-qa` | Does the advertised feature actually work end to end? | Before claiming a workspace works | Fixing what it finds |
| `response-quality-reviewer` | Is the presentation good **and the substance untouched**? | Changing how answers render | Anything touching retrieval/prompts/citations |

**Exclusive-ownership tie-breaks** (where two could plausibly answer the same question):

- `rag-pipeline-tracer` says *which stage*; `performance-profiler` says *what it costs*.
- `infra-health-checker` = **runtime, now**; `release-readiness-checker` = **artifact, pre-deploy**.
- `release-readiness-checker` **detects** an exposed secret; `security-reviewer` **adjudicates** it.
- `test-runner` reports suite results; **suite-green is not process-healthy** → `infra-health-checker`.
- `response-quality-reviewer` owns presentation only; retrieval, prompts, citation derivation,
  and trust-score computation are substance.
- `code-reviewer` reviews **a decision that was made**; `integrity-auditor` establishes **a claim
  that was never true**. A dead symbol, inert setting, hardcoded metric, missing dependency, or
  drifted library API is the auditor's even when the reviewer notices it first.
- `integrity-auditor` **detects** a fabricated control; `security-reviewer` **adjudicates** whether
  it is an exposure — the same detection→verdict split as the release checker.
- `rag-pipeline-tracer` explains why **one answer** was wrong; `integrity-auditor` establishes that
  a number was **never real for any answer**. A metric that is always identical cannot "disagree
  with the answer," so the tracer's trigger can never fire on it.

### Two trigger modes

Every agent runs in one of two modes, and the mode changes what the invoking prompt must supply.

- **Change-triggered** — the default. A diff exists; the agent judges it. Supply the diff.
- **Standing-defect** — no diff, no recent change. The agent audits code as it is, against a
  `final_audit.md` finding id or a file list. Supply the finding id and the claim under test
  **in place of** a diff.

**A missing diff is never a reason to decline.** The overwhelming majority of this repository's
real defects were found in code nobody had touched in months: the guard with zero callers, the
trust score that is a constant, the two features that have never executed once. A roster that
only reviews changes cannot find them, and for one full cycle this one could not. **Age is a
trigger, not a defence.**

**Subagents start cold.** The invoking prompt must carry every file path, diff, error, and
prior decision. All return the same 10-section contract (Summary · Evidence · Findings ·
Root Cause · Risks · Recommendations · Confidence · Escalation · Files Reviewed · Additional
Verification Needed) and tag blockers **agent-actionable** / **owner-access-required** /
**owner-decision-required**. Editing an agent file needs a session restart to take effect.

**Cross-agent repetition is deliberate.** The Turbopack restart rule appears in four agent
files, the `DummyLLMProvider` warning in three. Do not consolidate them into a shared file:
a cold subagent reads only its own definition, so a rule it does not carry is a rule it does
not have. **Duplication is the cost of cold start; pay it.** The rule for changing one is to
change every copy in the same commit.

**Verify agent output before acting on it.** Agents have been wrong here. Re-check any
load-bearing claim against the repo or runtime — this is not optional politeness, it has
caught real errors.

### Specialist agent lifecycle

**Inputs and outputs are uniform**, which is why they are stated once here rather than
repeated per agent (that would be two sources of truth for one contract):

- **Required inputs — every agent, every time.** Subagents start cold: nothing carries over.
  The invoking prompt must supply **(1)** the diff or changed-file list *or*, in standing-defect
  mode, the `final_audit.md` finding id and the claim under test; **(2)** the intent in one
  sentence — without it no agent can judge ownership; **(3)** how to run the stack; **(4)** any
  prior decision that must not be relitigated; **(5)** any known-failing baseline, so
  pre-existing failures are not reported as new. An agent's own file lists anything additional.
- **Expected output — every agent.** The 10-section contract (Summary · Evidence · Findings ·
  Root Cause · Risks · Recommendations · Confidence · Escalation · Files Reviewed ·
  Additional Verification Needed), findings ranked most-severe first, each blocker tagged
  **agent-actionable** / **owner-access-required** / **owner-decision-required**.

  Four quality bars apply to that contract, and a report that misses one is not usable:

  1. **Evidence is a command and its output**, or `file:line` and the actual lines. A timing
     without the command that produced it, or a claim without the grep behind it, is an
     assertion. This project has already shipped wrong conclusions drawn from a proxy metric
     (`len(app.routes)`) and from a regex that silently failed on a multi-line decorator.
  2. **Confidence is three-valued and load-bearing.** Verified / Partially Verified /
     Unverified. **Unverified is a distinct verdict from "fine"** — never collapse "I could not
     check this" into "no findings."
  3. **Every blocker carries its tag.** An untagged blocker cannot be routed and stalls.
  4. **No padding.** "No findings; the fix is at the right layer" is a complete report. Inventing
     findings to fill sections is worse than an empty section, because it costs the thread a
     verification pass it did not need.
- **Who consumes it.** Always the main engineering thread. Agents cannot invoke each other,
  so any "follow-up agent" in the table below is a call *the thread* makes next.
- **Implementation owner — always the main engineering thread.** No specialist writes
  production code, tests, or docs. A specialist that proposes a diff is advising, not
  implementing.

**Handoff chains** (thread-mediated): `release-readiness-checker` → `security-reviewer`
(detection → verdict) · `integrity-auditor` → `security-reviewer` (a fabricated control is
detected, then adjudicated) · `integrity-auditor` → `test-runner` (a test that passes by
asserting a hardcoded value) · `rag-pipeline-tracer` → `performance-profiler` (stage → cost) ·
`workspace-qa` → the layer owner it names · `test-runner` → `code-reviewer` when a failure
is architectural rather than a bad assertion · `code-reviewer` → `integrity-auditor` when a
reviewed file turns out to claim something it never did.

**Changing the roster.** Add an agent only for an *observed, recurring* responsibility no
existing agent covers — not because a technology exists. Split one that has grown two
distinct owners; merge two that answer the same question; retire one that stops earning its
place. Any change updates the registry table above in the same commit, and takes effect only
after a session restart.

### Skill registry and policy

`.agents/skills/` is **gitignored — zero tracked files.** It is local tooling, not
repository content. Therefore: **no pipeline may depend on a skill**, and no skill may be
cited as a requirement other contributors must satisfy. Skills are optional guidance,
consulted only when their domain is in play.

Classified by reading each `SKILL.md` against this stack (Next.js 16 + React 19 + Tailwind 4,
hand-rolled components — **no shadcn/ui, no Radix**, verified 0 in `package.json`):

| Skill | Verdict | Use for |
|---|---|---|
| `ui-ux-pro-max` | **Applicable** | Stack-agnostic a11y/UX rules: contrast ≥4.5:1, focus states, 44px touch targets, tab order, responsive/typography guidance |
| `ckm-design-system` | **Applicable in principle** | Three-layer token methodology (primitive→semantic→component); maps onto Tailwind 4 CSS variables |
| `ckm-ui-styling` | **Partially — Tailwind only** | Its shadcn/ui + Radix guidance is **rejected**: adopting it would add a component library this repo does not use and duplicate the existing design system |
| `ckm-brand` | **Marginal** | Only for `docs/marketing/` and landing-page copy. Not for product UI |
| `ckm-design`, `ckm-banner-design`, `ckm-slides` | **Not applicable** | Logo/CIP generation, ad and social banners, Chart.js decks — DocuMindAI has no such surface |

**Binding rules.** Repository architecture outranks any skill. Never adopt a technology a
skill recommends that the repo does not already use. Never migrate frameworks on a skill's
say-so. When skills conflict, the repo's existing implementation wins and stays single.
A newly added skill is classified by the same test — does it improve *this* stack without
importing foreign technology — so future skills need no edit to this section.

**Skill lifecycle.**

1. **Discover** at session startup (`ls .agents/skills/*/SKILL.md`) — names only. Do not read
   bodies yet; several are megabytes.
2. **Classify** any unseen skill by reading its `SKILL.md` entry point (the skill's contract)
   against this stack. Record the verdict in the table above.
3. **Load** a skill's body only when its domain is the work in hand — UI/a11y/typography
   skills for frontend and response-rendering work, nothing for backend, Celery, Redis,
   migrations, or deployment.
4. **Do NOT load** an unrelated skill, a skill already classified *not applicable*, or any
   skill merely because it exists. Loading costs context and buys nothing outside its domain.
5. **Resolve conflicts** in this order: repository architecture → the Directive's principles
   → the more specific skill → the more recent skill. When two skills disagree, the existing
   implementation stays single; never fork an implementation to satisfy both.
6. **Architecture overrides guidance, always.** A skill is advice from outside this project.
   It may not introduce a dependency the repo lacks, migrate a framework, or replace working
   code on stylistic grounds. `ckm-ui-styling`'s shadcn/Radix rejection is the worked example.

### Implementation lifecycle

```
Startup (3 docs + discovery)
  → Pick highest-priority unresolved item from PROGRESS.md
  → Read the smallest sufficient subsystem  (see Repository Scan Policy below)
  → Implement at the layer that OWNS the decision
  → Runtime verification (never compilation alone)
  → Targeted specialist review (matrix below — only the relevant ones)
  → Regression suite
  → Update PROGRESS.md
  → Commit
  → Next item
```

**Repository scan policy.** Exact file → related module → feature folder → workspace →
shared libraries → whole repo. Each widening needs a reason. Cache understanding for the
session; don't re-derive verified conclusions.

### Delegation matrix

Invoke **only** the reviewers a change actually touches. Running every reviewer on every
change is waste, not rigor.

| Work touches | Reviewers, in order |
|---|---|
| Auth, tenancy, uploads, secrets, prompt injection | `security-reviewer` → `test-runner` |
| Database schema / migration | `code-reviewer` → `test-runner` → `infra-health-checker` |
| Celery, Redis, queues, background jobs | `code-reviewer` → `infra-health-checker` → `test-runner` |
| Service start command, flags, env, Docker | `infra-health-checker` → `release-readiness-checker` |
| Retrieval, embedding, vector search, RRF, rerank | `rag-pipeline-tracer` → `performance-profiler` |
| Prompt construction, LLM provider, streaming | `code-reviewer` → `rag-pipeline-tracer` |
| API contract / endpoint shape | `code-reviewer` → `test-runner` |
| Response rendering, markdown, citations display | `response-quality-reviewer` → browser verification |
| Frontend layout, composer, responsive, a11y | browser verification → `response-quality-reviewer` |
| Any workspace feature claim | `workspace-qa` |
| Performance claim | `performance-profiler` |
| Deployment claim | `release-readiness-checker` → `security-reviewer` |
| Documentation | `docs-sync-checker` |
| A score, confidence, status, or count shown to a user | `integrity-auditor` → `security-reviewer` if it is a control |
| A feature that reports success | `integrity-auditor` → `workspace-qa` |
| Dead code, inert setting, missing dependency, drifted library API | `integrity-auditor` |
| Adding or changing a regression guard | `test-runner` (must watch it go red) |
| Changing how a value is **written** anywhere | `code-reviewer` — question 3 enumerates its readers |

**A finding is not routed by the file it lives in, but by the question it raises.** `veritas_engine.py`
is a services file, which suggests `code-reviewer`; the question "is this number real" is
`integrity-auditor`'s. Route on the question.

### Defect-register lifecycle

`final_audit.md` is the **standing defect register** — 83 findings from a line-by-line read of
all 425 tracked files. It is a register, not a status document: `PROGRESS.md` remains the single
source of truth for what is *done*. A finding is closed in `PROGRESS.md` and struck in
`final_audit.md`; **never record status in the register itself.**

Work it one finding at a time:

```
Pick a finding  (order: final_audit.md §7 tiers — exposure × cost, not severity alone)
  → Re-verify it still exists          ← the register is a snapshot; code moves
  → Read its "Debug — blast radius" tag
  → Implement at the layer that OWNS it
  → Route by the question, not the file (matrix above)
  → Force the failure path; add the guard; watch the guard go red
  → Update PROGRESS.md; strike the finding in final_audit.md
  → Commit
```

**Three rules specific to a register, learned from this one:**

1. **Re-verify before fixing.** A finding is a point-in-time observation. Fixing a defect that
   no longer exists wastes a cycle; worse, it can reintroduce one.
2. **Honour the blast-radius tag.** Findings marked *NOT self-contained* require two or more
   files changed **in the same commit** or the fix is not a fix — S5 (key rotation and
   `embedding_service` both mutate the same `genai` global) and S8 (embedding dimension agreement
   across two containers) are the live examples. A tag of *owner-decision-required* means the
   thread may not choose unilaterally.
3. **One finding per commit, unless the tag says otherwise.** Batching unrelated fixes is how H5
   escaped: a correct write-path change and an unexamined read path travelled together, and the
   green happy path covered for both.

**A fix is not done when the defect stops reproducing.** It is done when the *class* is closed —
see the regression lifecycle. Every finding in this register escaped a green suite; closing one
without asking why it escaped guarantees a sibling survives.

### Runtime verification lifecycle

**Compilation is never verification. Code inspection is never verification.** A change is
verified only by real execution: real DB rows, real streaming, real UI, real regression.
When a fix targets a failure path, **force that failure** — a fix that passes because the
happy path never exercises it is unverified.

**Browser verification (frontend — mandatory).** No frontend change is committed until
exercised in a real browser. `docker compose restart frontend` **first** — Turbopack does
not recompile across the Windows→Docker bind mount, and this has already produced one
multi-hour false negative. Cover: desktop / tablet / mobile widths, workspace switching,
chat switching, streaming, markdown, citations, upload, history, scroll, composer, loading
and error states. Screenshots are evidence; delete them once findings are recorded.

### Debugging lifecycle

Reproduce → localize to the owning layer → **rule out false signals first** → fix the
architecture, not the symptom → force the failure path → verify shared state was not left
bad. Known false signals in this repo: stale Turbopack bundles, the cached Next.js error
overlay, a test harness double-submitting, and any conclusion drawn from a proxy metric
instead of the observable behaviour.

### Regression lifecycle

Every fix must make its **class** of bug impossible, not just its instance. After each fix
ask: why did this escape, what review missed it, which test was absent, could another
subsystem fail the same way. Then strengthen the shared layer and add the guard —
**verify the guard bites** by reintroducing the defect. `tests/test_worker_session_discipline.py`
is the reference: a ratchet whose allowlist may only shrink.

**The thread writes the guard; `test-runner` verifies it bites.** A guard nobody has watched go
red is an untested guard, and this repository already contains a control that documents itself
as always-called and has zero callers. Add the guard **and** the observation that it failed on
the reintroduced defect — the second half is the part that has been skipped before.

**When the escape was a roster gap, fix the roster.** If no agent could have been triggered for
a defect, adding a test closes the instance and leaves the class open. That is how
`integrity-auditor` came to exist: three agents referenced the trust score and none could be
invoked for it, so a fabricated metric survived a repair phase, a security review, and 131
passing tests.

### Commit lifecycle

Commit at each **logically complete milestone** — a coherent unit that is verified, not a
day's accumulation and not a half-finished refactor. Before committing: runtime verification
done, regression green, relevant reviewers clear, `PROGRESS.md` updated in the same commit or
the one immediately after.

The message explains **why the change exists**, not what changed — the diff already says
what. State the defect, the mechanism, the architectural decision, and the evidence that
verified it. Working commits in this repo read like short incident notes; match that.

Never bypass hooks (`--no-verify`) or signing. Never commit build artifacts (`.next/`,
`celerybeat-schedule.*`, `.playwright-mcp/`), screenshots, or scratch scripts — delete debug
artifacts before committing. Push and deploy are **owner-authorized**, never automatic.

### Documentation lifecycle

Four files, four owners, no overlap — enforced by `docs-sync-checker`:

| File | Owns | Update when |
|---|---|---|
| `CLAUDE.md` | Stable context + this execution model | Architecture, invariants, or orchestration changes |
| `PROGRESS.md` | All status, evidence, blockers, session log | Every completed unit of work |
| The Directive | Permanent principles, Release Gate, definition of done | **Frozen** — only when a real failure exposes a missing rule |
| `final_audit.md` | The standing **defect register** — findings, causes, blast radius | A finding is added, struck, or its blast radius changes |

`final_audit.md` holds **defects, never status.** Whether a finding is fixed is `PROGRESS.md`'s
to say. The register answers "what is wrong and what does fixing it touch"; the progress file
answers "what has been done about it." Keeping the two separate is what stops the register from
becoming a second, competing status document — the split-brain failure this table exists to
prevent.

If information belongs elsewhere, **move it, never copy it**. When a fix invalidates a
documented claim, correct the claim in the same commit — an invariant that has become false
is worse than no invariant, because it is trusted (see the RLS and tenant-filter
corrections). Prefer descriptions that cannot drift over counts that must be maintained.

**Orchestration is living infrastructure.** When implementation reveals a better rule,
amend this section immediately so the next session inherits it — but amend incrementally;
never regenerate it wholesale.

### Workspace parity

The canonical list is `KNOWN_WORKSPACE_SLUGS` in `backend/app/core/workspace.py` — read it,
don't hardcode. Every workspace meets identical standards: user/chat/retrieval/streaming
isolation, history, uploads, reports, citations, and the **shared** renderer, design system,
markdown renderer, and streaming renderer. Only prompts, templates, and business logic may
differ. A workspace-specific UI component is an architecture violation, not a feature.

**Workspace completion pipeline.** A workspace is "done" only when every step below passes
for it. Run per workspace, in order; stop at the first failure and fix at the owning layer:

1. **Upload → READY** — document reaches READY; chunks exist.
2. **Real extraction** — the pipeline reads the *uploaded* document. Grep the owning task for
   placeholder strings; P0-8 shipped fabricated text in two workspaces and looked correct
   in both.
3. **Worker path sound** — task uses `SyncSessionLocal`, is registered, routed, and its queue
   consumed (the three-way rule).
4. **Rows land** with `owner_id` set, and `workspace_id` set to the resolved slug UUID.
5. **Isolation** — a second account sees none of it: documents, chats, retrieval, uploads,
   reports, streaming, cache/Redis keys, vector namespace.
6. **Retrieval + citations** — answers cite the right page; absent evidence is refused.
7. **Streaming** — SSE event names in lockstep; one `done`; no duplicate persistence.
8. **History + persistence** survive reload and workspace switch.
9. **Rendering** via the shared renderer — no workspace-specific component.
10. **Browser verification** at desktop/tablet/mobile.

Verification is `workspace-qa`'s call; the fix is the thread's. Record the per-workspace
result in `PROGRESS.md` — a workspace is never "done" by inference from another one passing.

### Deployment and release lifecycle

Deployment requires, in order: implementation verified at runtime → regression green →
`security-reviewer` clear → `performance-profiler` clear (if perf is claimed) →
`release-readiness-checker` clear → every Release Gate box in `PROGRESS.md` independently
verified. The Gate is defined in the Directive and tracked in `PROGRESS.md`; it is never
restated here.

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
