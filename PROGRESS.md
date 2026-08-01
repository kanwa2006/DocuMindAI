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
| P0-7 | Celery task modules used the **async** engine inside sync tasks | ✅ **RESOLVED — all 9 modules** (`c0c9370`); ratchet retired at zero |
| P0-8 | Four workspaces analysed **hardcoded placeholder text** instead of the upload | ✅ **RESOLVED & VERIFIED** (legal, finance, research, study) |
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

### 2026-08-01 (cont.) — P0-7 CLOSED; ratchet retired at zero (`c0c9370`)

**`hr_tasks` repaired — the last module.** It hid the defect better than the rest, and why
matters: it used `asyncio.get_event_loop()` + `run_until_complete`, which **reuses** one loop
per worker process instead of building and destroying one per task. Pooled asyncpg
connections therefore stayed bound to a *live* loop, so HR kept working — the one workspace
verified end-to-end — while `legal_tasks`, creating a fresh loop per call, failed on roughly
every second task. **Same architectural violation, opposite symptom.** That is precisely why
the guard tests for the async *session* rather than for one spelling of the bug.

Behaviour preserved deliberately: `MAX_RESUME_CHARS` chunk assembly, prompt-injection
sanitisation, idempotent candidate reuse, and the non-fatal embedding fallback (L-13).
No P0-8 work (it always read real `DocumentChunk` text); no P0-9 work (HR models are not
`TenantScoped`; `hr_job_roles` already carries `owner_id`).

**`flag_stale_reviews` now admits it is unimplemented.** Beat runs it daily at 08:00 and its
body was a single INFO log — in the logs, indistinguishable from a sweep that ran and found
nothing. Now WARNING, stated plainly. Not raising: a daily exception for a capability nobody
has requested is noise, not signal.

**The ratchet is retired.** `KNOWN_VIOLATIONS` and its xfail branch are deleted exactly as
the file always specified. There is no "known violation" state any more — a task module
importing the async session simply fails.

**Runtime verification:** the sync path executes fully — document read, chunks assembled,
reaching the LLM call with **no loop error and no session error**. The LLM step itself could
not complete because all 21 Gemini keys were rate-limited at that moment; it failed
gracefully through the existing handler. Test fixture created for the run was removed.

Suite **131 passed, 0 xfailed**.

---

### 2026-08-01 (cont.) — first browser-verified frontend change (`0c3a569`)

**The browser-verification policy has now actually executed.** It was written but unproven;
this is its first real use, and it earned its place immediately — it caught a regression
before commit rather than after.

**Composer measured before any CSS was touched.** At 375×667: composer 175px of a 615px main
= **28.5%**, reading area **400px**. Anatomy: chips 28 + textarea 44 + toolbar 36 = **108px of
content inside 175px rendered**. The stacked toolbar cost **44px** (36px row + 8px margin) —
as much vertical space as the textarea itself — purely for sitting on its own line.

**Worth recording: the reported symptom did not reproduce.** "Composer takes roughly half the
viewport" measured at 19.4% (desktop) to 28.5% (short mobile) — never half. The *underlying*
defect was real (fixed-height composer, 38% chrome overhead), so the work was justified, but
the framing was not. Measure before believing a UI report.

**After — inline toolbar where there is room:**

| Viewport | Composer | % of main | Reading area |
|---|---|---|---|
| 1440×900 | 175 → **131px** | 19.4 → **15.4%** | 673 → **677px** |
| 768×1024 | 175 → **131px** | **13.5%** | **801px** |
| 375×667 | **175px** (unchanged) | 28.5% | 400px |

**A regression caught in verification, not shipped.** Inline at 375px squeezed the textarea to
**33px wide** — the voice-input language select makes the left control group ~191px — so the
layout "worked" while the input was unusable. Below 640px the row now wraps with `order: -1`
putting the textarea first, i.e. the pre-existing layout. Recover 44px where it is safe, never
at the cost of usability.

**Second, subtler defect:** the first wrap fix appeared to do nothing because an **inline
`flex` beats the stylesheet**, so the responsive `flex-basis: 100%` never applied. Sizing moved
into `.chat-input` — shared-component styles belong in the shared stylesheet, not per-element
overrides.

**Recorded, not fixed:** composer buttons are 32×32 and 36×36, below the **44px minimum touch
target** (`ui-ux-pro-max`). Pre-existing, not introduced here; correcting it changes visual
design across the whole button system.

---

### 2026-08-01 (cont.) — response measure corrected (`62532f0`)

