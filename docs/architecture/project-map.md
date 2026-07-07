# DocuMindAI — Architecture & API Map

Architecture: **Next.js (App Router) frontend** ↔ **FastAPI backend** ↔ **Postgres + pgvector / FAISS** + **Redis** + **Celery workers**.

API base: all backend routes are mounted under `/api/v1` via `app/api/v1/api.py`.
Frontend convention: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` (already includes `/api/v1`). `apiFetch(endpoint)` does `${API_BASE}${endpoint}`, so endpoints in `lib/api.ts` start with `/` (no `/api/v1` prefix).

## Page → API → Endpoint → Service → Model → DB → Worker

| Frontend page / component | Calls (lib/api.ts or fetch) | Backend endpoint | Service | Model / table | Celery worker |
|---|---|---|---|---|---|
| `/login` | `login(form)` → `/auth/login` | `auth.py:login` | core.security | `User` / users | – |
| `/register` | `register()` → `/auth/register` | `auth.py:register` | core.security, email | `User`, `UserRole` | – |
| Email verify | `verifyEmail(otp)` → `/auth/verify-email` | `auth.py:verify_email` | – | `User.email_verified` | – |
| `/general`, `/hr`, `/legal`, `/finance`, `/study`, `/research`, `/exam` (WorkspaceUI) | `getChats`, `createChat`, `getChatMessages`, `askQuestionStream` | `chats.py:*`, `query.py:/query/stream` | retrieval, grounding, llm | `ChatSession`, `ChatMessage`, `Document`, `DocumentChunk` | `document_tasks` |
| Sidebar chats | `getChats(workspace_type)` | `GET /chats?workspace_type=…` | – | `ChatSession` | – |
| Document upload | `uploadDocumentWithProgress` → `/documents/upload/presigned`, `/documents/upload/local`, `/documents/upload/verify` | `documents.py:*` | document_service, ocr, chunking, embedding | `Document`, `DocumentPage`, `DocumentChunk` | `document_tasks.process_document` |
| Document preview | direct `${API_BASE}/api/v1/documents/{id}/file` | `documents.py:serve_file` | storage | `Document` | – |
| EnterpriseDocumentViewer | renders pdf via react-pdf (CSR-only — currently SSR-broken) | – | – | – | – |
| `/admin/cost`, `/admin/eval`, `/admin/tenants`, `/admin/corrections` | various `/api/v1/admin/...` (currently has manual `/api/v1` prefix → doubled) | `tenants`, `corrections`, etc. | tenant_guard, eval_service | – | – |
| Bookmarks (`/bookmarks`, `BookmarkButton`) | manual `${API_BASE}/api/v1/bookmarks` (DOUBLED) | `bookmarks.py:*` | – | `Bookmark` | – |
| NotificationCenter | manual `${API_BASE}/api/v1/notifications` (DOUBLED) | `notifications.py:*` | – | `Notification` | – |
| `/settings` | manual `${API_BASE}/api/v1/users/me` (DOUBLED) | `users.py:*` | – | `User` | – |
| `/shared/[token]` | manual `${API_BASE}/api/v1/shared/{token}` (DOUBLED) | `chats.py:shared_router:/shared/{token}` (no auth) | – | `ChatSession` | – |
| ExportModal, ReportShareModal | manual `${API_BASE}/api/v1/export/...` (DOUBLED) | `export.py:*` | export_engine | `ExportJob`, `ReportShare` | `export_tasks` |
| TrialPill, UpgradeModal | `getBillingStatus`, `upgradePlan` → `/billing/*` | `billing.py:*` | trial_enforcement | `User.plan` etc. | – |
| HR workspace panels | `/hr/*` (lib/api.ts) + manual `/api/v1/hr/*` (DOUBLED in CandidateRankingsPanel) | `hr.py:*` | – | `JobRole`, `CandidateProfile`, `JobMatch` | `hr_tasks` |
| Legal workspace | `/legal/*` + manual `/api/v1/legal/*` (DOUBLED in LegalRiskPanel) | `legal.py:*` | – | `Contract`, `Clause` | `legal_tasks` |
| Finance workspace | `/finance/*` + manual `/api/v1/finance/*` (DOUBLED in FinanceRatioPanel) | `finance.py:*` | financial_table_extractor | `FinancialDocument`, `Transaction`, `AuditFinding` | `finance_tasks` |
| Study workspace | `/study/*` + manual `/api/v1/study/*` (DOUBLED in WorkspaceUI for flashcards) | `study.py:*` | sm2_service | `StudyNote`, `FlashcardDeck`, `Flashcard` | `study_tasks` |
| Research | `/research/*` + manual `/api/v1/research/*` (DOUBLED) | `research.py:*` | deep_research_agent | `ResearchProject`, `ResearchPaper`, `ResearchFinding` | `research_tasks` |
| Exams | `/exams/*` + manual `/api/v1/exams/*` (DOUBLED) | `exams.py:*` | – | `ExamPaper`, `ExamVersion` | – |
| Insights | `/api/v1/insights` (DOUBLED) | `insights.py:*` | proactive_insights | `ProactiveInsight` | `auto_*` automation |
| Feedback | `/feedback/*` | `feedback.py:*` | feedback_service | `Feedback` | – |
| Corrections (CorrectionModal) | `/api/v1/corrections` (DOUBLED) | `corrections.py:*` | – | `Correction`, `CorrectionNote` | – |

## Automation (Celery beat)
`auto_daily_digest`, `auto_db_cleanup`, `auto_gst_notice`, `auto_health_check`, `auto_key_rotation`, `auto_model_check`, `auto_subscription_check` — all in `backend/app/automation/`.

## Workspace identity (CRITICAL inconsistency)
- `User.workspace_id` = `Column(String(50), default="general")` — string slug
- `ChatSession.workspace_id` = `Column(UUID, nullable=False)` — UUID
- `ScheduledReport.workspace_id` = `Column(String)` — string
- Endpoints universally do `uuid.UUID(current_user["workspace_id"])` → crash on slug `"general"`.
- **No `Workspace` table exists.**
- **Fix strategy**: deterministic `uuid.uuid5(NAMESPACE_OID, slug)` mapping via a new `app.core.workspace.resolve_workspace_id()` helper. No migration needed; existing UUIDs in `ChatSession.workspace_id` will be re-bound on the next write (read-by-owner remains compatible since reads filter by both owner_id and workspace_id).

## Doubled-prefix bug (A1)
`NEXT_PUBLIC_API_URL` already contains `/api/v1`. About 35 manual `${API_BASE}/api/v1/...` call sites across frontend/src bypass the convention. The fix is to drop `/api/v1` from those literals so they go through the same convention as `apiFetch`.

## STABLE files (CLAUDE.md) — additive/wrapper only
- `services/llm_service.py`, `llm_key_rotation.py`, `veritas_engine.py`, `automation/auto_health_check.py`, `automation/auto_daily_digest.py`
- **Never modify**: `services/retrieval_service.py`, `services/grounding_service.py`, `services/chunking_service.py`, `workers/celery_app.py`, `workers/tasks/hr_tasks.py`
