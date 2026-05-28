# DocuMindAI — MERGED PART 7: ENHANCEMENT PHASES
# VERSION: Enhancement Pack v1.0
# MODEL: claude-sonnet-4-6
# EXECUTION MODE: Fully Autonomous — Agentic Codebase Execution
# INSTRUCTION: Execute ALL phases below in order AFTER Phase 8 is complete.
#              Phases 10→11→12→13→14→15→Final-Enhanced
#              Same rules apply: verify after every task, never break working code.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENHANCEMENT OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 10 — Free Trial System (10 Queries, Full Access)
Phase 11 — Teacher Table Extraction (Perfect Table Export)
Phase 12 — Dynamic API Key Rotation (Zero Hardcoded Count)
Phase 13 — GST / Tax Auto-Update Automation (Daily, No Code Changes)
Phase 14 — Zero-Cost UI/UX Enhancements (All 11 Features)
Phase 15 — Structured Response Enforcement + Expert Mode Toggle

NEW EXECUTION ORDER (APPEND AFTER EXISTING):
  0→1→2→2.5→3→4→5→6-T→6-H→6-S→6-F→6-L→6-R→7→8→9(addendum)→
  10→11→12→13→14→15→Final-Enhanced

CRITICAL CONSTRAINTS INHERITED (ALL STILL APPLY):
  ✓ STABLE SYSTEMS list — never modify those files
  ✓ Answers ONLY from documents — grounding constraint unchanged
  ✓ bcrypt for passwords — never SHA256
  ✓ No secrets in code — only .env
  ✓ Legal/Finance disclaimers NEVER dismissable
  ✓ Financial ratios by Python NOT LLM
  ✓ WCAG 2.1 AA accessibility on all new UI
  ✓ PII never in logs

NEW STABLE SYSTEMS (DO NOT MODIFY AFTER PHASE 12):
  backend/app/services/llm_key_rotation.py   ← Phase 12 — STABLE after creation
  backend/app/workers/tasks/tax_update_tasks.py ← Phase 13 — STABLE after creation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 10 — FREE TRIAL SYSTEM (10 QUERIES, FULL ACCESS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Every new user gets 10 queries with COMPLETE access to all 7
workspaces, all features, all exports — no document limits, no workspace
locks. After query 10, they see an upgrade modal. Because they've
experienced everything, they're motivated to subscribe.
ESTIMATED TIME: 3–4 hours | RISK: Low | DEPENDS ON: Phase 8 complete

─────────────────────────────────────────────────────────────────────
PHASE 10 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

TRIAL USAGE INDICATOR (visible in navbar right zone, between share and avatar):
  Shown ONLY for users on free trial (plan = "trial"):
  .trial-pill {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1-5);
    padding: 4px 10px;
    background: var(--surface-raised);
    border: 1px solid var(--border);
    border-radius: 999px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
  }
  Content: "✦ 7 / 10 free queries"
  When 3 or fewer remain: border-color changes to var(--amber-500), text becomes amber
  When 1 remains: border-color var(--red-500), text becomes red
  Clicking it opens the Upgrade Modal

UPGRADE MODAL (appears automatically after query 10):
  Backdrop: fixed inset-0, bg rgba(0,0,0,0.6), z-index 100
  Modal: centered, max-width 480px, var(--surface-base), rounded-xl, shadow-2xl

  Header zone (no X close button — modal IS dismissable via ESC but not if
  triggered by query limit; if triggered by query limit, no dismiss):
    DocuMindAI logomark centered, 32px
    "Your free trial is complete" — Instrument Serif 24px, var(--text-primary)
    "You've experienced DocuMindAI fully. Ready to unlock unlimited access?" —
    13px var(--text-secondary), centered, max-width 360px

  What you got zone (amber background pill, full width, 12px text):
    "✓ All 7 workspaces · All features · Export · Preview · Citations"
    This reminds them what they already used — reinforces value.

  Plan card (brand blue border, full width):
    PROFESSIONAL PLAN
    ₹999 / month  (₹799 if billed annually — saves ₹2,400/year)
    [ Annual — Best Value ✓ ]  [ Monthly ] — radio toggle
    Divider line
    Feature list (checkmarks, 13px):
      ✓ Unlimited queries
      ✓ All 7 workspaces
      ✓ Unlimited documents (50MB each)
      ✓ PDF, DOCX, Markdown export
      ✓ Session sharing + API access
      ✓ GST & Tax auto-updates (Phase 13)
    [Subscribe Now →] — .btn .btn-primary, full width, 44px height

  Footer:
    "Questions? Chat with us →" — small link
    "Cancel anytime. No lock-in." — 11px var(--text-tertiary), centered

TRIAL QUERY INTERCEPT (after query 10 if using free plan — before modal):
  The last (10th) query runs FULLY and returns a complete response.
  ONLY AFTER the response is rendered does the modal appear (500ms delay).
  This ensures they see the value one last time before the paywall.

TRIAL BADGE IN WORKSPACE DROPDOWN:
  Next to each workspace name in the dropdown: no lock icons, no restrictions.
  During trial: all workspaces accessible.
  After trial expires: workspace names have a subtle lock icon (🔒) except General.
  Clicking a locked workspace → opens Upgrade Modal.

─────────────────────────────────────────────────────────────────────
PHASE 10 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 10.1 — Backend: User Model Trial Fields

File: backend/app/models/user.py
ADD these fields to the User model:
  plan              = Column(String, default="trial")
  # Values: "trial" | "professional" | "business" | "enterprise"
  trial_queries_used = Column(Integer, default=0, nullable=False)
  trial_started_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
  subscribed_at     = Column(DateTime, nullable=True)
  subscription_ends_at = Column(DateTime, nullable=True)

Run Alembic migration: "add_user_plan_trial_fields"

TASK 10.2 — Backend: Trial Enforcement Middleware

File: backend/app/core/trial_enforcement.py
CREATE:

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from sqlalchemy import select, update

TRIAL_QUERY_LIMIT = 10  # Change this one number to adjust trial length

