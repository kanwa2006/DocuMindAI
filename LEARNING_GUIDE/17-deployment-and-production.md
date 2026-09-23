# 17 — Deployment and Production

**Prerequisites: none.** Every term is explained where it appears.

**Estimated study time: 4–5 hours.**

**What this chapter is.** The system from Chapter 16 works on a laptop. This
chapter turns it into something that runs on a machine you cannot see, for
people you will never meet, and keeps running when things go wrong.

**What it is not.** A DevOps course. Every component here exists because *this*
repository needs it. Kubernetes gets one honest paragraph explaining where it
would fit and why this project does not use it.

**The shape of the chapter** is one continuous story: a developer writes code,
commits it, tests run, an image is built, configuration loads, the database
migrates, processes start, traffic arrives, something breaks, and somebody has
to work out what.

---

# Part A — What "Production" Actually Means

## A.1 The problem

Your code works. You have run it, clicked through it, and it does the right
thing.

**Now it has to run somewhere else** — a rented computer in a datacentre, with
no screen, that you reach only through a text connection. Nobody is watching it.
It must survive restarts, bad input, network failures and your next deployment.

**Production is not "the same code on a different computer."** Seven things
change, and every section of this chapter addresses one of them:

| On your laptop | In production |
|---|---|
| You are the only user | many people at once, unpredictably |
| You see errors on screen | nobody sees anything unless you record it |
| You restart it when it breaks | it must restart itself |
| Everything is installed already | the machine starts empty |
| Secrets sit in a file you edited | secrets must be injected, never committed |
| You stop it with Ctrl-C | it is stopped mid-request, on every deploy |
| Losing data is annoying | losing data is the end of the product |

## A.2 The three properties production needs

Everything in this chapter serves one of three goals:

**Reproducible** — the thing that runs is exactly the thing you tested, and can
be rebuilt identically tomorrow. *(Parts B, C, E.)*

**Observable** — when it misbehaves you can find out why, without being logged
in at the moment. *(Parts H, I.)*

**Recoverable** — failures are survivable: it restarts, it retries, it can be
rolled back, and the data can be restored. *(Parts J, L.)*

**If you remember nothing else from this chapter, remember those three words.**
They are also a very good structure for answering "how would you deploy this?"

---

# Part B — Build and Artifacts

## B.1 What a build is

**A build turns the code you wrote into the thing that actually runs.**

For the backend that is modest — Python runs its source directly, but the
libraries must be installed. For the frontend it is substantial: hundreds of
TypeScript files are type-stripped, joined, shrunk and turned into plain
JavaScript a browser understands.

**The output is called an artifact** — the deployable result. **Deploying means
putting an artifact somewhere it can run.**

## B.2 The naive approach, and why it fails

The obvious method: copy the files to the server, install what is missing,
start it.

It fails for reasons that are boring individually and fatal together:

1. **The server's operating system differs from yours.** Development here is on
   Windows; the server runs Linux. Different path separators, different case
   rules, different system libraries.
2. **Library versions drift.** You install today, a colleague installs next
   month, and a dependency has released a new version. Now two "identical"
   servers behave differently.
3. **System libraries are invisible dependencies.** Several Python packages here
   are thin wrappers around C libraries — image processing, OCR, PostgreSQL
   drivers. Missing one produces an error that mentions Python and is not about
   Python.
4. **You cannot go back.** Having installed on top of the previous version, the
   previous version no longer exists.

**"It works on my machine" is not a joke about carelessness. It is the accurate
description of a genuine engineering problem**, and containers are the answer to
it.

## B.3 Images and containers

Anchor first: a **process** is a running program with its own private memory
(Chapter 05).

**A container is a process that has been given its own private view of the
world** — its own filesystem, its own network interface, its own process list.
It runs on the host's operating system kernel, but it cannot see the host's
files or other containers unless you allow it.

**An image is the recipe.** A read-only package containing a filesystem: the
operating system files, your dependencies, your code, and a command to run.

> **An image is to a container what a class is to an object**, or what a recipe
> is to a meal. One image, many containers, all identical.

**That is the property that solves B.2.** The image contains the Linux system
libraries, the exact package versions, and the code — so what you tested is
byte-for-byte what runs. Rolling back is running the previous image, which still
exists.

**Docker** is the tool that builds images and runs containers. It won for one
reason: it made an existing capability of the Linux kernel usable by ordinary
developers with a text file and one command.

## B.4 The real backend image

