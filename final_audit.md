# DocuMindAI — Final Audit

**Date:** 2026-08-02 · **Branch:** `security/redact-env-example` · **HEAD:** `4b0af91`
**Type:** Read-only audit. **No code was changed to produce this document.**

---

## 1. Direct answer: is the project bug-free and ready to deploy?

**No.** Not yet, and I want to be precise rather than reassuring.

- **Deploy-blocking defects remaining: 3** (two need you, one needs code).
- **Performance defects found in this audit: 4** (one of which I introduced).
- **Frontend↔backend contract: clean** — 56/56 paths resolve.
- **Backend regression suite: 131 passed.**
- **End-to-end workspace certification: 0 of 7 complete.**

The system is materially healthier than a week ago — a large class of real defects is
gone — but "no known bugs" would be false. The honest status is **not deployable today**;
see §6.

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

### P-1 · N+1 query in legal DOCX export — HIGH · *introduced by me*

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

### P-2 · N+1 query in research document loading — HIGH

**Where:** `backend/app/api/v1/endpoints/research.py:184` (also `:250`, `:467`)

**What:** For each `doc_id`, one query for the `Document` then another for its chunks —
**2N queries** for N documents, on a request-path endpoint.

**Root cause:** per-item validation loop written before the multi-document case existed.

**Why it costs:** selecting 10 documents for a comparison issues 20 sequential awaited
round trips before any work starts.

**Safe fix:** two queries using `.in_(doc_ids)`, then group by `document_id` in Python.
Self-contained inside the endpoint; the response shape is unchanged, so no frontend
impact.

### P-3 · Blocking `time.sleep` inside an async function — MEDIUM (conditional)

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

### B-1 · Gemini generation unavailable — OWNER ACTION · one line

Verified by testing **every key against every configured model**, bypassing the rotator:

| Model | Result |
|---|---|
| `gemini-2.5-flash` (primary) | **0/21 keys — ResourceExhausted** → genuine daily quota |
| `gemini-1.5-flash` (fallback) | **0/21 keys — NotFound** → **retired by Google** |

**Root cause (fallback):** `GEMINI_FALLBACK_MODEL` in `backend/.env` names a model Google
no longer serves, so the retry at `llm_service.py:357` raises `NotFound` **every time** —
including for ordinary rate limits the fallback exists to absorb. The fallback chain has
never been able to fire.

**Fix:** `backend/.env` → `GEMINI_FALLBACK_MODEL=gemini-2.0-flash`. That model generated
successfully during this effort and is already `config.py`'s default. **No dependency
impact** — it is a configuration value read at call time.

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

1. **`GEMINI_FALLBACK_MODEL=gemini-2.0-flash`** — one line, unblocks generation (B-1).
2. **P-1 and P-2** — the two N+1 fixes. Self-contained, no contract change, ~20 lines each.
3. **P-3** — `await asyncio.sleep`. One line.
4. **Per-workspace certification** — now possible after `31c7119`. Re-upload per workspace.
5. **P0-3 image size** — bake vs. download is a tradeoff decision.
6. **P0-4 credential rotation** — yours; redaction does not un-leak git history.

**Not recommended:** adding the 100 missing indexes (write cost, no measured gain), and
backfilling historical `workspace_id` values (asserts a choice the user never made).

---

## 8. Method and limits

**What this audit did:** AST analysis over 208 Python files for query-in-loop and
blocking-call patterns; static route extraction from 24 endpoint modules compared against
56 frontend bindings; index-coverage analysis over ~50 ORM models; component size analysis;
live provider testing against every key and model.

**What it did not do — and you should not read as passing:**
- **No load testing.** Impact on P-1/P-2 is reasoned from query counts, not measured under
  concurrency.
- **No profiler run.** No flame graph, no per-endpoint latency distribution.
- **No end-to-end workspace certification.** 0 of 7 complete; generation is blocked.
- **Frontend runtime performance unmeasured** — no re-render counts, no bundle analysis.
  `WorkspaceUI.tsx` at **2,357 lines** is the shared shell for all 7 workspaces and is the
  obvious candidate for a render audit, but that claim is unmeasured and stated as such.

Every finding above is either a code reference you can open, or a command output. Where I
inferred rather than measured, I said so.
