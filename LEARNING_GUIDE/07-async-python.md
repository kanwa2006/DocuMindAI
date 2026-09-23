# 07 — Asynchronous Python

**Prerequisites:** Chapters 05 and 06. You need processes, threads, memory, the
memory hierarchy, sockets, and all of Chapter 06's Python — especially
functions, generators, decorators, context managers and exceptions.

**What this chapter is about.** Chapter 06 deliberately left one thing
unexplained. Real code in this repository is full of `async def` and `await`,
and you were told to read `await X` as "do X, and let other work run while
waiting". That placeholder ends here.

**Why this chapter is hard, and how we will make it easy.** Asynchronous
programming is where most self-taught engineers get permanently confused,
because it is almost always taught syntax-first: *"put `async` before `def` and
`await` before slow calls"*. That produces people who can write async code and
cannot debug it — and this repository contains three production incidents
caused by exactly that gap.

So we start with the problem, spend a long time there, and only introduce
syntax once you can predict what it must do.

---

# Part A — The Problem: Waiting Versus Working

## A.1 What actually takes time

Recall the memory hierarchy from Chapter 05:

| Operation | Rough time | In "one CPU cycle = 1 second" terms |
|---|---|---|
| Read from RAM | 100 nanoseconds | 5 minutes |
| Read from SSD | 100 microseconds | 4 days |
| Network inside a datacentre | 500 microseconds | 3 weeks |
| Network across the internet | 50 milliseconds | 5 years |
| One LLM call | 2 seconds | 200 years |

Now ask a question nobody asks early enough: **during those 2 seconds, what is
the CPU doing?**

Nothing. It sent a request over a socket and it is waiting for bytes to come
back. The processor is idle, the memory is idle, and the program is stopped on
one line.

**That idle time is the entire subject of this chapter.**

## A.2 Two kinds of work

Every piece of a program falls into one of two categories, and telling them
apart is the single most important diagnostic skill here.

**CPU-bound work** keeps the processor busy. Computing an embedding, resizing
an image, sorting a million numbers, parsing a large document. The limit is how
fast the processor can compute.

**I/O-bound work** waits for something outside the processor. Reading a file,
querying a database, calling an API, waiting for a browser to send the rest of
a request. **I/O** means input/output — anything that crosses the boundary out
of the CPU and memory. The limit is how fast the other thing answers.

**Why the distinction decides everything:**

- If work is **CPU-bound**, going faster means more processors, better
  algorithms, or a faster language. There is no trick.
- If work is **I/O-bound**, the processor is idle anyway, so you can do
  something *else* with that idle time — for free.

**Async programming is exclusively a technique for I/O-bound work.** It makes
waiting productive. It does not make computation faster. Hold on to that
sentence; half the misconceptions in Part L are people forgetting it.

**Which is this repository?** Let us count one grounded question honestly:

| Stage | Time | Kind |
|---|---|---|
| Embed the question | ~50 ms | **CPU** |
| Vector search in PostgreSQL | ~30 ms | **I/O** (waiting for the database) |
| Full-text search | ~20 ms | **I/O** |
| Rerank 30 candidates | ~300 ms | **CPU** |
| Generate the answer | ~2,000 ms | **I/O** (waiting for Google) |
| Write history rows | ~20 ms | **I/O** |

Total ≈ 2.4 seconds, of which about **2.07 seconds is waiting** — roughly 86%.
And 350 ms is genuine computation that will not be helped by async at all.

**That table is the whole architecture of this chapter.** The big number is
waiting, so async is the right tool. The 350 ms of CPU work is the exception
that must be handled separately — and mishandling it caused two of the three
incidents in Part K.

## A.3 Blocking, defined precisely

**Blocking** means: this line of code does not return until it is finished, and
while it waits, **the thread running it can do nothing else**.

```python
import time
response = requests.get("https://example.com")   # blocks ~200 ms
time.sleep(1)                                     # blocks 1 second
rows = cursor.execute("SELECT ...")               # blocks until the DB answers
```

**Why is this the default?** Because it is the obvious way to write a program
and it matches how we think: do this, then do that. Chapter 05's system-call
model explains the mechanism — your program asks the kernel to read from a
socket, and the kernel does not return control until data arrives. Your thread
is parked. Nothing about it is wrong; it is simply *exclusive*.

**The critical insight, and it is the hinge of this whole chapter:**

> Blocking is not a problem when there is only one thing to do.
> Blocking is a catastrophe when there are a hundred things to do and one of
> them is holding the only worker.

## A.4 The arithmetic of waiting

Make it concrete. One server, one thread, and each request takes 2.4 seconds of
which 2.07 is waiting.

**With blocking, one thread:**

- Requests handled per second: 1 ÷ 2.4 = **0.42**
- Twenty users arriving at once: the last waits 48 seconds.
- CPU usage while all this happens: about **14%**.

Read that last line again. The machine is idle 86% of the time *and* users are
waiting 48 seconds. **You are not short of computing power. You are short of
attention.** Buying a faster CPU would change nothing.

**If waiting could overlap:**

- The 2.07 seconds of waiting for one request happens *during* another
  request's waiting.
- The genuine limit becomes the CPU work: 350 ms per request.
- Requests per second: 1 ÷ 0.35 ≈ **2.85** — nearly seven times more, on the
  same hardware, with no faster anything.

**That factor of seven is why async exists.** Not because it is modern, not
because it is fashionable — because 86% of the time was being thrown away.

---

# Part B — What People Tried Before, and Why Each Was Not Enough

Async is the fourth answer to this problem. Knowing the first three tells you
exactly what async is for, and — just as important — when the older answers are
still correct.

## B.1 Attempt 1: one process per request

The earliest web servers started a whole new process for each request
(the CGI model, early 1990s).

**Why it worked:** processes are isolated (Chapter 05), so one crashing request
could not damage another. Simple, safe, obvious.

**Why it was not enough:** a process is expensive. Creating one takes
milliseconds and it needs its own memory — often megabytes. A hundred
simultaneous requests meant a hundred processes competing for memory. The
machine spent more time *managing* processes than serving requests.

## B.2 Attempt 2: one thread per request

Threads (Chapter 05, C.3) are much cheaper than processes: they share the
process's memory, so creating one is fast.

**Why it worked, and it genuinely did:** each request gets its own thread, each
thread blocks happily on its own I/O, and the operating system switches between
them. The code stays simple — you write ordinary blocking code and the OS
handles the overlap. This is still how many production servers work today, and
for many applications it is the right answer.

**Why it was not enough**, in three parts:

1. **Memory.** Every thread needs its own **stack** — a region of memory
   holding its chain of function calls — typically several hundred kilobytes to
   a megabyte. Ten thousand threads is gigabytes of stacks doing nothing but
   waiting.
2. **Switching cost.** The OS switching between threads is not free: it must
   save and restore registers and disturb the CPU's caches. With thousands of
   threads, a measurable share of the machine goes into switching.
3. **Shared memory is dangerous.** Threads share everything, so any data two
   threads touch needs locking, and locking is where the hardest bugs live.

This became famous around 2000 as the **C10K problem**: how do you serve ten
thousand simultaneous connections on one machine? Not with ten thousand
threads.

**And Python has a fourth problem the others do not**, from Chapter 06: the
**GIL** means only one thread runs Python code at a time. For *waiting* threads
that is fine — a thread waiting on a socket has released the GIL. But it does
mean threads will never give Python parallel computation.

## B.3 Attempt 3: callbacks

If waiting is the problem, do not wait. Ask for the data and supply a function
to be called when it arrives.

```python
def on_data(result):
    print(result)

fetch("https://example.com", on_data)     # returns immediately
print("this runs first")
```

**Why it worked:** one thread could now manage thousands of connections,
because nothing ever blocked. This is what made early Node.js fast, and it
solved C10K.

**Why it was not enough:** sequences of dependent operations nest, and the code
stops reading like the thing it does.

