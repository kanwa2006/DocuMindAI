# DocuMindAI — Debug Master Plan

> **Purpose:** A complete, dependency-ordered repair roadmap. Each issue is one self-contained implementation task with everything a repair model (Claude Fable 5) needs to fix it without rediscovering the architecture.
> **Constraint for the repair phase:** this document does **not** modify code. It documents *what* to change and *why*. The actual edits happen later.
> **Verification basis:** every finding below was re-verified against the live source (not trusted from prior docs). Line numbers reflect the current tree at audit time; the repair model should re-confirm exact lines before editing.
> **Companion:** [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) (structure, flows, import graph, change-impact matrix). Source findings: [FINAL_AUDIT.md](FINAL_AUDIT.md).

## How to use this file
- Work **top-down by phase** (Phase 1 = Critical first). Within a phase, follow the **Safe Implementation Order** table at the end.
- Each task lists **Dependencies** (must be done first) and **Blocks** (what waits on it).
- "Estimated token usage" is a planning hint for the repair model's own budget (read + edit + verify for that task).
- Legend for IDs: `C-*` Critical, `H-*` High, `M-*` Medium, `L-*` Low. IDs are stable and match [FINAL_AUDIT.md](FINAL_AUDIT.md) where possible; split/newly-discovered issues get fresh IDs (noted).

---

# PART 1 — ISSUE TASKS

---

## C-1 — `llm_service.get_embedding()` is called 12 times but never defined

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** Added `async def get_embedding(self, text: str) -> List[float]` to `LLMService` (`backend/app/services/llm_service.py`). It routes through `embedding_service.generate_embeddings([text])` (single source of truth, 1024-dim) via `run_in_executor` so the sync CPU-bound encode never blocks the event loop; `embedding_service` is imported lazily inside the method so importing `llm_service` does not trigger the embedding model load. Raises `ValueError` on an empty provider result (no silent fallback).
> **Verification:** new regression tests `backend/tests/test_get_embedding.py` (method exists; returns 1024-dim vector with provider mocked; raises on empty result) — fail before / pass after. Full suite `pytest tests/ -v`: 5 passed. All 12 call sites (`legal.py:168`, `finance.py:416`, `study.py:97,132`, `research.py:366,400`, `legal/finance/study/research_tasks.py`) now resolve the method.
> **Residual risk:** end-to-end 200s from the four `*/search` endpoints additionally require populated domain embeddings (C-2) and a live pgvector DB; dimension consistency depends on M-4 (Gemini fallback pads 768→1024).

- **Issue ID:** C-1
- **Severity:** Critical
- **Category:** AI / Backend / API
- **Files involved:**
  - Missing definition: `backend/app/services/llm_service.py` (class `LLMService` / `GeminiLLMProvider`)
  - Endpoint call sites: `endpoints/legal.py:168`, `endpoints/finance.py:416`, `endpoints/study.py:97`, `endpoints/study.py:132`, `endpoints/research.py:366`, `endpoints/research.py:400`
  - Worker call sites: `workers/tasks/legal_tasks.py:64`, `workers/tasks/finance_tasks.py:63`, `workers/tasks/study_tasks.py:53`, `workers/tasks/study_tasks.py:67`, `workers/tasks/research_tasks.py:61`, `workers/tasks/research_tasks.py:74`
  - Existing embedding logic to reuse: `services/embedding_service.py` (`embedding_service.generate_embeddings(list[str]) -> list[list[float]]`, synchronous)
