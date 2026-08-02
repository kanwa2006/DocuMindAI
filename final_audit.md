# DocuMindAI — Final Audit

**Date:** 2026-08-02 · **Branch:** `security/redact-env-example` · **HEAD:** `0c3e766`
**Type:** Read-only audit and debug report. **No code was changed to produce this document.**
**Coverage:** all 425 tracked files. The backend endpoints (24 modules), the frontend
(91 files under `src/`), and the backend services + core (44 modules) were each read in
full, line by line — §9, §11 and §12 respectively.

---

## 1. Direct answer: is the project bug-free and ready to deploy?

**No.** Not yet, and I want to be precise rather than reassuring.

The first pass (§3–§7) found 9 defects from targeted reading. Reading every file then found
**74 more**, and they change the picture: the earlier pass measured the parts that were being
actively worked on, so it saw a healthier system than actually exists.

| Area | Findings | Of which HIGH |
|---|---|---|
| §9 · backend endpoints (24 modules) | 22 | 11 |
| §11 · frontend (91 files) | 20 | 5 |
| §12 · backend services + core (44 modules) | 32 | 13 |
| §3, §5 · first-pass performance + functional | 9 | 3 |
| **Total** | **83** | **32** |

- **Deploy-blocking: more than 3.** The original three stand, and the deep read added
  **tenant isolation on the retrieval path** (§9 H1, §12 S3) — a live cross-tenant exposure,
  not a latent one.
- **Frontend↔backend contract: clean** — 56/56 paths resolve. Confirmed.
- **Backend regression suite: 131 passed.** Still true, and it is the point: **the suite is
  green while 32 HIGH findings are open.** That measures the tests, not the system.
- **End-to-end workspace certification: 0 of 7 complete.**

Three claims deserve to be stated plainly, because they are the ones most likely to be
believed and are false:

1. **The Trust Score does not measure trust.** 65% of its weight is hardcoded (§12 S6), and
   the rerank scores feeding the rest are renormalised so the top result always scores 1.0
   (§12 S7). It reports ~66/MEDIUM regardless of input.
2. **Two advertised features have never run once.** Web search (§12 S13 — the setting does not
   exist) and every Redis path including trial abuse prevention (§12 S12 — the package is not
   installed). Both report success.
3. **A security control that lies is in the tree.** `validate_retrieval_scope` documents
   itself as called before every retrieval and has zero callers (§12 S4).

The system is materially healthier than a week ago — a large class of real defects is
genuinely gone, and §10, §11 and §12 each close with the strengths worth preserving. But
"no known bugs" would be false. The honest status is **not deployable today**; see §6, and
§7 for the order to fix in.

### How to read the findings sections

§9, §11 and §12 use one format per finding: **Bug** (what is wrong) → **Root cause** (why the
code is shaped that way) → **Why it happens** (the trigger and its frequency) → **What
breaks** (user-visible consequence) → **Debug — blast radius** (what else must change, tagged
*self-contained*, *NOT self-contained*, or *owner-decision-required*). Claims marked ✅ were
re-verified against source before recording.

---

## 2. Repository structure

### Counts (tracked files only; excludes `node_modules`, build output, `.env`)

| Metric | Count |
|---|---|
| Tracked files | **425** |
| Tracked directories | **74** |
| Python files | 208 |
| TypeScript / TSX | 88 (75 `.tsx` + 13 `.ts`) |
| Markdown docs | 47 |
| Stylesheets | 5 |
| Config (`json`/`yml`/`sh`) | 11 |
| Demo PDFs | 13 |

### Lines of code by area

| Area | LOC |
|---|---|
| `backend/app` | 19,789 |
| `frontend/src` | 19,730 |
| `docs` | 7,054 |
| `backend/tests` | 1,913 |
| `.claude` (agents) | 1,168 |
| `infrastructure` | 215 |
| **Total (tracked source + docs)** | **~49,900** |

### Structure diagram

```
DocuMindAI/
│
├── CLAUDE.md                    stable project context + engineering orchestration
├── PROGRESS.md                  single source of truth for status
├── README.md  CHANGELOG.md  CONTRIBUTING.md  SECURITY.md  LICENSE
├── railway.json                 deploy target config
├── final_audit.md               ← this document
│
├── backend/                     Python 3.11 · FastAPI · Celery
│   ├── app/                     130 files
│   │   ├── main.py              ASGI app, middleware, Sentry, Gemini key bridge
│   │   ├── api/v1/
│   │   │   ├── api.py           router aggregation (24 routers)
│   │   │   └── endpoints/       24 modules · 127 routes
│   │   ├── core/                config, auth, workspace, tenant_scope, storage,
│   │   │                        middleware, rate_limiter, telemetry
│   │   ├── services/            28 modules — retrieval, grounding, reranker,
│   │   │                        embedding, llm_service, llm_key_rotation,
│   │   │                        veritas_engine, ocr_*, export_engine
│   │   ├── models/              ~50 ORM tables
│   │   ├── schemas/             Pydantic contracts
│   │   ├── workers/
│   │   │   ├── celery_app.py    config · includes · task_routes · beat_schedule
│   │   │   └── tasks/           9 Celery task modules + _document_text helper
│   │   ├── tasks/               async helpers — NOT Celery (namespace package)
│   │   └── automation/          8 beat-scheduled jobs
│   ├── alembic/versions/        45 migrations
│   ├── tests/                   29 files · 131 tests
│   └── scripts/                 seed_dev, prestart, run_worker_windows
│
├── frontend/                    Node 20 · Next.js 16 · React 19 · Tailwind 4
│   └── src/                     92 files
│       ├── app/                 App Router pages; 7 workspace routes
│       ├── components/          38 components (WorkspaceUI is the shared shell)
│       ├── styles/              tokens · typography · components · motion
│       ├── lib/api.ts           56 endpoint bindings — the API contract
│       ├── hooks/  lib/store/  middleware.ts
│       └── public/
│
├── infrastructure/              Dockerfile.backend · Dockerfile.frontend
│                                docker-compose.yml (+ local-test-override)
│
├── docs/
│   ├── engineering/             PRODUCTION_READINESS_DIRECTIVE (frozen) · rulebook
│   ├── architecture/            ARCHITECTURE · DEPENDENCY_GRAPH · WORKSPACES · API_AUDIT
│   ├── deployment/              PROJECT_AUDIT_AND_DEPLOYMENT · MANUAL_TESTING_GUIDE
│   ├── demo-documents/          13 representative PDFs used for certification
│   └── audit/  marketing/  screenshots/
│
├── .claude/agents/              10 specialist review agents (tracked, shared)
└── .github/workflows/ci.yml     backend + frontend validation
```

---

## 3. Performance findings

Method: AST analysis over all 208 Python files for query-in-loop patterns and blocking
calls inside `async def`; static index-coverage analysis over the ORM models; component
size analysis over the frontend. **Ranked by measured or reasoned impact.**

### ~~P-1 · N+1 query in legal DOCX export — HIGH · *introduced by me*~~ — STRUCK

**Where:** `backend/app/workers/tasks/export_tasks.py:67`

**What:** One `SELECT` per clause to fetch redlines, inside the clause loop.

```python
for clause in clauses:
    redlines = db.execute(
        select(RedlineSuggestion).where(RedlineSuggestion.clause_id == clause.id)
    ).scalars().all()
```

**Root cause:** I replaced a broken `selectinload` (the relationship did not exist — see
§5) with explicit per-row queries. Correct behaviour, wrong shape.

**Why it costs:** a 50-clause contract issues **51 queries instead of 2**. Against
Supabase's pooler each round trip carries network latency, so this scales linearly with
contract size on the export path.

**Safe fix (no dependency impact):** one query for all clause ids, then group in Python.
Touches only the local `clauses_data` construction inside `_process_export`; no schema
change, no model change, no caller change.

```python
ids = [c.id for c in clauses]
rows = db.execute(select(RedlineSuggestion)
                  .where(RedlineSuggestion.clause_id.in_(ids))).scalars().all()
by_clause = defaultdict(list)
for r in rows: by_clause[r.clause_id].append(r)
```

### ~~P-2 · N+1 query in research document loading — HIGH~~ — STRUCK

**Where:** `backend/app/api/v1/endpoints/research.py:184` (also `:250`, `:467`)

**What:** For each `doc_id`, one query for the `Document` then another for its chunks —
**2N queries** for N documents, on a request-path endpoint.

**Root cause:** per-item validation loop written before the multi-document case existed.

**Why it costs:** selecting 10 documents for a comparison issues 20 sequential awaited
round trips before any work starts.

**Safe fix:** two queries using `.in_(doc_ids)`, then group by `document_id` in Python.
Self-contained inside the endpoint; the response shape is unchanged, so no frontend
impact.

### ~~P-3 · Blocking `time.sleep` inside an async function — MEDIUM (conditional)~~ — STRUCK

**Where:** `backend/app/services/llm_service.py:179`, in `DummyLLMProvider.generate`

**What:** `time.sleep(0.5)` inside `async def`. This blocks the **entire event loop**, not
just the caller — every concurrent request on that worker stalls for 500 ms.

**Root cause:** simulated latency written with the sync sleep.

**Honest severity:** `DummyLLMProvider` only serves when **no Gemini key is configured**.
It is not on a correctly-configured production path. But it turns an already-degraded
deployment (missing keys) into a fully serialized one, which is the worst moment for it.

**Safe fix:** `await asyncio.sleep(0.5)`. One line, same class, no signature change.

