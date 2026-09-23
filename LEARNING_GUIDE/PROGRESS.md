# LEARNING_GUIDE — Progress

This file tracks **the course**, not the product. The repository root
`PROGRESS.md` tracks the product. Do not confuse them.

A new session can read this file alone and know exactly where to continue.

**Last updated:** 2026-08-05
**Next file to write:** `19-frontend-react-and-nextjs.md` (components, state,
effects, rendering, server vs client, the shared `WorkspaceUI`) — the last
chapter, and the only one marked **Useful rather than Essential**

**Scope was re-planned after Chapter 10.** The original 49-file outline was cut
to **19 chapters, 18 essential**, optimised for placement readiness in one to
two months rather than for completeness. The test applied to every remaining
topic: *does an interviewer for a backend/AI role ask about it, and does this
repository have a subsystem that cannot be explained without it?* See
[00-index.md](00-index.md) for the full roadmap, tags and the eight-week
schedule.

---

## Status legend

- `[x]` written and complete
- `[~]` partially written (says what is missing)
- `[ ]` not started

---

## Part 0 — Orientation

- [x] `00-index.md` — course map, chapter template, ground rules
- [x] `01-overview.md` — what the product does; the full story of one click
- [x] `02-system-design.md` — system design as a subject (9-step method), a
      tiny design and a medium design built from scratch, then DocuMindAI's
      30 FRs, NFR table, real constraints, arithmetic, 14 subsystems with
      alternatives, component + 2 sequence diagrams, failure table,
      4 whole-system alternatives, 10 common mistakes, design-level
      debugging, exercises with answer key, senior critique
- [x] `03-how-engineers-think.md` — the four levels of thinking; ten reusable
      reasoning tools (choke point, fail-closed, instance vs class, ratchet,
      guard that bites, measure the property, observability of a defect,
      positive/negative controls, second-order consequences, blast radius);
      the full 13-step treatment of three features (grounding pipeline,
      tenancy model, streaming answer path) with the real bugs that proved
      each lesson; startup/Google/Amazon/Microsoft comparisons with business
      reasoning; 12 progressive exercises with full answer key; senior
      critique of the *thinking*; 6 interview questions with model answers;
      4 reverse-engineering exercises; 3 design-it-yourself exercises;
      validation checklist
- [x] `04-ai-agents-and-orchestration.md` — agents taught as software
      engineering, not prompting: what an agent is (loop + tools + stopping
      condition), the history from prompts → retrieval → tool use → agents and
      why it rhymes with the microservices era; 15 engineering primitives
      (ownership, responsibility vs capability, boundaries and tie-breaks,
      contracts, communication, state, context, delegation, isolation, error
      propagation, retries, verification, composition, scaling, observability);
      all 11 agents with their one question, tool grant and model assignment;
      how `CLAUDE.md` orchestrates them; why orchestration prevents
      architectural decay (4 decay mechanisms, 4 counters); the full incident
      analysis of the roster failure (`bdc8308`) that let 32 HIGH findings
      pass; why more agents is usually harmful (5 costs) and when agents
      should not exist at all; specialists vs one large agent; how
      orchestration evolves across 4 repository stages; startup/Google/
      Amazon/Microsoft; 12 exercises with full answer keys; senior critique of
      the orchestration itself; validation checklist

## Part 1 — Foundations

- [x] `05-computing-foundations.md` — zero-knowledge foundations in 18 parts:
      the machine (binary, bytes, CPU, RAM, storage, the memory hierarchy with
      real ratios); files, paths, and character encoding (with the latin-1
      export defect); programs vs processes vs threads (and the fork/socket
      corruption bug); the operating system, kernel/user space, Linux vs
      Windows; terminal, shell, pipes, redirection, exit codes; environment
      variables, PATH, virtual environments; networking from packets to IP,
      DNS, ports, TCP, sockets, client/server (with `--host 0.0.0.0` and the
      PgBouncer `LISTEN_PORT` incident); HTTP request/response anatomy and
      status families; HTTPS/TLS (and the percent-encoding → 210 failed
      logins → circuit-breaker outage chain); JSON and serialisation;
      APIs, REST and versioning; one request end-to-end at the byte level;
      Git and GitHub; 15 exercises starting from `pwd` with full answer key;
      senior critique of the foundations layer; 5 interview questions with
      model answers; validation checklist
- [x] `06-python-from-zero.md` — the language taught as a way to express
      Chapter 05's ideas, in 17 parts: what a programming language is,
      compiled vs interpreted, the GIL and why it became an architecture
      decision; values, variables (with the name-tag model, not the box
      model), types, operators; strings and f-strings; conditionals and the
      truthiness trap that leaked every user's documents; loops, `break`,
      `enumerate`, unpacking; functions, defaults, the mutable-default trap,
      scope, `global`, docstrings, and a full line-by-line reading of
      `core/workspace.py`; lists, tuples, dicts, sets, comprehensions and how
      to choose; modules, packages, import-time execution and lazy imports;
      errors, tracebacks, `try/except/finally`, and the bare-except
      catastrophe from `redis_client.py`; classes, static methods, mixins,
      enums, context managers; type hints and Pydantic; generators; decorators
      built from scratch; files and encodings; a complete production function
      read line by line; PEP 8; 15 exercises with full answer key; senior
      critique; 5 interview questions; validation checklist
