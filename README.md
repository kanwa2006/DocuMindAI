<div align="center">

# ≡ƒºá DocuMindAI

**Enterprise-grade AI document intelligence ΓÇö grounded, cited, trusted.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL+pgvector-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery)](https://docs.celeryq.dev/)
[![CI](https://img.shields.io/github/actions/workflow/status/kanwa2006/DocuMindAI/ci.yml?label=CI)](https://github.com/kanwa2006/DocuMindAI/actions)

[Features](#-features) ┬╖ [Workspaces](#-seven-specialized-workspaces) ┬╖ [Architecture](#-architecture) ┬╖ [Tech Stack](#-tech-stack) ┬╖ [Installation](#-installation) ┬╖ [Project Structure](#-project-structure) ┬╖ [Roadmap](#-roadmap)

</div>

---

## ≡ƒôî What is DocuMindAI?

DocuMindAI is a **full-stack AI document intelligence platform** built around a strict **zero-hallucination policy**. Upload your documents ΓÇö contracts, financial statements, research papers, resumes, or textbooks ΓÇö and get AI-powered answers that are always **grounded in your content**, **cited to the source page**, and **scored for trustworthiness** before they reach you.

This is not a general-purpose AI chatbot. Every answer produced by DocuMindAI traces back to a specific document, a specific page, and a specific chunk of text. The system refuses to fabricate responses when evidence is absent.

> *"I cannot answer this based on the provided documents."* ΓÇö what DocuMindAI says instead of guessing.

---

## Γ£¿ Features

- ≡ƒöì **Hybrid Retrieval** ΓÇö Semantic (pgvector cosine) + Lexical (BM25 tsvector) search fused via **Reciprocal Rank Fusion (RRF)**
- ≡ƒñû **Gemini LLM** ΓÇö Multi-key rotation with automatic failover, rate-limit cooldowns, and safe streaming
- ≡ƒôä **Multi-engine OCR** ΓÇö PaddleOCR (handwritten/rotated) + Docling (structured/tabular) with validation gateway
- ≡ƒ¢í∩╕Å **Veritas Trust Engine** ΓÇö Post-generation trust scoring (0ΓÇô100) across 5 weighted factors
- ≡ƒÆí **Proactive Insights** ΓÇö AI surfaces critical findings automatically on upload (no query needed)
- ≡ƒÅó **7 Specialized Workspaces** ΓÇö Each workspace has tailored retrieval configs, domain models, and dedicated workers
- ≡ƒôñ **Export Engine** ΓÇö Generate formatted DOCX reports (legal redlines, exam papers, literature reviews)
- ≡ƒöä **Real-time Streaming** ΓÇö Server-Sent Events (SSE) for live answer streaming
- ≡ƒöÉ **Enterprise Security** ΓÇö JWT + CSRF + rate limiting + HSTS + device fingerprinting
- ≡ƒôè **Full Observability** ΓÇö OpenTelemetry distributed tracing + Prometheus metrics + Sentry + PostHog
- ≡ƒÆ│ **India-first Billing** ΓÇö Razorpay-ready with Go / Plus / Pro tiers (Γé╣799 / Γé╣999 / Γé╣2,999)
- Γÿü∩╕Å **Flexible Deployment** ΓÇö Docker Compose (dev) + Railway (prod) + GitHub Actions CI/CD

---

## ≡ƒùé∩╕Å Seven Specialized Workspaces

Each workspace is a fully independent environment with its own database models, API routes, Celery workers, retrieval configuration, and proactive insight prompts.

| Workspace | Icon | Purpose |
|-----------|------|---------|
| **General** | ≡ƒÆ¼ | Universal document Q&A ΓÇö upload anything, ask anything |
| **HR** | ≡ƒæÑ | Resume screening, candidate auto-ranking, interview pipeline tracking |
| **Legal** | ΓÜû∩╕Å | Contract review, clause risk flagging, redline DOCX export |
| **Finance** | ≡ƒôê | Financial statement analysis, ratio extraction, anomaly detection |
| **Study** | ≡ƒôÜ | Flashcard generation (SM-2 spaced repetition), Pomodoro timer, quizzes |
| **Research** | ≡ƒö¼ | Literature synthesis, contradiction detection, Deep Research Agent (RAG + Tavily web) |
| **Exam / Teacher** | ≡ƒÄô | Auto-generate exam papers with MCQ/Short/Long/Case Study sections, answer keys, DOCX export |

---

## ≡ƒÅù∩╕Å Architecture

```
ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
Γöé                    Next.js 16 (App Router)                      Γöé
Γöé   /login  /hr  /legal  /finance  /study  /research  /exam  ...  Γöé
Γöé   WorkspaceUI ┬╖ Sidebar ┬╖ CommandPalette ┬╖ ProactiveInsights     Γöé
ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
                        Γöé REST + SSE
ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓû╝ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
Γöé                  FastAPI  /api/v1/                               Γöé
Γöé  auth ┬╖ documents ┬╖ query ┬╖ hr ┬╖ legal ┬╖ finance ┬╖ study        Γöé
Γöé  research ┬╖ exams ┬╖ export ┬╖ billing ┬╖ bookmarks ┬╖ admin  ...   Γöé
Γöé  Middleware: CORS ┬╖ CSRF ┬╖ RateLimit ┬╖ TenantContext ┬╖ OTel      Γöé
ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
           Γöé                           Γöé
ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓû╝ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ   ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓû╝ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
Γöé   AI / RAG Pipeline  Γöé   Γöé           Celery Workers                Γöé
Γöé                      Γöé   Γöé                                         Γöé
Γöé  1. OCR Orchestrator Γöé   Γöé  document_tasks  hr_tasks  legal_tasks  Γöé
Γöé     Γö£ Docling        Γöé   Γöé  finance_tasks   study_tasks            Γöé
Γöé     Γöö PaddleOCR      Γöé   Γöé  research_tasks  export_tasks           Γöé
Γöé                      Γöé   Γöé                                         Γöé
Γöé  2. Embedding        Γöé   Γöé  Celery Beat Automation:                Γöé
Γöé     Γöö BAAI/bge-m3    Γöé   Γöé  auto_health_check ┬╖ auto_daily_digest  Γöé
Γöé                      Γöé   Γöé  auto_db_cleanup ┬╖ auto_key_rotation    Γöé
Γöé  3. Hybrid Retrieval Γöé   ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γöé     Γö£ pgvector       Γöé
Γöé     Γö£ tsvector BM25  Γöé   ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
Γöé     Γöö RRF Fusion     Γöé   Γöé          Data Layer                     Γöé
Γöé                      Γöé   Γöé                                         Γöé
Γöé  4. Reranker         Γöé   Γöé  PostgreSQL 16 + pgvector               Γöé
Γöé                      Γöé   Γöé  PgBouncer (1000 conn, transaction mode)Γöé
Γöé  5. Grounding        Γöé   Γöé  Redis 7 (broker + cache + sessions)    Γöé
Γöé     Γöö Token Budget   Γöé   Γöé  Local Storage / S3 / Supabase          Γöé
Γöé                      Γöé   ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γöé  6. Gemini LLM       Γöé
Γöé     Γöö Key Rotation   Γöé
Γöé                      Γöé
Γöé  7. Veritas Engine   Γöé
Γöé     Γöö Trust Score    Γöé
ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
```

### Core Pipeline Flow

```
User Query
    Γöé
    Γû╝
Hybrid Retrieval (Semantic + Lexical ΓåÆ RRF)
    Γöé
    Γû╝
Reranker (Cross-encoder scoring)
    Γöé
    Γû╝
Grounding Service (Token budget ┬╖ Citation formatting ┬╖ Document-order sort)
    Γöé
    Γû╝
Gemini LLM (Multi-key rotation ┬╖ Safe streaming ┬╖ JSON repair loop)
    Γöé
    Γû╝
Veritas Trust Engine (0-100 score ┬╖ 5 weighted factors)
    Γöé
    Γû╝
SSE Stream ΓåÆ Frontend
```

---

## ≡ƒ¢á∩╕Å Tech Stack

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
| FastAPI | ΓëÑ0.109 | Async REST API |
| Pydantic | ΓëÑ2.5 | Validation & settings |
| SQLAlchemy | ΓëÑ2.0 | Async ORM |
| Alembic | ΓëÑ1.13 | DB migrations |
| Celery | ΓëÑ5.3.6 | Distributed task queue |
| PaddleOCR | ΓëÑ2.7.0 | Handwritten/scanned OCR |
| Docling | ΓëÑ1.1.0 | Structured document extraction |
| PyMuPDF | ΓëÑ1.23.8 | Native PDF text extraction |
| sentence-transformers | ΓëÑ2.7.0 | Embeddings (BAAI/bge-m3) |
| pgvector | ΓëÑ0.2.5 | Vector similarity in Postgres |
| google-generativeai | latest | Gemini LLM integration |
| python-docx | ΓëÑ1.1.0 | DOCX export generation |
| slowapi | ΓëÑ0.1.9 | API rate limiting |
| OpenTelemetry | ΓëÑ1.20 | Distributed tracing |
| Razorpay | ΓëÑ1.4.1 | Payment integration |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 + pgvector |
| Connection Pool | PgBouncer (transaction mode) |
| Cache / Broker | Redis 7 |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Hosting | Railway (production) |
| Monitoring | Sentry ┬╖ OpenTelemetry ┬╖ Prometheus |

---

## ≡ƒô╕ Screenshots

> Screenshots below show the platform in action across different workspaces.

### General Workspace ΓÇö Grounded Q&A with Citations
```
[ Screenshot placeholder: /general workspace with a PDF uploaded,
  user question, and a streamed answer with inline page citations
  and Veritas trust score badge ]
```

### HR Workspace ΓÇö Candidate Rankings Panel
```
[ Screenshot placeholder: /hr workspace showing ranked candidates,
  job-description match scores, pipeline status columns ]
```

### Legal Workspace ΓÇö Contract Risk Analysis
```
[ Screenshot placeholder: /legal workspace showing clause-by-clause
  risk levels (HIGH/MEDIUM/LOW), with redline export button ]
```

### Finance Workspace ΓÇö Ratio Dashboard
```
[ Screenshot placeholder: /finance workspace with ratio charts,
  year-on-year trend graphs, and anomaly flagging ]
```

### Exam Workspace ΓÇö Paper Generation
```
[ Screenshot placeholder: /exam workspace with PaperConfigPanel
  showing sections, question types, auto-generated Q&A, DOCX export ]
```

---

## ≡ƒÜÇ Installation

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

# Database (local Docker default ΓÇö no changes needed for dev)
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

## ΓÜÖ∩╕Å Environment Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY_1` | Γ£à | Primary Gemini API key. Add `_2`, `_3`... for rotation |
| `AUTH_SECRET_KEY` | Γ£à | 64-char JWT signing secret |
| `CSRF_SECRET_KEY` | Γ£à | CSRF token secret |
| `POSTGRES_SERVER` | Γ£à | Database host |
| `REDIS_URL` | Γ£à | Redis connection string |
| `STORAGE_PROVIDER` | ΓÇö | `local` (default) or `s3` |
| `VECTOR_BACKEND` | ΓÇö | `faiss` (default), `pgvector`, or `qdrant` |
| `SENTRY_DSN` | ΓÇö | Error monitoring (optional) |
| `RAZORPAY_KEY_ID` | ΓÇö | Payment integration (optional) |
| `SMTP_PASSWORD` | ΓÇö | SendGrid API key for email OTP |

See [`.env.example`](.env.example) for the full reference.

---

## ≡ƒôü Project Structure

```
DocuMindAI/
Γö£ΓöÇΓöÇ backend/                         # FastAPI application
Γöé   Γö£ΓöÇΓöÇ app/
Γöé   Γöé   Γö£ΓöÇΓöÇ api/v1/
Γöé   Γöé   Γöé   ΓööΓöÇΓöÇ endpoints/           # 26 route modules
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ auth.py          # Register, login, verify, refresh
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ query.py         # Streaming Q&A (SSE)
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ documents.py     # Upload, process, serve
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ hr.py            # Candidate ranking, pipeline
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ legal.py         # Contract analysis, redlines
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ finance.py       # Ratio extraction, audit
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ study.py         # Flashcards, SM-2, quizzes
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ research.py      # Literature synthesis
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ exams.py         # Exam paper generation
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ export.py        # DOCX/PDF export
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ billing.py       # Plans, trial enforcement
Γöé   Γöé   Γöé       ΓööΓöÇΓöÇ ...              # + 14 more modules
Γöé   Γöé   Γö£ΓöÇΓöÇ core/
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ config.py            # Pydantic settings (all env vars)
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ security.py          # JWT helpers
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ middleware.py        # CSRF ┬╖ Tenant ┬╖ Fingerprint
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ telemetry.py         # OpenTelemetry + Prometheus
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ trial_enforcement.py # Plan & quota gating
Γöé   Γöé   Γöé   ΓööΓöÇΓöÇ gemini_env.py        # API key bridge (env ΓåÆ rotator)
Γöé   Γöé   Γö£ΓöÇΓöÇ models/                  # 27+ SQLAlchemy models
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ document.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ chat.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ hr.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ legal.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ finance.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ study.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ research.py
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ exam.py
Γöé   Γöé   Γöé   ΓööΓöÇΓöÇ ...
Γöé   Γöé   Γö£ΓöÇΓöÇ services/                # 28 specialized service files
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ llm_service.py       # Gemini provider + key rotation
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ retrieval_service.py # Hybrid semantic + lexical retrieval
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ grounding_service.py # Evidence selection + token budgeting
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ veritas_engine.py    # Trust scoring (0-100)
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ ocr_orchestrator.py  # PaddleOCR + Docling routing
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ embedding_service.py # BAAI/bge-m3 embeddings
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ deep_research_agent.py # RAG + Tavily web synthesis
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ export_engine.py     # DOCX generation
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ proactive_insights.py # Auto-surfaced findings
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ financial_table_extractor.py
Γöé   Γöé   Γöé   ΓööΓöÇΓöÇ ...
Γöé   Γöé   Γö£ΓöÇΓöÇ workers/
Γöé   Γöé   Γöé   Γö£ΓöÇΓöÇ celery_app.py        # Celery app + beat scheduler
Γöé   Γöé   Γöé   ΓööΓöÇΓöÇ tasks/               # 11 task modules
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ document_tasks.py
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ hr_tasks.py
Γöé   Γöé   Γöé       Γö£ΓöÇΓöÇ legal_tasks.py
Γöé   Γöé   Γöé       ΓööΓöÇΓöÇ ...
Γöé   Γöé   ΓööΓöÇΓöÇ automation/              # 7 scheduled jobs (Celery Beat)
Γöé   Γöé       Γö£ΓöÇΓöÇ auto_health_check.py
Γöé   Γöé       Γö£ΓöÇΓöÇ auto_daily_digest.py
Γöé   Γöé       Γö£ΓöÇΓöÇ auto_db_cleanup.py
Γöé   Γöé       ΓööΓöÇΓöÇ ...
Γöé   Γö£ΓöÇΓöÇ alembic/                     # DB migration scripts
Γöé   ΓööΓöÇΓöÇ requirements.txt
Γöé
Γö£ΓöÇΓöÇ frontend/                        # Next.js 16 application
Γöé   ΓööΓöÇΓöÇ src/
Γöé       Γö£ΓöÇΓöÇ app/                     # App Router pages (24 routes)
Γöé       Γöé   Γö£ΓöÇΓöÇ (marketing)/         # Landing, pricing, privacy, terms
Γöé       Γöé   Γö£ΓöÇΓöÇ login/
Γöé       Γöé   Γö£ΓöÇΓöÇ register/
Γöé       Γöé   Γö£ΓöÇΓöÇ general/             # General workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ hr/                  # HR workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ legal/               # Legal workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ finance/             # Finance workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ study/               # Study workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ research/            # Research workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ exam/                # Exam/Teacher workspace
Γöé       Γöé   Γö£ΓöÇΓöÇ admin/               # Admin panel
Γöé       Γöé   ΓööΓöÇΓöÇ ...
Γöé       Γö£ΓöÇΓöÇ components/              # 38+ reusable components
Γöé       Γöé   Γö£ΓöÇΓöÇ WorkspaceUI.tsx      # Core chat + document UI (110 KB)
Γöé       Γöé   Γö£ΓöÇΓöÇ Sidebar.tsx          # Navigation + chat history (41 KB)
Γöé       Γöé   Γö£ΓöÇΓöÇ PaperConfigPanel.tsx # Exam builder (33 KB)
Γöé       Γöé   Γö£ΓöÇΓöÇ CandidateRankingsPanel.tsx
Γöé       Γöé   Γö£ΓöÇΓöÇ LegalRiskPanel.tsx
Γöé       Γöé   Γö£ΓöÇΓöÇ FinanceRatioPanel.tsx
Γöé       Γöé   Γö£ΓöÇΓöÇ VeritasTrustScore/   # Trust score display
Γöé       Γöé   ΓööΓöÇΓöÇ ...
Γöé       ΓööΓöÇΓöÇ lib/
Γöé           Γö£ΓöÇΓöÇ api.ts               # All frontend API calls (~40 KB)
Γöé           Γö£ΓöÇΓöÇ pricing.ts           # Plan definitions (single source of truth)
Γöé           ΓööΓöÇΓöÇ store/               # State management
Γöé
ΓööΓöÇΓöÇ infrastructure/
    Γö£ΓöÇΓöÇ docker-compose.yml           # Full dev stack (6 services)
    Γö£ΓöÇΓöÇ Dockerfile.backend
    ΓööΓöÇΓöÇ Dockerfile.frontend
```

---

## ≡ƒöæ Key Design Decisions

### Zero-Hallucination Architecture
The entire pipeline ΓÇö from retrieval to grounding to the system prompt ΓÇö is designed to prevent fabricated responses. When the evidence doesn't support an answer, the system explicitly says so. The Veritas Engine adds a quantified trust score to every response.

### Hybrid Retrieval with RRF
Rather than relying on a single retrieval strategy, DocuMindAI combines vector similarity search (semantic meaning) and full-text BM25 search (keyword matching), then fuses them using **Reciprocal Rank Fusion** ΓÇö a research-proven technique that outperforms either method alone.

### Multi-Key Gemini Rotation
A production-grade key rotation system (`GeminiKeyRotator`) manages multiple Gemini API keys with cooldowns per key, automatic failover, and permanent invalidation ΓÇö ensuring high availability even when individual keys hit quota.

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

## ≡ƒù║∩╕Å Roadmap

### Γ£à Completed
- [x] 7 specialized workspaces with dedicated AI pipelines
- [x] Hybrid retrieval (semantic + lexical + RRF)
- [x] Veritas Trust Engine (5-factor scoring)
- [x] Multi-engine OCR (PaddleOCR + Docling)
- [x] Gemini multi-key rotation with automatic failover
- [x] Real-time SSE streaming
- [x] Proactive insights (auto-surfaced on upload)
- [x] Export engine (DOCX ΓÇö legal redlines, exam papers, literature reviews)
- [x] JWT + CSRF + rate limiting security stack
- [x] OpenTelemetry + Prometheus + Sentry observability
- [x] Docker Compose + GitHub Actions CI/CD
- [x] Deep Research Agent (RAG + Tavily web synthesis)
- [x] SM-2 spaced repetition (Study workspace)
- [x] Exam paper generation with Bloom's taxonomy tagging

### ≡ƒöä In Progress
- [ ] Real Razorpay/Stripe payment webhook integration
- [ ] Per-plan quota enforcement (Go / Plus / Pro feature gating)
- [ ] Rate limiting on `/query/stream` and `/documents/upload`
- [ ] `ChatMessage.mode` column (persist grounded/ungrounded state to history)

### ≡ƒôï Planned
- [ ] Migrate to `google-genai` SDK (next-gen Gemini integration)
- [ ] OTLP exporter for production tracing (Jaeger / Tempo / Datadog)
- [ ] Exam workspace Phase 2: Teacher image upload + inline positioning
- [ ] Exam workspace Phase 3: AI-generated diagram insertion (Gemini Imagen)
- [ ] Mobile PWA improvements (offline support, push notifications)
- [ ] Multi-language support (Hindi, Tamil, regional Indian languages)
- [ ] Organization-level multi-user collaboration
- [ ] Audit trail export for compliance workflows

---

## ≡ƒôä License

This project is licensed under the [MIT License](LICENSE).

---

## ≡ƒÖÅ Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) ΓÇö LLM backbone
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) ΓÇö OCR for complex documents
- [Docling](https://github.com/DS4SD/docling) ΓÇö Structured document extraction
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) ΓÇö Multilingual embedding model
- [pgvector](https://github.com/pgvector/pgvector) ΓÇö Vector similarity in PostgreSQL
- [Tavily](https://tavily.com/) ΓÇö Web research API for Deep Research Agent

---

<div align="center">

**Built with care for professionals who work with documents every day.**

[Γ¼å Back to top](#-documindai)

</div>
