# KNOWN_REMAINING_ISSUES.md — DocuMindAI

Issues the audit (sessions 1 + 2) could not fix, or deliberately deferred. Each
entry says what's left, why it was deferred, and a concrete next step.

---

## Backend

### A4 — `google.generativeai` → `google.genai` SDK migration

**State**: Deferred — STEP 5 documented this.

**Why**: CLAUDE.md says `services/llm_service.py` is wrap-only — "never rewrite
provider internals." Swapping the SDK means rewriting the `GeminiLLMProvider`
class entirely.

**Next step**: When the user is ready, create a *new* provider class
`services/gemini_genai_provider.py` that targets `google.genai`, gate the
selection in `llm_service.get_provider()` behind a setting
(`LLM_PROVIDER=gemini_legacy|gemini_genai`), and migrate one workspace at a time.

---

### E2 — Rate limits on `/query/stream` and `/documents/upload`

**State**: Login, forgot-password, reset-password are rate-limited (STEP 14).
The streaming and upload routes are not.

**Why**: `/query/stream` returns a long-lived `StreamingResponse`. The naive
`@limiter.limit("30/minute")` would count a 60-second stream as one request,
which is the right behaviour but the *opening* of the stream is what should be
limited, not the duration. Documenting before introducing subtle bugs.

**Next step**: Decorate `ask_question_stream` with `@limiter.limit("30/minute",
per_method=True)` and confirm slowapi counts the request when the route handler
returns, not when the SSE generator closes. For uploads, add
`@limiter.limit("10/minute")` on the presigned-URL request endpoint
(`/documents/upload/presigned`), not the file POST itself.

---

### E4 — OpenTelemetry `ConsoleSpanExporter` in production

**State**: Telemetry initialised but exports spans to stdout.

**Why**: The current docstring already says "In production, replace with
OTLPSpanExporter for Jaeger/Tempo/Datadog." This is a config swap, not a bug.

**Next step**: When a real OTLP backend exists, replace
`ConsoleSpanExporter()` with `OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT)`
and add the endpoint to `core/config.py`.

---

### D1 — Dead-code deletions (proposals only)

**State**: STEP 13 listed 1 backend stub + 9 frontend components with zero
references. Not deleted, per spec.

**Next step**: User reviews the list, gives the green light, then a focused
commit removes them all in one go.

Files in question:
- `backend/app/services/eval_service.py` (empty stub)
- `backend/app/services/export_service.py` (155 lines, zero imports —
  verify against deployment scripts before deletion)
- 9 frontend components (see AUDIT_REPORT.md STEP 13)

---

## Frontend

### C7 — Brand color: azure-blue → indigo-600

**State**: STEP 10 added spec-named aliases (`--accent` etc.) but kept
`--brand` at `hsl(220, 90%, 60%)` (azure). The user's spec calls for
`#4f46e5` (indigo-600).

**Why**: Flipping the brand color visually rethemes every button, focus ring,
chat bubble, and pill across the entire UI. Risky one-shot in a multi-step
audit.

**Next step**: One-line change in `tokens.css`:
```css
:root {
  --brand: #4f46e5;
  --brand-dim: #4338ca;
  --brand-ghost: rgb(79 70 229 / 0.08);
  --brand-glow: rgb(79 70 229 / 0.15);
  --brand-hue: 244;  /* indigo-600 hue */
}
```
Visually verify dark mode contrast after change.

---

### C8 — Inter font substitution

**State**: Spec asked for "Inter or system-ui"; current is `DM Sans` (humanist
sans, loaded via `next/font`).

**Why**: DM Sans already loads via `next/font`, switching to Inter adds a
font-load round-trip with no functional gain. Both are in the same family.

**Next step**: If brand consistency demands Inter, replace the import in
`app/layout.tsx`:
```ts
import { Inter, Source_Serif_4 } from 'next/font/google';
const inter = Inter({ ... variable: '--font-body-loaded', subsets: ['latin'] });
```
Spec also asks for Source Serif for marketing headings; currently we use
Instrument Serif — the substitution is cosmetic.

---

### C10 — Persist `mode` on past assistant ChatMessage rows

**State**: STEP 11 wired no-document mode for active streams. The
`Ungrounded` pill shows on the streaming response. History (`ChatMessage`
rows) does not store `mode`, so on chat reload past ungrounded answers
do not get the pill.

**Why**: Adding a column means an alembic migration and ChatMessage schema
change. Out of scope for a typography/UX pass.

**Next step**:
1. Add `mode VARCHAR(16) NULL` to `ChatMessage` model.
2. Generate migration: `alembic revision --autogenerate -m "add chatmessage_mode"`.
3. Write `mode` from `query.py` /stream when persisting the assistant
   message.
4. Read `mode` in `MemoizedMessage.tsx` and render the pill.

---

