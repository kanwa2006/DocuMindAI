# DocuMindAI — API Inventory & Frontend↔Backend Contract Audit

Companion to [ARCHITECTURE.md](ARCHITECTURE.md). Covers the backend endpoint surface, which endpoints the frontend actually consumes, and contract-level issues. Base path for all routes: **`/api/v1`** (mounted in `app/api/v1/api.py`). Frontend base: `NEXT_PUBLIC_API_URL` = `http://localhost:8000/api/v1`; `apiFetch(endpoint)` = `` `${API_BASE}${endpoint}` `` (endpoints start with `/`, no extra prefix).

---

## 1. Endpoint Inventory (by router)

Legend — **Consumer:** frontend function in `lib/api.ts` or component. **Status:** ✅ works · ⚠️ degraded/partial · ❌ broken · 🅢 stub/simulated.

### Auth (`/auth`, public) — `endpoints/auth.py`
| Method · Path | Purpose | Consumer | Status |
|---|---|---|---|
| POST `/auth/login` | Login (form), sets cookies | `login()` | ✅ |
| POST `/auth/register` | Register + device check | `register()` | ✅ |
| POST `/auth/logout` | Clear cookies | `logout()` | ✅ |
| POST `/auth/refresh` | Rotate access token | `apiFetch` silent refresh | ✅ |
| POST `/auth/verify-email` | OTP email verify | `verifyEmail()` | ✅ (optional gate) |
| POST `/auth/verify-email/resend` | Resend OTP | `resendVerificationEmail()` | ✅ |
| POST `/auth/forgot-password` | Send reset OTP (202 always) | `forgotPassword()` | ✅ |
| POST `/auth/verify-otp` | Validate reset OTP | `verifyResetOtp()` | ✅ |
| POST `/auth/reset-password` | Reset via OTP | `resetPassword()` | ✅ |
| POST `/auth/send-phone-otp` | Twilio phone OTP | `sendPhoneOTP()` | ⚠️ needs Twilio creds |
| POST `/auth/verify-phone` | Verify phone OTP | `verifyPhone()` | ⚠️ |

### CSRF / Health (public)
| GET `/csrf-token` | Issue CSRF cookie+token | `_fetchCsrf()` | ✅ |
| GET `/health` | db+redis liveness | infra healthcheck | ✅ |
| GET `/health/detailed` | + Gemini key status | admin | ✅ |

### Documents (`/documents`) — `endpoints/documents.py`
| GET `/documents/upload/presigned` | S3/local upload descriptor (20/min) | `uploadDocument*` | ✅ |
| POST `/documents/upload/local` | Multipart local upload (20/min) | `uploadDocumentWithProgress` | ✅ |
| POST `/documents/upload/verify` | Create row + dispatch ingest | `uploadDocument*` | ✅ |
| POST `/documents/clip` | Text clip ingest | `clipText()` | ✅ |
| GET `/documents` | List (workspace/chat filter) | `listDocuments()` | ✅ |
| GET `/documents/{id}` | Metadata | `getDocument()`, polling | ✅ |
| HEAD `/documents/{id}` · `/{id}/status` | Lightweight status | polling | ✅ |
| GET `/documents/{id}/signed-url` | 15-min HMAC URL | viewer | ✅ |
| DELETE `/documents/{id}` | Delete + purge vectors/cache | UI | ⚠️ cache purge pattern mismatch |

> Note: `documents.py` references a `serve_file` / `/files/{id}` concept via the signed URL, and `EnterpriseDocumentViewer` renders PDFs client-side.

### Query (`/query`) — `endpoints/query.py`
| POST `/query/stream` | **Main SSE RAG** (30/min) | `askQuestionStream()` | ✅ |
| POST `/query/ask` | Non-stream RAG | `askQuestion()` | ✅ |
| POST `/query/search` | Pure semantic search | — (no FE consumer) | ⚠️ unused |
| POST `/query/debug` | Debug retrieval (= ask) | — | ⚠️ unused |

### Chats / Collaboration (`/chats`, shared_router)
| GET/POST `/chats` | List/create sessions | `getChats`,`createChat` | ✅ |
| PATCH/DELETE `/chats/{id}` | Update/delete | `updateChat`,`deleteChat` | ✅ |
| PATCH `/chats/{id}/tags` | Session tags | `updateChatTags` | ✅ |
| GET/POST `/chats/{id}/messages` | Messages | `getChatMessages`,`createChatMessage` | ✅ |
| POST/DELETE `/chats/{id}/share` | Share/unshare | `shareSession`,`unshareSession` | ✅ |
| GET `/shared/{token}` | **Public** shared session | `getSharedSession()` | ✅ (unauth by design) |

### Workspaces
- **HR** `/hr/*` — see [WORKSPACES.md](WORKSPACES.md). `/hr/*/process` ✅ (registered worker). `/hr/events/processing/{id}` 🅢. No broken search (HR uses ILIKE + MiniLM).
- **Legal** `/legal/*` — `risk-report`, `compare`, `contracts`, `clauses`, `rules`, `approvals`, `audit-log` ✅ synchronous. `/legal/contracts/process` ⚠️ (worker not registered). `/legal/clauses/search` ❌ (`get_embedding`). `/legal/events/*` 🅢.
- **Finance** `/finance/*` — `ratios`, `compare`, `documents`, `findings` ✅. `/finance/process` ⚠️. `/finance/transactions/search` ❌. `/finance/events/*` 🅢.
- **Study** `/study/*` — `decks`, `quiz/generate`, `quiz/{id}/submit`, `flashcards/{id}/review`, `tutor/chat` ✅/⚠️. `/study/process` ⚠️. `/study/search` ❌. `/study/events/*` 🅢.
- **Research** `/research/*` — `projects`, `papers`, `findings`, `citations`, `gaps`, `copilot/chat` ✅/⚠️. `/research/synthesis/{id}` 🅢 (hardcoded). `/research/process` ⚠️. `/research/search` ❌. `/research/events/*` 🅢.
- **Exam** `/exams/*` — `generate/paper`, `generate/question`, CRUD, `export/docx`, `extract-tables`, `export/table[-docx]`, `save-edits` ✅. `generate/diagram` 🅢, `process/voice` 🅢.

