# DocuMindAI — Consolidated Critical Audit Findings

The single, severity-ranked issue list for the later debugging phase. Every finding includes **Location**, **Reason**, **Impact**, **Root cause**, and **Evidence**. This is a read-only audit — **nothing was fixed**. Severities reflect impact on a production deployment of the default configuration.

Cross-references: [ARCHITECTURE.md](ARCHITECTURE.md) · [WORKSPACES.md](WORKSPACES.md) · [API_AUDIT.md](API_AUDIT.md) · [INTEGRATIONS.md](INTEGRATIONS.md) · [SECURITY_AUDIT.md](SECURITY_AUDIT.md) · [QUALITY_AUDIT.md](QUALITY_AUDIT.md).

---

## CRITICAL

### C-1 — Four `*/search` endpoints call a nonexistent method (`llm_service.get_embedding`) — **RESOLVED (2026-07-18)**

> `get_embedding` added to `LLMService`, delegating to `embedding_service` via `run_in_executor`. Regression tests in `backend/tests/test_get_embedding.py`. See DEBUG_MASTER_PLAN C-1 implementation note.
- **Location:** `endpoints/legal.py:168` (`/legal/clauses/search`), `endpoints/finance.py:416` (`/finance/transactions/search`), `endpoints/study.py:97` (`/study/search`), `endpoints/research.py:366` (`/research/search`). Also called with a `try/except` fallback in `study/tutor/chat` (:132) and `research/copilot/chat` (:400).
- **Reason:** `LLMService`/`GeminiLLMProvider` (`services/llm_service.py`) implement `generate`, `generate_stream`, `generate_answer`, `generate_json` — **no `get_embedding`**.
- **Impact:** those four endpoints raise `AttributeError` → HTTP 500 on every call; the frontend `searchClauses/searchTransactions/searchStudyMaterial/searchResearch` are dead. Tutor/copilot degrade to recency ordering.
- **Root cause:** embedding generation lives in `embedding_service`, not `llm_service`; the search endpoints were written against a method that was never added.
- **Evidence:** method absent in `llm_service.py`; `frontend/src/lib/api.ts` `searchClauses` etc. call these routes.

### C-2 — Celery worker cannot execute legal/finance/study/research tasks (missing from `include`) — **RESOLVED (2026-07-18)**

> Four task modules added to `include`; `email_tasks` intentionally left out (dead code). Regression test: `backend/tests/test_worker_registration.py`.
- **Location:** `workers/celery_app.py` `include=[...]` omits `legal_tasks`, `finance_tasks`, `study_tasks`, `research_tasks` (only `document_tasks`, `export_tasks`, `audio_tasks`, `ocr_tasks`, `hr_tasks`, automation are listed). `docker-compose.yml` worker runs `-Q main-queue,celery`.
- **Reason:** the `/legal|finance|study|research/process` endpoints call `process_*_batch.delay(...)`, but the worker never imports/registers those modules, so it has no handler for the task.
- **Impact:** async document processing for four workspaces never completes; documents stay "queued." Populating `legal_clauses`/`finance_transactions`/`study_flashcards`/`research_findings` embeddings depends on these tasks → also blocks the (already broken) `*/search`.
- **Root cause:** task registration (`include`) not kept in sync with `task_routes` and the endpoints that dispatch them.
- **Evidence:** `celery_app.py:9-23` vs `task_routes` :28-42; `endpoints/{legal,finance,study,research}.py` `*_batch.delay`.

### C-3 — Marketed multi-engine OCR is not on the ingestion path (and its queue is unconsumed) — **RESOLVED (2026-07-18)**

