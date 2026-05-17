━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7 — OBSERVABILITY + RESILIENCE + RATE LIMITING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Production-ready reliability. Rate limits on all sensitive endpoints.
Circuit breaker for LLM. Structured JSON logging. Comprehensive health
checks. Token cost tracking. Settings and Usage Dashboard pages.
ESTIMATED TIME: 3–4 hours | RISK: Medium | DEPENDS ON: Phase 6 complete

─────────────────────────────────────────────────────────────────────
PHASE 7 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

SETTINGS PAGE (frontend/src/app/settings/page.tsx):
Two-column layout: left nav (200px) | right content (flex-1)
Left nav: vertical sections list (36px items, .sidebar-item style):
General | Appearance | Notifications | Privacy | Integrations | Danger Zone

GENERAL SECTION:
Heading: "General" — .text-heading-2 (Instrument Serif 24px)
Full Name: text .input + inline Save button
Email: read-only display (DM Sans 14px) + "Change Email" link
Password: "Change Password" link → modal with current + new + confirm fields
Default Workspace: dropdown (same 7 workspaces, same styling as navbar dropdown)
Language: dropdown (English selected; others "Coming soon" disabled)

APPEARANCE SECTION:
Heading: "Appearance" — .text-heading-2
Theme selection: 3 cards in a row:
Light | Dark | System
Each: .card, icon + label, 32px icon, 14px DM Sans below
Currently selected: .card-active (border-brand + shadow-brand)
Click: calls setTheme() from useTheme hook
Font size: segmented control \[Small | Normal | Large]
Adjusts --text-base CSS variable offset (Small: -0.05rem, Normal: 0, Large: +0.1rem)

DANGER ZONE SECTION:
Red border card (.card with border: 1px solid var(--error-border)):
"Danger Zone" heading in var(--error-text) color
"Delete All Chat History" — .btn .btn-danger → confirmation modal
Modal: "This will delete all X sessions. This cannot be undone."
Requires typing "DELETE" to confirm
"Delete Account" — .btn .btn-danger → modal asking for email confirmation
Modal: "Enter your email address to confirm account deletion."

USAGE DASHBOARD PAGE (frontend/src/app/dashboard/page.tsx):
Heading: "Usage Dashboard" — .text-heading-1

4 stat cards at top row (.card style):
Documents Uploaded this month | Queries this month
AI Tokens used | Estimated Cost ($)
Each: large number in Instrument Serif 36px, label below in .text-body-secondary

Charts section (using recharts):
Line chart: daily query volume, last 30 days
x-axis: dates, y-axis: query count
Line: brand color, dot on each point
Bar chart: queries by workspace, last 30 days
Stacked bar per day, each workspace a different color (use ws accent colors)

Per-workspace breakdown table:
Columns: Workspace | Sessions | Queries | Documents | Tokens | Est. Cost
One row per workspace with totals
Table: full-width, alternating row colors (surface-base / surface-sunken)
Total row: bold, border-top: 1px var(--border-default)

CIRCUIT BREAKER FRONTEND BANNER:
When query endpoint returns 503 (circuit breaker open):
Full-width amber banner ABOVE the input bar (not blocking messages):
"⚠ AI service is momentarily unavailable. Retrying in 30s..."
Auto-dismisses after 30 seconds or when next request succeeds

─────────────────────────────────────────────────────────────────────
PHASE 7 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 7.1 — Rate Limiting on Sensitive Endpoints
File: backend/app/main.py
Apply rate limits using slowapi or fastapi-limiter:
POST /auth/login             → "5/minute"
POST /auth/register          → "3/hour"
POST /auth/refresh           → "10/minute"
POST /query/stream           → "30/minute"
POST /documents/upload/local → "20/minute"
POST /exams/*/generate*      → "10/minute"
POST /hr/jobs/\*/analyze      → "5/minute"

On rate limit exceeded → 429 response:
{ "error": "Rate limit exceeded", "retry\_after": "60 seconds" }

Frontend: on 429 response → toast.error("Too many requests. Wait 60 seconds.")

TASK 7.2 — Circuit Breaker for LLM Calls
File: backend/app/services/llm\_service.py
ADD CircuitBreaker class (do not replace existing code — add alongside):
import time

class CircuitBreaker:
CLOSED    = "closed"
OPEN      = "open"
HALF\_OPEN = "half\_open"

&#x20;   def \_\_init\_\_(self, redis\_client, name: str,
                 failure\_threshold: int = 5, recovery\_timeout: int = 30):
      self.redis = redis\_client
      self.key = f"circuit:{name}"
      self.failure\_threshold = failure\_threshold
      self.recovery\_timeout = recovery\_timeout

    async def is\_open(self) -> bool:
      try:
        state = await self.redis.hgetall(self.key)
        if not state: return False
        if state.get(b"state", b"").decode() == self.OPEN:
          opened\_at = float(state.get(b"opened\_at", b"0").decode())
          if time.time() - opened\_at > self.recovery\_timeout:
            await self.redis.hset(self.key, "state", self.HALF\_OPEN)
            return False
          return True
      except Exception:
        return False  # Redis failure → never block LLM
      return False

    async def record\_failure(self):
      try:
        failures = await self.redis.hincrby(self.key, "failures", 1)
        if failures >= self.failure\_threshold:
          await self.redis.hset(self.key, mapping={
            "state": self.OPEN, "opened\_at": str(time.time())})
      except Exception:
        pass  # Redis failure → silently ignore

    async def record\_success(self):
      try:
        await self.redis.delete(self.key)
      except Exception:
        pass


Wrap ALL LLM calls with circuit breaker:
if await circuit\_breaker.is\_open():
raise HTTPException(503, detail=
"AI service temporarily unavailable. Please try again in 30 seconds.")
try:
result = await llm\_call(...)
await circuit\_breaker.record\_success()
return result
except Exception as e:
await circuit\_breaker.record\_failure()
raise

