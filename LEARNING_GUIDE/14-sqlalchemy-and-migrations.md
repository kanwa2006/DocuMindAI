# 14 — SQLAlchemy and Migrations

**Prerequisites: none.** Every technical word is explained where it appears,
including ones you have met before.

**Estimated study time: 4 hours**, including the exercises and the
build-it-yourself section.

**What you should be able to do at the end:** read any file in
`backend/app/models/`, explain what a session is and when it talks to the
database, spot an N+1 query, explain why this project has two database engines,
write a migration, and answer *"how do you change a database schema safely in
production?"*

---

# Part A — The Problem

## A.1 Two different worlds

Let me re-anchor two things first, because everything here sits between them.

**A database** is a separate program whose job is to store information safely
and answer questions about it. This project uses one called **PostgreSQL**. It
organises everything into **tables** — grids. A **row** is one entry across the
grid (one document, one user). A **column** is one named slot in every row
(`filename`, `status`).

**Python** — the language the server is written in — does not think in grids.
It thinks in **objects**. An object is a bundle of named values that you can
also ask to do things: `doc.filename`, `doc.status`, `doc.mark_ready()`.

So the server holds objects, and the database holds rows, and **something has
to translate between them, in both directions, constantly.**

That gap has a name — the **object–relational impedance mismatch** — and it is
the reason this chapter exists. The name is grand; the problem is simple. Rows
are flat; objects have relationships. Rows have no behaviour; objects do. Rows
are identified by a key column; objects are identified by where they sit in
memory.

## A.2 Doing it by hand

Suppose we translate manually. The lowest-level tool is a **driver** — a small
library that speaks the database's network protocol. For PostgreSQL and Python
that is `psycopg2`. Here is fetching one document with nothing else involved:

```python
import psycopg2

conn = psycopg2.connect(host="localhost", port=5433, dbname="documind",
                        user="postgres", password="secret")
cur = conn.cursor()
cur.execute(
    "SELECT id, filename, status, owner_id FROM documents WHERE id = %s",
    (document_id,)
)
row = cur.fetchone()
cur.close()
conn.close()

if row is None:
    doc = None
else:
    doc = {"id": row[0], "filename": row[1], "status": row[2], "owner_id": row[3]}
```

It works. Now look at what you are actually signing up for:

**1. Rows come back as numbered slots.** `row[1]` is the filename — until
somebody adds a column in the middle and now `row[1]` is something else. **The
meaning of your code depends on the order of columns in a query you wrote
somewhere else.**

**2. You write the translation twice per table.** Once reading, once writing.
Fifty tables is a hundred conversion functions, each a place to make a typo
that no tool can catch.

**3. Connections must be closed by hand.** Miss one `close()` on an error path
and you leak a connection. This deployment has about **fifteen in total**, so a
few hundred failed requests exhaust them and everything hangs.

**4. Every query is a string.** Which leads to the worst problem of all:

```python
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")   # NEVER
```

If somebody registers with the email `' OR '1'='1`, that string becomes
`... WHERE email = '' OR '1'='1'` and returns every user in the system. Worse
inputs delete tables. This is **SQL injection**, and it has been the
number-one web vulnerability for two decades.

*(The safe version above passes `%s` and the value separately, so the database
receives the value as data and can never read it as part of the command.)*

**5. Relationships are entirely manual.** "Give me this chat and its messages"
is two queries and a loop you write yourself, every time.

**6. Nothing knows what you changed.** Modify five objects in memory and you
must remember which five, and write five `UPDATE` statements in the right
order.

## A.3 What we actually want

Something that lets us write this —

```python
doc = await get_document(db, document_id)
doc.status = "READY"
await db.commit()
```

— and produces the correct SQL, with parameters, in the right order, without
either of those three lines mentioning a table.

---

# Part B — What People Tried

## B.1 Raw drivers (1990s onward)

What A.2 showed. Complete control, complete responsibility. **Still the right
answer** for a script that runs one query, or for a query so unusual that any
abstraction fights you.

## B.2 Query builders

The next step: a library that builds SQL from function calls, so you never
concatenate strings.

```python
query = select("id", "filename").from_("documents").where("id = ?", doc_id)
```

Injection is solved. Column order is solved. **But you still map rows to
objects yourself**, and relationships are still manual.

## B.3 ORMs

**ORM** stands for **Object–Relational Mapper**: a library that maps classes to
tables and objects to rows, in both directions, automatically.

A short history, because it explains the shape of every ORM you will meet:

- **Hibernate** (Java, 2001) — introduced the ideas most ORMs still use: a
  session, an identity map, and a "unit of work" that tracks changes.
- **ActiveRecord** (Ruby on Rails, 2004) — made ORMs mainstream by making them
  effortless: `User.find(1)`, and the model *is* the table.
- **SQLAlchemy** (Python, 2006) — deliberately different. Its author, Michael
  Bayer, argued that hiding SQL entirely is a trap, so SQLAlchemy exposes SQL
  as a first-class thing you compose, with the object mapping layered on top.

**That design choice is why this chapter can exist in the order it does.**
Chapter 10 taught SQL; SQLAlchemy's queries look like the SQL you already
know, so you are learning a new spelling rather than a new concept.

## B.4 The promise and the danger

**The promise:** no string building, no manual mapping, automatic change
tracking, relationships you can walk.

**The danger, and it is the reason for Part F:** the code no longer shows you
how many queries it runs. `chat.messages` looks like reading an attribute. It
might be a network round trip. Written in a loop, it might be fifty.

> **An ORM does not remove SQL. It removes the *typing* of SQL, while keeping
> every one of its costs.** Engineers who never learned SQL cannot see those
> costs, which is exactly why Chapter 10 came first.

---

# Part C — What SQLAlchemy Actually Is

## C.1 The mapping, in one table

| In the database | In Python |
|---|---|
| a table (`documents`) | a class (`Document`) |
| a row | an instance (one `Document` object) |
| a column (`filename`) | an attribute (`doc.filename`) |
| a foreign key link | a `relationship()` you can walk |

## C.2 Two layers, and knowing which you are using

SQLAlchemy is really two libraries stacked:

- **Core** — a query builder. Composes SQL safely, returns rows. No objects.
- **ORM** — built on Core. Adds classes, sessions, change tracking,
  relationships.

**You can drop from the ORM to Core at any time**, which matters when a query
gets unusual. This project stays in the ORM almost everywhere, and Chapter 03
recorded the one important consequence of leaving it: the tenancy hook that
filters every query by owner works on ORM queries only. The docstring says so
plainly:

> *"Covers **ORM** SELECTs. A raw `text()` query bypasses it entirely, exactly
> as it bypasses any ORM-level control."*

**Dropping a layer means dropping that layer's protections**, and knowing which
ones is the difference between a deliberate choice and an accident.

## C.3 The base class

Every model class must inherit from one shared class so the library can find
them all. In this project that file is four lines —
[`backend/app/db/base.py`](../backend/app/db/base.py):

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**Inherit** means "this class is a kind of that class, and gets its
behaviour". Every model here says `class Document(Base)`, which does two
things: it gives the class the machinery to map itself to a table, and it
**registers** the class in a shared catalogue called `Base.metadata`.

