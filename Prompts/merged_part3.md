
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4 — RETRIEVAL QUALITY + CHAT INTERFACE POLISH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Real CrossEncoder reranker. Conversation history in LLM context.
         Streaming cursor. Confidence badges. Stop/Regenerate. Workspace
         disclaimers. Follow-up suggestions. The chat interface must feel
         fast, responsive, and trustworthy.
ESTIMATED TIME: 4–5 hours | RISK: Medium | DEPENDS ON: Phase 3 complete

SCAN FIRST:
  backend/app/services/reranker_service.py   ✓/✗/⚠
  backend/app/api/v1/endpoints/query.py      ✓/✗/⚠
  backend/app/core/config.py                 ✓/✗/⚠ [READ ONLY — ADD only]
  frontend/src/components/WorkspaceUI.tsx    ✓/✗/⚠

─────────────────────────────────────────────────────────────────────
PHASE 4 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

CHAT AREA FULL SPEC:
  Container: flex column, fills available height, overflow-y auto, smooth scroll
  Padding: 0 32px desktop, 0 16px mobile
  Max content width: 760px centered within available space

  USER MESSAGE (.message-user):
    Align: right (align-self flex-end)
    Max width: 75% of container
    Background: var(--brand), color: white
    Border-radius: 16px 16px 4px 16px
    Padding: 12px 16px
    Font: .text-body (14px, leading-relaxed)
    Timestamp: 11px DM Sans, white/60%, below message, right-aligned,
               visible on hover only (opacity 0 → 1, 100ms)

  AI MESSAGE BLOCK (.message-ai):
    Align: left, full width, max-width 72ch
    No bubble background — clean reading surface
    Padding: 16px 0

    AI label row (above content):
      [DocuMindAI LogoMark 16px] [DM Sans 12px "DocuMindAI" text-tertiary]
      [Workspace badge small]
      Example: "DocuMindAI · Teacher Workspace"

    Content (.text-response, 15px leading-loose):
      Rendered Markdown: headers, bold, italic, lists, code blocks, tables
      Code blocks: JetBrains Mono 13px, var(--surface-sunken),
                   border var(--border-subtle), radius 8px, padding 16px
      Tables: full-width, border-collapse, alternating row backgrounds
              (odd: surface-base, even: surface-sunken)

    Streaming state:
      .streaming-cursor class on last text element while streaming
      Blinking ▍ cursor in var(--brand) at end of text
      "DocuMindAI is thinking..." label (12px text-tertiary, italic)
        if no tokens arrive after 1.5 seconds

    Citations row (below content, 8px gap above):
      Label: "Sources:" — 11px text-tertiary uppercase
      Citation chips (.citation-chip) for each unique source:
        Format: "📄 filename.pdf p.4" — 11px mono
        Hover: border-brand, background brand-ghost
        Click: opens document preview panel at that page

    Confidence badge (inline with citations):
      confidence ≥ 0.85 → <span class="badge badge-success">✓ High Confidence</span>
      confidence ≥ 0.70 → <span class="badge badge-warning">~ Moderate Confidence</span>
      confidence ≥ 0.50 → <span class="badge badge-error">⚠ Low Confidence — verify</span>
      confidence <  0.50 → <span class="badge badge-error">⚠ Please verify answer</span>

    Actions row (appears on hover, opacity 0 → 1, 100ms transition):
      Small ghost buttons in a row (.btn-ghost .btn-sm, 28px height):
        📋 Copy — copies response text to clipboard; icon changes to ✓ for 2s
        🔄 Regenerate — only on LAST AI message; re-runs last user query
        👍 Helpful — thumbs up feedback
        👎 Not Helpful — thumbs down + optional text input popup

    Workspace disclaimers (Legal, Finance only) — ALWAYS VISIBLE, NEVER DISMISSABLE:
      Full-width amber banner BELOW actions row:
      Background: var(--warning-bg), border: 1px var(--warning-border), radius: 8px
      Padding: 8px 12px, font: 12px DM Sans var(--warning-text), italic
      Icon: ⚠ 12px at start
      Legal:   "⚠ This analysis is AI-generated for informational purposes only.
                It does not constitute legal advice. Always consult a qualified
                legal professional before acting on any information above."
      Finance: "⚠ All figures are AI-extracted. Verify all numbers against
                original source documents before any financial, tax, or legal use."
      CRITICAL: Backend ALSO appends disclaimer as final chunk before "done" SSE event.
                Frontend detects it by prefix marker and renders in amber banner.

    FOLLOW-UP SUGGESTION CHIPS (below citation row):
      3 small outlined button chips after each AI message (when not streaming):
        Border: var(--border-default), border-radius: 20px, padding: 4px 12px, height: 28px
        Font: .text-body-secondary 13px
        Hover: border-brand, brand text
        On click: prefills textarea AND auto-submits
      Source: from backend response if provided, else from static workspace-aware list:
        General:  ["Summarize the key points", "What are the next steps?", "Explain this further"]
        Legal:    ["What are the key risks?", "Which clauses need attention?", "Compare with standard"]
        Finance:  ["Calculate profitability ratios", "Compare with previous year", "Flag anomalies"]
        HR:       ["Rank all candidates", "Who is the best fit?", "Generate interview questions"]
        Research: ["Find research gaps", "Summarize findings", "Export citations"]
        Student:  ["Quiz me on this", "Create flashcards", "Explain simpler"]
        Teacher:  ["Generate answer key", "Add more questions", "Change difficulty"]