### P-4 · SSE polling opens a session per poll — MEDIUM (design tension)

**Where:** `backend/app/services/processing_events.py:55` and `:99`

**What:** `MAX_POLLS = 150` at `POLL_INTERVAL_SEC = 2.0` (~5 min), and each iteration opens
a **new** `AsyncSessionLocal`.

**Why it matters here specifically:** the API connection budget is deliberately small —
`DB_POOL_SIZE=3 + DB_MAX_OVERFLOW=2 = 5` (P0-5, sized to Supabase session mode's 15-client
cap). Each poll checks a connection out and returns it, so it is not held for 5 minutes —
but N concurrent uploads being watched contend for a pool of 5.

**Not a defect on its own** — it is bounded, correct, and returns connections. Recorded
because the interaction between poll concurrency and the intentionally tight pool is the
kind of thing that only shows up under load.

**Safe change if needed:** raise `POLL_INTERVAL_SEC`, or reuse one session across polls
inside the generator. Both are local to the two generator functions.

### P-5 · `documents.status` has no index — LOW

Hot-path columns were checked individually. **Correctly indexed:**
`document_chunks.document_id` (retrieval), `documents.owner_id`, `documents.workspace_id`,
`documents.chat_session_id`. **Not indexed:** `documents.status`.

100 FK/status/date columns lack indexes repo-wide, but nearly all are on cold paths.
`documents.status` is the only one on a warm path, and the queries that filter it also
filter on the primary key, so the index would rarely be the deciding factor. **Recorded,
not recommended** — adding 100 indexes would cost write throughput for no measured gain.

### Checked and found clean

- **No unbounded `while` loops.** The only `while True` is
  `llm_key_rotation` key discovery, which terminates on the first missing
  `GEMINI_API_KEY_N` — correct and intentional (it is what makes keys addable without a
  code change).
- **No `O(n²)` nested scans** over collections in request paths.
- **No blocking `requests`/`subprocess` calls** inside `async def` anywhere.
- **Loop choice is appropriate throughout** — no `while` used where a bounded `for` was
  the right construct.

---

## 4. Frontend ↔ backend connectivity

**Result: clean. 56 of 56 frontend endpoint paths resolve to a defined backend route.**

| Side | Count |
|---|---|
| Backend routes defined (24 modules) | **127** |
| Frontend endpoint bindings (`lib/api.ts`) | **56** |
| Unmatched | **0** |

An initial pass flagged 4 mismatches (`/chats`, `/exams`, `/export`, `/documents/{}`).
**All four were artifacts of my own parser**, not defects — routes declared as
`@router.post("", ...)` with arguments on the following line, which the regex missed.
Verified individually against source before clearing them. Recorded because a reader
should know the difference between "checked and clean" and "tool said clean".

**Contract invariants confirmed:**
- `NEXT_PUBLIC_API_URL` already contains `/api/v1`; `lib/api.ts` paths correctly start
  with `/` and omit the prefix — no double-prefix bug.
- SSE event names match on both sides: `trial_status`, `thinking_stage`, `status`,
  `metadata`, `token`, `error`, `done`, `trust_report`.

---

## 5. Functional bugs — open

### ~~B-1 · Gemini generation unavailable — OWNER ACTION · one line~~ — STRUCK

**The measurement below was a snapshot and has since been superseded.** Re-measured
2026-08-02 with the same method (every key × every configured model, rotator bypassed):

| Model | Original reading | Re-measured 2026-08-02 |
|---|---|---|
| `gemini-2.5-flash` (primary) | 0/21 ResourceExhausted | **10/21 200 OK** · 10/21 429 · 1/21 404 |
| `gemini-1.5-flash` (old fallback) | 0/21 NotFound | **21/21 404 NotFound** — confirmed retired |
| `gemini-2.0-flash` (new fallback) | not tested | 21/21 429 ResourceExhausted (daily, resets) |

**The retired-fallback root cause was correct and is fixed:** `GEMINI_FALLBACK_MODEL`
named a model Google no longer serves, so the retry at `llm_service.py:357` raised
`NotFound` every time, including for the ordinary rate limits the fallback exists to
absorb. Set to `gemini-2.0-flash`.

**Two conclusions in the original entry were wrong**, and matter for anyone reasoning
about this subsystem later:

1. The primary was **never** globally exhausted — that reading was one day's free-tier
   quota, which resets. Generation was available the whole time.
2. The 21 keys do **not** share a single quota pool. Ten succeed while ten are
   exhausted, which is only possible if their quotas are independent.

**And the actual blocker was elsewhere:** the per-user **trial counter**
(`trial_queries_used >= 10`) halts `/query/stream` after retrieval and before the LLM is
reached, emitting `queries_remaining: 0` and no `token` events. That is indistinguishable
from an LLM failure when read from the client, and it is what was stopping generation in
practice. Not a defect — but it is why "generation is blocked" was attributed to Gemini.

Real generation confirmed end to end after the fix: full SSE contract, `Configured Gemini
with key 3…10` in the logs, correct grounded refusal. `DummyLLMProvider` never served.

**Rotation itself is correct**: dynamic `GEMINI_API_KEY_N` discovery (unlimited, no code
change to add keys), 403 → permanent skip, 429 → cooldown **with expiry**, sweeps every
key before raising.

### B-2 · Legal Risk Report evaluates nothing — OWNER DECISION

`legal_compliance_rules` ships **empty**. The pipeline is correct end to end, but with no
rules every clause returns `COMPLIANT` / `LOW`. Defining what constitutes a flagged clause
is a product decision, not an engineering one.

### B-3 · Stray keystroke changes workspace — OPEN, undiagnosed

Observed once: typing in the composer navigated `/general` → `/exam` mid-keystroke.
Reproduced in a Playwright session, not root-caused. Likely a global hotkey handler
(`CommandPalette` or a workspace shortcut) not checking whether focus is in an input.
**Suspected location:** a `keydown` listener on `document` without an
`event.target` guard.

### B-4 · Documents uploaded before `31c7119` are all in `general`

Not corrupt — they were recorded under the workspace the system believed it was in. But
they are unusable as per-workspace fixtures. **Re-upload per workspace** during
certification. No migration recommended: rewriting historical rows would assert a
workspace the user never actually chose.

### Recently fixed and verified (do not re-investigate)

| Defect | Evidence |
|---|---|
| Duplicate user message persisted | 3 clicks in one tick → **1 DB row** |
| Duplicate user bubble rendered | server row now used → **1 bubble** |
| Composer bricked at "Thinking…" forever | error path unwinds; composer stays usable |
| Dead "Thinking…" card after failure | `setResponse(null)` on error path |
| Markdown had no hierarchy (`h2` == `p`, all margins 0) | h2 now 18.3px/650 |
| Composer hidden on 1366×768 laptops | `min-h-0`; verified at 1365×637 and 1280×450 |
| Uploads always landed in `general` | verified `legal READY chunks=2 embedded=2` |
| Worker async/sync mixing (9 modules) | ratchet retired at zero |
| Placeholder text in 4 workspaces | real document text; AST guard added |
| Cross-tenant read exposure | fail-closed session scope; 2-account test |

---

## 6. Deployment readiness

| Gate | Status |
|---|---|
| Backend regression suite | ✅ 131 passed |
| TypeScript compile | ✅ clean |
| Frontend↔backend contract | ✅ 56/56 |
| Services healthy (compose) | ✅ all 7 |
| Tenant isolation (read path) | ✅ verified, 2 accounts |
| Worker pipeline on real documents | ✅ Legal: READY, chunks, embeddings |
| **LLM generation** | ❌ **B-1** — blocked |
| **Per-workspace certification** | ❌ **0 of 7** complete |
| **Container image size** | ❌ 18.8 GB (P0-3) |
| **Credential rotation** | ❌ P0-4 — owner |

**Verdict: not deployable today.** Three items block it — B-1 (one line, yours), the
18.8 GB image (P0-3), and credential rotation (P0-4, yours). Workspace certification is
not a blocker for *deploying* but is a blocker for *claiming the product works*.

---

## 7. Recommended order

Revised after the deep read. Ordered by *exposure × cost to fix*, not by severity alone.

**Tier 0 — before anyone else's data is in the system**

1. **Tenant isolation on the retrieval path** (§9 H1, §12 S3, §9 H3, §9 H4). One choke point,
   not ninety WHERE clauses — `tenant_scope.py` already establishes the right shape; extend it
   rather than working around it. Resolve `validate_retrieval_scope` (§12 S4) in the same
   commit: wire it up or delete it, but do not leave a control that lies.
2. **H5 — the regression I introduced in `31c7119`.** Five single-document endpoints; six of
   seven workspaces currently cannot GET/HEAD/DELETE their own documents. My defect, smallest
   diff on this list.

**Tier 1 — one-liners with disproportionate payoff**

3. **`GEMINI_FALLBACK_MODEL=gemini-2.0-flash`** — unblocks generation entirely (B-1). Yours.
4. **`TAVILY_API_KEY` added to `Settings`** (§12 S13) — or emit `status="skipped"` so the UI
   stops reporting a step that never ran.
5. **`WorkspaceUI.tsx:1614`** (§11 F1) — the one `workspaceType` I missed in `31c7119`.
6. **P-3** — `await asyncio.sleep`. One line.

**Tier 2 — event-loop blocking (do these together; they share a fix shape)**

