# DocuMindAI — Production Readiness Progress

Living log for the phased production-readiness effort. Read this at the start of every session.

---

Status-only log. Stable project context (stack, commands, conventions, constraints)
lives in [CLAUDE.md](CLAUDE.md). Engineering process lives in
[docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md](docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md).

---

## Established Baseline (do NOT re-investigate)

Verified earlier in this effort — treat as settled:

- Backend emits exactly **1** SSE `done` event per request (raw capture).
- Exactly **1** `WorkspaceUI` instance mounts (`CREATE I1`, `MOUNT I1`) — StrictMode double-mount ruled out.
- Assistant duplicate **root cause = side effect inside a `setState` updater** (React double-invokes updaters). Fixed by moving the persist behind `responseRef`. 4/4 clean generations.
- OCR verified end-to-end: image-only PDF → PaddleOCR → grounded answer w/ page citation, Trust 95%.
- HR verified: 3 resumes → ranked 95/50/15 with cited per-skill evidence + CSV export.
- Trial gate works (402 at 10/10) but is enforced on `/query/stream` **only**.
- PgBouncer is correctly **not** in the request path when `DATABASE_URL` targets Supabase.
- Measured: embed ~2s/chunk, bge-m3 load 65.7s, retrieval 0.92s, LLM gen 11-12s, OCR doc 240s.

---

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| 1 — Critical Release Blockers | 🔄 IN PROGRESS | see below |
| 2 — System Reliability | ⬜ Not started | |
| 3 — RAG Pipeline Audit | ⬜ Not started | partially covered by prior audit |
| 4 — Performance Engineering | ⬜ Not started | bottlenecks already measured |
| 5 — Security Audit | ⬜ Not started | prior audit found root Docker user, ENV string-match |
| 6 — Scalability Audit | ⬜ Not started | known: ~30 concurrent stream ceiling |
| 7 — Workspace Audit | ⬜ Not started | General+HR verified; Legal partial; 4 untested |
| 8 — Response Quality | ⬜ BLOCKED | gated behind 1-7 |
| 9 — Developer Experience | ⬜ Not started | |
| 10 — Regression Testing | 🔄 Continuous | |

---

## Release Gate

- [ ] Every P0 resolved
- [ ] Every P1 resolved
- [ ] All seven workspaces operational
- [ ] Provider layer resilient
- [ ] Streaming reliable
- [ ] RAG pipeline verified end-to-end
- [x] OCR verified — image-only PDF → PaddleOCR → cited answer
- [ ] Legal / HR / Finance / Study / Research / Exam workspaces verified  *(HR done)*
- [ ] Security audit complete
- [ ] Performance audit complete
- [ ] No known regressions

---

## P0 Register

| ID | Title | Status |
|---|---|---|
| P0-1 | LLM provider: 404 aborts request without rotating across 21 keys | ✅ **RESOLVED & VERIFIED** |
| P0-2 | Legal Risk Report unreachable — `processContract()` never called | 🔄 Frontend code applied; **runtime verification blocked by P0-7/P0-8** |
| P0-3 | Container image 18.8 GB; bge-m3 downloads 4.3 GB at import | ⬜ Open |
| P0-4 | Supabase credential in git history + plaintext `.env` — needs rotation | ⬜ Open (**owner-access-required**) |
| P0-5 | DB connection budget (30 API + 8×15 worker + 15 beat) vastly exceeded Supavisor session-mode cap of 15 | ✅ **RESOLVED & VERIFIED** |
| P0-6 | **NEW** — All 21 Gemini keys return `429 ResourceExhausted`; no LLM generation possible | ⬜ Open (**owner-access-required**) |
| P0-7 | **NEW** — 7 of 9 Celery task modules use the **async** engine via `asyncio.run()`; fails `got Future attached to a different loop` on ~every 2nd task | ⬜ Open |
| P0-8 | **NEW** — `legal_tasks.py:35` analyses a **hardcoded simulated contract string**; the uploaded document's text is never read | ⬜ Open |
| P0-9 | **Cross-tenant exposure.** `workspace_id` is a shared category slug, not a tenant key; 18 tables had no `owner_id` | 🟡 **Reads FIXED & VERIFIED** (`abf84a2`); worker writes land with P0-7 |
| P0-10 | **NEW** — `backend/.env` `DATABASE_URL` has a **double colon** (`pooler.supabase.com::6543`); host tests fail and the stack dies on next restart | ⬜ Open (**owner-access-required**, 1 char) |