async def check_and_increment_trial(
    user_id: str,
    db: AsyncSession
) -> dict:
    """
    Returns: {
      "allowed": bool,
      "queries_used": int,
      "queries_remaining": int,
      "plan": str
    }
    Raises HTTP 402 if trial exhausted and plan is still "trial".
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Non-trial users: always allowed
    if user.plan != "trial":
        return {
            "allowed": True,
            "queries_used": None,
            "queries_remaining": None,
            "plan": user.plan
        }

    # Trial users: check limit
    if user.trial_queries_used >= TRIAL_QUERY_LIMIT:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "trial_exhausted",
                "message": "Your free trial of 10 queries is complete.",
                "queries_used": user.trial_queries_used,
                "trial_limit": TRIAL_QUERY_LIMIT,
                "upgrade_url": "/upgrade"
            }
        )

    # Increment atomically
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(trial_queries_used=User.trial_queries_used + 1)
    )
    await db.commit()

    new_count = user.trial_queries_used + 1
    return {
        "allowed": True,
        "queries_used": new_count,
        "queries_remaining": TRIAL_QUERY_LIMIT - new_count,
        "plan": "trial"
    }

TASK 10.3 — Backend: Inject Trial Check Into Query Endpoint

File: backend/app/api/v1/endpoints/query.py
EDIT — add trial check at START of the streaming endpoint, BEFORE retrieval:

  from app.core.trial_enforcement import check_and_increment_trial

  # Inside the query handler, FIRST LINE after auth:
  trial_status = await check_and_increment_trial(
      user_id=str(current_user.id),
      db=db
  )

  # Add trial status to SSE stream header so frontend can update counter:
  # Yield this as the FIRST SSE event before any retrieval events:
  if trial_status["plan"] == "trial":
      yield f"data: {json.dumps({'type': 'trial_status', 'queries_used': trial_status['queries_used'], 'queries_remaining': trial_status['queries_remaining']})}\n\n"

TASK 10.4 — Backend: Upgrade Endpoint (Placeholder)

File: backend/app/api/v1/endpoints/billing.py
CREATE:

  POST /billing/upgrade:
    # For now, manually sets plan to "professional" for testing
    # In production: integrate Razorpay / Stripe webhook to set plan
    body: { "plan": "professional", "billing_cycle": "monthly" | "annual" }
    Sets user.plan = "professional"
    Sets user.subscribed_at = datetime.utcnow()
    Sets user.subscription_ends_at = now + 30 days (monthly) or 365 days (annual)
    Returns: { "success": true, "plan": "professional", "message": "Subscription activated" }

  GET /billing/status:
    Returns: { "plan": str, "trial_queries_used": int, "queries_remaining": int,
               "subscribed_at": datetime | null, "subscription_ends_at": datetime | null }

TASK 10.5 — Frontend: Trial Status in App State

File: frontend/src/lib/store/trialStore.ts
CREATE (using React context or Zustand — whichever state management is in use):

  interface TrialState {
    plan: "trial" | "professional" | "business" | "enterprise"
    queriesUsed: number
    queriesRemaining: number
    showUpgradeModal: boolean
  }

  // Updated from two sources:
  // 1. GET /billing/status on app load (after auth)
  // 2. SSE "trial_status" event on each query

TASK 10.6 — Frontend: Trial Pill Component

File: frontend/src/components/TrialPill.tsx
CREATE per design spec above.
Props: { queriesUsed: number, queriesRemaining: number, onClick: () => void }
Rendered in: LayoutWrapper.tsx navbar right zone (between Share and Avatar)
Hidden when: user.plan !== "trial"

TASK 10.7 — Frontend: Upgrade Modal Component

File: frontend/src/components/UpgradeModal.tsx
CREATE per design spec above.
Props: { trigger: "limit_reached" | "user_click" | "locked_workspace" }
When trigger = "limit_reached": no ESC dismiss, no X button
When trigger = "user_click" or "locked_workspace": ESC + X button available
Wire to: TrialPill onClick, post-query-10 SSE event, locked workspace click

TASK 10.8 — Frontend: Handle 402 Response

File: frontend/src/lib/api.ts
EDIT — in the SSE reader / apiFetch handler:
  if (response.status === 402) {
    const error = await response.json()
    if (error.detail?.error === "trial_exhausted") {
      // Update trial store → triggers UpgradeModal
      trialStore.setShowUpgradeModal(true)
      return // Don't throw — handle gracefully
    }
  }

─────────────────────────────────────────────────────────────────────
PHASE 10 — VERIFICATION
─────────────────────────────────────────────────────────────────────

# Backend
python -c "from app.core.trial_enforcement import check_and_increment_trial; print('OK')"
# Alembic
alembic upgrade head
# Manual: Register new user → GET /billing/status → confirm plan="trial", queries_used=0
# Manual: Run 10 queries → confirm trial_queries_used increments
# Manual: Run 11th query → confirm HTTP 402 with trial_exhausted error
# Manual: TrialPill shows "1 / 10 free queries" then "9 / 10 free queries" etc.
# Manual: After 10th query, UpgradeModal appears with 500ms delay
# TypeScript: npx tsc --noEmit

DEFINITION OF DONE — PHASE 10:
✅ New users get FULL access (all workspaces, no limits) for 10 queries
✅ Query counter increments atomically per query
✅ Trial pill visible in navbar, updates after each query
✅ 10th query runs fully — modal appears AFTER response renders
✅ 402 handled gracefully — no blank screen, no error toast (only modal)
✅ Non-trial users unaffected — zero performance impact

[CHECKPOINT 10 COMPLETE — Proceeding to Phase 11]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 11 — TEACHER TABLE EXTRACTION (PERFECT TABLE EXPORT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Teachers upload handwritten notes, textbooks, or any document
that contains structured tables. DocuMindAI extracts those tables with
ZERO alignment changes, ZERO cell merging errors, ZERO data loss.
The extracted table can be:
  a) Copied as HTML table (paste directly into Google Docs / Word)
  b) Exported as DOCX with a perfectly formatted Word table
  c) Downloaded as CSV for Excel
  d) Previewed in-app in a live interactive grid
ESTIMATED TIME: 5–6 hours | RISK: Medium | DEPENDS ON: Phase 6-T complete

─────────────────────────────────────────────────────────────────────
PHASE 11 — HOW TABLE EXTRACTION WORKS
─────────────────────────────────────────────────────────────────────

The extraction pipeline uses TWO layers:

LAYER 1 — Docling (already in tech stack):
  Docling is purpose-built for structured document understanding.
  It detects table boundaries, header rows, merged cells, rowspan/colspan.
  Returns tables as structured JSON:
  {
    "tables": [
      {
        "page": 2,
        "bbox": { "x0": 50, "y0": 120, "x1": 540, "y1": 380 },
        "rows": [
          ["Subject", "Marks", "Grade"],   // header row
          ["Mathematics", "92", "A1"],
          ["Physics", "87", "A2"]
        ],
        "merged_cells": [],
        "caption": "Table 1: Student Report Card"
      }
    ]
  }

LAYER 2 — PaddleOCR (for handwritten notes / scanned tables):
  If the document is a photograph or scan, Docling alone may miss tables.
  PaddleOCR detects table structure in images + performs OCR on each cell.
  Returns the same JSON structure above.

ROUTING LOGIC (table_extractor.py):
  IF document.is_native_pdf AND tables_detected_by_docling:
      → Use Docling output directly (fastest, most accurate)
  ELIF document.is_scanned OR document.is_image:
      → Route through PaddleOCR table detection
  ELSE:
      → Fallback: try Docling, if 0 tables → PaddleOCR → if 0 tables → tell user

─────────────────────────────────────────────────────────────────────
PHASE 11 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

TEACHER WORKSPACE — NEW "EXTRACT TABLES" BUTTON:
  Location: Action buttons row below textarea (alongside existing buttons)
  Appearance: .btn .btn-secondary, icon + label: "⊞ Extract Tables"
  Keyboard: Cmd+Shift+T

TABLE EXTRACTION PANEL (slides from right, 520px wide — wider than preview):
  Header:
    "📊 Tables Found" — 16px semibold
    "N tables detected across N pages" — 13px var(--text-secondary)
    × close button (right)
    "Extract All" button (blue, right of title) — bulk extracts all tables

  Table Selector (if multiple tables found):
    Horizontal scroll row of small pills: "Table 1 · p.2" "Table 2 · p.5" etc.
    Active pill: filled blue. Click to jump to that table.

  TABLE PREVIEW (main content area):
    Renders a live HTML table of the extracted data.
    Exact same cell structure as the source document.
    Header row: bold text, light blue background (var(--brand) at 10% opacity)
    Body rows: alternating white / var(--surface-sunken)
    Cell padding: 8px 12px
    Border: 1px solid var(--border-subtle)
    NO width constraints — table scrolls horizontally if wide
    Font: var(--font-mono) for numbers, var(--font-base) for text

  Per-Table Actions (below each table):
    [📋 Copy as HTML] → copies <table>...</table> HTML → paste into Google Docs/Word
    [📄 Export DOCX] → downloads .docx with the exact table
    [📊 Export CSV]  → downloads .csv
    [✏ Edit Cells]  → makes table cells editable (inline edit before export)
    Caption (shown below table if detected): italic 12px "Table 1: Student Report Card"
    Source: "📍 Found on page 2" chip

  EDIT CELLS MODE:
    Each cell becomes a contenteditable div
    [✓ Save Changes] button confirms edits (updates in-memory only, not re-OCR)
    [✕ Reset] button reverts to OCR output
    Purpose: fix minor OCR errors before exporting

  EMPTY STATE (no tables found):
    Icon: grid with question mark
    "No structured tables detected in this document."
    "Try uploading a clearer image or a native PDF with embedded tables."
    "If your table is in a scanned image, ensure the image is well-lit and horizontal."

  PROCESSING STATE:
    Spinner + "Scanning document for tables..."
    Progress: "Page 3 of 12 scanned..." (real-time via SSE)

─────────────────────────────────────────────────────────────────────
PHASE 11 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 11.1 — Backend: Table Extraction Service

File: backend/app/services/table_extractor.py
CREATE:

import json
from docling.document_converter import DocumentConverter
from app.models.document import Document
from typing import List, Dict, Any

class TableExtractor:
    def __init__(self):
        self.converter = DocumentConverter()

    async def extract_tables(
        self,
        file_path: str,
        is_scanned: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Returns list of table dicts:
        {
          "table_index": int,
          "page": int,
          "rows": List[List[str]],   # 2D array, row-major order
          "has_header": bool,        # first row is header?
          "caption": str | None,
          "merged_cells": List[dict] # {row, col, rowspan, colspan}
        }
        """
        if is_scanned:
            return await self._extract_with_paddle(file_path)
        else:
            return await self._extract_with_docling(file_path)

    async def _extract_with_docling(self, file_path: str) -> List[Dict]:
        result = self.converter.convert(file_path)
        tables = []
        for i, table in enumerate(result.document.tables):
            rows = []
            for row in table.data:
                rows.append([cell.text.strip() for cell in row])
            tables.append({
                "table_index": i,
                "page": table.prov[0].page_no if table.prov else None,
                "rows": rows,
                "has_header": len(rows) > 1,  # assume first row is header
                "caption": table.caption_text if hasattr(table, 'caption_text') else None,
                "merged_cells": []
            })
        return tables

    async def _extract_with_paddle(self, file_path: str) -> List[Dict]:
        from paddleocr import PPStructure
        engine = PPStructure(table=True, ocr=True, show_log=False, lang='en')
        import cv2
        img = cv2.imread(file_path)
        result = engine(img)
        tables = []
        idx = 0
        for region in result:
            if region["type"] == "table":
                # Parse HTML table from PaddleOCR output
                from html.parser import HTMLParser
                rows = self._parse_html_table(region["res"]["html"])
                tables.append({
                    "table_index": idx,
                    "page": 1,
                    "rows": rows,
                    "has_header": True,
                    "caption": None,
                    "merged_cells": []
                })
                idx += 1
        return tables

    def _parse_html_table(self, html: str) -> List[List[str]]:
        # Simple HTML table → 2D array parser
        import re
        rows = []
        for row_match in re.finditer(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL):
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_match.group(1), re.DOTALL)
            rows.append([re.sub(r'<[^>]+>', '', c).strip() for c in cells])
        return rows

    def export_to_docx(self, table: Dict, output_path: str) -> str:
        """Exports a single table to DOCX with exact structure preserved."""
        from docx import Document as DocxDocument
        from docx.shared import Pt, RGBColor
        from docx.oxml.ns import qn
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = DocxDocument()
        if table.get("caption"):
            p = doc.add_paragraph(table["caption"])
            p.style.font.italic = True

        rows = table["rows"]
        if not rows:
            return output_path

        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"

        for row_idx, row in enumerate(rows):
            for col_idx, cell_text in enumerate(row):
                cell = t.cell(row_idx, col_idx)
                cell.text = cell_text
                # Header row styling
                if row_idx == 0 and table.get("has_header"):
                    run = cell.paragraphs[0].runs
                    if run:
                        run[0].bold = True
                    # Light blue fill for header
                    tc = cell._tc
                    tcPr = tc.get_or_add_tcPr()
                    shd = OxmlElement('w:shd')
                    shd.set(qn('w:fill'), 'DBEAFE')  # brand blue 10%
                    shd.set(qn('w:val'), 'clear')
                    tcPr.append(shd)

        doc.save(output_path)
        return output_path

    def export_to_csv(self, table: Dict) -> str:
        """Returns CSV string."""
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)
        for row in table["rows"]:
            writer.writerow(row)
        return output.getvalue()

    def export_to_html(self, table: Dict) -> str:
        """Returns clean HTML table string for clipboard."""
        rows = table["rows"]
        html = '<table border="1" style="border-collapse:collapse;font-family:Arial,sans-serif;">\n'
        for row_idx, row in enumerate(rows):
            html += '  <tr>\n'
            tag = 'th' if row_idx == 0 and table.get("has_header") else 'td'
            for cell in row:
                style = 'padding:8px 12px;' + (
                    'background:#DBEAFE;font-weight:600;' if tag == 'th' else ''
                )
                html += f'    <{tag} style="{style}">{cell}</{tag}>\n'
            html += '  </tr>\n'
        html += '</table>'
        return html

# Singleton
_table_extractor_instance = None
def get_table_extractor() -> TableExtractor:
    global _table_extractor_instance
    if _table_extractor_instance is None:
        _table_extractor_instance = TableExtractor()
    return _table_extractor_instance

TASK 11.2 — Backend: Table Extraction Endpoint

File: backend/app/api/v1/endpoints/exams.py
ADD to existing exams router:

  POST /exams/extract-tables:
    body: { "document_id": str }
    Auth: required
    Steps:
      1. Verify document belongs to current_user
      2. Get document file_path and is_scanned flag
      3. extractor = get_table_extractor()
      4. tables = await extractor.extract_tables(file_path, is_scanned)
      5. Return: {
           "document_id": str,
           "tables_found": len(tables),
           "tables": tables  # list of table dicts
         }
    If no tables: return { "tables_found": 0, "tables": [] }
    If file not found: HTTP 404

  POST /exams/export-table:
    body: { "table": TableDict, "format": "docx" | "csv" | "html" }
    Auth: required
    Steps:
      if format == "docx":
          path = f"/tmp/table_{uuid4()}.docx"
          extractor.export_to_docx(table, path)
          return FileResponse(path, filename="extracted_table.docx")
      elif format == "csv":
          csv_str = extractor.export_to_csv(table)
          return Response(csv_str, media_type="text/csv",
                         headers={"Content-Disposition": "attachment; filename=table.csv"})
      elif format == "html":
          html = extractor.export_to_html(table)
          return { "html": html }  # Frontend copies this to clipboard

TASK 11.3 — Frontend: Extract Tables Button

File: frontend/src/app/exam/page.tsx
ADD "⊞ Extract Tables" button to action buttons row.
Wire to: open TableExtractionPanel component
Keyboard shortcut: Cmd+Shift+T

TASK 11.4 — Frontend: TableExtractionPanel Component

File: frontend/src/components/teacher/TableExtractionPanel.tsx
CREATE — full panel per design spec above.

