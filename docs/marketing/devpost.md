# Devpost Submission — DocuMindAI

---

## Short Description (≤200 characters)

> AI document intelligence platform with grounded answers, page citations, a trust score on every response, and 7 specialized workspaces. Zero hallucination by architecture.

*(168 characters)*

---

## Medium Description (≤500 characters)

> DocuMindAI is a full-stack AI document intelligence platform built around a strict zero-hallucination policy. Upload contracts, research papers, resumes, or financial statements and get answers grounded in your content, cited to the exact source page, and scored with a Veritas Trust Engine (0–100). Seven specialized workspaces — General, HR, Legal, Finance, Study, Research, and Exam — each with domain-tuned retrieval and dedicated AI workers.

*(449 characters)*

---

## Inspiration

We noticed a consistent problem among knowledge workers: they couldn't trust AI-generated answers about their own documents. Generic AI assistants blend document content with training-data knowledge, producing confident answers that often contain fabricated details. Lawyers couldn't stake their judgment on an uncited AI response. Analysts couldn't rely on financial summaries that might have mixed their data with something else.

The existing RAG (Retrieval-Augmented Generation) pattern helps, but most implementations don't enforce grounding — the LLM still draws on its parametric knowledge when context is weak. And none of them provide a transparent, auditable trust score that users can actually act on.

We wanted to build something that professionals could genuinely trust for high-stakes document work: not a general chatbot, but a purpose-built intelligence layer for documents.

---

## What It Does

DocuMindAI is an AI document intelligence platform with a strict zero-hallucination policy.

Users upload documents — PDFs, DOCX files, scanned images — into one of seven specialized workspaces:

- **General** — universal document Q&A
- **HR** — resume screening, candidate ranking, interview pipeline
- **Legal** — contract review, clause risk flagging, redline export
- **Finance** — financial ratio extraction, anomaly detection, audit findings
- **Study** — SM-2 spaced-repetition flashcards, Pomodoro timer, quizzes
- **Research** — literature synthesis, contradiction detection, web-augmented Deep Research Agent
- **Exam** — grounded exam paper generation with MCQ, short, long, and case study formats

Every answer is:
1. Retrieved from the document using **Hybrid RAG** (pgvector semantic + BM25 tsvector, fused via Reciprocal Rank Fusion)
2. Grounded strictly within the retrieved evidence — the LLM cannot draw on external knowledge
3. Cited to the specific page and passage it draws from
4. Scored 0–100 by the **Veritas Trust Engine** (citation density, source alignment, hedging detection) before delivery
5. Streamed token-by-token to the browser via Server-Sent Events

If no evidence supports the query, the system explicitly refuses to answer.

---

## How We Built It

**Backend:** FastAPI (async) with SQLAlchemy v2 (async ORM), Alembic (migrations), and Celery (distributed task queue) backed by Redis.

**AI Pipeline:**
- PaddleOCR + Docling for multi-engine OCR with a validation gateway
- BAAI/bge-m3 sentence-transformers (1024-dim) for embeddings
- pgvector for vector similarity search in PostgreSQL
- PostgreSQL tsvector for BM25 lexical search
- Reciprocal Rank Fusion to merge both ranked lists
- Cross-encoder reranking pass
- Grounding Service with strict token budget enforcement
- Google Gemini for generation (multi-key rotation with per-key cooldown)
- Veritas Trust Engine for post-generation scoring

**Frontend:** Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 4. Server-Sent Events consumer for live streaming. One dedicated page per workspace.

**Infrastructure:** Docker Compose (6 containers), PgBouncer for connection pooling, Redis for Celery broker and cache, GitHub Actions CI (dep audit, migration tests, API contracts, lint, build), Railway for cloud deployment.

**Observability:** OpenTelemetry distributed tracing, Prometheus metrics, Sentry error tracking, PostHog product analytics.

---

## Challenges

**1. Enforcing zero hallucination architecturally**
The challenge wasn't prompting the LLM to "not hallucinate" — it was making hallucination structurally impossible. We had to design the grounding service to enforce a strict token budget and prevent any knowledge bleed from the LLM's parametric memory. This required carefully constructed system prompts, output validation, and a JSON repair loop for structured responses.

**2. Hybrid retrieval across 7 different domains**
Semantic search and keyword search have different strengths. The challenge was fusing them via Reciprocal Rank Fusion without score normalization artifacts, and then independently tuning chunk sizes, top-k values, and RRF weights for each domain's document types and query patterns.