**A cap that existed, looked correct, and was wrong by 26%.** `.text-response` already had
`max-width: 72ch`. `ch` is the advance width of **"0"**, and in this font stack "0" is ~26%
wider than the average letter — measured in Chromium at 15px, **1ch = 9.00px** while the real
average glyph is **7.13px**. So `72ch` resolved to 648px and rendered **91 actual characters
per line**, past the ~90 threshold where comprehension measurably drops.

Nobody catches this by reading the CSS: the number says 72, the browser renders 91. It needed
a calibrated measurement — glyph width sampled from the rendered text via canvas
`measureText`, not assumed from a rule of thumb.

`57ch = 513px = ~72 real characters`, which is what the original was reaching for.

| Viewport | Before | After |
|---|---|---|
| 1920×1080 | 91 cpl (648px) | **72 cpl (513px)** |
| 1440×900 | 86 cpl (648px) | **72 cpl (513px)** |
| 375×667 | 46 cpl | **46 cpl** — cap correctly does not bind |

Applied to prose elements rather than the container so tables and code blocks keep the full
column. **Honest gap:** no table or `<pre>` appeared in the sampled responses, so that
exemption is reasoned, not yet observed rendering.

A comment records the calibration and instructs a RE-MEASURE if the body font changes, so it
does not get "corrected" back to a round 72.

**`CLARITY.md` does not exist** anywhere in the repository — referenced by the session brief
but never created. Recorded rather than invented; the canonical set remains `CLAUDE.md`,
`PROGRESS.md`, and the Directive.

---

### 2026-08-01 (cont.) — Gemini is NOT blocked; two response defects fixed (`c805b0e`)

**Correction: Gemini quota was never the blocker.** Verified the rotation implementation and
then tested it: **21 keys loaded, 0 cooling, 0 invalid, generation succeeded.** The rotator is
correct — dynamic `while True` discovery of `GEMINI_API_KEY_N` (unlimited, no code change to
add keys), 403 → permanent skip, 429 → cooldown **with expiry**, and it waits for the soonest
cooldown rather than failing. Earlier cooldowns had simply expired. My "quota blocker" framing
was wrong and cost a session of verification.

With real generation available, two defects surfaced by **reading actual responses**:

**1. One fixed template for every question.** The prompt said *"If the user asks for a summary,
structure your reply as: Overview · Key Topics · Important Details · Key Insights · Limitations
or Risks · Summary"* — and the model applied it regardless. A request for *"a markdown table
with columns Clause, Obligation, Risk"* returned those six headings and **no table**.
Replaced with intent-adaptive guidance (explicit format wins; else table / steps / timeline /
finding-severity-evidence / 1-3 sentences; scale depth to the question; never repeat).
**Verified at runtime:** same request now returns a real table with exactly the requested
columns and zero generic headings.

**2. Truncated answers presented as complete — loud-degradation violation.**
`_safe_extract_text` had a fast path `if text: return text` that returned **before ever reading
`finish_reason`**. Gemini returns `MAX_TOKENS` *together with* partial text, so a cut-off answer
was returned, persisted and rendered as whole. Found in the database: an answer ending
mid-citation at `"...within two weeks (scanned"` — no closing paren, no indication. The existing
MAX_TOKENS branch only fired when there were **no parts at all**; partial truncation — the
common case — was entirely silent. The fast path now checks `finish_reason`, logs, and appends
a visible notice while preserving every character produced.
**Confirmed pre-existing**, not caused by the prompt change: a response generated *before* it
was also truncated (2000 chars, ending `"...set for 12"`).

**Ruled out along the way** (recorded so nobody re-derives them): `GEMINI_MAX_OUTPUT_TOKENS`
8192 *is* correctly passed (not inert); `LLM_TIMEOUT_SECONDS` 120 vs a 28s call; no CSS
clipping; no table/cell overflow; no failed network requests.

**Visual inspection earned its place.** A screenshot showed text ending mid-sentence that
every numeric check called clean — `tableOverflows: false`, `clippedCells: []`. Measurement
alone would have missed it; that is why the policy requires both.

**Table exemption now observed, not just reasoned:** with a real table rendered, prose measures
513px while the table spans 1076px — the prose-only `max-width` behaves as intended.

---

### 2026-08-01 (cont.) — layout invariants verified across 4 viewports; NO defect found

Measured every mandatory layout invariant in Chromium at four independent viewports. **All
pass. No layout defect was found, and none was manufactured.**