```python
fetch(url, lambda a:
    query(a.id, lambda b:
        write(b, lambda c:
            respond(c))))
```

This is **callback hell**. Worse than ugly: error handling has no natural home
(there is no `try` that spans callbacks), and the ordinary tools of programming
— loops, exceptions, `return` — stop working normally.

## B.4 Attempt 4: coroutines with `async`/`await`

The insight: **keep the efficiency of callbacks, but let the code look
sequential.**

If a function could *pause itself* at a waiting point, let other work run, and
resume later exactly where it stopped — with its local variables intact — then
you could write:

```python
a = await fetch(url)
b = await query(a.id)
c = await write(b)
```

Reads top to bottom. `try`/`except` works. Loops work. And underneath, at every
`await`, other work runs.

**You already know the machinery that makes this possible.** Chapter 06 taught
generators: a function with `yield` that runs, hands over a value, **freezes
with its local variables intact**, and resumes when asked. A coroutine is that
same trick, aimed at a different purpose — pausing to wait instead of pausing
to produce.

**The history is exactly that.** Python 3.4 (2014) shipped `asyncio` using
generators with a decorator. Python 3.5 (2015) added `async def` and `await` as
proper syntax for what people were already doing with generators. **The syntax
came second; the mechanism came first.**

---

# Part C — The Event Loop, From First Principles

## C.1 The intuition: one waiter, many tables

Picture a small restaurant with **one waiter**.

A blocking waiter takes table 1's order, walks to the kitchen, and **stands
there** until the food is ready. Tables 2 through 10 wait, unserved, while the
waiter watches a pot.

An asynchronous waiter takes table 1's order, hands it to the kitchen, and
immediately goes to table 2. Then table 3. When the kitchen rings a bell, the
waiter delivers that dish and continues.

**Two things about this analogy matter more than the analogy itself:**

1. **The waiter never gets faster.** Serving is still one person doing one
   thing at a time. What changed is that *waiting* stopped consuming the
   waiter.
2. **If one task genuinely requires the waiter's hands** — say, hand-grinding
   pepper for four minutes — **everything stops again**. Async gains nothing,
   because the resource being consumed is the waiter, not the kitchen.

That second point *is* CPU-bound work. It is the whole of Part H, and it is
what caused every incident in Part K.

**A second analogy for the same thing, because different minds catch on
different pictures:** an air traffic controller manages thirty aircraft with
one voice. They are never talking to two planes at once. They issue an
instruction, and while that plane executes it, they speak to another. If the
controller had to personally walk out and refuel a plane, the whole airspace
would freeze.

## C.2 The mechanism

Behind the analogy is a specific, simple machine. It has three parts.

**1. The ready queue.** Coroutines that can run right now.

**2. The waiting set.** Coroutines that are paused, each recorded together with
the thing it is waiting for — this socket to have data, this timer to expire.

**3. The loop itself:**

```
forever:
    take the next coroutine from the ready queue
    run it until it awaits something, or finishes
    if it awaited something:
        move it to the waiting set, remembering what it waits for
    if the ready queue is empty:
        ask the operating system which of the waited-for things are ready now
        move those coroutines back to the ready queue
```

That is the entire event loop. There is no magic in it and no parallelism in
it: **one coroutine runs at a time**, on one thread, in one process.

**The one part that needs the operating system.** "Ask which of the waited-for
things are ready" is a real system call — `epoll` on Linux, `kqueue` on macOS,
IOCP on Windows. You hand the kernel a list of sockets and say "wake me when
any of these has data". The kernel is already tracking that, so it costs
almost nothing. **This is the piece that makes the whole design possible**, and
it is why async programming appeared only after operating systems provided it.

## C.3 What `await` actually does

**`await` does exactly two things:**

1. It **suspends** the current coroutine at that point, keeping all of its
   local variables.
2. It **hands control back to the event loop**, along with a note saying what
   would have to happen for it to continue.

That is all. Notice what it does **not** do:

- It does not create a thread.
- It does not make anything faster.
- It does not run the awaited thing "in the background".
- It does not, by itself, make anything happen at the same time as anything
  else.

**`await` is a request to be paused.** The word "await" is honest: the coroutine
is announcing that it is about to wait, so that something else may run.

## C.4 Cooperative versus preemptive

This is the property that makes async both efficient and dangerous.

**Preemptive multitasking** (how the OS handles threads and processes): the
system interrupts a thread whenever it likes — every few milliseconds — and
gives the CPU to someone else. The thread has no say. This is why blocking code
in *threads* does not freeze the whole program: the OS takes the CPU away.

**Cooperative multitasking** (how the event loop handles coroutines): a
coroutine keeps running until it *voluntarily* yields at an `await`. The loop
cannot interrupt it. There is no mechanism to.

**Therefore:**

> **A coroutine that does not `await` cannot be interrupted, and everything
> else waits for it.**

That sentence is the root cause of every incident in Part K. It is not a bug in
asyncio; it is the design. Cooperation is what makes it cheap — no OS
involvement, no locks needed at most points — and cooperation is a promise your
code must keep.

## C.5 Where the call stack lives

Chapter 05 said a thread has a stack: its chain of calls. In async code, each
paused coroutine keeps its own small frame — its local variables and its
position — as an object on the **heap** (the general memory area), not on the
thread's stack.

**Why this is the key efficiency.** A thread's stack costs hundreds of
kilobytes because it must reserve room for any depth of calls. A suspended
coroutine costs a few hundred *bytes*, because it only stores what it actually
has. That is why one process can hold a hundred thousand paused coroutines and
would collapse under a hundred thousand threads.

## C.6 A trace of two requests

Two requests arrive at nearly the same moment. Read this slowly; it is the
mental model you will use to debug real problems.

```
t=0ms    Request A starts. Runs until: await db.execute(...)
         → A suspends. Loop notes: A waits on socket to database.
t=0ms    Loop takes Request B from the ready queue.
         B runs until: await db.execute(...)
         → B suspends. Loop notes: B waits on socket to database.
t=0ms    Ready queue empty. Loop asks the OS: "wake me when either socket
         has data." Loop sleeps. CPU is free for other processes.
t=30ms   Database answers A. OS wakes the loop. A moves to ready.
         A resumes on the line after its await, with all locals intact.
         A runs until: await llm.generate(...)  → suspends again.
t=31ms   Database answers B. B moves to ready. B resumes. → suspends on its
         own LLM call.
t=2031ms Google answers A. A resumes, finishes, sends its response.
t=2050ms Google answers B. B resumes, finishes, sends its response.
```

**Both requests finished in about 2 seconds, not 4.** One thread. One CPU. No
parallelism anywhere. The overlap is entirely in the waiting.

**Now imagine that at t=0 request A did 3 seconds of CPU work instead of an
`await`.** B does not start at t=0. B does not start at t=1000. B starts at
t=3000, because nothing took the CPU away from A and A never offered it.
**That is the incident in Part K, in advance.**

---

# Part D — The Syntax, Now That It Is Motivated

## D.1 `async def` creates a coroutine function

```python
async def get_answer():
    return 42
```

`async def` does not define a normal function. It defines a **coroutine
function**: calling it *does not run the body*. It builds a coroutine object,
which is a paused computation waiting to be driven.

```python
result = get_answer()
print(result)        # <coroutine object get_answer at 0x...>
```

**This surprises everyone once**, and it is the first thing to recognise. If
you see a coroutine object where you expected a value, you forgot an `await`.
Python will also print a warning: `RuntimeWarning: coroutine ... was never
awaited`. **Treat that warning as an error** — it means a piece of your program
silently did not happen.

## D.2 `await` runs it and waits

```python
async def main():
    result = await get_answer()
    print(result)          # 42
```

**The rule: `await` may only appear inside `async def`.** Why? Because `await`
means "suspend me and return control to the loop", and only a coroutine *can*
be suspended. Writing `await` in a normal function is a syntax error, which is
Python failing fast at exactly the right moment.

