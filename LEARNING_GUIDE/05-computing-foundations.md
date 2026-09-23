# 05 — Computing From First Principles

**Prerequisites: none.** This is the first chapter of Part 1, and it is the
only chapter in the course that assumes nothing at all. If you have never
written a line of code, never opened a terminal, and are not sure what a
"process" is, you are exactly the reader this was written for.

Chapters 01–04 described a system, its design, the reasoning behind it, and
how it was built. Those chapters used words like *port*, *process*,
*environment variable*, *HTTP*, *TLS* and *JSON* as if you already knew them.
This chapter is where you actually learn them, properly, from the bottom.

**Why this chapter matters more than any other.** Everything after this —
Python, FastAPI, PostgreSQL, Docker, React — is built on the ideas here. A
student who is shaky on "what is a process" will be permanently confused by
Celery workers. A student who does not really understand ports will lose days
to a Docker networking problem. The most common reason a beginner plateaus is
not that the advanced material is hard. It is that the foundation has a hole
in it, and every new topic falls through.

So we take our time. This chapter is long on purpose.

**How to read it.** Slowly, in order, in one or two sittings per part. There
are exercises at the end that begin with things like "type one word into a
terminal". Do them. Reading about a terminal is not the same as having used
one.

---

# Part A — The Machine

## A.1 What is a computer?

**A computer is a machine that follows instructions, very fast, without
understanding them.**

That last part matters. A computer has no idea what it is doing. It performs
extremely simple operations — add two numbers, compare two numbers, copy this
value from here to there — billions of times per second. Every application you
have ever used, from a calculator to a video call to the system in this
repository, is built from those simple operations arranged in an order.

**Why does this framing matter?** Because it removes the magic. When something
in your program behaves strangely, the machine did not "get confused". It
followed your instructions exactly. The instructions were wrong, or they were
not the instructions you thought you wrote. Debugging is the process of
finding the difference between what you meant and what you said.

### The four things a computer has

Every computer, from a phone to a cloud server, has four parts that matter to
us:

1. **A processor (CPU)** — the part that follows instructions.
2. **Memory (RAM)** — a fast workspace that forgets everything when power is
   lost.
3. **Storage (disk)** — a slow warehouse that remembers after power is lost.
4. **Input and output** — keyboard, screen, network card.

Almost every performance problem you will ever debug comes from the
relationship between numbers 1, 2 and 3. Hold that thought; we return to it in
A.7.

## A.2 Hardware versus software

**Hardware** is the physical machine: metal, silicon, plastic. You can drop
it.

**Software** is instructions and data. You cannot drop it. It is a pattern —
a very long list of numbers — that tells the hardware what to do.

**Why the distinction exists.** The first computers were rewired physically to
change what they did. Changing the task took days of moving cables. The
crucial invention, around 1945, was the **stored-program computer**: the idea
that the instructions could live in memory alongside the data, as numbers.

**What that bought us.** If instructions are just numbers in memory, then a
program can be loaded, replaced, copied, sent over a network, and even written
by another program. Every single thing in this course depends on that one
idea. Installing an application is copying numbers. Deploying this repository
to a server is copying numbers. An AI model "generating code" is producing
numbers that are instructions.

**What happens if it disappears?** You would need a different machine for
every task. There would be no software industry, because there would be no
software.

## A.3 Binary — why everything is ones and zeros

**What it is.** Computers store and move information using only two symbols,
usually written `0` and `1`. One such symbol is called a **bit**.

**Why only two?** Because a physical thing that must reliably represent a
value is far easier to build with two states than with ten. A wire is either
carrying voltage or not. A tiny switch is on or off. Two states can be
distinguished even when the signal is noisy. Ten states cannot, not cheaply
and not reliably. **Binary is not a mathematical preference; it is an
engineering compromise with physics.**

**How counting works.** In the decimal numbers you already know, each position
is worth ten times the one to its right: 1, 10, 100, 1000. In binary, each
position is worth two times the one to its right: 1, 2, 4, 8, 16.

So the binary number `1011` means:

```
1 × 8  = 8
0 × 4  = 0
1 × 2  = 2
1 × 1  = 1
         --
         11
```

`1011` in binary is 11 in decimal. That is the whole system.

**The byte.** Eight bits grouped together is a **byte**. A byte can hold 256
different values (2 multiplied by itself 8 times). Almost everything is
measured in bytes:

| Name | Size | A useful mental picture |
|---|---|---|
| 1 byte | 1 character of English text | the letter `A` |
| 1 kilobyte (KB) | 1,000 bytes | a short paragraph |
| 1 megabyte (MB) | 1,000 KB | a large book, or one photo |
| 1 gigabyte (GB) | 1,000 MB | a long film |
| 1 terabyte (TB) | 1,000 GB | a large hard drive |

**How this connects to the repository.** In Chapter 02 we calculated that one
embedding — the list of 1024 numbers representing a chunk's meaning — takes
**4 KB**, because each number takes 4 bytes and 1024 × 4 = 4096. That
calculation is only possible because you know what a byte is. From it came a
real architectural decision: all the vectors fit in one PostgreSQL database,
so no separate vector database is needed (decision D-012).

**What beginners get wrong.** They treat sizes as abstract labels rather than
as quantities they can compute with. **Senior engineers do arithmetic with
bytes constantly**, because the answer usually decides the design.

## A.4 The CPU — the part that follows instructions

**What it is.** The **CPU** (central processing unit) is the component that
actually executes instructions.

**How it works internally.** It repeats one cycle, forever, until powered off:

1. **Fetch** — read the next instruction from memory.
2. **Decode** — work out which operation it is.
3. **Execute** — do it (add, compare, copy, jump elsewhere).
4. Repeat.

That is it. A modern CPU does this a few billion times per second and uses
elaborate tricks to overlap the steps, but the model above is honest.

**Cores.** A modern CPU contains several independent copies of this machinery,
called **cores**. A four-core CPU can genuinely execute four instructions at
the same instant. This is the physical basis of **parallelism** — actually
doing two things simultaneously — which we will distinguish carefully from
**concurrency** in Chapter 07.

**Where this appears in this repository.** In
[`infrastructure/docker-compose.yml`](../infrastructure/docker-compose.yml),
the background worker is started with `--concurrency=2`. That number says how
many worker child processes run at once. The comment in that file explains why
it is written explicitly rather than left to a default:

> *"Celery's prefork default is `os.cpu_count()` (8 on this host), and each
> child owns its own SQLAlchemy pool — so the worker's share of the database
> connection budget silently changed with whatever machine it ran on."*

Read that carefully, because it is a perfect illustration of why hardware
knowledge matters. A default that depends on **how many CPU cores the machine
happens to have** made a *database* setting change when the code moved to a
different computer. Understanding the machine explains the bug.

## A.5 Memory (RAM) — the fast, forgetful workspace

**What it is.** **RAM** (random access memory) is where a running program
keeps everything it is currently working with.

**Why it exists.** The CPU is extremely fast; storage is extremely slow. If
the CPU had to fetch every instruction and every piece of data from a disk, it
would spend nearly all its time waiting. RAM sits between them: much faster
than disk, much smaller, and much more expensive per byte.

**"Random access"** means you can read any location directly, at the same
cost, without reading everything before it. That is the opposite of a cassette
tape, where reaching the middle means winding through the beginning.

**The crucial property: RAM forgets.** When a program stops — or the machine
loses power — everything in RAM is gone. This single fact drives an enormous
amount of system design. It is *why* databases exist, why files exist, and why
Chapter 02's rule "the database stores facts, storage stores files" matters.

**How much a program uses.** Every value your program holds occupies memory. A
machine-learning model is an enormous grid of numbers — the embedding model
used here holds hundreds of millions of them — so loading it can take
hundreds of megabytes or several gigabytes.

**Where this appears in this repository.** Two places, and both are memory
decisions in disguise:

1. `worker_max_tasks_per_child=50` in
   [`backend/app/workers/celery_app.py`](../backend/app/workers/celery_app.py).
   After 50 jobs, the worker process is thrown away and a fresh one started.
   The compose file explains the trade honestly: *"it costs a 65.7s bge-m3
   reload every 50 tasks. That is a real cost, but the recycle also bounds
   memory growth from the ML models."*

   Why would memory grow? Because a long-running process that repeatedly loads
   large data can accumulate memory it never releases — a **memory leak** —
   and eventually the operating system kills it. Restarting the process
   periodically is a blunt but reliable cure: **you cannot leak memory across a
   process you no longer have.**

2. `MAX_UPLOAD_MB: int = 200` in
   [`backend/app/core/config.py`](../backend/app/core/config.py). An upload
   limit is partly a memory limit: processing a very large file can require
   holding large parts of it in RAM.

**What beginners get wrong.** Assuming memory is free and infinite. **Senior
engineers ask "how many of these will exist at once, and how big is each?"**
before choosing a data structure.

## A.6 Storage — the slow, permanent warehouse

**What it is.** A disk (today usually an **SSD**, solid-state drive) keeps
data after the power goes off.

**Why it exists.** Because RAM forgets, and because RAM is expensive. A
machine might have 16 GB of RAM and 1,000 GB of disk.

**The trade.** Disk is roughly a hundred to a thousand times slower than RAM
for the operations we care about, and far slower still if it is a spinning
mechanical drive.

**Where this appears in this repository.** The default storage setting is
`STORAGE_PROVIDER: str = "local"` — uploaded files are written to the server's
own disk. But look at the compose file: the backend service mounts a **volume**
at `/tmp/documind_storage`.

A **volume** is storage that lives outside the container and survives the
container being destroyed. This exists because of a property we meet in
Chapter 20: a container's own filesystem is temporary. Files written inside a
container vanish when it is replaced. That is why production uses S3 (decision
D-018) — **not because S3 is fancier, but because the container's disk is a
lie about permanence.**

## A.7 The memory hierarchy — the single most useful table in computing

Put the three storage layers next to each other with real numbers. Approximate
values, correct in their *ratios*, which is what matters:

