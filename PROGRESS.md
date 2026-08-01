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
| P0-2 | Legal Risk Report unreachable — `processContract()` never called | 🟡 **Backend chain VERIFIED** (`a214012`); frontend trigger still unverified in-browser |
| P0-3 | Container image 18.8 GB; bge-m3 downloads 4.3 GB at import | ⬜ Open |
| P0-4 | Supabase credential in git history + plaintext `.env` — needs rotation | ⬜ Open (**owner-access-required**) |
| P0-5 | DB connection budget (30 API + 8×15 worker + 15 beat) vastly exceeded Supavisor session-mode cap of 15 | ✅ **RESOLVED & VERIFIED** |
| P0-6 | Gemini quota — **downgraded**. Some keys are exhausted, but rotation finds a live one and generation succeeds. Not a blocker | ✅ **Not a P0** (see log 2026-08-01) |
| P0-7 | 7 of 9 Celery task modules use the **async** engine via `asyncio.run()` | 🟡 `legal_tasks` **FIXED & VERIFIED** (`a214012`); 6 modules remain, ratcheted by `test_worker_session_discipline.py` |
| P0-8 | `legal_tasks.py:35` analysed a **hardcoded simulated contract string** | ✅ **RESOLVED & VERIFIED** (`a214012`) |
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

**P0-10 RESOLVED (owner).** `DATABASE_URL` now reads `pooler.supabase.com:6543` —
single colon, transaction mode. Host `pytest` works again; all services healthy.

---

### 2026-08-01 — P0-8 resolved, P0-7 (Legal) resolved, P0-2 backend chain verified

**P0-6 downgraded — it was never a full outage.** My earlier "all 21 keys exhausted"
came from sampling keys 1–3 with raw `google.generativeai` calls. Wrong generalisation.
Through the real service, keys 0 and 1 returned 429 and the rotator moved on:
`Configured Gemini with key 2` → `JSON generated and validated successfully on attempt 1`.
**The P0-1 rotation fix did exactly its job.** Some keys are exhausted; generation works.
Not a blocker, and it should not have been recorded as one.

**P0-7 + P0-8 + P0-9-writes fixed together in `legal_tasks.py` (`a214012`)** — they were
literally the same lines. The module now uses `SyncSessionLocal` (matching
`document_tasks.py`, the module that was already correct), reads real `DocumentChunk`
text, and derives `owner_id` from the document being processed — the document's owner IS
the tenant, so a caller cannot pass a mismatched one and the task signature is unchanged.
`ContractTextUnavailable` is raised instead of falling back to placeholder text, and
deliberately does NOT consume the retry budget: retrying cannot conjure text that
extraction never produced.

**P0-2 backend chain VERIFIED at runtime** against the real uploaded MSA:
- `Segmenting contract … (2173 chars)` — real text, not the 90-char stub
- `legal_contracts` **0 → 1**, `legal_clauses` **7**
- `party_name` **"Meridian Labs Pvt. Ltd."**, `contract_type` **"Master Service Agreement"**
- clauses `1. Parties and Term` / `2. Services and Service Levels` / `3. Fees and Payment`
- `owner_id` = the document's real owner
Backend suite **112 passed, 6 xfailed**.

**Class-level regression guard (`97592ba`).** `tests/test_worker_session_discipline.py`
ratchets the P0-7 class: any task module importing `AsyncSessionLocal` fails, and
`KNOWN_VIOLATIONS` (the 6 remaining modules) may only shrink. Checks are **AST-based** —
the first draft grepped file text and failed against the repaired module because that
module documents the defect in its own docstring. A guard that greps its own
documentation is a false signal. Verified to bite: reintroducing the import fails 2 tests.

**Why P0-7 escaped for so long:** it fails ~50% of the time (task 1 succeeds on a fresh
connection, task 2 dies on a pooled one from a dead loop), and no test exercised a second
task in the same process. The ratchet closes that permanently.

**New gap recorded, not fixed:** `legal_compliance_rules` is empty, so every clause came
back `COMPLIANT` and `risk_score` `LOW`. Correct behaviour with no rules configured, but
the product ships **no default rule set** — the Risk Report is therefore vacuous out of
the box. Product decision, not a defect.

