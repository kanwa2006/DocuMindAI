<div align="center">

# 🧠 DocuMindAI

**Enterprise-grade AI document intelligence — grounded, cited, trusted.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL+pgvector-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery)](https://docs.celeryq.dev/)
[![CI](https://img.shields.io/github/actions/workflow/status/kanwa2006/DocuMindAI/ci.yml?label=CI)](https://github.com/kanwa2006/DocuMindAI/actions)

[Features](#-features) · [Workspaces](#-seven-specialized-workspaces) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Installation](#-installation) · [Project Structure](#-project-structure) · [Roadmap](#-roadmap)

</div>

---

## 📌 What is DocuMindAI?

DocuMindAI is a **full-stack AI document intelligence platform** built around a strict **zero-hallucination policy**. Upload your documents — contracts, financial statements, research papers, resumes, or textbooks — and get AI-powered answers that are always **grounded in your content**, **cited to the source page**, and **scored for trustworthiness** before they reach you.

This is not a general-purpose AI chatbot. Every answer produced by DocuMindAI traces back to a specific document, a specific page, and a specific chunk of text. The system refuses to fabricate responses when evidence is absent.

> *"I cannot answer this based on the provided documents."* — what DocuMindAI says instead of guessing.

---

## ✨ Features

- 🔍 **Hybrid Retrieval** — Semantic (pgvector cosine) + Lexical (BM25 tsvector) search fused via **Reciprocal Rank Fusion (RRF)**
- 🤖 **Gemini LLM** — Multi-key rotation with automatic failover, rate-limit cooldowns, and safe streaming
- 📄 **Multi-engine OCR** — PaddleOCR (handwritten/rotated) + Docling (structured/tabular) with validation gateway
- 🛡️ **Veritas Trust Engine** — Post-generation trust scoring (0–100) across 5 weighted factors
- 💡 **Proactive Insights** — AI surfaces critical findings automatically on upload (no query needed)
- 🏢 **7 Specialized Workspaces** — Each workspace has tailored retrieval configs, domain models, and dedicated workers
- 📤 **Export Engine** — Generate formatted DOCX reports (legal redlines, exam papers, literature reviews)
- 🔄 **Real-time Streaming** — Server-Sent Events (SSE) for live answer streaming
- 🔐 **Enterprise Security** — JWT + CSRF + rate limiting + HSTS + device fingerprinting
- 📊 **Full Observability** — OpenTelemetry distributed tracing + Prometheus metrics + Sentry + PostHog
- 💳 **India-first Billing** — Razorpay-ready with Go / Plus / Pro tiers (₹799 / ₹999 / ₹2,999)
- ☁️ **Flexible Deployment** — Docker Compose (dev) + Railway (prod) + GitHub Actions CI/CD

---

## 🗂️ Seven Specialized Workspaces

Each workspace is a fully independent environment with its own database models, API routes, Celery workers, retrieval configuration, and proactive insight prompts.

| Workspace | Icon | Purpose |
|-----------|------|---------|
| **General** | 💬 | Universal document Q&A — upload anything, ask anything |
| **HR** | 👥 | Resume screening, candidate auto-ranking, interview pipeline tracking |
| **Legal** | ⚖️ | Contract review, clause risk flagging, redline DOCX export |
| **Finance** | 📈 | Financial statement analysis, ratio extraction, anomaly detection |
| **Study** | 📚 | Flashcard generation (SM-2 spaced repetition), Pomodoro timer, quizzes |
| **Research** | 🔬 | Literature synthesis, contradiction detection, Deep Research Agent (RAG + Tavily web) |
| **Exam / Teacher** | 🎓 | Auto-generate exam papers with MCQ/Short/Long/Case Study sections, answer keys, DOCX export |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js 16 (App Router)                      │
│   /login  /hr  /legal  /finance  /study  /research  /exam  ...  │
│   WorkspaceUI · Sidebar · CommandPalette · ProactiveInsights     │
└───────────────────────┬─────────────────────────────────────────┘
                        │ REST + SSE
┌───────────────────────▼─────────────────────────────────────────┐
│                  FastAPI  /api/v1/                               │
│  auth · documents · query · hr · legal · finance · study        │
│  research · exams · export · billing · bookmarks · admin  ...   │
│  Middleware: CORS · CSRF · RateLimit · TenantContext · OTel      │
└──────────┬───────────────────────────┬───────────────────────────┘
           │                           │
┌──────────▼──────────┐   ┌────────────▼────────────────────────────┐
│   AI / RAG Pipeline  │   │           Celery Workers                │
│                      │   │                                         │
│  1. OCR Orchestrator │   │  document_tasks  hr_tasks  legal_tasks  │
│     ├ Docling        │   │  finance_tasks   study_tasks            │
│     └ PaddleOCR      │   │  research_tasks  export_tasks           │
│                      │   │                                         │
│  2. Embedding        │   │  Celery Beat Automation:                │
│     └ BAAI/bge-m3    │   │  auto_health_check · auto_daily_digest  │
│                      │   │  auto_db_cleanup · auto_key_rotation    │
│  3. Hybrid Retrieval │   └─────────────────────────────────────────┘
│     ├ pgvector       │
│     ├ tsvector BM25  │   ┌─────────────────────────────────────────┐
│     └ RRF Fusion     │   │          Data Layer                     │
│                      │   │                                         │
│  4. Reranker         │   │  PostgreSQL 16 + pgvector               │
│                      │   │  PgBouncer (1000 conn, transaction mode)│
│  5. Grounding        │   │  Redis 7 (broker + cache + sessions)    │
│     └ Token Budget   │   │  Local Storage / S3 / Supabase          │
│                      │   └─────────────────────────────────────────┘
│  6. Gemini LLM       │
│     └ Key Rotation   │
│                      │
│  7. Veritas Engine   │
│     └ Trust Score    │
└──────────────────────┘
```

### Core Pipeline Flow

```
User Query
    │
    ▼
Hybrid Retrieval (Semantic + Lexical → RRF)
    │
    ▼
Reranker (Cross-encoder scoring)
    │
    ▼
Grounding Service (Token budget · Citation formatting · Document-order sort)
    │
    ▼
Gemini LLM (Multi-key rotation · Safe streaming · JSON repair loop)
    │
    ▼
Veritas Trust Engine (0-100 score · 5 weighted factors)
    │
    ▼
SSE Stream → Frontend
```

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Role |
|-----------|---------|------|
| Next.js | 16.2.6 | App Router, SSR, routing |
| React | 19.2.4 | UI framework |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 4.x | Utility-first styling |
| react-pdf | 10.4.1 | In-browser PDF viewer |
| recharts | 2.15.4 | Charts & analytics |
| @sentry/nextjs | 10.53.1 | Error monitoring |
| posthog-js | 1.374.2 | Product analytics |

### Backend
| Technology | Version | Role |
|-----------|---------|------|
| FastAPI | ≥0.109 | Async REST API |
| Pydantic | ≥2.5 | Validation & settings |
| SQLAlchemy | ≥2.0 | Async ORM |
| Alembic | ≥1.13 | DB migrations |
| Celery | ≥5.3.6 | Distributed task queue |
| PaddleOCR | ≥2.7.0 | Handwritten/scanned OCR |
| Docling | ≥1.1.0 | Structured document extraction |
| PyMuPDF | ≥1.23.8 | Native PDF text extraction |
| sentence-transformers | ≥2.7.0 | Embeddings (BAAI/bge-m3) |
| pgvector | ≥0.2.5 | Vector similarity in Postgres |
| google-generativeai | latest | Gemini LLM integration |
| python-docx | ≥1.1.0 | DOCX export generation |
| slowapi | ≥0.1.9 | API rate limiting |
| OpenTelemetry | ≥1.20 | Distributed tracing |
| Razorpay | ≥1.4.1 | Payment integration |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 + pgvector |
| Connection Pool | PgBouncer (transaction mode) |
| Cache / Broker | Redis 7 |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Hosting | Railway (production) |
| Monitoring | Sentry · OpenTelemetry · Prometheus |

---

## 📸 Screenshots

> Screenshots below show the platform in action across different workspaces.

### General Workspace — Grounded Q&A with Citations
```
[ Screenshot placeholder: /general workspace with a PDF uploaded,
  user question, and a streamed answer with inline page citations
  and Veritas trust score badge ]
```

### HR Workspace — Candidate Rankings Panel
```
[ Screenshot placeholder: /hr workspace showing ranked candidates,
  job-description match scores, pipeline status columns ]
```

### Legal Workspace — Contract Risk Analysis
```
[ Screenshot placeholder: /legal workspace showing clause-by-clause
  risk levels (HIGH/MEDIUM/LOW), with redline export button ]
```

### Finance Workspace — Ratio Dashboard
```
[ Screenshot placeholder: /finance workspace with ratio charts,
  year-on-year trend graphs, and anomaly flagging ]
```

### Exam Workspace — Paper Generation
```
[ Screenshot placeholder: /exam workspace with PaperConfigPanel
  showing sections, question types, auto-generated Q&A, DOCX export ]
```

---

## 🚀 Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- A Google Gemini API key ([get one free](https://aistudio.google.com/))

### 1. Clone the Repository

```bash
git clone https://github.com/kanwa2006/DocuMindAI.git
cd DocuMindAI
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

```env
# Required
GEMINI_API_KEY_1=your_gemini_api_key_here
AUTH_SECRET_KEY=your_64_char_random_secret
CSRF_SECRET_KEY=your_other_random_secret

# Database (local Docker default — no changes needed for dev)
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=documind

# Redis (local Docker default)
REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/0
CELERY_RESULT_BACKEND=redis://localhost:6380/0

# App
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
```

### 3. Start Infrastructure Services

```bash
cd infrastructure
docker-compose up -d db pgbouncer redis
```

This starts:
- PostgreSQL + pgvector on port `5433`
- PgBouncer (connection pooling) on port `6432`
- Redis on port `6380`

### 4. Set Up the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is available at `http://localhost:8000`
Swagger docs at `http://localhost:8000/api/v1/openapi.json`

### 5. Start the Celery Worker

Open a new terminal:

```bash
cd backend
venv\Scripts\activate
celery -A app.workers.celery_app worker -Q main-queue,celery --loglevel=info
```

### 6. Set Up the Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is available at `http://localhost:3000`

### 7. (Optional) Run Everything with Docker Compose

```bash
cd infrastructure
docker-compose up --build
```

This starts all 6 services: `db`, `pgbouncer`, `redis`, `backend`, `worker`, `frontend`.

---

## ⚙️ Environment Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY_1` | ✅ | Primary Gemini API key. Add `_2`, `_3`... for rotation |
| `AUTH_SECRET_KEY` | ✅ | 64-char JWT signing secret |
| `CSRF_SECRET_KEY` | ✅ | CSRF token secret |
| `POSTGRES_SERVER` | ✅ | Database host |
| `REDIS_URL` | ✅ | Redis connection string |
| `STORAGE_PROVIDER` | — | `local` (default) or `s3` |
| `VECTOR_BACKEND` | — | `faiss` (default), `pgvector`, or `qdrant` |
| `SENTRY_DSN` | — | Error monitoring (optional) |
| `RAZORPAY_KEY_ID` | — | Payment integration (optional) |
| `SMTP_PASSWORD` | — | SendGrid API key for email OTP |

See [`.env.example`](.env.example) for the full reference.

---

## 📁 Project Structure

```
DocuMindAI/
├── backend/                         # FastAPI application
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── endpoints/           # 26 route modules
│   │   │       ├── auth.py          # Register, login, verify, refresh
│   │   │       ├── query.py         # Streaming Q&A (SSE)
│   │   │       ├── documents.py     # Upload, process, serve
│   │   │       ├── hr.py            # Candidate ranking, pipeline
│   │   │       ├── legal.py         # Contract analysis, redlines
│   │   │       ├── finance.py       # Ratio extraction, audit
│   │   │       ├── study.py         # Flashcards, SM-2, quizzes
│   │   │       ├── research.py      # Literature synthesis
│   │   │       ├── exams.py         # Exam paper generation
│   │   │       ├── export.py        # DOCX/PDF export
│   │   │       ├── billing.py       # Plans, trial enforcement
│   │   │       └── ...              # + 14 more modules
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic settings (all env vars)
│   │   │   ├── security.py          # JWT helpers
│   │   │   ├── middleware.py        # CSRF · Tenant · Fingerprint
│   │   │   ├── telemetry.py         # OpenTelemetry + Prometheus
│   │   │   ├── trial_enforcement.py # Plan & quota gating
│   │   │   └── gemini_env.py        # API key bridge (env → rotator)
│   │   ├── models/                  # 27+ SQLAlchemy models
│   │   │   ├── document.py
│   │   │   ├── chat.py
│   │   │   ├── hr.py
│   │   │   ├── legal.py
│   │   │   ├── finance.py
│   │   │   ├── study.py
│   │   │   ├── research.py
│   │   │   ├── exam.py
│   │   │   └── ...
│   │   ├── services/                # 28 specialized service files
│   │   │   ├── llm_service.py       # Gemini provider + key rotation
│   │   │   ├── retrieval_service.py # Hybrid semantic + lexical retrieval
│   │   │   ├── grounding_service.py # Evidence selection + token budgeting
│   │   │   ├── veritas_engine.py    # Trust scoring (0-100)
│   │   │   ├── ocr_orchestrator.py  # PaddleOCR + Docling routing
│   │   │   ├── embedding_service.py # BAAI/bge-m3 embeddings
│   │   │   ├── deep_research_agent.py # RAG + Tavily web synthesis
│   │   │   ├── export_engine.py     # DOCX generation
│   │   │   ├── proactive_insights.py # Auto-surfaced findings
│   │   │   ├── financial_table_extractor.py
│   │   │   └── ...
│   │   ├── workers/
│   │   │   ├── celery_app.py        # Celery app + beat scheduler
│   │   │   └── tasks/               # 11 task modules
│   │   │       ├── document_tasks.py
│   │   │       ├── hr_tasks.py
│   │   │       ├── legal_tasks.py
│   │   │       └── ...
│   │   └── automation/              # 7 scheduled jobs (Celery Beat)
│   │       ├── auto_health_check.py
│   │       ├── auto_daily_digest.py
│   │       ├── auto_db_cleanup.py
│   │       └── ...
│   ├── alembic/                     # DB migration scripts
│   └── requirements.txt
│
├── frontend/                        # Next.js 16 application
│   └── src/
│       ├── app/                     # App Router pages (24 routes)
│       │   ├── (marketing)/         # Landing, pricing, privacy, terms
│       │   ├── login/
│       │   ├── register/
│       │   ├── general/             # General workspace
│       │   ├── hr/                  # HR workspace
│       │   ├── legal/               # Legal workspace
│       │   ├── finance/             # Finance workspace
│       │   ├── study/               # Study workspace
│       │   ├── research/            # Research workspace
│       │   ├── exam/                # Exam/Teacher workspace
│       │   ├── admin/               # Admin panel
│       │   └── ...
│       ├── components/              # 38+ reusable components
│       │   ├── WorkspaceUI.tsx      # Core chat + document UI (110 KB)
│       │   ├── Sidebar.tsx          # Navigation + chat history (41 KB)
│       │   ├── PaperConfigPanel.tsx # Exam builder (33 KB)
│       │   ├── CandidateRankingsPanel.tsx
│       │   ├── LegalRiskPanel.tsx
│       │   ├── FinanceRatioPanel.tsx
│       │   ├── VeritasTrustScore/   # Trust score display
│       │   └── ...
│       └── lib/
│           ├── api.ts               # All frontend API calls (~40 KB)
│           ├── pricing.ts           # Plan definitions (single source of truth)
│           └── store/               # State management
│
└── infrastructure/
    ├── docker-compose.yml           # Full dev stack (6 services)
    ├── Dockerfile.backend
    └── Dockerfile.frontend
```

---

## 🔑 Key Design Decisions

### Zero-Hallucination Architecture
The entire pipeline — from retrieval to grounding to the system prompt — is designed to prevent fabricated responses. When the evidence doesn't support an answer, the system explicitly says so. The Veritas Engine adds a quantified trust score to every response.

### Hybrid Retrieval with RRF
Rather than relying on a single retrieval strategy, DocuMindAI combines vector similarity search (semantic meaning) and full-text BM25 search (keyword matching), then fuses them using **Reciprocal Rank Fusion** — a research-proven technique that outperforms either method alone.

### Multi-Key Gemini Rotation
A production-grade key rotation system (`GeminiKeyRotator`) manages multiple Gemini API keys with cooldowns per key, automatic failover, and permanent invalidation — ensuring high availability even when individual keys hit quota.

### Domain-Specific Retrieval Tuning
Each workspace has independently tuned retrieval parameters:

| Workspace | top_k | rerank_n | Chunk Preference |
|-----------|-------|----------|-----------------|
| HR | 18 | 12 | Small (fine-grained CV parsing) |
| Research | 16 | 10 | Large (preserve context) |
| Finance | 14 | 8 | Small (precise figures) |
| General / Study / Exam | 12 | 8 | Medium |
| Legal | 10 | 6 | Large (preserve clause context) |

---

## 🗺️ Roadmap

### ✅ Completed
- [x] 7 specialized workspaces with dedicated AI pipelines
- [x] Hybrid retrieval (semantic + lexical + RRF)
- [x] Veritas Trust Engine (5-factor scoring)
- [x] Multi-engine OCR (PaddleOCR + Docling)
- [x] Gemini multi-key rotation with automatic failover
- [x] Real-time SSE streaming
- [x] Proactive insights (auto-surfaced on upload)
- [x] Export engine (DOCX — legal redlines, exam papers, literature reviews)
- [x] JWT + CSRF + rate limiting security stack
- [x] OpenTelemetry + Prometheus + Sentry observability
- [x] Docker Compose + GitHub Actions CI/CD
- [x] Deep Research Agent (RAG + Tavily web synthesis)
- [x] SM-2 spaced repetition (Study workspace)
- [x] Exam paper generation with Bloom's taxonomy tagging

### 🔄 In Progress
- [ ] Real Razorpay/Stripe payment webhook integration
- [ ] Per-plan quota enforcement (Go / Plus / Pro feature gating)
- [ ] Rate limiting on `/query/stream` and `/documents/upload`
- [ ] `ChatMessage.mode` column (persist grounded/ungrounded state to history)

### 📋 Planned
- [ ] Migrate to `google-genai` SDK (next-gen Gemini integration)
- [ ] OTLP exporter for production tracing (Jaeger / Tempo / Datadog)
- [ ] Exam workspace Phase 2: Teacher image upload + inline positioning
- [ ] Exam workspace Phase 3: AI-generated diagram insertion (Gemini Imagen)
- [ ] Mobile PWA improvements (offline support, push notifications)
- [ ] Multi-language support (Hindi, Tamil, regional Indian languages)
- [ ] Organization-level multi-user collaboration
- [ ] Audit trail export for compliance workflows

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — LLM backbone
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR for complex documents
- [Docling](https://github.com/DS4SD/docling) — Structured document extraction
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) — Multilingual embedding model
- [pgvector](https://github.com/pgvector/pgvector) — Vector similarity in PostgreSQL
- [Tavily](https://tavily.com/) — Web research API for Deep Research Agent

---

<div align="center">

**Built with care for professionals who work with documents every day.**

[⬆ Back to top](#-documindai)

</div>
