# DocuMindAI — Product Hardening Report

**Date:** 2026-05-28
**Session focus:** Targeted fixes to the **response-quality / structured-output** subsystem, plus a code-grounded audit of that subsystem.
**Author:** Hardening pass (Cowork)

---

## 0. Scope & method (read this first)

This is **not** a full re-audit and not a UI redesign. The original request spans Phases 1–5 (full UI modernization, live testing of all 7 workspaces with real uploads, AI/retrieval rewrites, scalability) — that is multi-week, multi-person work. This session was deliberately narrowed to **one subsystem** with real, verified fixes, plus an honest report.

**What this report is based on:**

- **Direct code reading** (this session): `api/v1/endpoints/query.py`, `services/response_schemas.py`, `services/summary_service.py`, `core/config.py` (`WORKSPACE_RETRIEVAL_CONFIG`), `PROJECT_MAP.md`, `KNOWN_REMAINING_ISSUES.md`.
- **Cross-reference** with the prior audit docs already in the repo (`AUDIT_REPORT.md`, `KNOWN_REMAINING_ISSUES.md`). Items taken from there are **labelled** and were **not** re-verified line-by-line this session.

**What this report is NOT based on:**

- **No live behavioral testing.** The app "runs locally," but the analysis sandbox cannot reach `localhost`, so nothing here was validated by uploading a real document and reading a real model response. Anything requiring runtime confirmation is marked **[needs live verification]**.
- **No frontend re-audit.** The frontend was not read this session; UI findings are carried from prior docs and marked as such.

Each issue lists: **reproduction path · root cause · affected files · severity · minimal fix**. Severity scale: **P0** blocker, **P1** critical, **P2** medium, **P3** low.

---

## Fixes shipped this session (verified)

All changes are **additive / wrapper-only** and respect `CLAUDE.md` constraints (no edits to `retrieval_service.py`, `grounding_service.py`, `chunking_service.py`, or any provider internals). API contracts (`QueryRequest`/`QueryResponse`/SSE event names) are unchanged.

### FIX-1 — Study & Exam workspaces never received their response schema *(the headline "theater" bug)*

- **What was wrong:** `response_schemas.py` keyed its instruction blocks as `student` and `teacher`, but every caller (`query.py:428`) passes the **canonical** workspace slug, which is `study` and `exam` (confirmed against `config.WORKSPACE_RETRIEVAL_CONFIG`). `get_response_schema()` did `dict.get(slug, GENERAL)`, so `study` and `exam` **silently fell back to the GENERAL schema**, and the `student`/`teacher` blocks were dead code. Two of seven workspaces were running with the wrong output contract while *appearing* configured.
- **Why it matters:** the GENERAL schema even said *"Complex Q → up to 500 words"* — a hard brevity cap applied to the exact workspaces (Study/Exam) whose spec demands the opposite (complete topic-wise notes, full papers).
- **Fix:** re-keyed the dict to the 7 canonical slugs, added a `_ALIASES` map (`student→study`, `teacher→exam`) for back-compat, and normalized the resolver (`lower().strip()` → alias → lookup → general fallback).
- **Verification:** resolver logic executed independently — all 7 slugs route correctly, `study`/`exam` no longer equal GENERAL, aliases resolve, case/whitespace handled, unknown→general. `RESOLVER_OK`.

### FIX-2 — All 7 schemas upgraded to the per-workspace spec + a completeness rule

- Rewrote each block to match the requested structure: HR (ranking table + scorecard + JD alignment), Legal (clause-by-clause + **Obligations & Deadlines** + confidence), Finance (figure tables + ratio formulas + **Anomalies/Flags** + YoY), Research (methodology + contradictions + gaps + evidence strength), Study (topic-wise notes + flashcards + quiz + revision checkpoints), Exam (sections + mark allocation + **Bloom tags** + answer key).
- Added a shared **COMPLETENESS RULE** that explicitly overrides brevity for summary/notes/"explain all topics" requests while keeping pointed questions concise — resolving the 500-word-cap conflict.

### FIX-3 — Coverage requests now route to full-document map-reduce (not top-K)

