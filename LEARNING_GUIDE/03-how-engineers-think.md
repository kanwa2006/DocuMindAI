# 03 — How an Experienced Engineer Thinks

**Prerequisites:** Chapters 01 and 02. Nothing else is assumed. Every term
introduced here is defined before it is used and added to
[GLOSSARY.md](GLOSSARY.md).

---

## 3.0 What this chapter is for

Chapters 01 and 02 taught you *what* exists and *how to design a system*.
This chapter teaches something harder to write down: **the reasoning that
happens before any code is written.**

Two engineers can produce identical working code and be very different
engineers. The difference is not the code. It is:

- what they **noticed** before starting,
- what risks they **predicted**,
- what questions they **asked**,
- what they **measured** afterwards,
- which promises they decided must **never** break,
- and which costs they **knowingly accepted**.

This chapter makes that invisible process visible. It uses three real
features from this repository, and — crucially — the real bugs that each one
had. Bugs are the best teaching material in existence, because a bug is proof
that somebody's reasoning was incomplete, and the fix tells you exactly which
part was missing.

**A warning about the word "senior".** In this chapter, "beginner",
"intermediate", "senior" and "staff" are *ways of thinking*, not job titles
or years of experience. A person with eight years of experience can think
like a beginner about a subject they have never met. You will think like a
beginner about Kubernetes and like a senior about something else. The levels
are about the size of the question you are able to ask.

---

# Part A — The Four Levels of Thinking

Before the features, we need a shared vocabulary for the levels themselves.

## A.1 What the levels actually mean

**Beginner thinking** asks: *"How do I make this work?"*
The goal is a working happy path. Success is the feature doing the thing once,
in the way it was demonstrated.

**Intermediate thinking** asks: *"How do I make this work well?"*
The goal is clean, correct code: handled errors, tests, no obvious
duplication. Success is code a reviewer will approve.

**Senior thinking** asks: *"What breaks, who else is affected, and how will
we know?"*
The goal is a change that survives contact with reality — other users, other
subsystems, other engineers, failure, and time. Success is that the feature
keeps working six months later while ten unrelated things change around it.

**Staff thinking** asks: *"Is this the right problem, at the right layer, and
what class of problem does this belong to?"*
The goal is that this *kind* of bug becomes structurally impossible, that
future engineers cannot reintroduce it, and that the system's rules stay
few and consistent. Success is measured in things that never happen again.

## A.2 Why these levels exist — a short history

This progression is not invented for this course. It appears repeatedly in
software engineering literature under different names, because the same
sequence of realisations keeps happening to people.

In the 1970s, as programs first grew past what one person could hold in mind,
David Parnas published the idea of **information hiding**: a module should
hide the decisions most likely to change. That is the first appearance of
senior thinking as a discipline — *think about what will change, not only
about what works today*.

In the 1990s, as teams grew, the industry added **code review** and
**refactoring** — intermediate thinking, formalised.

From the 2000s onward, as systems became distributed and always-on, the focus
moved to **failure modes**, **observability**, and **invariants** — senior
and staff thinking, formalised.

The reason the levels feel like a ladder is that each one is only *useful*
after the one below is reliable. Worrying about the class of bug when your
code does not run yet is procrastination. Worrying only about whether it runs
when it is serving other people's private documents is negligence.

## A.3 The four levels, side by side

| | Beginner | Intermediate | Senior | Staff |
|---|---|---|---|---|
| **Core question** | Does it work? | Is it clean? | What breaks, and how do we know? | Is this the right layer, and is the class closed? |
| **Notices** | The happy path | Errors, duplication, tests | Other callers, other users, failure modes, time | Where the decision belongs; the family the bug is in |
| **Predicts** | Nothing yet | Obvious errors | Concurrency, partial failure, migration, drift | The next similar bug, in a different module |
| **Measures** | "It worked when I tried it" | Test suite green | Behaviour under load, concurrency, and failure | Whether the guard actually fails when the defect returns |
| **Protects** | Nothing explicit | Code style | Contracts, data integrity, user trust | Invariants, and the number of rules the system has |
| **Accepts** | Unknown costs | Small duplication | Named, written-down tradeoffs | Local ugliness in exchange for a closed class |

Keep this table nearby. We will fill each row with concrete evidence three
times.

---

# Part B — The Thinking Tools

These are the reusable reasoning primitives. They are *not* specific to this
project; they are the tools you carry to any project. Each is defined,
explained, and connected to real repository evidence — and each is a term you
should be able to use correctly in an interview.

## B.1 The choke point

**What it is.** A **choke point** is one place in the code that every path
must pass through to do a certain thing. If all document retrieval goes
through one function, that function is the choke point for retrieval.

**Why it exists.** Because a rule enforced in one place is enforced; a rule
enforced in ninety places is enforced ninety times minus the ones somebody
forgot. Human attention is the unreliable component.

**The problem it solves.** Duplicated decisions. When one decision — "which
rows may this user see" — is written at ninety call sites, the decision is not
really made anywhere. It is re-made, badly, ninety times.

**How beginners think.** "I will add the filter where I need it." This is
locally correct and globally fatal.

**Why that fails.** Not because the ninety are wrong today, but because the
ninety-first is written next month by someone who did not read the other
ninety.

**How experienced engineers think.** "Where does this decision *belong*? Can
I make the wrong version impossible to write?"

**Repository evidence.** From the commit that fixed the retrieval tenancy
hole (`8fd0f22`), in the author's own words:

> *"Fixed at the layer that owns the decision. 'Which documents may this
> query see' belongs to the retrieval service, not to its ~90 callers, so
> `owner_id` is now a REQUIRED positional parameter with no default: a caller
> that forgets it raises TypeError instead of quietly retrieving
> cross-tenant."*

Read the mechanism: the fix is not "we added a filter". The fix is "we made
the unsafe call *fail to run*". That is choke-point thinking.

**How to verify you have one.** Try to write the unsafe version. If you can
write it and it runs, you do not have a choke point — you have a convention.

**Generalising it.** Any project, any language: payment amounts, permission
checks, currency conversion, timezone handling, HTML escaping. Every one of
these is a decision that must have exactly one home.

## B.2 Fail-closed and fail-open

**What it is.** When something is missing or uncertain, a system either
**fails closed** (refuses, denies, stops) or **fails open** (allows,
continues, guesses).

**Why it exists.** Because "I do not know" is a real state, and somebody must
decide what it means.

**The history.** The terms come from physical security and electrical
engineering: a fail-closed door locks when power is lost; a fail-open door
unlocks. Neither is universally right — a bank vault should fail closed, a
fire exit should fail open. **The correct choice depends entirely on what the
failure costs.**

**How beginners think.** They do not think about it at all, and the language's
default decides for them. In Python, `except Exception: pass` fails open. So
does `.get(key, [])`.

**Why that fails.** Because failing open in a security or correctness context
turns a small fault into a large one, silently.

**How experienced engineers think.** "What does 'missing' mean here, and
which direction is the cheap mistake?"

**Repository evidence — failing closed, deliberately.** The tenancy layer
raises rather than returning rows when no owner scope is set. The module's
own documentation states the reasoning:

> *"If no scope is active, a SELECT against a scoped model raises
> `TenantScopeMissing` rather than returning unfiltered rows. An unscoped
> query is a bug; the safe response is to fail loudly, not to serve every
> tenant's data."*

**Repository evidence — failing open, accidentally, and the repair.** In
`query.py`, loading a chat's documents was wrapped in a handler that logged a
warning and continued with an empty list. Commit `7c32a15` explains exactly
why that was a fail-open disaster:

> *"`[]` is not a neutral value here — it is MEANINGFUL. It means 'this chat
> has no documents' … So a transient database error silently converted a
> grounded question about the user's own contract into a general-knowledge
> answer, with nothing anywhere saying the documents had not been
> consulted."*

**The generalisable lesson, and it is one of the most valuable in this whole
course:** before you use a default value on an error path, ask *what that
value already means elsewhere in the system*. If `[]` already means something
specific, using it to mean "I failed" merges two different states into one,
and no code downstream can tell them apart.

## B.3 Instance versus class

**What it is.** An **instance** is one bug. A **class** is the family of bugs
that share a cause.

**Why it matters.** Fixing an instance removes today's symptom. Closing a
class removes tomorrow's.

**How beginners think.** "The bug was on line 54. I fixed line 54."

**Why that fails.** Because the same reasoning error usually produced lines
54, 118 and 302, written by the same person on the same day.

**How experienced engineers think.** "What *kind* of mistake was this, and
where else could it live? Can I find them mechanically instead of by
memory?"

**Repository evidence — and this is the strongest example in the repository.**
The tenancy work could have fixed four listed findings. Instead the engineer
wrote a test that walks every endpoint module, finds every filter on
`workspace_id`, and demands a matching `owner_id` filter in the same
function. From commit `24d55c0`:

> *"Writing it found EIGHT sites the register never listed, including two
> whole models — `BenchmarkRun` and `Correction` — that have no owner column
> at all and were disclosing every user's rows. The register documents four
> instances of this class; there are at least twelve. It was enumerating
> examples, not bounding the problem, and only a mechanical sweep could tell
> the difference."*

Three times as many bugs as anyone had listed. That is the difference between
instance thinking and class thinking, measured.

**And then the honesty that makes it staff-level.** The very next commit
(`a83658b`) records the limit of that same tool:

> *"Three ways to read another tenant's content that the class ratchet could
> NOT see, because none of them filters on `workspace_id` at all. That is the
> point worth recording: the ratchet bounds one shape, and these are a
> different shape in the same family."*

Knowing what your own guard cannot see is a higher skill than writing the
guard.

## B.4 The ratchet

**What it is.** A **ratchet** is a test with an allowlist of known-bad cases
that is only ever allowed to shrink. New violations fail the build; existing
ones are listed with a reason; and a second test fails if a listed entry
stops being a real violation, so the list cannot rot.

**Why it exists.** Because some problems cannot be fixed all at once —
eleven of the sites in this repository could not be closed at all, since the
model had no owner column and adding one required a data decision from the
owner. Blocking all progress until then is unrealistic; allowing silent new
violations is unacceptable. A ratchet is the engineering answer to "we are
not done, but we will not get worse."

**How beginners think.** "We will fix the rest later." Later never has a
mechanism.

**How experienced engineers think.** "How do I make 'later' enforceable?"

**A detail worth stealing.** From `24d55c0`:

