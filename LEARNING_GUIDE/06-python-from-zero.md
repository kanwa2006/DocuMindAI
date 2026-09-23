# 06 — Python From Zero

**Prerequisites:** Chapter 05 only. You need to know what a process is, what
memory is, what a file is, and what the terminal does. Nothing else.

**What this chapter is not.** It is not a syntax reference. There are
thousands of those and they teach you to recognise Python without teaching you
to think in it.

**What this chapter is.** Python taught as *a way to express the computing
ideas from Chapter 05*. A variable is a name for a value in memory. A function
is a reusable group of instructions. A loop is repetition without copying. An
exception is what happens when the program cannot continue normally. Every
piece of syntax exists to express an idea, and we will always meet the idea
first.

**One deliberate omission.** You will see `async def` and `await` in real code
in this chapter. I will tell you what they mean in one sentence and then move
on. They are Chapter 07's entire subject, and trying to teach them here would
mean teaching two hard things at once.

**How to read it.** With a terminal open. Type the examples. Reading code is
not the same as running it, and the difference is where learning happens.

---

# Part A — Before the First Line

## A.1 What is a programming language?

Chapter 05 established that a CPU follows instructions, and that instructions
are numbers in memory. Writing those numbers by hand is possible and
unbearable — a single addition might be `10110000 01100001`.

**A programming language is a way to write instructions in text that humans
can read, which is then turned into instructions the machine can run.**

**Why they exist.** Not to make computers work — computers worked before them.
They exist to make *humans* work: to let you express an idea once, read it back
six months later, and let a colleague change it without breaking it. **A
programming language is a tool for human memory and human collaboration**, and
that framing explains almost every feature you will meet.

### Two ways of getting from text to instructions

**Compiled languages** (C, Rust, Go) use a **compiler**: a program that reads
your whole file and produces a separate file of machine instructions. You then
run that file. The translation happens once, before running.

**Interpreted languages** (Python, JavaScript) use an **interpreter**: a
program that reads your code and performs it as it goes. There is no separate
machine-code file. The translation happens while running.

**The trade-off:**

| | Compiled | Interpreted |
|---|---|---|
| Speed of the finished program | fast | slower |
| Time from writing to running | slower (must compile) | immediate |
| Errors found before running | many | few |
| Portability | one build per platform | same file everywhere |

**Where Python actually sits.** Python compiles your text into an intermediate
form called **bytecode** — instructions for Python's own imaginary machine, not
for your CPU — and then the interpreter executes that bytecode. This is why you
see `__pycache__` folders full of `.pyc` files: they are cached bytecode, saved
so that importing the same file again does not require re-translating it.
Chapter 05's `.gitignore` excludes them, because they are generated and can
always be rebuilt.

## A.2 Why Python, and what it costs

Decision D-011 already recorded *why this project* uses Python: the entire
document and machine-learning ecosystem is Python, so any other choice means
running a Python service anyway. Here is the language-level picture.

**Python's history.** Created by Guido van Rossum around 1990, with an unusual
design goal: **code is read far more often than it is written, so optimise for
reading.** That single principle explains its most distinctive features —
indentation instead of braces, few symbols, English-like keywords.

**What Python is good at:** readability, a vast library ecosystem, fast
development, and being the default language of data and machine learning.

**What Python is bad at, and you must be able to say this out loud:** raw
speed (roughly ten to a hundred times slower than C for pure computation),
memory efficiency, and — the one that bites this project — using multiple CPU
cores inside one process. That last limitation has a name, the **Global
Interpreter Lock** (GIL): a rule inside Python that only one thread may execute
Python bytecode at a time.

**Why the GIL matters here, concretely.** Chapter 05 explained threads share
memory. Python's GIL means that even with eight cores, eight Python threads
cannot run Python code simultaneously. This is *why* Chapter 01's
`run_in_executor` still helps — the model libraries release the GIL while doing
their heavy numeric work in C — and *why* the background worker uses separate
**processes** (`--concurrency=2`) rather than threads. **A language limitation
became an architecture decision.** That is normal, and noticing it is a senior
habit.

## A.3 Running Python: three ways

Chapter 05 taught that a running program is a process. Python is a program.
When you run Python, you start a process whose job is to read and perform your
code.

**1. The interactive shell (REPL).** Type `python` and you get a prompt where
each line runs immediately.

```
>>> 2 + 3
5
>>> name = "Priya"
>>> name
'Priya'
```

REPL means **read–evaluate–print loop**: it reads a line, works out its value,
prints it, and loops. This is the single most useful learning tool you have.
When you are unsure what something does, try it here.

**2. A script file.** Put code in `hello.py` and run `python hello.py`. The
interpreter reads the file top to bottom and performs each statement in order.

**3. A module, with `-m`.** `python -m pytest tests/` means "find the installed
module named `pytest` and run it as a program". Chapter 05 showed this exact
command in this repository:

```bash
cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q
```

Now every part reads: a specific interpreter (not a PATH lookup), asked to run
the installed `pytest` module, pointed at the `tests` folder, quietly.

**Why `-m` rather than just `pytest`?** Because `-m` guarantees the module runs
with *that* interpreter and *its* installed libraries. Typing `pytest` alone
uses whichever `pytest` the PATH finds first, which may belong to a different
Python. **This is Chapter 05's PATH lesson, causing a real daily decision.**

## A.4 Virtual environments, revisited

Chapter 05 defined a **virtual environment** as a private folder holding one
project's interpreter and libraries. Now the reason is sharper.

When you `import` a library, Python searches a list of folders. Without a
virtual environment, that list points at one shared system-wide location, so
every project on the machine shares one set of library versions. Two projects
needing different versions of the same library cannot both work.

A virtual environment gives each project its own folder in that search list.
Same isolation principle as processes and containers, applied to dependencies.

```bash
python -m venv venv                 # create it
./venv/Scripts/activate             # Windows: put it first on PATH
source venv/bin/activate            # Linux/macOS
pip install -r requirements.txt     # install this project's libraries into it
```

`requirements.txt` is a plain text file listing library names and versions.
`backend/venv/` is in `.gitignore` because it can always be rebuilt from that
list — **store the recipe, not the meal.**

---

# Part B — Values, Variables, and Types

## B.1 Values and expressions

**A value** is a piece of data: the number `5`, the text `"hello"`, the truth
value `True`.

**An expression** is anything that produces a value. `2 + 3` is an expression
producing `5`. `"a" + "b"` is an expression producing `"ab"`. A value on its
own is the simplest expression.

**A statement** is an instruction that does something. Assigning, deciding,
looping, defining — those are statements. The distinction sounds academic and
is not: **expressions can be nested inside each other; statements cannot.** You
can write `f(g(x) + 1)`, but you cannot put an `if` statement inside an
expression.

## B.2 Variables — and the mental model that prevents years of bugs

**What it is.** A **variable** is a name that refers to a value.

**Why it exists.** So you can compute something once and use it many times, and
so code says *what* a value means rather than showing an anonymous number. The
difference between `86400` and `SECONDS_PER_DAY` is the difference between code
that can be maintained and code that cannot.

```python
seconds_per_day = 86400
name = "Priya"
top_k = 12
```

The `=` is **assignment**. It is not equality. Read it as "let this name refer
to this value".

**Now the important part, and most beginner courses get it wrong.**

The common teaching model is "a variable is a box that holds a value". In
Python this model is false, and believing it will confuse you the first time
you meet a real bug.

**The correct model: a variable is a name tag attached to an object in memory.**
Assignment does not copy the object. It attaches another tag.

```python
a = [1, 2, 3]     # a list object exists in memory; `a` is a tag on it
b = a             # `b` is now a SECOND tag on the SAME object
b.append(4)
print(a)          # [1, 2, 3, 4]  ← `a` changed too
```

Nothing was copied. `a` and `b` name the same object, so a change through one
is visible through the other. This is called **aliasing**.

**Why Python works this way.** Copying every value on every assignment would be
enormously wasteful — imagine copying a 500-page document's text every time you
passed it to a function.

**When it does not bite.** Some objects cannot be changed after creation —
numbers, strings, tuples. These are **immutable**. For them, aliasing is
invisible, because there is no way to modify the shared object.

```python
x = 5
y = x
y = y + 1     # this does not modify 5; it makes y a tag on a NEW object, 6
print(x)      # 5
```

**The rule to carry forever:** *mutable objects are shared; immutable objects
are effectively copied.* Every confusing "why did that change?" moment in
Python is this distinction.

## B.3 The types you need

**A type** is what kind of value something is, which determines what you can do
with it.

| Type | Written as | Meaning | Mutable? |
|---|---|---|---|
| `int` | `5`, `-3`, `0` | whole number | no |
| `float` | `0.1`, `3.14` | decimal number | no |
| `str` | `"hello"` | text | no |
| `bool` | `True`, `False` | truth value | no |
| `NoneType` | `None` | "no value at all" | no |
| `list` | `[1, 2, 3]` | ordered collection | **yes** |
| `dict` | `{"a": 1}` | name-to-value pairs | **yes** |
| `tuple` | `(1, 2)` | fixed ordered collection | no |
| `set` | `{1, 2, 3}` | unordered, no duplicates | **yes** |

**`None` deserves special attention** because it causes more real bugs than any
other value. It means "there is no value here". It is not zero, not an empty
string, not `False`. Chapter 03's most instructive defect was exactly this
confusion: an empty list `[]` was used where "we could not find out" was meant,
and the two states became indistinguishable.

**Floats have a trap you must know about.** Computers store decimals in binary,
and some decimals have no exact binary form — the same way one third has no
exact decimal form.

```python
>>> 0.1 + 0.2
0.30000000000000004
```

This is not a Python bug; it is how nearly all computers represent decimals.
**Therefore: never use floats for money.** Use whole numbers of the smallest
unit (paise, cents) or a decimal type designed for it. This project uses floats
for scores and timings, where tiny imprecision is harmless, and that is the
correct division.

