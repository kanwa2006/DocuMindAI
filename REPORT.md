# DocuMindAI — Technical Report & System Documentation

> **Status:** Read-only technical audit. No code was modified in producing this document.
> **Scope:** Complete repository (`backend/`, `frontend/`, `infrastructure/`, `docs/`, migrations, CI, configs).
> **Method:** Direct source inspection of the FastAPI backend, Next.js frontend, Celery workers, Alembic migrations, Docker/CI configuration, and environment templates.
> **Audience:** A senior engineer who has never seen this codebase should be able to understand the entire system from this document set without reading the source.

This is the **executive overview**. The full documentation set is split across nine files so no single file becomes unwieldy:

| File | Contents |
|------|----------|
| **REPORT.md** (this file) | Executive overview, product, tech stack, subsystem summary, production-readiness scorecard, consolidated critical findings |
| **ARCHITECTURE.md** | System architecture, execution flows, every subsystem, pipelines, streaming, workers, deployment |
| **WORKSPACES.md** | Deep documentation of all 7 workspaces (General, HR, Legal, Finance, Study, Research, Exam) |
| **API_AUDIT.md** | Complete endpoint inventory + frontend↔backend contract audit |
| **INTEGRATIONS.md** | Every external service, API key, and connector with wiring status |
| **SECURITY_AUDIT.md** | Security findings and controls |
| **QUALITY_AUDIT.md** | Code quality, dead code, technical debt |
| **INTERVIEW_GUIDE.md** | FAANG-style interview preparation grounded in this project |
| **FINAL_AUDIT.md** | Consolidated, severity-ranked findings with evidence |

---

## 1. What DocuMindAI Is

**DocuMindAI** is a full-stack **AI document-intelligence platform**. A user uploads documents (PDF, DOCX, PPTX, or pasted text "clips"), the system extracts and indexes them, and the user then asks natural-language questions that are answered by a **Retrieval-Augmented Generation (RAG)** pipeline built on Google Gemini. The product's central promise is **grounded, cited answers** — every claim is supposed to trace back to a specific document and page, and the system is designed to refuse to answer when the evidence is absent.

The application is organized into **seven purpose-built "workspaces"** — General, HR, Legal, Finance, Study, Research, and Exam/Teacher — each with its own database tables, API namespace, Celery tasks, and domain-tuned retrieval configuration.

### 1.1 The Problem It Solves

Knowledge workers (lawyers, analysts, researchers, recruiters, teachers, students) spend large amounts of time locating answers inside documents. General-purpose chatbots hallucinate — they blend document content with training-data knowledge and produce confident, wrong answers. DocuMindAI's thesis is that hallucination should be eliminated **architecturally** (by only ever feeding the LLM retrieved evidence within a strict token budget and instructing it to refuse when evidence is missing) rather than merely discouraged at the prompt level.

### 1.2 Target Users

| Workspace | Primary user | Core job-to-be-done |
|-----------|--------------|---------------------|
| General | Anyone with documents | Upload anything, ask anything, get cited answers |
| HR | Recruiters / HR managers | Resume parsing, candidate ranking, job-fit scoring, pipeline tracking |
| Legal | Lawyers / legal ops | Clause extraction, contract risk reports, compliance, contract compare |
| Finance | Analysts / auditors | Financial line-item extraction, 15 ratios, anomaly/audit findings |
| Study | Students / educators | Flashcards (SM-2 spaced repetition), quizzes, AI tutor |
| Research | Academics | Literature synthesis, citation formatting, gap analysis, deep research (web-augmented) |
| Exam/Teacher | Teachers / trainers | Grounded exam-paper generation with answer keys, DOCX export, table extraction |

### 1.3 Business / Monetization Model

A trial-to-paid SaaS model. New users start on a **`trial` plan** capped at **10 queries** (`TRIAL_QUERY_LIMIT = 10`). Paid tiers (`go`, `plus`, `pro`, plus aliases `professional`/`business`/`enterprise`) are priced in INR and sold through **Razorpay** (India-first). Payment is feature-flagged: `RAZORPAY_ENABLED=true` routes users through a real Razorpay order + HMAC-verified webhook; when disabled (the default) `/billing/upgrade` flips the plan directly in "sandbox mode."