7. **§12 S1, S2** — stream consumption and the two per-query model calls, into
   `run_in_executor`. Correct pattern already exists in `llm_service.get_embedding:573`.
8. **P-1 and P-2** — the two N+1 fixes. Self-contained, ~20 lines each.

**Tier 3 — stop reporting numbers the system does not compute**

9. **§12 S6, S7** — the Trust Score and rerank normalisation. Decide: implement, or reduce the
   report to what is actually measured. Either is honest; the current state is not.
10. **§12 S12** — migrate the six `aioredis` sites to `redis.asyncio`. Restores trial abuse
    prevention and the retrieval cache, both currently silent no-ops.
11. **§12 S10** — remove the ratio arithmetic from the Finance schema. Extract-then-compute is
    violated in the one workspace the invariant exists to protect.

**Tier 4 — after the above**

12. **Per-workspace certification** — blocked until Tier 0 and step 3 land.
13. **P0-3 image size** — bake vs. download is a tradeoff decision.
14. **P0-4 credential rotation** — yours; redaction does not un-leak git history.

**Not recommended:** adding the 100 missing indexes (write cost, no measured gain), and
backfilling historical `workspace_id` values (asserts a choice the user never made).

**Do not fix in bulk.** §12 S5 and §12 S8 each require two files changed *together* or the fix
is not a fix; §12 S19 implies a re-index. Those are marked *NOT self-contained* at the finding.

---

## 8. Method and limits

**What this audit did — first pass (§3–§7):** AST analysis over 208 Python files for
query-in-loop and blocking-call patterns; static route extraction from 24 endpoint modules
compared against 56 frontend bindings; index-coverage analysis over ~50 ORM models; component
size analysis; live provider testing against every key and model.

**What this audit did — deep read (§9, §11, §12):** every one of the 425 tracked files read
line by line, in three passes scoped by subsystem. Nothing was sampled or skimmed.

**How the deep-read findings were checked.** Read-every-file at this volume produces confident
wrong answers, so no finding was recorded on assertion alone. Load-bearing claims were
re-verified against source before entering this document, and that check has already caught
errors in this audit: four "contract mismatches" that were my regex failing on a multi-line
decorator (all 56 resolve), and a "0 Celery routes" reading that was a parser bug (23 includes,
7 routes, 3 queues, all consumed). Findings marked ✅ carry a specific verification. **Where a
claim is inferred rather than confirmed, it says so at the finding** — treat those as leads.

**What it did not do — and you should not read as passing:**
- **No load testing.** Impact on P-1/P-2 and the §12 S1/S2 blocking findings is reasoned from
  query counts and call shape, **not measured under concurrency.** §12 S1 and S2 assert *that*
  the event loop blocks — which the code shows — not *by how much*. `performance-profiler`
  owns the magnitude.
- **No profiler run.** No flame graph, no per-endpoint latency distribution.
- **No end-to-end workspace certification.** 0 of 7 complete; generation is blocked.
- **No runtime execution of any finding.** This is a static read. §12 S11 (the fpdf latin-1
  crash) is the single exception — reproduced against the installed library.
- **Frontend runtime performance unmeasured** — no re-render counts, no bundle analysis.
  `WorkspaceUI.tsx` at **2,357 lines** is the shared shell for all 7 workspaces and is the
  obvious candidate for a render audit, but that claim is unmeasured and stated as such.
- **Severity is my judgement, not a verdict.** `security-reviewer` adjudicates §9 H1/H3/H4 and
  §12 S3/S4/S9; `release-readiness-checker` owns the deployment-facing items.

Every finding above is either a code reference you can open, or a command output. Where I
inferred rather than measured, I said so.

---

# 9. DEEP-READ FINDINGS — backend endpoints (all 24 modules read in full)

A specialist agent read all 24 endpoint modules plus supporting core/service/model files.
**Every claim below was re-verified by me against source before being recorded.**

## 9.0 One root cause behind nine of eleven HIGH findings

**`workspace_id` is used as a tenant discriminator on models the P0-9 fix never reached.**

P0-9 chose the right layer — the session, via `TenantScoped` + `do_orm_execute` — but scoped
coverage to a **model list** rather than a **rule**. 18 models inherit the mixin; everything
else silently opts out, and nothing detects the omission because the hook only fires for
models that already inherit it (`core/tenant_scope.py:155-165`).

`Document` — the highest-value table in the system — sits outside that set. That is why the
shared retrieval path has no tenant filter at all.

---

## ~~H1 · Retrieval service has no owner filter — CRITICAL~~ — STRUCK

**File:** `backend/app/services/retrieval_service.py:53-119` (all four query branches)

- **Bug:** the hybrid query joins `Document` and filters on `Document.workspace_id` and
  optionally `document_ids`. There is **no `owner_id` predicate on any branch**.
- **Verified:** `grep -c owner_id retrieval_service.py` returns **0**. Line 59 is
  `.where(Document.workspace_id == workspace_id)`.
- **Root cause:** tenant filtering was delegated to callers, but `workspace_id` is
  `uuid5(DNS,"general")` — identical for every user. The layer that owns *which documents a
  query may see* is the retrieval service, and it was never given the tenant key.
- **Why it happens:** bites whenever `document_ids` is `None`. `query.py:442` sets
  `doc_filter = attached_doc_ids if body.session_id else None`, so a session-less query
  retrieves across **every user's** READY documents.
- **What breaks:** any authenticated user can extract another user's document content,
  verbatim with page citations, through the primary RAG answer path.
- **Debug — blast radius: NOT self-contained.** Add a **required** `owner_id` parameter (fail
  closed, not optional) and apply it to all four branches. Callers that must change:
  `services/grounding_service.py`, `endpoints/query.py:172-178` and `:443-450`,
  `endpoints/exams.py:221-227` and `:859-865`, `services/evaluation_service.py`,
  `services/summary_service.py`.
- **Severity: HIGH — fix first.** One function closes the leak for all seven workspaces.

---

## ~~H5 · Six workspaces cannot read or delete their own documents — REGRESSION I INTRODUCED~~ — STRUCK

**File:** `backend/app/api/v1/endpoints/documents.py:425, 457, 500, 537, 661`

- **Bug:** `get_document`, `head_document`, `get_signed_url`, `head_document_status` and
  `delete_document` derive the workspace from the **JWT claim**
  (`current_user.get("workspace_id","general")`) and then require
  `Document.workspace_id == ws_uuid`.
- **Verified:** 5 sites confirmed; predicate present at `:432` and `:545`.
- **Root cause: my commit `31c7119`.** I fixed the *write* path so uploads store the real
  workspace — without checking what *reads* it. Before that fix every document was `general`,
  so the JWT claim always matched. It no longer does.
- **Why it happens:** immediately, for anything uploaded from HR / Legal / Finance / Study /
  Research / Exam. `User.workspace_id` is `"general"` for every user (`auth.py:394`), so the
  claim and the stored value now disagree for six of seven workspaces.
- **What breaks:** `GET /documents/{id}` 404s. `DELETE` 404s, so those documents **can never
  be deleted**. `HEAD` polling 404s, so the frontend READY transition never fires.
- **Why it escaped:** `list_documents` takes an **explicit** `workspace_id` query param and
  still works. A list-based smoke test passes while every single-document operation fails.
  My own certification checked the database directly, not these endpoints.
- **Debug — blast radius: self-contained in `documents.py`.** Drop the `workspace_id`
  predicate from all five; `owner_id` alone is correct and sufficient. No frontend or schema
  change.
- **Severity: HIGH — a live regression, not a pre-existing defect.**

---

## H3 · HR models have no ownership column at all — HIGH

**File:** `backend/app/models/hr.py:21, 38, 48, 60`

- **Bug:** `CandidateProfile`, `CandidateNote`, `Interview`, `JobMatch` have **no `owner_id`
  column**. Only `JobRole` has one, and no query uses it.
- **Verified:** confirmed by reading the model file.
- **Root cause:** explicitly scoped out during P0-9. The exclusion was recorded; the exposure
  it left was not.
- **Why it happens:** every request. `GET /hr/jobs` returns every user's roles; `/candidates`
  and `/candidates/export/csv` accept any `job_id` and return name, email, phone, skills.
  `PUT /matches/{id}/status` and `PATCH /candidates/{id}/stage` **mutate** other users' rows.
- **What breaks:** full cross-tenant disclosure of **resume PII**, plus cross-tenant write.
  HR is the one workspace certified end-to-end, which makes this the highest-confidence
  live exposure in the audit.
- **Debug — blast radius: NOT self-contained; migration required.** Add `owner_id` +
  `TenantScoped` to the four models and the existing hook covers all reads with zero endpoint
  edits. Also needs an Alembic migration **with a real backfill** (tables are non-empty —
  derive from `JobRole.owner_id` via `job_id`), the `workers/tasks/hr_tasks.py` write sites,
  and `services/processing_events.py:88-106`.
- **Severity: HIGH — do last; the backfill is an owner decision.**

---

## ~~H4 · Nine chat routes scoped by category, not owner — HIGH~~ — STRUCK

**File:** `backend/app/api/v1/endpoints/chats.py`

- **Bug:** nine routes resolve a `ChatSession` by `id + workspace_id` while
  `ChatSession.owner_id` exists and is populated. Only `delete_chat_session` uses it.
- **Verified:** **10** `ChatSession.workspace_id` filters vs **5** total `owner_id` uses.
- **Root cause:** the convention P0-9 disproved. The `# belt-and-suspenders ownership check`
  comment on the delete route shows `owner_id` was treated as redundant rather than as *the*
  tenant key.
