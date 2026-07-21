# DocuMindAI — FAANG Interview Preparation Guide

This guide turns the DocuMindAI codebase into interview-ready material: how each subsystem works, how to explain the design decisions, likely questions with strong answers, trade-offs, the engineering competencies demonstrated, resume bullets, and system-design concepts. It is grounded in the actual implementation (see [ARCHITECTURE.md](ARCHITECTURE.md)), and it is honest about what is real vs. aspirational — interviewers reward candidates who can name the gaps.

---

## 1. The 30-Second Pitch

> "DocuMindAI is a full-stack, multi-tenant RAG platform. Users upload documents; we extract, chunk, and embed them, then answer questions with Google Gemini strictly grounded in retrieved evidence, streaming tokens over SSE with page-level citations. It's organized into seven domain workspaces — each with its own schema, Celery workers, and retrieval tuning — and it's built async end-to-end on FastAPI + async SQLAlchemy + Postgres/pgvector + Redis/Celery, with an LLM resilience layer that rotates across Gemini API keys and never crashes on blocked responses."

Then, if pressed for depth, pick one subsystem below and go deep.

---

## 2. Subsystem Explanations (how it works + how to explain it)

### 2.1 Hybrid Retrieval + RRF
**How it works:** For each query we run two searches — semantic (vector cosine) and lexical (Postgres full-text `ts_rank_cd`, BM25-style) — over a fusion pool (`max(top_k*2, 30)`), then combine them with **Reciprocal Rank Fusion**: `score(d) = Σ 1/(k + rank_i(d))`, `k=60`.
**Why RRF:** it fuses ranked lists **without score normalization**, so we don't have to reconcile cosine similarities with BM25 scores that live on different scales. It's robust and cheap.
**Trade-off to state:** RRF ignores score magnitude (only rank), so a very-high-confidence semantic hit ranks similarly to a marginal one at the same position. Alternatives: weighted linear fusion (needs normalization), or learned fusion.
**Honesty point:** in this codebase the default `VECTOR_BACKEND=faiss` path is actually an in-memory NumPy scan; pgvector is the correct-but-non-default option. A strong candidate says: *"I'd flip the default to pgvector with an HNSW index; NumPy brute force is O(N) and won't scale."*

### 2.2 Grounding & the Anti-Hallucination Contract
**How it works:** After retrieval we dedupe → rerank (cross-encoder) → threshold-filter → take top-N → **sort into document order** → pack into a token budget (6000) as `<evidence>` blocks. The system prompt forbids external knowledge and mandates an exact refusal string when evidence is absent.
**Why it matters:** hallucination is prevented **architecturally** (the LLM only sees retrieved evidence) rather than by asking nicely. Document-order presentation gives linear, page-ordered citations.
**Trade-off:** token budgeting truncates evidence; summary questions can't be answered from top-k alone — which is why there's a separate **map-reduce full-document summary** path.

