# 04 — AI Agents and Orchestration, as Software Engineering

**Prerequisites:** Chapters 01, 02 and 03. In particular this chapter reuses,
without re-explaining: choke point, fail-closed, instance versus class, the
ratchet, the guard that bites, measure-the-property-not-the-source,
observability of a defect, blast radius, and the four levels of thinking. If
any of those is hazy, re-read Chapter 03 Part B first — this chapter is
Chapter 03 applied to a new subject.

---

## 4.0 What this chapter is, and what it refuses to be

This chapter is **not** about prompting. There will be no tips about phrasing,
no "act as a senior engineer" tricks, no template for getting better output.
Those things exist, they matter a little, and they are not engineering.

This chapter treats an AI agent as what it actually is: **a component in a
system.** A component has a responsibility, an interface, inputs, outputs,
state, failure modes, a cost, and a blast radius. Every question you learned
to ask about a service in Chapter 02 and about a decision in Chapter 03
applies here, unchanged.

The claim this chapter defends is this: **the interesting part of building
with AI agents is not the AI. It is the orchestration** — deciding what the
parts are, who owns which question, how they hand work to each other, what
happens when one is wrong, and how you keep the whole thing from decaying.
That is a distributed-systems problem and an organisational-design problem
wearing a new hat.

The laboratory is this repository, which was built by exactly this method and
which recorded, in its own commit history, the moment its agent roster failed
and why.

---

# Part A — What an Agent Actually Is

## A.1 The problem statement

> *You have a large, unfamiliar task — audit a codebase, verify a fix, find
> why an answer was wrong. A language model can help. But the task needs many
> steps, the steps depend on what earlier steps found, the model cannot see
> your files unless something shows them to it, and it cannot run anything
> unless something runs it for it. How do you turn "a model that produces
> text" into "a thing that completes a task"?*

## A.2 The three things people confuse

Before defining an agent, we must separate three things that beginners treat
as one.

**1. A model.** A function from text to text. You give it a string, it
returns a string. It has no memory of yesterday, no ability to read a file, no
ability to run a command. It is stateless and inert. Everything else is built
around it.

**2. A one-off prompt.** One call to that function. You paste in a question,
you get an answer. All the information the model will ever have about your
problem must be in that one string. If the answer requires knowing what is in
forty files, you must paste forty files.

**3. An agent.** A **loop** around the model, plus **tools**, plus a
**goal**.

Here is the loop, in plain language, because this is the definition that
matters:

> The agent is given a goal and a set of tools. It calls the model. The model
> replies with either an answer, or a request to use a tool ("read this file",
> "run this command"). If it is a tool request, the surrounding program
> actually performs it and puts the result back into the conversation, then
> calls the model again. This repeats until the model produces an answer or
> the loop hits a limit.

That is all an agent is. **A loop, tools, and a stopping condition.** There is
nothing mystical in it. If you have ever written a `while` loop that calls a
function, decides what to do with the result, and loops again, you have
written the same shape.

Three consequences follow immediately, and they are the whole engineering
story:

- **The agent decides its own next step.** You do not know in advance which
  files it will read. That is the source of its usefulness *and* of every
  problem in this chapter.
- **Everything it knows lives in one growing conversation.** That
  conversation is its entire world, and it has a size limit.
- **Tools are power.** An agent with a "delete file" tool can delete files.
  Its capability is exactly the set of tools you granted, and nothing more.

## A.3 Why agents exist — the history, briefly

The progression took about three years and each step solved a specific
failure of the previous one.

**2020–2022 — the prompt era.** Models were good at text but knew nothing
about your situation. You pasted context by hand. The limits were obvious:
you could not paste a repository, and the model could not check anything it
claimed.

**2022–2023 — retrieval.** Rather than pasting everything, fetch the relevant
parts first. This is exactly the RAG pattern in Chapter 01 — the same
technique, applied to a different problem. It solved "the model does not know
my data" but not "the model cannot *do* anything".

**2023 — tool use.** Models were trained to emit a structured request meaning
"call this function with these arguments". Now the model could ask for a
search, a calculation, a file read. This is the moment the agent became
possible, because a loop around tool use is an agent.

**2023–2025 — agents and multi-agent systems.** Once one agent worked, people
tried many. And the industry immediately rediscovered — at high speed and
some expense — every lesson from the microservices era of Chapter 02:
coordination is expensive, unclear ownership is fatal, and more parts is not
more capability.

**The historical rhyme is worth stating explicitly.** In 2015 the industry
learned that splitting a system into many services solves an organisational
problem and costs you a distributed-systems problem. In 2024 the industry
learned that splitting work across many agents solves a *context and focus*
problem and costs you a distributed-systems problem. **Same lesson, same
mistakes, ten years apart.** If you understand Chapter 02's monolith
argument, you already understand most of the multi-agent argument.

## A.4 How a beginner thinks about agents

*"An agent is a smart assistant. If I give it a big task and a good
description, it will do the task. If the result is bad, my description was not
good enough, so I will write a longer one."*

This produces the characteristic beginner artifact: **one enormous
instruction, doing everything, growing every time something goes wrong.** Each
failure adds a paragraph. The instruction becomes a museum of past mistakes.

## A.5 Why that breaks

Five failure modes, and they arrive in this order.

**1. Context dilution.** The model's attention is finite. An instruction
containing forty rules gives each rule a smaller share of attention than an
instruction containing four. Adding a rule to fix problem A measurably
degrades compliance with rules for problems B and C. **You cannot add rules
for free.**

**2. Context exhaustion.** The conversation grows with every tool result. A
long task fills the window with file contents, most of which are no longer
relevant. Then either the oldest material is dropped — silently losing your
original instruction — or the task fails.

**3. No verifiable output.** "Review my code" produces prose. Prose cannot be
checked, routed, or acted on mechanically. You cannot tell "found nothing"
from "did not look".

**4. Conflicting goals in one head.** Ask one agent to both *write* a fix and
*decide whether the fix is good* and it will approve its own work. Not from
dishonesty — from the same reason human authors are poor proofreaders of their
own text: the thing that produced the error also produced the belief that it
was right.

**5. Unbounded blast radius.** One agent with every tool can do anything at
any moment, including things you never intended, in a step you never
inspected.

## A.6 The intermediate solution

The intermediate engineer discovers "multi-agent" and splits the work: a
planner agent, a coder agent, a reviewer agent, a tester agent. Each gets its
own instruction. Output flows from one to the next.

This is real progress. It fixes dilution and gives each part a focus.

## A.7 What is still weak

**Weakness 1 — the split is by job title, not by question.** "Coder" and
"reviewer" describe *roles*, not *questions*. When the reviewer says
"consider refactoring this" and the tester says "this is untestable as
written", who decides? Both are commenting on structure. Nobody owns
structure.

**Weakness 2 — no output contract.** Each agent returns prose in its own
shape. The orchestrator must interpret. Interpretation is where information
gets lost.

**Weakness 3 — no notion of what the agent *cannot* do.** Without an explicit
scope boundary, every agent drifts toward commenting on everything, because
every agent is capable of commenting on everything.

**Weakness 4 — no trigger definition.** *When* does the reviewer run? On every
change? Only on request? What about code nobody is changing? This one is not
academic. It is the exact hole that cost this repository thirty-two
high-severity findings, and we will examine it in Part E.

**Weakness 5 — cost is invisible.** Every agent is a fresh conversation that
must be re-supplied with context. Five agents on one task can cost five times
one agent, for work that may have needed one.

## A.8 The senior reframing

The senior engineer stops asking "what roles should my agents have" and asks:

> **"What questions must be answered about this work, and which of them must
> be answered by something that did not do the work?"**

That single reframing produces almost everything else:

- If a question must be answered independently, it needs its own agent —
  because independence is the whole point.
- If two questions would always be answered by the same evidence and the same
  reasoning, they are one question, and splitting them buys nothing but cost.
- If a question has no clear owner, it will not be answered by anyone, and
  the gap will be invisible because every agent will *look* like it might have
  covered it.

The senior's questions before creating any agent:

1. What is the one question this agent answers, in a single sentence?
2. Could any existing agent answer that same sentence? If yes, this is not a
   new agent.
3. What must it *not* do — and is that written down?
4. What must the caller supply for it to work from a cold start?
5. What shape is its output, so that the answer can be routed rather than
   read?
6. What tools does it need — and what is the smallest set that suffices?
7. When is it triggered, and can it be triggered when *nothing has changed*?
8. What does it cost to run, and is that cost worth it every time?

## A.9 The staff reframing

The staff engineer accepts all of that and asks two further questions that
only make sense once you have several agents:

**"Does the roster, as a system, have holes?"**

Each agent may be individually excellent and the *set* may still fail to cover
something. This is not a hypothetical — it is what happened here, and Part E
is the incident report.

**"What is the total number of rules a contributor must know?"**

Every agent, every boundary, every handoff is a rule someone must hold in
their head. Rules have a budget. An eleventh agent that duplicates a tenth
does not add capability; it adds ambiguity, and ambiguity is worse than
absence because it *looks* like coverage.

## A.10 An agent, defined in engineering terms

Now we can state the definition this chapter will use, and it is deliberately
boring:

> **An agent is a component with: one responsibility, an explicit input
> contract, an explicit output contract, a defined trigger, a bounded tool
> grant, isolated state, and a named owner for its result.**

Read that list again and notice that **not one item mentions AI**. Replace
"agent" with "microservice" and every word still applies. That is the point:
you already know how to think about this. The techniques transfer.

---

# Part B — The Engineering Primitives