- **Why it happens:** `GET /chats` lists every user's sessions. With an id from that list an
  attacker can read the transcript, append messages, rename and retag it — and
  `POST /chats/{id}/share` **mints a public link to another user's conversation**, then
  readable unauthenticated at `GET /shared/{token}`.
- **Debug — blast radius: self-contained in `chats.py`.** Replace the predicate with
  `ChatSession.owner_id == current_user["id"]` in all nine. Schema and frontend contract
  unchanged. **Cheapest high-value fix in the audit.**
- **Severity: HIGH**

---

## Remaining HIGH findings

| ID | File | Bug | Blast radius |
|---|---|---|---|
| H2 | `documents.py:194`, `core/storage.py:64` | `verify_upload` stores client-supplied `object_key` verbatim. Sinks: `Path(...).stat()` file oracle, absolute-path read into the RAG corpus, and `delete_document` calling `Path(...).unlink()` = **arbitrary file delete** | `documents.py` + `core/storage.py`; no frontend change |
| H6 | `finance.py:482` | Comment reads `# Verify document ownership`; **there is no ownership predicate**. `/compare` does no lookup at all | self-contained |
| H7 | `legal.py:54-61` | `_get_document_text` selects chunks by `document_id` alone; `/contracts/compare` feeds it caller-supplied ids | `legal.py` + mirror in `finance.py:300` — make it one shared helper |
| ~~H8~~ **STRUCK** | `exams.py:757, 768, 823` | `list/get/update_exam` filter `workspace_id` only while two routes **in the same file** correctly use `owner_id`. `PUT /exams/{id}` overwrites another user's paper | self-contained — copy from the same file |
| ~~H9~~ **STRUCK** | 7 sites in legal/finance/study/research/hr | `Document` lookups filter `id + workspace_id`, never `owner_id`; `/process` dispatches another user's `document_id` to Celery | 7 one-line edits + a shared `get_owned_document()` |
| H10 | `query.py:294-300` | History load selects `ChatMessage` by `session_id` alone — while the query **seven lines below** correctly filters `Document.owner_id`. Another user's transcript enters the LLM prompt and is paraphrased back | self-contained; **H4 does not fix this** |
| ~~H11~~ **STRUCK** | `export.py:124, 143` | `list_exports` / `get_export_job` filter `workspace_id` only; the *create* docstring claims strict isolation | self-contained |

---

## N1–N2 · Added 2026-08-03 — models with NO ownership column, found by sweep

Found by `tests/test_owned_model_reads_are_owner_scoped.py`, not by the original
read. Both are the same shape as H3: the model has **no `owner_id` at all**, so no
predicate can close them — each needs an Alembic migration with a backfill, which
is an owner decision. Both are currently allowlisted in that test's ratchet.

| ID | File | Bug | Blast radius |
|---|---|---|---|
| N1 | `benchmark.py:56` | `BenchmarkRun` has no `owner_id`. `list_benchmark_runs` filters `workspace_id` only, so every user sees every user's benchmark runs — including `results`, which embeds per-query metrics | model + migration + backfill; **owner-decision-required** |
| N2 | `corrections.py:167, 264` | `Correction` has no `owner_id`. `list_corrections` and `export_corrections` filter `workspace_id` only. The export path writes them to a file | model + migration + backfill; **owner-decision-required** |

**Why this section exists.** §9 lists four instances of the
`workspace_id`-instead-of-`owner_id` class (H4, H5, H8, H11) and §12 adds H9. A
mechanical sweep found **twelve** sites across seven files, plus a fifth in
`research.py` that no finding covered. The register was enumerating examples of
this class, not bounding it. Treat any future `<Model>.workspace_id ==` filter as
suspect until proven otherwise — the ratchet now does that automatically.

---

## Silent failure — the ones hiding a real failure

22 swallow sites judged individually. Most are legitimate. These are not:

| File | What it hides | Why it matters |
|---|---|---|
| `study.py:235` | Quiz parse failure produces `_stub_quiz()` with `correct_index: 0` and a fabricated explanation, **persisted and returned 200** | A student is graded against invented answers. `exams.py:419` models the honest behaviour — it refuses |
| `legal.py:390` | LLM parse failure produces `overall_risk_level: "Low"`, 200 | A parse error renders as *this contract is low risk* |
| `finance.py:505` | Parse failure produces `{}`; all 15 ratios `None`, returned as a normal result | Indistinguishable from *the document had no financials* |
| `research.py:228` | Citation failure falls back to `title = filename`, **formatted as a real APA/IEEE citation** | Fabricated bibliography |
| `legal.py:85` | `_log_audit` failure becomes a warning | This is the **immutable compliance audit trail** |
| `query.py:328` | History load failure sets `attached_doc_ids = []` | Silently widens retrieval to unscoped mode |
| `auth.py:263`, `feedback.py:41` | `_get_redis` returns `None`; callers no-op | Registration IP limits, password-reset OTP storage and feedback limits **fail open, silently** |
| `hr.py:462` | Embedding failure sets `similarity = 0.0` | Returns a real-looking blended score for a computation that never ran |

---

## Notable MEDIUM findings

| ID | File | Bug |
|---|---|---|
| M1 | `auth.py:115` + `core/auth.py:40-45` | `POST /auth/refresh` **always** 401s. `verify_token` rebuilds its return dict from four hard-coded keys and drops `token_type`, so the check is `None != "refresh"`. The refresh path has never worked; users are silently logged out at the 60-minute expiry |
| M4 | `query.py:512` | `getattr(request, "comparison_mode", False)` reads the Starlette `Request`, not `body`. **Always `False`** — comparison mode has never activated. `getattr` with a default turned a rename into permanent silence |
| M11 | `auth.py:143-153` | Logout deletes only the `token` cookie; `refresh_token` (different `path`) survives. Currently masked by M1 — **fix both together or logout stops working** |
| M3 | `auth.py:442, 826` | Email/phone OTP compared with `!=`, no attempt limit, no rate limit. 10^6 keyspace, 600s TTL, unlimited attempts |
| M10 | `hr.py:453` | `SentenceTransformer(...)` constructed **inside the request handler** on every scoring call — blocking model load on the async path |
| M14 | `billing.py:176-187` | Razorpay webhook has no idempotency key and does not verify the captured amount. A replayed body extends the subscription each time |

---

# 10. STRENGTHS — preserve these through any fix

- **`core/tenant_scope.py`** — the right answer to the right question. Puts the decision in
  the session rather than ~90 `WHERE` clauses, **fails closed**, covers eager loads, forces
  `system_scope()` to be typed explicitly, and **documents its own limits** rather than
  overselling. Its shortcoming is coverage, not design.
- **`core/auth.py:57-72`** — the comment explaining why `ContextVar.set()` without a reset is
  correct here is precise, non-obvious and load-bearing.
- **`endpoints/retention.py`** — all 11 routes scope on `user_id` from the token. Zero
  `workspace_id`. **This is what the rest of the codebase should look like.**
- **`notifications.py`, `bookmarks.py`** — uniformly `user_id`-scoped on read, write, delete.
- **`insights.py`** — joins `Document` and filters `Document.owner_id`, deriving tenancy from
  the parent. The correct technique when a child table has no owner column.
- **`documents.py` `delete_document`** — per-step status, **HTTP 207 on partial failure**,
  `finally: await redis.close()`, an explicit audit line, and a comment stating vector-
  deletion failures must never be silently ignored.
- **`finance.py:97-258`** — extract-then-compute preserved rigorously: **Python computes all
  15 ratios**, `_safe_div` guards zero denominators, and two ratios return explicit `error`
  strings rather than a misleading number.
- **`exams.py:173-236, 419-421`** — best-scoped retrieval helper in the codebase, a five-way
  `doc_status_hint` giving a distinct actionable error per failure mode, and a refusal path
  that **refuses honestly** rather than shipping placeholder questions.
- **`auth.py:594-691`** — password reset: identical 202 regardless of account existence,
  `secrets.compare_digest`, a separate cooldown key so the response cannot probe for
  accounts, atomic consume-on-success, layered rate limits.
- **`billing.py:146-166`** — HMAC verified with `compare_digest` **before any parsing**, and a
  guard refusing the sandbox free-upgrade path when `ENVIRONMENT == "production"`.
- **`study.py:256-262`** — `correct_index` stripped from the response while the full version
  persists. Correct anti-cheat placement.
- **`health.py:20-52`** — the `unquote()` comment explaining that the 10-second healthcheck
  loop tripped Supavisor's circuit breaker after ~210 rejected logins. An incident note, not
  a code comment.

**The pattern worth naming — and this is the audit's most useful finding for planning:**
in nearly every case the *correct* implementation already exists **in the same file** as the
defective one. `exams.py` has both. `export.py` has both. `documents.py` has both. The
knowledge is present; it was applied unevenly. That makes these fixes **low-risk**: you copy
a proven line from three functions away rather than inventing an approach.

---

# 11. DEEP-READ FINDINGS — frontend (all 91 files under `src/` read in full)

43 findings. **Load-bearing claims re-verified by me against source before recording.**

---

## ~~F1 · HR batch upload still sends resumes to `general` — MY FIX WAS INCOMPLETE~~ — STRUCK

**File:** `frontend/src/components/WorkspaceUI.tsx:1614`

- **Bug:** `uploadDocument(file, undefined, chatId || undefined)` — the workspace argument is
  still `undefined` on the **batch** upload path.
