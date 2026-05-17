━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE 6 — OPUS 4.6 PRE-FLIGHT ARCHITECTURE REASONING

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



⚠ THIS SECTION IS FOR OPUS 4.6 ONLY — READ AND REASON, DO NOT IMPLEMENT.

Sonnet 4.6 reads the OPUS REASONING OUTPUT before beginning Phase 6 tasks.



OPUS TASK: Before any Phase 6 workspace is implemented, reason through

the following questions and produce a written architecture decision

document. Sonnet will receive this document as its Phase 6 execution plan.



OPUS MUST ANSWER ALL OF THESE:



1\. SHARED ABSTRACTIONS — Which code should be written ONCE and reused?

&#x20;  Identify: extract\_structured\_json(), DisclaimerMiddleware, ExportEngine

&#x20;  methods, PIIRedactor scope, StatusTracker pattern. Specify which file

&#x20;  each lives in and which workspaces call it.



2\. ALEMBIC MIGRATION ORDER — Plan the exact migration sequence:

&#x20;  6-H adds: stage to candidates

&#x20;  6-S adds: study\_quizzes, flashcards, next\_review\_date

&#x20;  6-F adds: is\_verified to extracted\_values, financial\_extractions table

&#x20;  6-L adds: legal\_analyses table, clause\_risks table, audit\_trail table

&#x20;  6-R adds: nothing (stateless endpoint, citation data not persisted yet)

&#x20;  Confirm: do any of these conflict? What is the safe execution order?



3\. WORKSPACE PRIORITY — Which workspace has the highest risk of breaking

&#x20;  Phase 4 or Phase 5 work? Which should be implemented last? Justify.



4\. SCOPE DEFERRAL — Which specific tasks in Phase 6 are under-specified

&#x20;  or too complex for this session? List them explicitly. Sonnet will

&#x20;  skip deferred tasks and log them as \[DEFERRED].



5\. EXPORT ENGINE — Task 6-T3 defines DOCX export. Tasks 6-L2 and 6-R1

&#x20;  also need export. Specify the shared ExportEngine methods needed.

&#x20;  Do not duplicate export code across endpoints.



6\. RETRIEVAL CONFIG — Each workspace uses different retrieval parameters

&#x20;  (chunk\_size, overlap, top\_k, similarity\_threshold). Confirm the values

&#x20;  for each workspace. Flag any that conflict with Phase 4 Task 4.8 config.



