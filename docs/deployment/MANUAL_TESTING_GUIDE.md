# DocuMindAI — Manual Testing Guide (Pre-Deployment QA)

**Purpose:** verify the whole application actually works, end to end, in your own hands, before anything is pushed to GitHub or deployed. Nothing in this file changes code — it only tells you what to run and what to click.

**Order:** run Part 1 once to get the stack up. Run Part 2 once to create a login. Then work through Part 3 workspace by workspace, checking boxes as you go. Part 4 is a final sweep. Part 5 is what to do with the results.

---

## Table of contents

1. [Start the stack (PowerShell)](#1-start-the-stack-powershell)
2. [Create a login](#2-create-a-login)
3. [Per-workspace test cases](#3-per-workspace-test-cases)
   - [3.1 General](#31-general)
   - [3.2 HR](#32-hr)
   - [3.3 Legal](#33-legal)
   - [3.4 Finance](#34-finance)
   - [3.5 Study](#35-study)
   - [3.6 Research](#36-research)
   - [3.7 Exam](#37-exam)
4. [Cross-cutting checks](#4-cross-cutting-checks)
5. [What to do with the results](#5-what-to-do-with-the-results)

---

## 1. Start the stack (PowerShell)

### 1.1 One-time setup

Confirm your backend env file has real values. It already exists on disk (`backend/.env`) — this just checks it's not empty:

```powershell
Get-Content backend\.env | Select-String "GEMINI_API_KEY_1|AUTH_SECRET_KEY|CSRF_SECRET_KEY"
```

You should see all three with non-empty values on the right of `=`. If `GEMINI_API_KEY_1` is blank, get a key from https://aistudio.google.com/app/apikey and paste it in, then save.

### 1.2 Start the full stack

From the repo root:

```powershell
cd infrastructure
docker compose up --build
```

Leave this terminal running — it streams logs from all six services (db, pgbouncer, redis, backend, worker, beat, frontend). Watch for these two lines from the `backend` container, which confirm the LLM key loaded:

```
[startup] Gemini keys available: 1
```

If you instead see `CRITICAL: No Gemini API keys configured`, stop (`Ctrl+C`), fix `backend/.env`, and re-run.

**First run only** — compose builds the images, which takes a while (the backend pulls the OCR/ML stack). Subsequent runs are fast.

### 1.3 Open a second PowerShell window and seed a dev login

Migrations run automatically as part of the backend container's startup, so by the time compose settles, the schema is ready. Seed a test user:

```powershell
cd infrastructure
docker compose exec backend python scripts/seed_dev.py
```

Expected output:
```
✓ Dev user created successfully.
  Email:    dev@test.com
  Password: devpass123
  Role:     admin
  Workspace: general
```

If it says `✓ Dev user already exists`, that's fine — it means a previous test run already created it.

### 1.4 Confirm everything is actually up

```powershell
# Backend health — expect {"api":"ok","db":"ok","redis":"ok"}
curl.exe http://localhost:8000/api/v1/health

# Frontend — expect a 200
curl.exe -I http://localhost:3000
```

Then open **http://localhost:3000** in your browser. You should land on the marketing/landing page.

### 1.5 Alternative — run without Docker (if you prefer native processes)

Only use this if you already have Python 3.11 + the `backend\venv` set up and Postgres/Redis running some other way. Docker Compose (1.2) is the tested, recommended path.

```powershell
# Terminal 1 — infrastructure only
cd infrastructure
docker compose up db redis pgbouncer

# Terminal 2 — backend API
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Terminal 3 — worker + beat combined (Windows-safe solo pool)
cd backend
.\venv\Scripts\Activate.ps1
.\scripts\run_worker_windows.ps1

# Terminal 4 — frontend
cd frontend
npm run dev
```

### 1.6 Stopping everything

In the terminal running `docker compose up`, press `Ctrl+C`, then:

```powershell
cd infrastructure
docker compose down
```

This stops the containers but **keeps your data** (Postgres volume persists). Do not run `docker compose down -v` — that deletes the database volume.

---

## 2. Create a login

You have two options. Do **both** at least once — they exercise different code paths.

### 2.1 Fast path — use the seeded dev user

1. Go to http://localhost:3000/login
2. Email: `dev@test.com` / Password: `devpass123`
3. You should land on `/dashboard`.

This user has the `admin` role, so it can reach every workspace and the `/admin/*` pages.

### 2.2 Real path — register a fresh account

1. Go to http://localhost:3000/register
2. Use any email (e.g. `tester1@example.com`) and a password meeting the strength requirement shown on the form.
3. Submit. You should be logged in and land on `/dashboard` **immediately** — this app sets `email_verified=True` at registration and does not gate login on email OTP (SMTP is optional; if unconfigured, the OTP email is silently skipped and nothing blocks you).
4. **Check:** ☐ Registration succeeds ☐ You land on the dashboard without needing to click a verification link.

---

## 3. Per-workspace test cases

Demo documents already exist in the repo at `docs/demo-documents/` — synthetic files built specifically to exercise each workspace. Use them.

**General pattern for every workspace below:**
1. Open the workspace from the sidebar.
2. Click **New Chat**.
3. Upload the listed file(s) (drag-and-drop or the upload button).
4. Wait for the document status to reach **READY** (it cycles `UPLOADED → PROCESSING → EXTRACTED → INDEXING → READY`; watch the doc's status badge).
5. Type the prompt(s) listed, or click the button listed, and check the box.

---

### 3.1 General

Route: `/general` · File(s): `meridian_employee_handbook.pdf`, `meridian_gridwatch_spec.pdf`, `scanned_site_inspection_memo.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Upload `meridian_employee_handbook.pdf`. Wait for READY. | ☐ Status reaches READY (not FAILED) |
| 2 | Prompt: `What is the company's policy on annual leave?` | ☐ Grounded answer streams in token-by-token ☐ Cites a page number ☐ A trust/Veritas score appears after the answer |
| 3 | Prompt: `What is the CEO's home address?` (not in the document) | ☐ The system **refuses** or says it can't find this rather than inventing an answer |
| 4 | Upload `scanned_site_inspection_memo.pdf` (this one is image-only — no selectable text). Wait for READY. | ☐ Status reaches READY — this proves OCR ran (PaddleOCR/Docling), not raw text extraction |
| 5 | Prompt: `Summarize the site inspection findings.` | ☐ Answer reflects the scanned document's content, with a page citation |
| 6 | Open the **Trust score** on any answer (click to expand). | ☐ Shows a breakdown (retrieval consensus, grounding, etc.), not just a bare number |

### 3.2 HR

Route: `/hr` · File(s): `resume_priya_sharma.pdf`, `resume_arjun_mehta.pdf`, `resume_sara_iyer.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Click **Set JD Context**, paste a short backend-engineer JD above the marker line the prefill gives you, and send. | ☐ Response acknowledges/uses the JD |
| 2 | Click **Batch Upload**, select all three resume PDFs at once. Wait for all to reach READY. | ☐ All three process without error |
| 3 | Click **View Rankings**. | ☐ A ranking panel opens showing all three candidates scored/ordered against the JD |
| 4 | Click **Export Candidates**, then use the panel's export button. | ☐ A CSV file downloads |
| 5 | Prompt: `Which candidate has the strongest backend experience and why?` | ☐ Grounded answer referencing specific resume content with citations |

### 3.3 Legal

Route: `/legal` · File: `meridian_vendor_msa.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Upload `meridian_vendor_msa.pdf`. Wait for READY. | ☐ Status reaches READY |
| 2 | Click **Risk Report** (or **Risk Mode**). | ☐ Risk panel opens and populates — this contract has a deliberately uncapped-liability clause, so expect it flagged as high severity |
| 3 | Click **Contract Mode**. | ☐ Response extracts and categorizes clauses with page references |
| 4 | Click **Clause Library**. | ☐ Response groups clauses by category (payment, IP, termination, liability, confidentiality) with quotes and pages |
| 5 | Prompt: `Summarize the termination conditions.` | ☐ Grounded, cited answer |

### 3.4 Finance

Route: `/finance` · File(s): `meridian_annual_report_fy2025.pdf`, `meridian_financials_fy2025_clean.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Upload `meridian_financials_fy2025_clean.pdf`. Wait for READY. | ☐ Status reaches READY |
| 2 | Click **Ratios** (or **Verify**). | ☐ Ratio panel opens showing computed ratios (liquidity, profitability, leverage, etc.) — **these numbers come from Python, not the LLM**, so they should be internally consistent (e.g. current ratio = current assets ÷ current liabilities, matching the source figures) |
| 3 | Click **Extraction Mode**. | ☐ Response lists key figures with exact page/row citations |
| 4 | Upload `meridian_annual_report_fy2025.pdf` as a second document, wait for READY, then look for a **Compare** action (or ask directly, see next row). | ☐ Both documents show READY |
| 5 | Prompt: `Compare the two financial documents and highlight any discrepancies.` | ☐ Answer references both documents by name with citations |
| 6 | Check for a **proactive insights** card/notification (may appear automatically after ingestion, or check `/dashboard`). | ☐ At least one insight is surfaced without you asking for it |

### 3.5 Study

Route: `/study` · File: `os_process_scheduling_chapter.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Upload `os_process_scheduling_chapter.pdf`. Wait for READY. | ☐ Status reaches READY |
| 2 | Click **Flashcard Mode**. | ☐ A deck is created/shown with flashcards generated from the chapter |
| 3 | Review a few cards and mark them (e.g. "know it" / "don't know it" or similar SM-2 style buttons). | ☐ The next-review scheduling visibly reacts (card moves out of the immediate queue, or a "next review" date appears) |
| 4 | Look for a **Quiz** action/button and take a short quiz. | ☐ Quiz generates questions from the document ☐ Submitting shows a score |
| 5 | Prompt (tutor chat): `Explain round-robin scheduling like I'm a beginner.` | ☐ Grounded answer, cites the chapter |
| 6 | Click **Pomodoro Timer**. | ☐ A timer UI opens/starts |

### 3.6 Research

Route: `/research` · Files: `paper_attention_cnn_retina.pdf`, `paper_cnn_attention_null_result.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Upload both papers. Wait for both to reach READY. | ☐ Both READY |
| 2 | Click **Review Mode** (or send the prefilled synthesis prompt). | ☐ Response synthesizes both papers by theme and **flags that they disagree** — Paper A says attention helps, Paper B reports a null result. This is the built-in contradiction-detection test case. |
| 3 | Click **Find Gaps**. | ☐ Gap-analysis panel opens listing unanswered questions across the two papers |
| 4 | Click **Citation Mode** (or **Export Citations**). | ☐ Citation panel opens; try exporting — pick at least one format (APA/MLA/IEEE/BibTeX) and confirm it downloads/copies correctly |
| 5 | Send a prompt to `/research/deep-research` (there should be a "Deep Research" action or similar in the UI) with a question like `What does current literature say about attention mechanisms in CNNs beyond these two papers?` | ☐ It runs and streams a response grounded in the two uploaded papers. **Known limitation — do not treat as a bug:** the web-search step of this pipeline is not wired to a live API key in this build, so the response will be based on document evidence only, not fresh web results. This is expected; see `docs/deployment/PROJECT_AUDIT_AND_DEPLOYMENT.md` §10. |

### 3.7 Exam

Route: `/exam` · File: `photosynthesis_lesson_notes.pdf`

| # | Action | Expect |
|---|---|---|
| 1 | Upload `photosynthesis_lesson_notes.pdf`. Wait for READY. | ☐ Status reaches READY |
| 2 | Click **Generate Paper**. A configuration panel opens — set question count/types and confirm. | ☐ A grounded exam paper is generated with questions traceable to the source notes |
| 3 | Click **Answer Key**. | ☐ Answer key panel opens showing correct answers for the generated paper |
| 4 | Click **Extract Tables** (if the notes contain any table/diagram data) or try it on a Finance PDF instead if this document has no tables. | ☐ Table extraction panel opens and shows structured data |
| 5 | Click **Edit Paper**. | ☐ A rich-text editor opens over the generated paper and lets you make changes |
| 6 | Click **Export DOCX**. | ☐ A `.docx` file downloads |
| 7 | Click **Question Bank**. | ☐ Response generates ~50 varied questions (MCQ/short/long) tagged with Bloom's level |
| 8 | Ask the exam workspace a question with **no uploaded document context**, e.g. open a brand-new chat with nothing uploaded and ask `Generate a paper on quantum computing.` | ☐ The system **honestly refuses** rather than generating an ungrounded paper — this is a headline feature ("honest refusal") |

---

## 4. Cross-cutting checks

These aren't workspace-specific — run them once after you've been through Part 3.

| # | Check | How | Expect |
|---|---|---|---|
| 1 | **Background worker is actually processing** | Watch the `worker` container's logs while you upload any document | ☐ You see task pickup/completion log lines, not silence |
| 2 | **Sessions persist across reload** | Refresh the browser mid-chat | ☐ Chat history and uploaded documents are still there |
| 3 | **Logout / login roundtrip** | Log out, log back in with the same account | ☐ Works cleanly, lands back on dashboard |
| 4 | **Bookmarks** | From any answer, bookmark it (if the UI offers this), then check `/bookmarks` | ☐ The bookmarked item appears |
| 5 | **Account/settings page** | Visit `/account` and `/settings` | ☐ Both load without error, show your user info |
| 6 | **Billing page loads** | Visit `/billing` | ☐ Page loads (Razorpay is disabled by default in dev, so no real checkout is expected — just confirm it doesn't crash) |
| 7 | **Rate limiting works, doesn't over-trigger** | Send ~5 normal queries in a row on `/general` | ☐ None of them get blocked (limit is 30/minute) |
| 8 | **Mobile/responsive sanity check** | Resize the browser window narrow, or use DevTools device mode | ☐ Sidebar collapses/adapts, chat is still usable |
| 9 | **No console errors** | Open browser DevTools → Console while using any workspace | ☐ No red errors during normal use (warnings are fine) |
| 10 | **Health endpoint under load** | While a document is processing, hit `curl.exe http://localhost:8000/api/v1/health` | ☐ Still returns `{"api":"ok","db":"ok","redis":"ok"}` |

---

## 5. What to do with the results

- **Everything checked, no surprises:** you're ready to move to the git push + deployment steps. Say so and we'll proceed.
- **Something is unchecked or behaves differently than described:** note which numbered item, what you saw instead, and any error text/screenshot. Bring that back here — a real defect found by manual testing gets fixed before anything is pushed, per your instruction.
- **A "known limitation" box was checked as expected** (e.g. Research §3.6 row 5 web-search): that's not a bug, no action needed.

**Do not push to GitHub or trigger a deployment until you've been through this guide yourself.** That was the whole point of writing it.
