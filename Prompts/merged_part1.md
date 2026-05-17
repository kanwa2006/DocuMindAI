# DocuMindAI — UNIFIED MASTER IMPLEMENTATION PROMPT
# VERSION: CONSOLIDATED v1.0 (Merged from UI-based v2 + Execution-oriented v3)
# MODEL: claude-sonnet-4-6
# EXECUTION MODE: Fully Autonomous — Agentic Codebase Execution
# TOOL: Antigravity (auto file read, edit, create, run commands)
# INSTRUCTION: Execute ALL phases in dependency order automatically.
#              After each phase, run verification AND checkpoint before continuing.
#              Scan codebase first, then execute. Never skip verifications.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MERGER ANALYSIS — READ BEFORE EXECUTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MERGED SAFELY:
  ✓ Phase 0 emergency bug fixes (identical across both files — deduplicated)
  ✓ Stable systems protection list (identical — single authoritative copy)
  ✓ Technology stack (identical — single copy)
  ✓ LocalCrossEncoder reranker implementation (identical code — single copy)
  ✓ bge-m3 embedding model configuration (identical — single copy)
  ✓ Conversation history in LLM context (identical — single copy)
  ✓ Stop/Regenerate button logic (identical — single copy)
  ✓ Retrieval cache (Redis, identical — single copy)
  ✓ Circuit breaker class (identical — single copy)
  ✓ JSON logging (identical — single copy)
  ✓ DB connection pool settings (identical — single copy)
  ✓ Workspace disclaimers backend logic (identical — single copy)
  ✓ Workspace retrieval config (identical — single copy)
  ✓ JWT shareable links + SharedSession model (identical — single copy)
  ✓ Export quality improvements PDF/DOCX (identical — single copy)
  ✓ Design token philosophy (identical — merged into single philosophy block)
  ✓ PII redactor utility (identical — single copy)
  ✓ SM-2 spaced repetition backend (identical — single copy)
  ✓ Financial ratio computation (Python, not LLM — single copy)
  ✓ Citation format export for Research (identical — single copy)

POTENTIAL SEMANTIC CONFLICTS (RESOLVED):
  CONFLICT 1 — Session expired handling:
    UI-based file:    window.location.href redirect inside apiFetch on 401+refresh failure
    Execution file:   Custom event "session:expired" → SessionExpiredOverlay modal overlay
    RESOLUTION:       Execution file approach PRESERVED (stricter, no hard redirect,
                      better UX with save-state overlay before redirect, prevents data loss)
    BEHAVIORAL IMPACT: apiFetch dispatches custom event; SessionExpiredOverlay catches it.

  CONFLICT 2 — Error boundary UI richness:
    UI-based file:    Single "Reload Page" button, minimal error display
    Execution file:   "Reload Page" + "Go to Home" buttons, code-style error box, support note
    RESOLUTION:       Execution file version PRESERVED (stricter, safer, more recovery paths)

  CONFLICT 3 — Legal workspace disclaimer rendering:
    UI-based file:    Disclaimer appended to each AI response body as final chunk
    Execution file:   Fixed amber banner ALWAYS visible, NEVER dismissable + response disclaimer
    RESOLUTION:       BOTH preserved — response disclaimer still sent as final chunk AND
                      persistent amber banner always shown in Legal workspace.
                      Execution file's "never dismissable" rule is preserved.

  CONFLICT 4 — Phase numbering:
    UI-based file:    Phases 0→1→2→2.5→3→4→5(workspace features)→6(infra)→7(export)
    Execution file:   Phases 0→1→2→2.5→3→4→5(welcome/onboarding)→6-T/H/S/F/L/R→7(infra)→8(export+a11y)
    RESOLUTION:       Execution file numbering ADOPTED. Workspace welcome states are
                      Phase 5 (not embedded in Phase 2.5). Infra is Phase 7. Export+a11y
                      is Phase 8. This ordering is safer (observability before export).

  CONFLICT 5 — Workspace Dropdown trigger icon vs execution:
    UI-based file:    Shows workspace icon only
    Execution file:   Shows [icon 16px] [workspace name 14px weight 500] [chevron 12px]
    RESOLUTION:       Execution file version PRESERVED (more specific, better UX)

  CONFLICT 6 — SidebarSkeleton row count:
    UI-based file:    6 rows of skeleton items
    Execution file:   8 rows of skeleton items (more realistic)
    RESOLUTION:       8 rows (execution file — stricter/more complete)

PRESERVED CRITICAL CONSTRAINTS:
  ✓ Stable system list — enforced throughout, NEVER modify these files
  ✓ bcrypt over SHA256 — enforced in Phase 0, verified in Final Phase
  ✓ No secrets in version control — enforced in Phase 0 Task 0.3
  ✓ Environment-aware secure cookie (IS_PRODUCTION flag) — enforced Phase 0
  ✓ CSRF exempt paths — enforced Phase 0, cannot be weakened
  ✓ NOT NULL document fields always computed — enforced Phase 0
  ✓ Workspace disclaimers NEVER dismissable in Legal workspace — enforced Phase 6-L
  ✓ Answers ONLY from documents (grounding constraint) — enforced at system level
  ✓ PII never in plain logs — enforced Phase 7 logging config + HR tasks
  ✓ Rate limits on all auth and AI endpoints — enforced Phase 7 Task 7.1
  ✓ Circuit breaker on ALL LLM calls — enforced Phase 7 Task 7.2
  ✓ Quiz answers stripped before frontend delivery (anti-cheat) — enforced Phase 6-S
  ✓ Financial ratios computed by Python, NOT LLM (numerical integrity) — Phase 6-F
  ✓ Cache failure never breaks request (silent fallthrough) — Phase 4 Task 4.9
  ✓ prefers-reduced-motion respected — Phase 2.5 motion.css
  ✓ WCAG 2.1 AA accessibility — enforced Phase 8 Task 8.7
  ✓ Token usage tracked per query — Phase 7 Task 7.4
  ✓ alembic migrations run for every model change — enforced throughout
  ✓ Workspace-specific retrieval config applied per query — Phase 4 Task 4.8

