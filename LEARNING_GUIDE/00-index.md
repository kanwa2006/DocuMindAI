# 00 — Course Index

**Course title:** Software Engineering, taught through DocuMindAI.

**What this course is.** This is not a tour of one codebase. It is an
engineering course. The subject is engineering; this repository is the
laboratory where we look at the subject with real, running code instead of toy
examples.

**The test of success.** At the end you should be able to open an empty folder
on a fresh computer and build a different production application with these
same tools, without copying anything from here — and explain every decision in
an interview. If you can only describe what DocuMindAI does, the course failed.

**How to read.** In order. Each file assumes only the files before it, and
re-explains borrowed ideas in a sentence rather than assuming you remember.

**Three living documents** (updated as we go, not written once):

| File | What it holds |
|---|---|
| [PROGRESS.md](PROGRESS.md) | Checklist of what is taught, what is next |
| [ENGINEERING_DECISIONS.md](ENGINEERING_DECISIONS.md) | Every real decision: problem, options, choice, tradeoff |
| [GLOSSARY.md](GLOSSARY.md) | Every technical term, one simple sentence each |

> A note on file placement: the repository root already has its own
> `PROGRESS.md` (product status). To avoid two files with the same name
> fighting each other, all three course documents live inside `LEARNING_GUIDE/`.
> `LEARNING_GUIDE/PROGRESS.md` is about *your learning*; the root one is about
> *the product*.

---

## Scope decision — read this before planning your time

**This course was re-planned after Chapter 10 for a specific goal: placement
readiness for backend and AI engineering roles within one to two months.**

The original outline had 49 files. It was optimised for completeness and would
have taken about six months, with roughly a third of it providing little
interview or engineering return. It was cut to **19 chapters, 18 of them
essential**, using one test on every candidate topic:

> *Does an interviewer for a backend/AI role ask about it, **and** does this
> repository have a subsystem that cannot be explained without it?*

Topics failing both were cut or merged. Nothing was dropped for being hard.

**What was merged:** Redis into caching; Celery, Beat and queues into one
background-jobs chapter; React, Next.js and Tailwind into one frontend
chapter; LLM fundamentals and the RAG pipeline into one double-length AI
chapter; Docker, CI/CD, observability and debugging into one production
chapter; interview prep, study artefacts, capstone and career into one final
chapter.

**What moved to Advanced Learning** (worth doing after placements, listed at
the bottom of this file): Kubernetes, microservices, PostgreSQL tuning at
scale, dedicated vector databases, model fine-tuning, distributed tracing
depth, load testing, multi-region deployment.

---

## The course

### Part 0 — Orientation (complete)

| # | File | You will learn | Status |
|---|---|---|---|
| 01 | [01-overview.md](01-overview.md) | What the product does, and one click traced through every layer | ✅ |
| 02 | [02-system-design.md](02-system-design.md) | The nine-step design method; requirements, subsystems, alternatives, tradeoffs | ✅ |
| 03 | [03-how-engineers-think.md](03-how-engineers-think.md) | Beginner → intermediate → senior → staff reasoning on three real features | ✅ |
| 04 | [04-ai-agents-and-orchestration.md](04-ai-agents-and-orchestration.md) | Agents as software engineering: ownership, contracts, isolation, coverage | ✅ |

### Part 1 — Foundations (complete)

| # | File | You will learn | Status |
|---|---|---|---|
| 05 | [05-computing-foundations.md](05-computing-foundations.md) | Machine, files, processes, OS, terminal, networking, HTTP, TLS, JSON, Git | ✅ |
| 06 | [06-python-from-zero.md](06-python-from-zero.md) | Python as a way to express those ideas, up to decorators and typing | ✅ |
| 07 | [07-async-python.md](07-async-python.md) | The event loop, coroutines, `await`, blocking code, thread and process pools | ✅ |
| 08 | [08-javascript-from-zero.md](08-javascript-from-zero.md) | The browser's language, its event loop, `fetch`, promises, closures | ✅ |
| 09 | [09-typescript.md](09-typescript.md) | Types as an engineering tool, and a bug fixed at the type | ✅ |
| 10 | [10-sql-from-zero.md](10-sql-from-zero.md) | Tables, keys, joins, indexes, transactions, ACID, a real race condition | ✅ |