---

## 2. Technology Stack

### Backend
| Technology | Role |
|------------|------|
| **FastAPI** (≥0.109) | Async REST + Server-Sent-Events server |
| **SQLAlchemy 2.0** (async, `asyncpg`) | ORM; `psycopg2` used for sync (Celery/health) |
| **Alembic** | 55 migration files |
| **Celery** (≥5.3.6) + Redis | Distributed background tasks + Beat scheduler (see caveats) |
| **PyMuPDF** (`fitz`) + `pymupdf4llm` | Primary document text extraction (the real ingestion engine) |
| **PaddleOCR + Docling** | Multi-engine OCR **orchestrator** (present but off the main ingestion path — see §5) |
| **sentence-transformers** (`BAAI/bge-m3`, 1024-dim) | Local embedding model |
| **google-generativeai** (Gemini) | LLM generation + fallback embeddings (`text-embedding-004`) |
| **cross-encoder/ms-marco-MiniLM-L-6-v2** | Reranker |
| **SlowAPI** | Rate limiting |
| **python-docx / python-pptx / fpdf2** | Export & PPTX extraction |
| **Razorpay** | Payments |
| **Tavily** | Web search for the Research "Deep Research Agent" |
| **OpenTelemetry / Prometheus / Sentry** | Observability |

### Frontend
| Technology | Role |
|------------|------|
| **Next.js 16.2.6** (App Router) | SSR + file-based routing |
| **React 19.2.4** | UI |
| **TypeScript 5** | Types |
| **Tailwind CSS 4** | Styling |
| **react-pdf** | In-browser PDF viewing |
| **recharts** | Analytics charts |
| **@fingerprintjs/fingerprintjs** | Device fingerprint (abuse prevention) |
| **posthog-js / @sentry/nextjs** | Analytics + error tracking |

### Data & Infra
| Technology | Role |
|------------|------|
| **PostgreSQL 16 + pgvector** (`ankane/pgvector`) | Primary DB + vector column |
| **PgBouncer** (transaction mode) | Connection pooling |
| **Redis 7** | Celery broker/result backend + retrieval cache + device-trial keys |
| **Docker Compose** | 5-service local stack (db, pgbouncer, redis, backend, worker, frontend) |
| **Railway** | Cloud deploy target (`railway.json`) |
| **GitHub Actions** | CI (dep audit, migrations, pytest, lint, Next build) |

---

## 3. High-Level Architecture

```
 Next.js 16 App Router (frontend/src/app/*)
   /general /hr /legal /finance /study /research /exam  → all render <WorkspaceUI workspaceType=…/>
        │  REST + Server-Sent Events (fetch → apiFetch → NEXT_PUBLIC_API_URL=/api/v1)
        ▼
 FastAPI  (backend/app/main.py → app/api/v1/api.py)
   Middleware: CORS → CorrelationId → SecurityHeaders → CSRF → TenantContext → DeviceFingerprint → OTel
   Routers: auth, documents, query, hr, legal, finance, study, research, exams,
            export, billing, bookmarks, notifications, users, feedback, insights,
            chats, corrections, retention, reports, benchmark, admin, health, ws, csrf
        │                                   │
        ▼                                   ▼
 RAG pipeline (services/*)          Celery worker (workers/tasks/*)
   retrieval → grounding →            document_tasks (ingest: PyMuPDF→chunk→embed),
   rerank → LLM (Gemini) →            proactive_insights, hr/legal/finance/study/research
   [Veritas: research only]          tasks, export_tasks, ocr_tasks, automation (Beat)
        │                                   │
        ▼                                   ▼
 PostgreSQL 16 + pgvector  ·  PgBouncer  ·  Redis 7  ·  local/S3 storage
        │
        ▼
 Observability: OpenTelemetry · Prometheus /metrics · Sentry · PostHog
```