Fifteen concepts, each of which is the difference between a working
multi-agent system and an expensive mess. Each follows the pattern from
Chapter 03: what it is, why it exists, how beginners get it wrong, what
experienced engineers do instead, the tradeoff, and the repository evidence.

## B.1 Ownership

**What it is.** For every question the system must answer, exactly one
component is responsible for answering it.

**Why it exists.** Because a question owned by two components is owned by
neither. When two reviewers both "sort of" cover security, each assumes the
other looked.

**The beginner error.** Assigning ownership by *subject area* — "this agent
handles the backend, that one handles the frontend". Subjects overlap; a
tenancy bug lives in an endpoint file and is a security question and an
architecture question at once.

**What experienced engineers do.** Assign ownership by **question**, not by
area, and write the question as one sentence.

**The repository's test for this**, from `CLAUDE.md`:

> *"Each agent answers **one question no other agent may answer.** If you
> cannot state an agent's question in a single sentence that no sibling could
> also claim, the roster is wrong — fix the roster, not the prompt."*

Note the last clause. When two agents overlap, the instinct is to add a
sentence to one of them clarifying the boundary. That treats a structural
problem as a wording problem. The structural fix is to merge them, split them
differently, or delete one.

**The tradeoff.** Strict single ownership means some findings arrive through
an agent that cannot fully judge them, requiring a handoff. That is a real
cost — handoffs lose information — and it is accepted because diffuse
ownership loses *entire findings*.

**Generalising.** This is exactly the rule for on-call rotations, for module
ownership in a large codebase, and for who signs off a release. "Two teams
own it" is how outages happen.

## B.2 Responsibility versus capability

**What it is.** *Capability* is what a component can do. *Responsibility* is
what it is supposed to do. They are not the same, and the gap between them is
where trouble lives.

**Why it matters.** A language model can comment on anything. Given a
security review task, it will also notice a typo, an inefficiency, and a
naming inconsistency — and reporting all of them dilutes the finding that
mattered.

**How experienced engineers handle it.** They write down what the component
must *not* do, as explicitly as what it must do. Every agent definition in
this repository has a section headed "Scope boundary — what you do NOT own",
and it is usually longer than the purpose section. For example,
`test-runner`'s boundary includes:

> *"You do not adjudicate a test that passes by asserting a fabricated value
> → `integrity-auditor` owns that verdict. Report the suspicion with evidence
> and hand it over: a test asserting `trust_score == 70.0` against a hardcoded
> literal is green, correct as written, and worthless. **Green is a fact about
> the test, not about the system.**"*

That paragraph does three jobs at once: it removes a responsibility, it names
who takes it, and it explains the reasoning so the boundary is understood
rather than merely obeyed.

**The tradeoff.** Writing negative scope takes effort and dates quickly. It
must be maintained, and the repository has a rule that agent files are updated
in the same commit as the registry table describing them.

## B.3 Boundaries and tie-breaks

**What it is.** A boundary is the rule that decides which of two plausible
owners actually owns a case.

**Why it exists.** Because for any two well-designed components there will be
cases that look like both.

**The beginner error.** Assuming clear roles produce clear boundaries. They do
not. The hard cases are precisely where two clear roles meet.

**What experienced engineers do.** They write the tie-breaks down **as a
list, in advance**, using the ambiguous cases they have actually hit.
`CLAUDE.md` carries seven of them. Three are worth quoting because each
encodes a distinction that took a real defect to learn:

> *"`rag-pipeline-tracer` says *which stage*; `performance-profiler` says
> *what it costs*."*

> *"`infra-health-checker` = **runtime, now**; `release-readiness-checker` =
> **artifact, pre-deploy**."*

> *"`release-readiness-checker` **detects** an exposed secret;
> `security-reviewer` **adjudicates** it."*

That third pattern — **detection separated from verdict** — appears three
times in this roster. It is a genuinely reusable design: the component that
*finds* a thing is often not the component qualified to *judge* it. A smoke
detector does not decide whether to evacuate the building.

**The sharpest tie-break in the file** is the one that had to be invented
after a defect escaped:

> *"`rag-pipeline-tracer` explains why **one answer** was wrong;
> `integrity-auditor` establishes that a number was **never real for any
> answer**. A metric that is always identical cannot 'disagree with the
> answer,' so the tracer's trigger can never fire on it."*

Read the logic. It is not a preference. It is a proof that one agent's trigger
condition is *unreachable* for a certain class of defect — therefore that
class needs a different owner. That is a formal argument about coverage, and
it is the kind of reasoning this chapter is trying to install in you.

## B.4 Contracts

**What it is.** A contract is the agreed shape of what goes in and what comes
out. Chapter 02 defined an interface; a contract is an interface plus its
promises.

**Why it exists.** Because output that must be *interpreted* cannot be
*routed*. If every agent returns free prose, a human must read all of it to
decide what to do. If every agent returns the same ten sections with tagged
findings, the orchestrator can act on them mechanically.

**The repository's output contract** is identical for all eleven agents:
Summary · Evidence · Findings · Root Cause · Risks · Recommendations ·
Confidence · Escalation · Files Reviewed · Additional Verification Needed.

Uniformity is deliberate, and `CLAUDE.md` explains why it is stated once
centrally rather than repeated per agent: *"that would be two sources of truth
for one contract."*

**The four quality bars** attached to that contract matter more than the
sections. Each exists because of a specific past failure:

1. **Evidence is a command and its output**, or `file:line` and the actual
   lines. The stated reason: *"This project has already shipped wrong
   conclusions drawn from a proxy metric (`len(app.routes)`) and from a regex
   that silently failed on a multi-line decorator."* A **proxy metric** is a
   number you measure because it is easy, standing in for the number you
   actually care about — counting registered routes to prove endpoints work is
   a proxy, and it was wrong.
2. **Confidence is three-valued and load-bearing:** Verified / Partially
   Verified / Unverified — with the rule *"**Unverified is a distinct verdict
   from 'fine'** — never collapse 'I could not check this' into 'no
   findings.'"* This is the same lesson as Chapter 03's `[]` bug: two
   different states must not share one value.
3. **Every blocker carries a routing tag:** agent-actionable /
   owner-access-required / owner-decision-required. An untagged blocker
   cannot be routed and stalls.
4. **No padding.** *"'No findings; the fix is at the right layer' is a
   complete report. Inventing findings to fill sections is worse than an empty
   section, because it costs the thread a verification pass it did not need."*

Bar 4 is the one people underestimate. A component that manufactures output to
appear useful imposes a hidden tax on everything downstream. This is true of
agents, of status reports, and of code reviewers.

## B.5 Communication

**What it is.** How results move between components.

**Two shapes exist**, and choosing between them is a real architectural
decision:

- **Direct** — agent A calls agent B and consumes its answer.
- **Mediated** — every agent returns to a coordinator, which decides what
  happens next.

**This repository chose mediated, absolutely:** *"They run in isolated
contexts, cannot invoke each other, and report back to the thread that called
them."*

**Why.** Three reasons, in increasing importance:

1. **Loop prevention.** If A can call B and B can call A, you have built
   something that can spin forever and spend money doing it.
2. **Attribution.** With a single coordinator, every result has a known
   requester and a known consumer. In a mesh, a wrong conclusion three hops
   deep is very hard to trace.
3. **Judgment stays in one place.** Agents produce findings; the coordinator
   decides what to *do*. If agents could act on each other's output, the
   decision authority would be distributed across components that each see
   only part of the picture.

**The tradeoff, stated honestly.** Everything is serialised through one
coordinator, which becomes a bottleneck and must hold the whole picture. The
repository accepts this because the coordinator is also the only writer of
production code, so it must hold the whole picture anyway.

**Generalising.** This is the difference between a service mesh where
everything calls everything, and an orchestrator pattern where a workflow
engine drives each step. The second is easier to debug, easier to audit, and
slower. For anything where a wrong answer is expensive, the second usually
wins.

## B.6 State

**What it is.** Information that persists between invocations.

**The central fact about these agents: they have none.** Each invocation
starts empty. `CLAUDE.md` states it as a warning because it is the single most
common source of failure:

> *"**Subagents start cold.** The invoking prompt must carry every file path,
> diff, error, and prior decision."*

**Why statelessness was chosen.** Chapter 02 taught that a stateless component
can be run any number of times, in any order, on any machine, and cannot leak
one invocation's information into another's. That last property is the
important one here: a reviewer that remembered the last three reviews would
carry assumptions into a case where they do not apply, and you would have no
way to know which assumptions.

**The cost, and it is not small.** Every invocation must be re-supplied with
context. That is tokens, latency, and a real chance the caller forgets
something. Which is exactly why the required inputs are specified centrally
rather than left to memory. Five things, every time:

> *"**(1)** the diff or changed-file list *or*, in standing-defect mode, the
> `final_audit.md` finding id and the claim under test; **(2)** the intent in
> one sentence — without it no agent can judge ownership; **(3)** how to run
> the stack; **(4)** any prior decision that must not be relitigated; **(5)**
> any known-failing baseline, so pre-existing failures are not reported as
> new."*

Item (5) is a subtle piece of craft. Without a baseline, a cold agent reports
every pre-existing failure as though your change caused it, and you spend an
hour investigating something that was broken before you arrived.

Item (4) prevents a specific and maddening failure: an agent with no history
will happily re-open a decision that was made deliberately last week, because
from its position that decision looks like an oversight.

## B.7 Context

**What it is.** The material an agent can see while working: its instruction,
plus everything the loop has put in front of it.

**Why it is the scarcest resource.** It is finite, it is shared by everything
the agent must know, and it degrades — attention thins as it fills.

