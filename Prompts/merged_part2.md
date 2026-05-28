━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — CORE LAYOUT ARCHITECTURE + NAVIGATION UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Implement the approved 4-layer layout. Workspaces in navbar dropdown
only. Sidebar shows sessions only. Center area changes per workspace.
This is the structural backbone of the entire app.
ESTIMATED TIME: 4–6 hours | RISK: Medium | DEPENDS ON: Phase 1 complete

SCAN FIRST:
frontend/src/components/LayoutWrapper.tsx  ✓/✗/⚠
frontend/src/components/Sidebar.tsx        ✓/✗/⚠
frontend/src/components/WorkspaceUI.tsx    ✓/✗/⚠
frontend/src/app/layout.tsx                ✓/✗/⚠
frontend/src/app/page.tsx                  ✓/✗/⚠

─────────────────────────────────────────────────────────────────────
PHASE 2 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

NAVBAR (52px tall, fixed top, full width):
Background: var(--surface-base) with backdrop-filter: blur(12px)
Border-bottom: 1px var(--border-subtle)
z-index: 50 (always above everything)
Layout: CSS grid 3 columns: \[auto] \[1fr] \[auto]
.navbar CSS class

LEFT ZONE (auto width):
Logo (clickable → "/"):
<LogoMark size={24} /> + <Logo size="sm" /> wrapped in <Link href="/">
Total width \~120px, height 36px touch target
Hover: opacity 0.8, transition 100ms
Gap: 12px
Sidebar toggle button (≡ icon):
36×36px, border-radius 8px, ghost style (.btn-icon .btn-ghost)
On click: toggles sidebar open/closed (width 260px ↔ 0px)
Tooltip: "Toggle sidebar (Cmd+B)"
Icon: ≡ when sidebar open, → when sidebar closed
Keyboard: Cmd+B triggers this

CENTER ZONE (fills remaining space, content absolutely centered):
WorkspaceDropdown component (see Task 2.1)
Never reflows with other navbar content

RIGHT ZONE (auto width, items in a row with 8px gap):
Share button: ↑ icon, .btn-icon .btn-ghost, 36×36px
On click: copies current page URL to clipboard
+ toast.success("Link copied!")
Tooltip: "Share current session"
Dark/Light toggle: sun/moon icon, .btn-icon .btn-ghost, 36×36px
On click: cycle dark → light → system → dark
Icon: ☀ (in dark mode) or ☾ (in light mode) or 💻 (system)
Tooltip updates per state
Keyboard: Cmd+D
Profile avatar:
Circle 32px, shows user initials (first+last initial)
in brand blue background, white text
On click: opens profile dropdown (see below)
If user has avatar URL: shows image instead of initials

PROFILE DROPDOWN (appears below avatar, right-aligned):
Background: var(--surface-overlay)
Border: 1px var(--border-default), border-radius 12px
Box-shadow: var(--shadow-xl), min-width: 220px, padding: 8px
Opens with .dropdown-enter animation (scale-in 200ms ease-bounce)
Closes on Escape or click outside

&#x20;   Top section (non-clickable, padding 12px 8px):
      User's full name — DM Sans 14px weight 600, text-primary
      User's email — DM Sans 12px, text-secondary
      User's workspace badge — small pill with current workspace name
    Divider (1px var(--border-subtle))
    Menu items (.dropdown-item, each 36px tall):
      ⚙  Settings → /settings
      📊 Usage Dashboard → /dashboard
      💳 Billing → /billing
    Divider
      🚪 Log Out — text-red-500 on hover, calls logout endpoint


WORKSPACE DROPDOWN (center navbar):
Trigger button (shows current workspace):
Background: var(--surface-sunken)
Border: 1px var(--border-default), border-radius 8px
Padding: 8px 12px, height: 36px
Content: \[workspace icon 16px] \[workspace name DM Sans 14px weight 500] \[▼ chevron 12px]
Hover: border var(--border-strong), background var(--surface-hover)
Focus: box-shadow var(--shadow-brand)
Active/open state: border var(--brand)
Transition: 100ms ease-out

Dropdown panel (opens downward):
Background: var(--surface-overlay)
Border: 1px var(--border-default), border-radius 12px
Box-shadow: var(--shadow-xl), min-width: 280px, padding: 8px
Opens with .dropdown-enter animation (scale-in + slide-down 200ms ease-bounce)
Closes on: Escape, click outside, or workspace selection

&#x20;   Panel header (non-clickable):
      "Switch Workspace" — 11px DM Sans weight 500 uppercase letter-spacing 0.08em
      text-tertiary, padding: 8px 12px 4px

    Workspace list items (7 workspaces, each 44px tall):
      Border-radius: 8px, padding: 8px 12px
      Layout: \[icon 20px] \[name + description flex-1] \[badge if any] \[→ on hover]
      Name: DM Sans 14px weight 500, text-primary
      Description: DM Sans 12px, text-secondary, below name
      Badge: small pill (e.g., "OCR" for Teacher)
      Active workspace: background var(--brand-ghost), left border 2px var(--brand)
      Hover: background var(--surface-hover)
      Keyboard: ArrowUp/Down to navigate, Enter to select, Escape to close

    Complete workspace definitions:
      💬 General       "Chat with any document"                  route: "/"        badge: none
      📋 Teacher       "Generate question papers \& assessments"  route: "/exam"    badge: "OCR"
      👥 HR            "Resume analysis \& candidate pipeline"    route: "/hr"      badge: "Batch"
      📚 Student       "Personalized study \& exam preparation"   route: "/study"   badge: "30+ PDFs"
      🔬 Research      "Literature review \& paper synthesis"     route: "/research" badge: "Citations"
      ⚖  Legal         "Contract analysis \& risk scoring"        route: "/legal"   badge: "Risk"
      📊 CA / Finance  "Financial documents \& ratio analysis"    route: "/finance" badge: "Precision"

    Divider
    "More workspaces coming soon" — 12px text-tertiary, padding 8px 12px (non-clickable)


SIDEBAR (260px wide, collapsible to 0px):
Transition: width 350ms ease-in-out (smooth slide)
Background: var(--surface-base)
Border-right: 1px var(--border-subtle)
Overflow: hidden during collapse (clip content, no wrapping)
.sidebar CSS class; .sidebar.collapsed → width 0

TOP SECTION (fixed, never scrolls):
New Chat button:
Full width, 44px height, border-radius 10px
Background: var(--brand), color: white
Content: ✏ icon 14px + "New Chat" DM Sans 14px weight 600
Hover: brightness(1.08), 100ms
Margin: 12px on all sides
On click: creates new session for active workspace, navigates to it

&#x20;   Search field (below New Chat, 12px horizontal margin):
      Height: 36px, border-radius 8px, background: var(--surface-sunken)
      Border: 1px var(--border-default)
      Placeholder: "Search chats..." (text-disabled)
      Left icon: 🔍 12px, text-tertiary
      Clear button: ✕ appears when has value, 24px touch target
      On type: filters session list in real-time (client-side substring match)
      Keyboard: Cmd+K focuses this field


MIDDLE SECTION (scrollable, fills remaining height):
Padding: 0 8px
Session groups by date (groupChatsByDate function):
Group labels (non-clickable):
"TODAY", "YESTERDAY", "LAST 7 DAYS", "JUNE 2025"...
10px DM Sans weight 500 uppercase, letter-spacing 0.1em, text-tertiary
Padding: 12px 4px 4px
No divider line (spacing alone separates groups)

&#x20;     Session items (each 40px min-height, border-radius 8px, .sidebar-item):
        Layout: \[workspace icon 16px] \[title flex-1] \[...menu trigger 28px]
        Workspace icon: emoji 14px (shows which workspace this session belongs to)
        Title: DM Sans 13px, text-primary, truncated with ellipsis after \~26 chars
        ... trigger: appears on HOVER ONLY, 28×28px ghost button, 3 vertical dots icon
        Active session: background var(--brand-ghost), color var(--text-brand)
        Hover: background var(--surface-hover)
        Pinned sessions: ☆ pin icon after title; pinned items appear at TOP before unpinned
        Click: navigates to that session

      Context menu (appears on ... click):
        Background var(--surface-overlay), border 1px var(--border-default)
        Border-radius 10px, box-shadow var(--shadow-xl), min-width: 160px
        Items (each 32px, border-radius 6px, 12px horizontal padding):
          ✏  Rename → inline edit in sidebar (input replaces title, Enter=save, Escape=cancel)
          ☆  Pin / Unpin → toggles is\_pinned
          📤 Export → submenu: PDF / DOCX / Markdown
          🔗 Share → copies share link + toast.success("Link copied!")
          ─ divider ─
          🗑  Delete → confirmation dialog (destructive, red highlight text)

    TanStack Virtual virtualization: preserve or implement for session list.


