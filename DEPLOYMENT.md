# DocuMindAI — Deployment Guide

> **Demo deployment** — free-tier infrastructure for recruiters and reviewers.
> Not a durable production deployment. Read the limitations section.

---

## Architecture

```
Browser (Next.js on Vercel)
      │  NEXT_PUBLIC_API_URL
      ▼
FastAPI + Uvicorn  (Render Free web service)
      │  async SQLAlchemy / asyncpg
      ▼
PostgreSQL 16 + pgvector  (Supabase Free — 500 MB)
      │  Redis broker / result backend
      ▼
Upstash Redis TLS  (Free — 500K commands/month, 256 MB)
      │  Celery task dispatch
      ▼
Celery Worker  (Render Free worker service)
   ├── OCRService (text-based only: PyMuPDF / python-docx / python-pptx)
   ├── ChunkingService
   └── EmbeddingService
         ├── BAAI/bge-m3 (2.2 GB) → FAILS on 512 MB free tier
         └── gemini-embedding-2, output_dimensionality=1024 ✓ FALLBACK
      │  embeddings stored in Vector(1024) HNSW column
      ▼
Query path (FastAPI process, synchronous per-request):
   ├── Hybrid retrieval: pgvector cosine ANN + tsvector BM25 → RRF fusion
   ├── cross-encoder/ms-marco-MiniLM-L-6-v2 reranker (~80 MB, lazy-loaded)
   ├── GroundingService (token budget enforcement)
   ├── Gemini LLM (gemini-2.5-flash-lite, key-rotating)
   └── VeritasEngine (trust score + grounded/general mode)
      │  SSE stream
      ▼
Browser (citations, trust score, streaming answer)
```

---

## Deployment Platforms (All Free Tier — Sep 2026)

| Component | Platform | Free Tier |
|-----------|----------|-----------|
| Frontend  | Vercel Hobby | $0 · 100 GB/month bandwidth · 45 min build |
| API + Worker | Render Free | $0 · 512 MB RAM · 0.1 CPU · 750 h/workspace/month |
| PostgreSQL + pgvector | Supabase Free | $0 · 500 MB · pauses after 7 days idle |
| Redis broker/cache | Upstash Free | $0 · 500K commands/month · 256 MB |

---

## Environment Variables

### Backend (set in Render Dashboard — NEVER commit these)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Supabase transaction-pooler URL — `postgresql+asyncpg://postgres.<ref>:<pass>@<region>.pooler.supabase.com:6543/postgres` |
| `REDIS_URL` | ✅ | Upstash TLS URL — `rediss://default:<pass>@<host>.upstash.io:6379` |
| `CELERY_BROKER_URL` | ✅ | Same Upstash URL |
| `CELERY_RESULT_BACKEND` | ✅ | Same Upstash URL |
| `AUTH_SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `CSRF_SECRET_KEY` | ✅ | `openssl rand -hex 32` (different from AUTH) |
| `FRONTEND_URL` | ✅ | `https://<your-app>.vercel.app` |
| `CORS_ORIGINS` | ✅ | `["https://<your-app>.vercel.app"]` |
| `GEMINI_API_KEY_1` | ✅ | Your Google AI Studio API key |
| `GEMINI_API_KEY_2..N` | optional | Additional keys for rotation |
| `POSTGRES_PASSWORD` | ✅ | Required by Settings even when DATABASE_URL is set |
| `ENVIRONMENT` | ✅ | `production` |
| `STORAGE_PROVIDER` | ✅ | `local` (ephemeral `/tmp`) |
| `STORAGE_PATH` | ✅ | `/tmp/documind_storage` |
| `OCR_SCANNED_ENABLED` | ✅ | `false` (PaddleOCR not installed in slim build) |
| `MAX_UPLOAD_MB` | ✅ | `50` (safe for 512 MB RAM) |
| `VECTOR_BACKEND` | ✅ | `pgvector` |
| `GEMINI_MODEL` | ✅ | `gemini-2.5-flash-lite` |

### Frontend (set in Vercel Dashboard — build-time)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://documindai-api.onrender.com/api/v1` (include `/api/v1`) |

---

## Step-by-Step Deployment

### 1. Supabase (PostgreSQL + pgvector)