**Context pollution** is the term for filling that space with material that is
not relevant to the current question. It is not merely wasteful. It measurably
worsens the answer, because the model must decide what matters, and more
irrelevant material means more chances to weigh the wrong thing.

**This is the strongest engineering argument for specialist agents**, and it
is worth stating precisely, because it is the argument people most often get
backwards:

> Splitting work across agents is not primarily about specialised
> *knowledge*. It is about specialised *context*. A security review that never
> loads the frontend styling files is not smarter about security — it is
> **undistracted** about security.

**The repository's expression of this**, from the skill policy: load a skill's
body *"only when its domain is the work in hand — UI/a11y/typography skills
for frontend and response-rendering work, nothing for backend, Celery, Redis,
migrations, or deployment."* And explicitly: *"Loading costs context and buys
nothing outside its domain."*

Note also the discipline of **discovering names without reading bodies**: at
session start, list the skills (names only) and only read a skill's full text
when its domain comes up — *"Do not read bodies yet; several are megabytes."*
That is context budgeting as a deliberate practice.

## B.8 Delegation

**What it is.** Deciding which work leaves the coordinator, and to whom.

**The beginner error.** Delegating everything, on the theory that more review
is more rigour.

**Why that fails.** Every delegation costs a cold-start briefing, a full
invocation, and a verification pass on the result. Running eleven reviewers on
a one-line change is not thoroughness; it is a tax that makes people stop
running reviewers at all.

**The repository's rule** is blunt: *"Invoke **only** the reviewers a change
actually touches. Running every reviewer on every change is waste, not
rigor."* And it is implemented as a routing table from *what the work touches*
to *which reviewers, in order*. Auth or tenancy → `security-reviewer` then
`test-runner`. Celery or queues → `code-reviewer`, `infra-health-checker`,
`test-runner`. A score shown to a user → `integrity-auditor`, then
`security-reviewer` if it is a control.

**The single most important line in that table** is not a row. It is the note
beneath it:

> *"A finding is not routed by the file it lives in, but by the question it
> raises. `veritas_engine.py` is a services file, which suggests
> `code-reviewer`; the question 'is this number real' is
> `integrity-auditor`'s. Route on the question."*

This generalises far beyond agents. Routing a bug report by which file it
touches sends database questions to whoever owns the file, rather than to
whoever understands databases. **Route on the question.**

## B.9 Isolation

**What it is.** Each agent runs in its own context and cannot see or affect
another's.

**Why it exists.** Two reasons, and both are load-bearing:

1. **Independence of judgment.** A reviewer that has seen the author's
   justification is influenced by it. A reviewer that sees only the code is
   not. This is the same reason scientific peer review is blinded.
2. **Bounded damage.** An agent that goes wrong ruins its own report and
   nothing else.

**The strongest evidence of isolation being taken seriously in this
repository is the tool grants**, which differ per agent. Most get
`Read, Grep, Glob, Bash`. But `security-reviewer` gets:

```
tools: Read, Grep, Glob
```

**No `Bash`.** The agent that reviews the security of the system cannot
execute anything on it. That is **least privilege** — the principle that every
component gets the minimum access it needs and nothing more — applied to an
AI agent exactly as you would apply it to a service account.

Think about why that specific agent is the one without shell access. It reads
authentication code, secret handling, and upload paths. It is the agent most
likely to encounter a real credential in the course of its work, and the one
whose instruction explicitly forbids reading `.env` contents. Removing its
ability to run commands means that even a confused or manipulated invocation
cannot exfiltrate or execute anything. **The capability was removed rather
than the behaviour forbidden** — which is precisely Chapter 03's rule: make
the unsafe thing impossible, not merely discouraged.

**A second isolation decision worth noticing: the model assignment.** Each
agent declares which model runs it:

| Model | Agents | Why |
|---|---|---|
| `opus` (most capable, most expensive) | `code-reviewer`, `integrity-auditor`, `rag-pipeline-tracer`, `security-reviewer` | Open-ended judgment, adversarial reasoning, attribution across a pipeline |
| `sonnet` (balanced) | `test-runner`, `infra-health-checker`, `performance-profiler`, `release-readiness-checker`, `response-quality-reviewer`, `workspace-qa` | Procedural work with a defined checklist |
| `haiku` (fastest, cheapest) | `docs-sync-checker` | Purely mechanical: counts, paths, contradictions |

That table is a **cost-versus-capability allocation**, and it is the same
decision as choosing instance sizes for services. `docs-sync-checker` runs on
the cheapest model because its own instruction says *"You do mechanical
verification, not judgment. Every finding must be a checkable fact."* A task
defined that tightly does not need expensive reasoning — and it runs at the
start of *every* session, so its cost is paid most often.

**The generalisable rule:** match the model to the *shape of the task*, not to
its importance. Mechanical verification of important things still only needs
mechanical capability.

## B.10 Error propagation

**What it is.** What happens to a failure discovered by one component, on its
way to whoever can act on it.

**The beginner error.** Assuming a found problem is a solved problem. It is
not: it must reach a decision-maker with enough information to act, and be
labelled with what kind of action it needs.

**The mechanism here** is the three-way escalation tag on every blocker:

- **agent-actionable** — the coordinator can fix it now.
- **owner-access-required** — it needs a credential, a paid tier, or an
  account that no agent has.
- **owner-decision-required** — it is a real choice a human must make; the
  agent presents options and does not pick.

**The subtlest rule in the entire roster** lives in `integrity-auditor`'s
escalation section, and it is worth reading twice:

> *"**owner-access-required** — the claim needs a credential, paid tier, or
> account to become true (Tavily, a paid model tier, production data).
> **Report the feature as unearned and currently misreported, never as 'works
> once configured'** — the misreporting is the finding and it is fixable
> without the credential."*

Unpack that. A feature cannot work because a key is missing. The lazy report
is "blocked, needs a key". But there are *two* defects: the feature does not
work, **and** it claims success while not working. The second is fixable today
by anyone, with no key. Separating "blocked on access" from "misreporting" is
what turns a stalled item into an actionable one.

**Generalise it:** whenever something is blocked, ask what part of it is
*not* blocked. Very often the honest reporting of the blockage is the part you
can fix immediately, and it is the part that matters most.

## B.11 Retries

**What it is.** Running something again after a failure.

**When it is correct.** For **transient** failures — a network blip, a rate
limit, a timeout. The defining property is that the same input may succeed
next time.

**When it is wrong, and this is the part beginners miss.** For
**deterministic** failures, a retry is pure cost. If the agent's report is
wrong because the prompt omitted the baseline, retrying with the same prompt
produces the same wrong report, more slowly and more expensively.

**The engineering discipline** is therefore: *before retrying, change
something.* Either the input (add the missing context) or the approach (ask a
different agent, or ask a narrower question).

**Where retries appear in this repository, and it is not in the agents.** The
Gemini key rotation logic retries across many API keys when one is rate
limited — a genuinely transient failure. And Chapter 03 showed the failure
mode of retrying blindly: the fallback model had been *retired*, so every
retry produced `NotFound`, which is deterministic. Retrying a deterministic
failure across twenty-one keys produces twenty-one identical failures and the
appearance of a quota problem. **Distinguishing transient from deterministic
before retrying is the whole skill.**

## B.12 Verification

**What it is.** Establishing that a result is true, rather than merely
produced.

**Why it exists in this chapter at all.** Because an agent's output is
confident prose, and confident prose is exactly what a wrong answer also looks
like. Chapter 03's rule — *a control that lies is worse than an absent one* —
applies with full force to an agent's report.

**The repository's rule is unusually blunt**, and it is the most important
sentence in this whole chapter for anyone about to build with agents:

> *"**Verify agent output before acting on it.** Agents have been wrong here.
> Re-check any load-bearing claim against the repo or runtime — this is not
> optional politeness, it has caught real errors."*

**How to verify cheaply.** Three techniques, in order of cost:

1. **Demand evidence in the contract, not conclusions.** A report that
   contains the command and its output can be checked by re-running the
   command. A report that says "I checked and it is fine" cannot.
2. **Spot-check the load-bearing claim only.** Not every sentence — the one
   the decision rests on.
3. **Use an independent path.** The tenancy work verified with two real
   accounts over HTTP *and* an assertion on the compiled SQL. Two paths that
   fail differently.

**The tradeoff.** Verification costs time, and if you verify everything you
have gained nothing from delegating. The judgment call is *which* claim is
load-bearing — and that judgment cannot be delegated.

## B.13 Composition

**What it is.** Combining components so the output of one becomes the input of
another.

**The named chains in this repository:**

- `release-readiness-checker` → `security-reviewer` (detection → verdict)
- `integrity-auditor` → `security-reviewer` (a fabricated control is
  detected, then adjudicated)
- `integrity-auditor` → `test-runner` (a test that passes by asserting a
  hardcoded value)
- `rag-pipeline-tracer` → `performance-profiler` (stage → cost)
- `workspace-qa` → the layer owner it names
- `test-runner` → `code-reviewer` when a failure is architectural rather than
  a bad assertion
- `code-reviewer` → `integrity-auditor` when a reviewed file turns out to
  claim something it never did

**The critical qualifier:** these are described as *"thread-mediated"* —
meaning the second agent is a call *the coordinator makes next*, not a call
the first agent makes. The chain is a routing rule for a human-or-coordinator
decision, not a pipeline the agents execute themselves. That preserves B.5's
mediated communication.