BOTTOM SECTION (fixed at bottom, never scrolls):
Divider line at top: 1px var(--border-subtle)
Items (.sidebar-item, each 36px):
📋 All Sessions → /sessions
⚙  Settings → /settings
👤 Account → /account
🆘 Help \& Feedback → opens feedback modal

COLLAPSED STATE (0px wide):
Sidebar content hidden (overflow: hidden)
Navbar sidebar toggle icon changes to → (pointing right)
Chat area expands to fill full width
All keyboard shortcuts still work when sidebar collapsed

MOBILE BEHAVIOR (≤768px):
Sidebar HIDDEN by default (width 0)
Toggle button opens sidebar as OVERLAY (position fixed, z-index 60)
Overlay backdrop: rgba(0,0,0,0.4), clickable to close sidebar
Sidebar slides from left (translateX -100% → 0, 300ms ease-decel)
Side-by-side layout NEVER shown on mobile — always overlay
Sidebar open/closed state stored in localStorage: key "sidebar\_open"

─────────────────────────────────────────────────────────────────────
PHASE 2 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 2.1 — Create WorkspaceDropdown Component
Create: frontend/src/components/WorkspaceDropdown.tsx
Workspace definitions array with all 7 workspaces (id, label, icon, route,
badge, description) — exactly as defined in design spec above.
Uses usePathname() to detect active workspace.
Uses useRouter() for navigation.
Keyboard: Escape closes, ArrowUp/Down navigates, Enter selects.
Mousedown listener on document to close on outside click.
Applies .dropdown-enter animation class on open (CSS class from Phase 2.5).
When workspace changes: calls onWorkspaceChange(workspaceId) callback.

TASK 2.2 — Update LayoutWrapper Navbar
File: frontend/src/components/LayoutWrapper.tsx
Restructure navbar to CSS grid: \[auto] \[1fr] \[auto]
Left: Logo text placeholder (real Logo component in Phase 2.5)
Center: <WorkspaceDropdown onWorkspaceChange={handleWorkspaceChange} />
Right: Share button → Dark/Light toggle → Profile avatar with dropdown
Profile dropdown: full name, email, Settings, Dashboard, Billing, Logout
Share button: copies window.location.href + toast.success("Link copied!")
Dark/Light toggle: stores in localStorage, applies to
document.documentElement.dataset.theme

TASK 2.3 — Rebuild Sidebar Component
File: frontend/src/components/Sidebar.tsx
Implement per design spec above:
groupChatsByDate(chats): buckets Today/Yesterday/Last7Days/MonthYear
Session list with TanStack Virtual (keep/implement virtualization)
Context menu per item with all 5 actions (Rename, Pin, Export, Share, Delete)
Inline rename: input replaces title, Enter=save, Escape=cancel, blur=cancel
Delete confirmation: small modal, "Are you sure?" + Cancel/Delete buttons
Search filtering: client-side, filters by session title substring
New Chat button + bottom navigation items
Sidebar open/closed state in localStorage "sidebar\_open"
Mobile overlay behavior: isMobile state (window.innerWidth ≤ 768)
REMOVE any workspace list from sidebar — sessions ONLY

TASK 2.4 — Create Skeleton Loaders
Create: frontend/src/components/SkeletonLoader.tsx
Export these components (use .skeleton CSS class from Phase 2.5,
or animate-pulse as temporary fallback):

SidebarSkeleton: 8 rows of:
\[circle 16px] \[rect 140px h-4] \[rect 36px h-4] with 8px gap, 8px vertical spacing

ChatMessageSkeleton: 3 message pairs:
User: right-aligned rect 200px h-10, border-radius 12px
AI: left-aligned: rect 320px h-4, rect 260px h-4, rect 180px h-4 stacked, 8px gap

DocumentBarSkeleton: 3 horizontal cards:
Each: rect 160px × 40px, border-radius 10px, inner rect

WorkspaceHeroSkeleton: centered column:
Circle 56px, rect 200px h-6, rect 280px h-4,
then 3 rect buttons 140px × 40px in a row

TASK 2.5 — Chat Session Backend Updates
File: backend/app/api/v1/endpoints/chats.py
GET /chats: returns sessions sorted by created\_at DESC, including:
created\_at (ISO timestamp for date grouping)
workspace\_id (so sidebar can show workspace icon)
is\_pinned boolean (add to ChatSession model if missing)
title field for display
POST /chats: accepts workspace\_id in request body, stores on ChatSession.
GET /chats: returns all sessions for current user, sorted: pinned first, then created\_at DESC.
PATCH /chats/{id}/pin: toggles is\_pinned on ChatSession.
PATCH /chats/{id}/rename: updates title on ChatSession.
DELETE /chats/{id}: soft-delete (add deleted\_at column) with confirmation.

Run Alembic migration for any new columns:
alembic revision --autogenerate -m "add\_is\_pinned\_and\_workspace\_to\_session"
alembic upgrade head

─────────────────────────────────────────────────────────────────────
PHASE 2 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
cd frontend \&\& npx tsc --noEmit \&\& echo "TypeScript OK"
cd frontend \&\& npm run build \&\& echo "Build OK"

# Manual: Workspace dropdown opens with all 7 workspaces

# Manual: Clicking workspace changes center area; sidebar + navbar unchanged

# Manual: Sidebar toggle (≡) opens/closes with smooth 350ms animation

# Manual: Session items show workspace icons (emoji)

# Manual: Context menu shows all 5 options per session

# Manual: Sidebar state persists after page refresh (localStorage)

# Manual: Mobile (375px): sidebar appears as overlay with backdrop

DEFINITION OF DONE — PHASE 2:
✅ Workspace dropdown in navbar with all 7 workspaces
✅ Workspaces completely removed from sidebar
✅ Sidebar shows only sessions grouped by date
✅ Session context menu: rename, pin, export, share, delete
✅ Sidebar collapse/expand works smoothly (350ms)
✅ Mobile: sidebar as overlay with backdrop
✅ New Chat button creates session for active workspace
✅ Chat history loads from API (not local state)

\[CHECKPOINT 2 COMPLETE — Proceeding to Phase 2.5]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2.5 — VISUAL DESIGN SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Apply full visual design language to every component.
Typography, colors, spacing, motion, dark mode — all from one
source of truth. NEVER skip this phase — it affects all subsequent UI.
ESTIMATED TIME: 4–5 hours | RISK: Low-Medium | DEPENDS ON: Phase 2 complete

SCAN FIRST:
frontend/src/app/globals.css    ✓/✗/⚠
frontend/src/app/layout.tsx     ✓/✗/⚠
frontend/tailwind.config.ts     ✓/✗/⚠
frontend/package.json           ✓/✗/⚠

════════════════════════════════════════════════════════════════════════

PHASE 2.5 ADDENDUM — CITATION TEXT SPAN HIGHLIGHTING

════════════════════════════════════════════════════════════════════════



TASK 2.5-X1 — Store Text Span Coordinates on Extraction

─────────────────────────────────────────────────────────────────────

PURPOSE: When a user clicks a citation chip, instead of just opening the

page, the exact text excerpt should be visually highlighted in the PDF

viewer. This is the most powerful trust-building UX in the entire app.

It makes retrieval quality immediately visible and verifiable.



File: backend/app/services/pdf\_extractor.py

During text extraction with pymupdf4llm, store character-level coordinates:

&#x20; import fitz  # PyMuPDF direct API (pymupdf4llm wraps this)



&#x20; def extract\_with\_spans(pdf\_path: str) -> list\[dict]:

&#x20;   """

&#x20;   Extract text chunks with bounding box coordinates per chunk.

&#x20;   Returns chunks with: text, page\_number, bbox (x0, y0, x1, y1),

&#x20;   normalized to 0-1 range relative to page dimensions.

&#x20;   """

&#x20;   doc = fitz.open(pdf\_path)

&#x20;   chunks\_with\_spans = \[]

&#x20;   for page\_num, page in enumerate(doc, start=1):

&#x20;     blocks = page.get\_text("blocks")  # Returns (x0, y0, x1, y1, text, ...)

&#x20;     page\_width = page.rect.width

&#x20;     page\_height = page.rect.height

&#x20;     for block in blocks:

&#x20;       x0, y0, x1, y1, text = block\[:5]

&#x20;       if len(text.strip()) < 10:

&#x20;         continue  # skip noise