**That catalogue is load-bearing**, and Part H returns to it: it is how the
migration tool knows what your tables are supposed to look like.

## C.4 A model is a description

Here is a real one,
[`backend/app/models/document.py`](../backend/app/models/document.py):

```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, index=True, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING_UPLOAD, nullable=False)

    owner_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    chat_session_id = Column(UUID(as_uuid=True), index=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

Reading it as a description rather than as code:

- **`__tablename__`** — the table this class maps to. The double underscores
  mark it as something the library looks for rather than an ordinary value.
- **Each `Column(...)`** describes one column: its type, whether it may be
  empty, whether it is indexed, what it defaults to.
- **`primary_key=True`** — the column that uniquely identifies a row.
- **`default=uuid.uuid4`** — Python generates the id. Note there are no
  brackets: it hands over the *function*, so a new value is produced per row
  rather than one value shared by all of them.
- **`server_default=func.now()`** — the *database* fills this in. Different
  from `default`, and deliberately: every application server has its own clock
  and they drift; the database has one.
- **`nullable=False`** on `owner_id` — the database rejects a document with no
  owner. Chapter 03 explained why that is a security control rather than
  tidiness: a code path that forgets to set an owner **fails loudly at the
  database** instead of writing a row nobody owns.

**Two styles you will see in this repository**, because it was written over
time. The older `Column(...)` style above, and the newer typed style in
[`chat.py`](../backend/app/models/chat.py):

```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
```

`Mapped[uuid.UUID]` is a **type annotation** — a note saying what kind of value
this is. It does the same job as the older form, and additionally lets editors
and type checkers understand your models. **New code should use it**; the mixed
styles here are a mild inconsistency noted in the critique.

---

# Part D — The Session

This is the concept people find hardest and the one interviewers probe most, so
it gets the most space.

## D.1 What a session is

**A session is a workspace for talking to the database.** It holds three
things:

1. **A connection** to the database (borrowed from a pool — Part G).
2. **A collection of the objects you have loaded**, called the **identity
   map**.
3. **A record of what you have changed**, so it can write it out later.

The everyday comparison that actually holds: a session is a **shopping
basket**. You add things, change things, remove things, and nothing is charged
until you go to the till. `commit()` is the till.

## D.2 The unit of work

Here is the idea that makes ORMs feel different from writing SQL.

**You do not tell the session what SQL to run. You change objects, and at
commit time the session works out what SQL is needed, in what order.**

```python
doc = await get_document(db, some_id)   # SELECT happens here
doc.status = "READY"                    # nothing happens — a note is taken
doc.filename = "contract-final.pdf"     # still nothing
await db.commit()                       # ONE UPDATE, both columns, then COMMIT
```

Three things the session did without being asked: it noticed which attributes
changed, it combined them into one statement, and it wrapped the whole thing in
a transaction (a group of changes that all happen or none do).

**Why this design?** Because ordering matters. If you create a document and its
pages in one go, the document must be inserted first — the pages point at it.
Working that out by hand, every time, is exactly the kind of thing that is
right ninety-nine times and catastrophic on the hundredth.

## D.3 `flush` versus `commit` — the distinction that confuses everyone

**`flush()` sends the SQL. `commit()` sends the SQL *and* ends the
transaction.**

After a flush, the changes exist inside the database's current transaction —
visible to you, invisible to everyone else, and still undoable. After a commit
they are permanent and visible to everybody.

**Why would you ever want a flush?** Because you need something the database
generates. Here is the real case, in
[`backend/app/workers/tasks/document_tasks.py`](../backend/app/workers/tasks/document_tasks.py):

```python
                page_record = DocumentPage(
                    document_id=doc.id,
                    page_number=p_data["page_number"],
                    extracted_text=p_data["extracted_text"],
                    layout_metadata=p_data["layout_metadata"]
                )
                db.add(page_record)
                db.flush() # Need ID for chunk FK
```

Read the comment. A chunk stores `page_id` — a **foreign key**, a column
pointing at another table's row. To store it, the page's id must exist. The
flush makes the database assign it, without ending the transaction, so if
anything fails later the whole batch still rolls back together.

**The rule:** flush when you need generated values mid-transaction; commit when
the whole unit of work is genuinely finished.

## D.4 The identity map

Within one session, **the same row is always the same object**:

```python
a = await db.get(Document, doc_id)
b = await db.get(Document, doc_id)
a is b        # True — the second lookup returned the object already loaded
```

**Why this matters:** without it, you could hold two copies of one row, change
both differently, and write one on top of the other with no error. The identity
map makes that impossible inside a session. It also means the second lookup is
free — no query at all.

## D.5 A session lives for one request

Chapter 13 showed how each web request gets its own session, in
[`backend/app/db/session.py`](../backend/app/db/session.py):

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

`yield` hands the session to the endpoint and pauses; when the request
finishes, the function resumes and the `async with` block returns the
connection to the pool.

**Why one session per request and not one shared globally?** Three reasons:

1. **Sessions are not safe to share between concurrent requests.** They hold
   one connection and one set of pending changes; two requests would interleave
   into nonsense.
2. **The identity map should not outlive the request**, or you would serve
   yesterday's cached objects.
3. **Failure isolation.** One request's rollback must not discard another's
   work.

**What breaks without the cleanup:** connections are borrowed and never
returned. With fifteen available, a few hundred requests hang the entire
system.

## D.6 One setting worth understanding

```python
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

By default, SQLAlchemy marks every object as **expired** after a commit — so
the next time you read any attribute, it silently re-queries the database to be
sure it is current.

That default is safe and, on an async request path, harmful: reading
`doc.filename` after a commit would trigger a hidden database round trip, and
in async code a hidden query at an unexpected moment is a real source of
confusing errors.

`expire_on_commit=False` says: **after commit, the objects I have keep the
values they had.** Fewer surprises, fewer queries.

**The tradeoff, and you should be able to state it:** if another process
changed that row in the meantime, your object is now stale and you will not
find out until you deliberately refresh it. That is why you see
`await db.refresh(new_doc)` in the upload endpoint — an explicit "go and get
the current values", used exactly where the code needs the database's version.

---

# Part E — Querying

## E.1 It looks like the SQL you already know

Chapter 10 taught `SELECT ... FROM ... WHERE ... ORDER BY ... LIMIT`.
SQLAlchemy mirrors it:

```sql
SELECT * FROM documents
WHERE owner_id = '8f3a...' AND status = 'READY'
ORDER BY created_at DESC
LIMIT 20;
```

```python
stmt = (
    select(Document)
    .where(Document.owner_id == owner_id)
    .where(Document.status == "READY")
    .order_by(Document.created_at.desc())
    .limit(20)
)
result = await db.execute(stmt)
documents = result.scalars().all()
```

- **`select(Document)`** — build a SELECT for that table.
- **`.where(...)`** — chained calls add conditions, combined with AND.
- **`Document.owner_id == owner_id`** does *not* compare anything. It builds a
  description of a comparison, which becomes SQL later. That surprises people
  once and then becomes natural.