- [x] `07-async-python.md` — problem first, syntax last, in 18 parts: waiting
      vs working with this system's real 86%-waiting arithmetic; CPU-bound vs
      I/O-bound; blocking defined; the four historical attempts (process per
      request, thread per request and C10K, callbacks and callback hell,
      coroutines) and why each was not enough; the event loop taught by
      analogy then by ready queue / waiting set / `epoll`; what `await`
      actually does and three things it does not; cooperative vs preemptive;
      a timed trace of two interleaved requests; `async def`, `await`,
      `asyncio.run`; tasks, `gather`, `create_task`, fire-and-forget traps,
      `TaskGroup`; cancellation and per-step timeouts; async generators,
      `async for`, `async with`, and why the tenant scope is not a `yield`
      dependency; thread pools, process pools, the GIL, job queues, and a
      decision table; mixing sync and async safely; locks, semaphores, queues,
      backpressure; all three real incidents with their measured guards; seven
      misconceptions corrected explicitly; reading the real streaming endpoint;
      15 exercises with full answer key; senior critique; 5 interview
      questions; validation checklist
- [x] `08-javascript-from-zero.md` — the browser's language from zero, in 17
      parts: why a second language is unavoidable (agreement, safety, instant
      start, history); the 1995 origin and why the oddities can never be
      fixed; running JS in the console, in a page, in Node, and what the build
      step does to this project's files; `let`/`const`/`var`; the one number
      type and the money rule; `null` vs `undefined`; `==` vs `===` with the
      coercion table; truthiness and the `||` vs `??` bug that would tell a
      user with 0 trial questions that they have 10; template literals;
      objects, arrays, `map`/`filter`/`reduce`, destructuring, spread,
      optional chaining; functions, arrow functions, closures, callbacks and
      `this`; the DOM, the browser's single-threaded event loop, event
      listeners and why they must be removed, custom events as decoupling,
      and the three storage places as a security decision; callbacks →
      promises → async/await; `fetch` and why it does not reject on a 404;
      `apiFetch` read line by line including in-flight de-duplication; the SSE
      reader and `buffer = blocks.pop()`; errors; modules; classes and
      prototypes; 10 beginner mistakes; how companies use this; 15 exercises
      with full answer key; senior critique; 5 interview questions;
      validation checklist
- [x] `09-typescript.md` — types as an engineering idea, in 14 parts: the
      silent-`undefined` problem; what a type is at the level of bytes; static
      vs dynamic checking as a trade-off, not a ranking; why JavaScript's
      dynamism stopped scaling; the four earlier attempts (JSDoc, Dart, Flow,
      Closure) and why "every valid JS file is already valid TS" won; type
      erasure and its three consequences; the compiler's four internal stages;
      structural vs nominal typing; annotations, inference, interfaces vs
      `type`, optional vs `| null`, literal unions, narrowing, generics,
      `any`/`unknown`/`never`, and assertions as unverifiable promises;
      `strict: true` and the billion-dollar mistake; the full anatomy of the
      `workspaceId` incident — an HR feature that had never once worked, fixed
      at the type because no test could exist; where TypeScript stops and why
      Pydantic exists on the other side; three real repository types read line
      by line; beginner and production mistakes; how to read a `TS2345` error;
      15 exercises with reasoning-based answers; senior critique (80 `any`s,
      duplicated vocabularies, unvalidated responses); 5 interview questions;
      validation checklist
- [x] `10-sql-from-zero.md` — the database before the library, in 15 parts:
      the six problems files cannot solve; hierarchical and network databases
      and why pointer-chasing failed; Codd, data independence and the query
      planner; tables, columns, types and the cost of a wrong one; `NULL`,
      three-valued logic, and `NOT NULL` as a tenancy control; primary keys
      with the UUID-vs-integer argument; foreign keys, referential integrity,
      `ON DELETE CASCADE` and its danger; unique constraints as race-proof
      checks; the four-table document hierarchy as an ER diagram;
      relationships, normalisation taught through its three anomalies, and
      when to denormalise on purpose; SQL itself — SELECT, WHERE, GROUP BY,
      HAVING, every join type, CTEs — ending with this project's real
      retrieval query written as raw SQL and read line by line; indexes,
      B-tree internals, what an index costs, composite column order, HNSW for
      vectors, and `EXPLAIN ANALYZE`; transactions, ACID, the write-ahead log,
      isolation levels, locks and deadlock; a full analysis of the trial-limit
      TOCTOU race with three costed fixes; constraints as the last line of
      defence; beginner and production mistakes including SQL injection, N+1,
      and the two timestamp conventions; five debugging techniques including
      `pg_stat_activity`; 15 exercises with reasoning-based answers; senior
      critique; 5 interview questions; validation checklist
- [x] `11-caching-concepts.md` — caching and Redis: the repeated-work problem,
      locality, cache hit/miss/hit-rate, the cache layer ladder and why a
      shared cache is needed; Redis history, single-threaded internals, data
      types, persistence and the durability trade; cache key design with the
      four inputs that change the answer; five invalidation strategies;
      Incident One (the purge pattern that matched nothing, so deleted
      documents were still answered from cache) and Incident Two (the missing
      library that made a dependency failure indistinguishable from a cache
      miss, silently disabling three features); the real read/write path read
      line by line including `finally: close()`; five situations not to cache;
      eviction, hit-rate measurement, the command budget, stampede,
      penetration and hot keys; 15 exercises with reasoning-based answers;
      senior critique; 5 interview questions; validation checklist