REMOVED REDUNDANCIES:
  REMOVED: Duplicate "DocuMindAI is NOT a general chatbot" philosophy block
    WHY SAFE: Preserved once in PROJECT CORE PURPOSE. No behavioral loss.
  REMOVED: Duplicate GOLDEN RULES / EXECUTION RULES sections
    WHY SAFE: Merged into single EXECUTION RULES block. All 10 rules preserved.
  REMOVED: Duplicate stable systems list (appeared in both files)
    WHY SAFE: Single authoritative STABLE SYSTEMS block preserved.
  REMOVED: Duplicate technology stack block
    WHY SAFE: Single authoritative TECHNOLOGY STACK block preserved.
  REMOVED: Duplicate LocalCrossEncoder implementation (identical in both files)
    WHY SAFE: Single implementation preserved in Phase 4 Task 4.1.
  REMOVED: Duplicate verification checkpoint commands repeated within same phase
    WHY SAFE: Checkpoint commands merged; all unique commands preserved.
  REMOVED: Duplicate workspace definitions (appeared in both WorkspaceDropdown and
    WORKSPACE_CONFIG objects with same content)
    WHY SAFE: Single WORKSPACE_CONFIG with full definitions in Phase 2 Task 2.1.
  REMOVED: Redundant preamble from execution-oriented file ("PASTE THIS WITH EVERY PHASE")
    WHY SAFE: This prompt is used autonomously (full document at once), so the
    per-phase preamble pattern is replaced by global preamble at top.
  REMOVED: Duplicate Final Output Report format (both files had identical table)
    WHY SAFE: Single report format preserved in FINAL OUTPUT REPORT section.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT CORE PURPOSE — READ THIS FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DocuMindAI is NOT a general chatbot.
DocuMindAI is NOT competing with ChatGPT.

DocuMindAI is: "Trusted document intelligence with grounded answers."

THE REAL PROBLEM BEING SOLVED:
  Most AI tools hallucinate when given documents.
  They mix document content with internet memory.
  Professionals cannot verify the answers.
  This is dangerous in legal, finance, research, and education.

CORE PHILOSOPHY:
  "The AI must answer ONLY from the provided documents —
   never from random internet memory."

Every implementation decision must prioritize (in this order):
  1. Retrieval quality — the system's #1 moat
  2. Citation accuracy — shows source page + text
  3. Upload reliability — smooth, predictable, no hanging
  4. Clean UI consistency — professional, not cluttered
  5. Stability — boring and stable beats feature-rich and broken

Every phase you execute must serve these 5 goals.
Never add complexity that does not serve these goals.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEFORE ANYTHING — SCAN THE FULL CODEBASE FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before writing a single line of code, read and understand these files.
Output status for each file: ✓ found | ✗ missing | ⚠ has issues

Backend (read all):
  backend/app/main.py                                  ✓/✗/⚠
  backend/app/core/config.py                           ✓/✗/⚠
  backend/app/core/security.py                         ✓/✗/⚠
  backend/app/core/middleware.py                       ✓/✗/⚠
  backend/app/api/v1/endpoints/auth.py                 ✓/✗/⚠
  backend/app/api/v1/endpoints/csrf.py                 ✓/✗/⚠
  backend/app/api/v1/endpoints/documents.py            ✓/✗/⚠
  backend/app/api/v1/endpoints/query.py                ✓/✗/⚠
  backend/app/api/v1/endpoints/chats.py                ✓/✗/⚠
  backend/app/api/v1/endpoints/exams.py                ✓/✗/⚠
  backend/app/api/v1/endpoints/hr.py                   ✓/✗/⚠
  backend/app/api/v1/endpoints/legal.py                ✓/✗/⚠
  backend/app/api/v1/endpoints/finance.py              ✓/✗/⚠
  backend/app/api/v1/endpoints/study.py                ✓/✗/⚠
  backend/app/api/v1/endpoints/research.py             ✓/✗/⚠
  backend/app/api/v1/endpoints/export.py               ✓/✗/⚠
  backend/app/api/v1/endpoints/health.py               ✓/✗/⚠
  backend/app/models/org.py                            ✓/✗/⚠
  backend/app/models/document.py                       ✓/✗/⚠
  backend/app/services/retrieval_service.py            ✓/✗/⚠
  backend/app/services/grounding_service.py            ✓/✗/⚠
  backend/app/services/reranker_service.py             ✓/✗/⚠
  backend/app/services/llm_service.py                  ✓/✗/⚠
  backend/app/services/embedding_service.py            ✓/✗/⚠
  backend/app/services/chunking_service.py             ✓/✗/⚠
  backend/app/services/export_engine.py                ✓/✗/⚠
  backend/app/services/ocr_orchestrator.py             ✓/✗/⚠
  backend/app/workers/tasks/document_tasks.py          ✓/✗/⚠
  backend/app/workers/tasks/hr_tasks.py                ✓/✗/⚠
  backend/app/db/session.py                            ✓/✗/⚠
  backend/app/celery_app.py                            ✓/✗/⚠
  backend/requirements.txt                             ✓/✗/⚠
  backend/.env.local (or .env — whichever exists)      ✓/✗/⚠
  docker-compose.yml                                   ✓/✗/⚠

Frontend (read all):
  frontend/src/app/layout.tsx                          ✓/✗/⚠
  frontend/src/app/page.tsx                            ✓/✗/⚠
  frontend/src/app/login/page.tsx                      ✓/✗/⚠
  frontend/src/app/exam/page.tsx                       ✓/✗/⚠
  frontend/src/app/hr/page.tsx                         ✓/✗/⚠
  frontend/src/app/study/page.tsx                      ✓/✗/⚠
  frontend/src/app/research/page.tsx                   ✓/✗/⚠
  frontend/src/app/legal/page.tsx                      ✓/✗/⚠
  frontend/src/app/finance/page.tsx                    ✓/✗/⚠
  frontend/src/components/LayoutWrapper.tsx            ✓/✗/⚠
  frontend/src/components/Sidebar.tsx                  ✓/✗/⚠
  frontend/src/components/WorkspaceUI.tsx              ✓/✗/⚠
  frontend/src/components/EnterpriseDocumentViewer.tsx ✓/✗/⚠
  frontend/src/lib/api.ts                              ✓/✗/⚠
  frontend/.env.local (or .env — whichever exists)     ✓/✗/⚠
  frontend/package.json                                ✓/✗/⚠
  frontend/src/app/globals.css                         ✓/✗/⚠
  frontend/tailwind.config.ts                          ✓/✗/⚠