---

## Session Log

### 2026-07-31 — Phase 1 (partial)

**P0-1 RESOLVED.** `llm_service.py::_execute_with_rotation` had no branch for
model-availability errors; they hit `else: raise e` and aborted on the FIRST key,
defeating the rotation loop. Added a `_MODEL_UNAVAILABLE_MARKERS` branch that
rotates without mis-marking the key rate-limited/invalid, and raises the new typed
`ModelUnavailableError` only once ALL keys have rejected the model.

Verified by forcing a nonexistent model:
- swept all 21 keys (`1/21` … `21/21 keys have rejected it`)
- raised `ModelUnavailableError` in 10.8s with a precise message
- **key health after sweep: `{'total':21,'available':21,'cooling':0,'invalid':0}`** — no poisoning
- real generations succeeded again with the ORIGINAL model config unchanged
- 3 runs: 1 user + 1 assistant row each, `DUPLICATES: NONE`
- backend suite: **100 passed**

**Also confirmed:** the doubled user bubbles in earlier screenshots were the test
harness double-submitting while the composer was busy — NOT an app defect. DB shows
1 user row per run across 13 runs; clean screenshot shows `RCRUN-3` exactly once.

**Environment lesson recorded:** the Next.js dev error overlay caches stale errors.
A screenshot showed a `window is not defined` error at `WorkspaceUI.tsx:823` from
already-deleted instrumentation; both host and container files verified at 0
occurrences. Reload clears it. Do not trust the overlay without checking the file.

**Not done this session:** P0-2, P0-3, P0-4; duplicate-response regression still
4 dev / 0 prod runs against the 10+10 bar.


### 2026-07-31 — Phase 1 continued (P0-2 partial)

**Docs synchronized.** `CLAUDE.md` rewritten as stable context only (stale test count,
resolved backlog, `.agents/` refs, old doc paths removed; Required Context merged in).
`PROGRESS.md` is now status-only. Directive is canonical at
`docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md`.

**P0-2 code applied, NOT verified.** Added `promoteLegalDocumentToContract()` in
`WorkspaceUI.tsx`, called from the existing READY-transition handler, guarded to
`workspaceType === "legal"`, fire-and-forget so it cannot delay/fail uploads.
`processContract` imported from `lib/api.ts`. `tsc --noEmit` EXIT 0.
End-to-end verification did NOT complete — see blockers below.

**REGRESSION I INTRODUCED AND REVERTED.** The earlier `--max-tasks-per-child=0`
compose flag is invalid for Celery's prefork pool — billiard asserts
`maxtasks is None or (int and > 0)`, so the worker crash-looped
(`AssertionError` at billiard/pool.py:241) and the queue backed up to **134 tasks**.
Reverted; a comment now documents why the flag must not be re-added. The bge-m3
reload cost is real but belongs in Phase 4 with measurement, not an unmeasured flag.
Root cause of my miss: I changed the worker command but never restarted the worker
and verified it came up.

**NEW BLOCKER P0-5.** Draining the 134-task backlog exhausted Supabase's session-mode
pooler: `(EMAXCONNSESSION) max clients reached in session mode - max clients are
limited to pool_size: 15`. Worker concurrency and pool sizing exceed what the hosted
pooler allows under backlog. Needs sizing analysis (Phase 6 territory, but it blocks
verification now).

**Still open from before:** duplicate-response regression at 4 dev / 0 prod runs.


### 2026-07-31 — Engineering organization set up (no product code touched)

