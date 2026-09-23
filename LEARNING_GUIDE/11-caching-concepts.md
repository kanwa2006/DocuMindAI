# 11 — Caching and Redis

**Prerequisites:** none. Anything borrowed from an earlier chapter is
re-explained in a sentence where it appears.

**Why this chapter is first in Part 2.** Caching is the topic where beginners
are most confident and most wrong. Adding a cache is easy — four lines. Knowing
*what* to cache, *how to name it*, *when to throw it away*, and *what happens
when it fails* is the part that separates a working system from one that serves
a deleted document to a stranger.

This repository has done both. It has a working cache, and it has shipped two
real cache defects — one where the cache never cached anything and nobody
noticed, and one where deleting a document did not remove it from the cache. We
will study both in full.

---

# Part A — The Problem

## A.1 The same expensive work, again and again

Anchor first: this system answers questions about a user's uploaded documents.
Answering one question means turning the question into a list of numbers,
searching the database twice, re-scoring the results with a second model, then
asking Google's Gemini to write the answer.

Here is what one question costs, stage by stage:

| Stage | Time | Kind of cost |
|---|---|---|
| Turn the question into numbers (embedding) | ~50 ms | processor |
| Search the database by meaning | ~30 ms | database |
| Search the database by keyword | ~20 ms | database |
| Re-score 30 candidates (reranking) | ~300 ms | processor |
| Generate the answer | ~2,000 ms | external API, and money |

Now suppose two people in the same class ask *"what is the notice period?"*
about the same contract, ten seconds apart. Or one person asks, does not like
the phrasing, and asks again. Or a browser retries a request that appeared to
fail.

**The system does all of that work a second time**, at the same cost in
milliseconds, database load, processor time and API quota — to produce the same
answer.

## A.2 Why the obvious alternatives are not enough

**"Make it faster."** Optimising the reranker from 300 ms to 200 ms is real
work for a third of one stage. Not doing the stage at all saves 100% of it.

**"Buy a bigger machine."** The 2,000 ms is Google's server, not yours. No
hardware you own affects it.

**"Store the answer in the database."** Better — but the database is on another
machine across a network, has a small connection budget (this deployment has
about fifteen connections in total), and is the thing you were trying to
protect.

**What is actually needed is a small, very fast place to keep recent results,
close to the application, that forgets things on purpose.**

That is a cache.

---

# Part B — What a Cache Is

## B.1 The definition

**A cache is a store of results you have already computed, kept so that you can
answer the same request again without doing the work.**

Two words describe every access:

- **Cache hit** — the answer was there. Cost: microseconds.
- **Cache miss** — it was not. Do the work, and usually store the result for
  next time.

The fraction of requests that hit is the **hit rate**, and it is the number
that decides whether a cache is worth having at all. A cache with a 5% hit rate
is a cost with a rounding error attached.

## B.2 Why caching works at all

Caching is not a free lunch; it exploits a specific property of real workloads
called **locality**.

- **Temporal locality** — something requested once is likely to be requested
  again soon. A popular document. A question everyone in a class asks the same
  week.
- **Spatial locality** — things near a requested item are likely to be
  requested too.

**If your workload has no locality, a cache does nothing.** If every user asks
a unique question about a unique document once and never returns, every access
is a miss, and you have added machinery, memory, and a new way to be wrong.
Knowing this is what stops you caching things that should not be cached
(Part J).

## B.3 The three questions

Every cache decision is these three, in order:

1. **What do we store?** The final answer? The retrieved evidence? The
   embedding of the question?
2. **How do we name it?** The name — the **key** — decides who gets which
   cached value. This is where the real bugs live (Part E).
3. **When do we throw it away?** After a fixed time? When the underlying data
   changes? Both?

Question 3 has a famous quotation attached, from Phil Karlton at Netscape:

> *"There are only two hard things in computer science: cache invalidation and
> naming things."*

It is a joke that turned out to be a road map. This chapter is mostly questions
2 and 3, because question 1 is usually easy.

---

# Part C — Where Caches Live

You are already surrounded by caches, and seeing the ladder helps you place the
one you are building.

| Layer | Example | Typical lifetime |
|---|---|---|
| Processor cache | the CPU's own memory | nanoseconds |
| Operating system page cache | recently read file blocks | until memory is needed |
| Application memory | a Python dictionary in the process | until restart |
| **Shared cache server** | **Redis** | **seconds to hours** |
| Database buffer pool | recently read table pages | managed by the database |
| Content delivery network | images and scripts near the user | hours to days |
| Browser cache | files this user already downloaded | hours to days |

**Why this project needs the shared kind.** A dictionary inside the Python
process would be the simplest cache in the world — and it breaks the moment you
run two copies of the application, because each copy has its own memory. User A
warms the cache on server 1; user B's identical question lands on server 2 and
misses. Worse, deleting a document would clear one server's cache and not the
other's.

**A shared cache is one place all your servers agree on.** That is the whole
justification for running a separate cache server, and it is the answer to the
interview question "why not just use a dictionary?"

---

# Part D — Redis

## D.1 What it is and why it was created

**Redis is a database that keeps all its data in memory.**

It was written in 2009 by Salvatore Sanfilippo, who needed to record real-time
page-view statistics for a web analytics product. A traditional database was
too slow for the write volume, because a traditional database writes to disk —
and Chapter 05's memory hierarchy explains why that matters: reading from
memory takes about 100 nanoseconds, reading from a solid-state disk takes about
100 microseconds. **A thousand times slower.**

His decision was to give up the thing that makes disk necessary — the
guarantee that data survives a power cut — in exchange for that thousandfold
speed. **That trade is the entire identity of Redis**, and every property below
follows from it.

## D.2 How it works internally

**It keeps everything in RAM.** No disk seek on the read path.

**It is single-threaded for command execution.** One command runs at a time, to
completion. That sounds like a limitation and is mostly a gift:

- **No locks are needed.** Two clients cannot interleave inside one command.
- **Every operation is atomic by construction** — `INCR` cannot lose an
  increment, because nothing can run between reading and writing.