> Scanned pages now route through the orchestrator inline in `extract_document_stream` (Paddle primary, Docling fallback, loud degraded path, `OCR_SCANNED_ENABLED` toggle); orchestrator upgraded to the installed PaddleOCR 3.x API. Queue consumption fixed under H-3. Regression tests: `backend/tests/test_ocr_ingestion.py`.
- **Location:** ingestion uses `services/ocr_service.OCRService.extract_document_stream` (`workers/tasks/document_tasks.py:55`). The `OCROrchestrator` (PaddleOCR + Docling + validation gateway) is used only by `workers/tasks/ocr_tasks.py`, routed to `ocr_gpu_queue` (`celery_app.py:38`), which the compose worker does not consume.
- **Reason:** real extraction is PyMuPDF text only; scanned/handwritten pages fall back to `page.get_text("text")` (`ocr_service.py:150-154`, a "Tesseract would be injected here" stub).
- **Impact:** handwritten/rotated/scanned documents yield little or no text → empty retrieval → refusals or wrong answers. Contradicts the headline "Multi-Engine OCR" feature.
- **Root cause:** the orchestrator was built but never wired into `process_document`; its queue has no consumer.
- **Evidence:** `document_tasks.py` imports `OCRService`, not `ocr_orchestrator`; `ocr_orchestrator` referenced only by `ocr_tasks.py`.

### C-4 — Veritas "trust score on every response" is not implemented on the main path — **RESOLVED (2026-07-18)**

> `/query/stream` now emits a real `trust_report` SSE event (grounded answers, both retrieval and summary paths), adapted at the caller to the frontend `TrustReport` interface. Regression tests: `backend/tests/test_trust_report_event.py`. Veritas heuristics themselves unchanged (future work).
- **Location:** `services/veritas_engine.py` is invoked only in `services/deep_research_agent.py:82`. `/query/stream` emits `confidence_score` from grounding (`endpoints/query.py:407`), and hardcodes `0.95` on the summary path (:321).
- **Reason:** README/marketing claim every answer is scored 0–100 by an "AI evaluation layer." In reality Veritas is a **heuristic with hardcoded constants** and is never called for normal queries.
- **Impact:** the product's flagship trust guarantee is not delivered on the path all seven workspaces use; the UI shows grounding rerank average, not a trust score.
- **Root cause:** Veritas wiring stopped at the Research agent; factor names in the README don't match the code.
- **Evidence:** grep shows `veritas_engine`/`compute_trust_score` referenced only in `deep_research_agent.py`.

### C-5 — Deep Research Agent step 1 is broken (nonexistent retrieval API) — **RESOLVED (2026-07-18)**

> Step 1 rewritten to call `RetrievalService.retrieve_chunks(db=…, query=…, document_ids=…)`, build grounded evidence blocks, and synthesize `doc_answer` via `llm_service.generate_answer`; the failure path now logs at ERROR instead of silently degrading. Regression tests: `backend/tests/test_deep_research_agent.py`. **Discovery during verification:** `deep_research_agent` has **no caller** anywhere (backend or frontend) — recorded as new issue N-1 in DEBUG_MASTER_PLAN.

### C-6 — `llm_service.generate()` called 10× but never defined on `LLMService` (newly discovered 2026-07-18) — **RESOLVED (2026-07-18)**
- **Location:** `endpoints/legal.py:305,382`, `finance.py:498,609`, `research.py:215,285`, `reports.py:339`, `app/tasks/report_tasks.py:240`, `deep_research_agent.py:147,212` vs `services/llm_service.py` (`LLMService` had no `generate` — only the provider did).
- **Reason:** this audit's C-1 finding wrongly listed `generate` among `LLMService` methods (conflated service with provider). The read-only audit never executed these paths, so "risk-report/ratios work ✅" claims were **wrong** — every `llm_service.generate` call raised `AttributeError` → 500.
- **Resolution:** service-level async `generate` delegating to the provider. Regression test: `backend/tests/test_llm_service_generate.py`.
- **Location:** `services/deep_research_agent.py:80-81`: `from app.services.retrieval_service import retrieval_service` and `retrieval_service.query(query, document_ids)`.
- **Reason:** `retrieval_service.py` defines a `RetrievalService` class with a static `retrieve_chunks` — **no module-level `retrieval_service` singleton and no `.query` method**.
- **Impact:** step 1 always raises (ImportError/AttributeError), is swallowed by the `except`, and the agent proceeds with `doc_answer=""` — the "hybrid RAG + web" agent runs web-only/empty, and Veritas scores empty chunks.
- **Root cause:** written against an API shape that doesn't exist in the current retrieval service.
- **Evidence:** `retrieval_service.py` has no `query`/singleton; the call sits inside a `try/except`.