**The pattern to extract.** Look at the direction of every chain: they all run
from **cheap and mechanical** toward **expensive and judgmental**. Detection
before verdict. Measurement before ranking. Localisation before optimisation.
This is the same shape as the retrieval pipeline in Chapter 01 — cheap wide
search, then expensive narrow rerank. **Cheap filters first, expensive
judgment last, is a universal system-design pattern**, and recognising it in
two completely different subsystems is exactly the kind of transfer this
course is for.

## B.14 Scaling

**What it is.** What happens as the work grows.

**The counter-intuitive fact:** adding agents does not scale a system the way
adding servers does. Servers are interchangeable; agents are not. Two
identical reviewers do not review twice as well — they review the same thing
twice and disagree, and now you need a third thing to resolve them.

**What actually scales:**

- **Narrower questions.** As a codebase grows, a question that was clear
  becomes two questions. That is the moment to split an agent — the
  repository's rule is *"Split one that has grown two distinct owners."*
- **Sharper triggers.** More code means more changes; without precise
  triggers you either run everything always (unaffordable) or nothing reliably
  (useless).
- **Better inputs.** Cold-start briefing quality dominates output quality far
  more than instruction length does.

**What does not scale:** a bigger instruction. Every rule added dilutes the
others (B.7). There is a size past which an agent gets worse with each
addition, and the repository's response to that pressure is telling: when the
audit proved `code-reviewer`'s charter incomplete, it gained *one* question —
symmetry — rather than three paragraphs of examples.

## B.15 Observability

**What it is.** Being able to tell what the system did and why, after the
fact.

**Why it is harder here than in ordinary software.** An agent's reasoning is
not a stack trace. You cannot step through it. What you *can* observe is: what
it was given, what tools it used, what it claimed, and whether the claim held.

**The design response** is to make the report itself the observable artifact —
which is why "Evidence", "Files Reviewed", "Confidence" and "Additional
Verification Needed" are mandatory sections. Those four exist so that a reader
can reconstruct **what the agent actually looked at**, which is the closest
thing to a trace that exists.

"Additional Verification Needed" deserves special note: it is a component
declaring the limits of its own coverage. That is the same discipline as the
tenancy hook's docstring listing what it does not cover (Chapter 03, D-019),
and as the ratchet commit recording what the sweep cannot see. **A component
that states its own blind spots is worth more than one that appears
complete.**

---

# Part C — The Roster: Eleven Agents, Eleven Questions

Here is the actual system. For each agent: the one question, why it exists,
and the boundary that keeps it from colliding with its neighbours.

| Agent | The one question it answers | Model |
|---|---|---|
| `docs-sync-checker` | Do the three governing docs still match the repo? | haiku |
| `test-runner` | Did the suite pass, is the failure path covered, and does the guard bite? | sonnet |
| `code-reviewer` | Is this decision in the layer that owns it — and are its readers still symmetric? | opus |
| `integrity-auditor` | Does this code do what it claims? | opus |
| `security-reviewer` | Is this an exposure, and how bad? | opus |
| `infra-health-checker` | Did it come up healthy, and what did it leave behind? | sonnet |
| `release-readiness-checker` | Is the artifact shippable? | sonnet |
| `rag-pipeline-tracer` | Which stage produced this bad answer? | opus |
| `performance-profiler` | What does it cost, and is it worth fixing? | sonnet |
| `workspace-qa` | Does the advertised feature actually work end to end? | sonnet |
| `response-quality-reviewer` | Is the presentation good and the substance untouched? | sonnet |

Read down the "question" column. Every entry is a *different kind of
question*: consistency, execution, structure, truthfulness, risk, runtime,
artifact, attribution, cost, function, presentation. Not one is a subject
area. That is the design.

## C.1 The agents that verify *claims*

**`integrity-auditor`** — *does this code do what it claims?*

The newest agent, created because of a specific escape (Part E). Its class has
one signature: **the code reports success it did not earn.** Its instruction
lists ten mechanical discriminators, ordered cheapest-first — zero callers,
declared-but-never-read settings, read-but-never-declared settings, imported
but not installed, hardcoded where computed is claimed, initialised and never
reassigned, renormalised into meaninglessness, library API drift, encoding
assumptions, and finally *does the claim reach a user*.

Two rules inside it are worth stealing for any review work you ever do:

> *"**You do not report ordinary unused code.** A helper written for future
> use, clearly named, claiming nothing, is not a finding. **The defect is the
> claim, not the disuse.**"*

> *"Never report a claim as earned because you could not disprove it.
> **Unverified is a distinct verdict from earned**, and conflating them is the
> exact failure you exist to catch."*

And one piece of rhetorical craft that makes findings land instead of starting
arguments:

> *"**The refusals that prove the standard exists.** `embedding_service.py:86`
> and `reranker_service.py:40` both refuse to emit fabricated data in
> production and explain why a zero vector is worse than an outage. **Cite
> these when reporting — the codebase already holds the correct standard, and
> your findings are places it was not applied.** That framing is what makes
> the fix obvious rather than contentious."*

That is a lesson about *how to deliver a finding*, not about finding it: show
that the team already agrees with the principle elsewhere, and the argument is
over before it starts.

**`test-runner`** — *did it pass, is the failure path covered, does the guard
bite?*

Three duties, and the third was added later (Part E). It may not write or edit
tests — *"Never edit a test to make it pass"* — which is separation of powers:
the component that judges the tests cannot change them.

**`docs-sync-checker`** — *do the docs still match the repo?*

Runs first in every session, on the cheapest model, doing purely mechanical
checks. It exists because of a documented failure mode: stale documentation is
trusted, and trusted-and-wrong is worse than absent. It also enforces which of
the three governing documents may contain what — a table of "must contain" and
"must NOT contain" that prevents the split-brain problem Chapter 02's D-009
described.

## C.2 The agents that judge *changes*

**`code-reviewer`** — *is this decision in the layer that owns it?* Four
ordered questions: ownership, duplication, **symmetry**, honesty. Question 3
was added after the H5 regression from Chapter 03 — the write-path fix whose
readers were never enumerated — and its own instruction explains why it was
missing: *"Right layer, no duplication, nothing silenced — every existing
question passes it."*

**`security-reviewer`** — *is this an exposure, and how bad?* The only agent
that may assign security severity. No shell access (B.9). Explicitly forbidden
from reading `.env` contents.

**`response-quality-reviewer`** — *is presentation good and substance
untouched?* Its primary job is enforcing a boundary rather than improving
anything: a formatting change that touches retrieval, prompts, citation
derivation, or trust computation is its top finding *regardless of how good it
looks*. It also refuses to work at all if the system is not yet functionally
correct — *"presentation work on a broken pipeline is wasted."* **An agent
that declines to run under the wrong conditions is a well-designed agent.**

## C.3 The agents that observe *reality*

**`infra-health-checker`** (runtime, now) and **`release-readiness-checker`**
(artifact, before deploy) — separated purely by *time*, which is an unusual
and clean way to draw a boundary.

**`workspace-qa`** — *does the advertised feature actually work?* Its
instruction contains the single best sentence in the roster for setting the
right attitude: *"**Assume nothing works because a document says it does.**"*

There is also a deliberate decision recorded inside it that is worth studying:

> *"There is **one QA agent for all seven workspaces, deliberately.**
> Per-workspace agents were rejected because the defects here have not been
> workspace-shaped: the Legal contract bug lived in a shared frontend handler,
> not in Legal code. You verify per workspace and attribute per **layer**."*

This is the anti-proliferation argument in its purest form. Seven workspaces
*looks* like seven agents. But agents should be split by **where defects
live**, and defects lived in shared code. **Split by the shape of the
problem, not by the shape of the product.**

**`rag-pipeline-tracer`** and **`performance-profiler`** — attribution and
cost. The profiler carries a hard rule that eliminates a whole genre of
useless output: *"**no recommendation without a measurement** … You do not
recommend loop-keyword swaps, comprehension rewrites, micro-refactors, or
style changes — ever."*

## C.4 Why no two agents own the same question

Because it was *tested*, not assumed. The roster was checked as a system
against 83 real findings, and the gap that emerged is Part E.

The enforcement rule is the one-sentence test from B.1, plus a lifecycle:

> *"Add an agent only for an *observed, recurring* responsibility no existing
> agent covers — not because a technology exists. Split one that has grown two
> distinct owners; merge two that answer the same question; retire one that
> stops earning its place."*

Four verbs: add, split, merge, retire. **Most people building agent systems
only ever use the first.**

---

# Part D — Orchestration: How `CLAUDE.md` Runs This

An agent roster is a set of parts. Orchestration is the system that makes
them a system.

## D.1 The responsibility hierarchy

One rule, stated first because everything else depends on it:

> *"**The main engineering thread owns** planning, implementation, debugging,
> architectural decisions, prioritization, integration, and commits. **It is
> the only writer of production code.**
> **Specialist agents own** verification, review, diagnosis, measurement, and
> quality gates. **No specialist implements.**"*

**Why this split and not another.** Three reasons of increasing depth:

1. **Independence.** A component that both writes and approves cannot review
   independently. This is the separation of duties that every audit regime in
   any industry requires.
2. **Coherence.** Code written by eleven separate writers, each with its own
   cold context, would drift in style and structure immediately. One writer
   means one voice, one set of patterns, one architecture.
3. **Accountability.** When something is wrong, exactly one component wrote
   it. There is no distributed authorship to untangle.

**The tradeoff, and it is real:** the coordinator becomes the bottleneck. All
implementation is serialised through one worker. That is accepted here because
the coordinator is also the only component holding the full architecture in
mind, and Chapter 02's argument applies unchanged — for one developer,
coordination cost dominates parallelism benefit.