> *"It is keyed by (module, function, model) rather than line number, so it
> survives unrelated edits — a line-numbered allowlist rots on the first
> insertion above it and then gets 'repaired', which is how allowlists
> quietly grow."*

That is a small, specific, hard-won piece of craft: **key your allowlists by
identity, never by position.** It applies to lint suppressions, snapshot
tests, and every other allowlist you will ever maintain.

## B.5 The guard that bites

**What it is.** A regression test whose failure has actually been *observed*
by deliberately reintroducing the bug.

**Why it exists.** Because a test that has never failed is not evidence. It
may be asserting something that is always true, or testing the wrong module,
or silently skipped.

**How beginners think.** "I wrote a test and it passed. Done."

**Why that fails.** A test that passes both before and after your fix tested
nothing about your fix.

**How experienced engineers think.** "Put the bug back. Did the test go red?
What exactly did it say?"

**Repository evidence.** Every fix commit in this repository records the red
observation, with the message the test printed. From `24d55c0`:

> *"Guard observed RED: removing the owner predicate from list_exports alone
> fails with 'export.py:131 list_exports() filters ExportJob.workspace_id
> with no ExportJob.owner_id'."*

From `4964ed6`:

> *"Observed RED on the reintroduced defect — 'only 0 heartbeats while
> consuming a stream that blocks 0.60s in total'. Zero, not merely fewer: the
> loop was completely starved, which is the defect stated as a number."*

Notice the second one states the defect **as a number**. Not "the server felt
slow" — zero heartbeats in 0.6 seconds.

## B.6 Measure the property, not the source

**What it is.** Testing the *behaviour you care about*, rather than testing
that a particular line of code is present.

**Why it exists.** Because the presence of a correct-looking call does not
prove correct behaviour.

**The clearest possible example, from this repository.** The event-loop
blocking bug (S1) existed *even though* `run_in_executor` was present in the
code. From commit `4964ed6`:

> *"Only the call that OBTAINS the stream was wrapped in `run_in_executor`;
> the iteration that performs the actual network I/O ran on the event loop
> thread… Wrapping only the constructor looks correct and is not, which is
> why this survived review."*

A test asserting "`run_in_executor` appears in this function" would have
passed on the broken code. So the guard was written to measure the property
instead — start a heartbeat coroutine, consume a stream that blocks, and
assert the heartbeat keeps ticking. As `e697dd1` puts it:

> *"It measures the property (the loop stays free) rather than asserting a
> `run_in_executor` call is present — a call can be present and still wrap
> the wrong thing, which is exactly what S1 turned out to be."*

**Generalise it:** test that the cache is faster, not that `cache.get` was
called. Test that the email arrives, not that `send()` was invoked. Test that
unauthorised users get nothing, not that `check_permission` appears.

## B.7 Observability of a defect

**What it is.** Whether a defect can be *seen* under your test conditions at
all. Some bugs are invisible not because the test is weak but because the
setup cannot express the difference.

**The repository's recurring example**, repeated in four separate commit
messages because it kept being the answer to "why did this escape?":

> *"with one seeded account, a filter that matches every row and a filter
> that matches the right row are indistinguishable by results — every test
> asserted on results."*

Think about how deep that is. With one tenant in the database, `WHERE
owner_id = me` and no filter at all **return exactly the same rows**. No
amount of careful result-checking can tell them apart. The bug is not
invisible because the tests were lazy; it is invisible because the *test
fixture* had one tenant.

