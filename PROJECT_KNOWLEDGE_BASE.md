# DocuMindAI — Project Knowledge Base (Index)

This is the entry point to the complete technical documentation and audit produced by a **read-only** inspection of the entire repository (no code was modified). It is intended as the knowledge base for a later debugging phase.

## Document Set

| Document | Read it for |
|----------|-------------|
| **[REPORT.md](REPORT.md)** | Executive overview, product, tech stack, subsystem summary, **production-readiness scorecard**, and the top marketing-vs-reality gaps |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Folder map, bootstrap, request routing, auth pipeline, ingestion pipeline, full RAG pipeline, streaming, worker/queue architecture, data layer, caching, deployment, observability |
| **[WORKSPACES.md](WORKSPACES.md)** | Deep per-workspace docs (General, HR, Legal, Finance, Study, Research, Exam): purpose, flow, APIs, tables, workers, limitations, improvements; full data-model list |
| **[API_AUDIT.md](API_AUDIT.md)** | Endpoint inventory (used/unused/broken/stub) + frontend↔backend contract audit |
| **[INTEGRATIONS.md](INTEGRATIONS.md)** | Every external service/API key/connector with wiring status |
| **[SECURITY_AUDIT.md](SECURITY_AUDIT.md)** | Security controls + findings (auth, tenancy, secrets, payments, prompt injection) |
| **[QUALITY_AUDIT.md](QUALITY_AUDIT.md)** | Dead code, duplication, smells, testing, concurrency/performance, migrations |
| **[INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md)** | FAANG-style explanations, likely Q&A, trade-offs, resume bullets, system-design concepts |
| **[FINAL_AUDIT.md](FINAL_AUDIT.md)** | **Consolidated, severity-ranked findings** (Critical→Low) with Location / Reason / Impact / Root cause / Evidence — the debugging backlog |

## The One-Paragraph Summary

**DocuMindAI** is a multi-tenant, seven-workspace RAG platform (FastAPI + async SQLAlchemy + Postgres/pgvector + Redis/Celery + Next.js 16) that answers questions about uploaded documents with Gemini, grounded and page-cited, streamed over SSE. Its strongest pieces are the **LLM resilience layer**, the **grounding pipeline**, the **Finance ratio engine** (Python does the math), the **Legal risk report**, and the **Exam generator**. Its biggest gaps are that several headline features are **partially wired, mislabeled, or dead on the default configuration** — the Veritas trust score isn't on the main query path, the multi-engine OCR isn't on the ingestion path, pgvector isn't the default (an in-memory NumPy scan is), four `*/search` endpoints call a nonexistent method, four workspace Celery task classes aren't registered with the worker, there's no Beat scheduler container, and test coverage is two smoke tests. Start with **[FINAL_AUDIT.md](FINAL_AUDIT.md)** for the prioritized issue list.

*Read-only audit — document first, do not fix.*