**Dynamic typing.** Python does not require you to declare a variable's type,
and a name can refer to a different kind of value later. This is convenient and
it is also why type hints (Part K) exist: convenience for the writer, ambiguity
for the reader.

## B.4 Operators

```python
7 + 3      # 10   addition
7 - 3      # 4
7 * 3      # 21
7 / 3      # 2.3333333333333335   true division — ALWAYS a float
7 // 3     # 2                    floor division — whole number, rounds down
7 % 3      # 1                    modulo — the remainder
7 ** 3     # 343                  power
```

**`//` and `%` are more useful than beginners expect.** `%` answers "is this
divisible?" (`n % 2 == 0` means even) and "which slot does this fall into?".

And `//` appears in this repository doing real work, in
[`backend/app/services/grounding_service.py`](../backend/app/services/grounding_service.py):

```python
chunk_tokens = len(candidate["text_content"]) // 4
```

Chapter 01 met this line; now you can read it exactly. `len(...)` gives the
number of characters. `// 4` divides by four and discards the remainder,
because roughly four characters make one token. The result must be a whole
number of tokens, so floor division is the right operator, not `/`.

**Comparison operators** produce `True` or `False`:

```python
a == b     # equal (two equals signs — one is assignment)
a != b     # not equal
a < b      # less than
a >= b     # greater than or equal
```

**Logical operators** combine truth values:

```python
if is_logged_in and has_credit:      # both must be true
if is_admin or is_owner:             # at least one
if not is_deleted:                   # invert
```

**A subtlety that matters:** `and` and `or` **short-circuit** — they stop as
soon as the answer is known. In `a and b`, if `a` is false, `b` is never
evaluated. This is why you can safely write `if user and user["name"]`: when
`user` is `None`, the second part never runs and cannot fail.

## B.5 Where this appears in the repository

Every setting in
[`backend/app/core/config.py`](../backend/app/core/config.py) is a named value
with a declared type:

```python
    CHUNK_SIZE: int = 1800
    CHUNK_OVERLAP: int = 300
    OCR_CONFIDENCE_THRESHOLD: float = 0.80
    OCR_SCANNED_ENABLED: bool = True
    MAX_UPLOAD_MB: int = 200
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    TAVILY_API_KEY: Optional[str] = None
```

Read the last one. `Optional[str] = None` says: this is either text or nothing,
and by default it is nothing. That is `None` used correctly — it means "not
configured", which is a real, distinct state, and the comment above it in the
file records what happened when it was *missing entirely*: a step reported
success while never having run.

---

# Part C — Output, Input, and Strings

## C.1 Showing things

```python
print("Hello")
print("Chunks:", 200)          # several values, separated by spaces
```

`print` writes to **stdout** — Chapter 05's standard output channel. In this
project, production code does not use `print`; it uses a logger (Part I),
because a logger records *when*, *how important*, and *where from*. But
`print` is how you learn and how you debug quickly.

## C.2 Strings

**A string** is text: a sequence of characters. Chapter 05 taught that
characters become bytes through an encoding; a Python string is the
*characters*, and encoding happens when it is written to a file or a network.

```python
name = "Priya"
message = 'Single quotes work too'
long_text = """Three quotes
span several lines."""
```

Strings are **immutable**: you never change one, you make a new one. Every
"string modification" produces a new object.

```python
s = "hello"
s.upper()          # returns "HELLO"
print(s)           # still "hello" — s was not changed
```

**The methods you will actually use:**

```python
"  padded  ".strip()          # "padded"       remove surrounding whitespace
"a,b,c".split(",")            # ["a", "b", "c"] break into a list
",".join(["a", "b", "c"])     # "a,b,c"        glue a list together
"Legal".lower()               # "legal"
"legal".capitalize()          # "Legal"
"hello".startswith("he")      # True
"hello".replace("l", "L")     # "heLLo"
len("hello")                  # 5
"ell" in "hello"              # True
```

`split` and `join` are opposites and they appear constantly. Anywhere you have
a list that must become one string, or one string that must become a list, one
of these is the answer.

## C.3 f-strings — building text from values

**The problem.** You need text that includes computed values.

**The old ways, and why they were not enough.** Adding pieces
(`"Hello " + name`) fails the moment a value is not a string, and reads badly
with more than two parts. Percent formatting and `.format()` separate the
placeholder from the value, so you must count arguments.

**The modern answer**, introduced in Python 3.6: put the expression inside the
string.

```python
name = "Priya"
count = 12
print(f"{name} asked a question with {count} chunks")
# Priya asked a question with 12 chunks
```

The `f` before the quote marks it as a **formatted string literal**. Anything
inside `{ }` is evaluated and inserted.

**A real one from the repository**, in
[`backend/app/services/language_detector.py`](../backend/app/services/language_detector.py):

```python
    return (
        f"\n\nIMPORTANT: The user's question is in {language.capitalize()}. "
        f"Respond in {language.capitalize()} language throughout your entire response. "
        f"Technical terms and document citations can remain in English."
    )
```

Three things to notice, because they are all deliberate:

1. **Adjacent strings are joined automatically.** Three string pieces on three
   lines, wrapped in brackets, become one string. This is how long text stays
   readable.
2. **A method call inside the braces.** `{language.capitalize()}` runs code and
   inserts the result.
3. **`\n\n` is an escape sequence** — a backslash plus a letter meaning a
   character you cannot type directly. `\n` is a newline, `\t` a tab, `\\` a
   literal backslash.

**And one warning that becomes important in Chapter 31.** Never build a
database query or a shell command by inserting user text into a string. That
is how injection attacks work. Placing user text into a *prompt* is a related
risk — prompt injection — and this repository takes it seriously precisely
because documents are untrusted input.

---

# Part D — Making Decisions

## D.1 Booleans and truthiness

**What it is.** A **conditional** runs some code only when something is true.

**Why it exists.** Without it, a program does the same thing every time. Every
useful behaviour — permission checks, error handling, choosing a path — is a
decision.

```python
age = 20
if age >= 18:
    print("adult")
else:
    print("minor")
```

**Indentation is the syntax.** Most languages use braces to mark a block;
Python uses the indentation itself. Four spaces is the convention. This is
Python's most controversial decision and its reasoning is consistent with A.2:
**the indentation was always there for humans; making it meaningful removes the
possibility of it lying to you.** In brace languages, code can be indented to
look like it belongs to an `if` while actually not belonging to it. That bug
cannot exist in Python.

**Multiple branches:**

```python
if score >= 80:
    grade = "HIGH"
elif score >= 50:
    grade = "MEDIUM"
else:
    grade = "LOW"
```

`elif` is "else if". Branches are tested top to bottom and the first true one
wins, so **order matters**: if you put `score >= 50` first, nothing would ever
be HIGH.

## D.2 Truthiness — a convenience that caused a real security bug

Python lets you use non-boolean values in a condition. Each type has a rule for
what counts as false:

| Value | Truth |
|---|---|
| `False`, `None` | false |
| `0`, `0.0` | false |
| `""` empty string | false |
| `[]` empty list, `{}` empty dict, `set()` | false |
| everything else | true |

So `if my_list:` means "if the list has anything in it".

**This is convenient and it is a trap**, because it merges several different
states into one. `None`, `[]`, `0` and `""` are four distinct situations, and
truthiness treats them identically.

**The real defect.** From commit `8fd0f22`, describing the retrieval path:

> *"Deep Research collapsed an EMPTY document_ids list to None via
> `[...] if document_ids else None`, turning "the user attached no documents"
> into "apply no document filter", which scanned every READY chunk in the
> database."*

Trace it precisely. The code meant: *if there are document ids, use them.* But
an empty list is falsy, so an empty list became `None`, and downstream `None`
meant *"do not filter by document at all"*. **"The user selected no documents"
became "search everything belonging to everyone."**

The fix is a language-level habit worth adopting permanently:

```python
if document_ids is not None:          # tests IDENTITY, not truthiness
    stmt = stmt.where(Document.id.in_(document_ids))
```

`is not None` asks exactly one question: is this the `None` object? An empty
list passes that test and keeps its meaning.

**The rule:** when `None` and "empty" mean different things — and they usually
do — test for `None` explicitly. This is Chapter 03's *"every state value must
mean exactly one thing"*, enforced in syntax.

## D.3 `is` versus `==`

- `==` asks **are these values equal?**
- `is` asks **are these the same object in memory?**

Use `is` only with `None`, `True` and `False`, which exist as single shared
objects. For everything else use `==`. `"hello" is "hello"` may be `True` or
`False` depending on internal details you should never rely on.

You saw the correct use in
[`backend/app/core/tenant_scope.py`](../backend/app/core/tenant_scope.py):

```python
    raw = _current_owner.get()
    if raw is _SYSTEM:
        return
    if raw is None:
        raise TenantScopeMissing(...)
```

Three states, three identity tests: the system marker, no scope at all, and a
real owner id. Truthiness could not distinguish them — and getting that
distinction wrong here would mean serving every tenant's data.

---

# Part E — Repetition

## E.1 Why loops exist

**The problem.** You have 200 chunks to process. Writing the same three lines
200 times is impossible to maintain and impossible when the number is not known
in advance.

**A loop repeats instructions instead of copying them.**

```python
for chunk in chunks:
    print(chunk)
```

Read it as English: *for each chunk in chunks, print it.* On each pass, the
name `chunk` refers to the next item.

**Counting loops** use `range`:

```python
for i in range(5):        # 0, 1, 2, 3, 4
    print(i)
```

`range(5)` produces the numbers 0 to 4 — starting at zero and stopping *before*
the end. **Zero-based counting** is universal in programming, and the reason is
historical: an index is an *offset* from the start of a block of memory, and
the first item is zero away from the start.

**`while` loops** repeat until a condition stops being true:

```python
while not done:
    done = do_some_work()
```

Use `for` when you know what you are iterating over; use `while` when you are
waiting for a condition. **A `while` loop with no way to become false is an
infinite loop**, and it will pin a CPU core at 100% until killed.

## E.2 Controlling a loop

```python
for item in items:
    if item.is_broken:
        continue          # skip to the next item
    if budget_exhausted:
        break             # leave the loop entirely
    process(item)
```

