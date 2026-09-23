# Engineering Decisions

Every real decision made in this project, written the way a senior engineer
would write it: the problem first, then the options, then the choice, then
what it cost.

This file grows through the course. It is not written once.

**How to read one entry.** The heading is the decision. `Problem` is what
forced a choice. `Options` are what a competent engineer would have
considered. `Chosen` is what this project does, with the file. `Why` is the
reasoning. `Tradeoff` is the price paid. `Industry` compares this to what
most companies do. `Later` is what could be improved.

---

## D-001 — Search by meaning *and* by keyword, then merge

**Problem.** A user asks "when do I have to move out?" The document says
"the lessee shall vacate the premises". Keyword search finds nothing.
Another user asks about "clause 14.2(b)". Meaning search ranks it poorly,
because a clause number carries almost no meaning to an embedding model.
One search method alone fails a large fraction of real questions.

**Options.**
1. Vector search only. Simple, one code path, one index.
2. Keyword search only. Cheap, exact, no model needed.
3. Both, merged by adding their scores together.
4. Both, merged by rank position (Reciprocal Rank Fusion).

**Chosen.** Option 4, in
[`backend/app/services/retrieval_service.py`](../backend/app/services/retrieval_service.py)
lines 179–221.

**Why.** The two methods fail in *different* situations, so together they
cover far more questions than either alone. Merging by score (option 3) is
tempting but wrong: `ts_rank_cd` returns a small unbounded relevance number
and cosine similarity returns roughly 0 to 1. Adding them means one silently
dominates. Positions are comparable even when scores are not, which is what
RRF exploits. The constant `rrf_k = 60` is the value from the original
research and it dampens the influence of a single first-place result.

**Tradeoff.** Two database queries per question instead of one. More code to
maintain. RRF throws away score *magnitude*, so a result that is much better
than second place gets no extra credit for it — the reranker later restores
that information.

**Industry.** Hybrid retrieval with RRF is the current mainstream default
for production RAG. Elastic, Weaviate, and Azure AI Search all ship RRF as
a built-in.

**Later.** Weighted RRF (giving vector or lexical more influence per
workspace) is a known improvement, but it needs evaluation data to tune, not
a guess.

---

## D-002 — Rerank after retrieval instead of retrieving fewer, better results

**Problem.** The cheap searches return roughly relevant text, but the order
is imperfect, and the AI model can only be given about five pieces. Sending
the wrong five produces a wrong answer even when the right text was found.

**Options.**
1. Trust the retrieval order, send the top 5.
2. Retrieve 30 and send all 30 to the model.
3. Retrieve 30, then rerank with a slower, more accurate model, send the
   best 5.

**Chosen.** Option 3, in
[`backend/app/services/grounding_service.py`](../backend/app/services/grounding_service.py)
lines 66–102. The retrieval width is `retrieval_top_k: int = 30` and the
final selection is `final_top_k: int = 5`.

**Why.** This is the standard two-stage design used across search: a fast,
approximate stage to reduce millions to dozens, then an expensive, accurate
stage on the dozens. The reranker is a **cross-encoder**: it reads the
question and one passage *together* and scores the pair. That is much more
accurate than comparing two separately-computed embeddings, and much too
slow to run over a whole database.

**Tradeoff.** The cross-encoder is the single biggest CPU cost of a query —
up to 30 pairs at 512 tokens each. That cost caused a real production
defect, see D-003.

**Industry.** Standard. `ms-marco-MiniLM-L-6-v2` (used here) is the common
small cross-encoder; larger systems use bigger rerankers or a hosted rerank
API.

**Later.** Cache rerank scores per (query hash, chunk id), and skip
reranking entirely when the top RRF result is far ahead of the rest.

---

## D-003 — Move CPU-heavy model calls off the event loop

**Problem.** FastAPI serves many requests at once using a single-threaded
**event loop** — a loop that runs a bit of one request, then a bit of
another, switching whenever a request is waiting on something. That trick
only works if no piece of code hogs the loop. The embedding model and the
reranker are pure CPU work that took seconds, and they were called directly.
While one user's question was being embedded, **every other user's request
was frozen**.

**Options.**
1. Leave it and add more server processes to hide the problem.
2. Move the model work to a Celery worker and wait for the result.
3. Run the blocking call on a thread pool with `run_in_executor`.

**Chosen.** Option 3, in
[`retrieval_service.py:56`](../backend/app/services/retrieval_service.py) and
[`grounding_service.py:94`](../backend/app/services/grounding_service.py).

```python
loop = asyncio.get_running_loop()
query_vector = (
    await loop.run_in_executor(
        None, embedding_service.generate_embeddings, [query]
    )
)[0]
```

**Why.** The work is short (hundreds of milliseconds), needed immediately
for the answer, and already loaded in this process's memory. Sending it to a
worker (option 2) adds queue latency and a second copy of a large model in
memory, for no benefit. Option 1 hides a bug behind hardware spending.

**Tradeoff.** Threads share memory, so the model must be safe to call from
several threads; and the default thread pool is shared, so a flood of
queries can still saturate it. The real fix bounds concurrency, not just
moves it.

**Industry.** This is the single most common async mistake in Python web
services. Every framework's documentation warns about it, and it still
happens constantly.

**Later.** A dedicated, size-limited executor for model calls, so embedding
work cannot starve other thread-pool users.

---

## D-004 — Citations are written by Python, not produced by the model

**Problem.** If you ask a language model to cite its sources, it will happily
invent a page number that looks plausible. A citation you cannot trust is
worse than no citation, because it *creates* false confidence.

**Options.**
1. Ask the model to cite, and hope.
2. Ask the model to cite, then verify each citation afterwards.
3. Label every piece of evidence with its true source *before* the model
   sees it, so the model can only copy a label that is already correct.

**Chosen.** Option 3, in
[`grounding_service.py:132`](../backend/app/services/grounding_service.py):

```python
context_block = (
    f"<evidence document=\"{candidate['filename']}\" "
    f"page=\"{candidate['page_number']}\" "
    f"chunk_id=\"{candidate['chunk_id']}\">\n"
    f"{candidate['text_content']}\n"
    f"</evidence>"
)
```

**Why.** The filename and page number come from database rows written during
document processing. They are facts, not generations. The model's job is
reduced from "know where this came from" to "repeat the label attached to
the text you used" — a far easier task with a far smaller failure surface.

**Tradeoff.** The model can still attach the wrong label to the right
sentence when several evidence blocks are present. It reduces the problem;
it does not eliminate it. That residual risk is what the trust score exists
to measure.

**Industry.** This is the correct pattern and is what serious RAG products
do. The naive "please cite your sources" prompt is a known anti-pattern.

**Later.** Post-generation verification (option 2) *in addition*: check that
each cited page actually contains supporting text.

---

## D-005 — The same "extract then compute" rule for every number

**Problem.** Financial ratios, legal escalation levels, and scores are
numbers a user may act on. A language model doing arithmetic will sometimes
produce a confident wrong number, and there is no way to see it happened.

**Options.**
1. Ask the model for the final numbers.
2. Ask the model to extract raw values, then compute in Python.

**Chosen.** Option 2, project-wide. It is recorded as an architectural
invariant in `CLAUDE.md` under "Extract-then-compute", and enforced in the
finance and legal services. The commit `c944a81` — *"fix(finance): stop
instructing the model to do the arithmetic"* — is the moment a violation was
removed.

**Why.** Extraction is a task models are good at (find the revenue figure in
this table). Arithmetic is a task they are unreliable at and Python is
perfect at. Splitting the task along that line makes an entire category of
error impossible rather than merely unlikely.

**Tradeoff.** More Python code, and every new ratio must be implemented by
hand instead of described in a prompt.

**Industry.** The general principle — use the model for language, use code
for determinism — is the strongest single reliability rule in AI
engineering.

**Later.** Nothing needed. This is the right design.

---

## D-006 — The tenant key is `owner_id`, and the database layer enforces it

**Problem.** In a multi-tenant system, one forgotten `WHERE` clause leaks
one customer's documents to another. Relying on every developer remembering
every filter, in every query, forever, is not a security control.

**Options.**
1. Filter by hand in each endpoint.
2. Use PostgreSQL Row-Level Security (RLS) so the database enforces it.
3. Enforce it in the ORM layer, so a query without a scope raises an error.

**Chosen.** Option 3, via `backend/app/core/tenant_scope.py` and the
`_set_request_owner` call in
[`core/auth.py:71`](../backend/app/core/auth.py). Every request binds the
current owner; an ORM read on a tenant-scoped model with no scope set
**raises** rather than returning unfiltered rows.

**Why.** Option 1 already failed here — the audit found multiple endpoints
scoped by `workspace_id`, which looks like a tenant key but is not: it is a
category slug (`uuid5` of "legal"), identical for every user in the system.
Several commits in the history (`0df7df9`, `a632b13`, `8fd0f22`) are exactly
this bug. Option 2 is present in the schema but **inert** — the app connects
as a superuser that bypasses RLS — so counting it as protection would be a
fabricated control.

**Tradeoff.** Raw SQL (`text()`) bypasses the ORM hook and must still be
scoped by hand. That exception is documented rather than hidden.

**Industry.** Large SaaS companies usually do both: RLS in the database
*and* a scoped repository layer. Doing neither, and trusting per-endpoint
filters, is unfortunately the most common state of real code.

**Later.** Make RLS real by connecting as a non-superuser role and setting
the session variable its policies key on — then the two controls are
independent and either one alone is enough.

---

## D-007 — Slow work leaves the web request

**Problem.** Extracting and indexing a 200-page scanned PDF takes minutes.
An HTTP request that takes minutes will be killed by a proxy, will hold a
database connection open the whole time, and will look broken to the user.

**Options.**
1. Do it in the request and raise every timeout.
2. Do it in a background thread inside the web process.
3. Put a job on a queue and have a separate worker process do it.

**Chosen.** Option 3: Redis as the queue, Celery as the worker, defined as
the `worker:` service in
[`infrastructure/docker-compose.yml`](../infrastructure/docker-compose.yml).

**Why.** Only option 3 survives a restart of the web process, can be scaled
independently (more workers without more web servers), and keeps heavy
machine-learning dependencies out of the request path's memory budget. A
background thread (option 2) dies with the process and takes the job with
it, with no record that it was ever running.

**Tradeoff.** Much more moving machinery: a broker, a worker, queue routing,
and a rule that a task must be registered *and* routed *and* have its queue
consumed. Break any of the three and the job silently never runs. This
project calls that the "worker three-way rule" precisely because it was
broken before.

**Industry.** Standard. Celery + Redis or RabbitMQ in Python; Sidekiq in
Ruby; BullMQ in Node; SQS + Lambda on AWS.

**Later.** Dead-letter handling and a visible per-document failure reason in
the UI, so a stuck document explains itself.

---

## D-008 — Stream the answer with Server-Sent Events, not WebSockets

**Problem.** A grounded answer takes several seconds to generate. Silence
for several seconds reads as "broken".

**Options.**
1. Wait, then send the whole answer.
2. WebSockets — a two-way, always-open connection.
3. Server-Sent Events — a one-way stream over ordinary HTTP.

**Chosen.** Option 3. The server writes labelled frames in
[`query.py`](../backend/app/api/v1/endpoints/query.py); the browser decodes
them at [`api.ts:355`](../frontend/src/lib/api.ts).

**Why.** The data only flows one way: server to browser. WebSockets add a
different protocol, a separate authentication story (cookies work
differently on the WebSocket handshake), reconnection logic, and proxy
configuration — all to solve a two-way problem this feature does not have.
SSE is plain HTTP: the same cookie, the same CSRF check, the same middleware
stack, no new infrastructure.

**Tradeoff.** The browser cannot send anything back on the same connection;
cancelling uses a separate mechanism (`AbortSignal`). Some proxies buffer
SSE and must be configured not to.

**Industry.** SSE is the standard choice for LLM token streaming — OpenAI,
Anthropic, and Google all stream over SSE-style HTTP rather than WebSockets.

**Later.** A `Last-Event-ID` based resume, so a dropped connection can pick
up where it stopped rather than restarting the answer.

---

## D-009 — Course document placement

**Problem.** The course needs a progress file, but the repository root
already has `PROGRESS.md`, which is the product's single source of truth for
implementation status. Two files with the same purpose-sounding name in one
repository is how split-brain documentation starts.

**Options.**
1. Put the course's progress file at the root and hope readers notice.
2. Put all course documents inside `LEARNING_GUIDE/`.

**Chosen.** Option 2. `LEARNING_GUIDE/PROGRESS.md`,
`LEARNING_GUIDE/GLOSSARY.md`, `LEARNING_GUIDE/ENGINEERING_DECISIONS.md`.

**Why.** One folder owns one concern. The root `PROGRESS.md` answers "what
is done in the product"; `LEARNING_GUIDE/PROGRESS.md` answers "what is
taught in the course". Keeping them in separate folders means neither can be
mistaken for the other by a future reader or a documentation checker.

**Tradeoff.** The course brief named `ENGINEERING_DECISIONS.md` without a
folder; this deviates from that by one path segment, deliberately, and says
so here.

---

## D-010 — A modular monolith plus two extra processes, not microservices

**Problem.** How many separately deployable programs should this system be?

**Options.**
1. One program doing everything, including document processing.
2. One web application, one background worker, one scheduler.
3. Microservices: an auth service, a document service, a query service, a
   billing service.

**Chosen.** Option 2. The three processes are the `backend`, `worker` and
`beat` services in
[`infrastructure/docker-compose.yml`](../infrastructure/docker-compose.yml).

