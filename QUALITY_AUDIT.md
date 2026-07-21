# DocuMindAI — Code Quality & Technical Debt Audit

Companion to [FINAL_AUDIT.md](FINAL_AUDIT.md). Covers dead code, duplication, architecture smells, testing, concurrency/performance, and maintainability. Read-only; nothing changed.

---

## 1. Testing

**State:** the entire backend test suite is `backend/tests/test_api_contracts.py` with **two tests**: `test_health_check` (mocks DB + Redis) and `test_docs_schema_generation` (OpenAPI generates). CI labels this step "Execute API Contracts & Regression Tests," which overstates coverage.

- **No tests** for authentication, RAG retrieval/grounding/rerank, any workspace endpoint, billing/trial, workers, migrations-in-anger, or the frontend (only `npm run lint` + `npm run build`).
- `load_tests/locustfile.py` exists (performance harness) but is not run in CI.
- **Risk:** the many broken endpoints (`*/search`, deep-research step 1, synthesis stub, worker routing) would all have been caught by minimal endpoint tests.

**Recommendation:** contract tests per router; a retrieval golden-set; a worker registration test that asserts every routed task is importable by the worker.

---

## 2. Dead / Unused / Mislabeled Code

| Item | Location | Issue |
|---|---|---|
| **OCR orchestrator** | `services/ocr_orchestrator.py`, `workers/tasks/ocr_tasks.py` | PaddleOCR + Docling engines are only reachable via `ocr_tasks` on `ocr_gpu_queue`, which the running worker never consumes. Effectively dead on the ingestion path. |
| **`extraction_router.route_extraction`** | `services/extraction_router.py` | pymupdf4llm-first router that the ingestion worker intentionally bypasses. Orphaned. |
| **FAISS import** | `services/retrieval_service.py` | `import faiss` guarded and never used; `faiss` not in requirements. The "faiss" backend is NumPy. |
| **`get_embedding` callers** | legal/finance/study/research endpoints | Call a method that doesn't exist → dead-on-arrival endpoints. |
| **`retrieval_service.query` / singleton** | `deep_research_agent.py` | Referenced but nonexistent → step 1 always excepts. |
| **Simulated SSE** | hr/legal/finance/study/research `/events/*` | Heartbeat stubs, never wired to real task status. |
| **Stub endpoints** | `exams/generate/diagram`, `exams/process/voice`, `research/synthesis` | Hardcoded/placeholder responses. |
| **`DummyLLMProvider` / `DummyLocalReranker` / `DummyEmbeddingProvider`** | services | Test/fallback doubles that can silently serve fabricated data in prod-like conditions. |
| **`ws` websocket router** | `endpoints/ws.py` | Product uses SSE; websocket surface appears unused by the frontend. |
| **`app/tasks/` vs `app/workers/tasks/`** | two task packages | `eval_tasks`, `report_tasks` live in `app/tasks/`; everything else in `app/workers/tasks/`. Confusing split. |
| **Committed Celery beat schedule files** | `backend/celerybeat-schedule.*` | Runtime artifacts committed to git. |
| **Empty knowledge base** | `PROJECT_KNOWLEDGE_BASE.md` (0 bytes), untracked `docs/marketing/` | Placeholder/aspirational docs. |
| **Frontend build artifacts** | `frontend/build.log`, `frontend/tmp/next-build/*` | Build output committed. |

---

## 3. Duplication & Inconsistency

- **Three answer paths:** `/query/stream`, `/query/ask`, `/chats` ask — each invokes grounding/LLM independently.
- **Two embedding models:** `bge-m3` (1024) for docs vs `all-MiniLM-L6-v2` (384) for HR JD scoring; different vector spaces.
- **Two vector-namespace derivations:** `resolve_workspace_id` lowercases the slug; `documents.py` inline `uuid5` does not — a latent divergence if a slug ever has mixed case.
- **Config vs env defaults diverge:** `OTEL_ENABLED`/`PROMETHEUS_ENABLED` default `True` in `config.py` but `false` in `.env.example`.
- **Trial-limit drift:** `TRIAL_QUERY_LIMIT = 10`, but `query.py` comments/logic reference a "5th query" and nudge emails at uses 3 and 4 — stale relative to the limit.
- **Repeated inline workspace-UUID logic** across `documents.py` handlers instead of calling `resolve_workspace_id`.
- **`S3_REGION` vs `AWS_REGION`** inconsistency between `documents.py` and `storage.py`.

---

## 4. Architecture Smells