## D.3 Starting the loop

Someone must create and drive the loop. At the top level that is
`asyncio.run`:

```python
import asyncio

async def main():
    print("start")
    await asyncio.sleep(1)
    print("end")

asyncio.run(main())
```

`asyncio.run` creates an event loop, runs `main()` until it finishes, and
closes the loop. **In this repository you will never write it**, because the
web server creates the loop and calls your endpoint coroutines for you. But
knowing something must drive the loop explains why a stray coroutine in a
script does nothing.

**And note `asyncio.sleep` versus `time.sleep`** — the difference is the whole
chapter in two lines:

```python
time.sleep(1)              # blocks the thread; the loop cannot run anything
await asyncio.sleep(1)     # suspends this coroutine; the loop runs others
```

## D.4 The tiny example that proves it

```python
import asyncio
import time

async def task(name, seconds):
    print(f"{name} starting")
    await asyncio.sleep(seconds)
    print(f"{name} done")

async def main():
    start = time.time()
    await task("A", 1)
    await task("B", 1)
    print(f"sequential: {time.time() - start:.1f}s")

asyncio.run(main())
```

Output: **2.0 seconds.** And this is the most important early lesson:

> **`await` on its own is sequential.** `await task("A", 1)` means "pause me
> until A is finished". Nothing else of *yours* runs during it.

`await` gives the loop an opportunity to run *other* work. If there is no other
work, nothing overlaps. To overlap your own tasks, you must say so — Part E.

## D.5 Where this appears in the repository

Almost every function in the request path is a coroutine function. From
[`backend/app/core/document_access.py`](../backend/app/core/document_access.py):

```python
async def get_owned_document(
    db: AsyncSession,
    document_id: uuid.UUID | str,
    current_user: dict,
) -> Document:
    ...
    doc = (
        await db.execute(
            select(Document).where(...)
        )
    ).scalar_one_or_none()
```

Reading it with everything we now know:

- `async def` — this function will suspend at least once, so it must be a
  coroutine.
- `await db.execute(...)` — send the query over a socket to PostgreSQL and
  **suspend**. During the ~20 ms wait, the event loop serves other users.
- `.scalar_one_or_none()` — runs *after* resuming, on the awaited result. Note
  it is not awaited itself: it just reads from a result already in memory.

**What would happen if the `await` disappeared?** `db.execute(...)` would
return a coroutine object, `.scalar_one_or_none()` would be called on a
coroutine rather than a result, and you would get an `AttributeError` — or
worse, with some libraries, a silently wrong value. The query would never run.

---

# Part E — Tasks: Making Your Own Work Overlap

## E.1 The problem `await` does not solve

D.4 showed that two awaits in a row take the sum of their times. If two things
are genuinely independent — fetching a user and fetching their documents —
waiting for one before starting the other is pure waste.

## E.2 Coroutine, Task, Future

Three words that are constantly confused:

- A **coroutine** is a paused computation. It does nothing until driven.
- A **Task** is a coroutine that the loop has been told to run. It is *already
  progressing* whenever the loop gets a chance.
- A **Future** is a placeholder for a value that is not ready yet. A Task is a
  kind of Future.

**The distinction that matters: a coroutine is inert; a Task is scheduled.**

```python
coro = fetch(url)                       # nothing is happening
task = asyncio.create_task(fetch(url))  # now it is progressing
result = await task                     # wait for a result that may already exist
```

## E.3 `gather` — the everyday tool

```python
async def main():
    start = time.time()
    await asyncio.gather(
        task("A", 1),
        task("B", 1),
    )
    print(f"concurrent: {time.time() - start:.1f}s")
```

Output: **1.0 second.** `gather` schedules everything as tasks, then waits for
all of them, and returns their results in the order given — not the order they
finished.

**When to use it:** several independent I/O operations. The classic shape is
three database queries that do not depend on each other.

**When not to use it:** when the operations depend on each other (you have no
choice but to sequence them), or when running them at once would overwhelm
something. `gather` over a thousand items starts a thousand simultaneous
requests, and the database or the API will not thank you. That is what a
semaphore is for (Part J).

**By default, one failure cancels nothing else and the exception propagates
after the others finish.** `return_exceptions=True` changes it to collect
exceptions as results instead. Choose deliberately: is a partial result useful,
or is the whole operation void?

## E.4 Fire-and-forget, and its traps

Sometimes you want to start something and not wait for it:

```python
asyncio.create_task(send_email(user))     # start it; carry on
```

**Two traps, both real:**

1. **The task may be garbage collected.** The loop keeps only a weak reference,
   so if you do not keep the task object, it can be destroyed mid-flight.
   The fix is to store it somewhere until it completes.
2. **Exceptions vanish.** If the task raises and nobody ever awaits it, the
   error may surface only as a warning when the object is destroyed — possibly
   long afterwards, possibly never. **A fire-and-forget task is a silent
   failure waiting to happen**, which is exactly the pattern this repository's
   loud-degradation rule exists to prevent.