- **`await db.execute(stmt)`** actually sends it. `await` means "pause here
  while waiting for the database, and let the server serve other people
  meanwhile".
- **`.scalars()`** — return the objects rather than one-column rows.
- **`.all()`** — as a list. Alternatives: `.first()`, or
  `.scalar_one_or_none()` for "exactly one or nothing", which raises if there
  are two — useful when two would mean a bug.

## E.2 Injection is impossible by construction

This is the single strongest safety argument for a query builder.

```python
.where(Document.filename == user_supplied_text)
```

The value never becomes part of the SQL text. SQLAlchemy sends the statement
and the values **separately**, so the database parses the command first and
then receives the data. There is no arrangement of characters the user can type
that changes what the query means.

**Compare with the string version in A.2**, where the value *is* the query.
That difference is why every professional codebase uses a builder or
parameters, and why "we escape user input carefully" is not an equivalent
answer.

## E.3 A real query, read completely

From [`backend/app/api/v1/endpoints/documents.py`](../backend/app/api/v1/endpoints/documents.py):

```python
    stmt = (
        select(Document)
        .where(Document.workspace_id == ws_uuid)
        .where(Document.owner_id == uuid.UUID(current_user["id"]))
    )
```

Two conditions, and they do different jobs. `workspace_id` is a **filter** —
which category of documents the user asked for. `owner_id` is the **tenant
check** — which documents this person is allowed to see at all.

Chapter 03 covered what happens when someone mistakes the first for the second:
`workspace_id` is derived from a workspace name and is byte-identical for every
user in the system, so filtering on it alone returns everybody's documents.
That confusion produced at least four separate defects in this repository.

---

# Part F — Relationships, and the N+1 Problem

## F.1 Walking a link

A **relationship** lets you follow a foreign key as if it were an attribute.
From [`backend/app/models/chat.py`](../backend/app/models/chat.py):

```python
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
```

Now `session.messages` gives a list of message objects.

Each argument earns its place:

- **`back_populates="session"`** — the other class has a `session` attribute
  pointing back. Setting one side updates the other in memory, so the two
  cannot disagree.
- **`cascade="all, delete-orphan"`** — deleting a chat deletes its messages,
  and removing a message from the list deletes it. Correct here because **a
  message has no meaning without its chat.**
- **`order_by=...`** — messages always come back oldest-first, so no caller has
  to remember to sort. A conversation displayed in the wrong order is not a
  conversation.

## F.2 Lazy loading — the convenience with a bill attached

By default a relationship is **lazy**: it is not fetched until you touch it.

```python
session = await db.get(ChatSession, session_id)   # 1 query
print(session.title)                              # no query — already loaded
for m in session.messages:                        # A QUERY HAPPENS HERE
    print(m.content)
```

That third line looks like reading an attribute. It is a network round trip to
another machine.

**Why lazy loading exists:** most of the time you do not need the related rows,
and fetching them always would be wasteful. **Why it is dangerous:** the cost
is invisible in the code.

## F.3 The N+1 problem, with numbers

```python
sessions = (await db.execute(select(ChatSession).limit(50))).scalars().all()  # 1 query
for s in sessions:
    print(len(s.messages))                                                     # 50 queries
```

**51 queries where 2 would do.**

Why it hurts more than it looks: each query is a round trip. Against a database
on another machine that is 5–20 milliseconds each, and they are *sequential* —
each waits for the last. Fifty of them is half a second to a full second of
nothing but waiting.

**It is called N+1** because you run one query to get N things, then one more
per thing.

**And the reason it is the single most common ORM bug in the world:** the code
looks completely innocent. There is no loop full of SQL. There is a loop, and
an attribute.

## F.4 The real incident

Commit `3daf888` in this repository, and it is worth reading closely because it
contains four separate lessons.

**Defect one:**

> *"`export_tasks.py` issued one SELECT per clause to fetch its redlines,
> inside the clause loop. A 50-clause contract ran 51 queries instead of 2.
> Correct behaviour, wrong shape."*

**"Correct behaviour, wrong shape"** is the phrase to remember. The exports
were right. Nothing was broken. It was just fifty times more expensive than
necessary — the kind of defect that never produces a bug report, only a
gradually slower product.

**Defect two, and this one was on the live request path:**

> *"`research.py` ran a per-document loop issuing one query for the Document
> and another for its chunks: 2N sequential awaited round trips for N
> documents, on a REQUEST-path endpoint. Ten documents in a comparison meant
> twenty round trips against Supabase's pooler before any work began."*

Twenty sequential round trips to a database **in another country**, before the
feature started doing anything.

**The fix was consolidation, not two corrections:**

> *"Both research call sites are now one shared `_load_owned_docs_with_text`
> helper rather than two corrected loops … the two loops were the same code
> twice, and fixing them separately would leave the third copy — whenever it is
> written — free to repeat both defects."*

**And then the part that makes this a great story.** While rewriting the query,
the engineer noticed something the performance finding never mentioned:

> *"THE HELPER ALSO CLOSES A TENANCY HOLE both loops shared … They scoped
> documents by `Document.workspace_id`, which is uuid5 of the workspace SLUG
> and identical for every user. Any authenticated user could pass another
> user's document id and receive its text back inside a generated citation or
> gap analysis."*

**A performance fix uncovered a data leak**, because both live in the same
`WHERE` clause. The commit's reasoning for fixing it there and then: *"leaving
a known cross-tenant read in a predicate I was already editing was not
defensible."*

**The general lesson:** when you open a piece of code that nobody has examined
closely, expect to find more than one problem. Code that has been ignored tends
to have been ignored in several ways at once.

## F.5 The four ways to fix an N+1

**1. `selectinload` — a second query that fetches all the children at once.**

```python
from sqlalchemy.orm import selectinload

stmt = select(ChatSession).options(selectinload(ChatSession.messages)).limit(50)
```

Two queries total, whatever N is. **Usually the right default.**

**2. `joinedload` — one query with a JOIN.**

```python
stmt = select(ChatSession).options(joinedload(ChatSession.messages))
```

One round trip, but the parent's columns are repeated for every child, so a
chat with 200 messages sends its title 200 times. Good for one-to-one; wasteful
for large one-to-many.

**3. Batch by hand with `.in_()`** — what the repository did:

```python
chunks = (await db.execute(
    select(DocumentChunk).where(DocumentChunk.document_id.in_(doc_ids))
)).scalars().all()

by_doc = {}
for c in chunks:
    by_doc.setdefault(c.document_id, []).append(c)
```

One query for all documents, then group in Python. More code, and complete
control — which is why it is chosen when the loading also has to enforce
something, as the tenancy check did here.

**4. Configure the relationship to always load eagerly.** The repository does
this in [`models/org.py`](../backend/app/models/org.py):

```python
    roles = relationship(
        "UserRole",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
```

`lazy="selectin"` means: whenever a user is loaded, fetch their roles too, in
one extra query.

**Why that is right *here* specifically:** roles are checked on essentially
every authenticated request, they are few, and the alternative is a lazy load
firing at an unpredictable moment inside async code. **Set eager loading on a
relationship when you almost always need it; use `selectinload` per query when
you sometimes do.**