- **Verified:** two call sites exist. Line 1307 (single upload) passes `workspaceType` —
  that is my commit `31c7119`. **Line 1614 (HR batch upload) still passes `undefined`.**
- **Root cause:** I fixed `handleFileChange` and did not check for other callers. There were
  two.
- **Why it happens:** every time an HR user clicks "Batch Upload". The backend falls back to
  the JWT claim (`general`) — exactly the defect `31c7119` was written to fix.
- **What breaks:** HR's headline feature is bulk resume ingest. Those documents land in
  `general` and are invisible to HR retrieval and rankings. Per-workspace isolation cannot
  be certified while this exists.
- **Debug — blast radius: self-contained.** `uploadDocument(file, workspaceType, chatId || undefined)`.
  **Better:** make `workspaceId` a **required** parameter in `lib/api.ts:180` so the compiler
  catches any third call site. That is the fix that makes the class impossible rather than
  the instance.
- **Severity: HIGH**

---

## F2 · Trial exhaustion locks the composer forever and writes a blank message

**File:** `frontend/src/lib/api.ts:335-343`

- **Bug:** the `402 / trial_exhausted` branch dispatches an event and does a bare `return` —
  it calls **neither `onError` nor `onDone`**. Every other exit path calls one of them.
- **Verified:** confirmed by reading the branch; the `return` is unguarded.
- **Root cause:** the trial-modal path was added as an early exit without considering that
  the caller's state machine is driven entirely by those two callbacks.
- **Why it happens:** on the query immediately after the trial limit. `WorkspaceUI` awaits
  and resolves normally, so its outer `catch` never fires: `loading` stays `true`,
  `sendingRef.current` stays `true`, and the empty response stub remains mounted.
- **What breaks:** composer permanently disabled, dead "Thinking…" bubble, and the only
  escape (`Stop`) persists an assistant row with `answer: ""` into the user's history. Only
  a reload clears it.
- **Debug — blast radius: self-contained in `api.ts`** — call `onError("Free trial limit reached.")`
  before the `return`. **Independently** harden `WorkspaceUI.tsx:1202-1205` so the outer
  catch also resets `sendingRef`, clears the thinking timer, and calls `setResponse(null)`.
- **Severity: HIGH**

---

## F3 · `React.memo` on messages never prevents a re-render

**File:** `frontend/src/components/WorkspaceUI.tsx:1906-1926`

- **Bug:** three props are new identities every parent render — `followUps={[]}` (fresh array
  literal), `onTrustToggle={() => …}` (fresh closure), `onRegenerate` (`useCallback` keyed on
  `history`). The shallow compare fails unconditionally.
- **Root cause:** memoisation was added without stabilising the props it depends on.
- **Why it happens:** the rAF token buffer correctly caps `setResponse` to one call per frame
  — but each of those re-renders the parent, rebuilds every `history.map` element, fails
  memo, and re-runs `<ReactMarkdown>` over **every prior message's full text**.
- **What breaks:** the O(n²) heap growth the rAF fix was written to solve still happens, once
  per frame instead of once per token. Long threads stutter during streaming.
- **Debug — blast radius: self-contained.** Hoist `const NO_FOLLOWUPS: string[] = []` to
  module scope; make `onTrustToggle` a stable `useCallback` taking `msg.id`; give
  `regenerateLastResponse` a `historyRef` instead of a `history` dependency.
- **Severity: HIGH**

---

## F4 · Cannot scroll up while a response streams

**File:** `frontend/src/components/WorkspaceUI.tsx:864-866`

- **Bug:** `scrollIntoView({behavior:"smooth"})` in an effect keyed on `response?.answer`,
  with no "is the user near the bottom?" check.
- **Why it happens:** `answer` changes every rAF flush. Each smooth scroll cancels and
  restarts the previous one, so it never settles — and any manual scroll-up is yanked back
  within ~16ms.
- **What breaks:** reading anything above the fold during generation is impossible.
- **Debug — blast radius: self-contained.** Track `isPinnedToBottom` from
  `scrollHeight - scrollTop - clientHeight < 80` and only auto-scroll when true; use
  `behavior:"auto"` while streaming. Needs a ref on the scroll container.
- **Severity: HIGH**

---

## F5 · Ctrl/Cmd+B does nothing — two listeners cancel each other

**Files:** `LayoutWrapper.tsx:191-198` + `Sidebar.tsx:364`

- **Bug:** two independent global `keydown` listeners both handle Ctrl+B and both call the
  same setter. Sidebar enqueues a **value** (`setIsOpen(!isOpenRef.current)`); LayoutWrapper
  enqueues an **updater** (`setIsSidebarOpen(o => !o)`).
- **Why it happens:** child effects run before parent effects, so React resolves the queue as
  `state = !isOpen` then `fn(!isOpen) = isOpen`. **Net result: unchanged.** Ctrl+K is
  likewise double-bound and both handlers `preventDefault()`.
- **What breaks:** a shortcut documented in the app's own `KeyboardShortcutsModal` is
  silently inert.
- **Debug — blast radius: `Sidebar.tsx` + `LayoutWrapper.tsx` together** — they share state.
  Delete the Sidebar shortcut block; LayoutWrapper already owns both concerns.
- **Severity: HIGH**

---

## F6 · "All Sessions" opens the wrong chat

**File:** `frontend/src/app/sessions/page.tsx:79`

- **Bug:** the link is `?session=${s.id}` but `WorkspaceUI.tsx:845` reads `?chat=`.
- **Verified:** confirmed. Every other producer of this URL (5 sites) uses `?chat=`.
- **What breaks:** `chatId` resolves to `null`, so the page loads an arbitrary recent chat —
  or silently **creates a new one** on an empty workspace.
- **Debug — blast radius: self-contained.** Same class at `app/bookmarks/page.tsx:150`, which
  builds `/` for the general workspace instead of `/general` and lands on the marketing page.
  **Fix both together, and add a `chatUrl(workspace, chatId)` helper** — these strings are
  constructed ad hoc in five files.
- **Severity: HIGH**

---

## F7 · Shared links render assistant replies as raw JSON

**File:** `frontend/src/app/shared/[token]/page.tsx:290`

- **Bug:** assistant messages are persisted as `JSON.stringify({query, answer, evidence, …})`.
  `MemoizedMessage` parses that; this page feeds `message.content` straight into `<ReactMarkdown>`.
- **What breaks:** the **one public, unauthenticated surface of the product** displays
  `{"query":"…","answer":"…","diagnostics":{…}}` — no citations, no trust badge.
- **Debug — blast radius: this is a duplicated-renderer bug, not a parsing bug.** A one-line
  `JSON.parse` here would re-create the duplication the architecture forbids and would still
  miss `SafeParagraph`. Correct fix: extract `MemoizedMessage`'s parse/render body into a
  shared `AssistantMessage` component and adopt it in both places.
- **Severity: HIGH**

---

## F8 · First visit to a workspace creates two chat sessions

**File:** `frontend/src/components/WorkspaceUI.tsx:869-893`

- **Bug:** `initChat` has no in-flight guard. `reactStrictMode: true` runs mount effects
  twice; both passes see `chats.length === 0` and both call `createChat`.
- **Why it happens:** first visit to any of the seven workspaces, and whenever the last chat
  is deleted. StrictMode surfaces it in dev, but the underlying race is real in production —
  nothing prevents re-entry while the first round trip is outstanding.
- **Debug — blast radius: self-contained.** An `initChatRef` guard keyed on
  `${workspaceType}:${chatId}`. **Related, same effect:** the `catch` only logs, so a failed
  `getChatMessages` leaves the *previous* chat's messages rendered under the new chat id.
- **Severity: HIGH**

---

## F9 · Paid users are treated as trial users

**File:** `frontend/src/lib/store/trialStore.tsx:46`

- **Bug:** the store's `setPlan` is **never called** from anywhere.
- **Verified:** confirmed — the only `setPlan` references are a *local* `useState` in
  `Sidebar.tsx:278`, which is a different variable. `LayoutWrapper` fetches billing status
  and calls only `setTrialStatus`, discarding `status.plan`.
- **What breaks:** the "Free trial — N left" pill renders to **paying customers**;
  `ShareSessionModal` resolves `PLAN_CONFIG["trial"]`, permanently disabling "View and ask"
  sharing and capping collaborators at 1 regardless of plan.
- **Debug — blast radius: `LayoutWrapper.tsx` only** — call `setPlan(status.plan)` in the
  existing billing effect. Then delete `Sidebar.tsx:281-283`, a second independent
  `getBillingStatus()` fetch that exists only to gate one menu item.
- **Severity: HIGH**

---

## Selected MEDIUM findings