**Full detail in [ARCHITECTURE.md](ARCHITECTURE.md).**

### The Query Pipeline (the product's core loop)

1. **`POST /api/v1/query/stream`** (SSE, rate-limited 30/min) receives the question + `workspace_type` + `session_id`.
2. **Trial quota** is checked/incremented (`check_and_increment_trial`, HTTP 402 when exhausted).
3. If the chat has attached documents and the query is a summary intent → a **map-reduce full-document summary** path runs.
4. Otherwise: **hybrid retrieval** (`RetrievalService.retrieve_chunks`) runs semantic + lexical searches, fused via **Reciprocal Rank Fusion (RRF)**.
5. **Reranking** (`GroundingService` → cross-encoder), token-budgeting (default 6000 tokens), and **document-order sorting** produce a citation-ready evidence block.
6. **Gemini** streams tokens back through an async generator with **multi-key rotation** and a **safe text extractor** (never crashes on empty/blocked responses).
7. Tokens stream to the browser as SSE `token` events; a `metadata` event carries evidence + a `confidence_score`.

---

## 4. Subsystem Summary

| Subsystem | File(s) | What it does | Reality check |
|-----------|---------|--------------|---------------|
| **Hybrid retrieval** | `services/retrieval_service.py` | pgvector cosine **or** in-memory NumPy cosine + Postgres `ts_rank_cd` BM25, fused by RRF (k=60) | RRF is real. But the **default backend is `faiss`**, whose code path is actually a NumPy brute-force scan that loads all chunks into memory (`faiss` itself is imported but unused and not in `requirements.txt`). True pgvector only runs when `VECTOR_BACKEND=pgvector`. |
| **Grounding** | `services/grounding_service.py` | Top-30 candidate expansion → dedupe → rerank → threshold filter → token budget → `<evidence …>` blocks | Solid, well-structured. Presents chunks in document order for linear citations. |
| **Reranker** | `services/reranker_service.py` | Cross-encoder `ms-marco-MiniLM-L-6-v2`, min-max normalized | Real by default. **Silently falls back to `DummyLocalReranker`, which fabricates alternating 0.85/0.99 scores**, if sentence-transformers is unavailable. |
| **Embeddings** | `services/embedding_service.py` | `BAAI/bge-m3` (1024-dim), normalized | Falls back to Gemini `text-embedding-004` (768-dim, **zero-padded to 1024**), then to **all-zero vectors** on failure — either fallback silently degrades retrieval quality. |
| **LLM** | `services/llm_service.py` + `llm_key_rotation.py` | Gemini with round-robin multi-key rotation, 429/403 cooldowns, JSON-repair loop, safe text extraction, model fallback | Genuinely robust. Module-level singleton **raises at import** if no keys and `ENVIRONMENT != test` (hard boot dependency). |
| **Veritas Trust Engine** | `services/veritas_engine.py` | 0–100 "trust score" from 5 weighted factors | **Heuristic with hardcoded constants** (70.0/20.0/80.0/100.0), *not* an "AI evaluation layer." Only invoked by the Research Deep-Research path (which is itself broken — see §5). **Not wired into `/query/stream`**, so it does not score "every response." |
| **OCR** | `services/ocr_service.py` (real) vs `ocr_orchestrator.py` (unused) | Ingestion uses **PyMuPDF** text extraction + a python-pptx branch | The marketed **PaddleOCR + Docling multi-engine orchestrator is dead code on the upload path** — it lives only in `ocr_tasks.py`, routed to a queue the running worker never consumes. Scanned pages fall back to `page.get_text()` (a "Tesseract would go here" stub). |
| **Export** | `services/export_engine.py`, `table_extractor.py` | DOCX generation for exams/tables; CSV/HTML | Exam DOCX export is wired and synchronous; the async `export_tasks` queue is not consumed by the default worker. |
| **Auth** | `core/auth.py`, `core/security.py`, `core/middleware.py` | JWT (HS256) in cookies, bcrypt passwords, CSRF double-submit, device fingerprint, tenant context | Mostly sound. `TenantContextMiddleware` re-introduces `HS256+RS256` decoding (algorithm-confusion smell) that `auth.py` deliberately removed. |
| **Billing** | `endpoints/billing.py`, `core/trial_enforcement.py` | Trial counter, Razorpay orders + HMAC webhook, plan activation | Well-built. No per-tier quota enforcement after upgrade (roadmap item). Default `RAZORPAY_ENABLED=false` allows free self-upgrade. |
| **Automation** | `automation/auto_*.py` + Celery Beat | Health checks, daily digest, DB cleanup, key rotation, subscription/GST/model checks | Code is solid, but **no Celery Beat service exists in docker-compose**, so none of it runs in the default deployment. |