**Directive frozen.** `docs/engineering/PRODUCTION_READINESS_DIRECTIVE.md` synchronized to the
final version and marked frozen at the top. Additions over the prior copy, each traceable to a
real failure this effort produced: the *"Own your regressions out loud"* operating principle
(durable marker required, not just a chat note); *"restart it and confirm it comes up healthy"*
added to **Verify the real thing**; the docs-drift check promoted into Execution Model step 1;
backlog-drain and fire-and-forget scenarios added to Phase 2; the
agent-actionable / owner-access-required / owner-decision-required taxonomy on deliverable
item 9; Docker + production deployment boxes on the Release Gate. **Do not edit it again**
unless a real failure exposes a missing rule.

**Ten subagents created** in `.claude/agents/`: `test-runner`, `security-reviewer`,
`code-reviewer`, `performance-profiler`, `rag-pipeline-tracer`, `docs-sync-checker`,
`workspace-qa`, `infra-health-checker`, `release-readiness-checker`,
`response-quality-reviewer`. All are verify/review/diagnose only — implementation stays in the
main thread. Each carries this project's real incidents (P0-1 rotation ownership + the
`_mark_key_failed` mismatched-reuse trap, P0-2's shared-handler location, the
`--max-tasks-per-child=0` billiard crash-loop, the `EMAXCONNSESSION` pooler cap, the pgbouncer
`LISTEN_PORT` bind-vs-probe mismatch, the Turbopack stale-bundle false negative, the harness
double-submit false positive, the GIN benchmark that measured the wrong thing, the
`len(app.routes)` proxy claim that was simply wrong). Delegation policy — including the
exclusive-ownership boundaries — is in `CLAUDE.md` → **Engineering Organization**. No
orchestrator agent exists; agents cannot invoke each other.

**`.gitignore` fixed.** `.claude/` excluded everything, so project-level agents could never be
shared. Changed to `.claude/*` plus `!.claude/agents/` — git does not descend into an excluded
directory, so a negation under `.claude/` would have been a silent no-op. Verified: exactly the
ten agent files are now visible to git; `settings.local.json`, `skills/`, and `worktrees/`
remain ignored.

**Cleanup.** Removed the empty stray directory `backend/tests/test_route_registration.py;C`
(malformed shell redirect artifact, untracked, no content).

**Observation, not changed:** `backend/scripts/run_worker_windows.ps1:38` still passes
`--max-tasks-per-child=0`. It is harmless *there* because `--pool=solo` ignores the setting —
but it is a latent trap: switching that script to a prefork pool reproduces the exact billiard
`AssertionError` crash-loop. Recorded in `infra-health-checker`; left alone because it works
today and is outside this task's scope.

**No product code was modified this session.** P0-2 remains code-applied / verification
incomplete; P0-5 remains the blocker in front of it.


### 2026-07-31 — Phase 1 continued (P0-5 RESOLVED; four new P0s found)

**P0-5 RESOLVED & VERIFIED.** The earlier characterization ("worker backlog exhausts it")
was **wrong**. The backlog was a victim, not the cause. Measured with worker and beat
**stopped**, the API alone held **15/15** connections (14 idle, 1 active): `db/session.py`
hardcoded `pool_size=10, max_overflow=20` — a 30-connection ceiling — against Supavisor
**session mode**'s project-wide cap of 15, and SQLAlchemy *retains* pooled connections, so
the ceiling was held permanently rather than spiking. The `/health` endpoint's unpooled
`psycopg2.connect()` (every 10s) could never open its 16th connection, which is why the
backend container sat `unhealthy` for **19 hours**.

Contributing factors, all measured:
- sync engine passed **no** pool args → SQLAlchemy defaults 5+10 = **15 per process**
- worker `--concurrency` unset → Celery defaulted to `os.cpu_count()` = **8** children
- no fork safety: `sync_engine` is built at import in the parent and inherited by every child

