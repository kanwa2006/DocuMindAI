# 13 — FastAPI: How a Request Becomes Python

**Prerequisites: none.** Every technical word is explained in the sentence
where it first appears, even if you have met it before.

**Estimated study time: 4 hours**, including the exercises and the build-it-
yourself section.

**What you should be able to do at the end:** open any file in
`backend/app/api/` and explain what it does and why it exists; answer *"walk me
through your backend"* and *"walk me through one API request"* without notes;
work out why a request failed from its status code alone; and write a small
working backend from an empty folder.

---

# Part A — What Is a Web Framework?

## A.1 Start with what you actually have

Strip everything away. Here is the raw situation.

Somewhere there is a computer running a program. Another computer — someone's
laptop, running a browser — wants something from it. The two are connected by a
network, and a network can carry only one thing: **bytes**. Numbers, in order.

The program on the server can ask the operating system for a **socket**, which
is the programming object representing one end of a network connection. Through
that socket, bytes arrive. Here is exactly what arrives when someone visits a
page:

```
GET /api/v1/documents?workspace_id=legal HTTP/1.1
Host: localhost:8000
Cookie: token=eyJhbGciOiJIUzI1NiJ9...
Accept: application/json

```

That is it. A blob of text. **Your program's job is to turn that text into a
useful reply**, and send back another blob of text.

## A.2 Everything you would have to write yourself

Suppose you decided to do it by hand, with no library at all. Here is your
to-do list, and it is worth reading slowly because **every item on it is a
feature of the framework we are about to learn**:

1. **Open a socket, listen on a port, accept connections.** A **port** is a
   number identifying which program on the machine a message is for.
2. **Read bytes until you have the whole request** — which means knowing where
   a request ends, which means parsing the headers to find the `Content-Length`
   before you know how much more to read.
3. **Parse the first line** into a method (`GET`), a path (`/api/v1/documents`)
   and a version.
4. **Parse the query string** — `?workspace_id=legal` — undoing the special
   encoding that lets it contain spaces and symbols.
5. **Parse every header line** into a name and a value.
6. **Parse cookies**, which are one header containing several values in their
   own format.
7. **Read the body**, if any, and decode it — usually JSON text into real
   values.
8. **Decide which piece of your code handles this path**, out of two hundred.
9. **Check who the user is**, on every request.
10. **Validate the input** — is `workspace_id` a real workspace? Is `top_k` a
    number?
11. **Run your actual logic** — the two lines you cared about.
12. **Turn the result back into text**, in a shape the browser expects.
13. **Build a reply** with a status line, headers, a blank line and the body.
14. **Handle errors** so one bad request does not kill the server for everyone.
15. **Do all of this for hundreds of people at once.**

**Steps 1 to 10 and 12 to 15 are identical for every application in the
world.** Only step 11 is yours.

## A.3 So: what is a framework?

**A web framework is a program that does all of those steps for you, and calls
your code for step 11.**

That last part is the definition that matters and it deserves emphasis. With a
plain library, *you* call *it*. With a framework, **it calls you**. You write
functions and register them; the framework decides when to run them.

This is sometimes called **inversion of control** — the control flow is
inverted compared to a normal program. It is why framework code can feel
strange at first: you never see the loop that runs your functions, because it
is not yours.

---

# Part B — Where This Came From

The history is short and it explains every design decision in FastAPI.

## B.1 CGI (1993): one process per request

The first standard was **CGI** — Common Gateway Interface. The web server
received a request and **started a whole new program** for it, handed the
request in through environment variables and standard input, and read the reply
from standard output.

**Why it was good:** any language could be used. Your program did not need to
know anything about networks.

**Why it died:** starting a process takes milliseconds and its own memory
(Chapter 05: a **process** is a running program with its own private memory).
A hundred simultaneous visitors meant a hundred processes. The machine spent
more time creating and destroying programs than answering anyone.

## B.2 WSGI (2003): one standard, many frameworks

The obvious fix is to keep one long-running program and let it handle requests
in a loop. Python people did that — and immediately created a new problem:
**every framework invented its own way of talking to every web server.** Ten
frameworks and five servers meant fifty combinations, most of which did not
exist.

**WSGI** — Web Server Gateway Interface — fixed it with an agreement so simple
it is almost silly. Your application is **a function that takes two arguments
and returns bytes**:

```python
def application(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Hello, world"]
```

`environ` is a dictionary of everything about the request. `start_response` is a
function you call with the status and headers. You return the body.

**That is a complete, working, standards-compliant Python web application.**
Any WSGI server can run it.

**What the standard bought**, and this is a lesson about standards generally:
suddenly any framework worked with any server. Django, Flask and dozens of
others could be deployed on Gunicorn, uWSGI or Apache, interchangeably.
**Agreeing on one small interface turned a fifty-combination problem into
five-plus-ten.**

## B.3 Why WSGI eventually was not enough

WSGI has one property baked into its shape: **the function returns the whole
response and then it is finished.** Synchronous, one request per worker at a
time.

By the mid-2010s three things had become normal that WSGI could not do well:

1. **Long-lived connections.** WebSockets — a two-way connection that stays
   open — do not fit "take a request, return a response".
2. **Streaming.** Sending a response gradually over ten seconds means a worker
   is blocked for ten seconds. Ten users, ten blocked workers.
3. **Waiting efficiently.** Most of a modern request is *waiting* — for a
   database, for another service. Under WSGI a waiting worker is a wasted
   worker, so you buy workers to hold waiting.

## B.4 ASGI (2018): the asynchronous standard

**ASGI** — Asynchronous Server Gateway Interface — is WSGI redesigned for
waiting. The application is again a single function, but with three arguments
and the ability to pause:

```python
async def application(scope, receive, send):
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": b"Hello, world"})
```

- **`scope`** describes the connection — what kind, which path, which headers.
- **`receive`** is a function you await to get the next incoming message.
- **`send`** is a function you await to send one outgoing message.

Three consequences follow, and all three are why this project can do what it
does:

1. **A response is sent as several messages**, so streaming is natural rather
   than bolted on.
2. **`async` means a request can pause while waiting**, letting the same worker
   serve someone else meanwhile.
3. **`scope` describes any connection type**, so WebSockets fit the same shape.

**A quick anchor on `async` and `await`**, since they are about to appear
everywhere: `async def` marks a function that is allowed to pause. `await X`
means *"start X, and while it is waiting, let other work run; wake me when it
is done."* There is still only one thread — nothing is happening
simultaneously — but waiting overlaps, which is where the capacity comes from.

## B.5 Where FastAPI fits

**FastAPI** was released in 2018 by Sebastián Ramírez. It is built on top of
two existing pieces rather than from scratch:

- **Starlette** — a small ASGI toolkit providing routing, requests, responses,
  middleware and the WebSocket plumbing.
- **Pydantic** — a library that validates data using Python's type annotations.

**FastAPI is essentially the observation that those two things belong
together.** If Pydantic can already turn a type annotation into a validation
rule, and Starlette can already route requests, then a function signature like
this:

```python
async def create_document(body: DocumentRequest) -> DocumentResponse:
```

contains everything needed to: parse the body, validate it, reject bad input
with a helpful error, convert the result to JSON, **and** write the API
documentation. All from information the programmer was going to write anyway.

**Why it became popular so quickly**, in order of importance:

1. **The types do triple duty** — validation, editor autocompletion, and
   documentation — with no extra work.
2. **Async by default**, arriving exactly when Python teams needed streaming
   and high-concurrency I/O.
3. **Automatic interactive documentation**, which we will meet in Part K.
4. **Small surface area.** You can learn the useful 90% in an afternoon.

## B.6 The honest comparison

| | Flask | Django | FastAPI |
|---|---|---|---|
| Year | 2010 | 2005 | 2018 |
| Style | minimal, you assemble it | batteries included | minimal, typed |
| Async | added later, partial | added later, partial | native |
| Validation | you write it | forms and models | from type hints |
| Built-in admin, ORM, auth | no | **yes** | no |
| Best for | small services | content-heavy applications with a database | APIs, especially async and typed |

**Why this project chose FastAPI**, honestly:

- The request path is dominated by *waiting* — for PostgreSQL, for Google's
  model API. Chapter 07 measured about 86% of a question's time as waiting.
  Native async is worth a great deal here.
- Answers **stream** token by token, which ASGI makes natural.
- The API contract is large — 24 endpoint modules — so automatic validation and
  documentation pay for themselves.

