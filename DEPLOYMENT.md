# DocuMindAI — Deployment Guide

> **Free-tier public demo** — intended for recruiter review, not durable production.
> All free-tier limitations are documented honestly below.

---

## Deployed Stack

| Component | Platform | Free-Tier Limits (Sep 2026) |
|-----------|----------|-----------------------------|
| Frontend (Next.js 16) | Vercel Hobby | $0 · 100 GB/mo bandwidth · 45 min build |
| API (FastAPI + Uvicorn) | Render Free web service | $0 · 512 MB RAM · 0.1 CPU · 750 h/workspace/mo |
| Worker (Celery) | Render Free worker service | $0 · 512 MB RAM · same 750 h pool |
| Database (PostgreSQL 16 + pgvector) | Supabase Free | $0 · 500 MB · pauses after 7 days idle |
| Redis (broker + result backend) | Upstash Free | $0 · 500 K commands/mo · 256 MB |

**Total infrastructure cost: $0 / ₹0**

---

## Architecture

```
Browser  (Next.js on Vercel)
   │  NEXT_PUBLIC_API_URL
   ▼
FastAPI + Uvicorn  (Render Free — 512 MB RAM)
   │  asyncpg → Supabase Transaction Pooler (port 6543)
   ▼
PostgreSQL 16 + pgvector  (Supabase Free — 500 MB)
   document_chunks.embedding  Vector(1024)
   HNSW index  vector_cosine_ops  m=16  ef_construction=64
   │  Redis broker
   ▼
Upstash Redis TLS  (Free — 500 K cmd/mo)
   │  Celery task dispatch
   ▼
Celery Worker  (Render Free — 512 MB RAM)
   ├── Text extraction: PyMuPDF / python-docx / python-pptx
   ├── Chunking: 1 800-char chunks, 300-char overlap
   └── EmbeddingService
         ├── LocalEmbeddingProvider (BAAI/bge-m3 2.2 GB) → OOM on 512 MB
         └── GeminiEmbeddingProvider FALLBACK ← ACTIVE on free tier
               model: gemini-embedding-2
               output_dimensionality: 1024  (MRL truncation)
               → native 1024-dim vectors, no zero-padding
               → exact match with Vector(1024) pgvector column
   │
   ▼  vectors stored in Supabase pgvector
Query path  (FastAPI process — synchronous per request)
   ├── Hybrid retrieval: pgvector cosine ANN + tsvector BM25 → RRF fusion
   ├── Cross-encoder reranker: ms-marco-MiniLM-L-6-v2 (~80 MB, lazy-load)
   ├── GroundingService: token-budget enforcement (6 000 tokens)
   ├── Gemini LLM: gemini-2.5-flash-lite (key-rotating, SSE streaming)
   └── VeritasEngine: trust score + grounded/general mode badge
   │  SSE stream
   ▼
Browser  (citations, page numbers, trust score, streaming answer)
```

---

## Embedding Pipeline — Why gemini-embedding-2

`text-embedding-004` was **shut down on January 14 2026**.

`gemini-embedding-2` supports Matryoshka Representation Learning (MRL), allowing
the caller to request any output dimension between 128 and 3 072. We request
**exactly 1 024 dimensions** (`output_dimensionality=1024`), which is the size of
the existing `document_chunks.embedding Vector(1024)` column and HNSW index.

Result: no zero-padding, no dimension mismatch, no corpus corruption.

```
bge-m3 (primary, unavailable on 512 MB free tier)
  └── 1024-dim native vectors
gemini-embedding-2 (fallback, active on Render Free)
  └── output_dimensionality=1024  ← MRL truncation, native 1024-dim
  └── task_type=RETRIEVAL_DOCUMENT for indexing
  └── Consistent: both index-time and query-time use the same path
```

> ⚠️ The Gemini fallback is self-consistent **only on a fresh database**.
> Do not mix bge-m3 vectors and Gemini vectors in the same corpus.

---

## Step-by-Step Deployment

