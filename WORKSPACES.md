# DocuMindAI — Workspace Documentation

Companion to [REPORT.md](REPORT.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Each of the seven workspaces is documented individually. All seven frontend pages render the shared `components/WorkspaceUI.tsx` with a different `workspaceType`, so the **chat + upload + streaming** experience is common; what differs is the **backend router, models, Celery task, retrieval tuning, response schema, and domain panels**.

## Shared Foundations (apply to every workspace)

- **Frontend page:** `src/app/<name>/page.tsx` → `<WorkspaceUI workspaceType="<name>" />`.
- **Chat + Q&A:** `POST /query/stream` (SSE) with `workspace_type`; sessions/messages via `/chats/*`; documents via `/documents/*` (per-chat isolation through `chat_session_id`).
- **Retrieval tuning** (`config.WORKSPACE_RETRIEVAL_CONFIG`):

  | Workspace | top_k | rerank_n | chunk_pref |
  |-----------|:----:|:-------:|:----------:|
  | exam | 12 | 8 | medium |
  | hr | 18 | 12 | small |
  | legal | 10 | 6 | large |
  | finance | 14 | 8 | small |
  | research | 16 | 10 | large |
  | study | 12 | 8 | medium |
  | general | 12 | 8 | medium |

- **Cost guard** (`config`): per-workspace daily token budgets (`TOKEN_LIMIT_*`: general 50k, legal/finance 80k, hr 60k, teacher/student 40k, research 60k) — defined in config; enforcement lives in `services/cost_guard_service.py`.
- **Response schema injection:** `services/response_schemas.get_response_schema(workspace_type)` appends a domain-specific formatting instruction to the system prompt.
- **Ownership/isolation:** every workspace query filters by `resolve_workspace_id(current_user["workspace_id"])` and `owner_id`.
- **Async processing pattern:** `POST /<ws>/process?document_id=…` dispatches a Celery `process_*_batch` task; a simulated SSE `/<ws>/events/…` reports fake progress.

> ⚠️ **Cross-workspace defect:** the `/<ws>/process` endpoints for **legal, finance, study, research** enqueue Celery tasks (`process_contract_batch`, `process_finance_batch`, `process_study_batch`, `process_research_batch`) whose modules are **not in the worker `include` list** (`workers/celery_app.py`). With the default Docker worker they will not execute. HR's `process_resume_batch` **is** registered. See [FINAL_AUDIT.md](FINAL_AUDIT.md).

> ⚠️ **Cross-workspace defect:** the per-workspace semantic search endpoints (`/legal/clauses/search`, `/finance/transactions/search`, `/study/search`, `/research/search`) call `llm_service.get_embedding()`, which **does not exist** → HTTP 500. The tutor/copilot chats call it too but catch the error and fall back to recency.

---

# 1. General Workspace

**Route:** `/general` · **Users:** anyone with documents · **Backend:** shared `/query`, `/chats`, `/documents`, `/insights`.

### Purpose & business value
The universal document-Q&A surface: upload any supported file and ask grounded questions. It is the reference implementation of the "zero-hallucination, cited answer" promise and the on-ramp for the trial funnel.

### Technical flow
1. User creates/opens a chat (`/chats`), uploads docs (`/documents/upload/*`) bound to that chat.
2. Ingestion worker indexes the docs (PyMuPDF → chunk → embed → `READY`).
3. `/query/stream` runs hybrid retrieval → grounding → Gemini, streaming tokens with a `metadata` event carrying evidence + grounding confidence.
4. Summary-intent questions trigger the map-reduce full-document summary path.
5. On upload, `generate_proactive_insights_task` surfaces findings into `ProactiveInsightsPanel`.

### AI workflow & prompt engineering
Strict "document intelligence" system prompt: read every evidence block, cover the document proportionally, cite `(filename, p.N)`, and output the exact refusal string when evidence is missing. In **no-document mode** it switches to a general-knowledge prompt and flags `mode: "general"` so the UI can show an "Ungrounded" badge.

### Data / workers / APIs
- **Tables:** `documents`, `document_pages`, `document_chunks`, `chat_sessions`, `chat_messages`, `proactive_insights`, `bookmarks`, `notifications`.
- **Worker:** `document_tasks` (+ `generate_proactive_insights_task`).
- **APIs:** `/query/stream`, `/query/ask`, `/query/search`, `/query/debug`, `/chats/*`, `/documents/*`, `/insights/*`.

### Current limitations
- Grounding confidence, not Veritas, is shown as the "trust" number.
- No-document mode contradicts the absolute "refuses without evidence" marketing (it answers from general knowledge, though honestly labeled).
- Default `faiss` retrieval is an in-memory NumPy scan.

### Improvement opportunities
- **Retrieval:** enable pgvector by default + HNSW index; add query rewriting/HyDE; hybrid weighting instead of pure RRF.
- **AI:** wire the real Veritas score here; add answer-level citation verification (does each sentence's cited page actually support it?).
- **UX:** inline citation hover-to-source; streaming token latency budget; retry/regenerate.
- **Observability:** per-query trace with retrieval/rerank/gen spans surfaced to the user (tracing data already exists).
- **Caching:** semantic (embedding-level) response cache keyed by normalized query.

---

# 2. HR Workspace

**Route:** `/hr` · **Users:** recruiters, HR managers · **Router:** `endpoints/hr.py` · **Worker:** `hr_tasks.process_resume_batch` (registered ✅).

### Purpose & business value
Turn a pile of resumes into a ranked, searchable candidate pipeline against a job role: parse resumes, score fit, track stages, collaborate with notes, and export CSV.

### Technical flow
1. Create a `JobRole` (`POST /hr/jobs`).
2. Upload resumes as documents, then `POST /hr/jobs/{job_id}/candidates/process?document_id=…` → `process_resume_batch` (LLM extracts `CandidateProfile`, computes `JobMatch.fit_score`).
3. List/rank candidates (`GET /hr/jobs/{job_id}/candidates`, filter by `min_score`/`status`/`search`).
4. **Semantic re-score** (`POST /hr/jobs/{job_id}/candidates/{candidate_id}/score`): loads `all-MiniLM-L6-v2` (384-dim) to compute JD↔resume cosine similarity, blends `final = 0.6*llm_score + 0.4*similarity*100`.
5. Analytics funnel (`GET /hr/jobs/{job_id}/analytics`), CSV export, candidate notes, stage transitions (`PATCH /hr/candidates/{id}/stage`).

### AI workflow
LLM structured extraction (`CandidateExtractionSchema`, `MatchAnalysisSchema`) for profile + skills + missing-skills gap analysis; a **separate** MiniLM embedding for JD-resume similarity. PII is redacted in logs (`utils/pii_redactor`, `[REDACTED-PII]`).

### Data / APIs
- **Tables:** `hr_job_roles`, `hr_candidates`, `hr_candidate_notes`, `hr_interviews`, `hr_job_matches`.
- **APIs:** `/hr/jobs`, `/hr/jobs/{id}/candidates[/process|/analytics|/export/csv]`, `/hr/candidates/{id}/notes`, `/hr/candidates/{id}/stage`, `/hr/matches/{id}/status`, `/hr/jobs/{id}/candidates/{cid}/score`, `/hr/events/processing/{id}` (simulated SSE).

### Current limitations
- The list `search` param is `ILIKE` keyword matching, not true semantic search (the pgvector version is commented out).
- Two embedding models coexist (bge-m3 for docs, MiniLM for JD scoring) — extra memory, inconsistent vector spaces.
- SSE processing feed is a fake heartbeat.

### Improvement opportunities
- Replace `ILIKE` search with real candidate-embedding pgvector ranking.
- Bias/fairness auditing on ranking; explainable score breakdowns (partially present).
- Interview scheduling integration (model `hr_interviews` exists but is underused).
- Bulk resume ingest with dedupe; ATS webhook integrations.

---

# 3. Legal Workspace

**Route:** `/legal` · **Users:** lawyers, legal ops · **Router:** `endpoints/legal.py` · **Worker:** `legal_tasks.process_contract_batch` (⚠️ not in worker `include`).

### Purpose & business value
Contract intelligence: clause extraction, risk scoring, compliance checks, contract comparison, redlines, approval workflow, and an immutable audit trail — with a mandatory "not legal advice" disclaimer on every response.

### Technical flow & AI workflow (strong design)
- **`POST /legal/contracts/{id}/risk-report`** (synchronous, works without Celery): pulls the contract's chunk text, asks Gemini for a **structured risk JSON** (overall score/level, per-clause `risk_level` + `confidence_basis` + `page`, missing clauses), then applies **Python logic** for:
  - **Escalation triggers** (score ≥ 70, any Critical clause, or ≥3 missing clauses).
  - **Consistency validation** vs the previous `LegalAnalysis` (flags clauses whose risk level jumped ≥2 levels).
  - **Unassessable handling** (confidence < 0.5 → risk downgraded, honest "insufficient information").
  - Persists a `LegalAnalysis` row + immutable `LegalAuditLog` entries (`analysis_created`, `escalation_triggered`).
- **`POST /legal/contracts/compare`**: LLM clause-by-clause diff → JSON (matching/unique clauses, material differences), disclaimer appended.
- **`GET /legal/audit-log`**: user's own audit events.

### Data / APIs
- **Tables:** `legal_contracts`, `legal_clauses` (with embedding), `legal_compliance_rules`, `legal_redlines`, `legal_approvals`, `legal_analyses`, `legal_audit_log`, `extraction_audit`.
- **APIs:** `/legal/rules`, `/legal/contracts[/process|/compare]`, `/legal/contracts/{id}[/clauses|/approvals|/risk-report]`, `/legal/clauses/search` (⚠️ broken — `get_embedding`), `/legal/audit-log`, `/legal/events/legal/{id}` (simulated SSE).

### Current limitations
- `process_contract` (async clause extraction into `legal_clauses`) is queued to a task the default worker doesn't run; so `/legal/clauses/search` has no populated embeddings **and** calls a missing method → doubly broken.
- Redline generation model (`legal_redlines`) is defined but the generation path is thin.

### Improvement opportunities
- Register `legal_tasks` on the worker; back `clauses/search` with a real embedding call (`embedding_service`) + pgvector.
- Clause library / precedent retrieval across contracts; obligation & deadline extraction with calendar export.
- Jurisdiction-aware compliance rule packs; redline DOCX (the README's advertised legal export) fully wired.

---

# 4. Finance Workspace

**Route:** `/finance` · **Users:** analysts, auditors, CFO office · **Router:** `endpoints/finance.py` · **Worker:** `finance_tasks.process_finance_batch` (⚠️ not in worker `include`).

### Purpose & business value
Extract financial statements and compute a full ratio suite with **traceability and numerical integrity** — the anti-hallucination story done right for numbers.

### Technical flow & AI workflow (strongest anti-hallucination design in the app)
- **`POST /finance/ratios`**: LLM **extracts line items only** (current assets, revenue, COGS, EBITDA, etc.) as structured JSON with per-field `raw_text`, `page_number`, `confidence`. Then **Python computes all 15 ratios** (`compute_ratios`) — the LLM never does arithmetic. Adds:
  - **Indian number normalization** (`normalize_indian_number` — lakh/crore) and accounting-standard detection (`detect_accounting_standard`).
  - **Numerical integrity validation** (`_validate_values`): each number in the answer is confidence-scored by exact/approximate presence in source chunks.
  - **Ratio status** (Good/Caution/Risk) vs benchmarks, plus input traceability.
  - Persists `ExtractionAudit` rows per line item.
- **`POST /finance/compare`**: runs extraction per period and computes YoY trends + direction (improving/declining/stable) in **Python**.

### Data / APIs
- **Tables:** `finance_documents`, `finance_transactions` (with embedding), `finance_audit_findings`, `finance_rules`, `extraction_audit`.
- **APIs:** `/finance/process`, `/finance/ratios`, `/finance/compare`, `/finance/documents`, `/finance/findings`, `/finance/transactions/search` (⚠️ broken — `get_embedding`), `/finance/events/finance/{id}` (simulated SSE).

### Current limitations
- Async `process_finance_batch` (populates transactions + audit findings) isn't consumed by the default worker.
- Transaction semantic search is broken (missing `get_embedding` + unpopulated embeddings).
- Ratio extraction reads only the first ~12k chars of the document.

### Improvement opportunities
- Register `finance_tasks`; wire transaction anomaly detection (models exist).
- Multi-statement reconciliation (balance-sheet ↔ cash-flow tie-outs); XBRL ingestion.
- Chart generation for trends (recharts already in frontend via `FinanceRatioPanel`).
- Extend ratio benchmarks by industry.

---

# 5. Study Workspace

**Route:** `/study` · **Users:** students, educators · **Router:** `endpoints/study.py` · **Worker:** `study_tasks.process_study_batch` (⚠️ not in worker `include`).

### Purpose & business value
Convert study material into active-recall tools: flashcards with **SM-2 spaced repetition**, MCQ quizzes with grading, and an AI tutor.

### Technical flow & AI workflow
- **Flashcards:** `process_study_batch` generates `StudyNote`/`FlashcardDeck`/`Flashcard`; review via `PATCH /study/flashcards/{id}/review` applies the **SM-2 algorithm** (`services/sm2_service.compute_sm2`) to update interval/ease/next-review.
- **Quizzes:** `POST /study/quiz/generate` (LLM MCQ generation; **stores `correct_index` server-side and strips it from the response** — anti-cheat; falls back to a stub quiz on parse failure). `POST /study/quiz/{id}/submit` grades and returns per-question explanations + letter grade.
- **AI tutor:** `GET /study/tutor/chat` (SSE) retrieves relevant `StudyNote`s and streams a grounded, encouraging tutor response. It tries `get_embedding` (missing) but **catches the error and falls back to recency**, so it degrades but does not crash.
- **Pomodoro timer:** frontend `PomodoroTimer` component (client-only).

### Data / APIs
- **Tables:** `study_notes`, `study_flashcard_decks`, `study_flashcards`, `study_quizzes`, `study_quiz_attempts`.
- **APIs:** `/study/process`, `/study/decks[/{id}/flashcards]`, `/study/quiz/generate`, `/study/quiz/{id}/submit`, `/study/flashcards/{id}/review`, `/study/tutor/chat`, `/study/search` (⚠️ broken), `/study/events/study/{id}` (simulated SSE).

### Current limitations
- Flashcard generation depends on the unregistered `study_tasks` worker.
- `/study/search` is broken; tutor search degrades to recency.

### Improvement opportunities
- Register `study_tasks`; wire flashcard embeddings for real semantic search.
- Adaptive difficulty from quiz history (`study_quiz_attempts` exists); concept mastery maps.
- Cloze deletions and image-occlusion cards; export to Anki.

---

# 6. Research Workspace

**Route:** `/research` · **Users:** academics, scientists · **Router:** `endpoints/research.py` · **Worker:** `research_tasks.process_research_batch` (⚠️ not in worker `include`) · **Extra service:** `deep_research_agent.py` (Tavily).

### Purpose & business value
Literature workflows: multi-format citation export, research-gap/consensus/conflict analysis, cross-document synthesis, an AI copilot, and a web-augmented "Deep Research" agent.

### Technical flow & AI workflow
- **Citations** (`POST /research/citations`): LLM extracts bibliographic metadata; **Python formats** APA/MLA/IEEE/Chicago/BibTeX/Vancouver (deterministic formatters — a clean anti-hallucination split).
- **Gaps** (`POST /research/gaps`): LLM returns `{gaps, conflicts, consensus}` JSON across paper excerpts.
- **Synthesis** (`GET /research/synthesis/{project_id}`): ⚠️ **returns hardcoded placeholder** contradiction/consensus data ("X causes Y", "Paper A suggests…") — a stub, not real analysis.
- **Copilot** (`GET /research/copilot/chat`, SSE): retrieves `ResearchFinding`s (tries `get_embedding`, falls back to recency) and streams an evidence-grounded answer.
- **Deep Research Agent** (`deep_research_agent.py`): a 4-step pipeline (RAG → gap ID → Tavily web search restricted to gov/academic domains → synthesis) that also computes a **Veritas trust score**. ⚠️ Step 1 calls `retrieval_service.query(...)` / imports a `retrieval_service` singleton that **do not exist**, so the document-RAG step always throws and is swallowed — the agent effectively runs web-only or empty.

### Data / APIs
- **Tables:** `research_projects`, `research_papers`, `research_findings` (with embedding), `research_contradictions`.
- **APIs:** `/research/projects[/{id}/papers]`, `/research/papers/{id}/findings`, `/research/process`, `/research/citations`, `/research/gaps`, `/research/synthesis/{id}`, `/research/copilot/chat`, `/research/search` (⚠️ broken), `/research/events/research/{id}` (simulated SSE).

### Current limitations
- Synthesis is fake; Deep Research document step is broken; `research_tasks` unregistered; `/research/search` broken.
- Veritas is reachable only here and only over an already-broken code path.

### Improvement opportunities
- Fix the retrieval call in the deep-research agent (use `RetrievalService.retrieve_chunks`); make synthesis real via finding clustering + contradiction detection (models exist).
- Configurable Tavily domain allowlists; citation-graph building; PDF metadata (DOI/arXiv) enrichment.

---

# 7. Exam / Teacher Workspace

**Route:** `/exam` · **Users:** teachers, trainers · **Router:** `endpoints/exams.py` · **Worker:** none required (synchronous generation).

### Purpose & business value
Generate complete, **grounded** exam papers with answer keys from uploaded syllabi/textbooks, validate marks allocation, honor Bloom's taxonomy, edit, version, and export to DOCX. Also extract tables from documents. This is the most polished workspace.

### Technical flow & AI workflow (strong design)
- **`POST /exams/generate/paper`**: validates marks allocation (`validate_marks_allocation`), retrieves evidence from the chat's attached READY documents (`_retrieve_grounding_for_paper`, using `RetrievalService`), and prompts Gemini for a strict paper+answer_key JSON grounded only in the evidence. On parse failure it **retries once and then emits an honest refusal paper** (never placeholder questions). Auto-saves to `ExamPaper` so DOCX export always has a source; returns `exam_id`. Precise, actionable errors distinguish "no session / no docs / still processing / no matching chunks."
- **`GET /exams/{id}/export/docx`**: renders a stored paper (or `"latest"`) to an academic DOCX via `ExportEngine.generate_exam_docx`.
- **`POST /exams/extract-tables`**: uses `table_extractor` (Docling for native PDFs, PaddleOCR for scanned — detected via `is_native_pdf`) → export as DOCX/CSV/HTML.
- **`POST /exams/generate/question`**: single grounded question via `llm_service.generate_json` + `QuestionSchema` (JSON-repair loop).
- CRUD + versioning (`ExamVersion`), free-form edit save (`/save-edits`).
- **Stubs:** `/exams/generate/diagram` returns a hardcoded Mermaid template; `/exams/process/voice` is a stub.

### Data / APIs
- **Tables:** `exam_papers`, `exam_versions`.
- **APIs:** `/exams` (CRUD), `/exams/generate/paper`, `/exams/generate/question`, `/exams/generate/diagram` (stub), `/exams/{id}/export/docx`, `/exams/extract-tables`, `/exams/export/table[-docx]`, `/exams/{id}/save-edits`, `/exams/process/voice` (stub).

### Current limitations
- Table extraction reads `doc.storage_path` from disk directly → works locally, breaks on S3 keys.
- Diagram/voice endpoints are placeholders.

### Improvement opportunities
- Real diagram generation (Graphviz/Mermaid from content); question bank + difficulty calibration; anti-plagiarism variants; rubric auto-grading of student submissions.
- Multi-language paper generation (language instruction infra already exists).

---

## Cross-Workspace Improvement Themes

| Theme | Opportunity |
|-------|-------------|
| **Retrieval** | Default to pgvector + HNSW; per-domain embedding fine-tuning; query rewriting |
| **AI** | Wire real Veritas across all workspaces; sentence-level citation verification; structured-output APIs (Gemini JSON mode) instead of prompt-and-parse |
| **Workers** | Register all `*_tasks`; run a Beat container; give each queue a consumer; real Redis Pub/Sub SSE progress |
| **Search** | Add the missing `get_embedding` (or route to `embedding_service`) to unbreak the four `*/search` endpoints |
| **Exports** | Legal redline DOCX + HR candidate summary DOCX (advertised, thin in code); async export queue consumer |
| **Observability** | Surface retrieval/rerank/gen tracing per workspace; per-workspace cost dashboards (config exists) |
| **Testing** | Contract tests per workspace (currently none) |
| **Security** | Per-tier quota enforcement; organization isolation on by default for enterprise tenants |

## Data Model Reference (all tables)

`users`, `organizations`, `user_roles`, `organization_users`, `documents`, `document_pages`, `document_chunks`, `chat_sessions`, `chat_messages`, `pinned_session`, `bookmarks`, `notifications`, `feedback`, `corrections`, `correction_notes`, `proactive_insights`, `report_shares`, `message_notes`, `saved_query_templates`, `scheduled_reports`, `export_jobs`, `benchmark_runs`, `eval_benchmark_queries`, `eval_results`, `hr_job_roles`, `hr_candidates`, `hr_candidate_notes`, `hr_interviews`, `hr_job_matches`, `legal_contracts`, `legal_compliance_rules`, `legal_clauses`, `legal_redlines`, `legal_approvals`, `legal_analyses`, `legal_audit_log`, `extraction_audit`, `finance_documents`, `finance_transactions`, `finance_audit_findings`, `finance_rules`, `study_notes`, `study_flashcard_decks`, `study_flashcards`, `study_quizzes`, `study_quiz_attempts`, `research_projects`, `research_papers`, `research_findings`, `research_contradictions`, `exam_papers`, `exam_versions`.