BOTTOM INPUT BAR FULL SPEC:
  Container: fixed at bottom of chat area
  Background: var(--surface-base), padding: 12px 16px
  Border-top: 1px var(--border-subtle)
  Backdrop-filter: blur(8px)

  .chat-input-container (rounded card wrapping textarea + buttons):
    Background: var(--surface-raised)
    Border: 1px var(--border-default), border-radius: 16px
    Box-shadow: var(--shadow-sm)
    Focus-within: border var(--border-strong), shadow var(--shadow-md)
    Padding: 12px 16px

    Textarea (.chat-input):
      Transparent, no border, no outline, resize-none
      Min-height: 44px, max-height: 200px (auto-expand with JS)
      Placeholder: "Ask anything about your documents... (Shift+Enter for new line)"
      Font: DM Sans 14px leading-relaxed
      Shift+Enter: new line in textarea
      Enter (without Shift, not composing): sends message

    Bottom action row (inside container, below textarea):
      Left side:
        📎 Attach button — .btn-icon .btn-ghost 32×32px, opens file picker
        ⊞ Templates button — .btn-icon .btn-ghost, opens template picker dropdown
      Right side:
        Character count: "0 / 4000" — 11px text-tertiary, visible when >80% capacity
        ⌘↵ Send button — .btn .btn-primary, 36px, "Send" label
        While streaming: ⏹ Stop — .btn .btn-secondary (REPLACES Send button)

  Below .chat-input-container — workspace-specific action buttons row:
    Teacher:  [📄 Generate Paper] [📖 Question Bank] [🔑 Answer Key] [🖨 Export DOCX]
    HR:       [📂 Batch Upload] [🎯 Set JD Context] [📊 View Rankings] [📋 Export Candidates]
    Student:  [📖 Study Mode] [🃏 Flashcard Mode] [⏱ Pomodoro Timer] [📊 My Progress]
    Finance:  [🔢 Extraction Mode] [📊 Table Mode] [✅ Verify] [📈 Ratios]
    Research: [🔬 Citation Mode] [📝 Review Mode] [📚 Import Papers] [🔍 Find Gaps]
    Legal:    [⚖ Contract Mode] [🚨 Risk Mode] [📋 Clause Library] [📄 Risk Report]
    General:  (no workspace-specific buttons)
    Each button: .btn .btn-secondary .btn-sm, 32px height

  Below workspace actions — STICKY disclaimer pill (Legal and Finance ONLY):
    "⚠ AI analysis — not legal/financial advice. Always verify with a professional."
    12px, amber background var(--warning-bg), amber text var(--warning-text)
    Always visible in those workspaces, NEVER dismissable

