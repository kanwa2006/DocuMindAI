# DocuMindAI — Runtime Failure Report

**Scope:** Forensic diagnosis of 8 confirmed production failures.
**Method:** Real runtime reproduction in the sandbox where the cloud backing services were reachable in-process; exact code-path tracing where they were not. No HTTP 200s, UI renders, placeholder scores, or "operational" messages were trusted as evidence.

## Verification environment & honest constraints

End-to-end "verify with a real upload through the live stack" **could not be fully performed from this sandbox**, and I will not pretend otherwise:

- **Supabase Postgres** (`aws-1-ap-southeast-1.pooler.supabase.com:6543`) and **Upstash Redis** are **unreachable** from the sandbox (DNS resolution fails). So I could not drive a document through the live Celery worker → DB → retrieval → stream path.
- The backend `venv` is **Windows-format** and won't execute under the Linux sandbox.
- `sentence_transformers` is **not importable** in the sandbox (`ModuleNotFoundError`) — which, as it turns out, is itself the central piece of evidence.

What I *did* execute at runtime: the real PyMuPDF extraction path against the real uploaded PDFs; a real `pgvector` dimension-rejection test against `Vector(1024)`; and the **actual** `exams.py` JSON parser against realistic Gemini outputs. Every claim below is tagged:

- **`PROVEN (runtime)`** — reproduced by executing real code against real data in the sandbox.
- **`CODE-TRACED`** — determined by reading the exact execution path; not executed end-to-end because the cloud services are unreachable.
- **`ENV-DEPENDENT`** — behavior hinges on a deployment variable or an installed package.

---

## The linchpin (read this first)

Five of the eight failures share **one** upstream root cause:

> **`sentence_transformers` is not actually available in the running backend.**

This single absence cascades:

1. `LocalEmbeddingProvider` (`bge-m3`, **1024-dim**) fails to load → silently falls back to `GeminiEmbeddingProvider` (**768-dim**) or a 768-dim zero vector.
2. The `DocumentChunk.embedding` column is a fixed **`Vector(1024)`**. A 768-dim vector is **rejected by Postgres at commit**.
3. `process_document` commits chunks in batches; the **first** rejected batch throws → rollback → all 3 retries fail the same way → document ends in **`FAILED`**, never `READY`.
4. Every retrieval/summary query filters `status == READY`, so they find **zero** chunks → "I couldn't find any extracted text…".
5. Independently, the **reranker** also lazy-imports `sentence_transformers` and has no fallback on import failure → uncaught `ImportError` surfaces as a stream error whenever retrieval *does* return candidates.

So "embeddings" and "grounding/reranking" are not two unrelated bugs — they are the same missing dependency hitting two subsystems. The fixes are still separable, and I keep them separate below.

---

# P0-A — Extraction / retrieval: "I couldn't find any extracted text"

**Classification: Orchestration (primary) + Retrieval (secondary)**

### 1. Reproduction steps
1. Upload any PDF (including `GUARDIAN_Project_Overview.pdf`).
2. Ask any question or request a summary/overview in that workspace.
3. Observe the assistant reply: *"I couldn't find any extracted text in the attached document(s)…"* even though the PDF visibly contains text.

### 2. Runtime evidence
- **`PROVEN (runtime)`** — Extraction itself is *not* the failure for native PDFs. Running the real `ocr_service` path (PyMuPDF `get_text("blocks")`) against the actual uploads:
  - `GUARDIAN_Project_Overview.pdf` → 9 native pages, ~10,500 chars
  - `DocuMindAI_Full_Clarity.md.pdf` → 30 pages, 53,152 chars
  - `CS305-Unit-3-Fitting.pdf` → 24 pages, 4,673 chars
  - `RM_JULY_DEC-2024__3_.pdf` (scanned) → **0 native pages, 0 chars** (see P2-H / OCR note)