**`break` is the important one**, because it appears in this repository doing
something significant. From `grounding_service.py`:

```python
        for candidate in selected_candidates:
            chunk_tokens = len(candidate["text_content"]) // 4 
            if current_token_estimate + chunk_tokens > max_tokens:
                logger.warning(f"[Tracing] Token budget exceeded ({max_tokens}). Halting evidence injection.")
                break
                
            current_token_estimate += chunk_tokens
            accepted_evidence.append(candidate)
```

Now you can read every line:

- `for candidate in selected_candidates:` — one pass per piece of evidence.
- `len(...) // 4` — estimate this piece's token cost (B.4, C.2).
- `if current + chunk > max:` — would adding it exceed the budget?
- `logger.warning(...)` then `break` — stop adding, and **say so**. This is
  Chapter 01's loud-degradation rule expressed in three lines: the truncation
  is a fact someone may need later, so it is recorded rather than silent.
- `+=` is shorthand for `current = current + chunk`.
- `.append(...)` adds to the end of a list.

**Why `break` rather than checking every candidate?** Because the list is
already sorted by importance, so once the budget is full, nothing later can be
included either. Stopping is both correct and cheaper.

## E.3 `enumerate` and `zip`

**`enumerate`** gives you the position *and* the item:

```python
for rank, name in enumerate(["alice", "bob"]):
    print(rank, name)      # 0 alice / 1 bob
```

**Why it exists.** The alternative — keeping your own counter and incrementing
it — is three extra lines and a chance to forget one.

**A real use**, from
[`backend/app/services/retrieval_service.py`](../backend/app/services/retrieval_service.py),
implementing Reciprocal Rank Fusion:

```python
        for rank, (chunk, page_number, filename, similarity) in enumerate(rows_vec):
            chunk_id = str(chunk.id)
            ...
            fused_scores[chunk_id] += 1.0 / (rrf_k + rank + 1)
```

Two features at once. `enumerate` provides `rank`, which **is** the position in
the ranked list — exactly what RRF needs. And the second name is not one name
but a pattern in brackets: each row contains four values, and they are
**unpacked** into four names in one step.

**Unpacking** works anywhere:

```python
a, b = 1, 2
first, second = ["x", "y"]
text, chunks = get_owned_document_text(...)      # a real one, Part G
```

**`zip`** walks two collections together:

```python
for name, score in zip(names, scores):
    print(name, score)
```

---

# Part F — Functions

This is the most important part of the chapter. Everything after it is built on
functions.

## F.1 What a function is and why it exists

**A function is a named, reusable group of instructions.**

**The problem it solves.** Without functions, code that must happen in five
places is written five times — and when it changes, you must find all five.
Chapter 03 has a whole vocabulary for what goes wrong then: duplicated
decisions, shotgun surgery, the choke point that does not exist. **A function is
the smallest unit of "decide it once".**

**The second problem it solves, which beginners underestimate: naming.** A
function gives a name to an idea. `resolve_workspace_id(slug)` tells you what
is happening; the six lines inside it do not.

## F.2 Defining and calling

```python
def greet(name):
    return f"Hello, {name}"

message = greet("Priya")
```

Every word:

- `def` — "define a function" (a statement, not an expression).
- `greet` — the name. Lowercase with underscores, by convention.
- `(name)` — the **parameter**: a variable that will hold whatever the caller
  passes.
- `:` and indentation — the body, as with `if`.
- `return` — send a value back and stop. A function with no `return` returns
  `None`.

**Argument versus parameter:** the parameter is the name in the definition;
the argument is the actual value passed in. People use them interchangeably;
knowing the difference helps when reading error messages.

## F.3 Default values and keyword arguments

```python
def retrieve(query, top_k=5, threshold=0.0):
    ...

retrieve("notice period")                      # uses the defaults
retrieve("notice period", 30)                  # positional
retrieve("notice period", threshold=0.5)       # by name — clearer
```

**Why defaults exist.** So a function can have many options without every
caller supplying all of them.

**Why keyword arguments matter in production.** Compare:

```python
prepare_grounded_context(db, query, owner, ws, 30, 5, 0.0, 0.0)
```

against the real call in `query.py`:

```python
    grounding_payload = await GroundingService.prepare_grounded_context(
        db=db,
        query=request.query,
        owner_id=uuid.UUID(current_user["id"]),
        workspace_id=resolve_workspace_id(current_user["workspace_id"]),
        final_top_k=request.top_k,
        similarity_threshold=request.similarity_threshold
    )
```

The first is unreadable and one wrong position silently changes behaviour. The
second cannot be misread. **Use keyword arguments for anything that is not
obvious from context** — this is not style, it is defect prevention.

## F.4 The mutable default trap

```python
def add_item(item, basket=[]):        # WRONG
    basket.append(item)
    return basket
```

The default value is created **once, when the function is defined**, not each
time it is called. So every call without a basket shares the same list, and it
grows forever across calls. This is the direct consequence of B.2's model:
the default is an object, and `basket` is a tag on it.

```python
def add_item(item, basket=None):      # correct
    if basket is None:
        basket = []
    basket.append(item)
    return basket
```

Note that the fix uses `is None` (D.2) for exactly the reason taught there.

## F.5 Scope

**Scope** is where a name is visible.

```python
count = 0                  # module scope

def increase():
    count = 5              # a NEW local name; the outer one is untouched
    print(count)           # 5

increase()
print(count)               # 0
```

**Why Python works this way.** If assigning inside a function could silently
change outer variables, no function would be safe to call — you could never
know what it touched. **Local by default is a safety rule**, and it is the same
isolation principle as processes in Chapter 05.

To deliberately change a module-level name you must say so:

```python
_unavailable_logged = False

def get_redis():
    global _unavailable_logged
    ...
    _unavailable_logged = True
```

That is real code from
[`backend/app/core/redis_client.py`](../backend/app/core/redis_client.py). The
`global` keyword is a warning sign — shared mutable state — and here it is
justified and explained: *"Log the failure once per process, not once per
request."* Without it, a Redis outage would write an error line on every single
request and drown the log.

**Senior engineers treat `global` as a smell that must be argued for.** This one
is argued for, in a comment, which is the standard.

## F.6 Docstrings

A string as the first thing in a function is a **docstring**: documentation
that travels with the code.

```python
def resolve_workspace_id(value):
    """Accept a UUID string or a workspace slug; return a stable UUID."""
```

**Why they matter more than comments.** Tools can read them, editors show them
on hover, and they are attached to the function rather than to a line that may
move. This repository's docstrings are unusually good and often record *why*
and *what this does not cover* — the tenant-scope module's "Limits — read
before relying on this" section is a docstring.

## F.7 A complete real function, line by line

Now read a whole file you have already met conceptually. This is
[`backend/app/core/workspace.py`](../backend/app/core/workspace.py), and by the
end of this section every character of it should be clear.

```python
import uuid
from typing import Optional
from fastapi import HTTPException

WORKSPACE_NAMESPACE = uuid.NAMESPACE_DNS

DEFAULT_WORKSPACE_SLUG = "general"

KNOWN_WORKSPACE_SLUGS = frozenset(
    {"general", "hr", "legal", "finance", "research", "study", "exam"}
)


def resolve_workspace_id(value: Optional[str]) -> uuid.UUID:
    """Accept a UUID string or a workspace slug; return a stable UUID."""
    if value is None or value == "":
        value = DEFAULT_WORKSPACE_SLUG

    candidate = str(value).strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Invalid workspace identifier")

    try:
        return uuid.UUID(candidate)
    except (ValueError, AttributeError):
        return uuid.uuid5(WORKSPACE_NAMESPACE, candidate.lower())
```

Reading it:

- **`import uuid`** — bring in a standard library module (Part H).
- **`WORKSPACE_NAMESPACE`, `DEFAULT_WORKSPACE_SLUG`** — module-level constants.
  ALL_CAPS is a convention meaning "do not change this at runtime"; Python does
  not enforce it, and every Python programmer respects it anyway.
- **`frozenset({...})`** — an unchangeable set (Part G). A set because the only
  question ever asked is "is this slug one of ours?", and frozen because it must
  never be modified.
- **`def resolve_workspace_id(value: Optional[str]) -> uuid.UUID:`** — the
  colons and arrow are **type hints** (Part K): the parameter is text or
  nothing, the result is a UUID. They document intent; they do not enforce it.
- **`if value is None or value == ""`** — exactly D.2's lesson. Both "nothing
  was passed" and "empty text was passed" are treated as "use the default", and
  the code says so explicitly rather than relying on truthiness.
- **`str(value).strip()`** — force to text, remove surrounding whitespace.
  Defensive, because the caller might pass something unexpected.
- **`if not candidate: raise HTTPException(...)`** — after stripping, if
  nothing remains, refuse. `raise` produces an error (Part I). **This is
  fail-closed**, Chapter 03's vocabulary: an unusable input stops the request
  rather than being guessed at.
- **`try: return uuid.UUID(candidate)`** — attempt to read the text as a UUID.
- **`except (ValueError, AttributeError):`** — if it was not a UUID, do the
  other thing. Note it names the two specific errors expected rather than
  catching everything (Part I.4 explains why that matters enormously).
- **`uuid.uuid5(NAMESPACE, candidate.lower())`** — derive a UUID from the name.
  Same input, same output, in every process, forever — which is decision D-014.

**Why production code differs from beginner code**, visible in this one small
function: it validates its input, it names its constants, it distinguishes
`None` from empty, it catches only the errors it expects, it declares its types,
and it explains itself in a docstring. A beginner version would be two lines and
would be wrong in four ways.

---

# Part G — Data Structures

Chapter 05 said memory holds values. These are the shapes Python gives them.

## G.1 Lists — ordered, changeable

```python
names = ["alice", "bob", "carol"]
names[0]                 # "alice"    — indexing starts at 0
names[-1]                # "carol"    — negative counts from the end
names[0:2]               # ["alice", "bob"]   — a slice: start included, end excluded
names.append("dan")      # add to the end
names.remove("bob")      # remove by value
len(names)               # 3
"alice" in names         # True — but this SCANS the whole list
```