- **No lock bugs**, which are the hardest bugs in concurrent systems.

The cost is that one very slow command blocks everyone. This is exactly the
cooperative-scheduling problem from Chapter 07, in a different program: `KEYS *`
on a large database scans everything while every other client waits. Part L
returns to this, because it appears in this repository.

**Persistence is optional and imperfect.** Redis can write to disk in two ways
— periodic snapshots, or an append-only log of commands. Neither gives the
guarantee a real database gives, and *that is deliberate*. **If you need a
promise that committed data survives, you need PostgreSQL. Redis's promise is
speed.**

## D.3 What it can store

Not just text. Redis has data structures, and knowing them is what separates
someone who has used Redis from someone who has read about it:

| Type | Use |
|---|---|
| String | a cached value, a counter, a flag |
| List | a simple queue — push one end, pop the other |
| Set | membership, uniqueness |
| Sorted set | leaderboards, rate limiting by time window |
| Hash | an object with fields |
| Stream | an append-only log with consumer groups |

**This project uses two of them**: plain strings for cached retrieval results,
and — through Celery — lists as the job queue that Chapter 12 covers.

## D.4 The commands you actually need

```
SET  key value              store
GET  key                    read
SETEX key 300 value         store, and delete automatically after 300 seconds
DEL  key                    delete
EXISTS key                  is it there?
TTL  key                    how long until it expires?
INCR key                    add one, atomically
KEYS pattern                every key matching a pattern  ← dangerous, see Part L
SCAN cursor MATCH pattern   the same, in safe small batches
FLUSHDB                     delete everything ← never in production
```

**`SETEX` is the one that matters most for caching**, because it does two
things in one step: store the value, and set its **TTL** — its "time to live",
after which Redis deletes it automatically without anybody asking. That
automatic expiry is the cheapest form of cache invalidation there is.

## D.5 Why this project uses Redis for two different jobs

Redis is both the cache **and** the job queue here. Chapter 02 recorded that as
decision D-017, and the reasoning is worth restating: at this scale a separate
message broker is extra machinery with no benefit.

**And the tradeoff, which you should be able to say out loud in an interview:**
Redis is not durable by default. If it dies with jobs in it, those jobs are
gone. That is survivable for document processing — the document row still says
`PROCESSING` and can be requeued — and would *not* be acceptable for payments.
**Choosing a broker is really choosing what you can afford to lose.**

---

# Part E — Cache Keys

This is the most important practical section in the chapter, because the key is
where cache bugs are born.

## E.1 What a key must contain

**A cache key must contain every input that changes the answer.**

That sentence is the whole rule, and it fails in two directions:

- **Too little in the key** → different questions collide on one entry, and one
  user gets another user's answer. This is a security incident, not a bug.
- **Too much in the key** → nothing ever matches, the hit rate is zero, and you
  have a cache that costs and never pays.

For a retrieval result in this system, what changes the answer?

- **Which user is asking** — different users own different documents.
- **Which workspace** — retrieval settings and filters differ.
- **The question text** — obviously.
- **Which documents are attached to this chat** — the same question against a
  different document set is a different question.

Miss any of those four and the cache returns something that does not belong to
this request.

## E.2 The real key in this repository