---

## Part 2 — The system, subsystem by subsystem

- [x] `12-background-jobs.md` — queues and workers from zero, in 19 parts: the
      six things that break when slow work sits in a request; synchronous vs
      asynchronous and the test for which you need; queues from first
      principles (producer, consumer, decoupling, and why a queue smooths
      rather than accelerates); building a queue by hand to discover the six
      hard problems; brokers, what is actually in a message, and why JSON-only
      serialisation is a security control; workers, acknowledgement,
      at-least-once vs at-most-once, prefetch; Celery's five pieces with a
      complete runnable three-file example; the three-way rule and the C-2
      incident where four workspaces' tasks were routed, dispatched and never
      registered; the full upload journey mapped to real files with a sequence
      diagram; task states, retries with backoff, the `self.retry` trap and
      the guaranteed terminal state, idempotency (with an honest audit of
      which steps are and are not), dead letters; Beat and why exactly one;
      scaling, the `--concurrency=2` connection arithmetic, the
      `--max-tasks-per-child=0` crash loop, worker recycling and its 65.7s
      cost, and the fork/pool corruption incident; monitoring by queue depth
      and `inspect`; the ordered investigation for a stuck document;
      10 production mistakes; 15 exercises with reasoning-based answers;
      senior critique; 5 interview questions; validation checklist.
      **Study time: 4–5h**
- [x] `13-fastapi.md` — how a request becomes Python, in 21 parts: the fifteen
      things you would have to write yourself, and inversion of control; the
      history from CGI through WSGI to ASGI and why each died; Uvicorn vs
      Starlette vs FastAPI vs Pydantic; **the complete seventeen-step life of
      one request**, each step mapped to a real file; routing, the 24-router
      structure, path/query/body parameters and the doubled-prefix bug;
      Pydantic validation, 422 vs 400 vs 404, and `response_model` as a
      security filter; dependency injection explained without magic, the
      `yield` session dependency, and why streaming breaks dependency
      lifetimes; middleware, the onion, the order surprise, and all six layers
      with what breaks without each; errors, the Sentry body-stripping hook,
      and why streaming changes the error model; SSE responses; OpenAPI and
      `/docs`; lifespan events and the shutdown gap; four real incidents (the
      dead WebSocket router, the `len(app.routes)` proxy metric, the blocking
      async endpoint, the doubled prefix); a status-code debugging table and
      procedure; 10 production mistakes; **a complete runnable Todo API built
      from an empty folder**; 15 exercises with reasoning-based answers; senior
      critique; 10 interview questions with model answers; validation
      checklist. **Study time: 4h**
- [x] `14-sqlalchemy-and-migrations.md` — the data layer, in 17 parts: the
      object–relational mismatch and the six things you must do with a raw
      driver (including SQL injection); raw drivers → query builders → ORMs
      with the Hibernate/ActiveRecord/SQLAlchemy history and why SQLAlchemy
      keeps SQL visible; the class↔table mapping, Core vs ORM, and the
      four-line declarative base; **sessions in depth** — unit of work,
      `flush` vs `commit` with the real foreign-key case, the identity map,
      one session per request, and `expire_on_commit=False`; querying, and why
      injection is impossible by construction; relationships, lazy loading,
      **the N+1 problem with real numbers**, the `3daf888` incident where a
      performance fix uncovered a cross-tenant read, four fixes and when each
      applies, and the guard that flagged the fixed code; engines, drivers,
      the two-engine invariant, pool settings, the connection budget and the
      19-hour outage from hardcoding it; migrations — what Alembic is, a real
      migration read line by line, autogenerate's traps, heads and merge
      revisions, safe vs unsafe changes, the three-deploy rename pattern, and
      why `downgrade()` is not a rollback plan; debugging; 10 production
      mistakes; **a complete runnable SQLAlchemy + Alembic demo from an empty
      folder that makes the N+1 visible in printed SQL**; 15 exercises with
      reasoning-based answers; senior critique; 6 interview questions;
      validation checklist. **Study time: 4h**
- [x] `15-auth-and-security.md` — authentication, authorisation and the real
      attack surface, in 16 parts: authN vs authZ and which fails more quietly;
      passwords — why not encryption, salt, key stretching, bcrypt, timing
      attacks, and the SHA-256 repair; staying logged in — sessions vs tokens
      with this project's connection-budget reason, JWT internals, the
      hardcoded-fallback-secret bug, algorithm confusion, access vs refresh
      tokens and the bug that made refresh useless; cookie storage and every
      attribute with what breaks without it; five attacks (XSS, CSRF, SQL
      injection, CORS, enumeration) each with mechanism, defence and the repo
      line that implements it; authorisation — RBAC, the four-times-repeated
      tenancy leak, the fail-closed session hook, the shared document-access
      helper, defence in depth and zero trust, and the honest note about inert
      row-level security; file uploads and the `object_key` arbitrary-file-
      delete incident with all three sinks; prompt injection and why the SQL
      fix cannot transfer; secrets; an auth-failure debugging table;
      12 production mistakes; 15 exercises with reasoning-based answers;
      senior critique; 10 interview questions with model answers; validation
      checklist. **Study time: 4–5h**