**The performance fact you must know.** `x in some_list` checks every item one
by one. With 10 items that is nothing; with 100,000 items inside a loop that
runs 100,000 times, it is ten billion comparisons and your program appears to
hang. This is why sets exist (G.4).

## G.2 Tuples — ordered, fixed

```python
point = (3, 4)
text, chunks = get_owned_document_text(...)     # unpacking a returned tuple
```

**Why have both lists and tuples?** Three reasons:

1. **Intent.** A tuple says "this group is a unit and will not change".
2. **Safety.** It cannot be modified by accident, including by a function you
   passed it to.
3. **Capability.** Because it is immutable, a tuple can be a dictionary key
   (G.3). A list cannot.

**A real one from this repository**, in
[`backend/app/core/document_access.py`](../backend/app/core/document_access.py):

```python
) -> tuple[str, list[dict[str, Any]]]:
    """Return `(full_text, chunks)` for a document the caller owns."""
```

The function returns two related things at once — the full text and the list of
chunks. A tuple is the natural way to say "these belong together and there are
exactly two".

## G.3 Dictionaries — the workhorse

**What it is.** A **dictionary** maps keys to values. Look up by key, get the
value, immediately.

```python
config = {"top_k": 12, "rerank_n": 8, "chunk_pref": "medium"}
config["top_k"]                  # 12
config["missing"]                # KeyError — crashes
config.get("missing")            # None — safe
config.get("missing", 0)         # 0 — safe with a default
config["new_key"] = 5            # add or replace
for key, value in config.items():
    print(key, value)
```

**Why it exists and why it is fast.** A dictionary uses a **hash table**: the
key is converted to a number that says roughly where to look, so lookup does
not depend on how many items there are. A list scan gets slower as it grows; a
dictionary lookup does not. *(If you are studying data structures separately,
this is the hash map you already know, and Python's `dict` is one.)*

**`.get()` versus `[ ]` is a real decision, not a style choice.** `[ ]` crashes
on a missing key; `.get()` returns `None` or a default. Which you want depends
on whether a missing key is a *bug* or an *expected absence*. **If it is a bug,
crash** — a KeyError with a traceback is far better than a `None` that flows
onward and causes a confusing failure later. This is fail-fast at the level of
one line.

**A real dictionary of dictionaries**, from `config.py`:

```python
    WORKSPACE_RETRIEVAL_CONFIG: ClassVar[Dict[str, Any]] = {
        "exam":     {"top_k": 12, "rerank_n": 8,  "chunk_pref": "medium"},
        "hr":       {"top_k": 18, "rerank_n": 12, "chunk_pref": "small"},
        "legal":    {"top_k": 10, "rerank_n": 6,  "chunk_pref": "large"},
        ...
    }
```

Seven workspaces, each with its own settings, in one lookup table. Without a
dictionary this would be a long chain of `if workspace == "exam": ... elif ...`
— which is more code, slower to read, and must be edited in several places to
add a workspace. **A table is data; a chain of `if`s is code. Prefer data.**

## G.4 Sets — unique, unordered, fast membership

```python
seen = set()
seen.add("a")
seen.add("a")           # no effect — sets hold each value once
"a" in seen             # True, and FAST regardless of size
```

**A real use**, from `grounding_service.py` — removing duplicate chunks:

```python
        seen_chunks = set()
        unique_candidates = []
        for c in candidates:
            if c["chunk_id"] not in seen_chunks:
                seen_chunks.add(c["chunk_id"])
                unique_candidates.append(c)
```

**Why a set and not a list?** Because `not in` runs once per candidate. With a
list it would scan everything seen so far each time — work that grows with the
square of the number of candidates. With a set each check is constant. The
correct data structure removes the problem rather than optimising it.

**Why keep a separate list too?** Because sets have no order, and the order of
retrieval results is meaningful. So: a set for *asking*, a list for *keeping*.
That pairing is a common and worth-memorising pattern.

## G.5 Comprehensions

**What they are.** A compact way to build a list, dict or set from another
collection.

```python
squares = []
for n in numbers:
    squares.append(n * n)
```

becomes

```python
squares = [n * n for n in numbers]
```

Read it as: *the value `n * n`, for each `n` in numbers.* You can filter too:

```python
long_names = [n for n in names if len(n) > 3]
```

**Why they exist.** The loop version spends three lines on mechanics — create,
append, repeat — and one on the idea. The comprehension is the idea.

**Dictionary comprehensions** build dictionaries, and here is a real one from
`language_detector.py`:

```python
    char_counts = {lang: len(pattern.findall(query))
                   for lang, pattern in LANGUAGE_PATTERNS.items()}
```

*For each language and its pattern, count how many characters in the query
match, and store that count under the language's name.* One line, and it reads
as a sentence.

**Generator expressions** use round brackets and produce items one at a time
rather than building a whole list (Part M). One appears in
`document_access.py`:

```python
    text = "\n".join(c.text_content for c in chunks if c.text_content)
```

*Join with newlines the text of every chunk that has text.* The `if` filters
out empty chunks. Nothing intermediate is built — the items are produced as
`join` consumes them, which matters when there are thousands of chunks.

**When not to use a comprehension.** When it needs more than one condition and
a transformation, or when it stops fitting on two lines. Then a plain loop is
clearer, and clarity wins.

## G.6 Choosing the right structure

| Question you ask most often | Use |
|---|---|
| "give me item number N" / "keep them in order" | list |
| "is X present?" / "remove duplicates" | set |
| "what is the value for key X?" | dict |
| "these values belong together and will not change" | tuple |

**Choosing wrongly is not a style error; it is a performance error**, and it is
one of the few places where a beginner decision shows up as a production
incident.

---

# Part H — Modules, Imports, and Packages

## H.1 The problem

One file cannot hold a system with 425 files. And code written once should be
usable elsewhere without copying.

**A module is a file of Python code.** **An import is reusing code written
somewhere else.**

```python
import uuid                                  # the whole module
uuid.uuid4()                                 # used with its name in front

from typing import Optional                  # one name out of a module
from app.models.document import Document     # from this project's own code
```

**Why both forms exist.** `import x` keeps the origin visible at every use,
which is good for readability. `from x import y` is shorter, which is good when
the name is used constantly. This repository uses both, appropriately: `uuid`
is imported whole (so `uuid.UUID` reads clearly), while `Document` is imported
directly (because writing the full path each time would be noise).

**What happens if imports disappear?** Every file would need every line of
every library it uses. There would be no libraries — and therefore no
FastAPI, no PyMuPDF, no ecosystem, which per decision D-011 is the entire
reason this project is written in Python.

## H.2 Packages

**A package is a folder of modules.** `app.core.config` means: the folder
`app`, the folder `core`, the file `config.py`.

Traditionally a folder becomes a package by containing a file named
`__init__.py`, which may be empty. Modern Python also allows **namespace
packages** — folders with no `__init__.py`.

**And that distinction is a documented trap in this repository.** From
`CLAUDE.md`'s pitfalls:

> *"`app/tasks/` vs `app/workers/tasks/` are **two different packages**. The
> former holds plain async helpers (`report_tasks`, `eval_tasks`); the latter
> holds real Celery tasks. `app/tasks/` has no `__init__.py` (namespace
> package)."*

Two folders with the same last name, different contents, different behaviour.
Importing from the wrong one gives you a module that exists and does not do
what you expect — the worst kind of error, because there is no error.

## H.3 Import runs code — and this has consequences

**The most misunderstood fact about imports:** importing a module *executes it,
top to bottom*, the first time. Function definitions run (creating the
functions), and so does everything else at module level.

Python then caches the module, so a second import of the same module does not
re-run it. **A module's top-level code runs exactly once per process.**

**Why this matters here.** In
[`backend/app/db/session.py`](../backend/app/db/session.py), the database
engine is created at module level — so it is created when the module is first
imported. The file's own comment explains the consequence:

> *"this engine is created at IMPORT time, in the Celery parent process, and
> every prefork child inherits it across fork()."*

Chapter 05 explained why inheriting network connections across a fork corrupts
them. Now you can see the *language-level* cause: the object existed because
an import ran code, before any child process existed.

**The senior habit that follows:** be deliberate about what happens at import
time. Anything expensive, anything that opens a connection, anything with side
effects — ask whether it should be created on import or created when first
needed.

## H.4 Circular imports, and the lazy import

If module A imports B, and B imports A, Python may hit a half-finished module
and fail with a confusing error.

**The clean fix is usually architectural** — one of them should not depend on
the other. Sometimes the layering makes that expensive, and then the tool is to
import *inside* the function, so the import happens when called rather than at
module load.

A real one, in [`backend/app/core/auth.py`](../backend/app/core/auth.py):

```python
def _set_request_owner(user_id: str) -> None:
    """Bind the current request's owner scope. Imported lazily to keep
    `core.auth` free of a module-level dependency on the ORM layer."""
    import uuid as _uuid

    from app.core.tenant_scope import _current_owner
```

The docstring states the reason: the authentication module should not depend on
the database layer at import time. The import inside the function keeps the
dependency at *call* time instead.

**Note the underscore prefixes.** `_set_request_owner` and `_current_owner`
begin with `_`, which by convention means *internal — not part of the public
interface of this module*. Python does not enforce it. Every Python programmer
respects it, and a linter will warn you.

---

# Part I — Errors and Exceptions

## I.1 Two kinds of error

**A syntax error** means the text is not valid Python. Nothing runs at all.

**A runtime error** means the code was valid but something went wrong while
running: a missing key, a wrong type, a file that is not there.

**Why the distinction matters.** A syntax error is found by the machine before
anything happens. A runtime error only appears when the offending line
executes — which may be in a rare branch, at 3 a.m., in production.

## I.2 Reading a traceback

When an error is not handled, Python prints a **traceback**: the chain of calls
leading to the failure.

```
Traceback (most recent call last):
  File "app/api/v1/endpoints/query.py", line 442, in stream_query
    payload = await GroundingService.prepare_grounded_context(...)
  File "app/services/grounding_service.py", line 124, in prepare_grounded_context
    chunk_tokens = len(candidate["text_content"]) // 4
KeyError: 'text_content'
```

**Read it from the bottom.** The last line is the actual error and its type.
The line above it is where it happened. Above that is who called that. The
phrase "most recent call last" tells you the order.

**The single most common beginner mistake is reading the top first, or not
reading it at all.** A traceback contains the file, the line, the code, and the
error type. It is the best evidence you will ever get for free.

## I.3 Handling exceptions

**What an exception is.** An **exception** is Python's way of saying "I cannot
continue normally here". It stops the current line and travels up through the
callers until something handles it — or the program stops.

**Why this design, rather than returning an error code?** Because error codes
must be checked at every level, and can be ignored silently. An exception
cannot be ignored; it will stop the program unless someone deliberately
handles it. **The default is loud**, which matches this repository's most
important invariant.

```python
try:
    doc_uuid = uuid.UUID(str(document_id))
except (ValueError, TypeError):
    raise HTTPException(status_code=422, detail="Invalid Document ID format.")
```

- `try:` — attempt this.
- `except (ValueError, TypeError):` — if one of *these specific* errors occurs,
  do this instead.
- `raise` — produce an exception yourself.

Two more clauses complete the picture:

```python
try:
    ...
except SomeError as exc:      # `as exc` captures the exception object
    ...
else:
    ...                       # runs only if NO exception happened
finally:
    ...                       # runs ALWAYS — success, failure, or return
```

**`finally` is for cleanup**, and it is not optional politeness. A real example
from [`backend/app/api/v1/endpoints/query.py`](../backend/app/api/v1/endpoints/query.py):

```python
        try:
            cached = await redis.get(cache_key)
        finally:
            await redis.close()
```

With the comment above it explaining exactly why:

> *"close() must be in a finally: when redis.get() raises (dropped connection,
> timeout), the outer `except Exception: pass` swallows it and the connection
> is leaked. This runs on every query, so a Redis blip used to exhaust the
> pool."*