Key implementation details:
  // Fetch tables when panel opens and a document is selected
  const [tables, setTables] = useState<ExtractedTable[]>([])
  const [loading, setLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editedRows, setEditedRows] = useState<string[][]>([])

  // Copy HTML to clipboard
  const copyAsHtml = async (table: ExtractedTable) => {
    const html = await apiFetch('/exams/export-table', {
      method: 'POST',
      body: JSON.stringify({ table, format: 'html' })
    })
    await navigator.clipboard.writeText(html.html)
    toast.success('Table copied! Paste into Google Docs or Word.')
  }

  // Download DOCX
  const exportDocx = async (table: ExtractedTable) => {
    const response = await fetch('/api/exams/export-table', {
      method: 'POST',
      body: JSON.stringify({ table, format: 'docx' }),
      headers: { 'Content-Type': 'application/json' }
    })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'extracted_table.docx'
    a.click()
    URL.revokeObjectURL(url)
  }

  // Render table in UI
  const renderTable = (table: ExtractedTable, editable: boolean) => (
    <div className="overflow-x-auto">
      <table className="border-collapse text-sm">
        {table.rows.map((row, rowIdx) => (
          <tr key={rowIdx}>
            {row.map((cell, colIdx) => {
              const Tag = rowIdx === 0 && table.has_header ? 'th' : 'td'
              return (
                <Tag
                  key={colIdx}
                  contentEditable={editable}
                  suppressContentEditableWarning
                  onBlur={(e) => updateCell(rowIdx, colIdx, e.target.textContent ?? '')}
                  className={`border border-[var(--border)] px-3 py-2 ${
                    rowIdx === 0 && table.has_header
                      ? 'bg-blue-50 font-semibold dark:bg-blue-950/30'
                      : 'bg-[var(--surface-base)]'
                  }`}
                >
                  {editable ? editedRows[rowIdx]?.[colIdx] ?? cell : cell}
                </Tag>
              )
            })}
          </tr>
        ))}
      </table>
    </div>
  )

TASK 11.5 — Frontend: Add to Document Chips

File: frontend/src/components/WorkspaceUI.tsx
In Teacher workspace only: when a document chip is hovered/focused,
show "Extract Tables" as an additional action (alongside "Preview"):
  "⊞ Tables" button → opens TableExtractionPanel pre-loaded with that document

─────────────────────────────────────────────────────────────────────
PHASE 11 — VERIFICATION
─────────────────────────────────────────────────────────────────────

# Backend
python -c "from app.services.table_extractor import get_table_extractor; print('OK')"
# Manual: Upload a PDF with a table → POST /exams/extract-tables → confirm tables array
# Manual: Export that table as DOCX → open in Word → confirm no alignment changes
# Manual: Copy HTML → paste into Google Docs → confirm table looks identical
# Manual: Upload a handwritten notes photo → confirm PaddleOCR path triggers
# Manual: Document with no tables → confirm empty state shows (not an error)
# TypeScript: npx tsc --noEmit

DEFINITION OF DONE — PHASE 11:
✅ Tables extracted from native PDFs via Docling
✅ Tables extracted from scanned/handwritten documents via PaddleOCR
✅ DOCX export opens in Word with identical structure (zero alignment drift)
✅ HTML copy pastes into Google Docs preserving columns and header
✅ CSV export opens cleanly in Excel
✅ In-app edit mode works before export
✅ Teacher workspace shows "Extract Tables" button and "⊞ Tables" on document chips