**A real fire-and-forget in this repository**, in
[`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py),
sending trial-lifecycle emails:

```python
                # Fire-and-forget lifecycle emails — never blocks the stream.
                if user_obj and getattr(user_obj, "email_notifications_enabled", True):
                    _loop = asyncio.get_event_loop()
                    _q_used = trial_status["queries_used"]
                    if _q_used == TRIAL_QUERY_LIMIT - 2:
                        _loop.run_in_executor(...)
```

Note what it is and is not. The comment states the intent — *never blocks the
stream* — and it uses `run_in_executor` **without awaiting it**, so the email is
sent on a worker thread while the answer streams on.

**Is this correct?** For its purpose, mostly: a failed marketing email must not
break a user's answer. But it inherits trap 2 — if sending raises, nothing
observes it. A more defensive version would attach a completion callback that
logs failures. This is a genuine, small weakness, and it appears again in the
critique.

## E.5 `TaskGroup` — the modern, safer form

This project runs Python 3.11, which added a better tool:

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(fetch_user())
        tg.create_task(fetch_documents())
    # both are finished here
```

**Why it is better than `gather`:** the block does not exit until every task
finishes, so no task can outlive its scope; and if one fails, the others are
cancelled and the errors are raised together. This is called **structured
concurrency** — the principle that a task's lifetime is bounded by a visible
block, exactly as a variable's lifetime is bounded by its scope.

**Why this repository does not use it:** the async code predates a decision to
adopt it, and `gather` plus explicit `run_in_executor` calls cover the cases
present. That is a defensible position and also a candidate for future work —
noted in the critique.

---

# Part F — Cancellation and Timeouts

## F.1 Why cancellation exists

A user asks a question, waits three seconds, and closes the tab. The server is
still generating an answer nobody will read: still holding a database
connection, still paying for tokens, still occupying a slot in the LLM rate
limit.

**Cancellation is how work stops when its result stops being wanted.**

## F.2 How it works

Cancelling a task raises `asyncio.CancelledError` **inside the coroutine, at
its current suspension point**. The coroutine can catch it to clean up, but
should re-raise: cancellation is a request that must be honoured, not an error
to be swallowed.

```python
task = asyncio.create_task(long_job())
task.cancel()
try:
    await task
except asyncio.CancelledError:
    print("cancelled cleanly")
```

**The catch that follows from C.4:** cancellation can only be delivered at an
`await`. A coroutine doing three seconds of pure computation cannot be
cancelled during it — there is no point at which to interrupt. **Cooperative
scheduling means cooperative cancellation.**

## F.3 Timeouts

A timeout is cancellation on a timer:

```python
try:
    result = await asyncio.wait_for(slow_call(), timeout=5)
except asyncio.TimeoutError:
    ...
```

**And now the decision from Chapter 03, with full understanding.** From
[`backend/app/services/llm_service.py`](../backend/app/services/llm_service.py):

```python
        return await asyncio.wait_for(
            ...,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
```

for the non-streaming path — a bound on the whole call. But for the streaming
path the same setting bounds **each step**:

```python
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda it=iterator: next(it, exhausted)),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
```

with the reasoning in the code:

> *"Bound each STEP, not the whole stream: total generation time is
> legitimately long, but an individual chunk that never arrives previously hung
> forever — generate_stream had no timeout at all, while _provider_generate
> enforces this same setting."*

**Why a whole-stream timeout would be wrong:** any value is wrong. Too low
kills legitimate long answers; too high fails to protect. The meaningful unit
for a progressive operation is one step, and asking "what unit should this
timeout bound?" is a question to carry to every timeout you ever set.

## F.4 The client's cancel

Chapter 01 showed the browser side:

```ts
const res = await apiFetch(`/query/stream`, { method: "POST", signal, ... });
```

`signal` is an `AbortSignal`. When the user presses stop, the browser closes
the connection. The server's write then fails, the streaming generator raises,
and the work unwinds. **Cancellation is end-to-end**, and it only works because
every layer eventually reaches an `await` that can raise.

---

# Part G — Async Generators and Async Context Managers

## G.1 `async with` — cleanup that must happen

Chapter 06 taught context managers: `with` guarantees the cleanup step runs. An
**async context manager** is the same idea when setup or cleanup must wait.

```python
async with AsyncSessionLocal() as session:
    ...
```

That is real, from
[`backend/app/db/session.py`](../backend/app/db/session.py). Acquiring a
database session may need to wait for a free connection from the pool, and
returning it may need to wait for a transaction to settle. Both are I/O.
**`async with` is `with` where the entering and leaving can suspend.**

## G.2 `async for` and async generators

An **async generator** produces values over time, where getting the next value
may require waiting.

```python
async def read_lines(url):
    async with open_connection(url) as conn:
        while True:
            line = await conn.readline()
            if not line:
                return
            yield line

async for line in read_lines(url):
    print(line)
```

Ordinary generators (Chapter 06) produce values whenever asked. Async
generators may need to *wait* before they can produce the next one — which is
exactly the shape of streaming.

**Where this is the entire feature in this repository.** The provider's
streaming method is declared:

```python
    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
```

and the endpoint that consumes it is itself an async generator, whose values
are SSE frames:

```python
    async def event_generator():
        ...
        yield f"event: status\ndata: {json.dumps({'message': 'Retrieving semantic chunks...'})}\n\n"
        ...
        yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        ...
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Read what that means at the network level.** `StreamingResponse` takes the
async generator and, each time it yields, writes those bytes to the open socket
and flushes. Between yields, the coroutine is suspended and the loop serves
other users. **The answer appearing word by word in the browser is this
generator suspending and resuming, dozens of times, interleaved with everyone
else's requests.**

## G.3 The dependency generator

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

One `yield`, in an async generator, used as a FastAPI **dependency** (Chapter
14). The shape is: set up, hand the thing over, and — when the request is
finished — resume after the `yield` so the `async with` can clean up.

**Why a generator and not a plain function?** Because a plain function can only
hand something over; it cannot get control back afterwards to clean up. The
`yield` is what creates an "after".

**And this connects to a subtle decision you have already seen.** Chapter 01
quoted the comment in `core/auth.py` explaining why the tenant scope is set with
a plain `.set()` rather than a `yield`-style dependency:

> *"A `yield`-style dependency would tie the scope's lifetime to the
> dependency's, which is WRONG for SSE: the streaming generator in query.py
> outlives the dependency and still needs the scope while it runs."*

Now that sentence is fully readable. FastAPI cleans up `yield` dependencies
when the *handler* returns — but for a streaming response the handler returns
almost immediately, handing back a generator that runs for seconds afterwards.
A scope tied to the dependency would be gone exactly when the streaming code
needed it. **Understanding coroutine lifetimes was required to get tenant
isolation right in the streaming path.**

---

# Part H — When Async Is Not the Answer

## H.1 The CPU-bound problem

Return to C.4: a coroutine that does not `await` cannot be interrupted. So what
do you do with 300 milliseconds of genuine computation on the request path?

You cannot `await` it — there is nothing to wait for. It is not I/O. It is the
waiter grinding pepper.

**The answer: get it off the event loop's thread.**

## H.2 Thread pools — `run_in_executor`

```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, slow_function, arg1, arg2)
```

What happens, step by step:

1. `slow_function(arg1, arg2)` is handed to a pool of worker **threads**.
2. `run_in_executor` returns a Future immediately.
3. `await` suspends this coroutine — **the loop is free**.
4. A worker thread runs the function. It blocks; that is fine, it is not the
   loop's thread.
5. When it finishes, the Future resolves, the coroutine returns to the ready
   queue, and it resumes with the result.

`None` as the first argument means "use the default thread pool".

**"But the GIL!"** Correct and important. Chapter 06 said only one thread runs
Python code at a time, so how does moving Python work to a thread help?

Two answers:

1. **The loop is freed even if the work is not parallel.** The blocking now
   happens somewhere that does not stop everyone else. Other requests progress
   *at their await points*.
2. **The heavy libraries release the GIL.** The embedding model and the
   reranker do their real work in compiled C or C++ code, and those libraries
   release the GIL while computing. So that work genuinely runs in parallel
   with Python code on another core.

**That second point is why this pattern works so well here specifically**, and
why it would help much less for 300 ms of pure-Python looping.

## H.3 Process pools

When the work is CPU-bound **and** written in pure Python, threads cannot give
parallelism. Then you need separate processes:

```python
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor() as pool:
    result = await loop.run_in_executor(pool, cpu_heavy, data)
```

Each process has its own interpreter and its own GIL, so they compute in
parallel. **The cost, from Chapter 05:** separate memory means arguments and
results must be serialised and copied between processes, which is expensive for
large data — and it is why sending a 500 MB document to a process pool is
usually worse than doing the work where it is.

## H.4 The third option: a job queue

For work measured in minutes rather than milliseconds, neither pool is right.
Chapter 02's decision D-007 applies: put it on a queue and let a separate
worker process do it — which survives a restart, scales independently, and
keeps heavy dependencies out of the web process.

## H.5 The decision table

Memorise this; it answers a question you will be asked in interviews and on the
job.

| The work is… | Use | Why |
|---|---|---|
| Waiting for I/O, milliseconds to seconds | `await` | The loop stays free; nearly free to do |
| CPU-bound, milliseconds, mostly in C libraries | `run_in_executor` (threads) | Frees the loop; the library releases the GIL |
| CPU-bound, pure Python, needs real parallelism | process pool | Each process has its own GIL |
| Minutes, must survive a restart, independently scalable | job queue + worker | Durable, observable, retryable |
| Nothing else is happening | plain blocking code | Simplest thing that works — do not add async for its own sake |

**That last row is not a joke.** A script that does one thing has no other work
to overlap with, so async adds machinery and buys nothing. **Async is a
throughput technique, not a correctness technique.**

---

# Part I — Mixing Sync and Async Safely

## I.1 The one rule

> **Never call blocking code from inside a coroutine.**

Every incident in Part K is a violation of that sentence.

## I.2 How to find violations

Reading code is unreliable, because blocking calls look ordinary. Four
techniques, in order of usefulness:

1. **Know the blocking library names.** `requests`, `time.sleep`,
   `psycopg2`, plain `open()` on a large file, any model's `.predict()`.
   If an async-capable equivalent exists (`httpx`, `asyncio.sleep`, `asyncpg`),
   its presence is the signal.
2. **Look for a call with no `await` that is doing real work.** In an
   `async def`, a line that takes measurable time and has no `await` is
   suspicious by construction.
3. **Measure the property, not the source.** Run a heartbeat coroutine that
   ticks every 10 ms while the suspect code runs. If ticks stop, the loop is
   blocked. This is exactly what this repository's guards do, and it is the only
   method that cannot be fooled by code that *looks* offloaded.
4. **Use asyncio's debug mode**, which warns when a callback takes too long.

## I.3 `asyncio.to_thread`

Python 3.9 added a friendlier form of the same thing:

```python
result = await asyncio.to_thread(slow_function, arg1, arg2)
```

Identical in effect to `run_in_executor(None, ...)`, and easier to read. The
repository uses the older form because that is the shape already established in
`llm_service.get_embedding`; consistency inside one codebase is worth more than
using the newest spelling.

## I.4 Calling async code from sync code

The reverse direction. If you are in an ordinary function and need to run a
coroutine, you must drive a loop:

```python
result = asyncio.run(my_coroutine())
```

**But never inside a running loop.** `asyncio.run` creates a new loop, and
creating a loop inside a loop raises. If you find yourself wanting this, you are
usually in a function that should have been a coroutine.

**And this is why the repository's worker code is entirely synchronous.** From
`CLAUDE.md`:

> *"**Async API / sync workers.** FastAPI + `asyncpg` on the request path;
> Celery uses `SyncSessionLocal` (psycopg2). Never mix."*

The Celery worker has no event loop. It is a plain synchronous program running
one task at a time per child process, and it uses a synchronous database driver
to match. **Two consistent worlds are far easier to reason about than one
hybrid**, and the invariant exists because half-async code is where the worst
bugs live.

## I.5 A sync lock in an async codebase

One more real case, and it is instructive. In
[`backend/app/services/llm_key_rotation.py`](../backend/app/services/llm_key_rotation.py):

```python
        self._lock = threading.Lock()