- [x] `16-ai-engineering-and-rag.md` — the AI system as one continuous
      pipeline, in 20 parts: what a model actually is (weights, frozen, no
      memory, cannot look anything up) and why hallucination is the expected
      behaviour rather than a bug; tokens, context windows, temperature and
      top-p, and **five reasons not to paste the whole PDF, only one of which
      is size**; the RAG idea with a full pipeline diagram; extraction and OCR
      and why extraction quality caps everything; chunking — naive splitting,
      overlap, and the real layout-aware chunker that keeps tables whole, with
      the arithmetic tying chunk size to retrieval width to prompt budget;
      embeddings — the map-of-meaning intuition, cosine similarity and why
      direction not distance, 1024 dimensions and the storage maths, bge-m3
      and `normalize_embeddings`, and **the 768-zero-padded-to-1024 fallback
      that silently corrupts a corpus**; retrieval — sparse/BM25, dense, what
      each structurally cannot do, why scores cannot be added, RRF worked
      through numerically, precision vs recall; reranking — bi-encoder vs
      cross-encoder, and **the min-max normalisation that makes the
      low-confidence threshold unable to fire**; prompt construction — token
      budget, document-order sorting, and evidence blocks labelled by code so
      **citations are copied rather than generated**; the real system prompt
      read in parts; streaming, key rotation and the truncation notice; the
      trust score told honestly as a cautionary tale and the rule it produced;
      evaluation — golden sets, precision@k, recall@k, MRR, groundedness,
      citation accuracy, refusal correctness; cost and latency with the levers
      used and not used; prompt injection and context poisoning; **the complete
      end-to-end journey in 16 steps**; 15 exercises with reasoning-based
      answers; senior critique; 10 interview questions with model answers;
      validation checklist. **Study time: 7–8h**
- [x] `17-deployment-and-production.md` — one continuous deployment story in
      20 parts: the seven differences between a laptop and production and the
      three properties production needs (reproducible, observable,
      recoverable); builds and artifacts, images vs containers, the real
      multi-stage backend Dockerfile line by line, the frontend's dev-vs-
      production targets and the `NEXT_PUBLIC_` build-time trap, layers and
      caching; configuration, fail-fast secrets and configuration drift;
      Compose, volumes, `depends_on: service_healthy`, and one honest
      paragraph on where Kubernetes fits; CI read step by step including the
      blocking `pip-audit` and why the ten env vars must be declared;
      deployment order — `alembic upgrade head && uvicorn`, restart policy,
      cold starts, and the three processes; reverse proxies, TLS, and **the
      two proxy settings that silently break streaming**; liveness vs
      readiness, the real `/health`, and the two incidents it made visible;
      observability — the three signals, structured JSON logs with correlation
      ids and PII redaction, Prometheus metrics, traces crossing the
      API/worker boundary, Sentry and PostHog, and the alerting gap; timeouts,
      retries, rate limiting, graceful shutdown, resource limits and backups;
      scaling and which resource binds first; rolling deploys and rollback;
      **the full production trace of one request**; a six-step debugging
      method; 12 production mistakes; 15 exercises with reasoning-based
      answers including a two-minute "how would you deploy this"; senior
      critique; 8 interview questions; validation checklist.
      **Study time: 4–5h**

## Part 3 — Converting knowledge into offers

- [x] `18-interview-capstone-and-career.md` — **a manual, not a chapter.** No
      new technical material; everything converts Ch. 01–17 into performance.
      Three rules (never claim what you cannot show · lead with the decision ·
      volunteer the weakness); the project story at four lengths — 30 s, 2 min,
      5 min in four movements, and five pullable threads for the deep version;
      a 16-decision defence deck, each as problem → choice → alternatives →
      trade-off → when I'd choose differently; the ten-step screen-share
      walkthrough with **where interviewers interrupt and what to say**; eight
      rehearsed incident stories from the real defect register (tenancy leak,
      blocked event loop, unregistered tasks, cache never invalidated, silent
      no-op, the health check that stopped two services, the connection budget,
      the metric that was a constant); question banks for HR, Python and
      concurrency, FastAPI, databases, AI/RAG, system design, deployment and
      security, each with model answer, common mistake and follow-up; six
      communication habits including the three-part "I don't know"; **the full
      60-minute capstone — 12 questions with rubric, scoring guide, and weak vs
      strong answers side by side**; career — four resume bullets, the five
      GitHub moves, tailoring by company type, and an honest read on the odds
      with the five actions that move them; master checklist for Ch. 01–17,
      the numbers revision table, one-day and one-week plans, three mock
      schedules, six interviewer traps, and the validation gate.
      **Study time: 1h reading + 3–4h drilling**
- [ ] `19-frontend-react-and-nextjs.md` — **Useful, defer if short on time.**
      Components, props, state, effects, rendering and re-render bugs, server
      vs client components, routing, and the shared `WorkspaceUI` design.
      ~9k · 3h

## Cut from the core guide (Advanced Learning, post-placement)

Kubernetes · microservices · PostgreSQL tuning at scale · dedicated vector
databases · model fine-tuning · distributed tracing depth · load and chaos
testing · multi-region and disaster recovery.