[CHECKPOINT 11 COMPLETE — Proceeding to Phase 12]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 12 — DYNAMIC API KEY ROTATION (ZERO HARDCODED COUNT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: The system reads ALL Gemini API keys from .env automatically.
Adding a new key = add one line to .env, restart. No code changes ever.
Keys rotate round-robin. On 429 (rate limit), instantly rotate to next key.
On 403 (invalid key), skip that key permanently until restart.
ESTIMATED TIME: 2–3 hours | RISK: Low | DEPENDS ON: Phase 7 complete

─────────────────────────────────────────────────────────────────────
PHASE 12 — HOW TO ADD API KEYS (THE ONLY CHANGE EVER NEEDED)
─────────────────────────────────────────────────────────────────────

In .env.local — just add more lines in this pattern:
  GEMINI_API_KEY_1=AIzaSy...key1...
  GEMINI_API_KEY_2=AIzaSy...key2...
  GEMINI_API_KEY_3=AIzaSy...key3...
  # Add as many as you want — any number
  # The system counts them automatically

No code changes. No config changes. Restart backend. Done.

─────────────────────────────────────────────────────────────────────
PHASE 12 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 12.1 — Backend: LLM Key Rotation Service

File: backend/app/services/llm_key_rotation.py
CREATE — THIS FILE IS STABLE AFTER CREATION. DO NOT MODIFY IT.

import os
import threading
import time
import logging
from typing import List, Optional
from itertools import cycle

logger = logging.getLogger(__name__)

class GeminiKeyRotator:
    """
    Dynamically reads ALL GEMINI_API_KEY_N keys from environment.
    Rotates round-robin. Handles 429 (rate limit) and 403 (invalid key).
    Thread-safe. Singleton pattern.

    .env pattern: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... (any count)
    Also accepts GEMINI_API_KEY (single key, legacy support).
    """

    def __init__(self):
        self._keys: List[str] = []
        self._bad_keys: set = set()      # permanently skip these (403)
        self._cooling_keys: dict = {}    # key → cooldown_until timestamp (429)
        self._lock = threading.Lock()
        self._cycle = None
        self._load_keys()

    def _load_keys(self):
        """
        Reads keys from environment. Supports:
          GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... (recommended, unlimited)
          GEMINI_API_KEY (single key, legacy)
        """
        keys = []

        # Read numbered keys (GEMINI_API_KEY_1, _2, _3, ...)
        i = 1
        while True:
            key = os.environ.get(f"GEMINI_API_KEY_{i}")
            if key and key.strip():
                keys.append(key.strip())
                i += 1
            else:
                break  # Stop at first missing number — no need to scan further

        # Also read GEMINI_API_KEY (single key legacy support)
        single = os.environ.get("GEMINI_API_KEY")
        if single and single.strip() and single.strip() not in keys:
            keys.append(single.strip())

        if not keys:
            raise RuntimeError(
                "No Gemini API keys found in environment. "
                "Set GEMINI_API_KEY_1 (and optionally GEMINI_API_KEY_2, _3, ...) in .env"
            )

        self._keys = keys
        self._cycle = cycle(keys)
        logger.info(f"GeminiKeyRotator loaded {len(keys)} API key(s)")

    def get_key(self) -> str:
        """
        Returns the next available API key.
        Skips: permanently bad keys (403), cooling-down keys (429).
        If ALL keys are unavailable, waits for the soonest cooldown to end.
        """
        with self._lock:
            now = time.time()
            available = [
                k for k in self._keys
                if k not in self._bad_keys
                and self._cooling_keys.get(k, 0) <= now
            ]

            if not available:
                # All keys cooling — wait for the soonest one
                soonest = min(self._cooling_keys.values())
                wait_time = max(0, soonest - now)
                logger.warning(f"All API keys cooling. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time + 0.5)
                # Retry after wait
                available = [
                    k for k in self._keys
                    if k not in self._bad_keys
                ]

            if not available:
                raise RuntimeError(
                    "All API keys are invalid (403). "
                    "Add valid keys to .env and restart."
                )

            # Round-robin through available keys
            for _ in range(len(self._keys)):
                key = next(self._cycle)
                if key in available:
                    return key

            return available[0]  # Fallback

    def report_rate_limit(self, key: str, retry_after_seconds: int = 60):
        """Call this when Gemini returns 429. Cools down the key."""
        with self._lock:
            cooldown_until = time.time() + retry_after_seconds
            self._cooling_keys[key] = cooldown_until
            logger.warning(
                f"API key ...{key[-6:]} rate-limited. "
                f"Cooling for {retry_after_seconds}s."
            )

    def report_invalid_key(self, key: str):
        """Call this when Gemini returns 403. Permanently skips the key."""
        with self._lock:
            self._bad_keys.add(key)
            logger.error(
                f"API key ...{key[-6:]} is invalid (403). "
                f"Permanently skipping. {len(self._keys) - len(self._bad_keys)} "
                f"keys remaining."
            )

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    @property
    def available_keys(self) -> int:
        now = time.time()
        return len([
            k for k in self._keys
            if k not in self._bad_keys
            and self._cooling_keys.get(k, 0) <= now
        ])

    @property
    def key_status(self) -> dict:
        """For /health endpoint — shows key health without exposing actual keys."""
        now = time.time()
        return {
            "total": self.total_keys,
            "available": self.available_keys,
            "cooling": len([k for k, t in self._cooling_keys.items() if t > now]),
            "invalid": len(self._bad_keys)
        }

# Singleton
_rotator_instance: Optional[GeminiKeyRotator] = None

def get_key_rotator() -> GeminiKeyRotator:
    global _rotator_instance
    if _rotator_instance is None:
        _rotator_instance = GeminiKeyRotator()
    return _rotator_instance

TASK 12.2 — Backend: Integrate Key Rotator into LLM Service

File: backend/app/services/llm_service.py
NOTE: This is a STABLE SYSTEM. Make only targeted additions.

FIND: wherever the Gemini client is initialized with an API key
REPLACE the static key with rotator call:

  from app.services.llm_key_rotation import get_key_rotator

  # In the generate/stream function:
  rotator = get_key_rotator()
  current_key = rotator.get_key()

  try:
      genai.configure(api_key=current_key)
      # ... existing Gemini call ...

  except Exception as e:
      error_str = str(e)
      if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
          # Extract retry-after from headers if available, default 60s
          rotator.report_rate_limit(current_key, retry_after_seconds=60)
          # Retry once with next key
          current_key = rotator.get_key()
          genai.configure(api_key=current_key)
          # ... retry same call ...
      elif "403" in error_str or "API_KEY_INVALID" in error_str:
          rotator.report_invalid_key(current_key)
          current_key = rotator.get_key()
          genai.configure(api_key=current_key)
          # ... retry same call ...
      else:
          raise  # Unknown error — let circuit breaker handle it

TASK 12.3 — Backend: Update .env.local Template

File: backend/.env.local (or .env — whichever is used)
RENAME: GEMINI_API_KEY → GEMINI_API_KEY_1
ADD comment explaining the pattern:

  # GEMINI API KEYS — Add as many as needed. No code changes required.
  # Pattern: GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3, ...
  # The system auto-detects all keys and rotates them round-robin.
  # On 429 (rate limit): that key cools down, others continue.
  # On 403 (invalid key): that key is permanently skipped until restart.
  GEMINI_API_KEY_1=your_first_key_here
  # GEMINI_API_KEY_2=your_second_key_here  # uncomment to add more

TASK 12.4 — Backend: Update /health Endpoint

File: backend/app/api/v1/endpoints/health.py
ADD key rotation status to the health response:

  from app.services.llm_key_rotation import get_key_rotator

  # In the health check response dict:
  "llm_keys": get_key_rotator().key_status
  # Returns: { "total": 3, "available": 3, "cooling": 0, "invalid": 0 }
  # NEVER returns actual key values

TASK 12.5 — Update docker-compose.yml Reference Comment

  # In docker-compose.yml, add comment (do not change actual config):
  # environment:
  #   GEMINI_API_KEY_1: ${GEMINI_API_KEY_1}
  #   # Add GEMINI_API_KEY_2, _3, etc. as needed — auto-detected by rotator

─────────────────────────────────────────────────────────────────────
PHASE 12 — VERIFICATION
─────────────────────────────────────────────────────────────────────

# Test with 1 key
python -c "
import os
os.environ['GEMINI_API_KEY_1'] = 'test_key_1'
from app.services.llm_key_rotation import get_key_rotator
r = get_key_rotator()
print(f'Keys loaded: {r.total_keys}')  # Should print 1
print(r.key_status)
"

# Test with 3 keys
python -c "
import os
os.environ['GEMINI_API_KEY_1'] = 'key1'
os.environ['GEMINI_API_KEY_2'] = 'key2'
os.environ['GEMINI_API_KEY_3'] = 'key3'
from app.services.llm_key_rotation import GeminiKeyRotator
r = GeminiKeyRotator()
print(f'Keys loaded: {r.total_keys}')  # Should print 3
r.report_rate_limit('key1', 30)
print(f'Available after rate limit: {r.available_keys}')  # Should print 2
"

# Manual: Add GEMINI_API_KEY_2 to .env → restart → GET /health → confirm total=2
# Manual: Run 20 queries → confirm no errors (keys rotating)
# Manual: GET /health → llm_keys shows total/available/cooling/invalid

DEFINITION OF DONE — PHASE 12:
✅ Adding GEMINI_API_KEY_2 to .env (no other change) → system uses both keys
✅ 429 response → that key cools 60s → next key used immediately (no user-visible error)
✅ 403 response → that key skipped permanently until restart
✅ /health shows key status (never actual key values)
✅ Original single GEMINI_API_KEY still works (backward compatible)

[CHECKPOINT 12 COMPLETE — Proceeding to Phase 13]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 13 — GST & TAX AUTO-UPDATE AUTOMATION (DAILY, NO CODE CHANGES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: GST rates, TDS rates, and income tax slabs change over time.
This phase builds a fully automated pipeline that:
  1. Scrapes official government sources daily at 6:00 AM
  2. Detects what changed vs. the previous day
  3. Updates the tax_rates database table automatically
  4. Notifies relevant users about changes
  5. Makes the Finance/GST workspace answer with current values ALWAYS
No code changes needed when rates change — the database updates itself.
ESTIMATED TIME: 7–8 hours | RISK: Medium | DEPENDS ON: Phase 7 complete

─────────────────────────────────────────────────────────────────────
PHASE 13 — DATABASE SCHEMA
─────────────────────────────────────────────────────────────────────

TASK 13.1 — Backend: Tax Database Models

File: backend/app/models/tax_data.py
CREATE:

from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from datetime import datetime
from app.db.base import Base

class TaxRate(Base):
    __tablename__ = "tax_rates"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category        = Column(String, nullable=False, index=True)
    # Values: "gst" | "tds" | "income_tax" | "customs" | "cess"

    subcategory     = Column(String, nullable=False)
    # For GST: HSN code range or item description
    # For TDS: Section number (e.g., "194C", "194J")
    # For IT: "old_regime" | "new_regime" | "corporate"

    description     = Column(Text, nullable=False)
    # Human readable: "Laptops and notebooks" or "Contract payments"

    rate            = Column(Float, nullable=True)
    # Percentage value. None if "nil" or "exempt"

    rate_type       = Column(String, default="percentage")
    # "percentage" | "nil" | "exempt" | "specific" (specific amount, not %)

    threshold_inr   = Column(Float, nullable=True)
    # For TDS: threshold limit before deduction applies

    effective_date  = Column(DateTime, nullable=False)
    # When this rate became effective

    notification_no = Column(String, nullable=True)
    # Official notification number, e.g., "15/2025-CT(Rate)"

    notification_url = Column(String, nullable=True)
    # URL to the official notification PDF

    source          = Column(String, nullable=False)
    # "cbic.gov.in" | "incometaxindia.gov.in" | "manual"

    is_current      = Column(Boolean, default=True, index=True)
    # False for superseded rates (kept for historical reference)

    previous_rate   = Column(Float, nullable=True)
    # Previous rate before this update (for change detection UI)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hsn_code        = Column(String, nullable=True, index=True)
    # For GST items: specific HSN code (e.g., "8471")

    tds_section     = Column(String, nullable=True, index=True)
    # For TDS: "194C", "194J", "194I", etc.

    applicability   = Column(JSON, nullable=True)
    # e.g., {"individual": 1.0, "company": 2.0} for different TDS rates

class TaxUpdateLog(Base):
    __tablename__ = "tax_update_logs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    scrape_date     = Column(DateTime, default=datetime.utcnow)
    source          = Column(String, nullable=False)
    items_checked   = Column(Integer, default=0)
    items_changed   = Column(Integer, default=0)
    items_added     = Column(Integer, default=0)
    error           = Column(Text, nullable=True)
    status          = Column(String, default="success")  # "success" | "partial" | "failed"
    changes_summary = Column(JSON, nullable=True)
    # List of { "description": str, "old_rate": float, "new_rate": float }

Run Alembic migration: "add_tax_rates_and_update_logs"

─────────────────────────────────────────────────────────────────────
PHASE 13 — SCRAPER SERVICES
─────────────────────────────────────────────────────────────────────

TASK 13.2 — Backend: Tax Data Scrapers

File: backend/app/services/tax_scrapers/base_scraper.py
CREATE:

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging, httpx

logger = logging.getLogger(__name__)

class BaseTaxScraper(ABC):
    """Base class for all tax data scrapers."""

    source_name: str = ""
    source_url: str = ""
    timeout: int = 30

    async def fetch_url(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers={
                "User-Agent": "DocuMindAI-TaxBot/1.0 (Educational; contact@documindai.com)"
            })
            response.raise_for_status()
            return response.content

    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Returns list of rate dicts matching TaxRate model fields.
        Must be implemented by each scraper.
        """
        pass

    async def safe_scrape(self) -> List[Dict[str, Any]]:
        """Wraps scrape() with error handling."""
        try:
            return await self.scrape()
        except Exception as e:
            logger.error(f"Scraper {self.source_name} failed: {e}")
            return []

File: backend/app/services/tax_scrapers/gst_scraper.py
CREATE:

"""
Scrapes GST rate changes from CBIC official notifications.
Source: https://www.cbic.gov.in/htdocs-cbec/gst/notfctn-2025-cgst-rate-english.htm
(URL updated annually — stored in config, not hardcoded)
"""

from app.services.tax_scrapers.base_scraper import BaseTaxScraper
import httpx, re, json
from datetime import datetime
from app.core.config import settings

class CBICGSTScraper(BaseTaxScraper):
    source_name = "cbic.gov.in"
    source_url = settings.CBIC_NOTIFICATION_URL  # from .env

    # KNOWN GST RATES DATABASE (baseline, kept as fallback)
    # This is NOT hardcoded rates — it's a SEED for the database.
    # The scraper updates these when official notifications change them.
    KNOWN_GST_ITEMS = [
        {"hsn": "8471", "description": "Laptops, notebooks, tablets",
         "rate": 18.0, "subcategory": "electronics"},
        {"hsn": "0101", "description": "Live horses, asses, mules",
         "rate": 0.0, "subcategory": "animals"},
        {"hsn": "4901", "description": "Printed books (not newspaper/periodicals)",
         "rate": 0.0, "subcategory": "education"},
        {"hsn": "9403", "description": "Furniture and parts",
         "rate": 18.0, "subcategory": "furniture"},
        {"hsn": "8517", "description": "Mobile phones",
         "rate": 18.0, "subcategory": "electronics"},
        {"hsn": "3004", "description": "Medicaments (formulated medicines)",
         "rate": 12.0, "subcategory": "pharmaceuticals"},
        {"hsn": "6109", "description": "T-shirts, vests (cotton)",
         "rate": 12.0, "subcategory": "apparel"},
        # ... Additional HSN codes added by the team over time
        # DO NOT hardcode all 10,000+ HSN codes here — only seed common ones.
        # The LLM prompt injection (Task 13.5) handles the full response.
    ]

    async def scrape(self):
        """
        Scrapes the CBIC notifications page for rate changes.
        Returns structured rate data.
        """
        results = []

        # Attempt live scrape
        try:
            content = await self.fetch_url(self.source_url)
            # Parse notification PDFs for rate changes
            # This is a best-effort scraper — if the page structure changes,
            # it falls back to the seeded database
            changes = self._parse_notification_page(content)
            results.extend(changes)
        except Exception as e:
            # Log and continue — the database still has yesterday's rates
            import logging
            logging.getLogger(__name__).warning(
                f"Live GST scrape failed ({e}). Using seeded data."
            )

        # Always return seeded items (they won't overwrite unless rate changed)
        for item in self.KNOWN_GST_ITEMS:
            results.append({
                "category": "gst",
                "subcategory": item["subcategory"],
                "description": item["description"],
                "hsn_code": item["hsn"],
                "rate": item["rate"],
                "rate_type": "percentage" if item["rate"] > 0 else "nil",
                "source": self.source_name,
                "effective_date": datetime.now(),
                "notification_no": None
            })

        return results

    def _parse_notification_page(self, html_bytes: bytes) -> list:
        """
        Parses CBIC notification list page.
        Looks for patterns like "18% to 12%" or "exempted" in notification titles.
        Returns change records to cross-check against database.
        """
        html = html_bytes.decode('utf-8', errors='replace')
        # Find notification patterns
        rate_change_pattern = re.compile(
            r'(\d+\.?\d*)\s*%\s*to\s*(\d+\.?\d*)\s*%', re.IGNORECASE
        )
        changes = []
        for match in rate_change_pattern.finditer(html):
            changes.append({
                "old_rate": float(match.group(1)),
                "new_rate": float(match.group(2)),
                "context": html[max(0, match.start()-100):match.end()+100]
            })
        return []  # Returns processed list (implementation-specific to page structure)


File: backend/app/services/tax_scrapers/tds_scraper.py
CREATE:

"""
Maintains TDS rate database from Income Tax Act Section lookup.
Source: incometaxindia.gov.in
"""

from app.services.tax_scrapers.base_scraper import BaseTaxScraper
from datetime import datetime

class TDSRateScraper(BaseTaxScraper):
    source_name = "incometaxindia.gov.in"

    # TDS RATE SEED DATABASE (all major sections as of FY 2024-25)
    # Updated annually after Budget. Scraper detects changes.
    TDS_SECTIONS = [
        {"section": "192",  "description": "Salary",
         "rate_individual": None, "rate_company": None,
         "threshold": 0, "note": "As per slab rates"},
        {"section": "194A", "description": "Interest (other than securities)",
         "rate_individual": 10.0, "rate_company": 10.0, "threshold": 40000},
        {"section": "194C", "description": "Contractor/sub-contractor payments",
         "rate_individual": 1.0, "rate_company": 2.0, "threshold": 30000},
        {"section": "194D", "description": "Insurance commission",
         "rate_individual": 5.0, "rate_company": 10.0, "threshold": 15000},
        {"section": "194H", "description": "Commission or brokerage",
         "rate_individual": 5.0, "rate_company": 5.0, "threshold": 15000},
        {"section": "194I", "description": "Rent (land/building/furniture)",
         "rate_individual": 10.0, "rate_company": 10.0, "threshold": 240000},
        {"section": "194J", "description": "Professional/technical fees",
         "rate_individual": 10.0, "rate_company": 10.0, "threshold": 30000},
        {"section": "194Q", "description": "Purchase of goods",
         "rate_individual": 0.1, "rate_company": 0.1, "threshold": 5000000},
        {"section": "206C", "description": "Tax collected at source (TCS)",
         "rate_individual": 1.0, "rate_company": 1.0, "threshold": 0},
        # Add more sections as needed — no code changes required, just add to this list
    ]

    async def scrape(self):
        results = []
        for section in self.TDS_SECTIONS:
            results.append({
                "category": "tds",
                "subcategory": "tds_section",
                "description": section["description"],
                "tds_section": section["section"],
                "rate": section.get("rate_individual"),
                "threshold_inr": section.get("threshold"),
                "applicability": {
                    "individual": section.get("rate_individual"),
                    "company": section.get("rate_company")
                },
                "source": self.source_name,
                "effective_date": datetime(2024, 4, 1),  # FY start
                "notification_no": None
            })
        return results

TASK 13.3 — Backend: Tax Update Celery Task

File: backend/app/workers/tasks/tax_update_tasks.py
CREATE — THIS FILE IS STABLE AFTER CREATION:

from app.celery_app import celery_app
from app.services.tax_scrapers.gst_scraper import CBICGSTScraper
from app.services.tax_scrapers.tds_scraper import TDSRateScraper
from app.models.tax_data import TaxRate, TaxUpdateLog
from app.db.session import AsyncSessionLocal
from sqlalchemy import select, update
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tax_update_tasks.daily_tax_update")
async def daily_tax_update():
    """
    Runs daily at 6:00 AM.
    Scrapes all tax data sources and updates the database.
    Detects changes and logs them.
    """
    log = TaxUpdateLog(scrape_date=datetime.utcnow())
    changes = []

    async with AsyncSessionLocal() as db:
        try:
            scrapers = [CBICGSTScraper(), TDSRateScraper()]
            total_checked = 0
            total_changed = 0
            total_added = 0

            for scraper in scrapers:
                items = await scraper.safe_scrape()
                total_checked += len(items)

                for item in items:
                    # Find existing rate for this item
                    existing = await db.execute(
                        select(TaxRate).where(
                            TaxRate.category == item["category"],
                            TaxRate.subcategory == item["subcategory"],
                            TaxRate.description == item["description"],
                            TaxRate.is_current == True
                        )
                    )
                    existing_rate = existing.scalar_one_or_none()

                    if existing_rate is None:
                        # New rate item — add to database
                        new_rate = TaxRate(**item, is_current=True)
                        db.add(new_rate)
                        total_added += 1

                    elif existing_rate.rate != item.get("rate"):
                        # Rate CHANGED — record old, update to new
                        old_rate_value = existing_rate.rate
                        # Mark old record as superseded
                        existing_rate.is_current = False
                        # Insert new record
                        new_record = TaxRate(
                            **item,
                            is_current=True,
                            previous_rate=old_rate_value
                        )
                        db.add(new_record)
                        total_changed += 1
                        changes.append({
                            "description": item["description"],
                            "old_rate": old_rate_value,
                            "new_rate": item.get("rate"),
                            "category": item["category"]
                        })
                        logger.info(
                            f"TAX RATE CHANGED: {item['description']} "
                            f"{old_rate_value}% → {item.get('rate')}%"
                        )

            log.items_checked = total_checked
            log.items_changed = total_changed
            log.items_added = total_added
            log.changes_summary = changes
            log.status = "success"
            db.add(log)
            await db.commit()

            # If any changes detected → queue user notifications
            if changes:
                await notify_users_of_tax_changes.apply_async(
                    kwargs={"changes": changes}
                )

            logger.info(
                f"Tax update complete: {total_checked} checked, "
                f"{total_changed} changed, {total_added} added"
            )

        except Exception as e:
            log.error = str(e)
            log.status = "failed"
            db.add(log)
            await db.commit()
            logger.error(f"Tax update failed: {e}")
            raise

@celery_app.task(name="tax_update_tasks.notify_users_of_tax_changes")
async def notify_users_of_tax_changes(changes: list):
    """
    Sends in-app notifications to Finance/GST workspace users about rate changes.
    """
    async with AsyncSessionLocal() as db:
        # Find users who have used Finance or Legal workspace in last 30 days
        # (these users are most likely to care about tax changes)
        from sqlalchemy import text
        active_users = await db.execute(text(
            """SELECT DISTINCT user_id FROM chat_sessions
               WHERE workspace IN ('finance', 'legal', 'general')
               AND created_at > NOW() - INTERVAL '30 days'"""
        ))
        user_ids = [str(row[0]) for row in active_users.fetchall()]

        for user_id in user_ids:
            # Create notification (using existing notification system from Phase 14)
            notif = {
                "user_id": user_id,
                "type": "tax_update",
                "title": f"Tax Rate Update — {datetime.now().strftime('%d %b %Y')}",
                "body": f"{len(changes)} tax rate change(s) detected. "
                        f"Example: {changes[0]['description']} changed from "
                        f"{changes[0]['old_rate']}% to {changes[0]['new_rate']}%.",
                "action_url": "/finance?tab=tax-updates",
                "is_read": False
            }
            # Insert into notifications table (created in Phase 14)
            await db.execute(text(
                """INSERT INTO notifications (user_id, type, title, body, action_url)
                   VALUES (:user_id, :type, :title, :body, :action_url)""",
                notif
            ))

        await db.commit()
        logger.info(f"Tax update notifications sent to {len(user_ids)} users")

TASK 13.4 — Backend: Schedule Daily Task in Celery Beat

File: backend/app/celery_app.py
NOTE: STABLE SYSTEM — only ADD to beat_schedule, never modify existing.

ADD to celery_app.conf.beat_schedule:

  "daily-tax-update": {
      "task": "tax_update_tasks.daily_tax_update",
      "schedule": crontab(hour=6, minute=0),  # 6:00 AM daily
      # Using UTC — adjust if server is in IST (hour=0, minute=30 for 6 AM IST)
  },

Import: from celery.schedules import crontab

TASK 13.5 — Backend: Tax Knowledge Injection into LLM Queries

File: backend/app/services/tax_query_injector.py
CREATE:

"""
When a query in Finance/Legal workspace contains tax-rate-related keywords,
inject current tax rates from the database into the LLM context.
This is how the AI always knows current rates without being retrained.
"""

import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tax_data import TaxRate
from typing import Optional

# Keywords that indicate a tax rate query
TAX_RATE_KEYWORDS = [
    "gst rate", "gst%", "tax rate", "tds rate", "tds section",
    "how much gst", "what is the gst", "what gst", "gst on",
    "income tax slab", "tax slab", "what tds", "tds on",
    "hsn code", "hsn rate", "custom duty", "cess",
    "what is the rate", "current rate", "latest rate"
]

async def get_tax_context_for_query(
    query: str,
    db: AsyncSession,
    workspace: str
) -> Optional[str]:
    """
    Returns a tax context string to inject into the LLM prompt,
    or None if query doesn't seem to be tax-rate-related.
    """
    if workspace not in ("finance", "legal", "general"):
        return None

    query_lower = query.lower()
    is_tax_query = any(kw in query_lower for kw in TAX_RATE_KEYWORDS)

    if not is_tax_query:
        return None

    # Fetch relevant current rates from database
    result = await db.execute(
        select(TaxRate)
        .where(TaxRate.is_current == True)
        .order_by(TaxRate.category, TaxRate.subcategory)
        .limit(50)  # Don't flood the context
    )
    rates = result.scalars().all()

    if not rates:
        return None

    # Build context string
    lines = [
        "=== CURRENT TAX RATES (Auto-updated daily from official sources) ===",
        f"Last updated: {rates[0].updated_at.strftime('%d %b %Y') if rates else 'Unknown'}",
        ""
    ]

    gst_rates = [r for r in rates if r.category == "gst"]
    tds_rates = [r for r in rates if r.category == "tds"]

    if gst_rates:
        lines.append("GST RATES:")
        for r in gst_rates[:20]:
            rate_str = f"{r.rate}%" if r.rate is not None else "Nil/Exempt"
            lines.append(f"  • {r.description} (HSN {r.hsn_code or 'N/A'}): {rate_str}")

    if tds_rates:
        lines.append("")
        lines.append("TDS RATES (FY 2024-25):")
        for r in tds_rates[:15]:
            applicability = r.applicability or {}
            ind_rate = applicability.get('individual', r.rate)
            comp_rate = applicability.get('company', r.rate)
            thresh = f"₹{r.threshold_inr:,.0f}" if r.threshold_inr else "No threshold"
            lines.append(
                f"  • Section {r.tds_section}: {r.description} — "
                f"Individual: {ind_rate}%, Company: {comp_rate}% | Threshold: {thresh}"
            )

    lines.append("")
    lines.append("=== END TAX RATES — Use these values in your response ===")

    return "\n".join(lines)

TASK 13.6 — Backend: Inject Tax Context Into Query Stream

File: backend/app/api/v1/endpoints/query.py
EDIT — in the streaming query handler, AFTER building the main prompt:

  from app.services.tax_query_injector import get_tax_context_for_query

  # After retrieving chunks, before building LLM prompt:
  tax_context = await get_tax_context_for_query(query, db, workspace)

  # Prepend tax context to system prompt if available:
  if tax_context:
      system_prompt = tax_context + "\n\n" + system_prompt
      # The LLM now sees current tax rates AND the document chunks

TASK 13.7 — Frontend: Tax Update Notification Badge

File: frontend/src/components/NotificationCenter.tsx
EXTEND (or CREATE if not in Phase 14 yet):
  Add a "Tax Rate Changes" section in the notification panel.
  For each change: show "📊 {description}: {old_rate}% → {new_rate}%"
  with a link "Ask AI about this change →"

TASK 13.8 — Frontend: "What Changed Today?" Button in Finance Workspace

File: frontend/src/app/finance/page.tsx
ADD a "🔔 Latest Tax Updates" chip in the action bar.
Clicking it: auto-sends the question "What tax rates have changed recently?"
to the Finance workspace chat. The LLM uses the injected tax_context to answer.

─────────────────────────────────────────────────────────────────────
PHASE 13 — VERIFICATION
─────────────────────────────────────────────────────────────────────

# Run migration
alembic upgrade head

# Check scrapers
python -c "
import asyncio
from app.services.tax_scrapers.gst_scraper import CBICGSTScraper
from app.services.tax_scrapers.tds_scraper import TDSRateScraper
async def test():
    items = await CBICGSTScraper().safe_scrape()
    print(f'GST items: {len(items)}')
    items2 = await TDSRateScraper().safe_scrape()
    print(f'TDS items: {len(items2)}')
asyncio.run(test())
"

# Trigger task manually (test without waiting for 6 AM)
python -c "
from app.workers.tasks.tax_update_tasks import daily_tax_update
daily_tax_update.apply()
"

# Manual: Finance workspace → ask "What is the GST rate on laptops?"
# → Confirm response includes current rate (18%) with "Auto-updated daily" notice
# Manual: Finance workspace → "Latest Tax Updates" button → see notification

DEFINITION OF DONE — PHASE 13:
✅ tax_rates table populated with seed data on first run
✅ Celery beat runs daily_tax_update at 6:00 AM
✅ Changed rates logged in tax_update_logs with old and new values
✅ Finance/Legal workspace queries get current tax rates injected
✅ User notifications sent when rates change
✅ "What Changed Today?" works in Finance workspace
✅ Rate changes logged without any manual intervention ever

[CHECKPOINT 13 COMPLETE — Proceeding to Phase 14]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 14 — ZERO-COST UI/UX ENHANCEMENTS (ALL 11 FEATURES)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: 11 UI/UX upgrades that make DocuMindAI genuinely world-class.
Every feature below costs $0 to run and requires no new paid services.
ESTIMATED TIME: 12–15 hours | RISK: Low | DEPENDS ON: Phase 8 complete

─────────────────────────────────────────────────────────────────────
TASK 14.1 — COMMAND PALETTE (Cmd+K)
─────────────────────────────────────────────────────────────────────

File: frontend/src/components/CommandPalette.tsx
CREATE:

Design:
  Backdrop: fixed inset-0, bg rgba(0,0,0,0.4), z-50, blur-sm
  Panel: centered, max-width 560px, top 20%, var(--surface-raised),
         rounded-xl, shadow-2xl, border var(--border)

  Search input (top):
    Full width, 44px height, 16px font
    Placeholder: "Search sessions, run commands, switch workspace..."
    Left icon: 🔍 (16px)
    Right: "ESC" badge (11px, var(--surface-sunken), rounded)

  Results list (below input):
    Max height 320px, overflow-y scroll
    Each result row: 44px height, flex, gap 12px
      Left: icon (emoji or SVG, 20px)
      Center: result title (14px) + subtitle (12px var(--text-tertiary))
      Right: keyboard shortcut if applicable (12px .kbd style)
      Hover/selected: var(--surface-sunken) background
      Active item: highlighted with 2px left border var(--brand)

  Sections (with section label above group):
    SESSIONS — matching chat sessions
    COMMANDS — quick actions
    WORKSPACES — switch workspace
    DOCUMENTS — find uploaded documents

  Empty state: "No results for '{query}'" centered, 40px icon

Keyboard behavior:
  ↑ / ↓ : navigate items
  Enter  : execute selected item
  Escape : close palette
  Cmd+K (or Ctrl+K) anywhere: toggle palette

Commands included:
  "New Chat"            → creates session in current workspace
  "Upload Document"     → opens file picker
  "Switch to Legal"     → switches workspace (one per workspace)
  "Switch to Finance"   → same
  "Switch to Teacher"   → same
  "Switch to HR"        → same
  "Switch to Student"   → same
  "Switch to Research"  → same
  "Export Chat as PDF"  → triggers export
  "Toggle Dark Mode"    → toggles theme
  "Open Settings"       → navigates to /settings
  "Open Dashboard"      → navigates to /dashboard
  "Keyboard Shortcuts"  → opens keyboard shortcuts modal (Task 14.8)

Wire to: global keydown listener in layout.tsx (Cmd+K / Ctrl+K)
The palette searches sessions from existing sessions store in real-time.

─────────────────────────────────────────────────────────────────────
TASK 14.2 — INLINE CITATION HIGHLIGHTING
─────────────────────────────────────────────────────────────────────

File: frontend/src/components/CitationHighlighter.tsx
CREATE:

Purpose: Every sentence in the AI response that has a corresponding source
gets a subtle underline. Hovering shows the original source text snippet.

Design:
  Highlighted sentence: underline, underline-offset-3, decoration-style dotted,
  decoration-color var(--brand) at 40% opacity
  Cursor: help (shows tooltip is available)

  Tooltip on hover:
    max-width 300px, var(--surface-raised), shadow-lg, rounded-lg, p-3
    "📄 {filename} · Page {page}"  — 11px bold, mb-1
    Source text snippet (first 120 chars of the chunk) — 12px var(--text-secondary)
    Italicized, quoted

Implementation approach:
  The backend already returns citations with chunks.
  Add a sentence_map field to the streaming response:
    sentence_map: [{ sentence_start: int, sentence_end: int, source_index: int }]
  This maps character positions in the response to citation indices.
  Frontend uses this to wrap the right text spans in <mark> elements.

Backend changes needed:
  In query streaming: after response is complete, compute sentence_map
  using a simple sentence splitter on the full response text.
  Map each sentence to the citation that most contributed to it
  (use the chunk scores from the reranker — highest score = most contributing).
  Add as a final SSE event: { type: "sentence_map", data: [...] }

Frontend rendering:
  Use react-markdown with custom components:
  - Override the <p> renderer to parse sentences and apply citation highlighting
  - Each cited sentence becomes: <CitedSentence citation={citationData}>text</CitedSentence>
  - CitedSentence wraps in <span> with tooltip on hover

─────────────────────────────────────────────────────────────────────
TASK 14.3 — VOICE INPUT
─────────────────────────────────────────────────────────────────────

File: frontend/src/components/VoiceInput.tsx
CREATE:

Uses: Web Speech API (SpeechRecognition) — built into Chrome/Edge/Safari. $0 cost.

Design:
  Microphone button: 36px × 36px, positioned right of textarea, left of send button
  Default state: 🎤 icon, var(--text-tertiary) color
  Listening state: red pulsing circle animation, 🎤 icon turns red
    animation: pulse 1s ease-in-out infinite (scale 1.0 → 1.15 → 1.0)
  Success state: ✓ icon for 1.5 seconds (text was inserted)

Behavior:
  Click mic → starts listening (continuous: false, language: 'en-IN')
  Speech recognised → text injected into textarea (appended to existing text)
  Auto-stops after 5 seconds of silence
  On error: toast "Microphone access needed. Please allow in browser settings."

Language support:
  Default: 'en-IN' (Indian English — better for Indian accents)
  Respects user's preferred language from Settings (Phase 15 Task)

Browser support check:
  if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
    // Don't render the mic button at all — no error, no fallback
    return null
  }

ARIA: aria-label="Voice input", role="button"

─────────────────────────────────────────────────────────────────────
TASK 14.4 — RESPONSE BOOKMARKING
─────────────────────────────────────────────────────────────────────

Backend:
  File: backend/app/models/bookmark.py
  CREATE:
    class Bookmark(Base):
      __tablename__ = "bookmarks"
      id = Column(UUID, primary_key=True, default=uuid4)
      user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
      session_id = Column(UUID, ForeignKey("chat_sessions.id"), nullable=False)
      message_id = Column(String, nullable=False)  # frontend message ID
      message_content = Column(Text, nullable=False)  # stored snapshot
      citations = Column(JSON, nullable=True)
      tags = Column(ARRAY(String), default=[])
      workspace = Column(String, nullable=False)
      created_at = Column(DateTime, default=datetime.utcnow)

  Endpoints in: backend/app/api/v1/endpoints/bookmarks.py (CREATE)
    POST /bookmarks: { session_id, message_id, content, citations, tags }
    GET  /bookmarks: list all, filter by tag, filter by workspace
    DELETE /bookmarks/{id}: remove
    PATCH /bookmarks/{id}/tags: update tags

  Alembic migration: "add_bookmarks"

Frontend:
  File: frontend/src/components/BookmarkButton.tsx
  🔖 icon button — appears on hover on each AI message (alongside 📋 Copy)
  Filled blue when bookmarked, outline when not
  Click: toggles bookmark (POST or DELETE)

  File: frontend/src/app/bookmarks/page.tsx (CREATE)
  Page at /bookmarks:
    Left column: tag cloud (filter by tag)
    Main: list of bookmarked responses, grouped by workspace
    Each bookmark shows: workspace badge, session name, response preview, tags, date
    Click: opens that session at that message

  Sidebar: add "🔖 Saved" item in bottom section (alongside Settings, Account)

─────────────────────────────────────────────────────────────────────
TASK 14.5 — SESSION TAGGING & FOLDER ORGANISATION
─────────────────────────────────────────────────────────────────────

Backend:
  Add to chat_sessions table:
    tags = Column(ARRAY(String), default=[])
    is_pinned = Column(Boolean, default=False)  # already exists — verify

  Endpoints:
    PATCH /chats/{id}/tags: { "tags": ["Client: Tata", "Q1 Review"] }
    GET /chats?tag=Client%3ATata: filter sessions by tag

Frontend:
  In sidebar ⋯ menu per session: ADD "🏷 Add Tags" option
  Opens a small popover: type tag → Enter to add → chip appears
  × to remove a tag
  Tags stored and synced to backend immediately

  Sidebar top: ADD a small "Filter" button (funnel icon) next to search
  Click: shows tag cloud of all user's tags
  Selecting a tag: filters sidebar to show only matching sessions

─────────────────────────────────────────────────────────────────────
TASK 14.6 — MULTI-DOCUMENT COMPARISON TOGGLE
─────────────────────────────────────────────────────────────────────

File: frontend/src/components/ComparisonToggle.tsx
CREATE — a small toggle in the document chips bar:

  Design:
    "⇄ Compare Mode" toggle, right side of document chips bar
    Only visible when 2+ documents are uploaded
    When ON: amber border around the entire document chips bar
    When ON: amber badge appears in input bar "⇄ Comparing N documents"

Backend behavior (query.py):
  Add comparison_mode: bool to query request body
  When comparison_mode=True:
    Modify system prompt to include:
    "You are comparing multiple documents. For each point, specify which
     document supports it: use [Doc A] and [Doc B] notation. Format your
     response as a comparison — use a table when 3+ dimensions are compared."
    Retrieve top_k from ALL documents (not just top-scoring one)

─────────────────────────────────────────────────────────────────────
TASK 14.7 — NOTIFICATION CENTER
─────────────────────────────────────────────────────────────────────

Backend:
  File: backend/app/models/notification.py
  CREATE:
    class Notification(Base):
      __tablename__ = "notifications"
      id = Column(UUID, primary_key=True, default=uuid4)
      user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
      type = Column(String)  # "tax_update"|"product_update"|"system"
      title = Column(String, nullable=False)
      body = Column(Text)
      action_url = Column(String, nullable=True)
      is_read = Column(Boolean, default=False)
      created_at = Column(DateTime, default=datetime.utcnow)

  Endpoints:
    GET  /notifications: list unread + last 20 read
    PATCH /notifications/{id}/read: mark read
    PATCH /notifications/read-all: mark all read

Frontend:
  Add 🔔 bell icon in navbar (between trial pill and avatar)
  Badge: red dot with count when unread > 0
  Click: slides notification panel from right (280px)
  Panel shows notifications grouped: "TODAY" / "EARLIER"
  Each notification:
    Icon (📊 for tax updates, 🎉 for product updates, ⚠ for system)
    Title (13px semibold) + body (12px text-secondary)
    Time ago (11px text-tertiary)
    "→" action link if action_url exists
  "Mark all read" button at top of panel

─────────────────────────────────────────────────────────────────────
TASK 14.8 — KEYBOARD SHORTCUTS MAP
─────────────────────────────────────────────────────────────────────

File: frontend/src/components/KeyboardShortcutsModal.tsx
CREATE:

  Trigger: pressing "?" when textarea is NOT focused
  Design: centered modal, max-width 480px, 2-column grid of shortcuts

  Shortcuts listed:
    NAVIGATION:     Cmd+K = Command palette
    NAVIGATION:     Cmd+B = Toggle sidebar
    NAVIGATION:     Cmd+D = Toggle dark/light mode
    CHAT:           Cmd+Enter = Send message
    CHAT:           Shift+Enter = New line in message
    CHAT:           Cmd+/ = Open template library
    TEACHER:        Cmd+Shift+T = Extract tables
    EXPORT:         Cmd+Shift+E = Export chat
    SEARCH:         Cmd+F = Focus session search (in sidebar)
    GENERAL:        ? = Show this shortcuts panel
    GENERAL:        Esc = Close any open panel

  Each row: [Cmd] [K] notation (styled as .kbd elements)
  Footer: "Shortcuts work everywhere except when typing in a text field"

─────────────────────────────────────────────────────────────────────
TASK 14.9 — AUTOSAVE INDICATOR
─────────────────────────────────────────────────────────────────────

File: frontend/src/components/AutosaveIndicator.tsx
CREATE:

  Location: navbar center-right (subtle, 12px text)
  States:
    Idle: invisible (no text)
    Saving: "Saving..." with a subtle spinner (12px)
    Saved: "All changes saved ✓" (var(--text-tertiary)) — fades out after 3s
    Error: "⚠ Save failed" (amber) — stays visible until next save succeeds

  Triggers:
    Show "Saving..." when: any API mutation starts (new message, session rename, etc.)
    Show "Saved ✓" when: mutation completes successfully
    Show "⚠ Save failed" when: mutation fails

─────────────────────────────────────────────────────────────────────
TASK 14.10 — AI THINKING TRANSPARENCY
─────────────────────────────────────────────────────────────────────

Backend (query.py):
  Add stage events to the SSE stream BEFORE response starts:
    Stage 1 (immediate): { "type": "thinking_stage", "stage": "searching",
                           "detail": "Searching your documents..." }
    Stage 2 (after retrieval): { "type": "thinking_stage", "stage": "reranking",
                           "detail": f"Reviewing {N} relevant passages..." }
    Stage 3 (after reranking): { "type": "thinking_stage", "stage": "generating",
                           "detail": "Generating response..." }

Frontend (message renderer):
  While streaming and content is empty:
    Show small text below "DocuMindAI is thinking...":
    "🔍 Searching 3 relevant passages from contract.pdf"
    Then: "📊 Reviewing results..."
    Then: "✍ Generating response..."
    Each stage fades in/out smoothly (opacity transition 200ms)
    When actual content starts streaming: all stage text disappears

─────────────────────────────────────────────────────────────────────
TASK 14.11 — PROGRESSIVE WEB APP (PWA — INSTALLABLE)
─────────────────────────────────────────────────────────────────────

File: frontend/public/manifest.json
CREATE:
{
  "name": "DocuMindAI",
  "short_name": "DocuMindAI",
  "description": "Trusted document intelligence with grounded answers",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0C0C0E",
  "theme_color": "#0C0C0E",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png",
      "purpose": "maskable" }
  ]
}

File: frontend/src/app/layout.tsx
ADD in <head>:
  <link rel="manifest" href="/manifest.json" />
  <meta name="theme-color" content="#0C0C0E" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="DocuMindAI" />

File: frontend/public/sw.js (service worker)
CREATE — caches app shell for offline:
  CACHE_NAME = "documindai-v1"
  Cache on install: ["/", "/login", "/_next/static/**"]
  Network-first strategy for API calls (never serve stale API responses)
  Cache-first for static assets (_next/static, fonts, icons)

File: frontend/src/app/layout.tsx
ADD service worker registration:
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(r => console.log('SW registered'))
        .catch(e => console.log('SW registration failed:', e))
    }
  }, [])

─────────────────────────────────────────────────────────────────────
PHASE 14 — VERIFICATION
─────────────────────────────────────────────────────────────────────

# TypeScript check
npx tsc --noEmit

# Manual: Press Cmd+K anywhere → command palette opens
# Manual: Type "Legal" → workspace switch option appears → Enter → switches
# Manual: Ask a question → see thinking stages before response
# Manual: Hover a cited sentence → tooltip shows source text
# Manual: Click mic → speak → text appears in textarea
# Manual: Bookmark a response → appears at /bookmarks
# Manual: Add tag to session → filter sidebar by that tag
# Manual: Upload 2 docs → comparison toggle appears → enable → ask comparison Q
# Manual: Press ? → keyboard shortcuts modal
# Manual: On mobile Chrome → install prompt appears → install → opens as app
# Manual: Notification bell → shows tax update notifications (if Phase 13 done)

DEFINITION OF DONE — PHASE 14:
✅ Command palette opens with Cmd+K, finds sessions, runs commands
✅ Inline citation underlines appear + tooltip shows source text
✅ Voice input works in Chrome/Edge/Safari
✅ Bookmarks save, appear at /bookmarks, searchable by tag
✅ Session tags filter sidebar correctly
✅ Comparison mode modifies LLM prompt correctly
✅ Notification center shows tax updates + product updates
✅ Keyboard shortcuts modal complete
✅ Autosave indicator updates on mutations
✅ Thinking stages appear before streaming content
✅ PWA installable on Chrome mobile (Add to Home Screen)

[CHECKPOINT 14 COMPLETE — Proceeding to Phase 15]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 15 — STRUCTURED RESPONSE ENFORCEMENT + REGIONAL LANGUAGE SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: This phase answers the question "Is my AI response structured?"
DocuMindAI uses Gemini 2.5 Flash with prompts — it is NOT fine-tuned.
This means response quality = prompt quality. This phase enforces strict
response structure through prompt engineering and schema validation.
Also adds Hindi/Tamil/Telugu/regional language support at zero cost.
ESTIMATED TIME: 4–5 hours | RISK: Low | DEPENDS ON: Phase 14 complete

─────────────────────────────────────────────────────────────────────
UNDERSTANDING: WHY RESPONSES MAY BE UNSTRUCTURED
─────────────────────────────────────────────────────────────────────

The AI (Gemini 2.5 Flash) responds exactly as it's prompted.
Currently, workspace system prompts ask for markdown — but there are
no explicit structure rules. This can cause:
  - Inconsistent header usage (## sometimes, bold sometimes)
  - Bullet lists when a table would be better
  - Answers of inconsistent length (too short for complex Q, too long for simple Q)
  - Numbers mixed with prose (should be tables in Finance)
  - Missing summary in long answers

This phase adds response structure schemas per workspace.

─────────────────────────────────────────────────────────────────────
TASK 15.1 — Backend: Workspace Response Schemas
─────────────────────────────────────────────────────────────────────

File: backend/app/services/response_schemas.py
CREATE:

"""
Response structure schemas injected into system prompts.
These are plain-language instructions that enforce consistent output.
They do NOT change what the AI answers — only HOW it structures the answer.
"""

RESPONSE_SCHEMAS = {

    "general": """
RESPONSE FORMAT RULES (follow exactly):
1. Start with a 1-2 sentence direct answer.
2. Use ### headers for each major point (if 3+ points exist).
3. Use bullet lists (- item) for enumerations of 3+ items.
4. Use **bold** for key terms, numbers, and dates.
5. End with a 1-sentence summary if response > 200 words.
6. Maximum response length: match the complexity of the question.
   Simple Q → 2-4 sentences. Complex Q → up to 500 words.
""",

    "legal": """
RESPONSE FORMAT RULES (follow exactly):
1. Start with a Risk Summary sentence: "Overall risk: [Low/Medium/High/Critical]"
2. For clause analysis: use this exact structure per clause:
   **Clause Type:** [name]
   **Risk Level:** [Low / Medium / High / Critical]
   **Finding:** [what the clause says, in plain English]
   **Concern:** [why this is risky, if applicable]
   **Recommendation:** [what to do]
   **Source:** [filename, page N]
3. For list of issues: numbered list with **bold** issue name.
4. Never paraphrase legal language — quote the exact clause text when relevant.
5. Always end with: "⚠ Verify all findings with a qualified legal professional."
6. Use tables (| col | col |) when comparing multiple clauses or documents.
""",

    "finance": """
RESPONSE FORMAT RULES (follow exactly):
1. All monetary values: use Indian format (₹X,XX,XXX or ₹X crore/lakh).
2. All ratios: show formula, then value. Example:
   **Current Ratio** = Current Assets / Current Liabilities = ₹X,XXX / ₹X,XXX = **2.4x**
3. For extraction: use a table with columns: | Line Item | Value | Page |
4. For comparisons: use a table with years as columns.
5. Trend indicators: use ↑ (improving) ↓ (declining) → (stable) per metric.
6. Never compute ratios yourself — state extracted values only if Python calculation
   is unavailable for this query. Mark computed values with [Computed].
7. End every financial analysis with: "⚠ Verify all figures with source documents."
8. For multi-value responses: use numbered sections with ### headers.
""",

    "teacher": """
RESPONSE FORMAT RULES (follow exactly):
1. For question generation: number all questions (1., 2., 3.)
2. MCQs: show question, then options labeled (A) (B) (C) (D)
3. Short answer questions: show [X marks] after each question
4. Long answer questions: show [X marks] and hint in italics
5. Use --- dividers between sections (A, B, C)
6. Answer key format: Q1: (B) | Q2: See page 12 | Q3: [sample answer]
7. For explanation responses: use ### headers for each concept
8. Use > blockquote for direct textbook quotes with page reference
""",

    "hr": """
RESPONSE FORMAT RULES (follow exactly):
1. Candidate rankings: use table format:
   | Rank | Name | Score | Top Skills | Experience |
2. Individual analysis: use fixed sections:
   **Match Score:** X/100
   **Strengths:** bullet list
   **Gaps:** bullet list  
   **Recommendation:** [Shortlist / Review / Reject]
3. Comparison: use side-by-side table format
4. Never include candidate PII (phone/email) in responses
5. Always cite which resume section the finding comes from
""",

    "student": """
RESPONSE FORMAT RULES (follow exactly):
1. For explanations: use the ELI5 approach — explain like teaching a smart 16-year-old
2. Always end explanations with: **In one line:** [summary in 10-15 words]
3. For formulas: display on their own line with = alignment
4. For step-by-step solutions: number every step
5. For concept comparisons: use | Concept A | Concept B | comparison table
6. Quiz questions: always show (A) (B) (C) (D) with exactly one correct answer
7. Do NOT give the quiz answer until asked
8. Use emojis sparingly for memory hooks: 🧠 for key concepts, 📌 for important facts
""",

    "research": """
RESPONSE FORMAT RULES (follow exactly):
1. For synthesis: use ### Paper title or [Author, Year] headers per paper
2. Evidence strength: label each finding: [Strong evidence] / [Moderate] / [Limited]
3. For gaps: numbered list with **Gap:** prefix
4. For conflicts: show both sides — "Paper A finds X. Contradicting this, Paper B finds Y."
5. Citations format: (Author, Year, p.X) inline
6. For summaries: use Abstract / Methods / Findings / Limitations sections
7. Always state the number of papers reviewed: "Based on analysis of N papers:"
"""
}

def get_response_schema(workspace: str) -> str:
    return RESPONSE_SCHEMAS.get(workspace, RESPONSE_SCHEMAS["general"])

TASK 15.2 — Backend: Inject Response Schema Into System Prompt

File: backend/app/api/v1/endpoints/query.py
EDIT — ADD schema injection into system prompt building:

  from app.services.response_schemas import get_response_schema

  # In prompt builder, append response schema to system_prompt:
  schema = get_response_schema(workspace)
  system_prompt = f"{system_prompt}\n\n{schema}"

TASK 15.3 — Backend: Language Detection and Response Language

File: backend/app/services/language_detector.py
CREATE:

import re
from typing import Literal

# Character range patterns for Indian languages
LANGUAGE_PATTERNS = {
    "hindi":    re.compile(r'[\u0900-\u097F]'),   # Devanagari
    "tamil":    re.compile(r'[\u0B80-\u0BFF]'),   # Tamil
    "telugu":   re.compile(r'[\u0C00-\u0C7F]'),   # Telugu
    "kannada":  re.compile(r'[\u0C80-\u0CFF]'),   # Kannada
    "malayalam":re.compile(r'[\u0D00-\u0D7F]'),   # Malayalam
    "gujarati": re.compile(r'[\u0A80-\u0AFF]'),   # Gujarati
    "marathi":  re.compile(r'[\u0900-\u097F]'),   # Same as Hindi (Devanagari)
    "bengali":  re.compile(r'[\u0980-\u09FF]'),   # Bengali
    "english":  re.compile(r'[a-zA-Z]'),
}

def detect_query_language(query: str) -> str:
    """
    Detects the primary language of the query.
    Returns ISO language name for injection into LLM prompt.
    """
    char_counts = {lang: len(pattern.findall(query))
                   for lang, pattern in LANGUAGE_PATTERNS.items()}
    # Find the dominant language
    dominant = max(char_counts, key=char_counts.get)
    if char_counts[dominant] == 0:
        return "english"
    return dominant

def get_language_instruction(language: str) -> str:
    """Returns the instruction to add to system prompt for language."""
    if language == "english":
        return ""  # No instruction needed
    return (
        f"\n\nIMPORTANT: The user's question is in {language.capitalize()}. "
        f"Respond in {language.capitalize()} language throughout your entire response. "
        f"Technical terms and document citations can remain in English."
    )

TASK 15.4 — Backend: Inject Language Instruction Into Query

File: backend/app/api/v1/endpoints/query.py
EDIT:

  from app.services.language_detector import detect_query_language, get_language_instruction

  # After getting the query text:
  query_language = detect_query_language(query_text)
  lang_instruction = get_language_instruction(query_language)
  if lang_instruction:
      system_prompt = system_prompt + lang_instruction

TASK 15.5 — Frontend: Language Preference in Settings

File: frontend/src/app/settings/page.tsx
ADD to General section:

  "Response Language" field:
    Label: "AI Response Language"
    Description: "DocuMindAI auto-detects your question language. Set a preference to always respond in your language."
    Dropdown: Auto-detect (default) | English | Hindi (हिंदी) | Tamil (தமிழ்) |
              Telugu (తెలుగు) | Kannada (ಕನ್ನಡ) | Malayalam (മലയാളം) |
              Gujarati (ગુજરાતી) | Marathi (मराठी) | Bengali (বাংলা)

  Store in user profile (PATCH /users/me with preferred_language field)
  When preferred_language is set: always use that language (override auto-detect)

─────────────────────────────────────────────────────────────────────
PHASE 15 — VERIFICATION
─────────────────────────────────────────────────────────────────────

# Python check
python -c "from app.services.response_schemas import get_response_schema; print(get_response_schema('legal')[:50])"
python -c "from app.services.language_detector import detect_query_language; print(detect_query_language('यह क्या है?'))"

# Manual: Finance workspace → ask "What is the current ratio?" → verify table format
# Manual: Legal workspace → ask "What are the risks?" → verify Risk Level prefix structure
# Manual: HR workspace → ask "Rank the candidates" → verify table format
# Manual: Type a question in Hindi → verify Hindi response
# Manual: Settings → set language to Tamil → ask English Q → verify Tamil response
# TypeScript: npx tsc --noEmit

DEFINITION OF DONE — PHASE 15:
✅ Every workspace response follows its defined structure schema
✅ Finance responses always use tables for values, ratios
✅ Legal responses always have Risk Level and Recommendation
✅ Hindi/Tamil/Telugu queries get responses in the same language
✅ Language preference persists in settings
✅ Existing functionality unchanged — only response STRUCTURE improved

[CHECKPOINT 15 COMPLETE]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL ENHANCED — VERIFICATION & OUTPUT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run ALL of the following after Phase 15 is complete:

BACKEND CHECKS:
  python -c "from app.main import app; print('Backend OK')"
  alembic upgrade head
  alembic check  (verify no pending migrations)
  python -m pytest tests/ -q --tb=short  (if tests exist)

CELERY CHECKS:
  celery -A app.celery_app inspect registered | grep tax_update
  celery -A app.celery_app inspect registered | grep daily_tax

FRONTEND CHECKS:
  npx tsc --noEmit
  npx next build  (should complete with zero errors)

MANUAL INTEGRATION TEST CHECKLIST:
  ✓ Register new account → trial pill shows "0/10" → all workspaces accessible
  ✓ Run 10 queries → on 10th: response shown, then upgrade modal appears
  ✓ 11th query attempt: immediately shows upgrade modal (no API call made)
  ✓ Teacher: upload PDF with table → Extract Tables → copy HTML → paste Google Docs
  ✓ Teacher: handwritten notes photo → Extract Tables → OCR detects table
  ✓ Add 2nd API key to .env → restart → /health shows total:2 available:2
  ✓ Tax update task runs manually → check tax_rates table populated
  ✓ Finance: ask "What is GST on laptops?" → response says 18% with "auto-updated" note
  ✓ Cmd+K opens command palette → type "Legal" → workspace switches
  ✓ Ask question → see thinking stages (Searching... → Reviewing... → Generating...)
  ✓ Hover over cited sentence → tooltip shows source text from document
  ✓ Click mic → speak → text appears in textarea
  ✓ Bookmark a response → go to /bookmarks → see it there
  ✓ Add tag "Test" to session → filter sidebar → only tagged session shows
  ✓ 2 docs uploaded → comparison toggle → enable → ask comparative Q → table format
  ✓ Press ? → keyboard shortcuts modal opens
  ✓ PWA: mobile Chrome → install prompt → add to home screen → opens as app
  ✓ Hindi question → Hindi response
  ✓ Finance question → response uses tables, ↑↓ indicators, ₹ formatting

FINAL OUTPUT REPORT:

| Feature                        | Status | Notes |
|--------------------------------|--------|-------|
| Free Trial (10 queries full)   | ✅/❌  |       |
| Teacher Table Extraction       | ✅/❌  |       |
| Dynamic API Key Rotation       | ✅/❌  |       |
| GST Auto-Update (daily)        | ✅/❌  |       |
| Command Palette (Cmd+K)        | ✅/❌  |       |
| Inline Citation Highlighting   | ✅/❌  |       |
| Voice Input                    | ✅/❌  |       |
| Response Bookmarking           | ✅/❌  |       |
| Session Tagging                | ✅/❌  |       |
| Comparison Toggle              | ✅/❌  |       |
| Notification Center            | ✅/❌  |       |
| Keyboard Shortcuts Map         | ✅/❌  |       |
| Autosave Indicator             | ✅/❌  |       |
| AI Thinking Transparency       | ✅/❌  |       |
| PWA (Installable)              | ✅/❌  |       |
| Structured Response Schemas    | ✅/❌  |       |
| Regional Language Support      | ✅/❌  |       |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT NOTES FOR CLAUDE PRO WHEN EXECUTING THIS PART
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Phases 10-15 depend on Phases 0-9 being COMPLETE. Do not start Phase 10
   unless the existing system is working (backend starts, frontend builds).

2. Phase 12 (API key rotation) touches llm_service.py which is a STABLE SYSTEM.
   Make ONLY the targeted change described. Do not rewrite the file.

3. Phase 13 (Tax automation) uses Celery beat. Verify celery_app.py has
   beat_schedule already configured before adding to it.

4. Phase 14 Task 14.2 (inline citations) requires the backend to emit
   a "sentence_map" SSE event. This is a NEW SSE event type — the frontend
   must handle it alongside existing event types without breaking the stream.

5. The TRIAL_QUERY_LIMIT constant in Phase 10 is intentionally a single number
   in a single file. To change trial length (e.g., 15 queries instead of 10):
   change ONE number in trial_enforcement.py. That's it.

6. For Phase 15 response schemas: these are PROMPT ADDITIONS, not code logic.
   If a schema produces bad results for a specific workspace, edit the schema
   string in response_schemas.py — no other file needs changing.

7. GST scraper (Phase 13) is best-effort. If CBIC changes their website structure,
   the seeded database still works. The scraper just won't detect new notifications
   until updated. This is by design — the system degrades gracefully.

8. After Phase 12, the GEMINI_API_KEY (legacy single key) still works. No need
   to rename it if only one key is used. But renaming to GEMINI_API_KEY_1 is
   recommended for consistency.

9. Phase 14.11 (PWA) requires icon files: icon-192.png and icon-512.png in
   frontend/public/. Generate these from the DocuMindAI logomark before building.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEW .ENV ADDITIONS (add these to backend/.env.local)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# === PHASE 10 — TRIAL ===
TRIAL_QUERY_LIMIT=10  # (optional override — hardcoded in trial_enforcement.py)

# === PHASE 12 — API KEY ROTATION ===
# Rename your existing GEMINI_API_KEY to GEMINI_API_KEY_1
GEMINI_API_KEY_1=your_existing_gemini_key
# GEMINI_API_KEY_2=your_second_key  # Uncomment when you add more keys

# === PHASE 13 — TAX AUTOMATION ===
CBIC_NOTIFICATION_URL=https://www.cbic.gov.in/htdocs-cbec/gst/index.htm
IT_INDIA_CIRCULARS_URL=https://www.incometaxindia.gov.in/Pages/communications/circulars.aspx
# These URLs are in .env so they can be updated if the source website changes
# without touching any code.

NEW REQUIREMENTS.TXT ADDITIONS (backend/requirements.txt):
# Phase 11
docling>=2.0.0  # already in stack — verify version
paddlepaddle>=2.5.0  # already in stack — verify installed
paddleocr>=2.7.0  # already in stack — verify installed

# Phase 13
httpx>=0.24.0  # for async HTTP in scrapers (likely already installed)
langdetect>=1.0.9  # for language detection in Phase 15

# Phase 14
# No new packages — all features use existing stack or browser APIs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF MERGED PART 7 — ENHANCEMENT PHASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