| Where | Time to read something | If one CPU cycle were 1 second… |
|---|---|---|
| CPU register | ~0.3 nanoseconds | 1 second |
| CPU cache | ~1–10 nanoseconds | 3–30 seconds |
| RAM | ~100 nanoseconds | 5 minutes |
| SSD | ~100 microseconds | 4 days |
| Network, same datacentre | ~500 microseconds | 3 weeks |
| Network, across the internet | ~50 milliseconds | 5 years |
| An LLM call | ~2 seconds | 200 years |

**Read that last column again.** These are not small differences. They are
differences of the kind that separate a second from a decade.

**Everything in performance engineering follows from this table.** When
Chapter 02 said "the LLM dominates; optimising a 20 ms database query next to
a 4-second model call is wasted effort", that is this table talking. When
Chapter 01 said "caching retrieval results for 300 seconds makes repeated
questions cheap", that is moving work from the slow rows to the fast rows.

**The rule to memorise:** *make the slow thing happen less often.* Almost
every optimisation you will ever perform is an instance of that sentence.

## A.8 A short exercise before moving on

Do not skip this; it is thirty seconds and it makes the abstract concrete.

Look at any file on your computer and note its size in bytes. Now compute: how
many 1024-dimension embeddings (4 KB each) would fit in it? If a 100-page
document produces about 200 chunks, how many documents is that?

You have just done capacity planning. That is the same calculation, at the
same level of rigour, that produced decision D-012.

---

# Part B — Files, Folders, and Text

## B.1 What is a file?

**What it is.** A **file** is a named sequence of bytes stored on a disk.

That is the entire definition, and it is more useful than it sounds. A file is
not "a document" or "a picture". It is a run of numbers with a name. What
those numbers *mean* is decided entirely by the program reading them.

**Why files exist.** Because RAM forgets (A.5), we need a way to keep bytes
after a program ends and to find them again later. A file is that: bytes, plus
a name to find them by.

**What existed before.** Early machines addressed storage by physical
position — "the data starting at track 4, sector 17". That works until someone
moves it. Naming decouples *what you want* from *where it is*, which is the
same idea as a variable name, a DNS name (Part G), and a function name. **The
pattern "give it a name so you can stop caring where it is" is one of the most
reused ideas in all of computing.**

## B.2 Text, bytes, and encoding — a source of real bugs

Here is a question that sounds trivial and is not: if a file is a sequence of
bytes, and a byte is a number from 0 to 255, how do you store the letter `A`?

**Answer: you agree on a code.** Someone decides that the number 65 means `A`.
That agreement is called a **character encoding**.

**The history, briefly, because it explains today's bugs.** The first widely
used agreement was **ASCII** (1963): 128 codes covering English letters,
digits and punctuation. That was sufficient for American English and for
nothing else. Every other language then got its own incompatible extension,
so a file written in one country was unreadable in another.

The fix was **Unicode**: one enormous table giving every character in every
human writing system its own number — Latin, Devanagari, Chinese, emoji,
mathematical symbols. Over a million slots.

But Unicode is only a table of numbers. You still need a rule for turning
those numbers into bytes, and that rule is called an **encoding**. The one
that won is **UTF-8**, which is clever in a specific way: characters that
existed in ASCII take exactly one byte with exactly their old value, and
everything else takes two to four bytes. So every old English text file is
already valid UTF-8, and nothing had to be converted.

**Where this bites in this repository — a real defect.** From the
`integrity-auditor` agent's list of known failure patterns:

> *"Encoding and locale assumptions. Run the real path with real data. `fpdf`
> core fonts are latin-1; `⚠`, `₹`, `…` and every Devanagari script raise —
> and the code emits `⚠` itself."*

Unpack that. The PDF export library, using its built-in fonts, can only encode
**latin-1** — an old 256-character encoding with no rupee sign, no warning
triangle, no Hindi. Meanwhile the application generates warning messages
containing `⚠` and serves users in India where `₹` is routine. So the export
crashes on exactly the content it was most likely to receive.

**Three lessons, and they generalise far beyond PDFs:**

1. **Encoding is not a detail; it is a contract between writer and reader.**
2. **Test with real data, not English test data.** The bug is invisible with
   the word "hello".
3. **Your own program's output is input to something else.** The code emitted
   a character its own export path could not handle.

**What beginners get wrong.** Believing text "just works". **Senior engineers
know that text is bytes plus an agreement**, and that the agreement is often
implicit and often wrong.

## B.3 Folders and paths

**What a folder is.** A **folder** (or directory) is a file that contains a
list of other files and folders. That is all a folder is: a list.

**Why folders exist.** With a hundred files, one flat list is workable. With a
hundred thousand, it is not. Folders let names be reused in different contexts
— two files can both be called `config.py` as long as they are in different
folders.

**What a path is.** A **path** is the route to a file, written as folder names
separated by a separator character.