```

A **threading** lock, not an `asyncio.Lock`, in a system whose request path is
async. Is that a mistake?

No — it is correct, and the reason is worth working through. The key rotator's
state is touched from three places: the async request path, worker threads
running executor calls, and the synchronous Celery worker. An `asyncio.Lock`
protects only against interleaving *coroutines on one loop*; it does nothing
about two threads. A `threading.Lock` protects against threads.

**The rule to extract:** choose the lock that matches the thing that can
actually interleave. If your shared state is reachable from threads, an
async-only lock is a comfort blanket, not a control.

---

# Part J — Locks, Semaphores, Queues, Backpressure

## J.1 Why locks exist even without threads

"There is only one thread, so nothing can interleave" — a natural conclusion,
and wrong.

**Every `await` is an interleaving point.** Between the moment you suspend and
the moment you resume, other coroutines run and may modify the same data.

```python
async def transfer(account, amount):
    balance = account.balance          # read
    await save_audit_log()             # ← anything can happen here
    account.balance = balance - amount # write, using a possibly stale value
```

Two concurrent transfers can both read the same balance before either writes.
This is a **race condition** (Chapter 03) in single-threaded code.

**The saving grace:** the interleaving points are *visible*. In threaded code
a switch can happen between any two machine instructions; in async code it can
only happen at an `await`. **You can find the danger by looking for awaits**,
which is why async concurrency bugs are far more tractable than threaded ones.

## J.2 `asyncio.Lock`

```python
lock = asyncio.Lock()

async def transfer(account, amount):
    async with lock:
        balance = account.balance
        await save_audit_log()
        account.balance = balance - amount
```

Only one coroutine may be inside the block at a time; others wait at the
`async with` — suspended, not blocking.

**The cost, and it is the same cost locks always have:** the protected section
becomes sequential. Holding a lock across a slow `await` serialises everything.
The discipline is to **keep the awaited work outside the lock wherever you
can** — which the key rotator does deliberately, with an out-of-lock cooldown
wait recorded in its comments as something to preserve.

## J.3 Semaphores — bounding concurrency

A **semaphore** allows up to N at once instead of one.

```python
sem = asyncio.Semaphore(5)

async def fetch_one(url):
    async with sem:
        return await http_get(url)

await asyncio.gather(*(fetch_one(u) for u in thousand_urls))
```

Without the semaphore this starts a thousand simultaneous requests. With it,
five at a time.

**Why this matters in this repository's world.** The AI provider limits
requests per minute; the database has a connection budget of a handful
(Chapter 02's arithmetic). **Unbounded concurrency does not increase
throughput once you have saturated the bottleneck; it just converts a queue you
control into failures you do not.** A semaphore is how you keep the queue on
your side.

## J.4 Queues and backpressure

`asyncio.Queue` passes items between coroutines. A queue created with a
`maxsize` blocks producers when full — and that is **backpressure** (Chapter
04): the mechanism by which a slow consumer tells a fast producer to slow down.

**Without backpressure, a fast producer and a slow consumer end in one of two
places: unbounded memory growth, or dropped data.** A bounded queue chooses the
third option — the producer waits — and it is almost always the right one.

---

# Part K — The Real Incidents

Three production defects in this repository, all the same class, discovered in
order of decreasing obviousness. Each is presented as problem, symptom, root
cause, why async behaved that way, and the fix.

## K.1 Incident 1 — the mock provider that froze everyone

**The problem.** `DummyLLMProvider.generate` — used when no API key is
configured — contained `time.sleep(0.5)` to simulate latency.

**The symptom.** Under a misconfigured deployment, every request took
progressively longer as concurrency rose; requests were serialised.

**The root cause**, from commit `1c02c6b`:

> *"`time.sleep(0.5)` inside `async def DummyLLMProvider.generate` blocks the
> entire event loop, not just its caller. Every concurrent request on that
> worker stalls for the full 500 ms."*

**Why async behaved that way.** `time.sleep` is a blocking call: it parks the
thread. The thread is the event loop. C.4's cooperative rule says the loop
cannot take control back. So all requests waited 500 ms each, in turn.

**Why the fix is one line:**

```python
await asyncio.sleep(0.5)  # Simulate generation latency
```

`asyncio.sleep` suspends the coroutine and schedules a wake-up. The loop is
free for the whole half-second.

**The detail that shows engineering maturity**, from the same commit:

> *"DummyLLMProvider only serves when no Gemini key is configured, so this is
> not on a correctly-configured production path. That is also what makes it
> worth fixing: it takes an already-degraded deployment — one that has just
> lost its API keys and is serving mock answers — and serializes it completely,
> at exactly the moment throughput matters most."*

**Failures compound.** A defect that only appears when something else has
already gone wrong is *more* dangerous, not less, because it arrives during an
incident.

**And the verification is the model to copy:**

> *"Guard `tests/test_dummy_provider_does_not_block_loop.py` measures the
> property rather than the source text: four concurrent `generate` calls must
> overlap. Observed RED on the reintroduced defect — '  4 concurrent calls took
> 2.00s (ceiling 1.20s, fully serialized would be 2.00s)', which is the
> serialization made visible, not a proxy for it."*

Four calls of 0.5 s each: overlapping ≈ 0.5 s, serialised = 2.0 s. The test
asserts the total is under 1.2 s. **The number *is* the defect**, not a symptom
of it.

## K.2 Incident 2 — the two model calls on the query path

**The problem.** Two CPU-bound model inferences ran directly inside coroutines:
the query embedding in `retrieval_service.py` and the cross-encoder rerank in
`grounding_service.py`.

**The symptom.** Unrelated endpoints became slow whenever anyone asked a
question.

**The root cause**, from commit `e697dd1`:

> *"Both run on EVERY query, `/ask` as well as `/stream`, so this was not
> confined to streaming users. Together with S1 it meant the API had
> effectively one worker thread: any query froze every other request for the
> duration of its embedding plus its rerank."*

**Why async behaved that way.** Same rule again: no `await`, no yield point, no
interruption. The rerank alone is up to 30 passes of a cross-encoder at 512
tokens each — the dominant CPU cost of a query.

**The fix**, in `grounding_service.py`:

```python
        loop = asyncio.get_running_loop()
        reranked_candidates = await loop.run_in_executor(
            None, reranker_service.rerank_results, query, unique_candidates
        )