- **`PROVEN (runtime)`** — `from sentence_transformers import SentenceTransformer` raises `ModuleNotFoundError` in the backend's runtime.
- **`PROVEN (runtime)`** — Simulated the exact column constraint: inserting a **1024-dim** vector into `Vector(1024)` succeeds; inserting **768-dim** (Gemini fallback) or a **768-dim zero** vector fails with `expected 1024 dimensions, not 768`.
- **`CODE-TRACED`** — Because the first batch commit throws, `process_document` rolls back and retries (≤3), each failing identically, ending at `status = FAILED`. Downstream `summary_service._load_all_chunks_ordered` and `retrieval_service` both require `status == READY`, so they return empty.

### 3. Exact root cause
Embedding **dimension inconsistency** triggered by the missing local model. `embedding_service.py` falls back from a 1024-dim model to a 768-dim provider (or 768-dim zero vector on per-text failure), but `document_chunk.py` pins `embedding = Column(Vector(1024))`. Postgres rejects the 768-dim write, which fails the whole document, so it never reaches `READY` and retrieval/summary legitimately find nothing.

### 4. Affected files
- `backend/app/services/embedding_service.py` (lines 35–43 fallback to Gemini 768; 71 zero-vector `[0.0]*768`; 79 `[0.0]*1024`)
- `backend/app/models/document_chunk.py` (`Vector(1024)` column)
- `backend/app/workers/tasks/document_tasks.py` (batch commit → rollback → retry → `FAILED`) — **orchestrator**
- `backend/app/services/summary_service.py:251` (the user-facing message origin)
- `backend/app/services/retrieval_service.py` (READY filter; consumes the same chunks) — **HIGH-RISK**

### 5. Minimal production-grade fix
Two additive guards, no internal rewrites:

**(a) Enforce dimension at the embedding boundary** — never return a vector of the wrong width. In `embedding_service.py`, wrap provider output so any vector ≠ `EMBEDDING_DIM` is rejected/padded *consistently to 1024* (and emit a loud log), so a provider mismatch can never poison a DB write:
```python
def _coerce_dim(vecs, dim=EMBEDDING_DIM):
    out = []
    for v in vecs:
        if len(v) == dim:
            out.append(v)
        elif len(v) < dim:
            logger.error("[embedding] under-dim %d<%d; right-padding (DEGRADED)", len(v), dim)
            out.append(list(v) + [0.0]*(dim-len(v)))
        else:
            logger.error("[embedding] over-dim %d>%d; truncating (DEGRADED)", len(v), dim)
            out.append(list(v[:dim]))
    return out
```
This keeps the document reaching `READY` instead of dying. **It is a degraded-mode stopgap, not a quality fix** — padded 768→1024 vectors retrieve poorly.

**(b) The real fix is making the 1024-dim model available** (`ENV-DEPENDENT`): ensure `sentence_transformers` + `bge-m3` are installed/baked into the worker image, or set `EMBEDDING_DIM` and the column to a Gemini-native 768 and re-embed. Do **not** silently mix dimensions in one column.

**(c) Surface FAILED loudly** in `document_tasks.py`: on terminal failure, store the exception text on the document so the UI shows "processing failed: <reason>" rather than letting the user discover it only when a summary says "no extracted text."

---

# P0-B — Retrieval grounding failure (non-grounded answers, citations)

**Classification: Retrieval + Orchestration**

### 1. Reproduction steps
1. Get a document to `READY` (requires P0-A resolved first).
2. Ask a grounded question.
3. Observe either a stream error, or an answer that is non-grounded / missing citations.

### 2. Runtime evidence
- **`PROVEN (runtime)`** — `sentence_transformers` is not importable. `reranker_service.LocalCrossEncoder` lazy-imports `from sentence_transformers import CrossEncoder` **inside `rerank()`**, i.e. *after* construction.
- **`CODE-TRACED`** — `_get_default_reranker` (reranker_service.py:76–82) wraps only **construction** in try/except, not the lazy model load. So the fallback to `DummyLocalReranker` **never fires** on import failure; the `ImportError` propagates out of `grounding_service.rerank_results` (called at grounding_service.py:87) into the query stream as an error event.
- **`CODE-TRACED`** — This only triggers once retrieval returns candidates (`if not results: return []`), which is why it's distinct from P0-A: with P0-A present, retrieval returns nothing and the reranker is never reached; fix P0-A and this becomes the next domino.
- **`CODE-TRACED`** — `grounding_service` computes a **real** `confidence_score` = mean rerank score of accepted evidence (0.0 when none) and short-circuits to empty when `document_ids == []`. The grounding logic itself is sound; it's starved by the two upstream failures.