| Viewport | Page scrolls V | Composer in viewport | Gap below | Reading area | Scroll owners |
|---|---|---|---|---|---|
| 1440×900 desktop | **no** | yes | — | 677px (75%) | **1** |
| 1366×768 laptop | **no** | yes | 16px | 545px (71%) | **1** |
| 768×1024 tablet | **no** | yes | 16px | 801px (78%) | **1** |
| 375×667 mobile | **no** | yes | 16px | 400px (60%) | **1** |

Scroll ownership is correct everywhere: the **message list** owns it
(`flex-1 overflow-y-auto`, e.g. 677 visible / 7900 content) and the document does not
scroll — `documentElement.scrollHeight == clientHeight` at every size. No horizontal
overflow. Send/attach present and the textarea usable at all widths (309px at 375).

**A misread I corrected.** From the laptop screenshot I judged the composer's bottom border
clipped by the viewport edge. Measurement disproved it: the bordered box bottom sits at 752
of 768 — a **16px gap**, consistent at every breakpoint. The layout is tight at the bottom
(24px top padding vs 16px bottom) but not broken. Per the directive, an unmeasured
"improvement" is not made — so it was not changed.

**Standing conclusion:** the chat layout architecture (header + sidebar + flex-1 scrolling
message list + pinned composer) is sound and satisfies every stated invariant. Future
frontend work should target *content* presentation, not the layout shell, unless new evidence
contradicts this table.

---

### 2026-08-01 (cont.) — first product-quality (not engineering) defect fixed (`d6714a5`)

**Engineering invariants passing is the floor, not the target.** The layout passed every
mandatory invariant at four viewports — and a design review of the screenshot still found a
defect worth fixing. Both bars are needed.

**Follow-up suggestions rendered after every response.** A 17-message thread showed the same
three static prompts **17 times** — 51 buttons, 476px of transcript (6% of scroll height).
Noise was the lesser problem: they were *misleading*, because clicking "What are the next
steps?" on message 3 cannot branch the conversation there — it appends to the end like any
other prompt. A suggestion only means anything on the turn you are actually at.

**Root cause was a missing condition, not styling.** `isLastAI` already existed, was already
computed via `lastAiMsgIdx`, and was already used correctly by the **Regenerate** button
directly above. The follow-up render just omitted it. Fixed at the shared message component,
so every workspace benefits — no viewport hack, no per-screen override.

Verified: 17 sets → **1**; Regenerate also 1 (the two controls are now consistent);
Copy still present on all 18 messages (nothing over-removed); transcript 7900px → 7292px.

**Design-review observations recorded, NOT yet acted on** (each needs its own measurement
before any change): sidebar has a large dead zone between the chat list and the bottom nav
at short viewports; the user message bubble is high-contrast black and competes with the
response for attention; header controls cluster at both edges with a centred workspace pill.

---

### 2026-08-01 (cont.) — composer hidden on a real laptop (`f0a0619`) — MY TEST WAS WRONG

**Reported by the owner: the "Ask anything..." input was not visible on a 1366x768 laptop.**
My earlier entry claimed 1366x768 passed. **That number was wrong.** On a real 1366x768
laptop the PAGE viewport is ~1365x637 after browser chrome (~90px) and the Windows taskbar
(~48px). I measured a window that does not exist on that machine and recorded it as a pass.
The testing was the defect, not only the code.

**Code root cause — a latent flexbox bug.** The message list was `flex-1 overflow-y-auto`
with **no `min-height: 0`**. A flex child defaults to `min-height: auto`: it refuses to
shrink below its own content height, so past a content/height threshold it stops scrolling
and **grows**, pushing the composer off the bottom. That is precisely the reported shape —
fine at one window size, input gone at another, depending on transcript length. It is why
every measurement I took "passed" while the owner's screen did not.

**Fix:** `min-h-0` on the list so `overflow-y-auto` actually engages, and `shrink-0` on the
composer form so the input is never what gives way — the transcript yields instead.

**Verified at heights the earlier pass never covered:** computed `min-height: 0px`,
form `flex-shrink: 0`; composer, textarea and action button fully inside the viewport at
**1365x637** (real laptop) and **1280x450**; page still does not scroll; reading area
shrinks to 414px and 227px respectively.

**Standing lesson for viewport testing:** a device resolution is NOT a viewport. Subtract
browser chrome and OS taskbar, and test a short-viewport case (<=500px tall) explicitly.
The invariant table recorded earlier is only valid for the viewport sizes actually listed
in it.

---

### 2026-08-01 (cont.) — response presentation: hierarchy + column balance (`a15b382`)

Owner supplied a ChatGPT screenshot as the target and a critique: *"response column uses
only part of the reading width, excessive empty space; mostly plain paragraphs; headings,
bullets, tables, spacing and hierarchy inconsistent; feels like raw markdown in a container."*
Both root causes found by measurement, both fixed in the **shared** renderer.

