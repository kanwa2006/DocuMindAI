# Screenshot Checklist — DocuMindAI

Screenshots to capture for README, Devpost, GitHub, and LinkedIn.

**Format:** PNG, 1280×720 or 1920×1080, dark mode enabled  
**Location once captured:** `docs/screenshots/`  
**Naming:** `{workspace}-{feature}.png` e.g. `general-streaming.png`

---

## Priority 1 — Core Demo (Must Have)

These are required before any public launch or Devpost submission.

- [ ] **General — Streaming Answer**
  - File: `general-streaming.png`
  - Show: Chat interface mid-stream, text appearing, Veritas score visible
  - Represents: The core product experience

- [ ] **General — Trust Score Detail**
  - File: `general-trust-score.png`
  - Show: Completed answer with Trust Score badge (e.g. 87/100)
  - Represents: The Veritas Trust Engine differentiator

- [ ] **General — Source Citation**
  - File: `general-citation.png`
  - Show: Answer with [Page X] citation and document viewer highlighting the referenced passage
  - Represents: Grounded, citable answers

- [ ] **General — Proactive Insights**
  - File: `general-insights.png`
  - Show: ProactiveInsightsPanel with auto-surfaced document findings
  - Represents: AI that works without prompting

- [ ] **Upload Flow — Processing State**
  - File: `upload-processing.png`
  - Show: Document being processed, status indicator visible
  - Represents: Async OCR pipeline

---

## Priority 2 — Workspace Showcase

- [ ] **HR Workspace — Candidate Ranking**
  - File: `hr-candidates.png`
  - Show: CandidateRankingsPanel with scored candidates visible
  - Caption: *HR workspace — automatic candidate ranking against job descriptions*

- [ ] **Legal Workspace — Contract Risk Flagging**
  - File: `legal-risk.png`
  - Show: LegalRiskPanel or chat with risk-flagged contract clauses
  - Caption: *Legal workspace — clause risk detection and contract analysis*

- [ ] **Finance Workspace — Financial Analysis**
  - File: `finance-analysis.png`
  - Show: FinanceRatioPanel or financial document Q&A
  - Caption: *Finance workspace — ratio extraction and anomaly detection*

- [ ] **Study Workspace — Flashcards**
  - File: `study-flashcards.png`
  - Show: Flashcard interface with SM-2 spaced repetition UI visible
  - Caption: *Study workspace — AI-generated flashcards with spaced repetition*

- [ ] **Research Workspace — Literature Synthesis**
  - File: `research-synthesis.png`
  - Show: Multi-document research synthesis or citation cross-reference view
  - Caption: *Research workspace — literature synthesis and contradiction detection*

- [ ] **Exam Workspace — Paper Generation**
  - File: `exam-paper.png`
  - Show: Generated exam paper with MCQ sections and answer key
  - Caption: *Exam workspace — grounded question paper generation*

---

## Priority 3 — Application UX

- [ ] **Login Page**
  - File: `auth-login.png`
  - Show: Login screen, clean dark design
  - Note: Capture without any credentials visible

- [ ] **Register / OTP Verification**
  - File: `auth-register.png`
  - Show: Email OTP verification screen

- [ ] **Dashboard / Workspace Picker**
  - File: `dashboard.png`
  - Show: Workspace selection overview (all 7 icons visible)
  - Represents: First impression after login

- [ ] **Command Palette**
  - File: `command-palette.png`
  - Show: CommandPalette open with search results
  - Represents: Power-user UX

- [ ] **Sidebar — Chat History**
  - File: `sidebar-chats.png`
  - Show: Sidebar with multiple conversation threads
  - Represents: Session continuity

- [ ] **Settings Page**
  - File: `settings.png`
  - Show: User settings or API configuration
  - Note: No personal data visible

---

## Priority 4 — Advanced Features

- [ ] **Export Modal**
  - File: `export-modal.png`
  - Show: Export options dialog (DOCX, PDF)
  - Represents: Export engine

- [ ] **Dark Mode — Full Interface**
  - File: `dark-mode-overview.png`
  - Show: Full workspace UI in dark mode
  - Represents: Polished dark-mode-first design

- [ ] **Mobile / Responsive View**
  - File: `mobile-responsive.png`
  - Show: Interface at mobile breakpoint (Chrome DevTools mobile view)
  - Represents: Responsive design

- [ ] **Bookmarks Panel**
  - File: `bookmarks.png`
  - Show: Bookmarks list or bookmarked answers
  - Represents: Answer persistence

- [ ] **Admin Panel — Cost / Usage**
  - File: `admin-cost.png`
  - Show: Admin cost or tenant management view (blurred/anonymized data)
  - Represents: Multi-tenancy and admin capabilities
  - **Note:** Blur any real email or personal data

---

## Priority 5 — Infrastructure / Technical

- [ ] **Swagger API Docs**
  - File: `api-swagger.png`
  - Show: `localhost:8000/docs` with endpoint list visible
  - Represents: Developer-friendly API

- [ ] **CI Pipeline — GitHub Actions**
  - File: `ci-green.png`
  - Show: GitHub Actions workflow run with all checks green
  - Represents: Production-grade CI/CD

- [ ] **Docker Compose Startup**
  - File: `docker-compose-up.png`
  - Show: Terminal with `docker-compose up --build` output, all containers starting
  - Represents: Easy deployment

---

## Capture Guidelines

### Technical
- Browser: Chrome (latest), dark mode
- Extensions: Disable all (use incognito mode)
- Zoom: Browser at 100% (no zoom)
- OS: Hide taskbar / dock for cleaner screenshots
- Tool: Chrome DevTools screenshot (⌘+Shift+P → "Capture screenshot") for exact pixel crops

### Content
- Never show real names, emails, or personal data in screenshots
- Use fictional or clearly placeholder document names
- Use realistic but non-sensitive document content (e.g., a public-domain legal text)
- Blur or crop any tokens, API keys, or credentials

### Naming & Storage
```
docs/screenshots/
├── general-streaming.png
├── general-trust-score.png
├── general-citation.png
├── general-insights.png
├── upload-processing.png
├── hr-candidates.png
├── legal-risk.png
├── finance-analysis.png
├── study-flashcards.png
├── research-synthesis.png
├── exam-paper.png
├── auth-login.png
├── dashboard.png
├── command-palette.png
├── export-modal.png
├── dark-mode-overview.png
├── api-swagger.png
└── ci-green.png
```

---

## README Integration

Once captured, add the Priority 1 screenshots to the README Screenshots section:

```markdown
### General Workspace — Streaming Answer with Trust Score
![Streaming Answer](docs/screenshots/general-streaming.png)

### Source Citations — Grounded to the Page
![Source Citations](docs/screenshots/general-citation.png)

### Proactive Insights — Auto-Surfaced Findings
![Proactive Insights](docs/screenshots/general-insights.png)
```

For workspaces, replace the placeholder table with:

```markdown
| Workspace | Screenshot |
|-----------|-----------|
| **General** — Document Q&A | ![](docs/screenshots/general-streaming.png) |
| **HR** — Candidate Ranking | ![](docs/screenshots/hr-candidates.png) |
| **Legal** — Risk Flagging | ![](docs/screenshots/legal-risk.png) |
| **Finance** — Statement Analysis | ![](docs/screenshots/finance-analysis.png) |
| **Exam** — Paper Generation | ![](docs/screenshots/exam-paper.png) |
```
