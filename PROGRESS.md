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
| P0-2 | Legal Risk Report unreachable — `processContract()` never called | 🔄 Code applied, **verification incomplete** |
| P0-3 | Container image 18.8 GB; bge-m3 downloads 4.3 GB at import | ⬜ Open |
| P0-4 | Supabase credential in git history + plaintext `.env` — needs rotation | ⬜ Open (**user action**) |
| P0-5 | **NEW** — Supabase session pooler caps at 15 connections; worker backlog exhausts it (`EMAXCONNSESSION`) | ⬜ Open |

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