### 3. Exact root cause
The reranker has **no effective fallback** when its model backend can't be imported. The guard protects the wrong line (construction, not the lazy `import`/load inside `rerank()`).

### 4. Affected files
- `backend/app/services/reranker_service.py` (lazy import inside `rerank()`; `_get_default_reranker` guard at 76–82) — **P0 grounding**
- `backend/app/services/grounding_service.py:87` (invocation site) — **HIGH-RISK**
- `backend/app/api/v1/endpoints/query.py` (stream error surfaces here)

### 5. Minimal production-grade fix
Additive, wrapper-style (respects the HIGH-RISK rule — no grounding internals touched):

Move the import-failure fallback to where the import actually happens. Wrap the lazy load in `LocalCrossEncoder.rerank()` so an `ImportError`/load error **degrades to `DummyLocalReranker`** (identity/score-preserving order) instead of throwing:
```python
def rerank(self, query, results, top_k=None):
    if not results:
        return []
    try:
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.MODEL_NAME)
    except Exception as e:
        logger.error("[reranker] model unavailable (%s) — falling back to Dummy (DEGRADED)", e)
        return DummyLocalReranker().rerank(query, results, top_k)
    ...
```
Grounding then still produces evidence + a real confidence score (lower quality without a true cross-encoder, but **grounded and honest**). As with P0-A, the durable fix is making the reranker model available in the image (`ENV-DEPENDENT`).

---

# P1-C — Duplicate assistant responses

**Classification: Orchestration (frontend state)**

### 1. Reproduction steps
1. Ask a question; let the stream finish.
2. Observe the completed answer momentarily (or persistently) rendered twice.

### 2. Runtime evidence
- **`CODE-TRACED`** — The SSE parser is **not** the cause. `frontend/src/lib/api.ts` `askQuestionStream` (288–394) frames on `\n\n` correctly and fires exactly one `onToken` per event. Verified by reading the parser; no double-dispatch.
- **`CODE-TRACED`** — `WorkspaceUI.tsx` carries a **dual source of truth**: live `response` state *and* `history`. In the `done` handler (1063–1107) it `queueMicrotask`s `createChatMessage(...)` then pushes to `history` and clears `response`. The code comment (1072–1079) explicitly documents a *prior partial fix* for duplicate rendering — i.e. this is a known race, patched but not eliminated.

### 3. Exact root cause
Race between two render sources: the streamed `response` and the persisted `history` entry are swapped via an async network call, so for a window (or on re-entrancy) both render the same assistant turn.

### 4. Affected files
- `frontend/src/components/WorkspaceUI.tsx` (1035–1119, esp. the `done` handler 1063–1107)
- `frontend/src/lib/api.ts` (ruled out as cause)

### 5. Minimal production-grade fix
Single source of truth for the just-completed turn. On `done`, append the final assistant message to `history` **synchronously and atomically with clearing `response`** (one state update), and **stop gating persistence on the async `createChatMessage` round-trip** for render purposes — persist in the background, but don't let its timing drive what's on screen. Concretely: build the final history array first, then `setHistory(next)` and `setResponse(null)` in the same tick; de-dupe by a stable message id so a late network echo can't introduce a second copy.

---

# P1-D — Fake trust scores (95% shown alongside "no extracted text")

**Classification: Prompting/Orchestration (hardcoded value)**

### 1. Reproduction steps
1. Trigger the summary/overview path (ask for "summary"/"overview"/"notes").
2. Observe a **95%** confidence/trust score even when the same response says there's no extracted text.