**When Django would be the better choice:** a content site needing an admin
panel, user management and an ORM out of the box. Django gives you a working
application in an afternoon; FastAPI gives you an excellent API and expects you
to choose everything else. **Neither is better. They optimise for different
products.**

---

# Part C — The Four Pieces in This Project

Four names appear in the startup command and in the code, and beginners
routinely confuse them. Here is what each one is:

| Piece | What it is | What it does here |
|---|---|---|
| **Uvicorn** | an ASGI **server** | owns the socket, speaks HTTP, calls the app |
| **Starlette** | an ASGI **toolkit** | routing, request/response objects, middleware |
| **FastAPI** | a **framework** on Starlette | dependency injection, validation, docs |
| **Pydantic** | a **validation library** | turns type annotations into runtime checks |

The layering, from the network inwards:

```
network bytes
      ↓
   Uvicorn        parses HTTP, builds `scope`, calls the ASGI app
      ↓
  Middleware      runs on every request, in order (Part H)
      ↓
   FastAPI        matches the path, resolves dependencies, validates input
      ↓
 your function    the ten lines you actually wrote
      ↓
   Pydantic       converts the returned object to JSON
      ↓
   Uvicorn        writes the reply bytes back to the socket
```

**And the command that starts it all**, from the compose file:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Word by word:

- `uvicorn` — the program.
- `app.main:app` — *in the module `app.main`, use the object named `app`*. The
  first `app` is the folder; the second is the variable.
- `--host 0.0.0.0` — accept connections on every network interface. Inside a
  container this is essential: `127.0.0.1` would mean "only from inside this
  container", and the request would be refused with no error in the application
  log because it never arrived.
- `--port 8000` — which port number to listen on.

---

# Part D — The Complete Life of One Request

This is the centrepiece of the chapter. One request, seventeen steps, each
mapped to real code. **This is the answer to "walk me through one API
request".**

The request: a logged-in user opens their Legal workspace, and the page asks
for their documents.

### Step 1 — The browser builds a request

The page calls the project's one network wrapper,
[`frontend/src/lib/api.ts`](../frontend/src/lib/api.ts), which attaches the
CSRF header and tells the browser to include cookies. The resulting bytes:

```
GET /api/v1/documents?workspace_id=legal HTTP/1.1
Host: localhost:8000
Cookie: token=eyJhbGciOiJIUzI1NiJ9...; csrf_token=a7f3...
```

### Step 2 — Finding the machine

The browser resolves the host name to a numeric address. `localhost` is
special-cased to `127.0.0.1`, meaning "this same machine", so no lookup goes
anywhere.

### Step 3 — Opening a connection

The browser opens a **TCP** connection to that address on port 8000. TCP is the
protocol that turns unreliable network packets into a reliable, ordered stream
of bytes.

The operating system on the receiving side sees a connection arriving for port
8000, finds the process that claimed that port — Uvicorn — and hands it over.

### Step 4 — Uvicorn parses the HTTP text

Uvicorn reads the bytes and turns them into a `scope` dictionary: the method,
the path, the query string, the headers. **All of item 2–6 from Part A's to-do
list happens here**, and none of it is your code.

### Step 5 — The middleware chain

Before any of your endpoint code runs, the request passes through several
layers of code that run on *every* request. From
[`backend/app/main.py`](../backend/app/main.py):

```python
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(DeviceFingerprintMiddleware)
```

Part H explains each one, and the surprising thing about their order.

### Step 6 — FastAPI matches the path

FastAPI compares `/api/v1/documents` against its registered routes and finds
the `list_documents` function. If nothing matched, it would return **404 Not
Found** here — before any of your code runs.

### Step 7 — Dependencies are resolved

The function's signature says what it needs:

```python
async def list_documents(
    workspace_id: Optional[str] = Query(None),
    chat_session_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
```

FastAPI reads this and **works out where each argument comes from**:

- `workspace_id` — from the query string, optional, default `None`.
- `chat_session_id` — likewise.
- `current_user` — from calling `get_current_user`.
- `db` — from calling `get_db`.

Part G is entirely about this.

### Step 8 — Authentication happens inside a dependency

`get_current_user` runs, in [`backend/app/core/auth.py`](../backend/app/core/auth.py):

```python
async def get_current_user(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = AuthProvider.verify_token(token)
    _set_request_owner(user["id"])
    return user
```

It reads the cookie, checks the token's mathematical seal, and — importantly —
binds the current user into a place the database layer reads automatically, so
that every query is filtered to this user without any endpoint remembering to
do it.

**If the token is missing or invalid, it raises here.** The endpoint function
never runs. That is the point: authentication is a wall in front of the
handler, not a check inside it.

### Step 9 — A database session is created

`get_db` runs, in [`backend/app/db/session.py`](../backend/app/db/session.py):

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

A **session** is a workspace for database operations. This borrows one from a
small pool of connections and hands it over. The `yield` is important and Part
G.3 explains it.

### Step 10 — Your function finally runs

```python
    effective_workspace = workspace_id or current_user.get("workspace_id", "general")
    ws_uuid = resolve_workspace_id(effective_workspace)

    stmt = (
        select(Document)
        .where(Document.workspace_id == ws_uuid)
        .where(Document.owner_id == uuid.UUID(current_user["id"]))
    )
```

Ten lines of actual product logic. Everything before this was infrastructure,
and everything after it is too.

### Step 11 — The database is asked

The query goes out over another socket to PostgreSQL. The function **pauses**
here — `await` — and Uvicorn spends that time serving other people's requests.

### Step 12 — Rows come back and become Python objects

The database returns rows; the ORM turns them into `Document` objects.

### Step 13 — The function returns

It returns a list of those objects.

### Step 14 — Serialisation

**Serialisation** means turning live objects into text that can travel over a
network. FastAPI converts the list into JSON. If the endpoint declares a
`response_model`, it also *filters* the output to exactly those fields — which
is a security feature, covered in Part F.

### Step 15 — The response travels back out through the middleware

The onion unwinds. Each middleware gets a chance to modify the response —
adding the security headers and the correlation id.

### Step 16 — Uvicorn writes the reply

```
HTTP/1.1 200 OK
content-type: application/json
x-correlation-id: 4f2c8e1a-...
x-content-type-options: nosniff

[{"id":"0a56...","filename":"contract.pdf","status":"READY", ...}]
```

### Step 17 — The browser turns it back into data and redraws

`await res.json()` in the browser, and the document list appears.

**Seventeen steps. You wrote step 10.** That is what a framework is for.

---

# Part E — Routing

## E.1 What routing is

**Routing is deciding which of your functions handles a given path and
method.**

With two hundred endpoints, something must map `GET /api/v1/documents` to one
specific function, and do it quickly.

## E.2 The smallest possible example

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def say_hello():
    return {"message": "hi"}
```

`@app.get("/hello")` is a **decorator** — a line starting with `@` above a
function that does something to it. Here it registers the function as the
handler for `GET /hello`. **The decorator is the registration**; the function
itself is ordinary.

Returning a dictionary is enough — FastAPI converts it to JSON automatically.

## E.3 Routers, and why this project has 24 of them

Putting two hundred endpoints in one file would be unmanageable. An
**APIRouter** is a group of related endpoints that can be attached to the
application as a unit.

Each endpoint file creates one:

```python
# backend/app/api/v1/endpoints/csrf.py
from fastapi import APIRouter, Response

router = APIRouter()

@router.get("/csrf-token")
async def get_csrf_token(response: Response):
    ...
```

And one file assembles them all, in
[`backend/app/api/v1/api.py`](../backend/app/api/v1/api.py):

```python
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
...
```

Then `main.py` attaches the whole thing once:

```python
app.include_router(api_router, prefix=settings.API_V1_STR)
```

**Follow one path through all three levels**, because this is how every address
in the system is built:

```
"/api/v1"          from settings.API_V1_STR, applied in main.py
    + "/documents" from the include_router prefix in api.py
    + "/{document_id}"  from the decorator in documents.py
    = /api/v1/documents/{document_id}