**Remaining P0-7 modules:** `export`, `finance`, `hr`, `ocr`, `research`, `study`.

---

### 2026-08-01 (cont.) — orchestration layer + finance repaired

**Engineering Orchestration is now repository infrastructure (`64251ef`).** The rules for
*using* the 10 specialists lived only in prompts, so every session re-derived them and
drifted. `CLAUDE.md` now owns the execution model: session startup, agent + skill
registries, delegation matrix, implementation/debugging/verification/regression lifecycles,
mandatory browser verification, workspace parity, deployment gate. Agents and workspaces are
**discovered** (`ls .claude/agents/*.md`, `KNOWN_WORKSPACE_SLUGS`), not hardcoded, so the
section degrades gracefully as files change. Source-of-truth boundary held — the Release
Gate and permanent principles stay in the Directive, status stays here, neither is restated.

**Skills classified, not adopted wholesale.** `.agents/skills/` is **gitignored (0 tracked
files)**, so no pipeline may depend on one. `ui-ux-pro-max` → applicable (stack-agnostic
a11y/UX rules). `ckm-design-system` → applicable in principle (token methodology).
`ckm-ui-styling` → **Tailwind guidance only; its shadcn/ui + Radix direction is rejected**,
because this repo uses neither (0 in `package.json`) and adopting it would import a
component library beside the existing hand-rolled design system.
`ckm-design`/`ckm-banner-design`/`ckm-slides` → not applicable (logo/CIP, ad banners,
Chart.js decks — no such surface here). Future skills are classified by the same test, so
no edit is needed to add one.

**Two invariants corrected in `CLAUDE.md` — they had become false documentation.**
Tenant filtering now describes `owner_id` + `TenantScoped` rather than the old
"filter on `workspace_id`" rule that P0-9 disproved. **Postgres RLS is marked INERT** with
evidence (`rolbypassrls=true`, disabled on all workspace tables, the policy variable never
set). Claiming a control that does not execute is worse than claiming none.
Also removed three hardcoded counts (migrations, test files) that drifted on every change
and were caught stale twice — the drift *source* is gone, not merely reset.

**P0-8 was systemic (`9dc50c7`).** `finance_tasks.py` hardcoded
`"Simulated invoice ... Vendor: AWS. Total: $5050.00 ..."`, so every uploaded invoice was
analysed as that fake AWS bill. Repaired with the same treatment as Legal, plus
`SyncSessionLocal` (P0-7) and derived `owner_id` (P0-9). The text loader was **extracted to
`_document_text.load_document_text`** rather than copied — copying it would have repeated
the duplication that let the class spread. Finance's deterministic math validation is
preserved and now documents why: Python computes every number, never the prompt.

Ratchet released `finance_tasks`: suite **114 passed / 5 xfailed** (was 112 / 6).

**Remaining P0-7 + P0-8 modules:** `export`, `hr`, `ocr`, `research`, `study`.

---

### 2026-08-01 (cont.) — orchestration completed; research + study repaired

**Orchestration completeness audit (`a1cbfcf`).** Five genuine gaps found and closed
incrementally (existing decisions preserved, one canonical delegation matrix):
commit lifecycle · documentation lifecycle · specialist agent lifecycle · skill lifecycle ·
workspace completion pipeline. Agent **inputs/outputs are documented once, not per agent** —
the cold-start prompt requirements and the 10-section contract are identical for all ten, so
per-row repetition would create two sources of truth for one contract. Added handoff chains
and an explicit statement that the implementation owner is always the main thread. The skill
lifecycle makes load/don't-load mechanical and gives conflict resolution a fixed precedence
with repository architecture on top. The workspace completion pipeline is ten ordered checks,
step 2 of which greps for placeholder text.

**P0-8 was in FOUR workspaces, not one (`1c39768`).** Research shipped
`"Simulated paper text … We demonstrate that X causes Y …"` and Study shipped
`"Simulated study material … Mitochondria is the powerhouse of the cell …"` — so every paper
yielded findings about a fake study, and every uploaded document produced mitochondria
flashcards regardless of subject. Both repaired: real chunk text via the shared loader,
`SyncSessionLocal` (P0-7), derived `owner_id` (P0-9).

**Validation Gateway restored.** `research_tasks.py` had