1. Sign in at [supabase.com](https://supabase.com) → New Project
2. Save the **database password** you set
3. Go to **Settings → Database → Connection string → URI** (Transaction pooler — port **6543**)
4. Copy the full URI — this is your `DATABASE_URL`
5. In the Supabase SQL editor run: `CREATE EXTENSION IF NOT EXISTS vector;`
6. Migrations run automatically at API startup via `alembic upgrade head`

> ⚠️ Supabase Free pauses projects after **7 consecutive days without database requests**. To unpause: Supabase Dashboard → your project → "Restore project".

### 2. Upstash Redis

1. Sign in at [upstash.com](https://upstash.com) → New Redis Database
2. Choose **Global** or a region close to your Render deployment
3. Copy the **TLS endpoint** (`rediss://default:<pass>@<host>.upstash.io:6379`)
4. Use this URL for `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND`

### 3. Render (API + Celery Worker)

1. Sign in at [render.com](https://render.com) → New → Blueprint
2. Connect your GitHub repo (`kanwa2006/DocuMindAI`)
3. Render will detect `render.yaml` and propose both services
4. For each service, click **"Configure"** and add all `sync: false` secrets via the dashboard
5. **Generate secrets locally:**
   ```bash
   openssl rand -hex 32   # AUTH_SECRET_KEY
   openssl rand -hex 32   # CSRF_SECRET_KEY (run again for a different value)
   ```
6. Click **"Apply"** to start the build

**Start command (API):**
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
This runs migrations on every deploy before starting the server.

**Start command (Worker):**
```
celery -A app.workers.celery_app worker -Q main-queue,celery,export_queue,ocr_gpu_queue --concurrency=1 --loglevel=info
```

### 4. Vercel (Next.js Frontend)

1. Sign in at [vercel.com](https://vercel.com) → New Project → Import from GitHub
2. Select `kanwa2006/DocuMindAI`
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://documindai-api.onrender.com/api/v1`
5. Click **Deploy**

> ⚠️ `NEXT_PUBLIC_API_URL` is **inlined at build time** — changing it requires a redeploy, not just a restart.

### 5. Update CORS after Vercel deploy

Once you have your Vercel URL (`https://<app>.vercel.app`), update the Render environment variables:
- `FRONTEND_URL` = `https://<app>.vercel.app`
- `CORS_ORIGINS` = `["https://<app>.vercel.app"]`

Then trigger a **Manual Deploy** on the Render API service to pick up the CORS change.

---

## Database Schema

45 Alembic migrations run automatically on API startup:
- `alembic upgrade head` is the first command in the start script
- Creates all tables including pgvector-backed `document_chunks.embedding Vector(1024)`
- HNSW index: `vector_cosine_ops`, `m=16`, `ef_construction=64`
- RLS (Row Level Security) policies for tenant isolation

---

## Embedding Pipeline

```
Model priority (runtime selection):

1. BAAI/bge-m3 (LocalEmbeddingProvider)
   → 1024-dim native
   → FAILS on Render Free 512 MB RAM
   → LocalEmbeddingProvider catches RuntimeError, falls back to ↓

2. gemini-embedding-2 (GeminiEmbeddingProvider) ← ACTIVE on free tier
   → output_dimensionality=1024 (MRL truncation)
   → Returns exactly 1024-dim vectors
   → No zero-padding (text-embedding-004 was shut down Jan 14 2026)
   → task_type=RETRIEVAL_DOCUMENT for indexing
   → Consistent across API and Worker processes
```

**Dimension compatibility:**
- pgvector column: `Vector(1024)` (set by migration `a1b2c3d4e5f7`)
- HNSW index: `vector_cosine_ops` on 1024-dim column
- gemini-embedding-2 with `output_dimensionality=1024`: ✅ exact match
- No padding, no truncation, no corpus corruption

---

## Worker Architecture

Celery worker consumes four queues: `main-queue`, `celery`, `export_queue`, `ocr_gpu_queue`

**Document ingestion flow (Celery):**
1. API receives upload → saves to `/tmp/documind_storage` → dispatches `process_document` task
2. Worker downloads file from storage → extracts text (PyMuPDF / python-docx / python-pptx)
3. OCRService: text-based extraction only (`OCR_SCANNED_ENABLED=false`)
4. ChunkingService: 1800-char chunks with 300-char overlap
5. EmbeddingService: gemini-embedding-2 → 1024-dim vectors
6. Vectors stored in PostgreSQL pgvector

**NOT deployed (Celery Beat):**
Celery Beat (scheduled tasks) is not deployed. This affects:
- Automated health checks (auto_health_check — no user impact)
- Daily digest emails (no user impact — email not configured)
- DB cleanup (no user impact for demo)

---

## Free-Tier Limitations

| Limitation | Detail |
|-----------|--------|
| **Cold start** | Render Free sleeps after 15 min idle. First request after sleep takes 30–60s. |
| **Ephemeral storage** | Files in `/tmp/documind_storage` are lost on restart/redeploy. If the worker restarts after a file was uploaded, ingestion will fail. Upload fresh files after any restart. |
| **RAM: 512 MB** | bge-m3 (2.2 GB) cannot load — gemini-embedding-2 fallback is used. |
| **CPU: 0.1 vCPU** | Reranking and embedding are slow (~5-15s/query). |
| **Scanned PDFs** | PaddleOCR/Docling not installed. Scanned-only PDFs (no text layer) will fail to extract text. Text-based PDFs, DOCX, PPTX work fine. |
| **750 hours/month** | Two services × usage hours. For a recruiter demo with low traffic this is sufficient. |
| **Supabase pause** | Project pauses after 7 days with no DB requests. Manually unpause at supabase.com. |
| **Upstash 500K cmds** | Sufficient for demo traffic. Each document upload ≈ 5–20 Celery task commands. |
| **Gemini API cost** | Uses your Gemini API keys. Free tier of Google AI Studio includes limited requests. |
| **No persistent disk** | Render Free does not support persistent disk mounts. |

---

## Local Development (Unaffected)

Local development continues to use `docker-compose` as before:
```bash
cd infrastructure
docker compose up
```

The Dockerfile changes are backward-compatible:
- Default `REQUIREMENTS_FILE=requirements.txt` → full deps including PaddleOCR
- `docker-compose.yml` does not pass `REQUIREMENTS_FILE` → uses full deps

Verify local config is intact:
```bash
docker compose config
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| API returns 503 on `/health` | DB or Redis unreachable | Check Supabase paused? Check Upstash URL? |
| Upload stuck at PROCESSING | Worker not running | Check Render worker service logs |
| Worker crash loop at startup | Missing env var | Check CELERY_BROKER_URL, DATABASE_URL in Render |
| "No Gemini API keys" error | Missing GEMINI_API_KEY_1 | Add to Render environment |
| Frontend cannot reach API | Wrong CORS_ORIGINS or NEXT_PUBLIC_API_URL | Update both, redeploy both |
| Cold start timeout on upload | Normal — first request after sleep | Wait 60s, retry |
| "Embedding generation failed" | Gemini quota exhausted | Add more GEMINI_API_KEY_N keys |

---

## Security Notes

- `AUTH_SECRET_KEY` and `CSRF_SECRET_KEY` must be unique 32+ byte hex strings
- Never put secrets in `render.yaml` (all secrets are `sync: false`)
- `NEXT_PUBLIC_*` variables are public — never put keys there
- CORS is enforced server-side — `CORS_ORIGINS` must exactly match the Vercel URL
- JWT tokens expire in 60 minutes (ACCESS_TOKEN_EXPIRE_MINUTES=60)
- Documents are tenant-isolated by `owner_id` (PostgreSQL RLS)
- Debug mode is off in production (`ENVIRONMENT=production`)
- Stack traces are never returned to the browser in production

---

## Verified End-to-End Test Flow

```
1. GET /api/v1/health → { "api": "ok", "db": "ok", "redis": "ok" }
2. POST /api/v1/auth/register → 201 Created
3. POST /api/v1/auth/login → JWT access token
4. POST /api/v1/documents/upload → { document_id, status: "UPLOADED" }
5. Celery processes → status: PROCESSING → EXTRACTED → INDEXING → READY
6. GET /api/v1/documents/{id} → { status: "READY", page_count: N }
7. POST /api/v1/query/stream → SSE: answer chunks + evidence + Veritas score
8. Evidence contains { filename, page_number, text_content, similarity_score }
9. Ask out-of-scope question → answer indicates "cannot answer from documents"
```

---

## Resume Description

> **DocuMindAI** — Production-grade multi-tenant document QA platform. Implements hybrid retrieval (pgvector HNSW + BM25 + Reciprocal Rank Fusion), cross-encoder reranking, token-budgeted grounding, and streaming Gemini LLM answers with page-level citations and Veritas trust scoring. Built with FastAPI, Celery, PostgreSQL + pgvector, Redis, and Next.js 16. Deployed at zero cost on Vercel + Render + Supabase + Upstash.