**Trace the failure that comment describes.** A connection is opened. Something
fails. The failure is swallowed. The connection is never closed. It happens on
every query. Connections run out. **A missing four-letter keyword becomes a
resource exhaustion outage.**

## I.4 The bare `except` — the most expensive mistake in this repository

```python
try:
    import aioredis
    return await aioredis.from_url(settings.REDIS_URL)
except Exception:
    return None
```

That code looks careful. It is a catastrophe, and
[`backend/app/core/redis_client.py`](../backend/app/core/redis_client.py) opens
with a full account of why:

> *"`aioredis` is **not installed** in this environment … So every one of those
> calls raised `ModuleNotFoundError`, was swallowed by the bare `except`, and
> returned `None` — with **no log line anywhere**."*

And what that silently disabled: an advertised abuse-prevention control, the
retrieval cache (so every query paid full cost while the code *looked* like it
had a cache), and two rate limits which failed open.

Then the sentence that states the principle:

> *"The mechanism is the point: `except Exception: return None` makes a MISSING
> DEPENDENCY indistinguishable from a cache miss. Both look like 'no Redis
> today'."*

**This is Chapter 03's lesson in one language construct.** Two different states
— "the library is not installed" and "the cache had no entry" — collapsed into
one value. Nobody could tell them apart, so nobody looked.

**The rules that follow, and they are permanent:**

1. **Catch the narrowest exception that can actually occur.**
   `except (ValueError, TypeError)` states what you expect.
2. **If you must catch broadly, log loudly**, including the exception type.
3. **Never let a caught exception produce a value that already means something
   else.**

The repaired version does all three:

```python
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

Note `type(exc).__name__` — the *name of the error's type*. "ModuleNotFoundError"
and "ConnectionRefusedError" send you to completely different investigations,
and the difference is one expression.

Note also that this is `logger.error`, not `print`. A **logger** records a
message with a severity level, a timestamp and its source module. Severity is
what lets you say "show me only the errors" across a million lines of output.
And the comment `# noqa: BLE001` tells the linter that this broad catch is
deliberate — it is a signed exception to a rule, not an oversight.

## I.5 Custom exceptions

You can define your own error type, and it is worth doing when the *kind* of
failure matters:

```python
class TenantScopeMissing(RuntimeError):
    """A scoped model was queried with no owner scope established."""
```

That is from `tenant_scope.py`, and it uses classes, which is Part J. `class X(Y)`
means "X is a kind of Y" — so this is a kind of RuntimeError and can be caught
either as itself or as a RuntimeError.

**Why bother, instead of raising a generic error?** Because callers can catch
*this specific thing* without accidentally catching everything else, and
because the name appears in logs and tracebacks. `TenantScopeMissing` in a
traceback tells you what happened before you read a single line of code.

---

# Part J — Objects and Classes

## J.1 Everything is an object

**An object is a value that carries both data and the operations that belong to
it.** In Python, *every* value is an object, including numbers and functions.

That is why `"hello".upper()` works: the string is an object, and `upper` is
one of its **methods** — a function that belongs to it. The dot means "reach
inside this object".

## J.2 Why classes exist

**The problem.** You have many things of the same kind — many documents, each
with a filename, a size, a status. Keeping them as loose variables does not
scale, and keeping them as dictionaries means every piece of code must remember
which keys exist and what they mean.

**A class describes a new kind of object**: what data it holds and what it can
do.

```python
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height

r = Rectangle(3, 4)
r.area()            # 12
```

Every part:

- `class Rectangle:` — define a new kind of thing. Class names use CapitalCase.
- `__init__` — the **initialiser**, run automatically when a new object is
  created. Names with double underscores at both ends are called **dunder**
  methods, and Python calls them for you at defined moments.
- `self` — the object being worked on. It is passed automatically; you write it
  as the first parameter and never pass it at the call site. **This is Python
  being explicit where other languages are implicit**, consistent with A.2.
- `self.width = width` — store data on the object. These are **attributes**.
- `def area(self):` — a **method**: a function belonging to the object.

## J.3 Static methods — and why this repository uses them

Sometimes a group of functions belongs together conceptually but does not need
any per-object data.

```python
class GroundingService:
    @staticmethod
    async def prepare_grounded_context(db, query, owner_id, ...):
        ...
```

That is the real declaration from `grounding_service.py`. The `@staticmethod`
line is a **decorator** (Part N) saying: this method does not receive `self`,
because there is no object state to receive.

**Why write it this way rather than as a plain function?** Because the class
name becomes part of the call — `GroundingService.prepare_grounded_context(...)`
— which tells the reader where the behaviour lives. It is namespacing, not
object-orientation.

**Would another language do this differently?** Yes, and it is worth knowing.
In Java everything must be in a class, so this shape is forced. In Go there are
no classes and this would be a package-level function. Python allows both, and
this repository's choice is a readability preference, not a requirement. **A
senior engineer should be able to say "this is a stylistic choice, and here is
what it buys" rather than assuming it is necessary.**

## J.4 Inheritance and mixins

**Inheritance** lets one class build on another.

```python
class TenantScopeMissing(RuntimeError):
    ...
```

`TenantScopeMissing` gets everything `RuntimeError` has, and adds its own
identity.

**A mixin** is a small class that exists to add one capability to other classes,
and this repository has a good one:

```python
class TenantScoped:
    """Mixin marking a model as owned by exactly one user.

    Declares the tenant key itself so the column definition lives in one place
    rather than being copy-pasted into every model — the same duplication
    argument that motivates the query hook below.
    """

    @declared_attr
    def owner_id(cls):
        return Column(UUID(as_uuid=True), index=True, nullable=False)
```

Any model that inherits `TenantScoped` automatically gets an `owner_id` column,
*and* becomes visible to the security hook that filters by owner. One
inheritance declaration carries both the data and the protection.

**Why this is good design in one sentence:** Chapter 03's choke-point rule
expressed in the type system — you cannot have the column without the
protection, or the protection without the column.

## J.5 Enums — a fixed set of allowed values

**The problem.** A document's status is one of eight things. Storing it as free
text means `"READY"`, `"Ready"` and `"redy"` are all possible, and the typo is
found in production.

**An enum is a named, fixed set of values.**

```python
class DocumentStatus(str, enum.Enum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    DEDUPLICATED = "DEDUPLICATED"
```

That is real, from
[`backend/app/models/document.py`](../backend/app/models/document.py). Now
`DocumentStatus.READY` is a value you cannot misspell — a typo is an
`AttributeError` immediately, not a silent mismatch later.

**Why `(str, enum.Enum)` and not just `enum.Enum`?** Because inheriting from
`str` as well means each member *is* a string. It can be compared to text,
serialised to JSON, and written to a database column without conversion. That
is a small, deliberate design decision with real ergonomic consequences, and
noticing it is the kind of reading skill this chapter is training.

**And notice what the eight values encode:** the document pipeline from Chapter
01, as a set of legal states. `READY` is the only one retrieval accepts, which
is why `.where(Document.status == "READY")` appears in the retrieval query.
**A type is documentation that the program can check.**

## J.6 A model class, read completely

```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, index=True, nullable=False)
    file_hash = Column(String, index=True, nullable=False)
    ...
    owner_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

You are not expected to know SQLAlchemy yet — Chapter 15 covers it. What you
*can* now read is the Python:

- `class Document(Base)` — inherits from `Base`, which is what marks it as a
  database model.
- `__tablename__` — a dunder attribute the library looks for.
- Each `Column(...)` is a class attribute: a value belonging to the class
  itself rather than to one instance.
- `nullable=False` means the database will reject a missing value.

**And one line carries a security decision you already know.** `owner_id` is
`nullable=False`, so a row without an owner cannot be written at all. Chapter
03's tenancy work relies on that: *"`owner_id` is `NOT NULL`, so a missed write
fails loudly at the database instead of writing an unowned row."* **The
database enforces what the developer might forget** — the same principle as
making the parameter required, one layer down.

## J.7 Context managers and `with`

**The problem.** Some things must be cleaned up: files closed, connections
returned, locks released. `finally` (I.3) works but must be repeated at every
use.

**A context manager packages "set up" and "tear down" into one object**, used
with `with`:

```python
with open("notes.txt") as f:
    content = f.read()