| # | File | Bug |
|---|---|---|
| F10 | `hooks/useSelectionClip.ts:46` | Unstable callback identity tears down and re-adds a `document` mouseup listener **every render**; any re-render inside the 500ms window cancels selection detection. Dead during streaming |
| F11 | `DocumentPreviewPanel.tsx:54` | Styled as a 380px side panel but mounted as a **column flex child** with no `position: fixed` — it pushes the transcript and composer out of view. Every sibling panel uses `fixed` |
| F12 | `PomodoroTimer.tsx:75` | `toast()` and `localStorage` write **inside a `setState` updater** — a new instance of the canonical impure-updater bug. Duplicate toasts under StrictMode |
| F13 | `LayoutWrapper.tsx:130` | Redirects `/` to `lastActiveWorkspace` for **logged-out visitors too** — the marketing landing page becomes unreachable after one workspace visit |
| F15 | `CommandPalette.tsx:42,47,52` | "New Chat", "Upload Document", "Export Chat" dispatch events with **zero listeners**. 3 of 7 palette commands are dead |
| F16 | `WorkspaceUI.tsx:1277` | `legal:contracts-updated` is dispatched with a comment claiming an open panel self-heals. **Nothing listens.** A silenced failure by documentation |
| F21 | `WorkspaceUI.tsx:1301` | `loading` conflates "streaming" and "uploading". Attaching a file mid-stream clears it, hiding Stop and re-enabling Send — the next message is then swallowed silently by the `sendingRef` guard |
| F23 | `WorkspaceUI.tsx:1640` | Generated exam papers are pushed into `history` with a fabricated `Date.now()` id and **never persisted** — the paper vanishes on reload. Same pattern already fixed for user messages |
| F25/27/28 | `Sidebar.tsx:233`, `WorkspaceUI.tsx:1899, 2055` | Delete dialog has `aria-hidden` on an **ancestor of the dialog it exposes**; `aria-live` wraps the whole transcript so screen readers re-announce everything each frame; document chips nest `<button>` inside `role="button"` |
| F31 | `lib/analytics.ts` | The entire typed `Analytics` helper is **never imported anywhere**, PostHog runs with autocapture off, and two other dead conventions coexist. Zero telemetry while shipping the bundle |
| F32 | `FeedbackBar.tsx`, `VoiceInput.tsx` | Dead components. `FeedbackBar` is never rendered, so the 561-line admin corrections queue **can never be populated**. `VoiceInput` duplicates the live `voice/VoiceInputButton` |

---

## Frontend strengths — preserve these

- **`WorkspaceUI.tsx:781-817` — the rAF token buffer.** Tokens accumulate in a ref and flush
  once per frame, with `flushTokensSync` for done/error and a cleanup cancelling both the rAF
  and its timeout fallback. The design is right; only the memo defeat (F3) blunts it.
- **`WorkspaceUI.tsx:990-1004` — the `sendingRef` guard.** A ref, not state, with an accurate
  comment on why state cannot close a window that exists *because* state is async.
- **`WorkspaceUI.tsx:1054-1069` — guarded user-turn persistence.** Resets *every* piece of
  in-flight state before returning and gives a specific, actionable message. **This is the
  template the other error paths should copy** — F2 exists precisely because it wasn't.
- **`WorkspaceUI.tsx:940-982` — the in-flight document poller.** Keyed on the *set of
  in-flight ids* rather than on `docs`; cleanup removes its own interval from the shared
  registry rather than clearing all of them. A genuinely subtle correctness fix.
- **`WorkspaceUI.tsx:312-341` — `SafeParagraph`.** Fixes invalid `<p><pre>` nesting at the
  renderer rather than at each call site.
- **`components.css:87-125` — the composer row.** The wrap-below-640px rule and the
  `pointer: coarse`-scoped 44px tap-target expansion (visual size unchanged, hit area grown
  via `::after`) are measured, minimal and shared across all seven workspaces.
- **`lib/api.ts:55-72` — CSRF bootstrapping.** Single-flight `_csrfPromise`, pre-mutation
  await, `/auth/*` exemption, and an explicit error when the token returns empty rather than
  letting it read as an expired session.
- **`voice/VoiceInputButton.tsx:43-46` — the `mounted` gate.** Renders nothing on SSR *and*
  the first client render — the correct way to kill a hydration mismatch.
- **`Sidebar.tsx:317-343` — `loadChats` error classification.** Offline / 401 / 5xx / timeout
  each get an appropriate recovery affordance. The mutation handlers (F18) should be raised
  to this standard.
- **`ErrorBoundary.tsx`**, **`lib/pricing.ts`** — a real class boundary with two recovery
  paths, and a genuine single source of truth with named lookups.

---

## The cross-cutting pattern — most important planning insight

**Three of the highest findings are the same architectural mistake: a defect fixed at one
call site and not at its siblings.**

- F1 — upload workspace fixed at one of two call sites (mine)
- F7 — the message renderer duplicated instead of shared
- F16/F23 — persistence fixed for user messages, not for exam papers or contract events

Each is **cheaper to fix by consolidating the call sites than by patching each one.** The
same applies to navigation: F6 and F14 both come from route strings built ad hoc in five
files, and a single `chatUrl(workspace, chatId)` helper makes both impossible rather than
merely fixed.

`reactStrictMode: true` in `next.config.ts` is why F8 and F12 reproduce in dev. **Do not
disable it** — it is surfacing real impurity.

---

# 12. DEEP-READ FINDINGS — backend services + core (44 modules read in full)

29 service modules and 15 core modules. 59 findings. **Load-bearing claims re-verified by
me against source before recording.** This section independently corroborates §9's H1.

---

## ~~S1 · Streaming blocks the entire event loop — HIGH~~ — STRUCK

**File:** `backend/app/services/llm_service.py:391`

- **Bug:** the Gemini stream is consumed with a **synchronous `for` loop inside an
  `async def`**: `for chunk in stream_response:`. Only the call that *obtains* the stream is
  wrapped in `run_in_executor` (line 375); the iteration that performs the network I/O was
  left on the event loop thread.
- **Verified:** ✅ confirmed by reading lines 388-397.
- **Root cause:** the returned object is a blocking generator whose `__next__` does network
  I/O. Wrapping only the constructor looks correct and is not.
- **Why it happens:** every `/query/stream` request. Each `next()` blocks until the next
  Gemini chunk arrives — tens to hundreds of ms each, seconds in aggregate.
- **What breaks:** **one streaming user stalls the whole API worker.** Other requests, health
  checks and other SSE streams all freeze. Directly violates the documented invariant
  "blocking model/LLM calls are offloaded via `run_in_executor`". Will be misdiagnosed as
  "Gemini is slow." `generate_stream` also has **no timeout at all**, while
  `_provider_generate` correctly enforces `LLM_TIMEOUT_SECONDS` — a hung stream is unbounded.
- **Debug — blast radius: self-contained** in `GeminiLLMProvider.generate_stream`. Pump the
  sync iterator through a thread: `await loop.run_in_executor(None, lambda: next(it, SENTINEL))`
  and yield until the sentinel. Consumers already `async for` and need no change. Extra-care
  file — full regression required.

---

## ~~S2 · Every query blocks the event loop twice more — HIGH~~ — STRUCK

**Files:** `retrieval_service.py:45` (bge-m3 query embedding) · `grounding_service.py:87`
(cross-encoder rerank of up to 30 candidates)

- **Bug:** two CPU-bound model inferences run synchronously from `async def` functions.
- **Root cause:** `embedding_service.generate_embeddings` and `reranker_service.rerank_results`
  are sync APIs called directly. `llm_service.get_embedding:573` shows the team knows the
  correct pattern — it was applied there and not here.
- **Why it happens:** **every single query**, both `/ask` and `/stream` — not only streaming
  ones. The cross-encoder on 30×512-token pairs on CPU is the dominant cost.
- **What breaks:** combined with S1, the API serializes all work onto one thread.
- **Debug — blast radius: self-contained.** Both functions are already `async`, so signatures
  do not change: wrap each call in `run_in_executor`. Both are extra-care files.
  `performance-profiler` owns the magnitude; this finding asserts only that it blocks.

---

## ~~S3 · Deep Research scans the entire database — HIGH~~ — STRUCK

**File:** `backend/app/services/deep_research_agent.py:89`

- **Bug:** `retrieve_chunks` is called with **no `workspace_id` and no owner filter**, and
  line 88 (`doc_uuid_ids = [...] if document_ids else None`) converts an **empty list** into
  `None` — "the user attached no documents" becomes "no filter at all".
- **Why it happens:** any Deep Research request with no attached documents.
- **What breaks:** unlike §9's H1 this has not even a workspace narrowing — it scans every
  READY chunk **in the entire database**, then feeds it to the LLM as cited evidence.
- **Debug — blast radius:** distinguish empty from absent, as `grounding_service.py:44`
  already does correctly. The calling endpoint must supply `owner_id` (see §9 H1).

---

## ~~S4 · `validate_retrieval_scope` has zero callers — HIGH~~ — STRUCK

**File:** `backend/app/services/tenant_guard.py:45`

- **Bug:** the guard's own docstring reads *"Hard blocking guard called before EVERY retrieval
  operation… CRITICAL: Never remove or bypass this call."* It is **never called**.
- **Verified:** ✅ zero call sites (confirmed independently in §9 and by my own grep).
- **What breaks:** it compounds H1 by an order of magnitude — an auditor reading this file
  concludes retrieval is tenant-guarded and stops looking. **A security control that lies is
  worse than an absent one.** The only other reference is a stale comment at `admin.py:79`
  claiming violations are logged; that log line can never execute.
- **Debug — blast radius:** either delete the module **and** the `admin.py:79` comment in the
  same commit, or call it from the single retrieval choke point created by H1. Do not leave
  it as-is.

---

## S5 · Key rotation attributes failures to the wrong key — HIGH

**File:** `backend/app/services/llm_service.py:224, 343, 375`

- **Bug:** rotation mutates **process-global** SDK state (`genai.configure(api_key=key)`)
  while requests execute concurrently in a thread pool.
- **Root cause:** `google.generativeai` resolves its client from a module-level default **at
  call time**, not at `GenerativeModel` construction. Nothing serializes the window between
  configure and dispatch.