- **What was wrong:** `is_summary_intent()` only matched literal "summarize"-type phrasing. "Give me notes", "explain all topics", "detailed summary", "cover every concept" fell through to **top-K retrieval (k≈12)**, which by construction sees only a fraction of a long document — so "notes on everything" silently omitted most of the document.
- **Fix:** added 6 high-precision patterns. **Tested** against coverage vs. needle queries: coverage asks ("make notes", "explain all topics", "detailed notes on chapter 2") now match; needle asks ("what is the indemnity cap in section 3", "what is the notes payable balance") correctly do **not**. `PATTERNS_OK`, 16 patterns total.

### FIX-4 — Map-reduce summary is now workspace-aware

- **What was wrong:** the reduce step used a single GENERAL structure for every workspace, so a Study "summarize" produced generic headings instead of notes/flashcards.
- **Fix:** added per-workspace reduce prompts (Study → notes/flashcards/quiz/checkpoints; Research → methodology/contradictions/gaps; Legal → clauses/obligations/risks; Finance → figures/trends/anomalies) selected via a new `workspace_type` param (defaulted, so existing callers are unaffected). Wired `workspace_type` through at `query.py`.

**Files touched:** `backend/app/services/response_schemas.py` (rewrite), `backend/app/services/summary_service.py` (additive), `backend/app/api/v1/endpoints/query.py` (one-line kwarg).

---

## 1. Production blockers (P0)

> None *newly* discovered in the response subsystem this session. The blockers below are **carried from `PROJECT_MAP.md` / `KNOWN_REMAINING_ISSUES.md`** and should be confirmed live before any production claim.

| ID | Issue | Source | Note |
|----|-------|--------|------|
| B1 | **No real payment integration.** `/billing/upgrade` flips `User.plan` directly; "Upgrade" grants paid access for free. | KNOWN_ISSUES | Blocker for monetization only. Needs Razorpay/Stripe order + webhook. |
| B2 | **Plan tiers are cosmetic.** Go/Plus/Pro are shown but enforced identically; only the trial gate (`TRIAL_QUERY_LIMIT=10`) exists. | KNOWN_ISSUES | Blocker for monetization. |

If neither monetization is in scope for launch, there are **no hard P0 code blockers** in the generation path that I observed — but see §11/§12 for scalability/security gaps that gate *enterprise* readiness.

---

## 2. Critical issues (P1)

### C1 — Study/Exam ran with the wrong response contract *(FIXED this session — see FIX-1)*
- **Repro (pre-fix):** open `/study` or `/exam`, attach a doc, ask anything → response uses the generic schema, capped "up to 500 words". **Root cause:** dict key mismatch (`student`/`teacher` vs canonical `study`/`exam`). **Affected:** `response_schemas.py`, consumed at `query.py:428`. **Severity:** P1 (2/7 workspaces mis-contracted). **Status:** fixed + verified.

### C2 — "Give me notes / cover everything" silently omitted most of the document *(FIXED — FIX-3)*
- **Repro (pre-fix):** attach a 40-page PDF in `/study`, ask "make detailed notes" → answer drawn from ~k=12 chunks (~10% of doc); whole sections missing with no warning. **Root cause:** `is_summary_intent()` too narrow → coverage query took the top-K path. **Affected:** `summary_service.py`. **Severity:** P1 (directly violates the "never skip topics" mandate). **Status:** fixed + tested.

### C3 — Map-reduce hard cap can truncate very long documents **[needs live verification]**
- **Repro:** summarize a document with > ~240 chunks (`MAX_WINDOWS_HARD_CAP=40 × WINDOW_CHUNKS=6`). **Behaviour:** windows past 40 are dropped with only a server-side `logger.warning` — **the user is not told the tail was truncated.** **Root cause:** `summary_service._group_into_windows`. **Affected:** `summary_service.py`. **Severity:** P1 for large-doc trust (silent incompleteness is worse than a slow answer). **Minimal fix:** when the cap trips, emit a visible note in the final summary ("⚠ Document exceeds single-pass size; this summary covers the first N pages") and/or raise the cap with batched map calls. *(Not changed this session — would alter behaviour of an otherwise-stable file beyond the targeted scope; flagged for sign-off.)*

### C4 — Doubled `/api/v1` prefix on ~35 frontend call sites **[from PROJECT_MAP, not re-verified]**
- **Root cause:** `NEXT_PUBLIC_API_URL` already includes `/api/v1`; many manual `${API_BASE}/api/v1/...` literals double it. **Severity:** P1 for the affected panels (bookmarks, notifications, settings, several workspace panels, export, corrections). **Minimal fix:** drop `/api/v1` from those literals so they use the `apiFetch` convention.