Fix (repo-local): connection budget moved into `core/config.py` as four settings
(`DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`, `WORKER_DB_POOL_SIZE=1`, `WORKER_DB_MAX_OVERFLOW=1`),
`--concurrency=2` pinned in compose, and a `worker_process_init` handler calling
`sync_engine.dispose(close=False)` (close=True would sever sockets shared with the parent).

Verified: connections **15/15 → 2/15**; `/health` → `{"api":"ok","db":"ok","redis":"ok"}`
(first time in 19h); worker healthy, `RestartCount=0`; backend suite **105 passed**
(100 baseline + 5 new guards in `tests/test_db_connection_budget.py`). The guard bites —
re-running with the original 10/20 fails: *"Default connection budget is 37, over 15."*

**Pooler architecture decision (evidence-based).** Grep confirms the app uses **no**
session-scoped Postgres features: no `pg_advisory*`, no `LISTEN`/`NOTIFY`, no `CREATE TEMP`,
no `SET SESSION`/`SET LOCAL`; the only lock is a `threading.Lock` in `llm_key_rotation.py`.
Prepared statements are already disabled for pooler hosts (`session.py:39-41`). Nothing
requires session mode. Conversely `query.py:215` + `:568` hold the `get_db` session for the
entire `StreamingResponse`, so in session mode every concurrent SSE stream pins a server
connection for the full 11-12s generation. **Transaction mode (6543) is the correct
production posture** — but switching alone would NOT have fixed this, because the ~165-
connection demand was unbounded in either mode. Sizing the budget was the actual fix.
The port change lives in `backend/.env` → **owner-access-required**.

**NEW P0-6 — Gemini quota exhausted.** All 21 keys return `429 ResourceExhausted`. Confirmed
with **raw `google.generativeai` calls bypassing the rotator**, so this is real upstream
quota, not rotator cooldown bookkeeping — the rotator is behaving correctly.
Blocks every LLM-dependent verification. **owner-access-required.**

**NEW P0-7 — async engine inside sync Celery tasks.** `legal_tasks.py` (and
`finance/hr/study/research/export/ocr_tasks`, **7 of 9**) use `AsyncSessionLocal` via
`asyncio.run()`. Each call creates a new event loop, so a pooled asyncpg connection from a
previous loop fails with `RuntimeError: got Future attached to a different loop`. Violates
the CLAUDE.md invariant *"Async API / sync workers … Never mix."* The two modules that work
(`document_tasks`, `audio_tasks`) correctly use `SyncSessionLocal` — which is exactly why
uploads reach READY but Legal never produces a contract.
**Proven independent of the P0-5 fix** by controlled A/B: identical failure at the new 3/2
and the original 10/20 settings (run1 OK, run2 FAIL, run3 OK — it fails ~every other task).

**NEW P0-8 — Legal analyses fabricated text.** `legal_tasks.py:35` assigns a hardcoded
`"Simulated text. 1. Confidentiality… 2. Liability capped at $50."` and never reads the
uploaded document; `doc` is fetched only for `doc.filename`. Every contract would yield the
same two fake clauses. A real `_get_document_text()` helper exists at `legal.py:54` and is
unused. Direct violation of the **Loud degradation** invariant.

**NEW P0-9 — cross-tenant exposure (security-reviewer verdict: CONFIRMED P0).**
`auth.py:51,202` set `workspace_id` to the literal `"general"` for every user, so
`resolve_workspace_id()` yields one constant UUID
(`33d76fbe-437c-5b72-989c-798243045681` = `uuid5(DNS,"general")`) shared by all — verified
live: 3 users, 3 distinct document owners, **one** workspace UUID. `models/legal.py` and
`legal.py` contain **0** occurrences of `owner_id`, so the documented
*"filter on `owner_id` AND the workspace UUID"* invariant is unrepresentable, not merely
omitted. `tenant_guard.validate_retrieval_scope` has **zero call sites** despite documenting
itself as mandatory. RLS is inert (`rolbypassrls=True`; disabled on all `legal_*` tables;
the `app.current_workspace_id` setting the policies key on is never set).
Exploitable today: `/legal/contracts/compare` → `_get_document_text` (`legal.py:54-61`)
filters on `document_id` **only** and returns document text to any authenticated user;
`/legal/contracts/{id}/approvals` (`legal.py:215`) is an unscoped cross-tenant **write**.
Systemic — Finance/Study/Research models also lack `owner_id`. `documents.py` and
`processing_events.py:57-61` are correctly scoped and are the reference pattern.