─────────────────────────────────────────────────────────────────────
PHASE 4 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 4.1 — Replace Dummy Reranker with Real CrossEncoder
File: backend/app/services/reranker_service.py
Find DummyLocalReranker class. Replace dummy predict() with:

  class LocalCrossEncoder:
    _model = None  # singleton — loads once, reused forever

    @classmethod
    def get_model(cls):
      if cls._model is None:
        from sentence_transformers import CrossEncoder
        # Downloads ~80MB on first run — expected and normal
        cls._model = CrossEncoder(
          "cross-encoder/ms-marco-MiniLM-L-6-v2",
          max_length=512
        )
      return cls._model

    def rerank(self, query: str, passages: list[str]) -> list[float]:
      model = self.get_model()
      pairs = [[query, p[:512]] for p in passages]
      scores = model.predict(pairs, batch_size=min(16, len(pairs)))
      import numpy as np
      min_s, max_s = scores.min(), scores.max()
      if max_s > min_s:
        normalized = (scores - min_s) / (max_s - min_s)
      else:
        normalized = np.ones_like(scores) * 0.5
      return normalized.tolist()

Update factory in reranker_service.py to return LocalCrossEncoder()
when RERANKER_PROVIDER == "local".

TASK 4.2 — Verify bge-m3 Embedding
File: backend/app/services/embedding_service.py [READ ONLY — minimal change only]
Confirm MODEL_NAME = "BAAI/bge-m3". If not, update ONLY that string.
Add startup logs:
  logger.info(f"[embedding] Using model: {MODEL_NAME}")
  logger.info(f"[embedding] Dimension: {model.get_sentence_embedding_dimension()}")
bge-m3 produces 1024-dim vectors — confirm this in startup logs.

TASK 4.3 — Conversation History in LLM Context
File: backend/app/api/v1/endpoints/query.py
Before LLM call, fetch last 8 messages (4 turns) for the session:
  stmt = (
    select(ChatMessage)
    .where(ChatMessage.session_id == session_id)
    .order_by(ChatMessage.created_at.desc())
    .limit(8)
  )
  result = await db.execute(stmt)
  recent_messages = list(reversed(result.scalars().all()))

  conversation_history = [
    {"role": msg.role, "content": msg.content}
    for msg in recent_messages
    if msg.role in ("user", "assistant")
  ]

Pass conversation_history to the LLM service call.
In llm_service.py: prepend history before RAG prompt:
  history_text = "\n".join([
    f"{m['role'].upper()}: {m['content']}"
    for m in conversation_history[-6:]
  ])
  if history_text:
    full_prompt = f"Previous conversation:\n{history_text}\n\n---\n{rag_prompt}"
  else:
    full_prompt = rag_prompt

TASK 4.4 — Stop Generating Button
File: frontend/src/components/WorkspaceUI.tsx
  const abortControllerRef = useRef<AbortController | null>(null)

  On stream start:
    abortControllerRef.current = new AbortController()
    // pass abortControllerRef.current.signal to the fetch call

  Show ⏹ Stop button ONLY while isStreaming === true (replaces Send button):
    <button
      className="btn btn-secondary btn-sm"
      onClick={() => {
        abortControllerRef.current?.abort()
        setIsStreaming(false)  // keep partial response displayed
      }}
    >⏹ Stop generating</button>

TASK 4.5 — Regenerate Button
File: frontend/src/components/WorkspaceUI.tsx
On the LAST AI message only (when NOT streaming):
  Show 🔄 Regenerate button with opacity-0 → group-hover:opacity-100 (100ms)
  onClick → regenerateLastResponse():
    Remove last AI message from messages state
    Re-send the last user message content
    Stream new response into messages

TASK 4.6 — Real Confidence Badge Display
File: frontend/src/components/WorkspaceUI.tsx
Read confidence from each message's response metadata (backend returns this).
Render below citations using thresholds per design spec above.
Never omit this UI — even absent/0 confidence should show the lowest badge.