```

and the same shape in `retrieval_service.py` for the embedding.

**The detail worth stealing**, again from the commit:

> *"`llm_service.get_embedding` already demonstrated the correct pattern — it
> was applied there and simply never applied here."*

The codebase already contained the right answer. The defect was inconsistency,
not ignorance — which is exactly the framing `integrity-auditor` recommends for
making a finding land (Chapter 04).

**And the verification, measuring the property:**

> *"Verified at runtime: with a real `/query/stream` in flight, five concurrent
> health checks returned 200 in 956-1215 ms each — the ~1s is the Supabase
> round trip, not loop starvation."*

Note the second clause. The engineer explains the residual second so the number
is not mistaken for a remaining problem. **Reporting a measurement without
explaining what it contains is how misleading conclusions get shipped.**

## K.3 Incident 3 — the wrapped constructor

The subtlest, and the most instructive.

**The problem.** In `generate_stream`, the call that *obtained* the stream was
correctly offloaded with `run_in_executor` — and the loop that *iterated* it
was not.

**The symptom.** The whole API froze for the duration of every streaming
answer, including the health check.

**The root cause**, from commit `4964ed6`:

> *"The object Gemini returns is a blocking generator whose `__next__` waits on
> the network — tens to hundreds of milliseconds per chunk, seconds in
> aggregate. So one streaming user froze the entire API worker … Wrapping only
> the constructor looks correct and is not, which is why this survived
> review."*

**Why async behaved that way.** `for chunk in stream_response:` calls
`__next__` repeatedly, and each call blocks on the network. Nothing about the
`for` statement suspends anything. The presence of `run_in_executor` three
lines above created a strong and false impression of safety.

**The fix**, which you can now read completely:

```python
        loop = asyncio.get_event_loop()
        iterator = iter(stream_response)
        exhausted = object()

        while True:
            try:
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda it=iterator: next(it, exhausted)),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "[Gemini] stream stalled — no chunk within %ss. Ending the "
                    "stream rather than hanging the request indefinitely.",
                    settings.LLM_TIMEOUT_SECONDS,
                )
                return

            if chunk is exhausted:
                break

            token = _safe_extract_text(chunk)
            if token:
                yield token
```

Line by line, using everything from Chapters 06 and 07:

- **`iter(stream_response)`** — get the iterator explicitly, so we can step it
  by hand rather than with `for`.
- **`exhausted = object()`** — a sentinel (Chapter 06). A plain unique object,
  distinguishable from every real chunk, including falsy ones.
- **`loop.run_in_executor(None, lambda it=iterator: next(it, exhausted))`** —
  one step, on a worker thread. `next(it, default)` returns the sentinel
  instead of raising `StopIteration`, because **`StopIteration` cannot cross an
  executor boundary** — inside an async generator it becomes a confusing
  `RuntimeError`.
- **`lambda it=iterator:`** — a default argument used to capture the iterator by
  value. A small, careful defence against the classic late-binding surprise in
  closures.
- **`await asyncio.wait_for(..., timeout=...)`** — per-step bound (F.3).
- **`except asyncio.TimeoutError: logger.error(...); return`** — stop the
  stream loudly. `return` inside an async generator ends it, so the consumer
  sees a clean end rather than a hang.
- **`if chunk is exhausted: break`** — identity test (Chapter 06, D.3), the
  only correct way to compare against a sentinel.
- **`yield token`** — hand one token to the endpoint's generator, which frames
  it as SSE and writes it to the socket.

**And the verification, which is the best in the repository:**

> *"Guard `tests/test_stream_does_not_block_loop.py` measures the property, not
> the source: while consuming a stream whose every chunk blocks its thread, an
> independent heartbeat coroutine must keep ticking. Observed RED on the
> reintroduced defect — 'only 0 heartbeats while consuming a stream that blocks
> 0.60s in total'. Zero, not merely fewer: the loop was completely starved,
> which is the defect stated as a number."*

## K.4 What the three have in common

| | Incident 1 | Incident 2 | Incident 3 |
|---|---|---|---|
| Blocking call | `time.sleep` | model inference | iterating a blocking generator |
| Visible in one-user testing? | no | no | no |
| Looked correct in review? | yes | yes | **especially** |
| Found by | reading | audit | audit |
| Verified by | concurrency measurement | concurrency measurement | heartbeat measurement |

**Three lessons, and they are the chapter's core:**

1. **Async defects are invisible under single-user testing**, because with one
   user there is nobody to starve. Your test fixture decides what your tests
   can see — Chapter 03's *observability of a defect*, in a new domain.
2. **The symptom appears far from the cause.** Health checks time out; the
   document list is slow; someone else's upload hangs. None of those files
   contains the bug.
3. **Only a concurrent measurement proves the fix.** Not the presence of
   `run_in_executor` — incident 3 had it and was broken.

---

# Part L — Misconceptions, Corrected Explicitly

**"async means parallel."** No. Async is concurrency on one thread: one thing
runs at a time, and waiting overlaps. Parallelism needs multiple cores and, in
Python, multiple processes.

**"`await` means sleep or pause the program."** No. It pauses *this coroutine*
and hands the CPU to others. The program as a whole gets busier, not idler.

**"async makes CPU work faster."** No. It makes waiting free. 300 ms of
computation is still 300 ms, and on the loop's thread it is 300 ms of frozen
service for everyone.

**"One request equals one thread."** No. In this repository, hundreds of
concurrent requests share one thread, each as a suspended coroutine costing a
few hundred bytes.

**"`await` starts a background thread."** No. It creates nothing. Only
`run_in_executor` / `to_thread` involve a thread, and only `create_task` /
`gather` schedule concurrent work.

**"Adding `async` to a function makes it non-blocking."** No — and this is the
most expensive one. `async def` only makes the function *capable* of
suspending. A blocking call inside it blocks exactly as much as before, and now
it blocks everyone else too. **`async def` around blocking code makes things
worse, not better**, because it moves the blocking onto the shared thread.

**"If it works on my machine with one browser tab, it works."** No. That is the
one condition under which every defect in Part K is invisible.

---

# Part M — Reading the Real Thing

Open [`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py)
at the streaming endpoint. Its shape, with everything you now know:

```python
@router.post("/stream")
@limiter.limit("30/minute")
async def stream_query(
    request: Request,
    body: QueryRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async def event_generator():
        ...
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Six things to be able to explain, which is exactly what the validation
checklist will ask:

1. **`@router.post` and `@limiter.limit`** are decorators (Chapter 06):
   registration, and a cross-cutting rate limit.
2. **`async def stream_query`** — a coroutine function. FastAPI awaits it.
3. **`Depends(get_db)`** — the async generator dependency from G.3. FastAPI
   drives it to the `yield`, hands the session in, and resumes it afterwards
   for cleanup.
4. **`async def event_generator()`** — a coroutine function defined *inside*
   another, which becomes an async generator because it contains `yield`. It
   closes over `db`, `body` and `current_user` — it can use them because they
   are in its enclosing scope (Chapter 06, F.5).
5. **`return StreamingResponse(event_generator(), ...)`** — note carefully:
   `event_generator()` is **called but not awaited**. Calling an async
   generator function creates the generator object without running any of it.
   The handler returns immediately; the response object holds the generator and
   drives it as the client reads.
6. **Every `yield` inside it** writes one SSE frame and suspends. Between
   frames, other users' requests run.

**The single most important thing to notice about that structure:** the handler
finishes long before the work does. That is why the tenant scope could not be a
`yield` dependency (G.3), why cancellation must be handled inside the
generator, and why an exception raised after the first `yield` cannot become an
HTTP error status — the status line was sent long ago. **Streaming changes the
error model**, and the code reflects that by yielding an `error` event instead:

```python
            yield f"event: error\ndata: {json.dumps({'detail': 'An internal error occurred while generating the response. Please retry.'})}\n\n"