```

**Three benefits of this structure, and they are worth naming:**

1. **One file per subject** — 24 manageable files instead of one enormous one.
2. **The version number appears exactly once.** Moving to `/api/v2` is one
   line.
3. **`tags` groups endpoints in the documentation** (Part K).

**And one deleted line worth reading**, because it teaches something:

```python
# L-7: the ws WebSocket router was removed — the product streams over SSE
# and no frontend code ever opened a WebSocket (dead surface).
```

A whole feature existed, was registered, appeared in the documentation, and
**no client ever used it**. Every endpoint you expose is a surface that must be
secured, tested and maintained. **Deleting the dead one is engineering work,
not tidying**, and recording why is what stops someone adding it back.

## E.4 The three places input comes from

Every piece of input arrives in one of three ways, and FastAPI decides which by
looking at your function's signature.

**Path parameters** — part of the address itself:

```python
@router.get("/{document_id}")
async def get_document(document_id: str, ...):
```

The name in the braces matches the parameter name. `GET /api/v1/documents/0a56…`
gives `document_id = "0a56…"`.

*Use them for identifying a specific thing.*

**Query parameters** — after the `?`:

```python
async def list_documents(
    workspace_id: Optional[str] = Query(None),
    chat_session_id: Optional[str] = Query(None),
    ...
```

`GET /api/v1/documents?workspace_id=legal` gives `workspace_id = "legal"`.
`Query(None)` means optional with a default of nothing.

*Use them for filtering, sorting and paging — things that modify a request
rather than identify a resource.*

**The request body** — a block of JSON sent with the request:

```python
@router.post("/stream")
async def stream_query(request: Request, body: QueryRequest, ...):
```

Because `QueryRequest` is a Pydantic model (Part F), FastAPI knows this comes
from the body, parses it, validates it, and rejects it with a clear error if it
is wrong.

**The rule FastAPI applies**: a parameter whose name matches a path placeholder
is a path parameter; a parameter of a simple type (`str`, `int`) is a query
parameter; a parameter that is a Pydantic model is the body.

## E.5 The prefix invariant, and the bug it prevents

`CLAUDE.md` records this as an architectural rule:

> *"All routes under `/api/v1`. `NEXT_PUBLIC_API_URL` already includes it;
> endpoint strings in `lib/api.ts` start with `/` and **omit** `/api/v1`."*

The browser's base address already ends with `/api/v1`. So a frontend call
writes `/documents`, not `/api/v1/documents`.

**Write it twice and you get `/api/v1/api/v1/documents`**, which matches no
route, so FastAPI returns 404 — and the developer, seeing "not found", goes
looking for a missing endpoint that exists perfectly well.

**The general lesson:** when a value is composed from several places, write
down where each piece comes from. A 404 caused by a doubled prefix looks
identical to a 404 caused by a missing route, and only one of them is real.

---

# Part F — Validation With Pydantic

## F.1 The problem

Anchor: the **client** is the program making the request, and it is under the
user's control. Anyone can change what their browser sends, or bypass the
browser entirely with a command-line tool.

So every value arriving from outside is a claim, not a fact. `top_k` might be
`"twelve"`, or `-5`, or `999999`. `query` might be missing entirely.

**Without validation, those become crashes deep inside your logic** — or worse,
they do not crash and produce nonsense.

## F.2 What Pydantic does

**A Pydantic model is a class of typed fields that checks and converts data at
runtime.** Here is the real one, from
[`backend/app/schemas/query.py`](../backend/app/schemas/query.py):

```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

class QueryRequest(BaseModel):
    query: str
    workspace_id: Optional[UUID] = None
    session_id: Optional[str] = None
    workspace_type: Optional[str] = "general"
    top_k: int = 5
    similarity_threshold: float = 0.0
    comparison_mode: bool = False
```

Because it inherits `BaseModel`, this does real work when a request arrives:

- **`query: str` with no default is required.** A request without it is
  rejected before your code runs.
- **`top_k: int = 5`** is optional and defaults to 5. `"twelve"` is rejected;
  `"12"` is *converted* to the number 12.
- **`workspace_id: Optional[UUID]`** — text that is not a valid UUID is
  rejected; valid text becomes a real UUID object.

**The word "before" is the whole value.** By the time your function's first
line runs, every field is present, of the right type, and converted. There is
no defensive checking inside the handler because there is nothing left to
check.

## F.3 Where the 422 comes from

Send a bad request and FastAPI replies **422 Unprocessable Entity** with a body
telling you precisely what was wrong:

```json
{
  "detail": [
    {
      "loc": ["body", "top_k"],
      "msg": "Input should be a valid integer",
      "type": "int_parsing"
    }
  ]
}
```

`loc` is the location of the problem. **You did not write any of this**, and it
is better than most hand-written validation because it reports *every* problem
rather than the first.

**Which status code means what**, since this is a common interview question:

- **422** — the shape is wrong (a string where a number belongs).
- **400** — the shape is fine but the value makes no sense in context.
- **404** — no such thing (or, deliberately, "not yours" — see I.5).

You can see the project making that distinction in
[`core/document_access.py`](../backend/app/core/document_access.py), which
raises 422 for an unparseable id and 404 for one that parses but is not the
caller's.

## F.4 Response models

The same idea in the other direction:

```python
@router.post("/ask", response_model=QueryResponse)
async def ask_question(...) -> Any:
```

`response_model` does three things:

1. **Converts** the returned object to JSON.
2. **Filters** it to exactly the declared fields.
3. **Documents** the response shape automatically.

**Number 2 is a security feature and people miss it.** If your function returns
a `User` object containing `hashed_password`, and the response model does not
list that field, **it is not sent**. The filter is at the boundary, so no
handler can leak a field by accident.

## F.5 Why this is a choke point

Chapter 03 introduced the idea of a **choke point** — one place every path must
pass through, so a rule is enforced once instead of many times.

Pydantic models are the choke point for *data validity*. Every assumption your
code makes about the shape of a request is checked here, once, rather than
re-checked (or forgotten) in twenty handlers.

**And it is the counterpart to the frontend's TypeScript.** Chapter 09
established that TypeScript is erased before the program runs, so it checks
your code against itself and never against the data a client actually sends.
Pydantic checks the data. **Compile-time checking protects you from your
mistakes; runtime validation protects you from the world's.**

---

# Part G — Dependency Injection

## G.1 The problem

Almost every endpoint needs the same two things: a database session, and the
identity of the current user.

Without help, every function would begin identically:

```python
async def list_documents(request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(401)
    user = verify_token(token)
    session = AsyncSessionLocal()
    try:
        ...  # the actual work
    finally:
        await session.close()
```

Six lines of setup before anything useful, repeated in two hundred functions,
each an opportunity to forget the `finally`, or the auth check, or both.

## G.2 What dependency injection is

The name sounds heavy. The idea is not.

**Dependency injection means: instead of a function fetching what it needs, it
declares what it needs and something else provides it.**

An everyday comparison. "Fetching" is arriving at a hotel and being told to go
and find a room, clean it and make the bed. "Injection" is being handed a key
to a prepared room. You state what you need — a room for two nights — and the
system provides it.

In FastAPI you declare it in the signature:

```python
async def list_documents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

`Depends(f)` means *"before running me, call `f` and give me its result"*.

## G.3 It is not magic

This is worth being blunt about, because "dependency injection" sounds like a
mysterious framework capability. It is not.

**FastAPI reads your function's parameters, sees the `Depends` markers, calls
those functions first, and passes the results in.** That is the entire
mechanism. If you wrote the framework yourself, you would write roughly:

```python
kwargs = {}
for name, dep in dependencies.items():
    kwargs[name] = await dep()
result = await endpoint(**kwargs)
```

Nothing more.

## G.4 The database dependency, and why it uses `yield`

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

Anchor: `yield` hands a value out and **pauses the function**, keeping its
local state, until somebody asks it to continue.

That is exactly the shape needed here:

- Everything **before** `yield` is setup — borrow a connection from the pool.
- The value is handed to your endpoint.
- Everything **after** `yield` — here, the exit of the `async with` block — is
  cleanup, and FastAPI runs it when the request finishes.

**Why not a plain function?** Because a plain function can only hand something
over. It cannot get control back afterwards to clean up. The `yield` is what
creates an "after".

**What breaks without it:** connections are borrowed and never returned. This
deployment has a budget of about fifteen database connections in total, so a
few hundred requests would exhaust them and every later request would hang
waiting for one.

## G.5 Authentication as a dependency

```python
current_user: dict = Depends(get_current_user)
```

Three things happen because auth is a dependency rather than a line inside the
handler:

1. **It runs before the handler.** An unauthenticated request never reaches
   your code.
2. **It can refuse.** Raising `HTTPException(401)` inside a dependency ends the
   request there.
3. **It is visible in the signature.** You can tell whether an endpoint is
   protected by reading one line — and, importantly, *reviewers can tell too*.

**And it does something invisible but crucial.** `get_current_user` also calls
`_set_request_owner(user["id"])`, which stores the current user where the
database layer can read it, so every query is automatically filtered to that
user. Chapter 03 covered why that matters: relying on each endpoint to remember
a filter is how the same data leak happens four times.

## G.6 The testing benefit

FastAPI lets you replace a dependency during tests:

```python
app.dependency_overrides[get_db] = get_test_db
```

Every endpoint now uses the test database, with no change to any endpoint.
**This is one of the strongest practical arguments for dependency injection in
general:** what a function needs is stated in one place, so it can be swapped in
one place.

## G.7 The subtlety that this project had to reason about

A `yield` dependency is cleaned up when the **handler** returns. For a normal
endpoint that is when the work is done.

For a **streaming** endpoint it is not. The handler returns a response object
almost immediately, and the actual work runs for several seconds afterwards
while sending output.

That is why `core/auth.py` carries this comment:

> *"A `yield`-style dependency would tie the scope's lifetime to the
> dependency's, which is WRONG for SSE: the streaming generator in query.py
> outlives the dependency and still needs the scope while it runs."*

**The general lesson:** whenever you acquire something, ask *how long does this
need to live, and does that match the thing that acquired it?* For streaming
responses the answer is often no.

---

# Part H — Middleware

## H.1 What it is and why it exists

**Middleware is code that runs on every request, before and after your
handler, without any handler asking for it.**

The airport comparison holds well: every passenger passes through security, and
no gate agent has to check individually.

**Why not just call a function at the top of each endpoint?** Because "every
endpoint" includes the one somebody adds next month. A rule that must be
remembered will eventually be forgotten. **Middleware makes forgetting
impossible**, which is the same principle as a required parameter or a
`NOT NULL` column: enforce it where it cannot be skipped.

## H.2 The onion

A request goes *in* through each layer and the response comes *out* through
them in reverse:

```
     request  →  CORS  →  correlation id  →  security headers  →  CSRF  →  handler
     response ←  CORS  ←  correlation id  ←  security headers  ←  CSRF  ←
```

Each layer can inspect or change the request on the way in, and the response on
the way out. Any layer can also **stop** the request and reply immediately —
which is exactly what the CSRF layer does when a token is missing.

## H.3 The order surprise

Here is something that catches everyone once.

```python
app.add_middleware(CORSMiddleware, ...)          # added first
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(DeviceFingerprintMiddleware)  # added last
```

**The last one added is the first one to run.** Each `add_middleware` call
wraps the application built so far, so the outermost layer is the one added
most recently.

Execution order for an incoming request is therefore:

```
DeviceFingerprint → TenantContext → CSRF → SecurityHeaders → CorrelationId → CORS → handler
```

**This is not a detail.** If an authentication middleware is added before a
logging middleware, then rejected requests are never logged — and you cannot
see attacks. **Whenever you touch a middleware stack, write out the real
execution order first.**

## H.4 What each layer here does

| Middleware | Job | What breaks without it |
|---|---|---|
| `CORSMiddleware` | tells browsers which sites may call this API | the browser blocks every request from the frontend |
| `CorrelationIdMiddleware` | attaches a unique id to each request | you cannot find one request's log lines among millions |
| `SecurityHeadersMiddleware` | adds protective response headers | clickjacking, MIME-sniffing and downgrade attacks become possible |
| `CSRFMiddleware` | rejects state-changing requests without a matching token | another website can act as your logged-in user |
| `TenantContextMiddleware` | derives the tenant's storage namespace from the token | vector operations could address the wrong namespace |
| `DeviceFingerprintMiddleware` | limits repeat trial registrations from one device | free trials can be farmed indefinitely |

Two of them are worth reading in full.

**The correlation id** is fifteen lines and solves a real operational problem:

```python
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

- `dispatch` is the method every Starlette middleware implements.
- `call_next(request)` runs the rest of the chain and eventually your handler.
  **Everything before that line happens on the way in; everything after happens
  on the way out.**
- It accepts an id the caller supplied, or invents one — so an id created by
  the browser can be traced across several services.
- `request.state` is a scratchpad attached to this one request.

**The CSRF middleware** shows the other pattern — stopping a request:

```python
class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if request.url.path in CSRF_EXEMPT_PATHS:
                return await call_next(request)

            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")

            if not csrf_cookie or not csrf_header:
                logger.warning(...)
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed. Missing token."})

            if csrf_cookie != csrf_header:
                logger.warning(f"CSRF blocked: Token mismatch path={request.url.path}")
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed. Token mismatch."})

        response = await call_next(request)
        return response
```

Three observations:

- **It only checks methods that change data.** `GET` is agreed not to modify
  anything, so it is exempt by design — the protocol's promise is load-bearing
  for the security control.
- **`return` without calling `call_next` ends the request.** The handler never
  runs.
- **There is an exemption list**, because login and registration are the one
  case where the user legitimately has no token yet. Every exemption is a hole
  you have chosen deliberately, which is why they are listed in one visible
  place.

## H.5 Middleware or dependency?

Both run before your handler. The rule:

- **Middleware** for things that apply to *every* request, including ones that
  do not match a route: logging, headers, CORS.
- **A dependency** for things that apply to *some* endpoints and produce a
  *value* the handler uses: the current user, a database session.

Authentication is a dependency here precisely because it produces the user
object and because a few endpoints are public.

---

# Part I — Errors

## I.1 Raising a controlled error

```python
raise HTTPException(status_code=404, detail="Document not found")
```

FastAPI catches this and turns it into a proper response:

```json
{"detail": "Document not found"}
```

**Raise, do not return.** Raising stops execution immediately, so nothing after
it can run by accident. That matters when the error is a permission check.

## I.2 Registering a handler for a whole class of error

```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

`add_exception_handler` says: whenever this kind of exception escapes anywhere,
turn it into a response using this function. Here it converts a rate-limit
error into a **429 Too Many Requests** — consistently, from every endpoint,
without any endpoint knowing.

## I.3 What happens to an unexpected error

If your code raises something nobody handled, FastAPI returns **500 Internal
Server Error** with no details — deliberately, because an exception message can
reveal file paths, queries and internal structure.

The details go to the logs and, here, to Sentry (a service that collects
errors), configured in `main.py` with one careful touch:

```python
        before_send=lambda event, hint: (
            {**event, 'request': {
                k: v for k, v in event.get('request', {}).items()
                if k not in ['data', 'body']
            }} if event else None
        ),
```

**This strips the request body before sending the error report.** In a system
where request bodies contain users' private questions about their private
documents, that is not optional. **An error reporting tool is a place your
users' data can leak to**, and this is the line that prevents it.

## I.4 Streaming changes the error model

Once the first byte of a response has been sent, the status code is already
gone. You cannot decide afterwards to make it a 500.

So the streaming endpoint reports failures *inside the stream*:

```python
            yield f"event: error\ndata: {json.dumps({'detail': 'An internal error occurred while generating the response. Please retry.'})}\n\n"
```

**The general rule: streaming responses need an in-band error channel**, and
both sides must agree on it. The browser's reader handles an `error` event
explicitly.

## I.5 The status code as a security decision

```python
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
```

The comment above it in `document_access.py` explains the choice:

> *"404 rather than 403 deliberately: a 403 would confirm the id exists and
> belongs to somebody, which is an enumeration oracle."*

**403 Forbidden** says *this exists and is not yours*, which lets an attacker
walk through identifiers and map your system's contents without reading
anything. **404** reveals nothing.

---

# Part J — Streaming Responses

The answer to a question arrives word by word. Here is how.

```python
@router.post("/stream")
@limiter.limit("30/minute")
async def stream_query(request: Request, body: QueryRequest, ...):
    async def event_generator():
        yield f"event: status\ndata: {json.dumps({'message': 'Retrieving semantic chunks...'})}\n\n"
        ...
        yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        ...
        yield f"event: done\ndata: {{}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Five things to understand:

1. **`event_generator` is an async generator** — a function containing `yield`
   that produces values over time and may wait between them.
2. **It is called but not awaited.** `event_generator()` creates the generator
   without running any of it.
3. **The handler returns immediately.** `StreamingResponse` holds the generator
   and drives it as the client reads.
4. **Each `yield` writes bytes to the still-open connection** and then suspends,
   so other users' requests run in between.
5. **`media_type="text/event-stream"`** tells the browser this is Server-Sent
   Events — a stream of small labelled messages — rather than a document that
   ends.

**The consequence to remember:** the handler finishes long before the work
does. That is why the tenant scope could not be a `yield` dependency (G.7), and
why errors must be sent as events (I.4).

---

# Part K — Automatic Documentation

Because FastAPI already knows every path, method, parameter type and response
model, it can generate a description of the whole API for free.

**OpenAPI** is a standard format for describing an HTTP API as a JSON
document — every endpoint, every parameter, every shape. FastAPI produces it
automatically, at the address configured in `main.py`:

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)
```

And it serves two human interfaces built from it:

- **`/docs`** — Swagger UI: a page listing every endpoint, with a "Try it out"
  button that sends real requests.
- **`/redoc`** — a cleaner, read-only version.

**Why this matters beyond convenience**, in three levels:

1. **It cannot drift.** It is generated from the code that runs, so it cannot
   describe an endpoint that no longer exists.
2. **It is a working test client**, with no extra tool to install.
3. **It can generate other code.** Chapter 09 identified this as the single
   highest-value improvement available in this project: the frontend's
   TypeScript types could be generated from this exact document, which would
   turn "the server changed a field" from a silent frontend gap into a compile
   error.

**One production consideration:** `/docs` describes your entire attack surface.
Many teams disable it in production or put it behind authentication. This
project leaves it open, which is reasonable for a portfolio project and worth
being able to discuss.

---

# Part L — Startup and Shutdown

FastAPI can run code when the application starts and stops:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await connect_to_something()
    yield
    # shutdown
    await close_it()

app = FastAPI(lifespan=lifespan)
```

**What it is for:** opening connection pools, loading models, warming caches;
and on the way out, finishing in-flight work and closing things cleanly.

**This project does not use it.** Its startup work happens at module level in
`main.py` instead — bridging the API keys, configuring Sentry, setting up
logging.

**Is that wrong?** Not exactly, and the distinction is worth understanding:

- Module-level code runs on **import**, which includes contexts where you did
  not intend it — a test importing the module, a script, a documentation
  generator.
- Lifespan code runs when the **server** starts, which is more precise.

**The concrete gap it leaves** is shutdown. Nothing here defines what should
happen when the process is asked to stop, so an in-flight streaming answer is
cut off mid-sentence on every deploy. Chapter 05's critique named this, and it
appears again in Part S.

---

# Part M — Real Incidents

## M.1 The endpoints that were registered and never called

```python
# L-7: the ws WebSocket router was removed — the product streams over SSE
# and no frontend code ever opened a WebSocket (dead surface).
```

**Symptom:** none, which is the problem. Everything worked.

**Root cause:** a feature was built, registered and documented, and the product
went a different way (SSE). Nothing removed it.

**Why review missed it:** reviews look at diffs. Nobody was changing this code,
so nobody looked at it. Chapter 04 recorded the same structural gap in the
review roster — *"age is a trigger, not a defence"*.

**The lesson:** every registered endpoint is surface that must be secured,
tested and maintained. **Unused endpoints are not free.** The audit that found
this also removed two `/query` endpoints with no consumers.

## M.2 The proxy metric that produced a wrong conclusion

`CLAUDE.md` records this as a standing rule about evidence:

> *"This project has already shipped wrong conclusions drawn from a proxy
> metric (`len(app.routes)`) and from a regex that silently failed on a
> multi-line decorator."*

**Symptom:** someone verified that routes were registered by counting
`len(app.routes)`. The number looked right.

**Root cause:** a count is not a check. It tells you *how many* routes exist,
not *which* — so a route registered under the wrong prefix, or an endpoint
that would fail on its first call, counts exactly the same as a healthy one.

**The lesson, which generalises far beyond FastAPI:** *measure the property you
care about, not something correlated with it.* The real check is calling the
endpoint and looking at the response.

## M.3 The endpoint that froze the whole server

Chapter 07 covered this in depth; here is the framework-level framing.

**Symptom:** unrelated endpoints — including the health check — became slow
whenever anyone was streaming an answer.

**Root cause:** an `async def` endpoint doing work that does not pause. Uvicorn
runs all requests on one thread, switching between them only when a request
*pauses at an `await`*. Code that computes rather than waits never pauses, so
everyone else waits for it.

**Why review missed it:** the function had `async def` at the top and a
`run_in_executor` call three lines above the offending loop. It looked correct.

**The framework lesson:** `async def` does not make a function non-blocking. It
makes it *able to pause*. Blocking work inside one blocks everybody, and it is
worse than putting the same work in a normal synchronous endpoint — where
FastAPI would have run it on a thread pool automatically.

**Which is a genuinely useful rule most people do not know:**

> If your endpoint does blocking work and you cannot offload it, declare it as
> `def` rather than `async def`. FastAPI runs plain `def` endpoints in a thread
> pool, so they cannot block the loop.

---

# Part N — Debugging Request Failures

**The status code tells you which layer failed.** Learn this table and most
debugging becomes a lookup.

| Code | Meaning | Where it came from | First thing to check |
|---|---|---|---|
| **404** | no route matched | FastAPI routing | the path — count the `/api/v1` prefixes |
| **405** | route exists, wrong method | routing | are you sending POST to a GET route? |
| **422** | body/params failed validation | Pydantic | read `loc` in the response — it names the field |
| **401** | not authenticated | `get_current_user` | is the cookie being sent? `credentials: 'include'` |
| **403** | CSRF or permission | CSRF middleware | is the `X-CSRF-Token` header present and matching? |
| **402** | trial exhausted | trial dependency | expected; the frontend shows an upgrade dialog |
| **429** | too many requests | rate-limit handler | expected; back off |
| **500** | unhandled exception | your code | read the server log — the detail is deliberately not sent |
| **503** | dependency unavailable | your code | here: the job queue was unreachable |
| **connection refused** | nothing is listening | operating system | is the process running? bound to `0.0.0.0`? |

**The procedure**, cheapest first:

1. **Read the status code** and use the table.
2. **Read the response body.** A 422 names the field; a 403 says whether the
   token was missing or mismatched.
3. **Check `/docs`.** If the endpoint is not listed, the route is not
   registered — check the include chain in `api.py`.
4. **Look at the server log**, filtered by the correlation id from the
   `X-Correlation-ID` response header. **This is what that middleware is for.**
5. **Reproduce with `curl`**, which removes the browser from the picture
   entirely:
   ```bash
   curl -i http://localhost:8000/api/v1/health
   ```
   `-i` shows the response headers. If `curl` works and the browser does not,
   the problem is CORS, cookies or the frontend — not the endpoint.
6. **Only now** read the endpoint's code.

---

# Part O — Production Mistakes

1. **Blocking work in an `async def` endpoint.** M.3. Use `def`, or offload it.
2. **No `response_model`**, so internal fields leak into responses. A `User`
   object returned directly can include a password hash.
3. **Returning 200 with an error inside the body.** Clients, caches and
   monitoring all read the status code; hiding failure in a 200 defeats all
   three.
4. **Catching exceptions too broadly in a handler**, converting a real fault
   into an empty result.
5. **Business logic inside the endpoint function.** Endpoints should parse,
   authorise, delegate and format. Logic belongs in a service module, so it can
   be tested and reused — which is exactly why this project has
   `services/`.
6. **Middleware added in the wrong order.** H.3.
7. **Leaving `/docs` public** without deciding to.
8. **Not stripping sensitive data from error reports.** `before_send` exists
   for this.
9. **Forgetting that a dependency raising ends the request.** That is a feature
   for auth and a surprise if you did not intend it.
10. **No timeout on outbound calls.** A slow upstream holds your worker open
    indefinitely.

---

# Part P — Build One From an Empty Folder

Twenty minutes, and it makes everything above concrete. This is not from this
project — it is a complete, runnable application.

```bash
mkdir todo-api && cd todo-api
python -m venv venv
./venv/Scripts/activate        # Windows
# source venv/bin/activate     # macOS / Linux
pip install "fastapi[standard]" uvicorn
```

Create `main.py`:

```python
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI(title="Todo API")

# ---- storage (a dictionary standing in for a database) ----
TODOS: dict[str, dict] = {}

# ---- shapes ----
class TodoCreate(BaseModel):
    title: str
    done: bool = False

class Todo(BaseModel):
    id: str
    title: str
    done: bool

# ---- a dependency ----
def get_current_user(x_user: Optional[str] = None) -> str:
    if not x_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return x_user

# ---- endpoints ----
@app.get("/todos", response_model=list[Todo])
async def list_todos(done: Optional[bool] = Query(None),
                     user: str = Depends(get_current_user)):
    items = [t for t in TODOS.values() if t["owner"] == user]
    if done is not None:
        items = [t for t in items if t["done"] == done]
    return items

@app.post("/todos", response_model=Todo, status_code=201)
async def create_todo(body: TodoCreate, user: str = Depends(get_current_user)):
    todo_id = str(uuid.uuid4())
    TODOS[todo_id] = {"id": todo_id, "title": body.title,
                      "done": body.done, "owner": user}
    return TODOS[todo_id]

@app.get("/todos/{todo_id}", response_model=Todo)
async def get_todo(todo_id: str, user: str = Depends(get_current_user)):
    todo = TODOS.get(todo_id)
    if not todo or todo["owner"] != user:
        raise HTTPException(status_code=404, detail="Not found")
    return todo
```

Run it:

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000/docs` and use it.

**Five things to notice, each mapping to something in this chapter:**

1. **`response_model=list[Todo]`** filters the output — the `owner` field is
   stored but never sent, because `Todo` does not list it. That is F.4's
   security property, visible in ten lines.
2. **`get_todo` returns 404 for someone else's item**, not 403 — I.5's
   enumeration-oracle decision.
3. **`Depends(get_current_user)`** appears in every signature, so protection is
   readable at a glance.
4. **`status_code=201`** on creation, because "created" is a different outcome
   from "here it is".
5. **The docs page exists** and you wrote no documentation.

**Then break it deliberately**, which is where the learning is:

- Call `/todos` with no `x-user` → 401 from the dependency.
- POST `{"title": 123, "done": "maybe"}` → 422, and read exactly which fields
  failed.
- Ask for a todo id that does not exist → 404.
- Add `owner: str` to the `Todo` model and watch the field appear in responses.

---

# Part Q — Exercises

### Level 0 — Understanding

**Q1.** In your own words, what is a web framework? Name three things it does
for you.

**Q2.** Explain the difference between Uvicorn, Starlette, FastAPI and
Pydantic.

**Q3.** What is the difference between a path parameter, a query parameter and
a request body? Give an example of each from this project.

### Level 1 — Mechanics

**Q4.** Explain `Depends(get_db)` to someone who has never used a framework.
What is `yield` doing, and what breaks without it?

**Q5.** Middleware is added in one order and runs in another. State the rule,
then write the execution order for this project's six middlewares.

**Q6.** A request returns 422. What layer produced it, what does the response
body contain, and how is 422 different from 400 and 404?

### Level 2 — Applying

**Q7.** An endpoint returns a `User` object directly and users report that
their password hashes are visible in the API response. What single change fixes
it, and why does that change fix it?

**Q8.** Someone reports a 404 from the frontend, but the endpoint clearly
exists and works in `/docs`. Give the two most likely causes and how to
distinguish them.

**Q9.** Your endpoint does two seconds of pure computation. It is declared
`async def`. Explain what happens to other users, and give two different correct
fixes.

### Level 3 — Design

**Q10.** Why is authentication a dependency here rather than middleware? Give
two reasons, and one situation where middleware would be the better choice.

**Q11.** A streaming endpoint fails after it has already sent 200 OK and some
tokens. Explain why you cannot return a 500, and describe the correct approach.

**Q12.** Design a `PATCH /documents/{id}` endpoint for renaming a document.
Specify the path, the request model, the response model, the dependencies,
every error case with its status code, and the one security check that must not
be forgotten.

### Level 4 — Repository

**Q13.** Trace `POST /api/v1/query/stream` from the browser to the first token
appearing on screen. Name the file for each stage and state what would break if
that stage were removed.

**Q14.** The address `/api/v1/documents/{document_id}` is assembled from three
places. Name them, and describe the bug produced by writing the version prefix
twice — including why it is hard to diagnose.

**Q15.** This project has no lifespan handler. Describe two concrete problems
that causes, and write the lifespan function that would fix one of them.

---

# Part R — Answer Key

**R1.** A web framework is a program that handles everything between the
network and your logic: accepting connections, parsing HTTP text, routing to
the right function, validating input, serialising output, handling errors, and
serving many requests at once. It **calls your code** rather than being called
by it. Three things it does for you: parsing and routing, validation, and
turning your return value into a correct HTTP response.

**R2.** **Uvicorn** is the server: it owns the socket, speaks HTTP, and calls
the application. **Starlette** is the toolkit underneath FastAPI providing
routing, request/response objects and middleware. **FastAPI** is the framework
built on Starlette adding dependency injection, validation from type hints, and
automatic documentation. **Pydantic** is the validation library FastAPI uses to
turn type annotations into runtime checks.

**R3.** A **path parameter** is part of the address and identifies a specific
thing — `/documents/{document_id}`. A **query parameter** comes after `?` and
modifies the request — `?workspace_id=legal&chat_session_id=...` on
`list_documents`. The **request body** is a block of JSON sent with the request
— `QueryRequest` on `POST /query/stream`.

**R4.** `Depends(get_db)` tells the framework: before running this function,
call `get_db` and pass its result in as `db`. It is not magic — FastAPI reads
the signature, sees the marker, calls the function first.

`get_db` uses `yield` rather than `return` because the work has two halves.
Before the `yield` it borrows a database connection; the `yield` hands it to the
endpoint and pauses; after the endpoint finishes, the function resumes and its
`async with` block returns the connection to the pool. A plain `return` could
only do the first half — there would be no "after".

Without the cleanup, connections are borrowed and never given back. With a
budget of about fifteen, a few hundred requests exhaust the pool and every
later request hangs waiting for a connection that never comes.

**R5.** The rule: **`add_middleware` wraps the application, so the last one
added is the outermost and runs first.**

Execution order here: `DeviceFingerprint` → `TenantContext` → `CSRF` →
`SecurityHeaders` → `CorrelationId` → `CORS` → handler, and back out in reverse
on the response.

It matters because a layer that rejects requests, placed *inside* a logging
layer, means rejected requests are never logged.

**R6.** Pydantic produced it, during validation, before the endpoint function
ran. The body contains a `detail` list where each entry has `loc` (which field),
`msg` (what is wrong) and `type` — and it reports every problem, not just the
first.

**422** means the shape is wrong: a string where a number belongs, or a missing
required field. **400** means the shape is fine but the value is wrong in
context — for example a workspace identifier that parses but is not one of the
seven. **404** means no such resource, and in this project it is also used
deliberately for "not yours", to avoid confirming that an id exists.

**R7.** Add a `response_model` that lists only the safe fields:

```python
@router.get("/me", response_model=UserPublic)
```

It fixes it because `response_model` **filters** the outgoing object to exactly
the declared fields. Any field not listed is not serialised, no matter what the
function returned.

The deeper reason this is the right fix rather than "remember to strip the
field": the filter is at the boundary, applied automatically, so no future
handler can leak it by accident. It is a choke point rather than a habit.

**R8.** Two likely causes:

1. **A doubled version prefix.** The frontend base URL already ends in
   `/api/v1`, so writing `/api/v1/documents` produces
   `/api/v1/api/v1/documents` — which matches no route.
2. **Deliberate 404 for "not yours".** The endpoint exists and works; this
   user simply does not own that resource, and the project returns 404 rather
   than 403 on purpose.

Distinguish them by looking at the actual request URL in the browser's network
panel. If the path contains `/api/v1` twice, it is the first. If the path is
correct, try the same id as its owner — success there confirms the second.

**R9.** Uvicorn runs requests on one thread and switches between them only when
a request pauses at an `await`. Pure computation never pauses, so for two
seconds **every other request on that process is frozen** — including health
checks and other users' streams. The symptom appears everywhere except in the
code responsible.

Two correct fixes:

1. Offload the work: `await loop.run_in_executor(None, heavy_function, arg)`,
   which runs it on a worker thread and frees the loop.
2. Declare the endpoint as plain `def` rather than `async def`. FastAPI runs
   synchronous endpoints in a thread pool automatically, so they cannot block
   the loop.

If the work takes minutes rather than seconds, neither is right — it belongs on
a job queue.

**R10.** Two reasons authentication is a dependency:

1. **It produces a value** — the user object — that the handler uses. Middleware
   returns a response, not a value for the handler.
2. **It applies to most endpoints but not all.** Login, registration, health and
   the CSRF-token endpoint are public. A dependency is opt-in per endpoint and
   visible in the signature, so a reviewer can see which endpoints are
   protected.

Middleware would be better if authentication had to apply to **every** request
including unmatched paths — for example an API where even a 404 must not be
returned to an unauthenticated caller, since the fact that a path does not
exist is itself information.

**R11.** Once the first byte is written, the status line has already been sent —
it was the very first thing on the wire. HTTP has no mechanism to change it
afterwards, so `raise HTTPException(500)` inside a streaming generator cannot
produce a 500; the client already has a 200.

The correct approach is an in-band error channel: send an `error` event on the
stream that the client understands, log the real cause on the server, and end
the stream cleanly. Both sides must agree on the event name, which is why this
project treats its SSE event names as an invariant that must stay in step.

**R12.**

```python
class RenameRequest(BaseModel):
    filename: str

@router.patch("/{document_id}", response_model=DocumentResponse)
async def rename_document(
    document_id: str,
    body: RenameRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await get_owned_document(db, document_id, current_user)
    doc.filename = body.filename
    await db.commit()
    await db.refresh(doc)
    return doc
```

- **Path:** `PATCH /api/v1/documents/{document_id}` — `PATCH` because it is a
  partial update, not a replacement (`PUT`).
- **Request model:** `RenameRequest` with a required `filename`. Adding
  `min_length=1` would be better still.
- **Response model:** the document, filtered to its public fields.
- **Dependencies:** the current user and a database session.
- **Errors:** 401 if not authenticated (raised by the dependency); 422 if
  `filename` is missing or not text; 404 if the document does not exist **or is
  not this user's**; 500 if the write fails.
- **The security check that must not be forgotten:** ownership. Using the shared
  `get_owned_document` helper rather than a bare lookup by id is what enforces
  it — and returning 404 rather than 403 avoids confirming the id exists.

**R13.** The trace:

1. `frontend/src/lib/api.ts` — builds the request, attaches the CSRF header and
   cookies. *Without it:* every call would repeat that setup and some would
   forget it.
2. Uvicorn — parses the HTTP bytes into a `scope`. *Without it:* nothing speaks
   HTTP.
3. `core/middleware.py` — CSRF check and tenant context on the way in.
   *Without it:* another site could act as the logged-in user.
4. `api/v1/api.py` + the decorator in `endpoints/query.py` — routing to
   `stream_query`. *Without it:* 404.
5. `core/auth.py` via `Depends(get_current_user)` — identity, and binding the
   owner scope. *Without it:* anonymous access, and unscoped database reads.
6. `schemas/query.py` — validates the body. *Without it:* bad input reaches the
   pipeline and fails deep inside.
7. `core/trial_enforcement.py` — quota check, 402 if exhausted. *Without it:*
   the free trial is unlimited.
8. `services/grounding_service.py` → `retrieval_service.py` → `reranker` —
   finds the evidence. *Without it:* the answer would be ungrounded.
9. `services/llm_service.py` — generates tokens. *Without it:* no answer.
10. `StreamingResponse(event_generator())` — each `yield` writes an SSE frame.
    *Without it:* the user waits in silence for the whole answer.
11. `api.ts`'s reader — decodes frames and appends tokens to the screen.

**R14.** The three places: `settings.API_V1_STR` (`/api/v1`) applied in
`main.py`; the `prefix="/documents"` given to `include_router` in `api.py`; and
the path in the decorator in `documents.py`.

Writing the version prefix twice on the frontend produces
`/api/v1/api/v1/documents/…`, which matches no route, so FastAPI returns 404.

It is hard to diagnose because **that 404 is indistinguishable from a genuinely
missing endpoint**, so the developer goes looking for a routing bug in code
that is correct. The fastest way to settle it is to read the actual request URL
in the browser's network panel, or to call the correct URL with `curl` and see
it succeed.

**R15.** Two concrete problems:

1. **No graceful shutdown.** When the process is asked to stop during a deploy,
   in-flight streaming answers are cut off mid-sentence, and any work between
   database writes is lost with no record.
2. **Startup work runs on import**, so importing `main` in a test or a script
   executes it — configuring Sentry, bridging API keys, emitting startup logs —
   in contexts that did not want it.

A lifespan that fixes the first:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] application ready")
    yield
    logger.info("[shutdown] draining: no new requests, finishing in-flight work")
    await engine.dispose()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
```

The shutdown half closes the database connection pool cleanly. Full graceful
shutdown also needs the server to stop accepting new connections while
finishing existing ones, which Uvicorn does on `SIGTERM` — but only if the
container's stop timeout is long enough, which is a deployment setting rather
than a code one.

---

# Part S — Senior Critique

### Strengths

1. **Routing is layered cleanly** — 24 routers, one prefix applied once, the
   version number in a single setting.
2. **Authentication is a dependency**, so protection is visible in every
   signature and reviewers can see at a glance which endpoints are public.
3. **The database session is a `yield` dependency**, guaranteeing the
   connection returns to a scarce pool.
4. **Validation is at the boundary**, with typed request models, so handlers do
   not re-check input.
5. **The middleware stack is complete and purposeful** — correlation ids,
   security headers, CSRF, tenant context — and each has a written reason.
6. **Sentry strips request bodies**, which in a product handling private
   documents is essential rather than optional.
7. **Status codes carry deliberate meaning**, including 404-not-403 for
   ownership and 402 for an exhausted trial.
8. **Dead endpoints were removed and the removal was recorded** rather than
   left in place.

### Weaknesses

1. **No lifespan handler**, so there is no defined shutdown and startup work
   happens at import time. For a product whose main interaction is a
   multi-second stream, every deploy cuts answers mid-sentence.
2. **`response_model` is used inconsistently.** `/query/ask` declares one;
   several endpoints return `Any`, so nothing filters the output and nothing
   documents the shape.
3. **Business logic sits inside some endpoint functions.** `query.py` is over
   600 lines and contains cache helpers, SSE frame construction, trust-report
   adaptation and history loading. Endpoints should parse, authorise, delegate
   and format.
4. **Two answer paths** (`/query/ask` and `/query/stream`) mean a fix can be
   applied to one and not the other — a shape this repository's history already
   shows.
5. **`/docs` is exposed by default**, which publishes the full attack surface.
   Fine for a portfolio, a decision to make explicitly for production.
6. **No global exception handler for unexpected errors** beyond the rate-limit
   one, so responses to unhandled faults are FastAPI's default rather than a
   consistent shape the frontend can rely on.
7. **Rate limiting is applied per endpoint by decorator**, so a new endpoint has
   none unless someone remembers — the same "enforced by discipline" pattern the
   project criticises elsewhere.

### The one improvement I would make first

**Add a lifespan handler with a real shutdown.** It is perhaps fifteen lines,
and it removes a defect that occurs on *every single deploy* — mid-sentence
truncation of live answers — which is invisible in development and unmissable
in production. Second would be extracting `query.py`'s helpers into the service
layer, because a 600-line endpoint module is where two answer paths drift apart.

---

# Part T — Interview Questions With Model Answers

**T1. "What is FastAPI?"**

> A Python web framework for building APIs, built on Starlette for the async
> HTTP machinery and Pydantic for validation. The distinctive idea is that it
> reads your type annotations and uses them for three things at once —
> validating incoming requests, serialising responses, and generating OpenAPI
> documentation — from information you were going to write anyway.
>
> It is ASGI-based, so endpoints can be async and a single worker can handle
> many requests that are mostly waiting. That matters for us because about 86%
> of a request's time is spent waiting on the database and the model API.

**T2. "Why FastAPI over Flask or Django?"**

> Django is a full product framework — admin panel, ORM, auth, templates. If I
> were building a content site with a database and an admin interface, Django
> would have me running in an afternoon. Flask is minimal and excellent for
> small synchronous services.
>
> We chose FastAPI for three concrete reasons. Our request path is dominated by
> waiting, so native async lets one worker serve many concurrent requests.
> Answers stream token by token, which ASGI makes natural and WSGI does not.
> And with 24 endpoint modules, automatic validation and generated
> documentation pay for themselves quickly.
>
> The tradeoff is honest: we had to choose and wire up our own ORM, migrations,
> auth and admin, which Django would have provided.

**T3. "Explain dependency injection."**

> Instead of a function fetching what it needs, it declares what it needs and
> the framework provides it. In FastAPI you write
> `db: AsyncSession = Depends(get_db)` and the framework calls `get_db` first
> and passes in the result.
>
> There is no magic — it reads the signature, sees the marker, calls the
> function. The value is threefold: no repetition across two hundred endpoints,
> the requirements are visible in the signature so a reviewer can tell whether
> an endpoint is protected, and dependencies can be overridden in tests so every
> endpoint uses a test database with no change to any endpoint.
>
> Our database dependency uses `yield` rather than `return`, so the code after
> the yield runs when the request finishes and returns the connection to the
> pool. With a fifteen-connection budget, that cleanup is not optional.

**T4. "Explain middleware, and where order matters."**

> Middleware runs on every request before and after the handler, without any
> handler asking for it. It is an onion: the request goes in through each layer
> and the response comes back out through them in reverse, and any layer can
> stop the request and reply itself.
>
> The order surprise is that `add_middleware` wraps the app, so the *last* one
> added runs *first*. That matters: if a layer that rejects requests sits inside
> a logging layer, rejected requests are never logged and you cannot see
> attacks.
>
> Ours does CORS, correlation ids, security headers, CSRF, tenant context and
> device fingerprinting. The correlation id is the one I use most in debugging —
> it goes out as a response header, so I can take it from a user's failed
> request and find exactly those log lines.

**T5. "Walk me through one API request."**

> Take `GET /api/v1/documents?workspace_id=legal`.
>
> The browser resolves the host, opens a TCP connection to port 8000, and sends
> HTTP text with the session cookie. Uvicorn owns that port; it parses the text
> into an ASGI scope and calls the application.
>
> The middleware chain runs first — CSRF is skipped because this is a GET, and
> the correlation id is attached. FastAPI matches the path to `list_documents`,
> then resolves its dependencies: `get_current_user` reads the cookie, verifies
> the token's signature, and binds the user into a context variable that the
> database layer reads, so every query is filtered to that user automatically.
> `get_db` borrows a session from the pool.
>
> Only then does my ten lines of logic run: build a query filtered by owner and
> workspace, await the database — which suspends the coroutine so Uvicorn serves
> other people meanwhile — and return the rows. FastAPI serialises them to JSON,
> the response travels back out through the middleware picking up security
> headers, and Uvicorn writes the bytes.
>
> The point I would make is that I wrote step ten of about seventeen. Everything
> else is the framework, and knowing which step owns which failure is what makes
> debugging fast.

**T6. "How does validation work, and what is a 422?"**

> Request bodies are declared as Pydantic models — classes of typed fields. When
> a request arrives, FastAPI parses the JSON and validates it against that model
> before my function runs, converting where it safely can: `"12"` becomes the
> integer 12, but `"twelve"` is rejected.
>
> A failure produces 422 with a body listing every problem and its location, so
> the client knows exactly which field was wrong. I did not write any of that.
>
> The important property is that it is a single choke point. By the time my
> first line runs, every field is present, correctly typed and converted, so
> there is no defensive checking inside handlers — and no handler can forget it.
> It is the runtime counterpart to the frontend's TypeScript, which is erased
> before the code runs and so cannot check anything a client actually sends.

**T7. "Explain async endpoints, and when not to use them."**

> `async def` means the function can pause. When it awaits something — a
> database query, an HTTP call — it hands control back to the event loop, which
> serves other requests while this one waits. One thread, many concurrent
> requests, because most of the time is waiting.
>
> The trap is that `async def` does not make a function non-blocking. It makes
> it *able* to pause. If the body does two seconds of pure computation, nothing
> pauses and every other request on that process is frozen — including health
> checks, so the symptom shows up far from the cause. We hit exactly that: a
> stream loop that looked offloaded because there was a `run_in_executor` call
> three lines above it.
>
> Two fixes: offload the blocking part with `run_in_executor`, or — the rule
> most people do not know — declare the endpoint as plain `def`, because FastAPI
> runs synchronous endpoints in a thread pool where blocking is harmless.

**T8. "How does your streaming work?"**

> The endpoint returns a `StreamingResponse` wrapping an async generator. The
> generator is created but not awaited, so the handler returns almost
> immediately; the response object then drives the generator as the client
> reads. Each `yield` writes one Server-Sent Events frame — a labelled text
> message — to the still-open connection and suspends, so other requests run in
> between.
>
> Two consequences shaped the design. The handler finishes long before the work
> does, so anything acquired as a `yield` dependency would be cleaned up while
> the stream still needed it — which is why our tenant scope is bound
> differently. And once the first byte is sent, the status code is gone, so a
> later failure cannot be a 500; we send an `error` event that the client
> understands.

**T9. "Walk me through your backend."**

> It is a FastAPI application, served by Uvicorn, in front of PostgreSQL and
> Redis, with a separate Celery worker for slow work.
>
> A request enters through a middleware chain — CORS, correlation id, security
> headers, CSRF, tenant context, device fingerprint. Routing is layered:
> `main.py` mounts one router with the `/api/v1` prefix, that router includes 24
> subject routers, and each endpoint file declares its own paths.
>
> Endpoints are thin. They declare their dependencies — the current user and a
> database session — validate input through Pydantic models, and delegate to a
> service module. The services hold the real logic: retrieval, grounding,
> reranking, the LLM layer.
>
> Anything slow leaves the request. Uploading a document writes a row, puts a
> job on Redis and returns in milliseconds; a Celery worker does the OCR,
> chunking and embedding.
>
> The two design rules I would highlight: every rule that matters is enforced at
> a choke point rather than per endpoint — validation in Pydantic, tenancy in
> the session layer, CSRF in middleware — and failures are loud, so a feature
> that cannot work returns an error rather than a plausible-looking empty
> result.

**T10. "How do you debug a failing request?"**

> The status code tells me which layer failed, so I start there. 404 is routing
> — and the first thing I check is whether the path has the version prefix
> twice, because that produces a 404 identical to a missing endpoint. 422 is
> validation, and the response body names the field. 401 is the auth dependency,
> usually a cookie not being sent. 403 is CSRF. 500 is my code, and the detail
> is deliberately not in the response, so I go to the logs.
>
> Then I use the correlation id from the response header to find that request's
> log lines. If I need to remove the browser from the picture, I reproduce with
> `curl` — if `curl` works and the browser does not, it is CORS, cookies or the
> frontend, not the endpoint.
>
> Reading the endpoint's code is last, not first.

---

# Part U — Validation Checklist

- [ ] I can explain what a web framework is and name five things it does for
      me. *(A.2, A.3)*
- [ ] I can explain why CGI died and what WSGI fixed. *(B.1, B.2)*
- [ ] I can explain why WSGI could not do streaming and what ASGI changed.
      *(B.3, B.4)*
- [ ] I can distinguish Uvicorn, Starlette, FastAPI and Pydantic. *(C)*
- [ ] I can narrate all seventeen steps of a request without notes. *(D)*
- [ ] I can build a path from `API_V1_STR` + router prefix + decorator, and
      explain the doubled-prefix bug. *(E.3, E.5)*
- [ ] I can explain what `response_model` filters and why that is a security
      feature. *(F.4)*
- [ ] I can explain dependency injection without using the word "magic", and
      say why `get_db` uses `yield`. *(G.2, G.4)*
- [ ] I can state the middleware ordering rule and write this project's real
      execution order. *(H.3)*
- [ ] I can explain why a streaming endpoint cannot return a 500 after it
      starts. *(I.4, R11)*
- [ ] I can explain why `async def` does not make code non-blocking, and give
      two fixes. *(M.3, R9)*
- [ ] I can debug a failure from its status code using the table. *(N)*
- [ ] **I built the Todo API in Part P, ran it, opened `/docs`, and broke it
      four ways on purpose.**
- [ ] **The real test:** open [`main.py`](../backend/app/main.py),
      [`api/v1/api.py`](../backend/app/api/v1/api.py) and one endpoint file.
      Explain every middleware in execution order, trace one path from
      `API_V1_STR` to the decorator, and for one endpoint name every dependency,
      every possible status code it can return, and which layer produces each.

If the last two boxes are ticked, you can answer *"walk me through your
backend"* properly — and Chapter 14 can be about the layer underneath: how those
`select(...)` statements become SQL, and how the schema changes safely.

---

*Next: `14-sqlalchemy-and-migrations.md` — the ORM over the SQL you already
know, sessions and identity, the N+1 trap, the connection-pool budget, and
Alembic migrations that can be rolled back.*