**1. Markdown had NO hierarchy — the big one.** Measured: `<h2>` computed to
**15px / weight 400**, byte-identical to `<p>`, and **every block margin was 0px**.
Tailwind Preflight strips default heading sizes, weights and margins; nothing added them
back for markdown. ReactMarkdown was emitting correct semantic HTML that rendered as an
undifferentiated wall of text. Added a scoped heading scale + block rhythm to
`.text-response` (space above a heading > space below, list markers/indent restored,
blockquote, hr, `:first-child` reset). Verified: h2 **18.3px/650** with 29.3px top margin,
paragraphs 13.5px, list items 5.25px, disc markers present.

**2. Column badly unbalanced.** Prose 513px flush LEFT in a 1088px column — **47%
utilisation, all 575px of gutter on one side** — while tables spanned 1076px, so prose and
tables shared a left edge but ended 500px apart. `max-w-6xl` → `max-w-4xl`, prose 57ch →
63ch. Result: column **832px**, prose **567px (68%, was 47%)**, gutter **265px (was 575)**,
table 820px on the same right edge.

**Two self-inflicted breakages, recorded because the class matters more than the instance:**
- A JSX comment between `return (` and the root element created two adjacent root nodes
  (TS1109). It shipped because my check ran `npx tsc | tail` and echoed `$?` — **the exit
  code of `tail`, not tsc**. Always `PIPESTATUS` (or don't pipe) when gating on a compiler.
- Inserting a new CSS block **into an existing multi-line selector list** orphaned
  `max-width: 63ch` onto `h5,h6` only, silently removing the measure from all prose. Caught
  by re-measuring after the edit rather than trusting it. Never insert into a selector list.

---

### 2026-08-01 (cont.) — send-path certification (`4098ef6`); halted on Gemini quota

**Duplicate user message — FIXED AND VERIFIED.** `sendMessage` had no re-entrancy guard;
`setLoading(true)` is a state update, so `disabled={loading}` lags a render and a second
click re-enters and persists the same turn twice. Proven: `disabled` was still `false`
immediately after the first click. Fixed with a synchronous ref cleared on all five exit
paths. **Certified: 3 clicks fired in ONE tick → exactly 1 user row in the database.**
This also corrects the old baseline entry blaming doubled bubbles on the test harness —
the harness only *exposed* the missing guard.

**Composer bricking — FIXED AND VERIFIED.** `await createChatMessage(...)` was unguarded.
When the chat session 404s (belongs to another account / deleted) the exception escaped
`sendMessage`, so `setLoading(false)` never ran and the textarea stayed **disabled showing
"Thinking…" permanently** behind a generic toast — no retry, no chat switch, reload only.
Reproduced live as `POST /chats/{id}/messages → 404`. Now caught: state unwound, guard
released, actionable message. **Certified: after a failed send the composer stays usable.**

**Response measure widened** 63ch → 78ch (~98 chars, ~84% of the 832px column) on owner
report that text wrapped while horizontal space remained. Full history recorded in the CSS
comment so it is not "corrected" back to a round number.

**RAG pipeline — partially certified.** `POST /query/stream` → **200**; retrieval and
grounding executed; the failure is downstream at generation only.

**HALTED: Gemini quota genuinely exhausted (external blocker).**
```
Configured Gemini with key 5 … 6 … 7 … 15     <- rotator sweeping all keys
[query/stream] Stream failed
Exception: All Gemini API keys exhausted or on cooldown.
```
Rotation behaved **correctly** — it swept all 21 keys before raising. This is the free-tier
daily quota, consumed largely by this session's own verification runs. Per the standing stop
conditions this is "external infrastructure unavailable": no repository change can produce
tokens. It resets on Google's daily schedule.

**Blocked behind it (cannot be certified without generation):** streaming render, citations,
trust score, markdown/table output for NEW responses, and the full per-workspace journey for
General / Legal / HR / Finance / Study / Research / Exam.

**Not blocked, available now for the next session:** upload → READY → indexing per workspace,
persistence, history, chat/workspace switching, exports of EXISTING content, responsive
verification at all four breakpoints, and console/network checks — none of which need the LLM.

---

### 2026-08-01 (cont.) — duplicate bubble was a RENDER bug; fallback model is RETIRED (`7c59b06`)

**I was wrong to call the duplicate fixed.** The re-entrancy guard did stop double
*persistence* (verified: 3 clicks in one tick → exactly 1 DB row) — but the screen still
showed two bubbles. **One row in the database, two bubbles on screen.** The optimistic append
fabricated its own row (`id: Date.now().toString()`) and discarded what `createChatMessage`
returned, so once history reloaded from the server both the fake-id entry and the real UUID
row were in state. The assistant path already used `savedMsg` correctly; the user path did
not. Now uses the server-returned message. **Lesson: a clean database row count does not
prove a clean render — check both.**

**Perpetual "Thinking…" fixed.** The stream error handler cleared loading, released the send
guard and toasted, but never cleared the in-flight response block — a dead card stayed
mounted rendering "Thinking…" forever. `setResponse(null)` added to the error path.

**Provider failure classified with runtime evidence, per key AND per model** (tested directly,
bypassing the rotator):

| Model | Result across all 21 keys |
|---|---|
| `gemini-2.5-flash` (primary) | **0/21 — ResourceExhausted** → genuine daily quota |
| `gemini-1.5-flash` (fallback) | **0/21 — NotFound** → **model retired by Google** |

**So the fallback chain has never been able to work.** `llm_service.py:357-359` retries with
`GEMINI_FALLBACK_MODEL` when the primary fails, but that name resolves to a model Google no
longer serves — the retry raises NotFound every time, including on ordinary rate-limits that
the fallback exists specifically to absorb. **This is configuration, not quota, and it is
fixable now.**

**OWNER ACTION (unblocks generation without waiting for quota reset):** in `backend/.env` set
`GEMINI_FALLBACK_MODEL=gemini-2.0-flash`. That model was verified working earlier today in
this very session (`Configured Gemini with key 2` → successful JSON generation). `config.py`
already defaults to it; the `.env` override is what points at the retired name. `.env` is
out of scope for me to edit.

**Genuine external blocker (primary path only):** `gemini-2.5-flash` quota is exhausted on
all 21 keys and resets on Google's daily schedule. Rotation behaved correctly throughout —
it swept every key before raising.

---

## Continuation state (for the next session)

- **Branch:** `security/redact-env-example` · **HEAD:** `d6714a5` · working tree clean
- **Suite:** 131 passed, 0 xfailed · stack healthy (backend/worker/beat/db/redis/pgbouncer)
- **Closed this effort:** P0-1, P0-5, P0-7, P0-8, P0-10; P0-9 read path + all worker writes;
  P0-2 backend chain; orchestration layer complete
- **Highest-priority remaining work, in order:**
  1. **Frontend UX (continuing)** — composer + response measure done and browser-verified. Next: sidebar/header balance, empty/error/loading states, citation + trust-score presentation. Gemini is available, so real responses can be generated for any component that needs content.
     response area itself (typography, spacing, markdown density, citation rendering), then
     loading/empty/error states. Browser-verification loop is proven and reusable.
  2. **Response quality** — generation-time structure *and* the shared renderer (both, per
     Phase 8; presentation only, never retrieval/citations/grounding).
  3. **Per-workspace verification** using the 10-step Workspace Completion Pipeline in
     `CLAUDE.md`. None of the 7 has been through it end to end. **Note:** a full
     upload→READY→query pass per workspace needs working Gemini quota, which is intermittent.
  4. **Deployment verification**, then the Release Gate.
- **Active blockers:**
  - **P0-6 Gemini quota** (owner-access) — keys rotate in and out of exhaustion; LLM-dependent
    verification is intermittent, not impossible. Not a hard blocker.
  - **`legal_compliance_rules` ships empty** (owner-decision) — the Legal Risk Report is
    correct end-to-end but has no rules to evaluate against, so every clause returns
    `COMPLIANT`/`LOW`. A default rule set is a product judgment.
  - **P0-3** container image 18.8 GB · **P0-4** credential rotation (owner-access).
- **Exact next step:** measure the composer/response viewport split at desktop, tablet and
  mobile widths in Chromium **before** changing any CSS — the policy requires a measured
  before/after, not an eyeballed one.

---

**Superseded — `backend/.env` typo (P0-10), now fixed:** `DATABASE_URL` reads
`...pooler.supabase.com::6543/postgres` — **double colon**. The 5432→6543 pooler switch was
applied but left an extra `:`. Effects: host `pytest` fails at collection with
`ValueError: invalid literal for int() with base 10: ':6543'`, and the running containers
still hold the pre-edit value from creation time, so **the stack dies on next restart**.
Proven to be the sole cause: supplying a corrected URL via env override (without touching
`.env`) gives **105/105**, which also confirms port 6543 works. One character; `.env` is
out of scope for me to edit.
