# Interview Guide — DocuMindAI

Concise, technically precise talking points for engineering interviews and hackathon presentations.

---

## Q1: What problem does DocuMindAI solve?

**Short answer (30 seconds):**

Knowledge workers — lawyers, analysts, researchers — increasingly want to use AI to query their own documents. The problem is that general AI assistants hallucinate. They blend document content with training-data knowledge and produce confident answers that can be factually wrong. For high-stakes professional work, that's a serious reliability problem.

DocuMindAI enforces zero hallucination at the architecture level. Every answer is grounded strictly in retrieved document evidence, cited to the specific page it comes from, and scored for trustworthiness before the user sees it. When evidence is absent, the system explicitly refuses to answer.

**Technical depth (60 seconds):**

The core insight was that prompt-based hallucination mitigation is fragile — it works sometimes but can't be relied on. The correct approach is to eliminate the LLM's access to any knowledge beyond the retrieved evidence. The Grounding Service enforces a strict token budget that contains only document chunks, structured citations, and the system instruction. No external context can enter the generation step. If the retrieval step returns low-confidence results, the system can detect this and refuse. The Veritas Trust Engine then evaluates the generated answer post-hoc across five factors and scores it 0–100 before delivery.

---

## Q2: Why hybrid retrieval?

**Short answer:**

Semantic search (vector similarity) is excellent at capturing conceptual meaning but misses exact keyword matches. BM25 keyword search is excellent for specific terms — clause numbers, person names, technical identifiers — but misses paraphrase. Neither works best alone. Reciprocal Rank Fusion merges both ranked lists without requiring score normalization, which avoids a common pitfall in hybrid systems. The combination reliably outperforms either method in isolation, especially for the diverse query types that professional document work generates.

**If asked about RRF specifically:**

RRF assigns a score of `1 / (rank + k)` to each document for each retrieval method, then sums across methods. The constant `k` (typically 60) prevents very high-ranked documents in one system from dominating. It requires no calibration of score scales, which is critical because vector similarity scores and BM25 scores are not directly comparable.

---

## Q3: Why the Veritas Trust Engine?

**Short answer:**

Even a grounded RAG system can produce answers of varying quality. The retrieval might return relevant but not perfectly aligned passages. The LLM might still hedge excessively or use weak citation language. Users need a signal about how much to trust a specific answer — not just that the system is "grounded in general."

The Veritas Engine evaluates five factors post-generation: citation density (how many claims are explicitly cited), structural alignment (does the answer structure match the question type), hedging language (excessive hedging signals low-confidence generation), source coherence (do the cited passages actually support the claims), and retrieval confidence (the quality of the underlying retrieval step). This produces a 0–100 score that users can act on.

**If challenged: "Why not just use the LLM's confidence score?"**

LLMs don't produce reliable calibrated confidence scores — their logprobs don't correlate well with factual accuracy. An external evaluator that measures observable properties of the output (citation structure, source alignment) is more reliable and interpretable.

---

## Q4: Why FastAPI?

**Short answer:**

FastAPI gave us three things: async-native I/O from the ground up, automatic OpenAPI documentation from type annotations, and Python's ecosystem for AI/ML libraries (sentence-transformers, PaddleOCR, google-generativeai). The async model was critical because the query pipeline involves several I/O-bound steps — database queries, Redis lookups, LLM API calls, streaming SSE — that would cause significant latency under a synchronous framework. With FastAPI + asyncpg, all of these run concurrently within a single process.

---

## Q5: Why Celery?

**Short answer:**

Document processing is CPU-heavy and slow — OCR on a 100-page PDF can take 30–60 seconds, and embedding 10,000 chunks is similarly expensive. These operations cannot run in the API server's event loop without blocking all other requests. Celery separates these into independent worker processes with their own resource allocation, scales independently of the API, provides retry logic on failure, and supports priority queues (we use `main-queue` for document tasks and `celery` for lower-priority background tasks).

**If asked about the async event loop issue in Celery:**

Celery workers run synchronously by default. Our document tasks needed to call async services (async SQLAlchemy sessions, async Redis). We solved this by creating an isolated `asyncio.new_event_loop()` inside each task, running the coroutine in that loop, and cleaning up. This avoids the `RuntimeError: no current event loop` problem that occurs when using `asyncio.get_event_loop()` in a Celery worker context.