## F.6 How the fix was verified — and the guard that was wrong first

The test asserts **query count**, not elapsed time:

> *"Guard `tests/test_n_plus_one_batching.py` asserts query COUNT against
> growing input (1, 5, 20 documents -> exactly 2 queries every time) rather
> than elapsed time, which would be flaky and would not state the property."*

**Counting queries is the correct measurement**, because the property you care
about is *"the number of queries does not grow with the input"*. Timing would
pass or fail depending on the mood of the network.

And then this, which is the most instructive sentence in the whole commit:

> *"The P-1 guard needed correcting before it was trustworthy: its first
> version walked the whole `ast.For` node and flagged the FIXED code, because
> the batched query legitimately sits in the loop's ITERATOR expression, which
> runs once. It now inspects only the loop body."*

**The test declared the correct code broken.** A guard that cannot tell the fix
from the defect is worse than no guard — it teaches the team to ignore it.

Two lessons: **verify your verification**, and remember that a query *inside* a
loop is a bug while a query that *produces* the loop's items is exactly the
fix.

---

# Part G — Engines, Drivers and Pools

## G.1 What an engine is

An **engine** is the object that knows how to reach the database: the address,
the credentials, which driver to use, and a pool of open connections.

A **driver** is the low-level library that speaks the database's network
protocol. Two matter here:

- **asyncpg** — asynchronous, used by the web application.
- **psycopg2** — synchronous, used by the background worker.

## G.2 Why two engines

From [`backend/app/db/session.py`](../backend/app/db/session.py), the project
builds both:

```python
engine = create_async_engine(async_url, ...)          # web application
sync_engine = create_engine(sync_url, ...)            # Celery worker
```

**Why not one?** Because the two programs have different shapes.

The web application is **asynchronous**: one thread serves many requests by
pausing whenever a request waits. That needs a driver that can pause —
asyncpg.

The background worker is **synchronous**: it does one long job at a time in
each process, with no event loop at all. A synchronous driver is simpler and
matches.

`CLAUDE.md` states it as an invariant: *"FastAPI + `asyncpg` on the request
path; Celery uses `SyncSessionLocal` (psycopg2). Never mix."*

**Why "never mix" is a rule rather than advice:** an async call in the worker
has no loop to run on; a synchronous database call on the web path blocks the
single thread and freezes every concurrent request. Both failures appear only
under load, far from the code that caused them.

## G.3 The pool, and the budget

Opening a database connection is expensive — a network handshake, and on the
PostgreSQL side a whole new operating-system process. So engines keep a
**pool**: a small set of already-open connections that requests borrow and
return.

```python
engine = create_async_engine(
    async_url,
    **({} if _is_sqlite else {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }),
    **async_args,
)
```

- **`pool_size`** — how many connections to keep open.
- **`max_overflow`** — how many extra are allowed temporarily under load.
- **`pool_pre_ping=True`** — test a connection before handing it out. Without
  it, a connection the *other* side quietly closed surfaces as a random error
  in the middle of a user's request. With it, the pool notices and reconnects.
- **`pool_recycle=3600`** — throw connections away after an hour, because
  network equipment between you and the database often closes idle connections
  without telling anyone.

**And the numbers are not in this file, deliberately.** They live in
[`core/config.py`](../backend/app/core/config.py), with the reasoning written
out:

```
API    DB_POOL_SIZE 3 + DB_MAX_OVERFLOW 2                      =  5
worker 2 children x (WORKER_DB_POOL_SIZE 1 + OVERFLOW 1)       =  4
beat   1 x (1 + 1)                                             =  2
/health unpooled psycopg2 ping (transient, every 10s)          =  1
                                                                ----
                                                                 12 / 15
```

**Why configuration rather than code:** the ceiling belongs to the deployment,
not the program. The hosted database this project targets allows fifteen
connections for the whole project. A pool size hardcoded in a source file
cannot be adjusted when the tier changes.

The comment in `config.py` records what happened when it *was* hardcoded, at
10 + 20:

> *"Measured with worker and beat stopped, the API held all 15 (14 idle, 1
> active) and nothing else could connect at all: the worker could not drain its
> queue and the /health probe could not open its 16th connection, so the
> container sat 'unhealthy' for 19 hours."*

**Nineteen hours of outage from two numbers in the wrong file.**

## G.4 One more setting, for a specific host

```python
            if _is_supavisor_pooler(url):
                connect_args["statement_cache_size"] = 0
                connect_args["prepared_statement_cache_size"] = 0
```

Some hosted databases put their own pooler in front, which can hand your next
statement to a *different* backend connection. asyncpg normally remembers
prepared statements per connection, so a remembered plan can fail with
"prepared statement does not exist".

You do not need to memorise this. **The transferable lesson is that a pooler
between you and the database changes what your driver may assume**, and those
assumptions fail in ways that look like random database faults.

## G.5 The fork incident, briefly

Chapter 12 covered it in full. In one paragraph: the worker's engine is created
when the module is imported, in the parent process, and the child processes are
made by **copying** that parent — including its open connections. Two processes
writing to one connection corrupt it, and the errors look like database faults
rather than process faults. The fix disposes of the inherited pool in each new
child, with `close=False` so the parent's connections are not severed.

**Why it belongs in this chapter too:** it is a consequence of *where the
engine is created*. Module-level objects are shared by everything that imports
them, including processes you did not know would exist.

---

# Part H — Migrations

## H.1 The problem

You add a column to a model:

```python
    summary = Column(String, nullable=True)
```

The Python class now has it. **The database does not.** The next query
mentioning `summary` fails, because the table has no such column.

So the schema has to change too. How?

## H.2 What people did before, and why it failed

**Option 1: run SQL by hand.** Somebody opens a database console and types
`ALTER TABLE documents ADD COLUMN summary TEXT;`.

It works exactly once, on one database. Then: did anyone run it on the test
database? On the second developer's machine? Was it run *before* or *after* the
new code was deployed? Nobody knows, and there is no record.

**Option 2: a folder of numbered SQL files** that everyone agrees to run in
order. Better — and now you must remember which ones you have already run, and
so must every environment.

**Option 3: let the ORM create the tables from the models** (`create_all()`).
Wonderful for a first run, useless afterwards: it creates missing tables and
**never alters existing ones**, so it cannot add a column to a table that
already has data.

## H.3 What Alembic is

**Alembic is version control for your database schema.** Same idea as Git for
code: a chain of small, ordered, recorded changes, and a record in the database
itself of which ones have been applied.

The pieces:

- **A revision** — one file describing one change, with `upgrade()` and
  `downgrade()` functions.
- **A chain** — each revision names its parent (`down_revision`), forming a
  line of history.
- **A version table** — a real table in your database storing which revision it
  is currently at.
- **`alembic upgrade head`** — apply every revision the database has not yet
  seen.

This project has **46 revision files** in
[`backend/alembic/versions/`](../backend/alembic/versions).

## H.4 A real migration, read line by line