**Why.** Microservices solve an *organisational* problem — many teams needing
to deploy without blocking each other. This project has one developer, so
there is no such problem to solve, and every microservice cost (network hops
between parts, distributed failure modes, several deployment pipelines,
distributed tracing needed to debug anything) would be paid for nothing.
Option 1 fails for a different reason: document processing takes minutes and
has completely different memory and time characteristics from a web request,
so it genuinely belongs in a different process.

**The rule this expresses:** split a system along lines where the *shape of
the work* differs (fast request vs slow batch vs scheduled), not along lines
where the *nouns* differ.

**Tradeoff.** The web app and the worker share code, so a bug in a shared
service breaks both, and both must be redeployed together. Accepted, because
the alternative is duplicating the shared services.

**Industry.** The modular monolith is the current mainstream default for
small teams; the industry has largely walked back the "microservices for
everyone" period of 2015–2020.

**Later.** The OCR path is the one genuine candidate for extraction, because
it may need a GPU machine. The design already anticipates this: OCR tasks are
routed to their own queue (`ocr_gpu_queue`), so a dedicated worker could take
that queue over with no change to any call site.

---

## D-011 — Python for the backend, because the document ecosystem is Python

**Problem.** Which language runs the API?

**Options.** Python; Node.js/TypeScript (same language as the frontend); Go
(fast, easy deployment); Java.

**Chosen.** Python 3.11 with FastAPI.

**Why.** Every high-quality tool this product depends on is Python: PyMuPDF
for PDF text, PaddleOCR and Docling for scanned pages, sentence-transformers
for the bge-m3 embedding model and the cross-encoder reranker. Choosing any
other language means either reimplementing that work or running a Python
service anyway — in which case you have two languages *and* an extra network
hop, for no gain.

**Tradeoff.** Python is slower at raw computation than Go or Java, and its
async model has sharp edges that this project cut itself on (D-003). Both
costs are real and both are outweighed by the ecosystem.

**Industry.** Standard. Nearly all document-AI and machine-learning backends
are Python for exactly this reason.

**Later.** Nothing. If a specific hot path ever needs raw speed, the answer is
a native extension for that path, not a language migration.

---

## D-012 — One PostgreSQL for both rows and vectors, not a separate vector database

**Problem.** Embeddings need a store that can compare them quickly. Should
that be a dedicated vector database?

**Options.** Pinecone (hosted); Qdrant or Weaviate (self-hosted); FAISS (an
in-process library); pgvector inside the PostgreSQL already required.

**Chosen.** pgvector, set as the default in
[`config.py:119`](../backend/app/core/config.py).

**Why — and the reasoning is arithmetic, not preference.** A 100-page
document produces about 200 chunks; each chunk stores ~1.8 KB of text and a
1024-dimension embedding at 4 KB, so ~1.2 MB per document. A thousand users
with twenty documents each is about 24 GB. That fits one PostgreSQL instance
comfortably. A second data store would mean a second thing to back up,
secure, monitor and pay for — and it would break transactional deletion:
"delete this document and all its chunks" is one transaction today, and would
become a two-system cleanup that leaves orphaned vectors whenever the second
system is unreachable.

**Tradeoff.** pgvector's approximate index is good but not the fastest option
at very large scale. At 24 GB the difference is irrelevant; at 24 TB it would
not be.

**Industry.** Splitting between a dedicated vector store and a relational
database is common and often premature. "Use the database you already have
until the numbers say otherwise" is the better default.

**Later.** The seam already exists: `VECTOR_BACKEND` selects the
implementation and all retrieval goes through one function, so swapping the
backend touches one file.

---

## D-013 — A signed token in an httpOnly cookie, not a server-side session

**Problem.** How does the server know who is making a request?

**Options.**
1. A session id in a cookie, with session data in a database or Redis.
2. A signed JWT in a cookie.
3. A JWT in browser storage (`localStorage`), sent as a header.
4. A hosted identity provider such as Auth0 or Clerk.

**Chosen.** Option 2 — see [`core/auth.py`](../backend/app/core/auth.py).

**Why.** A signed token is verified with a secret and some arithmetic — no
database lookup. Database connections are the scarcest resource in this
deployment (fifteen, project-wide), so adding a lookup to *every* request
would be the most expensive possible place to spend them. Option 3 is
rejected because JavaScript can read `localStorage`, so any cross-site
scripting bug becomes total account theft; an `httpOnly` cookie cannot be
read by JavaScript at all. Option 4 is excellent but costs money and puts an
external service in the login path.

**Tradeoff, and it is a real one.** A signed token cannot be revoked before
it expires, because nothing is stored server-side to delete. The mitigations
are a short access-token lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES: int = 60`)
plus a refresh flow. And because cookies are sent automatically by the
browser, this choice *creates* the CSRF problem — which is why
`CSRFMiddleware` and the double-submit token exist. Each defence creates the
need for the next; being able to explain that chain is the point.

**Industry.** Both patterns are standard. Sessions are preferred where
instant revocation matters (banking); tokens where request cost matters.

**Later.** A short revocation list in Redis for "log out everywhere",
checked only on refresh rather than on every request.

---

## D-014 — Workspace identity derived with `uuid5`, with no Workspace table

**Problem.** Seven fixed workspaces need a stable identifier that every
process agrees on, and some columns store it as a UUID while user rows store
a slug like `"legal"`.

**Options.**
1. A `workspaces` table with rows and generated ids.
2. An enum of hardcoded UUID constants.
3. Derive the UUID from the slug with `uuid5`, deterministically.

**Chosen.** Option 3, in
[`core/workspace.py`](../backend/app/core/workspace.py):
`uuid.uuid5(uuid.NAMESPACE_DNS, slug.lower())`.

**Why.** The workspaces are fixed categories, not user data. A table would add
a migration, a join, and a seeding step to guarantee something that is already
guaranteed by arithmetic: `uuid5` of the same name is the same value in every
process, forever, with no coordination. It also accepts a real UUID
unchanged, so both storage styles work through one function.

**Tradeoff, stated in the code.** The derivation is one-way: you cannot
recover `"legal"` from the UUID. Therefore the slug must be stored at write
time wherever it is needed later. That cost is accepted knowingly, which is
what makes it a tradeoff rather than a mistake.

**Industry.** Deterministic ids for fixed categories are a good, underused
pattern. A table is the right answer the moment users can create their own
workspaces.

**Later.** If user-defined workspaces are ever added, the table becomes
necessary and `resolve_workspace_id` is the single place that changes.

---

## D-015 — Configuration fails fast: ten settings have no default

**Problem.** The same code runs on a laptop, in Docker, and on a cloud host
with different secrets and URLs. What happens when one is missing?

**Options.**
1. Sensible defaults for everything, so it always starts.
2. Required fields with no defaults, so a missing one crashes at startup.

**Chosen.** Option 2 for the ten fields that cannot have a safe default:
`AUTH_SECRET_KEY`, `CSRF_SECRET_KEY`, `FRONTEND_URL`, the four Postgres
fields, `REDIS_URL`, and the two Celery URLs — see
[`core/config.py`](../backend/app/core/config.py).

**Why.** A default secret key is not a convenience, it is a vulnerability
that looks like a working system. This exact bug existed here: `core/auth.py`
once fell back to a hardcoded development secret, meaning anyone who knew
that string could forge a token for any user. Crashing on boot with a clear
message is strictly better than booting successfully and being silently
insecure.

**Tradeoff.** A first-time setup is less forgiving; you must fill in the
environment file before anything runs. That is the correct direction for the
inconvenience to point.

**Industry.** Standard and correct. "Fail fast on missing configuration" is
one of the twelve-factor app principles.

**Later.** Extend the same principle to a startup self-check: refuse to start
in `ENVIRONMENT=production` when no real LLM key is present, instead of
serving mock answers with a CRITICAL log.

---

## D-016 — Telemetry defaults to off

**Problem.** OpenTelemetry and Prometheus are useful in production and
useless noise on a laptop with no collector running.

**Options.** Default on (production-shaped); default off (development-shaped).

**Chosen.** Off — `OTEL_ENABLED: bool = False`,
`PROMETHEUS_ENABLED: bool = False`
([`config.py:175`](../backend/app/core/config.py)).

**Why.** A default should describe the most common case, and the most common
case for this codebase is a developer's machine. With no collector attached,
every span export fails and the logs fill with errors that are not errors —
which trains the developer to ignore logs, which is how real failures get
missed. The comment also records that `config.py` and `.env.example`
previously disagreed on this value, which is its own kind of bug.

**Tradeoff.** Production deployments must remember to switch them on. That
belongs in a deployment checklist.

**Industry.** Mixed. Many teams default telemetry on and accept the noise.
Defaulting off with an explicit production toggle is defensible as long as
the toggle is in the deploy checklist.

---

## D-017 — Redis serves as both the job broker and the cache

**Problem.** The system needs a place to queue jobs and a place to cache
retrieval results.

**Options.** One Redis for both; Redis for cache and RabbitMQ for the queue;
a managed queue such as SQS.

**Chosen.** One Redis, configured as `CELERY_BROKER_URL`,
`CELERY_RESULT_BACKEND` and `REDIS_URL`.

**Why.** At this scale a dedicated broker is extra machinery with no benefit.
Redis is already required, is fast, and Celery supports it as a first-class
broker.

**Tradeoff — and this is the part to be able to say out loud.** Redis is not a
durable queue by default. If it dies with jobs in it, those jobs are gone.
That is survivable here because a lost job leaves a `PROCESSING` document row
that can be requeued; it would **not** be acceptable for payments or emails
that must be sent exactly once. Choosing a broker is really choosing what you
can afford to lose.

**Industry.** Redis-as-broker is extremely common for this scale. RabbitMQ or
SQS appear when delivery guarantees matter more than simplicity.

**Later.** Cache and broker on separate Redis databases or instances, so a
cache flush cannot touch queued work.

---

## D-018 — Storage is an interface, with local disk as the default

**Problem.** Uploaded files must be stored somewhere, on a laptop and in
production, without changing application code.

**Options.** Always S3; always local disk; one interface with both
implementations.

**Chosen.** The third: `STORAGE_PROVIDER: str = "local"` with an `s3` option,
validated at startup (`core/config.py` refuses `s3` without a bucket and
credentials), behind `core/storage.py`.

**Why.** Local disk means a new developer needs no cloud account to run the
project — that lowers the cost of the first hour, which matters more than
people admit. S3 is required in production because containers are
disposable: a file written inside a container is lost when it restarts.

**Tradeoff.** Two code paths to keep working, and the upload flow differs
slightly between them (a direct PUT for S3, a multipart POST for local) —
visible in [`frontend/src/lib/api.ts:198`](../frontend/src/lib/api.ts). That
divergence is a place bugs can hide, and it should be tested on both paths.

**Industry.** Standard. The interface-with-two-implementations pattern for
storage is close to universal.

**Later.** A third implementation for a cheaper object store, which should
require no application change if the interface is honest.

---

## D-019 — Tenant isolation enforced in the session layer, failing closed, with an explicit bypass

**Problem.** D-006 established *which column* is the tenant key. This decides
*where the filter is applied*. Roughly ninety queries filtered on the category
key alone and therefore returned every user's rows.

**Options.**
1. Add `owner_id ==` to all ninety `WHERE` clauses.
2. A shared helper function that endpoints are expected to call.
3. A session-level hook that injects the filter into every ORM select on a
   scoped model, and raises when no scope is set.

**Chosen.** Option 3, in
[`backend/app/core/tenant_scope.py`](../backend/app/core/tenant_scope.py).

**Why.** The module states the reasoning itself: option 1 *"duplicates one
decision across ninety sites, and the ninety-first query written next month
silently reintroduces the vulnerability. The layer that actually owns 'which
rows may this user see' is the session, not the call site."* Option 2 is
option 1 with extra steps, because nothing forces the call. Option 3 means a
new endpoint *cannot forget a filter it never writes*.

Two sub-decisions matter as much as the main one:

- **Fail closed.** With no scope established, the hook raises
  `TenantScopeMissing` instead of returning unfiltered rows. An unscoped
  query is a programming error, and the safest response to a programming
  error is to stop.
- **An explicit, greppable bypass.** Migrations, cleanup jobs and admin
  tooling legitimately read across tenants, so `system_scope()` exists — a
  bypass *you have to type*. Compare with a design where passing `None` skips
  filtering: that would be indistinguishable from forgetting.

**Tradeoff.** The hook is invisible: a query behaves differently from what its
source says, which surprises newcomers. It covers ORM reads only — raw
`text()` queries and all writes are outside it. Those limits are written in
the module docstring rather than assumed, because an overestimated control is
more dangerous than a known gap.

**Industry.** Well-established. Rails has default scopes, Django has managers,
Hibernate has filters. The distinguishing choice here is failing closed rather
than defaulting to unfiltered.

**Later.** Extend the same idea to writes, and make PostgreSQL RLS real so
that two independent layers enforce the same rule.

---

## D-020 — Cross-tenant access returns 404, never 403

**Problem.** When user B requests user A's document, which status code?

**Options.** 403 Forbidden (accurate: it exists, you may not have it); 404 Not
Found (indistinguishable from a nonexistent id).

**Chosen.** 404, stated explicitly in commit `24d55c0`: *"It returns 404 and
not 403 deliberately — 403 would confirm the id exists and belongs to
somebody, which is an enumeration oracle."*

**Why.** 403 leaks existence. An attacker can walk through identifiers and map
what your system contains without reading a single record. 404 tells them
nothing.

**Tradeoff.** Worse diagnostics for legitimate users, and worse debugging for
engineers, who cannot tell "I typed the wrong id" from "not mine" without
looking at logs.

**When to choose differently.** When existence is not secret and the user is
expected to act on the refusal — a corporate tool where "ask that department
for access" is the intended next step. Then 403 is more helpful and leaks
nothing that matters.

**Industry.** Both appear widely. GitHub famously returns 404 for private
repositories you cannot see, for exactly this reason.

---

## D-021 — A class ratchet keyed by identity, not by line number

**Problem.** Twelve instances of one tenancy defect existed; eleven could not
be closed immediately because the model had no owner column, and adding one
required an owner decision. Blocking all work was unrealistic; allowing new
violations was unacceptable.

**Options.**
1. Fix what can be fixed, note the rest in a document.
2. Fix what can be fixed, list the rest in a test allowlist keyed by line
   number.
3. The same, keyed by (module, function, model), with a second test that fails
   if a listed entry stops being a real violation.

**Chosen.** Option 3 —
`backend/tests/test_owned_model_reads_are_owner_scoped.py`.

**Why.** A document is not enforcement. And a line-numbered allowlist, in the
commit's words, *"rots on the first insertion above it and then gets
'repaired', which is how allowlists quietly grow."* Keying by identity
survives unrelated edits. The second test is what makes it a ratchet rather
than a list: entries can only be removed, never quietly kept after they stop
matching reality.

**The result that justifies it.** Writing the sweep found eight sites the
defect register never listed, and two models with no owner column at all. The
register documented four instances of a class that had at least twelve — *"it
was enumerating examples, not bounding the problem."*

**Tradeoff.** A mechanical check bounds exactly one shape. Three later
findings escaped it because they filtered on *neither* key, which the sweep
cannot see. That limit was written down at the time rather than discovered
later.

**Industry.** Common under names like "baseline files" or "suppression
lists" — for example ESLint or type-checker baselines in large migrations. The
identity-keyed detail is the part most teams get wrong.

---

## D-022 — A streaming timeout bounds each step, not the whole stream

**Problem.** A hung upstream held a request open forever, because
`generate_stream` had no timeout at all while the non-streaming path enforced
`LLM_TIMEOUT_SECONDS`.

**Options.**
1. No timeout (the original state).
2. A timeout on the whole stream.
3. A timeout on each individual step of the stream.

**Chosen.** Option 3, described in commit `4964ed6`: *"Each STEP is now
bounded by that same setting rather than the whole stream — total generation
time is legitimately long, but an individual chunk that never arrives is
not."*

**Why.** Option 2 cannot distinguish a slow-but-healthy long answer from a
dead connection, so any value is wrong: too low kills good answers, too high
fails to protect. The meaningful unit for a progressive operation is one
step.

**Tradeoff.** More bookkeeping, and a stalled stream is cut off mid-answer —
so partial output must still be delivered rather than discarded, which the
implementation does.

**Generalises to.** File downloads, database cursors, paginated API reads,
message consumers — anything progressive. Ask what unit the timeout should
bound before picking the number.

---

## D-023 — Re-entrancy guarded by a synchronous ref, not by the loading state

**Problem.** Two rapid clicks on Send persisted the same message twice. The
button was disabled by a state flag, but state updates in React are applied
on the next render, so the guard did not exist during the window where the
second click landed.

**Options.**
1. Disable the button harder (it was already disabled — this does not work).
2. Debounce the click handler by a fixed delay.
3. A synchronous flag (a ref) checked and set at the top of the handler,
   released on every exit path.

**Chosen.** Option 3, with the reasoning recorded in commit `4098ef6`: *"A ref
is the correct instrument precisely because the window exists due to state
being asynchronous; nothing else can close it."*

**Why.** The bug is caused by asynchrony, so the fix must be synchronous.
Debouncing (option 2) picks an arbitrary delay that is either too short to
close the window or long enough to feel unresponsive, and it hides the
problem rather than removing it.

**Tradeoff.** A flag outside the rendering system must be released manually on
every exit path — here there are five (two early returns, error, done, stop).
If you cannot count the exits, you cannot be sure it is released, which is
exactly how the same commit's second defect occurred.

**Industry.** Standard for user interfaces, and the same shape as an
idempotency key on the server. Serious systems use both: the client stops the
second send, and the server recognises it if one arrives anyway.

---

## D-024 — When the chat's documents cannot be loaded, refuse rather than answer

**Problem.** Loading a chat's history and attached documents was wrapped in a
handler that logged a warning and continued with an empty list.

**Options.**
1. Continue with no documents (the original behaviour).
2. Continue, but mark the answer as ungrounded.
3. Stop, tell the user, and never call the model.

**Chosen.** Option 3, in
[`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py).

