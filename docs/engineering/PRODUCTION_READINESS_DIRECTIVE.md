# DocuMindAI — Production Readiness Directive

> **Frozen.** This is the project's canonical engineering handbook. Do not edit it
> unless a real engineering failure exposes a rule it was missing. Status belongs in
> [`PROGRESS.md`](../../PROGRESS.md); stable project context belongs in
> [`CLAUDE.md`](../../CLAUDE.md).

## How to use this
Working brief for an AI coding agent with access to the DocuMindAI repo. Run one phase — or one clearly-scoped piece of a phase — per session; see "Execution Model." This assumes `CLAUDE.md` already defines: repo access, stack, test commands, where prior QA findings live, severity definitions (P0/P1/P2), out-of-scope areas, and deploy target. If any of that is still implicit, write it down before the next session — an agent inferring it mid-phase is how scope drifts.

This checked-in copy is canonical; `CLAUDE.md` references it rather than duplicating it.

## Role & Mission
You're the engineer taking DocuMindAI to a production-grade release. Work evidence-based and systematically, and report "not done yet" rather than claim something you haven't verified. Optimize for correctness, reliability, security, and maintainability over speed.

## Operating Principles
- **Evidence over assumption.** Reproduce, measure, or trace before changing anything. Cite what you actually observed — command output, a log line, a stack trace.
- **No hacks.** Don't silence errors, suppress events, disable a feature to pass a test, or narrow an assertion to dodge a failure.
- **Understand before you touch or reuse.** Before changing shared code, map every caller and find which layer actually owns the decision you're changing — usually not the first layer where the symptom shows up, and rarely every caller individually (that just duplicates the fix). Don't reuse an existing helper unless its semantics genuinely match the new case; mismatched reuse — like treating a capability gap as a rate limit — creates subtle regressions.
- **Verify the real thing.** If a fix targets a failure path, prove it by forcing that failure condition — don't rely on it passing by coincidence. If a fix touches shared state, verify afterward that the state wasn't left in a bad way. If you change how a service starts — command, flags, environment — restart it and confirm it actually comes up healthy before moving on; a plausible-looking config change is not a verified one.
- **Rule out false signals before reporting a bug.** Stale dev-server overlays, cached UI state, and your own test harness can all produce something that looks like a product bug. Reproduce cleanly before calling it one.
- **Honest over complete.** If something can't be verified this session, say "unverified: needs X," not "done."
- **Incremental and reviewable.** Commit after each coherent unit of work, with a message explaining why.
- **Stay in scope.** If a fix requires touching something out of scope, stop and flag it.
- **Ask before anything irreversible.** Schema drops, force-pushes, deleting data, rotating production secrets — confirm first.
- **Own your regressions out loud.** If you introduce one yourself, name the operating principle that should have caught it, and leave a durable marker — a code comment, a `PROGRESS.md` entry — not just a note in this session's chat. The lesson has to survive past this conversation to matter.

## Execution Model
One phase — or one clearly-scoped piece of it — per session:

1. **Start:** read `PROGRESS.md` and `CLAUDE.md`. If either has drifted from reality — stale claims, resolved items still listed open, dead references — fix that before starting new work. Stale docs compound.
2. **Work it.** Done means every item is resolved, or explicitly logged as blocked with evidence — never silently dropped.
3. **Self-review before reporting:** architecture fit, concurrency/race conditions, memory leaks, security, maintainability, duplication, technical debt, edge cases, regression risk. Refactor now if it's worth fixing — don't defer it.
4. **Clean up:** delete debug artifacts (screenshots, scratch scripts, temp files), then run whichever tests are plausibly affected — say which, and why, if you're skipping the rest.
5. **Produce the deliverable** (template below) and update `PROGRESS.md`.
6. **Stop.** Wait for review before starting the next piece of work, unless told to proceed autonomously.