Frontend: on 503 from query endpoint → show amber banner per design spec.

TASK 7.3 — Structured JSON Logging
Create: backend/app/core/logging\_config.py
import logging, json, time
from contextvars import ContextVar

correlation\_id\_var: ContextVar\[str] = ContextVar("correlation\_id", default="")

class JSONFormatter(logging.Formatter):
def format(self, record: logging.LogRecord) -> str:
log\_data = {
"timestamp":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
"level":          record.levelname,
"message":        record.getMessage(),
"correlation\_id": correlation\_id\_var.get(""),
"module":         record.module,
"function":       record.funcName,
}
return json.dumps(log\_data)

def setup\_logging():
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
root = logging.getLogger()
root.handlers = \[handler]
root.setLevel(logging.INFO)

Call setup\_logging() in backend/app/main.py on startup (lifespan or startup event).

SECURITY RULE — ABSOLUTE:
NEVER log: passwords, full JWT tokens, API keys, email addresses,
phone numbers, file contents, or personal identifying information.

TASK 7.4 — Token Usage and Cost Tracking
Create Alembic migration: query\_logs table
Columns: id (UUID PK), user\_id (UUID FK users), workspace (str),
session\_id (UUID FK nullable), input\_tokens (int),
output\_tokens (int), total\_tokens (int), cost\_usd (float),
model (str), duration\_ms (int), created\_at (datetime)

File: backend/app/api/v1/endpoints/query.py
After each LLM response, log to query\_logs:
if hasattr(response, "usage\_metadata"):
usage = response.usage\_metadata
# Gemini 2.5 Flash pricing (2025):
# Input: $0.075 per 1M tokens = $0.000075 per token
# Output: $0.300 per 1M tokens = $0.000300 per token
cost = (usage.prompt\_token\_count \* 0.000075 +
usage.candidates\_token\_count \* 0.000300) / 1000
async with AsyncSessionLocal() as db:
db.add(QueryLog(
user\_id=current\_user.id, workspace=workspace\_type,
input\_tokens=usage.prompt\_token\_count,
output\_tokens=usage.candidates\_token\_count,
total\_tokens=usage.total\_token\_count,
cost\_usd=cost, model="gemini-2.5-flash",
duration\_ms=duration\_ms
))
await db.commit()

Add API: GET /api/v1/usage/summary → aggregates query\_logs per workspace:
Returns: { "by\_workspace": \[{workspace, sessions, queries, documents, tokens, cost\_usd}],
"totals": {queries, tokens, cost\_usd}, "period": "30 days" }

TASK 7.5 — Comprehensive Health Check
File: backend/app/api/v1/endpoints/health.py
Update GET /health to return detailed status (with 2s timeouts on each check):
{
"status": "healthy" | "degraded" | "unhealthy",
"version": "1.0.0",
"uptime\_seconds": int,
"services": {
"database":        "connected" | "error: ...",
"redis":           "connected" | "error: ...",
"celery":          "workers\_online: N" | "no\_workers",
"llm\_circuit":     "closed" | "open" | "half\_open",
"embedding\_model": "loaded:BAAI/bge-m3" | "not\_loaded",
"storage":         "accessible" | "error: ..."
},
"timestamp": "ISO datetime"
}
HTTP 200 if all critical services (database + redis) healthy.
HTTP 503 if any critical service is down.
Check each service with try/except and asyncio.wait\_for(timeout=2.0).

TASK 7.6 — DB Connection Pool Tuning
File: backend/app/db/session.py
Update create\_async\_engine() call:
engine = create\_async\_engine(
settings.DATABASE\_URL,
echo=settings.DB\_ECHO,
pool\_size=10,
max\_overflow=20,
pool\_pre\_ping=True,
pool\_recycle=3600,
)

TASK 7.7 — Document-Workspace Binding in DB
File: backend/app/api/v1/endpoints/documents.py
In GET /documents: add optional query param workspace\_id: Optional\[str] = Query(None)
If workspace\_id provided: filter documents.workspace\_id == workspace\_id
Else: return all documents for current user

File: frontend/src/lib/api.ts
Update listDocuments(workspaceId: string):
return apiFetch(`/documents?workspace\_id=${encodeURIComponent(workspaceId)}`)

File: frontend/src/components/WorkspaceUI.tsx
Remove any localStorage-based document filtering.
DB is the ONLY source of truth for workspace-document binding.

TASK 7.8 — Implement Settings and Usage Dashboard Pages
Create: frontend/src/app/settings/page.tsx
Per design spec above.
Wire theme selection cards to useTheme hook (setTheme() on card click).
Wire "Delete All Chat History" → calls DELETE /chats/all (add this endpoint).
Wire "Delete Account" → calls DELETE /auth/account with email confirmation.

Create: frontend/src/app/dashboard/page.tsx
Per design spec above.
Fetches GET /api/v1/usage/summary for data.
Uses recharts: LineChart for daily volume, BarChart for workspace breakdown.
Show loading skeletons while data loads.

─────────────────────────────────────────────────────────────────────
PHASE 7 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
cd backend \&\& python -c "
from app.core.logging\_config import setup\_logging
setup\_logging()
import logging
logging.info('test log')
print('Logging OK')
"
cd backend \&\& python -c "from app.db.session import engine; print('DB pool OK')"
cd backend \&\& python -c "from app.main import app; print('App OK')"
cd backend \&\& python -c "from app.api.v1.endpoints.health import router; print('Health OK')"
cd frontend \&\& npx tsc --noEmit \&\& echo "TypeScript OK"
cd frontend \&\& npm run build \&\& echo "Build OK"