[`2a2aee1828d4_resize_domain_embeddings_to_1024.py`](../backend/alembic/versions/2a2aee1828d4_resize_domain_embeddings_to_1024.py):

```python
"""resize_domain_embeddings_to_1024

C-7 (newly discovered during H-4): every workspace embedding column was
created as vector(1536) (an OpenAI-ada-era scaffold) while the actual
embedding pipeline (embedding_service, bge-m3) produces 1024-dim vectors.
Even after C-1/C-2, inserts and l2_distance comparisons would fail with a
dimension mismatch.

USING NULL is safe here: both writer paths (worker tasks + get_embedding)
were broken since inception, so these columns cannot contain real data in
any deployment that ran this codebase.

Revision ID: 2a2aee1828d4
Revises: d0aab53082d2
"""

revision: str = '2a2aee1828d4'
down_revision: Union[str, None] = 'd0aab53082d2'

_COLUMNS = [
    ("hr_candidates", "embedding"),
    ("legal_clauses", "embedding"),
    ...
]
```

**The defect first**, because it is a good one. An **embedding** is a list of
numbers representing the meaning of a piece of text. The database columns were
declared to hold **1536** numbers — the size produced by an OpenAI model that
an early scaffold assumed. The system actually uses a model producing **1024**.

So every insert into those columns failed on a size mismatch. **Seven tables
across five workspaces, wrong since the day they were created**, and the
features using them had therefore never worked.

**Now the mechanics:**

- **`revision`** — this migration's unique id.
- **`down_revision`** — its parent. These two lines are what make the chain.
- **The docstring is doing real engineering work.** It records what was wrong,
  why, and — crucially — *why the destructive part is safe*.

**That last point is the lesson.** Changing a column's type usually requires
saying what happens to existing data. `USING NULL` means "throw the old values
away". That is normally unacceptable. Here it is safe, and **the migration
proves it rather than asserting it**: both code paths that could have written
to these columns were broken since inception, so no real data can exist.

> **A destructive migration must carry an argument for why the data being
> destroyed cannot exist.** "It is probably fine" is how production data is
> lost.

## H.5 Autogenerate, and why you must read the output

Alembic can compare your models to the live database and write a migration for
you:

```bash
alembic revision --autogenerate -m "add summary column"
```

It works because of the catalogue from C.3. In
[`backend/alembic/env.py`](../backend/alembic/env.py):

```python
from app.db.base import Base
import app.models  # Ensures models are registered for autogenerate

target_metadata = Base.metadata
```

Read the comment on the second line. **Importing `app.models` has no visible
effect and is essential.** A model class only enters the catalogue when its
module is imported. Without that line, models nobody happened to import are
invisible — and autogenerate would cheerfully write a migration *deleting* the
tables it cannot see.

**Autogenerate is a first draft, not an answer.** It reliably detects new
tables, new columns and changed nullability. It regularly misses or mangles
renames — it usually sees "drop column A, add column B", which **deletes your
data** — as well as constraint changes, index details and anything involving
data movement.

> **Always read a generated migration before running it. Every time.**

## H.6 Heads, branches and merges

The chain assumes one line of history. Two people working at once each add a
revision whose parent is the current end — so now there are **two ends**. In
Alembic an end is called a **head**.

Two heads means `alembic upgrade head` does not know where to go.

The fix is a **merge revision**: one revision with two parents. This repository
has them. From
[`2245e3e6d30c_merge_remaining_heads.py`](../backend/alembic/versions/2245e3e6d30c_merge_remaining_heads.py):

```python
revision: str = '2245e3e6d30c'
down_revision: Union[str, None] = ('2a94679787a7', 'a0b1c2d3e4f5')

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
```

Note that it **does nothing** — both functions are empty. Its entire purpose is
to rejoin the history into one line.

And `CLAUDE.md` records the operational consequence:

> *"`alembic/versions/*` — migrations (count drifts; `alembic heads` is
> truth)."*

**"The count drifts"** means: do not judge the state of the schema by counting
files. Some are merges that do nothing; some branches were abandoned. **The
authoritative answer is what the tool says**, which is Part J's first command.

## H.7 Safe and unsafe migrations

This is the part that matters most in production, and it is a favourite
interview question.

**The core difficulty:** the new code and the new schema do not arrive at the
same instant. During a deployment, old code and new code both run for a while.
**Any migration that breaks the old code causes an outage during the deploy.**

**Safe changes** (old code keeps working):

- Adding a nullable column.
- Adding a new table.
- Adding an index — **with care**: on a large table, building one normally
  locks writes. PostgreSQL's `CREATE INDEX CONCURRENTLY` avoids that.

**Unsafe changes** (old code breaks):

- Dropping a column the old code still selects.
- Renaming anything — it is a drop plus an add, from the database's point of
  view.
- Adding a `NOT NULL` column with no default: every existing row violates it
  immediately.
- Narrowing a type.

**The standard safe pattern for a rename, in three deploys**, because it is the
answer interviewers are listening for:

1. **Add** the new column, nullable. Deploy code that writes **both** and reads
   the old one.
2. **Backfill** the new column for existing rows. Deploy code that reads the
   new one and still writes both.
3. **Drop** the old column, once nothing reads it.

Slow, boring, and it never takes the site down.

## H.8 Rollback, and why `downgrade()` is often a lie

Every revision has a `downgrade()`. In practice:

**It usually works for structural changes** — dropping a column you added.

**It usually cannot restore data.** Downgrading a migration that dropped a
column recreates the column, empty. The data is gone.

**And often nobody has ever run it**, so it is untested code that only executes
during an emergency — the worst possible moment to discover a mistake in it.

**How professionals actually roll back**, which is the honest answer to give in
an interview:

1. **Roll back the code, not the schema.** This is why safe migrations matter:
   if the schema change was backward compatible, the previous version of the
   code still runs against it.
2. **Restore from a backup** if data was genuinely lost — which is why backups
   exist, and why this project's missing backup story is a real gap noted in
   Chapter 02.
3. **Write a new forward migration** that undoes the change, tested like any
   other.

---

# Part I — Debugging

**See the SQL that is actually being sent:**

```python
engine = create_async_engine(url, echo=True)
```

Every statement is printed. Never leave it on in production — it is enormous
and it logs your parameters, which are user data.

**Count queries in a test**, which is how the N+1 guard works: hook the
engine's "before cursor execute" event, increment a counter, and assert that
the count does not grow with the input size. **Assert on counts, not on
timings.**

**Ask the database what it is doing right now:**

```sql
SELECT pid, state, query, now() - query_start AS duration
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duration DESC;
```

The first thing to run when everything is slow. Sessions stuck in
`idle in transaction` are the classic cause of connection exhaustion — a
transaction someone opened and never closed.

**Migration state:**

```bash
alembic current      # which revision is this database at?
alembic heads        # what are the ends of the chain? (more than one = trouble)
alembic history      # the chain
alembic upgrade head # apply everything outstanding
alembic downgrade -1 # step back one — read it first
```

**The order to check when a query behaves oddly:**

1. Is the session committed? Uncommitted changes are invisible to everyone
   else, including other requests.
