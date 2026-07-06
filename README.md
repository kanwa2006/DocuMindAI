<div align="center">

# 🧠 DocuMindAI

**Enterprise-grade AI document intelligence — grounded, cited, trusted.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Contributing](https://img.shields.io/badge/Contributing-Guide-orange.svg)](CONTRIBUTING.md)
[![Security](https://img.shields.io/badge/Security-Policy-red.svg)](SECURITY.md)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL+pgvector-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io/)
[![CI](https://img.shields.io/github/actions/workflow/status/kanwa2006/DocuMindAI/ci.yml?label=CI)](https://github.com/kanwa2006/DocuMindAI/actions)

[Features](#-features) · [Workspaces](#-seven-specialized-workspaces) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Screenshots](#-screenshots) · [Quick Start](#-quick-start) · [Project Structure](#-project-structure) · [Roadmap](#-roadmap)

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
- 💳 **Multi-Tier Billing** — Razorpay-ready integration supporting custom plans
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
- **Next.js** (16.2.6) — App Router, SSR, Routing
- **React** (19.2.4) — UI Framework
- **TypeScript** (5.x) — Type Safety
- **Tailwind CSS** (4.x) — Utility-first styling
- **react-pdf** (10.4.1) — In-browser PDF rendering
- **recharts** (2.15.4) — Interactive analytics

### Backend
- **FastAPI** (≥0.109) — Async REST API server
- **SQLAlchemy** (≥2.0) — Async Python ORM
- **Alembic** (≥1.13) — Database migrations
- **Celery** (≥5.3.6) — Distributed task execution queue
- **PaddleOCR** & **Docling** — OCR and structural extraction
- **sentence-transformers** — Embedding (BAAI/bge-m3)
- **pgvector** — Similarity vector search database integration
- **google-generativeai** — Gemini LLM provider

---

## 📸 Screenshots

### Document Analysis & Grounded Q&A Interface
![DocuMindAI Dashboard Mockup](docs/screenshots/dashboard.png)

---

## 🚀 Quick Start

To spin up the entire application stack using Docker Compose:

### 1. Clone the Repository
```bash
git clone https://github.com/kanwa2006/DocuMindAI.git
cd DocuMindAI
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
*Open `.env` and fill in your `GEMINI_API_KEY_1` and random security keys.*

### 3. Run with Docker Compose
```bash
cd infrastructure
docker-compose up --build
```
The FastAPI backend will run at `http://localhost:8000` and the Next.js frontend will run at `http://localhost:3000`.

*For manual setups, dependencies, and test execution details, see the [Installation & Deployment Guide](docs/deployment/installation.md).*

---

## ⚙️ Environment Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY_1` | ✅ | Primary Gemini API key. Add `_2`, `_3`... for rotation |
| `AUTH_SECRET_KEY` | ✅ | 64-char JWT signing secret |
| `CSRF_SECRET_KEY` | ✅ | CSRF token secret |
| `POSTGRES_SERVER` | ✅ | Database host (local default: `localhost`) |
| `REDIS_URL` | ✅ | Redis connection string (local default: `redis://localhost:6380/0`) |

See [`.env.example`](.env.example) for the full list of configuration variables.

---

## 📁 Project Structure

```
DocuMindAI/
├── .github/                         # GitHub Action CI/CD workflows
├── backend/                         # FastAPI application source code
│   ├── app/                         # Backend API logic, routes, and services
│   ├── alembic/                     # Database migration scripts
│   └── requirements.txt             # Python packages listing
├── docs/                            # Documentation, assets, and project maps
│   ├── architecture/                # System architecture and API mapping
│   ├── deployment/                  # Deployment & setup documentation
│   └── screenshots/                 # Application screenshots and visuals
├── frontend/                        # Next.js 16 React client-side application
│   ├── src/                         # Page routes, components, and React hooks
│   └── package.json                 # Node package configuration
├── infrastructure/                  # Docker Compose & multi-service deployment configurations
├── .env.example                     # Environment setup template
├── .gitignore                       # Repository files filter
├── LICENSE                          # MIT License details
├── railway.json                     # Railway deployment specs
└── README.md                        # Main project documentation
```

---

## 🔑 Key Design Decisions

### Zero-Hallucination Architecture
The pipeline is designed to prevent hallucination by passing retrieved documents into Gemini within a strict token budget. If evidence is absent, the system refuses to answer. The Veritas Engine evaluates the result and assigns a 0-100 trust score based on structural alignment and direct citation references.

### Hybrid Retrieval & Retrieval Tuning
Vector similarity search (semantic matching) is fused with full-text search (BM25 keyword search) using Reciprocal Rank Fusion (RRF). Each workspace (HR, Legal, Finance, etc.) is configured with domain-specific retrieval parameters to optimize context lengths. The detailed hyperparameter mappings are documented under [docs/architecture/project-map.md](docs/architecture/project-map.md).

### Multi-Key Gemini Rotation
An automated key rotator handles failover, rate limits, and key cooldowns across multiple Gemini API keys, providing robust enterprise-ready uptime.

---

## 🗺️ Roadmap

### ✅ Completed
- 7 specialized workspaces (General, HR, Legal, Finance, Study, Research, Exam)
- Hybrid retrieval (pgvector + BM25 + RRF) and Veritas Trust Engine
- OCR pipeline (PaddleOCR + Docling) and Gemini key rotation
- Real-time Server-Sent Events (SSE) streaming answers
- PDF/DOCX report export engine
- OpenTelemetry, Prometheus, and Sentry observability integration

### 🔄 In Progress
- Quota enforcement gating based on pricing plans
- Rate-limiting rules on `/query/stream` and `/documents/upload`

### 📋 Planned
- Migration to the next-gen `google-genai` SDK
- Mobile PWA improvements & offline support
- Multi-language translation for regional Indian languages

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — LLM backbone
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) & [Docling](https://github.com/DS4SD/docling) — OCR & document layout parsing
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) & [pgvector](https://github.com/pgvector/pgvector) — Semantic embeddings and vector search
- [Tavily](https://tavily.com/) — Web research API for deep agent synthesis

---

<div align="center">

**Built with care for professionals who work with documents every day.**

[⬆ Back to top](#-documindai)

</div>