**Why.** An empty list is not neutral in this system — it already means "this
chat has no documents", which legitimately produces a general-knowledge
answer. Reusing it for "we could not find out" merges two states, so a
transient database error silently produced a confident general answer to a
question about the user's own contract. Option 2 fails for the same reason:
the existing `mode: "general"` marker already means the first thing, so it
cannot also mean the second.

**Tradeoff.** A transient error now produces a visible failure instead of an
answer. That is the intended direction: the product's promise is grounding,
and an ungrounded answer that looks grounded costs more trust than an error
does.

**The generalisable rule.** Before using a default value on an error path,
check what that value already means elsewhere. Every state value must mean
exactly one thing.

---

## D-025 — One module owns "may this caller read this document"

**Problem.** Two endpoint files each carried a private helper that read
document text by id with no ownership check, and five `/process` routes each
resolved a caller-supplied document id their own way.

**Options.**
1. Fix each copy where it is.
2. One shared module that every caller routes through.

**Chosen.** Option 2 — `backend/app/core/document_access.py`, holding
`get_owned_document` and `get_owned_document_text`.

**Why.** The two private copies had *the same* missing check, which is the
signature of a duplicated decision rather than two independent bugs. Commit
`a83658b` puts it plainly: *"Two copies of one helper, both missing the same
check — which is exactly why the register says consolidate rather than patch
twice."* One definition means the next feature inherits the check instead of
re-deriving it.

**Tradeoff.** A shared module is a coupling point: every workspace now depends
on it, so a change there has a wide blast radius. That is the correct place
for the risk to sit, since the alternative distributes the risk somewhere
nobody is looking.

**Industry.** This is the standard remedy for duplicated authorisation logic,
and the shape most authorisation libraries assume.

---

## D-026 — A roster of narrow specialists rather than one general assistant

**Problem.** Recurring engineering questions — is this test real, is this a
security exposure, does this number mean anything — kept being answered
inconsistently or not at all.

**Options.**
1. One capable general assistant handling every task.
2. Agents split by subject area (backend, frontend, database).
3. Agents split by *question*, each owning one that no sibling may claim.

**Chosen.** Option 3 — eleven agents in
[`.claude/agents/`](../.claude/agents), with the registry table and the
one-sentence test in `CLAUDE.md`.

**Why.** Option 1 suffers context dilution: every rule added to one large
instruction weakens the others, and a component that both writes and approves
cannot review independently. Option 2 fails because subject areas overlap — a
tenancy defect is a backend file, a security question and an architecture
question simultaneously — so ownership stays ambiguous exactly where it
matters most. Splitting by question makes coverage something you can *reason
about*: "does any agent own this?" has an answer.

**The enforcing rule.** *"If you cannot state an agent's question in a single
sentence that no sibling could also claim, the roster is wrong — fix the
roster, not the prompt."*

**Tradeoff.** Strict single ownership forces handoffs, and handoffs lose
information. Accepted because diffuse ownership loses whole findings — proven
by the trust-score gap that three agents referenced and none could be invoked
for.

**When to choose differently.** Early exploratory work, where the recurring
questions are not yet known. Roles should be *discovered* from repeated
mistakes, not designed up front.

---

## D-027 — Specialists verify; only the coordinator writes code

**Problem.** If agents can implement, who reviews their work, and whose
architecture is it?

**Options.** Let each agent fix what it finds; let one agent implement and the
rest review; let a human implement everything.

**Chosen.** The second: *"The main engineering thread … is the only writer of
production code … No specialist implements."*

**Why.** Three reasons: independence (a reviewer that wrote the code is not a
reviewer), coherence (eleven cold-start authors would produce eleven styles
and no architecture), and accountability (exactly one component wrote any given
line). Every agent file repeats "you do not fix anything" for the cold-start
reason in D-032.

**Tradeoff.** The coordinator is a bottleneck and all implementation is
serialised through it. Accepted because it is the only component holding the
whole architecture, so serialisation was inevitable.

**Industry.** This is separation of duties, required in every audited
industry, and the reason most teams forbid self-merging a pull request.

---

## D-028 — Agents cannot invoke each other; all communication is mediated

**Problem.** Findings need to move between specialists — a detected secret
needs a severity verdict, a localised slow stage needs costing.

**Options.** Direct agent-to-agent calls; a mediated model where every result
returns to the coordinator, which decides what runs next.

**Chosen.** Mediated: *"They run in isolated contexts, cannot invoke each
other, and report back to the thread that called them."* The documented
handoff chains are explicitly *"thread-mediated"* — a call the coordinator
makes next, not one the agent makes.

**Why.** Loop prevention (A calls B calls A spends money forever),
attribution (every result has one known requester), and keeping decision
authority in the one place that sees the whole picture.

**Tradeoff.** The coordinator becomes a serialisation point and must
understand every handoff. That is also its job, so the cost lands where the
knowledge already is.

**Industry.** The same choice as an orchestrator/workflow engine versus a
free-for-all service mesh: slower, far easier to audit and debug.

---

## D-029 — Per-agent tool grants and per-agent model assignment

**Problem.** Every agent could be given every tool and the strongest model.
Should it be?

**Chosen.** No, on both axes. Tools are granted per agent — most get
`Read, Grep, Glob, Bash`; `security-reviewer` gets `Read, Grep, Glob` with
**no shell access**. Models are assigned by task shape: `opus` for open-ended
judgment (`code-reviewer`, `integrity-auditor`, `rag-pipeline-tracer`,
`security-reviewer`), `sonnet` for procedural checklists, `haiku` for
`docs-sync-checker`'s purely mechanical checks.

**Why the tool grant.** Least privilege. `security-reviewer` reads
authentication code, secret handling and upload paths, so it is the agent most
likely to encounter real credentials — and its instruction already forbids
reading `.env` contents. Removing execution means a confused or manipulated
invocation *cannot* exfiltrate or run anything. The capability is absent
rather than the behaviour discouraged.

**Why the model assignment.** Cost against capability, the same decision as
choosing instance sizes. `docs-sync-checker` runs at the start of every
session and does only checkable facts, so it runs on the cheapest model; its
frequency makes that saving the largest in the roster.

**Tradeoff.** A read-only security reviewer cannot verify a claim by running
anything, so some of its findings must be handed back for execution. Accepted.

**Later.** Several of `docs-sync-checker`'s checks are decidable and should
become a script; a cheap model reduces the cost of the anti-pattern without
removing it.

---

## D-030 — One uniform output contract, with three-valued confidence

**Problem.** Reports that must be *interpreted* cannot be *routed*, and a
report that cannot distinguish "I checked and it is fine" from "I could not
check" is dangerous.

**Chosen.** All eleven agents return the same ten sections, with four quality
bars: evidence must be a command and its output or `file:line` and real lines;
confidence is Verified / Partially Verified / **Unverified**; every blocker
carries a routing tag; and no padding.

**Why.** Uniformity makes findings routable and comparable. The three-valued
confidence exists for the same reason Chapter 03's `[]` bug did: *"Unverified
is a distinct verdict from 'fine' — never collapse 'I could not check this'
into 'no findings.'"* The no-padding bar exists because invented findings cost
the coordinator a verification pass it did not need.

**Tradeoff.** A rigid shape produces some ceremony on trivial results —
answered by the explicit rule that "no findings" is a complete report.

**Industry.** The same reasoning as structured logging over free-text logs:
you give up expressiveness and gain the ability to act on the output
mechanically.

---

## D-031 — Two trigger modes: age is a trigger, not a defence

**Problem.** Ten well-designed agents shared one structural defect: *"every
trigger is a change … Nothing owned code nobody was touching — which is where
the audit found the majority of the real defects."* Thirty-two high-severity
findings passed review because no agent could be invoked for untouched code.

**Options.** Accept that reviews are change-triggered and audit manually;
create a dedicated audit agent only; make standing-defect mode a first-class
trigger for the whole roster and add the one missing question.

**Chosen.** The third, in commit `bdc8308`: two documented trigger modes,
plus `integrity-auditor` for the question no sibling could answer, plus a
`symmetry` question added to `code-reviewer` and a guard-bites duty added to
`test-runner`.

**Why.** The sharpest case proved the hole was structural rather than an
oversight: three agents referenced the trust score, and none could be invoked
for it — one excluded computation by charter, one had unrelated triggers, and
the third's trigger ("the score disagrees with the answer") was *unreachable*
because the defect made the score constant. *"Coverage claimed in three
places, deliverable in none"* — the same shape as the guard whose docstring
claimed it was always called and which had zero callers.

**How it changes practice.** The rule *"A missing diff is never a reason to
decline"* means an agent must audit standing code when asked, with the claim
under test supplied in place of a diff.

**Generalises to.** Any monitoring, testing or on-call design: check whether
each trigger condition can actually occur during the failure it claims to
cover. Claimed coverage is not coverage.

---