- On Linux and macOS: `/home/student/project/main.py` — the separator is `/`.
- On Windows: `C:\Users\student\project\main.py` — the separator is `\`.

**Absolute versus relative.** An **absolute path** starts from the very top of
the filesystem and is unambiguous everywhere. A **relative path** starts from
wherever the program currently is — its **working directory** — and means
different things depending on where you are standing.

Two special names appear in every relative path system:
- `.` means "here"
- `..` means "the folder above"

**Where this appears in this repository — and a real constraint.** From the
top of
[`infrastructure/Dockerfile.backend`](../infrastructure/Dockerfile.backend):

> *"BUILD CONTEXT: the repository ROOT (not backend/) … Docker forbids
> `COPY ../` — a COPY source can never escape the build context — so every
> path below is repo-root-relative."*

That is a rule about relative paths with a security purpose: a build must not
be able to reach outside the folder it was given, or a build file could copy
anything from your machine into an image. Understanding `..` explains the rule
instantly.

**The Windows/Linux split is a real cost in this project.** Development
happens on Windows, deployment on Linux. That is why the test commands say
`./venv/Scripts/python.exe` (a Windows layout) while the same virtual
environment on Linux would be `./venv/bin/python`. Same tool, different path,
because two operating systems chose different conventions decades ago.

## B.4 File extensions are a convention, not a rule

The `.py` at the end of `main.py` is part of the name. The operating system
does not enforce that a `.py` file contains Python. Renaming a photograph to
`.py` does not make it a program.

**Why the convention exists anyway:** so humans and tools can guess a file's
purpose without opening it. Guessing is useful and fallible — which is exactly
why the web sends a separate, explicit statement of a file's type (Part H) and
why this repository's security headers include `X-Content-Type-Options:
nosniff`, meaning *"do not guess the type, believe what I told you"*. Guessing
file types has caused real security incidents, which is what that header
prevents.

## B.5 The repository as a tree of folders

Everything you have read about in Chapters 01–04 lives in a folder structure.
Now you can read it as what it is: a tree of named byte-sequences.

```
isolated_project/
├── backend/            Python application
│   ├── app/            the code
│   ├── tests/          tests
│   ├── requirements.txt   list of libraries needed
│   └── .env            secrets — NOT in version control
├── frontend/           browser application
├── infrastructure/     Docker and compose files
├── docs/               documentation
├── CLAUDE.md           the engineering handbook
└── .gitignore          list of things never to store in version control
```

One entry deserves attention now: **`.gitignore`**. Files starting with a dot
are hidden by convention on Linux and macOS. This one lists things that must
never be stored in version control, and the first section is dependencies, the
second is secrets:

```
# ── Environment & Secrets ────────────────────────────────────────────────────
.env
.env.local
.env.production
```

We will understand version control fully in Part M. For now, note the shape of
the decision: **some files must exist on the machine and must never leave it.**

---

# Part C — Programs, Processes, and Threads

This part contains the single most important distinction in the chapter. If
you take one thing from Chapter 05, take C.2.

## C.1 What is a program?

**A program is a file containing instructions.** It sits on disk doing
nothing, like a recipe in a closed book.

## C.2 What is a process?

**A process is a running program.**

The recipe is the program. The actual cooking — with a real kitchen, real
ingredients, a specific point you have reached in the steps — is the process.

**Why the distinction is the important one.** One program can be running many
times at once, and each run is separate. Your browser might be one program
running as eight processes. In this repository, the *same* backend program
runs as three different processes with different jobs.

**What a process actually consists of:**

- **Its own memory space.** Every process gets a region of RAM that other
  processes cannot read or write. This is enforced by the hardware and the
  operating system.
- **A program counter** — where it has reached in the instructions.
- **Open files and network connections.**
- **A process id (PID)** — a number identifying it while it runs.
- **An exit code** — a number it reports when it finishes. By universal
  convention, `0` means success and anything else means failure.

**Why memory isolation exists — and it is the reason computers are usable at
all.** Without it, any program could read your password out of another
program's memory, and any bug in any program could corrupt every other
program. Isolation means a crash is *contained*: one process dies, the rest
continue.

**How processes talk to each other.** Since they cannot share memory, they need
other mechanisms: files on disk, network connections, or a message broker like
Redis. **This is exactly why the queue in Chapter 01 exists.** The web process
cannot simply hand a Python object to the worker process — they have separate
memory. It must serialise the job into bytes and send it somewhere both can
reach.

Now Chapter 02's decision D-007 reads differently, doesn't it? "Put a job on a
queue" is not a fashion. It is the consequence of process isolation.

**Where this appears in this repository.** Three processes, from the compose
file, all running the same codebase:

| Process | Command | Job |
|---|---|---|
| `backend` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | answer web requests |
| `worker` | `celery -A app.workers.celery_app worker -Q main-queue,… --concurrency=2` | do slow jobs |
| `beat` | `celery -A app.workers.celery_app beat --schedule=/tmp/celerybeat-schedule` | start scheduled jobs on time |

And the warning in that file about `beat`:

> *"Run EXACTLY ONE Beat instance — a second one duplicates every scheduled
> task (double emails)."*

That is process thinking. Two copies of a **stateless** process are harmless
and useful (Chapter 02). Two copies of a process that *holds a schedule* are a
bug that emails your users twice.

**What happens if process isolation disappeared?** Every program could corrupt
every other. Multi-user servers would be impossible. Multi-tenancy — the
entire premise of this product — would have no foundation to sit on.

## C.3 What is a thread?

**A thread is one sequence of execution inside a process.**

A process starts with one thread. It can create more. All threads in a process
**share the same memory**, which is what makes them different from processes.

**Why threads exist.** Creating a process is expensive; creating a thread is
cheap. And sometimes you *want* shared memory — several threads working on the
same large data structure without copying it.

**Why threads are dangerous.** Shared memory means two threads can modify the
same value at the same time and corrupt it. That is a **race condition**
(Chapter 03), and race conditions are notoriously hard to reproduce because
they depend on timing.

**The trade, stated once so you can carry it everywhere:**

| | Processes | Threads |
|---|---|---|
| Memory | separate | shared |
| Crash affects | itself only | the whole process |
| Cost to create | high | low |
| Communication | must serialise through a queue/file/socket | direct, and dangerous |

**Where this appears in this repository.** In Chapter 01 you saw
`run_in_executor`, which moves a slow calculation onto a **thread** so the main
one stays free. That is threads used correctly: the work is self-contained,
and the shared memory is what makes it cheap (no copying the model).

And a fork-related bug is documented in
[`backend/app/db/session.py`](../backend/app/db/session.py) that only makes
sense once you know processes:

> *"Inherited pooled connections are shared TCP sockets. Two processes writing
> to one socket corrupts the protocol stream."*

Here is the sequence, in plain language. The worker's parent process opened
database connections. It then created child processes by **forking** —
copying itself. The children inherited copies of the parent's open network
connections. But a network connection is not really copyable: both processes
now believe they own the same channel, and when both write, their messages
interleave into nonsense. The symptom looked like a database fault. The cause
was a process-creation fault. **Symptoms surface far from causes** — Chapter
03's lesson, appearing here at the operating-system level.

## C.4 Concurrency versus parallelism (the short version)

Two words that sound the same and are not. Chapter 07 does this in depth; you
need the distinction now.

- **Concurrency** is *dealing with* many things at once. One cook, four pots:
  stir one, check another, return to the first. Nothing happens
  simultaneously — but everything progresses.
- **Parallelism** is *doing* many things at once. Four cooks, four pots.
  Genuinely simultaneous, and it requires multiple CPU cores.

**Why you need both words.** The backend serves many users concurrently with
very few threads, because most of what a request does is *wait* — for the
database, for the AI provider. Waiting is not work. A single cook can watch a
hundred pots as long as the pots do the boiling.

**And the failure this makes visible.** Chapter 03's event-loop bug was code
that *worked* instead of *waiting*, on the thread that everyone shares. One
cook chopping vegetables for four seconds is one hundred pots boiling over.

## C.5 Exit codes, signals, and restarts

**Exit code.** A finished process reports a number. `0` = success. Everything
else = failure. This convention is what allows one program to check whether
another succeeded, and it is why the shell in Part E cares about it.

**Signal.** A message the operating system sends to a running process — most
commonly "please stop" (which a well-written program handles by finishing its
current work) or "stop now" (which cannot be caught or refused).

**Why this matters for real systems.** When your container platform deploys a
new version, it sends "please stop" to the old process. If your program
ignores it, in-flight requests are cut off mid-answer — which for this
repository means a user's streaming answer stops mid-sentence. **Graceful
shutdown is a feature you have to write; it is not free.**

---

# Part D — The Operating System

## D.1 What an operating system does

**What it is.** The **operating system** (OS) is a program that manages the
machine and runs your programs for you. Windows, macOS, Linux and Android are
operating systems.

**Why it exists.** Without one, every program would have to contain its own
code for talking to the disk, the network card, the keyboard, and every model
of each. And nothing would stop two programs from using the same memory. The
OS exists so that programs can be written against **one consistent set of
services** instead of against hardware.

**Its four main jobs:**

1. **Scheduling** — deciding which process gets the CPU next, and switching
   between them thousands of times per second so everything appears to run at
   once. (This is *concurrency*, implemented by the OS.)
2. **Memory management** — giving each process its own isolated space.
3. **Filesystem** — turning "a named file in a folder" into actual disk
   operations.
4. **Device access** — one uniform way to use the network card, the screen,
   the keyboard.

**What existed before.** Programs ran one at a time and did everything
themselves. Multi-user, multi-program machines were impossible. Every one of
the "isolation" properties this course depends on came from operating systems.

## D.2 Kernel and user space

The OS is split in two:

- The **kernel** is the core, with full hardware access.
- **User space** is where your programs run, with no direct hardware access.

**Why the split.** So that a bug in your program cannot destroy the machine.
When your program wants something privileged — read a file, send a network
packet — it makes a **system call**: a formal request to the kernel. The
kernel checks permissions and does it on your behalf.

**This is the same design pattern as everything else in this course.** The
tenancy hook in Chapter 03: application code cannot query without going
through a checkpoint. Agent tool grants in Chapter 04: a component asks for a
capability rather than having it. **Mediated access through a checking layer
is a universal pattern**, and the kernel is its oldest large-scale example.

## D.3 Linux, and why servers use it

**Linux** is an operating system kernel, started by Linus Torvalds in 1991,
free and open source. Combined with supporting programs it forms distributions
like Ubuntu, Debian and Alpine.

**Why servers run Linux**, in order of importance:

1. **No licence cost**, which matters enormously at scale.
2. **It runs without a graphical interface**, so nothing wastes memory drawing
   a desktop nobody looks at.
3. **Every server tool assumes it.** Docker, most databases, most deployment
   platforms are built for Linux first.
4. **It can be inspected and modified**, so problems can be diagnosed all the
   way down.

**The vocabulary you need:**

- **Root** — the all-powerful administrative user. Running as root
  unnecessarily is a security mistake, because a compromised program inherits
  the power.
- **Permissions** — every file records who may read, write and execute it.
- **Everything is a file** — Linux exposes devices, and even some system
  information, as files you can read. This is a design philosophy, and it is
  why so many tools compose so easily.

**Where this appears in this repository.** The images are built `FROM
python:3.11-slim` — a minimal Debian Linux with Python installed. The
Dockerfile installs Linux packages by name:

```dockerfile
RUN apt-get update && \
    apt-get install -y libpq-dev libgl1 libglib2.0-0 tesseract-ocr poppler-utils curl && \
    rm -rf /var/lib/apt/lists/*
```

Every one of those is a Linux system library needed by a Python package —
`libpq-dev` for PostgreSQL, `libgl1` for the image-processing library,
`tesseract-ocr` and `poppler-utils` for reading scanned documents, `curl` for
the container's health check. **A Python library is often a thin wrapper
around a C library that must be installed separately**, and discovering that
is a rite of passage.

Note the `rm -rf /var/lib/apt/lists/*` at the end: it deletes the package
index that `apt-get update` downloaded, in the same command, to keep the image
smaller. Why the same command matters is a Docker detail we cover in Chapter
20.

## D.4 Windows versus Linux, and why this project straddles both

Development happens on Windows; deployment targets Linux. That is extremely
common and it costs real time. The differences that bite:

| | Windows | Linux |
|---|---|---|
| Path separator | `\` | `/` |
| Case sensitivity | `File.py` = `file.py` | different files |
| Line endings | `\r\n` | `\n` |
| Python virtual environment | `venv\Scripts\python.exe` | `venv/bin/python` |
| Process creation | no `fork()` | `fork()` |

**Case sensitivity is the classic disaster.** An import that works on Windows
because `Utils.py` and `utils.py` are the same file fails on the Linux server,
where they are not. Everything passes locally; the deployment breaks.

**And process creation caused a real failure here.** Chapter 03 mentioned that
the worker cannot use certain Celery settings on Windows; the compose file
records the crash, and `scripts/run_worker_windows.ps1` uses `--pool=solo`
precisely because the default prefork pool relies on `fork()`, which Windows
does not have.

**Why containers exist, in one sentence:** so the thing you test is the thing
you ship, regardless of what your laptop runs. That is Chapter 20's whole
argument, and you can already feel the need for it.

---

# Part E — The Terminal and the Shell

## E.1 What they are

**A terminal** is a window that shows text and accepts typed text.

**A shell** is a program running inside it that reads what you type,
interprets it as a command, runs the corresponding program, and shows the
output. Common shells: `bash` and `zsh` on Linux and macOS; PowerShell on
Windows.

**Why they exist, when graphical interfaces are nicer.** Four reasons, and
they are not nostalgia:

1. **Text can be repeated.** A command can be saved, pasted into a document,
   put in a script, and run identically a thousand times. You cannot save a
   sequence of mouse clicks.
2. **Text can be composed.** The output of one program can become the input of
   another (E.3). There is no equivalent for windows.
3. **Text works remotely.** A server in another country has no screen. You
   reach it over a text connection.
4. **Text is precise.** "Click the button near the top" is ambiguous;
   `docker compose restart frontend` is not.

**What existed before, and what happens if it disappears.** Before terminals,
input was punched cards. Without shells, everything in this repository's
Commands section becomes a written procedure with screenshots that goes stale
in a month — and **automation becomes impossible**, which means CI, deployment
and tests all become impossible.

## E.2 Commands, arguments, and flags

Every command has the same shape:

```bash
program argument1 argument2 --flag --option value
```

Take a real one from this repository:

```bash
celery -A app.workers.celery_app worker -Q main-queue,celery --concurrency=2 --loglevel=info
```

Reading it word by word:

- `celery` — the program to run.
- `-A app.workers.celery_app` — a flag with a value: *the application is
  here*. (`-A` is short for `--app`.)
- `worker` — a **subcommand**: which mode of `celery` to run.
- `-Q main-queue,celery` — which queues to consume, comma-separated.
- `--concurrency=2` — how many child processes.
- `--loglevel=info` — how chatty to be.

**Conventions worth knowing:** a single dash takes one letter (`-A`), two
dashes take a word (`--concurrency`), and a value is attached with a space or
an `=`.

**What beginners get wrong.** Typing commands from a tutorial without reading
them. **Read every flag before you run it.** Chapter 03's method applies:
understand before acting. The compose file even contains a warning learned the
hard way about one flag value crashing the worker in a loop — flags are code.

## E.3 Standard input, output, error, and pipes

Every process starts with three channels open:

- **stdin** (0) — where input comes from, normally the keyboard.
- **stdout** (1) — where normal output goes, normally the screen.
- **stderr** (2) — where errors go, also the screen by default.

**Why errors have their own channel — and this is a genuinely good design.**
Because output is often fed into another program. If errors were mixed into
the output, they would corrupt the data. Separating them means you can capture
the useful output while errors still reach a human.

**Redirection** points a channel somewhere else:

```bash
pytest tests/ > results.txt        # stdout into a file
pytest tests/ 2> errors.txt        # stderr into a file
```

**Pipes** connect one program's stdout to the next program's stdin:

```bash
git log --oneline | wc -l
```

`git log --oneline` prints one line per commit; `wc -l` counts lines. Together
they count commits — which is exactly how Chapter 01 established that this
repository has 233 of them. Neither program knows the other exists. **That is
composition**, and it is the Unix philosophy: small programs that do one thing
and can be joined.

**Recognise the pattern?** Chapter 02 defined a pipeline as stages where each
stage's output is the next stage's input, and the RAG pipeline is one. Shell
pipes are the same idea, at the operating-system level, invented in 1973.

## E.4 Exit status, and why `&&` exists

After every command the shell keeps its exit code (C.5). This enables:

```bash
cd backend && pytest tests/
```

`&&` means *run the second only if the first succeeded*. Without it, a failed
`cd` would leave you elsewhere and the tests would run in the wrong folder —
or not at all, confusingly.

**A real trap recorded in this repository's own instructions:** Windows
PowerShell 5.1 does not support `&&` at all; it is a parse error. The
equivalent is `A; if ($?) { B }`. Two shells, two syntaxes, same idea — which
is why the repository documents both.

## E.5 The commands this repository actually uses

Now these read as sentences rather than incantations:

```bash
cd infrastructure
docker compose -f docker-compose.yml -f docker-compose.local-test-override.yml up -d
```
Change folder; then start all services defined in two configuration files
(the second overriding the first), `-d` meaning "detached" — run in the
background and give me my terminal back.

```bash
cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q
```
Run *this specific* Python interpreter (not whichever one is on the PATH — see
Part F), asking it to run the module `pytest` against the `tests` folder,
quietly.

```bash
curl http://localhost:8000/api/v1/health
```
`curl` makes an HTTP request from the command line and prints the response.
This is the simplest possible client (Part K), and it is how you check a
server without a browser.

```bash
docker compose restart frontend
```
The command Chapter 01 warned you never to skip, because Turbopack does not
recompile across the Windows-to-Docker bind mount.

## E.6 Common beginner mistakes at the terminal

1. **Not knowing where you are.** Run `pwd` (print working directory) on
   Linux/macOS or `Get-Location` in PowerShell. Most "file not found" errors
   are this.
2. **Assuming a command exists.** `curl` is present in the container because
   the Dockerfile installs it. Nothing is there unless it was put there.
3. **Ignoring output.** Read errors. The message usually names the problem.
4. **Running a destructive command copied from the internet.** `rm -rf` deletes
   permanently, with no recycle bin, no confirmation, and no undo.
5. **Believing a command worked because there was no output.** Many Unix
   programs print nothing on success — that is a convention, not a failure.
   Check the exit code.

---

# Part F — Environment Variables and PATH

## F.1 What an environment variable is

**What it is.** An **environment variable** is a named piece of text that the
operating system hands to a process when it starts.

**Why it exists.** Because the same program must behave differently in
different places without changing its code. Your laptop's database is not the
production database. Your test key is not the real key.

**What existed before, and why it was not enough.** Configuration inside the
code. Which means the code differs per environment, which means the thing you
tested is not the thing you shipped, which means secrets end up in version
control. That last one is not hypothetical — leaked credentials in public
repositories are one of the most common real-world breaches.

**How it works internally.** The environment is a list of `NAME=value` pairs
copied to a process when it starts. A child process inherits its parent's copy.
Changing your own does not affect anyone else's — which is why an environment
variable set in one terminal is invisible in another.

**Where this appears in this repository — everywhere.** Ten variables have no
default and the program refuses to start without them (decision D-015). The
`.env.example` file marks them:

```
# [REQUIRED][SECRET] Generate each with:  openssl rand -hex 32
AUTH_SECRET_KEY=replace_with_64_hex_chars_from_openssl_rand_hex_32
CSRF_SECRET_KEY=replace_with_a_DIFFERENT_64_hex_char_secret
```

Note the discipline in that snippet: it says what the value is for, how to
generate one, that the two must differ, and that they are secret — without
containing a single real secret. **`.env.example` is a template that is safe to
commit; `.env` is the filled-in version that must never be.**

And in the continuous-integration configuration
([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)), the same
variables appear with fake values and a comment explaining exactly why:

```yaml
    env:
      ENVIRONMENT: test
      AUTH_SECRET_KEY: ci-test-auth-secret
      CSRF_SECRET_KEY: ci-test-csrf-secret
```

> *"CI has no .env, so importing `settings` … fails validation unless we
> provide them here. Test-only values; the real secrets are supplied by the
> deployment."*

That is fail-fast configuration (Chapter 03's vocabulary) meeting the practical
consequence: **if your program refuses to start without configuration, then
every environment must supply it, including your test robot.**

**What happens if environment variables disappear?** You would need a
different build of the program for every environment, and secrets would have
to live inside it.

## F.2 PATH — the one variable everyone must understand

When you type `python` and press Enter, how does the shell know which file to
run?

It looks in the **PATH**: an environment variable holding a list of folders,
checked left to right, first match wins.

```
/usr/local/bin:/usr/bin:/bin
```

**Why this exists.** So you can type `python` instead of
`/usr/local/bin/python3.11`.

**Why it causes so much confusion.** If two versions are installed, the one
earlier in the PATH wins — silently. You believe you are running one thing and
are running another. Every "but it works on my machine" story involving
versions is a PATH story.

**Where this appears in this repository.** The test command is deliberately
explicit:

```bash
cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q
```

`./venv/Scripts/python.exe` is a **path**, not a PATH lookup. It names exactly
one interpreter and cannot be affected by what else is installed.

**What is `venv`?** A **virtual environment** is a private folder holding one
project's Python interpreter and libraries. Without it, every project on the
machine shares one set of libraries, and two projects needing different
versions of the same library cannot coexist. With it, each project is isolated
— the same isolation principle as processes (C.2) and containers (Chapter 20),
applied to dependencies. Note that `backend/venv/` appears in `.gitignore`:
it is generated from `requirements.txt` and must never be committed.

## F.3 Two more environment variables from this repository

From the Dockerfile:

```dockerfile
ENV PYTHONUNBUFFERED=1
```

By default Python holds output in a buffer and writes it in batches, which is
faster. In a container that is a disaster: your logs appear late or not at all
when the process crashes, so the last thing you see is not the last thing that
happened. This setting turns buffering off. **A one-line configuration change
that decides whether you can debug a crash.**

And the final line:

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

`${PORT:-8000}` means "use the environment variable `PORT` if it is set,
otherwise 8000". Hosting platforms tell your program which port to use by
setting `PORT`. This one expression makes the same image work locally and on a
platform that chooses the port for you.

Also note `--host 0.0.0.0`. That is the single most important flag in this
whole file, and it needs Part G to explain.

---

# Part G — Networking

## G.1 What a network is

**What it is.** Two or more computers connected so they can exchange bytes.

**How it works, in one paragraph.** Data is chopped into small pieces called
**packets**. Each packet carries the address of where it is going and where it
came from. Packets travel independently, may take different routes, may arrive
out of order, and may be lost. Everything else in networking is machinery to
make that unreliable stream of pieces look like a reliable conversation.

**Why packets rather than a continuous line?** Because a dedicated line
between every pair of computers is impossible, and a line reserved for one
conversation is idle most of the time. Packets share the same wires among many
conversations, and they route around damage. **The internet is a mesh where no
single failure stops everything** — that was the original design goal, and it
is why the network you rely on is built this way.

## G.2 IP addresses

**What it is.** An **IP address** is a number identifying a machine on a
network. In the older, still-dominant version (IPv4) it is written as four
numbers: `142.250.183.14`.

**Three you must know:**

- **`127.0.0.1`**, also called **`localhost`** — "this same machine". Traffic
  to it never leaves the computer.
- **`0.0.0.0`** — in a *listening* context, it means "accept connections
  arriving on any of my network interfaces".
- **Private ranges** (`10.x.x.x`, `172.16–31.x.x`, `192.168.x.x`) — reachable
  only inside a local network, not from the internet.

**Now the most valuable five minutes in this chapter.** Look again at:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If that said `--host 127.0.0.1`, the server would accept connections *only
from inside its own container*. From your browser it would appear completely
dead — no error, no log line, just a refused connection. Because a container
is an isolated environment with its own network view (Chapter 20), a server
listening on `localhost` inside a container is listening on the container's
own private loopback, which nothing outside can reach.

**This is the number one Docker networking mistake in the world**, it produces
a symptom ("connection refused") that looks like the application is broken,
and the cure is one flag. You now understand it before ever meeting it.

## G.3 DNS — names instead of numbers

**What it is.** The **Domain Name System** turns a name like
`api.example.com` into an IP address.

**Why it exists.** Humans cannot remember numbers, and — more importantly —
**the number must be allowed to change** without every user having to be told.
A service can move to a new machine and keep its name.

**How it works internally, simplified.** Your computer asks a **resolver**;
the resolver asks a chain of servers, from the root to the one authoritative
for the domain; the answer is cached for a time (a **TTL**) so the next lookup
is instant.

**Where this appears in this repository.** In the compose file, the backend is
configured with `POSTGRES_SERVER=pgbouncer` and `REDIS_URL=redis://redis:6379/0`.

`pgbouncer` and `redis` are not domain names on the internet. They are
**service names**, and Docker runs a small DNS server that resolves them to the
right container's address on the private network it creates. That is why the
compose file can say "connect to `redis`" without knowing any IP address, and
why the same file works on any machine.

**And a subtlety from Chapter 02 that now makes sense.** The local override
file remaps only the *host* port for Redis, from 6380 to 6381, and the comment
says *"Container-to-container traffic is unaffected (`redis:6379`)."* Two
different networks are in play: the private one between containers, and the
host machine's. Understanding that distinction is exactly what keeps that
change safe.

## G.4 Ports — the concept backend development runs on

**What it is.** One machine has one IP address but runs many programs that all
want to use the network. A **port** is a number from 1 to 65535 that says
*which program on that machine* a packet is for.

**The analogy that actually works:** the IP address is the building's street
address; the port is the apartment number.

**How it works.** A server program **binds** to a port: it tells the operating
system "deliver anything arriving for port 8000 to me". Only one program can
hold a given port at a time — which is why "address already in use" happens
when you start a server twice.

**Conventions:** 80 is plain HTTP, 443 is HTTPS, 5432 is PostgreSQL, 6379 is
Redis. These are agreements, not laws; you can run anything anywhere, and
people will be confused if you do.

**The port map of this repository**, which you can now read completely:

| Port on your machine | Service | Notes |
|---|---|---|
| 3000 | frontend (Next.js) | what you open in a browser |
| 8000 | backend (FastAPI) | what the frontend calls |
| 5433 | PostgreSQL | mapped from 5432 inside the container |
| 6432 | PgBouncer | the connection pooler |
| 6380 (6381 with the override) | Redis | mapped from 6379 inside |

**Why is PostgreSQL on 5433 rather than 5432?** Because the developer's
machine may already run a PostgreSQL on 5432, and two programs cannot share a
port. The `"5433:5432"` in the compose file means *"port 5433 on my machine
forwards to port 5432 inside the container"*. The database inside still
believes it is on its normal port. **Port mapping is a translation at the
boundary**, and it is why the container's internal configuration never has to
know about your machine's clutter.

**And a real incident from this exact concept**, recorded in the compose file:
the PgBouncer container defaults to listening on 5432, but the port mapping,
the health check and the application all targeted 6432. So the health check
probed a closed port forever, PgBouncer was permanently marked "unhealthy",
and the worker and beat — which wait for it to be healthy — never started.
The fix was one line: `LISTEN_PORT=6432`.

**Diagnosing that requires exactly the knowledge in this section**, and nothing
more.

## G.5 TCP, sockets, and connections

Packets are unreliable (G.1). Most applications need reliability. That gap is
filled by two protocols.

**TCP** (Transmission Control Protocol) provides a reliable, ordered stream.
It numbers packets, re-sends lost ones, reassembles them in order, and tells
the sender to slow down when the receiver cannot keep up (which is
**backpressure**, from Chapter 04, implemented in the network itself).

**UDP** does none of that. It is faster and used where late data is worthless —
live video, games.

**A socket** is the programming object representing one end of a connection.
When code "opens a connection to the database", it creates a socket.

**The server model**, which is what a web framework does for you:

1. Create a socket.
2. **Bind** it to an address and port.
3. **Listen** — tell the OS to queue incoming connections.
4. **Accept** — take the next waiting connection, producing a new socket
   dedicated to that one client.
5. Read the request, write the response, close.
6. Go back to step 4.

**Every web server in every language does this.** FastAPI, Express, Rails,
Spring — all of them wrap those six steps. Knowing they exist demystifies the
whole category.

**Where this appears in this repository.** Two places where sockets are visible
rather than hidden:

- The fork bug in `db/session.py` (C.3): *"Inherited pooled connections are
  shared TCP sockets."* You now know a socket is one endpoint of a
  conversation, and that two processes sharing one endpoint is nonsense.
- The connection budget (Chapter 02). Each database connection is a socket
  plus, on the PostgreSQL side, a whole operating-system process. That is
  *why* connections are scarce and must be counted — a connection is not an
  abstraction, it is real resources on two machines.

## G.6 Client and server

**A server** is a program that waits for requests and answers them.
**A client** is a program that makes requests.

**These are roles, not machines.** In this repository, the backend is a server
when your browser calls it, and a client when it calls the database, Redis and
the AI provider — in the same request.

**Why the distinction matters for security**, and it is the most important
sentence in this section: **the client is under the user's control and the
server is not.** Anyone can modify what the browser sends. Therefore *every*
rule that matters must be enforced on the server. The trial limit in Chapter 01
is counted server-side for this reason, and Chapter 03's tenancy work is
entirely about the server refusing to trust a supplied identifier.

---

# Part H — HTTP

## H.1 What a protocol is

**A protocol** is an agreed format for a conversation: what may be said, in
what order, and what each thing means. TCP is a protocol for moving bytes
reliably. **HTTP** is a protocol for asking for things and getting them back.

## H.2 What HTTP is and why it exists

**HTTP** (HyperText Transfer Protocol) was created around 1990 for fetching
documents that link to each other. Its design was deliberately simple: a
client sends a text request, a server sends a text response, done.

**Why it took over everything.** Because that simplicity made it easy to
implement, easy to inspect, easy to pass through firewalls, and easy to cache.
It is now used for things its inventors never imagined — including streaming
AI answers, which is what this repository does with it.

## H.3 The anatomy of a request

An HTTP request is text with four parts. Here is a real one from this
application, exactly as it travels:

```http
POST /api/v1/query/stream HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Cookie: token=eyJhbGciOiJIUzI1NiJ9...; csrf_token=a7f3...
X-CSRF-Token: a7f3...
X-Device-ID: 9c21...
Content-Length: 132

{"query":"What is the notice period?","top_k":12,"workspace_type":"legal"}
```

The four parts:

1. **The request line** — method, path, protocol version.
2. **Headers** — `Name: value` pairs carrying metadata.
3. **A blank line** — the separator between headers and body.
4. **The body** — the data being sent (optional).

**Methods**, and what each promises:

| Method | Means | Should it change data? |
|---|---|---|
| `GET` | give me this | No |
| `POST` | here is data, do something | Yes |
| `PUT` | store this at this location | Yes |
| `DELETE` | remove this | Yes |
| `HEAD` | like GET, headers only | No |

**Why the promise matters.** Because things assume it. Browsers pre-fetch
`GET` links; caches store `GET` responses. A `GET` that deletes something will
be triggered by a crawler, and this has destroyed real data at real companies.

**Where this appears in this repository.** The CSRF middleware only checks
methods that change data:

```python
if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
```

That is only correct **because** `GET` is agreed not to change anything. The
protocol's promise is load-bearing for the security control.

## H.4 The anatomy of a response

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
X-Correlation-ID: 4f2c8e1a-...
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains

event: token
data: {"token":"The"}

event: token
data: {"token":" notice"}
```

Same shape: status line, headers, blank line, body.

**Status codes**, grouped so you never have to memorise individually:

| Range | Meaning | Examples used here |
|---|---|---|
| 1xx | information | rare |
| 2xx | success | 200 OK, 201 Created |
| 3xx | go elsewhere | 301 moved, 304 not changed |
| 4xx | **you** made a mistake | 400 bad request, 401 not authenticated, 402 payment required, 403 forbidden, 404 not found, 429 too many requests |
| 5xx | **the server** made a mistake | 500 internal error, 503 unavailable |

**The 4xx/5xx split is the useful part.** It tells you where to look first: 4xx
means fix the request, 5xx means fix the server.

**Three of these carry decisions from earlier chapters:**

- **402 Payment Required** is returned when the free trial is exhausted, and
  the frontend turns it into an upgrade dialog
  ([`api.ts:342`](../frontend/src/lib/api.ts)).
- **404 rather than 403** for another user's document — decision D-020,
  because 403 would confirm the resource exists (an enumeration oracle).
- **401** triggers the silent token refresh and one retry in `apiFetch`.

## H.5 HTTP is stateless — and what that forces

**Statelessness** means each request is independent. The server does not
inherently remember that the previous request came from the same person.

**Why it was designed that way.** Because it makes servers simple and
replaceable. Any server can answer any request, which is exactly the property
Chapter 02 called *stateless* and identified as the prerequisite for
horizontal scaling.

**The consequence.** If the server does not remember you, every request must
carry proof of who you are. Two options exist:

1. Send credentials every time (terrible).
2. Log in once, receive a token, send the token every time.

Option 2 is what everyone does, and the browser mechanism for carrying it is
the **cookie** (Chapter 01): a small piece of data the server sets and the
browser sends back automatically to that site.

**And "automatically" is precisely the problem.** The browser attaches cookies
to requests it makes to that site *regardless of which page started them* — so
a malicious page can cause a request that carries your cookie. That is CSRF,
and it is why the CSRF token exists. **Statelessness → cookies → CSRF → CSRF
tokens.** Four chapters of security design, all descending from one property
of a 1990s document protocol.

## H.6 HTTP versions, briefly

- **HTTP/1.1** (1997) — one request at a time per connection; connections
  reused.
- **HTTP/2** (2015) — many requests interleaved on one connection.
- **HTTP/3** (2022) — same ideas on top of UDP, faster to establish.

**What stays identical across all three:** methods, paths, headers, status
codes, bodies. Only the transport changed. That is why your knowledge here
does not expire.

---

# Part I — HTTPS and TLS

## I.1 The problem

An HTTP request is plain text travelling through equipment owned by other
people. Anyone on the path can read it and change it. That is unacceptable for
a password, a session cookie, or a private document.

Three distinct dangers, and it is worth naming them separately because the
solution addresses each:

1. **Eavesdropping** — someone reads your data.
2. **Tampering** — someone changes it in flight.
3. **Impersonation** — you connect to something pretending to be the server.

## I.2 What TLS is

**TLS** (Transport Layer Security) is a protocol that sits between TCP and
HTTP and provides encryption, integrity, and identity. **HTTPS is simply HTTP
running inside TLS.** (You may see "SSL" — that is the older name for the same
idea; the protocol was renamed to TLS in 1999 and everyone kept saying SSL.)

**The two kinds of encryption you need to know:**

- **Symmetric** — one shared secret encrypts and decrypts. Fast. Problem: both
  sides must already share the secret.
- **Asymmetric** — a key *pair*. Anything encrypted with the public key can
  only be decrypted with the private key. Slow. Solves the sharing problem.

**How TLS uses both, and the design is elegant.** Use slow asymmetric
cryptography *once* to agree on a fresh shared secret, then use fast symmetric
encryption for the actual conversation. Best of both.

**Certificates and identity.** Encryption alone does not tell you *who* you are
talking to. A **certificate** is a document saying "this public key belongs to
`example.com`", signed by a **certificate authority** that browsers already
trust. Your browser checks the signature, the name, and the expiry date. This
is why an expired certificate produces a frightening warning: the identity
claim can no longer be verified.

**What TLS does not protect.** It protects data *in transit* only. It does not
protect data on the server, does not verify that the server is well-behaved,
and does not hide *which* server you connected to.

## I.3 Where this appears in this repository

Three places, and one of them is a genuinely instructive bug.

**1. The response headers**, set in
[`backend/app/main.py`](../backend/app/main.py):

```python
response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```

**HSTS** tells the browser: for the next year, never contact this site over
plain HTTP, even if a link says to. It closes the window where a first
plain-text request could be intercepted and redirected.

**2. Database connections.** Managed databases require TLS. In
[`backend/app/core/config.py`](../backend/app/core/config.py):

```python
if "sslmode=" not in url and not _is_local_db_host(url):
    url += ("&" if "?" in url else "?") + "sslmode=require"
```

Note the condition: TLS is required for remote hosts and *not* forced for
local ones. The comment records why — an earlier version forced it
unconditionally, and *"made every sync connection — health checks, Celery
workers — fail against non-SSL Postgres, including the project's own
docker-compose stack."* **A security control applied without a condition broke
the development environment**, which is a very common way for good security
intentions to get switched off entirely.

**3. Two libraries, two spellings, one bug.** The async driver wants
`ssl=require`; the sync driver wants `sslmode=require` and *rejects* the other
spelling. The `sync_database_url` property exists mostly to normalise between
them. This is the unglamorous reality of integration work: two libraries
solving the same problem with incompatible names, and a translation layer in
the middle. **Recognising "this function exists only to reconcile two
vocabularies" is a useful reading skill.**

## I.4 The encoding bug that took down a database connection

This one deserves its own section, because it connects text encoding (Part B),
URLs, TLS, and failure amplification in one incident. From
[`backend/app/api/v1/endpoints/health.py`](../backend/app/api/v1/endpoints/health.py):

First, the concept. A URL cannot contain arbitrary characters, because some —
`@`, `:`, `/`, `?` — have structural meaning. So special characters are
**percent-encoded**: replaced by `%` followed by their value in hexadecimal.
The `@` character becomes `%40`. A password containing `@` must therefore be
written `%40` inside a connection URL.

Now the bug, in the code's own words:

> *"`urlparse()` does NOT percent-decode userinfo, but psycopg2's keyword
> arguments expect the literal credential. A password containing any character
> that must be encoded in a URL — `@` as `%40` is the common case … was
> therefore sent verbatim ("Kanwams%4012345" instead of "Kanwams@12345") and
> rejected."*

So the health check sent a wrong password. Annoying but harmless — except for
what happened next:

> *"This was not a harmless false alarm: the healthcheck re-runs every 10s, so
> each failure became another rejected login against the upstream. Supabase's
> Supavisor pooler tripped its circuit breaker after ~210 attempts
> (ECIRCUITBREAKER) and began refusing *all* new connections, including the
> correctly-authenticated ones used by the application itself."*

**Trace the causal chain, because it is a masterclass in how small things
become outages:**

encoding rule (`@` → `%40`) → one function that decodes and one that does not →
wrong password → a *repeating* health check → 210 failed logins → the
provider's defence mechanism activates → **the entire application loses
database access**.

Not one link in that chain is exotic. Every one is in this chapter.

**Three lessons:**

1. **Know which layer decodes what.** Two libraries in one path, different
   assumptions, is where these live.
2. **A repeating failure is qualitatively different from a single one.** Every
   10 seconds turns a nuisance into an attack on yourself.
3. **A defence mechanism protecting someone else can take you down.** Rate
   limits and circuit breakers do not distinguish your bug from an attacker.

---

# Part J — JSON and Data Formats

## J.1 The problem

A program holds structured values in memory — a question, a number, a list of
document ids. A network carries only bytes. So structure must be flattened
into bytes to send (**serialisation**) and rebuilt on the other side
(**deserialisation** or parsing).

**Why this is not trivial.** The two sides may be different languages on
different machines. They must agree exactly on how structure is written down.

## J.2 What JSON is

**JSON** (JavaScript Object Notation) is a text format for structured data.
It has six types and no more:

```json
{
  "query": "What is the notice period?",
  "top_k": 12,
  "similarity_threshold": 0.1,
  "session_id": null,
  "comparison_mode": false,
  "document_ids": ["a7f3", "b2e9"]
}
```

- **object** — `{ }`, unordered name/value pairs
- **array** — `[ ]`, ordered list
- **string** — `"in double quotes"`
- **number** — `12`, `0.1`
- **boolean** — `true`, `false`
- **null** — absence of a value

**Why it won.** It is human-readable, every language can parse it, and it is
small enough. Its predecessor, **XML**, was more powerful and much more
verbose; for the common case of "send me an object", JSON's simplicity beat
XML's capability. **Simplicity beating capability is one of the most reliable
patterns in technology adoption.**

**What JSON deliberately lacks:** comments, dates, and integers distinct from
decimals. Every one of those omissions causes a real annoyance, and every one
was a deliberate choice to keep the format small.

**Alternatives worth recognising:**

| Format | Good at | Weak at |
|---|---|---|
| JSON | universal, readable | verbose, no schema, no dates |
| YAML | human-written config (Docker Compose, CI) | whitespace-sensitive, surprising type rules |
| CSV | tabular data, spreadsheets | no nesting, no types |
| XML | documents, formal schemas | verbose |
| Protocol Buffers | compact, fast, versioned | not human-readable, needs a schema |

## J.3 Where JSON appears in this repository

Four places, each teaching something different:

**1. The browser sends it.** [`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts):

```ts
body: JSON.stringify({
  query,
  top_k: topK,
  similarity_threshold: 0.1,
  session_id: sessionId || null,
  workspace_type: workspaceType || "general",
})
```

`JSON.stringify` turns a live JavaScript object into a string of text. The
`Content-Type: application/json` header tells the server how to interpret the
bytes that follow — without it the server would be guessing (Part B.4 again).

**2. The server parses and validates it.** FastAPI does not merely parse the
JSON; it checks it against a declared shape and rejects anything that does not
fit, before your code runs. Chapter 14 covers this fully. The important idea
now: **parsing asks "is this valid JSON?"; validation asks "is this the JSON I
expect?"** They are different questions and you need both.

**3. Streaming uses JSON inside a text protocol.** Each SSE frame carries a
JSON payload on its `data:` line, and the browser calls `JSON.parse(data)` on
it. So the outer envelope is line-based text and the inner content is JSON —
a very common layering.

**4. Configuration uses it.** From `.env.example`:

```
CORS_ORIGINS=["http://localhost:3000"]
```

An environment variable is *always* a string. Here that string happens to
contain JSON, which the settings loader parses into a list. That is how a flat
key/value system carries structured data — a small trick you will see
constantly.

**And a fifth, in the worker configuration:**

```python
task_serializer="json",
accept_content=["json"],
```

Celery could serialise jobs using Python's own `pickle` format, which can
represent any Python object — including instructions that execute on load. A
message broker that accepts pickle is a remote-code-execution risk if anyone
can write to the queue. **Restricting to JSON is a security decision**: JSON
can describe data and cannot describe code.

---

# Part K — APIs and the Client/Server Contract

## K.1 What an API is

**An API** (application programming interface) is a defined way for one
program to use another. Not for humans — for programs.

**Why it exists.** So capability can be offered without exposing internals.
The user of an API needs to know what to send and what comes back; nothing
else. That is Chapter 02's *interface*, applied across a network.

## K.2 What a web API looks like

A **web API** is an API reached over HTTP. It is defined by:

- a **base URL** — `http://localhost:8000/api/v1`
- a set of **paths** — `/query/stream`, `/documents`, `/auth/login`
- a **method** per path — `GET`, `POST`, …
- a **request shape** — usually JSON
- a **response shape** — usually JSON, or a stream
- **authentication rules** — what proof of identity is required

**REST** is the common style: paths name *things* (nouns), methods say what
to *do* to them. `GET /documents` lists them; `POST /documents` creates one;
`DELETE /documents/{id}` removes one.

## K.3 Versioning, and a real invariant

Every path here begins `/api/v1`. **Why a version number?** Because clients you
do not control — a mobile app, a customer's integration, a browser tab left
open for a week — depend on the current shape. When you must change it
incompatibly, you publish `/api/v2` and keep `/api/v1` alive while people
migrate. **Versioning is how you change a contract without breaking the people
who signed it.**

And an invariant from `CLAUDE.md` that you can now read precisely:

> *"All routes under `/api/v1`. `NEXT_PUBLIC_API_URL` already includes it; endpoint
> strings in `lib/api.ts` start with `/` and **omit** `/api/v1`."*

The base URL is configured once as an environment variable; every call appends
a path to it. Writing `/api/v1` again in a path produces
`/api/v1/api/v1/documents`, which 404s. **One decision, made in one place,
because it varies per environment — exactly the reasoning from Part F.**

---

# Part L — One Request, End to End, at the Byte Level

Everything in this chapter, in a single narrative. You typed
`http://localhost:3000` and pressed Enter.

1. **The browser parses the URL.** Scheme `http`, host `localhost`, port —
   absent, so it uses the default 80… except this URL says `:3000`, so 3000.
2. **Name resolution.** `localhost` is special: no DNS query, it maps to
   `127.0.0.1`.
3. **TCP connection.** The browser opens a socket to `127.0.0.1:3000`. The
   operating system on the receiving end sees a connection arriving for port
   3000, finds the process that bound it (the Next.js server), and hands it
   over.
4. **HTTP request.** The browser writes a `GET / HTTP/1.1` request with
   headers into the socket.
5. **The server responds** with HTML, CSS and JavaScript.
6. **The browser renders**, then runs the JavaScript, which becomes the
   application.
7. **You log in.** The page sends `POST /api/v1/auth/login` with a JSON body to
   a *different* port — 8000 — which is a different process. The response
   includes a `Set-Cookie` header. The browser stores the cookie.
8. **You ask a question.** The page sends `POST /api/v1/query/stream`. The
   browser automatically attaches the cookie. The code attaches the CSRF token
   header.
9. **The backend process** — a Python program listening on port 8000 —
   accepts the connection, reads the request, and runs the pipeline from
   Chapter 01. Along the way it opens *its own* sockets: to PostgreSQL through
   PgBouncer, and to the AI provider over TLS across the internet.
10. **The response streams back.** The server writes small chunks into the
    same open socket, and the browser's reader loop decodes each one.
11. **You see the answer appear.**

**Every noun in that story is now defined.** URL, DNS, socket, port, process,
HTTP, header, cookie, JSON, TLS, stream. If any is still fuzzy, go back to its
part — everything after this chapter builds on it.

---

# Part M — Version Control: Git and GitHub

## M.1 The problem

You have working code. You change it. It breaks. What was it before?

Three problems, all severe:

1. **History.** Which change broke it, and when?
2. **Collaboration.** Two people editing the same file.
3. **Experimentation.** Trying something risky without endangering what works.

**What existed before.** Folders named `project_final`, `project_final_v2`,
`project_final_ACTUAL`. Everyone has done this. It fails on all three counts —
no record of *why* anything changed, no way to merge, and no safety.

## M.2 What Git is

**Git** is a program that records snapshots of a folder over time.

The vocabulary, defined once:

- **Repository (repo)** — a folder Git is tracking, plus its whole history.
- **Commit** — one saved snapshot, with a message explaining *why*, an author,
  and a timestamp. It has a unique id like `8fd0f22`.
- **Branch** — a movable pointer to a line of commits. Working on a branch
  means your changes do not affect the main line until you merge.
- **Merge** — combining one branch's work into another.
- **Diff** — the difference between two states: which lines were added and
  removed.
- **Remote** — a copy of the repository somewhere else, usually a server.
- **Clone / push / pull** — copy the whole thing down, send commits up, fetch
  commits down.

**How it works internally, briefly.** Git stores the full content of each
version, addressed by a hash of that content. A commit records the whole tree,
its parent commit, and the message. **Because a commit's id depends on its
content and its parent, history is tamper-evident**: changing an old commit
changes every id after it, which is why rewriting published history is
disruptive and why this repository lists it as out of scope without explicit
approval.

**Git versus GitHub.** Git is the program on your machine. **GitHub** is a
website that hosts copies and adds collaboration features — pull requests,
issues, automation. You can use Git with no GitHub at all. This distinction
confuses nearly every beginner.

## M.3 Where this appears in this repository

**233 commits.** Chapter 03 used their messages as its primary teaching
material — and now you know that a commit message is a permanent, attributable
note attached to an exact set of changes. That is why the practice is
valuable: the explanation cannot drift away from the change it explains.

**The branch.** Work happens on a named branch such as
`security/redact-env-example`, separate from `main`. The rule in `CLAUDE.md` —
*"If on the default branch, branch first"* — exists so that unfinished work
never sits on the line everyone else builds from.

**`.gitignore`.** Now fully readable: generated things (`node_modules/`,
`venv/`, `__pycache__/`, `.next/`) and secrets (`.env`). Generated files are
excluded because they can be rebuilt from what *is* stored and would otherwise
be enormous. Secrets are excluded because a repository is copied, shared, and
often published — and **a secret committed once is compromised forever, even
if deleted later, because it remains in the history.**

**Continuous integration.** From `.github/workflows/ci.yml`:

```yaml
on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
```

**CI** means: every time code is pushed, a fresh machine somewhere starts,
installs everything, and runs the tests. Its value is that the fresh machine
has *none of your local mess* — no leftover installed package, no
environment variable you forgot you set. **CI is the honest answer to "it works
on my machine."** And notice from Part F why it must declare all ten required
environment variables: a program that fails fast on missing configuration fails
fast for robots too.

---

# Part N — Exercises

These start at zero. Do them in order, at a real computer. Answers in Part O.

### Level 0 — First contact with a terminal

**N1.** Open a terminal (Terminal on macOS/Linux, PowerShell on Windows). Type
`pwd` (or `Get-Location` on PowerShell) and press Enter. What did it print,
and what does it mean?

**N2.** List the files where you are: `ls` (or `dir`). Now list them again with
details: `ls -l` (or `dir` alone shows sizes). Find one file's size in bytes.

**N3.** Print one line of text: `echo hello`. Now send it to a file:
`echo hello > greeting.txt`. Read it back: `cat greeting.txt` (or
`Get-Content greeting.txt`). Explain in one sentence what `>` did.

### Level 1 — Counting and connecting

**N4.** Using the byte facts from A.3: a document produces 200 chunks. Each
chunk stores about 1,800 characters of text plus a 1024-dimension embedding at
4 bytes per number. How many bytes is one document, roughly? Show your
arithmetic.

**N5.** Your friend says "my program is slow because the disk is slow, so I
will add more RAM." Using the table in A.7, explain when that helps and when
it does nothing.

**N6.** In this repository, three processes run from the same code. Name them
and say in one sentence what each does. Why must exactly one copy of the third
one run?

### Level 2 — Reading real configuration

**N7.** Explain, to someone who has never seen it, what each part of this means:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then explain what would break if `0.0.0.0` were changed to `127.0.0.1` inside
a container, and what the symptom would look like.

**N8.** The compose file maps `"5433:5432"` for PostgreSQL. Which number is on
your machine, which is inside the container, and why are they different?

**N9.** Look at this line and say what it does and why it exists:

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### Level 3 — Diagnosis

**N10.** You start the stack and the backend logs show
`connection refused` when it tries to reach the database. List, in order, the
things you would check, using only Part G. For each, say what the result tells
you.

**N11.** A health check runs every 10 seconds and fails every time because of a
wrong password. Explain why this is much worse than a single failed check, and
name two independent things that could go wrong as a result.

**N12.** A colleague's export feature works perfectly in testing and crashes
for users in India. Using Part B, state the most likely cause and the one test
that would have caught it.

### Level 4 — Explanation

**N13.** Explain to a non-technical person, in under 150 words, why a website
needs both a "port" and an "IP address". Use an analogy but also give the
technical statement.

**N14.** HTTP is stateless. Walk from that single fact to the existence of CSRF
tokens, naming each step in the chain.

**N15.** Why does this repository restrict its job queue to JSON rather than
allowing Python's `pickle` format? Answer in terms of what each format can
express.

---

# Part O — Answer Key

**O1 (N1).** It printed your **working directory** — the folder the shell is
currently "standing in". Relative paths are interpreted from here, which is why
`cd backend && pytest tests/` works and `pytest tests/` from elsewhere does
not.

**O2 (N2).** Any answer is correct; the point is that a file's size is a
concrete number of bytes, not an abstraction. A 4,096-byte file is exactly one
embedding's worth of data.

**O3 (N3).** `>` is **redirection**: it points the command's standard output
(stdout) at a file instead of the screen. The program did not know or care —
it wrote to stdout as usual, and the shell changed where stdout led. That
separation is why the same programs work in pipelines, scripts and terminals.

**O4 (N4).** Text: 200 × 1,800 = 360,000 bytes ≈ 360 KB. Embeddings: 1024
numbers × 4 bytes = 4,096 bytes each, × 200 = 819,200 bytes ≈ 819 KB. Total
roughly **1.2 MB per document**. This is the same calculation behind decision
D-012 — vectors are small enough to keep in the main database.

**O5 (N5).** More RAM helps if the program is repeatedly reading data from
disk that it *could* have kept in memory — more RAM means fewer trips to the
slow row of the table. It does nothing if the program is limited by CPU work,
by network latency, or by a single unavoidable read of data far larger than any
plausible amount of RAM. **The correct move is to measure which row of the
hierarchy the time is being spent in before buying anything** — which is
`performance-profiler`'s rule from Chapter 04: no recommendation without a
measurement.

**O6 (N6).** `backend` answers web requests (uvicorn on port 8000); `worker`
takes slow jobs off the Redis queue and does them (Celery worker); `beat`
starts scheduled jobs at fixed times (Celery Beat). Exactly one Beat must run
because it holds the *schedule* — it is stateful — so a second copy fires every
scheduled job twice, which the compose file notes means double emails. Compare
with the web process, which is stateless and can safely be run many times.

**O7 (N7).** `uvicorn` is the program (a web server for Python). `app.main:app`
means "in the module `app.main`, use the object named `app`". `--host 0.0.0.0`
means listen on all network interfaces. `--port 8000` means bind to port 8000.

With `127.0.0.1` inside a container, the server accepts connections only from
inside that container's own isolated network view. From your browser it looks
completely dead: the connection is **refused**, with no error in the
application logs, because the request never reached the application at all.
The absence of a log line is itself the clue — the traffic did not arrive.

**O8 (N8).** 5433 is on your machine (the host); 5432 is inside the container.
They differ because a developer's machine may already have PostgreSQL using
5432, and only one program may hold a port at a time. Mapping translates at the
boundary so the container's own configuration never needs to know.

**O9 (N9).** It is the default command run when the container starts. It runs a
shell (`sh -c`) so that `${PORT:-8000}` is expanded: use the environment
variable `PORT` if the hosting platform set one, otherwise 8000. It exists so
that one image works both locally and on a platform that assigns the port at
deploy time — configuration outside the code (Part F).

**O10 (N10).** In order, cheapest first:

1. **Is the database process running at all?** If not, nothing else matters.
2. **Is it listening on the port you are using?** "Connection refused" almost
   always means nothing is bound to that port — as opposed to a timeout, which
   usually means something is blocking the traffic.
3. **Are you using the right name?** Inside the compose network the host is
   `pgbouncer` or `db`, not `localhost`. From your own machine it is
   `localhost` with the *mapped* port. Mixing these up is the most common
   error.
4. **Right port?** The PgBouncer incident is exactly this: everything targeted
   6432 while the container listened on 5432, so the port was genuinely closed.
5. **Is the target bound to `0.0.0.0` or to `127.0.0.1`?** The latter is
   unreachable from another container.
6. **Only then** consider credentials — a wrong password produces an
   authentication error, not a refused connection. **The error's shape tells
   you which layer to look at**, and that is the real skill here.

**O11 (N11).** A single failed check is one error. A check repeating every 10
seconds is 8,640 failed logins per day aimed at your own database. Two
independent consequences: (a) the upstream provider's protective mechanism —
a circuit breaker or rate limit — activates and refuses *all* connections,
including the healthy ones, which is precisely what happened here after ~210
attempts; (b) the container is marked unhealthy, so anything that waits for it
to be healthy (the worker, the scheduler) never starts, turning a monitoring
bug into a total outage. **Repetition changes the nature of a failure, not
just its count.**

**O12 (N12).** A character-encoding failure. The export path uses fonts limited
to latin-1, which cannot represent `₹` or Devanagari script, so it raises an
exception on exactly the content Indian users produce. The test that would have
caught it: run the real export path with real non-English data, rather than
with English test strings. This is the "test with real data" lesson, and it is
also Chapter 03's *observability of a defect* — with English-only fixtures the
bug cannot appear at all.

**O13 (N13).** *An IP address identifies a machine, the way a street address
identifies a building. But one machine runs many programs that all use the
network, so an address alone is not enough to know which one a message is for.
A port is a number attached to the address that says which program. Technically:
the IP address routes the packet to the correct machine, and the port tells that
machine's operating system which listening process should receive it. This is
why one server can run a website on 3000 and a database on 5432 at the same
time, and why two programs cannot use the same port.*

**O14 (N14).** (1) HTTP is stateless, so the server does not inherently know
that two requests came from the same person. (2) Therefore identity must travel
with every request. (3) Sending a password every time is unacceptable, so the
server issues a token after login. (4) The browser's built-in mechanism for
carrying such a token is the cookie. (5) The browser attaches cookies to
requests for that site **automatically**, whatever page caused the request.
(6) So a malicious page can cause an authenticated request — CSRF. (7) The
defence is a secret value that the real site can read and attach as a header,
and that another site cannot read, so the server can tell genuine requests from
forged ones.

**O15 (N15).** JSON can describe **data**: strings, numbers, lists, objects.
Python's `pickle` can describe **objects, including instructions that run when
loaded**. A worker that accepts pickled jobs will execute whatever the message
tells it to construct, so anyone able to write to the queue can run code on
your server. Restricting to JSON means the worst a malicious message can do is
be invalid data. **The format's expressive limits are the security control.**

---

# Part P — Senior Critique: How This Repository Treats the Fundamentals

A code review of the *foundations layer*, in the style of previous chapters.

### Strengths

1. **Ports, hosts and networking are handled correctly and explained.** The
   `--host 0.0.0.0` flag, the port mappings, and the container service names
   are all right, and the compose file records the PgBouncer `LISTEN_PORT`
   incident rather than silently fixing it.
2. **Configuration is properly externalised**, with required fields that fail
   fast and a committed `.env.example` that documents every variable without
   containing a secret.
3. **`PYTHONUNBUFFERED=1` is set.** Small, easily forgotten, and the difference
   between having logs after a crash and not.
4. **TLS is conditional on the host being remote**, after an unconditional
   version broke local development. Security that is applied thoughtlessly gets
   switched off entirely; this version survives.
5. **The queue is restricted to JSON**, closing a remote-code-execution class
   without ceremony.
6. **The Dockerfile explains its own constraint** about build context and
   relative paths, so the next reader does not rediscover it.

### Weaknesses

1. **The Windows/Linux split is handled per-command rather than systematically.**
   `./venv/Scripts/python.exe` appears in documentation and agent files; a
   single wrapper script would make every command portable and remove a whole
   category of copied-command failure.
2. **The percent-decoding bug indicates a missing rule.** Two libraries in one
   path with different assumptions about URL encoding is a known hazard; the
   codebase now has `sync_database_url` as a normalisation point for TLS
   spelling, but credential decoding was handled separately, at the call site.
   One connection-parameter builder would own both.
3. **No documented graceful-shutdown behaviour.** Nothing states what happens
   to an in-flight streaming answer when the process is asked to stop. For a
   product whose main interaction is a multi-second stream, that is a real gap
   at deploy time.
4. **Storage defaults to local disk**, which is correct for developer
   convenience and dangerous if a production deployment inherits the default —
   the same shape of risk as `DummyLLMProvider` remaining reachable in
   production, and worth the same treatment: refuse to start with
   `STORAGE_PROVIDER=local` when `ENVIRONMENT=production`.
5. **Health checks are unauthenticated and exempt from CSRF** (they appear in
   `CSRF_EXEMPT_PATHS`), which is normal and correct — but nothing documents
   that the detailed variant must not leak internal state. Worth an explicit
   note, since "detailed health endpoint reveals infrastructure" is a
   well-known finding.

### The one thing to fix first

**Document and implement graceful shutdown.** Everything else on this list is
a paper cut; this one silently corrupts the user experience on every single
deploy, and it becomes visible only after the deployment pipeline exists —
which is the worst possible time to discover it.

---

# Part Q — Interview Questions With Model Answers

**Q1. "What actually happens when you type a URL and press Enter?"**

> The browser parses the URL into scheme, host, port and path. It resolves the
> host to an IP address through DNS, unless it is `localhost`, which is
> special-cased. It opens a TCP connection to that address and port — and if
> the scheme is HTTPS, negotiates TLS first, which verifies the server's
> certificate and agrees a shared encryption key. It then writes an HTTP
> request: a method and path, headers, a blank line, and optionally a body. On
> the server, the operating system delivers the connection to whichever process
> bound that port. That process reads the request, does its work, and writes a
> response with a status line, headers and a body. The browser parses it and
> renders.
>
> The part people miss is that the port is what selects the *process*. That is
> why `--host 0.0.0.0` versus `127.0.0.1` in a container decides whether
> anything outside can reach you at all, and why the failure looks like the
> application is dead rather than like an error.

**Q2. "What is the difference between a process and a thread, and why does it
matter here?"**

> A process is a running program with its own isolated memory. A thread is one
> line of execution inside a process, sharing that memory with the other
> threads.
>
> It matters in two concrete ways in this system. First, the web process and
> the background worker are separate processes, so they cannot pass objects to
> each other — they must serialise jobs through Redis. That is not an
> architectural preference, it is a consequence of memory isolation. Second, we
> use threads deliberately for CPU-heavy model calls, because threads share
> memory and so do not require copying a large model — but that is also why
> shared state between them is dangerous.
>
> We hit a real bug at that boundary: the worker's child processes were created
> by forking a parent that already had open database connections, and a socket
> cannot be meaningfully shared by two processes. Both wrote to it, the protocol
> stream corrupted, and the symptom looked like a database fault.

**Q3. "Why do you keep configuration in environment variables?"**

> Because the same build must run in several places with different databases,
> URLs and keys, and I want the artefact I tested to be the artefact I ship.
> Putting configuration in code means a different build per environment and
> secrets in version control.
>
> Ten of our settings have no default at all, so the process refuses to start
> without them. That was a deliberate choice after a defect where a missing
> secret fell back to a hardcoded development value — anyone who knew that
> string could forge a session for any user. Crashing on boot with a clear
> message is strictly better than booting insecurely.
>
> The consequence is that every environment must supply them, including CI —
> which is why our workflow file declares all ten with test-only values.

**Q4. "How do you debug 'connection refused'?"**

> By the shape of the error before anything else. "Refused" means nothing is
> listening at that address and port — it is not a credentials problem and not
> usually a firewall, which typically produces a timeout instead.
>
> So: is the target process running; is it bound to the port I am using; am I
> using the right hostname for where I am calling from — inside a container
> network the host is a service name, from my own machine it is localhost with
> the *mapped* port; and is the target bound to `0.0.0.0` rather than
> `127.0.0.1`.
>
> We had exactly this: the pooler container defaulted to listening on 5432
> while the health check, the port mapping and the application all targeted
> 6432. It reported unhealthy indefinitely, and because the worker waits for it
> to be healthy, the worker never started. One environment variable fixed it.

**Q5. "Why does it matter that HTTP is stateless?"**

> It is the reason the entire authentication design looks the way it does. A
> stateless protocol means the server does not inherently know that two
> requests are from the same person, so identity has to travel with each
> request. That is why we issue a signed token at login and why the browser
> carries it in a cookie.
>
> But cookies are attached automatically to any request to our domain, whatever
> page triggered it, which creates CSRF — so we add a token the real frontend
> can read and a malicious page cannot. Each defence exists because of the
> previous one.
>
> The upside of statelessness is that any server instance can serve any
> request, which is what makes horizontal scaling possible at all.

---

# Part R — Validation Checklist

Tick honestly. A failure means re-read the section, not push on.

- [ ] I can explain what a byte is and compute the size of 200 embeddings.
      *(A.3, N4)*
- [ ] I can explain why RAM forgetting is the reason databases and files exist.
      *(A.5)*
- [ ] I can state, from memory, the rough ratio between RAM, SSD and a network
      call, and use it to reject a bad optimisation. *(A.7, N5)*
- [ ] I can explain the difference between a program and a process, and why
      two processes cannot share Python objects. *(C.1, C.2)*
- [ ] I can explain why exactly one Celery Beat may run. *(C.2, N6)*
- [ ] I can explain what a shell pipe does and name the same pattern elsewhere
      in this system. *(E.3)*
- [ ] I can explain PATH and why the test command names an interpreter
      explicitly. *(F.2)*
- [ ] I can explain `--host 0.0.0.0` versus `127.0.0.1` in a container, and
      describe the symptom of getting it wrong. *(G.2, N7)*
- [ ] I can read the port map of this repository and explain why PostgreSQL is
      on 5433 outside and 5432 inside. *(G.4, N8)*
- [ ] I can name the four parts of an HTTP request and the five status-code
      families. *(H.3, H.4)*
- [ ] I can explain what TLS protects and what it does not. *(I.2)*
- [ ] I can trace statelessness → cookies → CSRF → CSRF tokens without notes.
      *(H.5, N14)*
- [ ] I can explain why the job queue accepts only JSON. *(J.3, N15)*
- [ ] I can explain what a commit is and why a secret committed once is
      compromised forever. *(M.2, M.3)*
- [ ] **The real test:** I can take any single line from this repository's
      `docker-compose.yml` or `Dockerfile.backend` and explain what it does,
      why it is there, and what would break without it.

If the last box is ticked, you are ready for Chapter 06, where we write our
first line of code — and where every instruction we write will run inside a
process, in memory, on an operating system, that you now understand.

---

*Next: [06-python-from-zero.md](06-python-from-zero.md) — the Python language
itself, from `print("hello")` to the classes, decorators and type hints this
repository uses. No prior programming assumed.*