2. Is this an N+1? Count the queries.
3. Is the object stale? With `expire_on_commit=False` your object may be older
   than the database — `refresh()` to be sure.
4. Is the tenant filter present? A missing owner predicate returns *more* rows,
   which looks like working code.
5. Only then read the emitted SQL.

---

# Part J — Production Mistakes

1. **N+1 queries.** The most common by far, and invisible in the code.
2. **Missing `await`.** In async SQLAlchemy this gives you a coroutine object
   where you expected data, and the error appears somewhere unrelated.
3. **Sharing a session between concurrent tasks.** Sessions are not safe to
   share; the symptoms are bizarre and intermittent.
4. **Long transactions.** A transaction held open across a slow API call holds
   one of a very small number of connections.
5. **Hardcoding pool sizes.** Nineteen hours of outage, documented in this
   repository.
6. **Running autogenerated migrations unread**, especially renames — which
   generate as drop-plus-add and destroy data.
7. **Unsafe migrations during a rolling deploy**, where old and new code both
   run.
8. **Trusting `downgrade()`** as a rollback plan.
9. **Forgetting `import app.models` in `env.py`**, so autogenerate cannot see
   half your tables and proposes dropping them.
10. **Mixing sync and async database calls**, which fails only under
    concurrency.

---

# Part K — Build One From an Empty Folder

Thirty minutes. This is not from this project; it is complete and runnable.

```bash
mkdir orm-demo && cd orm-demo
python -m venv venv
./venv/Scripts/activate            # Windows
# source venv/bin/activate         # macOS / Linux
pip install sqlalchemy alembic
```

`models.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List

class Base(DeclarativeBase):
    pass

class Author(Base):
    __tablename__ = "authors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    books: Mapped[List["Book"]] = relationship(back_populates="author",
                                               cascade="all, delete-orphan")

class Book(Base):
    __tablename__ = "books"
    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author_id: Mapped[str] = mapped_column(ForeignKey("authors.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    author: Mapped["Author"] = relationship(back_populates="books")
```

`main.py`:

```python
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload
from models import Base, Author, Book

engine = create_engine("sqlite:///demo.db", echo=True)   # echo shows the SQL
Base.metadata.create_all(engine)                          # fine for a demo only

with Session(engine) as session:
    rowling = Author(name="J. K. Rowling")
    rowling.books.append(Book(title="Book One"))
    rowling.books.append(Book(title="Book Two"))
    session.add(rowling)
    session.commit()

# The N+1, made visible
with Session(engine) as session:
    authors = session.execute(select(Author)).scalars().all()
    for a in authors:
        print(a.name, len(a.books))        # one query PER author

print("---- now the fixed version ----")

with Session(engine) as session:
    authors = session.execute(
        select(Author).options(selectinload(Author.books))
    ).scalars().all()
    for a in authors:
        print(a.name, len(a.books))        # no extra queries
```

Run it and **read the printed SQL**. You will see the extra `SELECT` per author
in the first loop and not in the second. That is the N+1, in front of you, in
thirty lines.

**Then add Alembic:**

```bash
alembic init alembic
```

Edit `alembic/env.py` to point at your models:

```python
from models import Base
target_metadata = Base.metadata
```

and set the database URL in `alembic.ini`:

```
sqlalchemy.url = sqlite:///demo.db
```

Then:

```bash
alembic revision --autogenerate -m "add pages column"
```

after adding `pages: Mapped[int] = mapped_column(default=0)` to `Book`.

**Open the generated file and read it before running `alembic upgrade head`.**
Then try the instructive experiment: **rename** a column in the model,
autogenerate again, and look at what it produced. You will see a drop and an
add — which, on a table with data, would destroy it.

---

# Part L — Exercises

### Level 0 — Understanding

**L1.** In your own words: what is an ORM, and what problem does it solve?

**L2.** Explain the difference between a table, a row, a class and an object.

**L3.** What is a session, using an everyday comparison and then technically?

### Level 1 — Mechanics

**L4.** Explain `flush()` versus `commit()`. Give the real reason
`document_tasks.py` calls `flush()` in its page loop.

**L5.** Why is `expire_on_commit=False` set, and what does the project have to
do because of it?

**L6.** Write the SQLAlchemy for: *documents belonging to owner X, with status
READY, newest first, at most 20*. Then write the SQL it produces.

### Level 2 — The N+1

**L7.** Explain the N+1 problem with a code example and real numbers. Why is it
so easy to miss?

**L8.** Give four ways to fix an N+1 and say when each is the right choice.

**L9.** The repository's guard asserts query *count*, not elapsed time.
Explain why. Then explain how its first version managed to flag the *fixed*
code as broken, and what that teaches.

### Level 3 — Engines and pools

**L10.** Why does this project have two engines? What would break if the worker
used the async one?

**L11.** Explain `pool_pre_ping` and `pool_recycle`. What symptom appears
without each?

**L12.** Reproduce the connection budget arithmetic, and explain why those
numbers live in `config.py` rather than `session.py`.

### Level 4 — Migrations

**L13.** You must rename `documents.filename` to `documents.original_name` on a
live system with users. Write the deployment plan.

**L14.** Read this migration docstring and say what makes the destructive part
defensible: *"USING NULL is safe here: both writer paths were broken since
inception, so these columns cannot contain real data in any deployment that ran
this codebase."*

**L15.** `alembic upgrade head` fails saying there are multiple heads. Explain
how that happened, how to fix it, and why `CLAUDE.md` says the file count
drifts.

---

# Part M — Answer Key

**M1.** An ORM (object–relational mapper) is a library that translates between
database tables and program objects, in both directions. It removes four things
you would otherwise write by hand for every table: building SQL as text (and
the injection risk that comes with it), converting rows into objects and back,
tracking which objects you changed so it can write them out, and following
links between tables. What it does **not** remove is the cost of the queries —
it only removes the typing.

**M2.** A **table** is a grid in the database holding one kind of thing. A
**row** is one entry in that grid. A **class** is a Python description of a kind
of thing. An **object** is one instance of that class, held in memory. The ORM
maps class↔table and object↔row.

**M3.** Everyday: a shopping basket. You add and change things, and nothing is
charged until the till — `commit()`. Technically: a workspace holding a
borrowed database connection, an identity map of the objects it has loaded, and
a record of changes, which it converts into the right SQL in the right order at
commit time.

**M4.** `flush()` sends the SQL but leaves the transaction open, so the changes
exist inside the database but are not permanent and are invisible to others.
`commit()` sends the SQL *and* ends the transaction, making everything
permanent and visible.

`document_tasks.py` flushes because a chunk stores `page_id`, a foreign key
pointing at the page's row — and the page's id is generated when it is
inserted. Flushing makes the database assign that id without ending the
transaction, so if a later page fails, the entire batch still rolls back
together.

**M5.** By default SQLAlchemy expires all objects after commit, so reading any
attribute afterwards silently re-queries the database. On an async request path
that is a hidden round trip at an unpredictable moment. `expire_on_commit=False`
keeps the values the objects already have.

The consequence is that an object can be stale if something else changed that
row, so where the code genuinely needs the database's current values it must
ask — which is why `await db.refresh(new_doc)` appears in the upload endpoint.