## D-032 — Deliberate cross-agent duplication, with a same-commit sync rule

**Problem.** Several rules (the Turbopack restart, the `DummyLLMProvider`
warning) apply to more than one agent. Normally shared knowledge is
centralised.

**Chosen.** Duplicate the rule into every agent file that needs it, and
require that changing one changes all copies in the same commit.

**Why.** *"a cold subagent reads only its own definition, so a rule it does
not carry is a rule it does not have. Duplication is the cost of cold start;
pay it."* A shared file nobody loads is not shared — it is absent.

**Tradeoff.** Drift risk, paid for with an explicit maintenance rule rather
than avoided.

**The general principle.** DRY assumes every reader can see the shared source.
Where that assumption fails — cold-start agents, offline documents, safety
notices in separate rooms — duplication is correct and what you owe is a
synchronisation rule, not consolidation.

---

## D-033 — One QA agent for all seven workspaces

**Problem.** Seven workspaces with different business logic. Seven QA agents,
or one?

**Chosen.** One, deliberately: *"Per-workspace agents were rejected because
the defects here have not been workspace-shaped: the Legal contract bug lived
in a shared frontend handler, not in Legal code. You verify per workspace and
attribute per **layer**."*

**Why.** Agents should be split along the axis where *defects* vary, not where
the *product* varies. The register shows defects concentrating in shared code
— retrieval, tenancy, the composer, worker registration — so seven agents
would each have re-derived the same shared-code understanding and each missed
the same shared-code defects, at seven times the cost.

**Tradeoff.** One agent carries seven domains of context, which is exactly the
dilution D-026 warns about. It is accepted because attribution is per layer,
not per domain, so deep domain knowledge is not what the job requires.

**What would reverse it.** Repeated defects *inside* one workspace's own
business logic that a generalist misses — for example wrong ratio arithmetic
producing plausible numbers.

---

## D-034 — Bind to `0.0.0.0` and take the port from the environment

**Problem.** The same image must serve requests on a laptop inside Docker and
on a hosting platform that chooses the port itself.

**Options.**
1. Bind to `127.0.0.1` on a fixed port.
2. Bind to `0.0.0.0` on a fixed port.
3. Bind to `0.0.0.0` on a port read from the environment, with a default.

**Chosen.** Option 3, in
[`infrastructure/Dockerfile.backend`](../infrastructure/Dockerfile.backend):
`uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.

**Why.** `127.0.0.1` inside a container means "reachable only from inside this
container", so nothing outside can connect — and the symptom is a refused
connection with **no application error**, because the request never arrives.
`0.0.0.0` accepts on every interface, which is what a container needs.
Reading `PORT` from the environment lets Railway or Render assign a port
without a code change, and `:-8000` keeps the local default working.

**Tradeoff.** Binding to all interfaces is broader than binding to one. Inside
a container that is correct, because the container's network boundary is the
real control; on a bare host it would deserve more thought.

**Industry.** Universal for containerised services, and required by every
platform that injects `PORT`.

---

## D-035 — `PYTHONUNBUFFERED=1` in the image

**Problem.** Python buffers its output by default, writing it in batches. In a
container, logs then appear late or are lost entirely when the process
crashes — so the last thing you see is not the last thing that happened.

**Chosen.** `ENV PYTHONUNBUFFERED=1` in the Dockerfile.

**Why.** The ability to debug a crash from its final log lines is worth more
than the small throughput gain from buffering. Losing the evidence of a
failure at the moment of failure is the worst possible trade.

**Tradeoff.** Slightly more write syscalls. Irrelevant at this volume.

**Industry.** Standard in every Python container image; its absence is a
common cause of "the container died and there is nothing in the logs".

---

## D-036 — TLS required for remote database hosts, never forced for local ones

**Problem.** Managed databases require encrypted connections. An earlier
version forced TLS unconditionally.

**Options.** Always require; never require; require based on the host.

**Chosen.** Host-based, in
[`core/config.py`](../backend/app/core/config.py) with a shared
`LOCAL_DB_HOSTS` set and the same policy in `alembic/env.py`:

```python
if "sslmode=" not in url and not _is_local_db_host(url):
    url += ("&" if "?" in url else "?") + "sslmode=require"
```

**Why.** Unconditional TLS *"made every sync connection — health checks,
Celery workers — fail against non-SSL Postgres, including the project's own
docker-compose stack."* A security control that breaks local development gets
disabled wholesale, which leaves you worse off than a conditional one.

**Tradeoff.** A host list must be maintained, and a misconfigured host name
could skip TLS where it was needed. Mitigated by making the list explicit and
shared between the app and the migration tool rather than duplicated.

**A related detail worth its own note.** Two drivers spell the same option
differently — asyncpg wants `ssl`, psycopg2 wants `sslmode` and rejects
`ssl` — so `sync_database_url` exists largely to normalise between them. A
function whose only job is reconciling two vocabularies is a normal and
healthy thing to find at an integration boundary.

---

## D-037 — Multi-stage build that wheels the full dependency closure

**Problem.** The image must stay small, and the installed dependencies must be
exactly what the build resolved — not re-resolved at install time.

**Chosen.** A builder stage that runs `pip wheel` for the whole requirements
file, then a runtime stage that installs from those wheels with `--no-index`.

**Why.** `--no-index` makes the final install **hermetic**: everything must
come from the wheels already built, so *"the image cannot drift from what the
builder resolved."* The Dockerfile also records a failed earlier attempt —
using `--no-deps` wheeled only the ~40 top-level requirements, so the final
stage pinned every wheel to an exact file *and* tried to resolve missing
transitive dependencies fresh from the internet, which is unsatisfiable and
failed with `ResolutionImpossible`.

**Tradeoff.** A longer, more complex build, and a rebuild is needed for any
dependency change.

**Industry.** Multi-stage builds are the standard way to keep build tools out
of the runtime image. The hermetic install is the part teams more often skip.

---

## D-038 — The job queue accepts JSON only, never pickle

**Problem.** Celery can serialise jobs with Python's `pickle`, which
represents arbitrary objects, or with JSON, which represents only data.

**Chosen.** JSON, in
[`workers/celery_app.py`](../backend/app/workers/celery_app.py):
`task_serializer="json"`, `accept_content=["json"]`.

**Why.** Pickle can encode instructions that execute when the message is
loaded. A worker that accepts pickled messages will run whatever anyone able
to write to the queue tells it to construct — a remote-code-execution path
through the broker. JSON cannot express code, so the worst a malicious message
can be is invalid data. **The format's expressive limit is the security
control.**

**Tradeoff.** Task arguments must be JSON-representable: no arbitrary Python
objects, no datetimes without conversion. That constraint is also a design
benefit, since it keeps task arguments small and explicit.

**Industry.** Standard advice; every Celery security guide leads with it.

---

## D-039 — Host ports are remapped to avoid collisions with the developer's machine

**Problem.** A developer's machine often already runs PostgreSQL on 5432 or
another Redis on 6379, and only one program may hold a port.

**Chosen.** Map host ports away from the defaults: `"5433:5432"` for
PostgreSQL, `"6380:6379"` for Redis — and a local override file that moves
Redis again to 6381 because *"a pre-existing container holds 6380"*.

**Why.** Port mapping translates only at the boundary, so the container's own
configuration keeps the conventional port and nothing inside needs to know
about the host's clutter. The override changes **only** the host port, leaving
container-to-container traffic on `redis:6379` untouched — which is why it is
safe.

**Tradeoff.** Two numbers to remember per service, and connection strings
differ depending on whether you are calling from your machine or from another
container. That confusion is the single most common cause of "connection
refused" for newcomers, and it is worth documenting rather than removing.

**Later.** Drop the override once the conflicting container is gone, as the
file itself instructs.

---

## D-040 — Test identity (`is None`), never truthiness, when empty and absent differ

**Problem.** Python treats `None`, `0`, `""` and `[]` as false in a condition.
That is convenient and it merges states that mean different things.

**Chosen.** Explicit identity checks wherever the distinction matters — for
example in
[`retrieval_service.py`](../backend/app/services/retrieval_service.py):

```python
if document_ids is not None:
    stmt_vec = stmt_vec.where(Document.id.in_(document_ids))
```

**Why.** Commit `8fd0f22` records what the truthy version cost: *"Deep Research
collapsed an EMPTY document_ids list to None via `[...] if document_ids else
None`, turning 'the user attached no documents' into 'apply no document
filter', which scanned every READY chunk in the database."* One falsy value,
two meanings, and the wrong one selected everybody's data.

**Tradeoff.** Slightly longer conditions, and a rule the team must actually
follow. Cheap for what it prevents.

**Generalises to.** Any language with a truthy/falsy notion — JavaScript's `0`
and `""` cause the identical family of bug, which Chapter 08 will meet again.

---

## D-041 — Narrow `except` clauses; a broad catch must log loudly

**Problem.** `except Exception: return None` reads as careful error handling
and is, in fact, a way to erase evidence.

**Chosen.** Catch only the exceptions that can genuinely occur
(`except (ValueError, TypeError)` in
[`document_access.py`](../backend/app/core/document_access.py)); where a broad
catch is unavoidable on a request path, annotate it and log at ERROR with the
exception's type, once per process
([`redis_client.py`](../backend/app/core/redis_client.py)).

**Why.** The module's own docstring states the mechanism: *"`except Exception:
return None` makes a MISSING DEPENDENCY indistinguishable from a cache miss.
Both look like 'no Redis today'."* Six call sites silently disabled an
advertised abuse control, the retrieval cache and two rate limits, with no log
line anywhere.

**Tradeoff.** Naming exception types means updating them if a library's
behaviour changes — which is a feature: you find out.

**Industry.** Every Python style guide forbids bare `except`; linters flag it
as `BLE001`. Note that this repository *keeps* the broad catch where a request
path must never break, and pays for it with a loud log and an explicit
`# noqa` — a signed exception rather than an oversight.

---

## D-042 — Pydantic at trust boundaries, dataclasses inside

**Problem.** Data arriving from a browser is untrusted; data passed between
internal functions is not. Validating both costs time; validating neither costs
security.

**Chosen.** Pydantic models for requests, responses and settings
([`schemas/query.py`](../backend/app/schemas/query.py),
[`core/config.py`](../backend/app/core/config.py)); plain dataclasses for
internal structures such as the trust report.

**Why.** A Pydantic model is a single validation choke point at the boundary:
`query: str` with no default means a request missing it is rejected before any
handler runs, and `Optional[UUID]` rejects malformed ids and converts valid
ones. Doing that inside the process, on data the process itself produced, buys
nothing and costs time on every call.

**Tradeoff.** Two mental models for "a class of fields", and a judgment call at
each new type about which side of the boundary it lives on.

**Industry.** Standard practice in modern Python services; FastAPI assumes it.

---

## D-043 — Enums for fixed state sets, with `str` mixed in

**Problem.** A document's status is one of eight values. As free text,
`"READY"`, `"Ready"` and `"redy"` are all writable, and the typo is found in
production.

**Chosen.** `class DocumentStatus(str, enum.Enum)` in
[`models/document.py`](../backend/app/models/document.py).

**Why.** An enum makes a misspelling an immediate `AttributeError` instead of a
silent mismatch. Inheriting `str` as well means each member *is* a string, so it
compares to text, serialises to JSON and writes to a database column with no
conversion — which is why the retrieval filter can read
`Document.status == "READY"` directly.

**Tradeoff.** Adding a state means editing the enum and any migration that
persists it; a plain string would allow a new value silently, which is exactly
what we do not want.

**Generalises to.** Every fixed vocabulary: roles, workspace slugs, job states,
payment statuses. If the set of legal values is knowable, encode it in a type.

---

## D-044 — Required positional parameters as a security control

**Problem.** A tenant filter that callers may forget will eventually be
forgotten.

**Chosen.** `owner_id` is a required positional parameter with no default on
`RetrievalService.retrieve_chunks`.

**Why.** Commit `8fd0f22`: *"a caller that forgets it raises TypeError instead
of quietly retrieving cross-tenant."* The language's own call-checking becomes
the enforcement mechanism — the unsafe call does not run, rather than running
unsafely.

**Tradeoff.** Every call site must supply it, including tests and internal
tooling. That is the intended cost.

**The general pattern.** When a value must never be omitted, make omission a
*syntax-level* failure: a required parameter, a non-null column, a required
field in a model. This is the same move as `owner_id` being `NOT NULL` in the
database and as `workspaceId` being made required in the frontend upload
function after two callers omitted it.

---

## D-045 — An async request path, because 86% of a request is waiting

**Problem.** A grounded answer takes ~2.4 seconds, of which ~2.07 is spent
waiting for PostgreSQL and for Google. With blocking code and one thread that
is 0.42 requests per second at 14% CPU: idle hardware and queueing users.

**Options.**
1. Blocking code, one thread per request (the classic model).
2. Blocking code with a large thread pool.
3. An async event loop.

**Chosen.** Option 3, throughout `backend/app/api` and `backend/app/services`.

**Why.** Option 1 needs one thread per concurrent request, each with its own
stack of hundreds of kilobytes, and the OS pays a switching cost per thread.
Option 2 is the same with a ceiling. An event loop holds a suspended request as
a few hundred bytes on the heap, so concurrency is limited by the real
bottleneck — the database connection budget and the provider's rate limit —
rather than by thread memory.

**Tradeoff, and it is a serious one.** Cooperative scheduling means the loop
cannot interrupt a coroutine. One blocking call freezes every concurrent
request on that process. This repository paid that cost three times (D-046).
Async buys throughput and charges discipline.

