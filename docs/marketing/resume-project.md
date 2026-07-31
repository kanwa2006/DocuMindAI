# Resume Project Entry — DocuMindAI

*ATS-optimized. Use the version that best matches the target role.*

---

## Full Version

**DocuMindAI — Enterprise AI Document Intelligence Platform**
*Full-Stack Engineering · AI/ML · Open Source · v1.0.0 · July 2026*
GitHub: github.com/kanwa2006/DocuMindAI

- Designed and built a zero-hallucination AI document intelligence platform with 7 specialized workspaces (HR, Legal, Finance, Research, Study, Exam, General), enforcing grounded answers via a strict token-budget RAG pipeline that cites source pages and explicitly refuses to respond when evidence is absent
- Implemented a hybrid retrieval system combining pgvector semantic search (BAAI/bge-m3, 1024-dim embeddings) with PostgreSQL BM25 full-text search, fused via Reciprocal Rank Fusion and followed by cross-encoder reranking — improving retrieval precision over semantic-only baselines
- Engineered the Veritas Trust Engine, a post-generation multi-factor scoring system (0–100) evaluating citation density, structural alignment, source coherence, and hedging behavior on every LLM response before delivery to the user
- Architected a fully async production backend (FastAPI, asyncpg, async SQLAlchemy, Celery, Redis) with PgBouncer connection pooling, OpenTelemetry distributed tracing, Prometheus metrics, and Sentry error tracking across all services
- Built a Next.js 16 / React 19 / TypeScript frontend with real-time Server-Sent Events streaming, a command palette, proactive insights panel, PWA support, and one workspace-specific page per domain

**Technologies:** Python · FastAPI · SQLAlchemy · Alembic · Celery · PostgreSQL · pgvector · Redis · PgBouncer · Google Gemini · BAAI/bge-m3 · PaddleOCR · Docling · Tavily · Next.js 16 · React 19 · TypeScript · Tailwind CSS · OpenTelemetry · Prometheus · Sentry · Docker · GitHub Actions · Railway

---

## Condensed Version (3 bullets — for space-constrained resumes)

**DocuMindAI** | Full-Stack AI Platform | github.com/kanwa2006/DocuMindAI

- Built an open-source AI document intelligence platform enforcing zero hallucination via grounded RAG — hybrid retrieval (pgvector + BM25 + RRF) with page-level source citations and a post-generation trust score (0–100) across 7 specialized workspaces
- Designed a fully async FastAPI backend with Celery distributed task queue, PgBouncer connection pooling, and an OpenTelemetry + Prometheus + Sentry observability stack; Next.js 16 frontend with real-time SSE streaming
- Shipped production CI/CD (GitHub Actions: dep audit, Alembic migration tests, API contracts, lint, build) and Docker Compose + Railway deployment infrastructure

**Stack:** Python · FastAPI · PostgreSQL + pgvector · Redis · Next.js · TypeScript · Google Gemini · Docker · GitHub Actions

---

## Single-Line Version (for skills section or project list)

**DocuMindAI** — Zero-hallucination AI document intelligence platform; hybrid RAG (pgvector + BM25 + RRF); Veritas Trust Engine; 7 workspaces; FastAPI · Next.js 16 · PostgreSQL · Celery · Gemini | *github.com/kanwa2006/DocuMindAI*

---

## Role-Specific Tailoring

### For AI/ML Engineer roles — emphasize:
- Hybrid retrieval architecture (RRF, cross-encoder reranking)
- BAAI/bge-m3 embedding pipeline and dimension management
- Veritas Trust Engine design (multi-factor scoring)
- Zero-hallucination grounding service token budget enforcement
- Multi-key Gemini rotation with per-key cooldown logic

### For Backend Engineer roles — emphasize:
- Fully async FastAPI + asyncpg + async SQLAlchemy architecture
- Celery distributed task queue with domain-specific worker pools
- PgBouncer connection pooling configuration
- Alembic migration management across 7 workspace schemas
- OpenTelemetry tracing and Prometheus metrics instrumentation

### For Full-Stack Engineer roles — emphasize:
- Next.js 16 App Router with one workspace page per domain
- Real-time SSE streaming pipeline (generator → FastAPI → browser)
- TypeScript strict mode throughout frontend
- React 19 with custom hooks (useVoiceInput, useSessionExpiry, useOnboarding)
- PWA manifest, service worker, and offline support

### For DevOps / Platform Engineer roles — emphasize:
- GitHub Actions CI: dep audit (pip-audit), Alembic migration tests, API contracts (pytest), ESLint, Next.js build
- Docker Compose multi-service orchestration (6 containers)
- Railway cloud deployment via `railway.json`
- OpenTelemetry, Prometheus, Sentry full observability stack
- PgBouncer transaction-mode connection pooling

---

## Impact Framing (for cover letters / interviews)

> DocuMindAI demonstrates the ability to design systems where correctness guarantees are enforced at the architecture level — not patched at the prompt level. The zero-hallucination constraint required carefully restricting LLM data access at the pipeline boundary, making this a meaningful engineering constraint rather than an aspirational feature.

> The project required making real architectural trade-offs: hybrid retrieval over semantic-only (improved precision), per-workspace configuration over a single shared config (improved domain accuracy), Celery workers over in-process async (improved scalability and failure isolation).