TASK 4.7 — Mandatory Workspace Disclaimers
File: backend/app/api/v1/endpoints/query.py
  WORKSPACE_DISCLAIMERS = {
    "legal": (
      "\n\n---\n"
      "⚠️ **Legal Disclaimer**: This analysis is AI-generated for "
      "informational purposes only. It does not constitute legal advice. "
      "Always consult a qualified legal professional before acting on "
      "any information above."
    ),
    "finance": (
      "\n\n---\n"
      "⚠️ **Financial Disclaimer**: All figures are AI-extracted. "
      "Verify all numbers against original source documents before "
      "any financial, tax, or legal use."
    )
  }
  disclaimer = WORKSPACE_DISCLAIMERS.get(workspace_type, "")
  # In streaming: send disclaimer as the final chunk before the "done" SSE event
  # In non-streaming: append to response body

Frontend: detect disclaimer chunk by prefix marker "⚠️ **Legal Disclaimer**"
or "⚠️ **Financial Disclaimer**". Render in amber banner below actions row.
CRITICAL: The persistent bottom-bar disclaimer (always visible) is SEPARATE
from the per-message disclaimer. Both must exist in Legal and Finance workspaces.

TASK 4.8 — Workspace-Specific Retrieval Config
File: backend/app/core/config.py [ADD ONLY — never delete lines]
Add:
  WORKSPACE_RETRIEVAL_CONFIG = {
    "exam":     {"top_k": 8,  "rerank_n": 5,  "chunk_pref": "medium"},
    "hr":       {"top_k": 15, "rerank_n": 10, "chunk_pref": "small"},
    "legal":    {"top_k": 6,  "rerank_n": 4,  "chunk_pref": "large"},
    "finance":  {"top_k": 10, "rerank_n": 6,  "chunk_pref": "small"},
    "research": {"top_k": 12, "rerank_n": 8,  "chunk_pref": "large"},
    "study":    {"top_k": 8,  "rerank_n": 5,  "chunk_pref": "medium"},
    "general":  {"top_k": 8,  "rerank_n": 5,  "chunk_pref": "medium"},
  }

File: backend/app/api/v1/endpoints/query.py
Read config for active workspace:
  ws_config = settings.WORKSPACE_RETRIEVAL_CONFIG.get(
    workspace_type, settings.WORKSPACE_RETRIEVAL_CONFIG["general"])
  chunks = await retrieval_service.retrieve(
    query=query, doc_ids=doc_ids,
    top_k=ws_config["top_k"], rerank_n=ws_config["rerank_n"]
  )

TASK 4.9 — Basic Retrieval Cache (Redis)
File: backend/app/api/v1/endpoints/query.py
Add Redis caching around retrieval (NOT around LLM — retrieval only):
  import hashlib, json

  async def get_cached_retrieval(redis, cache_key):
    try:
      cached = await redis.get(cache_key)
      if cached: return json.loads(cached)
    except Exception:
      pass  # Cache failure → fall through silently; NEVER break the request
    return None

  async def set_cached_retrieval(redis, cache_key, chunks, ttl=300):
    try:
      await redis.setex(cache_key, ttl, json.dumps(chunks))
    except Exception:
      pass  # Cache failure → silently ignore

  # In query handler:
  sorted_doc_ids = sorted(doc_ids)
  query_hash = hashlib.sha256(
    f"{workspace_type}:{query}:{'|'.join(sorted_doc_ids)}".encode()
  ).hexdigest()[:16]
  cache_key = f"retrieval:{workspace_type}:{query_hash}"

  cached = await get_cached_retrieval(redis, cache_key)
  if cached:
    chunks = cached
  else:
    chunks = await retrieval_service.retrieve(...)
    await set_cached_retrieval(redis, cache_key, chunks)

TASK 4.10 — Follow-Up Question Suggestions
File: frontend/src/components/WorkspaceUI.tsx
After each AI message settles (isStreaming becomes false), render 3 suggestion chips.
Use backend-provided suggestions if API returns them; else use static workspace list
as defined in interface design spec above.
On click: set textarea value AND auto-submit (do not just prefill).