- **Functions involved:** `LLMService` (no `get_embedding`); `semantic_search_clauses`, `semantic_search_transactions`, `semantic_search_study`, `ai_tutor_chat`, `semantic_search_research`, `ai_copilot_chat`; worker `process_*_batch` embedding lines.
- **Execution path:** frontend `searchClauses/searchTransactions/searchStudyMaterial/searchResearch` → `GET /{ws}/…/search` → endpoint calls `await llm_service.get_embedding(query)` → `AttributeError`. In workers, `process_*_batch` calls `await llm_service.get_embedding(text)` when populating per-row embeddings.
- **Root cause:** embedding generation lives in `embedding_service`, not `llm_service`. Code was written against an `llm_service.get_embedding` API that was never implemented.
- **Current behavior:** the four `*/search` endpoints raise `AttributeError` → HTTP 500 (no fallback). `study/tutor/chat` and `research/copilot/chat` call it inside `try/except` and silently fall back to recency ordering. The four worker tasks (if ever registered — see C-2) would also crash on the embedding line.
- **Expected behavior:** a single async embedding method returns a 1024-dim vector for a query/text; search endpoints run pgvector `l2_distance`/cosine ordering; worker tasks populate `.embedding` columns.
- **Why it happens:** API drift — a method name assumed but never added.
- **Business impact:** every workspace's "semantic search" is broken (Legal clause search, Finance transaction search, Study/Research search). Domain embedding population is broken, so even fixing C-2 won't make those searches work.
- **Technical impact:** guaranteed 500s; unpopulated `embedding` columns on `legal_clauses`, `finance_transactions`, `study_flashcards`, `research_findings`, `study_notes`, `research_papers`.
- **Risk level:** High blast radius, but the fix is additive and low-risk.
- **Dependencies:** none. (Enables C-2's tasks to actually succeed.)
- **Can it be fixed independently?** Yes — add the method. Recommended: `async def get_embedding(self, text: str) -> list[float]` that wraps `embedding_service.generate_embeddings([text])[0]` via `run_in_executor` (it is a sync, CPU-bound call).
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 20–40 min.
- **Estimated token usage:** 8–15K (read llm_service + embedding_service + one call site to confirm shape).
- **Regression risk:** Low.
- **Regression areas:** any code path that starts using the new method; ensure the returned dimensionality (1024) matches the DB `Vector(1024)` columns. Note the Gemini fallback pads 768→1024; confirm consistency for pgvector distance ops.
- **Required tests:** unit test asserting `get_embedding` returns a `len==1024` list; endpoint test for one `*/search` returning 200.
- **Manual verification steps:** call `GET /api/v1/study/search?query=test` with a session cookie → expect 200 + JSON list (not 500).
- **Automated verification steps:** add a pytest hitting each `*/search` endpoint with a mocked embedding provider; assert 200.
- **Suggested implementation order:** 1 (do before C-2 so registered tasks don't crash).
- **Success criteria:** `get_embedding` exists; all four `*/search` endpoints return 200; worker embedding lines no longer raise.
- **Notes:** Prefer routing through `embedding_service` (single source of truth) rather than adding a second embedding path. Keep it async-safe (offload the sync encode).

---

## C-2 — Celery worker `include` omits legal/finance/study/research (and email) task modules

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** Added `legal_tasks`, `finance_tasks`, `study_tasks`, `research_tasks` to `celery_app.py include`. **Decision:** `email_tasks` deliberately left unregistered — email is sent synchronously via `email_service`; the module is dead code (removal deferred to its own issue). All four modules verified to import cleanly under the worker (regression risk for worker boot).
> **Verification:** `backend/tests/test_worker_registration.py` — asserts all five `process_*_batch` tasks are in `celery_app.tasks` and every `include` module imports. Passed. C-1 was landed first, so the tasks' `get_embedding` calls now resolve.
> **Residual risk:** end-to-end task execution requires a running broker/worker (`-Q main-queue,celery` already consumes `main-queue`, so these tasks are now registered *and* consumed).

- **Issue ID:** C-2
- **Severity:** Critical
- **Category:** Worker / Infrastructure
- **Files involved:** `backend/app/workers/celery_app.py:9-23` (`include`), `:28-42` (`task_routes`); `docker-compose.yml` worker command (`-Q main-queue,celery`); task modules `workers/tasks/{legal,finance,study,research,email}_tasks.py`; dispatch sites `endpoints/{legal:133,finance:381,study:65,research:334}.py`.
- **Functions involved:** `process_contract_batch`, `process_finance_batch`, `process_study_batch`, `process_research_batch` (defined but not registered on the worker); their `.delay(...)` producers.
- **Execution path:** endpoint `POST /{ws}/process` → `process_*_batch.delay(...)` enqueues to `main-queue` → worker (`-Q main-queue,celery`) has no registered handler because it never imported the module → task sits unacknowledged / errors as unregistered.
- **Root cause:** `include` list was not kept in sync with `task_routes` and the endpoints that dispatch these tasks.
- **Current behavior:** legal/finance/study/research async processing never runs; documents stay "queued." `email_tasks` also unregistered (email is mostly sent synchronously elsewhere, so lower impact).
- **Expected behavior:** the worker imports and registers all task modules it is routed to consume.
- **Why it happens:** manual `include` list drift.
- **Business impact:** four workspaces' background ingestion (clause/transaction/flashcard/finding extraction + embeddings) never completes.
- **Technical impact:** `KeyError`/"Received unregistered task" on the worker; domain tables never populated.
- **Risk level:** Medium (config change), but depends on C-1 to actually succeed.
- **Dependencies:** **C-1** (tasks call `get_embedding`), and functionally overlaps **H-3** (queue consumption).
- **Can it be fixed independently?** The registration change is independent, but the tasks won't succeed until C-1 lands.
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 15–30 min.
- **Estimated token usage:** 5–10K.
- **Regression risk:** Low–Medium (adds task imports at worker boot; import errors in those modules would now crash the worker).
- **Regression areas:** worker startup (import-time errors in the newly-included modules — verify they import cleanly, especially given C-1/H-7).
- **Required tests:** a test asserting every module in `task_routes` is importable and its task is present in `celery_app.tasks`.
- **Manual verification steps:** start the worker; run `celery -A app.workers.celery_app inspect registered`; confirm the four tasks appear.
- **Automated verification steps:** pytest that imports `celery_app` and asserts `process_contract_batch.name in celery_app.tasks`.
- **Suggested implementation order:** 2 (after C-1).
- **Success criteria:** the four `process_*_batch` tasks are registered and execute to completion on an uploaded document.
- **Notes:** Also either remove or implement `embedding_tasks`/`retrieval_tasks` routes (they reference modules that don't exist — see H-3). Decide whether `email_tasks` should be included or removed as dead.

---

## C-3 — Multi-engine OCR (PaddleOCR + Docling) is not wired into the ingestion path

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note (option a — inline):** `OCRService.extract_document_stream` now routes non-native (scanned/image) pages through `ocr_orchestrator.extract_document`: page rendered to a temp PNG at 2× zoom, `hint="handwritten"` (PaddleOCR primary, Docling fallback), fresh event loop per call (sync worker context, same pattern as proactive insights). Native pages and PPTX are byte-for-byte unchanged. On OCR failure the page falls back to raw `page.get_text("text")` with an **ERROR log** and `ocr_failed`/`requires_fallback` metadata (observable, not silent). New config `OCR_SCANNED_ENABLED` (default true; `Settings` + `backend/.env.example`) is the rollback toggle for the heavy engines (§31.4).
> **Also fixed (prerequisite):** `ocr_orchestrator.py` targeted the PaddleOCR **2.x** API while requirements install **3.5.0** — `use_gpu`/`use_angle_cls` kwargs no longer exist (TypeError at init, uncaught by the old `except ImportError`) and the result format changed. Init now uses `use_textline_orientation=True, lang='en'` (device follows the installed paddlepaddle build — resolves the CPU-host `use_gpu=True` concern), engine init failures are caught broadly and logged at ERROR, and `PaddleOCREngine.extract` parses both the 3.x (`rec_texts`/`rec_scores`/`rec_polys`) and legacy 2.x formats.
> **Verification:** `backend/tests/test_ocr_ingestion.py` (5 tests): native PDF never touches the orchestrator; scanned page routes through it with engine/confidence metadata; failure path is loud with observable metadata; config kill-switch honored; 3.x result parsing. Full suite: 22 passed.
> **Residual risk:** real Paddle/Docling inference (model downloads, memory, latency on the shared CPU worker) not exercised in the test environment — first production scanned upload should be monitored; `ocr_gpu_queue` remains available for a dedicated worker (H-3).

- **Issue ID:** C-3
- **Severity:** Critical
- **Category:** OCR / Worker / AI
- **Files involved:** `workers/tasks/document_tasks.py:55` (uses `OCRService.extract_document_stream`); `services/ocr_service.py:128-181` (PyMuPDF path; scanned fallback at `:150-154`); `services/ocr_orchestrator.py` (`OCROrchestrator`, `DoclingEngine`, `PaddleOCREngine`, `OCRValidationGateway` — unused by ingestion); `workers/tasks/ocr_tasks.py` (only caller of the orchestrator, routed to `ocr_gpu_queue`); `services/extraction_router.py` (pymupdf4llm-first router, also unused by ingestion).
- **Functions involved:** `process_document` (ingestion), `OCRService.extract_document_stream`, `OCROrchestrator.extract_document`, `ocr_tasks.extract_document_ocr`.
- **Execution path:** upload → `process_document` → `OCRService.extract_document_stream` (PyMuPDF/pptx only). The orchestrator path (`ocr_tasks` → `ocr_gpu_queue`) is never invoked and its queue has no consumer (see H-3).
- **Root cause:** the orchestrator was built as a separate subsystem and never connected to `process_document`; a prior "skip OCR" optimization (extraction_router) left multiple parallel, unused extraction paths.
- **Current behavior:** all uploads are extracted by PyMuPDF text extraction; scanned/handwritten/image pages fall back to `page.get_text("text")` (returns little/nothing) — a stub comment says Tesseract/EasyOCR "would be injected here."
- **Expected behavior:** scanned/image documents route to a real OCR engine (PaddleOCR) and structured/tabular PDFs to Docling, with the validation gateway selecting the best output — matching the product claim.
- **Why it happens:** feature built in isolation; ingestion never updated to call it.
- **Business impact:** the advertised "handles handwritten/rotated/scanned + tables" capability does not work; such uploads produce empty retrieval → refusals/wrong answers.
- **Technical impact:** dead subsystem; wasted PaddleOCR/Docling dependencies; scanned docs index no chunks.
- **Risk level:** High (touches the core ingestion worker); PaddleOCR/Docling are heavy (GPU/CPU, model downloads) so wiring them has performance/deployment implications.
- **Dependencies:** interacts with **H-3** (needs a consumer for the OCR queue) and **C-2** (worker registration patterns).
- **Can it be fixed independently?** Partially — you can route scanned pages through the orchestrator inside `process_document`, but you must also ensure a worker consumes the OCR work (either inline in `process_document` or via a consumed queue).
- **Estimated implementation difficulty:** High.
- **Estimated implementation time:** 4–8 h (incl. engine setup + perf testing).
- **Estimated token usage:** 25–50K.
- **Regression risk:** High (changes ingestion behavior, timing, memory).
- **Regression areas:** all document processing; worker memory/latency; `document_pages`/`document_chunks` content; retrieval quality.
- **Required tests:** ingest a native PDF (unchanged text), a scanned/image PDF (now produces text), a tabular PDF (Docling tables). Golden-text assertions.
- **Manual verification steps:** upload a handwritten/scanned PDF; confirm `document_chunks` are created and a grounded answer is returnable.
- **Automated verification steps:** integration test with a small scanned fixture asserting `chunks > 0`.
- **Suggested implementation order:** after worker/queue fixes (C-2/H-3), before/with H-1.
- **Success criteria:** scanned documents yield non-empty chunks; native PDFs unchanged; engine selection logged.
- **Notes:** Decide the architecture: (a) call the orchestrator inline in `process_document` for non-native pages, or (b) enqueue `ocr_tasks` and consume `ocr_gpu_queue`. Option (a) is simpler operationally. Beware CPU-only hosts (PaddleOCR `use_gpu=True` in `ocr_orchestrator.py` will fail/fallback).

---

## C-4 — Veritas Trust Engine is not invoked on the main `/query/stream` path

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** `endpoints/query.py` now accumulates the streamed answer on both paths (retrieval and map-reduce summary), computes `veritas_engine.compute_trust_score` post-stream, and emits an `event: trust_report` SSE frame after tokens/disclaimer and before `done`. `veritas_engine.py` untouched (§8a — wired via the caller). New helpers `_veritas_sse_payload` (maps the backend dataclass to the frontend `TrustReport` interface in `TrustScoreBadge.tsx`: `level` HIGH|MEDIUM|LOW with VERY_LOW/UNKNOWN→LOW, `evidence_items`, `factors[{name,weight,score}]`) and `_compute_trust_event` (failure logs at ERROR and skips the event — never breaks token delivery, never fabricates a score).
> **Decisions:** trust_report is emitted **only for grounded answers** — scoring a general-knowledge answer with a document-grounding heuristic would fabricate meaning; the UI already shows an "Ungrounded" badge in general mode. The summary path's hardcoded `confidence_score: 0.95` metadata is unchanged (drives the grounded badge) — the real signal is now the trust_report; noted as residual polish.
> **Verification:** `backend/tests/test_trust_report_event.py` (payload matches the frontend interface; SSE frame well-formed; VERY_LOW/UNKNOWN map to LOW; failure path loud-but-not-fatal). Full suite: 17 passed. SSE event names unchanged otherwise (`lib/api.ts` already parses `trust_report` — no frontend change needed).
> **Residual risk:** Veritas factors remain heuristic (hardcoded constants; no real contradiction detection) — upgrading the engine itself is future work, out of C-4's scope.

- **Issue ID:** C-4
- **Severity:** Critical (product-claim gap) / functionally Medium
- **Category:** AI / Streaming / API
- **Files involved:** `services/veritas_engine.py` (heuristic, `compute_trust_score`); `services/deep_research_agent.py:72,82` (only caller); `endpoints/query.py` (`/query/stream` emits grounding `confidence_score` at `:407`, hardcodes `0.95` at `:321`); frontend `lib/api.ts` `askQuestionStream` handles a `trust_report` SSE event that the main path never emits; `components/veritas/TrustScorePanel.tsx`.
- **Functions involved:** `VeritasEngine.compute_trust_score`, `ask_question_stream.event_generator`.
- **Execution path:** `/query/stream` → grounding → LLM stream → emits `metadata.confidence_score` (avg rerank), never calls Veritas. Frontend `onTrustReport` is wired but unused for normal queries.
- **Root cause:** Veritas wiring stopped at the (broken) Research agent; never integrated into the shared query path.
- **Current behavior:** the UI shows grounding confidence (rerank average), not a Veritas 0–100 trust score. README claims a trust score on "every response."
- **Expected behavior:** after generation, compute a Veritas report over the answer + evidence and emit it as a `trust_report` SSE event for every workspace query.
- **Why it happens:** incomplete integration.
- **Business impact:** the flagship "trust score on every answer" is not delivered.
- **Technical impact:** dead `trust_report` handler; misleading confidence semantics.
- **Risk level:** Medium.
- **Dependencies:** none technically; **M-4/M-10** (silent-degradation) affect the meaningfulness of inputs; the Veritas heuristic itself may warrant improvement (see Notes).
- **Can it be fixed independently?** Yes — call `veritas_engine.compute_trust_score(answer, evidence_metadata, query, document_ids)` after the stream completes and emit a `trust_report` event.
- **Estimated implementation difficulty:** Medium (streaming ordering: Veritas needs the full answer, so emit after tokens finish).
- **Estimated implementation time:** 1–2 h.
- **Estimated token usage:** 12–20K.
- **Regression risk:** Low–Medium (adds a post-stream step; must accumulate the answer text without breaking token streaming).
- **Regression areas:** SSE event ordering; frontend rendering of trust panel; summary path (which currently hardcodes 0.95).
- **Required tests:** endpoint test asserting a `trust_report` event is emitted with a 0–100 score.
- **Manual verification steps:** run a grounded query; confirm `TrustScorePanel` populates.
- **Automated verification steps:** parse SSE stream in a test; assert a `trust_report` frame exists.
- **Suggested implementation order:** after C-1 (so retrieval is meaningful).
- **Success criteria:** every `/query/stream` response ends with a real Veritas `trust_report`.
- **Notes:** Consider upgrading Veritas beyond hardcoded constants (its `contradiction` factor does no real detection; factor names don't match the README). At minimum align semantics; ideally make it evidence-driven.

---

## C-5 — Deep Research Agent step 1 calls a nonexistent retrieval API

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** Step 1 rewritten in `services/deep_research_agent.py`: requires a `db` session, converts `document_ids` to UUIDs, calls `RetrievalService.retrieve_chunks(db=…, query=…, top_k=8, document_ids=…)`, renders `<evidence …>` blocks matching the grounding format, and synthesizes `doc_answer` via `llm_service.generate_answer` (grounded prompt contract). The catch-all no longer swallows silently — logs at ERROR with traceback, keeps the degraded VeritasTrustReport(0) path.
> **Verification:** `backend/tests/test_deep_research_agent.py` — happy path (retrieve → synthesize → citations + trust > 0) and loud-failure path (ERROR log + degraded events). Passed. C-6 was required for steps 2/4 (`llm_service.generate`).
> **Discovered during verification:** (1) **C-6** — `llm_service.generate` missing (fixed separately); (2) **N-1** — `deep_research_agent` has **no caller** in any endpoint or frontend code (the audit's "Research deep-research path" doesn't exist as an API). Recorded below.

- **Issue ID:** C-5
- **Severity:** Critical
- **Category:** AI / Backend
- **Files involved:** `services/deep_research_agent.py:80-81` (`from app.services.retrieval_service import retrieval_service` + `await retrieval_service.query(query, document_ids)`); `services/retrieval_service.py` (defines `class RetrievalService` with static `retrieve_chunks`; **no** module-level `retrieval_service`, **no** `query`).
- **Functions involved:** `DeepResearchAgent.research` (step 1), `RetrievalService.retrieve_chunks`.
- **Execution path:** Research "Deep Research" → `deep_research_agent.research()` → step 1 imports `retrieval_service` (ImportError) or calls `.query` (AttributeError) → caught by the `except` at `:89` → `doc_answer=""`, `doc_citations=[]`.
- **Root cause:** written against a `retrieval_service.query(query, doc_ids) -> (answer, citations)` API that does not exist; the real API is `RetrievalService.retrieve_chunks(db=…, query=…, document_ids=…) -> {results, tracing}` and does not generate an answer.
- **Current behavior:** step 1 always fails silently; the agent proceeds web-only/empty; Veritas scores empty chunks.
- **Expected behavior:** step 1 retrieves chunks from the given documents and synthesizes a grounded document answer + citations.
- **Why it happens:** API drift + swallowed exception hides the failure.
- **Business impact:** the "hybrid RAG + web" deep-research feature does no document RAG.
- **Technical impact:** dead branch; misleading trust scores.
- **Risk level:** Medium.
- **Dependencies:** uses `RetrievalService.retrieve_chunks` (needs a `db` session — currently `research()` receives `db`). May reuse `GroundingService` + `llm_service.generate` to form `doc_answer`.
- **Can it be fixed independently?** Yes — rewrite step 1 to call `RetrievalService.retrieve_chunks(db=db, query=query, document_ids=[UUID…])`, then build `doc_answer` via `llm_service.generate_answer`.
- **Estimated implementation difficulty:** Medium.
- **Estimated implementation time:** 1–2 h.
- **Estimated token usage:** 12–20K.
- **Regression risk:** Low (isolated to the research agent).
- **Regression areas:** Research deep-research flow; Veritas inputs.
- **Required tests:** unit test with a stub retrieval returning chunks; assert `doc_answer` non-empty and `doc_citations` populated.
- **Manual verification steps:** run a deep-research query with an attached doc; confirm step 1 reports "Found relevant content in N passages" with N>0.
- **Automated verification steps:** mock `RetrievalService.retrieve_chunks`; assert step 1 populates citations.
- **Suggested implementation order:** with C-1/C-4.
- **Success criteria:** step 1 returns real document evidence; no swallowed exception in the happy path.
- **Notes:** Also stop swallowing the exception silently — log at ERROR so future drift is visible.

---

## C-6 — `llm_service.generate()` is called 10 times but `LLMService` never defines it (newly discovered)

- **Issue ID:** C-6 (discovered 2026-07-18 during C-5 verification; not in the original audit — FINAL_AUDIT C-1 wrongly listed `generate` among `LLMService` methods, conflating the service with its provider)
- **Severity:** Critical
- **Category:** AI / Backend / API
- **Files involved:** `services/llm_service.py` (`LLMService` defines `generate_answer`/`generate_json`/`get_embedding`; **no `generate`** — only `BaseLLMProvider.generate` exists); call sites: `endpoints/legal.py:305,382` (risk-report, compare), `endpoints/finance.py:498,609` (ratios, compare), `endpoints/research.py:215,285` (citations, gaps), `endpoints/reports.py:339`, `app/tasks/report_tasks.py:240`, `services/deep_research_agent.py:147,212` (steps 2/4).
- **Execution path:** endpoint → `await llm_service.generate(system_prompt, user_prompt)` → `AttributeError` → HTTP 500 (or caught-and-degraded in deep_research_agent).
- **Root cause:** same API-drift class as C-1 — callers written against a service-level `generate` that only exists on the provider.
- **Current behavior:** Legal risk-report/compare, Finance ratios/compare, Research citations/gaps, report naming, and report tasks all raise `AttributeError`. This contradicts the audit's "risk-report/ratios work" claims (the audit was read-only and never executed these paths).
- **Expected behavior:** a service-level async `generate(system_prompt, user_prompt) -> str` delegating to the provider (which already carries rotation/fallback/safe-extraction).
- **Fix:** additive one-method delegation on `LLMService` (allowed by REPAIR_RULEBOOK §8a additive-only rule).
- **Dependencies:** none. **Blocks:** full C-5 behavior (agent steps 2/4), Legal/Finance/Research primary endpoints.
- **Required tests:** `generate` exists; delegates to provider (stub provider test).

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** Added `async def generate()` to `LLMService` delegating to `self.provider.generate` (one line of behavior; docstring records the 10 call sites). Regression test `backend/tests/test_llm_service_generate.py` (exists + delegation via injected stub provider).
> **Verification:** targeted pytest green; full suite green. Legal/Finance/Research endpoints now resolve the method (end-to-end 200s additionally need a live DB + Gemini key, unchanged contract otherwise).

---

## H-1 — Default `VECTOR_BACKEND=faiss` is an in-memory NumPy brute-force scan

- **Issue ID:** H-1
- **Severity:** High
- **Category:** AI / Performance / Configuration / Database
- **Files involved:** `core/config.py:64` (`VECTOR_BACKEND="faiss"`); `.env.example:104`; `services/retrieval_service.py:15-18` (`import faiss` guarded, unused), `:67-141` (NumPy fallback branch), `:48-66` (pgvector branch); `requirements.txt` (no `faiss`); pgvector column `models/document_chunk.py`.
- **Functions involved:** `RetrievalService.retrieve_chunks`.
- **Execution path:** query → `retrieve_chunks` → `if settings.VECTOR_BACKEND == "pgvector": <SQL cosine>` else `<load all chunk embeddings into NumPy, compute cosine in Python>`.
- **Root cause:** default config selects a branch that materializes all matching embeddings in memory; FAISS is imported but never used and isn't a dependency.
- **Current behavior:** O(N) memory + compute per query; no ANN index; won't scale; contradicts the "pgvector" marketing.
- **Expected behavior:** default to `pgvector` with a proper vector index (IVFFlat/HNSW) for scalable ANN.
- **Why it happens:** default value + a misnamed "faiss" fallback.
- **Business impact:** poor performance/scalability; misleading capability.
- **Technical impact:** memory pressure on large corpora; latency.
- **Risk level:** Medium (config flip) but must ensure the pgvector path + index exist and embeddings are populated with a consistent dimension.
- **Dependencies:** pgvector extension present (it is, via `ankane/pgvector`); embeddings must be real (M-4). A migration adding a vector index is advisable.
- **Can it be fixed independently?** Yes — set default `VECTOR_BACKEND=pgvector` and add an index migration; keep NumPy as an explicit dev-only fallback.
- **Estimated implementation difficulty:** Medium.
- **Estimated implementation time:** 1–3 h.
- **Estimated token usage:** 15–25K.
- **Regression risk:** Medium (changes retrieval SQL path; index build).
- **Regression areas:** all retrieval/grounding; migration correctness; embedding dimension consistency (bge-m3 1024 vs padded Gemini 768→1024).
- **Required tests:** retrieval golden set comparing pgvector vs NumPy results on a fixture corpus.
- **Manual verification steps:** set `VECTOR_BACKEND=pgvector`; run a query; confirm results + `EXPLAIN` uses the index.
- **Automated verification steps:** test asserting `retrieve_chunks` returns ranked results under `pgvector` mode.
- **Suggested implementation order:** after C-1/M-4 (embeddings must be real to matter).
- **Success criteria:** pgvector is default; an ANN index exists; latency acceptable at scale.
- **Notes:** Remove the misleading `import faiss` or actually implement a FAISS backend; align the label with reality.

---

## H-2 — No Celery Beat service → all scheduled automation never runs

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** Added a dedicated single `beat` service to `infrastructure/docker-compose.yml` (same image/env as the worker; schedule file at `/tmp/celerybeat-schedule` so the bind mount stays clean; comment warns against running a second Beat — duplicate schedules). Chose a dedicated service over `worker -B` so worker scaling never multiplies schedulers. `run_worker_linux.sh` keeps its embedded `-B` for non-Docker local dev (mutually exclusive deployment modes). Beat env includes the Gemini keys because `auto_health_check._check_gemini` needs one.
> **Verification:** compose YAML parses; `test_compose_runs_exactly_one_beat_scheduler` asserts exactly one Beat command in the stack. 5 worker-registration tests passed.
> **Residual risk:** live cadence (auto_health_check every 5 min etc.) verified only by config — first `docker compose up` should confirm Beat logs its schedule entries.

- **Issue ID:** H-2
- **Severity:** High
- **Category:** Infrastructure / Worker / Deployment
- **Files involved:** `workers/celery_app.py:48-82` (`beat_schedule`); `infrastructure/docker-compose.yml` (services: db, pgbouncer, redis, backend, worker, frontend — **no beat**); `automation/auto_*.py`; `railway.json`.
- **Functions involved:** `run_health_check`, `check_api_keys`, `send_daily_digest`, `run_db_cleanup`, `run_subscription_check`, `check_gst_rates`, `check_model_status`, `flag_stale_reviews`.
- **Execution path:** `beat_schedule` entries require a `celery beat` process to enqueue them on schedule; none exists.
- **Root cause:** orchestration missing a Beat container/process.
- **Current behavior:** health alerts, key-rotation checks, digests, DB cleanup, subscription expiry, GST/model checks, stale-review flagging never fire.
- **Expected behavior:** a Beat scheduler process runs alongside the worker.
- **Why it happens:** compose defines a worker but no scheduler.
- **Business impact:** no proactive monitoring/cleanup/subscription enforcement.
- **Technical impact:** silent absence of scheduled maintenance.
- **Risk level:** Low (add a service).
- **Dependencies:** the automation tasks are already in `include`; H-2 just needs a runner. Consider whether to run `worker --beat` (embedded) or a dedicated `beat` service.
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 30–60 min.
- **Estimated token usage:** 6–12K.
- **Regression risk:** Low (new process); ensure single Beat instance (avoid duplicate schedules).
- **Regression areas:** none to existing request paths; watch for duplicate emails if two Beats run.
- **Required tests:** n/a (infra); smoke: Beat starts and logs scheduled entries.
- **Manual verification steps:** `docker compose up`; confirm a beat container schedules `auto_health_check` every 5 min.
- **Automated verification steps:** CI lint of compose; optional: assert `celery beat` command present.
- **Suggested implementation order:** with C-2/H-3 (worker wiring group).
- **Success criteria:** scheduled tasks fire on cadence in the default deployment.
- **Notes:** The health check requires a live Gemini key (`_check_gemini`); ensure Beat env has keys or the check will always alert.

---

## H-3 — Routed queues have no consumer; routes reference nonexistent task modules

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** (1) Removed the phantom `embedding_tasks`/`retrieval_tasks` routes from `celery_app.py task_routes` (modules never existed). (2) Expanded the deployed worker's queue list to `-Q main-queue,celery,export_queue,ocr_gpu_queue` in `infrastructure/docker-compose.yml`, `backend/scripts/run_worker_linux.sh`, `CONTRIBUTING.md`, and `docs/deployment/installation.md`. Queue names/routes preserved so a dedicated GPU worker can later take over `ocr_gpu_queue` without route changes.
> **Verification:** `backend/tests/test_worker_registration.py` — `test_task_routes_reference_existing_modules` (fails on phantom routes) and `test_routed_queues_are_consumed_by_compose_worker` (parses docker-compose; fails on route/queue drift). 4 passed.
> **Residual risk:** OCR/export tasks now execute on the CPU worker — heavy OCR jobs share capacity with ingestion until a dedicated worker is deployed.

- **Issue ID:** H-3
- **Severity:** High
- **Category:** Worker / Infrastructure
- **Files involved:** `workers/celery_app.py:28-42` (`task_routes` → `ocr_gpu_queue`, `embedding_queue`, `retrieval_queue`, `export_queue`); `docker-compose.yml` worker `-Q main-queue,celery`; task modules `ocr_tasks.py`, `export_tasks.py`; **nonexistent** `embedding_tasks.py`, `retrieval_tasks.py`.
- **Functions involved:** `export_tasks.*`, `ocr_tasks.extract_document_ocr`.
- **Execution path:** a task routed to `export_queue`/`ocr_gpu_queue` is enqueued but the single worker consumes only `main-queue`+`celery` → never processed. Routes for `embedding_tasks`/`retrieval_tasks` target modules that don't exist.
- **Root cause:** queue routing not matched to deployed consumers; stale routes.
- **Current behavior:** async exports and OCR-queue tasks never run; phantom routes are dead config.
- **Expected behavior:** every routed queue has a consumer (either add `-Q` entries or dedicated workers), and routes reference real modules.
- **Why it happens:** aspirational GPU-worker architecture never deployed.
- **Business impact:** async DOCX/report exports and any OCR-queue work never complete.
- **Technical impact:** silently stuck tasks.
- **Risk level:** Low–Medium.
- **Dependencies:** overlaps C-2 (`include`), C-3 (OCR path decision), H-2 (Beat).
- **Can it be fixed independently?** Yes — either expand the worker `-Q` list to include `export_queue`/`ocr_gpu_queue` (and register those modules) or route those tasks to `main-queue`/`celery`. Remove phantom `embedding_tasks`/`retrieval_tasks` routes.
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 30–60 min.
- **Estimated token usage:** 6–12K.
- **Regression risk:** Low.
- **Regression areas:** export flow; OCR (tie to C-3 decision).
- **Required tests:** enqueue an export task; assert it completes.
- **Manual verification steps:** trigger a DOCX export via `/export`; confirm the job runs.
- **Automated verification steps:** `celery inspect active_queues` includes the routed queues.
- **Suggested implementation order:** with C-2.
- **Success criteria:** no routed queue lacks a consumer; no route points to a missing module.
- **Notes:** Simplest safe fix: collapse GPU queues into consumed queues unless a separate GPU worker is actually deployed.

---

## H-4 — `research/synthesis/{project_id}` returns hardcoded fake data

- **Issue ID:** H-4
- **Severity:** High
- **Category:** AI / API / Backend
- **Files involved:** `endpoints/research.py:437-468` (`synthesize_project`); models `research_findings`, `research_contradictions`.
- **Functions involved:** `synthesize_project`.
- **Execution path:** frontend `runSynthesis(projectId)` → `GET /research/synthesis/{id}` → returns a static dict with placeholder clusters/contradictions.
- **Root cause:** prototype stub never replaced with real analysis.
- **Current behavior:** returns literal "X causes Y" / "Paper A suggests…" regardless of data.
- **Expected behavior:** cluster `ResearchFinding`s, detect consensus/contradictions, return real results (persist to `research_contradictions`).
- **Why it happens:** stubbed for demo.
- **Business impact:** advertised contradiction detection is fabricated.
- **Technical impact:** misleading output; unused `research_contradictions` table.
- **Risk level:** Medium.
- **Dependencies:** needs real findings (C-2 populates them; C-1 populates their embeddings).
- **Can it be fixed independently?** The endpoint can be rewritten, but meaningful output depends on populated findings/embeddings.
- **Estimated implementation difficulty:** High.
- **Estimated implementation time:** 3–6 h.
- **Estimated token usage:** 20–35K.
- **Regression risk:** Low (isolated endpoint).
- **Regression areas:** Research synthesis UI.
- **Required tests:** with fixture findings, assert non-static clustering output.
- **Manual verification steps:** create a project with 2 contradictory findings; confirm the report reflects them.
- **Automated verification steps:** test asserting output is derived from inputs (not the static strings).
- **Suggested implementation order:** after C-1/C-2 (data must exist).
- **Success criteria:** synthesis reflects actual project findings.
- **Notes:** Could reuse embeddings + cosine clustering + an LLM contradiction pass (Finance/Legal show the extract-then-compute pattern).

---

## H-5 — `S3StorageProvider` reads undefined `settings.AWS_REGION`

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).** One-line fix: `core/storage.py` now reads `settings.S3_REGION`. No `AWS_REGION` alias added (would be a second name for the same contract — the guard test asserts the phantom attr stays gone). Regression tests: `backend/tests/test_storage_s3_init.py` (provider init with mocked boto3 uses `S3_REGION`; Settings has no `AWS_REGION`). 2 passed.

- **Issue ID:** H-5
- **Severity:** High (for S3 deployments) / latent otherwise
- **Category:** Infrastructure / Configuration / Storage
- **Files involved:** `core/storage.py:82` (`region_name=settings.AWS_REGION`); `core/config.py:40` (`S3_REGION`, no `AWS_REGION`); `endpoints/documents.py:36` (correctly uses `S3_REGION`).
- **Functions involved:** `S3StorageProvider.__init__`, `StorageFactory.get_provider`.
- **Execution path:** `STORAGE_PROVIDER=s3` → `StorageFactory.get_provider()` → `S3StorageProvider()` → `settings.AWS_REGION` → `AttributeError`.
- **Root cause:** setting name mismatch between modules.
- **Current behavior:** S3 storage crashes on init; local storage (default) unaffected.
- **Expected behavior:** use `settings.S3_REGION` consistently.
- **Why it happens:** copy/rename drift.
- **Business impact:** cloud/S3/Supabase-Storage deployments break at boot.
- **Technical impact:** worker/API crash when building `storage_service` under S3.
- **Risk level:** Low to fix (one-line rename).
- **Dependencies:** none.
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Trivial.
- **Estimated implementation time:** 5–10 min.
- **Estimated token usage:** 3–6K.
- **Regression risk:** Very low.
- **Regression areas:** S3 upload/download in the worker.
- **Required tests:** init `S3StorageProvider` with `STORAGE_PROVIDER=s3` + dummy creds; assert no `AttributeError`.
- **Manual verification steps:** set S3 env; boot worker; confirm no crash.
- **Automated verification steps:** unit test constructing the provider with mocked boto3.
- **Suggested implementation order:** early (trivial, unblocks S3).
- **Success criteria:** S3 provider initializes using `S3_REGION`.
- **Notes:** Optionally add `AWS_REGION` as an alias in config to be safe.

---

## H-6 — Free plan self-upgrade when `RAZORPAY_ENABLED=false` (default)

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** `/billing/upgrade` sandbox path now returns **403 `payments_disabled`** (with a WARNING log) when `settings.ENVIRONMENT == "production"` and Razorpay is off. Dev/test sandbox upgrades unchanged; `RAZORPAY_ENABLED=true` behavior (402 → create-order) unchanged.
> **Verification:** `backend/tests/test_billing_upgrade_gate.py` — production blocked (403), Razorpay-on still 402, dev sandbox still activates. 3 passed.
> **Residual note:** frontend `UpgradeModal` treats non-2xx as failure generically; the 403 message is surfaced via detail. Per-tier quota enforcement after upgrade remains a roadmap item (unchanged).

- **Issue ID:** H-6
- **Severity:** High
- **Category:** Security / Billing / API
- **Files involved:** `endpoints/billing.py:36` (`RAZORPAY_ENABLED` default false), `:190-218` (`upgrade_plan` else-branch calls `_activate_plan`), `:73-89` (`_activate_plan`); `core/trial_enforcement.py`.
- **Functions involved:** `upgrade_plan`, `_activate_plan`.
- **Execution path:** authenticated `POST /billing/upgrade {plan}` with flag off → `_activate_plan(user, plan, cycle)` sets any tier free.
- **Root cause:** insecure-by-default feature flag; "sandbox" mode is the default.
- **Current behavior:** any user can self-assign `enterprise` with no payment if deployed with defaults.
- **Expected behavior:** production must not free-upgrade; require real payment or an explicit non-production guard.
- **Why it happens:** dev convenience default shipped as the default.
- **Business impact:** revenue bypass / tier escalation.
- **Technical impact:** unauthorized entitlement changes.
- **Risk level:** High if deployed as-is.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes — gate the sandbox path behind `ENVIRONMENT != production`, or default `RAZORPAY_ENABLED` safely.
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 30–60 min.
- **Estimated token usage:** 6–10K.
- **Regression risk:** Low–Medium (may break dev upgrade convenience — keep it for non-prod).
- **Regression areas:** dev/test upgrade flows; frontend upgrade modal.
- **Required tests:** with `ENVIRONMENT=production` + flag off, `POST /billing/upgrade` returns 402/403, not 200.
- **Manual verification steps:** simulate prod env; attempt upgrade; confirm blocked.
- **Automated verification steps:** pytest for the prod-gate behavior.
- **Suggested implementation order:** Phase 2 (security hardening).
- **Success criteria:** no free tier escalation in production defaults.
- **Notes:** Keep sandbox upgrade available only in dev/test.

---

## H-7 — `llm_service` singleton raises at import when no Gemini keys (non-test)

> **STATUS: ✅ RESOLVED (2026-07-18, branch `repair/debug-master-plan`).**
> **Implementation note:** `LLMService.__init__` no longer constructs the provider; a lazy `provider` property builds it on first access via `_build_provider()` (logic unchanged otherwise). Injected providers are still honored. Bonus root-cause fix: the old code caught only `RuntimeError`, but `GeminiLLMProvider` raises `ValueError` when the rotator has no keys — so the intended friendly fail-loud message never actually fired; `_build_provider` now catches both. The "no silent DummyLLMProvider outside test" policy is preserved verbatim, just moved from import time to first use.
> **Verification:** `backend/tests/test_llm_service_lazy_init.py` (construction never builds; first access fails loud without keys in development; injected provider honored; provider cached). Full suite: 29 passed. No call site assigns to `.provider` (grep-verified), so the property is safe.

- **Issue ID:** H-7
- **Severity:** High
- **Category:** Backend / Configuration / AI
- **Files involved:** `services/llm_service.py:434` (`llm_service = LLMService()`), `:284-324` (constructor fail-loud branches); `core/gemini_env.py` (key bridge); `main.py:34-49` (startup key check).
- **Functions involved:** `LLMService.__init__`.
- **Execution path:** importing any module that imports `llm_service` (most endpoints, exams, workspace routers) → `LLMService()` runs at import → `RuntimeError` unless keys present or `ENVIRONMENT=test`.
- **Root cause:** eager module-level instantiation with fail-loud policy.
- **Current behavior:** the app cannot import the query stack without Gemini keys; complicates testing/CI and any keyless boot.
- **Expected behavior:** lazy provider initialization (construct on first use), or a clear startup-time failure that doesn't couple import to keys.
- **Why it happens:** singleton pattern + strict no-mock policy outside tests.
- **Business impact:** brittle boot; hard to run/test without keys.
- **Technical impact:** import-time coupling; test friction.
- **Risk level:** Medium.
- **Dependencies:** interacts with C-1 (adding `get_embedding` to the same class), C-4/C-5.
- **Can it be fixed independently?** Yes — make the provider lazy (a `@property`/factory) so import never triggers provider construction.
- **Estimated implementation difficulty:** Medium.
- **Estimated implementation time:** 1–2 h.
- **Estimated token usage:** 12–20K.
- **Regression risk:** Medium (touches a central singleton used everywhere).
- **Regression areas:** every LLM call site; the fail-loud guarantee (keep the loud failure at first use, not import).
- **Required tests:** import `endpoints.query` with no keys and `ENVIRONMENT=development`; assert import succeeds; first LLM call raises clearly.
- **Manual verification steps:** boot API without keys; confirm it starts and returns a clear error only on a query.
- **Automated verification steps:** pytest importing modules keyless.
- **Suggested implementation order:** Phase 2, coordinate with C-1.
- **Success criteria:** import is key-independent; first-use failure remains explicit.
- **Notes:** Preserve the "no silent DummyLLMProvider in prod" intent — fail loud at call time.

---

## M-1 — Simulated SSE progress endpoints (fake heartbeats)

- **Issue ID:** M-1
- **Severity:** Medium
- **Category:** Streaming / API / Frontend
- **Files involved:** `endpoints/hr.py:218` (`sse_processing_updates`), `legal.py:137`, `finance.py:385`, `study.py:69`, `research.py:338`.
- **Functions involved:** each `event_generator` emitting `progress: i*10` with `asyncio.sleep(2)`.
- **Execution path:** frontend opens `/{ws}/events/…` SSE → receives fake progress unrelated to the real Celery task.
- **Root cause:** placeholder never wired to real task state (comments say "would subscribe to Redis Pub/Sub").
- **Current behavior:** UI shows fabricated progress.
- **Expected behavior:** real progress via Redis Pub/Sub or task-state polling (`AsyncResult`).
- **Why it happens:** demo stub.
- **Business impact:** misleading UX; users can't tell real completion.
- **Technical impact:** dead feedback loop.
- **Risk level:** Low.
- **Dependencies:** meaningful only once C-2/H-3 make the tasks actually run.
- **Can it be fixed independently?** Yes, but pointless until tasks run.
- **Estimated implementation difficulty:** Medium.
- **Estimated implementation time:** 2–4 h (all five).
- **Estimated token usage:** 15–25K.
- **Regression risk:** Low.
- **Regression areas:** workspace processing UIs.
- **Required tests:** publish a task-progress event; assert SSE forwards it.
- **Manual verification steps:** process a doc; confirm progress tracks actual stages.
- **Automated verification steps:** integration test with a Redis pub/sub stub.
- **Suggested implementation order:** after C-2.
- **Success criteria:** SSE reflects real task state.
- **Notes:** Could reuse Celery result backend or a Redis channel keyed by document/job id.

---

## M-2 — Retrieval cache not purged on document delete (key-pattern mismatch)

- **Issue ID:** M-2
- **Severity:** Medium
- **Category:** Backend / Performance / Security (data retention)
- **Files involved:** `endpoints/documents.py:597-607` (purge `retrieval:uid_{uid}:*`); `endpoints/query.py:355-372` (writes `retrieval:{workspace}:{hash}`).
- **Functions involved:** `delete_document`, `_get_cached_retrieval`/`_set_cached_retrieval`.
- **Execution path:** delete → purge pattern `retrieval:uid_{uid}:*` matches nothing (cache keys are `retrieval:{workspace}:…`) → stale cache persists ≤300s.
- **Root cause:** two different cache-key conventions.
- **Current behavior:** deleted content can appear in answers for up to the TTL.
- **Expected behavior:** delete purges the actual keys (scoped by tenant+workspace).
- **Why it happens:** key formats drifted.
- **Business impact:** deleted data momentarily served (privacy/retention).
- **Technical impact:** cache staleness.
- **Risk level:** Low–Medium.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes — unify the key format and purge pattern (include owner/tenant).
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 30–60 min.
- **Estimated token usage:** 6–10K.
- **Regression risk:** Low.
- **Regression areas:** retrieval cache hit rate.
- **Required tests:** set a cache key via a query; delete the doc; assert the key is gone.
- **Manual verification steps:** query (populate cache) → delete doc → re-query → confirm no stale hit.
- **Automated verification steps:** Redis-backed test asserting purge.
- **Suggested implementation order:** Phase 3.
- **Success criteria:** deletion invalidates all related cache entries.
- **Notes:** Consider embedding `owner_id` in the cache key for tenant-scoped purges.

---

## M-3 — JWT algorithm confusion in `TenantContextMiddleware`

- **Issue ID:** M-3
- **Severity:** Medium
- **Category:** Security / Authentication
- **Files involved:** `core/middleware.py:96-99` (`algorithms=["HS256","RS256"]`); contrast `core/auth.py:26` (HS256 only).
- **Functions involved:** `TenantContextMiddleware.dispatch`.
- **Execution path:** every request → middleware decodes the JWT with HS256+RS256 to derive `collection_name`.
- **Root cause:** accepts RS256 alongside a symmetric secret — the exact pattern hardened out of `auth.py` (BUG-013).
- **Current behavior:** latent algorithm-confusion smell (used only for `collection_name`, not authz).
- **Expected behavior:** decode with HS256 only, consistently.
- **Why it happens:** middleware not updated when `auth.py` was hardened.
- **Business impact:** low direct, but a foot-gun if this decode is ever trusted for authz.
- **Technical impact:** inconsistent JWT handling.
- **Risk level:** Low.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes — remove `RS256`.
- **Estimated implementation difficulty:** Trivial.
- **Estimated implementation time:** 5–15 min.
- **Estimated token usage:** 3–6K.
- **Regression risk:** Very low.
- **Regression areas:** tenant collection derivation.
- **Required tests:** a forged RS256 token is rejected by the middleware decode.
- **Manual verification steps:** confirm normal HS256 sessions still derive the right collection.
- **Automated verification steps:** unit test on the decode.
- **Suggested implementation order:** Phase 2.
- **Success criteria:** all JWT decodes use HS256 only.
- **Notes:** Align with `auth.py`'s `settings.JWT_ALGORITHM`.

---

## M-4 — Embedding service silently degrades to zero vectors

- **Issue ID:** M-4
- **Severity:** Medium
- **Category:** AI / Backend
- **Files involved:** `services/embedding_service.py` (`GeminiEmbeddingProvider.embed_documents` pads 768→1024 and returns zero vectors on failure; `DummyEmbeddingProvider`; `LocalEmbeddingProvider` fallback chain).
- **Functions involved:** `embed_documents`, `EmbeddingService.generate_embeddings`.
- **Execution path:** bge-m3 load fails → Gemini fallback (768→zero-pad→1024) → on Gemini failure → per-text zero vector.
- **Root cause:** fallbacks prioritize uptime over correctness; failures are swallowed.
- **Current behavior:** retrieval may run over zero/padded vectors, producing meaningless similarity while appearing "grounded."
- **Expected behavior:** fail loud or emit metrics/alerts when the primary model is unavailable; never silently index zero vectors.
- **Why it happens:** defensive fallbacks.
- **Business impact:** silently wrong answers.
- **Technical impact:** corrupted embedding space; RRF/rerank meaningless.
- **Risk level:** Medium.
- **Dependencies:** relates to H-1 (pgvector requires consistent, real vectors).
- **Can it be fixed independently?** Yes — add logging/metrics + a health signal; consider refusing to index zero vectors.
- **Estimated implementation difficulty:** Low–Medium.
- **Estimated implementation time:** 1–2 h.
- **Estimated token usage:** 10–18K.
- **Regression risk:** Low.
- **Regression areas:** ingestion (may now surface errors previously hidden).
- **Required tests:** simulate provider failure; assert an alert/metric and non-silent behavior.
- **Manual verification steps:** disable bge-m3; confirm a visible warning/health degradation.
- **Automated verification steps:** unit test on the fallback path.
- **Suggested implementation order:** with H-1.
- **Success criteria:** silent zero-vector indexing is eliminated or clearly observable.
- **Notes:** Mixing bge-m3 (1024 real) and padded-Gemini (768→1024) vectors in one corpus harms similarity; standardize on one.

---

## M-5 — CI uses Node 18 while the app targets Next.js 16 / React 19

- **Issue ID:** M-5
- **Severity:** Medium
- **Category:** Deployment / Testing / Infrastructure
- **Files involved:** `.github/workflows/ci.yml` (`node-version: "18"`); `frontend/package.json` (`next@16.2.6`, `react@19.2.4`).
- **Functions involved:** CI `frontend-validation` job.
- **Execution path:** CI installs deps + `npm run build` on Node 18.
- **Root cause:** stale Node version pin.
- **Current behavior:** Next 16 targets Node ≥20; the build may warn/fail or diverge from local.
- **Expected behavior:** CI Node ≥20 (LTS) matching Next 16 support.
- **Why it happens:** version drift.
- **Business impact:** CI may not reflect real build; false confidence.
- **Technical impact:** build/runtime mismatch.
- **Risk level:** Low.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Trivial.
- **Estimated implementation time:** 5–15 min.
- **Estimated token usage:** 3–6K.
- **Regression risk:** Low.
- **Regression areas:** CI only.
- **Required tests:** CI build passes on Node 20.
- **Manual verification steps:** run `npm run build` on Node 20 locally.
- **Automated verification steps:** CI matrix on 20.x.
- **Suggested implementation order:** Phase 3.
- **Success criteria:** CI builds on a supported Node.
- **Notes:** Also confirm the backend Dockerfile/Node base images if the frontend is containerized.

---

## M-6 — Only two backend tests; `pip-audit` is non-blocking

- **Issue ID:** M-6
- **Severity:** Medium
- **Category:** Testing / Deployment
- **Files involved:** `backend/tests/test_api_contracts.py` (2 tests); `.github/workflows/ci.yml` (`pip-audit -r requirements.txt || echo …`).
- **Functions involved:** `test_health_check`, `test_docs_schema_generation`.
- **Execution path:** CI runs `pytest tests/ -v` (2 tests) and a non-failing `pip-audit`.
- **Root cause:** minimal test scaffolding; audit intentionally soft.
- **Current behavior:** almost no regression protection; vulnerabilities never fail the build.
- **Expected behavior:** meaningful coverage (auth, retrieval, each workspace, billing, worker registration) and a blocking (or triaged) audit.
- **Why it happens:** early-stage project.
- **Business impact:** bugs like C-1..C-5 ship unnoticed.
- **Technical impact:** low safety net.
- **Risk level:** Low (but enables everything else).
- **Dependencies:** benefits from C-1..C-5 fixes (tests would cover them).
- **Can it be fixed independently?** Yes — add tests incrementally.
- **Estimated implementation difficulty:** Medium (breadth).
- **Estimated implementation time:** ongoing; initial pass 1–2 days.
- **Estimated token usage:** 30–60K for a first meaningful suite.
- **Regression risk:** none (adds tests).
- **Regression areas:** none.
- **Required tests:** this task *is* the tests.
- **Manual verification steps:** `pytest` green; coverage report.
- **Automated verification steps:** CI coverage gate.
- **Suggested implementation order:** Phase 3, incremental alongside fixes.
- **Success criteria:** core paths covered; `pip-audit` triaged.
- **Notes:** Add a worker-registration test (would catch C-2) and a `get_embedding`-exists test (would catch C-1).

---

## M-7 — Config vs `.env.example` default mismatches + stale trial-limit comments

- **Issue ID:** M-7
- **Severity:** Medium
- **Category:** Configuration
- **Files involved:** `core/config.py:121-122` (`OTEL_ENABLED=True`, `PROMETHEUS_ENABLED=True`) vs `.env.example:100-101` (`false`); `core/trial_enforcement.py:8` (`TRIAL_QUERY_LIMIT=10`) vs `endpoints/query.py` nudge logic/comments referencing a "5th query" and nudges at uses 3/4.
- **Functions involved:** telemetry setup; `check_and_increment_trial`; trial nudge emails in `/query/stream`.
- **Execution path:** effective observability depends on which source wins; trial nudge/upgrade-modal logic keys off counts that assume a smaller limit than 10.
- **Root cause:** defaults and comments drifted across files.
- **Current behavior:** ambiguous observability defaults; trial UX comments/logic inconsistent with the 10-query limit.
- **Expected behavior:** one source of truth; consistent trial thresholds.
- **Why it happens:** iterative edits.
- **Business impact:** confusing trial UX; observability may be unexpectedly on/off.
- **Technical impact:** config ambiguity.
- **Risk level:** Low.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 30–60 min.
- **Estimated token usage:** 6–12K.
- **Regression risk:** Low.
- **Regression areas:** telemetry toggles; trial nudges/upgrade modal.
- **Required tests:** assert trial nudge thresholds derive from `TRIAL_QUERY_LIMIT`.
- **Manual verification steps:** run a trial to exhaustion; confirm nudges/modal timing.
- **Automated verification steps:** unit test on nudge thresholds.
- **Suggested implementation order:** Phase 3.
- **Success criteria:** consistent defaults; trial logic references the constant.
- **Notes:** Decide the intended default for OTEL/Prometheus and set both places.

---

## M-8 — Prompt-injection surface in grounded generation

- **Issue ID:** M-8
- **Severity:** Medium
- **Category:** Security / AI
- **Files involved:** `services/llm_service.py:326-370` (`_build_system_prompt`); domain prompts in `endpoints/legal.py`, `finance.py`, `exams.py`, `research.py`, `study.py` (inject document text verbatim).
- **Functions involved:** all system-prompt builders that embed retrieved evidence/document text.
- **Execution path:** malicious document text is placed into the system prompt inside `<evidence>` blocks; a crafted document can attempt "ignore previous instructions."
- **Root cause:** evidence is trusted content with no instruction isolation beyond tags.
- **Current behavior:** injection is possible; no sanitization/guarding.
- **Expected behavior:** delimit/escape evidence, add anti-injection guardrails, and treat evidence strictly as data.
- **Why it happens:** standard RAG prompt construction without hardening.
- **Business impact:** answer manipulation; potential data exfiltration prompts.
- **Technical impact:** integrity of grounded answers.
- **Risk level:** Medium.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Medium.
- **Estimated implementation time:** 2–4 h.
- **Estimated token usage:** 15–25K.
- **Regression risk:** Low–Medium (prompt changes can shift answer quality).
- **Regression areas:** all grounded answers.
- **Required tests:** adversarial doc with injected instructions; assert the model still refuses/ignores.
- **Manual verification steps:** upload a doc containing an override instruction; confirm it's ignored.
- **Automated verification steps:** prompt-injection test fixtures.
- **Suggested implementation order:** Phase 2.
- **Success criteria:** injected instructions in documents do not alter system behavior.
- **Notes:** Consider a separate "system rules" channel and explicit "evidence is untrusted data" framing.

---

## M-9 — `time.sleep()` inside the key-rotator lock

- **Issue ID:** M-9
- **Severity:** Medium
- **Category:** Performance / AI / Backend
- **Files involved:** `services/llm_key_rotation.py:77-109` (`get_key`), `:85-91` (sleep while holding `self._lock`).
- **Functions involved:** `GeminiKeyRotator.get_key`.
- **Execution path:** when all keys are cooling → thread computes wait, `time.sleep(wait)` **inside** the lock → blocks all other `get_key` callers; blocking in async contexts.
- **Root cause:** sleep in the critical section.
- **Current behavior:** thundering-herd stall under full cooldown; event-loop blocking if called from async.
- **Expected behavior:** release the lock before sleeping (or use a condition variable / async sleep).
- **Why it happens:** simplest implementation.
- **Business impact:** latency spikes / stalls under rate-limit pressure.
- **Technical impact:** contention; potential event-loop block.
- **Risk level:** Low–Medium.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Medium.
- **Estimated implementation time:** 1–2 h.
- **Estimated token usage:** 8–15K.
- **Regression risk:** Medium (concurrency-sensitive).
- **Regression areas:** all Gemini calls under rate limiting.
- **Required tests:** concurrency test: multiple threads request keys during cooldown without serial stalls.
- **Manual verification steps:** force all keys to cooldown; confirm no global stall.
- **Automated verification steps:** threaded unit test measuring contention.
- **Suggested implementation order:** Phase 2/3.
- **Success criteria:** no sleep under lock; callers not serialized during cooldown.
- **Notes:** Since callers are often async, prefer offloading or an async-aware wait.

---

## M-10 — Reranker silently returns fabricated scores (`DummyLocalReranker`)

- **Issue ID:** M-10 (split from FINAL_AUDIT M-4)
- **Severity:** Medium
- **Category:** AI
- **Files involved:** `services/reranker_service.py` (`DummyLocalReranker` returns alternating 0.85/0.99; `_get_default_reranker` falls back to it on any error).
- **Functions involved:** `RerankerService.rerank_results`, `LocalCrossEncoder.rerank`, `DummyLocalReranker.rerank`.
- **Execution path:** cross-encoder import/config fails → `DummyLocalReranker` → grounding uses fake rerank scores → answer looks "confidence-scored" but isn't.
- **Root cause:** silent fallback to fabricated data.
- **Current behavior:** degraded ranking masquerades as real.
- **Expected behavior:** log/alert on fallback; consider failing loud or clearly marking degraded mode.
- **Why it happens:** dependency-optional design.
- **Business impact:** wrong ordering + misleading grounding confidence (which feeds the UI trust number).
- **Technical impact:** meaningless rerank + confidence.
- **Risk level:** Medium.
- **Dependencies:** relates to C-4 (grounding confidence shown as trust).
- **Can it be fixed independently?** Yes.
- **Estimated implementation difficulty:** Low.
- **Estimated implementation time:** 30–60 min.
- **Estimated token usage:** 6–12K.
- **Regression risk:** Low.
- **Regression areas:** grounding ordering; confidence semantics.
- **Required tests:** simulate reranker failure; assert a warning/metric and no silent fabricated scores.
- **Manual verification steps:** disable sentence-transformers; confirm a visible degraded signal.
- **Automated verification steps:** unit test on fallback.
- **Suggested implementation order:** with M-4/C-4.
- **Success criteria:** dummy reranker never silently used in production.
- **Notes:** Pair with M-4 as the "silent AI degradation" theme.

---

## M-11 — Proactive insights read `doc.workspace_type` which does not exist on the model

- **Issue ID:** M-11 (newly discovered during verification)
- **Severity:** Medium
- **Category:** AI / Worker / Backend
- **Files involved:** `workers/tasks/document_tasks.py:121` (`workspace_type = getattr(doc, "workspace_type", None) or "general"`); `models/document.py` (has `workspace_id`, not `workspace_type`); `services/proactive_insights.py`.
- **Functions involved:** `process_document` (insights dispatch), `generate_proactive_insights_task`, `proactive_insights_service.generate_insights`.
- **Execution path:** after ingest → `getattr(doc, "workspace_type", None)` → always `None` → defaults to `"general"` → insights always use the general prompt regardless of the document's actual workspace.
- **Root cause:** wrong attribute name; `Document` has no `workspace_type`.
- **Current behavior:** domain-specific proactive insights (legal risk, finance anomalies, HR standouts) never trigger; everything is "general."
- **Expected behavior:** derive the workspace from the document's `workspace_id`/session or pass the workspace explicitly so domain insight prompts run.
- **Why it happens:** attribute misnomer.
- **Business impact:** the advertised domain-tuned "proactive insights on upload" degrade to generic.
- **Technical impact:** insight quality; unused domain prompts.
- **Risk level:** Low–Medium.
- **Dependencies:** none.
- **Can it be fixed independently?** Yes — map `workspace_id` → slug (reverse of `resolve_workspace_id`) or thread the workspace through the upload/verify flow.
- **Estimated implementation difficulty:** Medium (reverse-mapping a `uuid5` slug is non-trivial; may need to store the slug on the document/session).
- **Estimated implementation time:** 1–3 h.
- **Estimated token usage:** 12–20K.
- **Regression risk:** Low.
- **Regression areas:** proactive insights content.
- **Required tests:** ingest a legal-workspace doc; assert legal insight prompt used.
- **Manual verification steps:** upload in Legal; confirm risk-oriented insights.
- **Automated verification steps:** unit test asserting the resolved workspace passed to `generate_insights`.
- **Suggested implementation order:** Phase 3.
- **Success criteria:** insights reflect the document's real workspace.
- **Notes:** Because `workspace_id` is a `uuid5(slug)`, you cannot reverse it; store the workspace slug on the `Document`/`ChatSession` at upload, or pass it from the endpoint.

---

## L-1 — Stale internal docs (`docs/architecture/project-map.md`, `docs/marketing/`)

- **Issue ID:** L-1 · **Severity:** Low · **Category:** Documentation
- **Files involved:** `docs/architecture/project-map.md`, `docs/marketing/*`.
- **Root cause / current behavior:** they describe an already-fixed doubled-`/api/v1` prefix bug and a workspace-UUID crash (`resolve_workspace_id` now handles it); marketing overstates OCR/Veritas/pgvector.
- **Expected behavior:** docs match delivered behavior.
- **Business/Technical impact:** misleads future engineers/repair models.
- **Risk / Regression:** none (docs only).
- **Dependencies:** best done after the code fixes so docs describe the fixed state. **Can be fixed independently:** yes.
- **Difficulty/Time/Tokens:** Low / 1–2 h / 8–15K.
- **Required/Manual/Automated verification:** re-read against code; grep for `${API_BASE}/api/v1` (should only be historical).
- **Suggested order:** Phase 4 (last). **Success criteria:** docs reflect reality. **Notes:** the audit set (REPORT/ARCHITECTURE/etc.) supersedes these.

---

## L-2 — Committed runtime/build artifacts

- **Issue ID:** L-2 · **Severity:** Low · **Category:** Infrastructure / Configuration
- **Files involved:** `backend/celerybeat-schedule.{bak,dat,dir}`, `frontend/build.log`, `frontend/tmp/next-build/*`, empty `PROJECT_KNOWLEDGE_BASE.md` (now populated), untracked `docs/marketing/`.
- **Root cause / current behavior:** runtime/build outputs tracked in git.
- **Expected behavior:** ignored via `.gitignore`.
- **Impact:** repo noise, merge churn, potential stale-state confusion.
- **Risk/Regression:** none. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Trivial / 15 min / 2–5K.
- **Verification:** `git status` clean of artifacts.
- **Suggested order:** Phase 4. **Success criteria:** artifacts untracked/ignored. **Notes:** don't delete user data; just stop tracking.

---

## L-3 — Exam table extraction reads local disk path (breaks on S3)

- **Issue ID:** L-3 · **Severity:** Low · **Category:** API / Storage
- **Files involved:** `endpoints/exams.py:651-653` (`os.path.exists(doc.storage_path)`), `services/table_extractor.py`, `services/pdf_extractor.is_native_pdf`.
- **Root cause / current behavior:** assumes a local filesystem path; S3 `storage_path` is a key, so extraction 404s under S3.
- **Expected behavior:** download via `storage_service` before extraction (as `document_tasks` does).
- **Impact:** table extraction unavailable on S3 deployments.
- **Risk/Regression:** Low. **Dependencies:** H-5 (S3 init). **Independent:** yes.
- **Difficulty/Time/Tokens:** Low / 30–60 min / 6–10K.
- **Verification:** extract tables from an S3-stored doc.
- **Suggested order:** Phase 3/4. **Success criteria:** works for both local and S3. **Notes:** mirror the temp-download pattern in `document_tasks.process_document`.

---

## L-4 — `exams/generate/diagram` returns a hardcoded Mermaid template

- **Issue ID:** L-4 · **Severity:** Low · **Category:** AI / API
- **Files involved:** `endpoints/exams.py:869-880`.
- **Root cause / current behavior:** returns a static `graph TD` template regardless of topic.
- **Expected behavior:** generate a real diagram (LLM → Mermaid/Graphviz) or remove the endpoint.
- **Impact:** feature is a stub. **Risk/Regression:** none. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Medium / 1–3 h / 10–18K.
- **Verification:** diagram varies by topic. **Suggested order:** Phase 4. **Success criteria:** topic-specific diagram. **Notes:** low priority.

---

## L-5 — Workspace-UUID casing divergence

- **Issue ID:** L-5 · **Severity:** Low · **Category:** Backend / Database
- **Files involved:** `core/workspace.py:32-52` (`resolve_workspace_id` lowercases slug); `endpoints/documents.py` inline `uuid.uuid5(NAMESPACE_DNS, effective_workspace)` (no lowercasing) at list/get/head/delete handlers.
- **Root cause / current behavior:** two derivations of the workspace UUID; mixed-case slugs would diverge.
- **Expected behavior:** all workspace-UUID derivations go through `resolve_workspace_id`.
- **Impact:** latent (slugs are lowercase today). **Risk/Regression:** Low. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Low / 30–45 min / 6–10K.
- **Verification:** documents remain visible after refactor. **Suggested order:** Phase 4. **Success criteria:** single derivation path. **Notes:** replace inline `uuid5` calls with `resolve_workspace_id`.

---

## L-6 — Duplicate answer paths (`/query/stream`, `/query/ask`, `/chats` ask)

- **Issue ID:** L-6 (was L-7) · **Severity:** Low · **Category:** API / Backend
- **Files involved:** `endpoints/query.py` (`/stream`, `/ask`, `/search`, `/debug`), `endpoints/chats.py:~451-470` (ask path persisting messages).
- **Root cause / current behavior:** three grounding/LLM invocation paths risk behavioral drift and double retrieval.
- **Expected behavior:** consolidate behind one grounding/answer service.
- **Impact:** maintenance risk. **Risk/Regression:** Medium (refactor). **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Medium / 2–4 h / 15–25K.
- **Verification:** all paths produce consistent grounded answers. **Suggested order:** Phase 4. **Success criteria:** single source of truth for answering. **Notes:** decide which path persists messages.

---

## L-7 — Unused `ws` WebSocket router

- **Issue ID:** L-7 (was L-8) · **Severity:** Low · **Category:** API / Streaming
- **Files involved:** `endpoints/ws.py`, mounted in `api.py:22`.
- **Root cause / current behavior:** product uses SSE; the websocket surface appears unused by the frontend.
- **Expected behavior:** remove, or document/support it. **Impact:** dead surface / attack surface.
- **Risk/Regression:** Low. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Low / 30 min / 5–8K.
- **Verification:** confirm no frontend caller. **Suggested order:** Phase 4. **Success criteria:** decision made + implemented. **Notes:** verify no future plan depends on it before removal.

---

## L-8 — Two embedding models in use (bge-m3 vs all-MiniLM-L6-v2)

- **Issue ID:** L-8 (was L-9) · **Severity:** Low · **Category:** AI / Performance
- **Files involved:** `services/embedding_service.py` (bge-m3, 1024); `endpoints/hr.py:341-356,412-426` (`all-MiniLM-L6-v2`, 384).
- **Root cause / current behavior:** HR JD scoring uses a second, smaller model → extra memory + inconsistent vector spaces.
- **Expected behavior:** standardize on one embedding model (or clearly isolate HR scoring).
- **Impact:** memory + inconsistency. **Risk/Regression:** Low–Medium. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Low–Medium / 1–2 h / 8–15K.
- **Verification:** HR scores stable after switch. **Suggested order:** Phase 4. **Success criteria:** one embedding model or documented rationale. **Notes:** MiniLM (384) can't be compared to bge-m3 (1024) vectors.

---

## L-9 — No pagination on many list endpoints

- **Issue ID:** L-9 (split from FINAL_AUDIT L-6) · **Severity:** Low · **Category:** API / Performance
- **Files involved:** most workspace `list_*` endpoints (e.g., `hr.py`, `legal.py`, `finance.py`, `research.py`, `study.py`) return unbounded `scalars().all()`.
- **Root cause / current behavior:** no `limit`/`offset` on many lists (chats/messages do paginate).
- **Expected behavior:** paginate list endpoints.
- **Impact:** latency/memory at scale. **Risk/Regression:** Low. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Low–Medium / 2–3 h / 12–20K.
- **Verification:** large datasets paginate. **Suggested order:** Phase 4. **Success criteria:** bounded responses. **Notes:** add sensible defaults + max caps.

---

## L-10 — `exams/process/voice` is a no-op stub

- **Issue ID:** L-10 (split from FINAL_AUDIT L-4) · **Severity:** Low · **Category:** API / AI
- **Files involved:** `endpoints/exams.py:882-889`.
- **Root cause / current behavior:** returns a static "queued" message; no voice pipeline.
- **Expected behavior:** implement voice→exam via a real transcription pipeline, or remove.
- **Impact:** stub feature. **Risk/Regression:** none. **Dependencies:** `audio_tasks` (present). **Independent:** yes.
- **Difficulty/Time/Tokens:** Medium / 2–4 h / 12–20K.
- **Verification:** voice input produces content. **Suggested order:** Phase 4. **Success criteria:** real behavior or removal. **Notes:** low priority.

---

## L-11 — No server-side timeout on LLM calls

- **Issue ID:** L-11 (split from FINAL_AUDIT L-6) · **Severity:** Low · **Category:** Performance / Backend
- **Files involved:** `services/llm_service.py` (`generate`, `generate_stream` via `run_in_executor`), `endpoints/query.py`.
- **Root cause / current behavior:** long Gemini calls have no hard server-side cap (client uses `AbortSignal`).
- **Expected behavior:** enforce a server timeout to free worker threads.
- **Impact:** thread tie-up under slow upstream. **Risk/Regression:** Low–Medium. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Low–Medium / 1–2 h / 8–15K.
- **Verification:** slow-LLM simulation times out gracefully. **Suggested order:** Phase 4. **Success criteria:** bounded server-side LLM latency. **Notes:** coordinate with M-9 (rotation) and streaming semantics.

---

## L-12 — Verbose error strings leak internals

- **Issue ID:** L-12 (split from FINAL_AUDIT L-6) · **Severity:** Low · **Category:** Security / API
- **Files involved:** `endpoints/health.py` (`f"error: {str(e)}"`), SSE `error` events in `query.py`, various endpoints returning raw exception text.
- **Root cause / current behavior:** raw exceptions can expose DSNs/host/config.
- **Expected behavior:** generic client errors + detailed server-side logs.
- **Impact:** info disclosure. **Risk/Regression:** Low. **Dependencies:** none. **Independent:** yes.
- **Difficulty/Time/Tokens:** Low / 1–2 h / 8–15K.
- **Verification:** error responses are generic. **Suggested order:** Phase 4. **Success criteria:** no internal detail in client errors. **Notes:** keep correlation IDs for support.

---

## L-13 — HR candidate `search` uses `ILIKE`, not semantic search

- **Issue ID:** L-13 (newly itemized) · **Severity:** Low · **Category:** AI / API
- **Files involved:** `endpoints/hr.py:119-133` (`ILIKE` on name/skills; the pgvector version is commented out).
- **Root cause / current behavior:** "semantic candidate search" is keyword matching.
- **Expected behavior:** real embedding ranking (blocked historically by the missing `get_embedding` — C-1).
- **Impact:** weaker search than advertised. **Risk/Regression:** Low. **Dependencies:** C-1. **Independent:** after C-1.
- **Difficulty/Time/Tokens:** Low–Medium / 1–2 h / 8–15K.
- **Verification:** semantic queries rank plausibly. **Suggested order:** Phase 4 (after C-1). **Success criteria:** embedding-based candidate ranking. **Notes:** candidate embeddings must be populated.

---

## N-1 — `deep_research_agent` has no caller (newly discovered)

- **Issue ID:** N-1 (discovered 2026-07-18 during C-5)
- **Severity:** Medium (feature-gap; the service itself now works after C-5/C-6)
- **Category:** API / AI / Frontend
- **Files involved:** `services/deep_research_agent.py` (singleton, zero imports elsewhere); `endpoints/research.py` (no deep-research route); frontend (no consumer).
- **Current behavior:** the 4-step deep-research pipeline (and with it the only pre-C-4 Veritas invocation) is unreachable — the audit docs described a "Research Deep Research path" that was never exposed as an endpoint.
- **Expected behavior:** either expose an SSE endpoint (e.g. `POST /research/deep-research`) that streams `ResearchEvent`s and wire a frontend consumer, or explicitly mark the module as an unshipped feature.
- **Dependencies:** C-5, C-6 (done). Requires an API-contract decision (new endpoint + `lib/api.ts` + UI), so it is **not** a silent bug fix; scheduled with Phase 3/4.
- **Required tests:** endpoint contract test streaming events, once exposed.

---

# PART 2 — ROADMAP (phased, dependency-ordered)

## Phase 1 — Critical (unbreak core paths)
Ordered by dependency:
1. **C-1** — add `get_embedding` (unblocks 4 search endpoints + 4 worker tasks + L-13).
2. **C-2** — register legal/finance/study/research (+decide email) tasks on the worker.
3. **H-3** — give routed queues consumers; remove phantom `embedding_tasks`/`retrieval_tasks` routes *(High, but co-located with worker wiring; do it with C-2)*.
4. **C-5** — fix Deep Research step 1 retrieval call.
5. **C-4** — wire Veritas into `/query/stream` (emit `trust_report`).
6. **C-3** — wire real OCR (PaddleOCR/Docling) into ingestion *(heaviest; can trail within Phase 1 or start Phase 2)*.

## Phase 2 — High
Ordered by dependency:
1. **H-5** — fix `AWS_REGION`→`S3_REGION` (trivial, unblocks S3 + L-3).
2. **H-2** — add Celery Beat service.
3. **H-1** — default to pgvector + add ANN index *(after M-4 so vectors are real)*.
4. **H-7** — make `llm_service` provider lazy (import-safe).
5. **H-6** — block free self-upgrade in production.
6. **H-4** — replace fake research synthesis with real analysis *(after C-1/C-2 populate findings)*.

## Phase 3 — Medium
1. **M-4** + **M-10** — stop silent embedding/reranker degradation (observability).
2. **M-3** — HS256-only in tenant middleware.
3. **M-8** — prompt-injection hardening.
4. **M-9** — remove sleep-under-lock in key rotator.
5. **M-2** — fix delete cache-purge key.
6. **M-1** — real SSE progress (after C-2).
7. **M-11** — fix proactive-insights workspace resolution.
8. **M-5** — CI Node ≥20.
9. **M-7** — reconcile config/env defaults + trial thresholds.
10. **M-6** — build a real test suite (start early, run throughout).

## Phase 4 — Low
L-1 (docs) · L-2 (artifacts) · L-3 (exam S3 path) · L-4 (diagram stub) · L-5 (uuid casing) · L-6 (dup answer paths) · L-7 (ws router) · L-8 (dual embeddings) · L-9 (pagination) · L-10 (voice stub) · L-11 (LLM timeout) · L-12 (verbose errors) · L-13 (HR semantic search, after C-1).

---

# PART 3 — SAFE IMPLEMENTATION ORDER

| Issue | Depends on | Blocks | Safe to parallelize? |
|-------|-----------|--------|----------------------|
| **C-1** get_embedding | — | C-2 success, H-4, L-13, workspace searches | ✅ (isolated addition) |
| **C-2** worker include | C-1 | M-1 (real progress), H-4, domain embeddings | ⚠️ do after C-1; config-only |
| **H-3** queue consumers | — (co-locate w/ C-2) | export/OCR async | ⚠️ with C-2 |
| **C-3** OCR wiring | H-3 (OCR consumer), C-2 patterns | scanned-doc retrieval | ❌ heavy; isolate |
| **C-4** Veritas on stream | C-1 (meaningful evidence) | trust UX | ✅ mostly isolated (query.py) |
| **C-5** deep research step 1 | C-1 (optional) | research quality, Veritas inputs | ✅ isolated (deep_research_agent.py) |
| **H-1** pgvector default | M-4 (real vectors), migration | scalable retrieval | ⚠️ needs index migration |
| **H-2** Beat service | — | scheduled automation | ✅ infra-only |
| **H-4** real synthesis | C-1, C-2 (findings) | research synthesis UX | ❌ after data exists |
| **H-5** S3 region | — | S3 deploys, L-3 | ✅ trivial |
| **H-6** billing gate | — | revenue safety | ✅ isolated (billing.py) |
| **H-7** lazy llm_service | coordinate w/ C-1 | keyless boot/tests | ⚠️ central singleton |
| **M-1** real SSE progress | C-2 | progress UX | ⚠️ after tasks run |
| **M-2** cache purge | — | delete correctness | ✅ isolated |
| **M-3** JWT HS256 | — | consistency | ✅ trivial |
| **M-4** embedding degrade | — | H-1 correctness | ✅ isolated |
| **M-10** reranker degrade | — | C-4 confidence meaning | ✅ isolated |
| **M-5** CI Node | — | CI fidelity | ✅ infra-only |
| **M-6** tests | benefits from C-1..C-5 | regression safety | ✅ additive |
| **M-7** config defaults | — | config clarity | ✅ isolated |
| **M-8** injection hardening | — | answer integrity | ✅ prompt-only |
| **M-9** lock sleep | — | rotation latency | ⚠️ concurrency-sensitive |
| **M-11** insights workspace | (schema: store slug) | insight quality | ⚠️ may need a column |
| **L-1..L-13** | as noted per item | polish | ✅ mostly parallel |

**Parallelization guidance:** C-4, C-5, H-5, H-6, M-2, M-3, M-4, M-10, M-5, M-7, M-8 are largely isolated and can be worked concurrently. C-1→C-2→H-3 form a strict chain (do in order). C-3 and H-1 are the two "heavy" changes and should be isolated (separate branches, careful testing).

---

*End of Debug Master Plan. This is documentation only — no code was modified. Pair with [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) so the repair model has both the "what/why to fix" (this file) and the "how it all connects" (that file).*