**When to choose differently.** If most of a request is computation rather than
waiting, an event loop adds machinery and buys nothing. A CPU-bound service is
better served by processes.

---

## D-046 — CPU-bound work is offloaded, and the guard measures the loop, not the source

**Problem.** Three separate defects put blocking work on the event loop: a
`time.sleep` in the mock provider, two model inferences on the query path, and
the iteration of a blocking stream generator.

**Chosen.** `run_in_executor` at each site, plus regression guards that measure
loop freedom rather than inspecting code.

**Why the guards are the important half.** Commit `4964ed6` shows why source
inspection is insufficient: `run_in_executor` was *present* and wrapped the
wrong operation — the call that obtained the stream was offloaded, the
iteration that performed the network I/O was not. *"Wrapping only the
constructor looks correct and is not, which is why this survived review."* A
test asserting the call exists would have passed on the broken code.

So each guard states the defect as a number:

- *"only 0 heartbeats while consuming a stream that blocks 0.60s in total"*
- *"4 concurrent calls took 2.00s (ceiling 1.20s, fully serialized would be 2.00s)"*
- *"only 1 heartbeats while the cross-encoder rerank blocked for 0.5s"*

**Tradeoff.** Offloading does not remove blocking; it moves it to a thread. The
work still occupies a thread and still takes the same time — and the default
pool is shared and unbounded, which is the residual weakness recorded below.

**Generalises to.** Any cooperative runtime — Node.js, Go's older scheduler,
any UI thread. The rule is identical: never do long work on the shared thread,
and prove it with a concurrent measurement.

---

## D-047 — Async on the request path, synchronous in the workers, never mixed

**Problem.** Celery tasks and FastAPI endpoints both touch the database. Should
the worker be async too?

**Chosen.** No. `CLAUDE.md` states it as an invariant: *"FastAPI + `asyncpg` on
the request path; Celery uses `SyncSessionLocal` (psycopg2). Never mix."*

**Why.** The worker has no event loop and no concurrency requirement — each
child process handles one task at a time — so async would add a runtime with no
benefit. More importantly, half-async code is where the hardest bugs live: a
blocking call in an async worker, or a coroutine never awaited in a sync one,
fails in ways that are invisible until load arrives. **Two internally
consistent worlds are far cheaper to reason about than one hybrid.**

**Tradeoff.** Two database drivers, two session factories, and shared service
code that must avoid assuming either. That cost is visible and bounded; the
alternative's cost is not.

---

## D-048 — A `threading.Lock` for state reachable from threads, not an `asyncio.Lock`

**Problem.** The Gemini key rotator's state is touched from the async request
path, from executor threads, and from the synchronous Celery worker.

**Chosen.** `self._lock = threading.Lock()` in
[`services/llm_key_rotation.py`](../backend/app/services/llm_key_rotation.py).

**Why.** An `asyncio.Lock` serialises coroutines on one event loop and does
nothing about two threads. Since this state is genuinely reachable from
threads, an async-only lock would be a comfort blanket rather than a control.

**The general rule.** Choose the lock that matches the thing that can actually
interleave. Ask "what are the two things that could touch this at once?" before
choosing, not after.

**Tradeoff.** A threading lock held on the event loop's thread blocks the loop
for its duration, so the critical section must stay short — which is why the
rotator deliberately performs its cooldown wait *outside* the lock, a detail
its comments mark as something to preserve.

---

## D-049 — Streaming responses are async generators, and the tenant scope is not a `yield` dependency

**Problem.** The SSE endpoint returns almost immediately and then produces
output for several seconds. Anything whose lifetime is tied to the *handler*
disappears while the stream is still running.

**Chosen.** `StreamingResponse(event_generator(), ...)` where
`event_generator` is an async generator, and the tenant scope is bound with a
plain `ContextVar.set()` rather than a `yield`-style dependency — with the
reasoning recorded in [`core/auth.py`](../backend/app/core/auth.py):

> *"A `yield`-style dependency would tie the scope's lifetime to the
> dependency's, which is WRONG for SSE: the streaming generator in query.py
> outlives the dependency and still needs the scope while it runs."*

**Why this is safe rather than a leak.** Starlette runs each request in its own
asyncio Task, and a Task copies the ambient context when it is created, so the
binding is private to that request and cannot bleed into a concurrent one.

**Tradeoff.** The error model changes: once the first frame is written, the
HTTP status is already sent, so a later failure cannot become a 500. The code
yields an `error` event instead — which the frontend's SSE reader handles
explicitly.

**Generalises to.** Any streaming or long-lived response: ask what the lifetime
of each acquired resource is, and whether it outlives the handler that acquired
it.

---

## D-050 — Every network call goes through one wrapper

**Problem.** Every request from the browser needs the same things: cookies
attached, a CSRF header on anything that changes data, a device header, a
readable message when the network is down, and a single silent retry when the
session token has expired. Doing that at each call site means doing it wrong
somewhere.

**Options.**
1. Call `fetch` directly wherever a request is needed.
2. A thin helper that only prefixes the base URL.
3. One wrapper that owns the whole request policy.