7\. DISCLAIMER SYSTEM — Legal requires two disclaimers (response-appended

&#x20;  + persistent bottom banner). Finance requires one (response-appended).

&#x20;  Design the shared DisclaimerMiddleware so both are handled in one place.

&#x20;  Specify the middleware location and invocation point.



OPUS OUTPUT FORMAT:

&#x20; ## Architecture Decisions

&#x20; ## Shared Code Plan

&#x20; ## Migration Order

&#x20; ## Workspace Risk Ranking

&#x20; ## Deferred Tasks

&#x20; ## Retrieval Config Table

&#x20; ## Disclaimer Middleware Design



SONNET READS THIS OUTPUT BEFORE BEGINNING PHASE 6-T.

SONNET DOES NOT RE-REASON — IT EXECUTES THE OPUS PLAN.



\[OPUS REASONING COMPLETE → SONNET BEGINS PHASE 6-T]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6 — WORKSPACE FEATURE IMPLEMENTATION (Domain Logic)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Domain-specific backend + frontend features for each workspace.
Teacher marks engine. HR JD matching. Student quiz + spaced repetition.
Finance numerical validation + ratio computation. Legal risk scoring.
Research citations + gap analysis.
ESTIMATED TIME: 8–12 hours | RISK: High | DEPENDS ON: Phase 5 complete
NOTE: Execute ONE WORKSPACE at a time. Do not mix workspaces in one session.
ORDER: 6-T → 6-H → 6-S → 6-F → 6-L → 6-R

════════════════════════════════════════════════════════════════════════
PHASE 6-T — TEACHER WORKSPACE
════════════════════════════════════════════════════════════════════════

INTERFACE DESIGN — TEACHER:
Paper Config Panel (slides from right, 320px, triggered by "Generate Paper" button):
Background: var(--surface-raised), border-left: 1px var(--border-subtle)
Header: "Paper Configuration" DM Sans 16px 600, × close button

&#x20;   Fields (each 40px tall):
      Subject: text input, placeholder "Mathematics / Physics / Chemistry..."
      Board: dropdown \[CBSE, ICSE, State Board, University, JEE/NEET Style]
      Total Marks: number input (default 100)
      Duration: number input + "minutes" label (default 180)
      Difficulty: segmented control \[Easy | Mixed | Hard]
      Bloom's Distribution: 3-handle slider (L1-L2 / L3-L4 / L5-L6),
                            visual bar shows %, all 3 must add to 100%

    Section Builder:
      "Add Section" button → appends a section row:
        Section label input (A/B/C/D) | Type dropdown (MCQ/Short/Long/Case Study)
        Marks input | Count input | × to remove
        Live validation: "Section marks: 80/100 ✓" or "⚠ 110/100 — exceeds total!"
      
    Generate button: .btn .btn-primary full width "Generate Paper →"
    Disabled if marks don't add up (red validation message below button)


Answer Key Toggle: "Show Answer Key" / "Hide Answer Key" button in Teacher header
When shown: right panel or below paper, reveals answer key content

─────────────────────────────────────────────────────────────────────
TASK 6-T1 — Section-Wise Paper Structure Backend
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/exams.py
Add Pydantic models:
class ExamSection(BaseModel):
label: str           # "A", "B", "C"
question\_type: str   # "mcq", "short", "long", "case\_study"
total\_marks: int
count: int

class ExamGenerationRequest(BaseModel):
sections: list\[ExamSection]
subject: str
board: str = "CBSE"   # CBSE | ICSE | IB | Cambridge | State | University | JEE/NEET
total\_marks: int = 100
duration\_minutes: int = 180
instructions: str = ""
difficulty: str = "mixed"  # easy | mixed | hard
bloom\_distribution: dict = {}  # {"L1-L2": 30, "L3-L4": 40, "L5-L6": 30}

&#x20;   @model\_validator(mode="after")
    def validate\_marks(self):
      total = sum(s.total\_marks for s in self.sections)
      if total != self.total\_marks:
        raise ValueError(
          f"Section marks total ({total}) != paper total ({self.total\_marks})")
      return self


Return structure:
{
"paper": { "sections": \[{ "label", "questions": \[
{ "num", "text", "marks", "bloom\_level", "difficulty" }
]}]},
"answer\_key": \[
{ "question\_number", "correct\_answer", "marking\_scheme",
"bloom\_level", "difficulty" }
],
"metadata": { "total\_marks", "duration\_minutes", "board", "bloom\_distribution" },
"generated\_at": "ISO timestamp"
}

─────────────────────────────────────────────────────────────────────
TASK 6-T2 — Answer Key Generation
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/exams.py
Return answer\_key alongside paper in same response (see structure above).
Frontend: "Show Answer Key" toggle button in Teacher workspace header.
When toggled on: render key in a collapsible right panel or below paper.
Answer key shows: question number, correct answer, step-wise marks, Bloom's level.

─────────────────────────────────────────────────────────────────────
TASK 6-T3 — DOCX Export with Academic Formatting
─────────────────────────────────────────────────────────────────────
File: backend/app/services/export\_engine.py
Add generate\_exam\_docx(exam\_data: dict) -> bytes:
Use python-docx:
Page size: A4 (21cm × 29.7cm) with standard margins (2.5cm each)
Header: School Name placeholder | Subject | Date | Max Marks | Duration
Watermark text: "DRAFT" or "FINAL" (configurable via exam\_data.get("watermark"))
Each section heading: "SECTION A — MCQ" — Bold + Underlined style
Instructions block: Italic paragraph after section heading
Questions numbered: 1. / 1a. / (i) as appropriate per question type
Marks in \[square brackets] right-aligned per question: "\[2]"
Answer key on new page after divider line
Footer: "Page N of Total | Generated by DocuMindAI"
Return bytes

Add endpoint: GET /exams/{id}/export/docx → FileResponse

─────────────────────────────────────────────────────────────────────
TASK 6-T4 — Marks Validation Engine
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/exams.py
Create validate\_marks\_allocation(sections, total\_marks) → list\[str] (errors list):
Check 1: sum(s.total\_marks for s in sections) == total\_marks
Check 2: each section's total\_marks is divisible by its count (marks per question)
Check 3: no section has 0 marks or 0 questions
Check 4: bloom\_distribution values sum to 100 (if provided)
Returns: empty list if valid, list of error strings if invalid
Call this BEFORE generating paper. If any errors, return 400 with error list.
Frontend: display errors as red inline messages below Generate button.

─────────────────────────────────────────────────────────────────────
PHASE 6-T VERIFICATION:
cd backend \&\& python -c "from app.api.v1.endpoints.exams import router; print('Exams OK')"

# Manual: generate 100-mark paper with 3 sections → marks add up exactly

# Manual: set mismatched marks → red validation error appears before generation

════════════════════════════════════════════════════════════════════════
PHASE 6-H — HR WORKSPACE
════════════════════════════════════════════════════════════════════════

INTERFACE DESIGN — HR:
Candidate Ranking Panel (activated by "View Rankings" button):
Table view with sortable columns:
Rank | Candidate Name | Score | Skills Match | Experience | Stage | Actions
Each row:
Avatar (initials circle, 32px) | Full name | Score pill (0-100, color-coded)
Skill tags | Stage badge | Action buttons
Score color bands: ≥80 = green, 60-79 = amber, <60 = red/muted
Stage badges with colors:
Applied | Screened | Shortlisted | Interviewed | Offered | Hired | Rejected
Action buttons per row (icon buttons 28px): \[✓ Shortlist] \[✗ Reject] \[📋 View Profile]
Bulk actions bar (when rows checked): "Move X candidates to:" + stage dropdown + Apply
Export CSV button: top right of table

─────────────────────────────────────────────────────────────────────
TASK 6-H1 — Candidate Stage Tracking API
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/hr.py
Add PATCH /hr/candidates/{id}/stage endpoint:
Body: { "stage": "shortlisted" }
Valid stages: \["applied", "screened", "shortlisted",
"interviewed", "offered", "hired", "rejected"]
Add stage column to Candidate model if missing
Run Alembic migration: "add\_stage\_to\_candidate"
Return: updated candidate object with new stage

─────────────────────────────────────────────────────────────────────
TASK 6-H2 — JD-to-Resume Embedding Similarity Score
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/hr.py
In resume analysis endpoint, add semantic similarity computation:

1. Embed the job description text (cache by sha256(jd\_text\[:2000]) to avoid re-embedding)
2. Embed each resume summary (first 512 tokens of resume content)
3. Compute cosine similarity:
from sentence\_transformers import util
similarity = float(util.cos\_sim(jd\_embedding, resume\_embedding))
4. Blend score:
final\_score = round(0.6 \* llm\_score + 0.4 \* similarity \* 100, 1)
5. Include in response:
{ "match\_score": final\_score, "skill\_gaps": \[...], "match\_breakdown": {...} }

─────────────────────────────────────────────────────────────────────
TASK 6-H3 — PII Protection in Logs
─────────────────────────────────────────────────────────────────────
Create: backend/app/utils/pii\_redactor.py
import re

def redact\_pii(text: str) -> str:
text = re.sub(r'\[\\w.+]+@\[\\w.]+.\\w+', '\[EMAIL]', text)
text = re.sub(r'+?\[\\d\\s-()]{10,15}', '\[PHONE]', text)
text = re.sub(r'\\b\\d{3}-\\d{2}-\\d{4}\\b', '\[SSN]', text)  # US SSN pattern
return text

Use in ALL NEW log statements in HR-related code only.
NEVER modify existing stable files (hr\_tasks.py is a stable system).
Only use in new additions made during this implementation.
Example in new code:
from app.utils.pii\_redactor import redact\_pii
logger.info(f"Processing resume: {redact\_pii(resume\_text\[:200])}")

─────────────────────────────────────────────────────────────────────
PHASE 6-H VERIFICATION:
cd backend \&\& python -c "from app.api.v1.endpoints.hr import router; print('HR OK')"

# Manual: upload 3 resumes + JD → ranking shows numerical semantic scores

# Manual: click ✓ Shortlist → stage badge updates to "Shortlisted"

════════════════════════════════════════════════════════════════════════
PHASE 6-S — STUDENT WORKSPACE
════════════════════════════════════════════════════════════════════════

INTERFACE DESIGN — STUDENT:
Flashcard Mode (replaces chat area when active):
Card flip interface: front = question, back = answer
3D CSS flip animation: rotateY 180deg, 300ms, backface-visibility: hidden
Below card: 4 quality rating buttons:
\[😵 Forgot (0)] \[😕 Hard (2)] \[😊 OK (4)] \[🎯 Easy (5)]
Button values map to SM-2 quality scores
Progress bar: "Card 3 of 20 · 5 correct · 2 remaining today"
Exit button: "← Back to chat" — returns to normal chat view

Pomodoro Timer (compact addition to bottom action bar when active):
Compact timer display: shows "25:00" countdown or current phase label
Start / Pause / Reset icon buttons (28px each)
Progress ring: thin SVG circle, brand color fills as time elapses
Phases: "Focus (25 min)" → "Short Break (5 min)" → repeat
After 4 focus sessions → "Long Break (15 min)"
On phase complete: toast.success("Time for a break! ☕") or "Back to work! 📖"
Timer continues running across workspace switches (Web Worker or setInterval + visibility API)

─────────────────────────────────────────────────────────────────────
TASK 6-S1 — Quiz Mode with Scoring
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/study.py
Add POST /study/quiz/generate:
Input: { topic, difficulty, count: 10, doc\_ids, workspace\_id }
LLM generates structured MCQ JSON (prompt LLM to return ONLY JSON):
\[
{
"id": "q1",
"question": "...",
"options": \["A", "B", "C", "D"],
"correct\_index": 2,
"explanation": "...",
"source\_page": 14
}
]
SECURITY: Strip correct\_index BEFORE returning to frontend (anti-cheat)
Store full quiz including correct\_index in study\_quizzes table
Return: { "quiz\_id": "...", "questions": \[...without correct\_index...] }

Add POST /study/quiz/{quiz\_id}/submit:
Input: { "answers": \[{"question\_id": "q1", "chosen\_index": 2}] }
Fetch stored quiz from DB, compare answers
Return:
{
"score": 7, "total": 10, "percentage": 70,
"grade": "B",
"results": \[
{ "question\_id", "correct": bool, "chosen\_index",
"correct\_index", "explanation", "source\_page" }
]
}

─────────────────────────────────────────────────────────────────────
TASK 6-S2 — Spaced Repetition (SM-2 Algorithm)
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/study.py
Add PATCH /study/flashcards/{id}/review:
Input: { "quality": int }  # 0-5 (SM-2 quality rating)
Implement SM-2 algorithm:
# Initial values: interval=1, ease\_factor=2.5
if quality >= 3:
if interval == 1:   new\_interval = 1
elif interval == 6: new\_interval = 6
else:               new\_interval = round(interval \* ease\_factor)
else:
new\_interval = 1  # relearn
new\_ease = max(1.3, ease\_factor + 0.1 - (5-quality) \* (0.08 + (5-quality) \* 0.02))
next\_review\_date = today + timedelta(days=new\_interval)
Update flashcard in DB with new interval, ease\_factor, next\_review\_date
Return: { "next\_review": ISO date, "interval\_days": int, "ease\_factor": float }

Frontend Flashcard Mode: quality buttons submit review to this endpoint.

─────────────────────────────────────────────────────────────────────
TASK 6-S3 — Pomodoro Timer Component
─────────────────────────────────────────────────────────────────────
Create: frontend/src/components/PomodoroTimer.tsx
Local state: minutes=25, seconds=0, isRunning=false, phase="focus"|"short\_break"|"long\_break"
sessionCount state: tracks number of completed focus sessions
Start/Pause/Reset buttons (.btn-icon .btn-ghost .btn-sm)
Progress ring: SVG circle, stroke-dashoffset animation based on time remaining
circumference = 2 \* Math.PI \* r; dashoffset = circumference \* (1 - elapsed/total)
Transitions:
focus (25 min) → short\_break (5 min): after each focus completion
short\_break → focus: after break completion
Every 4th focus session → long\_break (15 min) before next focus
Persist timer state in localStorage: key "pomodoro\_state"
So timer survives workspace switches
On phase complete: toast notification (per phase labels above)

─────────────────────────────────────────────────────────────────────
PHASE 6-S VERIFICATION:
cd backend \&\& python -c "from app.api.v1.endpoints.study import router; print('Study OK')"

# Manual: generate quiz → correct\_index NOT present in frontend response

# Manual: submit quiz answers → get score + explanations back

# Manual: review flashcard with quality=5 → next\_review\_date is further out

# Manual: Pomodoro timer persists across workspace switches

════════════════════════════════════════════════════════════════════════
PHASE 6-F — FINANCE WORKSPACE
════════════════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────────────
TASK 6-F1 — Numerical Integrity Validation
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/finance.py
After LLM response, extract all currency/numerical values via regex:
import re

# Match patterns like: ₹1,23,456 / $1,234.56 / 1234.56 / 12,34,567

number\_pattern = re.compile(
r'\[₹$€£¥]?\\s?\\d{1,3}(?:\[,.]\\d{2,3})\*(?:.\\d{1,2})?')
extracted\_values = number\_pattern.findall(response\_text)

For each extracted value:
Search source chunks for matching text context
Assign confidence:
exact match found in chunk → confidence = 0.95
approximate match (within 5%) → confidence = 0.70
not found in any chunk → confidence = 0.35 → FLAG as unverified

Include in response:
{ "flagged\_values": \[{ "value": str, "confidence": float, "verified": bool }] }

Frontend: inline ⚠ icon next to flagged values where confidence < 0.70
Amber color, 12px, with tooltip: "Value not confirmed in source — verify manually"

─────────────────────────────────────────────────────────────────────
TASK 6-F2 — Financial Ratio Computation (Python, NOT LLM)
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/finance.py
Add POST /finance/ratios:
Step 1: LLM extracts raw line items as structured JSON only — NO arithmetic by LLM:
{ "current\_assets", "current\_liabilities", "total\_assets", "total\_liabilities",
"net\_profit", "total\_equity", "revenue", "cogs", "inventory",
"accounts\_receivable", "quick\_assets" }
Step 2: Python computes ALL ratios — never LLM:
current\_ratio     = current\_assets / current\_liabilities
quick\_ratio       = quick\_assets / current\_liabilities
net\_profit\_margin = (net\_profit / revenue) \* 100
roe               = (net\_profit / total\_equity) \* 100
debt\_to\_equity    = total\_liabilities / total\_equity
Step 3: Return:
{ "ratios": \[
{ "name": "Current Ratio", "value": 1.85,
"formula": "Current Assets / Current Liabilities",
"inputs\_used": { "current\_assets": ..., "current\_liabilities": ... },
"source\_citation": "Balance Sheet, p.12" }
]
}
CRITICAL: The LLM extracts numbers. Python computes formulas. Never swap these roles.

─────────────────────────────────────────────────────────────────────
PHASE 6-F VERIFICATION:
cd backend \&\& python -c "from app.api.v1.endpoints.finance import router; print('Finance OK')"

# Manual: upload P\&L → extract key figures → unverified values show ⚠ amber icon

# Manual: POST /finance/ratios → all 5 ratios returned with formula strings

════════════════════════════════════════════════════════════════════════

PHASE 6-F ADDENDUM — FINANCIAL EXTRACTION DEPTH

════════════════════════════════════════════════════════════════════════



TASK 6-F3 — PDF Table Extraction for Financial Statements

─────────────────────────────────────────────────────────────────────

File: backend/app/services/financial\_table\_extractor.py

CREATE this file.



Financial statements are primarily structured as tables. Text extraction

alone misses the row/column relationships critical for correct ratio

computation. Use pdfplumber for table extraction:



&#x20; import pdfplumber

&#x20; from typing import Optional



&#x20; def extract\_financial\_tables(pdf\_path: str) -> list\[dict]:

&#x20;   """

&#x20;   Extract all tables from a PDF preserving row/column structure.

&#x20;   Returns a list of tables, each with page\_number, headers, and rows.

&#x20;   """

&#x20;   tables = \[]

&#x20;   with pdfplumber.open(pdf\_path) as pdf:

&#x20;     for page\_num, page in enumerate(pdf.pages, start=1):

&#x20;       page\_tables = page.extract\_tables(table\_settings={

&#x20;         "vertical\_strategy": "lines",

&#x20;         "horizontal\_strategy": "lines",

&#x20;         "snap\_tolerance": 3,

&#x20;         "join\_tolerance": 3,

&#x20;         "min\_words\_vertical": 1,

&#x20;         "min\_words\_horizontal": 1

&#x20;       })

&#x20;       for table in (page\_tables or \[]):

&#x20;         if not table or len(table) < 2:

&#x20;           continue

&#x20;         headers = \[str(cell or "").strip() for cell in table\[0]]

&#x20;         rows = \[

&#x20;           \[str(cell or "").strip() for cell in row]

&#x20;           for row in table\[1:]

&#x20;         ]

&#x20;         tables.append({

&#x20;           "page\_number": page\_num,

&#x20;           "headers": headers,

&#x20;           "rows": rows,

&#x20;           "raw\_text": str(table)

&#x20;         })

&#x20;   return tables



&#x20; def identify\_financial\_table\_type(table: dict) -> str:

&#x20;   """Classify which financial statement a table belongs to."""

&#x20;   text = " ".join(table\["headers"] + \[

&#x20;     cell for row in table\["rows"] for cell in row

&#x20;   ]).lower()

&#x20;   if any(k in text for k in \["revenue", "profit", "loss", "ebitda", "income"]):

&#x20;     return "profit\_loss"

&#x20;   if any(k in text for k in \["assets", "liabilities", "equity", "balance"]):

&#x20;     return "balance\_sheet"

&#x20;   if any(k in text for k in \["cash", "operating", "investing", "financing"]):

&#x20;     return "cash\_flow"

&#x20;   return "unknown"



Wire into documents.py upload pipeline:

&#x20; After route\_extraction() in Task 3.7, if workspace\_id == "finance":

&#x20;   from app.services.financial\_table\_extractor import extract\_financial\_tables

&#x20;   tables = extract\_financial\_tables(storage\_path)

&#x20;   # Store tables as JSON in document metadata field

&#x20;   document.financial\_tables = json.dumps(tables)



In finance.py, before LLM extraction in Task 6-F2:

&#x20; If document.financial\_tables:

&#x20;   tables = json.loads(document.financial\_tables)

&#x20;   # Pass table data as structured context to LLM

&#x20;   # LLM extraction from tables is more accurate than from raw text



TASK 6-F4 — Indian Financial Format Normalization

─────────────────────────────────────────────────────────────────────

File: backend/app/services/financial\_table\_extractor.py

ADD this function:



&#x20; import re



&#x20; INDIAN\_NUMERIC\_PATTERN = re.compile(

&#x20;   r'\[₹\\$€£]?\\s?(\\d{1,2}(?:,\\d{2})\*(?:,\\d{3})?(?:\\.\\d{1,2})?)'

&#x20;   r'|\\b(\\d+(?:\\.\\d+)?)\\s\*(lakh|lac|crore|cr|thousand|k)\\b',

&#x20;   re.IGNORECASE

&#x20; )



&#x20; def normalize\_indian\_number(value\_str: str) -> Optional\[float]:

&#x20;   """

&#x20;   Convert Indian financial notation to absolute float.

&#x20;   Examples:

&#x20;     "₹1,23,456"        → 123456.0

&#x20;     "45.5 crore"        → 45500000.0

&#x20;     "12 lakh"           → 1200000.0

&#x20;     "₹1,234.56 Cr"      → 12340000000.0  (wait — need units)

&#x20;     "₹ (in lakhs)"      → flag: values are in lakhs

&#x20;   """

&#x20;   value\_str = value\_str.strip().replace(",", "")

&#x20;   multiplier = 1.0



&#x20;   # Detect unit from nearby text context

&#x20;   if re.search(r'crore|cr\\.?\\b', value\_str, re.I):

&#x20;     multiplier = 10\_000\_000.0

&#x20;     value\_str = re.sub(r'crore|cr\\.?\\b', '', value\_str, flags=re.I)

&#x20;   elif re.search(r'lakh|lac\\b', value\_str, re.I):

&#x20;     multiplier = 100\_000.0

&#x20;     value\_str = re.sub(r'lakh|lac\\b', '', value\_str, flags=re.I)



&#x20;   value\_str = re.sub(r'\[₹\\$€£\\s]', '', value\_str)



&#x20;   try:

&#x20;     return float(value\_str) \* multiplier

&#x20;   except ValueError:

&#x20;     return None



&#x20; def detect\_statement\_unit(table: dict) -> tuple\[str, float]:

&#x20;   """

&#x20;   Detect if a table's values are expressed in thousands, lakhs, or crores.

&#x20;   Returns (unit\_label, multiplier).

&#x20;   """

&#x20;   all\_text = " ".join(table\["headers"]).lower()

&#x20;   if "crore" in all\_text or "cr." in all\_text:

&#x20;     return "crores", 10\_000\_000.0

&#x20;   if "lakh" in all\_text or "lac" in all\_text:

&#x20;     return "lakhs", 100\_000.0

&#x20;   if "thousand" in all\_text:

&#x20;     return "thousands", 1\_000.0

&#x20;   if "million" in all\_text:

&#x20;     return "millions", 1\_000\_000.0

&#x20;   return "absolute", 1.0



NOTE: Apply normalize\_indian\_number() to ALL extracted numerical values

in finance.py before passing to ratio computation.

NEVER apply ratio computation to un-normalized strings.



TASK 6-F5 — Extended Financial Ratio Suite

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/finance.py

EXTEND the existing POST /finance/ratios to compute 15 ratios (not 5).



Step 1: LLM extraction adds these line items to the existing 11:

&#x20; Additional items to extract:

&#x20;   ebitda, interest\_expense, depreciation\_amortization,

&#x20;   operating\_profit, inventory, accounts\_payable,

&#x20;   short\_term\_borrowings, cash\_and\_equivalents,

&#x20;   capital\_expenditure, long\_term\_debt



Step 2: Python computes these ADDITIONAL ratios (extend existing dict):



&#x20; # Profitability

&#x20; gross\_margin          = ((revenue - cogs) / revenue) \* 100

&#x20; operating\_margin      = (operating\_profit / revenue) \* 100

&#x20; ebitda\_margin         = (ebitda / revenue) \* 100



&#x20; # Liquidity

&#x20; cash\_ratio            = cash\_and\_equivalents / current\_liabilities



&#x20; # Coverage

&#x20; interest\_coverage     = ebitda / interest\_expense

&#x20;   # Guard: if interest\_expense == 0 → return None, label "No debt"



&#x20; # Efficiency

&#x20; inventory\_turnover    = cogs / inventory

&#x20;   # Guard: if inventory == 0 → return None, label "N/A"

&#x20; receivables\_turnover  = revenue / accounts\_receivable

&#x20; asset\_turnover        = revenue / total\_assets

&#x20; payables\_days         = (accounts\_payable / cogs) \* 365

&#x20; receivables\_days      = (accounts\_receivable / revenue) \* 365

&#x20;   # (Days Sales Outstanding — important for credit assessment)



&#x20; # Leverage

&#x20; debt\_to\_assets        = total\_liabilities / total\_assets

&#x20; interest\_coverage     = operating\_profit / interest\_expense



CRITICAL GUARDS — apply before every division:

&#x20; def safe\_divide(numerator, denominator, ratio\_name):

&#x20;   if denominator is None or denominator == 0:

&#x20;     return {

&#x20;       "name": ratio\_name, "value": None,

&#x20;       "error": "Division by zero — denominator not available or zero",

&#x20;       "formula": ratio\_name\_formula\_map\[ratio\_name]

&#x20;     }

&#x20;   return round(numerator / denominator, 4)



Return all 15 ratios in the same response structure as existing Task 6-F2.



TASK 6-F6 — Full Traceability Chain

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/finance.py

PURPOSE: Every ratio must be traceable from its computed value back to

the exact text span the LLM read to extract the input value.



Current Task 6-F2 returns source\_citation per ratio.

This task adds CHARACTER-LEVEL traceability:



Modify LLM extraction prompt to return text spans:

&#x20; {

&#x20;   "current\_assets": {

&#x20;     "value": 125000000,

&#x20;     "raw\_text": "Current Assets 1,25,000",

&#x20;     "page\_number": 12,

&#x20;     "table\_row": "Current Assets",

&#x20;     "table\_column": "FY2024",

&#x20;     "confidence": 0.95

&#x20;   }

&#x20; }



Store in extraction\_audit table (Alembic migration: "add\_extraction\_audit"):

&#x20; Columns: id (UUID PK), document\_id (FK), line\_item (str),

&#x20;          extracted\_value (float), raw\_text\_span (str),

&#x20;          page\_number (int), table\_row (str), table\_column (str),

&#x20;          confidence (float), created\_at (datetime),

&#x20;          session\_id (UUID FK, nullable)



Return in ratio response:

&#x20; {

&#x20;   "name": "Current Ratio",

&#x20;   "value": 2.5,

&#x20;   "formula": "Current Assets / Current Liabilities",

&#x20;   "inputs": {

&#x20;     "current\_assets":      { "value": 125000000, "page": 12,

&#x20;                              "text": "Current Assets 1,25,000",

&#x20;                              "confidence": 0.95, "verified": true },

&#x20;     "current\_liabilities": { "value": 50000000,  "page": 12,

&#x20;                              "text": "Current Liabilities 50,000",

&#x20;                              "confidence": 0.95, "verified": true }

&#x20;   },

&#x20;   "audit\_ids": \["uuid-for-assets-extraction", "uuid-for-liabilities-extraction"]

&#x20; }



Frontend — Extraction Audit Table UI:

&#x20; New panel in Finance workspace (activated by "✅ Verify" button in action bar):

&#x20;   Spreadsheet-like table:

&#x20;     Columns: Line Item | Extracted Value | Source Text | Page | Confidence | Status

&#x20;   Each row:

&#x20;     Line item name (e.g., "Current Assets")

&#x20;     Extracted value (formatted: ₹1,25,000 or 1,25,00,000 in lakhs)

&#x20;     Source text span (truncated to 40 chars, full on hover)

&#x20;     Page number chip → click opens preview panel to that page

&#x20;     Confidence badge: green/amber/red per threshold

&#x20;     Status: ✓ Verified (confidence ≥ 0.85) | ⚠ Review (< 0.85) | ✗ Not Found

&#x20;   "Export Audit Trail" button → downloads CSV of this table

&#x20;   This table is the professional-grade evidence for client-facing reports.



TASK 6-F7 — Multi-Period Comparison

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/finance.py

PURPOSE: Allow a CA to upload P\&L/Balance Sheet for 3 years and compare

ratio trends.



Add POST /finance/compare:

&#x20; Input: { "period\_doc\_ids": {"FY2022": "doc\_id\_1", "FY2023": "doc\_id\_2", "FY2024": "doc\_id\_3"} }

&#x20; For each period: run the full ratio extraction (Task 6-F2 + 6-F5)

&#x20; Return:

&#x20;   {

&#x20;     "periods": \["FY2022", "FY2023", "FY2024"],

&#x20;     "ratios": \[

&#x20;       {

&#x20;         "name": "Current Ratio",

&#x20;         "values": { "FY2022": 1.8, "FY2023": 2.1, "FY2024": 2.5 },

&#x20;         "trend": "improving",        // "improving" | "declining" | "stable"

&#x20;         "yoy\_changes": {

&#x20;           "FY2022→FY2023": +16.7,   // percentage change

&#x20;           "FY2023→FY2024": +19.0

&#x20;         },

&#x20;         "interpretation": "Liquidity has improved consistently over 3 years."

&#x20;       }

&#x20;     ]

&#x20;   }



&#x20; Trend computation (Python, never LLM):

&#x20;   values = \[v for v in period\_values.values() if v is not None]

&#x20;   if len(values) >= 2:

&#x20;     if values\[-1] > values\[0] \* 1.05:  trend = "improving"

&#x20;     elif values\[-1] < values\[0] \* 0.95: trend = "declining"

&#x20;     else:                                trend = "stable"



Frontend — Multi-Period Comparison UI:

&#x20; Available when ≥ 2 documents are uploaded to Finance workspace.

&#x20; "📊 Year-on-Year Analysis" quick action activates comparison mode.

&#x20; Display: table with ratios as rows, years as columns

&#x20;   Each cell: ratio value + small arrow (↑ green / ↓ red / → gray)

&#x20;   Arrow based on YoY change vs previous period

&#x20;   Last column: "3-Year Trend" sparkline (tiny SVG line chart, 80px wide)

&#x20; "Export Comparison Report" → DOCX with table + trend interpretations

&#x20;   DOCX: ratio name | FY2022 | FY2023 | FY2024 | Trend | Interpretation



TASK 6-F8 — IFRS vs Ind AS Detection

─────────────────────────────────────────────────────────────────────

File: backend/app/services/financial\_table\_extractor.py

ADD:



&#x20; IFRS\_MARKERS = \["IFRS", "IAS", "International Financial Reporting Standards"]

&#x20; IND\_AS\_MARKERS = \["Ind AS", "Indian Accounting Standard", "ICAI", "Companies Act 2013"]

&#x20; US\_GAAP\_MARKERS = \["US GAAP", "FASB", "ASC 606", "Generally Accepted Accounting"]



&#x20; def detect\_accounting\_standard(document\_text: str) -> str:

&#x20;   for marker in IFRS\_MARKERS:

&#x20;     if marker.lower() in document\_text.lower():

&#x20;       return "IFRS"

&#x20;   for marker in IND\_AS\_MARKERS:

&#x20;     if marker.lower() in document\_text.lower():

&#x20;       return "IND\_AS"

&#x20;   for marker in US\_GAAP\_MARKERS:

&#x20;     if marker.lower() in document\_text.lower():

&#x20;       return "US\_GAAP"

&#x20;   return "UNKNOWN"



&#x20; # Line item name mapping across standards:

&#x20; LINE\_ITEM\_ALIASES = {

&#x20;   "revenue": \["Revenue", "Turnover", "Net Sales", "Revenue from Operations",

&#x20;               "Revenue from Contracts with Customers"],

&#x20;   "operating\_profit": \["PBIT", "Operating Profit", "EBIT",

&#x20;                        "Profit from Operations"],

&#x20;   "net\_profit": \["PAT", "Profit After Tax", "Net Income", "Net Profit",

&#x20;                  "Profit for the year"],

&#x20;   "current\_assets": \["Current Assets", "Total Current Assets"],

&#x20;   "current\_liabilities": \["Current Liabilities", "Total Current Liabilities"],

&#x20;   "total\_equity": \["Shareholders' Equity", "Net Worth", "Equity",

&#x20;                    "Total Equity", "Shareholders' Funds"],

&#x20;   "inventory": \["Inventories", "Stock", "Inventory"],

&#x20;   "accounts\_receivable": \["Trade Receivables", "Debtors", "Accounts Receivable"]

&#x20; }



In the LLM extraction prompt for Task 6-F2, include the detected standard

and the alias list so the LLM knows to look for "Turnover" if the document

uses Ind AS terminology instead of "Revenue."

Include accounting\_standard field in the ratio API response.



─────────────────────────────────────────────────────────────────────

PHASE 6-F ADDENDUM VERIFICATION:

─────────────────────────────────────────────────────────────────────

&#x20; cd backend \&\& python -c "

&#x20; from app.services.financial\_table\_extractor import (

&#x20;   extract\_financial\_tables, normalize\_indian\_number, detect\_statement\_unit

&#x20; )

&#x20; assert normalize\_indian\_number('₹45.5 crore') == 455000000.0

&#x20; assert normalize\_indian\_number('12 lakh') == 1200000.0

&#x20; print('Indian number normalization OK')

&#x20; "

&#x20; # Manual: upload a real Ind AS annual report (e.g., Infosys FY2024)

&#x20; # Manual: POST /finance/ratios → 15 ratios returned, all with traceability

&#x20; # Manual: upload 3 year-wise reports → POST /finance/compare → trend arrows correct

&#x20; # Manual: Extraction Audit Table shows all values with source page links

&#x20; # Manual: click page chip in audit table → preview panel opens to correct page

════════════════════════════════════════════════════════════════════════
PHASE 6-L — LEGAL WORKSPACE
════════════════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────────────
TASK 6-L1 — Mandatory Disclaimer — Always Visible, Never Dismissable
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/legal.py
File: backend/app/api/v1/endpoints/query.py (legal workspace path)

PREPEND to every legal workspace response without exception:
⚠ This analysis is AI-generated for informational use only.
It does NOT constitute legal advice. Always consult a qualified
legal professional before acting on any information.

Frontend:
Fixed amber banner at BOTTOM of Legal workspace (below input bar):
NEVER dismissable — no × button, no hide option
Always visible in Legal workspace regardless of scroll position
This is SEPARATE from the per-message disclaimer

The per-message disclaimer (from Task 4.7) also applies in Legal workspace.
Both must coexist. The bottom bar is workspace-persistent.
The message disclaimer is response-specific.

─────────────────────────────────────────────────────────────────────
TASK 6-L2 — Contract Risk Report
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/legal.py
Add POST /legal/contracts/{id}/risk-report:
LLM returns structured JSON ONLY:
{
"overall\_risk\_score": int,   // 0-100
"overall\_risk\_level": str,   // "Low" | "Medium" | "High" | "Critical"
"summary": str,
"clause\_risks": \[
{
"clause\_type": str,
"text\_excerpt": str,
"risk\_level": "Low"|"Medium"|"High"|"Critical",
"risk\_reason": str,
"page": int,
"recommendation": str
}
],
"missing\_clauses": \[str]
}
Store in legal\_analyses table (create with Alembic migration if missing).

Frontend — Risk Report UI (collapsible panel below AI response):
Header: overall risk score circle (0-100):
0-30 = green ring, 31-60 = amber ring, 61-80 = red ring, 81-100 = dark red ring
Score number in center, risk level text below
Clause list: each row = risk color pill | clause type | brief reason | page reference chip
Missing clauses: red pill list below clause list
"Export Risk Report PDF" button: .btn .btn-secondary .btn-sm (calls backend export)

─────────────────────────────────────────────────────────────────────
PHASE 6-L VERIFICATION:
cd backend \&\& python -c "from app.api.v1.endpoints.legal import router; print('Legal OK')"

════════════════════════════════════════════════════════════════════════

PHASE 6-L ADDENDUM — LEGAL TRUST AND RISK CALIBRATION

════════════════════════════════════════════════════════════════════════



TASK 6-L3 — Per-Clause Confidence Scoring

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/legal.py

PURPOSE: The current risk report returns one overall\_risk\_score. Each

clause must also have a confidence score indicating how certain the AI

is about its risk assessment. Low confidence must surface visibly.



Modify the LLM prompt for POST /legal/contracts/{id}/risk-report to

require confidence\_score per clause:

&#x20; {

&#x20;   "clause\_risks": \[

&#x20;     {

&#x20;       "clause\_type": "Indemnity",

&#x20;       "text\_excerpt": "...",

&#x20;       "risk\_level": "High",

&#x20;       "risk\_reason": "...",

&#x20;       "confidence\_score": 0.82,    // NEW: 0.0-1.0

&#x20;       "confidence\_basis": "clause\_clearly\_stated",

&#x20;                                    // "clause\_clearly\_stated"

&#x20;                                    // | "inferred\_from\_context"

&#x20;                                    // | "ambiguous\_language"

&#x20;                                    // | "insufficient\_text"

&#x20;       "page": 4,

&#x20;       "recommendation": "..."

&#x20;     }

&#x20;   ]

&#x20; }



FALSE CONFIDENCE PREVENTION RULE (enforce in prompt):

&#x20; If confidence\_basis == "insufficient\_text" OR confidence\_score < 0.50:

&#x20;   risk\_level MUST be "Unassessable" (never "Low" / "Medium" / "High")

&#x20;   risk\_reason MUST begin with: "Insufficient information to assess..."

&#x20;   NEVER return a confident risk level when the clause text is unclear.



Frontend — Clause confidence display:

&#x20; Each clause row in risk report panel:

&#x20;   confidence\_score ≥ 0.80 → no indicator (normal display)

&#x20;   confidence\_score 0.60-0.79 → small "\~" prefix before risk level pill,

&#x20;                                  tooltip: "Moderate confidence — verify manually"

&#x20;   confidence\_score < 0.60 → "?" prefix, amber border on row,

&#x20;                               tooltip: "Low confidence — AI is uncertain"

&#x20;   confidence\_basis == "insufficient\_text" → gray pill "Unassessable",

&#x20;                                             amber ⚠ icon, tooltip explains



TASK 6-L4 — Clause Consistency Validation

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/legal.py

PURPOSE: If the same contract is re-analyzed, similar clauses must

receive consistent risk levels. Inconsistency destroys professional trust.



On each risk report generation, check if a previous analysis exists for

the same document in legal\_analyses table.



If previous analysis exists:

&#x20; For each clause\_type that appears in both old and new analysis:

&#x20;   old\_level = previous\["clause\_risks"]\[clause\_type]\["risk\_level"]

&#x20;   new\_level = current\["clause\_risks"]\[clause\_type]\["risk\_level"]

&#x20;   RISK\_LEVELS = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

&#x20;   level\_diff = abs(RISK\_LEVELS\[new\_level] - RISK\_LEVELS\[old\_level])

&#x20;   if level\_diff >= 2:  # jumped from Low → High or worse

&#x20;     flag consistency\_warning for this clause



Return in risk report response:

&#x20; "consistency\_warnings": \[

&#x20;   {

&#x20;     "clause\_type": "Indemnity",

&#x20;     "previous\_level": "Low",

&#x20;     "current\_level": "High",

&#x20;     "warning": "Risk level changed significantly from previous analysis.

&#x20;                 Manual review recommended."

&#x20;   }

&#x20; ]



Frontend: if consistency\_warnings is non-empty, show a yellow banner

above the risk report:

&#x20; "⚠ Some clause risk levels differ from the previous analysis of this

&#x20;  document. Review flagged clauses carefully."

&#x20; List each flagged clause\_type below the warning.



TASK 6-L5 — Human-Review Escalation

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/legal.py

PURPOSE: When risk thresholds are crossed, the system must explicitly

call for human legal review — not suggest it, but require it in the UI.



ESCALATION TRIGGERS (apply in POST /legal/contracts/{id}/risk-report):

&#x20; if overall\_risk\_score >= 70:

&#x20;   escalation\_required = True

&#x20;   escalation\_reason = "Overall contract risk score is High or Critical."

&#x20; elif any(c\["risk\_level"] == "Critical" for c in clause\_risks):

&#x20;   escalation\_required = True

&#x20;   escalation\_reason = "One or more Critical risk clauses identified."

&#x20; elif len(missing\_clauses) >= 3:

&#x20;   escalation\_required = True

&#x20;   escalation\_reason = "Three or more standard clauses are missing."

&#x20; else:

&#x20;   escalation\_required = False

&#x20;   escalation\_reason = None



Add to response: { "escalation\_required": bool, "escalation\_reason": str|null }



Frontend: if escalation\_required:

&#x20; Show a mandatory red banner at TOP of risk report panel (before score circle):

&#x20;   Background: var(--error-bg), border: 1px var(--error-border)

&#x20;   "🚨 Human Legal Review Required"

&#x20;   escalation\_reason text below in 13px

&#x20;   "This contract requires review by a qualified legal professional

&#x20;    before any action is taken. DocuMindAI identifies risk signals —

&#x20;    it does not provide legal advice."

&#x20; This banner is NOT dismissable (like the Legal disclaimer banner).

&#x20; "Export Risk Report PDF" button still available — professional can share it.



TASK 6-L6 — Legal Analysis Audit Trail

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/legal.py

PURPOSE: Enterprise legal teams require immutable audit trails for

professional liability and regulatory compliance.



Modify legal\_analyses table (new Alembic migration: "add\_legal\_audit\_trail"):

&#x20; ADD columns:

&#x20;   model\_version (str)             # which LLM was used

&#x20;   analysis\_version (str)          # "v1.0" — increment on prompt changes

&#x20;   user\_id (UUID FK users)

&#x20;   ip\_address (str)                # requestor IP, for audit purposes

&#x20;   request\_timestamp (datetime)

&#x20;   response\_duration\_ms (int)

&#x20;   clause\_count (int)

&#x20;   missing\_clause\_count (int)

&#x20;   escalation\_required (bool)



CREATE legal\_audit\_log table (immutable):

&#x20; id (UUID PK), user\_id (UUID FK), document\_id (UUID FK),

&#x20; analysis\_id (UUID FK legal\_analyses), event\_type (str),

&#x20; event\_detail (JSONB), timestamp (datetime)

&#x20; RULE: This table has NO UPDATE, NO DELETE permissions — INSERT ONLY.

&#x20; event\_type values: "analysis\_created" | "report\_exported" |

&#x20;                    "session\_shared" | "escalation\_triggered"



Populate audit log on every analysis and export. Log:

&#x20; user\_id, document\_id, analysis\_id, event\_type, timestamp.

&#x20; NEVER log: document content, extracted text, or PII.



Add endpoint: GET /legal/audit-log (authenticated, user's own records only):

&#x20; Returns list of all events for current user, ordered by timestamp desc.

&#x20; Useful for enterprise admins reviewing staff usage.



TASK 6-L7 — Contract Comparison (Two-Document Mode)

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/legal.py

PURPOSE: Compare two contracts (e.g., standard template vs received draft,

or two versions of an agreement). Show clause-level differences.



Add POST /legal/contracts/compare:

&#x20; Input: { "doc\_id\_a": "...", "doc\_id\_b": "...", "label\_a": "Template",

&#x20;          "label\_b": "Received Draft" }



&#x20; LLM compares both documents and returns:

&#x20;   {

&#x20;     "matching\_clauses": \[

&#x20;       { "clause\_type": "Governing Law", "doc\_a": "Courts of Delhi",

&#x20;         "doc\_b": "Courts of Mumbai", "material\_difference": true,

&#x20;         "difference\_note": "Jurisdiction differs — check preference." }

&#x20;     ],

&#x20;     "clauses\_in\_a\_only": \[

&#x20;       { "clause\_type": "Non-Solicitation",

&#x20;         "risk\_note": "Missing from received draft — consider requiring it." }

&#x20;     ],

&#x20;     "clauses\_in\_b\_only": \[

&#x20;       { "clause\_type": "Unilateral Termination",

&#x20;         "risk\_note": "Non-standard clause added by counterparty." }

&#x20;     ]

&#x20;   }



Frontend — Comparison UI:

&#x20; 3-column layout within Legal workspace:

&#x20;   Left: Label A clauses  |  Middle: Differences  |  Right: Label B clauses

&#x20;   Matching clauses with differences: amber row

&#x20;   Clauses missing from one side: red row with ✗ icon

&#x20;   Each row: clause type, brief text excerpt, difference note

&#x20; "Export Comparison Report" → PDF showing side-by-side clause differences

&#x20; Triggered by "⚖ Contract Mode" button → upload two documents flow



NOTE: Contract comparison disclaimer applies — same mandatory amber

banner and escalation rules from Tasks 6-L1 and 6-L5.



─────────────────────────────────────────────────────────────────────

PHASE 6-L ADDENDUM VERIFICATION:

─────────────────────────────────────────────────────────────────────

&#x20; cd backend \&\& python -c "

&#x20; from app.api.v1.endpoints.legal import router

&#x20; routes = \[r.path for r in router.routes]

&#x20; assert '/contracts/{id}/risk-report' in str(routes)

&#x20; assert '/contracts/compare' in str(routes)

&#x20; assert '/audit-log' in str(routes)

&#x20; print('Legal routes OK')

&#x20; "

&#x20; # Manual: generate risk report on a complex contract

&#x20; #   → clauses with confidence < 0.60 show amber border + "?" prefix

&#x20; #   → if overall\_risk\_score ≥ 70: red escalation banner appears (no dismiss)

&#x20; # Manual: re-analyze same contract → consistency\_warnings if levels changed

&#x20; # Manual: compare two documents → 3-column diff view renders

&#x20; # Manual: GET /legal/audit-log → returns events for current user

&#x20; # Manual: "Unassessable" clauses show gray pill not a risk color

# Manual: legal workspace → every AI response has disclaimer (no exception)

# Manual: bottom disclaimer banner never shows × or dismiss option

# Manual: generate risk report → shows score circle + clause list

════════════════════════════════════════════════════════════════════════
PHASE 6-R — RESEARCH WORKSPACE
════════════════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────────────
TASK 6-R1 — Citation Format Export
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/research.py
Add POST /research/citations:
Input: { doc\_ids: \[], format: "APA"|"MLA"|"IEEE"|"Chicago" }
For each document, LLM extracts:
{ author, title, journal, year, DOI, volume, issue, pages, publisher }
Format in requested citation style (Python string formatting, not LLM):
APA:     Author, A. A. (Year). Title. Journal, Volume(Issue), Pages. https://doi.org/...
MLA:     Author, First. "Title." Journal vol.Volume, no.Issue, Year, pp. Pages.
IEEE:    A. Author, "Title," Journal, vol. Volume, no. Issue, pp. Pages, Year.
Chicago: Author, First. "Title." Journal Volume, no. Issue (Year): Pages.
Return: { "citations": \[str], "format": str, "count": int }

Frontend: "Export Citations" button → dropdown (APA/MLA/IEEE/Chicago):
On format select: call API → show citations in a modal
Two actions: "Copy All to Clipboard" + "Download .txt"

─────────────────────────────────────────────────────────────────────
TASK 6-R2 — Research Gap Identification
─────────────────────────────────────────────────────────────────────
File: backend/app/api/v1/endpoints/research.py
Add POST /research/gaps:
Multi-document retrieval across all uploaded research papers.
LLM returns structured JSON:
{
"gaps": \[str],       // Unexplored areas and open questions
"conflicts": \[str],  // Areas where papers contradict each other
"consensus": \[str]   // Areas of strong agreement across papers
}

Frontend — 3-tab panel in Research workspace:
Tab 1: Gaps      (shows gaps list with bullet points)
Tab 2: Conflicts (shows conflicts list)
Tab 3: Consensus (shows consensus list)
Each item: card with text, no action buttons

─────────────────────────────────────────────────────────────────────
PHASE 6-R VERIFICATION:
cd backend \&\& python -c "from app.api.v1.endpoints.research import router; print('Research OK')"

════════════════════════════════════════════════════════════════════════

PHASE 6 CROSS-WORKSPACE ADDENDUM — SHARED PROFESSIONAL FEATURES

════════════════════════════════════════════════════════════════════════



TASK 6-X1 — BibTeX Export for Research Workspace

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/research.py

Add "BibTeX" to the format list in POST /research/citations:

&#x20; Formats: "APA" | "MLA" | "IEEE" | "Chicago" | "BibTeX"



&#x20; BibTeX format function:

&#x20; def format\_bibtex(metadata: dict, index: int) -> str:

&#x20;   key = f"{metadata.get('author','Unknown').split(',')\[0].strip()}"

&#x20;         f"{metadata.get('year','XXXX')}"

&#x20;   return (

&#x20;     f"@article{{{key}{index},\\n"

&#x20;     f"  author  = {{{metadata.get('author','')}}},\\n"

&#x20;     f"  title   = {{{metadata.get('title','')}}},\\n"

&#x20;     f"  journal = {{{metadata.get('journal','')}}},\\n"

&#x20;     f"  year    = {{{metadata.get('year','')}}},\\n"

&#x20;     f"  volume  = {{{metadata.get('volume','')}}},\\n"

&#x20;     f"  number  = {{{metadata.get('issue','')}}},\\n"

&#x20;     f"  pages   = {{{metadata.get('pages','')}}},\\n"

&#x20;     f"  doi     = {{{metadata.get('doi','')}}}\\n"

&#x20;     f"}}"

&#x20;   )



Frontend: add "BibTeX (.bib)" to citation format dropdown.

"Download .bib" button in citation modal → downloads as filename.bib

This enables direct import into Zotero, Mendeley, Overleaf.



TASK 6-X2 — Document Health Score

─────────────────────────────────────────────────────────────────────

File: backend/app/api/v1/endpoints/documents.py

PURPOSE: When a document is uploaded, compute quality metrics that

predict retrieval quality. Show these before the user asks their

first question so they can re-upload a better version if needed.



Compute on upload (after extraction in Task 3.7):

&#x20; from app.services.document\_health import compute\_health\_score



Create: backend/app/services/document\_health.py

&#x20; import pymupdf4llm, statistics



&#x20; def compute\_health\_score(pdf\_path: str, extraction\_result: dict) -> dict:

&#x20;   """

&#x20;   Compute a document health score 0-100 that predicts retrieval quality.

&#x20;   """

&#x20;   # 1. Text density: words per page

&#x20;   text = extraction\_result.get("extracted\_text", "")

&#x20;   page\_count = extraction\_result.get("page\_count", 1)

&#x20;   words\_per\_page = len(text.split()) / max(page\_count, 1)



&#x20;   # 2. Is native PDF or scanned?

&#x20;   is\_native = not extraction\_result.get("needs\_ocr", True)



&#x20;   # 3. Encoding detection: any replacement characters (U+FFFD)?

&#x20;   encoding\_issues = text.count("\\ufffd")



&#x20;   # Scoring (0-100):

&#x20;   score = 100

&#x20;   if not is\_native:

&#x20;     score -= 20  # OCR reduces reliability

&#x20;   if words\_per\_page < 100:

&#x20;     score -= 30  # Very sparse — image-heavy or poorly extracted

&#x20;   elif words\_per\_page < 200:

&#x20;     score -= 15

&#x20;   if encoding\_issues > 10:

&#x20;     score -= 20  # Bad encoding

&#x20;   score = max(0, min(100, score))



&#x20;   # Grade

&#x20;   if score >= 80: grade = "Excellent"

&#x20;   elif score >= 60: grade = "Good"

&#x20;   elif score >= 40: grade = "Fair"

&#x20;   else: grade = "Poor — consider re-uploading a text-based PDF"



&#x20;   return {

&#x20;     "score": score,

&#x20;     "grade": grade,

&#x20;     "is\_native\_pdf": is\_native,

&#x20;     "words\_per\_page": round(words\_per\_page, 1),

&#x20;     "page\_count": page\_count,

&#x20;     "encoding\_issues": encoding\_issues,

&#x20;     "warnings": \[

&#x20;       w for w in \[

&#x20;         "Scanned PDF — OCR may reduce accuracy" if not is\_native else None,

&#x20;         "Low text density — PDF may be image-heavy" if words\_per\_page < 150 else None,

&#x20;         "Encoding issues detected — some text may be garbled" if encoding\_issues > 10 else None

&#x20;       ] if w

&#x20;     ]

&#x20;   }



Add health\_score JSON to Document model (Alembic: "add\_document\_health\_score").

Return in GET /documents/{id} response.



Frontend — Document chip enhancement:

&#x20; After document reaches READY status, show health score badge on chip:

&#x20;   score ≥ 80 → green dot (no label — good is default)

&#x20;   score 50-79 → amber "\~" dot + tooltip showing warnings

&#x20;   score < 50 → red "⚠" dot + tooltip "Poor quality — retrieval may be limited"

&#x20; In document list panel, hovering chip shows full health summary card:

&#x20;   Score circle, grade, words\_per\_page, warnings list.

&#x20;   "Re-upload better version" link if score < 50.



TASK 6-X3 — Query Template Library

─────────────────────────────────────────────────────────────────────

File: frontend/src/components/QueryTemplateModal.tsx

CREATE this component.

PURPOSE: Beyond the 3 quick actions in the workspace welcome state,

professionals need a library of 10-15 domain-specific query templates

they can run with one click. Available any time during a session.



Triggered by: ⊞ Templates button in chat input bar (already defined in Phase 4 design spec).



TEMPLATE\_LIBRARY = {

&#x20; general: \[

&#x20;   { label: "Executive Summary", prompt: "Summarize the key points of this document in under 200 words." },

&#x20;   { label: "Action Items", prompt: "List all action items, deadlines, and responsible parties mentioned." },

&#x20;   { label: "Key Definitions", prompt: "Extract all defined terms and their definitions from this document." },

&#x20;   { label: "Unanswered Questions", prompt: "What questions does this document leave unanswered?" }

&#x20; ],

&#x20; finance: \[

&#x20;   { label: "Extract All Figures", prompt: "Extract all financial figures with exact page citations, formatted as: \[Figure Name]: \[Value] — Source: \[filename] p.\[N]" },

&#x20;   { label: "Revenue Breakdown", prompt: "Break down revenue by segment, product line, or geography as reported." },

&#x20;   { label: "Working Capital Analysis", prompt: "Analyze working capital position. Calculate current ratio, quick ratio, and working capital in absolute terms." },

&#x20;   { label: "Management Discussion Summary", prompt: "Summarize the Management Discussion \& Analysis section, highlighting risks and opportunities." },

&#x20;   { label: "Related Party Transactions", prompt: "List all related party transactions mentioned, with amounts and nature of relationship." },

&#x20;   { label: "Contingent Liabilities", prompt: "Extract all contingent liabilities, provisions, and commitments with amounts." },

&#x20;   { label: "Auditor Observations", prompt: "Summarize the auditor's key observations, qualifications, and emphasis of matter paragraphs." }

&#x20; ],

&#x20; legal: \[

&#x20;   { label: "Party Identification", prompt: "Identify all parties to this agreement with their full legal names and defined terms." },

&#x20;   { label: "Key Dates \& Deadlines", prompt: "Extract all dates, deadlines, notice periods, and time-bound obligations." },

&#x20;   { label: "Payment Terms", prompt: "Extract all payment terms, amounts, schedules, and late payment consequences." },

&#x20;   { label: "Termination Conditions", prompt: "List all conditions under which this agreement can be terminated by either party." },

&#x20;   { label: "Governing Law \& Jurisdiction", prompt: "What is the governing law and jurisdiction for disputes under this agreement?" },

&#x20;   { label: "Confidentiality Scope", prompt: "What information is defined as confidential? What are the exceptions?" },

&#x20;   { label: "Representations \& Warranties", prompt: "Summarize all representations and warranties made by each party." }

&#x20; ],

&#x20; hr: \[

&#x20;   { label: "Skills Summary", prompt: "For each candidate, list their top 5 skills and years of experience in each." },

&#x20;   { label: "Education Comparison", prompt: "Compare the educational qualifications of all candidates in a table." },

&#x20;   { label: "Experience Timeline", prompt: "Describe each candidate's career progression from earliest to most recent role." },

&#x20;   { label: "Red Flags", prompt: "Are there any unexplained employment gaps, inconsistencies, or unusual patterns in these resumes?" },

&#x20;   { label: "Interview Questions", prompt: "Based on this candidate's background, generate 5 targeted interview questions." }

&#x20; ],

&#x20; teacher: \[

&#x20;   { label: "Topic Coverage", prompt: "What topics from this document are suitable for assessment? List them with difficulty level." },

&#x20;   { label: "Difficult Concepts", prompt: "What are the most conceptually difficult topics in this material? These warrant higher-order questions." },

&#x20;   { label: "Prerequisites", prompt: "What prior knowledge is assumed in this content? What concepts must students understand first?" }

&#x20; ],

&#x20; student: \[

&#x20;   { label: "Key Formulas", prompt: "List all formulas, equations, and mathematical relationships mentioned." },

&#x20;   { label: "Important Dates", prompt: "Extract all important dates, periods, and historical events mentioned." },

&#x20;   { label: "Explain Simply", prompt: "Explain the main concept of this document as if I am hearing it for the first time." },

&#x20;   { label: "Memory Tricks", prompt: "What are the key things I must remember for an exam on this material?" }

&#x20; ],

&#x20; research: \[

&#x20;   { label: "Methodology Summary", prompt: "Summarize the research methodology: sample size, data collection method, analysis approach." },

&#x20;   { label: "Limitations", prompt: "What are the stated limitations and potential weaknesses of this research?" },

&#x20;   { label: "Future Work", prompt: "What future research directions do the authors suggest or does the evidence imply?" },

&#x20;   { label: "Key Statistics", prompt: "Extract all statistical findings with their p-values, confidence intervals, and significance." }

&#x20; ]

}



Modal design:

&#x20; .modal, 520px wide, max-height 70vh, scrollable

&#x20; Header: "Query Templates — \[Workspace Name]"

&#x20; Search field: filters templates in real-time by label text

&#x20; Template groups: each template as a .card (light border, 8px radius):

&#x20;   Label in DM Sans 13px weight 500, prompt preview in 12px text-secondary (2 lines truncated)

&#x20;   "Use →" button on hover: .btn .btn-primary .btn-sm

&#x20;   onClick: closes modal, sets inputValue to prompt, auto-submits

&#x20; Footer: "Shift+Enter to preview without submitting" — 12px text-tertiary



Add keyboard shortcut: Cmd+/ opens this modal from anywhere in the workspace.

# Manual: upload 2 papers → POST /research/citations → correct APA format

# Manual: POST /research/gaps → 3-tab panel shows gaps/conflicts/consensus

─────────────────────────────────────────────────────────────────────
PHASE 6 FULL VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
cd backend \&\& python -c "from app.api.v1.endpoints.exams import router; print('Exams OK')"
cd backend \&\& python -c "from app.api.v1.endpoints.hr import router; print('HR OK')"
cd backend \&\& python -c "from app.api.v1.endpoints.study import router; print('Study OK')"
cd backend \&\& python -c "from app.api.v1.endpoints.finance import router; print('Finance OK')"
cd backend \&\& python -c "from app.api.v1.endpoints.legal import router; print('Legal OK')"
cd backend \&\& python -c "from app.api.v1.endpoints.research import router; print('Research OK')"
cd frontend \&\& npx tsc --noEmit \&\& echo "TypeScript OK"

DEFINITION OF DONE — PHASE 6:
✅ Teacher: marks validation prevents invalid paper generation (400 error)
✅ Teacher: DOCX export with academic formatting + section headers
✅ Teacher: Bloom's taxonomy level returned per question
✅ HR: JD-resume semantic score shown in candidate rankings
✅ HR: candidate stage update (PATCH) works and persists
✅ HR: PII (email/phone) redacted in all NEW log statements
✅ Student: quiz generation strips correct\_index before frontend delivery
✅ Student: quiz scoring returns explanations + source pages
✅ Student: SM-2 spaced repetition updates next\_review\_date correctly
✅ Student: Pomodoro timer persists across workspace switches
✅ Finance: numerical values flagged with ⚠ when unverified in source
✅ Finance: ratios computed by Python (not LLM), formulas returned
✅ Legal: disclaimer prepended to EVERY response without exception
✅ Legal: bottom disclaimer banner never dismissable
✅ Legal: risk report shows score circle + clause list
✅ Research: citations exported in correct format (APA/MLA/IEEE/Chicago)
✅ Research: gaps/conflicts/consensus 3-tab panel renders

\[CHECKPOINT 6 COMPLETE — Proceeding to Phase 7]