[`infrastructure/Dockerfile.backend`](../infrastructure/Dockerfile.backend),
read in parts.

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY backend/requirements.txt .
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt
```

- **`FROM python:3.11-slim`** — start from an existing image with Python 3.11 on
  a minimal Linux. `slim` means the trimmed version.
- **`AS builder`** — name this stage. There will be two.
- **`WORKDIR`** — the folder inside the image where later commands run.
- **`COPY backend/requirements.txt .`** — copy *only* the dependency list, not
  the code. That is deliberate and B.6 explains why.
- **`apt-get install build-essential libpq-dev`** — compilers and PostgreSQL
  headers, needed to *build* some packages.
- **`rm -rf /var/lib/apt/lists/*`** in the same command — delete the downloaded
  package index. Same command, because of how layers work (B.6).
- **`pip wheel`** — build every dependency into a wheel (a pre-built package
  file) rather than installing it.

Then the second stage:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y libpq-dev libgl1 libglib2.0-0 tesseract-ocr poppler-utils curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-cache --no-index --find-links=/wheels -r requirements.txt

COPY backend /app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**This is a multi-stage build.** A fresh image starts, copies only the finished
wheels from the builder, and installs them. **The compilers never appear in the
final image** — smaller, and less to attack.

Six details worth understanding:

**The runtime system libraries** are exactly Chapter 16's pipeline made
concrete: `libgl1` and `libglib2.0-0` for image processing, `tesseract-ocr` and
`poppler-utils` for reading scanned documents, `libpq-dev` for PostgreSQL, and
`curl` for the container's own health check.

**`--no-index`** means "do not contact the internet". Everything must come from
the wheels already built, so the image cannot drift from what the builder
resolved. The Dockerfile records a failed earlier attempt where using
`--no-deps` wheeled only top-level packages, leaving the final install to
resolve missing dependencies fresh — which was unsatisfiable and failed the
build.

**`COPY backend /app`** copies the application code — including `alembic/`,
because the deployment start command runs migrations, and the Dockerfile warns
that this silently does nothing if the versions folder is absent.

**`ENV PYTHONUNBUFFERED=1`** turns off output buffering. Without it, logs appear
late or vanish when the process crashes — so the last thing you see is not the
last thing that happened. **This one line decides whether you can debug a
crash.**

**`EXPOSE 8000`** is documentation, not a firewall rule. It records which port
the image expects to use.

**`CMD [...]`** is the default command. `--host 0.0.0.0` accepts connections on
every interface — inside a container, `127.0.0.1` would mean "only from inside
this container", and the symptom is a refused connection with *no error in the
application log*, because the request never arrives. `${PORT:-8000}` uses the
platform's assigned port when there is one.

## B.5 The frontend image, and a trap worth knowing

[`infrastructure/Dockerfile.frontend`](../infrastructure/Dockerfile.frontend)
opens with a comment recording a real mistake:

```dockerfile
# Two targets:
#   --target dev  → `next dev`, for the bind-mounted docker-compose workflow
#   (default)     → `next build` + `next start`, an actual production image
# The previous single-stage image ran `npm run dev` unconditionally; a dev
# server must never be what gets deployed.
```

**A development server is not a production server.** It recompiles on every
change, serves unminified code, prints internal details in errors, and is far
slower. Shipping one is a performance and information-disclosure problem at
once.

And then the trap:

```dockerfile
FROM deps AS builder
COPY frontend .
# NEXT_PUBLIC_* values are inlined into the bundle at build time, so the API
# URL has to be present here — setting it only at runtime has no effect.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build
```

**Backend configuration is read when the program runs. Frontend configuration is
baked in when the bundle is built.** A `NEXT_PUBLIC_*` value is literally
substituted into the JavaScript, so setting it at runtime does nothing at all —
the value is already inside the file the browser downloaded.

**Three consequences:**

1. One frontend image is **not** environment-independent. Staging and production
   need separate builds if their API URLs differ.
2. **Never put a secret in a `NEXT_PUBLIC_` variable.** It is shipped to every
   browser.
3. Rolling back the frontend means rolling back to an image built with the right
   URL — you cannot fix it with an environment change.

## B.6 Layers, caching and `.dockerignore`

Each instruction creates a **layer** — a saved filesystem change stacked on the
previous one. Docker caches layers: if an instruction and its inputs are
unchanged, the cached layer is reused.

**That is why dependencies are copied before code.** Dependencies change rarely
and code changes constantly. With this order, editing a Python file reuses the
cached install layer and rebuilds in seconds. Reverse the order and every code
change reinstalls every dependency.

**And it is why `rm -rf /var/lib/apt/lists/*` shares a command with
`apt-get`.** A layer is a permanent record; deleting a file in a *later* layer
does not remove it from the image, it only hides it. Deleting in the same
command means the files never enter a layer at all.

**`.dockerignore`** lists what to exclude from the build — `node_modules`, the
virtual environment, `.git`, `.env`. It keeps images small, builds fast, and
**secrets out of images**.

---

# Part C — Configuration and Secrets

## C.1 Same artifact, different environments

An **environment** is one running copy of the system: development, staging,
production. **The artifact must be identical across them** — otherwise you are
not shipping what you tested — so everything that differs must come from
outside.

That is what **environment variables** are: named pieces of text the operating
system hands a process when it starts (Chapter 05).

## C.2 Failing fast

Ten settings in this project have **no default**: the two secret keys, the
frontend URL, the four PostgreSQL fields, the Redis URL and the two Celery
URLs. A missing one crashes the process at startup.

**Why crashing is the right behaviour:** a default secret key is not a
convenience, it is a vulnerability that looks like a working system. Chapter 15
covered the real version — a hardcoded development secret in public source code
meant anyone could forge a token for any user.

**Crashing at boot with a clear message beats booting successfully and being
silently insecure.**

## C.3 Secrets

**A secret is any value that grants access.** Three rules:

1. **Never in the repository.** `.env` is in `.gitignore`, and `.env.example`
   documents the variable *names* with placeholder values.
2. **Never in a frontend build** (B.5).
3. **Injected by the platform.** Railway, Vercel and similar hosts have a
   settings page that supplies variables to the process. They are never written
   to disk in the image.

**A secret committed once is compromised forever**, even if deleted, because it
remains in the repository's history.

## C.4 Configuration drift

**Drift** is when the same setting has different values in different places and
nobody notices.

A real one, recorded in
[`core/config.py`](../backend/app/core/config.py):

```python
    # Monitoring — M-7: defaults are OFF (opt-in). config.py said True while
    # .env.example said false; and a stack without an OTLP collector spams
    # span-export errors.
    OTEL_ENABLED: bool = False
    PROMETHEUS_ENABLED: bool = False
```

The code's default and the documented default disagreed. **Anyone reading the
example file would have believed telemetry was off while the code turned it
on** — and with no collector attached, that produces a flood of export errors,
which trains everyone to ignore the logs.

**The fix is not just picking a value. It is picking one and making the two
sources agree**, which is why the comment records both.

---

# Part D — Composing the System Locally

## D.1 Why one container is not enough

This system is six programs: the API, the worker, the scheduler, PostgreSQL,
PgBouncer and Redis — plus the frontend. Starting them by hand, in the right
order, with the right settings, is a page of commands nobody runs correctly
twice.

**Docker Compose** describes them in one file and starts them with one command.

## D.2 The real file

From [`infrastructure/docker-compose.yml`](../infrastructure/docker-compose.yml):

```yaml
  db:
    image: ankane/pgvector:v0.5.1
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 5s
      retries: 5

  backend:
    build:
      context: ..
      dockerfile: infrastructure/Dockerfile.backend
    env_file:
      - ../backend/.env
    environment:
      - POSTGRES_SERVER=pgbouncer
      - POSTGRES_PORT=6432
    depends_on:
      db:
        condition: service_healthy
```

Six things, each solving a specific problem:

- **`image:` versus `build:`** — use a published image, or build one from a
  Dockerfile.
- **`ports: "5433:5432"`** — port 5433 on your machine forwards to 5432 inside.
  They differ because your laptop may already run PostgreSQL on 5432, and only
  one program can hold a port.
- **`volumes: postgres_data:/var/lib/...`** — a **volume** is storage that lives
  outside the container. **Without it, deleting the container deletes the
  database**, because a container's own filesystem is temporary. This one line
  is the difference between a database and a scratchpad.
- **`env_file`** plus **`environment`** — load the whole `.env`, then override
  specific values. The overrides matter: inside the Docker network the database
  is reached at the hostname `pgbouncer`, not `localhost`.
- **`healthcheck`** — a command Docker runs periodically to decide whether the
  container is working (Part H).
- **`depends_on: condition: service_healthy`** — do not start this until that
  one is *healthy*, not merely *started*. Without the condition, the backend
  starts while PostgreSQL is still initialising and dies on its first query.

**And the local override file** demonstrates a good habit: it changes **only**
the Redis host port, from 6380 to 6381, because another container on the machine
holds 6380. The comment notes container-to-container traffic is unaffected
because it uses `redis:6379` on the private network. **One narrow change with
its blast radius stated.**

## D.3 What Compose is not

Compose runs containers on **one machine**. It does not spread them across
several, does not restart them on a different host when one dies, and does not
do rolling updates.

**That is where Kubernetes fits** — a system for running containers across many
machines, with automatic restarts, scaling and rolling deployments. It is also a
large amount of machinery: for a system with three processes and one developer,
it would be more complex than the thing it manages.

**The honest sequence** is Compose for development → a managed platform
(Railway, Render, Fly) for a small production system → Kubernetes when you have
enough services and enough people that its coordination pays for its cost.
**This project is at the second step**, and saying that in an interview is a
better answer than claiming Kubernetes.

---

# Part E — CI: What Happens on Push

## E.1 The problem

You push a change. Does everything still work? *"It worked on my machine"* — but
your machine has leftover packages, a database with your test data, and
environment variables you set weeks ago and forgot.

**Continuous integration** is a fresh, empty machine that installs everything
from scratch and runs the checks, automatically, on every push.

**The value is the emptiness.** It cannot depend on anything you forgot you had.

## E.2 The real workflow

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml), step by step.

**Trigger:**

```yaml
on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
```

**Configuration**, and note *why* it must be here:

```yaml
    # The FastAPI Settings object (core/config.py) has ten required fields with
    # no defaults — including AUTH_SECRET_KEY/CSRF_SECRET_KEY. Locally they come
    # from backend/.env; CI has no .env, so importing `settings` ... fails
    # validation unless we provide them here. Test-only values; the real secrets
    # are supplied by the deployment.
    env:
      ENVIRONMENT: test
      AUTH_SECRET_KEY: ci-test-auth-secret
      ...
```

**Fail-fast configuration has a consequence: every environment must supply the
values, including the robot.** That is the correct trade, and the comment makes
it obvious rather than mysterious.

**Real dependencies, not fakes:**

```yaml
    services:
      postgres:
        image: ankane/pgvector:v0.5.1
        options: >-
          --health-cmd pg_isready
      redis:
        image: redis:7-alpine
```

CI starts a real PostgreSQL with the vector extension and a real Redis.
**Testing against a fake database proves your fake works.**

**A blocking security scan:**

```yaml
    - name: Dependency Vulnerability Scanning
      run: |
        # M-6: blocking — the audit was verified clean on 2026-07-19. If a new
        # vulnerability lands, triage it explicitly (--ignore-vuln ID) rather
        # than reverting to a swallowed failure.
        pip-audit -r requirements.txt --no-deps
```

`pip-audit` checks dependencies against a database of known vulnerabilities.
**The comment is the interesting part:** it was previously non-blocking, so
failures were ignored. Making it blocking forces a decision — fix it, or record
an explicit exception with an id. **A check whose failure is ignored is not a
check.**

**Wait, migrate, test:**

```yaml
    - name: Database Startup Readiness Check
      run: ./scripts/prestart.sh

    - name: Run Alembic Migrations
      run: alembic upgrade head

    - name: Execute API Contracts & Regression Tests
      run: pytest tests/ -v
```

`prestart.sh` waits for PostgreSQL to accept connections — *"the application
waits for the database ... before attempting to run migrations"* — because a
started container is not a ready one (Part H). Then migrations run against a
real empty database, which **also tests that the migrations themselves work**,
not just the code. Then the tests.

**And the frontend:**

```yaml
        # M-5: Next.js 16 requires Node >= 20; 18 diverged from local builds.
        node-version: "20"
    - run: npm run lint
    - run: npm run build
```

Another drift note. **The production build is the test**: if the build fails, no
deployable artifact exists, which is the most fundamental check there is.

## E.3 What is missing, honestly

This is CI without CD. There is **no step that builds and publishes an image, and
no step that deploys.** The pipeline proves the code is good; a human then
deploys.

**That is a legitimate choice for a small project** — automated deployment
without automated rollback is a way to break production quickly — but it should
be a decision, and the natural next step is to build and tag an image in CI so
that the artifact that was tested is the artifact that ships.

---

# Part F — Deployment and Start-up

## F.1 The start command

[`railway.json`](../railway.json):

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "infrastructure/Dockerfile.backend"
  },
  "deploy": {
    "startCommand": "bash -c 'alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT'",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Three decisions in nine lines.

**Build from the Dockerfile**, so the platform builds the same image you can
build locally.

**Migrate, then start.** `&&` means the server only starts if migrations
succeeded. **The order is not optional:** starting first would run new code
against an old schema, and every request touching a new column would fail.

**Restart on failure, up to ten times.** Automatic restart handles transient
problems — a dependency that was briefly unreachable. The limit prevents an
infinite crash loop from burning resources forever.

## F.2 The risk in running migrations at start-up

Convenient, and it has a real hazard: **if you run several copies of the API,
they all run migrations at once.** Alembic takes a lock so they do not corrupt
each other, but the others wait, and a slow migration delays every instance's
start.

**The alternatives**, with their costs:

- **A separate migration step before deploying.** Cleaner and correct at scale;
  requires the platform to support a pre-deploy command.
- **Migrate by hand.** Full control, and a human must not forget.

**This project's choice is right for one instance and would need revisiting at
three** — exactly the kind of statement that makes a good interview answer.

## F.3 Cold starts

**A cold start is the delay before a freshly started process can serve
traffic.**

Here it is significant, because the worker loads two machine-learning models —
the compose file records a **65.7-second** reload for the embedding model when a
worker child recycles.

**Two consequences:**

- The first request after a deploy is slow. Systems that care send synthetic
  traffic to warm a new instance before sending real users to it.
- **Health checks must account for it** (Part H), or the platform kills a
  container that was merely still starting.

## F.4 What actually runs

Three processes from one image, plus the frontend:

| Process | Command | Scales by copying? |
|---|---|---|
| API | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | **yes** — stateless |
| Worker | `celery ... worker -Q ... --concurrency=2` | **yes** — jobs come from a queue |
| Beat | `celery ... beat --schedule=/tmp/celerybeat-schedule` | **no — exactly one** |

**Beat holds the schedule**, so a second copy fires every scheduled job twice —
double emails. The compose file states it in capitals for that reason.

**Stateless components scale by copying; stateful ones do not.** That single
distinction answers most "how would you scale this?" questions.

---

# Part G — The Edge: Proxies, TLS and Streaming

## G.1 What sits in front

A **reverse proxy** is a server that receives requests from the internet and
forwards them to your application. Nginx and Caddy are common; hosting platforms
provide one automatically.

**Why have one at all?**

1. **TLS termination.** It handles the encryption (Chapter 05), so your
   application speaks plain HTTP internally.
2. **One public address** in front of several internal services — for example
   `/api` to the backend and everything else to the frontend.
3. **Protection.** It can absorb slow connections and enforce limits before
   traffic reaches your code.
4. **Serving static files** far more efficiently than an application can.

## G.2 The two settings that break this product

Generic advice would stop there. **This application streams answers token by
token**, which makes two proxy settings load-bearing.

**The idle timeout.** Proxies close connections that produce nothing for 30 or
60 seconds. A grounded answer can take longer than that to *start* if retrieval
is slow — and a long answer streams for a while. **A default timeout will cut
answers off mid-sentence**, and it will look like an application bug.

**Response buffering.** Many proxies collect a response and forward it once
complete — which is efficient and **completely destroys streaming**. The user
waits in silence, then the whole answer appears at once. Every symptom points at
the application; nothing is wrong with the application.

**These two are the most common production surprises for a streaming product**,
and knowing to check them is a strong interview signal. With Nginx it is
`proxy_buffering off` and a raised `proxy_read_timeout`; with a platform it is
whatever equivalent they expose.

---

# Part H — Health Checks

## H.1 Two different questions

**Liveness: is this process alive?** If not, restart it.

**Readiness: can this process serve traffic right now?** If not, stop sending it
requests — but do **not** restart it.

**Why the distinction has teeth:** a process that is starting up, or has
temporarily lost its database, is *alive but not ready*. Restarting it makes
things worse: you lose the warm-up progress and it starts again from nothing —
a restart loop that turns a brief dependency blip into an outage.

## H.2 The real check

[`api/v1/endpoints/health.py`](../backend/app/api/v1/endpoints/health.py)
returns:

```python
    status = {
        "api": "ok",
        "db": "unknown",
        "redis": "unknown",
```

and then actually tests the database with a direct connection and Redis with a
ping.

**Why test dependencies rather than just returning "ok"?** Because an API that
cannot reach its database is not serving anything useful, and a check that
always says "ok" tells you nothing. **A health check that cannot fail is
decoration.**

**And the counter-argument, which matters just as much:** a health check that
tests too much becomes an outage generator. If it fails whenever *any*
dependency is briefly unavailable, a two-second Redis blip restarts your entire
fleet.

**The rule:** liveness should test only the process itself; readiness may test
the dependencies it genuinely needs to serve a request.

## H.3 A health check with a real cost

The database ping in this project is a **direct, unpooled connection**, made
every ten seconds. Chapter 02's connection budget counts it explicitly:

```
API 3+2 = 5 · worker 2×(1+1) = 4 · beat 1+1 = 2 · health ping = 1 → 12 of 15
```

**Your monitoring consumes production resources.** Not a reason to avoid it — a
reason to count it.

## H.4 Two real incidents

**The health check that probed a closed port.** The PgBouncer container defaults
to listening on 5432, while the port mapping, the health check and the
application all targeted 6432. The comment in the compose file records the
result:

> *"the healthcheck probed a closed port and stayed 'unhealthy' forever, which
> blocked worker and beat (they depend on pgbouncer being healthy) while the
> backend silently could not reach the pooler over the Docker network."*

**One wrong number, and two services never started at all** — because
`depends_on: condition: service_healthy` did exactly what it was told.

**The health check that could not get a connection.** When pool sizes were
hardcoded too high, the API held all fifteen connections at rest. The health
ping could not open a sixteenth, so:

> *"the container sat 'unhealthy' for 19 hours."*

**Both incidents share a shape:** the health check was *correct* and reported a
*real* failure. The bug was elsewhere, and the health check is how it became
visible. That is the system working — nineteen hours of visible failure is far
better than nineteen hours of invisible one.

---

# Part I — Observability

## I.1 Three questions, three tools

**Observability** is being able to tell what a running system is doing without
attaching a debugger. Three kinds of signal, answering different questions:

| Signal | Answers | Example |
|---|---|---|
| **Logs** | what happened, in detail, for one request | "task started for document 0a56…" |
| **Metrics** | how much, how often, how fast, in aggregate | "requests per second, p95 latency" |
| **Traces** | where the time went across components | "40 ms database, 2,100 ms model" |

**You need all three, and they are not substitutes.** Logs cannot tell you the
95th-percentile latency without enormous effort. Metrics cannot tell you why one
user's request failed. Traces cannot tell you the exact error message.

## I.2 Structured logging

Ordinary logs are sentences. Fine for reading; hopeless for searching a million
of them.

**Structured logging** writes each line as machine-readable data. From
[`core/json_logger.py`](../backend/app/core/json_logger.py):

```python
class JSONFormatter(logging.Formatter):
    """Emits a single JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact_pii(record.getMessage()),
        }
        for attr in ("request_id", "user_id", "workspace_id"):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
```

Four decisions:

- **JSON in production, plain text in development.** Machines search one;
  humans read the other.
- **`redact_pii`** strips emails, phone numbers and similar before writing.
  **Logs are a place personal data escapes to** — they are copied to log
  services, kept for months, and read by people who never see the database.
  Chapter 13 covered the same reasoning for error reports.
- **`request_id`** is the correlation id from the middleware, so every line
  belonging to one request can be found together. **This is the single most
  useful field in a production log**, and the id is also returned as a response
  header so a user's failed request can be traced from their side.
- **Level** — `ERROR`, `WARNING`, `INFO`. Severity is what lets you say "show me
  only the errors" across millions of lines.

**Log levels, used properly:** `ERROR` means something needs attention;
`WARNING` means something unusual but handled; `INFO` means normal notable
events. **If everything is an error, nothing is.**

## I.3 Metrics

**A metric is a number over time.** From
[`core/telemetry.py`](../backend/app/core/telemetry.py):

```python
    metric_reader = PrometheusMetricReader()
    ...
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
```

**Prometheus** is a system that periodically fetches numbers from an endpoint
your application exposes and stores them over time. Mounting `/metrics` is
literally that endpoint.

**What to measure**, and the standard starting set is easy to remember —
**Rate, Errors, Duration**:

- requests per second, per endpoint
- error rate, per endpoint
- latency percentiles (p50, p95, p99 — Chapter 02)

Plus, specific to this system: **queue depth** (Chapter 12's early-warning
number), documents stuck in `PROCESSING`, model API latency, and tokens consumed
per hour.

**Why percentiles rather than averages:** with 99 requests at 100 ms and one at
10 seconds, the average of 199 ms describes nobody. p95 states a promise about
real users.

## I.4 Traces

A **trace** follows one request across components, recording how long each step
took. This project instruments both sides:

```python
    if app and not is_worker:
        FastAPIInstrumentor.instrument_app(app)
    if is_worker:
        CeleryInstrumentor().instrument()
```

with the comment: *"Auto-instruments Celery tasks, continuing TraceContext from
the API message broker."*

**That is the valuable part.** Chapter 12 explained that the API and the worker
are separate processes communicating through a queue. Tracing across that
boundary means a single trace can show *"the request took 80 ms and queued a job
that took four minutes"* — a story neither process could tell alone.

**One honest caveat**, visible in the code: the span exporter is
`ConsoleSpanExporter`, which prints traces to the log. The comment says *"In
production, replace with OTLPSpanExporter for Jaeger/Tempo/Datadog."*
**Traces printed to a log are not traces you can query.** The instrumentation is
in place; the destination is not.

## I.5 Errors and product analytics

**Sentry** collects unhandled exceptions with their stack traces, groups
identical ones, and tells you when a new kind appears. Configured in `main.py`
with sampling — `traces_sample_rate=0.05` means 5% of requests, because
recording all of them is expensive — and with the `before_send` hook that strips
request bodies (Chapter 13). **A user's private question must not end up in a
third-party dashboard.**

**PostHog** records product events — which features are used. Chapter 08 showed
its privacy-by-design shape: `query_length_chars` instead of the query,
`file_size_mb_bucket` instead of a filename.

**Three different destinations, three different privacy decisions**, each made
deliberately. That pattern — *ask of every outbound channel what user content it
carries* — is worth carrying to any system.

## I.6 The gap: nothing is watching

Telemetry defaults to **off** (`OTEL_ENABLED: bool = False`), which is correct
for a laptop with no collector. And nothing alerts.

**Observability without alerting means you find out when a user tells you.**
Chapter 12's incident is the proof: a bad worker flag caused a crash loop while
uploads kept "succeeding", and the only signal was a queue growing to 134 jobs —
a number nobody was watching.

**The first three alerts I would add**, in order: queue depth above a threshold
for five minutes; any document in `PROCESSING` for over thirty minutes; and the
API error rate above 1%. Each maps to a failure this project has actually had.

---

# Part J — Handling Failure

## J.1 Timeouts

Every call to something else needs a limit, or a hung dependency holds your
worker forever.

`LLM_TIMEOUT_SECONDS: int = 120` bounds the model call — and Chapter 07 showed
the subtlety: for the *streaming* path it bounds **each chunk**, not the whole
stream, because a long answer is legitimate while a chunk that never arrives is
not.

**Ask of every timeout: what unit should this bound?**

## J.2 Retries

Chapter 12 covered these: exponential backoff (1, 2, 4 seconds), a ceiling of
three attempts, and a guaranteed terminal state so a document never sits in
limbo. **Only retry transient failures** — a corrupt file will still be corrupt
on attempt four.

## J.3 Rate limiting

**Rate limiting caps how often something may be called**, protecting you from
abuse, from runaway clients, and from your own cost.

[`core/rate_limiter.py`](../backend/app/core/rate_limiter.py) defines one shared
limiter keyed by client IP, applied per endpoint:

```python
@router.post("/stream")
@limiter.limit("30/minute")
```

Thirty questions a minute per IP — generous for a human, restrictive for a
script, and it directly bounds model spending.

**The weakness**, consistent with what this project criticises elsewhere: it is
opt-in per endpoint, so **a new endpoint has no limit unless somebody
remembers**. A default limit with explicit exemptions would be the stronger
shape.

## J.4 Graceful shutdown — the real gap

**Graceful shutdown means finishing current work before stopping.** When a
platform deploys a new version it asks the old process to stop; a well-behaved
process stops accepting new requests, finishes what it is doing, and exits.

**This project has no shutdown handling** (Chapter 13, Part L). For a product
whose main interaction is a multi-second stream, that means **every deploy cuts
live answers off mid-sentence.**

Invisible in development, because you deploy while nobody is using it. Guaranteed
in production, because someone always is.

## J.5 Resource limits

A container can be given a memory ceiling. Exceed it and the operating system
kills the process — an **OOM kill** (out of memory), which looks like an
unexplained restart with nothing useful in the log.

**Why set a limit at all**, given that? Because without one, a runaway process
takes the whole machine down instead of only itself. **A limit converts a total
outage into one dead container that restarts.**

Relevant here because the worker loads machine-learning models, which is why it
recycles children every 50 tasks to bound memory growth.

## J.6 Backups — the largest gap

**A backup is a copy of your data you can restore from.**

This is the most serious omission in the project, because it is the only failure
that cannot be undone. Everything else — a bad deploy, a crashed worker, a wrong
configuration — is recoverable. Lost documents are not.

**What a real answer looks like**, and this is what interviewers listen for:

1. **Automated daily snapshots**, retained for a period.
2. **Point-in-time recovery** if the database supports it, so you can restore to
   *just before* a bad migration.
3. **A tested restore.** *An untested backup is a hope, not a backup.* Restoring
   into a scratch environment quarterly is the only way to know it works.
4. **The uploaded files too**, not only the database — the rows point at storage
   that must also survive.

---

# Part K — Scaling

## K.1 Two directions

**Vertical scaling** — a bigger machine. Simple, no code changes, a hard
ceiling, and usually a restart to resize.

**Horizontal scaling** — more machines. No ceiling, and it only works for
components that keep nothing important in their own memory.

## K.2 What scales here

| Component | Scales horizontally? | Why |
|---|---|---|
| API | **yes** | stateless — the session lives in a signed cookie, not in memory |
| Worker | **yes** | jobs come from a shared queue |
| Beat | **no** | holds the schedule; a second copy duplicates every job |
| PostgreSQL | not simply | one writer; read replicas are the usual first step |
| Redis | not simply | shared state by definition |

**Chapter 15's cookie decision pays off here.** Because the session is a signed
token rather than server memory, any API instance can serve any request — which
is precisely what makes horizontal scaling possible at all.

## K.3 The real ceilings

Adding instances does not help past whatever runs out first, and here it is not
CPU:

1. **Database connections — about fifteen for the whole project.** Each API
   instance takes five. **Three instances and there is nothing left for the
   worker.** This is the binding constraint, and it is why the arithmetic is
   written in `config.py`.
2. **The model API's requests-per-minute limit**, which key rotation stretches
   but does not remove.
3. **Worker throughput**, bounded by processor and memory for OCR.

**"Scale the API" is the wrong answer here.** The right one is: raise the
connection ceiling (move the pooler to transaction mode, which holds a server
connection only for the length of a transaction rather than the whole session),
then add instances.

**Knowing which resource binds is the whole skill.** Anyone can add servers.

---

# Part L — Deploying an Update Safely

## L.1 Rolling deployments

A **rolling deployment** replaces instances one at a time, so the service stays
up. **The consequence people forget: old and new code run simultaneously**,
often for minutes.

Everything must therefore be backward compatible for one release:

- **The database schema** must work with both versions (Chapter 14's three-step
  rename).
- **The API contract** must not break older frontend bundles still loaded in
  users' browsers.
- **Queued jobs** written by old code must be readable by new workers.

That last one is easy to miss: a job sitting in Redis was serialised by the old
version. **Changing a task's arguments without a transition breaks every job
already queued.**

## L.2 Rollback

**Roll back the code, not the schema.** This is why safe migrations matter: if
the schema change was backward compatible, the previous image runs against it
unchanged.

`downgrade()` functions exist but cannot restore data, and are usually untested
— emergency-only code that first executes during an emergency.

**And one rollback trap specific to this project:** the frontend's API URL is
baked in at build time (B.5). Rolling back the frontend means deploying an image
built with the right URL — an environment variable change will not fix it.

## L.3 The safe-deploy checklist

1. CI green on the exact commit.
2. Migrations reviewed for backward compatibility.
3. Deploy during low traffic if the change is risky.
4. Watch error rate and latency for the first few minutes.
5. Have the previous image ready to redeploy.

---

# Part M — One Request, in Production

Everything above, applied to one journey. **Production components are named at
each step.**

**A user uploads a 200-page scanned contract.**

1. Their browser resolves your domain through **DNS** and connects over
   **HTTPS**. A **reverse proxy** terminates TLS and forwards plain HTTP to the
   API container.
2. The request passes the middleware chain — a **correlation id** is attached
   and will appear in every log line for this request, and in the response
   header.
3. The API asks for a **database connection** from its pool, which reaches
   PostgreSQL through **PgBouncer**, sharing a small number of real
   connections. A row is created.
4. A job is placed on **Redis**. The API returns in milliseconds. **If Redis is
   unreachable, the document is marked FAILED and the user gets a 503** — a loud
   failure rather than a document that silently never processes.
5. The **Celery worker** — a separate container, from the same image — takes the
   job. Its **trace context** continues the API's trace, so both appear as one
   story.
6. It downloads the file from **storage** (S3 in production, because a
   container's own disk is temporary), runs **OCR**, chunks, embeds with the
   local model, and writes rows in batches. If it crashes, the platform
   **restarts** it and the job is redelivered.
7. Structured logs record each stage with the document id. **Metrics** record
   queue depth and processing duration.

**Then they ask a question.**

8. `POST /query/stream` arrives, is authenticated, and the trial quota is
   checked.
9. **Redis** is consulted as a cache. On a miss, the pipeline runs — embedding
   and reranking on worker threads so the event loop stays free.
10. The model API is called with a per-chunk **timeout**, through the **key
    rotator** to stay inside rate limits.
11. Tokens stream back as **server-sent events** — **which is why proxy
    buffering must be off and the idle timeout must be long enough.**
12. The answer is persisted. **Sentry** would capture any unhandled exception,
    with the request body stripped.

**And when a deploy happens mid-answer**, that stream is cut off, because
graceful shutdown is not implemented. Which is the honest end to the story, and
the first thing on the list below.

---

# Part N — Debugging Production

**The method, cheapest first. Never start by reading code.**

**1. What is the symptom, precisely?** "Slow" and "broken" are not symptoms.
"Uploads succeed but stay Processing" is.

**2. Is it everything or one thing?** If unrelated endpoints — including a
trivial health check — are affected, the cause is shared: the event loop, the
connection pool, or a dependency. That single question eliminates most
candidates.

**3. What changed?** A deploy, a configuration change, a dependency update, or
a traffic increase. Most incidents follow a change.

**4. Look at the signals, in this order:**

```bash
docker compose ps                                    # is everything running?
curl -i http://localhost:8000/api/v1/health          # does it say what is unhealthy?
docker compose logs --tail=200 backend               # errors, filtered by correlation id
docker compose exec redis redis-cli LLEN main-queue  # is work piling up?
```

Plus, on the database:

```sql
SELECT pid, state, query, now() - query_start AS duration
FROM pg_stat_activity WHERE state <> 'idle' ORDER BY duration DESC;
```

Long-running queries, and sessions stuck `idle in transaction`, which is the
classic cause of connection exhaustion.

**5. Form one hypothesis and test it.** Changing three things at once means not
knowing which worked.

**6. Only then read code**, in the component the evidence points at.

**Two shortcuts worth internalising**, both from this project's own history:

- **A status code tells you which layer failed.** 404 routing, 422 validation,
  401 authentication, 403 CSRF, 500 your code, 503 a dependency.
- **The symptom appears far from the cause** for concurrency, process and pool
  bugs. The fork-corrupted connections looked like database faults; the blocking
  event loop looked like a slow model provider.

---

# Part O — Production Mistakes

1. **Shipping a development server.** Slow, unminified, leaks internals.
2. **Secrets in the image or in a `NEXT_PUBLIC_` variable.**
3. **No volume on the database container** — the data dies with the container.
4. **`depends_on` without a health condition**, so services start before their
   dependencies are ready.
5. **A health check that always returns ok**, or one so deep that a blip
   restarts the fleet.
6. **Logs without correlation ids**, so one request cannot be reconstructed.
7. **Personal data in logs or error reports.**
8. **No graceful shutdown**, so every deploy cuts live requests.
9. **Proxy buffering left on** with a streaming API — a silent, total feature
   failure.
10. **Unsafe migrations during a rolling deploy.**
11. **Alerting on nothing**, so users are your monitoring.
12. **Untested backups.**

---

# Part P — Exercises

**P1.** Explain images and containers to someone non-technical, then say what
problem they solve that copying files does not.

**P2.** Why does the backend Dockerfile copy `requirements.txt` before the
code? What breaks if you reverse it?

**P3.** Why is `PYTHONUNBUFFERED=1` set? Describe the failure it prevents.

**P4.** Explain why a `NEXT_PUBLIC_` variable cannot be changed at runtime, and
give two consequences.

**P5.** Explain the difference between liveness and readiness, and why
restarting a not-ready process makes things worse.

**P6.** The PgBouncer health check probed the wrong port. Walk through the full
consequence chain and say what the system was doing correctly.

**P7.** The CI workflow declares ten environment variables with fake values.
Explain why it must, and what design decision makes that necessary.

**P8.** Why is `pip-audit` blocking rather than advisory? What does the comment
say happens if a new vulnerability appears?

**P9.** Give three things you would measure in this system and say what decision
each would inform. Then name the three alerts you would create first.

**P10.** A user says answers "appear all at once after a long wait, instead of
streaming". The application code is unchanged. Give the two most likely causes
and how to confirm each.

**P11.** You are asked to run three copies of the API. What breaks first, and
what would you do before adding instances?

**P12.** Write the deployment plan for a change that adds a required column to
the documents table, on a live system with users.

**P13.** Design the backup strategy: what is copied, how often, retained how
long, and how you know it works.

**P14.** The start command runs `alembic upgrade head && uvicorn ...`. Give one
advantage and one risk, and say at what point you would change it.

**P15.** Explain, to an interviewer, how you would deploy this repository from
scratch — build, configuration, database, workers, frontend, observability — in
under two minutes of speaking.

---

# Part Q — Answer Key

**Q1.** An **image** is a sealed package containing an operating system's files,
your dependencies and your code — like a recipe. A **container** is one running
copy of it — like a meal cooked from that recipe. One image, many identical
containers.

It solves what copying files cannot: the machine's operating system, library
versions and system packages are all *inside* the image, so what you tested is
byte-for-byte what runs. And because the old image still exists, rolling back is
running it again rather than reinstalling and hoping.

**Q2.** Because each instruction creates a cached layer, and Docker reuses a
layer when its inputs are unchanged. Dependencies change rarely; code changes
constantly. With this order, editing a Python file reuses the cached install and
rebuilds in seconds.

Reversed, every code change invalidates the install layer, so every build
reinstalls every dependency — turning a ten-second rebuild into several minutes,
on every commit.

**Q3.** Python buffers output by default, writing it in batches. In a container
that means logs appear late or are lost entirely when the process crashes — so
the last lines you see are not the last things that happened, and the actual
cause of a crash is missing. Unbuffered output costs a little performance and
makes crashes debuggable.

**Q4.** Because `NEXT_PUBLIC_*` values are substituted into the JavaScript
bundle when it is *built*. By the time the container runs, the value is already
inside the file the browser downloads, so changing the environment variable
changes nothing.

Consequences: staging and production need separate builds if their API URLs
differ, so one image is not environment-independent; and **a secret in such a
variable is shipped to every browser** — it is public by construction. A third
follows for rollback: you must redeploy an image built with the right value.

**Q5.** **Liveness** asks "is the process alive?" — if not, restart it.
**Readiness** asks "can it serve traffic now?" — if not, stop sending requests
but leave it alone.

Restarting a not-ready process makes things worse because the usual reason for
being not-ready is *still starting* — loading models, warming caches — or a
temporarily unavailable dependency. Restarting throws away the progress and
begins again, so a brief blip becomes a restart loop, and a restart loop is an
outage.

**Q6.** The PgBouncer image defaults to listening on 5432; the port mapping, the
health check and the application all targeted 6432. So the health check probed a
port nothing was listening on, and the container was marked unhealthy forever.

Because the worker and beat declared `depends_on: condition: service_healthy`,
**they never started at all** — no document was processed and no scheduled job
ran. Meanwhile the backend could not reach the pooler over the Docker network.

What the system did correctly: everything. The health check reported a real
failure, and `depends_on` refused to start services whose dependency was broken.
**A visible failure is the system working**; the bug was one wrong number in the
configuration.

**Q7.** Because ten settings have no defaults, so importing the settings object
— which every module does — fails validation without them. CI has no `.env`
file, so it must supply them.

The design decision that makes it necessary is **fail-fast configuration**: no
default secrets, because a default secret is a vulnerability that looks like a
working system. The consequence is that *every* environment must provide the
values, including automated ones. That is the correct direction for the
inconvenience to point.

**Q8.** Because a check whose failure is ignored is not a check. Non-blocking
means the pipeline goes green with known vulnerabilities in the dependency list,
and nobody reads the output.

The comment says a new vulnerability must be triaged explicitly — fixed, or
suppressed by id with `--ignore-vuln` — *"rather than reverting to a swallowed
failure."* That forces a decision and leaves a record of who decided.

**Q9.** Three measurements:

- **Queue depth** — informs whether to add worker capacity, and distinguishes
  "overloaded" from "broken" (growing while workers are idle means routing is
  broken, not capacity).
- **p95 latency for `/query/stream`** — informs whether the pipeline is
  degrading, and which stage to profile.
- **Model API error rate** — informs whether to add keys, back off, or switch
  models.

Three alerts first: queue depth above a threshold for five minutes; any document
in `PROCESSING` for over thirty minutes; API error rate above 1%. Each
corresponds to a failure this project has actually experienced.

**Q10.** **Proxy response buffering.** Many proxies collect a response and
forward it once complete, which destroys streaming while leaving the application
untouched. Confirm by requesting the endpoint directly against the container,
bypassing the proxy — if it streams there and not through the proxy, that is it.

**A timeout or buffering setting changed at the platform level**, or a new proxy
in front. Confirm by checking whether the change correlates with a deploy or an
infrastructure change rather than a code change.

The tell in both cases is that the application code is unchanged and the symptom
is entirely about *delivery*. This is the most common production surprise for a
streaming product.

**Q11.** **Database connections break first.** Each API instance takes five
(three pooled plus two overflow) from a project-wide budget of fifteen, so three
instances consume all fifteen and the worker, beat and health check get nothing —
the exact shape of the nineteen-hour unhealthy incident.

Before adding instances: move the pooler to transaction mode, where a server
connection is held only for the length of a transaction rather than a whole
session, which raises the effective ceiling substantially. Then re-do the
budget arithmetic and set the pool sizes to fit it.

**Q12.** Three deploys, because old and new code run together during a rolling
deployment:

1. **Add the column as nullable**, with no application change relying on it.
   Deploy. Old code is unaffected because nothing it uses changed.
2. **Backfill** existing rows, in batches if the table is large, then deploy
   code that writes the column for new rows and reads it defensively.
3. **Make it `NOT NULL`** once every row has a value and no running code writes
   rows without it.

Adding a `NOT NULL` column in one step fails immediately, because every existing
row violates it — and even with a default, the intermediate state would break
any old instance still running.

**Q13.** **What:** the PostgreSQL database *and* the uploaded files in object
storage — the rows point at files, so one without the other restores nothing
usable.

**How often:** automated daily snapshots, plus point-in-time recovery if the
provider offers it, so you can restore to just before a bad migration rather
than to midnight.

**Retention:** thirty days of dailies, with a monthly kept for a year — enough
to survive damage discovered late.

**How you know it works:** restore into a scratch environment on a schedule —
quarterly at minimum — and run a query proving the data is there. **An untested
backup is a hope.** I would also document the restore procedure with a target
recovery time, because the moment you need it is the worst moment to invent it.

**Q14.** **Advantage:** the schema is always migrated before the code that needs
it, automatically, with no separate step to forget — and `&&` means the server
does not start if migrations fail, so you never serve new code against an old
schema.

**Risk:** with several instances, all of them run migrations simultaneously on
deploy. Alembic locks so they cannot corrupt each other, but the others wait,
and a slow migration delays every instance's start — turning a schema change
into a partial outage.

I would change it at the point of running more than one instance, moving
migrations to a dedicated pre-deploy step.

**Q15.** *"Build a Docker image from the Dockerfile in CI — multi-stage, so the
compilers stay out of the runtime image — after the pipeline has run the
dependency audit, the migrations and the tests against a real PostgreSQL and
Redis.*

*Deploy that image to a platform like Railway. Configuration comes entirely from
environment variables: ten are required with no defaults, so a missing secret
crashes at boot rather than running insecurely. The start command runs
`alembic upgrade head` and only then starts Uvicorn, so the schema is never
behind the code.*

*Three processes from that one image: the API, a Celery worker consuming the
queues, and exactly one Beat scheduler — one, because it holds the schedule and
a second copy duplicates every scheduled job. PostgreSQL and Redis are managed
services; PgBouncer sits in front of the database because we have about fifteen
connections and each worker child has its own pool.*

*The frontend is a separate build, and its API URL is baked in at build time
rather than read at runtime.*

*For operations: health checks that actually test the database and Redis,
structured JSON logs with a correlation id and personal data redacted, Prometheus
metrics on `/metrics`, traces that follow a request from the API into the
worker, and Sentry with request bodies stripped.*

*The two things I would fix before calling it production-ready are graceful
shutdown — right now every deploy cuts a live streaming answer mid-sentence —
and backups, because that is the only failure we could not recover from."*

---

# Part R — Senior Critique

### Strengths

1. **Multi-stage, hermetic image build** — compilers excluded from the runtime
   image, and `--no-index` guaranteeing the image cannot drift from what the
   builder resolved.
2. **A real production frontend target**, after a version that shipped a
   development server, with the reason recorded.
3. **CI runs against real PostgreSQL and Redis**, and runs the migrations —
   testing the migrations themselves, not only the code.
4. **A blocking dependency audit**, with an explicit instruction to triage
   rather than silence failures.
5. **Migrations gated before start-up** by `&&`, so new code never meets an old
   schema.
6. **Health checks test dependencies**, and `depends_on: service_healthy` is
   used — which is exactly why two real misconfigurations became visible.
7. **Structured logging with correlation ids and PII redaction**, and three
   separate outbound channels each with a deliberate privacy decision.
8. **Tracing crosses the API/worker boundary**, so a queued job appears in the
   same trace as the request that created it.

### Weaknesses

1. **No graceful shutdown.** Every deploy truncates live streaming answers. The
   highest-impact defect here because it happens *every single time*.
2. **No backups.** The only unrecoverable failure, in a product whose entire
   value is the user's documents.
3. **No alerting.** Telemetry exists and nothing watches it; two documented
   incidents were visible only as a growing queue nobody was looking at.
4. **Traces go to the console**, so they are logs pretending to be traces —
   the instrumentation is done, the destination is not.
5. **CI has no CD.** No image is built or published, so the artifact that ships
   is not provably the artifact that was tested.
6. **Rate limiting is opt-in per endpoint**, so a new endpoint has none unless
   someone remembers.
7. **Migrations run in the start command**, which is fine at one instance and
   becomes a partial outage at three.
8. **No documented runbook.** The debugging knowledge in this chapter exists
   only in commit messages.

### The one improvement I would make first

**Graceful shutdown**, because it is the only defect on this list that occurs on
*every* deployment and is invisible until you have real users. It is a lifespan
handler and a container stop-timeout — perhaps twenty lines. **Backups** would
be second, and it is a close second: shutdown is a bad experience, data loss is
the end of the product.

---

# Part S — Interview Questions With Model Answers

**S1. "How would you deploy a FastAPI application?"**

> Build a container image so the artefact is reproducible, and run it with an
> ASGI server — Uvicorn — bound to `0.0.0.0` on a port the platform provides.
> Configuration comes from environment variables, with the required ones having
> no defaults so a missing secret crashes at boot rather than running
> insecurely.
>
> Migrations run before the server starts, so new code never meets an old
> schema. In front of it, a reverse proxy terminates TLS. Behind it, PostgreSQL
> through a connection pooler and Redis for the queue and cache. Background work
> runs as separate processes from the same image.
>
> Then health checks that actually test dependencies, structured logs with a
> correlation id, metrics, and error reporting with request bodies stripped.

**S2. "Why Docker? What is the difference between an image and a container?"**

> An image is a sealed read-only package — operating system files, dependencies,
> code, and a start command. A container is one running copy of it. Image is to
> container what a class is to an object.
>
> Docker solves a real problem, not a fashionable one. Our development machines
> are Windows and the server is Linux; several Python packages here wrap C
> libraries like the PostgreSQL driver and the OCR engine. Copying files to a
> server means the operating system, the library versions and the system
> packages all differ, and errors mention Python while not being about Python.
> With an image, what I tested is byte-for-byte what runs — and rollback is just
> running the previous image, which still exists.

**S3. "Liveness versus readiness?"**

> Liveness asks whether the process is alive; if not, restart it. Readiness asks
> whether it can serve traffic right now; if not, stop routing to it but leave
> it running.
>
> The distinction matters because restarting a not-ready process makes things
> worse. A process that is still loading models, or has briefly lost its
> database, is alive but not ready — restarting throws away the warm-up and
> starts again, so a two-second blip becomes a restart loop.
>
> We had a real case where a health check probed the wrong port, so a container
> was marked unhealthy forever and two services that depended on it never
> started. The health check was correct; it reported a real misconfiguration.

**S4. "What is observability, and what would you measure?"**

> Being able to tell what a running system is doing without attaching a
> debugger. Three signals answering different questions: logs say what happened
> in detail for one request, metrics say how much and how fast in aggregate, and
> traces say where the time went across components. They are not substitutes.
>
> For this system I would measure request rate, error rate and latency
> percentiles per endpoint — never averages, because 99 fast requests and one
> ten-second one averages to something that describes nobody. Plus queue depth,
> documents stuck in processing, and model API latency and token spend.
>
> Our tracing follows a request from the API into the Celery worker, so one
> trace shows an 80-millisecond request that queued a four-minute job — a story
> neither process could tell alone.

**S5. "How do you debug a production failure?"**

> Cheapest first, and never starting with code. Nail down the exact symptom.
> Then ask whether it is everything or one thing — if unrelated endpoints,
> including a trivial health check, are also slow, the cause is shared: the
> event loop, the connection pool, or a dependency. That one question eliminates
> most candidates.
>
> Then what changed, because most incidents follow a deploy or a configuration
> change. Then the signals in order: are the containers running, what does the
> health endpoint say is unhealthy, what do the logs say for that correlation id,
> is the queue growing, and what is the database doing right now.
>
> One hypothesis at a time. And I would remember that for concurrency and
> process bugs the symptom appears far from the cause — we had fork-corrupted
> connections that looked like database faults, and a blocked event loop that
> looked like a slow model provider.

**S6. "Horizontal or vertical scaling — and what breaks first here?"**

> Vertical is a bigger machine: simple, hard ceiling, usually a restart.
> Horizontal is more machines, with no ceiling, but only for components that
> keep nothing important in their own memory.
>
> Our API is stateless because the session is a signed cookie rather than server
> memory, so it scales horizontally. Workers scale too, since jobs come from a
> shared queue. Beat does not — it holds the schedule, so a second copy fires
> every scheduled job twice.
>
> But adding API instances is the wrong first move, because database connections
> break first. Each instance takes five from a project-wide budget of fifteen,
> so three instances leave nothing for the worker. The right sequence is to move
> the pooler to transaction mode to raise the ceiling, redo the budget
> arithmetic, and then scale. Knowing which resource binds is the whole skill.

**S7. "How do you deploy safely and roll back?"**

> Rolling deployment, replacing instances one at a time — which means old and
> new code run simultaneously for minutes. Everything must be backward
> compatible for one release: the schema, the API contract for browser bundles
> already loaded, and the shape of jobs already sitting in the queue.
>
> Schema changes follow the additive pattern: add nullable, backfill, then
> require, across separate deploys. A one-step rename breaks every running old
> instance.
>
> To roll back, I roll back the *code*, not the schema — which is exactly why
> the migration had to be backward compatible. `downgrade()` functions cannot
> restore data and are usually untested. One trap specific to us: the frontend's
> API URL is baked in at build time, so rolling it back means redeploying an
> image built with the right value.

**S8. "What is missing from your production setup?"**

> Three things, in order. Graceful shutdown — we have no lifespan handler, so
> every deploy cuts live streaming answers mid-sentence. It is invisible in
> development because you deploy when nobody is using it, and guaranteed in
> production because someone always is.
>
> Backups. It is the only failure we could not recover from, and in a product
> whose value is the user's own documents that is the most serious gap. I would
> want daily snapshots, point-in-time recovery, the object storage included, and
> a restore actually tested on a schedule — an untested backup is a hope.
>
> And alerting. We have logs, metrics and traces and nothing watches them. Two
> of our real incidents were visible only as a queue growing to 134 jobs, which
> nobody was looking at. Observability without alerting means users are your
> monitoring.

---

# Part T — Validation Checklist

- [ ] I can name the seven differences between a laptop and production, and the
      three properties production needs. *(A.1, A.2)*
- [ ] I can explain images versus containers and what problem they solve.
      *(B.3)*
- [ ] I can explain why dependencies are copied before code, and why the
      `apt-get` cleanup shares a command. *(B.6)*
- [ ] I can explain the `NEXT_PUBLIC_` build-time trap and its three
      consequences. *(B.5, Q4)*
- [ ] I can explain why ten settings have no defaults and what that forces on
      CI. *(C.2, E.2)*
- [ ] I can explain what a volume is and what happens without one on the
      database. *(D.2)*
- [ ] I can explain liveness versus readiness and why restarting a not-ready
      process is harmful. *(H.1)*
- [ ] I can retell the PgBouncer port incident and say what the system did
      correctly. *(H.4, Q6)*
- [ ] I can name the three observability signals and what each answers. *(I.1)*
- [ ] I can explain why a correlation id is the most useful field in a log.
      *(I.2)*
- [ ] I can explain why proxy buffering and idle timeouts are load-bearing for
      this product specifically. *(G.2)*
- [ ] I can say what scales horizontally here, what does not, and which resource
      binds first. *(K.2, K.3)*
- [ ] I can write the three-deploy plan for a required column. *(L.1, Q12)*
- [ ] I can deliver the two-minute "how would you deploy this" answer. *(Q15)*
- [ ] **The real test:** open
      [`Dockerfile.backend`](../infrastructure/Dockerfile.backend),
      [`docker-compose.yml`](../infrastructure/docker-compose.yml),
      [`railway.json`](../railway.json) and
      [`ci.yml`](../.github/workflows/ci.yml). For every line, say what it does,
      why it is there, and what would break without it.

If the last box is ticked, you can deploy, operate and defend this system — and
Chapter 18 can be about converting all of it into an offer.

---

*Next: `18-interview-capstone-and-career.md` — drills, the project narrative,
the cheat sheet, the capstone, and an honest read on where this stack puts you.*