### Prerequisites
- GitHub account with push access to `kanwa2006/DocuMindAI`
- Render account (free, sign up with GitHub)
- Vercel account (free, sign up with GitHub)
- Supabase account (free, no credit card)
- Upstash account (free, no credit card)

---

### Step 1 — Supabase (PostgreSQL + pgvector)

1. Sign in → [supabase.com](https://supabase.com) → **New project**
2. Choose a strong database password — save it
3. Go to **Settings → Database → Connection string → URI**
   - Select **Transaction pooler** (port **6543**)
   - Copy the full URI → this is `DATABASE_URL`
   - Format: `postgresql+asyncpg://postgres.<ref>:<password>@<region>.pooler.supabase.com:6543/postgres`
4. In the Supabase SQL editor, run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Migrations run automatically via `alembic upgrade head` at API startup.

> ⚠️ **Supabase Free pauses after 7 consecutive days with no database requests.**
> Unpause at: supabase.com → your project → "Restore project".

---

### Step 2 — Upstash Redis

1. Sign in → [upstash.com](https://upstash.com) → **Create database**
2. Choose a region close to your Render deployment (e.g. US East or EU West)
3. Copy the **TLS connection string** — format:
   `rediss://default:<password>@<host>.upstash.io:6379`
4. Use this URL for all three: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

---

### Step 3 — Render (API + Celery Worker)

1. Sign in → [render.com](https://render.com) → **New → Blueprint**
2. Connect your GitHub repo: `kanwa2006/DocuMindAI`
3. Render detects `render.yaml` → proposes `documindai-api` + `documindai-worker`
4. For each service, click **Environment** and add all `sync: false` secrets:

**Generate two fresh secret keys (run twice for different values):**
```bash
openssl rand -hex 32
```

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Supabase transaction-pooler URI (step 1) |
| `REDIS_URL` | Upstash TLS URL (step 2) |
| `CELERY_BROKER_URL` | Same Upstash URL |
| `CELERY_RESULT_BACKEND` | Same Upstash URL |
| `AUTH_SECRET_KEY` | `openssl rand -hex 32` output |
| `CSRF_SECRET_KEY` | `openssl rand -hex 32` (different value) |
| `FRONTEND_URL` | `https://<your-app>.vercel.app` (fill after step 4) |
| `CORS_ORIGINS` | `["https://<your-app>.vercel.app"]` |
| `GEMINI_API_KEY_1` | Your Google AI Studio API key |
| `POSTGRES_PASSWORD` | Your Supabase DB password |

5. Click **Apply** → build starts (~10–15 min for Docker + pip wheels)

**API service start command** (set automatically from `render.yaml`):
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Worker service start command:**
```
celery -A app.workers.celery_app worker -Q main-queue,celery,export_queue,ocr_gpu_queue --concurrency=1 --loglevel=info
```

---

### Step 4 — Vercel (Next.js Frontend)

1. Sign in → [vercel.com](https://vercel.com) → **New Project → Import from GitHub**
2. Select `kanwa2006/DocuMindAI`
3. Set **Root Directory** → `frontend`
4. Add environment variable (build-time):
   ```
   NEXT_PUBLIC_API_URL = https://documindai-api.onrender.com/api/v1
   ```
   *(Replace `documindai-api` with your actual Render service name)*
5. Click **Deploy**

> ⚠️ `NEXT_PUBLIC_*` is **inlined at build time**. Changing it requires a redeploy.

---

### Step 5 — Update CORS after Vercel deploy

Once you have your Vercel URL (e.g. `https://documindai.vercel.app`):

In **Render Dashboard → documindai-api → Environment**, update:
- `FRONTEND_URL` = `https://documindai.vercel.app`
- `CORS_ORIGINS` = `["https://documindai.vercel.app"]`

Then click **Manual Deploy → Deploy latest commit** on the API service.
Do the same for the worker service.

---

## Environment Variables Reference

### Backend (Render Dashboard only — never committed)

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | ✅ | Supabase transaction-pooler, asyncpg scheme |
| `REDIS_URL` | ✅ | Upstash TLS (`rediss://`) |
| `CELERY_BROKER_URL` | ✅ | Same as REDIS_URL |
| `CELERY_RESULT_BACKEND` | ✅ | Same as REDIS_URL |
| `AUTH_SECRET_KEY` | ✅ | ≥32 bytes hex |
| `CSRF_SECRET_KEY` | ✅ | ≥32 bytes hex, different from AUTH |
| `FRONTEND_URL` | ✅ | Your Vercel URL |
| `CORS_ORIGINS` | ✅ | JSON array of allowed origins |
| `GEMINI_API_KEY_1` | ✅ | Google AI Studio key |
| `GEMINI_API_KEY_2..N` | optional | Additional keys for rotation |
| `POSTGRES_PASSWORD` | ✅ | Supabase DB password |
| `ENVIRONMENT` | ✅ | `production` |
| `STORAGE_PROVIDER` | ✅ | `local` |
| `STORAGE_PATH` | ✅ | `/tmp/documind_storage` |
| `OCR_SCANNED_ENABLED` | ✅ | `false` (PaddleOCR not installed) |
| `VECTOR_BACKEND` | ✅ | `pgvector` |
| `GEMINI_MODEL` | ✅ | `gemini-2.5-flash-lite` |
| `MAX_UPLOAD_MB` | ✅ | `50` |

### Frontend (Vercel Dashboard — build-time only)

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://documindai-api.onrender.com/api/v1` |

> ⚠️ `NEXT_PUBLIC_*` values are **public** — never put any secret behind this prefix.

---

## Free-Tier Limitations (Honest)

| Limitation | Impact |
|-----------|--------|
| **Cold start ~30–60 s** | Render Free sleeps after 15 min idle. First request after sleep shows a loading delay. |
| **Ephemeral storage** | Files in `/tmp/documind_storage` are lost on restart or redeploy. If the Celery worker restarts after an upload, ingestion fails. Upload fresh files after any restart. |
| **512 MB RAM** | BAAI/bge-m3 (2.2 GB) OOMs — gemini-embedding-2 fallback used automatically. Retrieval quality is slightly lower than with the local model. |
| **0.1 vCPU** | Reranking and embedding are slow (~5–15 s/query cold, ~2–5 s warm). |
| **No scanned PDFs** | PaddleOCR/Docling not installed. PDFs with no text layer will fail extraction. Text-based PDFs, DOCX, PPTX work fine. |
| **750 h/month** | Two services combined. Low-traffic demo is fine; sustained load may exhaust hours. |
| **Supabase 7-day pause** | Project auto-pauses after 7 days with no DB requests. Manually unpause at supabase.com. |
| **Supabase 500 MB** | Vector embeddings consume storage. ~100 documents ≈ 10–50 MB of vectors. |
| **Upstash 500 K cmd/mo** | Sufficient for demo; each document upload ≈ 5–20 Celery task commands. |
| **Gemini API cost** | Uses your API keys. Google AI Studio free tier: generous daily quota. |
| **No Celery Beat** | Scheduled tasks (health checks, digest emails, DB cleanup) not deployed — no user-facing impact for demo. |

---

## Feature Status

| Feature | Status on Demo |
|---------|----------------|
| User auth (JWT + CSRF) | ✅ Working |
| Document upload (PDF/DOCX/PPTX) | ✅ Text-based only |
| Text extraction (PyMuPDF) | ✅ Working |
| Scanned PDF / OCR | ❌ Disabled (PaddleOCR not installed) |
| Chunking (1 800 char / 300 overlap) | ✅ Working |
| Embeddings (bge-m3) | ❌ OOM on 512 MB |
| Embeddings (gemini-embedding-2 fallback) | ✅ Active — 1024-dim native |
| pgvector HNSW hybrid retrieval | ✅ Working |
| BM25 + RRF fusion | ✅ Working |
| Cross-encoder reranking | ✅ Working (lazy-load ~80 MB) |
| Gemini LLM (SSE streaming) | ✅ Working |
| Grounded answers + page citations | ✅ Working |
| Veritas trust score | ✅ Working |
| Out-of-context refusal | ✅ Working |
| 7 specialized workspaces | ✅ All accessible |
| Rate limiting | ✅ Working |
| Tenant isolation (RLS) | ✅ Working |
| File persistence after restart | ❌ Ephemeral /tmp |

---

## Local Development (Unaffected)

```bash
cd infrastructure
docker compose up
```

The Dockerfile changes are backward-compatible:
- Default `REQUIREMENTS_FILE=requirements.txt` → full deps including PaddleOCR
- `docker-compose.yml` does not pass the ARG → uses full deps
- `context: ..` (repo root) is required so the Dockerfile can COPY `backend/`

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `GET /api/v1/health` returns 503 | DB or Redis unreachable | Is Supabase paused? Is Upstash URL correct? |
| Upload stuck at PROCESSING forever | Celery worker not running | Check Render worker service logs |
| Worker crash loop | Missing env var | Verify `DATABASE_URL`, `CELERY_BROKER_URL` in Render env |
| `No Gemini API keys configured` | Missing `GEMINI_API_KEY_1` | Add key in Render environment |
| Frontend shows CORS error | Wrong `CORS_ORIGINS` | Must exactly match your Vercel URL; redeploy API |
| `NEXT_PUBLIC_API_URL` still points to localhost | Stale Vercel build | Redeploy frontend after setting the env var |
| First request takes 60 s | Cold start (normal) | Expected behavior — Render Free sleeps after 15 min |
| Embedding fails with "model not found" | Wrong model name | Check `gemini-embedding-2` is spelled correctly |
| Upload works but query returns no results | Empty corpus | Verify document status is `READY`, not `PROCESSING` or `FAILED` |

---

## Security Checklist

- [x] `AUTH_SECRET_KEY` and `CSRF_SECRET_KEY` are unique 32+ byte hex strings
- [x] No secrets in `render.yaml` (all are `sync: false`)
- [x] `NEXT_PUBLIC_*` contains no secrets (public by design)
- [x] CORS enforced server-side — must match exact Vercel URL
- [x] JWT expires in 60 minutes
- [x] Documents isolated by `owner_id` (PostgreSQL RLS)
- [x] Stack traces never returned to browser in production
- [x] `ENVIRONMENT=production` disables DummyEmbeddingProvider (M-4)
- [x] `.env` and `.env.production` are gitignored — never committed

---

## End-to-End Test Checklist

After deployment, verify the full pipeline manually:

```
1.  GET  /api/v1/health
    → { "status": "ok" }  (or individual service checks)

2.  POST /api/v1/auth/register
    → 201 Created, user object returned

3.  POST /api/v1/auth/login
    → 200 OK, access_token in response

4.  POST /api/v1/documents/upload  (with Authorization header)
    → 201 Created, { document_id, status: "UPLOADED" }

5.  Poll GET /api/v1/documents/{id}
    → status: PROCESSING → EXTRACTED → INDEXING → READY

6.  POST /api/v1/query/stream  (SSE)
    Query: something the uploaded PDF explicitly answers
    → SSE chunks: answer text
    → Final event: evidence array with filename + page_number + text_content
    → Final event: confidence_score (Veritas trust score)
    → grounded: true

7.  POST /api/v1/query/stream
    Query: something NOT in the document
    → Answer indicates it cannot find this in the documents
    → grounded: false  OR  evidence: []
```

---

## Resume Description

> **DocuMindAI** — Production-grade multi-tenant document QA platform with page-level citations and Veritas trust scoring. Implements hybrid retrieval (pgvector HNSW cosine ANN + BM25 tsvector + Reciprocal Rank Fusion), cross-encoder reranking, token-budgeted grounding, and streaming Gemini LLM answers. Seven specialized AI workspaces (General, Legal, Finance, HR, Research, Teacher, Student). Built on FastAPI, Celery, PostgreSQL + pgvector, Redis, and Next.js 16. Deployed at zero cost on Vercel + Render + Supabase + Upstash.
>
> **GitHub:** https://github.com/kanwa2006/DocuMindAI