### BF3 — Avatar initials vs workspace pill

**State**: Spec said the avatar showed the workspace slug ("exam") instead of
initials ("DU"). The code already renders `user.initials = "DU"` (LayoutWrapper.tsx:257).
The "exam" the user saw was the workspace pill *inside* the dropdown panel,
not the circle.

**Why**: No bug present. Spec misread the screenshot.

**Next step**: None.

---

### Frontend dead-component deletion

**State**: STEP 13 listed 9 unused components. Not deleted.

**Next step**: User confirms which (if any) are safe to remove, then a
single commit drops them.

---

## Cross-cutting

### Phase 3 — Manual smoke tests still needed

The audit was static. Recommended manual checks (in this order):

1. **Auth flow**: register → email verify → login → land on /general.
2. **Trial quota**: open settings, confirm `10` is shown; ask 10 questions
   in the chat; on the 11th attempt, the UpgradeModal opens and is
   dismissable.
3. **Forgot password**: hit /forgot-password → check Redis or backend logs
   for the token (no SMTP in dev) → /reset-password?token=… → set a new
   password → log in.
4. **No-document mode**: open any workspace fresh, ask "What is 2+2?" —
   should answer with the `Ungrounded` pill and the C10 banner.
5. **Mobile**: resize browser to 375 px; sidebar slides; UpgradeModal X
   reachable; chat input sticky at bottom.
6. **Dark mode**: toggle theme; verify the workspace dot and the dismissable
   disclaimer banner both render correctly.
7. **Document upload**: drag-drop PDF → ready → chip appears in chat input
   bar → ask → grounded answer with citations.
8. **Workspace switch**: change workspace via the dropdown; the dot colour
   updates; the rest of the UI does not change colour (no UI wash).

### Phase 3 — What was not audited
- The `Veritas` engine (STABLE, untouched).
- Celery automation tasks (auto_health_check etc., STABLE).
- Vector store / pgvector schema (no changes needed).
- HR / Legal / Finance domain logic (worked correctly per the slug→UUID fix in STEP 3).

---

Last updated: critical-bug-sweep session 4 (2026-05-23).

---

## Updates from deep debug session 3

### Resolved this session
- **A1**: Email verification policy now coherent — register sets
  `email_verified=true`, query no longer gates on it, frontend skips OTP.
- **C7 brand color**: actually flipped (azure-blue → neutral greyscale,
  ChatGPT-style). Pulls open the prior C7 "deferred" item.
- **C8 font**: DM Sans → Inter (next/font/google).
- **D1 (frontend deletion list)**: 9 components deleted.
- **Backend eval_service.py / export_service.py**: deleted.
- **Pydantic orm_mode warnings**: silenced (from_attributes).

### New deferred items

#### E7 — Supabase Storage bucket cap may block 200 MB uploads

**State**: Backend, frontend, copy all bumped to 200 MB. Local-disk
storage adapter has no cap. Supabase Storage **default object size**
on the free tier is 50 MB; paid tiers default to 5 GB. If
`STORAGE_PROVIDER=supabase` in prod, raise the bucket policy too.

**Next step**: Supabase dashboard → Storage → bucket → set
`max_object_size = 209715200` (200 MB). Alternatively `supabase
storage set-policy <bucket> --max-size 200MB` via CLI.

#### C10 (carry-over) — Persist `mode` on past ChatMessage rows

Still deferred from session 2. Streaming responses correctly show the
`Ungrounded` chip; opening a past chat does not because `ChatMessage`
has no `mode` column. One alembic migration away.

#### Pre-existing stale Next.js build artefact

`.next/types/validator.ts:150` references `src/app/page.js` which
doesn't exist (the file is page.tsx). Same artefact was noted in
session 2 STEP 15. Harmless — `npx tsc --noEmit` reports it but it's
a build cache, not source. Cleared on next `rm -rf .next` + rebuild.

---

## Updates from critical-bug-sweep session 4 (2026-05-23)

### Resolved this session

- **P1** — `user_obj` NameError in `query.py` event_generator fixed.
- **P3** — Documents reach READY: always-dispatch +
  STORAGE_PATH-relative absolute writes.
- **P4** — Send toast spam silenced; inline "Document processing…" hint
  added.
- **P5** — three `useState(() => fn())` → `useEffect` conversions
  (Legal, Finance, TrustScore).
- **P6** — VoiceInputButton `<select>` rendered client-only via
  `mounted` flag.
- **P7** — duplicate `<Toaster>` removed; one global Toaster in
  `app/layout.tsx`.
- **P9** — every WORKSPACE_ACTIONS chip wired (11 ex-no-ops).
- **W1** — `Go ₹799 / Plus ₹999 / Pro ₹2,999` rendered from single
  `lib/pricing.ts` source; backend `/billing/upgrade` accepts new
  vocabulary alongside legacy.