# the file is closed here, automatically, even if an error occurred
```

Writing one is easiest with a decorator from the standard library, and this
repository has a real example in `tenant_scope.py`:

```python
@contextmanager
def tenant_scope(owner_id: uuid.UUID | str) -> Iterator[None]:
    """Scope every ORM read in this context to a single owner."""
    if isinstance(owner_id, str):
        owner_id = uuid.UUID(owner_id)
    token = _current_owner.set(owner_id)
    try:
        yield
    finally:
        _current_owner.reset(token)
```

Everything before `yield` is setup. `yield` hands control to the `with` block.
Everything after — inside `finally` — is teardown, guaranteed to run.

**Why this is exactly the right tool here.** The scope *must* be cleared when
the block ends, whatever happens. If an exception escaped and the scope stayed
set, the next piece of work could inherit someone else's identity. `finally`
inside a context manager makes that impossible rather than merely unlikely.

*(`yield` is Part M. `@contextmanager` is Part N. Both are used here before
being taught, which is why they are the next two parts.)*

---

# Part K — Type Hints

## K.1 What they are

**The problem.** Python does not require types, so a function's signature does
not say what it accepts or returns. `def process(data)` — is `data` a string, a
list, a document?

**Type hints are annotations that state the intent.**

```python
def resolve_workspace_id(value: Optional[str]) -> uuid.UUID:
```

`value: Optional[str]` — either text or `None`. `-> uuid.UUID` — returns a UUID.

**The crucial fact:** Python does **not** enforce them at runtime. Passing a
number to a parameter hinted as `str` runs anyway and may fail later. Hints are
for humans and for tools.

**Then why bother?** Four concrete returns:

1. **A separate checker** (`mypy`) can read them and find mistakes without
   running anything.
2. **Editors use them** for autocompletion and instant warnings.
3. **They are documentation that cannot drift silently**, because the checker
   complains when it stops matching.
4. **Some libraries make them do real work.** FastAPI reads them to validate
   incoming requests and generate documentation (Chapter 14), and Pydantic
   uses them to enforce types at runtime (K.3).

## K.2 The notations you will meet

```python
from typing import Optional, List, Dict, Any, Literal

name: str
count: int
scores: List[float]                 # a list of floats
config: Dict[str, Any]              # keys are text, values are anything
maybe: Optional[str]                # str or None — same as `str | None`
mode: Literal["grounded", "general"]   # only these two exact strings
```

Newer Python allows lowercase built-ins and the `|` union operator, which this
repository uses in its newer files:

```python
    document_id: uuid.UUID | str,
) -> tuple[str, list[dict[str, Any]]]:
```

Reading that return type: a tuple of exactly two things — a string, and a list
of dictionaries whose keys are strings and whose values are anything. **The
type is a sentence describing the shape of the data**, and once you can read it,
you can use a function without reading its body.

**`from __future__ import annotations`** at the top of some files makes the
newer syntax work on older versions by treating annotations as text rather than
evaluating them. You will see it in `tenant_scope.py`, `redis_client.py` and
`document_access.py`.

## K.3 Pydantic — types that actually enforce

**The problem type hints do not solve.** Data arriving from a browser is
untrusted. Hints do not check it.

**Pydantic** is a library where declaring a class with typed fields produces
runtime validation. Here is a real one,
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

Because it inherits `BaseModel`, this class does real work at runtime:

- **`query: str` with no default is required.** A request without it is
  rejected before your code runs.
- **`top_k: int = 5`** — optional, defaults to 5, and `"twelve"` is rejected
  while `"12"` is converted to the number 12.
- **`workspace_id: Optional[UUID]`** — text that is not a valid UUID is
  rejected, and valid text becomes a real UUID object.

**Why this matters so much.** Chapter 05's rule was that the client is under
the user's control and the server is not. This class is the wall. Every
assumption your code makes about the shape of the request is checked here,
once, at the boundary — rather than being re-checked (or forgotten) in twenty
places. **It is a choke point for data validity**, in exactly Chapter 03's
sense.

**And notice the file has four classes: request, evidence, diagnostics,
response.** The response shape is declared as precisely as the request. That is
the API contract from Chapter 05 written as code that the machine enforces.

## K.4 Dataclasses — the lighter alternative

For a plain group of fields that never crosses a trust boundary, the standard
library offers less machinery:

```python
from dataclasses import dataclass

@dataclass
class TrustFactor:
    name: str
    weight: float
    score: float
```

The `@dataclass` decorator writes `__init__`, a readable printout, and equality
comparison for you. No validation, no conversion — and therefore much faster.

**The rule this repository follows, and it is a good one to adopt:** Pydantic
at the edges where data is untrusted (requests, responses, settings);
dataclasses for internal structures that never leave the process. `VeritasTrustReport`
is internal, so it is a dataclass; `QueryRequest` arrives from a browser, so it
is a Pydantic model. **Validation costs time; spend it where the danger is.**

---

# Part L — Iterators and Generators

## L.1 Iteration, underneath

When you write `for x in things`, Python asks `things` for an **iterator** — an
object that produces items one at a time and remembers where it is. That is why
lists, dictionaries, sets, files and ranges can all be looped over: they all
provide one.

Chapter 03's exercise about consuming a blocking iterator used exactly this
protocol, and `next(it, sentinel)` was the manual way to ask for one item with
a fallback when there are none left.

## L.2 Generators

**The problem.** Building a list of a million items uses memory for a million
items — even if you only ever look at one at a time.

**A generator produces values lazily, one at a time, on demand.**

```python
def count_to(n):
    i = 0
    while i < n:
        yield i
        i += 1
```

`yield` is the whole difference. A function containing `yield` does not run when
called; it returns a generator. Each time you ask for the next value, it runs
until the next `yield`, hands the value over, and **freezes** — keeping its
local variables — until asked again.

**Why this is powerful.** Memory stays constant regardless of how many items
there are, and you can represent sequences that are infinite or arrive slowly
over time — like tokens streaming back from an AI model.

**Where this appears in this repository.** Two important places:

**1. The database session**, in `db/session.py`:

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

Setup before `yield`, the session handed to whoever needs it, cleanup after.
FastAPI uses this shape for dependencies — Chapter 14's subject — and the
pattern is the same one as the context manager in J.7: *give the thing out,
guarantee the cleanup.*

**2. Streaming.** The SSE response from Chapter 01 is produced by a generator
that yields one frame at a time. That is why the answer can begin arriving
before it is finished: **there is no complete answer in memory to wait for.**

---

# Part M — Decorators

Decorators appear everywhere in this repository, which is why they are last:
they require functions (F), objects (J), and the idea that a function is itself
a value.

## M.1 The prerequisite: functions are objects

```python
def shout(text):
    return text.upper()

f = shout            # no brackets — the FUNCTION itself, not its result
f("hello")           # "HELLO"
```

A function can be stored in a variable, passed to another function, and
returned from one. Once that clicks, decorators are simple.

## M.2 The problem decorators solve

Suppose ten functions must each log how long they take. Without decorators you
add the same four lines to each — Chapter 03's duplicated decision, in
miniature.

**A decorator is a function that takes a function and returns a new function
with added behaviour.**

Building one from scratch:

```python
import time
import functools

def timed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.3f}s")
        return result
    return wrapper
```

Line by line:

- `def timed(func):` — takes the function to be wrapped.
- `def wrapper(*args, **kwargs):` — the replacement. `*args` collects any
  positional arguments, `**kwargs` any keyword arguments, so the wrapper works
  for **any** function signature.
- `result = func(*args, **kwargs)` — call the original, passing everything
  through unchanged.
- `return result` — hand back what the original returned. Forgetting this line
  makes every decorated function return `None`, and it is the classic bug.
- `@functools.wraps(func)` — copy the original's name and docstring onto the
  wrapper. Without it, every decorated function is called `wrapper` in
  tracebacks and documentation.
- `return wrapper` — the decorator hands back the replacement.

Using it:

```python
@timed
def slow_thing():
    time.sleep(1)
```

**`@timed` above a definition is exactly equivalent to writing
`slow_thing = timed(slow_thing)` after it.** The `@` is only a nicer way to
write that, and knowing this demystifies every decorator you will ever see.

## M.3 Decorators with arguments

```python
@limiter.limit("5/minute")
def register(...):
```

An extra layer: `limiter.limit("5/minute")` is called first and *returns* a
decorator, which is then applied. Three levels of function, which is why they
are usually used rather than written.

## M.4 Every decorator in this repository, now readable

| Decorator | What it does |
|---|---|
| `@staticmethod` | this method takes no `self` |
| `@property` | call this method as if it were an attribute — `settings.async_database_url` |
| `@contextmanager` | turn a generator into a `with`-usable object |
| `@declared_attr` | SQLAlchemy: define a column inside a mixin |
| `@model_validator(mode='after')` | Pydantic: run this check after the object is built |
| `@event.listens_for(Session, "do_orm_execute")` | register a function to run on every ORM query — the tenancy hook |
| `@router.post("/stream")` | FastAPI: this function handles POST requests to this path |
| `@celery_app.task` | Celery: this function can be sent to a worker |
| `@worker_process_init.connect` | Celery: run this when a worker child starts |
| `@limiter.limit("5/minute")` | SlowAPI: cap how often this may be called |

**Look at what they have in common.** Every one is *registration* or
*cross-cutting behaviour*: telling a framework "this function has a role", or
adding something that applies to many functions. That is what decorators are
for, and if you ever write one that does neither, reconsider.

**And one of them is the security control from Chapter 03:**

```python
@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_scope(orm_execute_state) -> None:
```

A decorator is how "filter every database read by owner" attaches itself to
every query without any query asking for it. **The language feature is what
makes the architectural choke point possible.**

---

# Part N — Files

Chapter 05 said a file is a named sequence of bytes, and that turning bytes
into text requires an encoding. Python makes both explicit.

```python
with open("notes.txt", "r", encoding="utf-8") as f:
    content = f.read()