&#x20;       chunks\_with\_spans.append({

&#x20;         "text": text.strip(),

&#x20;         "page\_number": page\_num,

&#x20;         "bbox": {

&#x20;           "x0": round(x0 / page\_width, 4),

&#x20;           "y0": round(y0 / page\_height, 4),

&#x20;           "x1": round(x1 / page\_width, 4),

&#x20;           "y1": round(y1 / page\_height, 4)

&#x20;         }

&#x20;       })

&#x20;   return chunks\_with\_spans



Store bbox with each vector embedding in the vector store metadata.

When a chunk is returned as a citation, include its bbox in the response:

&#x20; { "doc\_id": "...", "page\_number": 4,

&#x20;   "text\_excerpt": "Current Assets 1,25,000",

&#x20;   "bbox": { "x0": 0.12, "y0": 0.34, "x1": 0.65, "y1": 0.38 } }



File: backend/app/api/v1/endpoints/query.py

Include bbox in all citation objects returned alongside query responses.



File: frontend/src/components/DocumentPreviewPanel.tsx

Receive citation bboxes as a prop: highlights?: CitationHighlight\[]

&#x20; type CitationHighlight = { page: number; bbox: BBox; label: string }



Render highlight overlay on the PDF viewer:

&#x20; For each highlight matching the current page:

&#x20;   Position an absolutely-placed div over the PDF canvas:

&#x20;     top: bbox.y0 \* pageHeight

&#x20;     left: bbox.x0 \* pageWidth

&#x20;     width: (bbox.x1 - bbox.x0) \* pageWidth

&#x20;     height: (bbox.y1 - bbox.y0) \* pageHeight

&#x20;     background: rgba(255, 200, 0, 0.35)   // yellow highlight

&#x20;     border: 2px solid rgba(255, 180, 0, 0.8)

&#x20;     border-radius: 2px

&#x20;     pointer-events: none  // does not interfere with PDF interaction



When a citation chip is clicked:

&#x20; setPreviewDoc(citingDocument)

&#x20; setPreviewPage(citation.page\_number)

&#x20; setHighlights(\[{ page: citation.page\_number, bbox: citation.bbox, label: "Source" }])



The yellow highlight band appears on the exact text span the AI used.

This is the primary trust signal. Users see exactly what the AI read.



DEFINITION OF DONE — TASK 2.5-X1:

&#x20; ✅ Click any citation chip → preview panel opens to correct page

&#x20; ✅ Yellow highlight band appears over the exact text the AI cited

&#x20; ✅ Highlight disappears when preview panel is closed

&#x20; ✅ Works for Finance workspace (⚠ values link to their source span)

&#x20; ✅ Works for Legal workspace (clause risks link to their excerpt)

─────────────────────────────────────────────────────────────────────
TASK 2.5.1 — Design Tokens (Single Source of Truth)
─────────────────────────────────────────────────────────────────────
Create: frontend/src/styles/tokens.css
Import in globals.css as the FIRST import.
ALL components MUST use these variables — never hardcode values.

Content:
/\* ═══════════════════════════════════════════════════
DOCUMINDAI DESIGN TOKENS
Single source of truth for all visual decisions.
═══════════════════════════════════════════════════ \*/

:root {
/\* ── BRAND ─────────────────────────────────────── \*/
--brand-hue: 220;
--brand-sat: 90%;
--brand: hsl(var(--brand-hue), var(--brand-sat), 60%);
--brand-dim: hsl(var(--brand-hue), 60%, 45%);
--brand-ghost: hsl(var(--brand-hue), var(--brand-sat), 60%, 0.08);
--brand-glow: hsl(var(--brand-hue), var(--brand-sat), 60%, 0.15);

&#x20;   /\* ── TYPOGRAPHY ─────────────────────────────────── \*/
    --font-display: var(--font-display-loaded, "Instrument Serif", Georgia, serif);
    --font-body:    var(--font-body-loaded, "DM Sans", "Helvetica Neue", sans-serif);
    --font-mono:    var(--font-mono-loaded, "JetBrains Mono", "Fira Code", monospace);

    /\* Scale — major third (1.250) ratio \*/
    --text-2xs: 0.64rem;   /\* 10.24px \*/
    --text-xs:  0.75rem;   /\* 12px \*/
    --text-sm:  0.875rem;  /\* 14px \*/
    --text-base: 1rem;     /\* 16px \*/
    --text-lg:  1.125rem;  /\* 18px \*/
    --text-xl:  1.25rem;   /\* 20px \*/
    --text-2xl: 1.5rem;    /\* 24px \*/
    --text-3xl: 1.875rem;  /\* 30px \*/
    --text-4xl: 2.25rem;   /\* 36px \*/

    /\* Weight \*/
    --weight-normal:   400;
    --weight-medium:   500;
    --weight-semibold: 600;
    --weight-bold:     700;

    /\* Leading \*/
    --leading-tight:   1.25;
    --leading-snug:    1.375;
    --leading-normal:  1.5;
    --leading-relaxed: 1.625;
    --leading-loose:   1.75;

    /\* Tracking \*/
    --tracking-tighter: -0.05em;
    --tracking-tight:   -0.025em;
    --tracking-snug:    -0.01em;
    --tracking-normal:   0em;
    --tracking-wide:     0.025em;
    --tracking-wider:    0.05em;
    --tracking-widest:   0.1em;

    /\* ── SPACING (4px base grid) ─────────────────── \*/
    --space-0-5: 2px;
    --space-1:   4px;
    --space-1-5: 6px;
    --space-2:   8px;
    --space-2-5: 10px;
    --space-3:   12px;
    --space-4:   16px;
    --space-5:   20px;
    --space-6:   24px;
    --space-8:   32px;
    --space-10:  40px;
    --space-12:  48px;
    --space-16:  64px;
    --space-20:  80px;
    --space-24:  96px;

    /\* ── RADIUS ──────────────────────────────────── \*/
    --radius-sm:   4px;
    --radius-md:   8px;
    --radius-lg:   12px;
    --radius-xl:   16px;
    --radius-2xl:  24px;
    --radius-full: 9999px;

    /\* ── MOTION ──────────────────────────────────── \*/
    --dur-instant: 0ms;
    --dur-fast:    100ms;
    --dur-normal:  200ms;
    --dur-slow:    350ms;
    --dur-slower:  500ms;
    --dur-slowest: 800ms;

    --ease-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
    --ease-decel:    cubic-bezier(0.0, 0.0, 0.2, 1);
    --ease-accel:    cubic-bezier(0.4, 0.0, 1.0, 1);
    --ease-bounce:   cubic-bezier(0.34, 1.56, 0.64, 1);
    --ease-spring:   cubic-bezier(0.22, 1.0, 0.36, 1);

    /\* ── WORKSPACE ACCENT COLORS ─────────────────── \*/
    --ws-general-accent:  hsl(220, 90%, 60%);
    --ws-exam-accent:     #7C3AED;   /\* purple — academic \*/
    --ws-hr-accent:       #0891B2;   /\* teal — corporate \*/
    --ws-study-accent:    #059669;   /\* green — growth \*/
    --ws-research-accent: #DC2626;   /\* red — precision \*/
    --ws-legal-accent:    #1D4ED8;   /\* deep blue — authority \*/
    --ws-finance-accent:  #0F766E;   /\* dark teal — trust \*/

    /\* ── SHADOWS ─────────────────────────────────── \*/
    --shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md:  0 4px 6px -1px rgb(0 0 0 / 0.10), 0 2px 4px -2px rgb(0 0 0 / 0.10);
    --shadow-lg:  0 10px 15px -3px rgb(0 0 0 / 0.10), 0 4px 6px -4px rgb(0 0 0 / 0.10);
    --shadow-xl:  0 20px 25px -5px rgb(0 0 0 / 0.10), 0 8px 10px -6px rgb(0 0 0 / 0.10);
    --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
    --shadow-brand:    0 0 0 3px hsl(var(--brand-hue) var(--brand-sat) 60% / 0.20);
    --shadow-brand-lg: 0 0 0 4px hsl(var(--brand-hue) var(--brand-sat) 60% / 0.30);

}