---

## Q6: Why pgvector?

**Short answer:**

pgvector integrates vector similarity search directly into PostgreSQL. This means embeddings and relational document metadata live in the same database, with the same transaction semantics, backup procedures, and access controls. The alternative — a separate vector database (Pinecone, Weaviate, Chroma) — adds operational complexity, requires managing a second data store, and introduces synchronization challenges. For a self-hosted project with PostgreSQL as the primary database, pgvector was the pragmatic and technically sound choice. PostgreSQL 16 + pgvector with HNSW indexing provides sufficient performance for the scales this application targets.

---

## Q7: Biggest engineering challenge?

**Option A — Grounding service (technical):**

Enforcing true zero hallucination required thinking carefully about what information the LLM can access during generation. We had to design the token budget allocation — reserving space for document chunks, citation headers, system instructions, and the query itself — while dynamically adjusting chunk count based on chunk sizes. If the budget ran out, we had to choose which chunks to drop based on their reranker score. This required a precise Grounding Service implementation that wasn't just "stuff chunks into the prompt."

**Option B — Unrelated Git history merge (systems):**

The development branch and main branch had completely separate root commits — no common ancestor. This meant a `git merge --allow-unrelated-histories` resulted in `add/add` conflicts for every single file in the repository (hundreds of files). We had to programmatically resolve all conflicts in favor of the development branch (using `git checkout batch-2-work -- .`), then selectively cherry-pick specific critical commits from main that were genuinely absent from the development branch, while preserving both full commit histories in the merged result.

---

## Q8: Most interesting feature?

**The Veritas Trust Engine** — because it requires thinking about what "trustworthy" means as a multi-factor engineering problem. It's easy to say "this answer is grounded." It's harder to quantify *how well* grounded it is, in a way that's transparent to the user and actionable.

The five-factor evaluation framework required thinking about:
- What properties of an answer correlate with factual accuracy?
- How do you weight them against each other?
- How do you evaluate source coherence without running another expensive LLM call?
- How do you present a score to a user in a way that's useful rather than arbitrary-looking?

Designing this evaluation pipeline was genuinely interesting because it pushed toward interpretable AI evaluation rather than black-box confidence scores.

---

## Q9: What would you improve in v1.1?

**Technically honest answer:**

Three things, in priority order:

1. **Workspace ID type unification.** `User.workspace_id` is a string slug (e.g., `"general"`) while `ChatSession.workspace_id` is a UUID. Several endpoints do `uuid.UUID(current_user["workspace_id"])` which crashes on slug inputs. The fix is a deterministic `uuid.uuid5(NAMESPACE_OID, slug)` mapping via a `resolve_workspace_id()` helper. This is a straightforward fix but requires careful migration of any existing rows.

2. **Frontend API prefix normalization.** About 35 frontend call sites bypass the `apiFetch()` convention and manually construct `${API_BASE}/api/v1/...` URLs. Since `NEXT_PUBLIC_API_URL` already includes `/api/v1`, these call sites have a doubled prefix. Pages still function but it's an inconsistency that should be resolved.

3. **Migrate to `google-genai` SDK.** The current `google-generativeai` package is being deprecated in favor of the new `google-genai` SDK with improved streaming and function calling APIs. The migration is mostly a client surface change, but it requires updating the key rotation service and streaming response handlers.

---

## Quick Stats (for "tell me about your project" moments)

| Metric | Value |
|--------|-------|
| Backend lines of code | ~15,000 |
| Frontend components | ~45 |
| API endpoints | ~60+ |
| Database tables | ~25+ |
| Celery task types | ~8 workspace queues + Beat |
| Languages | Python, TypeScript |
| CI checks | Dep audit, migrations, API contracts, ESLint, build |
| Time to deploy (Docker) | ~5 minutes |

---

## One-Sentence Pitch

> DocuMindAI is an open-source AI document intelligence platform that enforces zero hallucination at the architecture level — grounding every answer in retrieved evidence, citing the exact source page, and scoring each response with a Veritas Trust Engine before it reaches the user.