Merged rather than cut: Redis→11 · Celery/Beat→12 · Tailwind→19 ·
LLM fundamentals + RAG→16 · testing→13 and 17 · observability, CI/CD and
debugging→17 · cheat sheet, flashcards, mind map, career, validation gate and
capstone→18 · reverse-engineering and professional workflow→delivered inside
every chapter's exercises and critiques.

---

## File-coverage ledger

Every meaningful file in the repository must be covered somewhere. This
ledger is filled in as chapters are written, so nothing is silently skipped.

| Area | Files total (approx.) | Covered so far | Where |
|---|---|---|---|
| `backend/app/api/v1/api.py` | 1 | 1 (full — router aggregation, prefixes, the removed WebSocket router) | 13 |
| `backend/app/main.py` | 1 | 1 (full — middleware chain, Sentry, router mounting, no lifespan) | 01, 13 |
| `backend/app/api/v1/endpoints/` | 24 | 4 (`query.py` partial, `health.py` partial, `csrf.py` full, `documents.py` list/get/verify/delete) + tenancy findings referenced in `chats.py`, `documents.py`, `exams.py`, `export.py`, `legal.py`, `finance.py`, `hr.py`, `study.py`, `research.py` | 01, 02, 03 |
| `backend/app/core/` | 17 | 6 (`auth.py`, `config.py`, `middleware.py`, `workspace.py`, `tenant_scope.py` full, `document_access.py`) | 01, 02, 03 |
| `backend/app/services/` | 27 | 7 (`grounding_service.py`, `retrieval_service.py`, `llm_service.py` incl. prompt builder, `chunking_service.py`, `embedding_service.py`, `reranker_service.py`, `veritas_engine.py`) | 01, 03, 16 |
| `backend/app/models/` | 24 | 5 (`document.py`, `document_page.py`, `document_chunk.py` full; `chat.py`, `org.py` partial) | 06, 10 |
| `backend/app/core/trial_enforcement.py` | 1 | 1 (full — race analysis) | 10 |
| `backend/app/core/redis_client.py` | 1 | 1 (full — the silent-no-op incident) | 06, 11 |
| `backend/app/api/v1/endpoints/documents.py` | 1 | partial (upload flow, cache purge block) | 01, 11 |
| `backend/app/schemas/` | many | 1 (`query.py` full — 4 Pydantic models) | 06 |
| `backend/app/db/` | 2 | 2 (`session.py` full, `base.py` full) | 02, 14 |
| `backend/alembic/` | 46 versions + env | env.py + 2 migrations read in full | 14 |
| `backend/app/workers/` | 12 | 2 (`celery_app.py` full; `document_tasks.py` full) | 02, 12 |
| `frontend/src/app/` | ~30 pages | 0 | — |
| `frontend/src/components/` | many | 0 | — |
| `frontend/src/lib/` | `api.ts` + stores | 2 (`api.ts` — `apiFetch` and the SSE reader read in full; `analytics.ts` full) | 01, 08 |
| `frontend/src/hooks/` | 6 | 2 (`useTheme.ts`, `useSessionExpiry.ts` full) | 08 |
| `infrastructure/` | 4 | 1 (`docker-compose.yml`, partial) | 01, 02 |
| `infrastructure/Dockerfile.backend` | 1 | 1 (full — stages, apt packages, ENV, CMD) | 05, 17 |
| `infrastructure/Dockerfile.frontend` | 1 | 1 (full — dev/prod targets, build-time env) | 17 |
| `railway.json` | 1 | 1 (full — build, start command, restart policy) | 17 |
| `backend/app/core/` observability | 3 | 3 (`telemetry.py`, `json_logger.py`, `rate_limiter.py`) | 17 |
| `.github/workflows/ci.yml` | 1 | 1 (partial — triggers, env block, services) | 05 |
| `.env.example` / `.gitignore` | 2 | 2 (partial — required/secret markers, ignore rules) | 05 |
| `.claude/agents/` | 11 | 11 (all — question, trigger, boundary, tool grant, model) | 04 |
| `CLAUDE.md` (orchestration section) | 1 | 1 (responsibility hierarchy, registry, trigger modes, delegation matrix, lifecycles, skill policy) | 04 |

---

## Living-document state