TASK 4.11 — Auto-Expanding Textarea
File: frontend/src/components/WorkspaceUI.tsx
Replace any <input type="text"> with <textarea>:
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  <textarea
    ref={textareaRef}
    value={inputValue}
    onChange={(e) => {
      setInputValue(e.target.value)
      e.target.style.height = "auto"
      e.target.style.height = Math.min(e.target.scrollHeight, 200) + "px"
    }}
    onKeyDown={(e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault()
        handleSendMessage()
      }
    }}
    placeholder="Ask anything about your documents... (Shift+Enter for new line)"
    rows={1}
    className="chat-input"
    style={{ height: "44px" }}
  />

─────────────────────────────────────────────────────────────────────
PHASE 4 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
  cd backend && python -c "
  from app.services.reranker_service import LocalCrossEncoder
  r = LocalCrossEncoder()
  scores = r.rerank(
    'what is machine learning',
    ['ML is a subset of AI', 'The sky is blue']
  )
  assert scores[0] > scores[1], 'Relevance ordering wrong!'
  print('Reranker OK:', scores)
  "
  cd frontend && npx tsc --noEmit && echo "TypeScript OK"
  # Manual: send a message → streaming cursor appears (▍ blinks in brand color)
  # Manual: while streaming → ⏹ Stop button visible and functional
  # Manual: hover last AI message → 🔄 Regenerate button appears on hover
  # Manual: legal workspace → amber disclaimer banner always visible
  # Manual: confidence badge shows correct color/label per confidence value
  # Manual: follow-up suggestion chips appear after each AI response
  # Manual: textarea auto-expands to 6 lines max, then scrolls

DEFINITION OF DONE — PHASE 4:
  ✅ CrossEncoder reranker loads and produces correctly ordered scores (not dummy)
  ✅ bge-m3 embeddings confirmed in startup logs (1024 dimensions)
  ✅ Conversation history sent to LLM (visible in backend debug logs)
  ✅ Stop button works and preserves partial response text
  ✅ Regenerate button re-runs last query
  ✅ Confidence badges show correct semantic class per threshold
  ✅ Legal/Finance disclaimers always visible (message-level + persistent bottom)
  ✅ Follow-up suggestion chips appear after each settled AI response
  ✅ Textarea auto-expands up to 200px max height

[CHECKPOINT 4 COMPLETE — Proceeding to Phase 5]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5 — WORKSPACE WELCOME STATES + EMPTY STATES + ONBOARDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PURPOSE: Each workspace has a unique, professional welcome UI when no messages
         exist. First-time users get guided onboarding. Every empty state gives
         the user a clear next action. Nothing should ever be a dead end.
ESTIMATED TIME: 3–4 hours | RISK: Low | DEPENDS ON: Phase 4 complete

─────────────────────────────────────────────────────────────────────
PHASE 5 — INTERFACE DESIGN SPECIFICATION
─────────────────────────────────────────────────────────────────────

SHARED WELCOME STATE STRUCTURE (all workspaces):
  Shown centered in chat area when messages.length === 0
  Max-width: 560px, horizontally centered
  Fade-in animation (.message-enter) on workspace switch (300ms ease-decel)

  Layout (top to bottom):
    1. Workspace icon: 64px emoji, centered
    2. Workspace title: .text-heading-1 (Instrument Serif), centered
    3. Workspace subtitle: .text-body-secondary, centered, margin-top 8px
    4. Badge (if applicable): .badge .badge-brand or workspace-accent pill, centered, margin-top 8px
    5. Disclaimer (Legal/Finance only): amber pill, centered, 13px
    6. Feature highlights (Teacher, HR, Student, Research, Legal, Finance):
       Row of 3 small feature cards below quick actions
       Each: border var(--border-subtle), radius 10px, padding 10px 12px, 12px text-secondary
    7. Quick action buttons: 3 buttons in a row, margin-top 24px
       Each: .btn .btn-secondary, border-radius 20px, 36px height, font 13px
       On click: prefills textarea with prompt AND auto-submits