**3. Async OCR inside Celery workers**
PaddleOCR and Docling both use synchronous I/O, but our Celery tasks needed to run them inside async event loops. We had to isolate a dedicated event loop per Celery worker task to prevent runtime conflicts.

**4. Branches with unrelated Git histories**
The development branch and the main branch had diverged into completely separate histories (no common ancestor). Merging required `--allow-unrelated-histories`, careful conflict resolution across hundreds of files, and cherry-picking specific critical bug-fix commits without losing either branch's history.

**5. SlowAPI parameter constraint**
SlowAPI's rate limiter requires a function argument named exactly `request` (not `http_request`). This caused a cryptic startup crash that took careful debugging to trace.

---

## Accomplishments

- Built a complete zero-hallucination RAG architecture that refuses to answer when evidence is absent — this required engineering choices at every layer, not just prompting
- Shipped seven specialized, independent workspaces each with its own database schema, API namespace, Celery workers, and retrieval configuration
- Designed and implemented the Veritas Trust Engine — a five-factor post-generation scoring system that gives users a quantified confidence score on every answer
- Built a hybrid retrieval system that outperforms semantic-only RAG by combining pgvector and BM25 with Reciprocal Rank Fusion, without requiring score normalization
- Integrated OpenTelemetry distributed tracing, Prometheus metrics, Sentry, and PostHog into a cohesive observability stack
- Shipped full-stack streaming: async generator through FastAPI, SSE to the Next.js browser client, with live token-by-token rendering
- Resolved a complex multi-branch Git history merger preserving 75+ commits of application work alongside repository hygiene commits

---

## What We Learned

**Architecture-first thinking:** The biggest lesson was that correctness guarantees must be designed at the architecture level, not enforced through prompts or configuration. Zero hallucination only works if the data pathway to the LLM is structurally restricted — not just requested.

**Domain specialization pays off:** Building seven workspace-specific configurations rather than a generic one-size-fits-all system significantly improved answer quality per domain. Legal queries need different chunk sizes and retrieval depth than Study flashcard generation.

**Async from the start:** Starting with async I/O (asyncpg, async SQLAlchemy) throughout the backend paid dividends in responsiveness. Retrofit-async would have been significantly harder.

**Hybrid > semantic-only:** Reciprocal Rank Fusion is surprisingly robust. The combination of BM25 keyword matching and cosine semantic matching captures complementary query patterns. Users who searched for specific clause numbers (keyword match) and users who searched semantically both benefited.

---

## What's Next

- **Hosted public demo** — the highest priority; running locally with Docker requires technical setup
- **API prefix normalization** — ~35 frontend call sites have a doubled `/api/v1` prefix that creates routing inconsistency
- **Workspace ID unification** — `User.workspace_id` (string slug) and `ChatSession.workspace_id` (UUID) need to be reconciled via a `uuid.uuid5` deterministic resolver
- **Migration to `google-genai` SDK** — the next-gen Gemini client with improved streaming and function calling
- **Quota enforcement** — Go/Plus/Pro tier gating is scaffolded but not yet enforced
- **Mobile PWA** — improved offline support and caching
- **Multi-language** — support for regional Indian languages in OCR and retrieval

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Frontend** | Next.js 16, React 19, TypeScript 5, Tailwind CSS 4 |
| **Backend** | FastAPI, SQLAlchemy 2.0, Alembic, Celery 5.3, SlowAPI |
| **AI / ML** | Google Gemini, BAAI/bge-m3 (sentence-transformers), PaddleOCR, Docling, Tavily |
| **Database** | PostgreSQL 16, pgvector, PgBouncer, Redis 7 |
| **Infrastructure** | Docker Compose, Railway, GitHub Actions |
| **Observability** | OpenTelemetry, Prometheus, Sentry, PostHog |

---

## Project Links

| Resource | URL |
|----------|-----|
| GitHub Repository | https://github.com/kanwa2006/DocuMindAI |
| Release Notes | https://github.com/kanwa2006/DocuMindAI/blob/main/RELEASE_NOTES_v1.0.0.md |
| Installation Guide | https://github.com/kanwa2006/DocuMindAI/blob/main/docs/deployment/installation.md |
| Architecture | https://github.com/kanwa2006/DocuMindAI/blob/main/docs/architecture/project-map.md |

---

## Category Suggestions (Devpost)

- **Best AI/ML Hack**
- **Best Use of AI APIs** (Google Gemini)
- **Best Developer Tool**
- **Best Open Source Hack**
- **Most Technically Complex**