/\* LIGHT MODE SURFACES (default / :root) \*/
:root {
--surface-base:    #FAFAFA;
--surface-raised:  #FFFFFF;
--surface-overlay: #FFFFFF;
--surface-sunken:  #F4F4F5;
--surface-hover:   #F0F0F2;
--surface-active:  #E8E8EC;

&#x20;   --text-primary:   #0A0A0B;
    --text-secondary: #52525B;
    --text-tertiary:  #71717A;
    --text-disabled:  #A1A1AA;
    --text-brand:     hsl(var(--brand-hue), var(--brand-sat), 50%);

    --border-subtle:  rgb(0 0 0 / 0.06);
    --border-default: rgb(0 0 0 / 0.12);
    --border-strong:  rgb(0 0 0 / 0.24);

    --success-bg:     #F0FDF4;  --success-text:   #166534;  --success-border: #BBF7D0;
    --warning-bg:     #FFFBEB;  --warning-text:   #92400E;  --warning-border: #FDE68A;
    --error-bg:       #FEF2F2;  --error-text:     #991B1B;  --error-border:   #FECACA;
    --info-bg:        #EFF6FF;  --info-text:      #1E40AF;  --info-border:    #BFDBFE;

}

/\* DARK MODE SURFACES \*/
\[data-theme="dark"], .dark {
--surface-base:    #0C0C0E;
--surface-raised:  #141416;
--surface-overlay: #1C1C1F;
--surface-sunken:  #09090B;
--surface-hover:   #1E1E22;
--surface-active:  #27272A;

&#x20;   --text-primary:   #FAFAFA;
    --text-secondary: #A1A1AA;
    --text-tertiary:  #71717A;
    --text-disabled:  #52525B;
    --text-brand:     hsl(var(--brand-hue), var(--brand-sat), 70%);

    --border-subtle:  rgb(255 255 255 / 0.05);
    --border-default: rgb(255 255 255 / 0.10);
    --border-strong:  rgb(255 255 255 / 0.20);

    --success-bg:     #052E16;  --success-text:   #86EFAC;  --success-border: #166534;
    --warning-bg:     #1C1400;  --warning-text:   #FDE68A;  --warning-border: #92400E;
    --error-bg:       #1C0000;  --error-text:     #FCA5A5;  --error-border:   #991B1B;
    --info-bg:        #0A1628;  --info-text:      #93C5FD;  --info-border:    #1E40AF;

}

─────────────────────────────────────────────────────────────────────
TASK 2.5.2 — Typography System
─────────────────────────────────────────────────────────────────────
Create: frontend/src/styles/typography.css
Import in globals.css after tokens.css.

Load fonts in frontend/src/app/layout.tsx via next/font/google:
import { Instrument\_Serif, DM\_Sans, JetBrains\_Mono } from "next/font/google"
const instrumentSerif = Instrument\_Serif({
weight: "400", style: \["normal", "italic"],
variable: "--font-display-loaded", subsets: \["latin"] })
const dmSans = DM\_Sans({
weight: \["400","500","600","700"],
variable: "--font-body-loaded", subsets: \["latin"] })
const jetbrainsMono = JetBrains\_Mono({
weight: \["400","500"],
variable: "--font-mono-loaded", subsets: \["latin"] })
// Apply className to <html> element

Typography utility classes content:
.text-display      { font-family: var(--font-display); font-size: var(--text-4xl);
font-weight: var(--weight-normal); line-height: var(--leading-tight);
letter-spacing: var(--tracking-tight); color: var(--text-primary); }
.text-heading-1    { font-family: var(--font-display); font-size: var(--text-3xl);
line-height: var(--leading-tight); letter-spacing: var(--tracking-snug);
color: var(--text-primary); }
.text-heading-2    { font-family: var(--font-body); font-size: var(--text-2xl);
font-weight: var(--weight-semibold); line-height: var(--leading-snug);
letter-spacing: var(--tracking-snug); color: var(--text-primary); }
.text-heading-3    { font-family: var(--font-body); font-size: var(--text-xl);
font-weight: var(--weight-semibold); line-height: var(--leading-snug);
color: var(--text-primary); }
.text-body-lg      { font-family: var(--font-body); font-size: var(--text-base);
line-height: var(--leading-relaxed); color: var(--text-primary); }
.text-body         { font-family: var(--font-body); font-size: var(--text-sm);
line-height: var(--leading-normal); color: var(--text-primary); }
.text-body-secondary { font-family: var(--font-body); font-size: var(--text-sm);
line-height: var(--leading-normal); color: var(--text-secondary); }
.text-caption      { font-family: var(--font-body); font-size: var(--text-xs);
line-height: var(--leading-normal); color: var(--text-tertiary); }
.text-label        { font-family: var(--font-body); font-size: var(--text-2xs);
font-weight: var(--weight-medium); letter-spacing: var(--tracking-widest);
text-transform: uppercase; color: var(--text-tertiary); }
.text-mono         { font-family: var(--font-mono); font-size: var(--text-xs);
line-height: var(--leading-relaxed); color: var(--text-secondary); }
.text-response     { font-family: var(--font-body); font-size: var(--text-base);
line-height: var(--leading-loose); color: var(--text-primary);
max-width: 72ch; }

Apply to WorkspaceUI.tsx:
AI message content → .text-response
Citation chips → .text-mono
Sidebar section labels (TODAY etc.) → .text-label
Workspace welcome title → .text-heading-1
Replace all hardcoded text-sm / text-lg / font-semibold with semantic classes.

─────────────────────────────────────────────────────────────────────
TASK 2.5.3 — Motion System
─────────────────────────────────────────────────────────────────────
Create: frontend/src/styles/motion.css
Import in globals.css after typography.css.

Content:
/\* ═══════════════════════════════════════════════════
DOCUMINDAI MOTION SYSTEM
Motion communicates state changes — never decorates.
═══════════════════════════════════════════════════ \*/

/\* Accessibility — disable animations for sensitive users \*/
@media (prefers-reduced-motion: reduce) {
\*, \*::before, \*::after {
animation-duration: 0.01ms !important;
animation-iteration-count: 1 !important;
transition-duration: 0.01ms !important;
}
}

@keyframes fade-in     { from { opacity: 0; } to { opacity: 1; } }
@keyframes fade-out    { from { opacity: 1; } to { opacity: 0; } }

@keyframes slide-up    { from { opacity: 0; transform: translateY(8px); }
to   { opacity: 1; transform: translateY(0); } }
@keyframes slide-down  { from { opacity: 0; transform: translateY(-8px); }
to   { opacity: 1; transform: translateY(0); } }
@keyframes slide-in-right  { from { opacity: 0; transform: translateX(24px); }
to   { opacity: 1; transform: translateX(0); } }
@keyframes slide-out-right { from { opacity: 1; transform: translateX(0); }
to   { opacity: 0; transform: translateX(24px); } }
@keyframes slide-in-left   { from { opacity: 0; transform: translateX(-16px); }
to   { opacity: 1; transform: translateX(0); } }

@keyframes scale-in    { from { opacity: 0; transform: scale(0.95); }
to   { opacity: 1; transform: scale(1); } }
@keyframes scale-in-bounce {
0%   { opacity: 0; transform: scale(0.90); }
70%  { transform: scale(1.02); }
100% { opacity: 1; transform: scale(1); } }

/\* Streaming text tokens \*/
@keyframes token-appear { from { opacity: 0; } to { opacity: 1; } }
.streaming-token { animation: token-appear var(--dur-fast) var(--ease-decel) both; }

/\* Streaming cursor blink \*/
@keyframes cursor-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.streaming-cursor::after {
content: "▍"; display: inline-block;
animation: cursor-blink 0.8s ease infinite;
color: var(--brand); margin-left: 1px;
font-size: 0.9em; vertical-align: -0.05em; }

/\* Upload progress shimmer \*/
@keyframes progress-shimmer {
0%   { background-position: -200% 0; }
100% { background-position: 200% 0; } }
.progress-shimmer {
background: linear-gradient(90deg, var(--brand) 0%,
hsl(var(--brand-hue), var(--brand-sat), 75%) 50%, var(--brand) 100%);
background-size: 200% 100%;
animation: progress-shimmer 1.5s linear infinite; }

/\* Skeleton loaders \*/
@keyframes skeleton-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.skeleton {
background: var(--surface-hover); border-radius: var(--radius-sm);
animation: skeleton-pulse 1.8s var(--ease-standard) infinite; }

/\* Panel slide (document preview) \*/
@keyframes panel-slide-in  { from { opacity: 0; transform: translateX(100%); }
to   { opacity: 1; transform: translateX(0); } }
@keyframes panel-slide-out { from { opacity: 1; transform: translateX(0); }
to   { opacity: 0; transform: translateX(100%); } }
.panel-enter { animation: panel-slide-in  var(--dur-slow)   var(--ease-decel) both; }
.panel-exit  { animation: panel-slide-out var(--dur-normal)  var(--ease-accel) both; }