After reading all files, proceed automatically to execute all phases below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTION RULES — NEVER VIOLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.  Execute ALL phases in order: 0→1→2→2.5→3→4→5→6-T→6-H→6-S→6-F→6-L→6-R→7→8→Final
2.  At every CHECKPOINT marker: run verification, report status, THEN continue.
    This prevents compounding failures.
3.  If a file doesn't exist yet, CREATE it.
4.  If a file exists, EDIT only what needs to change.
    NEVER rewrite a stable file from scratch.
5.  After each phase, run verification automatically:
      backend: python -c "from app.main import app; print('OK')"
      frontend: npx tsc --noEmit (TypeScript check)
6.  If verification fails, fix the error before proceeding to the next phase.
7.  NEVER break working functionality to add new features.
8.  NEVER delete working code to add new features.
9.  Log every file changed: [MODIFIED], [CREATED], [SKIPPED], or [BONUS FIX].
10. If you find a bug not in the plan: fix it, log as [BONUS FIX].
11. NEVER touch STABLE SYSTEMS listed below.
12. NEVER hardcode secrets, API keys, or credentials.
13. ALWAYS add error handling and loading states to every UI component.
14. ALWAYS write TypeScript — no `any` types unless genuinely unavoidable.
15. ALWAYS think before writing. State your plan in one sentence, then execute.
16. Each phase is a bounded slice — complete it FULLY before moving on.
17. Run verification after every TASK, not only at phase end.
18. ALWAYS scan the file first, understand it, then make minimal targeted edits.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STABLE SYSTEMS — NEVER MODIFY THESE FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These files are architecturally correct. Do NOT touch:
  backend/app/services/retrieval_service.py
  backend/app/services/grounding_service.py
  backend/app/services/ocr_orchestrator.py
  backend/app/services/llm_service.py       ← ADD CircuitBreaker in Phase 7 only
  backend/app/services/embedding_service.py ← verify model name only, in Phase 4
  backend/app/services/chunking_service.py
  backend/app/workers/tasks/document_tasks.py
  backend/app/celery_app.py
  backend/app/core/config.py  ← read only; ADD to it, NEVER delete existing lines
  docker-compose.yml          ← read-only reference