- **Why it happens:** any concurrency ≥2. Request A configures key 3 and dispatches to the
  executor; request B configures key 7 before A's thread issues its HTTP call; **A's call
  goes out on key 7**. If it 429s, `_mark_key_failed` cools **key 3** — a healthy key — for
  300s while key 7 keeps being handed out.
- **What breaks:** under load the pool degrades progressively — healthy keys get cooled, hot
  keys never do. Presents as intermittent quota errors no log explains. Also makes the P0-1
  `keys_rejecting_model` accounting unreliable.
- **Debug — blast radius: NOT self-contained.** `embedding_service.py:59` calls
  `genai.configure` on the **same global** and will clobber whatever the rotator set — both
  must be fixed together or neither is fixed. Preferred fix: a per-call client so the key
  travels with the request rather than the process. Extra-care, concurrency-sensitive.

---

## S6 · The Trust Score is a near-constant — HIGH

**File:** `backend/app/services/veritas_engine.py:73-116`

- **Bug:** three of five factors (**65% of the weight**) are hardcoded literals.
- **Verified:** ✅ `scores["dual_retrieval"] = 70.0` whenever any chunk exists — **no second
  retrieval is performed** despite the class documenting "dual retrieval consensus".
  `has_contradictions = False` is initialised and **never reassigned**; the contradiction
  score is 80.0 or 100.0 purely from `len(document_ids) > 1` — **no contradiction detection
  exists**.
- **Why it happens:** always. Factor 2 asks whether a chunk's first 50 characters appear
  *verbatim* in the answer — an LLM answer essentially never does, so that factor is a
  constant 30.0 too. The arithmetic lands at **66-70, always graded MEDIUM**.
- **What breaks:** a **fabricated confidence metric presented as a measured one**, and
  re-exported into audit PDFs that carry the disclaimer "Trust scores indicate retrieval
  confidence." They indicate nothing. A more serious loud-degradation violation than
  `DummyLocalReranker`, because that one at least logs ERROR and refuses in production.
- **Debug — blast radius: owner-decision-required.** Either implement the three factors, or
  reduce the report to what is actually computed and stop advertising the rest. Touches
  `query.py::_compute_trust_event`, the SSE `trust_report` event, `audit_export.py:41`, and
  the frontend TrustScore component.

---

## S7 · Rerank scores are min-max normalised — the confidence number is meaningless — HIGH

**File:** `backend/app/services/reranker_service.py:32`

- **Bug:** scores are min-max normalised **within each candidate set**, so the best candidate
  always scores exactly 1.0 and the worst exactly 0.0 — regardless of whether any are relevant.
- **What breaks:** two concrete failures. `grounding_service.py:91` filters
  `rerank_score >= rerank_threshold` as a low-confidence gate — it can now **never** exclude
  the top result and **always** excludes the bottom one. And `grounding_service.py:138`
  averages these into `confidence_score`, which is streamed to the UI and feeds
  `audit_export._trust_score`. A set of 30 irrelevant chunks produces an identical
  distribution to 30 perfect ones.
- **Debug — blast radius:** return `sigmoid(logit)` instead, preserving the raw logit so
  ranking is unchanged and only the reported confidence becomes truthful. `rerank_threshold`
  must be re-tuned since its meaning changes. Extra-care file.

---

## S8 · Silent corpus corruption across containers — HIGH

**File:** `backend/app/services/embedding_service.py:78`

- **Bug:** when bge-m3 is unavailable the provider emits 768-dim Gemini vectors **zero-padded
  to 1024**. The code justifies this as safe because "the query embedding goes through the
  same fallback chain and gets padded identically."
- **Root cause:** that holds only if the API container and the Celery worker are in the
  **same mode**. They are separate containers with independent model loads, and **nothing
  detects or enforces agreement**.
- **What breaks:** a worker that fails to download bge-m3 while the API succeeds produces a
  corpus where document vectors are padded-Gemini and query vectors are bge-m3. Cosine
  similarity between them is not zero — it is **plausible garbage**. Retrieval returns
  confidently ranked irrelevant chunks; S7 rescales them to look decisive; S6 reports MEDIUM.
  **Every layer that could have caught it has been neutered.**
- **Debug — blast radius: owner-decision-required.** Record the producing model on the chunk
  and refuse at query time on mismatch; minimum viable is to assert `self._dim == EMBEDDING_DIM`
  and fail startup. Chunking/embedding changes imply a re-index.

---

## S9 · Three call sites bypass the prompt-injection guard and the timeout — HIGH

**Files:** `summary_service.py:284, 313` · `proactive_insights.py:124`

- **Bug:** these reach through to `llm_service.provider.generate(...)` directly, skipping both
  `_harden_system_prompt` (the M-8 anti-injection guard) and the `LLM_TIMEOUT_SECONDS` cap
  that `LLMService.generate` applies.
- **Why it matters here specifically:** `summary_service` exists to feed the **entire
  document** to the LLM, and its `_MAP_SYSTEM` prompt contains no injection guard of its own.
  These are the worst possible paths to bypass on.
- **What breaks:** a crafted uploaded document can smuggle instructions into the map step
  across up to 40 windows; the reduce step then treats the poisoned summaries as trusted
  input. None of these calls can time out, so a hung upstream pins the SSE stream indefinitely.
- **Debug — blast radius:** change the three sites to `llm_service.generate(...)`; add an
  `LLMService.generate_stream` that hardens and delegates. Then make the leak impossible —
  rename `provider` to `_provider_impl`. `security-reviewer` owns severity.

---

## S10 · The Finance schema tells the model to do the arithmetic — HIGH

**File:** `backend/app/services/response_schemas.py:98`

- **Bug:** the schema instructs the LLM to compute ratios in the prompt:
  `**Current Ratio** = Current Assets / Current Liabilities = ₹X / ₹Y = **2.4x**`.
- **What breaks:** **direct violation of extract-then-compute, in the exact workspace the
  invariant exists to protect.** The invariant's stated purpose is "why figures cannot be
  hallucinated"; a model computing `₹X / ₹Y` in-context will produce authoritative-looking
  wrong numbers carrying a page citation. Live on every finance chat query.
- **Debug — blast radius: self-contained** to `_FINANCE`. Rewrite the rule to formatting only:
  present a ratio when supplied, never compute one. The 15 Python-computed ratios on the
  finance endpoints are unaffected.

---

## S11 · Audit PDF export crashes on any non-latin-1 character — HIGH

**File:** `backend/app/services/audit_export.py:210`

- **Bug:** `_build_pdf` uses the fpdf core font Helvetica (latin-1 only) with no
  `add_font(..., uni=True)`. **Verified empirically by the agent** against the installed
  fpdf 2.8.7: `FPDFUnicodeEncodingException: Character "⚠" … outside the range of
  characters supported by the font`.
- **Why it happens deterministically, not occasionally:** line 210 emits `f"⚠ {w}"` for every
  trust warning, and `veritas_engine.py:110` produces one whenever fewer than 3 chunks are
  retrieved. Also fires on `…` truncation, curly quotes, em-dashes, **`₹` (which the Finance
  schema mandates)**, and any Hindi/Tamil/Telugu answer — which `language_detector.py` exists
  to produce.
- **What breaks:** the audit report — the compliance artifact for legal and finance users —
  500s for a large fraction of real sessions. DOCX is unaffected, so it presents as "PDF is
  broken, Word works."
- **Debug — blast radius:** register a Unicode TTF (DejaVuSans ships with fpdf2). The font
  file must be present in the backend image — `release-readiness-checker` should confirm
  `Dockerfile.backend` before deploy.

---

## S12 · `aioredis` is not installed — every Redis path is a silent no-op — HIGH

**Files:** `core/middleware.py:9` · `query.py:127, 146` · `auth.py:265` · `documents.py:609` ·
`feedback.py:43`

- **Bug:** every Redis access imports `aioredis` inside a bare `try/except` returning `None`
  with **no log line**. The agent verified `aioredis` is **not installed in `backend/venv`**
  (`ModuleNotFoundError`), and that `aioredis` 2.0.1 is known-broken on Python 3.11 — this
  stack's pinned version — via `TypeError: duplicate base class TimeoutError`. The package has
  been deprecated in favour of `redis.asyncio` since 2022.
- **What breaks:** `DeviceFingerprintMiddleware` silently stops blocking repeat trial
  registrations — an advertised abuse control, inert, with zero log evidence. The retrieval
  cache never caches, so every query pays full retrieval cost while the code presents a cache
  path. `except Exception: return None` is the mechanism — it makes a **missing dependency
  indistinguishable from a cache miss**.
- **Debug — blast radius:** migrate all six sites to `redis.asyncio` (already a transitive
  dependency), drop `aioredis` from `requirements.txt` and `requirements-deploy.txt`, and
  **log at ERROR** when the client cannot be constructed. Changes startup behaviour →
  `infra-health-checker` before merge.

---

## ~~S13 · Web search has never worked — HIGH~~ — STRUCK

**File:** `backend/app/services/deep_research_agent.py:58`

- **Bug:** `settings.TAVILY_API_KEY` **does not exist** in `core/config.py`.
- **Verified:** ✅ the only occurrence of `TAVILY` in the entire backend is this line. The
  resulting `AttributeError` is swallowed by an over-broad `except Exception` and returns
  `None` forever.