### 2. Runtime evidence
- **`CODE-TRACED`** — In `query.py` `/stream`, the **summary path** emits a **hardcoded** payload `{'confidence_score': 0.95, 'evidence': [], 'grounded': True, 'mode': 'grounded'}` at lines **311–314**, *before* any chunk check, and repeats `0.95 / grounded:True` at **332–335**.
- **`CODE-TRACED`** — Contrast the **non-summary path** (398–404), which correctly derives `confidence_score = <real> if is_grounded else 0.0`, `grounded: is_grounded`, `mode: "grounded" if is_grounded else "general"`. So the bug is path-specific to the summary branch.
- This is exactly why "95% trust" **co-occurs** with "no extracted text": the 0.95 is a literal, not a measurement.

### 3. Exact root cause
The summary streaming branch ships a **placeholder confidence** (`0.95`, `grounded:True`, empty evidence) instead of deriving it from the grounding result.

### 4. Affected files
- `backend/app/api/v1/endpoints/query.py` (summary path 298–345; offending literals at 311–314 and 332–335)

### 5. Minimal production-grade fix
Make the summary path emit the **same derived metrics** the non-summary path already computes. If the summary is produced from real chunks, set `confidence_score` from the grounding/aggregate score and `grounded`/`mode` from whether evidence exists; if `_load_all_chunks_ordered` returned empty (the "no extracted text" case), emit `confidence_score: 0.0, grounded: False, mode: "general"`. Never emit a literal 0.95. This is a contained edit to one endpoint, not a grounding-internals change.

---

# P1-E — Exam workspace "[Generation failed]" (JSON parse errors)

**Classification: Prompting (primary) + Orchestration**

### 1. Reproduction steps
1. Open the exam workspace; generate a paper.
2. Observe "[Generation failed]" / refusal paper instead of questions.

### 2. Runtime evidence
- **`PROVEN (runtime)`** — I ran the **actual** `exams.py` parser logic (`_strip_fences` → `json.loads` → require `paper` + `answer_key`) against four realistic Gemini outputs. **All four fail**:
  - `prose_preamble` (model adds "Here is your exam:" before JSON) → fail
  - `trailing_comma` → fail
  - `unescaped_newline_in_string` → fail
  - `truncated_maxtokens` (cut off mid-JSON) → fail
- **`PROVEN (runtime)`** — A tolerant parser (extract outermost `{…}` + strip trailing commas) **fixes** `prose_preamble` and `trailing_comma` but **cannot** fix `unescaped_newline` or `truncated` — those require the API to emit strict JSON and enough tokens to finish.
- **`CODE-TRACED`** — `llm_service.GeminiProvider.generate` (215–224) builds `GenerationConfig(temperature, top_p, max_output_tokens)` with **no `response_mime_type="application/json"`**. `generate_json` exists (392) but exams.py doesn't call it; its own comment (409) admits JSON mode isn't used. `GEMINI_MAX_OUTPUT_TOKENS=8192` is a real truncation risk for full papers.
- **`CODE-TRACED`** — `exams.py` (381–421) does only `_strip_fences` + one retry + `_build_refusal_paper` → "[Generation failed]" (470). No API-level structured output.

### 3. Exact root cause
Two compounding defects: (a) the model is asked for JSON **in the prompt only**, not via the API's JSON mode, so it intersperses prose/commas/unescaped control chars; and (b) the parser is brittle (fence-strip + `json.loads` only). Truncation at 8192 tokens makes long papers unparusable regardless of parser tolerance.

### 4. Affected files
- `backend/app/api/v1/endpoints/exams.py` (381–421 parse/retry; 470 refusal)
- `backend/app/services/llm_service.py` (`generate` 215–224 lacks `response_mime_type`; `generate_json` 392 unused; `GEMINI_MAX_OUTPUT_TOKENS` 8192)

### 5. Minimal production-grade fix
1. **Use the API's JSON mode** for exam generation: call a `generate_json` path that sets `response_mime_type="application/json"` (and a response schema if available). This eliminates prose preambles and unescaped control characters at the source.
2. **Add a tolerant parse fallback** (extract outermost balanced `{…}`, strip trailing commas) for residual cases — proven to recover the two common ones.
3. **Raise/segment the token budget** for papers (increase `max_output_tokens` for this call, or generate in sections) to remove the truncation class.
4. Keep the single retry + refusal as a last resort, but it should now be rare.