For these files: route through their existing APIs only.
Never rewrite internals. Never delete existing lines.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIRMED TECHNOLOGY STACK (DO NOT DEVIATE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Frontend:
  Next.js (App Router) | React | TypeScript
  TailwindCSS | React Markdown | TanStack Virtual
  react-hot-toast | recharts (charts in dashboard)

Backend:
  FastAPI | Python | SQLAlchemy (async) | Alembic
  Celery | Redis | PostgreSQL | Pydantic v2

AI Stack:
  PRIMARY LLM: Gemini 2.5 Flash (env-controlled)

  EMBEDDINGS — Use in this priority order:
    PRIMARY:   BAAI/bge-m3 (568M params, multilingual,
               dense+sparse+multi-vector, 8192 token ctx)
               Loaded via: SentenceTransformer("BAAI/bge-m3")
    FALLBACK:  nomic-embed-text v1.5 (274MB, CPU-only,
               8192 ctx, MRL support)
               Only if bge-m3 is too slow on available hardware.

  RERANKER:
    cross-encoder/ms-marco-MiniLM-L-6-v2
    (via sentence-transformers CrossEncoder class)
    ~80MB download on first run — expected.

  VECTOR SEARCH:
    PRIMARY:   FAISS (current — keep as-is)
    UPGRADE PATH: Qdrant (add client, migrate in Phase 4)

  SPARSE RETRIEVAL:
    BM25 (keep current implementation)

Document Processing:
  PRIMARY PDF (native/selectable text):
    pymupdf4llm → LLM-ready Markdown in 0.12s, no GPU needed
    pip install pymupdf4llm

  FALLBACK PDF (scanned/image-heavy):
    Docling → handles tables, formulas, complex layouts
    PaddleOCR → multilingual OCR fallback

  KEEP:
    PyMuPDF (low-level operations)
    OpenCV (image preprocessing)

Export:
  fpdf2 (PDF export) | python-docx (DOCX export)

Infrastructure:
  Docker Compose | Railway (backend) | Vercel (frontend)
  Redis | PostgreSQL | Supabase (production DB + Storage)
  Upstash Redis (free tier, serverless Redis for production)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN SYSTEM PHILOSOPHY — READ BEFORE ALL UI WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DocuMindAI's visual identity: "Calm authority with precision."

NOT: Flashy startup gradients. NOT: Generic AI purple. NOT: ChatGPT clone.
YES: The product a partner at McKinsey would trust with client data.
YES: The tool a judge would use to review a 400-page contract.
YES: Quiet confidence — dense when organised, precise in typography.

Design principles governing EVERY UI decision:
  1. Restraint over decoration — every element earns its place
  2. Density is fine when organised — legal/finance users deal with dense
     documents; the UI should match their mindset
  3. Precision typography — spacing, sizing, and weight carry more meaning
     than color in a document-intelligence product
  4. Motion serves information — animations communicate state changes,
     never decorate for attention-seeking
  5. Trust through consistency — the same interaction pattern everywhere;
     no surprises, no "clever" exceptions

Visual personality:
  DARK MODE PRIMARY — most professionals work in dark mode
  Dark: deep near-black (#0C0C0E) not pure black
  Light: off-white (#FAFAFA) not pure white
  Monochromatic base (blacks, whites, grays) + ONE accent color
  THE SINGLE ACCENT: hsl(220, 90%, 60%) — precise instrument blue.
  Not "tech blue." Not "AI purple." The blue of a well-calibrated
  scientific instrument. Used sparingly on interactive elements only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROVED LAYOUT ARCHITECTURE (LOCKED — DO NOT DEVIATE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LAYER 1 — NAVBAR (fixed top, always 52px, never scrolls)
  Left:   Logo (clickable → "/") → Sidebar toggle (≡ icon)
  Center: Workspace Dropdown — THE ONLY workspace navigation in the app
  Right:  Share (↑) → Dark/Light toggle → Profile Avatar Dropdown
  z-index: 50 (always above everything else)

LAYER 2 — LEFT SIDEBAR (260px wide, collapsible to 0px)
  Top:    NEW CHAT button (full width) → SEARCH CHATS field
  Middle: Chat/Session history grouped by date (Today/Yesterday/Last 7 days/Month-Year)
          Each item: [workspace icon] [session title] [...context menu]
          WORKSPACES ARE NEVER LISTED HERE — sessions only
  Bottom: All Sessions → Settings → Account → Help & Feedback

LAYER 3 — MAIN AREA (only this zone changes per workspace)
  Sub-zone A: Breadcrumb (Workspace → Session name)
  Sub-zone B: AI streaming response with citations and trust badge
  Sub-zone C: Document bar (horizontal scroll, 56px) — above input bar
  Sub-zone D: Input bar (fixed at bottom)

LAYER 4 — BOTTOM INPUT BAR (adapts per workspace)
  Row 1: Document chips (horizontal scroll) + "+ Add Documents" button
  Row 2: Attach (📎) → Textarea (auto-expand, min 44px, max 200px)
         → Templates (▼) → Stop/Send button (⌘↵)
  Row 3: Workspace-specific action buttons (varies per workspace)
  Below: Sticky disclaimer pill (Legal and Finance workspaces only)

OPTIONAL LAYER 5 — DOCUMENT PREVIEW PANEL (slides from right, 380px)
  Opens when: clicking "👁 Preview" on document chip OR clicking a citation
  Does NOT block the chat area — chat shrinks to accommodate
  Closes with ✕ button or Escape key

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 — EMERGENCY BUG FIXES + LOGIN & AUTH UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Make the entire platform functional end-to-end. Nothing else works
         until these bugs are fixed. Login must work. Upload must work.
         Auth pages must render.
ESTIMATED TIME: 3–5 hours | RISK: Low (fixes + new auth pages only)

─────────────────────────────────────────────────────────────────────
PHASE 0 — INTERFACE DESIGN SPECIFICATION (Auth Pages)
─────────────────────────────────────────────────────────────────────

LOGIN PAGE DESIGN (frontend/src/app/login/page.tsx)
Layout: Two-column split (50/50 on desktop, single column on mobile)

LEFT COLUMN — Brand Panel (hidden on mobile):
  Background: gradient from hsl(220, 90%, 60%) to hsl(220, 70%, 45%)
  Content centered vertically:
    DocuMindAI logo (white, large — use Logo component from Phase 2.5)
    Tagline: "Trusted document intelligence. Grounded answers."
      Font: Instrument Serif italic, 28px, white, centered
    Three trust points with checkmark icons:
      ✓  Answers only from your documents — never hallucinated
      ✓  Every answer cites the exact source page
      ✓  Works for Legal, Finance, Research, Education
    Each point: 14px DM Sans, white/90%, left-aligned
    Bottom: abstract document illustration SVG (no external image)

RIGHT COLUMN — Login Form:
  Background: var(--surface-base)
  Padding: 48px (desktop), 24px (mobile)
  Content max-width: 380px, centered in column

  Top of form:
    "Welcome back" — Instrument Serif, 28px, text-primary
    "Sign in to your workspace" — DM Sans 14px, text-secondary
    Margin below: 32px

  Form fields:
    Labels: DM Sans 12px, weight 500, uppercase, letter-spacing 0.1em, text-tertiary
    "EMAIL ADDRESS"
    Input: full-width, 44px height, border-radius 8px, border var(--border-default)
           focus: border var(--brand), box-shadow 0 0 0 3px hsl(220 90% 60% / 0.20)
           placeholder: "you@company.com" (text-disabled)
           padding: 0 12px; DM Sans 14px

    "PASSWORD"
    Input: same as above, type=password
           Right side: 👁 toggle (show/hide password), 36×36px touch target
           Show-password toggle does NOT submit form

    Below password: "Forgot password?" link, right-aligned, 13px brand blue

  Submit button:
    Full width, 44px height, border-radius 8px
    Background: var(--brand), color: white
    Text: "Sign In" — DM Sans 15px weight 600
    Hover: brightness(1.08), transition 100ms
    Loading state: spinner replaces text (16px white spinner)
    Disabled when loading

  Divider: "or" with horizontal lines on both sides, text-tertiary 12px

  OAuth buttons (future hooks — show as disabled for now):
    [G] Continue with Google — outlined, full-width, 44px height
    [M] Continue with Microsoft — outlined, full-width, 44px height
    Both: border var(--border-default), disabled opacity 0.5
    Tooltip: "Coming soon"

  Bottom: "Don't have an account? Create one →" — 14px text-secondary
          "Create one" links to /register (brand blue)

  Error states:
    Field error: inline red 13px + ⚠ icon below the failing field
    Global error (wrong password): amber banner at top of form
      "Invalid email or password. Please try again." — 13px amber
    Session expired state (searchParams expired=true):
      Amber info banner: "Your session expired. Please sign in again."

REGISTER PAGE DESIGN (frontend/src/app/register/page.tsx)
  Same two-column layout. LEFT COLUMN: identical brand panel.
  RIGHT COLUMN:
    "Create your account" — Instrument Serif 28px
    "Start with trusted document intelligence" — 14px text-secondary

    Fields (in this order):
      FULL NAME — text input, 44px
      WORK EMAIL — email input, 44px
      PASSWORD — password input with strength indicator below:
        4 segments, 2px tall, border-radius 2px
        Empty = var(--surface-hover)
        1 filled = red (Weak)  2 = amber (Fair)  3 = green (Good)  4 = brand (Strong)
        Label below bar: "Weak / Fair / Good / Strong" in matching color, 12px

    Terms line: "By creating an account, you agree to our Terms of Service
                 and Privacy Policy" — 12px text-tertiary with brand links

    Submit button: "Create Account" — same style as login
    Bottom: "Already have an account? Sign in →"

FORGOT PASSWORD PAGE (frontend/src/app/forgot-password/page.tsx)
  Single centered card, max-width 400px, vertically centered on page
  Card: var(--surface-raised), border var(--border-subtle), radius 16px, padding 40px
  "Forgot your password?" — Instrument Serif 24px, centered
  "Enter your email and we'll send a reset link." — 14px text-secondary, centered
  Email input: full width, same style as login
  "Send Reset Link" button: full-width brand button
  Success state: green banner "Reset link sent to [email]. Check your inbox."
  "← Back to Sign In" — 14px brand link, centered below button

MOBILE AUTH BEHAVIOR:
  Single column; left brand panel hidden completely
  Logo appears above the form card (centered)
  Form card takes full viewport width, 16px horizontal padding
  All inputs: 48px height (larger touch target on mobile)

─────────────────────────────────────────────────────────────────────
PHASE 0 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 0.1 — Fix Port Mismatch
File: frontend/.env.local
Problem: NEXT_PUBLIC_API_URL points to port 8001, backend runs on 8000.
Action: Change 8001 → 8000
Result: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

TASK 0.2 — Fix Redis Port Mismatch
File: backend/.env.local (or backend/.env)
Problem: REDIS_URL=redis://localhost:6379 but docker maps 6380:6379
Action: Change 6379 → 6380
Result: REDIS_URL=redis://localhost:6380/0

TASK 0.3 — Secure API Keys — Remove from Version Control
Files: backend/.env.local
Problem: Gemini API keys and SMTP credentials committed to repo.
Action:
  1. Create backend/.env (if not exists); copy all real secrets there
  2. Add backend/.env to backend/.gitignore
  3. In backend/.env.local replace all key values with placeholders:
       GEMINI_API_KEY=your_gemini_api_key_here
  4. Verify .gitignore contains: .env and .env.local (backend only)
  NOTE: Keep .env.local for non-secret local config values only

TASK 0.4 — Fix Secure Cookie Silently Failing on HTTP Localhost
Files: backend/app/api/v1/endpoints/auth.py
       backend/app/api/v1/endpoints/csrf.py
Problem: secure=True on localhost causes browser to silently drop cookies.
Action: Add environment-aware secure flag to BOTH files:
  import os
  IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

  # In ALL set_cookie() calls in both files:
  response.set_cookie(
    key="token",          # or "csrf_token"
    value=value,
    httponly=True,
    secure=IS_PRODUCTION, # False in dev, True in prod
    samesite="strict",
    max_age=expiry,
    path="/"
  )

TASK 0.5 — Fix CSRF Middleware Blocking Login
File: backend/app/core/middleware.py
Problem: CSRF middleware intercepts POST /auth/login before user has a token.
Action: Add exempt path list:
  CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/csrf/token",
    "/api/v1/health",
    "/api/v1/health/detailed",
  }
  # In middleware dispatch method:
  if request.url.path in CSRF_EXEMPT_PATHS:
    return await call_next(request)
  # else: proceed with CSRF validation as before

TASK 0.6 — Fix User Model Missing workspace_id and roles
File: backend/app/models/org.py
Problem: auth.py reads user.workspace_id and user.roles but User model
         has neither → AttributeError crash on login.
Action:
  1. Add to User model:
       workspace_id = Column(String(50), nullable=True, default="general")
       is_active = Column(Boolean, default=True, nullable=False)

  2. Create UserRole model (in same file if not exists):
       class UserRole(Base):
         __tablename__ = "user_roles"
         id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
         user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"),
                          nullable=False)
         role = Column(String(50), nullable=False, default="user")
         created_at = Column(DateTime, default=datetime.utcnow)
         user = relationship("User", back_populates="roles")

  3. Add to User model:
       roles = relationship("UserRole", back_populates="user",
                            lazy="selectin", cascade="all, delete-orphan")

  4. Run Alembic migration:
       alembic revision --autogenerate -m "add_workspace_id_and_roles_to_user"
       alembic upgrade head

TASK 0.7 — Fix Document Model NOT NULL Violations on Upload
File: backend/app/api/v1/endpoints/documents.py
Problem: verify_upload creates Document without file_hash, mime_type,
         size_bytes which are nullable=False → IntegrityError.
Action: In verify_upload endpoint, compute and pass all required fields:
  import hashlib, os
  from pathlib import Path

  storage_path = verified_data.storage_path
  file_exists = Path(storage_path).exists()

  doc = Document(
    id=...,
    filename=verified_data.filename,
    storage_path=storage_path,
    owner_id=current_user.id,
    workspace_id=verified_data.workspace_id or current_user.workspace_id,
    file_hash=verified_data.file_hash or hashlib.sha256(
      storage_path.encode()).hexdigest(),
    mime_type=verified_data.mime_type or "application/pdf",
    size_bytes=verified_data.size_bytes or (
      os.path.getsize(storage_path) if file_exists else 0)
  )

TASK 0.8 — Add Local Upload Endpoint (No S3 Needed in Dev)
File: backend/app/api/v1/endpoints/documents.py
Problem: Local storage presigned URL returns mock URL that doesn't exist.
Action 1: Update presigned URL endpoint to return local path when dev:
  @router.get("/upload/presigned")
  async def get_presigned_url(workspace_id: str, filename: str,
                               current_user=Depends(get_current_user)):
    if settings.STORAGE_PROVIDER == "local":
      return {
        "upload_url": "/api/v1/documents/upload/local",
        "provider": "local",
        "method": "multipart",
        "workspace_id": workspace_id
      }
    # else: existing S3 presigned logic

Action 2: Add new local upload endpoint:
  @router.post("/upload/local")
  async def upload_local(
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    current_user=Depends(get_current_user)
  ):
    if file.content_type not in ["application/pdf"]:
      raise HTTPException(400, "Only PDF files accepted")
    content = await file.read()
    size = len(content)
    if size > settings.MAX_UPLOAD_MB * 1024 * 1024:
      raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")
    import re, hashlib
    safe_name = re.sub(r'[^\w\.\-]', '_', file.filename)
    file_hash = hashlib.sha256(content).hexdigest()
    unique_name = f"{uuid4().hex}_{safe_name}"
    storage_dir = Path(f"./storage/{workspace_id}")
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_dir / unique_name)
    with open(storage_path, "wb") as f:
      f.write(content)
    return {
      "storage_path": storage_path,
      "filename": file.filename,
      "size_bytes": size,
      "mime_type": "application/pdf",
      "file_hash": file_hash
    }

Action 3: Update frontend/src/lib/api.ts uploadDocument():
  const presigned = await getPresignedUrl(workspaceId, file.name)
  if (presigned.provider === "local") {
    const formData = new FormData()
    formData.append("file", file)
    formData.append("workspace_id", workspaceId)
    const response = await apiFetch("/documents/upload/local", {
      method: "POST",
      body: formData,
      // No Content-Type header — browser sets multipart boundary
    })
    return response.json()
  } else {
    // existing S3 PUT path
  }

TASK 0.9 — Replace SHA256 with bcrypt
Files: backend/requirements.txt
       backend/app/core/security.py
       backend/app/api/v1/endpoints/auth.py (callers)
Problem: SHA256 has no salt and no key stretching — insecure for passwords.
Action:
  1. Add to requirements.txt: passlib[bcrypt]==1.7.4
  2. Rewrite security.py:
       from passlib.context import CryptContext
       pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

       def hash_password(password: str) -> str:
         return pwd_context.hash(password)

       def verify_password(plain_password: str, hashed_password: str) -> bool:
         return pwd_context.verify(plain_password, hashed_password)
  3. Update all callers in auth.py to use new function names.

TASK 0.10 — Fix export.py Broken Import
File: backend/app/api/v1/endpoints/export.py
Problem: References async_session() which doesn't exist → ImportError.
Action: Find every occurrence of async_session() in export.py.
        Replace with: AsyncSessionLocal()
        Verify AsyncSessionLocal is imported from app.db.session.

TASK 0.11 — Create Dev Seed Script
Create: backend/scripts/seed_dev.py
Purpose: Creates a working dev user so login can be tested immediately.
Content:
  import asyncio, sys
  sys.path.insert(0, ".")
  from app.db.session import AsyncSessionLocal
  from app.models.org import User, UserRole
  from app.core.security import hash_password
  from uuid import uuid4
  from datetime import datetime
  from sqlalchemy import select

  async def seed():
    async with AsyncSessionLocal() as db:
      existing = await db.execute(
        select(User).where(User.email == "dev@test.com"))
      if existing.scalar_one_or_none():
        print("Dev user already exists: dev@test.com / devpass123")
        return
      user = User(
        id=uuid4(), email="dev@test.com",
        hashed_password=hash_password("devpass123"),
        full_name="Dev User", workspace_id="general",
        is_active=True, created_at=datetime.utcnow()
      )
      db.add(user)
      role = UserRole(id=uuid4(), user_id=user.id, role="admin")
      db.add(role)
      await db.commit()
      print("✓ Dev user created: dev@test.com / devpass123")

  asyncio.run(seed())

After creating file, run: cd backend && python scripts/seed_dev.py

TASK 0.12 — Install pymupdf4llm + bge-m3 Dependencies
File: backend/requirements.txt
Add these lines (do NOT remove existing entries):
  pymupdf4llm>=0.0.17
  sentence-transformers>=2.7.0
  qdrant-client>=1.9.0
  passlib[bcrypt]==1.7.4

Then run: cd backend && pip install pymupdf4llm sentence-transformers qdrant-client

Create: backend/app/services/pdf_extractor.py
Purpose: Smart PDF extraction router — pymupdf4llm for native, Docling for scanned.
         This does NOT modify ocr_orchestrator.py (stable system). It is a NEW
         upstream router that routes BEFORE ocr_orchestrator is called.
Content:
  """
  Smart PDF extraction router.
  Native PDFs (selectable text): pymupdf4llm → 0.12s, excellent quality.
  Scanned/image PDFs: existing Docling/PaddleOCR pipeline via ocr_orchestrator.
  """
  import fitz  # PyMuPDF
  import pymupdf4llm
  from pathlib import Path
  import logging

  logger = logging.getLogger(__name__)

  EMBEDDING_MODEL_PRIMARY = "BAAI/bge-m3"
  EMBEDDING_MODEL_FALLBACK = "nomic-ai/nomic-embed-text-v1.5"

  def is_native_pdf(pdf_path: str) -> bool:
    """Returns True if PDF has selectable text (native, not scanned)."""
    try:
      doc = fitz.open(pdf_path)
      text_pages = sum(1 for page in doc if len(page.get_text().strip()) > 50)
      doc.close()
      return text_pages / max(len(doc), 1) > 0.7
    except Exception:
      return False

  def extract_native_pdf(pdf_path: str) -> str | None:
    """Extract native PDF to LLM-ready Markdown. Speed: ~0.12s/doc."""
    try:
      md_text = pymupdf4llm.to_markdown(pdf_path)
      logger.info(f"[pymupdf4llm] Extracted {pdf_path}: {len(md_text)} chars")
      return md_text
    except Exception as e:
      logger.warning(f"[pymupdf4llm] Failed on {pdf_path}: {e}. Falling back.")
      return None

  def smart_extract(pdf_path: str) -> dict:
    """
    Returns:
      {"text": str|None, "method": "pymupdf4llm"|"ocr_pipeline",
       "needs_ocr": bool, "quality": "high"|"pending"}
    """
    native = is_native_pdf(pdf_path)
    if native:
      text = extract_native_pdf(pdf_path)
      if text:
        return {"text": text, "method": "pymupdf4llm",
                "needs_ocr": False, "quality": "high"}
    logger.info(f"[pdf_extractor] Routing to OCR pipeline: {pdf_path}")
    return {"text": None, "method": "ocr_pipeline",
            "needs_ocr": True, "quality": "pending"}

Create: backend/app/services/extraction_router.py
  """Workspace-aware extraction routing."""
  from app.services.pdf_extractor import smart_extract
  import logging

  logger = logging.getLogger(__name__)

  WORKSPACE_EXTRACTION_PARAMS = {
    "legal":    {"chunk_pref": "large",  "prefer_full_page": True},
    "research": {"chunk_pref": "large",  "prefer_full_page": True},
    "finance":  {"chunk_pref": "small",  "table_safe": True},
    "hr":       {"chunk_pref": "small",  "table_safe": False},
    "general":  {"chunk_pref": "medium", "prefer_full_page": False},
    "study":    {"chunk_pref": "medium", "prefer_full_page": False},
    "exam":     {"chunk_pref": "medium", "prefer_full_page": False},
  }

  def route_extraction(pdf_path: str, workspace_id: str = "general") -> dict:
    result = smart_extract(pdf_path)
    params = WORKSPACE_EXTRACTION_PARAMS.get(
      workspace_id, WORKSPACE_EXTRACTION_PARAMS["general"])
    result["extraction_params"] = params
    return result

Also update embedding_service.py:
  [READ ONLY — only update if bge-m3 not already configured]
  If MODEL_NAME is NOT "BAAI/bge-m3", update ONLY that string.
  Add startup logs:
    logger.info(f"[embedding] Using model: {MODEL_NAME}")
    logger.info(f"[embedding] Dimension: {model.get_sentence_embedding_dimension()}")
  bge-m3 produces 1024-dim vectors — confirm this in startup logs.

TASK 0.13 — Implement Auth Pages UI
Files:
  frontend/src/app/login/page.tsx      — login UI per design spec above
  frontend/src/app/register/page.tsx   — register UI per design spec above
  frontend/src/app/forgot-password/page.tsx — forgot password UI per design spec above

All pages:
  "use client" client components with controlled inputs
  Use react-hot-toast for success/error notifications
  All form submissions: call apiFetch with proper error handling
  After successful login: redirect to sessionStorage.getItem("returnTo") || "/"
  Password strength meter on register page (client-side, no API call)

─────────────────────────────────────────────────────────────────────
PHASE 0 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
  cd backend && python -c "from app.main import app; print('Backend imports OK')"
  cd backend && python -c "from app.models.org import User, UserRole; print('Models OK')"
  cd backend && python -c "
  from app.core.security import hash_password, verify_password
  p = hash_password('test')
  assert verify_password('test', p), 'bcrypt verify failed!'
  print('bcrypt OK ✓')
  "
  cd backend && python -c "import pymupdf4llm; print('pymupdf4llm OK')"
  cd backend && python -c "
  from app.services.pdf_extractor import smart_extract
  print('PDF extractor OK')
  "
  cd backend && python -c "
  from app.services.extraction_router import route_extraction
  print('Extraction router OK')
  "
  cd backend && python scripts/seed_dev.py
  cd frontend && npx tsc --noEmit && echo "TypeScript OK"
  cd frontend && npm run build && echo "Build OK"

DEFINITION OF DONE — PHASE 0:
  ✅ Backend starts with zero import errors
  ✅ Login page renders correctly on desktop and mobile
  ✅ Register page renders correctly
  ✅ Forgot password page renders correctly
  ✅ dev@test.com / devpass123 logs in successfully
  ✅ Token cookie is set after login (check browser devtools)
  ✅ Upload local endpoint returns 200 for a test PDF
  ✅ bcrypt replaces SHA256 in security.py
  ✅ No API keys visible in .env.local or any tracked file

[CHECKPOINT 0 COMPLETE — Proceeding to Phase 1]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — AUTH HARDENING + ERROR BOUNDARIES + SESSION RECOVERY UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Make authentication bulletproof. Silent refresh. Session expired modal.
         Global error boundary. Never let a broken component crash the whole app.
ESTIMATED TIME: 2–3 hours | RISK: Low | DEPENDS ON: Phase 0 complete

SCAN FIRST:
  frontend/src/lib/api.ts                   ✓/✗/⚠
  frontend/src/app/layout.tsx               ✓/✗/⚠
  frontend/src/app/login/page.tsx           ✓/✗/⚠
  frontend/src/components/LayoutWrapper.tsx ✓/✗/⚠
  backend/app/api/v1/endpoints/auth.py      ✓/✗/⚠

─────────────────────────────────────────────────────────────────────
PHASE 1 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

SESSION EXPIRED OVERLAY:
  When JWT expires and silent refresh fails, show a centered modal overlay:
  Background: rgba(0,0,0,0.6) + backdrop-filter blur(4px) — dims the app
  Card: 400px wide, var(--surface-overlay), border-radius 16px, padding 32px, centered
  Icon: 🔒 at 48px centered
  Title: "Your session has expired" — Instrument Serif 22px, centered
  Body: "For your security, we sign you out after a period of inactivity.
         Your work is saved." — 14px text-secondary, centered
  Button: "Sign In Again →" — full-width brand button, 44px
    On click: save current URL to sessionStorage as "returnTo",
              redirect to /login?expired=true
  CRITICAL: Do NOT use window.alert(). This overlay is the ONLY session expired UI.
  CRITICAL: Component mounted at root layout level, NOT inside ErrorBoundary.

GLOBAL ERROR BOUNDARY UI:
  When a React component crashes, show instead of white screen:
  Full-viewport center layout on var(--surface-base):
  Icon: ⚠ in a 64px amber circle (amber background, amber icon color)
  Title: "Something went wrong" — Instrument Serif 24px, text-primary
  Error code box: shows error.message in monospace, var(--surface-sunken),
                  border var(--border-default), border-radius 8px, padding 12px
  Two buttons side by side:
    "Reload Page" — .btn .btn-primary → window.location.reload()
    "Go to Home" — .btn .btn-ghost → router.push("/")
  Below: "If this keeps happening, please contact support." — 12px text-tertiary

404 PAGE (frontend/src/app/not-found.tsx):
  Full-viewport centered on var(--surface-base):
  "404" — Instrument Serif 96px, brand blue at 0.15 opacity
  "Page not found" — Instrument Serif 28px, text-primary
  "The page you're looking for doesn't exist or has been moved." — 14px text-secondary
  "Go Back Home" — .btn .btn-primary → router.push("/")
  "Or search for what you need" — 13px text-tertiary with search icon

─────────────────────────────────────────────────────────────────────
PHASE 1 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 1.1 — Silent JWT Refresh + 401 Retry
File: frontend/src/lib/api.ts
Add at module level (singleton refresh coordination):
  let isRefreshing = false
  let refreshPromise: Promise<boolean> | null = null

  async function apiFetch(url: string, options: RequestInit = {},
                           _retried = false): Promise<Response> {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}${url}`,
      { ...options, credentials: "include" }
    )
    if (response.status === 401 && !_retried) {
      if (!isRefreshing) {
        isRefreshing = true
        refreshPromise = refreshToken().finally(() => {
          isRefreshing = false
          refreshPromise = null
        })
      }
      const refreshed = await refreshPromise
      if (refreshed) return apiFetch(url, options, true)
      // Refresh failed — dispatch event instead of hard redirect
      window.dispatchEvent(new CustomEvent("session:expired"))
      throw new Error("Session expired")
    }
    return response
  }

  async function refreshToken(): Promise<boolean> {
    try {
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
        { method: "POST", credentials: "include" }
      )
      return r.ok
    } catch { return false }
  }

TASK 1.2 — Session Expired Event System
Create: frontend/src/hooks/useSessionExpiry.ts
  "use client"
  import { useState, useEffect } from "react"

  export function useSessionExpiry() {
    const [sessionExpired, setSessionExpired] = useState(false)

    useEffect(() => {
      const handler = () => setSessionExpired(true)
      window.addEventListener("session:expired", handler)
      return () => window.removeEventListener("session:expired", handler)
    }, [])

    const dismiss = () => {
      setSessionExpired(false)
      sessionStorage.setItem("returnTo", window.location.pathname)
      window.location.href = "/login?expired=true"
    }

    return { sessionExpired, dismiss }
  }

Create: frontend/src/components/SessionExpiredOverlay.tsx
  "use client"
  import { useSessionExpiry } from "@/hooks/useSessionExpiry"

  export function SessionExpiredOverlay() {
    const { sessionExpired, dismiss } = useSessionExpiry()
    if (!sessionExpired) return null
    return (
      <div className="fixed inset-0 z-[200]"
           style={{ background: "rgba(0,0,0,0.6)",
                    backdropFilter: "blur(4px)",
                    display: "flex", alignItems: "center",
                    justifyContent: "center" }}>
        <div className="modal">
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 48 }}>🔒</div>
            <h2 className="text-heading-2" style={{ marginTop: 16 }}>
              Your session has expired
            </h2>
            <p className="text-body-secondary" style={{ margin: "12px 0 24px" }}>
              For your security, we sign you out after a period of inactivity.
              Your work is saved.
            </p>
            <button className="btn btn-primary" style={{ width: "100%" }}
                    onClick={dismiss}>
              Sign In Again →
            </button>
          </div>
        </div>
      </div>
    )
  }

TASK 1.3 — Global React Error Boundary
Create: frontend/src/components/ErrorBoundary.tsx
  "use client"
  import React from "react"

  interface State { hasError: boolean; error?: Error }

  export class ErrorBoundary extends React.Component<
    React.PropsWithChildren<{}>, State
  > {
    constructor(props: any) {
      super(props)
      this.state = { hasError: false }
    }
    static getDerivedStateFromError(error: Error): State {
      return { hasError: true, error }
    }
    componentDidCatch(error: Error, info: React.ErrorInfo) {
      console.error("[ErrorBoundary]", error, info)
    }
    render() {
      if (this.state.hasError) {
        return (
          <div style={{ display: "flex", flexDirection: "column",
                        alignItems: "center", justifyContent: "center",
                        minHeight: "100vh", gap: 16, padding: 32 }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%",
                          background: "var(--warning-bg)", display: "flex",
                          alignItems: "center", justifyContent: "center",
                          fontSize: 28 }}>⚠</div>
            <h1 className="text-heading-1">Something went wrong</h1>
            <pre style={{ fontFamily: "var(--font-mono)", fontSize: 13,
                          background: "var(--surface-sunken)",
                          border: "1px solid var(--border-default)",
                          borderRadius: "var(--radius-md)", padding: 12,
                          maxWidth: 480, overflow: "auto" }}>
              {this.state.error?.message || "An unexpected error occurred."}
            </pre>
            <div style={{ display: "flex", gap: 12 }}>
              <button className="btn btn-primary"
                      onClick={() => window.location.reload()}>
                Reload Page
              </button>
              <button className="btn btn-ghost"
                      onClick={() => { window.location.href = "/" }}>
                Go to Home
              </button>
            </div>
            <p className="text-caption">
              If this keeps happening, please contact support.
            </p>
          </div>
        )
      }
      return this.props.children
    }
  }

TASK 1.4 — Wire Both to Root Layout
File: frontend/src/app/layout.tsx
  import { ErrorBoundary } from "@/components/ErrorBoundary"
  import { SessionExpiredOverlay } from "@/components/SessionExpiredOverlay"

  // In JSX body:
  <ErrorBoundary>
    <SessionExpiredOverlay />
    {children}
  </ErrorBoundary>

TASK 1.5 — Fix LayoutWrapper Dynamic Require
File: frontend/src/components/LayoutWrapper.tsx
Find ALL require() calls for Next.js modules.
Replace every one with static imports at file top:
  import { useRouter, usePathname, useSearchParams } from 'next/navigation'
This prevents hydration mismatches.

TASK 1.6 — Session Expiry Handling on Login Page
File: frontend/src/app/login/page.tsx
  const searchParams = useSearchParams()
  useEffect(() => {
    if (searchParams.get("expired") === "true") {
      toast.error("Your session expired. Please sign in again.")
    }
  }, [])

  // After successful login:
  const returnTo = sessionStorage.getItem("returnTo")
  sessionStorage.removeItem("returnTo")
  router.push(returnTo || "/")

TASK 1.7 — Create 404 Page
Create: frontend/src/app/not-found.tsx
Implement per design spec above. No authentication required for this page.

TASK 1.8 — Verify Backend Refresh Token Endpoint
File: backend/app/api/v1/endpoints/auth.py
Verify POST /auth/refresh exists and:
  Reads refresh_token from httpOnly cookie
  Validates JWT signature and expiry
  Issues new access_token cookie (15 min expiry)
  Issues new refresh_token cookie (7 days, rotated)
  Returns {success: true} on 200
  Returns 401 with {error: "Refresh token expired"} on failure
  Implements: secure=IS_PRODUCTION, httponly=True, samesite="strict"

─────────────────────────────────────────────────────────────────────
PHASE 1 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
  cd frontend && npx tsc --noEmit && echo "TypeScript OK"
  cd frontend && npm run build && echo "Build OK"
  # Manual: open /login?expired=true → amber toast should appear
  # Manual: open a non-existent route → 404 page should render
  # Manual: cause a component error → ErrorBoundary should catch it
  # Manual: let token expire → SessionExpiredOverlay modal appears (no alert())

DEFINITION OF DONE — PHASE 1:
  ✅ Silent refresh works: expired token refreshed without user noticing
  ✅ Session expired overlay shows as modal (NOT window.alert())
  ✅ ErrorBoundary catches crashes → shows friendly UI with two recovery buttons
  ✅ 404 page renders correctly
  ✅ No require() calls for Next.js modules in LayoutWrapper.tsx
  ✅ TypeScript compiles with zero errors

[CHECKPOINT 1 COMPLETE — Proceeding to Phase 2]
