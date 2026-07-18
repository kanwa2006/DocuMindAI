# DocuMindAI — Dependency Graph & Engineering Handbook

> **Purpose:** the permanent map of how DocuMindAI fits together — structure, call chains, data model, workers, external services, env vars, execution flows, import graph, change-impact, and a knowledge graph. Paired with [DEBUG_MASTER_PLAN.md](DEBUG_MASTER_PLAN.md) (what to fix) this lets another model repair the project without rediscovering the architecture.
> **Verification:** derived from direct source inspection and re-verified anchors. Where a relationship is inferred from usage rather than read line-by-line, it is marked *(inferred)*.
> **Scope note:** `.agents/skills/**` is third-party design tooling checked into the repo and is **not** part of the application.

---

## 1. Application Structure (top level)

```
┌───────────────────────────────────────────────────────────────────────┐
│ FRONTEND  (Next.js 16 App Router, React 19, TS, Tailwind 4)          │
│  src/app/* pages → components/WorkspaceUI + panels                    │
│  src/lib/api.ts (apiFetch, SSE, CSRF, fingerprint, refresh)          │
└───────────────┬───────────────────────────────────────────────────────┘
                │ HTTPS: REST + SSE, cookies (token, csrf_token), X-CSRF-Token, X-Device-ID
┌───────────────▼───────────────────────────────────────────────────────┐
│ BACKEND  (FastAPI, async SQLAlchemy)  app/main.py → api/v1/api.py      │
│  Middleware → Routers → Endpoints → Services → Models                 │
│  Producers: *.delay() → Celery                                        │
└───────┬───────────────────────────────────────────┬───────────────────┘
        │                                           │
┌───────▼─────────────┐                   ┌─────────▼─────────────────────┐
│ WORKERS (Celery)    │                   │ DATA LAYER                    │
│ workers/celery_app  │                   │ PostgreSQL16 + pgvector       │
│ tasks/* + automation│                   │ PgBouncer · Redis7 · Storage  │
└───────┬─────────────┘                   └───────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────────┐
│ EXTERNAL: Gemini · bge-m3 · cross-encoder · Tavily · Razorpay ·        │
│           SendGrid/Brevo · Twilio · Sentry · PostHog · OTel/Prometheus │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 2. Frontend Dependency Graph

### 2.1 Pages (`frontend/src/app`) → what they render
| Route | File | Renders / calls |
|-------|------|-----------------|
| `/` (marketing) | `(marketing)/page.tsx`, `(marketing)/layout.tsx` | Landing |
| `/login` | `login/page.tsx` | `login()` |
| `/register` | `register/page.tsx` | `register()`, device fingerprint |
| `/verify-email` | `verify-email/page.tsx` | `verifyEmail()`, `resendVerificationEmail()` |
| `/forgot-password`,`/reset-password` | resp. pages | `forgotPassword/verifyResetOtp/resetPassword` |
| `/dashboard` | `dashboard/page.tsx` | overview |
| `/general`,`/hr`,`/legal`,`/finance`,`/study`,`/research`,`/exam` | `<ws>/page.tsx` | **all →** `<WorkspaceUI workspaceType="<ws>"/>` |
| `/sessions` | `sessions/page.tsx` | `getChats`, session mgmt |
| `/bookmarks` | `bookmarks/page.tsx` | `/bookmarks/*` |
| `/account`,`/settings` | resp. | `/users/*`, prefs |
| `/billing`,`/pricing` | resp. | `getBillingStatus`,`upgradePlan`,`createRazorpayOrder` |
| `/admin/{cost,eval,tenants,corrections}` | admin pages | `/admin/*`, `/eval`, `/corrections` |
| `/shared/[token]` | shared page | `getSharedSession()` (public) |
| `/privacy`,`/terms`,`/not-found`,`/sitemap.ts` | static/meta | — |

### 2.2 Central component: `WorkspaceUI.tsx`
`WorkspaceUI` is the shared shell for all 7 workspaces. It composes:
- **Chat/stream:** `askQuestionStream()` (SSE) · `getChats/createChat/getChatMessages/createChatMessage`
- **Uploads:** `uploadDocumentWithProgress` / `uploadDocument` / `clipText` · `pollDocumentStatus`
- **Panels (conditional by workspace):** `ProactiveInsightsPanel`, `CandidateRankingsPanel` (HR), `LegalRiskPanel` (Legal), `FinanceRatioPanel` (Finance), `ResearchGapsPanel`/`ResearchCitationModal` (Research), `PaperConfigPanel`/`EditablePaperPanel` (Exam), `veritas/TrustScorePanel`, `veritas/TrustScoreBadge`
- **Shared UI:** `Sidebar`, `CommandPalette`, `EnterpriseDocumentViewer`/`DocumentPreviewPanel`, `NotificationCenter`, `FeedbackBar`/`FeedbackModal`, `CorrectionModal`, `ShareSessionModal`, `UpgradeModal`, `TrialPill`, `ComparisonToggle`, `BookmarkButton`, `AutosaveIndicator`, `clips/ClipBar`+`ClipModal`, `voice/VoiceInputButton`, `KeyboardShortcutsModal`, `OnboardingProgress`/`OnboardingTooltip`, `PomodoroTimer` (Study), `teacher/TableExtractionPanel` (Exam)

### 2.3 Hooks / providers / stores / utils
| Kind | File | Role |
|------|------|------|
| Hook | `hooks/useOnboarding.ts` | onboarding steps |
| Hook | `hooks/useVoiceInput.ts`, `useVoiceReadback.ts`, `useSelectionClip.ts` | voice + selection clip |
| Hook | `hooks/useSessionExpiry.ts` | reacts to `session:expired` event |
| Hook | `hooks/useTheme.ts` | theme |
| Provider | `components/AnalyticsProvider.tsx` | PostHog init |
| Provider | `components/LayoutWrapper.tsx` | app shell |
| Store | `lib/store/trialStore.tsx` | Zustand trial state (reacts to `trial:exhausted`) |
| Util | `lib/api.ts` | all API + SSE + CSRF + fingerprint + refresh |
| Util | `lib/analytics.ts`, `lib/pricing.ts` | analytics, pricing |
| Middleware | `src/middleware.ts` | route protection |
| Error | `components/ErrorBoundary.tsx`, `SessionExpiredOverlay.tsx` | resilience |
| PWA | `public/manifest.json`, `public/sw.js`, `PWAInstaller.tsx` | PWA |

### 2.4 Frontend → Backend call chain (canonical)
```
Page (/legal)
  └─ WorkspaceUI(workspaceType="legal")
       ├─ askQuestionStream()      → POST /api/v1/query/stream   (SSE) → endpoints/query.py:ask_question_stream
       ├─ uploadDocumentWithProgress → GET /documents/upload/presigned → POST /documents/upload/local → POST /documents/upload/verify → document_tasks.process_document
       ├─ LegalRiskPanel → processContract() → POST /legal/contracts/process → legal_tasks.process_contract_batch  ⚠️(worker unregistered: C-2)
       ├─ LegalRiskPanel → (risk report) → POST /legal/contracts/{id}/risk-report → llm_service.generate (sync, works)
       └─ searchClauses() → GET /legal/clauses/search → ❌ llm_service.get_embedding (missing: C-1)
```
All requests go through `apiFetch` → `${NEXT_PUBLIC_API_URL}${endpoint}` (base already includes `/api/v1`). CSRF token + device id are attached automatically; 401 triggers one silent `/auth/refresh` retry.

---

## 3. Backend Dependency Graph

### 3.1 Middleware order (`main.py`)
`CORS → CorrelationId → SecurityHeaders → CSRF → TenantContext → DeviceFingerprint → (OTel/Prometheus)` → router `/api/v1`.

### 3.2 Router → Endpoint → Service → Model → Task → External
| Router (prefix) | Key endpoints | Services used | Models | Celery task | External |
|-----------------|---------------|---------------|--------|-------------|----------|
| `auth` | login/register/refresh/verify/reset/phone | `core.security`, `email_service`, (Twilio) | User, UserRole | — | SMTP, Twilio |
| `csrf` | csrf-token | — | — | — | — |
| `health` | health, health/detailed | `llm_key_rotation` | — | — | Postgres, Redis, Gemini |
| `documents` | presigned/local/verify/clip/list/get/delete/signed-url | `document_service`, `storage`, `extraction_router` | Document, DocumentPage, DocumentChunk | `document_tasks.process_document`, `process_clip_document` | Storage, (Qdrant delete) |
| `query` | stream/ask/search/debug | `grounding_service`→`retrieval_service`→`reranker_service`/`embedding_service`, `llm_service`, `summary_service`, `language_detector`, `response_schemas`, `trial_enforcement` | ChatMessage, Document | (reads) | Gemini, Redis cache |
| `chats` + `shared_router` | CRUD, messages, tags, share, `/shared/{token}` | — | ChatSession, ChatMessage, ReportShare | — | — |
| `hr` | jobs, candidates/process, analytics, csv, notes, stage, score | `llm_service`, `pii_redactor`, MiniLM (inline) | JobRole, CandidateProfile, JobMatch, CandidateNote, Interview | `hr_tasks.process_resume_batch` ✅ | Gemini, sentence-transformers |
| `legal` | rules, contracts/process, risk-report, compare, clauses, approvals, clauses/search, audit-log | `llm_service` | Contract, Clause, ComplianceRule, RedlineSuggestion, ApprovalWorkflow, LegalAnalysis, LegalAuditLog | `legal_tasks.process_contract_batch` ⚠️ | Gemini |
| `finance` | process, ratios, compare, documents, findings, transactions/search | `llm_service`, `financial_table_extractor` | FinancialDocument, Transaction, AuditFinding, FinancialRule, ExtractionAudit | `finance_tasks.process_finance_batch` ⚠️ | Gemini |
| `study` | process, decks, flashcards, quiz/generate+submit, review, tutor/chat, search | `llm_service`, `sm2_service` | StudyNote, FlashcardDeck, Flashcard, StudyQuiz, QuizAttempt | `study_tasks.process_study_batch` ⚠️ | Gemini |
| `research` | projects, papers, findings, process, citations, gaps, synthesis, copilot/chat, search | `llm_service`, `deep_research_agent`, `veritas_engine` | ResearchProject, ResearchPaper, ResearchFinding, ContradictionReport | `research_tasks.process_research_batch` ⚠️ | Gemini, **Tavily** |
| `exams` | generate/paper+question+diagram, CRUD, export/docx, extract-tables, export/table, save-edits, process/voice | `retrieval_service`, `llm_service`, `export_engine`, `table_extractor`, `pdf_extractor` | ExamPaper, ExamVersion | (sync; `audio_tasks` for voice) | Gemini, Docling/PaddleOCR (table) |
| `export` | create export job | `export_engine`, `audit_export` | ExportJob, ReportShare | `export_tasks.*` ⚠️(queue unconsumed) | — |
| `billing` | create-order, webhook, upgrade, status | `trial_enforcement` | User | — | **Razorpay** |
| `insights` | list/ack | `proactive_insights` | ProactiveInsight | (produced by `document_tasks`) | Gemini |
| `bookmarks`/`notifications`/`users`/`feedback`/`corrections`/`retention`/`reports`/`benchmark`/`eval`/`admin` | resp. | `feedback_service`, `evaluation_service`, `tenant_guard`, `cost_guard_service`, `report_tasks`, `eval_tasks` | Bookmark, Notification, User, Feedback, Correction, CorrectionNote, ScheduledReport, BenchmarkRun, EvalBenchmarkQuery, EvalResult, Org | `report_tasks`, `eval_tasks` | — |
| `ws` | websocket | — | — | — | — (⚠️ unused: L-7) |

### 3.3 Core services (`app/services`) — dependency directions
```
grounding_service ─┬─→ retrieval_service ─┬─→ embedding_service ─→ (bge-m3 | Gemini emb | zero)
                   │                       └─→ (pgvector SQL | NumPy in-mem)   ← VECTOR_BACKEND
                   └─→ reranker_service ──→ (cross-encoder | DummyLocalReranker)
llm_service ──→ llm_key_rotation ──→ Gemini
query endpoint ──→ grounding_service + llm_service + summary_service + language_detector + response_schemas + trial_enforcement
document_tasks ──→ ocr_service + chunking_service + embedding_service + storage
deep_research_agent ──→ (retrieval_service.query ❌C-5) + veritas_engine + llm_service + Tavily
ocr_orchestrator ──→ Docling + PaddleOCR   (only referenced by ocr_tasks — dead on ingest: C-3)
```

### 3.4 Core infra modules (`app/core`)
`config` (Settings), `auth` (JWT verify), `security` (bcrypt + token mint), `middleware` (CSRF/Tenant/Device), `rate_limiter` (SlowAPI), `circuit_breaker`, `telemetry` (OTel/Prom), `storage` (Local/S3 factory), `workspace` (`resolve_workspace_id`), `trial_enforcement`, `gemini_env` (key bridge), `json_logger`/`logging`. DB: `db/session` (async `asyncpg` + sync `psycopg2`), `db/base`, `db/base_class`.

---

## 4. Database Dependency Graph

### 4.1 Tables (~50) and key relationships
*(FKs marked (inferred) are derived from endpoint join/filter usage.)*

**Identity/tenancy**
- `users` (id, email, plan, trial_queries_used, workspace_id=slug, preferred_language, email_verified, phone…, subscribed_at, subscription_ends_at)
- `organizations`, `user_roles`, `organization_users` → users/orgs (RBAC)

**Documents & RAG core**
- `documents` (id, filename, storage_path, file_hash, mime_type, size_bytes, status[enum], owner_id→users, workspace_id[UUID], chat_session_id→chat_sessions, content_hash, source)
- `document_pages` (document_id→documents, page_number, extracted_text, layout_metadata)
- `document_chunks` (document_id→documents, page_id→document_pages, chunk_index, text_content, chunk_metadata, **embedding Vector(1024)**)

**Chat/collaboration**
- `chat_sessions` (id, owner_id, workspace_id[UUID], workspace_type, title, is_pinned, is_archived, tags, share_token, share_permissions)
- `chat_messages` (session_id→chat_sessions, role, content, created_at)
- `pinned_session`, `report_shares`, `message_notes`, `saved_query_templates`, `bookmarks`, `notifications`, `feedback`, `corrections`, `correction_notes`, `proactive_insights`, `scheduled_reports`, `export_jobs`, `benchmark_runs`, `eval_benchmark_queries`, `eval_results`

**HR:** `hr_job_roles` ← `hr_job_matches` → `hr_candidates` ← `hr_candidate_notes`; `hr_interviews`. (JobMatch.job_id→JobRole, JobMatch.candidate_id→CandidateProfile) *(inferred from joins)*
**Legal:** `legal_contracts` ← `legal_clauses`(embedding) ← `legal_redlines`; `legal_approvals`, `legal_compliance_rules`, `legal_analyses`, `legal_audit_log`, `extraction_audit`. (Clause.contract_id→Contract) *(inferred)*
**Finance:** `finance_documents` ← `finance_transactions`(embedding); `finance_audit_findings`, `finance_rules`. (Transaction.financial_doc_id→FinancialDocument) *(inferred)*
**Study:** `study_notes`(embedding), `study_flashcard_decks` ← `study_flashcards`(embedding), `study_quizzes` ← `study_quiz_attempts`. (Flashcard.deck_id→Deck) *(inferred)*
**Research:** `research_projects` ← `research_papers`(embedding) ← `research_findings`(embedding); `research_contradictions`. (Finding.paper_id→Paper) *(inferred)*
**Exam:** `exam_papers` ← `exam_versions`. (ExamVersion.exam_id→ExamPaper)

### 4.2 Indexes / vector indexes
- `document_chunks.embedding` is `Vector(1024)` (pgvector). Domain tables (`legal_clauses`, `finance_transactions`, `study_flashcards`, `study_notes`, `research_findings`, `research_papers`) also declare embedding columns.
- GIN index migration on display name (`5e6f70809102_add_display_name_gin_index`); FTS uses `to_tsvector('english')` at query time (functional, not necessarily a stored index).
- ⚠️ No explicit ANN (IVFFlat/HNSW) index migration observed → pgvector queries would do exact scans; combined with the `faiss`-default NumPy path (H-1), retrieval is unindexed today.
- RLS enabled by `2b3c4d5e6f70_add_rls_user_isolation` and `e253f70b7e95_enable_rls_documents`.

### 4.3 Migrations (Alembic, 55 files) — notable chain
`4c212bc07626_initial_schema` → `314e3009bc29_add_vector_column` → `33229a9d2798_document_chunk` → `72177cce8149_document_page` → per-workspace models (`2213…hr`, `07c651…legal`, `1234…finance`, `94fa…study`, `3cfcd…research`, `b636…exam`) → vectors (`8ec2…hr_vector`, `0f62…finance_vector`, `416d…study_vectors`) → `a1b2c3d4e5f7_resize_chunk_embedding_to_1024` → RBAC/RLS (`14f4…org_rbac`, `2b3c…rls`, `e253…rls_documents`) → eval/benchmark/retention/corrections/insights/bookmarks/notifications → **merge heads** (`2a94…`, `2245…`, `c4440…`, `ef358…`). Several explicit merges → branchy history (see QUALITY_AUDIT).

---

## 5. Workers Dependency Graph

### 5.1 Task registry vs routing vs consumption
| Task module | Task(s) | Registered (`include`)? | Routed to | Consumed by compose worker (`-Q main-queue,celery`)? |
|-------------|---------|:-----------------------:|-----------|:-----------------------------------------------------:|
| `document_tasks` | process_document, process_clip_document, generate_proactive_insights_task | ✅ | default (`celery`) | ✅ |
| `hr_tasks` | process_resume_batch, flag_stale_reviews | ✅ | `main-queue` | ✅ |
| `legal_tasks` | process_contract_batch | ✅ (C-2 fix) | `main-queue` | ✅ |
| `finance_tasks` | process_finance_batch | ✅ (C-2 fix) | `main-queue` | ✅ |
| `study_tasks` | process_study_batch | ✅ (C-2 fix) | `main-queue` | ✅ |
| `research_tasks` | process_research_batch | ✅ (C-2 fix) | `main-queue` | ✅ |
| `email_tasks` | (email) | ❌ | (default) | ❌ (mostly unused; email sent sync) |
| `export_tasks` | export jobs | ✅ | `export_queue` | ✅ (H-3 fix: `-Q` expanded) |
| `ocr_tasks` | extract_document_ocr | ✅ | `ocr_gpu_queue` | ✅ (H-3 fix: `-Q` expanded) |
| `audio_tasks` | audio/voice | ✅ | (default) | ✅ |
| ~~`embedding_tasks`~~ | — | — | — | route removed (H-3 fix — module never existed) |
| ~~`retrieval_tasks`~~ | — | — | — | route removed (H-3 fix — module never existed) |
| `automation.auto_*` (7) | scheduled | ✅ | default | ✅ if consumed, but **no Beat to schedule** (H-2) |

\* phantom routes referencing nonexistent modules (H-3).

### 5.2 Producers → tasks
- `documents.py verify_upload` → `process_document.delay` ; `documents.py clip_text` → `process_clip_document.delay`
- `document_tasks.process_document` → `generate_proactive_insights_task.delay` (fire-and-forget)
- `hr.py` → `process_resume_batch.delay` ; `legal/finance/study/research .py` → `process_*_batch.delay` (⚠️ unconsumed)
- `export.py` → `export_tasks.*` (⚠️ unconsumed)
- Beat schedule → `automation.*` + `hr_tasks.flag_stale_reviews` (⚠️ no Beat)

### 5.3 Retry / dead-letter
- `process_document` / `process_clip_document`: `self.retry(exc, countdown=2**retries, max_retries=3)`, pre-check `retries>=3` → status `FAILED` (dead-letter), `db.rollback()` on error.
- `hr_tasks.process_resume_batch`: `max_retries=3`.
- LLM layer: `_execute_with_rotation` retries across keys (`2×len(keys)`), model fallback on 404.
- No global DLQ queue; failure is represented by `Document.status=FAILED`.

---

## 6. External Services — purpose / init / config / env / usage / failure / fallback

### Google Gemini (generation)
- **Purpose:** grounded answer generation, structured extraction (legal/finance/exam/research), summaries.
- **Init:** `GeminiKeyRotator` (`llm_key_rotation.py`) reads `os.environ`; `GeminiLLMProvider` configures `genai`.
- **Config/env:** `GEMINI_API_KEY_1..N` (+ legacy `GEMINI_API_KEY`, `GEMINI_API_KEYS`), `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`, temp/top_p/max_output; bridged by `core/gemini_env.bridge_gemini_keys()`.
- **Backend usage:** `llm_service` everywhere. **Frontend:** none (via backend).
- **Failure mode:** 429→cooldown 300s; 403→permanent skip; 500/503→30s; 404→model fallback; empty parts→`_safe_extract_text`.
- **Fallback:** `DummyLLMProvider` only if `ENVIRONMENT=test`; otherwise **fail loud** (H-7 import-time).

### bge-m3 (embeddings, primary) / Gemini text-embedding-004 (fallback)
- **Purpose:** document + query embeddings (1024-dim). **Init:** `LocalEmbeddingProvider` (sentence-transformers). **Usage:** `embedding_service` in `document_tasks` + `retrieval_service`.
- **Failure/fallback:** bge-m3 fail → Gemini 768→zero-pad→1024 → zero vectors (M-4, silent).

### cross-encoder ms-marco-MiniLM-L-6-v2 (reranker)
- **Purpose:** rerank retrieval shortlist. **Config:** `RERANKER_PROVIDER=local`. **Usage:** `reranker_service` in `grounding_service`.
- **Failure/fallback:** `DummyLocalReranker` fabricated scores (M-10, silent).

### all-MiniLM-L6-v2 (HR JD scoring)
- **Purpose:** JD↔resume similarity (384-dim). **Init:** inline in `endpoints/hr.py`. **Failure:** falls back to `fit_score` only (L-8 dual-model smell).

### Tavily (web search, Research)
- **Purpose:** fill knowledge gaps in deep research. **Init:** `deep_research_agent._get_tavily()` → `TavilyClient(api_key=settings.TAVILY_API_KEY)` (⚠️ `TAVILY_API_KEY` not in Settings). **Failure:** logs + returns None → web step skipped. **Note:** upstream doc-RAG step broken (C-5).

### PaddleOCR + Docling (OCR)
- **Purpose:** scanned/handwritten (Paddle) + structured/tables (Docling). **Init:** lazy singletons in `ocr_orchestrator.py` (Paddle `use_gpu=True`). **Usage:** only `ocr_tasks` (dead on ingestion — C-3) and `exams/extract-tables` (via `table_extractor`). **Failure/fallback:** `"MOCK"` if not installed; validation gateway thresholds.

### PostgreSQL + pgvector
- **Purpose:** primary store + vectors. **Init:** async `asyncpg` (`async_database_url`), sync `psycopg2` (`sync_database_url` normalizes `ssl`→`sslmode`). **Env:** `DATABASE_URL` or `POSTGRES_*`. **Failure:** health check 503. **Fallback:** none (hard dependency).

### PgBouncer
- **Purpose:** pooling (transaction mode). **Where:** compose service; backend/worker `POSTGRES_SERVER=pgbouncer`, port 6432. **Failure:** DB unreachable.

### Redis / Upstash
- **Purpose:** Celery broker+backend, retrieval cache, device-trial keys, health streak. **Env:** `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (validated `redis://`/`rediss://`). **Failure:** cache/broker degrade (cache swallowed; broker down → upload 503).

### Qdrant
- **Purpose:** vector store option. **Usage:** only `delete_document` purge when `VECTOR_BACKEND=qdrant`. **Failure:** partial-failure 207. **Note:** no ingestion/retrieval path (⚠️ partial).

### Storage (Local / S3 / Supabase)
- **Purpose:** file persistence. **Init:** `StorageFactory` → `LocalStorageProvider` (default) or `S3StorageProvider` (⚠️ `AWS_REGION` bug H-5). **Env:** `STORAGE_PROVIDER`, `STORAGE_PATH`, `S3_*`, `AWS_*`. **Failure:** local file-not-found raises; S3 init crash (H-5).

### Razorpay
- **Purpose:** payments. **Init:** `razorpay.Client` in `billing.py` when `RAZORPAY_ENABLED`. **Env:** `RAZORPAY_ENABLED/KEY_ID/KEY_SECRET/WEBHOOK_SECRET` (os.getenv). **Failure:** 501/500/502. **Fallback:** sandbox free upgrade (H-6 risk).

### SendGrid / Brevo (SMTP)
- **Purpose:** OTP, reset, nudges, alerts, digest. **Init:** `email_service.send_email`. **Env:** `SMTP_*`, `BREVO_SMTP_*`, `EMAIL_FROM`, `ADMIN_EMAIL`. **Failure/fallback:** OTP skipped gracefully when unconfigured.

### Twilio
- **Purpose:** phone OTP. **Env:** `TWILIO_*`. **Failure:** no-op without creds.

### Sentry / PostHog / OpenTelemetry / Prometheus
- **Sentry:** `SENTRY_DSN`, backend `main.py` + frontend `sentry.client.config.ts`, PII scrubbed. **PostHog:** frontend `analytics.ts`. **OTel/Prometheus:** `core/telemetry`, `OTEL_ENABLED`/`PROMETHEUS_ENABLED` (⚠️ config vs env default mismatch M-7), `/metrics`.

### FingerprintJS
- **Purpose:** device id for trial-abuse control. **Init:** frontend `lib/api.ts initDeviceFingerprint`; backend `DeviceFingerprintMiddleware` + Redis `device_trial:{id}`. **Failure:** best-effort (non-blocking).

---

## 7. Environment Variables (complete table)

| Variable | Required? | Default | Where used | FE | BE | Security impact | Status |
|----------|:--------:|---------|------------|:--:|:--:|-----------------|--------|
| `ENVIRONMENT` | no | `development` | telemetry, dummy-LLM gate | – | ✅ | gates prod behavior | ok |
| `AUTH_SECRET_KEY` | **yes** | – | JWT sign/verify, HMAC URLs | – | ✅ | **high** (forge tokens) | ok |
| `CSRF_SECRET_KEY` | **yes** | – | CSRF | – | ✅ | high | ok |
| `JWT_ALGORITHM` | no | `HS256` | auth/middleware | – | ✅ | high (see M-3) | ok |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | 60 | tokens | – | ✅ | med | ok |
| `REFRESH_TOKEN_EXPIRE_DAYS` | no | 7 | refresh | – | ✅ | med | ok |
| `FRONTEND_URL` | **yes** | – | CORS/CSP | – | ✅ | med | ok |
| `CORS_ORIGINS` | no | `["http://localhost:3000"]` | CORS | – | ✅ | med | ok |
| `NEXT_PUBLIC_API_URL` | **yes** | – | API base (`/api/v1`) | ✅ | – | low | ok |
| `DATABASE_URL` / `POSTGRES_*` | **yes** | – | DB engines | – | ✅ | high | ok |
| `REDIS_URL`,`CELERY_BROKER_URL`,`CELERY_RESULT_BACKEND` | **yes** | – | cache/broker | – | ✅ | high | ok |
| `STORAGE_PROVIDER` | no | `local` | storage factory | – | ✅ | med | ok |
| `STORAGE_PATH` | no | `./storage` | local storage | – | ✅ | low | ok |
| `S3_BUCKET`/`S3_REGION`/`S3_ENDPOINT_URL`/`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` | if s3 | – | S3 | – | ✅ | high | ⚠️ `storage.py` reads `AWS_REGION` (H-5) |
| `AWS_REGION` | — | — | (read by `storage.py`) | – | ✅ | — | ❌ **not defined in Settings** |
| `CHUNK_SIZE`/`CHUNK_OVERLAP`/`OCR_CONFIDENCE_THRESHOLD`/`MAX_UPLOAD_MB` | no | 1800/300/0.80/200 | ingest | – | ✅ | low | ok |
| `GEMINI_API_KEY_1..N` / `GEMINI_API_KEY` | **yes** | – | LLM rotation | – | ✅ | high | ok (via env bridge, not Settings) |
| `GEMINI_API_KEYS` | no | `""` | legacy | – | ✅ | high | deprecated |
| `GEMINI_MODEL`/`GEMINI_FALLBACK_MODEL`/`GEMINI_TEMPERATURE`/`GEMINI_TOP_P`/`GEMINI_MAX_OUTPUT_TOKENS`/`GEMINI_CONTINUATION_ROUNDS` | no | flash-lite/2.0-flash/0.2/0.8/8192/2 | LLM | – | ✅ | low | ok |
| `TOP_K_RESULTS` | no | 20 | retrieval | – | ✅ | low | ok |
| `VECTOR_BACKEND` | no | `faiss` | retrieval branch | – | ✅ | med (perf) | ⚠️ default = NumPy (H-1) |
| `QDRANT_HOST`/`QDRANT_PORT` | no | localhost/6333 | qdrant delete | – | ✅ | low | partial |
| `VECTOR_ISOLATION_MODE`/`ENABLE_ORG_ISOLATION` | no | `user`/false | tenant vectors | – | ✅ | med | org off by default |
| `TOKEN_LIMIT_*`/`SLOW_QUERY_THRESHOLD_MS`/`MAX_CHUNKS_PER_QUERY`/`LARGE_DOC_PAGE_THRESHOLD`/`TOKEN_COST_PER_MTK` | no | see config | cost guard | – | ✅ | low | ok |
| `GROUNDING_TOKEN_BUDGET` | no | 6000 | grounding | – | ✅ | low | ok |
| `RAZORPAY_ENABLED`/`RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`/`RAZORPAY_WEBHOOK_SECRET` | no | false/– | billing | (key_id to FE) | ✅ | **high** (H-6) | os.getenv, not Settings |
| `TWILIO_*` | no | – | phone OTP | – | ✅ | med | optional |
| `SMTP_*`/`BREVO_SMTP_*`/`EMAIL_FROM`/`EMAILS_FROM_*`/`ADMIN_EMAIL` | no | SendGrid defaults | email | – | ✅ | med | optional |
| `SENTRY_DSN` | no | – | error tracking | ✅/✅ | ✅ | low | optional |
| `OTEL_ENABLED`/`PROMETHEUS_ENABLED`/`LOG_LEVEL` | no | True/True/INFO (config) vs false/false (.env) | telemetry | – | ✅ | low | ⚠️ mismatch (M-7) |
| `RERANKER_PROVIDER` | no | `local` | reranker | – | ✅ | low | ok |
| `TAVILY_API_KEY` | no | – | research web | – | ✅ | med | ⚠️ not in Settings |
| `DEPLOY_EVAL_SECRET`/`EVAL_SLACK_WEBHOOK_URL` | no | – | eval reports | – | ✅ | low | optional |
| `ENV_FILE` | no | `.env` | settings loader | – | ✅ | low | ok |

**Missing (referenced, undefined):** `AWS_REGION` (storage.py), `TAVILY_API_KEY` (not in Settings). **Unused/deprecated:** `GEMINI_API_KEYS` (legacy), phantom `embedding_tasks`/`retrieval_tasks` routes.

---

## 8. Execution Flows (Markdown diagrams)

### 8.1 Registration
```
/register → register() → POST /auth/register
  DeviceFingerprintMiddleware: Redis device_trial:{id}? → 409 if reused
  create user (bcrypt) → (optional) send OTP email (SendGrid/Brevo) → 200
```
### 8.2 Login
```
/login → login(form) → POST /auth/login
  verify_password (bcrypt) → create_access_token + create_refresh_token (HS256)
  Set-Cookie token, csrf_token → FE stores CSRF, inits fingerprint
```
### 8.3 Document upload → ready
```
uploadDocumentWithProgress
  → GET /documents/upload/presigned  (validate mime/size; local vs s3)
  → POST /documents/upload/local (multipart, XHR progress)  [or S3 PUT]
  → POST /documents/upload/verify → create Document row → process_document.delay
process_document (worker, sync session)
  → storage.download_file → OCRService.extract_document_stream (PyMuPDF | pptx)   [C-3: no Paddle/Docling]
  → ChunkingService.chunk_page_text (split \n\n, ≤CHUNK_SIZE, overlap)
  → embedding_service.generate_embeddings (batch 50)  [M-4 fallback risk]
  → status PROCESSING→EXTRACTED→READY
  → generate_proactive_insights_task.delay  [M-11: workspace_type wrong→"general"]
```
### 8.4 OCR / Chunking / Embedding (detail)
```
extract_document_stream: per page → is_text_native? 
   native → block-sorted text ; scanned → get_text() [STUB]        (C-3)
chunk_page_text: merge layout blocks; keep big tables whole
embeddings: bge-m3(1024) | gemini(768→pad1024) | zero                (M-4)
```
### 8.5 Query (retrieval → rerank → ground → generate → stream)
```
askQuestionStream → POST /query/stream (SSE, 30/min)
  trial check (402 if exhausted) → emit trial_status
  load history + attached READY doc_ids
  summary intent? → summary_service map-reduce → stream → done
  else: Redis cache? → GroundingService.prepare_grounded_context
        RetrievalService.retrieve_chunks (pgvector|NumPy + tsvector → RRF k=60)   (H-1)
        reranker_service (cross-encoder | dummy)                                   (M-10)
        token-budget → <evidence> blocks (doc order)
  emit metadata{confidence=grounding avg, grounded, mode}   [C-4: not Veritas]
  llm_service.provider.generate_stream (Gemini, key rotation, safe extract)
  emit token* → append disclaimer(legal/finance) → done
  [C-4 target: compute Veritas → emit trust_report here]
```
### 8.6 Export (exam DOCX — sync)
```
GET /exams/{id}/export/docx → load ExamPaper → ExportEngine.generate_exam_docx → StreamingResponse(docx)
(async /export jobs → export_tasks → export_queue → ⚠️ unconsumed H-3)
```
### 8.7 HR processing
```
POST /hr/jobs/{id}/candidates/process → process_resume_batch.delay ✅
  worker: LLM extract CandidateProfile + JobMatch.fit_score (+ embeddings via get_embedding ❌C-1)
POST /hr/jobs/{id}/candidates/{cid}/score → MiniLM cosine → 0.6*llm + 0.4*sim*100
```
### 8.8 Legal processing
```
POST /legal/contracts/process → process_contract_batch.delay ⚠️(unregistered C-2; embeds via get_embedding ❌C-1)
POST /legal/contracts/{id}/risk-report → LLM structured JSON → Python escalation/consistency → LegalAnalysis + audit log ✅
```
### 8.9 Finance processing
```
POST /finance/process → process_finance_batch.delay ⚠️C-2/C-1
POST /finance/ratios → LLM extract line items → Python compute 15 ratios → ExtractionAudit ✅
```
### 8.10 Study processing
```
POST /study/process → process_study_batch.delay ⚠️C-2/C-1
POST /study/quiz/generate → LLM MCQ (store correct_index, strip on return) ; submit → grade
PATCH /study/flashcards/{id}/review → SM-2 (sm2_service.compute_sm2)
```
### 8.11 Research processing
```
POST /research/process → process_research_batch.delay ⚠️C-2/C-1
POST /research/citations → LLM metadata → Python formatters (APA/MLA/IEEE/…)
POST /research/gaps → LLM gaps/conflicts/consensus JSON
GET /research/synthesis/{id} → HARDCODED FAKE (H-4)
deep_research_agent: step1 RAG ❌(C-5) → gaps → Tavily → synthesis → Veritas
```
### 8.12 Exam generation
```
POST /exams/generate/paper → validate marks → _retrieve_grounding_for_paper (RetrievalService over chat docs)
  → LLM strict JSON (paper+answer_key) → 1 retry → honest refusal on fail → auto-save ExamPaper → return exam_id
POST /exams/extract-tables → is_native_pdf? → table_extractor (Docling|Paddle)   [L-3 local-path]
```
### 8.13 Notifications / Insights
```
document READY → generate_proactive_insights_task → proactive_insights_service (LLM) → proactive_insights table → NotificationCenter/ProactiveInsightsPanel
```
### 8.14 Billing
```
trial: check_and_increment_trial (402 at 10)
upgrade: RAZORPAY_ENABLED? → /billing/create-order → Razorpay → /billing/webhook (HMAC) → _activate_plan
         else → /billing/upgrade → _activate_plan (FREE — H-6)
```
### 8.15 Automation (Beat) — ⚠️ not running (H-2)
```
Beat(cron) → auto_health_check(5m)/auto_key_rotation(1h)/auto_daily_digest/auto_db_cleanup/auto_subscription_check/auto_gst_notice/auto_model_check + hr flag_stale_reviews
```

---

## 9. Import Graph, Circular Dependencies, Dead Modules

### 9.1 High-level import direction (healthy layering)
```
endpoints/* → services/* → (core/config, models/*, db/session) → external SDKs
workers/tasks/* → services/* + models/* + core/*  (+ workers/celery_app)
core/middleware → core/config ; core/auth → core/config
services/grounding → services/retrieval → services/embedding/reranker
```
### 9.2 Notable import-time side effects (eager singletons)
`llm_service = LLMService()` (**raises without keys** H-7), `embedding_service`, `reranker_service` (`_get_default_reranker`), `storage_service` (`StorageFactory`), `veritas_engine`, `deep_research_agent`, `ocr_orchestrator`, `get_key_rotator()` singleton. These load models/clients at import → slow imports, test friction.

### 9.3 Broken / dangling references (not classic import cycles, but link failures)
- `deep_research_agent` → `from app.services.retrieval_service import retrieval_service` (**no such symbol** — C-5).
- ~~12 call sites → `llm_service.get_embedding` (**method absent** — C-1)~~ **RESOLVED 2026-07-18:** `LLMService.get_embedding` now exists, delegating to `embedding_service` (async-safe).
- `task_routes` → `embedding_tasks`/`retrieval_tasks` (**modules absent** — H-3).
- `storage.py` → `settings.AWS_REGION` (**attr absent** — H-5).
- `document_tasks` → `doc.workspace_type` (**attr absent** — M-11).

### 9.4 Circular dependencies
None fatal observed. `deep_research_agent` uses **function-local imports** (`from app.services.llm_service import llm_service` inside `research()`) to avoid import cycles — a deliberate pattern. `llm_key_rotation` ↔ `gemini_env` guarded by try/except.

### 9.5 Dead / orphan modules
- ~~`services/ocr_orchestrator.py` + `workers/tasks/ocr_tasks.py` (dead on ingest — C-3)~~ **RESOLVED 2026-07-18:** orchestrator wired into `OCRService.extract_document_stream` for scanned pages; `ocr_gpu_queue` consumed (H-3).
- `services/extraction_router.py` (bypassed by ingestion).
- `endpoints/ws.py` (unused surface — L-7).
- `workers/tasks/email_tasks.py` (unregistered; email sent sync).
- `app/tasks/{eval_tasks,report_tasks}.py` (separate package from `workers/tasks`).
- `import faiss` in `retrieval_service.py` (imported, never used).

---

## 10. Change Impact Matrix (for the most load-bearing files)

| If you modify… | Directly affects | May break / retest |
|----------------|------------------|--------------------|
| `services/llm_service.py` | every LLM call (all workspaces, query, exams, research, insights) | streaming, JSON extraction, key rotation, **adding `get_embedding` here (C-1)** touches search + workers |
| `services/retrieval_service.py` *(marked "never modify")* | grounding, query, exams paper gen, (deep research if fixed) | RRF ordering, pgvector vs NumPy (H-1), all grounded answers |
| `services/grounding_service.py` *("never modify")* | `/query/*`, exams | token budget, citations, confidence |
| `services/embedding_service.py` | ingestion + retrieval | dimension consistency (1024), pgvector distance, M-4 |
| `services/reranker_service.py` | grounding ordering | confidence semantics (feeds UI trust), M-10 |
| `core/config.py` | entire app (Settings) | any changed default/env; validators; VECTOR_BACKEND/storage |
| `core/auth.py` / `core/middleware.py` | every request | authz, CSRF, tenant collection, device gate (M-3) |
| `core/workspace.py` | all workspace-scoped queries | UUID derivation (L-5); document visibility |
| `workers/celery_app.py` | worker registration + routing | C-2/H-3/H-2; adding includes runs those modules at boot |
| `workers/tasks/document_tasks.py` | ingestion for all docs | OCR/chunk/embed, insights (M-11), status transitions |
| `models/document*.py` | documents/pages/chunks | migrations, retrieval joins, embedding column |
| `endpoints/query.py` | main answer path | SSE contract, trial, cache, Veritas wiring (C-4) |
| `endpoints/billing.py` | monetization | trial/upgrade/webhook (H-6) |
| `frontend/src/lib/api.ts` | every FE call | SSE parsing, CSRF, refresh, upload |
| `components/WorkspaceUI.tsx` | all 7 workspaces | chat/upload/stream/panels |

---

## 11. Project Knowledge Graph

```
                         ┌────────────── USER (users, plan, trial) ──────────────┐
                         │                                                        │
                    Auth (JWT/CSRF)                                        Billing (Razorpay)
                         │                                                        │
        ┌──── WORKSPACE (slug → uuid5) ────────────────────────────────────────────────┐
        │        │        │         │         │          │          │                    │
     General     HR     Legal    Finance    Study     Research     Exam                  │
        │        │        │         │         │          │          │                    │
   Router: query hr     legal    finance    study    research    exams                   │
        │        │        │         │         │          │          │                    │
 Services: grounding→retrieval→embedding/reranker→llm_service→Gemini                      │
        │        │        │         │         │          │          │                    │
   Models: Document/Page/Chunk(vec) + domain tables (JobMatch/Clause/Transaction/…)      │
        │        │        │         │         │          │          │                    │
   Workers: document_tasks (✅) · hr(✅) · legal/finance/study/research (⚠️ C-2) · export/ocr(⚠️H-3)
        │                                                                                 │
   Frontend: /<ws>/page → WorkspaceUI → panels (Legal/Finance/HR/Research/Exam)          │
        │                                                                                 │
   External: Gemini · bge-m3 · cross-encoder · Tavily(Research) · Docling/Paddle(dead C-3)│
        └─────────────────────────────────────────────────────────────────────────────────┘

  Cross-cutting: Redis(cache/broker) · PgBouncer · Storage(local/S3) · Observability(Sentry/OTel/Prom/PostHog)
  Automation(Beat ⚠️H-2): health/keys/digest/cleanup/subscription/gst/model
```

---

## 12. Interview Mapping (per subsystem)

### Retrieval (hybrid + RRF)
- **Why it exists:** combine semantic recall with lexical precision. **Design:** two ranked lists fused by RRF (`1/(60+rank)`). **Alternatives:** weighted linear fusion (needs normalization), learned rerank. **Trade-offs:** RRF ignores score magnitude. **Scalability:** needs pgvector+HNSW (currently NumPy default — H-1). **Production:** ANN index, sharding by tenant. **FAANG concepts:** two-phase retrieval, ANN, rank fusion.

### Grounding / anti-hallucination
- **Why:** eliminate hallucination architecturally. **Design:** evidence-only prompt + token budget + refusal contract + document-order citations. **Alternatives:** self-consistency, citation verification. **Trade-offs:** truncation vs coverage (hence map-reduce summaries). **FAANG concepts:** RAG, prompt contracts, context budgeting.

### Reranking
- **Why:** cheap recall then expensive precision. **Design:** cross-encoder over shortlist. **Alternatives:** ColBERT, Cohere Rerank. **Trade-offs:** latency vs quality; silent dummy fallback risk (M-10). **FAANG concepts:** cascade ranking.

### LLM resilience
- **Why:** provider rate limits/quirks. **Design:** key rotation, cooldowns, model fallback, safe extraction, JSON repair. **Alternatives:** managed gateway, provider SDK retries. **Trade-offs:** lock-sleep contention (M-9), import-time coupling (H-7). **FAANG concepts:** partial-failure handling, backpressure, idempotency.

### Async ingestion / workers
- **Why:** keep API latency low; scale CPU/GPU work independently. **Design:** Celery + Redis, per-domain queues, retry/DLQ via status. **Alternatives:** Arq/Temporal. **Trade-offs:** queue/worker wiring drift (C-2/H-3), no Beat (H-2). **FAANG concepts:** producer/consumer, DLQ, autoscaling workers.

### Multi-tenancy
- **Why:** isolate user/org data. **Design:** JWT claims + `owner_id`/workspace filters + vector namespaces + RLS. **Alternatives:** schema-per-tenant, DB-per-tenant. **Trade-offs:** app-layer filters must be everywhere; org isolation off by default. **FAANG concepts:** tenancy models, RLS, defense in depth.

### Streaming (SSE)
- **Why:** token-by-token UX over plain HTTP. **Design:** async generator → `StreamingResponse`; client parses `\n\n`. **Alternatives:** WebSockets. **Trade-offs:** one-directional; Veritas needs full answer (emit after stream — C-4). **FAANG concepts:** streaming, disconnect detection.

### Billing / trial
- **Why:** monetization + abuse control. **Design:** trial counter, device fingerprint, Razorpay + HMAC webhook. **Alternatives:** Stripe, metered usage. **Trade-offs:** free self-upgrade default (H-6), no per-tier quotas. **FAANG concepts:** webhook verification, entitlement, idempotent activation.

### Domain "extract-then-compute" (Finance/Legal/Research citations)
- **Why:** never trust the LLM with arithmetic/formatting. **Design:** LLM extracts structured fields; **Python** computes ratios / escalation / citation strings. **Why it's exemplary:** this is the correct pattern for numeric/deterministic correctness. **FAANG concepts:** LLM-as-extractor, deterministic post-processing, auditability.

---

*End of Dependency Graph. Documentation only — no code was modified. Use with [DEBUG_MASTER_PLAN.md](DEBUG_MASTER_PLAN.md) for the repair phase.*