---

## HIGH

### H-1 — Default vector backend is an in-memory NumPy scan, not pgvector or FAISS
- **Location:** `config.py:64` (`VECTOR_BACKEND="faiss"`), `.env.example:104`; `retrieval_service.py:67-141` (else branch loads all chunk embeddings and computes NumPy cosine).
- **Reason:** the "faiss" path never uses FAISS (`import faiss` is guarded and unused; `faiss` isn't in `requirements.txt`); pgvector cosine runs only when `VECTOR_BACKEND=pgvector`.
- **Impact:** O(N) memory/compute per query; no ANN index; won't scale; contradicts "pgvector semantic search" marketing.
- **Root cause:** default config + a fallback labeled "FAISS" that is really brute force.
- **Evidence:** `retrieval_service.py` NumPy block; no `faiss` in requirements.

### H-2 — No Celery Beat service → scheduled automation never runs — **RESOLVED (2026-07-18)**

> Dedicated single `beat` service added to docker-compose (schedule file in /tmp). Guard test asserts exactly one Beat command.
- **Location:** `celery_app.py beat_schedule` (health check, key rotation, daily digest, db cleanup, subscription/GST/model checks) vs `docker-compose.yml` (only a `worker`, no `beat`).
- **Reason:** Beat is the scheduler; without a `celery beat` process, `beat_schedule` entries never fire.
- **Impact:** health alerts, digests, cleanup, subscription expiry checks all silently never happen in the default deployment.
- **Root cause:** missing Beat container/process in orchestration.
- **Evidence:** `docker-compose.yml` services list; no `beat` command anywhere.

### H-3 — `export_tasks`/`ocr_tasks` (and embedding/retrieval queues) have no consumer — **RESOLVED (2026-07-18)**

> Phantom `embedding_tasks`/`retrieval_tasks` routes removed; worker `-Q` expanded to consume `export_queue` and `ocr_gpu_queue` in compose/scripts/docs. Regression tests in `backend/tests/test_worker_registration.py`.
- **Location:** `task_routes` sends `export_tasks.*`→`export_queue`, `ocr_tasks.*`→`ocr_gpu_queue`, etc.; worker consumes only `main-queue,celery`.
- **Reason:** routed queues aren't in the worker's `-Q` list.
- **Impact:** async exports and OCR-queue tasks enqueue but never process.
- **Root cause:** queue routing not matched to deployed consumers.
- **Evidence:** `celery_app.py:28-42` vs `docker-compose.yml` worker command.

### H-4 — `research/synthesis` returns hardcoded fake data
- **Location:** `endpoints/research.py:437-468`.
- **Reason:** the endpoint returns literal placeholder clusters/contradictions ("X causes Y", "Paper A suggests…") instead of analyzing findings.
- **Impact:** the advertised "contradiction detection / literature synthesis" is fabricated output.
- **Root cause:** stubbed prototype never replaced with real clustering/contradiction logic.
- **Evidence:** the function body constructs a static dict.

### H-5 — S3 storage provider crashes on init (`AWS_REGION` undefined) — **RESOLVED (2026-07-18)**

> `storage.py` now uses `settings.S3_REGION`. Regression tests: `backend/tests/test_storage_s3_init.py`.
- **Location:** `core/storage.py:82` uses `settings.AWS_REGION`; `config.py` defines `S3_REGION`, not `AWS_REGION`.
- **Reason:** attribute mismatch (`documents.py` correctly uses `S3_REGION`).
- **Impact:** selecting `STORAGE_PROVIDER=s3` → `AttributeError` when the worker builds `storage_service` → S3 deployments break.
- **Root cause:** inconsistent setting name between modules.
- **Evidence:** `storage.py` `S3StorageProvider.__init__` vs `config.py`.

### H-6 — Free plan self-upgrade in the default configuration — **RESOLVED (2026-07-18)**

> Sandbox upgrade gated to non-production (403 `payments_disabled` in production with payments off). Tests: `backend/tests/test_billing_upgrade_gate.py`.
- **Location:** `endpoints/billing.py:190-218`; default `RAZORPAY_ENABLED=false`.
- **Reason:** with the flag off, `/billing/upgrade` activates any tier directly (no payment).
- **Impact:** revenue bypass / tier escalation if shipped with the default.
- **Root cause:** insecure-by-default feature flag.
- **Evidence:** `_activate_plan` called in the `else` branch.

### H-7 — LLM service raises at import when no Gemini keys (non-test) — **RESOLVED (2026-07-18)**

> Provider construction is now lazy (first `.provider` access); fail-loud preserved at first use. Also fixed: keyless failure raised `ValueError`, which the intended `except RuntimeError` never caught. Tests: `backend/tests/test_llm_service_lazy_init.py`.
- **Location:** `services/llm_service.py:434` (`llm_service = LLMService()`), `:290-322`.
- **Reason:** the constructor raises `RuntimeError` unless keys exist or `ENVIRONMENT=test`.
- **Impact:** importing any module that imports `llm_service` (most endpoints) fails at boot without keys → hard startup dependency; also complicates testing.
- **Root cause:** eager module-level singleton with fail-loud behavior.
- **Evidence:** the `raise RuntimeError(...)` branches at import.

---

## MEDIUM

### M-1 — Simulated SSE progress endpoints
- **Location:** `hr.py:218`, `legal.py:137`, `finance.py:385`, `study.py:69`, `research.py:338`.
- **Reason:** `/events/*` emit `progress: i*10` heartbeats via `asyncio.sleep(2)`; comments admit "would subscribe to Redis Pub/Sub."
- **Impact:** UI shows fake progress unrelated to actual task state.
- **Evidence:** identical stub generators in each file.

### M-2 — Retrieval cache not purged on document delete
- **Location:** `documents.py:601` purges `retrieval:uid_{uid}:*`; cache written as `retrieval:{workspace}:{hash}` (`query.py:360-372`).
- **Reason:** key-pattern mismatch.
- **Impact:** deleted-document content can be served from cache for up to 300s.
- **Evidence:** the two differing key formats.

### M-3 — Algorithm-confusion smell in tenant middleware
- **Location:** `core/middleware.py:96-99` decodes JWT with `["HS256","RS256"]`, unlike `auth.py` (HS256 only).
- **Impact:** latent; inconsistent with the hardened verifier.
- **Evidence:** the `algorithms` list.

### M-4 — Embedding/reranker silent degradation to fabricated/zero data — **RESOLVED (2026-07-18, as M-4+M-10)**

> Zero-vector fallback removed (raises, ERROR-logged); dummy reranker/embedding providers refuse in production and log ERROR elsewhere. Tests: `backend/tests/test_silent_degradation.py`.
- **Location:** `embedding_service.py` (Gemini 768→zero-pad→zero vectors), `reranker_service.py` (`DummyLocalReranker` alternating 0.85/0.99).
- **Reason:** fallbacks swallow failures and return meaningless-but-plausible values.
- **Impact:** a "grounded" answer over zero vectors / fake rerank scores looks fine but is not actually grounded; no alert.
- **Evidence:** the fallback branches.

### M-5 — CI Node 18 vs Next.js 16
- **Location:** `.github/workflows/ci.yml` (`node-version: "18"`) with `next@16.2.6`/React 19.
- **Impact:** Next 16 targets Node ≥20; the build step may warn/fail or diverge from local.
- **Evidence:** CI file + `package.json`.

### M-6 — Only two backend tests; `pip-audit` non-blocking
- **Location:** `tests/test_api_contracts.py`; `ci.yml` `pip-audit ... || echo`.
- **Impact:** almost no regression protection; vuln scan never fails the build.
- **Evidence:** the test file and CI step.

### M-7 — Config vs `.env.example` default mismatches
- **Location:** `config.py` (`OTEL_ENABLED=True`, `PROMETHEUS_ENABLED=True`) vs `.env.example` (`false`); `TRIAL_QUERY_LIMIT=10` vs `query.py` "5th query" comments/nudges.
- **Impact:** ambiguous effective behavior; stale logic/comments.
- **Evidence:** the differing values.

### M-8 — Prompt-injection surface in grounded generation
- **Location:** all `_build_system_prompt`/domain prompts inject document text verbatim.
- **Impact:** malicious documents can attempt instruction override; no evidence isolation beyond `<evidence>` tags.
- **Evidence:** prompt construction in `llm_service.py`, `legal.py`, `finance.py`, `exams.py`.

### M-9 — `time.sleep()` inside the key-rotator lock
- **Location:** `llm_key_rotation.py:85-91`.
- **Impact:** when all keys cool down, one thread sleeps holding the lock, blocking others; also blocking in async contexts.
- **Evidence:** `get_key()` body.

---

## LOW

- **L-1 — Stale docs.** `docs/architecture/project-map.md` and `docs/marketing/interview-guide.md` describe an already-fixed doubled-`/api/v1` prefix bug and a workspace-UUID crash (`resolve_workspace_id` now handles it). Current code is correct; docs mislead. *Evidence:* repo-wide search finds `${API_BASE}/api/v1` only in docs + one stale comment.
- **L-2 — Committed runtime/build artifacts.** `backend/celerybeat-schedule.*`, `frontend/build.log`, `frontend/tmp/next-build/*` are in git. Empty `PROJECT_KNOWLEDGE_BASE.md`; untracked `docs/marketing/`.
- **L-3 — Exam table extraction reads local disk path.** `exams.py:652` `os.path.exists(doc.storage_path)` works for local storage, breaks for S3 keys.
- **L-4 — `exams/generate/diagram` / `exams/process/voice` are stubs.** Hardcoded Mermaid template / no-op.
- **L-5 — Workspace-UUID casing divergence.** `resolve_workspace_id` lowercases the slug; `documents.py` inline `uuid5` does not — latent mismatch on mixed-case slugs.
- **L-6 — Unbounded list endpoints / no server-side LLM timeouts / verbose error strings** (see [SECURITY_AUDIT.md](SECURITY_AUDIT.md) L-S1, [QUALITY_AUDIT.md](QUALITY_AUDIT.md) §5).
- **L-7 — Duplicate answer paths** (`/query/stream`, `/query/ask`, `/chats` ask) risk behavioral drift.
- **L-8 — `ws` websocket router** appears unused by the frontend (product uses SSE).
- **L-9 — Two embedding models** (bge-m3 vs all-MiniLM-L6-v2 in HR) → extra memory, inconsistent vector spaces.

---

## Severity Summary

| Severity | Count | Themes |
|---|:--:|---|
| **Critical** | 5 | Broken search endpoints, unregistered workers, OCR not wired, Veritas not wired, deep-research broken |
| **High** | 7 | Vector default, no Beat, unconsumed queues, fake synthesis, S3 init bug, free upgrade, import-time hard fail |
| **Medium** | 9 | Fake SSE, cache purge, JWT middleware, silent degradation, CI/Node, tests, config drift, prompt injection, lock sleep |
| **Low** | 9 | Stale docs, committed artifacts, stubs, casing, timeouts, dup paths, unused ws, dual embeddings |

## Recommended Debugging-Phase Order

1. **Unbreak the obvious 500s and dead paths:** C-1 (`get_embedding`), C-5 (deep-research retrieval), H-4 (synthesis), H-5 (S3 region).
2. **Fix worker wiring:** C-2/H-3 (`include` + queues), H-2 (Beat container).
3. **Align features with claims:** C-3 (OCR path), C-4 (Veritas on `/query/stream`), H-1 (pgvector default).
4. **Harden:** H-6 (payments default), M-2/M-3/M-8/M-9 (cache, JWT, injection, lock).
5. **Raise the floor:** M-6 (tests), M-5/M-7 (CI/config), L-1/L-2 (docs/artifacts).

*End of consolidated findings. This document, together with the eight companion files, constitutes the official technical documentation and the knowledge base for the subsequent debugging phase. No code was modified.*