### 2.3 Cross-Encoder Reranking
**How it works:** the bi-encoder (bge-m3) is fast but coarse; we re-score the top candidates with a **cross-encoder** (`ms-marco-MiniLM-L-6-v2`) that attends over the (query, passage) pair jointly, then min-max normalize.
**Why:** classic two-stage retrieval — cheap recall, expensive precision. **Trade-off:** cross-encoders are slow (can't run over the whole corpus), hence only on the shortlist.

### 2.4 LLM Resilience (the part most worth showing)
**How it works:** a `GeminiKeyRotator` round-robins across `GEMINI_API_KEY_1..N`, cooling down keys on 429 (5 min) and permanently skipping on 403; a model-fallback kicks in on 404/deprecated; and `_safe_extract_text` handles Gemini responses that have **no parts** (safety/recitation/max-token blocks) so a single bad chunk can't kill an SSE stream. Structured outputs use a **JSON-repair loop** (parse → Pydantic validate → re-prompt with the error, up to 3 times).
**Why it's interview gold:** it demonstrates production thinking about **partial failures**, **rate limits**, and **provider quirks**. **Trade-off to name:** `get_key()` sleeps inside a lock — a real concurrency bug you can offer to fix (move the sleep outside the critical section, or use a condition variable).

### 2.5 Async Ingestion Pipeline
**How it works:** upload → presigned/local → `verify` creates the row and dispatches a Celery task → worker streams pages (PyMuPDF / python-pptx), chunks on layout boundaries, **batches embeddings (50)**, commits per batch, transitions `PROCESSING → EXTRACTED → READY`, retries with exponential backoff, dead-letters to `FAILED`.
**Why offload:** OCR/embedding are CPU/GPU-heavy; keeping them off the API server preserves request latency and lets you scale workers independently of API replicas.

### 2.6 Multi-Tenancy
**How it works:** JWT carries `sub` + `workspace_id` + `roles`; every query filters by `owner_id` + a deterministic workspace UUID (`uuid5(slug)`); vectors are namespaced per user/org; Postgres RLS migrations exist.
**Trade-off:** app-layer filters are easy but must be applied everywhere (one missed filter = leak); RLS is defense-in-depth but requires a non-superuser DB role.

### 2.7 Streaming (SSE)
**How it works:** `StreamingResponse` yields `event: token\ndata: {...}\n\n` frames; the client parses on `\n\n` boundaries. A micro-sleep between tokens lets the ASGI server detect client disconnects.
**Why SSE over WebSockets:** one-directional server→client streaming, works over plain HTTP, no extra protocol — the right tool for token streaming.

---

## 3. Likely Interview Questions & Strong Answers

**Q: How do you prevent hallucination in a RAG system?**
A: Three layers — (1) *retrieval* gives the model only relevant evidence; (2) *prompt contract* forbids outside knowledge and mandates an explicit refusal; (3) *verification* — cite each claim to a page and, ideally, check that cited passages actually support the claim. In DocuMindAI the first two are implemented; the third (a trust score) exists as a heuristic but isn't wired into the main path — I'd add sentence-level citation verification.

**Q: Why hybrid retrieval instead of pure vector search?**
A: Vector search misses exact-match/keyword/rare-token queries (names, IDs, section numbers); lexical BM25 misses paraphrase/semantics. Fusing both with RRF captures conceptual and literal matches without score-scale reconciliation.

**Q: How would you scale this to millions of documents?**
A: pgvector with HNSW (or a dedicated vector DB like Qdrant) instead of the in-memory scan; shard by tenant; push embedding/OCR to autoscaled GPU workers with dedicated queues; add a read replica + PgBouncer; cache retrievals in Redis (already present); consider approximate rerank batching.

**Q: How do you handle LLM rate limits and outages?**
A: Multi-key rotation with per-key cooldowns, model fallback, retry with backoff, and a safe response extractor so blocked completions degrade to a friendly message instead of a 500. Add a circuit breaker (present as a primitive) and a queue-based backpressure mechanism under sustained 429s.

**Q: Walk me through what happens when a user asks a question.**
A: (SSE opens → trial check → load history + attached docs → summary-intent branch or hybrid retrieval → rerank + token budget → emit metadata with evidence → stream Gemini tokens with key rotation → append disclaimer → done.) Name the cache and the document-scoping.

**Q: What are the failure modes and how do you observe them?**
A: OTel tracing per route/worker, Prometheus metrics, Sentry errors, health checks (db/redis/gemini/disk/celery) with alerting after 3 consecutive failures. Then be honest: many failures degrade silently (zero-vector embeddings, dummy reranker) — I'd convert those to metrics/alerts.

**Q: How is background work structured?**
A: Celery + Redis with per-domain queues and Beat for scheduled automation. Then flag the real bug: the deployed worker only consumes two queues and half the task modules aren't in `include`, so several task classes never run — a wiring fix.

**Q: Design question — how would you add per-tier usage quotas?**
A: Move from a single trial counter to a usage-metering service keyed by (user, period), enforce in a dependency before generation, store counters in Redis with atomic INCR + TTL, reconcile to Postgres for billing, and surface remaining quota in `/billing/status`.

---

## 4. Trade-offs & Alternatives (have these ready)

| Decision | Alternative | Why this / when to switch |
|---|---|---|
| RRF fusion | Weighted linear fusion | RRF avoids normalization; switch when you have labeled data to tune weights |
| pgvector | Qdrant/Pinecone/Milvus | pgvector keeps one datastore; switch at large scale / advanced filtering |
| Gemini | OpenAI/Claude/local vLLM | provider abstraction allows swap; Gemini free tier fits a student build |
| SSE | WebSockets | SSE is simpler for one-way streaming |
| Celery | Arq/Dramatiq/Temporal | Celery is mature; Temporal for durable multi-step workflows |
| Cross-encoder rerank | Cohere Rerank API / ColBERT | local avoids API cost; managed for quality/scale |
| JWT (self-issued) | Auth0/Clerk (JWKS/RS256) | self-issued is simple; managed IdP for enterprise SSO |

---

## 5. Engineering Competencies Demonstrated

- **Systems design:** multi-stage RAG, two-phase retrieval, async pipeline, queue-based offload, multi-tenancy.
- **Reliability engineering:** retries/backoff, dead-letter, key rotation, cooldowns, safe degradation, health checks.
- **API design:** versioned REST, SSE streaming, CSRF, rate limiting, presigned uploads.
- **Data engineering:** vector + lexical indexing, chunking strategy, migrations, RLS.
- **Product breadth:** seven domain verticals with tailored prompts and schemas.
- **Security awareness:** bcrypt, JWT pinning, HMAC webhooks/URLs, PII redaction.
- **Judgment/honesty:** ability to articulate what's real vs. stubbed (the highest-signal trait).

---

## 6. Resume Bullets (accurate, defensible)

- *Built a multi-tenant RAG platform (FastAPI, async SQLAlchemy, Postgres/pgvector, Redis/Celery, Next.js 16/React 19) serving grounded, page-cited answers over user documents via Google Gemini with SSE token streaming.*
- *Engineered a two-stage retrieval pipeline — hybrid semantic + BM25 fusion (Reciprocal Rank Fusion) followed by cross-encoder reranking and token-budgeted grounding — to enforce evidence-grounded generation.*
- *Designed an LLM resilience layer with multi-key rotation, per-key rate-limit cooldowns, model fallback, safe response extraction, and a JSON-repair loop for reliable structured outputs.*
- *Implemented an async document-ingestion pipeline (PyMuPDF/python-pptx extraction, layout-aware chunking, batched embeddings) on Celery workers with retry/backoff and dead-letter handling.*
- *Delivered seven domain workspaces (HR/Legal/Finance/Study/Research/Exam/General) with domain-tuned retrieval, structured extraction, and DOCX export — including a Finance ratio engine that computes all arithmetic in Python to eliminate numeric hallucination.*
- *Added multi-tenant isolation (per-user/org vector namespaces, Postgres RLS), JWT+CSRF auth, SlowAPI rate limiting, and Razorpay billing with HMAC-verified webhooks.*

*(If asked, be ready to say which of these are default-on vs. config-gated — e.g., pgvector is available but not the default.)*

---

## 7. System-Design Concepts on Display

Retrieval-Augmented Generation · two-phase retrieval (recall→precision) · reciprocal rank fusion · vector databases & ANN · cross-encoder reranking · token budgeting · map-reduce summarization · SSE streaming · producer/consumer task queues · idempotent retries & dead-letter queues · circuit breaking · rate limiting · multi-tenancy & row-level security · connection pooling (PgBouncer) · cache-aside (Redis) · webhook signature verification · presigned uploads · provider abstraction / strategy pattern · graceful degradation.

---

## 8. If the Interviewer Reads the Code

Be ready to own these (they show you understand the difference between "demo-complete" and "production-complete"):
- The default vector path is NumPy in-memory, not pgvector.
- Veritas is a heuristic and only wired into one (broken) path, not "every response."
- The multi-engine OCR orchestrator isn't on the ingestion path.
- Four `*/search` endpoints call a nonexistent `get_embedding`.
- Worker queue routing means several task classes never execute; there's no Beat container.
- Test coverage is two smoke tests.

Framing this as *"here's the roadmap to production-harden it"* is far stronger than pretending it's finished.