```

- `open(...)` — returns a file object.
- `"r"` — mode: `r` read, `w` write (erases first), `a` append, `b` binary.
- `encoding="utf-8"` — **always state this.** Without it Python uses the
  system default, which differs between Windows and Linux, so the same code
  reads the same file differently on two machines. Chapter 05's latin-1 export
  defect is the same family of bug.
- `with` — guarantees the file is closed (J.7).

Reading line by line, which matters for large files:

```python
with open("big.log", "r", encoding="utf-8") as f:
    for line in f:            # one line at a time; memory stays small
        if "ERROR" in line:
            print(line.strip())
```

**Why not `f.read()` always?** Because it loads the entire file into memory.
For a 2 GB log that is a crash. The loop version is a generator in disguise
(Part L) — the file object hands over one line at a time.

**Where this appears here.** Reading the `.env` file at startup, reading
uploaded documents in the worker, and writing exports. And one detail from
`main.py`'s comment is worth repeating because it is a classic: the environment
file is resolved **relative to the backend root, not the current working
directory** — because Chapter 05 taught that a relative path means different
things depending on where the process was started, and a startup that works
from one folder and fails from another is a miserable bug.

---

# Part O — Reading a Whole Production File

Now the payoff. Here is a complete real function from
[`backend/app/core/document_access.py`](../backend/app/core/document_access.py),
and you should be able to read every line.

```python
async def get_owned_document(
    db: AsyncSession,
    document_id: uuid.UUID | str,
    current_user: dict,
) -> Document:
    """Return the document if it belongs to the caller, else raise 404.

    404 rather than 403 deliberately: a 403 would confirm the id exists and
    belongs to somebody, which is an enumeration oracle.
    """
    try:
        doc_uuid = (
            document_id if isinstance(document_id, uuid.UUID)
            else uuid.UUID(str(document_id))
        )
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid Document ID format.")

    doc = (
        await db.execute(
            select(Document).where(
                Document.id == doc_uuid,
                Document.owner_id == uuid.UUID(current_user["id"]),
            )
        )
    ).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc
```

Working through it:

1. **`async def`** — this function can pause while waiting. For now, read
   `await X` as "do X, and let other work run while waiting". Chapter 07 is
   entirely about this.
2. **The parameters are all type-hinted** (K). `uuid.UUID | str` says the caller
   may pass either form — a deliberate convenience, since some callers already
   have a UUID and others have text from a URL.
3. **The docstring records a security decision** (D-020) rather than describing
   the obvious.
4. **A conditional expression:** `A if condition else B` is an expression
   producing a value (B.1), used here to avoid converting something that is
   already a UUID.
5. **`isinstance(x, T)`** asks "is this value of type T?" — the correct way to
   check a type, rather than comparing `type(x) == T`, because `isinstance`
   also accepts subclasses.
6. **`except (ValueError, TypeError): raise HTTPException(422)`** — narrow
   catch (I.4), converted into a meaningful HTTP status (Chapter 05's status
   families). A malformed id is the caller's mistake, hence 4xx.
7. **The query** filters on **both** the id and the owner. This is Chapter 03's
   entire tenancy lesson in two lines, and the ownership check is not optional
   reinforcement — it *is* the check.
8. **`.scalar_one_or_none()`** — return the single row, or `None` if there was
   none.
9. **`if not doc:`** — truthiness, used correctly here because `None` is the
   only falsy thing this can be.
10. **404, not 403.** The status code is part of the security design.

**Why production code differs from beginner code**, summarised from this one
function: it declares its types, validates its input, converts errors into
meaningful responses at the boundary, catches narrowly, encodes a security
decision in a status code, and explains its reasoning where the reasoning is
not obvious from the code. None of that is complexity for its own sake. **Every
one of those lines is a defect that will not happen.**

---

# Part P — Style, and Why It Is Not Bikeshedding

Python has a style guide called **PEP 8**. The conventions that matter:

| Thing | Convention | Example |
|---|---|---|
| Variables, functions | lowercase with underscores | `chunk_tokens`, `resolve_workspace_id` |
| Classes | CapitalCase | `GroundingService`, `DocumentStatus` |
| Constants | ALL_CAPS | `DEFAULT_WORKSPACE_SLUG` |
| Internal names | leading underscore | `_current_owner`, `_set_request_owner` |
| Indentation | 4 spaces, never tabs | |
| Line length | around 79–100 characters | |

**Why consistency matters more than any individual rule.** When all code looks
the same, differences are *meaningful*. A capitalised name means a class. A
leading underscore means "internal". Those signals only work if everyone
follows them, which is why teams adopt automatic formatters and stop arguing.

**Comments: the rule this repository follows and you should steal.** Comments
explain **why**, not **what**. The code already says what. Compare:

```python
i += 1                                  # add one to i          ← worthless
fusion_k = max(top_k * 2, 30)           # deeper pool for robust reranking coverage
```

And the strongest form, seen throughout this codebase: a comment that records
the *defect* that motivated the line, so nobody removes it as unnecessary.

**With one warning from Chapter 03 that outranks all of this:** a comment
describing a control that does not exist is worse than no comment. Comments are
unverified claims. Keep them honest, or delete them.

---

# Part Q — Exercises

Start at the top even if it looks trivial. Answers in Part R.

### Level 0 — First lines

**Q1.** In the interactive shell, store the number 200 in a variable named
`chunks`, then print a sentence using an f-string that reads
`This document has 200 chunks`.

**Q2.** Store `4096` in `bytes_per_embedding` and `chunks` from Q1. Compute the
total bytes and print it. Then print the same number in kilobytes, using
division.

**Q3.** Write an `if` that prints `"large"` when `chunks` is over 100 and
`"small"` otherwise. Then change `chunks` to 50 and run it again.

### Level 1 — Collections and loops

**Q4.** Make a list of the seven workspace names. Print how many there are.
Print the third one. Print them one per line using a loop.

**Q5.** Given `scores = [0.9, 0.4, 0.7, 0.2]`, use a loop to build a new list
containing only the scores above 0.5. Then write the same thing as a list
comprehension.

**Q6.** Make a dictionary mapping each of three workspaces to a `top_k` number.
Print the value for `"legal"`. Then print every key and value using a loop.
Finally, ask for a workspace that is not in the dictionary using both `[ ]` and
`.get()`, and describe the difference in behaviour.

### Level 2 — Functions

**Q7.** Write a function `estimate_tokens(text)` that returns the number of
tokens, using four characters per token and whole numbers only. Test it with
`"hello world"`.

**Q8.** Write `pick_top(items, n=3)` that returns the first `n` items of a list.
Call it with and without `n`.

**Q9.** This function has a bug. Say what it is, why it happens, and fix it.

```python
def collect(item, seen=[]):
    seen.append(item)
    return seen
```

### Level 3 — Errors and structures

**Q10.** Write a function `to_uuid_or_default(value)` that tries to convert
text to a `uuid.UUID` and returns the string `"invalid"` if it cannot. Catch
only the errors that can actually occur.

**Q11.** Explain, in your own words, why this is dangerous and what two things
you would change:

```python
try:
    result = do_something()
except Exception:
    result = []
```

**Q12.** Given a list of dictionaries, each with a `"chunk_id"`, write code that
removes duplicates while keeping the original order. Say why you chose the data
structures you did.

### Level 4 — Real repository shapes

**Q13.** Write a simplified `resolve_workspace_id(value)`: if the value is
`None` or empty, use `"general"`; strip whitespace; if nothing remains, raise
`ValueError`; otherwise return `uuid.uuid5(uuid.NAMESPACE_DNS, value.lower())`.
Test it with `"Legal"`, `"  "`, and `None`.

**Q14.** Write a simplified token-budget loop. Given a list of dictionaries with
`"text"`, and a budget of 100 tokens (four characters each), build a list of the
pieces that fit, stopping at the first one that would exceed the budget. Print a
warning when you stop.

**Q15.** Write a `timed` decorator from scratch, apply it to a function that
sleeps for half a second, and confirm the decorated function's `__name__` is
still correct. Explain what `functools.wraps` changed.

---

# Part R — Answer Key

**R1.**
```python
chunks = 200
print(f"This document has {chunks} chunks")
```

**R2.**
```python
bytes_per_embedding = 4096
total = chunks * bytes_per_embedding
print(total)          # 819200
print(total / 1024)   # 800.0
```
Note `/` gives a float; `//` would give a whole number. Either is defensible —
say which you meant.

**R3.**
```python
if chunks > 100:
    print("large")
else:
    print("small")
```

**R4.**
```python
workspaces = ["general", "hr", "legal", "finance", "research", "study", "exam"]
print(len(workspaces))     # 7
print(workspaces[2])       # "legal" — index 2 is the THIRD item
for w in workspaces:
    print(w)
```
The point of the third line is zero-based indexing (E.1).

**R5.**
```python
good = []
for s in scores:
    if s > 0.5:
        good.append(s)

good = [s for s in scores if s > 0.5]
```

**R6.**
```python
config = {"legal": 10, "hr": 18, "finance": 14}
print(config["legal"])          # 10
for name, top_k in config.items():
    print(name, top_k)

config["exam"]                  # raises KeyError — the program stops
config.get("exam")              # None — the program continues
```
`[ ]` treats a missing key as a bug and fails immediately with a traceback that
names the key. `.get()` treats absence as expected. Choose based on which it
actually is; defaulting to `.get()` everywhere hides real bugs.

**R7.**
```python
def estimate_tokens(text):
    return len(text) // 4

estimate_tokens("hello world")     # 2
```
Floor division because tokens are whole.

**R8.**
```python
def pick_top(items, n=3):
    return items[:n]
```
A slice beyond the end is safe — it returns as many as exist, without error.

**R9.** The default `[]` is created once, when the function is defined, so every
call without `seen` shares one list and it grows across calls. This follows
directly from B.2: the default is an object and the parameter is a tag on it.