**Generalising:** this is exactly why many engineering organisations require
that a change be reviewed by someone who did not write it, and why the person
who deploys is often not the person who wrote the code.

## D.2 The two trigger modes

This is the most important orchestration concept in the chapter, and it exists
because of a failure.

- **Change-triggered** — a diff exists; the agent judges it. The default.
- **Standing-defect** — no diff, no recent change. The agent audits code as it
  is, against a finding id or a file list. The invoking prompt supplies *the
  claim under test* in place of a diff.

And then the rule that makes the second mode real rather than decorative:

> *"**A missing diff is never a reason to decline.** The overwhelming majority
> of this repository's real defects were found in code nobody had touched in
> months: the guard with zero callers, the trust score that is a constant, the
> two features that have never executed once. A roster that only reviews
> changes cannot find them, and for one full cycle this one could not. **Age
> is a trigger, not a defence.**"*

Sit with "age is a trigger, not a defence". The natural instinct — in code
review, in auditing, in operations — is that old code is proven code. It is
not. Old code is code that has *survived*, which is a different property
entirely, and survival is guaranteed for anything nobody looks at.

## D.3 The delegation matrix

Covered in B.8. The structural point: routing is written down *in advance*, as
a table from "work touches X" to "reviewers, in order". Deciding who to
consult in the moment, on each change, guarantees inconsistency.

## D.4 Cold start and deliberate duplication

The rule that most contradicts normal engineering instinct:

> *"**Cross-agent repetition is deliberate.** The Turbopack restart rule
> appears in four agent files, the `DummyLLMProvider` warning in three. Do not
> consolidate them into a shared file: a cold subagent reads only its own
> definition, so a rule it does not carry is a rule it does not have.
> **Duplication is the cost of cold start; pay it.** The rule for changing one
> is to change every copy in the same commit."*

Every instinct you have been building says *do not duplicate*. Here the
constraint inverts it: a shared file that nobody loads is not shared, it is
absent. So the duplication is correct — **and the cost is paid explicitly by a
maintenance rule** ("change every copy in the same commit").