**Correction accepted:** my initial reading of the fallback path was inverted.
`resolve_workspace_id` passes valid UUIDs through unchanged, so the
`claims.get("workspace_id", user_id)` **fallback is the safe path**; the hardcoded **claim**
is the defect.

**Recorded, deliberately NOT fixed (out of scope):** worker cold start took **30m24s** vs the
documented ~390s because the container healthcheck (`celery inspect ping`, every 15s) spawns
a full process whose import chain re-loads bge-m3 — `embedding_service.py:127` constructs the
`SentenceTransformer` singleton eagerly at import. Pre-existing; Phase 2/4 territory.

**Stopped here** per the standing instruction to stop on a new verified P0 blocker.


### 2026-08-01 — P0-9 reads fixed (`abf84a2`)

**Tenancy model decided (architectural, evidence-based):** per-user `owner_id`.
`documents` already uses it correctly (11 sites — the reference pattern), billing is
per-`User` (`plan`, `trial_queries_used`, `subscribed_at`), and `Organization` /
`OrganizationUser` exist but have **no `User.org_id` FK**, so the org model is unwired
aspiration. Org scoping remains additive later; `owner_id` does not block it.

**Root cause, restated precisely.** `User.workspace_id` is
`Column(String(50), default="general")` — *the user's active workspace tab*, a UI state
slug. It was never a tenant key. Tenant filtering had been layered onto a field carrying
no tenant identity, which is why every user resolved to the same UUID.

**Fix — the session owns the decision, not the call site.** Adding `owner_id ==` to ~90
`WHERE` clauses would duplicate one decision 90 times and the 91st query would reopen the
hole. Instead: `TenantScoped` mixin + a `do_orm_execute` hook that injects
`owner_id = <current owner>` into every ORM SELECT on a scoped model (incl. eager loads
and joins). **Fails closed** — no scope raises `TenantScopeMissing` rather than returning
unfiltered rows; trusted internal work must opt out explicitly via `system_scope()`.
`get_current_user` binds the scope per request (ContextVar `.set()` without reset is
deliberate — Starlette gives each request its own Task/context, and a yield-dependency
would end the scope before the SSE generator finishes streaming).

Migration `b7c1d2e3f4a5`: `owner_id` NOT NULL + indexes on all 18 tables. All were
**empty**, so no backfill; it fails loudly rather than mis-assigning rows elsewhere.

**Runtime verification (not inspection):** two users minted real JWTs and went through the
actual `get_current_user` dependency — A saw only `ALICE-DOC`, B only `BOB-DOC`;
`system_scope` saw both; an unscoped query raised. Backend suite **105/105**.

**Deliberately NOT covered** (documented limits, in `tenant_scope.py`): raw `text()` queries
bypass the ORM hook, and writes still set `owner_id` explicitly — `NOT NULL` makes a missed
write fail loudly instead of storing an unowned row. The 12 worker write sites land with
P0-7, since those modules are already broken by the async/sync defect.

**NEW P0-10 — `backend/.env` typo blocks the stack.** `DATABASE_URL` reads
`...pooler.supabase.com::6543/postgres` — **double colon**. The 5432→6543 pooler switch was
applied but left an extra `:`. Effects: host `pytest` fails at collection with
`ValueError: invalid literal for int() with base 10: ':6543'`, and the running containers
still hold the pre-edit value from creation time, so **the stack dies on next restart**.
Proven to be the sole cause: supplying a corrected URL via env override (without touching
`.env`) gives **105/105**, which also confirms port 6543 works. One character; `.env` is
out of scope for me to edit.
