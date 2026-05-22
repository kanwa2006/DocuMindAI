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

Last updated: deep debug session 3 (2026-05-22).

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