════════════════════════════════════════════════════════════════════════

PHASE 7 ADDENDUM — ENTERPRISE COMPLIANCE AND PRIVACY

════════════════════════════════════════════════════════════════════════



TASK 7-E1 — Global Audit Log

─────────────────────────────────────────────────────────────────────

File: backend/app/models/audit\_log.py

CREATE:

&#x20; class AuditLog(Base):

&#x20;   \_\_tablename\_\_ = "audit\_logs"

&#x20;   id           = Column(UUID(as\_uuid=True), primary\_key=True, default=uuid4)

&#x20;   user\_id      = Column(UUID(as\_uuid=True), ForeignKey("users.id"), nullable=False)

&#x20;   event\_type   = Column(String, nullable=False)

&#x20;   resource\_type = Column(String)    # "document" | "session" | "export" | "share"

&#x20;   resource\_id  = Column(UUID(as\_uuid=True), nullable=True)

&#x20;   ip\_address   = Column(String)

&#x20;   user\_agent   = Column(String)

&#x20;   event\_detail = Column(JSONB, default={})   # event-specific metadata

&#x20;   timestamp    = Column(DateTime, default=datetime.utcnow, index=True)



&#x20;   # IMMUTABLE — no update, no delete

&#x20;   \_\_table\_args\_\_ = (

&#x20;     # PostgreSQL: use triggers to prevent UPDATE/DELETE in production

&#x20;   )



EVENT\_TYPES = \[

&#x20; "user.login", "user.logout", "user.password\_changed",

&#x20; "document.uploaded", "document.deleted", "document.viewed",

&#x20; "session.created", "session.deleted",

&#x20; "query.run", "query.stop",

&#x20; "export.pdf", "export.docx", "export.markdown",

&#x20; "share.created", "share.accessed", "share.deactivated",

&#x20; "legal.risk\_report\_generated", "legal.audit\_trail\_accessed",

&#x20; "finance.ratios\_computed", "finance.audit\_trail\_exported",

&#x20; "settings.account\_deleted", "settings.data\_deletion\_requested"

]



File: backend/app/core/audit.py

CREATE:

&#x20; from contextvars import ContextVar

&#x20; from app.models.audit\_log import AuditLog



&#x20; audit\_context: ContextVar\[dict] = ContextVar("audit\_context", default={})



&#x20; async def log\_event(

&#x20;   db: AsyncSession,

&#x20;   user\_id: UUID,

&#x20;   event\_type: str,

&#x20;   resource\_type: str = None,

&#x20;   resource\_id: UUID = None,

&#x20;   event\_detail: dict = None,

&#x20;   request=None

&#x20; ):

&#x20;   """Log an immutable audit event. Never raises — audit failures must not

&#x20;      break the main request."""

&#x20;   try:

&#x20;     entry = AuditLog(

&#x20;       user\_id=user\_id,

&#x20;       event\_type=event\_type,

&#x20;       resource\_type=resource\_type,

&#x20;       resource\_id=resource\_id,

&#x20;       ip\_address=request.client.host if request else None,

&#x20;       user\_agent=request.headers.get("user-agent") if request else None,

&#x20;       event\_detail=event\_detail or {}

&#x20;     )

&#x20;     db.add(entry)

&#x20;     await db.commit()

&#x20;   except Exception as e:

&#x20;     # Log the failure to structured logging, never re-raise

&#x20;     logger.error(f"Audit log write failed: {e}")



INTEGRATE audit logging in:

&#x20; auth.py: login, logout, password\_changed events

&#x20; documents.py: uploaded, deleted events

&#x20; query.py: query.run event (include workspace, token\_count, duration\_ms)

&#x20; chats.py: share.created, share.accessed events

&#x20; export.py: export.pdf, export.docx events

&#x20; legal.py: legal.risk\_report\_generated event

&#x20; finance.py: finance.ratios\_computed event