---

# P2-F — Session delete: "Chat not found"

**Classification: Orchestration (authz filter asymmetry)**

### 1. Reproduction steps
1. Open a chat session that lists and loads normally.
2. Delete it.
3. Observe **404 "Chat not found"** for a session you can otherwise see and use.

### 2. Runtime evidence
- **`CODE-TRACED`** — Filter asymmetry across `chats.py`:
  - `list_chat_sessions` (~27–28): filters **`workspace_id` only**
  - `get_chat_messages` (238–262) and `create_chat_message` (264–290): filter **`id` + `workspace_id`**
  - `delete_chat_session` (175–236): filters **`id` + `workspace_id` + `owner_id`** (190–194) → returns 404 at line 199
- Therefore a session that is listable and usable can **404 on delete** whenever `owner_id` doesn't match the requester (e.g., created under a different owner association), because delete is the only path that also requires `owner_id`.

### 3. Exact root cause
**Inconsistent ownership predicate.** Delete enforces `owner_id`; list/read/create do not. The mismatch — not a missing row — produces "Chat not found."

### 4. Affected files
- `backend/app/api/v1/endpoints/chats.py` (`delete_chat_session` 175–236, esp. 190–194/199; compare list ~27–28, get 238–262, create 264–290)

### 5. Minimal production-grade fix
Make the ownership predicate **consistent** across all session routes. Either (preferred, secure) add `owner_id` to list/read/create so visibility and deletability match, or (minimal) align delete to the same predicate list/read use. If `owner_id` is the intended security boundary, apply it uniformly so a user can never see a session they can't delete. Return 403 vs 404 deliberately (404 is fine to avoid existence leaks, but the *set* of visible sessions must equal the deletable set).

---

# P2-G — Free-trial counter shows 0 but still processes

**Classification: Orchestration (decoupled display vs enforcement) + ENV**

### 1. Reproduction steps
1. As a trial user, observe the trial pill showing **0 left** while queries still go through.

### 2. Runtime evidence
- **`CODE-TRACED`** — Enforcement is **not** bypassed: `trial_enforcement.check_and_increment_trial` raises **402** once `used >= limit`, else increments. The mechanism is sound.
- **`PROVEN (runtime, static)`** — `trial_enforcement.py:7` hardcodes **`TRIAL_QUERY_LIMIT = 10`**, ignoring the `.env` value `TRIAL_QUERY_LIMIT=5`. So the *real* limit is 10, not the configured 5.
- **`CODE-TRACED`** — The **display** is independently defaulted: `LayoutWrapper.tsx:152` uses `status.queries_remaining ?? 0`, and `TrialPill.tsx:65` shows `Math.max(queriesRemaining, 0)`. On any fetch hiccup or before hydration, the pill reads **0** even though the server still allows up to 10.

