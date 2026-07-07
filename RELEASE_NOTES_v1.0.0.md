# Release Notes — DocuMindAI v1.0.0

**Release Date:** July 2026
**Tag:** [`v1.0.0`](https://github.com/kanwa2006/DocuMindAI/releases/tag/v1.0.0)
**Branch:** `main`

---

## 🎉 Highlights

DocuMindAI `v1.0.0` is the first stable public release of a full-stack, enterprise-grade AI document intelligence platform. This release ships:

- **7 independent, specialized workspaces** for General, HR, Legal, Finance, Study, Research, and Exam use cases
- A **hybrid RAG pipeline** combining pgvector semantic search and PostgreSQL BM25 full-text search, fused via Reciprocal Rank Fusion
- The **Veritas Trust Engine** — a post-generation answer scoring system that assigns 0–100 trust scores based on citation density, structural alignment, and hedging behavior
- A **zero-hallucination policy** enforced at the pipeline level: the system refuses to answer when document evidence is absent
- A production-ready **Next.js 16 frontend** with SSE streaming, a command palette, proactive insights panel, and a PWA manifest

---

## 🗂️ Major Features

### AI & RAG Pipeline

| Feature | Description |
|---------|-------------|
| Hybrid Retrieval | Semantic (pgvector cosine) + Lexical (tsvector BM25) fused via Reciprocal Rank Fusion (RRF) |
| Per-Workspace Tuning | Each workspace has independently configured chunk sizes, top-k values, and RRF weights |
| Reranker | Cross-encoder reranking pass after initial retrieval |
| Grounding Service | Strict token-budget enforcement with citation formatting and document-order sorting |
| Gemini LLM | Multi-key rotation across `GEMINI_API_KEY_1..N` with per-key cooldown and failover |
| JSON Repair Loop | Automatic retry and repair of malformed Gemini structured outputs |
| Proactive Insights | AI automatically surfaces critical findings from documents on upload (no query required) |

### Seven Specialized Workspaces

| Workspace | Key Capabilities |
|-----------|-----------------|
| **General** | Universal document Q&A with any file type |
| **HR** | Resume parsing, candidate auto-ranking, job-match scoring, interview pipeline |
| **Legal** | Contract clause risk flagging, compliance rule checking, redline DOCX export |
| **Finance** | Financial ratio extraction, anomaly detection, audit finding identification |
| **Study** | SM-2 spaced-repetition flashcard generation, Pomodoro timer, multi-format quizzes |
| **Research** | Literature synthesis, contradiction detection, Deep Research Agent (RAG + Tavily web) |
| **Exam / Teacher** | Grounded MCQ/Short/Long/Case Study paper generation with answer keys and DOCX export |

### Document Processing

- **OCR Pipeline**: PaddleOCR (handwritten, rotated, low-quality scans) + Docling (structured/tabular documents) with a validation gateway that selects the best output
- **Supported Formats**: PDF, DOCX, PPTX, and image uploads
- **Async Processing**: All document ingestion runs in Celery workers to keep the API non-blocking
- **Temporary File Handling**: Uploaded file extensions are preserved during OCR to prevent format detection errors

### Frontend

- **Next.js 16** with the App Router — one dedicated page per workspace
- **WorkspaceUI**: context-aware chat interface with document preview, SSE streaming, command palette, and selection clips
- **ProactiveInsightsPanel**: auto-refreshing insights surfaced from newly uploaded documents
- **EnterpriseDocumentViewer**: in-browser PDF rendering via `react-pdf`
- **PWA**: service worker, manifest, and install prompt support
- **PomodoroTimer**: built into the Study workspace
- **ShareSessionModal**: generate shareable, token-authenticated read-only chat links
- **Dark mode**: full theme support via CSS variables

### Authentication & Security

- JWT access tokens + refresh tokens (7-day expiry)
- CSRF protection (double-submit cookie pattern)
- Slowapi rate limiting on upload and query endpoints
- Email OTP verification flow for new registrations
- Device fingerprinting for session integrity

### Billing & Multi-Tenancy

- Go / Plus / Pro pricing tiers with plan-gated feature access
- Razorpay-ready billing integration
- Tenant context middleware for workspace isolation

### Observability

- **OpenTelemetry** distributed tracing across all services
- **Prometheus** metrics endpoint at `/metrics`
- **Sentry** error tracking (backend and frontend)
- **PostHog** product analytics

### Infrastructure & CI/CD

- Docker Compose with 6 containers: PostgreSQL 16 + pgvector, PgBouncer, Redis 7, FastAPI, Celery Worker, Next.js
- Railway deployment via `railway.json`
- GitHub Actions CI: dependency audit (`pip-audit`), Alembic migration test, API contract tests (`pytest`), ESLint, and Next.js production build on every push to `main`

---

## 🏗️ Architecture

```
Next.js 16 (App Router)
    │ REST + SSE
FastAPI /api/v1/
    ├── Middleware: CORS · CSRF · RateLimit · TenantContext · OTel
    ├── AI / RAG Pipeline (OCR → Embed → Retrieve → Rerank → Ground → Generate → Veritas)
    └── Celery Workers (7 workspace task queues + Celery Beat automation)
        │
        └── Data Layer: PostgreSQL 16 + pgvector · PgBouncer · Redis 7
```

Full route-to-service mapping is documented in [docs/architecture/project-map.md](docs/architecture/project-map.md).

---

## ⚡ Performance

- **Async throughout**: FastAPI with `asyncpg`, async SQLAlchemy, and async Redis — zero blocking I/O on the API server
- **Connection pooling**: PgBouncer in transaction mode handles up to 1000 concurrent database connections
- **Celery Beat automation**: background tasks (health check, daily digest, DB cleanup, key rotation) run on schedule without impacting request latency
- **SSE streaming**: answers begin rendering on the frontend after the first token — no waiting for full completion

---

## 🔐 Security

### Fixes included in v1.0.0

| ID | Description |
|----|-------------|
| BUG-001 | Resolved SSL/TLS `asyncpg` DSN configuration |
| BUG-002 | Fixed document serialization 500 error on missing fields |
| BUG-003 | Removed `setState` call inside render cycle |
| BUG-004 | Corrected embedding dimension mismatch (384 → 1024) for `bge-m3` |
| BUG-005 | Fixed document retry logic to correctly flip status to `FAILED` |
| BUG-006 | Dark-mode button contrast fix (hardcoded blue → `var(--brand)`) |
| BUG-007–016 | Backend stability fixes: auth token scope, embedding fallback, storage path resolution, rate-limiter parameter naming, celery event-loop isolation, UUID type coercion in trial enforcement |

### General posture

- `.env` is excluded from version control via `.gitignore`
- All Gemini API keys are loaded from environment variables only
- CSRF double-submit cookie protection is active on all mutating endpoints
- Rate limiting is applied to upload and query endpoints via SlowAPI

---

## ⚠️ Known Limitations

These limitations are known and tracked for future releases:

| Area | Limitation |
|------|-----------|
| **API prefix doubling** | ~35 frontend call sites include a manual `/api/v1` prefix that doubles with `NEXT_PUBLIC_API_URL`. Affected pages still function but the convention is inconsistent. |
| **Workspace identity** | `User.workspace_id` is a string slug (`"general"`) while `ChatSession.workspace_id` is a UUID. A deterministic `uuid.uuid5` resolver is planned to unify the model. |
| **EnterpriseDocumentViewer** | PDF rendering is client-side only; SSR causes a hydration error that is suppressed with a `dynamic` import guard. |
| **Demo** | No hosted public demo is currently available. Local Docker Compose setup is fully functional. |
| **Pydantic v1 compat warnings** | Several schema classes still use the deprecated `class Config` style (Pydantic v2 compatibility shim). These will be migrated to `model_config = ConfigDict(...)` in a future patch. |

---

## 🗺️ Future Roadmap

| Priority | Item |
|----------|------|
| High | Fix API prefix doubling across frontend call sites |
| High | Unify `workspace_id` type with `uuid.uuid5` slug mapping |
| High | Deploy hosted public demo |
| Medium | Migrate to `google-genai` SDK (next-gen Gemini client) |
| Medium | Migrate all Pydantic schemas from `class Config` to `ConfigDict` |
| Medium | Mobile PWA improvements & offline document caching |
| Low | Multi-language support for regional Indian languages |
| Low | Dedicated admin analytics dashboard |

---

## 💥 Breaking Changes

This is the first stable release (`v1.0.0`). There are no breaking changes from a previous stable version.

If you are migrating from an earlier development snapshot:
- Re-run `alembic upgrade head` after pulling — the migration history has been consolidated
- Regenerate all JWT secrets (`AUTH_SECRET_KEY`, `CSRF_SECRET_KEY`)
- Update `NEXT_PUBLIC_API_URL` to **not** include `/api/v1` — the client library handles the prefix

---

## 👥 Credits

**Lead Developer:** Kanwa Munipalle

### Open-Source Foundations

| Project | Role |
|---------|------|
| [Google Gemini](https://deepmind.google/technologies/gemini/) | LLM backbone |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | OCR for handwritten and rotated documents |
| [Docling](https://github.com/DS4SD/docling) | Structured document layout parsing |
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | Multilingual sentence embeddings |
| [pgvector](https://github.com/pgvector/pgvector) | Vector similarity search for PostgreSQL |
| [Tavily](https://tavily.com/) | Web research API for the Deep Research Agent |
| [FastAPI](https://fastapi.tiangolo.com/) | Async Python API framework |
| [Next.js](https://nextjs.org/) | React framework with App Router |
| [Celery](https://docs.celeryq.dev/) | Distributed task queue |

---

*Thank you to everyone who tested, reviewed, and contributed to this release.* 🙏