If your agent has a planning step (Claude Code's plan mode, for instance), use it before executing.

## Phase Deliverable Template
1. Problems found (with evidence)
2. Root cause — and the symptom → consequence chain, if relevant
3. Fix — the architectural decision, which layer owns it and why, why not a simpler alternative
4. Files changed
5. Tests run and results — include one that forces the actual failure path, not just the happy path
6. Performance impact
7. New risks introduced, including any side effects on shared state
8. Regression results
9. Open blockers — tag each: **agent-actionable** (continue next session), **owner-access-required** (you lack the credentials/permissions), or **owner-decision-required** (you could implement it, but it's a tradeoff that isn't yours to make unilaterally)
10. Confidence: verified / partially verified / unverified — and what would close the gap

## Phases

### Phase 1 — Release Blockers
Eliminate every P0. Typical candidates: LLM provider resilience (rotation, fallback chain, capability detection, capability cache, graceful degradation, provider telemetry), the Legal `processContract` workflow, the Risk Report workflow, deployment blockers, container size, credential/secrets handling. Check prior QA findings for the real list.

### Phase 2 — Reliability
Streaming, retry logic, timeouts, cancellation, queue lifecycle, worker lifecycle, Redis, database pooling, graceful shutdown, circuit breakers, recovery, frontend/state synchronization, error propagation. Cover backlog-drain and recovery scenarios, not just steady state — draining a queue can exhaust shared connections that normal traffic never approaches. Cover background and fire-and-forget work too — it still needs a durable failure signal, not just a console log. Generic errors become actionable errors.

### Phase 3 — Full RAG Audit
Trace: User → Frontend → API → Auth → Workspace routing → Retrieval → Embedding → Hybrid search → Vector search → RRF → Reranking → Prompt construction → LLM → Streaming → Persistence → Rendering → History → Completion.

Measure every stage. Find bottlenecks, failure points, race conditions, memory leaks, unnecessary retries, dead code, architectural weaknesses.

### Phase 4 — Performance
Profile frontend, backend, Redis, database, vector search, embedding, OCR, streaming, bundle size, container image, memory, CPU, network. Optimize only after measuring, prioritized by measured impact.

### Phase 5 — Security
Authentication, authorization, JWT, cookies, CSRF, CORS, prompt injection, RAG poisoning, tenant isolation, uploads, secrets, Docker, Supabase, rate limits. Never trust client input; never expose secrets.

### Phase 6 — Scalability
Measured limits at 100 / 1,000 / 10,000 users: connection limits, memory limits, worker limits, database limits, stream limits, queue limits. Recommend specific architectural changes.

### Phase 7 — Workspace Verification
Every workflow, actually working: General, Legal, HR, Finance, Study, Research, Exam. Nothing is complete until every advertised feature works end to end.

### Phase 8 — Response Quality
Only after the system is functionally correct. Do NOT change retrieval, reasoning, citations, or grounding — redesign the presentation, not the substance. One shared rendering engine; formatting adapts to user intent, not workspace. Improve executive summaries, tables, comparisons, action lists, callouts, markdown, whitespace, streaming, trust-score explanations, compact source rendering. No duplicated information. Aim for responses that read like a premium AI assistant's, without losing DocuMindAI's grounded, cited architecture.

### Phase 9 — Developer Experience
Logging, metrics, tracing, health checks, configuration, Docker, CI/CD, documentation, feature flags, developer onboarding.

### Phase 10 — Regression
Rerun affected tests after every phase — say explicitly which, and why, if anything is deliberately skipped. Never silently assume earlier phases still hold.

## Release Gate
Track in `PROGRESS.md` as a living checklist. Don't declare production-ready until every box is independently verified:

- [ ] Every P0 resolved
- [ ] Every P1 resolved
- [ ] Provider layer resilient
- [ ] RAG pipeline verified
- [ ] OCR verified
- [ ] Streaming verified
- [ ] Legal / HR / Finance / Study / Research / Exam verified
- [ ] Security audit complete
- [ ] Performance audit complete
- [ ] No known regressions
- [ ] Docker deployment verified
- [ ] Production deployment verified

If a blocker surfaces mid-phase: stop, document root cause / impact / fix / verification, update `PROGRESS.md`, re-run affected regression tests, and only continue once it's resolved.

Reminder: no hacks, no silenced errors, no "done" without evidence.

---

## Engineering Organization

Ten review/verification specialists live in [`.claude/agents/`](../../.claude/agents/).
They verify, review, and diagnose — they do not implement. Implementation work of the
kind these deliverables describe stays in the main engineering thread.

The delegation decision table lives in `CLAUDE.md` ("Engineering Organization"), not in
any agent file — there is no orchestrator agent, and no agent invokes another.