WORKSPACE WELCOME DEFINITIONS:

  general:
    icon: 💬
    title: "Ask anything about your documents"
    subtitle: "Upload a PDF or DOCX and get instant, cited answers from its content."
    badge: none | disclaimer: none
    quickActions:
      📋 "Summarize this document"
          → "Please provide a comprehensive executive summary with key points highlighted."
      🔍 "Extract key points"
          → "What are the 5 most important points in this document? List them clearly."
      ⚖ "Compare documents"
          → "Compare the uploaded documents and highlight the key differences and similarities."

  exam (Teacher):
    icon: 📋
    title: "Generate Professional Question Papers"
    subtitle: "Upload your syllabus or textbook. AI generates structured, exam-ready papers."
    badge: "OCR Extraction Available" (purple, ws-exam-accent)
    quickActions:
      📝 "Generate Question Paper"
          → "Generate a 100-mark CBSE-style paper from this syllabus with sections A, B, C."
      🗂 "Build Question Bank"
          → "Create a question bank of 50 varied questions covering all topics in this document."
      🔑 "Create Answer Key"
          → "Generate a detailed answer key with marking scheme for all sections."
    featureHighlights:
      [📊 Bloom's Taxonomy tagging] [✅ Mark validation] [🎯 Board templates]

  hr:
    icon: 👥
    title: "Intelligent Candidate Analysis Pipeline"
    subtitle: "Upload resumes + a job description. AI ranks, scores, and extracts insights."
    badge: "Batch Processing — up to 1,000 resumes" (teal, ws-hr-accent)
    quickActions:
      🏆 "Rank All Candidates"
          → "Rank all uploaded candidates for this role with numerical scores and justifications."
      🎯 "Match JD to Resumes"
          → "Compare all resumes against the job description and identify the top 3 matches."
      🗓 "Generate Interview Kit"
          → "Create role-specific interview questions and a scoring rubric for the top candidates."
    featureHighlights:
      [🔍 ATS scoring] [📊 Skills extraction] [📋 Interview kits]

  study (Student):
    icon: 📚
    title: "Your Personal AI Study Partner"
    subtitle: "Upload textbooks and notes. Study smarter, not harder."
    badge: "Supports 30+ PDFs simultaneously" (green, ws-study-accent)
    quickActions:
      🗓 "Create My Study Plan"
          → "Create a personalized study plan for the next 30 days based on this material."
      🃏 "Generate Flashcards"
          → "Generate 20 flashcards for the key concepts in this document."
      🎯 "Quiz Me"
          → "Quiz me with 10 MCQ questions on the material in this document."
    featureHighlights:
      [⏱ Spaced repetition] [📊 Progress tracking] [📝 Formula sheets]

  research:
    icon: 🔬
    title: "Systematic Literature Review & Analysis"
    subtitle: "Upload research papers. AI synthesizes, finds gaps, and formats citations."
    badge: "Citation-grounded — every claim traced to source" (red, ws-research-accent)
    quickActions:
      📑 "Synthesize All Papers"
          → "Provide a synthesis of all uploaded research papers, highlighting consensus and divergence."
      🔍 "Find Research Gaps"
          → "Identify research gaps and unexplored areas across all uploaded papers."
      📚 "Export All Citations"
          → "List all citations from these papers in APA 7th edition format."
    featureHighlights:
      [📖 PRISMA support] [🔗 DOI extraction] [⚡ Multi-paper reasoning]

  legal:
    icon: ⚖
    title: "Contract Analysis & Risk Assessment"
    subtitle: "Upload contracts. AI extracts clauses, flags risks, and maps obligations."
    badge: none
    disclaimer: "⚠ For informational use only — Not legal advice. Always consult a lawyer."
    quickActions:
      📋 "Extract All Clauses"
          → "Extract and categorize all key clauses from this contract with page references."
      🚨 "Risk Analysis"
          → "Identify high-risk clauses. Rate each as Critical/High/Medium/Low with justification."
      📊 "Map Obligations"
          → "Create a complete obligation map for each party with deadlines and conditions."
    featureHighlights:
      [🔴 Risk scoring] [⏰ Deadline extraction] [📋 Clause library]

  finance (CA / Finance):
    icon: 📊
    title: "Financial Document Intelligence"
    subtitle: "Upload P&L, balance sheets, invoices. AI extracts, analyzes, and verifies."
    badge: none
    disclaimer: "⚠ Verify all figures with source documents. Not financial advice."
    quickActions:
      💰 "Extract Key Figures"
          → "Extract all key financial figures with exact page citations and context."
      📈 "Calculate Ratios"
          → "Calculate liquidity, profitability, and solvency ratios using the uploaded statements."
      📅 "Year-on-Year Analysis"
          → "Compare financial performance across all uploaded years with percentage changes."
    featureHighlights:
      [🔢 Numerical validation] [📊 Ratio computation] [🔍 OCR extraction]

EMPTY STATE DESIGNS:

  Sidebar — No sessions (first use):
    Centered SVG illustration (document stack, abstract)
    "No chats yet" — 13px text-secondary
    "Start a new chat →" button — .btn .btn-secondary .btn-sm
    Points to the New Chat button above

  Sidebar — Search no results:
    🔍 icon centered, 32px
    "No sessions matching '[query]'" — 13px text-secondary
    "Clear search" link below — brand blue, 12px

  Document chip — Upload failed:
    Error style on chip, ✗ icon, filename
    Retry button (↺) appears on chip: .btn-icon .btn-ghost .btn-sm
    Tooltip on hover: shows error reason

  Sidebar — Session loading error (getChats() fails):
    ⚠ amber icon, "Couldn't load your chats" — 13px text-secondary
    "Retry" button — .btn .btn-ghost .btn-sm
    NOT just a console error — visible UI with clear retry action
    Error messages by type:
      Network error: "No connection. Check your internet."
      401 error: "Session expired. Please sign in." (link to /login)
      500 error: "Server error. Please try again."
      Timeout: "Taking too long. Try refreshing."

  Chat area — Session started but no documents:
    Centered, document upload icon (📄 or SVG), 48px
    "Upload a document to begin" — .text-body-secondary
    Arrow pointing to document bar and attach button
    Subtle bounce animation on the + Add Documents button

FIRST-TIME ONBOARDING FLOW:
  Detect first-time user: localStorage "onboarding_complete" !== "true"

  Step 1 — Workspace selection:
    Pulsing ring animation on workspace dropdown (box-shadow brand color, CSS keyframes)
    Tooltip bubble below dropdown:
      "Choose your workspace — Teacher, HR, Student, Legal..."
      "Got it →" button → advances to step 2

  Step 2 — Upload a document:
    Pulsing ring on document bar and "+ Add Documents" button
    Tooltip: "Upload your first document — PDF or DOCX"
    "Got it →" → advances to step 3

  Step 3 — Ask a question:
    Pulsing ring on textarea input bar
    Tooltip: "Ask any question about your document — AI will answer from it only"
    "Got it!" → dismisses onboarding entirely

  Progress checklist in sidebar (below New Chat button):
    ✅ Created account
    ⬜ Uploaded a document (complete when documentsUploaded.length > 0)
    ⬜ Asked first question (complete when messagesCount > 0)
    Each item: 12px text, check = brand green
    × dismiss button in corner (sets onboarding_complete = "true")
    Entire checklist disappears when all 3 items complete

─────────────────────────────────────────────────────────────────────
PHASE 5 — IMPLEMENTATION TASKS
─────────────────────────────────────────────────────────────────────

TASK 5.1 — Workspace Welcome States
File: frontend/src/components/WorkspaceUI.tsx
  Define WORKSPACE_CONFIG object with all 7 workspaces:
    { icon, title, subtitle, badge, disclaimer, quickActions[], featureHighlights[] }

  When messages.length === 0: render welcome state from WORKSPACE_CONFIG.
  Apply .message-enter animation class on workspace switch.
  Quick action buttons: onClick → setInputValue(prompt) → auto-submit (handleSendMessage).
  Disclaimer pill: amber background, centered, ⚠ icon prefix.
  Feature highlights row: 3 small info cards, no click action.

TASK 5.2 — All Empty States
File: frontend/src/components/Sidebar.tsx
  Empty state (no sessions OR search no results): per design spec above.
  Loading error state: try/catch around getChats(), show error UI with Retry button.
  Error message varies by HTTP status code (network / 401 / 500 / timeout).

File: frontend/src/components/WorkspaceUI.tsx
  "No documents" empty state in chat area: per design spec above.
  Animated arrow/pulse on + Add Documents button when no documents exist.

TASK 5.3 — Onboarding Flow
Create: frontend/src/components/OnboardingTooltip.tsx
  Props: { step: 1|2|3, targetRef: RefObject<HTMLElement>, onNext: ()=>void, onDismiss: ()=>void }
  Renders: pulsing ring on target element (box-shadow animation, brand color)
  Tooltip bubble: positioned below target, white card with arrow, brand "Got it →" button
  Escape key or click outside → calls onDismiss

Create: frontend/src/hooks/useOnboarding.ts
  Reads localStorage "onboarding_step" and "onboarding_complete"
  Returns: { currentStep: number, advance: ()=>void, dismiss: ()=>void, isComplete: boolean }

Create: frontend/src/components/OnboardingProgress.tsx
  Sidebar checklist, 3 items with ✅/⬜ icons
  Show when !isComplete
  Completion checks:
    Item 1: always complete (user is logged in)
    Item 2: documentsUploaded.length > 0
    Item 3: messagesCount > 0
  × dismiss button: sets onboarding_complete = "true" in localStorage

Wire OnboardingTooltip and OnboardingProgress in LayoutWrapper.tsx,
triggered by useOnboarding hook.

TASK 5.4 — Session Loading Error Handling (Sidebar)
File: frontend/src/components/Sidebar.tsx
  Wrap getChats() call in try/catch block.
  Add state: const [loadError, setLoadError] = useState<string | null>(null)
  On error: determine message from error type, set loadError.
  Render error empty state with specific message + Retry button.
  Retry button: calls getChats() again + clears loadError.
  401 case: show "Session expired" with link to /login (not just "retry").

─────────────────────────────────────────────────────────────────────
PHASE 5 VERIFICATION CHECKPOINT ✓
─────────────────────────────────────────────────────────────────────
  cd frontend && npx tsc --noEmit && echo "TypeScript OK"
  # Manual: open each workspace → unique welcome state renders with correct content
  # Manual: click any quick action button → prompt auto-submits (not just prefills)
  # Manual: Legal workspace welcome → amber disclaimer pill visible
  # Manual: Finance workspace welcome → amber disclaimer pill visible
  # Manual: clear localStorage → onboarding tooltips appear on correct elements
  # Manual: complete all onboarding steps → progress checklist disappears
  # Manual: disable network → sidebar shows typed error message + Retry button
  # Manual: search for non-existent session → shows "No sessions matching" UI

DEFINITION OF DONE — PHASE 5:
  ✅ All 7 workspaces have unique welcome states with correct content
  ✅ Feature highlights row appears for Teacher, HR, Student, Research, Legal, Finance
  ✅ Disclaimers visible in Legal and Finance welcome states (amber pill)
  ✅ Quick action buttons auto-submit prompts (not just prefill)
  ✅ Onboarding tooltip sequence works (3 steps, pulsing ring)
  ✅ Onboarding progress checklist in sidebar with completion tracking
  ✅ Sidebar shows friendly typed error when getChats() fails
  ✅ Empty search state shows "No sessions matching" UI
  ✅ "No documents" state visible when session has no uploads

[CHECKPOINT 5 COMPLETE — Proceeding to Phase 6]