```

---

# Part N — Exercises

Run these. Async is not learnable by reading.

### Level 0 — First contact

**N1.** Write a coroutine `hello()` that prints "hi", and call it *without*
`await`. What is printed? What warning appears? Then run it properly with
`asyncio.run`.

**N2.** Write `wait_and_print(name, seconds)` that awaits `asyncio.sleep` and
then prints. Call it twice in a row with `await`, timing the total. Explain the
total.

**N3.** Change N2 to use `asyncio.gather`. Time it again. Explain the
difference in one sentence, using the words *ready queue* and *waiting set*.

### Level 1 — Seeing the loop

**N4.** Write a `heartbeat()` coroutine that prints a dot every 0.1 s forever.
Start it as a task, then `await asyncio.sleep(1)`. Count the dots.

**N5.** Repeat N4 but replace `await asyncio.sleep(1)` with `time.sleep(1)`.
How many dots now? Explain exactly why, using C.4.

**N6.** Repeat N5 but wrap the blocking sleep in `run_in_executor`. Dots
again? Explain what changed and what did *not* change.

### Level 2 — Tasks and control

**N7.** Start three tasks with different durations using `gather`. Print the
results and note the order. Is it completion order or argument order? Why does
that matter for correctness?

**N8.** Start a task that sleeps 10 seconds. Cancel it after 1 second and catch
`CancelledError`. Now try to cancel a task that is doing a 10-second pure
computation instead. What happens, and why?

**N9.** Wrap a coroutine that sleeps 5 seconds in `asyncio.wait_for` with a
2-second timeout. Catch the error. Then explain when a whole-operation timeout
is wrong and what to use instead.

### Level 3 — Real shapes

**N10.** Write an async generator `countdown(n)` that yields `n, n-1, …, 1`
with a 0.2 s wait between values, and consume it with `async for`. Explain
where the coroutine is suspended each time.

**N11.** Write an async context manager (using `@contextlib.asynccontextmanager`)
that prints "open", yields a value, and prints "close" — then use it in a block
that raises an exception. Confirm "close" still prints, and say which
repository pattern this matches.

**N12.** Write a bounded fetcher: given 20 fake "urls", fetch them with at most
3 concurrent, using a `Semaphore` and `gather`. Time it and explain the total.

### Level 4 — Repository-shaped

**N13.** Write a `pump(iterator)` async generator that steps a *blocking*
iterator through `run_in_executor`, one item at a time, with a per-step
timeout, using a sentinel for exhaustion. Test it with an iterator whose
`__next__` calls `time.sleep(0.2)` while a heartbeat runs, and confirm the
heartbeat keeps ticking.

**N14.** Take this and say what is wrong, what the symptom would be, and how
you would prove it:

```python
async def get_summary(doc_id):
    text = requests.get(f"http://internal/doc/{doc_id}").text
    return summarise(text)
```

**N15.** Write the *test* that proves the fix for N14 works — not by inspecting
the source, but by measuring the property. State exactly what number you would
assert and what it would be if the defect returned.

---

# Part O — Answer Key

**O1.** Calling it prints nothing and produces a coroutine object; Python emits
`RuntimeWarning: coroutine 'hello' was never awaited`. The body never ran. Treat
that warning as an error — it means part of your program silently did not
happen.

**O2.** About 2 seconds. `await` is sequential: it means "suspend me until this
finishes". It creates an opportunity for *other* work to run, but you did not
give it any.

**O3.** About 1 second. `gather` schedules both as tasks, so both are in the
ready queue. The first runs until its `await asyncio.sleep`, moves to the
waiting set, and the second runs immediately instead of the loop idling. Both
timers expire at about the same moment and both return to the ready queue.

**O4.** About 10 dots. The heartbeat and the sleep are both suspended most of
the time, so the loop alternates between them freely.

**O5.** One dot at most — usually zero. `time.sleep` blocks the thread that
runs the loop. Cooperative scheduling means the loop cannot take control back;
it only regains control when a coroutine reaches an `await`, and a blocked
thread never reaches one. **This is Incident 1 reproduced in five lines.**

**O6.** About 10 dots again. The blocking sleep now happens on a worker thread,
so the loop's thread stays free to run the heartbeat. What did *not* change:
the sleep still takes one full second, and it still occupies a thread. You moved
the blocking; you did not remove it. That distinction is the whole of H.2.

**O7.** `gather` returns results in **argument order**, regardless of which
finished first. This matters because code that assumed completion order would
silently mismatch results with their inputs — a data-correctness bug with no
error message.

**O8.** The first cancels cleanly, because `asyncio.sleep` is a suspension
point and the cancellation is delivered there. The second does not cancel until
the computation finishes, because cancellation can only be delivered at an
`await` and pure computation has none. **Cooperative scheduling implies
cooperative cancellation** — the same property, seen from the other side.

**O9.** `asyncio.TimeoutError` after 2 seconds. A whole-operation timeout is
wrong when the operation is legitimately long but progressive — a stream, a
large download, a paginated read. Any single value is either too low (killing
healthy work) or too high (not protecting). Bound each *step* instead, which is
what `generate_stream` does.

**O10.** The coroutine is suspended at the `await asyncio.sleep(0.2)` inside
the generator, between yields. The consumer's `async for` is itself suspended
while waiting for the next value. Both are off the loop, so other work runs.

**O11.** "close" still prints, because the cleanup is in the `finally` of the
generator that `@asynccontextmanager` wraps. This matches `get_db` in
`db/session.py` and `tenant_scope` in `core/tenant_scope.py` — set up, hand
over, guarantee teardown regardless of how the block ends.

**O12.** About 7 batches' worth of time — with 20 items, 3 at a time, and each
taking the same time, the total is roughly `ceil(20/3)` times one fetch. The
semaphore converts unbounded concurrency into a controlled queue. Without it
you would issue 20 simultaneous requests and, against a real service, likely
receive rate-limit errors instead of speed.

**O13.** The shape to produce:

```python
import asyncio

_EXHAUSTED = object()

async def pump(iterator, step_timeout=5.0):
    loop = asyncio.get_running_loop()
    while True:
        item = await asyncio.wait_for(
            loop.run_in_executor(None, lambda it=iterator: next(it, _EXHAUSTED)),
            timeout=step_timeout,
        )
        if item is _EXHAUSTED:
            return
        yield item
```

Three decisions being tested: a unique sentinel rather than `None` (a real item
could be falsy); `next(it, default)` rather than catching `StopIteration`
(which cannot cross an executor boundary); and a per-step timeout rather than a
whole-stream one. This is `generate_stream`, minus the provider details.

**O14.** `requests.get` is a blocking HTTP call inside a coroutine. It parks the
event loop's thread for the entire round trip, so every other request on that
process — including health checks — freezes for the same duration.

The symptom is the giveaway: unrelated endpoints slow down together, and the
worse the internal service's latency, the worse everything else gets. `summarise`
may be blocking too, in which case it needs `run_in_executor` as well.

To prove it: run a heartbeat coroutine while calling `get_summary`, and observe
the ticks stop. To fix it: use an async HTTP client (`httpx.AsyncClient`) with
`await`, or `await asyncio.to_thread(requests.get, ...)` if the sync library
must be kept.

**O15.** The test:

```python
async def test_get_summary_does_not_block_loop(monkeypatch):
    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    hb = asyncio.create_task(heartbeat())
    await get_summary("doc-1")          # stand-in blocks ~0.5s
    hb.cancel()

    assert ticks >= 20, f"only {ticks} heartbeats while fetching a summary"
