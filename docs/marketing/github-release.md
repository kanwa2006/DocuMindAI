# 🧠 DocuMindAI v1.0.0 — First Stable Release

> Enterprise-grade AI document intelligence — grounded answers, page citations, and a trust score on every response.

---

## What is DocuMindAI?

DocuMindAI is a full-stack AI document intelligence platform built around a strict **zero-hallucination policy**. Upload your documents — contracts, research papers, resumes, financial statements — and get AI-powered answers that are always grounded in your content, cited to the source page, and scored for trustworthiness before they reach you.

This is not a general chatbot. Every answer traces back to a specific document and a specific page. When evidence is absent, the system refuses to answer rather than guessing.

> *"I cannot answer this based on the provided documents."*
> — DocuMindAI, instead of hallucinating.

---

## ✨ Highlights

### 🛡️ Zero-Hallucination by Architecture
The RAG pipeline injects only retrieved document chunks into the LLM within a strict token budget. No training-data knowledge leaks in. If evidence is missing, the answer is refused — explicitly.

### 🏅 Veritas Trust Engine
A post-generation scoring layer evaluates every answer across 5 weighted factors — citation density, structural alignment, hedging language, source coherence, and retrieval confidence — and produces a 0–100 trust score delivered alongside every response.

### 🔍 Hybrid RAG Retrieval
pgvector semantic search (BAAI/bge-m3, 1024-dim) fused with PostgreSQL BM25 tsvector via Reciprocal Rank Fusion, followed by cross-encoder reranking. Each of the 7 workspaces has independently tuned retrieval parameters.

### 🗂️ Seven Specialized Workspaces
General · HR · Legal · Finance · Study · Research · Exam — each with its own database models, API routes, Celery workers, and proactive insight prompts tuned to the domain.

### 📄 Multi-Engine OCR
PaddleOCR (handwritten/rotated) + Docling (structured/tabular) with a validation gateway that selects the best output automatically.

### 💡 Proactive Insights
On document upload, the AI automatically surfaces domain-critical findings — risk clauses, anomalies, standout candidates — without any user query.

### ⚡ Real-Time SSE Streaming
Answers stream token-by-token to the browser via Server-Sent Events across a fully async pipeline.

### 📤 Export Engine
Generate formatted DOCX reports: legal redlines, graded exam papers with answer keys, HR candidate summaries.

---

## 🔐 Security Fixes in this Release

| ID | Description |
|----|-------------|
| BUG-001 | SSL/TLS `asyncpg` DSN configuration |
| BUG-002 | Document serialization 500 error on missing fields |
| BUG-003 | `setState` in React render cycle |
| BUG-004 | Embedding dimension mismatch (384 → 1024 for bge-m3) |
| BUG-005 | Retry logic now correctly transitions status to `FAILED` |
| BUG-006 | Dark-mode button contrast (`var(--brand)` fix) |
| BUG-007 | JWT algorithm constraint enforcement |
| BUG-008 | Refresh token 7-day expiry consistency |
| BUG-009 | Absolute storage path resolution for local file serving |
| BUG-010 | UUID type coercion in trial enforcement middleware |
| BUG-011 | Embedding fallback dimension padding (768 → 1024) |
| BUG-012 | SlowAPI `request` parameter naming crash fix |
| BUG-013 | `Request` import missing in `query.py` |
| BUG-014 | Celery isolated event loop for async worker tasks |
| BUG-015 | Veritas Engine `hasattr` on dict → `.get()` |
| BUG-016 | Temporary file extension preservation during OCR |

---

## ⚠️ Known Limitations

| Issue | Impact |
|-------|--------|
| ~35 frontend API call sites have a doubled `/api/v1` prefix | Functional, tracked for v1.1 |
| `workspace_id` type inconsistency (string vs UUID) | Tracked for v1.1 |
| Pydantic v1 `class Config` deprecation warnings | Warnings only, no failures |
| No hosted public demo yet | Local Docker setup works fully |

---

## 🚀 Getting Started

```bash
git clone https://github.com/kanwa2006/DocuMindAI.git
cd DocuMindAI
cp .env.example .env
# Fill in GEMINI_API_KEY_1 and security secrets
cd infrastructure && docker-compose up --build
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Frontend |
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | Swagger / OpenAPI |

Full guide: [docs/deployment/installation.md](https://github.com/kanwa2006/DocuMindAI/blob/main/docs/deployment/installation.md)

---

## 🛠️ Stack

**Backend:** FastAPI · SQLAlchemy · Alembic · Celery · SlowAPI  
**Frontend:** Next.js 16 · React 19 · TypeScript 5 · Tailwind CSS 4  
**Database:** PostgreSQL 16 + pgvector · PgBouncer · Redis 7  
**AI:** Google Gemini · BAAI/bge-m3 · PaddleOCR · Docling · Tavily  
**Infra:** Docker Compose · Railway · GitHub Actions  
**Observability:** OpenTelemetry · Prometheus · Sentry · PostHog

---

## 🗺️ What's Next (v1.1)

- [ ] Normalize frontend API prefix (~35 call sites)
- [ ] Unify `workspace_id` type with `uuid.uuid5` slug mapping
- [ ] Quota enforcement gating by pricing tier
- [ ] Hosted public demo
- [ ] Migrate to `google-genai` SDK
- [ ] Code coverage in CI

---

## 📖 Full Release Notes

→ [`RELEASE_NOTES_v1.0.0.md`](https://github.com/kanwa2006/DocuMindAI/blob/main/RELEASE_NOTES_v1.0.0.md)

---

## 👤 Author

**Kanwa Munipalle** — [github.com/kanwa2006](https://github.com/kanwa2006)

---

*MIT License · Built with care for professionals who work with documents every day.*