**The generalisable principle:** DRY (don't repeat yourself) is not a law of
nature. It is a heuristic that assumes all readers can see the shared source.
When that assumption fails — cold-start agents, offline documentation, safety
placards in different rooms — duplication is correct, and what you owe is a
synchronisation rule, not consolidation.

## D.5 Why orchestration prevents architectural decay

**What architectural decay is.** The slow drift of a system away from its
intended structure: rules that used to hold stop holding, decisions get made
at the wrong layer, invariants quietly become false, and nobody notices
because each individual step was small and reasonable.

**Why it happens.** Four mechanisms, all of which are visible in this
repository's history:

1. **Local fixes at the wrong layer.** Each is defensible alone; together they
   distribute one decision across ninety sites.
2. **Documentation drifting from code.** A stale invariant is worse than none,
   because it is trusted.
3. **Claims outliving their implementations.** A guard with zero callers, a
   setting that gates nothing.
4. **Green tests providing false comfort.** 131 passing tests coexisting with
   a fabricated metric and two features that had never run.

**How orchestration counters each**, mechanically rather than by good
intentions:

| Decay mechanism | The counter | Enforced by |
|---|---|---|
| Fixes at the wrong layer | "Is this decision in the layer that owns it?" asked on every non-trivial diff | `code-reviewer` |
| Docs drifting from code | Mechanical cross-check at the start of every session | `docs-sync-checker` |
| Claims outliving code | "Does this do what it claims?" with age as a trigger | `integrity-auditor` |
| False comfort from green tests | Guards must be observed failing | `test-runner` |
| Rules decaying into folklore | The lifecycle rule: when implementation reveals a better rule, amend the handbook immediately | `CLAUDE.md`'s own maintenance rule |

**The deeper point, and it is the reason this section exists:** decay is not
caused by bad engineers. It is caused by *nobody being responsible for
noticing*. Every one of those counters is a **standing owner for a question
that would otherwise be nobody's job.** Orchestration is how you convert "we
should keep an eye on that" into a thing that actually happens on a schedule.

That principle applies with or without AI. A team that assigns one person to
audit documentation quarterly has done the same thing. The agents make it
cheap enough to do every session.

---

# Part E — The Roster Failure: A Full Incident Analysis

Now the case study, in the format of Chapter 03: problem, why it broke, why it
escaped, and how the fix changed practice.

## E.1 What happened

The repository had **ten** specialist agents. They were individually
well-designed: clear questions, explicit boundaries, no overlap. A line-by-line
audit of all 425 tracked files then produced 83 findings — and the majority of
them were things that *no agent could have been triggered for*.

The commit that repaired it, `bdc8308`, opens with the diagnosis:

> *"The ten specialists are individually strong and non-overlapping. Tested as
> a system against final_audit.md's 83 findings, they share one structural
> defect: every trigger is a change. 'Before committing a diff.' 'After
> changing a start command.' 'Before claiming a performance win.' Nothing
> owned code nobody was touching — which is where the audit found the majority
> of the real defects."*

**Every agent was correct. The system had a hole.** That is a property of the
set, not of any member — and no amount of reviewing individual agent
definitions would have revealed it.

## E.2 The sharpest case

> *"The sharpest case is the trust score. Three agents reference it and none
> can be invoked for it: response-quality-reviewer explicitly excludes
> computation, security-reviewer names fabricated scores as an invariant but
> triggers only on auth/tenancy/uploads/secrets, and rag-pipeline-tracer fires
> when trust disagrees with the answer — while S6's defect is that it always
> returns ~66/MEDIUM, so it never visibly disagrees. Coverage claimed in three
> places, deliverable in none."*

Trace that reasoning carefully, because it is a small masterpiece of coverage
analysis:

- Agent 1 mentions the trust score but its charter **excludes computation**.
- Agent 2 names fabricated scores as something it cares about, but its
  **trigger conditions** never fire for this file.
- Agent 3's trigger is "the trust score disagrees with the answer" — and **the
  defect makes that trigger unreachable**, because a constant cannot disagree
  with anything.

Three mentions, zero possible invocations. And the defect itself: three of five
factors hardcoded (65% of the weight), a fourth comparing a chunk's first 50
characters verbatim against model prose so it essentially never matches — with
the output re-exported into a compliance PDF under the line "Trust scores
indicate retrieval confidence."

## E.3 Why it escaped

The commit names it, and the name is what makes this incident great teaching
material:

> *"That is finding S4's own pattern reproduced inside the roster that missed
> it."*

S4 was `validate_retrieval_scope`: a function whose docstring said *"Hard
blocking guard called before EVERY retrieval operation… CRITICAL: Never remove
or bypass this call"* and which had **zero call sites**.

The roster had the identical defect at a different level of abstraction. Three
agent definitions *claimed* coverage of the trust score. Zero could actually be
invoked for it. **A control that lies, one level up.**

**The general lesson, and it is the most valuable one in this chapter:**
*claimed coverage is not coverage.* You must check whether the trigger
conditions can actually fire for the case you care about. This applies to
monitoring alerts (does this alert's condition occur during the failure it
claims to detect?), to test suites (does any test exercise this path?), to
on-call rotations (is anyone paged for this class of incident?), and to
review checklists.

## E.4 What the fix changed — practice, not just code

Four changes, and no application code was touched:

**1. A new agent with a question no sibling could answer.** `integrity-auditor`
— *does this code do what it claims?* Created for a proven gap, not because
the idea sounded good. It is 162 lines, and it detects; `security-reviewer`
still adjudicates exposure — *"the same split release-readiness-checker
already has."* **A new agent that reuses an existing boundary pattern is a
sign of a coherent system.**

**2. An existing agent gained one question.** `code-reviewer` gained
*symmetry*, because the H5 regression *"would have passed"* the other three:
*"Right layer, no duplication, nothing silenced — every existing question
passes it."*

**3. An existing agent gained a duty.** `test-runner` gained guard-bites
verification, because *"CLAUDE.md has always required guards to be verified by
reintroducing the defect; no agent owned watching one go red."* A requirement
with no owner is a wish.

**4. The orchestration document itself changed.** Two trigger modes were
documented explicitly *"so a missing diff can never again be grounds to
decline"*; a defect-register lifecycle was added; and `final_audit.md` was
given a documented owner *"so it is a register and not a second status
document competing with PROGRESS.md."*

**The shape of this repair is the lesson.** One new component, two amendments,
and a change to the rules — with the reasoning for each recorded. Not "we
added more review".

And the closing line of the commit is a piece of operational honesty most
teams never write down: *"No application code changed. Takes effect after a
session restart."* A change to your process is a deployment, and it has a
rollout mechanism like any other.

---

# Part F — Why More Agents Is Usually Harmful

## F.1 The problem statement

> *You have agents. Something goes wrong that none of them caught. The obvious
> response is to add an agent for it. When is that right, and when does it
> make the system worse?*

## F.2 How a beginner thinks

*"More reviewers means more coverage. Coverage is good. Add an agent."*

## F.3 Why that breaks — five costs, all invisible at first

**Cost 1 — diffusion of responsibility.** Two agents that both partly cover a
question produce the bystander effect: each report looks like coverage, and
the gap between them is invisible because it is nobody's stated job. Part E is
this cost, realised: three agents referenced the trust score and it was
nobody's.

**Cost 2 — the rule budget.** Every agent is a thing a contributor must know
exists, when to invoke, what to supply, and how to read. Eleven is already a
lot. Twenty is a system nobody uses correctly, so they use it randomly, which
is worse than not having it.

**Cost 3 — token and time cost.** Each agent is a fresh cold start with a full
briefing. Five agents on a small change costs five briefings, five runs, and
five verification passes by the coordinator.

**Cost 4 — verification burden.** Every report must be checked (B.12). More
reports means more checking, and checking is done by the one component that is
already the bottleneck. Past a certain point, adding agents *reduces* the
amount of real verification that happens, because the coordinator starts
skimming.

**Cost 5 — contradiction.** Two agents commenting on overlapping territory
will eventually disagree, and now the coordinator must adjudicate — a job that
did not exist before and produces nothing.

## F.4 The senior test

Before adding an agent, three questions:

1. **Can I state its question in one sentence that no existing agent could
   claim?** If not, it is not a new agent.
2. **Is this an observed, recurring gap, or one incident?** One incident is a
   handled case. A pattern is a role.
3. **Would amending an existing agent close it more cheaply?** Two of the
   three fixes in Part E were amendments, not additions. That ratio is
   healthy.

## F.5 The staff test

One further question: **does the roster get simpler or more complex?**

A roster where each agent's question is sharper after the change is healthier
than one with an extra member. `integrity-auditor`'s creation *sharpened*
three existing agents, because their boundaries against it had to be written
down — `test-runner`, `rag-pipeline-tracer` and `security-reviewer` all gained
explicit hand-off rules. The set became more legible, not less.

## F.6 When agents should not exist at all

State these plainly, because the honest answer to "should I use agents here?"
is often no.

- **When the task is deterministic.** A linter, a type checker, a schema
  validator or a script is faster, cheaper, and always right. Never use a
  probabilistic component for a decidable question. If you can write the
  check, write the check.
- **When the task is trivially verifiable by the person doing it.** Reviewing
  a three-line change costs less than briefing an agent to review it.
- **When you cannot state the question.** If you cannot write the one
  sentence, the agent will produce prose you cannot act on.
- **When you will not verify the output.** An unverified agent report is a
  confident claim with no evidence behind it, which is exactly the class of
  defect this whole repository exists to eliminate.
- **When the cost of being wrong is very high and the work is not
  independently checkable.** Do not let a probabilistic component be the last
  line of defence for something irreversible.
- **When a rule would work instead.** "Never commit `.next/`" is a
  `.gitignore` entry and a CI check, not an agent.

**That last one is the most commonly violated.** A large fraction of proposed
agents are rules that somebody has not written down yet.

---

# Part G — Specialists Versus One Large Agent

## G.1 The honest case for one large agent

Do not dismiss this. One agent with the whole task has real advantages:

- **No handoff loss.** Everything it learned in step 3 is available in step
  20. A specialist rediscovers context every time.
- **No coordination cost.** No briefings, no contracts, no routing table.
- **Coherence.** One reasoning process produces consistent decisions.
- **Simplicity.** One thing to maintain, one thing to understand.

**When it wins:** small, self-contained tasks; exploratory work where you do
not yet know the questions; anything where the cost of a handoff exceeds the
cost of dilution. If you are debugging one problem for an hour, one agent with
full context beats five with partial context.

## G.2 The honest case for specialists

- **Focused context** (B.7) — undistracted beats knowledgeable.
- **Independent judgment** — the reviewer that did not write the code.
- **Bounded capability** — least privilege per role (B.9).
- **Routable output** — a contract instead of prose.
- **Coverage that can be reasoned about** — you can ask "does any agent own
  this question?" and get an answer, which is impossible with one big agent
  whose coverage is whatever it happened to think of.

**When they win:** repeated work with known questions, anything where
independence matters, anything where the cost of a missed class of defect is
high.

## G.3 The rule for choosing

> **Use one agent when you are still discovering the questions. Use
> specialists when the questions are known and recurring.**

This repository is squarely in the second case: 233 commits, a defect register
with a taxonomy, and questions that recur every session. A brand-new prototype
is squarely in the first.

**And note the migration path**, which is how real systems actually get here:
you start with one agent, you notice the same question being asked badly every
time, and *that* question becomes the first specialist. Roles are discovered,
not designed up front. Every agent in this roster exists because a specific
kind of mistake kept happening.

---

# Part H — How Orchestration Evolves as a Repository Grows

Four stages. Recognising which one you are in prevents both premature
structure and overdue chaos.

**Stage 1 — one person, one small repo.** No agents. Maybe one general
assistant. Structure here is pure overhead; the whole system fits in one head.

**Stage 2 — one person, a real system (this repository).** A coordinator plus
a handful of specialists for the questions that recur. Written rules, because
one person across many sessions is effectively many people — *your own context
resets too*. This is the stage where written orchestration first pays for
itself, and it is why `CLAUDE.md` exists at all: a session six months from now
starts as cold as any subagent.

**Stage 3 — a small team.** The rules become social as well as technical:
which reviews are required before merge, who arbitrates a disagreement, how a
new rule gets adopted. The agent roster starts to mirror the team's actual
review culture, and the two must stay consistent or people will follow
whichever is cheaper.

**Stage 4 — many teams.** Ownership becomes formal (code owners, mandatory
reviewers per area), routing becomes automated, and the orchestration document
splits: global invariants centrally, local rules per area. **The failure mode
of this stage is that the central document becomes a document nobody reads**,
which is why this repository's rule is to *"amend incrementally; never
regenerate it wholesale"* — a document rewritten in bulk loses the reasons its
rules exist, and rules without reasons get deleted by the next person.

**The signal to move to the next stage** is always the same: a question is
being answered inconsistently, and the inconsistency is costing more than the
structure would.

---

# Part I — Startup, Google, Amazon, Microsoft

How each would build this orchestration, and *why* — business reasons, not
just technical taste.

### A startup

**Optimises:** speed of shipping and cash. Every hour of process is an hour
not spent on the product.

**Would build:** one capable agent, no roster, no contracts, review by the
founder reading the diff. Perhaps one automated check on the thing that has
burned them before.

**Sacrifices:** consistency and coverage. Classes of defect will accumulate
silently, exactly as they did here.

**Why it can be right:** with three engineers who all know the whole system,
tacit coordination is genuinely cheaper than written coordination. The tacit
approach fails at about the size where no single person knows everything —
and the failure is usually invisible until an incident.

**When they should choose differently:** the moment the product handles other
people's private data or money. Then the tenancy-style class of defect is not
a quality problem, it is an existential one, and the cheapest possible version
of `security-reviewer` earns its cost immediately.

### Google

**Optimises:** correctness at scale and consistency across an enormous
codebase. Their institutional strength is tooling and static analysis.

**Would build:** deterministic analysis wherever the question is decidable —
because a checker that is always right beats a reviewer that is usually right
— with review reserved for genuinely judgmental questions. Readability review
by a certified reviewer outside your team is a Google institution, and it is
the same idea as this roster's independence requirement, implemented with
humans.

**Sacrifices:** flexibility and speed. Heavy process is a real tax on small
changes.

**The transferable lesson:** *convert judgment into a checker whenever the
question becomes decidable.* Several agents here are doing work that could
become a script — `docs-sync-checker`'s path and count checks especially. That
is the direction of maturity, and the fact that it runs on the cheapest model
shows the author already sees it.

### Amazon

**Optimises:** ownership and operational accountability. You build it, you run
it, you are paged for it.

**Would build:** explicit ownership for every component, a written narrative
before significant work, and a mandatory failure analysis after every
incident — the **correction of error** document, whose whole purpose is to fix
the *mechanism* that allowed the defect rather than the defect.

**The remarkable thing:** this repository already does that, in commit
messages. Every fix ends with *"Why it escaped:"* and *"Which review missed
it:"*, and Part E is a full correction-of-error for the roster itself.
**One developer independently arrived at the practice a company of 1.5 million
people mandates**, because the underlying pressure is the same: if you do not
fix the mechanism, the defect returns wearing different clothes.

**Sacrifices:** it is slow, and it only works if the documents are actually
read.

### Microsoft

**Optimises:** compatibility, and processes that survive personnel change.
Their systems must be maintainable by people who were not there when they were
built.

**Would build:** heavy emphasis on written specification, threat modelling as
a required step for anything touching security boundaries, and a defined
lifecycle for how a rule is proposed, approved, and retired.

**Sacrifices:** agility, and a tendency for process to outlive its purpose.

**The transferable lesson:** `CLAUDE.md` has an amendment rule (*"When
implementation reveals a better rule, amend this section immediately"*) but no
**retirement** rule for orchestration rules themselves. Microsoft's discipline
would ask: which of these rules is still earning its place? A roster has a
retirement rule; the rulebook does not. That is a genuine gap, and it appears
in the critique below.

---

# Part J — Exercises

Progressive. Answers in Part K — write yours first.

### Level 1 — Recall

**J1.** Define in one sentence each: agent, tool grant, cold start, context
pollution, least privilege, escalation tag, trigger mode, proxy metric.

**J2.** State the one-sentence test for whether a proposed agent should exist.

**J3.** Why does `security-reviewer` have no shell access, when nine of its
ten siblings do?

### Level 2 — Comprehension

**J4.** Explain, to someone who has never used an agent, why duplicating the
same rule into four agent files is correct here, when duplication is usually a
defect.

**J5.** The commit says three agents referenced the trust score and none could
be invoked for it. Explain each of the three reasons separately, and then say
what general check this suggests you should run on any monitoring or review
system.

**J6.** Why does `integrity-auditor` insist on reporting a credential-blocked
feature as "unearned and currently misreported" rather than "works once
configured"? What becomes actionable that was not?

### Level 3 — Application

**J7 (design).** You are adding a feature that sends emails to users. Decide
whether a new agent is needed. Work through the senior test and the staff
test, name the question it would own if it existed, and then argue the
opposite case. Reach a conclusion and state what evidence would change it.

**J8 (review).** A colleague proposes this agent definition:

> *"name: backend-reviewer. description: Reviews all backend changes for
> quality, security, performance, and correctness. tools: all."*

Write the review. There are at least six distinct problems.

**J9 (debugging).** An agent reports: *"I reviewed the authentication changes
and found no security issues. The implementation follows best practices."*
List everything wrong with that report as an artifact, and say precisely what
you would do before acting on it.

### Level 4 — Analysis

**J10.** The roster has eleven agents and one coordinator. Identify the single
point of failure in that design and describe two independent ways it could
produce a wrong outcome that no agent would catch.

**J11.** `workspace-qa` covers all seven workspaces deliberately, rather than
seven per-workspace agents. Construct the strongest possible argument *for*
seven agents, then say what evidence would be needed to justify the split —
and what evidence the repository actually has.

### Level 5 — Synthesis

**J12.** Design an agent roster from scratch for a completely different
project: a payment processing service handling card transactions, built by a
team of four. Produce: the questions that must be answered, which of them need
an independent owner, the roster (aim for four or fewer agents), each one's
trigger and tool grant, the output contract, two handoff chains, and the two
biggest coverage gaps your roster will have. Then state which of your agents
should actually be a deterministic script instead.

---

# Part K — Answer Keys

### K1 (J1)

- **Agent:** a loop around a model, plus tools and a stopping condition,
  pursuing a goal.
- **Tool grant:** the exact set of actions an agent is permitted to perform;
  its capability is this set and nothing else.
- **Cold start:** an invocation beginning with no memory of anything before
  it, so all context must be supplied.
- **Context pollution:** filling the working context with material irrelevant
  to the current question, which measurably degrades the answer.
- **Least privilege:** granting the minimum access needed and nothing more.
- **Escalation tag:** the label on a blocker saying who can act on it —
  agent-actionable, owner-access-required, owner-decision-required.
- **Trigger mode:** whether an agent is invoked by a change (change-triggered)
  or by an audit of standing code (standing-defect).
- **Proxy metric:** a number measured because it is easy, standing in for the
  one you actually care about, and capable of being right while the real thing
  is wrong.

### K2 (J2)

If you cannot state the agent's question in one sentence that no existing
agent could also claim, the agent should not exist — and the roster, not the
wording, is what needs fixing.

### K3 (J3)

Least privilege applied to the agent with the highest exposure. It reads
authentication code, secret handling and upload paths, so it is the agent most
likely to encounter real credentials; its instruction already forbids reading
`.env` contents. Removing shell access means it *cannot* execute or exfiltrate
anything even if confused or manipulated — the capability is absent rather
than the behaviour merely forbidden. That is Chapter 03's rule: make the
unsafe thing impossible, not discouraged.

### K4 (J4)

Duplication is normally a defect because two copies drift apart and readers
may see the stale one. That argument assumes every reader can reach the shared
source. A cold-start agent reads only its own definition — nothing else is
loaded — so a rule kept in a shared file is, from that agent's position,
simply absent. Consolidating would produce a *tidier* repository and a
*less capable* system. The correct response is to keep the duplication and pay
for it with a maintenance rule: change every copy in the same commit. The
general principle is that DRY assumes shared visibility; when visibility is
not shared, duplicate and synchronise deliberately.

### K5 (J5)

- `response-quality-reviewer` mentions the trust score but its charter
  explicitly excludes *computation* — it owns how the score is explained, not
  how it is produced.
- `security-reviewer` names fabricated scores as a concern, but its triggers
  are auth, tenancy, uploads, secrets and prompt construction — none of which
  fire for a scoring service.
- `rag-pipeline-tracer` triggers when the trust score *disagrees with the
  answer*; the defect was that the score was effectively constant, so it can
  never visibly disagree. **The defect makes the trigger unreachable.**

The general check: for every alert, test, review, or on-call rotation, ask
whether its trigger condition can actually occur during the failure it claims
to cover. Claimed coverage is not coverage. A monitoring alert whose threshold
is never crossed during the outage it exists to detect is the same defect.

### K6 (J6)

Because there are two defects, not one. The feature does not work (blocked on
a credential — not fixable today), **and** it reports success while not
working (fixable today by anyone). Reporting "works once configured" merges
them and makes the whole item look blocked, so the fixable half never gets
done — and meanwhile the system keeps telling users a step succeeded when it
never ran. Separating them converts a stalled item into an actionable one. The
general habit: when something is blocked, ask which part of it is not blocked;
honest reporting of the blockage is almost always available immediately.

### K7 (J7) — Email agent

**Senior test.**
1. *One sentence no sibling could claim?* Candidates: "does this email
   actually get delivered?" — `workspace-qa` owns "does the advertised feature
   work end to end", so it could claim it. "Is the email content safe from
   injection?" — `security-reviewer` owns exposure verdicts. "Does the email
   sending code do what it claims?" — that is exactly `integrity-auditor`, and
   email is a strong candidate for its class, since a `send()` wrapped in a
   broad `except` returning success is the canonical unearned claim.
2. *Observed recurring gap, or one incident?* At the time of writing, email is
   sent synchronously and `email_tasks` is registered nowhere — a known dead
   module. That is one finding, not a pattern of email-specific defects.
3. *Would amending be cheaper?* Yes: add "a message sent to a user" to
   `integrity-auditor`'s trigger list, and add email delivery to
   `workspace-qa`'s end-to-end definition.

**Staff test.** Does the roster get simpler? No — a twelfth agent whose
question three siblings could claim makes every boundary fuzzier.

**Conclusion:** do not add the agent. Amend two.

**The opposite case, argued fairly:** email has a genuinely distinctive
property — the failure is *external and invisible*. A message can be accepted
by the provider and never arrive (spam filtering, domain reputation,
bounces), which no code inspection can detect and no existing agent's evidence
model covers. If delivery failures became recurrent and business-critical
(password resets, payment receipts), "did this message actually reach a human
inbox?" is a question no sibling can answer, and it would justify a role.

**What would change the decision:** two or three delivery incidents that no
existing agent could have been triggered for. One incident is a handled case.

### K8 (J8) — Reviewing the proposed agent

At least six problems:

1. **No single question.** "Quality, security, performance, and correctness"
   is four questions, three of which already have owners
   (`code-reviewer`, `security-reviewer`, `performance-profiler`). It fails the
   one-sentence test outright.
2. **Overlaps by subject, not question.** "Backend" is an area. Areas overlap;
   questions do not. A tenancy defect is backend *and* security *and*
   architecture.
3. **`tools: all` violates least privilege.** No stated reason to write, edit
   or execute. If it is a reviewer, it should be read-only — otherwise it can
   modify the thing it is judging.
4. **No scope boundary.** Nothing says what it does *not* own, so it will
   drift into everything and dilute its own findings.
5. **No trigger, and no standing-defect mode.** "Reviews all backend changes"
   is change-triggered only, which is precisely the hole from Part E.
6. **No input contract.** A cold agent given no diff, no intent, no baseline
   will report pre-existing failures as new.
7. **No output contract.** Free prose cannot be routed, and there is no
   confidence value, so "I could not check" and "it is fine" will be
   indistinguishable.
8. **Diffusion risk.** Its existence weakens three current agents by making
   every boundary ambiguous — the bystander effect, installed on purpose.

### K9 (J9) — The bad report

**What is wrong with it as an artifact:**

- **No evidence.** No commands, no `file:line`, no quoted code. Per the
  contract, a reading is not evidence.
- **No files reviewed.** You cannot tell whether it looked at the middleware,
  the token verification, the cookie flags, or none of them.
- **No confidence value.** "Found no issues" and "could not check" are
  collapsed into one statement — the exact conflation the contract forbids.
- **"Best practices" is unfalsifiable.** It names no practice and no
  standard, so it cannot be checked or disagreed with.
- **No scope statement.** Did it cover CSRF? Cookie attributes? Algorithm
  confusion? Refresh handling? Unknown.
- **No "additional verification needed".** Every real review has limits.

**What to do before acting on it:**

1. Do not treat it as a pass. Treat it as *unverified*.
2. Re-invoke with the missing inputs: the actual diff, the intent in one
   sentence, and the specific claims to test ("HS256 only", "httpOnly and
   samesite set", "CSRF exempt list unchanged").
3. Independently spot-check the one load-bearing claim yourself — for auth,
   that the algorithm list is restricted and the secret has no fallback.
4. If the shape of the report is a recurring problem, the fix is the contract
   and the invoking prompt, not a sterner instruction.

### K10 (J10) — Single point of failure

The coordinator. It is the only writer of code, the only router of findings,
and the only verifier of agent output.

Two failure paths no agent would catch:

1. **A wrong brief produces a confidently wrong report.** If the coordinator
   supplies the wrong diff, omits the known-failing baseline, or states the
   intent incorrectly, every agent reasons correctly from false premises and
   returns clean reports. No agent can detect this, because none of them can
   see what they were not given. This is the cold-start property turned
   against you.
2. **A question nobody was asked.** The coordinator decides which agents to
   invoke. If it does not recognise that a change touches tenancy, the tenancy
   reviewer is never called, and its silence is indistinguishable from
   approval. Part E is exactly this failure at the level of the roster rather
   than of one change.

**Partial mitigations that exist:** the delegation matrix removes some routing
judgment from the moment; the required-inputs list makes omissions visible;
`docs-sync-checker` runs unconditionally at session start rather than on
demand. **Unconditional, non-discretionary invocation is the only real defence
against a coordinator that fails to invoke.**

### K11 (J11) — Seven agents or one?

**Strongest case for seven:** each workspace has genuinely different business
logic (finance ratios computed in Python, legal escalation, HR ranking,
spaced-repetition scheduling). A specialist could carry deep domain knowledge
— what a debt-to-equity ratio should look like, what an escalation clause
means — and check *semantic* correctness rather than merely that a row
appeared. Seven focused contexts also avoid one agent carrying seven domains'
worth of instruction (B.7).

**Evidence that would justify the split:** defects concentrating *within* a
single workspace's own logic, repeatedly, in ways a generalist misses — for
example wrong ratio arithmetic that produces plausible numbers.

**Evidence the repository actually has:** the opposite. The stated reason is
that *"the Legal contract bug lived in a shared frontend handler, not in Legal
code"*, and the pattern across the register is that defects live in shared
code — retrieval, tenancy, the composer, the worker registration. Seven agents
would each have re-derived the same shared-code understanding and each missed
the same shared-code defects, at seven times the cost.

**The general rule:** split agents along the axis where *defects* vary, not
where the *product* varies.

### K12 (J12) — Payment service roster

A defensible answer. The exact composition matters less than the reasoning
being visible.

**Questions that must be answered:**
1. Is money ever created, lost, or double-charged? (correctness of amounts and
   idempotency)
2. Is this an exposure — card data, tokens, access to another merchant's
   transactions?
3. Does this code do what it claims — does a "settled" status mean settled?
4. Did the tests actually exercise the failure paths (declines, timeouts,
   partial captures, retries)?
5. Does it meet the compliance obligations we are contractually bound to?
6. Is it fast enough and what does it cost?

**Which need an independent owner:** 1, 2 and 3 absolutely — each is a case
where the author's own judgment is compromised by having written the code, and
each has catastrophic and irreversible failure. 5 needs an owner but is mostly
a checklist. 4 is procedural. 6 is measurement.

**A roster of four:**

| Agent | Question | Trigger | Tools |
|---|---|---|---|
| `money-integrity-auditor` | Can this path create, lose, or duplicate money? | Any change touching amounts, ledger writes, retries, refunds — **and** standing audits of untouched money paths, because age is a trigger | Read, Grep, Glob (read-only: it must not run anything against a payment system) |
| `security-reviewer` | Is this an exposure, and how bad? | Card data handling, tokens, authentication, merchant scoping | Read, Grep, Glob |
| `test-runner` | Did it pass, are the failure paths forced, does the guard bite? | Every change | Read, Grep, Bash |
| `compliance-checker` | Does this still satisfy our stated obligations? | Changes to storage, logging, retention, or data flow | Read, Grep, Glob |

**Output contract:** the same ten sections, with one addition specific to this
domain — **"Monetary impact if wrong"**, because severity in a payment system
is measured in currency and in irreversibility, and that must be stated
rather than inferred.

**Two handoff chains:** `money-integrity-auditor` → `security-reviewer` when a
fabricated status could hide a fraudulent transaction (detection → verdict);
`test-runner` → `money-integrity-auditor` when a test passes by asserting a
hardcoded amount.

**Two coverage gaps my roster will have, stated honestly:**
1. **Nothing owns "is the integration with the card network correct?"** — that
   is external behaviour, verifiable only against a sandbox, and none of my
   four can reach it.
2. **Nothing owns concurrency.** Double-charging under simultaneous requests
   is a race condition, and a reviewer reading code is poorly placed to find
   it. That needs a deliberately concurrent test, which is a *tool*, not an
   agent.

**Which should be a script instead:** `compliance-checker`, almost entirely.
"Is card data ever written to a log?", "is this field encrypted at rest?",
"does this table have a retention policy?" are decidable questions. A grep and
a schema check are faster, cheaper, and always right. Keep an agent only for
the genuinely judgmental residue — whether a *new* data flow falls inside a
regulated category.

---

# Part L — Senior Critique of This Orchestration

Honest review of the orchestration system itself.

### Strengths

1. **Ownership is by question, and the test for it is written down.** This is
   the single best decision in the design, and it is the one most systems get
   wrong.
2. **The roster was tested as a system, not as members**, against 83 real
   findings. That is how the structural hole was found, and almost nobody does
   it.
3. **Boundaries include tie-breaks for the ambiguous cases**, derived from
   real collisions rather than imagined ones.
4. **Detection is separated from verdict**, consistently, in three places.
5. **Tool grants and model assignments are per-agent** — least privilege and
   cost-versus-capability, applied deliberately.
6. **Duplication is deliberate and paid for** with an explicit synchronisation
   rule.
7. **"Verify agent output before acting on it" is stated as a rule**, not left
   to good sense.
8. **The correction-of-error habit** — every fix records why it escaped —
   applied even to the roster itself.

### Weaknesses

1. **Every defence against a coordinator failure is itself run by the
   coordinator.** K10's failure paths have no independent check. The one
   partial answer in the system — `docs-sync-checker` running unconditionally
   at session start — is not generalised. A small set of *mandatory,
   non-discretionary* invocations tied to touched paths would close most of it.
2. **No retirement rule for orchestration rules.** The roster has add / split /
   merge / retire; the rulebook has only amend. `CLAUDE.md` is now roughly
   forty thousand characters, and every rule dilutes the others exactly as it
   would inside an agent. Some rules have surely stopped earning their place,
   and nothing asks.
3. **Several agents are doing work a script should do.** `docs-sync-checker`'s
   path existence, count and contradiction checks are decidable. Running a
   probabilistic component for a decidable question is the anti-pattern named
   in F.6, and the cheap model mitigates the cost without addressing the
   principle.
4. **No measurement of the agents themselves.** There is no record of how
   often each agent produced a finding that survived verification, or how often
   one was wrong. Without that, retirement decisions are guesses. The
   repository demands measurement before every performance claim; it does not
   apply the same standard to its own process.
5. **The invoking prompt is the weakest link and is least specified.** Five
   required inputs are listed, but nothing checks that they were supplied. A
   template — or a checklist the coordinator must complete — would convert a
   discipline into a mechanism, which is exactly the transformation this
   project applies everywhere else.
6. **`workspace-qa` explicitly cannot verify UI rendering**, leaving that to
   the coordinator. That is a stated boundary rather than a hidden gap, which
   is honest — but it means the layer where two of Chapter 03's three
   streaming defects lived has no independent owner at all.

### The one improvement I would make first

**Make a small set of invocations mandatory and path-triggered rather than
discretionary.** If a diff touches `core/auth.py`, `security-reviewer` runs —
not because the coordinator remembered, but because the rule fires on the path.
That single change closes the largest hole in the design (K10, failure path 2)
and converts the delegation matrix from advice into enforcement. It is the same
move this repository already made with the tenancy hook: replace "the
developer must remember" with "the system does it".

---

# Part M — Validation Checklist

Tick honestly. Any failure sends you back to the named section.

- [ ] I can define an agent without using the word "smart", and name its three
      parts. *(A.2)*
- [ ] I can explain why splitting work across agents is about **context**, not
      knowledge. *(B.7)*
- [ ] I can state the one-sentence ownership test and apply it to a proposed
      agent. *(B.1, F.4)*
- [ ] I can explain why `security-reviewer` has no shell access, in terms of a
      principle rather than a preference. *(B.9)*
- [ ] I can explain why duplication across agent files is correct here, and
      what obligation it creates. *(D.4)*
- [ ] I can retell the roster failure — three agents referencing the trust
      score, none able to be invoked — and name the general check it implies.
      *(E.2, E.3)*
- [ ] I can list at least four costs of adding an agent, and name three
      situations where an agent should not exist at all. *(F.3, F.6)*
- [ ] I can argue both sides of specialists versus one large agent, and state
      the rule for choosing. *(G)*
- [ ] I can explain how orchestration prevents architectural decay, naming the
      four decay mechanisms and their counters. *(D.5)*
- [ ] I completed J8, J9 and J12 before reading the answers.
- [ ] **The real test:** given a project I have never seen, I can design a
      roster of four or fewer agents, state each one's question, trigger, tool
      grant and output contract, name two coverage gaps, and identify which of
      them should be a deterministic script instead. *(J12)*

If the last box is ticked, you can build with agents as an engineer rather
than as a user of them.

---

# Part N — A Closing Note on How to Talk About This Work

You will be asked how this project was built. The accurate answer, which this
chapter has evidenced rather than asserted:

> *I designed the architecture and the invariants, decomposed the work,
> defined a roster of specialist review roles with non-overlapping
> responsibilities, and integrated and verified every result. AI models acted
> as implementation assistants and as reviewers inside boundaries I set. When
> the roster missed a class of defect, I diagnosed the structural cause —
> every trigger was change-based, so nothing owned untouched code — and
> repaired the system by adding one role, amending two, and documenting a
> second trigger mode.*

Every clause of that is checkable against the repository: `CLAUDE.md` for the
orchestration, `.claude/agents/` for the roles, `bdc8308` for the diagnosis
and repair, and 233 commits whose messages record why each defect escaped.

**The skill on display is not prompting. It is decomposition, ownership
design, contract design, coverage analysis, and verification discipline** —
and those are the same skills that make someone effective on a team of
humans.

---

*Next: [05-computing-foundations.md](05-computing-foundations.md) — the ground
everything so far has been standing on: what a program, a process, a port, a
socket, a request, and a file actually are. Part 1 of the course begins, and
it assumes nothing at all.*