- `GLOSSARY.md` — ~425 terms. Ch. 18 added only 3 (incident story, referral,
  rubric) — it introduces no new technology, so almost nothing was owed, and
  padding the glossary to look productive would defeat its purpose.
  Ch. 17 added 13
  production entries (artifact,
  image, layer, liveness, readiness, reverse proxy, rolling deployment,
  structured logging, distributed trace, alerting, configuration drift),
  inserted in place. Ch. 16 added 13 AI entries (LLM, hallucination,
  attention, temperature, bi-encoder, cross-encoder, BM25, precision, recall,
  groundedness, golden set, context poisoning), inserted in place. Ch. 15 added
  13 security entries
  (authentication, authorisation, bcrypt, salt, timing attack, HttpOnly,
  SameSite, XSS, RBAC, defence in depth, zero trust), inserted in place.
  Ch. 14 added 13 data-layer entries (ORM,
  session, unit of work, identity map, engine, driver, lazy loading, eager
  loading, migration, Alembic, autogenerate), inserted in place. Ch. 13 added
  13 web-framework entries (ASGI,
  WSGI, web framework, inversion of control, FastAPI, Starlette, Uvicorn,
  OpenAPI, routing, router, response model, dependency injection), inserted in
  place. Ch. 12 added 13 queue entries (acknowledgement,
  at-least-once, at-most-once, backoff, broker, dead-letter queue, decoupling,
  idempotent, polling, prefetch count, producer/consumer, queue depth, Celery
  task), inserted in place. Ch. 11 added 11 caching entries (cache, cache
  hit/miss, cache penetration, cache stampede, eviction policy, hash function,
  hit rate, invalidation, locality, write-through), inserted in place. Ch. 10
  added 19 database entries (ACID, B-tree,
  CHECK constraint, CTE, deadlock, EXPLAIN, HNSW, isolation level, join, lost
  update, N+1, normalisation, query planner, referential integrity, SQL, SQL
  injection, TOCTOU, transaction, WAL), inserted in place. Ch. 09 added 18
  TypeScript entries (any, unknown,
  void, assertion, erasure, generic, inference, literal union, narrowing,
  nominal vs structural typing, static vs dynamic checking, strict mode,
  superset, TypeScript itself), inserted in place rather than by rewriting the
  file. Ch. 01–07 as before, plus ~24 from ch. 08's
  JavaScript vocabulary: array, arrow function, callback, closure, coercion,
  custom event, destructuring, DOM, ECMAScript, event listener, fetch,
  in-flight de-duplication, localStorage, Node.js, null, nullish coalescing,
  optional chaining, promise, prototype, recursion, sessionStorage, spread,
  template literal, ternary, undefined). Shared entries — `await`, `module`,
  `object`, `truthiness`, `short-circuit`, `REPL` — now carry both chapters.
- `ENGINEERING_DECISIONS.md` — D-001 … D-093 recorded. **D-093 added in ch. 18
  is the only decision that chapter produced** — publish the known-gaps list in
  the public README. No others were added, because Chapter 18 makes no
  technical choices; inventing entries to fill the file would be exactly the
  padding the register exists to prevent.
- D-088 … D-092 added in
  ch. 17: migrations gated before start-up by `&&` · a production frontend
  target with build-time configuration · CI against real dependencies with a
  blocking security audit · health checks that test dependencies plus
  `depends_on: service_healthy` · structured JSON logs with correlation ids and
  PII redaction.
- D-083 … D-087 added in
  ch. 16: layout-aware chunking that refuses to split tables · bge-m3 run
  locally with normalised vectors · cross-encoder reranking and the
  normalisation defect that disables the confidence gate · evidence blocks
  labelled by code so citations are copied not generated · the trust score
  that was mostly constant, and the rule it produced.
- D-078 … D-082 added in
  ch. 15: bcrypt replacing SHA-256 · signed tokens over sessions with the
  revocation cost accepted · two independent CSRF defences · client-supplied
  storage paths validated at one choke point · prompt injection treated as
  unfixable and bounded architecturally.
- D-074 … D-077 added in
  ch. 14: SQLAlchemy with SQL deliberately visible · N+1 fixed by
  consolidation and guarded by query count · `expire_on_commit=False` on the
  async session · migrations as versioned history with reasoning in the file.
- D-069 … D-073 added in
  ch. 13: FastAPI on ASGI chosen for waiting and streaming · authentication as
  a dependency rather than middleware · validation at the boundary with
  Pydantic · a middleware chain whose order is deliberate · Sentry strips
  request bodies before reporting.
- D-064 … D-068 added in
  ch. 12: the database row is the source of truth and the queue only a request
  to act · enqueue failure marks the document FAILED and returns 503 · retries
  with backoff, a ceiling and a guaranteed terminal state · batched commits in
  the pipeline · exactly one Beat instance while workers scale freely.
- D-061 … D-063 added in
  ch. 11: cache the retrieved evidence rather than the generated answer · one
  function builds the cache key and its prefix is an invariant · Redis
  unavailability degrades the feature but is logged loudly, once per process.
- D-057 … D-060 added in
  ch. 10: UUID primary keys everywhere · cascade deletes for data with no
  independent meaning · an HNSW index with explicit parameters, accepting
  approximate results · counter increments computed in the database, with the
  remaining TOCTOU window recorded rather than left implied.
- D-054 … D-056 added in
  ch. 09: TypeScript with `strict: true` for the browser code · fixing a class
  of bug at the type when no test could exist · compile-time checking in the
  browser with runtime validation at the server, and the drift gap that leaves.
- D-050 … D-053 added in
  ch. 08: one wrapper for every network call · in-flight de-duplication for
  the token refresh · cross-cutting signals as browser custom events ·
  analytics helpers shaped so private data is hard to send.
- D-045 … D-049 added in
  ch. 07: an async request path justified by the 86%-waiting arithmetic · CPU
  work offloaded with guards that measure the loop rather than the source ·
  async request path with fully synchronous workers, never mixed · a
  `threading.Lock` chosen to match the real interleaving surface · streaming
  as async generators, with the tenant scope deliberately not tied to a
  `yield` dependency.