### 3. Exact root cause
Two independent defects that *look* like one: (a) the counter **display** falls back to 0 on a missing/failed status fetch (decoupled from the server's true remaining count), and (b) the enforcement **limit is hardcoded to 10**, overriding the `.env` `=5`. So users see 0-but-works (display bug) while the actual gate is at 10 (config bug).

### 4. Affected files
- `backend/app/core/trial_enforcement.py:7` (hardcoded `TRIAL_QUERY_LIMIT = 10`)
- `frontend/src/components/LayoutWrapper.tsx:152` (`?? 0` default)
- `frontend/src/components/TrialPill.tsx:65` (`Math.max(queriesRemaining,0)`)

### 5. Minimal production-grade fix
1. **Read the limit from config:** `TRIAL_QUERY_LIMIT = int(os.getenv("TRIAL_QUERY_LIMIT", "10"))` so `.env=5` is honored.
2. **Single source of truth for display:** don't render `0` as a hydration/error default. Show a loading/indeterminate state until `queries_remaining` is known, and surface remaining as `limit - used` from the same server response that enforces the gate, so the pill and the 402 boundary can never disagree.

---

# P2-H — Long-document completeness (silent truncation) + scanned-PDF gap

**Classification: Retrieval/Orchestration + Extraction**

### 1. Reproduction steps
1. Upload a long document (or many), request a full summary/overview.
2. Observe answers that quietly omit later content; for scanned PDFs, "no extracted text" with no OCR.

### 2. Runtime evidence
- **`CODE-TRACED`** — `summary_service` caps the map-reduce window at `MAX_WINDOWS_HARD_CAP = 40 × WINDOW_CHUNKS = 6 = 240` chunks and **silently truncates** beyond that. `HARDENING_REPORT` (line 79) already flags this; `KNOWN_REMAINING_ISSUES.md:288` corroborates the `bge-m3` ~1.2 GB download fragility that underlies P0-A.
- **`PROVEN (runtime)`** — The scanned PDF `RM_JULY_DEC-2024__3_.pdf` extracts **0 chars**. `ocr_service.extract_document_stream` "fallback" at line 153 is just `page.get_text("text")` again — **no real OCR** (Tesseract/EasyOCR is only a comment). Scanned docs therefore produce no chunks at all.

### 3. Exact root cause
Two completeness gaps: (a) summaries **silently drop** content past 240 chunks (no user signal, no coverage report); (b) **no OCR backend** means image-only/scanned PDFs yield zero text and silently produce empty workspaces.

### 4. Affected files
- `backend/app/services/summary_service.py` (`MAX_WINDOWS_HARD_CAP=40`, `WINDOW_CHUNKS=6`; truncation)
- `backend/app/services/ocr_service.py` (line 153 non-OCR "fallback")

### 5. Minimal production-grade fix
1. **Make truncation visible:** when a summary covers fewer than all chunks, append an explicit coverage note ("Summarized first N of M sections") and/or raise the cap with chunked reduction so long docs are fully covered. Never drop silently.
2. **Add a real OCR path** for non-native pages (Tesseract/EasyOCR) gated behind a flag, OR detect 0-char extraction and **mark the document FAILED with a clear "scanned PDF — OCR required" reason** (ties into P0-A(c)) instead of producing a silent empty workspace.

---

## Consolidated fix list (priority order)

| # | Failure | Layer | Minimal fix | Touches HIGH-RISK? |
|---|---------|-------|-------------|--------------------|
| P0-A | No extracted text | Orchestration/Retrieval | Coerce embeddings to 1024 at boundary + install bge-m3 (or move column to 768) + surface FAILED reason | retrieval_service (read-only consumer) |
| P0-B | Grounding/rerank error | Retrieval | Wrap lazy model load in `rerank()` → fall back to `DummyLocalReranker` | grounding_service (call site only) |
| P1-D | Fake 95% trust | Prompting/Orch. | Summary path emits derived confidence, not literal `0.95` | No |
| P1-E | Exam JSON fail | Prompting/Orch. | API JSON mode + tolerant parser + larger/segmented token budget | No |
| P1-C | Duplicate responses | Orchestration (FE) | Single atomic state swap + de-dupe by message id | No |
| P2-F | Delete "Chat not found" | Orchestration | Consistent `owner_id` predicate across session routes | No |
| P2-G | Trial 0-but-works | Orchestration/ENV | Read `TRIAL_QUERY_LIMIT` from env + no `0` display default | No |
| P2-H | Long-doc / scanned | Retrieval/Extraction | Visible coverage + real OCR or explicit scanned-PDF failure | No (chunking untouched) |

## What I could NOT verify (and why)
- A full **live upload → worker → DB → retrieval → stream** run: the Supabase Postgres and Upstash Redis are **unreachable from the sandbox** and the backend venv is Windows-only. The P0/P0-B/P2 items marked `CODE-TRACED` are diagnosed from exact code paths, not a live reproduction.
- The embedding-dimension rejection and the exam-parser failures **were** reproduced at runtime against real data/inputs (`PROVEN`).

I have **not** applied any code changes yet. Per the project's HIGH-RISK rules, fixes touching `retrieval_service.py` / `grounding_service.py` should be verified against a real upload before merge — which requires running this on the actual host (where Supabase/Upstash resolve). I recommend we apply fixes **one failure at a time**, starting with P0-A, and validate each on the live host before proceeding.