```

Assert on **heartbeat count**, not on elapsed time and not on the presence of
`await` in the source. With a 0.5-second stand-in and a 10 ms heartbeat, a
healthy loop produces roughly 50 ticks; the broken version produces **zero**,
because the loop never runs. Zero versus fifty is the defect stated as a
number — which is precisely how this repository's real guard is written, and
why it could not be fooled by code that merely *looked* offloaded.

---

# Part P — Senior Critique: The Async in This Repository

### Strengths

1. **The blocking-call class is closed with property-based guards**, not with
   source inspection. Three separate tests measure loop freedom with a
   heartbeat or with concurrency timing, and each was observed red.
2. **Per-step timeouts on the stream**, with the reasoning written next to the
   code. Most codebases have either no timeout or a wrong one.
3. **The sync/async boundary is an explicit invariant** — async request path,
   sync workers, never mixed — rather than an accident.
4. **The lock choice matches the real interleaving surface**: a `threading.Lock`
   for state reachable from executor threads and the sync worker, not an
   `asyncio.Lock` that would protect against the wrong thing.
5. **Coroutine lifetimes were reasoned about correctly** in the one place it is
   genuinely subtle: the tenant scope is not a `yield` dependency, because the
   streaming generator outlives the dependency.

### Weaknesses

1. **Fire-and-forget executor calls have no failure observation.** The
   lifecycle-email calls are started and never awaited or callback-attached, so
   a failure disappears. In a codebase whose central rule is loud degradation,
   this is the one place a failure is structurally silent.
2. **No bound on executor concurrency.** Every CPU-heavy call uses the default
   thread pool. Under load, embedding and reranking work can saturate it, and
   the *pool* becomes the queue — invisibly. A dedicated, sized executor for
   model work would make that capacity explicit and prevent model work from
   starving other executor users.
3. **`asyncio.get_event_loop()` is used in places where
   `get_running_loop()` is correct.** The former is deprecated in modern Python
   and has subtle behaviour when no loop is running; the codebase already uses
   the correct form in `retrieval_service` and `grounding_service`, so this is
   an inconsistency rather than a knowledge gap.
4. **No `TaskGroup` adoption**, so concurrent work is managed with `gather`
   and bare executor calls. Structured concurrency would make task lifetimes
   visible and would have prevented weakness 1 by construction.
5. **No semaphore in front of the LLM provider.** Rate limiting is handled by
   key rotation after the fact rather than by bounding concurrency before it —
   which means the system discovers the limit by being refused rather than by
   respecting it.

### The one improvement I would make first

**A dedicated, size-bounded executor for model inference.** It converts an
invisible shared resource into an explicit one, stops embedding and reranking
work from starving every other `run_in_executor` caller, and gives a single
place to measure and tune the CPU-bound side of the request path. It is perhaps
fifteen lines, and it addresses the one part of the async design that is
currently unbounded.

---

# Part Q — Interview Questions With Model Answers

**Q1. "Explain async/await to someone who has never used it."**

> Most of the time a web request spends is waiting — for a database, for an
> API. In our query path about 86% of the time is waiting. With ordinary
> blocking code, the thread handling one request sits idle during that wait and
> cannot serve anyone else, so you need a thread per concurrent request and
> each costs memory.
>
> Async lets a function pause itself at a waiting point and hand control back
> to a scheduler called the event loop, which runs something else and comes
> back when the data arrives. `await` is the pause. There is still one thread
> and one thing running at a time — nothing is parallel — but the waiting
> overlaps, which is where the throughput comes from.
>
> The catch is that it is cooperative: the loop can only regain control when
> code reaches an `await`. Any blocking call inside a coroutine freezes
> everyone.

**Q2. "What is the difference between concurrency and parallelism?"**

> Concurrency is dealing with many things by interleaving them; parallelism is
> doing many things at the same instant, which needs multiple cores. Async
> gives concurrency on a single thread.
>
> The distinction is practical here because our query path has both kinds of
> work. About two seconds of it is waiting on the database and the model
> provider — that is what async handles. About 350 milliseconds is genuine
> computation, the embedding and the cross-encoder rerank, and async does
> nothing for that. Those go to a thread pool, which frees the loop, and they
> genuinely run in parallel because the underlying libraries release the GIL
> while computing in C.

**Q3. "You have an async service that becomes slow under load. How do you
diagnose it?"**

> First by the shape of the symptom. If *unrelated* endpoints slow down
> together — a health check that only pings, for instance — the cause is
> something shared rather than the slow feature's own logic. That single
> observation eliminates most candidates.
>
> Then I measure the property rather than reading code: run a heartbeat
> coroutine that ticks every 10 milliseconds and see whether it keeps ticking
> while the suspect work runs. If ticks stop, the loop is blocked.
>
> I would not trust reading for this. We had a case where `run_in_executor` was
> present in the function and wrapped the wrong operation — the call that
> obtained a stream was offloaded, the iteration that did the network I/O was
> not. A source-level check would have passed. The heartbeat test recorded zero
> ticks over 0.6 seconds.

**Q4. "When would you not use async?"**

> When the work is CPU-bound, because async only makes waiting productive.
> Pure computation on the event loop freezes every other request, which is a
> worse outcome than not using async at all.
>
> When the work takes minutes and must survive a restart — document processing
> in our case — because a coroutine dies with the process and leaves no record.
> That belongs on a durable queue with a separate worker.
>
> And when there is nothing to overlap. A script that does one thing gains
> nothing from an event loop and pays for the machinery. Our Celery workers are
> deliberately fully synchronous, with a synchronous database driver, because
> half-async code is where the hardest bugs live.

**Q5. "Do you need locks in single-threaded async code?"**

> Yes, whenever state is read and written across an `await`. Every `await` is
> an interleaving point: between suspending and resuming, other coroutines run
> and can modify the same data, so you can have a read-modify-write race with
> only one thread.
>
> The advantage over threads is that the danger is *visible* — the interleaving
> points are exactly the awaits, so you can find them by looking, rather than a
> switch being possible between any two instructions.
>
> And you have to pick the right kind of lock. Our key rotator uses a
> `threading.Lock`, not an `asyncio.Lock`, because its state is reachable from
> executor threads and from the synchronous Celery worker as well as from the
> event loop. An async lock there would protect against the wrong thing.

---

# Part R — Validation Checklist

- [ ] I can state what fraction of a request in this system is waiting, and why
      that number is the argument for async. *(A.4)*
- [ ] I can explain the event loop with an analogy **and** with the ready
      queue / waiting set mechanism. *(C.1, C.2)*
- [ ] I can say exactly what `await` does — the two things — and three things
      it does not do. *(C.3, L)*
- [ ] I can explain cooperative scheduling and why it makes one blocking call
      catastrophic. *(C.4)*
- [ ] I can explain why `await a(); await b()` is sequential and how to make it
      concurrent. *(D.4, E.3)*
- [ ] I can explain why cancellation cannot interrupt pure computation. *(F.2)*
- [ ] I can explain why the tenant scope is not a `yield` dependency. *(G.3)*
- [ ] I can choose correctly between `await`, a thread pool, a process pool and
      a job queue, and justify it. *(H.5)*
- [ ] I can explain why locks are still needed with one thread. *(J.1)*
- [ ] I can retell all three incidents: the blocking call, why it was invisible
      in testing, and how the fix was measured. *(K)*
- [ ] I completed N5, N6, N13 and N15 by running them.
- [ ] **The real test:** open
      [`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py)
      or [`backend/app/db/session.py`](../backend/app/db/session.py) and
      explain, for every `async def`, every `await`, every `async with`, every
      `yield` and every `run_in_executor`: what suspends, what continues
      running, who resumes it, and what would break if it were removed.

If the last box is ticked, you understand the concurrency model that FastAPI,
SQLAlchemy's async engine, the streaming path and the Celery boundary all
depend on — and Chapter 14 can be about the framework rather than about the
event loop.

---

*Next: [08-javascript-from-zero.md](08-javascript-from-zero.md) — the other
language in this system, taught from zero, with its own event loop that you
will recognise immediately.*