/\* Dropdowns \*/
.dropdown-enter { animation: scale-in var(--dur-normal) var(--ease-bounce) both;
transform-origin: top center; }
.dropdown-exit  { animation: fade-out var(--dur-fast) var(--ease-accel) both; }

/\* Messages \*/
.message-enter  { animation: slide-up var(--dur-normal) var(--ease-decel) both; }

/\* Modals \*/
.modal-backdrop-enter { animation: fade-in var(--dur-normal) var(--ease-standard) both; }
.modal-content-enter  { animation: scale-in-bounce var(--dur-slow) var(--ease-bounce) both; }

/\* Toasts \*/
.toast-enter { animation: slide-in-right var(--dur-normal) var(--ease-bounce) both; }
.toast-exit  { animation: slide-out-right var(--dur-normal) var(--ease-accel) both; }

/\* Interactive elements \*/
.interactive { transition:
background-color var(--dur-fast) var(--ease-standard),
border-color     var(--dur-fast) var(--ease-standard),
color            var(--dur-fast) var(--ease-standard),
box-shadow       var(--dur-fast) var(--ease-standard),
opacity          var(--dur-fast) var(--ease-standard); }

/\* Card hover lift \*/
.hover-lift { transition: transform var(--dur-normal) var(--ease-standard),
box-shadow var(--dur-normal) var(--ease-standard); }
.hover-lift:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }

Apply in WorkspaceUI.tsx:

* .message-enter on every new message container as it is appended
* .streaming-cursor on AI message while isStreaming === true
* Remove .streaming-cursor when isStreaming becomes false
* .progress-shimmer on upload card progress bar when uploading
* .panel-enter to document preview panel on open
* .dropdown-enter to every dropdown on mount
* .interactive on every button, link, and clickable element

In SkeletonLoader.tsx: replace animate-pulse with .skeleton class.

─────────────────────────────────────────────────────────────────────
TASK 2.5.4 — Brand Identity \& Logo Component
─────────────────────────────────────────────────────────────────────
Create: frontend/src/components/Logo.tsx

Content:
"use client"
import React from "react"

interface LogoProps {
size?: "sm" | "md" | "lg"
className?: string
}
const sizeMap = {
sm: { docu: "text-lg", mind: "text-lg" },
md: { docu: "text-xl", mind: "text-xl" },
lg: { docu: "text-2xl", mind: "text-2xl" },
}

export function Logo({ size = "md", className = "" }: LogoProps) {
const s = sizeMap\[size]
return (
<span className={`inline-flex items-baseline gap-0 select-none ${className}`}
aria-label="DocuMindAI">
{/\* "Docu" — Instrument Serif italic for document trust */}
<span style={{ fontFamily: "var(--font-display)", fontStyle: "italic",
color: "var(--text-primary)",
letterSpacing: "var(--tracking-snug)", lineHeight: 1 }}
className={s.docu}>Docu</span>
{/* "Mind" — DM Sans semibold in brand color */}
<span style={{ fontFamily: "var(--font-body)", fontWeight: 600,
color: "var(--brand)",
letterSpacing: "var(--tracking-wide)", lineHeight: 1 }}
className={s.mind}>Mind</span>
{/* "AI" — superscript, tertiary \*/}
<span style={{ fontFamily: "var(--font-body)", fontWeight: 500,
color: "var(--text-tertiary)", fontSize: "0.6em",
verticalAlign: "super", lineHeight: 1,
letterSpacing: "var(--tracking-widest)" }}>AI</span>
</span>
)
}

export function LogoMark({ size = 32 }: { size?: number }) {
return (
<svg width={size} height={size} viewBox="0 0 32 32" fill="none"xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
{/\* D letterform — document metaphor */}
<rect x="4" y="4" width="14" height="24" rx="3"fill="none" stroke="currentColor" strokeWidth="2"/>
<path d="M4 4 C4 4 14 4 18 10 C22 16 18 28 18 28 L4 28 Z"fill="hsl(220 90% 60% / 0.15)"/>
{/* Dot — the "intelligence" point \*/}
<circle cx="24" cy="8" r="4" fill="hsl(220, 90%, 60%)"/>
</svg>
)
}

File: frontend/src/components/LayoutWrapper.tsx
Replace existing logo with:

<Link href="/" className="flex items-center gap-2 hover:opacity-80
                             transition-opacity duration-100" aria-label="DocuMindAI home">
    <LogoMark size={24} />
    <Logo size="sm" />
  </Link>

File: frontend/src/app/layout.tsx
Update metadata:
export const metadata = {
title: { default: "DocuMindAI", template: "%s — DocuMindAI" },
description: "Trusted document intelligence with grounded answers.",
applicationName: "DocuMindAI",
themeColor: \[
{ media: "(prefers-color-scheme: light)", color: "#FAFAFA" },
{ media: "(prefers-color-scheme: dark)",  color: "#0C0C0E" },
],
icons: { icon: "/favicon.svg", apple: "/apple-touch-icon.png" },
openGraph: {
title: "DocuMindAI",
description: "Trusted document intelligence with grounded answers.",
type: "website",
}
}

─────────────────────────────────────────────────────────────────────
TASK 2.5.5 — Component CSS Library
─────────────────────────────────────────────────────────────────────
Create: frontend/src/styles/components.css
Import in globals.css after motion.css.
All values from design tokens — NEVER hardcoded values.