```python
def collect(item, seen=None):
    if seen is None:
        seen = []
    seen.append(item)
    return seen
```

**R10.**
```python
import uuid

def to_uuid_or_default(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return "invalid"
```
Naming the specific errors means a genuinely unexpected failure — say, a memory
error — still propagates instead of being disguised as bad input.

**R11.** Two problems.

First, `except Exception` catches everything, including errors that indicate a
missing dependency, a programming mistake, or a typo in a name. All of them
become "empty result", which is exactly the `redis_client.py` failure: a
missing library was indistinguishable from a legitimate empty answer, with no
log line anywhere.

Second, `[]` almost certainly already means something — "there were none". Now
it also means "we failed", so no code downstream can tell them apart. That is
the `document_ids` defect and the chat-documents defect, both from Chapter 03.

The two changes: catch the specific exceptions that can genuinely occur, and if
a broad catch is truly required on a request path, log at ERROR with
`type(exc).__name__` and return a value that cannot be mistaken for a valid
result — or re-raise.

**R12.**
```python
seen_ids = set()
unique = []
for c in candidates:
    if c["chunk_id"] not in seen_ids:
        seen_ids.add(c["chunk_id"])
        unique.append(c)
```
A **set** for the membership test, because `in` on a set does not get slower as
it grows, while `in` on a list scans everything and turns this loop into work
proportional to the square of the input. A **list** for the output, because
order is meaningful — these are ranked results — and sets have no order. This
is the exact pairing used in `grounding_service.py`.

**R13.**
```python
import uuid

def resolve_workspace_id(value):
    if value is None or value == "":
        value = "general"
    candidate = str(value).strip()
    if not candidate:
        raise ValueError("Invalid workspace identifier")
    return uuid.uuid5(uuid.NAMESPACE_DNS, candidate.lower())
```
`"Legal"` and `"legal"` produce the same UUID because of `.lower()` — which is
what makes the identity stable regardless of how a caller capitalises it.
`"  "` raises, because after stripping there is nothing left. `None` becomes
`"general"`.

**R14.**
```python
pieces = [{"text": "a" * 200}, {"text": "b" * 300}, {"text": "c" * 100}]
budget = 100
used = 0
accepted = []

for p in pieces:
    cost = len(p["text"]) // 4
    if used + cost > budget:
        print(f"Token budget exceeded ({budget}). Stopping.")
        break
    used += cost
    accepted.append(p)

print(len(accepted), used)
```
The first piece costs 50 and fits (50 used). The second costs 75, which would
reach 125, so the loop stops — and it does *not* skip ahead to the third piece,
because the list is ordered by importance and everything after the first
overflow is less important. Skipping instead of breaking would silently prefer
a small unimportant chunk over a large important one.

**R15.**
```python
import time
import functools

def timed(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time() - start:.3f}s")
        return result
    return wrapper

@timed
def slow():
    time.sleep(0.5)

slow()
print(slow.__name__)      # "slow"
```
Without `functools.wraps`, `slow.__name__` would be `"wrapper"`, and the
docstring would be lost. That matters because tracebacks, logs, API
documentation generators and test reports all read those attributes — so a
missing `wraps` turns every decorated function into an anonymous `wrapper` in
your error reports.

---

# Part S — Senior Critique: The Python in This Repository

### Strengths

1. **Docstrings carry reasoning, not restatement.** `tenant_scope.py`,
   `redis_client.py` and `document_access.py` each open with why the module
   exists and what it does not cover. That is unusually good.
2. **Exceptions are used to fail loudly**, and where a broad catch is
   unavoidable it is annotated (`# noqa: BLE001`) and logged with the exception
   type.
3. **Data structures are chosen deliberately** — a set for membership and a
   list for order; a lookup table instead of a chain of conditions.
4. **Types are used where they do work**: Pydantic at trust boundaries,
   plain hints elsewhere, enums for fixed state sets.
5. **Required parameters encode security decisions.** Making `owner_id`
   positional with no default means forgetting it is a `TypeError`, not a data
   leak.

### Weaknesses

1. **Mixed typing generations.** Some files use `Optional[str]` and `List[x]`,
   others `str | None` and `list[x]`. Both work; the inconsistency costs a beat
   of reading in every file. One convention plus a linter rule would settle it.
2. **`Dict[str, Any]` is common**, and `Any` switches type checking off. Several
   of those payloads have a knowable shape and would be better as small typed
   models — the trust-report adapter in `query.py` is the clearest candidate.
3. **Some functions are long.** `retrieve_chunks` does embedding, two query
   constructions, execution, fusion and formatting in one body. It is readable
   because it is a linear pipeline, but each stage would be independently
   testable if split — and Chapter 03's argument for stage isolation applies to
   functions as much as to systems.
4. **`global` appears in more than one module.** Each use is argued for, which
   is the right standard, but a small module-level state object would make the
   shared state visible rather than scattered.
5. **No enforced formatter or type checker in CI.** The conventions are
   followed by discipline. A formatter and a `mypy` run would convert that
   discipline into a mechanism — which is exactly the transformation this
   project applies everywhere else.

### The one improvement I would make first

**Add a type checker to CI, even in a permissive mode.** It converts the
existing type hints from documentation into verification, and it is the single
cheapest way to catch the class of bug where a function's declared shape and
its real behaviour have drifted apart.

---

# Part T — Interview Questions With Model Answers

**T1. "What is the difference between a list and a tuple, and when would you
choose each?"**

> A list is mutable and a tuple is not. That drives three practical
> differences: a tuple signals "this group is a fixed unit", it cannot be
> modified by a function you pass it to, and because it is immutable it can be
> used as a dictionary key.
>
> I use a list for a collection that grows or is reordered — retrieval results,
> accepted evidence — and a tuple for returning several related values at once.
> In our codebase `get_owned_document_text` returns
> `tuple[str, list[dict[str, Any]]]`: the full text and the chunks, which
> belong together and are always exactly two things.

**T2. "Why is `except Exception: pass` dangerous?"**

> Because it makes every possible failure look identical, including failures
> that are not runtime conditions at all. We had a real case: six call sites
> imported a Redis library inside a broad try/except and returned `None` on
> failure. The library was not installed, so every call raised
> `ModuleNotFoundError` and was swallowed with no log line.
>
> That silently disabled an advertised abuse control, made the retrieval cache
> a no-op while the code still looked like it had a cache, and turned two rate
> limits into no-ops. The mechanism is what matters: a missing dependency became
> indistinguishable from a cache miss.
>
> So I catch the narrowest exception that can actually occur; if I genuinely
> need a broad catch on a request path, I log at ERROR with the exception type
> and never return a value that already means something else.

**T3. "Explain mutable default arguments."**

> A default value is created once, when the function is defined, not on each
> call. So `def f(x, acc=[])` shares one list across every call that omits
> `acc`, and it accumulates forever.
>
> It follows from Python's assignment model: a variable is a name bound to an
> object, not a box holding a copy. The fix is `acc=None` and creating the list
> inside — and note the check must be `if acc is None`, not `if not acc`,
> because an empty list the caller genuinely passed should be respected rather
> than replaced.

**T4. "Why do type hints matter if Python ignores them?"**

> The interpreter ignores them; the ecosystem does not. A separate checker finds
> mismatches without running the code, editors use them for completion, and
> they are documentation that a tool can verify — so unlike a comment, they
> cannot drift silently.
>
> And some libraries make them enforce. Our request models are Pydantic
> classes: `query: str` with no default means a request missing it is rejected
> before any of our code runs, and `workspace_id: Optional[UUID]` rejects text
> that is not a valid UUID. That is a single validation choke point at the trust
> boundary rather than defensive checks scattered through the handlers.

**T5. "What is a decorator and where have you used one?"**

> A decorator is a function that takes a function and returns a replacement
> with added behaviour. `@d` above a definition is just
> `f = d(f)` written more readably.
>
> In our codebase almost every decorator is either registration or a
> cross-cutting concern: `@router.post` tells FastAPI which path a function
> handles, `@celery_app.task` makes a function sendable to a worker, and
> `@event.listens_for(Session, "do_orm_execute")` attaches our tenant filter to
> every database read. That last one is the interesting one — the decorator is
> what lets a security rule apply to every query without any query asking for
> it, which is the choke point the design depends on.

---

# Part U — Validation Checklist

- [ ] I can explain why "a variable is a box" is the wrong model, and show a
      two-line example where it misleads. *(B.2)*
- [ ] I can explain the difference between `None`, `[]`, `0` and `""`, and why
      truthiness merging them caused a real security defect. *(D.2)*
- [ ] I can read the token-budget loop in `grounding_service.py` line by line.
      *(E.2)*
- [ ] I can explain why a set is used for the duplicate check and a list for
      the output. *(G.4)*
- [ ] I can explain what happens the first time a module is imported, and why
      that mattered for the Celery fork bug. *(H.3)*
- [ ] I can state the three rules for exception handling and the failure that
      produced them. *(I.4)*
- [ ] I can explain what `@staticmethod`, `@property` and `@contextmanager` do.
      *(J.3, J.7, M.4)*
- [ ] I can explain the difference between a type hint and a Pydantic model.
      *(K.3)*
- [ ] I can write a decorator from scratch, including `functools.wraps`, and say
      what it fixes. *(M.2, Q15)*
- [ ] I completed Q9, Q11 and Q12 without looking at the answers.
- [ ] **The real test:** I can open `backend/app/core/workspace.py`,
      `backend/app/core/redis_client.py` or `backend/app/core/document_access.py`
      and explain every line — what it does, why it is written that way, and
      what would break without it.

If the last box is ticked, you can read most of `backend/app/` — and you are
ready for Chapter 07, which explains the one thing in those files we have
deliberately left unexplained: `async` and `await`.

---

*Next: [07-async-python.md](07-async-python.md) — the event loop, coroutines,
what `await` actually does, concurrency versus parallelism, blocking code, and
why one wrongly-placed loop froze this entire server for every user.*