- D-040 … D-044 added in
  ch. 06: identity tests instead of truthiness where empty and absent differ ·
  narrow `except` clauses with a loud log when a broad catch is unavoidable ·
  Pydantic at trust boundaries and dataclasses inside · enums with `str` mixed
  in for fixed state sets · required positional parameters as a security
  control.
- D-034 … D-039 added in
  ch. 05: bind `0.0.0.0` and read `PORT` from the environment ·
  `PYTHONUNBUFFERED=1` · TLS required for remote hosts but never forced
  locally · a hermetic multi-stage build wheeling the full dependency
  closure · JSON-only job serialisation as a security control · host port
  remapping to avoid collisions.
- D-026 … D-033 added in
  ch. 04: a roster of narrow specialists split by question · specialists
  verify while only the coordinator writes code · mediated communication with
  no agent-to-agent calls · per-agent tool grants and model assignment ·
  one uniform output contract with three-valued confidence · two trigger modes
  (age is a trigger, not a defence) · deliberate cross-agent duplication with
  a same-commit sync rule · one QA agent for seven workspaces.
- D-019 … D-025 added in
  ch. 03: session-layer tenancy enforcement that fails closed · 404 not 403 to
  avoid an enumeration oracle · a class ratchet keyed by identity not line
  number · per-step rather than whole-stream timeouts · a synchronous ref as
  the re-entrancy guard · refuse rather than answer when documents cannot be
  loaded · one module owning document read access.
- Earlier entries D-001 … D-018:
  hybrid search + RRF · rerank-after-retrieve · `run_in_executor` for CPU
  work · Python-written citations · extract-then-compute · `owner_id` as
  tenant key · work off the request path · SSE over WebSockets · course doc
  placement · modular monolith · Python for the ecosystem · one PostgreSQL
  for vectors · JWT in an httpOnly cookie · `uuid5` workspace identity ·
  fail-fast configuration · telemetry off by default · Redis as broker and
  cache · storage as an interface.

---

## Homework and critiques delivered