**Chosen.** Option 3 — `apiFetch` in
[`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts). Every exported
function in that file goes through it.

**Why.** This is the frontend's choke point, in the same sense as the backend's
tenant scope: a rule enforced in one place is enforced, and a rule repeated at
forty call sites is enforced forty times minus the ones somebody forgot. The
401-refresh logic in particular is impossible to get right per call site,
because it needs shared state across concurrent requests (D-051).

**Tradeoff.** The wrapper accumulates responsibilities and becomes a file that
must not be broken — which is why `CLAUDE.md` lists `lib/api.ts` among the
files needing extra care.

**Industry.** Universal. Every production frontend has one of these, usually
called `apiClient`, `http` or `request`.

---

## D-051 — In-flight de-duplication for the token refresh

**Problem.** When a session token expires, several requests fail with 401 at
the same moment. Each would independently try to refresh, producing several
refresh calls for one expiry.

**Chosen.** A module-level flag and a stored promise:

```javascript
if (!_isRefreshing) {
  _isRefreshing = true;
  _refreshPromise = doRefreshToken().finally(() => { _isRefreshing = false; _refreshPromise = null; });
}
const refreshed = await _refreshPromise;
```

**Why.** The first failing request starts the refresh and stores its promise;
every other awaits the *same* promise. One refresh, many waiters. The
`.finally` clears the flag on success **and** on failure — without it, one
failed refresh would leave the flag set forever and every later request would
await a promise that had already settled.

**Tradeoff.** Module-level mutable state, which is effectively global to the
file and hard to test in isolation. Accepted because the shared state is
exactly what the problem requires.

**Generalises to.** Any expensive operation that several callers may request at
once: a cache warm-up, a config fetch, a login. The shape — *check a flag,
store the promise, clear it in `finally`, await the stored one* — is worth
memorising.

---

## D-052 — Cross-cutting signals travel as browser custom events

**Problem.** The network layer discovers a dead session; the component that
shows a "session expired" message lives elsewhere entirely. Wiring them
directly would make the network module import a UI component.

**Chosen.** A named browser event: `window.dispatchEvent(new
CustomEvent('session:expired'))` in `api.ts`, and
`window.addEventListener("session:expired", handler)` in
[`useSessionExpiry.ts`](../frontend/src/hooks/useSessionExpiry.ts).

**Why.** Neither file imports the other. They agree only on a string — the same
shape as the SSE event names between server and browser, and as job names on a
queue.

**Tradeoff, and both halves are real.** First, a name-based contract breaks
silently when one side is renamed. Second, a broadcast reaches listeners it was
not aimed at — which is why the handler explicitly ignores the event on
`/login`, `/register`, `/forgot-password` and `/`, where unauthenticated 401s
would otherwise produce a false "session expired" dialog.

**When to choose differently.** For anything frequent, or where the sender
needs a reply, a shared store or an explicit callback is better. Custom events
suit rare, one-way, cross-cutting signals.

---

## D-053 — Analytics helpers are shaped so private data is hard to send

**Problem.** Product analytics must not carry query text, document names,
answer content, email addresses or user ids — and "remember not to include
them" is not a control.

**Chosen.** [`frontend/src/lib/analytics.ts`](../frontend/src/lib/analytics.ts)
exposes one named helper per event, each already reduced to safe fields:
`querySubmitted(workspace, query_length_chars, has_documents)`,
`documentUploaded(workspace, file_type, file_size_mb_bucket)`,
`clipTextUsed(text_length_chars_bucket)`.

**Why.** The convenient path is the safe one. Sending the query text would mean
bypassing the helpers and calling `track` by hand, which is more work and
visible in review. A count, a bucket and a boolean answer the product questions
without carrying the content.

**Tradeoff.** A new event needs a new helper, so the file grows. That friction
is the point: adding an event is a moment to think about what it carries.

**Industry.** This is the standard privacy-by-design pattern for analytics, and
in several jurisdictions the underlying obligation is legal rather than
optional.

---

## D-054 — TypeScript with `strict: true` for the browser code

**Problem.** JavaScript reports nothing when a property is misspelled, a
function is called with the wrong shape of data, or a value is missing —
`user.nmae` is `undefined`, not an error. At three hundred files that is
unmanageable.

**Options.** Plain JavaScript with careful review; JSDoc comments describing
types; Flow; TypeScript.

**Chosen.** TypeScript, configured with `"strict": true` in
[`frontend/tsconfig.json`](../frontend/tsconfig.json).

**Why TypeScript over the alternatives.** Comments cannot be enforced and drift
silently — the same failure mode as a comment describing a control that does
not exist. Flow required more toolchain commitment and had weaker editor
support. TypeScript's decisive advantage is that **every valid JavaScript file
is already a valid TypeScript file**, so adoption can begin by changing
nothing.

**Why strict specifically.** `strictNullChecks` makes absence part of the type,
so `chat_session_id?: string | null` forces every reader to handle the three
real states — missing, null, present. `noImplicitAny` prevents checking from
switching itself off wherever someone forgot an annotation.

**Tradeoff.** A compile step, more errors during development, and occasional
fights with library types (mitigated here by `skipLibCheck: true`). The
compensation is that renaming a field across the whole frontend becomes a
five-minute mechanical job.

**Limit, stated so it is not mistaken for a guarantee.** Types are erased before
the code runs, so they check the code against itself and never against the data
the server actually sends. That gap is D-056.

---

## D-055 — Fix a class of bug at the type, when no test could exist

**Problem.** `uploadDocument`'s `workspaceId` parameter was optional. A caller
omitted it, the server fell back to the constant `"general"`, and every
batch-uploaded résumé landed where HR's retrieval could not see it. It was the
*second* occurrence of the same defect at a sibling call site.

**Options.**
1. Fix the offending call site.
2. Fix it and add a test.
3. Make the parameter required, so omission cannot compile.

**Chosen.** Option 3, recorded in commit `8638c9c` and in a comment left at
[`frontend/src/lib/api.ts:180`](../frontend/src/lib/api.ts).

**Why.** Option 1 closes the instance and leaves the class open — *"the next
`uploadDocument` call is one omitted argument away from repeating it"*. Option 2
is impossible in a useful form: **you cannot test for "someone might leave this
out", because leaving it out was legal.** The commit says exactly that: *"Test
that was absent: none could exist, because the contract permitted the mistake;
that is why the repair is a type change rather than a test."*

**Verification, and why it is stronger than a test.** Reintroducing the defect
produces `error TS2345: Argument of type 'undefined' is not assignable to
parameter of type 'string'` — the guard observed red. And a clean
`npx tsc --noEmit` is an *exhaustive* proof that no other call site omits it,
across the entire codebase, which no test suite can offer.

**The general rule.** Some defects are best closed with a test, some with a
type. When the defect is "a caller can omit this" or "a value can be a word we
do not expect", the type is the right layer: it removes the possibility instead
of detecting the occurrence.

---

## D-056 — Compile-time checking in the browser, runtime validation at the server

**Problem.** Where should data be checked, given that TypeScript disappears
before the program runs?

**Chosen.** Two different mechanisms on the two sides: TypeScript for the
browser's own consistency, and Pydantic models validating actual request data on
the server.

**Why.** The boundary where untrusted data enters the system is the HTTP
request, and that is where runtime validation belongs — a request missing
`query` is rejected before any handler runs. In the browser, the main source of
mistakes is the developer, so compile-time checking is the tool that fits, and
it costs nothing at runtime.

**The gap this knowingly leaves.** `const docs: Document[] = await res.json()`
is a claim, not a check. If the server changes a field, that line still compiles
and the field silently becomes `undefined`. The same applies to the eight
document statuses, which exist independently in a Python enum and a TypeScript
literal union with nothing keeping them in step.

**Tradeoff accepted.** For a single-author system with a documented API
contract this is reasonable — but it should be a stated decision, not an
omission.

**Later, and it is the highest-value item available.** The backend already
publishes an OpenAPI description (`main.py` sets
`openapi_url=f"{settings.API_V1_STR}/openapi.json"`). Generating the frontend
types from it would eliminate the drift class entirely and turn "the server
changed a field" from a silent gap into a compile error.

---

## D-057 — UUID primary keys everywhere

**Problem.** Every row needs an identifier. Auto-incrementing integers are the
traditional choice.

**Options.** Sequential integers assigned by the database; UUIDs generated by
whoever needs them.

**Chosen.** UUIDs, on every table in
[`backend/app/models/`](../backend/app/models).

**Why — and the deciding reason is structural, not aesthetic.** The upload flow
creates a document id *before* the file exists: the server issues an id, the
browser uploads the bytes against it, then confirms. With a
database-assigned integer there is no id until after an insert, which would
force an extra round trip and a different flow. UUIDs can be generated anywhere.

Two further benefits come free: they are not guessable, so `/documents/124`
cannot be walked to `125` (Chapter 03's enumeration oracle), and they leak no
business information — a sequential id tells the world how many customers you
have.

**Tradeoff.** 16 bytes rather than 4, unreadable in logs, and random values
scatter across a B-tree index, making writes slightly less efficient than
sequential ones. At this scale that cost is invisible.

**Industry.** Both remain common. UUIDs dominate where ids cross system
boundaries or must be generated client-side; sequential integers remain popular
where index locality and log readability matter more.

---

## D-058 — Cascade deletes for data that has no independent meaning

**Problem.** Deleting a document must not leave its pages and chunks behind as
unreachable rows.

**Options.** Delete children in application code; `ON DELETE RESTRICT` and
refuse; `ON DELETE SET NULL`; `ON DELETE CASCADE`.

**Chosen.** `CASCADE`, declared on the foreign keys in
[`document_page.py`](../backend/app/models/document_page.py) and
[`document_chunk.py`](../backend/app/models/document_chunk.py).

**Why.** A chunk has no meaning without its document — it is a *piece of* that
document, not an independent thing that happens to be linked. Application-side
deletion is a multi-step process where any crash halfway leaves orphans forever,
and orphans are invisible: queries simply return fewer rows than expected with
no error.

**Tradeoff, and it is real.** A small delete can silently become an enormous
one. Deleting a user cascades to documents, pages and chunks — potentially
hundreds of thousands of rows in one statement, holding locks for the duration.
That depth is currently undocumented, which is a finding in this chapter's
critique.

**Where cascade would be wrong.** Anything with independent value: an invoice
should not vanish because a customer record was deleted. There, `RESTRICT` or a
soft-delete flag is correct.

---

## D-059 — An HNSW index with explicit parameters, accepting approximate results

**Problem.** Finding the chunks whose meaning is closest to a question means
comparing 1024-number vectors. A B-tree orders values along one dimension and
cannot help. Comparing every vector is exact and costs a full scan.

**Chosen.** An HNSW index, declared with its parameters stated rather than left
to defaults:

```python
Index('ix_document_chunks_embedding', 'embedding',
      postgresql_using='hnsw',
      postgresql_with={'m': 16, 'ef_construction': 64},
      postgresql_ops={'embedding': 'vector_cosine_ops'})
```

**Why.** HNSW walks a layered graph of near neighbours — long links at the top,
short ones at the bottom — so a search touches a few hundred vectors instead of
millions. `m` and `ef_construction` trade build time and memory for graph
quality, and `vector_cosine_ops` must match the distance the query uses.

**Tradeoff, stated plainly.** The result is **approximate**: a true nearest
neighbour can occasionally be missed. For finding relevant passages — where a
reranking stage follows anyway — that is an acceptable price. For anything
requiring exactness it would not be.

**The trap to know about.** A mismatch between the index's distance operator and
the query's does not error. It silently returns worse results, which is exactly
the kind of failure this project's loud-degradation rule exists to prevent, and
which no test asserting "results were returned" would catch.

---

## D-060 — Counter increments computed in the database, not in Python

**Problem.** The trial counter must increase by one per query, correctly, even
when two requests arrive together.

**Chosen.** In
[`core/trial_enforcement.py`](../backend/app/core/trial_enforcement.py):

```python
.values(trial_queries_used=User.trial_queries_used + 1)
```

**Why.** `User.trial_queries_used` is the *column*, so this becomes
`SET trial_queries_used = trial_queries_used + 1` — the addition happens inside
the database, on the current value, under a row lock. Two concurrent increments
produce +2.

The alternative, `user.trial_queries_used + 1`, uses the value the application
read earlier and generates `SET trial_queries_used = 10` unconditionally. Two
requests that both read 9 both write 10, and one increment is lost.

**The general rule.** Let the database compute values that depend on their own
current state. Read-modify-write in application code is a lost update waiting
for concurrency.

**What this does *not* fix, and it is recorded here rather than left implied.**
The *check* against the limit is a separate earlier statement, so two requests
can both pass it at 9 and produce a stored value of 11 on a ten-query trial —
a time-of-check-to-time-of-use race. The single-statement repair is
`UPDATE … SET used = used + 1 WHERE id = :id AND used < :limit`, treating zero
rows affected as refusal. Severity is low (a few free queries); the pattern
would be serious on a payment or a stock count.

---

## D-061 — Cache the retrieved evidence, not the generated answer

**Problem.** A grounded answer costs about 2.4 seconds, of which retrieval is
~400 ms of database and processor work and generation is ~2,000 ms of external
API time and money. Repeated or retried questions pay all of it again.

**Options.** Cache nothing; cache the retrieved evidence; cache the final
answer; cache both.

**Chosen.** Cache the retrieved evidence, with a 300-second TTL, in
[`query.py`](../backend/app/api/v1/endpoints/query.py).

**Why.** Retrieval is deterministic for a given question and document set, so
reusing it is safe. Generation is not fully deterministic, its input includes
the conversation history — so an answer cache key would need the history and the
hit rate would collapse — and a stale *answer* is far more visible and damaging
to a user than stale *evidence*.

**Tradeoff.** The largest single cost is left uncached, so a repeated question
still pays the model call.

**What would change it.** A measurement showing a meaningful share of requests
are repeats with identical history, or a model-cost problem making even a low
hit rate worth the staleness.

---

## D-062 — One function builds the cache key, and its prefix is an invariant

**Problem.** The write path stored `retrieval:{workspace}:{hash}` while the
delete path purged `retrieval:uid_{user_id}:*`. The patterns never matched, so
deleting a document purged nothing and its content could still be answered from
cache for the length of the TTL — with no error, because deleting zero keys is
a successful operation.

**Chosen.** `_retrieval_cache_key()` as the single definition, with the
constraint written into its docstring: *"The key MUST start with
`retrieval:uid_{user_id}:` — that is the pattern `delete_document` purges."*

**Why.** Two independent statements of one convention will drift, and the drift
is invisible: both halves work perfectly in isolation. One definition that both
sides depend on removes the possibility rather than documenting it.

**Key contents, each justified.** User id (tenant, *and* the purge prefix),
workspace (different retrieval settings), the question, and the attached
document ids — **sorted**, so ordering cannot fragment the cache — all hashed to
sixteen hex characters to keep keys short and pattern-matchable.

**Tradeoff / remaining gap.** The purge pattern in `documents.py` is still
written by hand. Deriving it from a shared `_retrieval_cache_prefix(user_id)`
would make drift structurally impossible instead of merely documented — the same
move as making a parameter required rather than warning about it.

---

## D-063 — Redis unavailability degrades the feature but is logged loudly, once

**Problem.** Six call sites imported Redis inside `try/except` and returned
`None` on failure. The library was not installed, so every call failed — and
because callers treat `None` as "no cache entry", a **missing dependency was
indistinguishable from a cache miss**. The retrieval cache never cached, a
device-fingerprint abuse control was inert, and two IP rate limits failed open.
No log line existed anywhere.

**Chosen.** One factory,
[`core/redis_client.py`](../backend/app/core/redis_client.py), using the
library that is actually installed (`redis.asyncio`), still returning `None` on
failure — but logging at ERROR with `type(exc).__name__`, **once per process**.

**Why.** Degrading is correct for a cache and for best-effort rate limits;
degrading *silently* is what turned one missing package into three dead
features. Including the exception type matters because `ModuleNotFoundError`
and `ConnectionRefusedError` require completely different responses. Logging
once per process rather than per request keeps a genuine outage from flooding
the log and hiding everything else.

**Tradeoff.** Callers still treat `None` as "no cache", so the degraded path is
identical; only the visibility changed. That is the intended scope — the fix is
about evidence, not behaviour.

**Related.** `finally: await redis.close()` on both cache paths, because a
raised `get()` would otherwise leak a connection on a code path that runs on
every query, exhausting the pool during any brief network problem.

---

## D-064 — The database row is the source of truth; the queue is only a request to act

**Problem.** Redis is not durable by default, so a queued job can be lost. If
the queue were the only record that work was needed, a Redis restart would
silently drop uploads.

**Chosen.** The document row is written and committed **before** the job is
enqueued, and the row's `status` column — not Celery's task state — is what the
user interface reads.

**Why.** A lost message then leaves a visible artefact: a row sitting at
`PROCESSING` that a human or a scheduled job can find and requeue. It also
avoids the reverse failure, where a worker picks up a job for a row that has not
been committed yet.

There is a second reason worth stating: Celery's `PENDING` state means both
"waiting in the queue" and "I have never heard of this id". That is one value
with two meanings — the shape this course keeps meeting — so it is unsuitable as
a user-facing progress signal. The database row is unambiguous.

**Tradeoff.** Two places record progress (the row and Celery's own state), and
only one is authoritative. That must be understood, or someone will read the
wrong one.

---

## D-065 — Enqueue failure marks the document FAILED and returns 503

**Problem.** If the broker is unreachable, `.delay()` raises. The tempting
response is to log it and return success, because the upload itself worked.

**Chosen.** In
[`documents.py`](../backend/app/api/v1/endpoints/documents.py): log at ERROR,
set the document to `FAILED`, and raise HTTP 503 with *"Document queue
unavailable. Try again in a moment."*

**Why.** Returning success would leave a document that no worker will ever
process, sitting at `PROCESSING` while the interface polls forever. That is the
"failure presented as success" pattern the project's loud-degradation rule
forbids. The comment above the block records the earlier version of exactly this
defect: an optimisation that marked some documents `INDEXING` and never
enqueued anything, leaving them permanently unsearchable while appearing in the
list.

**Tradeoff.** The user sees an error for a file that did upload successfully.
That is the correct direction — an honest error beats a document that silently
never works.

**Contrast worth noting.** Failing to enqueue the *optional* follow-up job
(proactive insights) logs a warning and continues, because the primary result is
already complete. **Whether a failed enqueue is fatal depends on whether the
user's result depends on it.**

---

## D-066 — Retries with exponential backoff, a ceiling, and a guaranteed terminal state

**Problem.** Background jobs fail transiently, and a naive retry either gives up
too early or never ends.

**Chosen.** In
[`document_tasks.py`](../backend/app/workers/tasks/document_tasks.py):
`countdown=2 ** self.request.retries`, `max_retries=3`, and — crucially — an
explicit pre-check that flips the document to `FAILED` before asking for another
retry.

**Why the pre-check exists**, in the code's own words: *"`self.retry(exc=e)`
defaults to `throw=True` and re-raises the ORIGINAL exception (not
`MaxRetriesExceededError`) once retries are exhausted. Pre-check so we always
flip status to FAILED — otherwise the doc stays in PROCESSING forever and the
frontend polls forever."*

**The general rule.** Every job must reach a terminal state that a user or an
operator can see. A job stuck in limbo is worse than a failed one, because it is
indistinguishable from a job that is merely slow.

**Tradeoff / gap.** Retries are only safe if the work is repeatable, and
`process_document` is not: a retry after a partial run re-inserts pages and
chunks. Deleting existing pages and chunks at the start would close it in about
five lines, and is the first improvement recommended in Chapter 12's critique.

---

## D-067 — Batched commits inside the document pipeline

**Problem.** A 200-page document produces hundreds of rows and hundreds of
embedding computations. Doing it all in one transaction holds locks for minutes
and loses everything if the worker dies at page 199.

**Chosen.** `batch_size = 50`: accumulate fifty chunks, embed them in one call,
commit, repeat — with the reason in the code: *"Commit this batch to avoid
ballooning transaction."*

**Why.** Two benefits at once. The embedding model is far more efficient given
fifty pieces than fifty single calls, and each commit bounds how much work a
crash can destroy.

**Tradeoff, and it is real.** Committing partway means a crash leaves a
half-processed document — neither complete nor clean. That is acceptable only
*because* the retry path exists, and it is exactly why idempotency (above)
matters more here than it first appears.

---

## D-068 — Exactly one Beat instance, and workers scaled freely

**Problem.** Scheduled jobs need something watching the clock. How many copies
should run?

**Chosen.** Exactly one Beat process, with the compose file warning: *"Run
EXACTLY ONE Beat instance — a second one duplicates every scheduled task (double
emails)."* Workers, by contrast, may be run in any number.

**Why.** Beat is **stateful** — it holds the schedule and what it has already
fired — so two copies each fire everything. Workers are **stateless**: they hold
nothing between jobs, so extra copies cooperate through the broker
automatically.

**The general rule this expresses.** Stateless components scale by copying;
stateful ones do not. Identifying which is which is the first question to ask
before adding a second instance of anything.

**Related detail.** The schedule file is written to `/tmp` so it cannot pollute
the bind-mounted project folder and be committed by accident.

---

## D-069 — FastAPI on ASGI, chosen for waiting and streaming

**Problem.** Which Python web framework should serve an API whose requests are
mostly waiting, whose answers stream token by token, and whose contract spans
24 endpoint modules?

**Options.** Flask (minimal, synchronous, mature); Django (batteries included —
admin, ORM, auth); FastAPI on ASGI.

**Chosen.** FastAPI, served by Uvicorn.

**Why.** Three properties of *this* workload decided it. About 86% of a
question's time is spent waiting on PostgreSQL and the model API, so native
async lets one worker serve many concurrent requests rather than buying workers
to hold waiting. Answers stream, which ASGI expresses naturally and WSGI —
"return the whole response, then finish" — does not. And with a large API
surface, validation and documentation generated from type annotations remove a
substantial maintenance burden.

**Tradeoff, stated honestly.** Django would have supplied an admin panel, an
ORM, auth and migrations in an afternoon; here each was chosen and wired up
separately. FastAPI gives an excellent API layer and expects you to assemble the
rest.

**When to choose differently.** A content-heavy product with an admin interface
and mostly synchronous database work — Django, without hesitation.

---

## D-070 — Authentication as a dependency, not middleware

**Problem.** Every protected endpoint needs the caller's identity, and a few
endpoints (login, registration, health, the CSRF token) must remain public.

**Options.** A middleware that authenticates every request; a helper each
endpoint calls; a dependency declared in the signature.

**Chosen.** `current_user: dict = Depends(get_current_user)` in
[`core/auth.py`](../backend/app/core/auth.py).

**Why.** A dependency *produces a value* the handler uses, which middleware
cannot. It is opt-in per endpoint, which is required because some are public.
And it is **visible in the signature**, so a reviewer can tell at a glance
whether an endpoint is protected — a helper called somewhere inside the body
gives no such guarantee.

It also does something invisible: it binds the owner into a context variable
that the database layer reads, so every ORM read is filtered without any
endpoint writing a filter.

**Tradeoff.** Opt-in means a new endpoint is public unless someone adds the
dependency. That is the mirror image of the rate-limit weakness noted in
Chapter 13's critique, and the mitigation is that the omission is visible in
review rather than hidden.

**When middleware would be right.** If *every* request had to be
authenticated, including ones matching no route — for example an API where even
the existence of a path is confidential.

---

## D-071 — Validation at the boundary with Pydantic models

**Problem.** Every value arriving from a client is a claim, not a fact.
Checking inside handlers means checking in two hundred places, inconsistently.

**Chosen.** Typed request models in
[`schemas/`](../backend/app/schemas), so FastAPI validates and converts before
any handler line runs, returning 422 with a per-field explanation when it fails.

**Why.** It is a choke point for data validity: by the time a handler starts,
every field is present, correctly typed and converted, so no defensive checking
is needed and none can be forgotten. It also produces better errors than
hand-written checks, because it reports every problem rather than the first.

**The counterpart worth stating.** The frontend's TypeScript is erased before
the code runs, so it checks the frontend against itself and never against what
the server sends. Pydantic checks actual data. Compile-time checking protects
against the developer's mistakes; runtime validation protects against the
world's.

**Gap.** `response_model` — which additionally *filters* outgoing fields, so an
internal field cannot leak — is applied inconsistently; several endpoints return
`Any`.

---

## D-072 — A middleware chain whose order is deliberate

**Problem.** Six cross-cutting concerns must apply to every request: CORS,
correlation ids, security headers, CSRF, tenant context, device fingerprinting.

**Chosen.** Six middlewares registered in
[`main.py`](../backend/app/main.py), with `add_middleware` semantics meaning the
last registered runs first — so execution order is DeviceFingerprint →
TenantContext → CSRF → SecurityHeaders → CorrelationId → CORS → handler.

**Why middleware rather than per-endpoint calls.** "Every endpoint" includes the
one added next month. A rule that must be remembered will eventually be
forgotten; middleware makes forgetting impossible.

**Why the order matters.** A layer that rejects requests, placed inside a
logging layer, means rejected requests are never logged — so attacks become
invisible. Any change to this stack requires writing out the real execution
order first.

**Tradeoff.** Middleware runs for every request including static and unmatched
paths, so anything expensive there is paid constantly. All six here are cheap.

---

## D-073 — Sentry strips request bodies before reporting

**Problem.** Error-reporting services capture request context, and in this
product a request body contains a user's private question about their private
documents.

**Chosen.** A `before_send` hook in
[`main.py`](../backend/app/main.py) that removes `data` and `body` from every
event, plus `send_default_pii=False`.

**Why.** An error reporting tool is a place user data can leak to — a third
party, outside the tenancy controls that protect everything else. Stripping the
body keeps the diagnostic value (which endpoint, which error, which correlation
id) without exporting the content.

**Tradeoff.** Harder debugging: you cannot see the exact input that caused a
crash. The correlation id and the endpoint name are usually enough to
reproduce, and the alternative — private documents in a third-party dashboard —
is not acceptable.

**Generalises to.** Logs, analytics, crash reporters, support tooling. Ask of
every outbound diagnostic channel: *what user content does this carry, and did
we decide that?*

---

## D-074 — SQLAlchemy as the data layer, with SQL deliberately visible

**Problem.** Something must translate between database rows and Python objects.
Doing it by hand means string-built SQL (and injection), manual row mapping per
table, and hand-written change tracking.

**Options.** A raw driver (`psycopg2` alone); a query builder; an ORM that
hides SQL entirely (ActiveRecord style); SQLAlchemy, whose queries mirror SQL.

**Chosen.** SQLAlchemy's ORM, over a four-line declarative base in
[`db/base.py`](../backend/app/db/base.py).

**Why.** It removes the three dangerous manual jobs — string building, row
mapping, change ordering — while keeping queries recognisably SQL, so anyone
who knows SQL can read them and reason about their cost. An ORM that hides SQL
completely also hides the N+1 problem, which is the most common performance
defect in this category.

**Tradeoff.** The cost of a query becomes invisible at the call site:
`chat.messages` looks like an attribute and may be a network round trip. This
repository paid that cost twice (D-075).

**Limit worth recording.** Dropping to raw `text()` SQL bypasses the ORM-level
tenancy hook entirely — stated in `tenant_scope.py`'s own docstring rather than
left implicit.

---

## D-075 — N+1 loops fixed by consolidation, and guarded by query count

**Problem.** Two places issued one query per item inside a loop: an export ran
51 queries for a 50-clause contract, and a research endpoint on the request
path ran two queries per document — twenty sequential round trips for ten
documents.

**Chosen.** Commit `3daf888`: one batched `.in_()` query grouped in Python, and
**both research call sites replaced by a single shared helper** rather than two
corrected loops.

**Why consolidation rather than two fixes.** The commit states it: *"the two
loops were the same code twice, and fixing them separately would leave the
third copy — whenever it is written — free to repeat both defects."*

**The second finding, which the performance report did not mention.** Both
loops scoped documents by `workspace_id`, which is derived from a workspace
name and identical for every user, so any authenticated user could pass another
user's document id and receive its text back inside a generated citation. The
fix closed it because *"leaving a known cross-tenant read in a predicate I was
already editing was not defensible."*

**How it is guarded.** The test asserts **query count** against growing input
(1, 5, 20 documents → exactly 2 queries) rather than elapsed time, *"which
would be flaky and would not state the property."*

**And the lesson about the guard itself.** Its first version inspected the
whole `for` statement and flagged the *fixed* code, because the batched query
legitimately sits in the loop's iterator expression, which runs once. **A guard
that cannot tell the fix from the defect is worse than no guard.** Verify your
verification.

---

## D-076 — `expire_on_commit=False` on the async session

**Problem.** SQLAlchemy's default expires every object after a commit, so
reading any attribute afterwards silently re-queries the database.

**Chosen.** `expire_on_commit=False` in
[`db/session.py`](../backend/app/db/session.py).

**Why.** On an async request path a hidden query at an unpredictable moment is
a real source of confusing failures, and reading an attribute you just wrote
should not cost a network round trip.

**Tradeoff, and the code shows it being paid.** Objects can be stale if another
process changed the row. Where the current values genuinely matter, the code
asks explicitly — `await db.refresh(new_doc)` in the upload endpoint is exactly
that.

---

## D-077 — Migrations as versioned schema history, with reasoning in the file

**Problem.** A model gains a column; the live database does not. Hand-run SQL
leaves no record of what was applied where, and `create_all()` cannot alter an
existing table.

**Chosen.** Alembic, with 46 revisions in
[`alembic/versions/`](../backend/alembic/versions), and `import app.models` in
`env.py` so every model is registered before autogenerate compares.

**Why the docstrings matter.** The 1536→1024 embedding resize does not merely
change a type; it argues that the destructive part is safe: *"USING NULL is
safe here: both writer paths were broken since inception, so these columns
cannot contain real data in any deployment that ran this codebase."*

**The standard that expresses:** a destructive migration must carry an argument
for why the data being destroyed cannot exist.

**Known operational reality.** The history has merge revisions with empty
`upgrade`/`downgrade` bodies, because two branches each added a revision to the
same tip. `CLAUDE.md` records the consequence — *"count drifts; `alembic heads`
is truth"* — so the number of files is not a measure of anything.

**Gaps, recorded rather than implied.** There is no written policy for
rolling-deploy safety (the three-step rename pattern), `downgrade()` functions
are untested, and nothing in CI flags a generated migration containing
`drop_column` — which is the shape autogenerate gives a rename.

---

## D-078 — bcrypt for passwords, replacing SHA-256

**Problem.** Passwords must be storable and checkable without being readable if
the database leaks. The original implementation used SHA-256: fast and
unsalted.

**Chosen.** bcrypt via passlib, in
[`core/security.py`](../backend/app/core/security.py) — `FIX 0.9`.

**Why not encryption.** It is reversible, so the key must live where the server
can reach it and usually leaks with the database — and you never need the
original password back, only an answer to "is this the same one?"

**Why not a plain hash.** Without a salt, identical passwords give identical
fingerprints, so one precomputed table cracks them all. Without deliberate
slowness, a graphics card computes billions of SHA-256 hashes per second.
bcrypt supplies both: a per-user salt automatically, and a tunable cost that
makes each attempt take about a tenth of a second — invisible to a user,
prohibitive to a brute-force attempt.

**Tradeoff.** Login costs measurable CPU, and the library version is
load-bearing: `bcrypt` is pinned to `4.0.1` because passlib breaks on 4.1+, so
a blanket dependency upgrade breaks authentication.

---

## D-079 — Signed tokens over server-side sessions, with the revocation cost accepted

**Problem.** HTTP is stateless, so every request must re-prove identity.

**Options.** Server-side sessions (a lookup per request, instantly revocable);
signed JWTs (no lookup, not revocable).

**Chosen.** JWTs in `HttpOnly` cookies, 60-minute access token plus a 7-day
refresh token.

**Why.** The deciding constraint is the connection budget: about fifteen
database connections for the entire deployment. A session lookup on *every*
request spends the scarcest resource in the system on something arithmetic does
for free.

**Tradeoff, stated rather than hidden.** A signed token cannot be revoked —
logout deletes the cookie from that browser, but a stolen copy works until it
expires. Bounded by the 60-minute lifetime.

**Two defects this decision produced, both fixed and recorded in the code:**
a hardcoded fallback secret (`BUG-003`) meant anyone who read the public source
could forge a token for any user; and accepting more than one signing algorithm
(`BUG-013`) enabled algorithm confusion, where an attacker signs with the
server's public key and declares `RS256`. The general rule from the second:
**never let untrusted input decide how it will be checked.**

**Later.** A short revocation list in Redis, checked at refresh rather than on
every request, would make logout effective within minutes while keeping the
no-lookup benefit.

---

## D-080 — Two independent CSRF defences

**Problem.** Cookies are sent automatically by the browser, which is what makes
them convenient and what makes cross-site request forgery possible.

**Chosen.** `samesite="strict"` on the auth cookie **and** a double-submit CSRF
token enforced in
[`core/middleware.py`](../backend/app/core/middleware.py), with a short,
explicit exemption list for pre-authentication endpoints.

**Why both.** `SameSite` is strong and depends on browser behaviour; older
browsers, unusual redirect flows and future changes can weaken it. Two
independent controls mean one failing does not open the door — defence in
depth, applied deliberately rather than by accumulation.

**Why the check is limited to mutating methods.** `GET` is agreed not to change
state, so the protocol's promise carries the control — which is also why a
`GET` that deletes something is a genuine vulnerability rather than a style
issue.

**Tradeoff.** Every exemption is a deliberate hole; keeping them in one named
list makes them reviewable rather than scattered.

---

## D-081 — Client-supplied storage paths validated at one choke point

**Problem.** `verify_upload` stored the client-supplied `object_key` verbatim
as the document's storage path. Three sinks consumed it: a `stat()` call (an
existence and size oracle for any path on the server), the worker's file read
(**any file on the machine could be pulled into the searchable corpus, then
queried and answered with citations**), and `unlink()` on delete — an
**arbitrary file delete** as the API's user.

**Chosen.** `core/storage.validate_object_key`, applied at the write path and
at both dangerous sinks: rejecting empty keys, NUL bytes, any `..` segment, and
anything resolving outside the storage root.

**Why one function rather than three patches.** "What is a valid storage
location" is a single decision; patching three sinks leaves the fourth,
written later, unprotected.

**Why strict enforcement rejects nothing legitimate**, from the commit:
*"neither upload route ever needed the client to choose a location … The client
is only echoing back a value the server produced."*

**The two transferable rules.** *When you are accepting a value the client had
no business choosing, you have probably found a vulnerability.* And: `..` is
refused on sight rather than resolved, because resolution can follow a symlink
out of the root and back in — **prefer a rule you cannot get wrong over a
computation you must get right.**

---

## D-082 — Prompt injection treated as unfixable, and bounded architecturally

**Problem.** Document text is placed into a model prompt. A language model
reads one stream of text and has no mechanism separating instructions from
data, so a document saying *"ignore previous instructions"* is read and may be
followed.

**Chosen.** A guard prepended exactly once
(`EVIDENCE_INJECTION_GUARD` in
[`services/llm_service.py`](../backend/app/services/llm_service.py)),
**plus** three structural limits: the model has no tools, all arithmetic is
performed in Python, and citation labels are written by code rather than
generated.

**Why the guard is not the defence.** It is text arguing with text; it raises
difficulty and guarantees nothing. Unlike SQL injection, there is no structural
separation available, because the model has no notion of "command" versus
"data".

**What actually bounds the damage.** With no tools, the worst outcome is wrong
text rather than an action. With arithmetic in Python, injected text cannot
change a computed number. With code-written labels, a citation is copied rather
than invented.

**The general principle.** When an attack cannot be eliminated, reduce what a
successful attack can reach.

---

## D-083 — Layout-aware chunking that refuses to split tables

**Problem.** Documents must be cut into pieces small enough to embed, search and
fit in a prompt. Fixed-size cutting lands mid-sentence, producing two chunks
that each match badly.

**Chosen.** [`chunking_service.py`](../backend/app/services/chunking_service.py)
merges whole layout blocks — separated by blank lines during extraction — until
`CHUNK_SIZE` (1800 characters), and **keeps an oversized block whole**.

**Why.** Every chunk boundary is then one the document already had. A table
split in half is not smaller but meaningless, because the rows lose their
headers, so exceeding the size limit is the lesser harm. Overlap is the previous
*block* when it is smaller than `CHUNK_OVERLAP`, so the repeated text is a unit
of meaning rather than an arbitrary 300 characters.

**Tradeoff.** Chunk sizes are uneven, and an oversized block is truncated at 512
tokens by the reranker later — a real interaction between two stages that is
worth knowing about.

**The arithmetic that ties it together.** 1800 characters ≈ 450 tokens; a 6,000
token grounding budget therefore holds about twelve chunks, which is exactly
`MAX_CHUNKS_PER_QUERY` and the workspace `top_k` values. **Chunk size, retrieval
width and prompt budget are one calculation, not three settings.**

---

## D-084 — bge-m3 run locally, with normalised vectors

**Problem.** Embedding hundreds of chunks per document must be cheap, must work
for Indian-language documents, and must fit the storage arithmetic.

**Chosen.** `BAAI/bge-m3` via sentence-transformers, on our own server, with
`normalize_embeddings=True`, producing 1024 numbers per chunk.

**Why.** Running locally removes a per-call cost that would otherwise scale with
corpus size — the deciding factor. It is multilingual, handles long inputs
suited to 1,800-character chunks, and 1024 dimensions is 4 KB per vector, which
keeps a thousand users' corpora around 24 GB and therefore inside one
PostgreSQL instance.

Normalising to unit length makes cosine similarity a plain dot product and keeps
stored vectors directly comparable.

**Tradeoff, and it is severe.** The Gemini fallback produces **768** numbers,
zero-padded to 1024 — a different coordinate system compared as though it were
the same one. Similarity between the two becomes meaningless *without erroring*,
and the damage is written permanently into stored vectors, repairable only by
re-embedding everything. The current mitigation is a loud ERROR log; the
reranker's approach (refuse in production) would be stronger.

**Related invariant.** Changing the embedding model means altering the column
dimension, rebuilding the HNSW index, and re-embedding every chunk. **It is a
data migration, not a configuration change.**

---

## D-085 — Reranking with a cross-encoder, and the normalisation defect

**Problem.** Rank fusion produces a reasonable order from two approximations,
but only about five chunks reach the model — and sending the wrong five produces
a wrong answer even when the right text was retrieved.

**Chosen.** `cross-encoder/ms-marco-MiniLM-L-6-v2`, loaded once as a singleton,
scoring up to 30 question-chunk pairs at `max_length=512` in batches of 16.

**Why a second stage at all.** A bi-encoder embeds question and chunk
separately, so chunk work is precomputed and searching millions is cheap — but
each chunk was encoded without knowing the question. A cross-encoder reads both
together and is far more accurate, and far too slow to run over a corpus.
**Cheap and wide, then expensive and narrow.**

**The defect recorded here rather than hidden.** The provider min-max normalises
scores *per candidate set*, so the top result is always exactly 1.0 and the
bottom always 0.0 regardless of quality — which means
`grounding_service.py`'s `rerank_score >= rerank_threshold` low-confidence gate
**can never exclude the top result nor keep the bottom one.** The audit's phrase
is the lesson: *"The gate reads as working in every review."* The defect exists
only in the relationship between two files.

**Fix.** Threshold on raw scores, which are comparable across queries, and
normalise only for display.

**Related good decision.** `DummyLocalReranker` **raises in production** rather
than returning fabricated scores, because those scores feed a confidence number
shown to users. Compare with the embedding fallback, which degrades: a worse
embedding is still a real embedding; a fabricated score is a lie with a number
attached.

---

## D-086 — Evidence blocks labelled by code, so citations are copied not generated

**Problem.** Asking a model to cite its sources produces plausible, sometimes
wrong page numbers — and a citation you cannot trust is worse than none, because
it manufactures confidence.

**Chosen.** In
[`grounding_service.py`](../backend/app/services/grounding_service.py), each
piece of evidence is wrapped in a block carrying the real filename, page number
and chunk id, read from database rows written during ingestion — **before the
model sees anything**.

**Why.** It reduces the model's job from *"know where this came from"* — which
it cannot do and will fake — to *"repeat the label attached to the text you
used"*, which is easy. The generalisable rule: **when you need a model to be
right about a fact, put the fact in front of it rather than asking it to
recall.**

**Two supporting decisions.** Evidence is sorted into document order before
presentation, so the model reasons linearly and produces page-ordered citations
— selection order and presentation order are deliberately different. And the
system prompt specifies an **exact refusal sentence**, so refusal is detectable
by software rather than judged by wording.

**Residual risk, stated.** With several blocks present the model can attach the
wrong label to the right sentence. Post-generation citation verification would
close it and does not exist.

---

## D-087 — A trust score that was mostly constant, and the rule it produced

**Problem.** Users cannot judge grounding from fluency, so a supporting
confidence signal is genuinely useful.

**What was built.** [`veritas_engine.py`](../backend/app/services/veritas_engine.py)
combines five weighted factors into a score displayed as HIGH / MEDIUM / LOW.

**What the audit found.** Three of the five are hardcoded constants — about 65%
of the weight — `dual_retrieval` returns 70.0 whenever any chunk was retrieved
despite its name implying two retrieval methods agreeing, and no contradiction
detection is performed at all. A fourth compares a chunk's **first 50 characters
verbatim** against model prose, which essentially never matches. The output is
roughly 66/MEDIUM for any input, and `audit_export.py` re-exports it into a
compliance PDF under the line *"Trust scores indicate retrieval confidence."*

**Why it survived.** The number looks reasonable and **a constant can never
disagree with an answer**, so no review trigger could fire. Chapter 04 records
that three review roles referenced the score and none could be invoked for it.

**The rule this produced, which is the most transferable item in Chapter 16:**
**a number displayed to a user needs a test proving it varies with its inputs.**
Compute it for a well-supported answer and a contradicted one, and assert the
scores differ.

**Status.** Open. The honest options are to implement the missing factors
(groundedness and citation validity are the achievable ones, since the
embeddings and the exact evidence are already available) or to reduce the
reported score to what is actually computed. Leaving it as it is, exported into
a compliance artefact, is the one option that is not defensible.

---

## D-088 — Migrations run before the server starts, gated by `&&`

**Problem.** New code and an old schema cannot coexist: the first request
touching a new column fails.

**Chosen.** In [`railway.json`](../railway.json):
`alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
with `restartPolicyType: ON_FAILURE` and a retry ceiling of 10.

**Why.** The `&&` means the server starts only if migrations succeeded, so the
application can never serve new code against an un-migrated database. Automatic
restart handles transient start-up failures; the ceiling stops an infinite crash
loop.

**Tradeoff, and it has a threshold.** With several API instances they all run
migrations on deploy — Alembic locks so they cannot corrupt each other, but the
others wait, and a slow migration delays every instance's start. **Correct at
one instance; should move to a dedicated pre-deploy step at three.**

---

## D-089 — A production frontend target, with build-time configuration

**Problem.** The original image ran `npm run dev` unconditionally — *"a dev
server must never be what gets deployed"*: slow, unminified, and leaking
internal details in errors.

**Chosen.** [`Dockerfile.frontend`](../infrastructure/Dockerfile.frontend) with
two targets — `dev` for the bind-mounted Compose workflow, and a default
production target that runs `next build` then `next start`.

**The constraint this creates**, stated in the file: `NEXT_PUBLIC_*` values are
**inlined into the bundle at build time**, so `NEXT_PUBLIC_API_URL` must be
present as a build argument. Setting it at runtime has no effect.

**Three consequences.** One frontend image is not environment-independent, so
staging and production need separate builds if their API URLs differ. A secret
in such a variable is shipped to every browser. And rolling back means
redeploying an image built with the correct value — an environment change cannot
fix it.

---

## D-090 — CI runs against real dependencies, with a blocking security audit

**Problem.** "It works on my machine" is a statement about leftover packages and
forgotten environment variables, not about the code.

**Chosen.** [`ci.yml`](../.github/workflows/ci.yml) on a fresh machine: real
PostgreSQL (with pgvector) and Redis as services, the ten required environment
variables supplied explicitly, `prestart.sh` waiting for the database, then
`alembic upgrade head`, then `pytest`, plus a frontend lint and production
build.

**Why real services rather than fakes.** Testing against a fake database proves
the fake works. Running the migrations in CI also tests the *migrations*, not
only the code.

**Why the audit blocks**, from the comment: it was previously non-blocking, so
failures were ignored. Now a new vulnerability must be triaged explicitly with
`--ignore-vuln`, *"rather than reverting to a swallowed failure."* **A check
whose failure is ignored is not a check.**

**Gap, recorded.** There is no CD half — no image is built or published and
nothing deploys — so the artefact that ships is not provably the artefact that
was tested. Building and tagging the image in CI is the natural next step.

---

## D-091 — Health checks that test dependencies, and `depends_on: service_healthy`

**Problem.** A started container is not a working one, and a service that begins
before its database is ready dies on its first query.

**Chosen.** `/health` pings PostgreSQL and Redis rather than returning a
constant, and Compose services declare
`depends_on: { condition: service_healthy }`.

**Why testing dependencies.** An API that cannot reach its database is not
serving anything useful; a check that cannot fail is decoration.

**The counter-balance, which matters equally.** A check that tests too much
becomes an outage generator — a brief Redis blip would restart the fleet. The
rule adopted: liveness tests the process, readiness may test the dependencies
needed to serve a request.

**Two incidents this made visible rather than caused.** PgBouncer defaulted to
port 5432 while the check targeted 6432, so it was unhealthy forever and worker
and beat — which depend on it — **never started at all**. And when pool sizes
were hardcoded too high, the health ping could not obtain a sixteenth
connection, leaving the container unhealthy for nineteen hours. **In both cases
the health check reported a real failure; that is the system working.**

**Accepted cost.** The database ping is an unpooled connection every ten
seconds, counted explicitly in the fifteen-connection budget. **Monitoring
consumes production resources — count it rather than avoid it.**

---

## D-092 — Structured JSON logs with correlation ids and PII redaction

**Problem.** Sentence-shaped logs are readable and unsearchable at volume, and
logs are copied to third-party services, retained for months, and read by people
who never see the database.

**Chosen.** [`core/json_logger.py`](../backend/app/core/json_logger.py): one
JSON object per line in production, plain text in development, with
`redact_pii()` applied to every message and `request_id`, `user_id` and
`workspace_id` attached when present.

**Why the correlation id matters most.** It is generated per request by
middleware and returned as a response header, so a user's failed request can be
traced from their side to exactly the lines that describe it — the single most
useful field in a production log.

**Tradeoff.** JSON is unpleasant to read directly, which is why development
keeps plain strings. Redaction can also remove detail you wanted; the answer is
to log identifiers rather than personal values in the first place.

**Related.** Sentry strips request bodies and PostHog sends buckets and counts
rather than content — **three outbound channels, three deliberate privacy
decisions.**

---

## D-093 — Publish the known-gaps list in the public README

**Problem.** The repository is a hiring artefact read by people who will never
speak to its author. A README that presents only what works invites the reader
to find the gaps themselves — and a gap the reader discovers reads as something
you did not know, while the same gap stated by you reads as judgment.

**Options.** (a) Describe only the working system, which is the normal choice
and the reason almost every student repository looks identical. (b) List the
gaps in an issue tracker, which is honest but invisible to a reader skimming for
twenty seconds. (c) A short **Known gaps** section in the README itself, ranked,
with a reason each.

**Chosen.** (c) — four entries, ranked: no backups, no graceful shutdown, no
alerting, and a trust score whose factors are largely hardcoded.

**Why.** The ranking is the content. Saying *backups first, because it is the
only failure we could not recover from* demonstrates that you can order risk,
which is the thing being assessed and cannot be demonstrated by a feature list.
It also removes the interviewer's strongest question from play — you cannot be
caught out on something you volunteered.

**Tradeoff.** A reader skimming for polish may read it as an unfinished project.
That is a real cost and it is accepted deliberately: the readers worth impressing
are the ones who read the section, and for them it is the strongest signal in the
file. The mitigation is placement — after the architecture, not before it.

**Related.** This is the artefact-level form of the rule the codebase already
enforces internally: **loud degradation.** A gap that is documented is a known
limit; a gap that is hidden is a claim that will eventually be tested.