- **"Never modify" governance:** `docs/architecture/project-map.md` and CLAUDE.md mark `retrieval_service.py`, `grounding_service.py`, `chunking_service.py`, `celery_app.py`, `hr_tasks.py` as un-modifiable "STABLE" files. This freezes bugs in place (e.g., the retrieval NumPy default) and is an unusual constraint for a living codebase.
- **Import-time side effects:** `llm_service = LLMService()` raises at import without keys; `embedding_service`, `reranker_service`, `storage_service`, `veritas_engine`, `deep_research_agent`, `ocr_orchestrator` are all module-level singletons that load models/clients eagerly → slow imports, hard-to-test, coupling.
- **Silent degradation everywhere:** embeddings → zero vectors; reranker → fabricated scores; retrieval cache/email/insights → swallowed exceptions. Robust for uptime, but hides correctness failures (a "grounded" answer over zero-vector retrieval looks fine but is meaningless).
- **Worker/queue mismatch:** `task_routes` sends tasks to queues the deployed worker doesn't consume, and `include` omits half the workspace task modules — an architecture-level wiring defect.
- **Mega-component frontend:** all seven workspaces route through one `WorkspaceUI.tsx`; risk of a large, branchy component.

---

## 5. Concurrency & Performance

| Issue | Location | Impact |
|---|---|---|
| **`time.sleep()` inside a lock** | `llm_key_rotation.get_key()` | When all keys cool down, the thread sleeps holding `self._lock`, blocking all other key requests. In async contexts this is also a blocking sleep. |
| **In-memory vector scan** | `retrieval_service` (faiss default) | Loads all matching chunk embeddings into NumPy per query — O(N) memory + compute, no index. |
| **Synchronous stream iteration** | `llm_service.generate_stream` | The initial call is offloaded, but `for chunk in stream_response` iterates a blocking network generator inside the async function. |
| **Eager model loads** | reranker/embedding singletons | First request pays large model-download/load latency; per-process memory pressure with `worker_max_tasks_per_child=50` recycling. |
| **First-12k/10k/6k-char truncation** | finance/legal | Long documents are truncated for extraction/analysis. |
| **Unbounded list endpoints** | most `list_*` | No pagination on many workspace list endpoints. |

**Positives:** batched embeddings (50) in the ingestion worker; Redis retrieval cache; async DB I/O; `run_in_executor` for blocking model/LLM calls; correlation IDs.

---

## 6. Migrations & Schema

- **55 Alembic migrations** with several explicit merge heads (`merge_heads`, `merge_remaining_heads`, `merge_orphaned_migration_head`, `merge_heads_after_phase19`) → branchy, phase-driven history.
- Notable evolution: `add_vector_column` → `resize_chunk_embedding_to_1024`; RLS enablement; per-workspace vector columns; repair migrations (`repair_create_bookmarks`). CI runs `alembic upgrade head` against pgvector, so the head is at least self-consistent.
- **Risk:** merge-head sprawl makes downgrade/rollback fragile; a squash before the next release would help.

---

## 7. Documentation Debt

- `README.md` and `docs/marketing/*` overstate delivered features (Veritas per response, multi-engine OCR, pgvector default, contradiction detection).
- `docs/architecture/project-map.md` is **stale**: it describes a doubled-API-prefix bug and a workspace-UUID crash that current code has resolved (`resolve_workspace_id`, cleaned frontend).
- `PROJECT_KNOWLEDGE_BASE.md` is empty; `docs/marketing/` is untracked.

---

## 8. Maintainability Scorecard

| Dimension | Score (0–10) | Notes |
|---|:--:|---|
| Readability | 7 | Clear names, heavy "why" comments |
| Consistency | 5 | Divergent defaults, duplicated logic, two task packages |
| Test safety net | 2 | Two smoke tests |
| Modularity | 6 | Good service/provider abstractions; import-time coupling |
| Dead-code hygiene | 4 | Multiple dead/stub subsystems shipped as "features" |
| Docs accuracy | 5 | Extensive but overstated/stale |
| Migration hygiene | 5 | Works but branchy |

---

## 9. Top Quality Recommendations (documentation only)

1. Add a worker-registration test and per-router contract tests; wire `locust` smoke into CI.
2. Remove/relabel dead subsystems (OCR orchestrator, FAISS import, `ws`) or actually wire them; make silent fallbacks emit warnings/metrics.
3. Retire the "never modify" freeze so the retrieval default and other latent bugs can be fixed.
4. Reconcile config vs `.env.example` defaults; fix `S3_REGION`/`AWS_REGION`, trial-limit comments, and workspace-UUID casing.
5. Squash the migration history before release; stop committing `celerybeat-schedule.*` and build artifacts.
6. Update `README`/`project-map` to match delivered behavior.