---

## 5. The Three Biggest "Marketing vs. Reality" Gaps

These are the findings a senior reviewer must understand first because they contradict the headline claims in `README.md` and `docs/marketing/`.

1. **"Trust score on every response" — not implemented on the main path.** The Veritas engine is a deterministic heuristic and is only called inside `deep_research_agent.py`. The `/query/stream` path returns the *grounding confidence* (average rerank score), which the UI renders. See [SECURITY_AUDIT.md](SECURITY_AUDIT.md) §Trust and [FINAL_AUDIT.md](FINAL_AUDIT.md).

2. **"Multi-engine OCR (PaddleOCR + Docling + validation gateway)" — off the ingestion path.** Real uploads are extracted by PyMuPDF only. The orchestrator is invoked only by `ocr_tasks.py`, routed to `ocr_gpu_queue`, which the single Docker worker (`-Q main-queue,celery`) does not consume. Handwritten/scanned documents therefore yield little/no text.

3. **"pgvector semantic search" — not the default.** `VECTOR_BACKEND` defaults to `faiss` in both `config.py` and `.env.example`; that path is a NumPy in-memory cosine scan over all rows, which does not scale and does not use the pgvector index. (`pgvector` and RRF *are* correctly implemented — they just are not the default configuration.)

Additional correctness defects (full list in [FINAL_AUDIT.md](FINAL_AUDIT.md)):

- **Broken semantic-search endpoints:** `legal/clauses/search`, `finance/transactions/search`, `study/search`, `research/search` all call `llm_service.get_embedding()` — **a method that does not exist** — and will raise `AttributeError` (HTTP 500) with no fallback. (`study/tutor/chat` and `research/copilot/chat` call the same missing method but catch the error and degrade to recency ordering.)
- **Deep Research Agent step 1** calls `retrieval_service.query(...)` and imports a `retrieval_service` singleton — neither exists — so the document-RAG step always throws and is silently swallowed.
- **`research/synthesis/{project_id}`** returns **hardcoded fake** contradiction/consensus data.
- **Async workspace processing** (`legal/finance/study/research` `/process` endpoints) enqueues Celery tasks whose modules are **not in the worker's `include` list**, so the running worker cannot execute them.
- Simulated SSE `/events/*` progress endpoints (HR/Legal/Finance/Study/Research) emit fake heartbeats, not real status.
- `S3StorageProvider` reads `settings.AWS_REGION`, which is undefined (`S3_REGION` is the real setting) → S3 storage crashes on init.

---

## 6. Production-Readiness Scorecard

Scores are 0–10, judged against a production SaaS bar, with the reasoning grounded in the source.