Content (key component classes):
/\* BUTTONS \*/
.btn { display: inline-flex; align-items: center; justify-content: center;
gap: var(--space-2); padding: var(--space-2) var(--space-4);
border-radius: var(--radius-md); font-family: var(--font-body);
font-size: var(--text-sm); font-weight: var(--weight-medium);
line-height: 1; cursor: pointer; border: none;
transition: all var(--dur-fast) var(--ease-standard); }
.btn-primary  { background: var(--brand); color: #fff; }
.btn-primary:hover { filter: brightness(1.08); }
.btn-secondary { background: var(--surface-raised); color: var(--text-primary);
border: 1px solid var(--border-default); }
.btn-secondary:hover { background: var(--surface-hover); border-color: var(--border-strong); }
.btn-ghost  { background: transparent; color: var(--text-secondary); }
.btn-ghost:hover { background: var(--surface-hover); color: var(--text-primary); }
.btn-danger { background: var(--error-bg); color: var(--error-text);
border: 1px solid var(--error-border); }
.btn-sm { padding: var(--space-1-5) var(--space-3); font-size: var(--text-xs); }
.btn-lg { padding: var(--space-3) var(--space-6); font-size: var(--text-base); }
.btn-icon { padding: 0; width: 36px; height: 36px; border-radius: var(--radius-md); }
.btn-icon.btn-sm { width: 28px; height: 28px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; pointer-events: none; }

/\* CARDS \*/
.card { background: var(--surface-raised); border: 1px solid var(--border-default);
border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
padding: var(--space-4); transition: box-shadow var(--dur-fast) var(--ease-standard); }
.card:hover { box-shadow: var(--shadow-md); }
.card-active { border-color: var(--brand); box-shadow: var(--shadow-brand); }

/\* INPUTS \*/
.input { width: 100%; height: 44px; padding: 0 var(--space-3);
background: var(--surface-sunken); border: 1px solid var(--border-default);
border-radius: var(--radius-md); font-family: var(--font-body);
font-size: var(--text-sm); color: var(--text-primary);
transition: border-color var(--dur-fast) var(--ease-standard),
box-shadow var(--dur-fast) var(--ease-standard); }
.input:focus { outline: none; border-color: var(--brand);
box-shadow: var(--shadow-brand); }
.chat-input { background: transparent; border: none; outline: none; resize: none;
font-family: var(--font-body); font-size: var(--text-sm);
color: var(--text-primary); min-height: 44px; max-height: 200px; }
.chat-input-container { background: var(--surface-raised);
border: 1px solid var(--border-default);
border-radius: var(--radius-xl); box-shadow: var(--shadow-sm);
padding: var(--space-3) var(--space-4); }
.chat-input-container:focus-within { border-color: var(--border-strong);
box-shadow: var(--shadow-md); }

/\* BADGES \*/
.badge { display: inline-flex; align-items: center; padding: var(--space-0-5) var(--space-2);
border-radius: var(--radius-full); font-size: var(--text-2xs);
font-weight: var(--weight-medium); }
.badge-brand   { background: var(--brand-ghost); color: var(--text-brand);
border: 1px solid var(--brand-glow); }
.badge-success { background: var(--success-bg); color: var(--success-text);
border: 1px solid var(--success-border); }
.badge-warning { background: var(--warning-bg); color: var(--warning-text);
border: 1px solid var(--warning-border); }
.badge-error   { background: var(--error-bg); color: var(--error-text);
border: 1px solid var(--error-border); }
.badge-neutral { background: var(--surface-hover); color: var(--text-secondary);
border: 1px solid var(--border-default); }

/\* NAVBAR + SIDEBAR \*/
.navbar { height: 52px; position: sticky; top: 0;
background: var(--surface-base); backdrop-filter: blur(12px);
border-bottom: 1px solid var(--border-subtle); z-index: 50;
display: grid; grid-template-columns: auto 1fr auto;
align-items: center; padding: 0 var(--space-4); gap: var(--space-3); }
.sidebar { width: 260px; height: 100vh; position: sticky; top: 52px;
background: var(--surface-base); border-right: 1px solid var(--border-subtle);
transition: width var(--dur-slow) var(--ease-standard); overflow: hidden; }
.sidebar.collapsed { width: 0; border-right: none; }
.sidebar-item { display: flex; align-items: center; gap: var(--space-2);
padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
cursor: pointer; color: var(--text-secondary);
transition: background-color var(--dur-fast) var(--ease-standard),
color var(--dur-fast) var(--ease-standard); }
.sidebar-item:hover  { background: var(--surface-hover); color: var(--text-primary); }
.sidebar-item.active { background: var(--brand-ghost); color: var(--text-brand); }

/\* CHAT MESSAGES \*/
.message-user { align-self: flex-end; max-width: 75%; background: var(--brand); color: #fff;
border-radius: var(--radius-xl) var(--radius-xl) var(--radius-sm) var(--radius-xl);
padding: var(--space-3) var(--space-4); font-size: var(--text-sm);
line-height: var(--leading-relaxed); }
.message-ai   { align-self: flex-start; width: 100%; max-width: 72ch;
color: var(--text-primary); padding: var(--space-3) 0; }

/\* CITATION CHIPS \*/
.citation-chip { display: inline-flex; align-items: center; gap: var(--space-1);
padding: var(--space-0-5) var(--space-2);
background: var(--brand-ghost); border: 1px solid var(--brand-glow);
border-radius: var(--radius-full); font-family: var(--font-mono);
font-size: var(--text-2xs); color: var(--text-brand); cursor: pointer;
vertical-align: middle;
transition: background-color var(--dur-fast) var(--ease-standard),
border-color var(--dur-fast) var(--ease-standard); }
.citation-chip:hover { background: var(--brand-glow); border-color: var(--brand); }

/\* DOCUMENT CHIPS \*/
.doc-chip { display: inline-flex; align-items: center; gap: var(--space-2);
padding: var(--space-2) var(--space-3); background: var(--surface-raised);
border: 1px solid var(--border-default); border-radius: var(--radius-lg);
font-size: var(--text-xs); color: var(--text-secondary);
min-width: 160px; max-width: 200px; position: relative; overflow: hidden;
transition: border-color var(--dur-fast) var(--ease-standard); }
.doc-chip:hover      { border-color: var(--border-strong); }
.doc-chip.ready      { border-color: var(--success-border); }
.doc-chip.processing { border-color: var(--warning-border); }
.doc-chip.error      { border-color: var(--error-border); }
.doc-chip-progress   { position: absolute; bottom: 0; left: 0; height: 2px;
background: var(--brand);
border-radius: 0 0 var(--radius-sm) var(--radius-sm);
transition: width var(--dur-normal) var(--ease-standard); }

/\* DROPDOWNS \*/
.dropdown { background: var(--surface-overlay); border: 1px solid var(--border-default);
border-radius: var(--radius-lg); box-shadow: var(--shadow-xl);
padding: var(--space-1); min-width: 200px; overflow: hidden; }
.dropdown-item { display: flex; align-items: center; gap: var(--space-2);
padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
font-size: var(--text-sm); color: var(--text-secondary); cursor: pointer;
transition: background-color var(--dur-fast) var(--ease-standard),
color var(--dur-fast) var(--ease-standard); }
.dropdown-item:hover  { background: var(--surface-hover); color: var(--text-primary); }
.dropdown-item.active { background: var(--brand-ghost); color: var(--text-brand);
font-weight: var(--weight-medium); }

/\* MODALS \*/
.modal-backdrop { position: fixed; inset: 0; background: rgb(0 0 0 / 0.5);
z-index: 100; display: flex; align-items: center;
justify-content: center; padding: var(--space-4); }
.modal { background: var(--surface-overlay); border: 1px solid var(--border-default);
border-radius: var(--radius-2xl); box-shadow: var(--shadow-2xl);
width: 100%; max-width: 480px; max-height: 85vh; overflow-y: auto;
padding: var(--space-6); }

/\* SCROLLBAR \*/
::-webkit-scrollbar        { width: 4px; height: 4px; }
::-webkit-scrollbar-track  { background: transparent; }
::-webkit-scrollbar-thumb  { background: var(--border-default);
border-radius: var(--radius-full); }
::-webkit-scrollbar-thumb:hover { background: var(--border-strong); }

/\* FOCUS RING — accessible, using brand color \*/
:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px;
border-radius: var(--radius-sm); }

/\* CONFIDENCE BADGES \*/
.confidence-high   { @apply badge badge-success; }
.confidence-medium { @apply badge badge-warning; }
.confidence-low    { @apply badge badge-error; }

/\* DIVIDERS \*/
.divider { height: 1px; background: var(--border-subtle); margin: var(--space-2) 0; }

Apply in WorkspaceUI.tsx:
Replace ALL Tailwind utility classes on buttons, inputs, cards, messages
with semantic component classes from components.css.
Tailwind layout utilities (flex, grid, w-full, overflow, gap) still OK.
NEVER mix component classes and Tailwind colors on the same element.

─────────────────────────────────────────────────────────────────────
TASK 2.5.6 — Dark Mode Implementation
─────────────────────────────────────────────────────────────────────
Create: frontend/src/hooks/useTheme.ts
"use client"
import { useState, useEffect, useCallback } from "react"

type Theme = "light" | "dark" | "system"

export function useTheme() {
const \[theme, setThemeState] = useState<Theme>("system")

&#x20;   const applyTheme = useCallback((t: Theme) => {
      const root = document.documentElement
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
      const isDark = t === "dark" || (t === "system" \&\& prefersDark)
      root.setAttribute("data-theme", isDark ? "dark" : "light")
      root.classList.toggle("dark", isDark)
    }, \[])

    useEffect(() => {
      const saved = (localStorage.getItem("theme") as Theme) || "system"
      setThemeState(saved)
      applyTheme(saved)
      const mq = window.matchMedia("(prefers-color-scheme: dark)")
      const handler = () => { if (theme === "system") applyTheme("system") }
      mq.addEventListener("change", handler)
      return () => mq.removeEventListener("change", handler)
    }, \[])

    const setTheme = useCallback((t: Theme) => {
      setThemeState(t)
      localStorage.setItem("theme", t)
      applyTheme(t)
    }, \[applyTheme])

    return { theme, setTheme }

}

File: frontend/src/app/layout.tsx
Add inline FOUC-prevention script in <head>:

<script dangerouslySetInnerHTML={{ \_\_html: `
    (function() {
      try {
        var t = localStorage.getItem('theme') || 'system';
        var dark = t === 'dark' || (t === 'system' \&\&
          window.matchMedia('(prefers-color-scheme: dark)').matches);
        document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
        if (dark) document.documentElement.classList.add('dark');
      } catch(e) {}
    })();
  `}} />

File: frontend/src/components/LayoutWrapper.tsx
Wire useTheme to the dark/light toggle button:
  const { theme, setTheme } = useTheme()
  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark")
  }
  // Icon: ☀ in dark mode | ☾ in light mode | 💻 in system mode

─────────────────────────────────────────────────────────────────────
TASK 2.5.7 — Refined Layout \& Spatial Dimensions
─────────────────────────────────────────────────────────────────────
File: frontend/src/components/WorkspaceUI.tsx

Apply these EXACT dimensions:
  Sidebar width:      260px (collapsed: 0px)
  Navbar height:      52px
  Document bar:       56px when has docs, 0 when empty (animate height change)
  Input area:         min 72px, max 280px (grows with textarea)
  Preview panel:      380px (fixed width from right)
  Content max-width:  760px (centered in remaining space)

SPACING RULES:
  Chat messages: var(--space-6) vertical gap between message pairs
  User → AI pair: no internal gap (they belong together)
  Input area top padding: var(--space-4)
  Chat area side padding: var(--space-8) desktop, var(--space-4) mobile
  Message content max-width: 72ch for AI, 75% for user