**M6.**
```python
stmt = (
    select(Document)
    .where(Document.owner_id == owner_id)
    .where(Document.status == "READY")
    .order_by(Document.created_at.desc())
    .limit(20)
)
documents = (await db.execute(stmt)).scalars().all()
```
```sql
SELECT documents.* FROM documents
WHERE documents.owner_id = $1 AND documents.status = $2
ORDER BY documents.created_at DESC
LIMIT 20;
```
Note `$1` and `$2`: the values travel separately from the statement, which is
why injection is impossible.

**M7.**
```python
sessions = (await db.execute(select(ChatSession).limit(50))).scalars().all()  # 1
for s in sessions:
    print(len(s.messages))                                                     # 50
```
51 queries instead of 2. Each is a sequential network round trip — 5–20 ms
against a remote database — so fifty of them is half a second to a second of
pure waiting.

It is easy to miss because **the expensive line looks like reading an
attribute.** There is no SQL in the loop, no obvious call. The repository's own
case was worse: `research.py` did two queries per document on a request-path
endpoint, so ten documents meant twenty sequential round trips before the
feature started.

**M8.**
1. **`selectinload`** — one extra query fetching all children. The usual right
   default for one-to-many.
2. **`joinedload`** — a single JOIN. Good for one-to-one; wasteful for large
   collections because parent columns repeat per child.
3. **Manual `.in_()` batching** — one query, group in Python. More code, full
   control; chosen when the loading must also enforce something, as the
   repository's tenancy check did.
4. **`lazy="selectin"` on the relationship** — always eager. Right when you
   almost always need the children, as with `User.roles`, which is read on
   nearly every authenticated request.

**M9.** Query count states the actual property — *the number of queries must
not grow with the input* — and is stable. Timing depends on the network and the
machine, so it would be flaky, and a passing time would not prove the shape was
fixed.

The first version of the guard inspected the whole `for` statement, including
the **iterator expression** — the part that produces the items, which runs
once. The batched query legitimately sits there, so the guard flagged the
correct code. It was narrowed to inspect only the loop body.

The lesson: **verify your verification.** A guard that cannot tell the fix from
the defect is worse than none, because it teaches the team to ignore failures.
The distinction it had to learn is real and worth knowing: a query *inside* a
loop is the bug; a query that *produces* the loop's items is the fix.

**M10.** Because the two programs have different shapes. The web application is
asynchronous — one thread serving many requests by pausing whenever one waits —
which needs a driver that can pause, `asyncpg`. The background worker is
synchronous, doing one long job per process with no event loop, so `psycopg2`
matches.

If the worker used the async engine, every call would need an event loop that
does not exist; someone would then add one, and half-async code is where the
worst bugs live. The reverse — synchronous database calls on the web path —
blocks the single thread and freezes every concurrent request, which is exactly
the class of defect Chapter 07 documented three times.

**M11.** `pool_pre_ping=True` tests a pooled connection before handing it out.
Without it, a connection the far side quietly closed is given to a request and
fails mid-work, as an apparently random error the user sees.

`pool_recycle=3600` discards connections after an hour. Without it, network
equipment that silently drops long-idle connections leaves the pool full of
dead ones, so failures cluster after quiet periods — which is confusing,
because the system looks *worse* after being idle.

**M12.**
```
API    3 + 2                        =  5
worker 2 children × (1 + 1)         =  4
beat   1 × (1 + 1)                  =  2
health check ping                   =  1
                                      ----
                                       12 / 15
```
They live in `config.py` because the ceiling belongs to the **deployment**, not
the program: the hosted database allows fifteen for the whole project, and a
different tier allows more. Hardcoding them in `session.py` means they cannot
be changed without editing code — and when they were hardcoded at 10 + 20, the
API alone held all fifteen at rest, the worker could not drain its queue, the
health probe could not connect, and the container sat unhealthy for nineteen
hours.

**M13.** Three deployments, never one:

1. **Add** `original_name` as a nullable column. Deploy code that **writes
   both** columns and **reads `filename`**. Old code still running is unaffected
   because nothing it uses changed.
2. **Backfill**: `UPDATE documents SET original_name = filename WHERE
   original_name IS NULL`, in batches if the table is large. Then deploy code
   that **reads `original_name`** and still writes both.
3. **Drop** `filename`, once you have confirmed nothing reads it — and only
   after the previous release is fully rolled out, so a rollback cannot land on
   code that needs it.

The single-step rename fails because old and new code run simultaneously during
a deploy: the moment the column is renamed, every still-running old instance
breaks. And autogenerate would produce a drop-plus-add, destroying the data.

**M14.** What makes it defensible is that the docstring **proves the data
cannot exist** rather than assuming it. Both code paths capable of writing to
those columns were broken since the columns were created — a size mismatch made
every insert fail — so no deployment that ran this code could have stored
anything there.

That is the standard to hold: a destructive migration must carry an argument
for why the destroyed data cannot exist, not a hope.

**M15.** Two people each added a revision whose parent was the same tip, so the
history has two ends — two heads — and `upgrade head` cannot tell which one you
mean.

Fix it with `alembic merge -m "merge heads" <head1> <head2>`, which creates a
revision with two parents and empty `upgrade`/`downgrade` functions. Its only
job is to rejoin the line.

The file count drifts because some revisions are merges that change nothing and
some branches were abandoned, so the number of files says nothing about the
number of real schema changes. `alembic heads` and `alembic current` are the
truth.

---

# Part N — Senior Critique

### Strengths

1. **Two engines with an explicit invariant** — async on the request path,
   synchronous in workers, never mixed — rather than a hybrid nobody can reason
   about.
2. **Pool sizes are configuration with the arithmetic written down**, after an
   outage caused by hardcoding them.
3. **`pool_pre_ping` and `pool_recycle` are set**, which most projects discover
   only after mysterious connection errors.
4. **The fork-inherited pool is disposed correctly**, with `close=False` and a
   full explanation of why the obvious default would break the parent.
5. **Migrations carry reasoning in their docstrings**, including an explicit
   argument for why a destructive change is safe.
6. **Merge revisions exist and the documentation warns that file counts
   drift** — the honest state of a real migration history.
7. **The N+1 fix consolidated two call sites into one helper** rather than
   correcting each, and closed a tenancy hole found in the same predicate.
8. **The guard asserts query counts, not timings**, and was corrected when it
   proved untrustworthy.

### Weaknesses

1. **Two model styles coexist** — older `Column(...)` and newer
   `Mapped[...]` / `mapped_column(...)`. Both work; the mixture costs a beat of
   reading in every file and prevents type checkers from helping uniformly.
2. **Relationships are underused.** Most models use bare foreign-key columns
   with manual joins, so the ORM's ability to express and cascade links is
   mostly unused — which also means cascade behaviour lives in the database
   only.
3. **No eager-loading policy.** `lazy="selectin"` appears once, correctly;
   everywhere else loading strategy is decided per query, or not decided.
4. **The N+1 guard covers the two known sites**, not the class. A general check
   — no query inside any loop body in request-path modules — would bound the
   family rather than two instances.