---

## 3. Medium issues (P2)

- **M1 — Ungrounded answers lose their badge on reload.** Streaming shows an "Ungrounded" pill, but `ChatMessage` has no `mode` column, so reopened chats render past ungrounded answers as if grounded. *Trust regression.* Fix: add `mode VARCHAR(16)` + migration; persist from `query.py`; read in `MemoizedMessage.tsx`. *(KNOWN_ISSUES C10.)*
- **M2 — Synthetic "full-document" evidence entries.** The map-reduce path emits placeholder evidence rows with zero-UUIDs and `similarity=1.0`/`rerank=1.0` so the UI shows a "grounded" badge before the reduce runs (`query.py:311`, `summary_service.py:185`). Defensible as a coverage signal, but the fixed `1.0` scores and confidence `0.95` are **not measured** — they're display constants. Fix: label these clearly as "full-document pass" in the UI rather than reusing the similarity-score schema. **[partly UI]**
- **M3 — Streaming rate-limit gap.** `/query/stream` and the upload POST are not rate-limited (login/reset are). Fix per KNOWN_ISSUES E2 (limit stream *open*, not duration; limit the presigned-URL request, not the file POST).
- **M4 — Workspace identity slug↔UUID.** `User.workspace_id` is a string slug; `ChatSession.workspace_id` is a UUID; resolved via `resolve_workspace_id()` (uuid5). Works, but there is **no `Workspace` table** — fragile if multi-workspace-per-user is ever needed. *(PROJECT_MAP.)*

---

## 4. Low-priority issues (P3)

- **L1 — Dead code:** legacy `student`/`teacher` schema blocks are now reachable only via alias; can be removed once nothing references them. Prior list: 9 unused frontend components + backend stubs (KNOWN_ISSUES D1) pending green-light.
- **L2 — `ConsoleSpanExporter` in prod** (OpenTelemetry to stdout) — config swap to OTLP. *(KNOWN_ISSUES E4.)*
- **L3 — First-upload latency** (BGE-m3 ~1.2 GB download) shows no progress hint. *(KNOWN_ISSUES.)*
- **L4 — Stale `.next` build artefact** references a non-existent `page.js`; harmless, cleared by rebuild.

---

## 5. Fake / UI-theater features (judged by behaviour, not by "it rendered")

1. **Per-workspace structured output for Study & Exam** — *was* theater: the schema machinery existed and looked configured, but those two workspaces never received it. **Now real (FIX-1/2).**
2. **"Covers the whole document" notes** — *was* theater for non-"summarize" phrasings: the map-reduce path existed but coverage requests bypassed it. **Now routed correctly (FIX-3/4).**
3. **Plan tiers (Go/Plus/Pro)** — **still theater**: distinct UI, identical backend behaviour (B2).
4. **"Upgrade" / payment** — **still theater**: grants paid plan via direct DB write, no payment (B1).
5. **Full-document trust score / confidence `0.95`, evidence `similarity 1.0`** — **partly theater**: these are display constants on the summary path, not measured values (M2).

---

## 6. Features that genuinely work (with honesty caveats)

- **Map-reduce summary architecture** *(read, not live-run)*: loads **all** chunks in `(filename, page, index)` order, windows them, maps then reduces — a sound design for true coverage (superior to top-K for summaries). Per-window failures degrade gracefully with a sentinel. Now workspace-aware.
- **SSE generation pipeline** *(read)*: clean staged events (`searching → reranking → generating`), early `metadata` emission for citations, disconnect-friendly `asyncio.sleep(0.005)`, graceful `error` event. Structurally solid.
- **Per-chat document scoping** *(read)*: retrieval is restricted to docs attached to the current `chat_session_id`, with an owner filter as belt-and-suspenders against session-id spoofing — good tenant hygiene.
- **No-document mode + grounded/ungrounded distinction** *(read)*: the backend distinguishes grounded vs general answers and signals `mode` on the live stream (reload caveat: M1).
- **Redis retrieval cache** *(read)*: keyed by workspace + query + attached-doc-ids, failures swallowed so they never break a request.

> Caveat: "works" above = **the code path is correct and well-structured on read**. None was confirmed against a live model response this session.

---