From [`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py):

```python
def _retrieval_cache_key(user_id: str, workspace_type: str, query: str, attached_doc_ids) -> str:
    """M-2: single source of truth for the retrieval cache key.

    The key MUST start with `retrieval:uid_{user_id}:` — that is the pattern
    `delete_document` purges (documents.py). The old write key
    (`retrieval:{workspace}:{hash}`) never matched the purge pattern, so
    deleted-document content could be served from cache for up to the TTL.
    """
    attached_ids_key = ",".join(sorted(str(d) for d in attached_doc_ids or []))
    digest = hashlib.sha256(
        f"{workspace_type}:{query}:{attached_ids_key}".encode()
    ).hexdigest()[:16]
    return f"retrieval:uid_{user_id}:{workspace_type}:{digest}"
```

Every line is a decision:

- **`sorted(...)`** on the document ids. Two requests with the same documents in
  a different order must produce the *same* key, or the cache misses for no
  reason. Sorting makes the key independent of order.
- **`",".join(...)`** turns the list into one piece of text so it can be hashed.
- **`hashlib.sha256(...)`** — a **hash function** turns any amount of text into a
  short fixed-length fingerprint. Two identical inputs always give the same
  fingerprint; different inputs almost never collide.
- **Why hash at all?** Because a question can be two thousand characters long
  and contain colons, spaces and newlines. Keys should be short and
  predictable.
- **`[:16]`** keeps sixteen hexadecimal characters — 64 bits. That is
  vanishingly unlikely to collide across the number of cache entries this system
  will ever hold, and it keeps keys readable.
- **The prefix `retrieval:uid_{user_id}:`** is the important part, and E.3
  explains why.

**Note the docstring's first line: "single source of truth for the retrieval
cache key."** One function builds it; readers and writers both call it. The
alternative — building the string in two places — is how the two ends drift
apart, which is exactly what happened.

## E.3 Key namespacing, and why the prefix is not decoration

Redis is one flat space of keys. Every cached value, every queue, every counter
lives in it together. So keys are conventionally namespaced with colons:

```
retrieval:uid_8f3a...:legal:9c21ab34de567f01
^^^^^^^^^ ^^^^^^^^^^^ ^^^^^ ^^^^^^^^^^^^^^^^
what      whose        where  which question
```

**The namespace is not for tidiness. It is what makes bulk deletion possible.**
Redis can delete by pattern — "every key starting with `retrieval:uid_8f3a…`" —
and that is the only practical way to say *"forget everything cached for this
user"*.

Which brings us to the first real incident.

---

# Part F — Invalidation

## F.1 The problem, stated precisely

A cached value is a copy. The moment the original changes, the copy is a lie.

**Invalidation is the act of removing or replacing a copy that has stopped
being true.** It is hard for a reason that sounds obvious and is not: *the code
that changes the data is usually nowhere near the code that cached it.* The
document deletion endpoint has no idea what the query endpoint stored.

## F.2 The five strategies

**1. Time to live (TTL).** Every entry expires after a fixed period.

- *Advantage:* requires no coordination at all. The writer of the data does not
  need to know a cache exists.
- *Disadvantage:* between the change and the expiry, you serve stale data. You
  are choosing a window of wrongness.
- *Use it when* being slightly out of date is acceptable.

**2. Explicit purge on write.** When data changes, delete the affected keys.

- *Advantage:* correct almost immediately.
- *Disadvantage:* the writing code must know which keys exist — which requires
  a key convention both sides agree on, and which is exactly what failed here.

**3. Write-through.** Update the cache at the same moment as the database.

- *Advantage:* the cache is never stale.
- *Disadvantage:* writes get slower, and now you have two systems to keep in
  step in one operation.

**4. Versioned keys.** Include a version number in the key; changing the data
increments the version, so old keys become unreachable and expire on their own.

- *Advantage:* no deletion needed; invalidation is instant and atomic.
- *Disadvantage:* old entries linger in memory until they expire.

**5. Never invalidate — cache only immutable things.** If a value can never
change, it can never be stale.

- *The strongest strategy where it applies.* An embedding of a fixed piece of
  text never changes. Neither does a processed page of a document.

## F.3 What this project uses

**TTL plus explicit purge**, which is the common production combination:

```python
async def _set_cached_retrieval(cache_key: str, payload: Any, ttl: int = 300) -> None:
```

Five minutes of TTL as the safety net, and an explicit purge when a document is
deleted so the window is not actually five minutes.

**Why five minutes?** It is a judgement, and you should be able to argue it:
long enough that a user re-asking or retrying gets a hit; short enough that any
staleness the purge misses cannot last. Longer would raise the hit rate and the
worst-case staleness together.

---

# Part G — Incident One: The Purge That Purged Nothing

## G.1 The setup

Two pieces of code, written at different times, both dealing with the same
cached values.

**The writer**, in `query.py`, stored results under a key built like this:

```
retrieval:{workspace}:{hash}
```

**The deleter**, in `documents.py`, purged like this:

```python
            uid = current_user["id"]
            keys = await redis.keys(f"retrieval:uid_{uid}:*")
            if keys:
                await redis.delete(*keys)
```

Read the two patterns next to each other:

```
written:  retrieval:legal:9c21ab34de567f01
purged:   retrieval:uid_8f3a7d...:*
```

**They do not match.** The purge asks for keys beginning with
`retrieval:uid_`; the writer never produced one. So the purge ran, found
nothing, deleted nothing, and reported success.

## G.2 What the user experienced

A user deletes a document — perhaps because it contained something private, or
because they uploaded it to the wrong workspace. The interface confirms the
deletion. The document row is gone, its pages and chunks are gone.

Then they ask the same question again, and **the answer is still built from the
deleted document's text, quoting its pages.**

For up to five minutes, and with no error anywhere.

## G.3 Why it escaped

Three reasons, each of which is a general lesson:

**1. The key was built in two places.** One in the writer, one — implicitly, as
a pattern — in the deleter. Two independent statements of one convention will
eventually disagree, and nothing in the language or the tests connects them.

**2. Both halves worked in isolation.** The cache stored and retrieved
correctly. The purge command executed without error. **Deleting zero keys is
indistinguishable from deleting the right zero keys** — there was nothing to
observe.

**3. Testing with one document and no deletion never exercises it.** This is
Chapter 03's *observability of a defect*: under the conditions the tests
created, the correct and incorrect versions behave identically.

## G.4 The fix, and why it is at the right layer

The repair was not "change the purge pattern to match the writer". It was to
create **one function that builds the key**, document the constraint the key
must satisfy, and make both sides depend on it:

```python
def _retrieval_cache_key(user_id, workspace_type, query, attached_doc_ids) -> str:
    """M-2: single source of truth for the retrieval cache key.

    The key MUST start with `retrieval:uid_{user_id}:` — that is the pattern
    `delete_document` purges (documents.py).
    """
```

**The comment is doing real work.** It states the *invariant* — the key must
begin with that prefix — so that the next person who changes the format knows
there is a second reader, and where it is.

**The general rule, and it appears in every chapter of this course in a
different costume:** when two pieces of code must agree on a format, put the
format in one place and make both call it. A convention held in two heads, or
two files, is a convention that will drift.

**And a stronger version, worth thinking about:** an even better fix would make
the purge pattern *derived* from the same function, so that changing the key
shape could not leave the purge behind at all. That is a real improvement and it
appears in the critique.

---

# Part H — Incident Two: The Cache That Never Cached

The second incident is worse, because it disabled several features at once and
produced no evidence whatsoever.

## H.1 The code

Six places in the codebase needed a Redis connection. Each did this:

```python
try:
    import aioredis
    return await aioredis.from_url(settings.REDIS_URL, ...)
except Exception:
    return None
```

Callers treated `None` as "Redis is unavailable, carry on without it".

## H.2 The problem

From the module that replaced it,
[`backend/app/core/redis_client.py`](../backend/app/core/redis_client.py):

> *"`aioredis` is **not installed** in this environment, and `aioredis` 2.0.1 is
> known-broken on Python 3.11 (this stack's pinned version) with
> `TypeError: duplicate base class TimeoutError`. The package has been
> deprecated in favour of `redis.asyncio` since 2022. So every one of those
> calls raised `ModuleNotFoundError`, was swallowed by the bare `except`, and
> returned `None` — with **no log line anywhere**."*

The import failed every single time. Not sometimes — always.

## H.3 What that silently disabled

Quoting the same file, because the list is the lesson:

> *"• `DeviceFingerprintMiddleware` — an advertised abuse control that stops
> repeat trial registrations. Inert, with zero evidence in the logs.
> • the retrieval cache — every query paid full retrieval cost while the code
> presented a working cache path
> • registration and feedback IP rate limits — fail-open"*

Three features, all reporting success:

- **The cache** was a pure cost: every request tried Redis, failed, and did the
  full work. The code *looked* like it had a cache. Every performance
  discussion would have assumed one existed.
- **The abuse control** was advertised and inert. Anyone could register
  repeatedly for new trials.
- **Two rate limits** failed open, meaning "when in doubt, allow" — the wrong
  direction for a control whose purpose is to refuse.

## H.4 The mechanism, which is the part to remember

> *"`except Exception: return None` makes a MISSING DEPENDENCY
> indistinguishable from a cache miss. Both look like 'no Redis today'."*

**Two entirely different states — "this library does not exist" and "this key
was not cached" — collapsed into one value.** Nobody could tell them apart, so
nobody looked.

You have now met this exact shape four times in this course, in four different
subsystems: an empty list meaning both "no documents" and "we failed to look";
`0 || 10` meaning both "zero remaining" and "not set"; a status field meaning
both "nothing there" and "could not check"; and now `None` meaning both "no
cache entry" and "no cache".

**It is the single most common shape of a silent failure. Learn to recognise
it:** *does this value already mean something else?*

## H.5 The repair

Three changes, and each maps to a rule:

```python
async def get_redis() -> Optional[Any]:
    global _unavailable_logged
    try:
        import redis.asyncio as redis_asyncio

        return redis_asyncio.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    except Exception as exc:  # noqa: BLE001 - must never break a request path
        if not _unavailable_logged:
            _unavailable_logged = True
            logger.error(
                "[redis] client could not be constructed (%s: %s). Trial abuse "
                "prevention, the retrieval cache and IP rate limits are all "
                "DEGRADED until this is fixed. Logged once per process.",
                type(exc).__name__,
                exc,
            )
        return None
```

1. **Use the library that is actually installed.** `redis.asyncio` replaced the
   deprecated `aioredis`.
2. **Fail loudly.** `logger.error` with `type(exc).__name__`, so
   `ModuleNotFoundError` and `ConnectionRefusedError` — which need completely
   different responses — are distinguishable.
3. **Log once per process**, not once per request, so a genuine Redis outage
   does not produce a flood that hides everything else.

And the docstring states the boundary honestly:

> *"Callers keep treating `None` as 'Redis unavailable, degrade gracefully' —
> that behaviour is deliberate for a cache and for best-effort rate limits.
> What changes is that the reason is now visible instead of being erased."*

**Degrading is fine. Degrading silently is not.** That distinction is this
project's central rule and this is its clearest illustration.

---

# Part I — Reading the Real Cache Code

The full read and write path, from `query.py`. You now have everything needed
to read every line.

```python
async def _get_cached_retrieval(cache_key: str) -> Any:
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return None
        try:
            cached = await redis.get(cache_key)
        finally:
            await redis.close()
        if cached:
            return json_module.loads(cached)
    except Exception:
        pass
    return None


async def _set_cached_retrieval(cache_key: str, payload: Any, ttl: int = 300) -> None:
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis is None:
            return
        try:
            await redis.setex(cache_key, ttl, json_module.dumps(payload, default=str))
        finally:
            await redis.close()
    except Exception:
        pass
```

Line by line:

- **`async def` / `await`** — these are network calls to another program, so
  they wait. `await` means "pause here and let the server handle other users
  meanwhile" (Chapter 07).
- **The import inside the function** rather than at the top. This keeps the
  query module from depending on the Redis module at import time — a deliberate
  choice about dependency direction.
- **`if redis is None: return None`** — the honest degrade. No cache today;
  carry on and do the work.
- **`try: ... finally: await redis.close()`** — and this is the line with a
  story. The comment in the real file explains it:

  > *"close() must be in a finally: when redis.get() raises (dropped
  > connection, timeout), the outer `except Exception: pass` swallows it and
  > the connection is leaked. This runs on every query, so a Redis blip used to
  > exhaust the pool."*

  A connection opened and never closed is a resource held forever. On a path
  that runs on **every single query**, one bad afternoon on the network
  exhausts the pool and the whole feature stops. `finally` guarantees the close
  regardless of what happened.

- **`json_module.loads` / `dumps`** — Redis stores text, and the payload is a
  structure, so it is converted to text on the way in and back on the way out
  (Chapter 05's serialisation).
- **`default=str`** in `dumps` — a safety net for values JSON does not natively
  understand, such as dates and UUIDs. Without it, storing a payload containing
  a UUID would raise.
- **`setex(key, ttl, value)`** — store and expire in one command. Storing and
  then setting an expiry separately would leave a window where a crash between
  the two produces a key that never expires.
- **`except Exception: pass`** — the broad catch this course has criticised
  repeatedly. **Here it is defensible, and it is worth being precise about
  why:** the loud reporting already happened inside `get_redis`, which logs at
  ERROR with the exception type. This outer catch only ensures that a cache
  problem cannot break a user's answer. **The failure is visible one layer
  down; this layer is deciding not to let it be fatal.**

  That is a different thing from erasing it — and if `get_redis` did not log,
  this would be the anti-pattern again.

---

# Part J — When Not to Cache

The instinct after learning about caches is to add them everywhere. Resist it.
**A cache is a copy of the truth, and every copy is a chance to be wrong.**

Do not cache when:

1. **The data changes constantly.** A live counter cached for five minutes is a
   wrong counter for five minutes.
2. **Correctness must be immediate.** Account balances, stock levels, permission
   checks. Whether the current user may read this document must never come from
   a cache — Chapter 03's exercise on team accounts identified exactly this as a
   new failure mode.
3. **The work is already cheap.** Caching a lookup that takes 2 ms and adding a
   network round trip of 1 ms to reach the cache is barely a saving, and it is
   pure cost when it misses.
4. **The hit rate would be low.** If every request is unique, every access is a
   miss, and you have added latency, memory, code and a failure mode for
   nothing.
5. **You cannot answer "when does this become wrong?"** If you cannot state the
   invalidation strategy, you are not ready to add the cache.

**A worked example from this system.** Should the *final generated answer* be
cached, rather than just the retrieved evidence?

Arguments for: it would save the 2,000 ms model call, which is by far the
biggest cost.

Arguments against: the model is deliberately not fully deterministic, so users
asking the same thing may reasonably expect a fresh answer; conversation
history is part of the input, so two identical questions in different chats are
different requests; and a wrong cached answer is far more visible to a user
than wrong cached evidence.

**A defensible position either way** — which is why it is a good interview
question, and why the honest answer is "here is the tradeoff", not "yes" or
"no".

---

# Part K — Production Concerns

## K.1 Memory is finite, so something must be evicted

Redis holds everything in RAM. When it fills, it must either refuse writes or
throw something away. That behaviour is configured with an **eviction policy**:

| Policy | Behaviour |
|---|---|
| `noeviction` | refuse new writes when full (the default) |
| `allkeys-lru` | evict the least recently used key |
| `allkeys-lfu` | evict the least frequently used key |
| `volatile-lru` | evict least recently used, but only among keys that have a TTL |

**For a pure cache, `allkeys-lru` is usually right** — everything is
disposable, and the least recently used thing is the best guess at what will be
missed least.

**For a Redis that is also a job queue — which is this project's situation —
`allkeys-lru` is dangerous**, because it can evict queued jobs. That is a real
argument for separating the cache and the broker onto different Redis
databases or instances, and it appears in the critique.

## K.2 Measure the hit rate or you are guessing

```
redis-cli INFO stats
```

gives `keyspace_hits` and `keyspace_misses`. The hit rate is

```
hits / (hits + misses)
```

**If you have never measured it, you do not know whether your cache is
working.** Incident Two is the extreme version of this: the hit rate was zero
for months and nobody knew, because nobody was looking.

## K.3 The command budget

The intended deployment uses Upstash, a hosted Redis whose free tier bills by
**number of commands**, not by memory. That changes the calculus: a cache that
checks Redis on every request and always misses is not free — it is spending
budget to learn nothing.

**Cost models change design.** With a per-command budget, batching and higher
TTLs become more attractive than they would be on a machine you own.

## K.4 The stampede

**The problem.** A popular cached entry expires. Fifty requests arrive in the
same second, all miss, and all start the same expensive work simultaneously.
The cache's purpose was to protect the database and the model API; at the
moment of expiry it does the opposite.

This is called a **cache stampede** or **thundering herd**.

**Three standard defences:**

1. **A lock.** The first miss takes a lock and does the work; the others wait
   briefly and read the result.
2. **Early recomputation.** Refresh an entry slightly *before* it expires, in
   the background, so it never actually disappears.
3. **Jittered TTLs.** Add a small random amount to each TTL so entries created
   together do not expire together.

**Does this project need one?** At tens of concurrent users, no. **Would an
interviewer ask?** Frequently — and the strong answer is the one that ends with
"we do not have it, and here is the load at which we would need it."

## K.5 Two more failure modes worth naming

**Cache penetration.** Requests for things that do not exist miss every time and
hit the database every time, because there is nothing to cache. The fix is to
cache the *absence* — store a small marker meaning "no result" with a short
TTL.

**Hot key.** One key is requested far more than the rest. Redis is
single-threaded, so a genuinely hot key can become a bottleneck in itself. The
fix is to replicate that value across several keys, or cache it in application
memory as well.

---

# Part L — Mistakes and Debugging

## L.1 Beginner mistakes

1. **Leaving something out of the key.** The user id, especially. In a
   multi-user system this is not a bug, it is a data leak.
2. **Caching without a TTL.** Entries live until the memory fills, then get
   evicted unpredictably.
3. **Building the key in two places.** Incident One.
4. **Treating the cache as storage.** Redis is allowed to lose your data. If
   losing it matters, it belongs in PostgreSQL.
5. **Caching authorisation decisions.** Permissions change; a cached "yes" is a
   security hole with a timer on it.
6. **Storing enormous values.** A multi-megabyte entry makes every read slow and
   fills memory quickly.

## L.2 Production mistakes

1. **`KEYS *` on a large database.** Redis is single-threaded, so this scans
   everything while every other client waits — a self-inflicted outage. `SCAN`
   does the same job in small batches.

   **This repository uses `KEYS`**, in the delete path:
   ```python
   keys = await redis.keys(f"retrieval:uid_{uid}:*")
   ```
   It is scoped by a prefix and runs only on document deletion, so at this scale
   it is fine. **At a million keys it would not be**, and `SCAN` with the same
   pattern is a drop-in improvement. That is the kind of "correct now, would not
   scale" observation interviewers like to hear volunteered.

2. **No eviction policy set**, so Redis starts refusing writes when full and the
   application sees write errors it does not expect.

3. **Sharing one Redis between cache and queue without thinking about
   eviction** (K.1).

4. **Leaking connections**, which this project fixed with `finally`.

5. **Assuming the cache is warm after a deploy.** Restarting Redis empties it,
   so the first minutes after a deploy carry full load. If your system can only
   survive with a warm cache, it cannot survive a restart.

## L.3 Debugging techniques

**Is the value actually there?**
```
redis-cli --scan --pattern 'retrieval:uid_8f3a*'
redis-cli TTL retrieval:uid_8f3a...:legal:9c21ab34
redis-cli GET retrieval:uid_8f3a...:legal:9c21ab34
```

**Is anything being stored at all?**
```
redis-cli INFO keyspace          # how many keys exist
redis-cli INFO stats             # hits and misses
```
Zero keys after a burst of traffic means writes are not happening — which is
Incident Two's signature.

**Watch commands live** (development only):
```
redis-cli MONITOR
```
This prints every command as it arrives. It is the fastest way to answer "is
the application even talking to Redis?" and it is expensive, so never leave it
running against production.

**The procedure for "why did I get stale data?"** — in order, cheapest first:

1. Is the value in the cache? (`GET`)
2. What is its TTL? (`TTL`)
3. **Does the key that was written match the pattern that purges?** Print both
   and compare them character by character. This is Incident One, and comparing
   the two strings side by side is the only reliable way to see it.
4. Did the purge actually run, and did it delete anything? A purge that deletes
   zero keys should log that fact.
5. Is there a second cache layer you forgot — the browser, or a CDN?

---

# Part M — How Companies Use This

- **Redis is close to universal** for caching, sessions, rate limiting and
  simple queues. Memcached is the older, simpler alternative — a pure cache with
  no data structures and no persistence.
- **Cache invalidation is genuinely one of the top sources of production
  incidents** at large companies, and it is almost always the pattern in
  Incident One: two places that had to agree, and did not.
- **Large systems cache at several layers at once** — CDN, application, Redis,
  database buffer pool — and the hard part is reasoning about staleness across
  all of them.
- **Hit rate is a dashboard metric**, not an occasional curiosity. A cache
  nobody measures is a cache nobody can defend in a review.
- **In interviews**, the reliable questions are: what would you cache and why;
  how do you invalidate; what is in the key; what happens when the cache is
  down; and what is a stampede. Part P answers all five.

---

# Part N — Exercises

### Level 0 — Understanding

**N1.** In one sentence each: cache hit, cache miss, hit rate, TTL.

**N2.** Explain in two sentences why a Python dictionary inside the application
process is not sufficient as a cache for this system.

**N3.** Redis keeps everything in memory and is not durable by default. State
what it gains from that, and one thing you must therefore never store in it
alone.

### Level 1 — Keys

**N4.** A colleague caches search results under the key `search:{query}`. List
every problem, ordered by severity, and say which one is a security incident
rather than a bug.

**N5.** Rewrite that key properly for this system, and justify every component
you include.

**N6.** Explain why `_retrieval_cache_key` sorts the document ids before hashing
them. What would break without the sort, and would it be a correctness problem
or a performance problem?

### Level 2 — Invalidation

**N7.** Name the five invalidation strategies and give one situation where each
is the best choice.

**N8.** Walk through Incident One: the key that was written, the pattern that
purged, why the mismatch produced no error, and what the user experienced.

**N9.** Propose a change that would make the purge pattern *impossible* to drift
from the write key, rather than merely documented. State what it costs.

### Level 3 — Failure and design

**N10.** Explain why `except Exception: return None` around the Redis import was
worse than having no cache at all. Name the three features it silently
disabled.

**N11.** The read path uses `try: ... finally: await redis.close()`. Explain
what happens without the `finally`, and why this particular code path makes it
serious rather than untidy.

**N12.** Should the final generated answer be cached? Argue both sides and give
a recommendation with the condition that would change your mind.

### Level 4 — Production

**N13.** Describe a cache stampede, and give three defences with their costs.
Then say whether this system needs one today, with a reason.

**N14.** This project runs cache and job queue on one Redis. Explain the risk
when an eviction policy is configured, and give the fix.

**N15.** You are told "the app got slower after we deployed on Tuesday". Write
the ordered investigation using only this chapter, and say what each result
would tell you.

---

# Part O — Answer Key

**O1.** A **cache hit** is finding the value already stored, so the work is
skipped. A **cache miss** is not finding it, so the work runs. The **hit rate**
is hits divided by total accesses, and it decides whether the cache is worth
having. **TTL** is how long an entry is allowed to live before the cache deletes
it automatically.

**O2.** Each running copy of the application has its own private memory, so a
value cached by one server is invisible to another — the hit rate falls as you
add servers, which is backwards. Worse, invalidation becomes impossible to do
correctly: deleting a document would clear one server's copy and leave the
others serving deleted content.

**O3.** It gains speed — memory access is roughly a thousand times faster than
disk. You must therefore never keep anything in Redis alone that you cannot
afford to lose: the source of truth belongs in PostgreSQL, and Redis holds
copies and disposable work.

**O4.** In order of severity:

1. **No user identity in the key.** Two users searching the same words share one
   entry, so one user receives results computed from another user's documents.
   **This is a data leak — a security incident, not a bug.**
2. **No workspace or attached-document context**, so the same words in different
   contexts collide and return evidence from the wrong document set.
3. **No namespace prefix**, so bulk invalidation for one user is impossible.
4. **The raw query in the key**, which may be thousands of characters and
   contain colons and newlines, making keys unwieldy and pattern matching
   unreliable.
5. **No TTL implied by the design**, so entries live until memory pressure
   evicts them unpredictably.

**O5.**
```
retrieval:uid_{user_id}:{workspace}:{sha256(workspace:query:sorted_doc_ids)[:16]}
```
- `retrieval:` — namespace, so this cache does not collide with queues or
  counters.
- `uid_{user_id}:` — the tenant, both for correctness *and* so that
  `retrieval:uid_X:*` can purge one user's entries.
- `{workspace}` — different workspaces use different retrieval settings and
  filters.
- the hash of workspace, query and sorted document ids — everything else that
  changes the answer, compressed to a short fixed length.

**O6.** Sorting makes the key independent of the order the ids arrive in. The
same two documents in a different order would otherwise hash differently and
produce two entries for one logical request.

**It is a performance problem, not a correctness problem** — the extra entries
are each individually correct, they simply lower the hit rate and waste memory.
That distinction matters: correctness bugs must be fixed, efficiency bugs are
prioritised by measurement.

**O7.**
- **TTL** — when slight staleness is acceptable and the writer cannot be
  expected to know about the cache. *(Search results.)*
- **Explicit purge** — when a specific change makes specific entries wrong and
  you know which. *(Document deletion.)*
- **Write-through** — when staleness is unacceptable and writes are rare enough
  to afford the extra step. *(A user's plan or permissions.)*
- **Versioned keys** — when invalidation must be instant and atomic without
  scanning for keys. *(A whole catalogue that regenerates at once.)*
- **Never invalidate** — when the value cannot change. *(The embedding of a
  fixed piece of text.)*

**O8.** The writer stored under `retrieval:{workspace}:{hash}`. The deleter
purged `retrieval:uid_{user_id}:*`. No key ever produced by the writer began
with `retrieval:uid_`, so the purge matched nothing.

No error appeared because **deleting zero keys is a successful operation**.
Redis was asked for keys matching a pattern, found none, and the code deleted
none — exactly as it would if the cache were legitimately empty. The two
outcomes are indistinguishable from outside.

The user deleted a document, saw it disappear, asked the same question again,
and received an answer built from the deleted document's text with page
citations — for up to five minutes, with the interface insisting the document
was gone.

**O9.** Derive the purge pattern from the same function that builds the key —
for example, a `_retrieval_cache_prefix(user_id)` that both the key builder and
the deleter call, so the key is literally `prefix + digest` and the purge is
`prefix + "*"`.

*Cost:* one more small function and a slightly less readable key builder. In
exchange, changing the key format cannot leave the purge behind, because there
is only one definition of the prefix. **This converts a documented constraint
into a structural one** — the same move as making a parameter required rather
than warning about it in a comment.

**O10.** Because the code *presented* a working cache. Without a cache, everyone
knows there is no cache, and performance discussions start from the truth. With
a fake one, every measurement, every capacity plan and every review proceeded on
a false assumption — and no log line contradicted it.

The three disabled features: the retrieval cache (every query paid full cost),
the device-fingerprint abuse control that prevents repeat trial registrations
(inert, so trials could be farmed), and the registration and feedback IP rate
limits (failed open, so they allowed everything).

The mechanism is the lesson: `except Exception: return None` made a **missing
dependency** indistinguishable from a **cache miss**, so nobody could tell them
apart and nobody looked.

**O11.** Without `finally`, an exception raised by `redis.get()` — a dropped
connection, a timeout — skips the close and is swallowed by the outer
`except Exception: pass`. The connection is never returned and never closed.

It is serious rather than untidy because **this path runs on every single
query**. A brief network problem produces a leaked connection per request, and
within minutes the connection pool is exhausted — at which point the failure
stops being about the cache and starts being about everything.

**O12.** **For caching the answer:** it would eliminate the 2,000 ms model call,
which is the single largest cost in the request and the one that also costs
money and consumes a rate-limited quota. For repeated identical questions the
saving is total, not partial.

**Against:** the model is not fully deterministic and users re-asking may
reasonably expect a fresh attempt; the conversation history is part of the
input, so two identical questions in different chats are genuinely different
requests and the key must include the history — which sharply reduces the hit
rate; and a stale *answer* is far more visible and damaging than stale
*evidence*, because the user reads it directly.

**Recommendation:** do not cache the final answer yet, because the key would
have to include conversation history and the hit rate would be low. **What would
change my mind:** a measurement showing a meaningful share of requests are
repeats with identical history — or a cost problem with the model API that made
even a 10% hit rate worth the staleness.

**O13.** A **stampede** happens when a popular entry expires and many
simultaneous requests all miss at once, all starting the same expensive work —
so the cache does the most damage at the exact moment it stops helping.

Defences: a **lock**, so only the first miss does the work (cost: the others
wait, and a lock is a new failure mode if its holder dies); **early
recomputation** in the background before expiry (cost: complexity, and work
done for entries nobody would have asked for); and **jittered TTLs** so entries
created together do not expire together (cost: almost none, which is why it is
the usual first move).

**This system does not need one today** — with tens of concurrent users, the
number of simultaneous misses on one key is small, and the TTL is short enough
that entries are cheap to rebuild. It would become necessary at the point where
a single popular question is asked by dozens of users within the same second.

**O14.** An eviction policy such as `allkeys-lru` throws away the least recently
used key when memory fills — **and it does not know which keys are cache
entries and which are queued jobs.** A memory spike could therefore delete
pending document-processing jobs, which vanish with no error: the document row
stays `PROCESSING` forever and nobody is told.

The fix is to separate them: different Redis databases at minimum, different
instances ideally, so the cache can be configured `allkeys-lru` while the broker
is configured `noeviction`. The separation also means a cache flush cannot touch
queued work.

**O15.** Ordered, cheapest first:

1. **Compare the deploy to the symptom.** Did the change touch Redis
   configuration, the key format, or the purge path? Incident One arrived
   exactly this way.
2. **Check the hit rate** — `INFO stats`. A rate that fell to near zero after
   the deploy means keys are being written under one name and read under
   another, which is a key-format change.
3. **Check the key count** — `INFO keyspace`. Zero keys means writes are failing
   entirely; that is Incident Two's signature and the logs should now say why.
4. **Check the logs for the Redis error line**, which is logged once per
   process, so look at the start of each container's log rather than the end.
5. **Check whether Redis was restarted.** An empty cache after a restart is not
   a bug; it is a cold cache, and the slowness should fade as it warms.
6. **Only then** look at query-level timings, because if the cache is healthy
   the cause is elsewhere entirely.

---

# Part P — Senior Critique

### Strengths

1. **One function builds the cache key**, with a docstring stating the
   invariant that the prefix must match the purge pattern — written after the
   defect that came from having two definitions.
2. **The key contains all four inputs that change the answer**, and the document
   ids are sorted so ordering cannot fragment the cache.
3. **TTL and explicit purge together** — the standard production combination,
   with the TTL acting as a bound on anything the purge misses.
4. **`setex` rather than set-then-expire**, so a key without an expiry cannot be
   created by a crash between two commands.
5. **The connection close is in a `finally`**, with a comment recording the pool
   exhaustion that motivated it.
6. **Redis unavailability is logged loudly, once per process**, with the
   exception type included — the repair for Incident Two, and the correct
   design.

### Weaknesses

1. **The purge pattern is still written by hand** in `documents.py` rather than
   derived from the key builder. The constraint is documented but not
   structural; a future key change can still leave the purge behind.
2. **`KEYS` rather than `SCAN`.** Correct at this scale, and a
   single-threaded-server stall waiting to happen at a larger one. `SCAN` with
   the same pattern is a drop-in replacement.
3. **A purge that deletes zero keys is not logged.** Given that this is exactly
   what Incident One looked like, "purged 0 entries for user X" would have made
   the defect visible from the logs alone.
4. **No hit-rate measurement anywhere.** Nothing in the application records
   whether the cache is working. Incident Two lasted as long as it did partly
   because there was no number to look at.
5. **Cache and job broker share one Redis** with no documented eviction policy,
   which is the risk in O14.
6. **A new Redis client is constructed on every call.** `from_url` per request
   rather than a shared client is wasteful, and it is why every call must also
   remember to close. A module-level client created once would remove both
   problems.

### The one improvement I would make first

**Log the purge result, including zero.** It is one line, it turns the exact
failure this system already suffered into something visible in the logs, and it
costs nothing. Second would be a shared Redis client created once per process,
which removes the whole class of connection-leak bugs rather than guarding
against it.

---

# Part Q — Interview Questions With Model Answers

**Q1. "What would you cache in a system like this, and why?"**

> I would cache the *retrieved evidence* rather than the final answer. Retrieval
> is deterministic for a given question and document set, costs an embedding, two
> database queries and a cross-encoder rerank — around 400 milliseconds and real
> database load — and is safe to reuse.
>
> I would be more careful about the generated answer. It is the biggest single
> cost at about two seconds, but the conversation history is part of the input,
> so the key would need to include it and the hit rate would fall sharply. And a
> stale answer is much more visible to a user than stale evidence.
>
> I would not cache authorisation decisions at all. Whether this user may read
> this document must be current, always.

**Q2. "What goes in a cache key?"**

> Every input that changes the answer, and nothing else. Too little and
> different requests collide — in a multi-user system that means one user
> receiving another user's data, which is a security incident rather than a
> bug. Too much and nothing ever matches, so you have paid for a cache that
> never hits.
>
> Ours contains the user id, the workspace, the question and the attached
> document ids, with the ids sorted so that ordering cannot fragment the cache,
> and the whole thing hashed to keep the key short.
>
> The user id is also a prefix rather than part of the hash, deliberately, so we
> can delete every entry for one user with a pattern when they delete a
> document.

**Q3. "Tell me about a caching bug you have seen."**

> Our write path stored keys as `retrieval:{workspace}:{hash}` and our delete
> path purged `retrieval:uid_{user_id}:*`. The two patterns never matched, so
> deleting a document purged nothing.
>
> The user deleted a document, the interface confirmed it, and the next
> identical question still produced an answer built from that document's text
> with page citations — for up to the five-minute TTL.
>
> Nothing errored, because deleting zero keys is a successful operation and is
> indistinguishable from a legitimately empty cache. The fix was one function
> that builds the key, with the prefix constraint written in its docstring, so
> both sides depend on one definition. The stronger version, which I would still
> do, is to derive the purge pattern from that same function so drift becomes
> impossible rather than merely documented.

**Q4. "What happens when your cache is down?"**

> The system should get slower and stay correct. Ours does: if the client cannot
> be constructed we return `None` and do the full work.
>
> The important part is that the reason is logged. We had a period where a
> missing library was swallowed by a broad `except` that returned `None`, and
> because callers treat `None` as "no cache entry", a missing dependency looked
> exactly like a cache miss. The cache never cached anything, an abuse control
> was inert and two rate limits failed open — all reporting success, with no log
> line anywhere.
>
> So the rule I apply is that degrading is fine and degrading silently is not.
> We now log at ERROR with the exception type, once per process so an outage
> does not flood the logs.

**Q5. "What is a cache stampede and how do you prevent it?"**

> When a popular entry expires, every request that arrives in the next moment
> misses and starts the same expensive work at once — so the cache does its most
> damage at the moment it stops helping.
>
> Three defences: a lock so only the first miss does the work; refreshing
> entries in the background slightly before they expire; and jittering the TTLs
> so entries created together do not expire together. Jitter is nearly free, so
> it is the usual first move.
>
> We do not have one today, and I would not add it yet — at our concurrency the
> number of simultaneous misses on one key is small. The trigger would be a
> single popular question being asked by dozens of users within the same second.

---

# Part R — Validation Checklist

- [ ] I can define cache hit, miss, hit rate and TTL without notes. *(B.1)*
- [ ] I can explain locality and give an example of a workload where a cache
      would be useless. *(B.2)*
- [ ] I can explain why a shared cache server is needed rather than a dictionary
      in the process. *(C)*
- [ ] I can explain what Redis traded away and what it got for it. *(D.1)*
- [ ] I can explain why Redis being single-threaded is mostly an advantage, and
      the one case where it is not. *(D.2, L.2)*
- [ ] I can list what must be in this project's cache key, and why the user id is
      a prefix rather than part of the hash. *(E.1, E.2, E.3)*
- [ ] I can name the five invalidation strategies and pick one for a given
      situation. *(F.2, O7)*
- [ ] I can retell Incident One — the mismatch, why nothing errored, what the
      user experienced, and the fix at the right layer. *(G)*
- [ ] I can explain why "a missing dependency looked like a cache miss" is the
      same shape as three other defects in this course. *(H.4)*
- [ ] I can explain why `finally: await redis.close()` matters on this specific
      path. *(I, O11)*
- [ ] I can give five situations where caching is the wrong answer. *(J)*
- [ ] I can explain a stampede, cache penetration and a hot key. *(K.4, K.5)*
- [ ] I completed N9, N12 and N15 with written reasoning.
- [ ] **The real test:** open
      [`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py)
      and read `_retrieval_cache_key`, `_get_cached_retrieval` and
      `_set_cached_retrieval`, then the purge block in
      [`documents.py`](../backend/app/api/v1/endpoints/documents.py). Explain
      every line, state which invariant connects the two files, and describe
      exactly what a user would experience if that invariant were broken again.

If the last box is ticked, you can defend the caching layer of this system in
an interview — and Chapter 12 can be about the *other* thing Redis does here:
carrying work to a separate process that does it later.

---

*Next: `12-background-jobs.md` — Celery, queues and scheduled work: how the
slow half of this system runs outside the request, survives restarts, and
occasionally fails silently when one of three rules is forgotten.*