5. **`downgrade()` functions are largely untested.** They exist; nothing
   exercises them, so they are emergency-only code that has never run.
6. **No documented migration policy for rolling deploys.** The three-step
   rename pattern is not written anywhere, so the next person will do it in one
   step.
7. **Autogenerate has no review gate.** Nothing in CI flags a generated
   migration containing a `drop_column`, which is the shape a rename takes.

### The one improvement I would make first

**Write down the safe-migration policy** — safe versus unsafe changes, and the
three-deploy rename pattern — in the engineering handbook, and add a CI check
that fails when a migration contains `drop_column` without an explicit
acknowledgement comment. It is an afternoon of work, and it prevents the one
mistake in this chapter that destroys user data rather than merely causing an
outage.

---

# Part O — Interview Questions With Model Answers

**O1. "What is an ORM, and what are its downsides?"**

> A library that maps classes to tables and objects to rows, so I write Python
> instead of SQL strings. It removes string building — which removes SQL
> injection — plus manual row-to-object conversion, and it tracks which objects
> I changed so it can write them out in the right order.
>
> The downside is that it hides cost, not work. `chat.messages` looks like an
> attribute and is a network round trip; in a loop it is fifty. That is the
> N+1 problem, and it is the most common ORM bug there is.
>
> That is exactly why I learned SQL first. An ORM is a spelling convenience
> over SQL, and if you cannot see the SQL it is producing, you cannot see what
> it costs.

**O2. "What is a session?"**

> A workspace for talking to the database. It holds a borrowed connection, an
> identity map so the same row is always the same object, and a record of what
> I changed.
>
> The important idea is the unit of work: I do not write UPDATE statements, I
> change objects, and at commit time the session works out the right SQL in the
> right order — which matters because inserts have to happen in dependency
> order.
>
> We give each web request its own session, created by a dependency that yields
> it and returns the connection to the pool afterwards. They cannot be shared
> between concurrent requests, because a session holds one connection and one
> set of pending changes.

**O3. "Explain the N+1 problem and how you would fix it."**

> You fetch N things with one query, then touch a relationship on each one,
> which issues one query per item — N+1 instead of 2. They are sequential
> network round trips, so fifty of them is easily half a second of pure
> waiting.
>
> We had it twice. An export ran 51 queries for a 50-clause contract, and a
> research endpoint on the request path ran two queries per document, so ten
> documents meant twenty sequential round trips before any work started.
>
> The fixes are `selectinload` for a second batched query, `joinedload` for a
> single JOIN when the child set is small, manual `.in_()` batching when you
> need full control, or configuring the relationship eager if you almost always
> need it.
>
> We used manual batching in one helper shared by both call sites, because the
> loading also had to enforce a tenancy check — and the test asserts the query
> *count* stays at two for 1, 5 and 20 documents, rather than asserting a time,
> because a count states the property and a timing is flaky.

**O4. "How do you change a database schema safely in production?"**

> With migrations — versioned, ordered, recorded changes, so every environment
> reaches the same state and the database itself records where it is.
>
> The hard part is that during a rolling deploy, old and new code run at the
> same time, so the schema change must not break the old code. Adding a
> nullable column or a new table is safe. Dropping, renaming or narrowing is
> not.
>
> For a rename I would do three deploys: add the new column nullable and write
> both; backfill and switch reads to the new one; drop the old column once
> nothing reads it. Slow and boring, and it never takes the site down.
>
> I would also read every autogenerated migration before running it —
> autogenerate turns a rename into a drop plus an add, which destroys the data.

**O5. "How do you roll back a migration?"**

> Honestly, usually I do not — I roll back the *code*. That is the real reason
> to keep migrations backward compatible: if the schema change was safe, the
> previous release still runs against it.
>
> `downgrade()` functions exist, but they can only undo structure, not data. A
> downgrade that recreates a dropped column gives you an empty column. And they
> are usually untested, so they are code that first runs during an emergency.
>
> So: roll back the code if the schema allows it; restore from backup if data
> was lost; otherwise write a new forward migration that undoes the change and
> test it like anything else.

**O6. "Why does your project have two database engines?"**

> Because the web application and the background worker have different shapes.
> The API is asynchronous — one thread serving many requests by pausing
> whenever one waits — so it uses `asyncpg`, a driver that can pause. The
> Celery worker is synchronous, one long job per process with no event loop, so
> it uses `psycopg2`.
>
> It is written down as an invariant — never mix — because half-async code
> fails only under load and far from the cause. A synchronous database call on
> the request path blocks every concurrent request, which we hit three times in
> other forms.
>
> The pool sizes also differ, and they live in configuration rather than code,
> because the ceiling belongs to the deployment: our hosted database allows
> fifteen connections for the whole project, and each worker child has its own
> pool. When those numbers were hardcoded at ten plus twenty, the API alone
> held all fifteen at rest and the container sat unhealthy for nineteen hours.

---

# Part P — Validation Checklist

- [ ] I can explain what an ORM is and name two things it does *not* remove.
      *(B.4, M1)*
- [ ] I can explain what a session is, using both an everyday comparison and
      the technical description. *(D.1, D.2)*
- [ ] I can explain `flush()` versus `commit()` and give the real reason the
      worker flushes mid-loop. *(D.3)*
- [ ] I can explain `expire_on_commit=False` and what the project must do
      because of it. *(D.6)*
- [ ] I can write a filtered, ordered, limited query in SQLAlchemy and say what
      SQL it produces. *(E.1, M6)*
- [ ] I can explain why injection is impossible with a query builder. *(E.2)*
- [ ] I can spot an N+1, explain it with numbers, and give four fixes. *(F.3,
      F.5)*
- [ ] I can explain why the guard asserts counts, and how it once flagged the
      fixed code. *(F.6, M9)*
- [ ] I can explain why there are two engines, and what the pool settings do.
      *(G.2, G.3)*
- [ ] I can reproduce the connection budget and say why it lives in
      configuration. *(G.3, M12)*
- [ ] I can explain what a migration is, what a head is, and why merge
      revisions exist. *(H.3, H.6)*
- [ ] I can write the three-deploy rename plan without notes. *(H.7, M13)*
- [ ] I can explain why `downgrade()` is not a rollback plan. *(H.8)*
- [ ] **I built the demo in Part K, saw the N+1 in the printed SQL, and
      autogenerated a migration for a rename to see what it produces.**
- [ ] **The real test:** open
      [`db/session.py`](../backend/app/db/session.py),
      [`models/chat.py`](../backend/app/models/chat.py) and one file in
      [`alembic/versions/`](../backend/alembic/versions). Explain every engine
      argument, every relationship option, and — for the migration — its
      revision, its parent, what it changes, and whether it is safe to run
      during a rolling deploy.

If the last two boxes are ticked, you can read and change the data layer of
this system — and Chapter 15 can be about who is allowed to see what.

---

*Next: `15-auth-and-security.md` — passwords, tokens, cookies, CSRF, tenancy
and the attacks this system is actually exposed to, including one that arrives
inside the documents themselves.*