Two different repairs follow from that insight, and both were used:
1. **Change the fixture** — seed two accounts, so the difference becomes
   observable. (Used for runtime verification: "Verified at runtime with TWO
   REAL ACCOUNTS".)
2. **Change the level of observation** — assert on the emitted SQL rather
   than on the returned rows, because an absent `WHERE` clause is visible
   there even with one tenant.

**The generalisable question to ask before writing any test:** *under my test
conditions, would the bug I am worried about produce a different result at
all?* If not, the test cannot help, no matter how many assertions it has.

## B.8 Positive and negative controls

**What it is.** Borrowed from laboratory science. A **negative control**
checks that the thing you expect to be blocked is blocked. A **positive
control** checks that the same operation *works* for someone who should be
allowed — proving your negative result was caused by the security check and
not by a broken URL.

**Why it exists.** Because "404 Not Found" proves nothing on its own. A
typo in the path produces the same 404 as a perfect permission check.

**Repository evidence.** From `24d55c0`:

> *"Verified at runtime with two accounts, negative AND positive control on
> the same document — a 404 alone proves nothing if the route is simply
> wrong, and an earlier run of this check did hit a nonexistent path and
> looked like a pass."*

That parenthetical is an engineer admitting their own earlier verification
was worthless, and fixing the method. This is the single most useful habit in
debugging: **always ask what else could produce the result I just saw.**

## B.9 Second-order consequences

**What it is.** The effects of your effects. First-order: "I changed uploads
to store the real workspace." Second-order: "every piece of code that *reads*
that field now sees a different value than before."

**Repository evidence — a textbook case.** Commit `31c7119` fixed the upload
write path so documents stored the workspace they were actually uploaded
into. Correct fix. Commit `a632b13` then had to repair the fallout, and its
message is the most honest sentence in the repository:

> *"H5 — a regression I introduced in 31c7119. That commit fixed the WRITE
> path so uploads store the real workspace; it did not check what READS it.
> Before it, every document was `general`, so the JWT claim always matched
> and the workspace predicate was invisible."*

Five endpoints started returning 404 for six of the seven workspaces —
including DELETE, so documents became **impossible to remove by anyone,
including their owner**.

**The rule extracted from it**, which now lives in the project's handbook:
*when you change how a value is written, enumerate its readers in the same
change.* That is why `CLAUDE.md`'s delegation matrix has a row that says
"Changing how a value is **written** anywhere → `code-reviewer` — question 3
enumerates its readers."

**A bug produced a rule.** That is how good engineering organisations
actually improve.

## B.10 Blast radius

**What it is.** How much of the system a change can damage if it is wrong.

**How to use it.** It decides how much verification a change deserves. A
change to a leaf component with one caller needs less scrutiny than a change
to a function called from ninety places.

**Repository evidence.** `CLAUDE.md` lists "Files Needing Extra Care" —
`llm_service.py`, `retrieval_service.py`, `grounding_service.py`,
`celery_app.py`, `core/config.py`, `core/auth.py`, `lib/api.ts`,
`WorkspaceUI.tsx` — and requires a minimal diff plus full regression for
each. The stream fix commit reports its own diff size as evidence of
restraint: *"Extra-care file: diff is 38 insertions, 1 deletion, confined to
the iteration."*

**Generalise it:** in any codebase, identify the five files where a mistake
hurts most, and treat changes to them differently. If you cannot name those
five files, you do not yet understand the codebase.

---

# Part C — Feature 1: The Grounding Pipeline

## C.1 The problem statement

> *A user asks a question in normal language. Their documents may be
> thousands of pages. The AI model can read only a few thousand tokens at
> once. Produce an answer that is based on their documents, that says which
> page each claim came from, and that refuses when the documents do not
> contain the answer.*

Read that again and notice how many separate promises are inside it:
relevance, size, attribution, and refusal. Each one is a different
engineering problem, and the levels differ mainly in **how many of the four
they see at the start**.

## C.2 How a beginner approaches it

The beginner sees one problem: get an answer out of the model.

Their reasoning is: the model is good at answering questions; the document is
text; therefore send the text and the question to the model. If the document
is too long, send the first part.

They will also ask the model to cite pages, because citations are required,
and the model will produce citations. They will look correct.

**What the beginner noticed:** that a model can answer questions.
**What they predicted:** nothing.
**What they measured:** "I tried it on my test PDF and the answer was right."
**What they protected:** nothing explicitly.
**What they accepted:** unknown costs, which is the definition of the level.

## C.3 Why that approach breaks

It breaks in five ways, and they arrive in this order:

1. **Size.** The second real document exceeds the context window. The request
   fails outright, or is silently truncated, which is worse.
2. **Cost.** Sending a whole document per question is enormously wasteful
   when the answer lives in two paragraphs.
3. **Accuracy.** Models attend worse to material buried in the middle of a
   very long input. More text is not more accuracy.
4. **Fabricated citations.** The model was asked to *produce* page numbers,
   so it produces plausible ones. Some are wrong. A wrong citation is worse
   than none, because it manufactures trust.
5. **No refusal.** Asked something the document does not cover, a model
   trained to be helpful answers from general knowledge — confidently, in the
   same voice, with no marker distinguishing it from a grounded answer.

Failure 5 is the one that should frighten you, because the output *looks
identical* to success. Every other failure announces itself.

## C.4 The intermediate approach

The intermediate engineer knows about **RAG** — retrieval-augmented
generation, taught in Chapter 01 — and implements it properly: split
documents into chunks, embed them, store the vectors, embed the question at
query time, find the nearest chunks, send only those to the model with an
instruction to answer only from them.

This is a genuinely good solution. It fixes size, cost, and much of accuracy.
It is what most tutorials teach and what most products ship.

**What the intermediate noticed:** that retrieval must precede generation.
**Predicted:** context overflow, cost.
**Measured:** the test suite passes; answers look good on their examples.
**Protected:** code cleanliness; no duplication.
**Accepted:** implicitly, everything they did not think about.

## C.5 Why the intermediate approach is still weak

Four weaknesses remain, and each one is a place where a senior engineer's
attention goes.

**Weakness 1 — vector search alone has a systematic blind spot.** Embeddings
capture meaning, and meaning is exactly what is missing from a clause number,
a surname, a part code, or an amount. Ask about "clause 14.2(b)" and vector
search returns paragraphs that are *about* similar topics while the actual
clause sits at position 40. The failure is not random; it is a *category* of
question that reliably fails. Category failures are much worse than random
ones, because a whole class of user gets a broken product every time.

**Weakness 2 — the retrieval score is not a relevance judgment.** Cosine
similarity between two independently computed vectors is a cheap
approximation. It was never asked "does this passage answer this question?"
It was asked "do these two texts point in similar directions?"

**Weakness 3 — "answer only from this context" is a request, not a
constraint.** The instruction is text in a prompt. It usually works. It is
not enforcement.

**Weakness 4 — nothing has been decided about failure.** What happens when
retrieval returns nothing? When the reranker fails to load? When the document
list cannot be read? The intermediate solution has no answer, so the language
supplies one, and the language always fails open.

## C.6 The senior engineer's reasoning process

A senior engineer does not begin by choosing a retrieval algorithm. They
begin by working out **what the product's promise is**, because the promise
determines which failures are unacceptable.

The promise here is: *the answer comes from your documents, you can check it,
and we tell you when we do not know.* From that, three properties follow, and
they are not negotiable:

- **Attribution must be verifiable**, so the citation cannot come from the
  same process that could be wrong.
- **Refusal must be possible**, so "I could not find it" must be a real
  output, not a fallback.
- **Failure must be visible**, so a degraded answer must never be
  indistinguishable from a good one.

Now, the questions a senior asks before writing code:

1. *Which questions will this fail on, and are they a category or a
   scattering?* — leads directly to hybrid search, because "exact tokens" is
   a category.
2. *When two ranked lists disagree, how do I combine them without inventing a
   number?* — leads to rank-based fusion, because the two scores are on
   incomparable scales.
3. *Where does the page number come from?* — leads to labelling evidence
   before generation, because a value the model *copies* is far safer than a
   value the model *produces*.
4. *What is the most expensive step, and does it run on every request?* —
   leads to retrieve-wide-then-rerank-narrow, and to knowing that the
   cross-encoder is the dominant CPU cost.
5. *What does "no evidence" produce?* — leads to designing refusal as a
   first-class path rather than an accident.
6. *Which of these steps can fail independently, and what should each failure
   produce?* — leads to a failure table.

**What the senior measures:** stage-by-stage timings, on every request, in
production, not in a benchmark. That is why the retrieval service returns a
`tracing` dictionary alongside the results, with embedding time, database
time, candidate counts and accepted-evidence counts. You cannot answer "why
was that slow?" or "why was that answer bad?" without per-stage numbers.

**What the senior protects:** the promise. Citations must be derived from
data; the token budget must never be exceeded; a failure must never be
convertible into a confident answer.

**What the senior accepts, knowingly:**
- two database queries per question instead of one;
- the largest CPU cost in the request path being the reranker;
- rank fusion discarding score magnitude;
- an approximate token estimate (`len(text) // 4`) rather than a real
  tokeniser, because the budget only needs to be roughly right and a real
  tokeniser costs time on every chunk.

Only now, after all of that reasoning, does code appear. This is what it
produced — evidence is labelled with its true source *before* the model sees
it, and the budget is enforced by the loop, not by the prompt
([`backend/app/services/grounding_service.py:117`](../backend/app/services/grounding_service.py)):

```python
        # 5. Token Budgeting & Grounded Context Formatting
        grounded_context = []
        current_token_estimate = 0
        accepted_evidence = []

        for candidate in selected_candidates:
            # Heuristic: ~4 characters per token
            chunk_tokens = len(candidate["text_content"]) // 4 
            if current_token_estimate + chunk_tokens > max_tokens:
                logger.warning(f"[Tracing] Token budget exceeded ({max_tokens}). Halting evidence injection.")
                break
                
            current_token_estimate += chunk_tokens
            accepted_evidence.append(candidate)
            
            # Citation formatting natively prepares the LLM to output grounded references
            context_block = (
                f"<evidence document=\"{candidate['filename']}\" "
                f"page=\"{candidate['page_number']}\" "
                f"chunk_id=\"{candidate['chunk_id']}\">\n"
                f"{candidate['text_content']}\n"
                f"</evidence>"
            )
            grounded_context.append(context_block)
```

Every line of that is a decision from the list above, made visible.

## C.7 The staff engineer's reasoning process

The staff engineer asks a different kind of question: *is this pipeline a
pipeline?* — meaning, is each stage independently inspectable, replaceable,
and attributable when something goes wrong?

That matters because of a property the senior may not have named: **a bad
answer is a debugging nightmare unless you can tell which stage produced
it.** Was the chunk never retrieved? Retrieved and reranked away? Reranked in
but dropped by the budget? Included but ignored by the model? These have
completely different fixes, and from the outside they all look like "the
answer was wrong".

So the staff engineer's contributions are structural:

1. **Stage isolation.** Retrieval, fusion, reranking, budgeting and
   generation are separate functions with separate outputs, so any two can be
   inspected between.
2. **Tracing as a first-class return value**, not a logging afterthought.
3. **A named owner for the question "which stage was it?"** — which in this
   repository is literally an agent definition, `rag-pipeline-tracer`, whose
   single question is *"which stage produced this bad answer?"* and which is
   explicitly forbidden from also deciding whether to optimise it. One
   question per role, no overlap.
4. **A rule that generalises beyond this feature.** "Extract with the model,
   compute with code" is not a RAG rule; it is a rule about every use of a
   language model anywhere in the system. Once stated, it applies to finance
   ratios, legal escalation levels, and anything invented next year.

**What the staff engineer predicted that the senior did not:** that the
*trust score* — a number computed to describe answer quality — could itself
become fiction. A metric that is always the same number cannot disagree with
any answer, so no amount of answer-level testing will ever catch it. This is
why the repository has a separate role, `integrity-auditor`, whose only
question is *"does this code do what it claims?"*, and why `CLAUDE.md`
carefully separates it from the pipeline tracer:

> *"`rag-pipeline-tracer` explains why **one answer** was wrong;
> `integrity-auditor` establishes that a number was **never real for any
> answer**. A metric that is always identical cannot 'disagree with the
> answer,' so the tracer's trigger can never fire on it."*

That distinction is staff-level thinking in one paragraph: it identifies a
class of defect that *no existing role could ever detect*, and fixes the
roster rather than the code.

## C.8 The failure that proves the point

All of the above is theory until something breaks. Here is what broke.

Loading a chat's attached documents was wrapped in a broad handler that
logged a warning and carried on with an empty list. The reasoning was
reasonable at intermediate level: *do not let a history-loading problem
destroy the user's question.*

The consequence was the exact failure mode the promise forbids. From
`7c32a15`:

> *"a transient database error silently converted a grounded question about
> the user's own contract into a general-knowledge answer, with nothing
> anywhere saying the documents had not been consulted. The user gets a
> confident answer to a question the system never actually looked at — which
> is worse than no answer, because it is indistinguishable from a real one."*

And then the sentence that shows why even a careful reviewer missed it:

> *"Why it escaped: the degraded path returns a complete, well-formed,
> confident answer. `mode: "general"` is even reported honestly in the
> metadata — but that field means 'this chat has no documents', not 'we
> failed to find out', so the one signal that existed was itself ambiguous."*

**The lesson to carry away, stated generally:** a status field that conflates
"nothing was there" with "we could not check" is not a signal. It is noise
wearing a signal's clothes. When you design a status enum, make sure every
state means exactly one thing.

The repair fails closed: log at ERROR with the session id, emit an `error`
event, and return **before** the model is called — because the whole point is
that the answer would not have been grounded. And it was verified by
injecting a real fault (a malformed session id), observing that the response
contained `trial_status`, `thinking_stage`, `error` and **no** `token` events
at all.

## C.9 How four companies would build this differently

The point of this section is not trivia about big companies. It is that
**the same feature has different correct answers depending on what the
organisation is optimising for**, and being able to say why is a senior
skill.

### A startup (5–20 people, pre-product-market-fit)

**What they optimise:** learning speed. Every week spent building is a week
not spent finding out whether anyone wants this.

**What they would build:** a hosted vector database, a hosted embedding API,
a single vector search, no reranker, no hybrid search. Perhaps a hundred
lines total. Citations from the prompt, accepted as imperfect.

**What they sacrifice:** the exact-token question category fails; costs are
higher per query; citations are sometimes wrong; there is no path to
inspecting why an answer was bad.

**Why that can be the right call:** if the product is wrong, the perfect
pipeline was wasted. And if it is right, they will have money and people to
rebuild it. The failure mode is real but recoverable *if* they know they took
the loan. A startup that does not know it took on this debt will be surprised
when accuracy complaints arrive and nobody can explain any individual answer.

**When a startup should choose differently:** when wrong answers are
dangerous rather than annoying — medical, legal, or financial advice. Then
refusal and attribution are the product, not a refinement, and must exist on
day one.

### Google

**What they optimise:** quality at very large scale, measured. Google's
institutional strength is information retrieval and evaluation
infrastructure.

**What they would build:** a serving stack with the retrieval index as a
separate service, a learned ranking model rather than a fixed fusion formula,
and — the real difference — **an evaluation harness before the feature**. A
labelled query set, offline metrics, online experiments comparing variants on
live traffic.

**What they sacrifice:** speed of delivery. Building the measurement
apparatus can take longer than building the feature.

**Why:** at their scale a 1% relevance improvement is enormous value, and a
1% regression is enormous damage, so anything unmeasured is unacceptable.
They can afford the apparatus because it is amortised over many products.

**What this project borrowed anyway:** the per-stage tracing, and an
evaluation service with an admin page. The instinct is right even at small
scale — but note the honest difference: RRF's constant of 60 here is taken
from the literature, not tuned on labelled data, because there is no labelled
data. Saying that out loud in an interview is far stronger than pretending
otherwise.

### Amazon

**What they optimise:** operational ownership and cost per unit. Amazon's
culture puts the team that builds a service on call for it, and asks
relentlessly what each request costs.

**What they would build:** the pipeline as separately deployable services
with explicit contracts, each with its own dashboards, alarms, and an owning
team. Cost per query would be an actual tracked metric with a target. There
would be a written document arguing the design *before* the code — Amazon's
famous six-page narrative — and a section on what happens when each
dependency fails.

**What they sacrifice:** simplicity and speed. Several services mean network
hops, versioning between them, and distributed debugging.

**Why:** when you own the pager, "what happens when the reranker is down" is
not a philosophical question. It is the difference between a good night's
sleep and a 3 a.m. call.

**What this project borrowed:** the failure table in Chapter 02, and the
rule that every degraded path must be loud. What it does not have is
alerting — which is exactly the gap named in Chapter 02's critique.

### Microsoft

**What they optimise:** compatibility, enterprise requirements, and the long
tail of customers who cannot be broken.

**What they would build:** the same pipeline with pluggable providers
(customer brings their own model, their own vector store, their own identity
system), a strong compliance story (data residency, audit logs, retention
policies), and a version policy that keeps old behaviour working for years.

**What they sacrifice:** the ability to change quickly. Every abstraction
that allows a customer to swap a component is a constraint on future
refactoring.

**Why:** their customers are organisations with procurement rules, auditors,
and a legal requirement to know where data lives. A brilliant pipeline that
cannot answer "where is my data stored?" is unsellable to them.

**What this project borrowed:** the storage interface with two
implementations, and the `VECTOR_BACKEND` seam. Both are small versions of
the same idea — and note that in Chapter 02 those were justified by
*developer convenience*, not by enterprise sales. Same mechanism, different
motivation. That is worth noticing: **the same design can be justified by
very different business reasons, and the reason determines how far you take
it.**

---

# Part D — Feature 2: The Tenancy Model

This is the most instructive feature in the repository, because it went wrong
repeatedly, in several different shapes, and each repair was documented.

## D.1 The problem statement

> *Many separate users store private documents in one running system. No user
> may ever read, modify, delete or export another user's content — through
> any endpoint, any background job, any cache, any export, or any share
> link.*

Note the last clause. It is where the real danger lives.

## D.2 How a beginner approaches it

The beginner adds a filter where they need one:

*"When listing documents, only show the ones belonging to this user."*

They write `WHERE user_id = current_user`. It works. They move on.

**Noticed:** that data must be filtered.
**Predicted:** nothing.
**Measured:** logged in as themselves; saw their own documents.
**Protected:** nothing.

## D.3 Why that breaks

Four reasons, each of which happened here.

**Reason 1 — coverage.** There is not one query. There are ninety. Every new
endpoint is a new opportunity to forget, forever.

**Reason 2 — the wrong column looks right.** This system has two identifier
columns on many tables: `workspace_id` and `owner_id`. One of them looks
exactly like a tenant key and is not. `workspace_id` is
`uuid5(NAMESPACE_DNS, "legal")` — the same value for every user on Earth.
Filtering by it feels like isolation and provides none.

**Reason 3 — the test cannot see the bug.** With one test account, filtering
correctly and not filtering at all return the same rows.

**Reason 4 — reachability, not just listing.** Even if listing is filtered,
can a user reach a resource by guessing or obtaining an id? This is where the
worst finding lived.

The consequences, in the repository's own words. From `0df7df9`:

> *"`GET /chats` listed every user's sessions. With an id from that list an
> attacker could read the transcript, append messages, rename, re-tag and pin
> another user's conversation — and `POST /chats/{id}/share` minted a PUBLIC
> link to it, afterwards readable with no authentication at all via
> `GET /shared/{token}`. That last one converts a tenancy bug into an
> unauthenticated disclosure."*

Sit with that chain: a wrong `WHERE` clause becomes a public URL that leaks a
stranger's private conversation to anyone on the internet. **The severity of
a tenancy bug is determined by what the system can do with the resource, not
by the bug itself.**

## D.4 The intermediate approach

The intermediate engineer recognises the coverage problem and responds with
discipline: a code review checklist, a shared helper function, a rule in the
contributing guide, and tests for the important endpoints.

This is a real improvement. It is also insufficient, and the repository
proves why in a single sentence from `0df7df9`:

> *"Only `delete_chat_session` checked `owner_id`, and its comment described
> that as a 'belt-and-suspenders ownership check'. Treating the tenant key as
> redundant belt-and-suspenders, rather than as THE key, is the inversion
> that produced all nine."*

Read what happened there. A previous engineer *did* write the correct check —
and described it in a comment as extra, optional reinforcement. The next nine
routes, written by someone reading that comment, reasonably concluded the
check was not the real control. **A comment that misdescribes a control is
not a neutral mistake; it actively teaches the next reader the wrong model.**

The same pattern appears again in an even purer form, from `a83658b`:

> *"`/finance/ratios` had `# Verify document ownership` written directly
> above `select(Document).where(Document.id == doc_id)` — no ownership
> predicate at all. A comment describing a control that does not exist is
> worse than no comment, because it stops the next reader looking."*

And a third time, with a docstring instead of a comment, from `8fd0f22`:

> *"`tenant_guard.validate_retrieval_scope` documented itself as a 'Hard
> blocking guard called before EVERY retrieval operation… CRITICAL: Never
> remove or bypass this call' and had zero call sites. A control that lies is
> worse than an absent one: it stops an auditor looking further, which is
> plausibly part of why H1 survived this long."*

Three separate instances of the same phenomenon. That is not bad luck; that
is a **class**. And naming the class is what produced a permanent role in
this project whose only question is *"does this code do what it claims?"*

## D.5 The senior engineer's reasoning

The senior asks the question the intermediate did not: *what layer owns this
decision?*

Their reasoning runs:

- "Which rows may this user see" is a property of **the session**, not of any
  individual query. A query should not have the authority to answer it.
- Therefore the enforcement belongs where the session lives — the database
  session layer — not at the call sites.
- Therefore a new endpoint should be *unable* to get this wrong, because it
  never writes the filter at all.

Then the questions before writing code:

1. *What happens if the scope is not set?* → Must fail closed. An unscoped
   query is a programming error, and serving every tenant's data is the worst
   possible response to a programming error.
2. *What legitimately needs to see across tenants?* → Migrations, cleanup
   jobs, admin tools. Those need an explicit, greppable, auditable bypass —
   something you have to *type*, never a default.
3. *What does this NOT cover?* → Raw SQL bypasses the ORM entirely. Writes
   are not reads. Both limits must be written down, because an
   overestimated control is more dangerous than a known gap.
4. *How do the background workers get a scope?* → They have no request to
   inherit from, so they must establish it from the task arguments.
5. *How do I prove it works?* → Two real accounts, negative and positive
   controls.

**What the senior measures:** actual cross-account HTTP requests against a
running system, with both the blocked case and the allowed case. Not unit
tests alone — those share the fixture that made the bug invisible.

**What the senior protects:** the invariant that the tenant key is
`owner_id`, and that no code path can read tenant data without a scope.

**What the senior accepts, knowingly:** an ORM-level hook has real costs. It
is invisible magic — a query behaves differently than its source suggests,
which is confusing to newcomers. It does not cover raw SQL. It adds a
per-query check. Those are accepted because the alternative failed, twelve
times, provably.

Only now does code appear. Two mechanisms: a context variable holding the
current owner, and a hook that injects the filter into every ORM select
([`backend/app/core/tenant_scope.py:118`](../backend/app/core/tenant_scope.py)):

```python
@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_scope(orm_execute_state) -> None:
    """Inject `owner_id = <current owner>` into every SELECT on a scoped model.

    `with_loader_criteria(..., include_aliases=True)` also covers eager loads
    and joined relationships, so a scoped row cannot be reached indirectly via
    a relationship from an unscoped one.
    """
    if not orm_execute_state.is_select:
        return
    ...
    raw = _current_owner.get()
    if raw is _SYSTEM:
        return
    if raw is None:
        raise TenantScopeMissing(
            "Query against a tenant-scoped table with no owner scope. Wrap the "
            "request path in tenant_scope(user_id), or system_scope() if this "
            "is trusted internal work."
        )

    orm_execute_state.statement = orm_execute_state.statement.options(
        with_loader_criteria(
            TenantScoped,
            lambda cls: cls.owner_id == raw,
            include_aliases=True,
        )
    )
```

Three details in that code are senior decisions you should be able to explain:

- `include_aliases=True` — because a scoped row could otherwise be reached
  *indirectly*, through a relationship loaded from an unscoped row. Thinking
  about the indirect path is the difference between a filter and a control.
- `raise TenantScopeMissing` when the scope is `None` — fail closed.
- `if raw is _SYSTEM: return` — the bypass exists, is explicit, and is
  greppable. Compare with a bypass implemented as "pass `None` to skip
  filtering", which would be indistinguishable from forgetting.

## D.6 The staff engineer's reasoning

The staff engineer accepts all of the above and then asks three questions the
senior did not.

**Question 1: how many rules does the system now have?**

Adding a mechanism adds a rule engineers must know. Every rule has a cost, and
the total number of rules is a real budget. So the mechanism must *remove*
more rules than it adds. Here it does: the old rule was "remember the owner
filter in every query" (impossible to satisfy); the new rule is "inherit the
mixin" (one line, checked by the type system and by the database's `NOT
NULL`). Net rules: fewer, and the remaining one is mechanically enforced.

**Question 2: what shape of this bug does my mechanism NOT catch?**

This is the question that separates staff from senior. The class ratchet
catches "filters on `workspace_id` without `owner_id`". It cannot catch code
that filters on *neither* — a helper that takes a document id from the
request and reads its text with no ownership check anywhere in the chain.
Which is exactly what was found next, in `a83658b`: two private
`_get_document_text` helpers, one in `legal.py` and one in `finance.py`,
selecting chunks by `document_id` alone. `/legal/contracts/compare` took two
caller-supplied ids and fed both to it.

The staff response was not another ad-hoc patch. It was consolidation: one
module, `core/document_access.py`, holding `get_owned_document` and
`get_owned_document_text`, so there is **one definition of "may this caller
read this document" for the whole codebase**. Every helper routes through it.

**Question 3: what does the error message leak?**

A small detail with a large name. From `24d55c0`:

> *"It returns 404 and not 403 deliberately — 403 would confirm the id exists
> and belongs to somebody, which is an enumeration oracle."*

An **enumeration oracle** is any response difference that lets an attacker
learn which identifiers exist. "403 Forbidden" says *this exists and is not
yours*; "404 Not Found" says nothing. With 403, an attacker can scan ids and
build a map of your system's contents without ever reading one. Choosing the
status code is a security decision, not a formatting decision.

**What the staff engineer predicted that the senior did not:** that the
register of known bugs was *incomplete and could not be trusted as a
boundary*. A senior fixes the four listed findings. A staff engineer writes
the mechanical sweep and discovers twelve — then writes down that the register
"was enumerating examples, not bounding the problem", so nobody treats a list
of examples as a measure of exposure again.

## D.7 What each level would have measured

| Level | Verification they would have done | Would it have caught the bug? |
|---|---|---|
| Beginner | Logged in, saw own documents | No |
| Intermediate | Unit tests asserting the endpoint returns the right rows, one seeded account | **No** — with one tenant, filtered and unfiltered results are identical |
| Senior | Two real accounts over HTTP, negative and positive controls, on every affected route | Yes |
| Staff | The above, plus a mechanical source-level sweep of the whole codebase for the pattern, plus a ratchet that only shrinks | Yes, **and** the eight nobody knew about |

That table is the single most important thing in this chapter. Copy it into
your notes.

## D.8 How four companies would build tenancy differently

### A startup

**Optimises:** shipping. Would use a framework or platform that provides
tenancy — for instance Supabase or Firebase with row-level security policies
attached to the authenticated user — so isolation is the platform's job.

**Sacrifices:** control and portability. The policies live in the platform's
configuration rather than in the codebase, so they can drift from the code
and are harder to review in a pull request. Migrating off the platform later
means reimplementing tenancy from scratch.

**Why it can be right:** tenancy is a solved problem that startups reliably
get wrong. Delegating it to a platform is often a better risk trade than
writing your own — *provided* someone verifies the policies with two accounts,
which is the step teams skip.

### Google

**Optimises:** correctness at scale, and defence in depth. Isolation would be
enforced at multiple independent layers — in the storage layer, in the
serving layer, and by automated analysis that proves data flows cannot cross
tenant boundaries. Their culture would additionally demand a *design review
document* signed off before implementation.

**Sacrifices:** velocity, and a great deal of infrastructure investment.

**Why:** when a single mistake exposes millions of users' data, the cost of
one incident dwarfs the cost of any amount of prevention. The mathematics of
scale changes which precautions are rational.

### Amazon

**Optimises:** explicit authorisation as a first-class, auditable service.
Amazon's answer to "may this principal do this action on this resource?" is a
policy engine — every access is an explicit decision, logged, with a written
policy behind it.

**Sacrifices:** simplicity. Policy systems are powerful and genuinely hard to
reason about; misconfigured policies are themselves a famous source of
breaches.

**Why:** their customers demand it, their auditors require it, and their
scale makes implicit rules unmanageable.

**What this project has instead**, honestly stated: an ORM hook plus a shared
access helper. That is the right size for a system with one resource type and
one relationship. It would not survive "share a document with a colleague
with read-only rights until Friday" — that requirement demands a real
authorisation model, and knowing when your simple mechanism has run out is
the skill.

### Microsoft

**Optimises:** hybrid identity, delegation, and compliance evidence.
Enterprises need service accounts, group membership, administrative
delegation, and an audit trail they can hand to a regulator.

**Sacrifices:** simplicity again, and a much larger surface area to get
right.

**Why:** their customers are organisations, not individuals, and an
organisation's access rules are genuinely complicated.

**The generalisable point across all four:** tenancy is not one problem. It
is a spectrum from "each row has one owner" (this project) to "a policy
language evaluating dynamic rules over hierarchical principals" (a cloud
provider). **Choosing a point on the spectrum is the design decision, and
choosing a point far to the right when you are at the left costs you months.**

---

# Part E — Feature 3: The Streaming Answer Path

The first two features were about correctness of data. This one is about
**time**, which is a different kind of hard.

## E.1 The problem statement

> *An answer takes several seconds to generate. Show it to the user as it is
> produced. Keep the interface honest at every moment: no duplicate messages,
> no permanently stuck state, no spinner that outlives its request, and never
> a frozen server for everybody else while one answer is generated.*

## E.2 How a beginner approaches it

Wait for the answer, then show it. When told it feels slow, add a spinner.
When told the spinner is not enough, discover streaming and iterate over the
provider's stream inside the request handler, sending each piece out.

**Noticed:** that users dislike waiting.
**Predicted:** nothing.
**Measured:** "it streamed on my machine, alone."
**Protected:** nothing.

## E.3 Why that breaks — and this one is genuinely surprising

The single-user experience is perfect. The bug only exists when *someone else
is also using the system*, which is precisely the condition that never occurs
during development.

Recall from Chapter 02 that the API is asynchronous: one thread serves many
requests by switching between them whenever one is waiting. That switching
only happens when code *yields* — when it says "I am waiting, run someone
else". Ordinary blocking code never yields. It just holds the thread.

The provider's stream object is a **blocking generator**: each time you ask
it for the next piece, it waits on the network — tens to hundreds of
milliseconds — without yielding. So iterating it inside the event loop
freezes every other request in the process for the entire duration of the
answer.

From `4964ed6`:

> *"The object Gemini returns is a blocking generator whose `__next__` waits
> on the network — tens to hundreds of milliseconds per chunk, seconds in
> aggregate. So one streaming user froze the entire API worker: every other
> request, every other SSE stream, and the health check with them."*

And the reason this particular instance survived review, which is the part
worth memorising:

> *"Only the call that OBTAINS the stream was wrapped in `run_in_executor`;
> the iteration that performs the actual network I/O ran on the event loop
> thread… Wrapping only the constructor looks correct and is not."*

Then the diagnostic sting:

> *"it would have been misdiagnosed as 'Gemini is slow' — the symptom shows
> up everywhere except the code responsible."*

**This is a general property of concurrency bugs and you should carry it with
you: the symptom appears far away from the cause.** The health check times
out. The document list is slow. Someone else's upload hangs. None of those
files contains the bug.

## E.4 The intermediate approach

The intermediate engineer knows about the event loop and wraps the blocking
call. They add error handling, a loading flag in the interface, and a way to
cancel.

They are now most of the way there, and three defects remain — all three of
which actually occurred, and all three of which were found *by looking at the
running screen*, not at the code.

**Defect 1 — the double send.** The Send button is disabled while loading.
But setting a loading flag in React is a *request to re-render*, not an
immediate change. Between the first click and the re-render, a second click
runs the handler again. From `4098ef6`:

> *"`setLoading(true)` is a state update, so the Send button's
> `disabled={loading}` does not take effect until React re-renders — between
> the first click and that render a second click re-enters sendMessage and
> runs createChatMessage again, persisting the SAME user turn twice.
> Confirmed by firing two clicks in one tick: `disabled` was still false
> immediately after the first."*

This is **re-entrancy**: a function being entered again before its previous
invocation has finished. It is one of the oldest bug families in computing,
and it appears in user interfaces exactly as it appears in operating systems.

The fix must be *synchronous*, because the problem is caused by
asynchrony — and the commit says precisely that: *"A ref is the correct
instrument precisely because the window exists due to state being
asynchronous; nothing else can close it."*

**Defect 2 — the bricked composer.** One `await` was not inside the
try-block. When it threw, the exception escaped the handler, so the cleanup
never ran: loading stayed true, the guard stayed set, and the text box stayed
disabled showing "Thinking…" forever. Only a page reload recovered it.

The general rule: **every early exit path must release every flag it set.**
The repaired version clears the guard on *five* exit paths — two early
returns, error, done, and stop. If you cannot count the exits, you cannot
know the flag is released.

**Defect 3 — the duplicate bubble that was not the duplicate send.** Here is
the subtle one. After the re-entrancy fix, exactly one row was written to the
database — verified by clicking three times in one tick — and the screen
*still* showed two bubbles. From `7c59b06`:

> *"the optimistic append fabricated its own row … It threw away what
> createChatMessage returned, so the optimistic entry carried a fake id while
> the persisted row carried a real UUID. The moment history reloaded from the
> server both were in state and the same turn rendered twice — one row in the
> database, two bubbles on screen."*

**Optimistic update** means showing the result of an action immediately,
before the server confirms, so the interface feels instant. It is a good
technique with one hard requirement: when the real result arrives, the
optimistic entry must be *reconciled* — replaced, not accompanied. Reconciling
requires that both refer to the same identity. A fabricated id guarantees they
never will.

Note also *how* this was found: **by looking at the screen after the previous
fix**. Two bugs with one symptom, where fixing the first left the symptom
unchanged. If the engineer had trusted "I fixed the duplicate" and moved on,
the product would still be visibly broken.

## E.5 The senior engineer's reasoning

The senior's framing is different from the start. They do not ask "how do I
stream tokens?" They ask: **"what states can this interface be in, and is
every one of them exitable?"**

That reframing produces the questions:

1. *What are all the states?* Idle, sending, streaming, error, cancelled,
   done.
2. *For each state, what exits it?* If any state has no exit, the interface
   can get stuck — which is exactly what defect 2 was.
3. *What can be entered twice?* Anything triggered by a user action, because
   users click twice.
4. *Whose speed limits whom?* If the answer is "one user limits everyone",
   that is a bug regardless of how fast it feels.
5. *What happens when the connection dies mid-stream?* Both sides must clean
   up; the client's abort must actually free the server's work.
6. *What happens when the provider stalls forever?* Not "is slow" — *stalls*.

Question 6 leads somewhere non-obvious, and it is the best small design
decision in the streaming path. A timeout on the whole stream is wrong,
because a long answer is legitimately long. A timeout on *each step* is
right, because a single chunk that never arrives is never legitimate. From
`4964ed6`:

> *"Each STEP is now bounded by that same setting rather than the whole
> stream — total generation time is legitimately long, but an individual
> chunk that never arrives is not."*

**Generalise that.** Whenever you set a timeout, ask what unit it should
bound: the whole operation, or one step of it? For anything streaming,
progressive, or paginated, per-step is usually the meaningful unit. This
applies to file downloads, database cursors, and message consumers.

**What the senior measures:** concurrency, deliberately. Not "did it stream"
but "did *other requests* keep working while it streamed". The commit reports
exactly that: five concurrent health checks returning 200 in 956–1215 ms
during a live stream — and even explains the ~1 s as the database round trip
rather than loop starvation, so the number is not mistaken for a residual
problem.

**What the senior protects:** the SSE event-name contract between server and
client; the rule that the interface never gets stuck; the rule that one
user's request cannot degrade another's.

**What the senior accepts:** SSE cannot carry client→server messages, so
cancellation needs a separate mechanism; a thread is occupied per streaming
request, so the thread pool becomes a capacity limit; per-step timeouts add
bookkeeping.

Now the code that reasoning produced. The blocking iterator is stepped one
item at a time through the executor, with a sentinel value to detect
exhaustion — because a `StopIteration` exception cannot cross an executor
boundary, so the ordinary Python idiom does not work here
([`backend/app/services/llm_service.py`](../backend/app/services/llm_service.py),
as described in `4964ed6`):

> *"The iterator is now stepped through the executor one `next()` at a time. A
> sentinel distinguishes exhaustion from a falsy chunk, because
> StopIteration cannot cross an executor boundary — `next(it, sentinel)`
> rather than letting it raise."*

That is a real, specific piece of Python knowledge (`next(iterator, default)`
returns the default instead of raising), used because the obvious version is
broken in this context. Chapter 07 teaches the mechanism in full.

## E.6 The staff engineer's reasoning

The staff engineer looks at these three defects and sees one question:
**why did our verification method allow all of them?**

The answers are uncomfortable and specific:

- The event-loop defect could not be seen by any test that ran one request at
  a time. So the test method must include a *concurrent* observer. That is
  why the guard runs an independent heartbeat coroutine while the stream is
  consumed, and asserts the heartbeat keeps ticking.
- The duplicate-bubble defect could not be seen by any test that checked the
  database. One row was written; the screen showed two. So the verification
  method must include *looking at the rendered screen*. That is why this
  project's rules state that no frontend change is committed until exercised
  in a real browser.
- The stuck-composer defect could not be seen by any test of the happy path,
  because it only occurs when a specific call throws. So the verification
  method must include *forcing the failure path*.

Each of those became a standing rule rather than a note about one bug. That
is the staff move: **when a defect escapes, fix the method that let it
escape, not only the defect.**

And when *no role could have caught it*, fix the roster. The repository
contains that reasoning too, in `CLAUDE.md`:

> *"If no agent could have been triggered for a defect, adding a test closes
> the instance and leaves the class open. That is how `integrity-auditor`
> came to exist: three agents referenced the trust score and none could be
> invoked for it, so a fabricated metric survived a repair phase, a security
> review, and 131 passing tests."*

**131 passing tests did not catch it.** Hold onto that number. A green suite
is evidence about the things you thought to test, and about nothing else.

## E.7 One more staff-level observation: the fallback that could not work

While investigating the streaming failures, every API key was tested against
every configured model directly — deliberately bypassing the rotation logic,
so the measurement could not be confused by the thing being measured. From
`7c59b06`:

```
gemini-2.5-flash  (primary)  0/21 keys — ResourceExhausted  -> genuine quota
gemini-1.5-flash  (fallback) 0/21 keys — NotFound           -> RETIRED MODEL
```

The fallback model had been retired by the provider. So the entire fallback
mechanism — the safety net for exactly this situation — could never have
worked, and would only ever have been discovered during the incident it
existed to survive.

Three lessons, each generalisable to any project:

1. **Test your fallback path on purpose, on a schedule.** An untested
   fallback is a comforting story.
2. **External dependencies change under you.** Model names, API versions, and
   endpoints get retired. Something must notice — which is why this project
   has a weekly scheduled `auto_model_check` job.
3. **Measure below the abstraction.** Testing keys *through* the rotator
   would have shown "everything fails" and told you nothing about why.
   Testing each key against each model directly separated "rate limited" from
   "does not exist" — two failures that look identical from above and require
   completely different responses.

## E.8 How four companies would build streaming differently

### A startup

Uses the provider's SDK streaming helper and a component library's chat
widget. Ships in a day. Accepts that one slow request may degrade others,
because with fifty users it rarely matters and they will find out when it
does.

**Sacrifices:** the failure arrives at exactly the wrong moment — the day
something is popular. That is a real, and often survivable, bet.

**When they should choose differently:** if the product is used
simultaneously by many users of the same organisation (a classroom, a
support desk), the "rarely matters" assumption is false on day one.

### Google

Would treat streaming as a serving problem: a protocol designed for streaming
(gRPC), backpressure handled explicitly, latency measured per token, and
alerting on time-to-first-token as a headline metric. **Backpressure** is the
mechanism by which a slow reader tells a fast writer to slow down — without
it, a fast producer and a slow consumer end up buffering unboundedly in
between, which becomes a memory failure.

**Sacrifices:** complexity, and infrastructure that only pays for itself at
scale.

### Amazon

Would ask the operational questions first: what is the timeout at every hop,
what happens when the load balancer's idle timeout is shorter than the
answer, how does a deployment drain in-flight streams, and what is the
per-request cost. **The load-balancer timeout question is the one that bites
real teams** — a proxy that closes idle connections after 60 seconds will
silently kill long streams in production while working perfectly in
development.

### Microsoft

Would care about the client matrix: corporate proxies that buffer SSE
(breaking streaming entirely for some customers), older browsers, and an
offline or degraded mode. They would ship a non-streaming fallback path and
support it for years.

**And note:** this project *has* a non-streaming path (`/query/ask`)
alongside the streaming one — but Chapter 02's critique flagged that as a
maintenance risk, because two answer paths can drift. Same fact, two valid
readings: Microsoft would call it necessary compatibility; a small team
should call it a duplication risk. **Which reading is correct depends on who
your users are, and being able to argue both sides is the point.**

---

# Part F — Generalising: How to Think This Way on Any Project

Strip away DocuMindAI and what remains is a checklist you can apply to a
payment system, a game backend, or a hospital scheduler.

## F.1 The questions, in order

**Before writing code:**

1. What is the product's promise, and which failures would break it?
2. What layer *owns* this decision? Could a future engineer write the unsafe
   version by accident?
3. What does "missing", "empty" or "unknown" mean here — and does that value
   already mean something else?
4. Which failures are acceptable, and what must each one produce?
5. Who else reads or writes the thing I am changing?
6. What is the slowest step, and does it run on every request?
7. What can be entered twice, arrive out of order, or arrive never?

**Before saying it works:**

8. Under my test conditions, would the bug I fear produce a different result
   at all?
9. Did I force the failure path, or only the happy path?
10. Did I observe the guard fail when I put the defect back?
11. Did I check with a second user, a second tenant, a second concurrent
    request?
12. Did I confirm my negative result was caused by my control, and not by a
    typo? (positive control)

**After it works:**

13. What class does this bug belong to, and where else could that class live?
14. Can I find the rest mechanically instead of by memory?
15. Why did this escape? Which method, not which person?
16. Does the rule I just learned belong somewhere permanent?

## F.2 The six sentences that carry the most weight

If you remember nothing else from this chapter, remember these, and be able
to explain each with an example:

1. **Fix it at the layer that owns the decision** — not at the ninety call
   sites.
2. **A control that lies is worse than an absent control** — because it stops
   the next person looking.
3. **With one tenant, a correct filter and no filter are indistinguishable** —
   your fixture decides what your tests can see.
4. **Measure the property, not the source** — a correct-looking call can wrap
   the wrong thing.
5. **A guard you have never seen fail is not a guard.**
6. **When a defect escapes, repair the method that let it escape.**

## F.3 Applying it to something completely different

Take a project with no documents and no AI: **a hotel booking system.**

- *Promise:* a confirmed booking is honoured. Therefore double-booking is the
  unacceptable failure, and everything else is negotiable.
- *Layer that owns the decision:* "is this room free for these dates" belongs
  to one place — a single reservation function with a database constraint
  behind it — not to each endpoint that happens to create a booking.
- *Meaning of empty:* an empty availability list must mean "no rooms", never
  "the availability service failed". Two different states, two different
  values, or you will confidently sell a room you could not check.
- *Entered twice:* a user double-clicking "Confirm" must not create two
  bookings. Same re-entrancy problem as the chat composer, same class of fix —
  plus an **idempotency key**, a client-supplied unique id that lets the
  server recognise a retry of the same request and return the original result
  instead of doing the work twice.
- *Observability of the defect:* a test with one room and one user cannot see
  a race condition. You need two concurrent bookings for the same room, which
  requires deliberately concurrent testing.
- *Class thinking:* if double-booking was possible for rooms, ask where else
  two people can claim one thing — parking spaces, conference rooms, staff
  shifts, the last seat on a tour.

Notice that **not one sentence of that required knowing anything about
hotels**. The reasoning transferred completely. That is what this chapter was
for.

---

# Part G — Exercises, Progressively Harder

Work top to bottom. Answers in Part H — write yours first.

### Level 1 — Recall

**G1.** Define, in one sentence each: choke point, fail-closed, enumeration
oracle, re-entrancy, optimistic update, ratchet, backpressure.

**G2.** Why can a test suite with one seeded user account not detect a
missing tenant filter?

**G3.** What is the difference between fixing an instance and closing a
class? Give one example of each from this chapter.

### Level 2 — Comprehension

**G4.** The commit for the streaming fix says *"Wrapping only the constructor
looks correct and is not."* Explain to a beginner what was wrapped, what was
not, and why the difference matters only under concurrency.

**G5.** Explain why the repository chose HTTP 404 rather than 403 when a user
requests another user's document, and describe a situation where 403 would be
the better choice.

**G6.** The chat-documents bug turned a database error into a
general-knowledge answer. Explain precisely why the existing `mode: "general"`
signal did not help, and state the general rule about status values that
follows.

### Level 3 — Application

**G7 (debugging).** A colleague reports: *"Since Tuesday, the app feels slow
for everyone, but only sometimes. The health check occasionally times out.
Our AI provider's dashboard shows normal latency."* Write the ordered
investigation you would run, what each step would tell you, and the one
measurement that would confirm or eliminate event-loop starvation.

**G8 (review).** You are reviewing this pull request description:

> *"Fixed the bug where users could see other users' exports. Added
> `owner_id` to the WHERE clause in `list_exports`. Tested: logged in and saw
> only my exports."*

Write the review comments a senior engineer would leave. There are at least
five distinct problems.

**G9 (coding).** Write a Python function that safely consumes a blocking
iterator inside an async function, one item at a time, with a per-step
timeout, yielding items as they arrive. It must distinguish exhaustion from a
falsy item. Do not look at the repository first.

### Level 4 — Analysis

**G10.** The tenancy ratchet catches "filters `workspace_id` without
`owner_id`". Three findings escaped it because they filtered on neither.
Design a *second* mechanical check that would have caught those three, and
then state honestly what your new check still cannot see.

**G11.** Chapter 02's critique said the `/query/ask` and `/query/stream`
split is a maintenance risk, while Part E says Microsoft would consider a
non-streaming path necessary. Both are correct. Write the paragraph you would
put in an ADR that resolves this for *this* project, and state what would
change your answer.

### Level 5 — Synthesis

**G12.** Take the "hotel booking" example in F.3 and produce the full
four-level treatment for the single feature "confirm a booking": beginner
approach, why it breaks, intermediate approach, its weakness, senior
reasoning (with the five questions they would ask), staff reasoning (with the
class they would close), and what each level would measure.

---

# Part H — Answer Keys

### H1 (G1) — Definitions

- **Choke point:** the single place every path must pass through to do a
  thing, so a rule can be enforced once instead of many times.
- **Fail-closed:** when something is missing or uncertain, refuse rather than
  allow.
- **Enumeration oracle:** any response difference that tells an attacker
  which identifiers exist.
- **Re-entrancy:** a function being entered again before its previous
  invocation finished.
- **Optimistic update:** showing the expected result immediately, before the
  server confirms, then reconciling with the real result.
- **Ratchet:** a test with an allowlist of known violations that may only
  shrink, so the situation cannot get worse while it is being fixed.
- **Backpressure:** the mechanism by which a slow consumer signals a fast
  producer to slow down, preventing unbounded buffering.

### H2 (G2)

Because with one tenant, `WHERE owner_id = me` and no filter at all select
the same rows. The difference between correct and incorrect code produces no
difference in output, so no assertion on results can distinguish them. The
two fixes are to change the fixture (seed a second account, making the
difference observable) or to change the level of observation (assert on the
emitted SQL, where an absent predicate is visible with any number of
tenants).

### H3 (G3)

An instance is one bug at one site; a class is the family sharing a cause.
Instance: adding `owner_id` to `list_exports`. Class: the mechanical sweep
that requires an `owner_id` filter wherever `workspace_id` is filtered — which
found eight sites nobody had listed, plus two models with no owner column at
all.

### H4 (G4)

Two separate operations were involved. **Obtaining** the stream — the initial
call that starts the request to the provider — was correctly moved to a
worker thread. **Iterating** the stream — asking it for each next chunk — was
not; it stayed on the event loop. Each `next()` waits on the network for tens
to hundreds of milliseconds without yielding, so the single thread that
serves all requests was held for the entire answer.

Under one user this is invisible: there is nobody else to starve, and the
total time is identical. Under concurrency it is catastrophic, because every
other request — including the health check — waits for one user's whole
answer. The symptom appears everywhere except in the file responsible, which
is why it would have been misdiagnosed as "the provider is slow".

### H5 (G5)

403 means "this exists and you may not have it", which confirms the id is
real. An attacker can then walk through identifiers and map what exists
without reading anything. 404 reveals nothing: unknown id and forbidden id
are indistinguishable.

403 is better when the *existence* of the resource is not secret and the user
needs to understand why they were refused — for example, a team member
opening a document belonging to a different department in a corporate tool,
where "ask the owner for access" is the intended next step and pretending the
document does not exist would be actively unhelpful.

### H6 (G6)

`mode: "general"` meant "this chat has no documents attached". The failure
path also produced an empty document list, so it produced the same `mode`.
One value therefore described two different situations: *there was nothing to
consult* and *we could not find out what to consult*. A consumer of that field
cannot distinguish them, so the signal is useless exactly when it matters.

The general rule: **every state value must have exactly one meaning.** If an
error path needs to reuse a value that already means something, it needs its
own value instead. Merging "empty" with "unknown" is one of the most common
and most damaging modelling errors in software.

### H7 (G7) — The investigation

1. **Establish whether it is one process or all of them.** If you run
   multiple API containers and only some are slow, it is per-process state —
   which points at something in-process, like loop starvation, rather than a
   shared dependency.
2. **Correlate slowness with concurrency, not with time.** Plot slow requests
   against the number of in-flight streaming requests. Event-loop starvation
   correlates with *concurrent long requests*, not with load in general.
3. **Check the provider's latency yourself, from your own process**, rather
   than trusting their dashboard. Their dashboard measures their side.
4. **Look at what is slow.** If unrelated, trivial endpoints (a health check
   that only pings) are also slow, the problem is not in the slow feature's
   code — it is in something shared. That single observation eliminates most
   candidates.
5. **The confirming measurement:** run a heartbeat. Start a task that
   increments a counter every 10 ms and logs it. If the counter stops
   advancing while a stream is in flight, the loop is blocked — that is proof,
   not inference. The repository's guard does exactly this, and reported "only
   0 heartbeats while consuming a stream that blocks 0.60s".
6. **Only then** read code, and specifically look for synchronous work inside
   `async def` — iteration over provider objects, model inference, file
   reading, and any library call that does not take `await`.

The generalisable shape: **narrow by observable behaviour before reading
code.** "Everything is slow, including things unrelated to the feature" is a
much stronger clue than any amount of code reading.

### H8 (G8) — The review

At least five problems:

1. **Verification cannot detect the bug.** "Logged in and saw only my
   exports" is a single-tenant check; the broken version would pass it too.
   Ask for two accounts, with a negative *and* a positive control.
2. **Instance, not class.** If `list_exports` was wrong, `get_export_job` is
   likely wrong too, and so is every other endpoint written the same
   afternoon. Ask for a mechanical sweep across the module or the codebase.
3. **No regression guard, and no evidence one bites.** Ask for a test, and
   for the observed red output when the defect is reintroduced.
4. **Wrong layer, possibly.** If this decision is being written into
   individual queries, ask whether it belongs in the scoping layer instead —
   otherwise the next endpoint reintroduces it.
5. **No blast-radius statement.** Which other readers of this resource exist?
   Does the export job's payload or file path expose content? Is there a share
   or download link that inherits the same weakness?
6. **Severity not assessed.** Was this exploitable without authentication?
   Was data actually exposed? That determines whether this is a routine fix or
   an incident with disclosure obligations.
7. **No note on why it escaped.** Without that, the same gap produces the
   next one.

### H9 (G9) — The code

A correct answer looks like this. It is complete, runnable Python.

```python
import asyncio
from typing import AsyncIterator, Iterator, TypeVar

T = TypeVar("T")

_EXHAUSTED = object()  # unique sentinel: cannot be confused with any real item


async def aiter_blocking(
    iterator: Iterator[T],
    step_timeout: float = 30.0,
) -> AsyncIterator[T]:
    """Consume a blocking iterator without holding the event loop.

    Each `next()` is executed on a worker thread and bounded by
    `step_timeout`, so a single stalled item cannot hang the caller forever
    while a legitimately long total duration is still allowed.
    """
    loop = asyncio.get_running_loop()
    while True:
        item = await asyncio.wait_for(
            # next(it, default) returns the default instead of raising
            # StopIteration, which cannot cross an executor boundary.
            loop.run_in_executor(None, next, iterator, _EXHAUSTED),
            timeout=step_timeout,
        )
        if item is _EXHAUSTED:
            return
        yield item
```

The three decisions being tested:

- **A unique sentinel object**, not `None` and not `False`, so a legitimately
  falsy item (an empty string chunk, a zero) is not mistaken for the end.
- **`next(iterator, default)` rather than catching `StopIteration`**, because
  an exception raised inside an executor thread cannot propagate as
  `StopIteration` across the boundary — it becomes a `RuntimeError` in an
  async generator.
- **The timeout bounds one step, not the whole stream**, because a long total
  duration is legitimate and a single missing chunk is not.

### H10 (G10)

A second check that catches "no filter at all" must look for *reads of
content by a caller-supplied id*. One workable design: walk the AST of every
endpoint module; find every function whose parameters include something ending
in `_id` that comes from the request; then require that, before any query
against a content table (`Document`, `DocumentChunk`, `ChatMessage`), the
function calls one of the approved access helpers (`get_owned_document`,
`get_owned_document_text`) with that id. Anything else is flagged.

What it still cannot see:

- Access through a *service* rather than directly in the endpoint — the check
  is per-module and the read may be two calls away.
- Raw SQL, which is invisible to an ORM-shaped check.
- Correct-looking calls to the approved helper with the *wrong id* — for
  example passing the document id where the chunk id was intended.
- Writes. Both this check and the existing ratchet are about reads.
- Anything reached from a background task, which has no request parameters at
  all.

Being able to write that second list is the actual skill. A guard whose
limits you have not enumerated will eventually be trusted beyond them.

### H11 (G11)

A defensible ADR paragraph:

> **Keep both paths, and make the duplication structural rather than
> accidental.** `/query/stream` serves the interactive user interface;
> `/query/ask` serves the message-persisting chat flow and any client that
> cannot consume SSE. The risk is drift: a correctness fix applied to one and
> not the other, which has already happened in this codebase in a different
> area. The mitigation is that both must obtain their evidence from the same
> `GroundingService.prepare_grounded_context` call and the same
> `llm_service`, so anything about *grounding* is impossible to fix in only
> one place; only presentation may differ. A test should assert that neither
> endpoint constructs evidence by any other route.
>
> **What would change this decision:** if no non-streaming client remains
> (verified from access logs, not assumption), delete `/query/ask` and remove
> the risk entirely. If a corporate customer appears whose proxy buffers SSE,
> the non-streaming path stops being duplication and becomes a supported
> compatibility mode with its own tests.

The shape to learn: **state the decision, state the mitigation, state what
evidence would reverse it.** A decision with no reversal condition is a
belief.

### H12 (G12) — Hotel booking, four levels

**Beginner.** Check whether a booking exists for that room and those dates;
if not, insert one. Works when tested alone.

**Why it breaks.** Two requests can both check, both find the room free, and
both insert — a **race condition**, where the outcome depends on timing
between concurrent operations. Also: a double-clicking user creates two
bookings; a payment failure after insertion leaves a booking nobody paid for;
a cancelled booking may not free the room.

**Intermediate.** Wrap it in a transaction and add a uniqueness check. Better
— but a transaction alone does not prevent this particular race unless the
isolation level or a constraint actually forbids the overlap. Two
transactions can still both read "free" under common isolation settings.

**Its weakness.** The correctness now depends on database isolation
behaviour the engineer has not stated, so it works in testing and fails under
load. It is also enforced in application code, so a second code path (an
admin tool, an import script) can bypass it.

**Senior reasoning.** Questions before code:
1. What is the invariant, precisely? *No two confirmed bookings for the same
   room may overlap in time.*
2. What can enforce that invariant such that no code path can violate it? →
   A database exclusion constraint on (room, date range) for confirmed
   bookings. The database is the choke point that every path passes through.
3. What does a conflict produce? A clear, retryable error — never a silent
   overwrite.
4. What about retries and double clicks? An idempotency key on the request,
   so a repeat returns the original booking rather than making a second one.
5. How do I prove it? A concurrency test firing many simultaneous bookings
   for one room and asserting exactly one succeeds — because a single-request
   test cannot see this class of bug at all.

Measured: concurrent success counts under deliberate contention; conflict
rate in production. Protected: the overlap invariant. Accepted: writes are
slower due to the constraint, and callers must handle a conflict error.

**Staff reasoning.** The class is *"two parties claiming one scarce
resource"*, which also covers parking spaces, staff shifts, equipment, and
the last seat on a tour. So the mechanism should be a shared pattern —
"scarce resource reservation" with the constraint expressed once and reused —
rather than a bespoke fix in the room-booking code. They would also ask what
happens to the constraint under a future requirement like overbooking by 5%,
which is a *business* decision the invariant would forbid — and would want
that conversation to happen now, while the invariant is cheap to state, rather
than in an incident later.

---

# Part I — Senior Engineer's Critique of the Thinking in This Repository

An honest review of the *reasoning practices*, not the code.

### Strengths

1. **Commit messages state why a defect escaped.** Almost no codebase does
   this. It converts each bug into a permanent lesson and is the single
   highest-value habit visible here.
2. **Guards are verified red.** The observed failure message is quoted in the
   commit. That is evidence, not assertion.
3. **The distinction between instance and class is applied consistently**, and
   the limits of each mechanical check are stated rather than assumed.
4. **Verification uses two accounts with positive and negative controls**, and
   one commit even admits an earlier verification was invalid because it hit a
   nonexistent path.
5. **Measurements are stated as numbers** — "0 heartbeats", "five concurrent
   health checks at 956–1215 ms", "0/21 keys".
6. **Roles are separated by question, not by file**, and when no role could
   have caught a defect, the roster was changed rather than a note added.

### Weaknesses

1. **The reasoning lives in commit messages**, which nobody reads
   proactively. The lessons should be promoted into a small number of durable
   rules — some have been, but not all. A rule discovered in `a632b13`
   ("enumerate the readers when you change a writer") is worth more in a
   checklist than in a message from months ago.
2. **Verification depth is uneven.** Tenancy was verified with two accounts
   over HTTP; other areas were verified by unit tests alone. That unevenness
   is not itself wrong — depth should follow blast radius — but it is not
   documented as a deliberate policy, so it reads as inconsistency.
3. **Some fixes bundle a correctness change with a formatting change**
   (the composer commit includes a typography change). That makes reverting
   the risky part harder than it should be.
4. **The known-limits lists are excellent but scattered.** The tenancy hook's
   limits are in its docstring; the ratchet's limits are in a commit message.
   A single "what our controls do not cover" page would be more useful than
   either.
5. **No load or concurrency testing as a routine practice.** The concurrency
   defects were found reactively. A modest, regular concurrency test would
   convert that into a proactive discipline.

### The one habit to copy above all others

Write, in every non-trivial fix, one sentence beginning **"Why it escaped:"**.
It costs a minute and it is the difference between a codebase that
accumulates fixes and one that accumulates *judgment*.

---

# Part J — Interview Questions, With Model Answers

These are the questions this chapter prepares you for. The model answers are
project-grounded and honest — you could defend every sentence.

**J1. "Tell me about a bug you found that was hard to detect."**

> The retrieval path filtered documents by a workspace identifier that looked
> like a tenant key but was actually a category derived from a slug, so it was
> identical for every user. Any session-less query swept every user's
> documents and returned their text with page citations.
>
> What made it hard to detect was not subtlety in the code — it was that our
> test fixtures had one account. With one tenant, a filter that matches the
> right rows and no filter at all return the same rows, so every result-based
> assertion passed. We fixed it by changing what we observed: the guard
> asserts on the compiled SQL, where a missing predicate is visible with any
> number of tenants, and runtime verification uses two real accounts with both
> a negative and a positive control.
>
> The fix itself was at the layer that owns the decision. `owner_id` became a
> required positional parameter with no default on the retrieval function, so
> a caller that forgets it raises a `TypeError` rather than quietly reading
> across tenants.

**J2. "How do you know your tests are any good?"**

> By reintroducing the defect and watching the test fail, and by reading what
> it prints. A test that has never failed is not evidence — it may assert
> something always true, or test the wrong module.
>
> I also try to test the property rather than the source. We had a case where
> `run_in_executor` was present in the function but wrapped the wrong
> operation — the call that obtained a stream was offloaded, the iteration was
> not. A test asserting the call existed would have passed. The test we wrote
> ran an independent heartbeat while consuming a blocking stream and asserted
> the heartbeat kept ticking. On the broken version it recorded zero
> heartbeats over 0.6 seconds.

**J3. "You fixed a bug. How do you know it is the only one of its kind?"**

> I usually do not, from reading. So where the pattern is mechanically
> detectable, I write the sweep rather than fixing the listed instances. On
> this project a class-wide check for "filters on the category key without the
> owner key" found eight sites that our defect register never listed,
> including two models with no owner column at all. The register documented
> four; there were at least twelve. It was enumerating examples, not bounding
> the problem.
>
> I also write down what the sweep cannot see. That one only catches code that
> filters on the category key — three findings escaped it because they
> filtered on nothing at all, which is a different shape of the same family.

**J4. "Walk me through a performance problem you diagnosed."**

> The symptom was that unrelated endpoints, including a trivial health check,
> became slow whenever anyone was streaming an answer — while the AI
> provider's own latency was normal. That combination is the signal: when
> things unrelated to a feature slow down alongside it, the cause is something
> shared, not the feature's logic.
>
> The API is asynchronous, so one thread serves many requests by switching
> whenever a request waits. The provider's stream is a blocking generator —
> each `next()` waits on the network without yielding — so iterating it on the
> event loop held the single thread for the whole answer. We stepped the
> iterator through a worker thread one item at a time, with a per-step timeout
> rather than a whole-stream timeout, because a long total answer is
> legitimate and a chunk that never arrives is not.
>
> We verified it by running five concurrent health checks during a live
> stream; they returned in about a second each, which was the database round
> trip, not starvation.

**J5. "When would you deliberately not fix something properly?"**

> When the cost of the proper fix exceeds the risk, and I can say so
> explicitly. On this project eleven tenancy sites could not be closed by
> adding a predicate because the model had no owner column, and adding one
> required a data decision that was not mine to make. Blocking everything
> until then was not realistic, so those were listed in a ratchet — an
> allowlist keyed by module, function and model, with each entry tagged with
> its finding and reason. New violations fail the build, and a second test
> fails if a listed entry stops being a real violation, so the list can only
> shrink.
>
> The important part is that it is written down with an owner and a reason.
> An undocumented shortcut is debt nobody is servicing.

**J6. "How would you build this differently at a much bigger company?"**

> The pipeline itself would not change much; the surrounding apparatus would.
> At Google's scale I would expect a labelled evaluation set and online
> experiments before a ranking change, because a one percent relevance
> regression is expensive enough to justify the measurement infrastructure. At
> Amazon I would expect a written design document with a failure section, an
> owning team on call, and cost per query tracked as a real metric. At
> Microsoft I would expect pluggable providers and a compatibility promise,
> because enterprise customers need to bring their own model and answer
> auditors about where data lives.
>
> Here, with one developer and free-tier limits, the right call was per-stage
> tracing returned with every request and honesty about what is not tuned. Our
> fusion constant is the value from the literature, not a value tuned on
> labelled data, because we have no labelled data. I would rather say that
> than imply otherwise.

---

# Part K — Reverse-Engineering Exercises

These train the skill of reading someone else's system, which Chapter 39
covers fully. Do them against this repository.

**K1.** Open [`backend/app/core/document_access.py`](../backend/app/core/document_access.py).
Without reading any commit history, work out from the code alone: what
decision does this module own, why does it return 404 rather than 403, and
which two files would be wrong if this module did not exist? Then check your
answer against commits `24d55c0` and `a83658b`.

**K2.** Run `git log --oneline | grep -i tenan`. Read the messages in order
and produce a timeline of the tenancy work: which finding was fixed when,
which fix caused a regression, and which commit first bounded the class
mechanically rather than by enumeration.

**K3.** Find one place in the repository where a comment describes behaviour
that the surrounding code does *not* implement, or where a comment records a
past fix in a way that would confuse a new reader. (There is at least one:
`7c32a15` mentions correcting a now-stale comment at the `doc_filter` site.)
Write the corrected comment.

**K4.** Pick any file in `backend/app/services/`. Identify: its choke points,
its fail-open paths, and one place where a status value could mean two
different things. Write what you would change and why.

---

# Part L — Design-It-Yourself Exercises

**L1 — A different product, same reasoning.** Design the *reasoning* (not the
code) for a feature that lets a user share a document with one other named
user, read-only, with an expiry date. Produce: the problem statement, the
layer that owns the decision, the meaning of every state including error
states, the failure table, what you would measure, and what class of bug you
are most afraid of. Then state which of this repository's existing mechanisms
would break under this feature — there are at least two.

**L2 — A different domain entirely.** A school needs a system where teachers
enter grades and students see only their own. Produce the four-level analysis
for "a student views their grades", and identify the equivalent of the
`workspace_id`/`owner_id` confusion that this domain is likely to have. (Hint:
class id versus student id.)

**L3 — Adversarial.** You have joined a team whose product has no tenancy
enforcement layer; every endpoint filters by hand and the test suite has one
account. You cannot rewrite everything. Write the ninety-day plan: what you
would do in week one, what mechanical check you would build first, what you
would tell leadership about risk, and how you would prevent new violations
while old ones remain.

---

# Part M — Validation Checklist for This Chapter

Tick these honestly. If any one fails, re-read the named section before
continuing to Chapter 04.

- [ ] I can state the core question of each of the four levels of thinking
      without looking. *(A.3)*
- [ ] I can explain why a single-tenant test fixture makes a whole class of
      security bug invisible. *(B.7, D.7)*
- [ ] I can define choke point, fail-closed, enumeration oracle, ratchet,
      re-entrancy, optimistic update, and backpressure. *(B, E)*
- [ ] I can explain why "measure the property, not the source" exists, using
      the wrapped-constructor example. *(B.6, E.3)*
- [ ] I can explain why a comment describing a non-existent control is worse
      than no comment, and name the three times it happened here. *(D.4)*
- [ ] I can explain why `[]` was the wrong error value, and state the general
      rule about status meanings. *(B.2, C.8)*
- [ ] I can describe the difference between a whole-operation timeout and a
      per-step timeout, and say which fits a stream. *(E.5)*
- [ ] I can argue how a startup, Google, Amazon and Microsoft would each build
      one of these features differently, in terms of what each optimises and
      sacrifices. *(C.9, D.8, E.8)*
- [ ] I completed G7, G8 and G9 without looking at the answers first.
- [ ] **The real test:** given a feature I have never seen, in a domain I know
      nothing about, I can produce the senior engineer's five questions before
      any code is written. *(F.1)*

If the last box is ticked, this chapter did its job: the reasoning is now
yours, not this repository's.

---

*Next: [04-ai-agents-and-orchestration.md](04-ai-agents-and-orchestration.md)
— what an AI agent actually is, how this project's eleven specialist roles
were designed so that no two answer the same question, and why splitting work
into isolated, focused roles is an engineering pattern rather than a
prompting trick.*