```python
if finding.evidence_quote.lower() in raw_text.lower() or True:  # Simulated pass
```

`or True` made the anti-hallucination check accept **every** evidence quote including
invented ones, and left the reject branch unreachable. It was not arbitrary: with the source
text fabricated, a real quote could never match, so the check had to be defeated for the
pipeline to emit anything. **The two defects propped each other up** — which is why restoring
real text is what makes the gateway viable, and why they had to land together. Comparison is
whitespace-normalised because extracted PDF text wraps mid-sentence.

**Guards generalised** from Legal-only to every task module (placeholder detection + gateway
short-circuit). The gateway check is **AST-based**: the text-search version failed against
the *fixed* module because that module documents the old expression in its own docstring —
the **second** time that mistake was made in this file, so the lesson is now written into the
test. Verified to bite in both directions.

Suite **128 passed / 3 xfailed** (was 114 / 5).

**Remaining P0-7 modules:** `export`, `hr`, `ocr` — P0-7 only; none carries placeholder text.

---

### 2026-08-01 (cont.) — export + ocr repaired; P0-7 down to one module

Both turned out to be broken **independently of** the session mixing:

**`export_tasks`** eager-loaded `selectinload(Contract.clauses).selectinload(Clause.redlines)`
— but **neither relationship exists**; `models/legal.py` declares only the FK columns. Every
dispatch raised `AttributeError` before touching the DB, so legal DOCX export has never run.
Fixed with explicit queries rather than by adding relationships, keeping the change inside
the task instead of altering shared models every workspace imports. Added the tenant scope
the now-`TenantScoped` models require: the contract's owner is resolved once under a narrow
`system_scope()` bootstrap (a background job has no request to inherit from), then all reads
run under that owner.

**`ocr_tasks`** looked implemented and *could not* have worked — fabricated file path
(`"Pass a mock file path ... for prototype"`), persistence commented out and targeting
`doc.extracted_text` / `doc.ocr_metadata` which **do not exist on the model**, then
`db.commit()` on no-op changes plus a log line saying `"OCR Extraction successful"`. A
dispatch would have reported success and discarded everything — the silent-degradation
pattern CLAUDE.md forbids. It has **zero dispatch sites**, and the real OCR path
(`document_tasks` → `storage_service` → `ocr_orchestrator`) is already verified end-to-end,
so making this one real would duplicate a working pipeline. It now raises
`OcrGpuTaskNotImplemented` and names the real implementation. **Wiring deliberately preserved**
(`include` + `task_routes` + `-Q ocr_gpu_queue`) so the three-way rule holds and a dedicated
GPU worker can take the queue over later, as `celery_app` already anticipates. Both tasks
verified still registered.

Suite **130 passed / 1 xfailed** (was 128 / 3).

**P0-7 remaining: `hr_tasks.py` only.** Deliberately NOT attempted this session. It is the
one worker module whose workspace is **verified working end-to-end** (3 resumes ranked
95/50/15 with cited evidence + CSV export), it is the largest (191 lines) and carries
idempotency handling and embedding error recovery. Converting it under low remaining context
risked breaking the only proven workspace for no urgency — its defect is intermittent, not
constant. Scope for whoever picks it up: `AsyncSessionLocal` → `SyncSessionLocal`, drop
`asyncio.run`, use `_run_async` for the LLM/embedding calls. **No P0-8 or P0-9 work needed** —
it carries no placeholder text and its models are not `TenantScoped`
(`hr_job_roles` already has `owner_id`). The ratchet in
`tests/test_worker_session_discipline.py` holds it as the single remaining entry.

---

**Superseded — `backend/.env` typo (P0-10), now fixed:** `DATABASE_URL` reads
`...pooler.supabase.com::6543/postgres` — **double colon**. The 5432→6543 pooler switch was
applied but left an extra `:`. Effects: host `pytest` fails at collection with
`ValueError: invalid literal for int() with base 10: ':6543'`, and the running containers
still hold the pre-edit value from creation time, so **the stack dies on next restart**.
Proven to be the sole cause: supplying a corrected URL via env override (without touching
`.env`) gives **105/105**, which also confirms port 6543 works. One character; `.env` is
out of scope for me to edit.
