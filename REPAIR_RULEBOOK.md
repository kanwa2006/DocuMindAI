# DocuMindAI — Repair Rulebook

> **Status:** Permanent engineering rulebook. Binding on every human and AI contributor who edits this repository.
> **Authority:** This document governs *how* changes are made. It does not itself change code. Where it conflicts with older inline notes (e.g., the "STABLE files / never modify" list in `docs/architecture/project-map.md`), **this rulebook supersedes them** — see [§10 Architecture Preservation Rules](#10-architecture-preservation-rules).
> **Companions:** [DEBUG_MASTER_PLAN.md](DEBUG_MASTER_PLAN.md) (what to fix), [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) (how it connects), [FINAL_AUDIT.md](FINAL_AUDIT.md) (verified findings), [CLAUDE.md](CLAUDE.md) (session operating manual).

---

## 1. Project Philosophy

1. **Correctness over cleverness.** DocuMindAI is a grounded, cited RAG product. A confident wrong answer is worse than a slow correct one. Every change is judged first by whether it makes the system *more truthful*, then by everything else.
2. **The repository is the truth; documents are a map.** Documentation (including this file) can drift. When code and a document disagree, the code wins and the document is corrected.
3. **Silent failure is the enemy.** This codebase historically prefers uptime over honesty (zero-vector embeddings, dummy reranker, swallowed exceptions). New work must make failures *visible*, not hidden.
4. **Small, reversible steps.** One issue, one change, one verification, one commit. Large simultaneous edits are prohibited.
5. **Claims must match reality.** Features are documented as they *behave*, never as they are *aspired* to behave.

---

## 2. Engineering Principles

- **Additive before invasive.** Prefer adding a method/module/wrapper over editing a load-bearing file in place.
- **Trace before touch.** Read the import chain, API consumers, workers, models, and migrations before editing.
- **Fail loud at the boundary, degrade gracefully only when intended and observable.**
- **One source of truth per concern** (embeddings via `embedding_service`, workspace UUIDs via `resolve_workspace_id`, LLM via `llm_service`, storage via `storage_service`).
- **Backwards compatibility by default.** Breaking an API/contract/DB shape requires explicit approval and a migration/versioning plan.
- **Determinism where correctness matters.** Numeric and formatting results are computed in Python, never delegated to the LLM (see Finance ratios, Legal escalation, Research citations — preserve this pattern).

---

## 3. Repository Source of Truth

- The **live source tree** is authoritative. Not this rulebook, not any audit doc, not comments, not the README.
- Before asserting "X works / X is broken," open the file and confirm the current lines. Line numbers in docs are snapshots and may drift.
- The README and `docs/marketing/*` are **known to overstate** delivered behavior (trust score, multi-engine OCR, pgvector default). Never cite them as evidence of what the system does.
- `docs/architecture/project-map.md` is **stale** in places (it describes an already-fixed doubled-`/api/v1` prefix and a workspace-UUID crash). Verify before relying on it.

---

## 4. Documentation Hierarchy

Precedence, highest first:

1. **Live source code** (ground truth).
2. **CLAUDE.md** — session operating manual (how to work).
3. **REPAIR_RULEBOOK.md** (this file) — engineering rules (how to change).
4. **DEBUG_MASTER_PLAN.md** — the authoritative issue backlog + order.
5. **DEPENDENCY_GRAPH.md** — structure, flows, change-impact.
6. **FINAL_AUDIT.md** — verified findings with evidence.
7. **ARCHITECTURE.md / WORKSPACES.md / API_AUDIT.md / INTEGRATIONS.md / SECURITY_AUDIT.md / QUALITY_AUDIT.md** — deep references.
8. **REPORT.md / PROJECT_KNOWLEDGE_BASE.md** — overview/index.
9. **INTERVIEW_GUIDE.md** — explanatory, non-normative.
10. **README.md / docs/marketing/** — non-authoritative; overstated.

If two documents conflict, the higher one wins; then correct the lower one.

---

## 5. Documentation Update Rules

- **Every code change updates documentation in the same change.** No exceptions.
- On fixing a `DEBUG_MASTER_PLAN.md` issue: mark it resolved, record an **Implementation Note** (what changed, files, verification performed, residual risk), and update any affected section of `DEPENDENCY_GRAPH.md`.
- If a change alters an API, env var, table, worker route, or flow → update `API_AUDIT.md` / `INTEGRATIONS.md` / `DEPENDENCY_GRAPH.md` accordingly.
- If a change invalidates a finding in `FINAL_AUDIT.md`, annotate it "RESOLVED (date, commit)" — do not silently delete.
- Never let documentation claim a capability the code does not deliver.

---

## 6. Issue Resolution Workflow (mandatory)

```
Read documentation (CLAUDE.md → DEBUG_MASTER_PLAN issue → DEPENDENCY_GRAPH)
        ↓
Locate issue in the live code (confirm current lines/behavior)
        ↓
Trace dependencies (imports, consumers, workers, models, migrations, env)
        ↓
Implement (one issue, minimal surgical change)
        ↓
Verify (drive the real behavior end-to-end, not just types/tests)
        ↓
Regression testing (named regression areas from the issue + change-impact matrix)
        ↓
Documentation update (mark issue done, implementation notes, dep graph)
        ↓
Issue completion (Definition of Done met)  →  STOP. Do not start the next issue unprompted.
```

Rules binding this workflow:
- **One `DEBUG_MASTER_PLAN.md` issue per change** unless the user explicitly authorizes a batch.
- Respect the issue's **Dependencies** field. The chain `C-1 → C-2 → H-3` is strict (see [§8](#8-common-ai-failure-modes-and-how-to-prevent-them)).
- If implementing reveals a new bug, **record it as a new issue** in `DEBUG_MASTER_PLAN.md`; do not fold an unrelated fix into the current change.

---

## 7. Mandatory Engineering Rules

These are non-negotiable.

1. **Never modify more than one `DEBUG_MASTER_PLAN.md` issue per change** unless explicitly requested.
2. **Never change a public API** (route path, method, request/response shape, SSE event names) **without checking `DEPENDENCY_GRAPH.md` §3/§8 and `API_AUDIT.md`** for consumers, and updating both.
3. **Never remove or weaken tests.** Add tests; never delete to make a build pass.
4. **Always update documentation** in the same change (see §5).
5. **Always verify affected dependencies** before and after (imports, consumers, workers, models, migrations, env).
6. **Always assess and state regression impact** using the issue's regression areas + the change-impact matrix.
7. **Always run verification** by exercising real behavior end-to-end, not only unit tests or typecheck.
8. **Always update the `DEBUG_MASTER_PLAN.md`** status + implementation notes when an issue is touched.
9. **Always preserve backwards compatibility** unless a breaking change is explicitly approved with a migration plan.
10. **Always record implementation notes** (files touched, decisions, verification evidence, residual risk).
11. **Never introduce a new silent fallback.** Any degradation path must log at WARNING/ERROR and emit an observable signal.
12. **Never delegate arithmetic or deterministic formatting to the LLM.** Extract with the LLM; compute in Python.
13. **Never hardcode secrets.** All credentials via environment variables.
14. **Never commit build/runtime artifacts** (`celerybeat-schedule.*`, `build.log`, `tmp/next-build/*`).
15. **Never rename an environment variable in one module only.** Config keys are shared contracts.

---

## 8. Architecture Preservation Rules

The following architectural decisions are **load-bearing** and must not be broken by accident. Changing any of them requires explicit approval and a stated migration/regression plan.

1. **API base path.** All backend routes live under `/api/v1`. The frontend `NEXT_PUBLIC_API_URL` already includes `/api/v1`; `apiFetch` prepends it. Do **not** re-introduce a manual `/api/v1` in call sites.
2. **Workspace identity.** `resolve_workspace_id(slug|uuid)` deterministically maps slugs to UUIDs via `uuid.uuid5(NAMESPACE_DNS, slug.lower())`. All workspace-scoped queries must go through it. Do not invent a second derivation (see L-5).
3. **Grounding contract.** The evidence-only prompt + token budget + explicit refusal string is the anti-hallucination mechanism. Do not let the model answer from outside the evidence on the grounded path.
4. **Extract-then-compute.** Finance ratios, Legal escalation/consistency, and Research citations compute results in Python from LLM-extracted fields. Preserve this split.
5. **Async everywhere on the API.** FastAPI + async SQLAlchemy (`asyncpg`); blocking model/LLM calls are offloaded via `run_in_executor`. Do not add blocking I/O to request handlers.
6. **Sync sessions in workers.** Celery tasks use `SyncSessionLocal` (psycopg2). Do not mix async sessions into sync task bodies.
7. **Tenant isolation.** Every workspace query filters by `owner_id` + workspace UUID. Never remove an ownership filter.
8. **SSE contract.** `/query/stream` emits `trial_status`, `thinking_stage`, `status`, `metadata`, `token`, `error`, `done` (and, per issue C-4, must add `trust_report`). Do not rename these event names without updating `frontend/src/lib/api.ts`.

### 8a. Extra-care files (formerly "STABLE / never modify")

`docs/architecture/project-map.md` historically labels some files "never modify" and others "additive/wrapper only." That absolute framing **blocks legitimate bug fixes** (e.g., issue C-2/H-3 require editing `workers/celery_app.py`). It is superseded by this graded process:

| File | Care level | Allowed change | Notes |
|------|-----------|----------------|-------|
| `services/llm_service.py` | Additive-only | Add methods/wrappers (e.g., `get_embedding` for C-1). Avoid altering existing generation/rotation logic. | Import-time singleton is fragile (H-7). |
| `services/llm_key_rotation.py` | Additive-only + targeted fix | M-9 (sleep-under-lock) is an authorized targeted fix. | Concurrency-sensitive. |
| `services/veritas_engine.py` | Additive-only | Wire into stream (C-4) via caller; improve factors deliberately. | Heuristic today. |
| `services/retrieval_service.py` | **Extra care** | H-1 (pgvector default) is an authorized, tested change. | Powers every grounded answer. |
| `services/grounding_service.py` | **Extra care** | Change only with full retrieval regression. | Token budget + citations. |
| `services/chunking_service.py` | **Extra care** | Change only with re-index plan (affects all chunks). | Chunk boundaries affect retrieval. |
| `workers/celery_app.py` | **Extra care** | C-2/H-3 require editing `include`/`task_routes`. Minimal, surgical. | Worker boot + routing. |
| `workers/tasks/hr_tasks.py` | **Extra care** | Only via its own issue. | Registered producer/consumer. |

**Rule:** touching any Extra-care file requires (a) an authorizing `DEBUG_MASTER_PLAN.md` issue, (b) the smallest possible diff, (c) full regression on the named areas, (d) documentation update, (e) an implementation note recording why the file had to change.

---

## 9. Safe Debugging Rules

1. Reproduce first. Confirm the current (broken) behavior against the live code before editing.
2. Form one hypothesis, change one thing, re-test. No shotgun edits.
3. Read the exact function and its callers before editing; do not pattern-match from memory or from a doc's line numbers.
4. Prefer the root cause over the symptom (e.g., add the missing `get_embedding` once in the embedding layer rather than patching six call sites — C-1).
5. Do not "fix" by widening a `try/except`. Swallowing is how these bugs hid (C-5 deep-research step 1).
6. When a fix depends on data that another broken task produces, fix the producer first (e.g., C-1 before C-2 before H-4).

---

## 10. Safe Refactoring Rules

1. **Do not refactor unrelated code** while fixing an issue. Scope creep is prohibited.
2. **Do not optimize** unless the issue is a performance issue.
3. **Do not rewrite working code** to a different style/pattern.
4. Behavior-preserving refactors (if explicitly requested) must be covered by tests *before* and *after*, and land in their own change.
5. Removing dead code (e.g., unused `ws` router, phantom task routes) is a refactor: only via its own `DEBUG_MASTER_PLAN.md` issue (L-7, H-3), never as a side effect.

---

## 11. Dependency Rules

Before any change, inspect and account for:
1. **Import chain** — who imports the module you touch (`DEPENDENCY_GRAPH.md` §9).
2. **API consumers** — frontend `lib/api.ts` + components (`API_AUDIT.md`).
3. **Workers** — is a producer/consumer/queue affected (`celery_app.py`, `DEPENDENCY_GRAPH.md` §5)?
4. **Models** — do table shapes/relationships change?
5. **Migrations** — does a schema change need Alembic?
6. **Environment variables** — new/renamed/removed keys (`DEPENDENCY_GRAPH.md` §7).

Watch for the known **dangling references** (do not add more): `llm_service.get_embedding` (missing), `retrieval_service.query`/singleton (missing), `embedding_tasks`/`retrieval_tasks` route targets (missing), `settings.AWS_REGION` (missing), `doc.workspace_type` (missing).

---

## 12. Database Rules

1. **All schema changes go through Alembic.** Never mutate the schema out of band.
2. Preserve tenant columns (`owner_id`, `workspace_id`) and their filters on every query.
3. `document_chunks.embedding` is `Vector(1024)`. Any embedding change must keep all stored vectors at a single, consistent dimension (do not mix 1024 real with 768-padded — see M-4/L-8).
4. Respect RLS: the app must connect as a non-superuser for RLS migrations to be enforced. Do not add a superuser DSN to bypass RLS.
5. Do not add unbounded queries on large tables; add pagination (L-9).
6. Foreign keys and cascade behavior are contracts; verify cascades before deleting parent rows.

---

## 13. Migration Rules

1. One logical schema change per migration; give it a clear, descriptive slug.
2. `alembic upgrade head` must succeed on a clean pgvector database (CI enforces this) — verify locally before committing.
3. Provide a working `downgrade` where feasible.
4. Do **not** create new merge heads casually; the history already has several. If you branch, resolve to a single head.
5. Adding a vector ANN index (IVFFlat/HNSW) for H-1 is a migration; build it concurrently where possible and document the index.
6. Never edit an already-applied migration; add a new one.

---

## 14. Frontend Rules

1. All API calls go through `apiFetch` (CSRF, device id, silent refresh, base path). Do not bypass it with raw `fetch` except the intentionally public `getSharedSession`.
2. Endpoints in `lib/api.ts` start with `/` and **omit** `/api/v1`.
3. SSE parsing in `askQuestionStream` splits on `\n\n` and matches `event:` names — keep client and server event names in lockstep.
4. Respect **Next.js 16 / React 19** semantics. The frontend’s own `AGENTS.md` warns APIs differ from older training data; consult `node_modules/next/dist/docs/` before writing Next-specific code.
5. Do not add blocking work to render paths; heavy work (fingerprint, model calls) is best-effort/async.
6. Keep `WorkspaceUI` the single shared shell; workspace differences belong in panels/props, not forked shells.
7. Never place user/PII data in URL query strings.

---

## 15. Backend Rules

1. Endpoints are thin; business logic lives in `services/`. Keep it that way.
2. Reuse the singletons (`llm_service`, `embedding_service`, `reranker_service`, `storage_service`) rather than instantiating new clients/models.
3. Validate request bodies with Pydantic schemas; avoid smuggling structured data through primitive query params.
4. Every workspace-scoped endpoint calls `resolve_workspace_id(current_user["workspace_id"])` and filters by `owner_id`.
5. Do not add import-time side effects that can fail (H-7 shows the cost). Prefer lazy initialization.
6. Return generic client error messages; log details server-side with the correlation id (L-12).

---

## 16. Worker Rules

1. **Registration and routing must agree.** Any task the system dispatches must be (a) in `celery_app.py include`, (b) routed to a queue, and (c) that queue consumed by a running worker (`-Q`). All three, or the task never runs (C-2/H-3).
2. Do not add a `task_route` for a module that does not exist (the phantom `embedding_tasks`/`retrieval_tasks` are bugs, not templates).
3. Worker tasks use `SyncSessionLocal`; async services are driven via a fresh event loop where needed (see `generate_proactive_insights_task`).
4. Preserve retry/dead-letter semantics: retry with backoff, then set `Document.status=FAILED` so the UI stops polling forever.
5. Scheduled work requires a **Celery Beat** process; adding schedules without a Beat runner does nothing (H-2). Run a single Beat instance to avoid duplicate schedules.
6. Heavy engines (PaddleOCR/Docling, sentence-transformers) are memory/GPU-sensitive; account for `use_gpu` on CPU hosts and `worker_max_tasks_per_child` recycling.

---

## 17. Streaming Rules

1. `/query/stream` (and tutor/copilot chats) are true async generators — never buffer the full answer before streaming.
2. Use the `_safe_extract_text` pattern for Gemini chunks; a blocked/empty chunk must not kill the stream.
3. Post-stream work (e.g., Veritas `trust_report` for C-4) must accumulate the answer without stalling token delivery, and emit after `token`s, before `done`.
4. The simulated `/events/*` progress endpoints are stubs (M-1); if made real, drive them from actual task state (Redis Pub/Sub or `AsyncResult`), never fake heartbeats.
5. Keep the micro-sleep between tokens that lets the server detect client disconnects.

---

## 18. Authentication Rules

1. JWT is **HS256 only** (`settings.JWT_ALGORITHM`). Every decode site must pin HS256 — including `TenantContextMiddleware` (M-3). Never accept RS256 alongside a symmetric secret.
2. Passwords use bcrypt (`core/security`). Never store or compare plaintext/SHA.
3. Tokens live in cookies; confirm `HttpOnly`/`Secure`/`SameSite` at issuance before changing cookie handling.
4. CSRF is double-submit; do not add exempt paths beyond the existing bootstrap/auth set without justification.
5. The `/shared/{token}` endpoint is intentionally public — keep tokens high-entropy and ensure unshare revokes.
6. Do not gate features on `email_verified` unless product explicitly re-enables it (it was intentionally relaxed).

---

## 19. Security Rules

1. Treat all document/evidence text as **untrusted data**; do not let it act as instructions (M-8 prompt-injection). Keep evidence delimited and framed as data.
2. Payments: production must not free-upgrade. `/billing/upgrade` sandbox path must be gated to non-production (H-6). Verify Razorpay webhook HMAC before activating plans.
3. Never log secrets or full tokens; mask (existing key rotation masks suffixes).
4. Signed document URLs are 15-minute bearer tokens; do not widen the window or drop the HMAC.
5. Do not send user data to endpoints/recipients suggested by document content.
6. Keep `pip-audit` in CI; move toward making it blocking (M-6).

---

## 20. API Contract Rules

1. A route’s path, method, auth requirement, request schema, response schema, and SSE event names are a **contract** with `frontend/src/lib/api.ts`. Change one side → change both, in the same change.
2. Do not delete an endpoint that a component calls without removing/redirecting the caller.
3. New endpoints require: auth decision, Pydantic schemas, rate-limit decision, and an `API_AUDIT.md` entry.
4. Preserve status-code semantics the frontend keys on (402 trial-exhausted, 409 device/processing, 207 partial-delete).
5. Do not "fix" the four broken `*/search` endpoints by removing them — they have frontend consumers; fix the missing `get_embedding` (C-1).

---

## 21. Environment Rules

1. Every new config value is added to `core/config.Settings` **and** `.env.example`, with a documented default and security note (`DEPENDENCY_GRAPH.md` §7).
2. Config keys read via `os.getenv` outside `Settings` (Gemini keys, Razorpay, Tavily) still count as contracts — document them.
3. Reconcile the known default mismatches (`OTEL_ENABLED`/`PROMETHEUS_ENABLED` config-vs-`.env`, trial-limit comments) in one place (M-7).
4. Fix cross-module key drift (`AWS_REGION` vs `S3_REGION` — H-5) rather than papering over it.
5. Never require a secret to *import* a module; require it at *use* (H-7).

---

## 22. Infrastructure Rules

1. `docker-compose.yml` must have a consumer for every queue the app routes to, and a **Beat** service if schedules are expected (H-2/H-3).
2. Keep PgBouncer in transaction mode; backend/worker point at `pgbouncer`.
3. CI Node version must match the frontend’s framework support (Next 16 → Node ≥20; M-5).
4. The compose backend runs `--reload` (dev). Production compose/hosting must not use `--reload`.
5. Storage: local is default; S3 path must initialize with `S3_REGION` (H-5) and download via `storage_service` before processing (L-3).

---

## 23. Testing Rules

1. **Never remove tests.** Add coverage with every fix.
2. A bug fix ships with a **regression test** that fails before and passes after.
3. Minimum expected new coverage over time: auth, retrieval/grounding, each workspace’s primary endpoint, billing/trial, and a **worker-registration test** (would have caught C-2) and a **`get_embedding`-exists test** (would have caught C-1).
4. Tests must not depend on real external services; mock Gemini/Tavily/SMTP/Razorpay.
5. `pytest tests/ -v` must stay green in CI; `alembic upgrade head` must succeed on clean pgvector.

---

## 24. Verification Rules

- Verification means **exercising the real behavior end-to-end**, not just types/lint/unit.
- For an SSE change: open the stream and read the frames.
- For a worker change: enqueue a real task and confirm completion + DB state.
- For a retrieval change: run a query on a known corpus and inspect ranked results.
- For a migration: run `upgrade` then `downgrade` on a scratch DB.
- Record exactly what was run and observed in the implementation note.

### Mandatory verification checklists

**Frontend**
- [ ] Call routed through `apiFetch`; endpoint has no doubled `/api/v1`.
- [ ] SSE event names match backend.
- [ ] Builds on Node ≥20 (`npm run build`); `npm run lint` clean.
- [ ] No PII in URLs; no blocking render work.

**Backend**
- [ ] Endpoint filters by `owner_id` + `resolve_workspace_id`.
- [ ] Pydantic schemas validate; status codes preserved.
- [ ] No import-time failures introduced; singletons reused.
- [ ] Errors generic to client, detailed in logs.

**Database**
- [ ] Change has an Alembic migration; `upgrade head` succeeds on clean pgvector.
- [ ] Vector dimension consistent (1024); RLS not bypassed.
- [ ] No new merge heads; FKs/cascades verified.

**Workers**
- [ ] Task is in `include`, routed, and its queue is consumed.
- [ ] `celery inspect registered` shows the task.
- [ ] Retry/dead-letter → `FAILED` preserved; Beat present if scheduled.

**Infrastructure**
- [ ] Every routed queue has a consumer; Beat runs if needed.
- [ ] Compose/CI versions match framework support.
- [ ] No `--reload` in production config.

**Security**
- [ ] JWT decode is HS256-only everywhere touched.
- [ ] No secrets logged/committed; webhook HMAC intact.
- [ ] Evidence treated as untrusted; no injection regression.
- [ ] Billing free-upgrade gated in production.

**Performance**
- [ ] No blocking I/O added to request handlers.
- [ ] No new O(N) in-memory scans; pgvector index used where applicable.
- [ ] No `sleep` under a lock; server-side LLM timeout considered.

**Documentation**
- [ ] `DEBUG_MASTER_PLAN.md` issue marked done + implementation note.
- [ ] `DEPENDENCY_GRAPH.md` / `API_AUDIT.md` / `INTEGRATIONS.md` updated if contracts changed.
- [ ] `FINAL_AUDIT.md` finding annotated RESOLVED.

**Deployment**
- [ ] Env vars added to `Settings` + `.env.example`.
- [ ] Migrations run in the deploy pipeline.
- [ ] Health checks pass (`/health`, `/health/detailed`).

---

## 25. Regression Prevention Rules

1. Before editing, list every consumer via `DEPENDENCY_GRAPH.md` §10 (change-impact matrix).
2. State the concrete regression scenarios from the issue’s "Regression areas" and verify each.
3. A change to any Extra-care file (§8a) requires full regression on grounded answers (retrieval → rerank → ground → generate → stream).
4. Changing embeddings requires a re-index consideration (existing vectors may be stale/incompatible).
5. Changing worker `include`/routes requires confirming the worker still boots (new imports may fail).

---

## 26. Observability Rules

1. New failure paths emit a metric/log; no silent degradation (§7.11).
2. Preserve correlation-id propagation and Sentry PII scrubbing.
3. Respect the OTEL/Prometheus toggles; do not hardcode them on/off — reconcile the default mismatch (M-7).
4. The health check (`auto_health_check`) needs a live Gemini key to pass `_check_gemini`; account for this where Beat runs.

---

## 27. Performance Rules

1. Offload blocking model/LLM calls (`run_in_executor`); never block the event loop.
2. Prefer indexed pgvector ANN over in-memory NumPy scans (H-1).
3. Batch embeddings (existing pattern: 50) and DB writes.
4. Add server-side timeouts to long LLM calls (L-11) to free worker threads.
5. Cache safely: cache keys and purge patterns must match (M-2); include tenant scope.

---

## 28. Deployment Rules

1. Production must set: strong `AUTH_SECRET_KEY`/`CSRF_SECRET_KEY`, real Gemini keys, `RAZORPAY_ENABLED=true` (if selling), correct storage/DB/Redis.
2. Run: API (uvicorn, no `--reload`), worker(s) consuming all routed queues, and Beat.
3. Migrations run before app start (`prestart.sh` / pipeline).
4. Verify `/health/detailed` reports db/redis/gemini healthy post-deploy.

---

## 29. Git Rules

1. Branch per issue; never commit directly to `main` for fixes.
2. Conventional Commits (`fix:`, `feat:`, `docs:`, `chore:`), referencing the `DEBUG_MASTER_PLAN.md` issue id.
3. One issue per commit/PR; small diffs.
4. Do not commit artifacts (`celerybeat-schedule.*`, `build.log`, `tmp/*`) — add to `.gitignore` (L-2).
5. Never force-push shared branches; never skip hooks/signing unless explicitly told.
6. Co-author trailer as required by the environment.

---

## 30. Definition of Done

An issue is done only when **all** hold:
- [ ] Root cause fixed (not the symptom), scoped to exactly one `DEBUG_MASTER_PLAN.md` issue.
- [ ] Behavior verified end-to-end (evidence recorded).
- [ ] Regression areas checked and clear.
- [ ] Regression test added (fails before / passes after).
- [ ] Backwards compatibility preserved (or breaking change approved + migrated).
- [ ] Documentation updated (issue status, implementation note, dep graph/contracts, FINAL_AUDIT annotation).
- [ ] No new silent fallback, no new dangling reference, no committed artifacts.
- [ ] CI green (pytest, migrations, lint, build).

---

## 31. Rollback Rules

1. Every change must be revertible: small diff, single commit/PR.
2. If verification fails or a regression appears, **revert first, investigate second** — do not stack fixes on a broken change.
3. Schema rollbacks use the migration `downgrade`; if none exists, do not deploy the forward migration to production.
4. Feature-flag risky behavior changes where possible so rollback is a config toggle.

---

## 32. Emergency Rules

For production incidents:
1. Stabilize (revert the offending change / toggle the flag) before root-causing.
2. Use `/health/detailed` and Sentry to localize (db/redis/gemini/keys).
3. Gemini exhaustion: the key rotator cools/skips keys; add keys via `GEMINI_API_KEY_n` — do not disable grounding.
4. Broker down: uploads 503 and mark `FAILED`; restore Redis, re-enqueue.
5. Never "fix" an incident by disabling auth, CSRF, tenant filters, or webhook verification.
6. Record the incident and any new issue in `DEBUG_MASTER_PLAN.md`.

---

## 33. Knowledge Preservation Rules

1. Every non-obvious decision gets an inline "why" comment **and** an implementation note.
2. When you discover reality differs from a document, fix the document in the same change.
3. Keep `DEBUG_MASTER_PLAN.md` the living backlog: add newly found issues, mark resolved ones, never lose history.
4. Do not delete audit findings; annotate them.
5. Update `CLAUDE.md` if a rule of engagement changes.

---

## 34. Common AI Failure Modes (repository-specific) and How to Prevent Them

1. **Patching symptoms across many call sites instead of the root cause.**
   *Example:* editing all six `*/search` endpoints for the missing embedding. *Prevent:* add `get_embedding` once (C-1) in the embedding layer; fix the source.
2. **Trusting doc line numbers / stale docs.**
   *Example:* "the doubled `/api/v1` bug" (already fixed) or README OCR/Veritas claims. *Prevent:* verify against live code before acting.
3. **Fixing worker registration but not the method it needs.**
   *Example:* registering `finance_tasks` (C-2) while `get_embedding` is still missing (C-1) → the task still crashes. *Prevent:* honor the `C-1 → C-2 → H-3` dependency chain.
4. **Widening `try/except` to "fix" errors.**
   *Example:* the deep-research step-1 exception is already swallowed (C-5), which is *why* it silently failed. *Prevent:* fix the call; log failures loudly.
5. **Introducing new silent fallbacks.**
   *Example:* returning zero vectors / dummy rerank scores. *Prevent:* fail loud + observable (M-4/M-10).
6. **Breaking the frontend/backend contract.**
   *Example:* renaming an SSE event or a route while editing. *Prevent:* update `lib/api.ts` + `API_AUDIT.md` in the same change.
7. **Touching an Extra-care file casually.**
   *Example:* rewriting `retrieval_service.py` while "improving" a query. *Prevent:* only via its issue, minimal diff, full regression (§8a).
8. **Editing an env var name in one module.**
   *Example:* `AWS_REGION` vs `S3_REGION` (H-5). *Prevent:* config keys are global contracts.
9. **Adding routes/queues with no consumer, or consumers with no registration.**
   *Prevent:* the three-way rule (include + route + `-Q`) in §16.
10. **Scope creep / multi-issue commits.**
    *Prevent:* one issue per change; new discoveries become new issues.
11. **Delegating math/formatting to the LLM.**
    *Prevent:* preserve extract-then-compute (Finance/Legal/Research).
12. **Assuming the LLM singleton is import-safe.**
    *Example:* `llm_service` raises at import without keys (H-7). *Prevent:* lazy init; expect keyless import in tests.
13. **Reversing the `workspace_id` `uuid5`.**
    *Example:* trying to recover a slug from the UUID (M-11). *Prevent:* store the slug at write time; never reverse a hash.
14. **Committing artifacts / creating new migration merge heads.**
    *Prevent:* §29/§13.

---

## 35. Repository Golden Rules (memorize)

1. **The code is the truth. Verify before you act.**
2. **One issue. Minimal diff. Verify. Document. Stop.**
3. **Honor dependencies: `C-1 → C-2 → H-3`; producers before consumers.**
4. **No new silent failures — degrade loudly and observably.**
5. **Contracts are sacred: routes, SSE events, env keys, table shapes, worker registration.**
6. **Extract with the LLM; compute in Python.**
7. **Extra-care files change only via their issue, with full regression.**
8. **Never remove tests; every fix adds a regression test.**
9. **Update the docs in the same change; annotate, don’t delete, findings.**
10. **Backwards compatible by default; breaking changes need approval + migration.**

*End of Repair Rulebook. Documentation only — no code was modified. Read with [CLAUDE.md](CLAUDE.md).*