- **W2** — workspace welcome titles + quick actions rewritten in
  ChatGPT-style plain language.
- **V2 stragglers** — hardcoded indigo / azure (#4f46e5, #6366f1,
  #2563eb) removed from forgot/reset-password buttons, /not-found 404,
  CandidateRankingsPanel STAGE_COLORS, shared/[token], NotificationCenter.

### New deferred items

#### Real Razorpay / Stripe checkout

The `/billing/upgrade` endpoint flips the `User.plan` column to the
requested string and reloads. There is no actual payment integration
yet — clicking "Upgrade to Plus" in dev grants Plus access for free.
For production, replace the direct DB write with a Razorpay/Stripe
webhook handler that:
1. Creates a payment order.
2. Returns the checkout URL to the frontend (frontend redirects).
3. Receives a webhook on success and *then* sets `User.plan` /
   `subscribed_at` / `subscription_ends_at`.

`billing.py:upgrade_plan`'s docstring already flags this ("In
production: validate Razorpay/Stripe webhook instead of direct call.").

#### Plan tier semantics in backend

UI shows Go / Plus / Pro as distinct tiers, but the backend currently
treats them identically (no per-plan quota differences, no per-plan
feature gating). The trial gate is the only quota enforced
(`TRIAL_QUERY_LIMIT = 10` for `plan == 'trial'`). When monetization
matters, extend `core/trial_enforcement.py` (or a new
`plan_enforcement.py`) with per-tier rules — e.g. Go = 200 queries/mo,
Plus = unlimited, Pro = unlimited + multi-user.

#### Worker first-upload latency (model download)

First upload on a fresh machine downloads BAAI/bge-m3 (~1.2 GB) inside
the worker. The user sees the doc stuck in PROCESSING for several
minutes with no progress indicator. P4's "Document processing…" dot
now keeps the input usable, but a small "first upload may take a
moment — downloading the embedding model" hint would be friendlier.
Could be inferred from the first call to `embedding_service.generate_embeddings`.

---

## PART 6 — Teacher rich editor: Phase 2 + Phase 3 design (deferred)

Phase 1 (built in this session, see `frontend/src/components/EditablePaperPanel.tsx`):
- contentEditable side-panel that wraps the generated paper.
- Minimal toolbar: bold / italic / underline · H2 / H3 / P · UL / OL · undo / redo.
- Save → `POST /exams/{exam_id}/save-edits` writes the free-form
  content blob (`edited_html` alongside the original `paper` structure).
- Export DOCX uses the existing `GET /exams/{exam_id}/export/docx` flow.

### Phase 2 — image upload + positioning

Goal: teacher can attach images (diagrams, scanned figures) to specific
questions, dragging or resizing them inline.

Sketch:
1. Add an image picker to the toolbar that calls a new endpoint
   `POST /exams/{exam_id}/upload-image` — returns a signed URL keyed
   to the exam. Backend stores images under
   `STORAGE_PATH/exam_images/{exam_id}/{uuid}.{ext}` and references them
   by URL.
2. Toolbar button inserts `<img src="…">` at caret; minimal CSS resize
   handles via `resize: both; overflow: auto;` on a wrapping `<span>`.
3. The DOCX exporter (`ExportEngine.generate_exam_docx`) currently
   walks `paper.sections[].questions[]`. To honour edited HTML it
   needs a small `html2docx` pass — `python-docx`'s `add_picture` for
   inline images. Reuse the same flow as Question Bank exports.
4. Backend rate-limit per exam (5 image uploads / minute) to keep
   storage costs bounded for free-tier users.

Effort: ~2 days. Risk: medium — DOCX image positioning is fiddly.

### Phase 3 — AI-generated images from text (e.g. "Romania map")

Goal: teacher selects text or pastes a description; an "AI image" button
generates a diagram and inserts it.

Sketch:
1. Pick a single image-generation provider. Recommended:
   `google-genai` Gemini `models.generate_images` (already aligned with
   the LLM provider abstraction). Cost: ~ $0.04 / image at 1024×1024.
2. Toolbar button opens a dialog: prompt textarea + "Generate" button →
   `POST /exams/generate/image { prompt }` → returns a URL or base64
   blob. Editor inserts as `<img>` (re-uses Phase 2's image plumbing).
3. Caching: hash(prompt) → URL in Redis so the same diagram isn't
   regenerated across reloads.
4. Cost guard: free-tier 5 images / day; Plus 50; Pro 500. Add the
   counter to `core/trial_enforcement.py` alongside the query quota.
5. Safety: Gemini image-generation already enforces content filters;
   plumb the refusal cleanly into the editor so the user sees why.

Effort: ~3 days. Risk: medium — billing + caching are the long pole.

**Order of operations**: Phase 2 first (image upload is a hard
dependency for Phase 3's insertion path).