### Part 2 — The system, subsystem by subsystem

| # | File | You will learn | Tag | Status |
|---|---|---|---|---|
| 11 | [11-caching-concepts.md](11-caching-concepts.md) | Caching and Redis: keys, invalidation, stampedes, and two real cache incidents | Essential | ✅ |
| 12 | [12-background-jobs.md](12-background-jobs.md) | Celery, queues, Beat: how slow work leaves the request and survives | Essential | ✅ |
| 13 | [13-fastapi.md](13-fastapi.md) | The backend request path: routing, dependencies, validation, middleware, SSE | Essential | ✅ |
| 14 | [14-sqlalchemy-and-migrations.md](14-sqlalchemy-and-migrations.md) | The ORM over the SQL you now know, sessions, pooling, Alembic | Essential | ✅ |
| 15 | [15-auth-and-security.md](15-auth-and-security.md) | JWT, cookies, CSRF, multi-tenancy, uploads, prompt injection, secrets | Essential | ✅ |
| 16 | [16-ai-engineering-and-rag.md](16-ai-engineering-and-rag.md) | LLMs, tokens, embeddings, chunking, hybrid retrieval, reranking, grounding, evaluation | Essential (double length) | ✅ |
| 17 | [17-deployment-and-production.md](17-deployment-and-production.md) | Docker, CI/CD, config, health, logging, metrics, rate limits, incident method | Essential | ✅ |

### Part 3 — Converting knowledge into offers

| # | File | You will learn | Tag | Status |
|---|---|---|---|---|
| 18 | [18-interview-capstone-and-career.md](18-interview-capstone-and-career.md) | Drills, the project story at four lengths, the decision defence deck, incident stories, question banks, the scored capstone, resume, honest odds, the validation gate | Essential | ✅ |
| 19 | 19-frontend-react-and-nextjs.md | Components, state, effects, rendering, SSR — enough to explain the UI you built | **Useful — defer if short on time** | ⏳ |

---

## Suggested eight-week schedule

| Week | Chapters | Study hours |
|---|---|---|
| 1 | 11 + 12 | ~8 |
| 2 | 13 + 14 | ~8 |
| 3 | 15 | ~5 |
| 4–5 | 16 (the big one) | ~8 |
| 6 | 17 | ~5 |
| 7 | 18, plus the capstone build | ~8 |
| 8 | Mock interviews, re-read weak chapters, Chapter 19 if time allows | ~6 |

Exercises are not optional. A chapter read without its exercises is worth
roughly half a chapter, because the exercises are where the recall is built.

---

## How each remaining chapter is structured

1. What problem existed before this?
2. Why were older approaches insufficient?
3. What is this, and why was it invented?
4. How does it work internally?
5. Why does this repository use it, and where?
6. The real implementation, read line by line.
7. Beginner mistakes, production mistakes, debugging techniques.
8. Interview expectations.
9. Progressively harder exercises with full reasoning-based answers.
10. A senior critique of this repository's use of it.
11. A validation checklist.

---

## Advanced Learning (after placements)

Worth knowing, not worth your next eight weeks. Each is a self-contained topic
you can pick up when a job requires it.

- **Kubernetes and orchestration at scale** — relevant once you have more than
  a handful of containers and a team operating them.
- **Microservices** — Chapter 02 already explains why this project is
  deliberately not one, which is the answer interviewers actually want.
- **PostgreSQL tuning at scale** — partitioning, replication, query plan
  pinning, connection multiplexing beyond PgBouncer.
- **Dedicated vector databases** — Pinecone, Qdrant, Weaviate; the migration
  seam already exists in `VECTOR_BACKEND`.
- **Model fine-tuning and serving** — LoRA, quantisation, self-hosted
  inference.
- **Distributed tracing in depth** — OpenTelemetry collectors, span design,
  sampling strategy.
- **Load and chaos testing** — k6, Locust, deliberate failure injection.
- **Multi-region and disaster recovery** — replication topology, RPO/RTO.

---

*Ground rule for the whole course: every code block is either copied from this
repository with its file path, or is complete, runnable code written for a
different example. There is no pseudocode anywhere.*