### Billing (`/billing`)
| POST `/billing/create-order` | Razorpay order | `createRazorpayOrder` | ⚠️ needs `RAZORPAY_ENABLED` |
| POST `/billing/webhook` | HMAC-verified upgrade | Razorpay | ✅ |
| POST `/billing/upgrade` | Direct/sandbox upgrade | `upgradePlan` | ✅ (free in default sandbox) |
| GET `/billing/status` | Plan + trial counter | `getBillingStatus` | ✅ |

### Export / Reports / Retention
| POST `/export` | DOCX/report job | `exportToDocx` | ⚠️ `export_tasks` queue unconsumed |
| `/reports/*`, `/retention/*` | Scheduled reports, retention reports | admin | ⚠️ |
| `/corrections/*` | User corrections | `CorrectionModal` | ✅ |
| `/feedback/*` | Feedback capture | `FeedbackBar/Modal` | ✅ |
| `/insights/*` | Proactive insights | `ProactiveInsightsPanel` | ✅ |
| `/bookmarks/*` | Bookmarks | `BookmarkButton` | ✅ |
| `/notifications/*` | Notifications | `NotificationCenter` | ✅ |
| `/users/*` | User profile/settings | `/settings` page | ✅ |
| `/benchmark/*`, `/eval` (admin), `/admin/*` | Eval, cost, tenants, corrections dashboards | admin pages | ⚠️ |
| `ws` (websocket) | Realtime channel | — | ⚠️ low/no FE use |

---

## 2. Frontend↔Backend Contract Audit

### 2.1 Prefix convention — RESOLVED
The `docs/architecture/project-map.md` and `docs/marketing/interview-guide.md` describe ~35 frontend call sites using a doubled `${API_BASE}/api/v1/...` prefix. **Current frontend code no longer does this** — a repository-wide search finds the doubled pattern only inside the two docs (and one stale comment in `NotificationCenter.tsx`). `lib/api.ts` and components consistently use `apiFetch('/…')`. **The documentation is stale on this point; the code is correct.**

### 2.2 Broken contracts (frontend calls a backend that errors)
| Frontend | Backend | Problem |
|---|---|---|
| `searchClauses()` → `/legal/clauses/search` | `endpoints/legal.py` | `llm_service.get_embedding()` does not exist → 500 |
| `searchTransactions()` → `/finance/transactions/search` | `endpoints/finance.py` | same missing method → 500 |
| `searchStudyMaterial()` → `/study/search` | `endpoints/study.py` | same → 500 |
| `searchResearch()` → `/research/search` | `endpoints/research.py` | same → 500 |
| workspace `process*()` (legal/finance/study/research) | Celery `*_tasks` | task modules not in worker `include` → never execute (doc stuck "queued") |
| `runSynthesis()` → `/research/synthesis/{id}` | `endpoints/research.py` | returns hardcoded fake data (not an error, but not real) |

### 2.3 SSE contracts
`askQuestionStream()` parses SSE events `status`, `metadata`, `token`, `thinking_stage`, `trial_status`, `trust_report`, `error`, `done`. The backend `/query/stream` emits all of these **except `trust_report`** on the main path (only the summary path and deep-research emit trust-like data), so the `onTrustReport` callback is effectively unused for normal queries — consistent with Veritas not being wired into `/query/stream`.

### 2.4 Unused / orphan endpoints (no frontend consumer found)
- `POST /query/search`, `POST /query/debug` — superseded by `/query/stream`.
- `ws` websocket router — the product uses SSE; websocket usage is minimal/absent in the frontend.
- Portions of `benchmark`/`eval`/`retention`/`reports` are admin-only or partially wired.

### 2.5 Duplicate/parallel answer paths
Three code paths can produce an answer: `/query/stream` (SSE, no persistence), `/query/ask` (sync), and the `/chats` ask path (persists user+assistant messages, `chats.py:451-470`). The frontend primarily uses `/query/stream`; message persistence for history appears to rely on the `/chats/{id}/messages` POST wrappers. This split is a maintenance risk (two grounding invocations, potential drift).

### 2.6 Auth/validation/timeouts
- **Auth:** all non-public endpoints depend on `get_current_user` (cookie JWT). The shared-session endpoint is intentionally public via a token.
- **Validation:** Pydantic schemas cover most bodies; several endpoints take primitives as query params (`status`, `comments`, `topic`) rather than typed bodies.
- **Rate limits:** only `/query/stream` and the two upload endpoints are limited.
- **Timeouts:** no explicit server-side request timeouts on long LLM calls; the frontend uses `AbortSignal` for cancellation and a 5-minute polling timeout for document status.
- **Pagination:** `/chats` and `/chats/{id}/messages` support `limit`/`offset`; most list endpoints return unbounded result sets.

### 2.7 Contract recommendations (documentation only — not applied)
1. Add `get_embedding` to the embedding path (or route those endpoints through `embedding_service`) to unbreak the four `*/search` endpoints.
2. Register `legal/finance/study/research_tasks` on the worker or make `/process` synchronous.
3. Emit a real `trust_report` SSE event from `/query/stream` if the trust score is to be shown per response.
4. Remove or document `/query/search` and `/query/debug`; decide whether `ws` is a supported surface.
5. Consolidate the three answer paths behind one grounding call.
