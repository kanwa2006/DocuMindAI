<div align="center">

# 🧠 DocuMindAI

**Enterprise-grade AI document intelligence — grounded, cited, trusted.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL+pgvector-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![CI](https://img.shields.io/github/actions/workflow/status/kanwa2006/DocuMindAI/ci.yml?label=CI&logo=github-actions&logoColor=white)](https://github.com/kanwa2006/DocuMindAI/actions)

[Features](#-features) · [Workspaces](#️-seven-specialized-workspaces) · [Architecture](#️-architecture) · [Quick Start](#-quick-start) · [Tech Stack](#️-tech-stack) · [Screenshots](#-screenshots) · [Roadmap](#️-roadmap)

</div>

---

## 📌 What is DocuMindAI?

DocuMindAI is a **full-stack AI document intelligence platform** built around a strict **zero-hallucination policy**. Upload your documents — contracts, financial statements, research papers, resumes, or textbooks — and get AI-powered answers that are always **grounded in your content**, **cited to the source page**, and **scored for trustworthiness** before they reach you.

This is not a general-purpose AI chatbot. Every answer produced by DocuMindAI traces back to a specific document, a specific page, and a specific chunk of text. The system refuses to fabricate responses when evidence is absent.

> *"I cannot answer this based on the provided documents."* — what DocuMindAI says instead of guessing.

---

## 🚀 Demo

> **Note:** A hosted demo is not yet deployed. The entries below are placeholders for when a live instance becomes available.

| Resource | Link |
|----------|------|
| 🌐 **Live Demo** | `TODO: https://demo.documindai.com` |
| 📖 **API Docs (Swagger)** | `TODO: https://api.documindai.com/docs` |
| 🎬 **Demo Video** | `TODO: Link to walkthrough video` |

To run the application locally in under 5 minutes, see the [Quick Start](#-quick-start) section below.

---

## ✨ Features

- 🔍 **Hybrid Retrieval** — Semantic (pgvector cosine) + Lexical (BM25 tsvector) search fused via **Reciprocal Rank Fusion (RRF)**
- 🤖 **Gemini LLM** — Multi-key rotation with automatic failover, rate-limit cooldowns, and safe streaming
- 📄 **Multi-engine OCR** — PaddleOCR (handwritten/rotated) + Docling (structured/tabular) with validation gateway
- 🛡️ **Veritas Trust Engine** — Post-generation trust scoring (0–100) across 5 weighted factors
- 💡 **Proactive Insights** — AI surfaces critical findings automatically on upload (no query needed)
- 🏢 **7 Specialized Workspaces** — Each workspace has tailored retrieval configs, domain models, and dedicated Celery workers
- 📤 **Export Engine** — Generate formatted DOCX reports (legal redlines, exam papers, literature reviews)
- 🔄 **Real-time Streaming** — Server-Sent Events (SSE) for live answer streaming to the browser
- 🔐 **Enterprise Security** — JWT + CSRF + rate limiting + HSTS + device fingerprinting
- 📊 **Full Observability** — OpenTelemetry distributed tracing + Prometheus metrics + Sentry + PostHog
- 💳 **Multi-Tier Billing** — Razorpay-ready integration supporting Go, Plus, and Pro plans
- ☁️ **Flexible Deployment** — Docker Compose (local) + Railway (cloud) + GitHub Actions CI/CD

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
│                      │   │  PgBouncer (connection pooling)         │
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
Reranker (cross-encoder scoring)
    │
    ▼
Grounding Service (token budget · citation formatting · document-order sort)
    │
    ▼
Gemini LLM (multi-key rotation · safe streaming · JSON repair loop)
    │
    ▼
Veritas Trust Engine (0–100 score · 5 weighted factors)
    │
    ▼
SSE Stream → Frontend
```

---

## 🚀 Quick Start

Spin up the entire application stack with Docker Compose in three steps.

### 1. Clone the Repository

```bash
git clone https://github.com/kanwa2006/DocuMindAI.git
cd DocuMindAI
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your `GEMINI_API_KEY_1` and random security keys (see [Environment Reference](#-environment-reference) below).

### 3. Run with Docker Compose

```bash
cd infrastructure
docker-compose up --build
```

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **Swagger Docs** | http://localhost:8000/docs |

For step-by-step manual setup (without Docker), see the [Installation & Deployment Guide](docs/deployment/installation.md).

---

## ⚙️ Environment Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY_1` | ✅ | Primary Gemini API key — add `_2`, `_3`, ... for multi-key rotation |
| `AUTH_SECRET_KEY` | ✅ | 64-character JWT signing secret |
| `CSRF_SECRET_KEY` | ✅ | CSRF token signing secret |
| `POSTGRES_SERVER` | ✅ | Database host (`localhost` for local Docker) |
| `REDIS_URL` | ✅ | Redis connection string (`redis://localhost:6380/0` for local Docker) |

See [`.env.example`](.env.example) for the complete list of configuration variables.

---

## 🛠️ Tech Stack

### Frontend

| Technology | Version | Role |
|------------|---------|------|
| **Next.js** | 16.2.6 | App Router, SSR, routing |
| **React** | 19.2.4 | UI framework |
| **TypeScript** | 5.x | Static type safety |
| **Tailwind CSS** | 4.x | Utility-first styling |
| **react-pdf** | 10.4.1 | In-browser PDF rendering |
| **recharts** | 2.15.4 | Interactive analytics charts |

### Backend

| Technology | Version | Role |
|------------|---------|------|
| **FastAPI** | ≥0.109 | Async REST API server |
| **SQLAlchemy** | ≥2.0 | Async Python ORM |
| **Alembic** | ≥1.13 | Database migration management |
| **Celery** | ≥5.3.6 | Distributed task execution queue |
| **PaddleOCR** & **Docling** | latest | OCR and structural document parsing |
| **sentence-transformers** | latest | Embedding model (BAAI/bge-m3) |
| **pgvector** | 0.5+ | Vector similarity search |
| **google-generativeai** | latest | Gemini LLM provider |

### Infrastructure

| Technology | Role |
|------------|------|
| **PostgreSQL 16** | Primary relational + vector database |
| **PgBouncer** | Connection pooling (transaction mode) |
| **Redis 7** | Celery broker, cache, and session store |
| **Docker Compose** | Local multi-service orchestration |
| **Railway** | Cloud deployment platform |
| **GitHub Actions** | CI/CD (lint, type-check, build, migration tests) |

---

## 📸 Screenshots

### Document Analysis & Grounded Q&A Interface

> **Note:** The image below is an interface design mockup. A live screenshot will be added once a hosted demo is deployed.

![DocuMindAI Dashboard Interface Mockup](docs/screenshots/dashboard.png)

---

## 📁 Project Structure

```
DocuMindAI/
├── .github/                         # GitHub Actions CI/CD workflows
├── backend/                         # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/        # REST API route handlers
│   │   ├── core/                    # Auth, config, security, storage
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/                # Business logic (RAG, OCR, grounding, Veritas)
│   │   ├── workers/tasks/           # Celery task definitions per workspace
│   │   └── automation/              # Celery Beat scheduled tasks
│   ├── alembic/                     # Database migration scripts
│   ├── tests/                       # API contract & regression tests
│   └── requirements.txt             # Python package dependencies
├── docs/
│   ├── architecture/                # System architecture & API mapping
│   ├── deployment/                  # Installation & deployment guide
│   └── screenshots/                 # Application screenshots
├── frontend/                        # Next.js 16 React application
│   ├── src/app/                     # App Router pages (per workspace)
│   ├── src/components/              # Reusable UI components
│   ├── src/hooks/                   # Custom React hooks
│   └── src/lib/                     # API client, stores, analytics
├── infrastructure/                  # Docker Compose & deployment configs
├── .env.example                     # Environment variable template
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE                          # MIT License
├── SECURITY.md
├── railway.json                     # Railway cloud deployment config
└── README.md
```

---

## 🔑 Key Design Decisions

### Zero-Hallucination Architecture

The RAG pipeline prevents hallucination by injecting retrieved document chunks into Gemini within a strict token budget. If no relevant evidence is found, the system explicitly refuses to answer rather than generating a plausible-sounding response. The Veritas Engine then evaluates each answer and assigns a 0–100 trust score based on structural alignment, citation density, and hedging behavior.

### Hybrid Retrieval & Per-Workspace Tuning

Vector similarity search (semantic) is combined with PostgreSQL full-text search (BM25/tsvector) and fused using Reciprocal Rank Fusion (RRF). Each of the 7 workspaces has independently configured retrieval parameters (chunk size, top-k, RRF weights) optimized for its domain. Details are in [docs/architecture/project-map.md](docs/architecture/project-map.md).

### Multi-Key Gemini Rotation

The `llm_key_rotation` service distributes requests across multiple Gemini API keys, tracks per-key rate-limit state, and applies exponential-backoff cooldowns — enabling continuous availability under heavy load without manual key management.

---

## 🗺️ Roadmap

### ✅ Completed

- 7 specialized workspaces (General, HR, Legal, Finance, Study, Research, Exam)
- Hybrid retrieval (pgvector + BM25 + RRF) and Veritas Trust Engine
- OCR pipeline (PaddleOCR + Docling) and Gemini multi-key rotation
- Real-time Server-Sent Events (SSE) streaming
- PDF/DOCX report export engine
- OpenTelemetry, Prometheus, and Sentry observability
- CI/CD pipeline via GitHub Actions

### 🔄 In Progress

- Quota enforcement gating by pricing plan
- Rate-limiting rules on `/query/stream` and `/documents/upload`

### 📋 Planned

- Migration to the next-gen `google-genai` SDK
- Mobile PWA improvements & offline support
- Multi-language support for regional Indian languages
- Hosted public demo deployment

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit conventions, development setup, and pull request guidelines.

---

## 🔒 Security

To report a security vulnerability, please follow the [Security Policy](SECURITY.md). **Do not open public GitHub issues for security concerns.**

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — LLM backbone
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) & [Docling](https://github.com/DS4SD/docling) — OCR & document layout parsing
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) & [pgvector](https://github.com/pgvector/pgvector) — Semantic embeddings and vector search
- [Tavily](https://tavily.com/) — Web research API for the Deep Research Agent

---

<div align="center">

**Built with care for professionals who work with documents every day.**

[⬆ Back to top](#-documindai)

</div>