MICRO-TYPOGRAPHY IN CHAT:
  Message timestamp: .text-caption, shown on hover only (opacity 0 → 1)
  Message actions (copy, regenerate): appear on hover, .text-caption size
  Citation chips: inline-flex, vertically centered with surrounding text
  Code blocks: .text-mono, var(--surface-sunken), border var(--border-subtle),
               border-radius var(--radius-md), padding var(--space-4)

─────────────────────────────────────────────────────────────────────
TASK 2.5.8 — Workspace Accent System
─────────────────────────────────────────────────────────────────────
File: frontend/src/components/WorkspaceUI.tsx
AND: frontend/src/components/LayoutWrapper.tsx

On workspace change, update CSS variable:
  const WORKSPACE\_ACCENTS: Record<string, string> = {
    general:  "220",
    exam:     "262",
    hr:       "198",
    study:    "160",
    research: "0",
    legal:    "221",
    finance:  "174",
  }

  useEffect(() => {
    const hue = WORKSPACE\_ACCENTS\[currentWorkspace] || "220"
    document.documentElement.style.setProperty("--brand-hue", hue)
    // Only update hue — sat/light stay from tokens for consistency
    // This ensures each workspace "feels" slightly different without jarring shifts
  }, \[currentWorkspace])

The workspace icon in dropdown uses workspace accent.
Active sidebar item uses workspace accent.
Send button, upload progress, and citation chips all inherit from --brand.

─────────────────────────────────────────────────────────────────────
TASK 2.5.9 — Tailwind Config Alignment
─────────────────────────────────────────────────────────────────────
File: frontend/tailwind.config.ts
Content:
  import type { Config } from "tailwindcss"
  const config: Config = {
    content: \["./src/\*\*/\*.{ts,tsx}"],
    darkMode: \["class", '\[data-theme="dark"]'],
    theme: {
      extend: {
        colors: {
          brand: "hsl(var(--brand-hue) var(--brand-sat) 60% / <alpha-value>)",
          surface: { base: "var(--surface-base)", raised: "var(--surface-raised)",
                     overlay: "var(--surface-overlay)", sunken: "var(--surface-sunken)",
                     hover: "var(--surface-hover)", active: "var(--surface-active)" },
          border: { subtle: "var(--border-subtle)", default: "var(--border-default)",
                    strong: "var(--border-strong)" },
          text: { primary: "var(--text-primary)", secondary: "var(--text-secondary)",
                  tertiary: "var(--text-tertiary)", disabled: "var(--text-disabled)",
                  brand: "var(--text-brand)" },
        },
        fontFamily: { display: \["var(--font-display)"], body: \["var(--font-body)"],
                      mono: \["var(--font-mono)"] },
        fontSize: {
          "2xs": \["var(--text-2xs)", { lineHeight: "var(--leading-normal)" }],
          xs:    \["var(--text-xs)",  { lineHeight: "var(--leading-normal)" }],
          sm:    \["var(--text-sm)",  { lineHeight: "var(--leading-normal)" }],
          base:  \["var(--text-base)",{ lineHeight: "var(--leading-relaxed)" }],
          lg:    \["var(--text-lg)",  { lineHeight: "var(--leading-snug)" }],
          xl:    \["var(--text-xl)",  { lineHeight: "var(--leading-snug)" }],
          "2xl": \["var(--text-2xl)", { lineHeight: "var(--leading-tight)" }],
          "3xl": \["var(--text-3xl)", { lineHeight: "var(--leading-tight)" }],
          "4xl": \["var(--text-4xl)", { lineHeight: "var(--leading-tight)" }],
        },
        spacing: { "0.5": "var(--space-0-5)", "1.5": "var(--space-1-5)",
                   "2.5": "var(--space-2-5)" },
        borderRadius: { sm: "var(--radius-sm)", md: "var(--radius-md)",
                        lg: "var(--radius-lg)", xl: "var(--radius-xl)",
                        "2xl": "var(--radius-2xl)" },
        transitionDuration: { fast: "var(--dur-fast)", normal: "var(--dur-normal)",
                               slow: "var(--dur-slow)" },
        transitionTimingFunction: { standard: "var(--ease-standard)",
                                     decel: "var(--ease-decel)", bounce: "var(--ease-bounce)" },
        boxShadow: { brand: "var(--shadow-brand)", "brand-lg": "var(--shadow-brand-lg)" },
      },
    },
    plugins: \[],
  }
  export default config

─────────────────────────────────────────────────────────────────────
PHASE 2.5 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
  test -f frontend/src/styles/tokens.css     \&\& echo "tokens.css OK"
  test -f frontend/src/styles/typography.css \&\& echo "typography.css OK"
  test -f frontend/src/styles/motion.css     \&\& echo "motion.css OK"
  test -f frontend/src/styles/components.css \&\& echo "components.css OK"
  test -f frontend/src/components/Logo.tsx   \&\& echo "Logo.tsx OK"
  test -f frontend/src/hooks/useTheme.ts     \&\& echo "useTheme.ts OK"
  grep "Instrument\_Serif" frontend/src/app/layout.tsx \&\& echo "Fonts OK"
  grep "brand-hue" frontend/src/styles/tokens.css \&\& echo "Brand token OK"
  cd frontend \&\& npx tsc --noEmit \&\& echo "TypeScript OK"
  cd frontend \&\& npm run build \&\& echo "Build OK"
  # Manual: toggle dark/light → no flash on reload (FOUC prevention test)
  # Manual: Instrument Serif visible in headings
  # Manual: Workspace accent shifts when switching workspaces
  # Manual: Cmd+/ opens shortcuts modal

DEFINITION OF DONE — PHASE 2.5:
  ✅ All 4 CSS files exist and imported in globals.css
  ✅ Instrument Serif + DM Sans + JetBrains Mono load (verify in Network tab)
  ✅ Dark mode toggles with no flash on reload
  ✅ All buttons use .btn classes, no hardcoded Tailwind color classes
  ✅ Streaming cursor animates during AI response
  ✅ Skeleton loaders pulse correctly
  ✅ Keyboard shortcuts work (Cmd+B, Cmd+N, Cmd+K, Cmd+/)
  ✅ Motion respects prefers-reduced-motion

\[CHECKPOINT 2.5 COMPLETE — Proceeding to Phase 3]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — UPLOAD SYSTEM + DOCUMENT MANAGEMENT UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Complete, reliable, beautiful document upload with real-time progress.
         Drag-and-drop. Duplicate detection. Status polling. Preview panel.
         pymupdf4llm integration for native PDFs.
ESTIMATED TIME: 4–5 hours | RISK: Medium | DEPENDS ON: Phase 2.5 complete

SCAN FIRST:
  frontend/src/components/WorkspaceUI.tsx        ✓/✗/⚠
  frontend/src/lib/api.ts                        ✓/✗/⚠
  backend/app/api/v1/endpoints/documents.py      ✓/✗/⚠
  backend/app/workers/tasks/document\_tasks.py    ✓/✗/⚠ \[READ ONLY]

─────────────────────────────────────────────────────────────────────
PHASE 3 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

DOCUMENT BAR (above input, horizontal scroll):
  Container: 56px tall when documents exist, 0px when no documents
             (animate height change with CSS transition)
  Background: var(--surface-base), border-top: 1px var(--border-subtle)
  Padding: 8px 16px
  Horizontal scroll: overflow-x auto, scrollbar hidden on mobile, 4px on desktop
  scroll-snap-type: x mandatory; children: scroll-snap-align: start

  Document chip (.doc-chip): width 160px min / 200px max, height 40px
    Layout: \[file icon 16px] \[filename truncated] \[status badge] \[× if done/error]
    File icon: 📄 PDF, 📝 DOCX, 🖼 image — 14px emoji
    Filename: DM Sans 12px, text-primary, max 18 chars + ellipsis, tooltip = full name
    Status badge (right side, .badge style):
      uploading:  .badge-brand "↑ XX%"
      processing: .badge-warning "⟳ Processing"
      indexing:   .badge-warning "⟳ Indexing"
      ready:      .badge-success "✓ Ready"
      error:      .badge-error "✗ Failed"
    × button: appears only when ready or error; ghost icon 20×20px
    Progress bar: .doc-chip-progress — absolute bottom stripe, animates width 0→100%
    Hover: shows "👁 Preview" button overlay (absolute positioned, 24px height)
    Click "👁 Preview": opens inline PDF preview panel

  "+ Add Documents" button (always visible at end of chip row):
    Outlined small: border dashed 1px var(--border-default), border-radius 8px
    Width: 140px, height: 40px
    Content: + icon 12px + "Add Documents" 12px text-secondary
    Hover: border-brand, text-brand, background brand-ghost
    On click: triggers hidden file input (accept PDF, DOCX)
    Tooltip: "Or drag and drop files here"