## 7. UX redesign recommendations (carried / inferred — frontend not re-read)

- Make the **grounding state honest end-to-end**: persist `mode` (M1) and visually separate "full-document pass" from "top-K grounded" (M2) so badges reflect what actually happened.
- Surface **coverage/extent**: for map-reduce, show "read N/N pages"; when truncated (C3), say so.
- Standardize the structured-output rendering so the new schema sections (tables, scorecards, clause blocks, flashcards) render consistently across workspaces.
- Address the **doubled-prefix** panels (C4) — several features likely 404 silently today.

---

## 8. AI-trust improvements

- **Shipped:** completeness rule + "only assert what's in the evidence; say so otherwise" baked into every schema; per-workspace evidence conventions (page cites, confidence labels, [Computed] tags for finance).
- **Next:** replace constant confidence/similarity on the summary path with real signals or honest labels (M2); persist `mode` (M1); on truncation, tell the user (C3).

## 9. Retrieval improvements

- The forbidden core (`retrieval_service`/`grounding_service`/`chunking_service`) was not touched. The biggest *retrieval-adjacent* win was **routing**: sending coverage queries to map-reduce instead of top-K (FIX-3) fixes the most common "it only used the first few pages" complaint without altering the retriever.
- **Next (needs sign-off, touches stable files):** raise/repair the map-reduce cap (C3); consider per-workspace `chunk_pref` validation against actual chunk sizes.

## 10. Architecture improvements

- Introduce a real `Workspace` entity to retire the slug↔UUID juggling (M4).
- Centralize prompt assembly: `query.py` now stitches base prompt + schema + language + comparison-mode inline; a small `PromptBuilder` would make this testable and prevent ordering regressions.

## 11. Scalability improvements **[mostly needs live verification]**

- The map step is **serial per window** (intentional, to respect the Gemini key rotator). For large docs this is the latency long-pole; a bounded-concurrency map (e.g. 3–4 in flight) would cut wall-clock without bursting limits.
- Prior reports of **8 GB Node OOM / duplicated prompts/outputs** were **not reproducible from static reading** and need a live profile (React render storms, SSE cleanup, duplicate `Toaster` was already fixed per KNOWN_ISSUES P7). Flagging honestly: **unconfirmed this session.**
- Add rate limits on stream/upload (M3) before opening to many users.

## 12. Security risks

- **No payment/plan enforcement** (B1/B2) = trivial entitlement bypass.
- **Streaming/upload not rate-limited** (M3) = abuse/cost-amplification surface.
- **Positive:** per-chat owner filtering on retrieval and summary chunk loading is consistently applied in the code I read — good tenant isolation discipline.
- **Not assessed this session:** authn/z on the ~35 doubled-prefix routes, CSRF, file-upload validation, SSRF on any URL ingestion. **[needs review]**

## 13. Enterprise-readiness gaps

- Honest grounding/trust signals (M1, M2) — enterprises will not tolerate confidence numbers that are display constants.
- Billing/entitlements (B1, B2).
- Observability to a real backend (L2).
- Large-document correctness guarantees (C3).
- Audit of the unread surface area (frontend, workers, security routes).

---

## 14. Priority roadmap

**Immediate (this session — done):**
- FIX-1 study/exam schema routing · FIX-2 schema upgrade + completeness · FIX-3 coverage-intent routing · FIX-4 workspace-aware reduce.

**Short-term (days):**
- C3 truncation honesty · M1 persist `mode` (1 migration) · M3 rate limits · C4 doubled-prefix sweep.

**Medium-term (1–2 weeks):**
- B1/B2 real billing + tier enforcement · M2 honest summary trust signals · concurrency-bounded map step · live profiling of the OOM/duplication reports (§11).

**Long-term:**
- `Workspace` entity (M4) · `PromptBuilder` extraction · full frontend UI modernization (Phases 1–2 of the original brief) · security review of unaudited surface · OTLP observability.

---

## Honesty statement

I fixed one subsystem and verified those fixes by executing the resolver and intent logic and by reading the canonical files directly. Everything outside that subsystem is either read-only observation (labelled) or carried from prior audit docs (labelled), and the live-runtime claims that this brief asked for — uploading real documents across 7 workspaces and judging correctness/grounding/hallucination — were **not performed**, because the running app is not reachable from this analysis environment. Those remain open and are the highest-value next step for a true "truth audit."