| Section | Homework | Answer key | Senior critique |
|---|---|---|---|
| Ch. 01 — Big picture | 5 checkpoint questions | Yes — in `02-system-design.md` Part J.1 | — (orientation chapter) |
| Ch. 02 — System design | 3 concept questions · 1 debugging challenge · 1 small design (30 min) · 1 mini architecture exercise (team accounts) | Yes — Part J.2 | Yes — Part K: 7 strengths, 7 weaknesses, readability, production verdict, 2 priority improvements |
| Ch. 18 — Interview, capstone, career | The whole chapter is exercise: 4 story lengths, 16 decision defences, 8 incident stories, 8 question banks, a 10-step walkthrough, 3 mock schedules, a one-day and a one-week plan | Yes — the 12-question capstone in Part H carries a rubric, a scoring guide, and weak/strong answers per question, which replaces a conventional answer key | Yes — Part J.7 (weak vs excellent side by side) and J.6 (interviewer traps) are the critique, aimed at the *answers* rather than the code |
| Ch. 17 — Deployment and production | 15 exercises: explaining images to a non-technical person, the layer-caching order, the `NEXT_PUBLIC_` trap, liveness vs readiness, the PgBouncer port incident chain, diagnosing "streaming stopped streaming", what breaks when you run three API instances, a three-deploy plan for a required column, a full backup strategy, and the two-minute deployment answer | Yes — Part Q, all 15 | Yes — Part R: 8 strengths, 8 weaknesses, the one improvement first (graceful shutdown, with backups a close second) |
| Ch. 16 — AI engineering and RAG | 15 exercises across 5 levels: explaining hallucination and why instructions cannot fix it, computing corpus storage, giving a question each retrieval method fails and why, working RRF numerically, explaining why the rerank threshold can never fire, diagnosing "answers only cover the first pages" at three pipeline stages, and designing the full evaluation with a first experiment | Yes — Part Q, all 15 | Yes — Part R: 8 strengths, 7 weaknesses, the one improvement first (build the golden set) |
| Ch. 15 — Auth and security | 15 exercises: correcting a colleague on JWT encoding, explaining algorithm confusion, walking a CSRF attack through three defence states, arguing whether CORS is a server-side control, defending fail-closed tenancy, retelling the `object_key` incident, and listing every check a document endpoint needs with status codes | Yes — Part M, all 15 | Yes — Part N: 8 strengths, 7 weaknesses, the one improvement first (a revocation list checked at refresh) |
| Ch. 14 — SQLAlchemy and migrations | 15 exercises across 5 levels, plus a runnable ORM demo built from an empty folder where the N+1 appears in printed SQL; includes writing a query and its SQL, explaining the guard that flagged correct code, reproducing the connection budget, writing the three-deploy rename plan, and diagnosing multiple Alembic heads | Yes — Part M, all 15 | Yes — Part N: 8 strengths, 7 weaknesses, the one improvement first (write the safe-migration policy and fail CI on unacknowledged `drop_column`) |
| Ch. 13 — FastAPI | 15 exercises across 5 levels, plus a complete Todo API built from an empty folder and broken four ways on purpose; includes fixing a leaked password hash with one change, distinguishing two causes of a 404, diagnosing a blocking async endpoint with two correct fixes, designing a PATCH endpoint with every error case, and writing the missing lifespan handler | Yes — Part R, all 15 | Yes — Part S: 8 strengths, 7 weaknesses, the one improvement first (a lifespan handler with real shutdown) |
| Ch. 12 — Background jobs | 15 exercises across 5 levels: explaining producer/consumer without software, auditing `process_document` for idempotency step by step, writing the smallest change that makes it repeatable, running the stuck-document investigation, designing the missing stuck-job detector including how it could cause harm, choosing a delivery guarantee for payment receipts, and specifying the startup self-check that would have prevented C-2 | Yes — Part P, all 15 | Yes — Part Q: 8 strengths, 7 weaknesses, the one improvement first (make `process_document` idempotent) |
| Ch. 11 — Caching and Redis | 15 exercises across 5 levels: critiquing a `search:{query}` key by severity, rewriting it properly, walking Incident One's mismatch, proposing a structural fix for key drift, arguing both sides of caching the generated answer, and writing the ordered investigation for "the app got slower on Tuesday" | Yes — Part O, all 15 | Yes — Part P: 6 strengths, 6 weaknesses, the one improvement first (log the purge result, including zero) |
| Ch. 10 — SQL from zero | 15 exercises across 5 levels written against this project's real tables: from `SELECT filename` to finding READY documents with no chunks, designing a composite index with justified column order, arguing both sides of a denormalised counter, and walking the trial-limit race interleaving before writing the one-statement fix | Yes — Part L, all 15 | Yes — Part M: 6 strengths, 7 weaknesses, the one improvement first (close the trial race with a conditional UPDATE) |
| Ch. 09 — TypeScript | 15 exercises across 5 levels, runnable in the TypeScript Playground with nothing installed: from a first annotation to replacing an `any` with `unknown` plus narrowing, earning the `localStorage` theme type instead of asserting it, explaining why `tsc --noEmit` proves more than a test, and analysing the two-sources-of-truth status drift with two costed fixes | Yes — Part K, all 15 | Yes — Part L: 5 strengths, 6 weaknesses, the one improvement first (generate frontend types from the backend's OpenAPI description) |
| Ch. 08 — JavaScript from zero | 15 exercises across 5 levels, all runnable in a browser console, from `2 + 3` to writing an SSE parser, the in-flight de-duplication pattern, and a `useTheme`-style setup function that returns its own cleanup; includes the `0 \|\| 10` trial-count bug and diagnosing a missing `await` on `fetch` | Yes — Part N, all 15 | Yes — Part O: 6 strengths, 5 weaknesses, the one improvement first (convert `askQuestionStream` to an options object) |
| Ch. 07 — Async Python | 15 exercises across 5 levels, from `await asyncio.sleep` to writing the executor-pumped blocking-iterator generator from `llm_service`; includes reproducing the loop-starvation defect in five lines, diagnosing a blocking `requests.get` inside a coroutine, and writing the heartbeat test that proves the fix | Yes — Part O, all 15 | Yes — Part P: 5 strengths, 5 weaknesses, the one improvement first (a dedicated, size-bounded executor for model inference) |
| Ch. 06 — Python from zero | 15 exercises across 5 levels, starting at "store a number and print it" and ending at simplified versions of real repository code (`resolve_workspace_id`, the token-budget loop, a `timed` decorator); includes the mutable-default bug, the bare-except critique, and duplicate removal with a justification of the data structures chosen | Yes — Part R, all 15 | Yes — Part S: 5 strengths, 5 weaknesses, the one improvement first (a type checker in CI) |
| Ch. 05 — Computing foundations | 15 exercises across 5 levels, starting at "type `pwd` and say what it means" and ending at explaining statelessness → CSRF tokens unaided; includes byte arithmetic, reading a real `uvicorn` command, a "connection refused" diagnosis procedure, and the repeating-health-check amplification question | Yes — Part O, all 15 | Yes — Part P: 6 strengths, 5 weaknesses, the one thing to fix first (graceful shutdown) |
| Ch. 04 — Agents and orchestration | 12 exercises across 5 levels, incl. reviewing a badly-specified agent definition (8 problems), diagnosing a worthless agent report, finding the single point of failure in the roster, and designing a 4-agent roster for a payment service | Yes — Part K, all 12 | Yes — Part L: 8 strengths, 6 weaknesses, the one improvement to make first (path-triggered mandatory invocation) |
| Ch. 03 — Engineering thinking | 12 exercises across 5 difficulty levels (recall → comprehension → application → analysis → synthesis), incl. a slow-system investigation, a PR review with 7 hidden problems, a real coding task (async consumption of a blocking iterator), and a full four-level treatment of hotel booking | Yes — Part H, all 12 | Yes — Part I: critique of the *reasoning practices*, 6 strengths, 5 weaknesses, the one habit to copy |

---

## Validation gate results

Filled in only at the end of the course (see `48-validation-gate.md`).

| Skill to prove | Attempted | Result |
|---|---|---|
| Explain the overall architecture unaided | no | — |
| Explain the backend flow unaided | no | — |
| Explain the frontend flow unaided | no | — |
| Explain the AI pipeline unaided | no | — |
| Explain the database unaided | no | — |
| Explain authentication unaided | no | — |
| Explain deployment unaided | no | — |
| Explain the agent orchestration unaided | no | — |
| Write a new FastAPI endpoint from a blank file | no | — |
| Write a new React component from a blank file | no | — |
| Write a new SQL schema from a blank file | no | — |
