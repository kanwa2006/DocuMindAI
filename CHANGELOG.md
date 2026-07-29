# DocuMindAI — Release Notes v1.0.0

**Release Date:** July 2026  
**Tag:** [`v1.0.0`](https://github.com/kanwa2006/DocuMindAI/releases/tag/v1.0.0)  
**Branch:** `main`  
**License:** MIT

---

> First stable public release. Enterprise-grade AI document intelligence with a strict zero-hallucination policy across seven specialized workspaces.

---

## 🎉 Highlights

- **7 independent workspaces** — each with its own models, API routes, Celery workers, and domain-tuned retrieval
- **Hybrid RAG pipeline** — pgvector semantic search + PostgreSQL BM25, fused via Reciprocal Rank Fusion
- **Veritas Trust Engine** — post-generation 0–100 trust scoring across 5 weighted factors
- **Multi-engine OCR** — PaddleOCR (handwritten/rotated) + Docling (structured/tabular) with validation gateway
- **Proactive insights** — AI surfaces domain-specific findings on every document upload, without user prompting
- **SSE streaming** — token-by-token answer delivery to the browser via Server-Sent Events
- **DOCX export engine** — formatted reports for legal, exam, and HR workspaces
- **Multi-key Gemini rotation** — automatic failover with per-key rate-limit state and cooldown
- **Full observability** — OpenTelemetry tracing, Prometheus metrics, Sentry, PostHog
- **GitHub Actions CI** — dependency audit, Alembic migration tests, API contracts, lint, and build on every push

---

## 📋 Features by Workspace

### 💬 General
Universal document Q&A. Upload any file type and ask any question. Answers are grounded in retrieved evidence with page citations.

### 👥 HR
- Resume parsing and structured field extraction
- Candidate auto-ranking with configurable scoring weights
- Job-match scoring against role descriptions
- Interview pipeline state tracking

### ⚖️ Legal
- Contract clause extraction and risk flagging
- Compliance rule checking
- Redline DOCX export with annotations

### 📈 Finance
- Financial ratio extraction (liquidity, leverage, profitability)
- Anomaly detection in financial statements
- Audit finding identification and categorization

### 📚 Study
- SM-2 spaced-repetition flashcard generation from documents
- Pomodoro timer integrated into workspace
- Adaptive quiz generation in multiple formats

### 🔬 Research
- Multi-paper literature synthesis
- Contradiction detection across sources
- Deep Research Agent combining RAG retrieval with Tavily live web search

### 🎓 Exam / Teacher
- Grounded question generation: MCQ, Short Answer, Long Answer, Case Study
- Configurable paper structure (section counts, marks per question)
- Answer key generation
- Formatted DOCX export with professional exam layout

---

## 🔐 Security Fixes

The following backend stability and security issues were resolved before this release:

| ID | Component | Description |
|----|-----------|-------------|
| BUG-001 | Database | SSL/TLS `asyncpg` DSN configuration fix |
| BUG-002 | Documents API | Document serialization 500 error on missing optional fields |
| BUG-003 | Frontend | Removed `setState` call inside React render cycle |
| BUG-004 | Embedding | Corrected dimension mismatch: 384 → 1024 for BAAI/bge-m3 |
| BUG-005 | Workers | Document retry logic now correctly flips status to `FAILED` |
| BUG-006 | Frontend | Dark-mode button contrast (hardcoded blue → `var(--brand)`) |
| BUG-007 | Auth | JWT algorithm constraint enforcement in token verification |
| BUG-008 | Security | `create_refresh_token` enforces 7-day expiry consistently |
| BUG-009 | Storage | Absolute storage path resolution for local file serving |
| BUG-010 | Billing | UUID type coercion in trial enforcement middleware |
| BUG-011 | Embedding | 768→1024 dimension padding for Gemini text-embedding-004 fallback |
| BUG-012 | Documents | SlowAPI parameter renamed `http_request` → `request` (crash fix) |
| BUG-013 | Query | `Request` import added to `query.py` (resolves `NameError`) |
| BUG-014 | Workers | Celery isolated event loop for async proactive insight tasks |
| BUG-015 | Veritas | Replaced `hasattr` on dict with `.get()` for direct-quote evaluation |
| BUG-016 | Workers | Temporary file extension preservation during OCR processing |

---

## ⚠️ Known Limitations

These issues are tracked for future releases and do not block usage of the current version.

| Issue | Impact | Planned Fix |
|-------|--------|-------------|
| **API prefix doubling** | ~35 frontend call sites include a manual `/api/v1` that duplicates the `NEXT_PUBLIC_API_URL` prefix. Affected pages still function correctly. | v1.1 |
| **Workspace ID type inconsistency** | `User.workspace_id` is a string slug (`"general"`) while `ChatSession.workspace_id` is a UUID. A `uuid.uuid5` resolver is planned. | v1.1 |
| **Pydantic v1 compatibility warnings** | Several schemas use deprecated `class Config` style. These generate 24 deprecation warnings during `pytest` but do not fail. | v1.2 |
| **No hosted public demo** | The application must currently be run locally via Docker Compose. | Planned |
| **EnterpriseDocumentViewer SSR** | PDF rendering is CSR-only; a `dynamic` import guard suppresses the hydration error. | Tracked |

---

## 🗺️ Roadmap

### 🔄 In Progress

- Quota enforcement gating by Go / Plus / Pro pricing tier
- Normalize frontend API prefix convention (~35 call sites)

### 📋 Planned

- Deploy hosted public demo
- Migrate to `google-genai` SDK (next-gen Gemini client)
- Unify `workspace_id` type with `uuid.uuid5` slug mapping
- Migrate Pydantic schemas from `class Config` to `ConfigDict`
- Mobile PWA improvements and offline document caching
- Multi-language support for regional Indian languages
- Code coverage reporting in CI

---

## 💥 Breaking Changes

This is the first stable release. There are no breaking changes from a previous stable version.

**If migrating from a development snapshot:**

- Re-run `alembic upgrade head` after pulling — the migration history has been consolidated
- Regenerate `AUTH_SECRET_KEY` and `CSRF_SECRET_KEY` with new 64-character random values
- Ensure `NEXT_PUBLIC_API_URL` does **not** include `/api/v1` — the API client handles the prefix internally

---

## 📦 Installation

```bash
git clone https://github.com/kanwa2006/DocuMindAI.git
cd DocuMindAI
cp .env.example .env
cd infrastructure && docker-compose up --build
```

Full setup guide: [docs/deployment/installation.md](docs/deployment/installation.md)

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
| [Tavily](https://tavily.com/) | Web search API for the Deep Research Agent |
| [FastAPI](https://fastapi.tiangolo.com/) | Async Python API framework |
| [Next.js](https://nextjs.org/) | React framework with App Router |
| [Celery](https://docs.celeryq.dev/) | Distributed task queue |

---

## 🔗 Links

| Resource | Link |
|----------|------|
| Repository | https://github.com/kanwa2006/DocuMindAI |
| Release tag | https://github.com/kanwa2006/DocuMindAI/releases/tag/v1.0.0 |
| Installation | [docs/deployment/installation.md](docs/deployment/installation.md) |
| Architecture | [docs/architecture/project-map.md](docs/architecture/project-map.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| License | [LICENSE](LICENSE) |

---

*Thank you to everyone who tested, reviewed, and contributed feedback during development.* 🙏