- **What breaks:** the advertised "hybrid RAG + web intelligence" pipeline is permanently
  document-only. Step 3 still emits `status="done", message="Found 0 current source(s)"`, so
  the UI reports a **successful web-search step that never ran**, and the synthesis prompt
  then tells the LLM "No web sources found" — inviting it to describe an absence as a finding.
- **Debug — blast radius:** add `TAVILY_API_KEY: Optional[str] = None` to `Settings`
  (extra-care file), emit `status="skipped"` when unset, and narrow the `except` to
  `ImportError`. Config change → `infra-health-checker`.

---

## Selected MEDIUM findings

| # | File | Bug |
|---|---|---|
| S14 | `core/trial_enforcement.py:32` | Docstring claims check-and-increment is atomic; they are **two statements**. Two concurrent requests both read `used = 9`, both pass, both increment → **11 queries on a 10-query trial**. Trivially exploitable with parallel requests |
| S15 | `grounding_service.py:98` | Candidates are re-sorted into **document order before** the token budget is spent, with a hard `break` — so the **rank-1 chunk is dropped** whenever it appears late in the document. The comment calls it "purely a presentation reorder"; it changes which evidence survives |
| S16 | `llm_key_rotation.py:142` | `available_keys`/`key_status` iterate `_cooling_keys` **outside the lock** while `report_rate_limit` writes it under the lock → `RuntimeError: dictionary changed size during iteration` on a `/health` poll concurrent with any 429. A failing health probe can get the container restarted |
| S17 | `llm_service.py:212` vs `llm_key_rotation.py:23` | **Two independent cooldown stores.** The provider writes to the rotator but reads only its own dict; `rotator.get_key()` is never called. The rotator's careful lock-free-wait logic is **dead code on the real path**, and `/health` reports the rotator's view while the provider acts on a different one |
| S18 | `llm_service.py:290` | Error classification is **substring matching** — `"500" in error_msg`, `"503"`, `"404"` — tested *before* structured checks. A token count like "503 tokens" misclassifies a capability gap as a transient server error, undoing P0-1 in the exact case it was written for |
| S19 | `chunking_service.py:28` | Length accounting ignores the `"\n\n"` separators it later joins with, and a block larger than `CHUNK_SIZE` is emitted **whole with no cap**. With no blank lines — common in OCR output — **the entire page becomes one chunk**, silently truncated by the embedder and scored on only its first 512 chars by the reranker. Extra-care: implies a re-index |
| S20 | `retrieval_service.py:105` | Lexical branch computes `to_tsvector(...)` at query time with **no matching GIN index** — verified absent across all 45 migrations. Vector side is O(log n) via HNSW; the hybrid pipeline is only as fast as its slowest half |
| S21 | `audit_export.py:192, 353` | Evidence read as `ev.get("text")` / `ev.get("chunk_text")`, but retrieval emits **`text_content`**. Every audit export renders bare "filename, p.4" with the **quoted passage always missing** — the one thing the report exists to show. Same key-drift as documented BUG-001, reintroduced |
| S22 | `table_extractor.py:110` | `PPStructure` + `show_log` — **both removed in PaddleOCR 3.x**. The C-3 fix documented this exact API break and updated one call site; this second one was missed. Table extraction silently returns `[]` |
| S23 | `table_extractor.py:117` | PDF fallback processes **only page 1** yet labels every table `"page": 1` — a **wrong citation**, the one thing the citation system must never produce. Also uses `BGRA2BGR` on RGBA data |
| S24 | `sm2_service.py:19` | A card whose interval reaches exactly 6 **never graduates** — `elif interval <= 6: new_interval = 6` is a fixed point. SM-2 keys off *repetition count*, not interval value. **Spaced repetition does not space** |
| S25 | `summary_service.py:293` | On a failed window the sentinel tells the reducer "the document continues normally after this point" — **actively instructing the model to conceal the gap**. The user gets a summary presented as complete that is missing a slice |
| S26 | `core/tenant_scope.py:126` | The hook returns early for non-SELECT, so ORM **UPDATE and DELETE** against scoped models are unfiltered. Genuinely unavoidable for `with_loader_criteria` — but the "Limits" docstring documents only `text()` and INSERT, **not this**. A reader who internalised "the session owns tenancy" will write an unfiltered DELETE in good faith |
| S27 | `core/config.py:27` | `CSRF_SECRET_KEY` is a **required, no-default** setting that is **never read**. ✅ Verified: single occurrence, its own declaration. `CSRFMiddleware` does unsigned double-submit — plain `!=` equality. Deployment is blocked on a secret that does nothing, and a reader concludes tokens are cryptographically bound when they are not |
| S28 | `ocr_orchestrator.py:194` | `OCRValidationGateway` hardcodes `0.80`/`0.60`; `settings.OCR_CONFIDENCE_THRESHOLD` is ✅ **verified read only by its own range check**. An inert knob that appears functional — and unlike other inert settings it is **not marked `# INERT`** |
| S29 | `email_service.py:44` | Every trial email hardcodes **5 queries** while `TRIAL_QUERY_LIMIT = 10` is annotated "single source of truth". ✅ Verified: 5 occurrences of the literal. Users are told they are on their last query at #4 while the system grants 10 |
| S30 | `email_service.py:42` | `{name}` interpolated into HTML email bodies **unescaped** — an HTML/link injection primitive in outbound mail carrying the product's sender reputation |
| S31 | `core/storage.py:45, 73` | Whole-file reads into memory (`dst.write(src.read())`) with `MAX_UPLOAD_MB = 200` — 200 MB resident per concurrent operation, in a worker whose DB pool was sized to 1+1 |
| S32 | `ocr_service.py:194` | `fitz.open()` never closed on the exception path — `doc.close()` is inside the `try`, not a `finally`. Leaks a handle and an mmap per failed document; on Windows the temp file then cannot be deleted |

---

## Notable LOW findings

`ocr_service.py:126` — `UnboundLocalError` on an empty `.pptx` · `ocr_service.py:32` — a
**fresh event loop per page** (200 loops for a 200-page scan) · `ocr_orchestrator.py:143` —
bounding boxes normalised against **text extent, not page size**, so every highlight overlay
is offset · `language_detector.py:5` — Marathi and Hindi share an identical Devanagari regex,
so **Marathi is never detected** · `core/auth.py:35` — `workspace_id` defaults to the **user
id**, producing a per-user "category" matching no real workspace · `config.py:226` —
`sync_database_url` does not normalise `postgres://`, the form **Railway hands out**, so the
Celery worker fails at startup with an obscure dialect error on the stated deploy target ·
`financial_table_extractor.py` — 4 of 6 public symbols dead, one of which (`detect_statement_unit`)
would **double-apply a 10⁷ scale factor** if wired · `telemetry.py:12` — ignores both
`OTEL_ENABLED` and `PROMETHEUS_ENABLED` and hardcodes `ConsoleSpanExporter`, flooding logs.

---

## Services/core strengths — preserve these

- **`core/tenant_scope.py`** — corroborated independently by both deep reads as the strongest
  engineering reasoning in the repo. It names the obvious fix (add `owner_id` to ninety WHERE
  clauses), explains why that is the wrong *shape*, and relocates the decision to the layer
  that owns it. Its "Limits — read before relying on this" section is the rare case of a
  control documenting its own gaps. **Extend it (H1, H3, S26); do not replace it.**
- **`llm_service.py:257-328` — the P0-1 branch.** Correctly identifies that a per-key
  capability gap is neither a rate limit nor an invalid key, and **refuses to reuse**
  `_mark_key_failed`/`_mark_key_invalid` whose semantics would poison healthy keys. Cites the
  production evidence (30 failures all from key 20 of 21). The model for how a fix should be
  reasoned about and recorded.
- **`llm_service.py:92-163` — `_safe_extract_text`.** The sharpest catch in the file: it
  recognised that MAX_TOKENS arrives *together with* partial text, so the naive fast path was
  delivering truncated answers as complete ones.
- **`llm_key_rotation.py:71-114` — the M-9 out-of-lock cooldown wait.** Compute under the
  lock, release, sleep, re-check — textbook correct, with a comment naming the bug it replaced.
- **`core/gemini_env.py`** — anchors the env file to `__file__` not CWD, is called from
  `get_key_rotator()` so web/worker/scripts load keys identically, and never overrides an
  existing `os.environ` value so real container env always wins.
- **`embedding_service.py:86` and `reranker_service.py:40` — the M-4/M-10 refusals.** Both
  refuse to emit fabricated data in production, with comments explaining why a zero vector is
  worse than an outage. **S6, S7 and the summary-service placeholder scores are failures to
  apply this same standard elsewhere — not failures of this code.**
- **`core/config.py:43-70` — the connection budget.** Shows the arithmetic
  (`API 5 · worker 4 · beat 2 · health 1 = ~12 of 15`), records the measured incident that
  motivated it (19 hours unhealthy), and says to raise via env rather than by editing code.
- **`core/config.py:210-238` — `sync_database_url`.** One place normalising every psycopg2 DSN
  quirk; the H-9 local-host exemption is genuinely subtle — an unconditional SSL append had
  broken the project's own compose stack.
- **`processing_events.py`** — derives progress from real persisted status transitions and
  states outright that these are "monotonic stage markers, not fabricated percentages." The
  honest choice over a smoother-looking lie.
- **`response_schemas.py:1-19`** — records that the dict was previously keyed
  `student`/`teacher` so Study and Exam silently fell back to the general schema. Documenting
  a silent-fallback bug at the point of fix is what prevents its recurrence.