DRAG AND DROP OVERLAY:
  When user drags files over chat area, show full-area drop zone:
  Position: absolute, fills entire chat main area, z-index 30
  Background: color-mix(in srgb, var(--brand-ghost) 90%, transparent)
  Border: 2px dashed var(--brand)
  Border-radius: 16px
  Content (centered):
    📄 icon at 48px brand color
    "Drop PDFs here to upload" — Instrument Serif 24px, brand color
    "Supports PDF and DOCX files up to 50MB" — 14px text-secondary
  Enters with slide-up + fade-in 150ms; Exits with fade-out 100ms

INLINE PDF PREVIEW PANEL (slides from right):
  Width: 380px fixed, height: full app minus navbar
  Background: var(--surface-raised), border-left: 1px var(--border-subtle)
  Animation: .panel-enter (slide-in from right 350ms ease-decel)
  z-index: 40

  Panel header (48px tall):
    \[← close button 32×32px] \[filename truncated, 13px text-secondary]
    \[page N / total, 12px mono text-tertiary] \[zoom - / 100% / + small ghost buttons]

  PDF viewer area (fills remaining height):
    Renders actual PDF using existing EnterpriseDocumentViewer component
    Props: docId, initialPage (for citation-linked opening)
    Scrollable, page-by-page navigation
    ← → arrow buttons, page number input at top

  Panel footer (40px):
    "Ask AI about selection" button — brand primary, full width
    Appears when text is selected in PDF viewer
    On click: copies selected text → pastes into chat input + focuses input

  Chat area shrinks by 380px when preview panel open (flex layout)
  On mobile (≤768px): preview panel takes full viewport width as overlay

─────────────────────────────────────────────────────────────────────
PHASE 3 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 3.1 — Upload State Type System
File: frontend/src/components/WorkspaceUI.tsx
  type UploadState = {
    id: string; name: string; progress: number;
    status: "uploading" | "processing" | "indexing" | "ready" | "error";
    error?: string; docId?: string; mimeType: string;
  }
  const \[uploads, setUploads] = useState<Record<string, UploadState>>({})
  const updateUpload = (id: string, partial: Partial<UploadState>) =>
    setUploads(prev => ({ ...prev, \[id]: { ...prev\[id], ...partial } }))

TASK 3.2 — XHR Upload with Real Progress
File: frontend/src/lib/api.ts
Add: uploadDocumentWithProgress(file, workspaceId, onProgress) → Promise<UploadResult>
  Uses XMLHttpRequest (not fetch) to track upload progress events.
  xhr.upload.onprogress: calls onProgress(Math.round(e.loaded/e.total\*100))
  Gets presigned URL first; handles local (multipart) and S3 (PUT) paths.
  Sets CSRF token header from getCsrfToken() before upload.
  On error: throws with descriptive message (size limit, type rejection, network).

TASK 3.3 — Document Status Polling
File: frontend/src/lib/api.ts
Add: pollDocumentStatus(docId, onStatusChange, timeoutMs=300000) → () => void (cleanup fn)
  Polls GET /documents/{docId} every 2 seconds.
  Calls onStatusChange(status) on each successful poll.
  Stops polling when status === "READY" or "FAILED".
  Stops after timeoutMs → calls onStatusChange("timeout").
  Returns cleanup function to cancel polling.

Wire in WorkspaceUI.tsx:
  After upload completes → call verifyUpload → get docId → start pollDocumentStatus
  updateUpload(id, {status: "processing"}) → polling → updateUpload per poll event

TASK 3.4 — Drag and Drop Upload
File: frontend/src/components/WorkspaceUI.tsx
  Add isDragging state.
  Handlers on chat area div:
    onDragEnter: if (event.dataTransfer.types.includes("Files")) setIsDragging(true)
    onDragOver: e.preventDefault()
    onDragLeave: check e.relatedTarget to avoid flicker from child element transitions
    onDrop: e.preventDefault(); setIsDragging(false); extract files; filter PDF/DOCX; upload each
  Render drag overlay UI when isDragging per design spec.
  Also: window paste handler for clipboard PDF files.

TASK 3.5 — Duplicate Detection
File: frontend/src/components/WorkspaceUI.tsx
Before starting upload of any file:
  Check if documentList already has a document with same filename AND status "READY".
  If duplicate found:
    Show toast with two inline action buttons:
      "Upload Again" (duration: Infinity until acted on) → proceeds with upload
      "Cancel" → dismisses toast, does NOT upload
    Do NOT start upload until user explicitly chooses "Upload Again".

TASK 3.6 — Wire Document Preview Panel
File: frontend/src/components/WorkspaceUI.tsx
  Add state: const \[previewDoc, setPreviewDoc] = useState<Doc | null>(null)
  Add state: const \[previewPage, setPreviewPage] = useState<number>(1)

  Document bar chip hover:
    Show "👁 Preview" button → onClick: setPreviewDoc(doc); setPreviewPage(1)

  Citation click handler:
    Extract page number from citation data
    setPreviewDoc(citingDocument)
    setPreviewPage(citation.page\_number)

Create: frontend/src/components/DocumentPreviewPanel.tsx
  Wraps EnterpriseDocumentViewer component
  Adds header with: close button (✕), filename, page indicator, zoom controls
  Adds .panel-enter class on mount for slide animation
  Adds "Ask AI about selection" footer button
  Props: { doc: Doc, initialPage: number, onClose: () => void }
  Applies .panel-enter animation class on mount

Render in WorkspaceUI.tsx:
  {previewDoc \&\& (
    <DocumentPreviewPanel
      doc={previewDoc}
      initialPage={previewPage}
      onClose={() => setPreviewDoc(null)}
    />
  )}
  Panel does NOT block the chat area.

TASK 3.7 — pymupdf4llm Integration in Upload Pipeline
File: backend/app/api/v1/endpoints/documents.py
  In the local upload handler (from Phase 0 Task 0.8), after saving the file:
    from app.services.extraction\_router import route\_extraction
    extraction\_result = route\_extraction(storage\_path, workspace\_id)
    if not extraction\_result\["needs\_ocr"]:
      # Native PDF: store extracted text directly, skip OCR queue
      # Update document record with extracted\_text field
      # Set document status to INDEXING (skip PROCESSING → OCR phase)
    else:
      # Scanned PDF: dispatch to Celery OCR task as before
      # Document stays in PROCESSING status

TASK 3.8 — Backend Document Status Endpoint Enhancement
File: backend/app/api/v1/endpoints/documents.py
  Verify GET /documents/{id} returns all expected fields:
    {id, filename, status, workspace\_id, size\_bytes, mime\_type, created\_at, page\_count}
  Status field values MUST match frontend expectations exactly:
    "UPLOADING", "PROCESSING", "INDEXING", "READY", "FAILED"
  Add HEAD /documents/{id}: lightweight polling (no body, status in X-Document-Status header)
    Returns 200 if document exists, 404 if not. Status code unchanged.

─────────────────────────────────────────────────────────────────────
PHASE 3 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
  cd backend \&\& python -c "
  from app.services.extraction\_router import route\_extraction
  print('Extraction router OK')
  "
  cd backend \&\& python -c "from app.main import app; print('App OK')"
  cd frontend \&\& npx tsc --noEmit \&\& echo "TypeScript OK"
  # Manual: drag a PDF onto chat area → drop zone appears → uploads → progress bar shows
  # Manual: upload same file twice → duplicate toast with two options appears
  # Manual: click "👁 Preview" on document chip → panel slides in from right
  # Manual: click a citation in chat → preview panel opens to correct page
  # Manual: upload fails → error badge + retry button appear on doc chip
  # Manual: upload succeeds → status goes uploading → processing → indexing → ready

DEFINITION OF DONE — PHASE 3:
  ✅ Upload progress bar shows actual percentage in real-time
  ✅ Status badge updates: uploading → processing → indexing → ready
  ✅ Drag and drop works with full-area visual overlay
  ✅ Duplicate detection asks user before re-uploading (not silent)
  ✅ PDF preview panel slides in and shows document content
  ✅ Clicking citation opens preview to correct page
  ✅ pymupdf4llm used for native PDFs (confirm method in backend logs)
  ✅ Large file size limit enforced with friendly error message

\[CHECKPOINT 3 COMPLETE — Proceeding to Phase 4]