Add endpoint: GET /api/v1/audit-log (admin users or user's own log):

&#x20; Returns last 500 events for current user, ordered by timestamp desc.

&#x20; Query params: event\_type (filter), resource\_type (filter),

&#x20;               from\_date, to\_date (ISO date strings)

&#x20; Response: { "events": \[...], "total": int, "page": int }



Frontend — Audit Log in Settings:

&#x20; Add "Audit Log" section to Settings left nav (between Privacy and Danger Zone)

&#x20; Table view: Timestamp | Event | Resource | Details

&#x20; Filter by event type dropdown

&#x20; "Export Audit Log CSV" button: downloads current user's full log

&#x20; Note below table: "This log cannot be modified or deleted."



TASK 7-E2 — Document Data Retention Policy

─────────────────────────────────────────────────────────────────────

File: backend/app/models/user.py

ADD to User model:

&#x20; data\_retention\_days = Column(Integer, default=90)

&#x20;   # How long documents are stored: 30 | 60 | 90 | 365 | 0 (never auto-delete)



File: backend/app/tasks/cleanup\_tasks.py

CREATE (as a Celery periodic task, runs daily at 2 AM):

&#x20; @celery.task

&#x20; def enforce\_data\_retention():

&#x20;   """Delete documents older than user's retention policy."""

&#x20;   async with AsyncSessionLocal() as db:

&#x20;     users = await db.execute(

&#x20;       select(User).where(User.data\_retention\_days > 0)

&#x20;     )

&#x20;     for user in users.scalars():

&#x20;       cutoff = datetime.utcnow() - timedelta(days=user.data\_retention\_days)

&#x20;       old\_docs = await db.execute(

&#x20;         select(Document).where(

&#x20;           Document.user\_id == user.id,

&#x20;           Document.created\_at < cutoff,

&#x20;           Document.status == "READY"

&#x20;         )

&#x20;       )

&#x20;       for doc in old\_docs.scalars():

&#x20;         # Delete from storage

&#x20;         await delete\_from\_storage(doc.storage\_path)

&#x20;         # Delete embeddings from vector store

&#x20;         await delete\_embeddings(doc.id)

&#x20;         # Delete DB record

&#x20;         await db.delete(doc)

&#x20;         # Audit log

&#x20;         await log\_event(db, user.id, "document.auto\_deleted",

&#x20;           resource\_type="document", resource\_id=doc.id,

&#x20;           event\_detail={"reason": "retention\_policy", "days": user.data\_retention\_days})

&#x20;     await db.commit()



Frontend — Data Retention Setting:

&#x20; In Settings → Privacy section:

&#x20;   "Document Retention Policy" heading

&#x20;   Description: "Documents are automatically deleted after this period."

&#x20;   Dropdown: \[30 days] \[60 days] \[90 days] \[1 year] \[Never auto-delete]

&#x20;   Current selection shown, saves on change (PATCH /auth/settings)

&#x20;   Warning on values < 60 days: "⚠ Short retention may delete documents

&#x20;     you still need. Sessions referencing deleted documents will lose context."



TASK 7-E3 — Privacy Mode (Document Isolation)

─────────────────────────────────────────────────────────────────────

File: backend/app/core/config.py

ADD:

&#x20; PRIVACY\_MODE: bool = Field(default=False, env="PRIVACY\_MODE")

&#x20;   # When True: document chunks are NOT cached in Redis

&#x20;   # Document text is NOT stored in any external service logs

&#x20;   # Query logs omit the query text (only tokens and workspace logged)



File: backend/app/api/v1/endpoints/query.py

When PRIVACY\_MODE is True:

&#x20; - Skip Redis retrieval cache entirely (still use vector store)

&#x20; - In query\_logs: set query\_text = "\[PRIVACY MODE]" instead of actual query

&#x20; - In structured logging: omit any chunk text from log entries



This setting is for enterprise deployments with strict data residency requirements.

Document it in the Final Output Report under "Privacy Configuration."



TASK 7-E4 — API Key Generation for Enterprise Users

─────────────────────────────────────────────────────────────────────

File: backend/app/models/api\_key.py

CREATE:

&#x20; class APIKey(Base):

&#x20;   \_\_tablename\_\_ = "api\_keys"

&#x20;   id          = Column(UUID(as\_uuid=True), primary\_key=True, default=uuid4)

&#x20;   user\_id     = Column(UUID(as\_uuid=True), ForeignKey("users.id"), nullable=False)

&#x20;   key\_hash    = Column(String, nullable=False, unique=True)  # bcrypt of raw key

&#x20;   key\_prefix  = Column(String, nullable=False)   # first 8 chars, shown in UI

&#x20;   name        = Column(String, nullable=False)   # user-given label

&#x20;   permissions = Column(JSONB, default=\["query", "documents"])  # scoped

&#x20;   last\_used\_at = Column(DateTime, nullable=True)

&#x20;   created\_at  = Column(DateTime, default=datetime.utcnow)

&#x20;   expires\_at  = Column(DateTime, nullable=True)  # None = never expires

&#x20;   is\_active   = Column(Boolean, default=True)



File: backend/app/api/v1/endpoints/api\_keys.py

CREATE:

&#x20; POST /api-keys:     Generate a new API key (raw key returned ONCE only)

&#x20; GET  /api-keys:     List user's API keys (prefix + name only, never raw key)

&#x20; DELETE /api-keys/{id}: Revoke a key



Raw key format: "dmk\_" prefix + 48 random bytes as hex = "dmk\_\[48hex chars]"

Store: hash the key with bcrypt, store hash. Return raw key once on creation.

Authentication: API key passed as Bearer token in Authorization header.

&#x20; Middleware checks if Authorization starts with "dmk\_" → API key auth path.



Frontend — Settings → Integrations section:

&#x20; "API Keys" sub-section heading

&#x20; "Your API keys enable programmatic access to DocuMindAI."

&#x20; Table: Name | Key Prefix | Created | Last Used | Expires | Actions

&#x20; "Create New Key" button → modal:

&#x20;   Name input (required), Expiry: \[Never | 30 days | 90 days | 1 year]

&#x20;   After creation: show raw key with "Copy" button + red warning:

&#x20;     "This key is shown only once. Copy and store it securely now."

&#x20;   × close button disabled until key is copied or user checks

&#x20;     "I have saved this key" checkbox.

&#x20; Revoke button per key → confirmation modal.

&#x20; Max 5 API keys per user.

# Manual: hit /auth/login 6 times rapidly → 429 response on 6th

# Manual: GET /health → JSON with all service statuses

# Manual: Settings page renders with all 3 sections

# Manual: Dashboard page renders stat cards and charts

DEFINITION OF DONE — PHASE 7:
✅ Rate limits applied to all sensitive endpoints (tested with rapid requests)
✅ Circuit breaker wraps ALL LLM calls (not just some)
✅ All backend logs output as JSON (not plain text)
✅ Token usage logged to query\_logs table after each query
✅ GET /health returns accurate status for all services
✅ DB connection pool tuned (pool\_size=10, max\_overflow=20)
✅ Document-workspace binding reads from DB, not localStorage
✅ Settings page functional with theme selection
✅ Usage dashboard shows real query counts from query\_logs

\[CHECKPOINT 7 COMPLETE — Proceeding to Phase 8]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 8 — EXPORT + SHARE + RESPONSIVE DESIGN + ACCESSIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Share sessions via JWT links. Export to PDF/DOCX/Markdown.
Full mobile and tablet responsive layout. WCAG 2.1 AA accessibility.
ESTIMATED TIME: 4–5 hours | RISK: Low-Medium | DEPENDS ON: Phase 7 complete

─────────────────────────────────────────────────────────────────────
PHASE 8 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

SHARE MODAL (appears when Share icon clicked in chat header):
.modal-backdrop + .modal (centered, 440px wide)
Header: "Share this session" — Instrument Serif 20px; × close button

Link section:
"Anyone with this link can view this session (read-only)" — 13px text-secondary
Link input: full-width, var(--surface-sunken), disabled text, shows share URL
\[Copy Link] button: .btn .btn-primary, inline right of input, 36px height
On copy: button text changes to "Copied! ✓" for 2 seconds

Expiry info: "Link expires in 7 days" — 12px text-tertiary

Access settings:
"Link is active" toggle (green when on, gray when off)
Toggle disables/enables the share link

Footer: \[Close] .btn .btn-ghost + \[Generate New Link] .btn .btn-secondary

EXPORT DROPDOWN (clicking export icon ↓ in chat header area):
.dropdown panel opens below export icon
Options (.dropdown-item each):
📄 Export as PDF    → POST /export/{session\_id}/pdf → triggers file download
📝 Export as DOCX   → POST /export/{session\_id}/docx → triggers file download
#  Export as Markdown → client-side, instant, no API call
📋 Copy All Text    → client-side, copies all messages as plain text
🔗 Share Link       → opens Share Modal
Loading state per option: spinner replaces icon while export is in progress

PUBLIC SHARED SESSION PAGE:
Minimal layout (no sidebar, no full navbar features)
Top bar: \[DocuMindAI LogoMark + Logo] + \["Try DocuMindAI — Free →" .btn .btn-primary .btn-sm, right]
Badge below logo: "Read-only · Shared session" — .badge .badge-neutral
Amber info pill above messages: "Can't interact — this is a read-only view"
Messages: same rendering as normal chat but without input bar
"Export PDF" button: .btn .btn-secondary .btn-sm, top right of messages area
Expired token: centered card "🔒 This link has expired" + "Try DocuMindAI" CTA button
<meta name="robots" content="noindex, nofollow"> (prevent search indexing)

MOBILE RESPONSIVE LAYOUT:
≤768px (mobile):
Sidebar: overlay only (position fixed, z-index 60, slides from left)
Navbar: same structure; workspace dropdown label shows icon only on ≤480px
Chat input: full width; Send button icon-only (no "Send" text label)
Document bar: smaller chips (max-width 140px), text 11px
Messages: full width, no side padding restriction
Preview panel: full-viewport overlay width on mobile (not 380px side panel)
Settings: single column (left nav becomes horizontal top tabs)

768px–1024px (tablet):
Sidebar: collapsible, visible toggle in navbar
Chat content max-width: 640px
Preview panel: 320px (narrower)
Document bar: same as desktop

ACCESSIBILITY (WCAG 2.1 AA):
All interactive elements keyboard reachable (Tab order: Navbar → Sidebar → Main → Input)
Focus indicators: 2px solid var(--brand), offset 2px — via :focus-visible in tokens.css
ARIA labels on ALL icon-only buttons:
aria-label="Toggle sidebar" | aria-label="Send message"
aria-label="Stop generating" | aria-label="Regenerate response"
aria-label="Copy response" | aria-label="Toggle dark mode" etc.
aria-live="polite" on AI message container (streaming updates announced to screen readers)
role="log" on chat messages list
role="navigation" on sidebar element
role="main" on main content area
aria-describedby on all form inputs that have error messages
All decorative icons: aria-hidden="true"
All meaningful images: descriptive alt text
Touch targets: min 44×44px on all mobile interactive elements
Color contrast: ≥4.5:1 for all text (do not rely on color alone to convey information)

─────────────────────────────────────────────────────────────────────
PHASE 8 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 8.1 — JWT-Based Shareable Links Backend
Create: backend/app/models/shared\_session.py
class SharedSession(Base):
**tablename** = "shared\_sessions"
id          = Column(UUID(as\_uuid=True), primary\_key=True, default=uuid4)
token       = Column(String, unique=True, nullable=False)
session\_id  = Column(UUID(as\_uuid=True), ForeignKey("chat\_sessions.id"),
nullable=False)
created\_by  = Column(UUID(as\_uuid=True), ForeignKey("users.id"), nullable=False)
created\_at  = Column(DateTime, default=datetime.utcnow)
expires\_at  = Column(DateTime, nullable=False)
view\_count  = Column(Integer, default=0)
is\_active   = Column(Boolean, default=True)

Run Alembic migration: "add\_shared\_sessions"

File: backend/app/api/v1/endpoints/chats.py
Add POST /chats/{id}/share:
Generate JWT: { "sub": str(session\_id), "type": "shared", "exp": now + 7 days }
Store in shared\_sessions table
Return:
{ "share\_url": f"{settings.FRONTEND\_URL}/shared/{token}",
"expires\_in": "7 days", "token": token }

Add GET /shared/{token} (NO authentication required):
Verify JWT signature and expiry
If invalid/expired: 404 { "error": "This link has expired or is invalid." }
If is\_active = False: 404 { "error": "This link has been deactivated." }
Increment view\_count atomically
Return: session messages + citations (read-only format)
OMIT from response: user\_id, internal IDs, private metadata, PII

Add PATCH /chats/{id}/share/toggle: toggles is\_active on the shared session

TASK 8.2 — Public Shared Session Page
Create: frontend/src/app/shared/\[token]/page.tsx
Fetch from GET /api/v1/shared/{token} (no auth cookies needed)
If 404/expired: show centered expired card per design spec
If valid: render read-only chat view per design spec
"Export as PDF" button: calls export endpoint with share token
<meta name="robots" content="noindex, nofollow" /> in page <head>

TASK 8.3 — Share Modal Component
Create: frontend/src/components/ShareModal.tsx
Per design spec above.
On open: calls POST /chats/{id}/share to get share URL.
Copy button: copies URL, changes label to "Copied! ✓" for 2 seconds.
Toggle: calls PATCH /chats/{id}/share/toggle.
"Generate New Link" button: calls POST /chats/{id}/share again (creates new token).
Wire to Share (↑) button in chat header and in sidebar context menu.

TASK 8.4 — Export Dropdown Component
Create: frontend/src/components/ExportDropdown.tsx
Per design spec above.
Wire to export icon in chat header area.

Markdown export (client-side, no backend call):
const md = messages.map(msg => {
const role = msg.role === "user" ? "**You**" : "**DocuMindAI**"
return `${role}:\\n\\n${msg.content}\\n\\n---\\n`
}).join("\\n")
const blob = new Blob(\[md], { type: "text/markdown" })
const url = URL.createObjectURL(blob)
const a = document.createElement("a")
a.href = url
a.download = `${chatTitle || "documind-chat"}.md`
a.click()
URL.revokeObjectURL(url)

PDF/DOCX export: calls existing export endpoints; triggers file download via Blob.
"Copy All Text": joins all messages as plain text, copies to clipboard.
Show spinner replacing icon while PDF/DOCX export is in progress.

TASK 8.5 — Export Quality Improvements
File: backend/app/services/export\_engine.py

PDF improvements (using fpdf2):
Session title as H1 at top of document
User messages: light background box (#F5F5F5 light / #1C1C1F dark), max-width 72ch
AI responses: full text, max-width 72ch for readability
Citations as numbered footnotes: ¹ Source: filename.pdf, p.3
Footer per page: "Generated by DocuMindAI | {timestamp} | grounded answers"
Page numbers: "Page N of Total" (right-aligned in footer)
Workspace badge in header (e.g., "LEGAL WORKSPACE")
Legal/Finance: print disclaimer text on first page (before messages)

DOCX improvements (using python-docx):
Heading 1 style for session title
"You:" label in Bold + brand blue color (RGB 59, 130, 246)
"DocuMindAI:" in Normal style
Citations as superscript footnote references with ¹²³ numbering
Horizontal rule (paragraph with border) between each message pair
Workspace badge in document header (Header section)
Legal/Finance disclaimer on first page before messages

TASK 8.6 — Responsive CSS
File: frontend/src/styles/components.css (ADD responsive section at end)

@media (max-width: 768px) {
.sidebar { width: 0; position: fixed; z-index: 60;
transition: transform 300ms var(--ease-decel);
transform: translateX(-100%); }
.sidebar.mobile-open { transform: translateX(0); width: 260px; }
.chat-area { padding: 0 var(--space-4); }
.preview-panel { position: fixed; inset: 0; width: 100%; z-index: 50; }
.settings-layout { flex-direction: column; }
.settings-nav { flex-direction: row; overflow-x: auto;
border-right: none; border-bottom: 1px solid var(--border-subtle); }
}
@media (min-width: 768px) and (max-width: 1024px) {
.preview-panel { width: 320px; }
.chat-content-max { max-width: 640px; }
}

File: frontend/src/components/LayoutWrapper.tsx
Add isMobile state: const \[isMobile, setIsMobile] = useState(false)
useEffect: window.innerWidth ≤ 768 → setIsMobile(true)
window.addEventListener("resize", handler); return cleanup
On mobile: sidebar always renders as overlay; backdrop renders when open

TASK 8.7 — Accessibility Pass
Apply to ALL interactive components (WorkspaceUI.tsx, LayoutWrapper.tsx,
Sidebar.tsx, WorkspaceDropdown.tsx, all modal/dropdown components):

1. aria-label on every icon-only button (no visible text label)
2. aria-live="polite" on AI message container (for streaming announcements)
3. role="log" on chat messages list (scrolling log semantics)
4. role="navigation" on sidebar element
5. role="main" on main content area
6. aria-describedby linking form inputs to their error message elements
7. aria-hidden="true" on all decorative icons and emoji icons
8. aria-expanded={isOpen} on all toggle buttons (sidebar, dropdowns)
9. Verify Tab order: Navbar → Sidebar → Main Content → Input Bar
10. Touch targets: verify all buttons ≥ 44×44px on mobile

─────────────────────────────────────────────────────────────────────
PHASE 8 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
cd backend \&\& python -c "
from app.models.shared\_session import SharedSession
print('SharedSession model OK')
"
cd frontend \&\& npx tsc --noEmit \&\& echo "TypeScript OK"
cd frontend \&\& npm run build \&\& echo "Build OK"

# Manual: share a session → link works when opened in incognito (no auth)

# Manual: expired/invalid token → shows expired page

# Manual: export PDF → file downloads with citations and workspace header

# Manual: export Markdown → downloads .md file instantly (no API call)

# Manual: mobile (375px viewport) → sidebar is overlay with backdrop

# Manual: Tab through interface → every button reachable, focus ring visible

# Manual: screen reader check → aria-live region announces streaming text

DEFINITION OF DONE — PHASE 8:
✅ Share link works in incognito browser (no auth needed, read-only)
✅ Expired links show friendly expired page with CTA
✅ PDF export contains session title, citations, workspace header, disclaimer
✅ DOCX export has proper academic-style formatting
✅ Markdown export is client-side instant (no API call)
✅ Mobile layout correct on 375px viewport
✅ All icon-only buttons have aria-label
✅ Tab order is logical (Navbar → Sidebar → Main → Input)
✅ Focus rings visible on all interactive elements
✅ aria-live region announces streaming AI text to screen readers

\[CHECKPOINT 8 COMPLETE — Proceeding to Final Phase]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL PHASE — PRODUCTION READINESS CHECKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Final sweep before deploying to Railway (backend) + Vercel (frontend).
Security audit. Environment validation. Build verification.
Stable systems untouched check. ML tools check.
ESTIMATED TIME: 1–2 hours | RISK: Low | DEPENDS ON: All phases complete

Run ALL these checks. Fix any failures before deploying.

1. Full backend import check:
cd backend \&\& python -c "
from app.main import app
routes = \[r.path for r in app.routes]
print(f'Total routes: {len(routes)}')
print('All routes imported OK ✓')
"
2. Alembic migration sync (both must show the same revision ID):
cd backend \&\& alembic current
cd backend \&\& alembic heads
3. Frontend full build (zero errors — warnings are acceptable but review them):
cd frontend \&\& npm run build
4. Security checks:

   # Confirm bcrypt replaced SHA256

   grep -r "sha256" backend/app/core/security.py

   # Expected: EMPTY output (no SHA256 in security.py)

   # Confirm no real API keys in tracked config

   cat backend/.env.local | grep "API\_KEY"

   # Expected: all values should be placeholder strings like "your\_key\_here"

   cat backend/.env.local | grep -i "password"

   # Expected: only placeholder values

   # Confirm .gitignore protects secrets

   cat backend/.gitignore | grep ".env"

   # Expected: .env and .env.local both present in gitignore

5. Stable systems untouched verification:
git diff --name-only HEAD | grep -E   
"retrieval\_service|grounding\_service|ocr\_orchestrator|  
chunking\_service|document\_tasks|celery\_app"

   # Expected: EMPTY — none of these stable files should appear in diff

6. ML tools verification:
cd backend \&\& python -c "
import pymupdf4llm
from sentence\_transformers import CrossEncoder, SentenceTransformer
ce = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
print('CrossEncoder OK ✓')
st = SentenceTransformer('BAAI/bge-m3')
dim = st.get\_sentence\_embedding\_dimension()
assert dim == 1024, f'Expected 1024 dims, got {dim}'
print(f'bge-m3 OK ✓ ({dim} dims)')
print('All ML tools OK ✓')
"
7. Design system verification:
test -f frontend/src/styles/tokens.css     \&\& echo "tokens.css OK"
test -f frontend/src/styles/typography.css \&\& echo "typography.css OK"
test -f frontend/src/styles/motion.css     \&\& echo "motion.css OK"
test -f frontend/src/styles/components.css \&\& echo "components.css OK"
test -f frontend/src/components/Logo.tsx   \&\& echo "Logo.tsx OK"
test -f frontend/src/hooks/useTheme.ts     \&\& echo "useTheme.ts OK"
grep "Instrument\_Serif" frontend/src/app/layout.tsx \&\& echo "Fonts wired OK"
8. Full changed-files report (review before committing):
git diff --name-only HEAD
git status

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL OUTPUT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   After all phases complete, output this summary table:

|Phase|Status|Files Modified|Files Created|Issues Found|
|-|-|-|-|-|
|0|✓/✗|N|N|list|
|1|✓/✗|N|N|list|
|2|✓/✗|N|N|list|
|2.5|✓/✗|N|N|list|
|3|✓/✗|N|N|list|
|4|✓/✗|N|N|list|
|5|✓/✗|N|N|list|
|6-T|✓/✗|N|N|list|
|6-H|✓/✗|N|N|list|
|6-S|✓/✗|N|N|list|
|6-F|✓/✗|N|N|list|
|6-L|✓/✗|N|N|list|
|6-R|✓/✗|N|N|list|
|7|✓/✗|N|N|list|
|8|✓/✗|N|N|list|
|Final|✓/✗|N|N|list|

Then output:
OVERALL STATUS: COMPLETE / PARTIAL / BLOCKED

NEW TOOLS ADDED:
pymupdf4llm       ← native PDF extraction
BAAI/bge-m3       ← multilingual embeddings (1024-dim)
CrossEncoder      ← ms-marco reranker
passlib\[bcrypt]   ← secure password hashing
qdrant-client     ← vector store client (ready for migration)

NEW DESIGN FILES ADDED:
frontend/src/styles/tokens.css       ← design token system
frontend/src/styles/typography.css   ← type scale + semantic classes
frontend/src/styles/motion.css       ← animation + transition system
frontend/src/styles/components.css   ← component visual system
frontend/src/components/Logo.tsx     ← brand identity component
frontend/src/hooks/useTheme.ts       ← dark/light/system theme

NEW BACKEND FILES ADDED:
backend/app/services/pdf\_extractor.py     ← smart extraction router
backend/app/services/extraction\_router.py ← workspace-aware routing
backend/app/core/logging\_config.py        ← JSON structured logging
backend/app/models/shared\_session.py      ← shareable link model
backend/app/utils/pii\_redactor.py         ← PII protection utility
backend/scripts/seed\_dev.py               ← dev user seed script

NEW FRONTEND FILES ADDED:
frontend/src/components/ErrorBoundary.tsx
frontend/src/components/SessionExpiredOverlay.tsx
frontend/src/hooks/useSessionExpiry.ts
frontend/src/components/WorkspaceDropdown.tsx
frontend/src/components/SkeletonLoader.tsx
frontend/src/components/DocumentPreviewPanel.tsx
frontend/src/components/OnboardingTooltip.tsx
frontend/src/components/OnboardingProgress.tsx
frontend/src/components/PomodoroTimer.tsx
frontend/src/components/ShareModal.tsx
frontend/src/components/ExportDropdown.tsx
frontend/src/hooks/useKeyboardShortcuts.ts
frontend/src/hooks/useOnboarding.ts
frontend/src/app/shared/\[token]/page.tsx
frontend/src/app/settings/page.tsx
frontend/src/app/dashboard/page.tsx
frontend/src/app/register/page.tsx
frontend/src/app/forgot-password/page.tsx
frontend/src/app/not-found.tsx

ESTIMATED PRODUCTION READINESS: X%

REMAINING ISSUES: \[list any \[NEW BUG FOUND] or \[BONUS FIX] items not yet resolved]

RECOMMENDED NEXT STEPS:
1.  Manual end-to-end test: upload PDF → ask question → verify citation
points to correct page in preview panel
2.  Verify bge-m3 embedding quality vs previous model (compare retrieval)
3.  Stress test HR workspace with 50+ resumes simultaneously
4.  Test dark/light/system theme on all 7 workspaces
5.  Verify Instrument Serif + DM Sans render on Windows Chrome (cross-platform)
6.  Check motion animations on low-power Android device
7.  Test onboarding flow with fresh localStorage (incognito)
8.  Run Lighthouse audit (target: Performance >85, Accessibility >95)
9.  Deploy backend to Railway:
Set ENVIRONMENT=production
Set all env vars from backend/.env
Update CORS\_ORIGINS to Vercel URL
10. Deploy frontend to Vercel:
Set NEXT\_PUBLIC\_API\_URL to Railway production URL
11. Monitor /health endpoint continuously for first 24 hours in production
12. Verify circuit breaker status in /health after first 100 queries
════════════════════════════════════════════════════════════════════════

FINAL PHASE ADDENDUM — PRODUCTION READINESS ADDITIONAL CHECKS

════════════════════════════════════════════════════════════════════════



9\. Audit log verification:

&#x20;  cd backend \&\& python -c "

&#x20;  from app.models.audit\_log import AuditLog

&#x20;  from app.models.api\_key import APIKey

&#x20;  print('Audit models OK')

&#x20;  "



10\. Privacy mode test:

&#x20;   PRIVACY\_MODE=true python -c "

&#x20;   from app.core.config import settings

&#x20;   assert settings.PRIVACY\_MODE == True

&#x20;   print('Privacy mode config OK')

&#x20;   "



11\. Data retention task verification:

&#x20;   cd backend \&\& python -c "

&#x20;   from app.tasks.cleanup\_tasks import enforce\_data\_retention

&#x20;   print('Retention task OK')

&#x20;   "



12\. Indian number normalization verification:

&#x20;   cd backend \&\& python -c "

&#x20;   from app.services.financial\_table\_extractor import normalize\_indian\_number

&#x20;   assert normalize\_indian\_number('₹45.5 crore') == 455000000.0, 'Crore failed'

&#x20;   assert normalize\_indian\_number('12 lakh') == 1200000.0, 'Lakh failed'

&#x20;   assert normalize\_indian\_number('1,23,456') == 123456.0, 'Indian format failed'

&#x20;   print('Indian number normalization OK ✓')

&#x20;   "



13\. Legal audit trail immutability check (in production only):

&#x20;   # Verify PostgreSQL trigger prevents UPDATE/DELETE on audit\_logs

&#x20;   # Run via psql:

&#x20;   psql $DATABASE\_URL -c "

&#x20;   UPDATE audit\_logs SET event\_type = 'modified' WHERE id = (

&#x20;     SELECT id FROM audit\_logs LIMIT 1

&#x20;   );

&#x20;   "

&#x20;   # Expected: ERROR: permission denied (trigger blocks update)



14\. BibTeX export format check:

&#x20;   cd backend \&\& python -c "

&#x20;   from app.api.v1.endpoints.research import format\_bibtex

&#x20;   metadata = {'author': 'Smith, J.', 'title': 'Test', 'journal': 'Nature',

&#x20;               'year': '2024', 'volume': '10', 'issue': '2',

&#x20;               'pages': '1-10', 'doi': '10.1234/test'}

&#x20;   result = format\_bibtex(metadata, 1)

&#x20;   assert result.startswith('@article{')

&#x20;   assert 'Smith, J.' in result

&#x20;   print('BibTeX format OK ✓')

&#x20;   "



ADDITIONAL ITEMS FOR FINAL OUTPUT REPORT — add these rows to the phase table:

&#x20; | 6-F Addendum  | ✓/✗ | N | N | Extended ratios, table extraction, multi-period |

&#x20; | 6-L Addendum  | ✓/✗ | N | N | Confidence scoring, escalation, comparison       |

&#x20; | 6-X Addendum  | ✓/✗ | N | N | BibTeX, health score, templates, audit log       |

&#x20; | 7-E Addendum  | ✓/✗ | N | N | Global audit, retention, privacy mode, API keys  |

&#x20; | 2.5-X Addendum| ✓/✗ | N | N | Citation text span highlighting                  |



NEW FILES ADDED (update Final Output Report):

&#x20; backend/app/services/financial\_table\_extractor.py

&#x20; backend/app/services/document\_health.py

&#x20; backend/app/core/audit.py

&#x20; backend/app/models/audit\_log.py

&#x20; backend/app/models/api\_key.py

&#x20; backend/app/tasks/cleanup\_tasks.py

&#x20; frontend/src/components/QueryTemplateModal.tsx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF UNIFIED MASTER PROMPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE EXECUTION ORDER (for reference):
Phase 0 → Phase 1 → Phase 2 → Phase 2.5 → Phase 3 → Phase 4
→ Phase 5 → Phase 6-T → Phase 6-H → Phase 6-S → Phase 6-F
→ Phase 6-L → Phase 6-R → Phase 7 → Phase 8 → Final Checks

EXECUTION DISCIPLINE:
Execute each phase fully before moving to the next.
Run verification checkpoint at the end of every phase.
Fix ALL failures before proceeding.
Never skip a phase. Never run two phases simultaneously.
Log every file changed: \[MODIFIED] | \[CREATED] | \[SKIPPED] | \[BONUS FIX]