| Category | Score | Rationale |
|----------|:----:|-----------|
| **Architecture & design** | 7 | Clean layering (endpoints → services → models), async throughout, provider abstractions for LLM/embeddings/reranker/storage, sensible workspace isolation. Undermined by dead/duplicated subsystems. |
| **Scalability** | 5 | FastAPI async + Celery + PgBouncer are the right bones. But default vector path is in-memory NumPy (won't scale), and worker queue routing means whole task classes never run. |
| **Reliability** | 4 | Good retry/cooldown logic in the LLM layer and document worker. Offset by broken endpoints, missing Beat, and unconsumed queues that fail silently. |
| **Maintainability** | 5 | Readable code, heavy inline "why" comments. Hurt by a "never modify these files" governance model, 55 migrations with several merge heads, and stale docs. |
| **Observability** | 6 | OTel + Prometheus + Sentry + PostHog wired and env-gated; correlation-ID middleware; structured health checks. Defaults ship them **off** (`OTEL_ENABLED=false`). |
| **Security** | 5 | bcrypt, HS256 JWT pinned in `auth.py`, CSRF double-submit, HSTS/CSP headers, rate limiting, PII redaction, signed URLs. Weakened by middleware algorithm-confusion smell, free self-upgrade default, and secrets-via-env only. |
| **Performance** | 5 | Streaming, Redis caching, batched embeddings. Blocking `time.sleep` inside the key-rotator lock and NumPy full scans are latent bottlenecks. |
| **Testing** | 2 | Only **two** backend tests (health + OpenAPI generation). No auth/RAG/workspace/billing tests. CI mislabels this as "regression tests." |
| **DevOps / Deployment** | 5 | Docker Compose + Railway + CI exist and mostly work. No Beat container, Node-18/Next-16 mismatch, `--reload` in the compose backend command. |
| **Developer experience** | 6 | Rich README, CONTRIBUTING, SECURITY, architecture map, seed script, load tests. Some docs are stale/aspirational. |
| **Documentation** | 6 | Extensive but overstates delivered capability (trust score, OCR, pgvector). |
| **Enterprise readiness** | 4 | Multi-tenant isolation, org/RBAC models, RLS migrations, audit logs (legal), cost guard config. But org isolation is off by default and several enterprise features are stubs. |

**Overall: ~5/10 — an ambitious, well-structured prototype with genuinely strong pieces (LLM resilience, Finance ratio engine, Exam generation, grounding pipeline) but several headline features that are partially wired, mislabeled, or dead on the default configuration.**

---

## 7. What Is Genuinely Well-Built

To keep the audit balanced, these are the parts that are production-grade or close:

- **LLM resilience layer** (`llm_service.py`): safe text extraction across Gemini `finish_reason` cases, multi-key rotation with per-key cooldowns, model fallback, and a JSON-repair loop with Pydantic validation.
- **Finance ratio engine** (`endpoints/finance.py`): the LLM only *extracts* line items; **Python computes all 15 ratios**, with Indian number normalization (lakh/crore), accounting-standard detection, per-value numerical-integrity confidence, and an extraction audit trail. This is the correct anti-hallucination pattern for numbers.
- **Legal risk report** (`endpoints/legal.py`): LLM structured JSON + **Python-side** escalation logic, cross-analysis consistency checks, and an immutable audit log.
- **Exam generation** (`endpoints/exams.py`): grounded from chat-attached documents, marks-allocation validation, Bloom's taxonomy, honest refusal on LLM failure (no placeholder questions), auto-save, and academic DOCX export.
- **Grounding pipeline**: candidate expansion → dedupe → rerank → token budget → document-order presentation is a textbook, well-commented RAG grounding flow.
- **Document ingestion worker**: batched embeddings, streamed page extraction, retry with exponential backoff, dead-letter → `FAILED` status transitions, PPTX support.

---

## 8. How to Read the Rest of This Documentation Set

- Start with **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full system model and data flows.
- Use **[WORKSPACES.md](WORKSPACES.md)** as the per-workspace reference (features, APIs, tables, workers, limitations, improvement roadmap).
- Use **[API_AUDIT.md](API_AUDIT.md)** and **[INTEGRATIONS.md](INTEGRATIONS.md)** for endpoint- and integration-level detail.
- **[SECURITY_AUDIT.md](SECURITY_AUDIT.md)** and **[QUALITY_AUDIT.md](QUALITY_AUDIT.md)** hold the risk analysis.
- **[FINAL_AUDIT.md](FINAL_AUDIT.md)** is the single consolidated, severity-ranked issue list with evidence — use it as the backlog for the later debugging phase.
- **[INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md)** translates the system into interview-ready explanations.

*Generated as read-only documentation. No fixes were applied; every issue is described, not changed.*
