# Demo GIF / Video Storyboard — DocuMindAI

**Total Duration:** 35–45 seconds  
**Format:** Screen recording → GIF (README) + MP4 (Devpost/LinkedIn)  
**Resolution:** 1280×720 (720p), or 1920×1080 for MP4  
**Frame rate:** 24fps for MP4, 15fps for GIF  
**Tools:** OBS Studio (record), ScreenToGif / LiceCap (GIF trim), ffmpeg (MP4 export)

---

## Pre-Recording Setup

Before recording, prepare the application:

- [ ] Application running locally at `localhost:3000`
- [ ] Sample documents pre-loaded:
  - A PDF contract (Legal workspace)
  - A research paper PDF (Research workspace)
  - A PDF resume or job description (HR workspace)
- [ ] Browser: Chrome, dark mode enabled, bookmarks bar hidden
- [ ] Window maximized or at 1280×720
- [ ] Clear browser cache / storage for a clean first impression
- [ ] Zoom: 100% (no browser zoom)
- [ ] Disable notifications

---

## Scene-by-Scene Storyboard

---

### Scene 1 — Hero Landing (3 seconds)

**What's on screen:**
- Login or landing page of DocuMindAI
- Dark background, logo centered
- Tagline: *"Enterprise AI Document Intelligence"*

**Action:** Hold still. Gentle cursor appearance.

**Purpose:** Establish brand, professional SaaS appearance.

**Cut:** Hard cut to Scene 2.

---

### Scene 2 — Workspace Selection (2 seconds)

**What's on screen:**
- Dashboard / workspace picker
- Visible workspace icons: General, HR, Legal, Finance, Study, Research, Exam

**Action:** Mouse moves over workspace icons, hover effects visible.

**Purpose:** Show the 7 specialized workspaces exist.

**Cut:** Click on **General** workspace.

---

### Scene 3 — Document Upload (4 seconds)

**What's on screen:**
- General workspace, document panel on the left
- Drag and drop zone or upload button visible

**Action:**
- Click "Upload Document" or drag a PDF into the upload zone
- Progress indicator appears
- File name appears in the document list

**Purpose:** Show file upload is simple and fast.

**Voiceover / subtitle (optional):** *"Upload any document — PDF, DOCX, or image."*

---

### Scene 4 — OCR & Processing (4 seconds)

**What's on screen:**
- Document status shows "Processing…" with spinner or progress bar
- Status transitions from `PROCESSING` → `READY`

**Action:** Watch status update in real time (Celery worker processing).

**Purpose:** Show async processing pipeline is working.

**Voiceover / subtitle (optional):** *"OCR and embedding run automatically in the background."*

---

### Scene 5 — Ask a Question (3 seconds)

**What's on screen:**
- Chat input field at the bottom of the workspace
- Document is selected / active

**Action:**
- Click into the input box
- Type a question relevant to the document (e.g., *"What are the key termination clauses?"*)
- Press Enter

**Purpose:** Show the conversational query interface.

---

### Scene 6 — Streaming Answer (5 seconds)

**What's on screen:**
- Answer begins streaming token-by-token into the chat area
- Text appears word by word, visibly streaming

**Action:** Watch the answer stream live. Do not fast-forward.

**Purpose:** Demonstrate real-time SSE streaming — the most visually striking feature.

**Voiceover / subtitle (optional):** *"Answers stream live from the AI pipeline."*

---

### Scene 7 — Veritas Trust Score (3 seconds)

**What's on screen:**
- Answer is fully rendered
- Veritas Trust Score badge visible (e.g., "Trust Score: 87/100" or a visual gauge)

**Action:** Zoom slightly or hover over the trust score badge to show the tooltip or detail.

**Purpose:** Highlight the differentiating Veritas Trust Engine.

**Voiceover / subtitle (optional):** *"Every answer is scored for trustworthiness — 0 to 100."*

---

### Scene 8 — Source Citations (3 seconds)

**What's on screen:**
- Scroll down or expand the answer
- Citation markers visible (e.g., [Page 12], [Section 3.2])
- Clicking a citation highlights or jumps to the source page in the document viewer

**Action:** Click one citation. Document viewer scrolls to / highlights the referenced passage.

**Purpose:** Show grounded citations — not just answers, but verifiable sources.

**Voiceover / subtitle (optional):** *"Every claim links back to the exact page it came from."*

---

### Scene 9 — Proactive Insights (3 seconds)

**What's on screen:**
- Proactive Insights panel on the right side (or a dedicated section)
- Auto-generated findings from the uploaded document (e.g., "3 high-risk clauses detected")

**Action:** Scroll to or expand the Proactive Insights panel.

**Purpose:** Show that insights appear without any query — on upload.

**Voiceover / subtitle (optional):** *"Critical findings surface automatically — no question needed."*

---

### Scene 10 — Export Report (4 seconds)

**What's on screen:**
- Export button visible in the toolbar
- Click Export → "Download DOCX" or similar option
- Download animation / toast notification

**Action:** Click export, show a brief file download indicator.

**Purpose:** Show the export engine capability.

**Voiceover / subtitle (optional):** *"Export formatted reports in one click."*

---

### Scene 11 — Second Workspace: HR (3 seconds)

**What's on screen:**
- Navigate to HR workspace
- Candidate ranking panel or job-match scores visible

**Action:** Brief pan across the HR workspace UI.

**Purpose:** Show workspace specialization — this isn't one-size-fits-all.

---

### Scene 12 — Closing Logo (3 seconds)

**What's on screen:**
- Fade to dark
- Centered: `🧠 DocuMindAI`
- Subtitle: *"Enterprise AI Document Intelligence"*
- GitHub URL: `github.com/kanwa2006/DocuMindAI`

**Action:** Hold 2–3 seconds. Fade out.

**Purpose:** Brand close, memorable ending.

---

## Scene Summary Table

| # | Scene | Duration | Key Visual |
|---|-------|----------|------------|
| 1 | Hero Landing | 3s | Login / landing page |
| 2 | Workspace Selection | 2s | 7 workspace icons |
| 3 | Document Upload | 4s | Drag-drop + file list |
| 4 | OCR Processing | 4s | Status → READY |
| 5 | Ask a Question | 3s | Chat input + query |
| 6 | Streaming Answer | 5s | Live token streaming |
| 7 | Veritas Trust Score | 3s | Score badge |
| 8 | Source Citations | 3s | Citation → document |
| 9 | Proactive Insights | 3s | Auto-surfaced findings |
| 10 | Export Report | 4s | DOCX download |
| 11 | HR Workspace | 3s | Candidate ranking |
| 12 | Closing Logo | 3s | Brand close |
| **Total** | | **~40s** | |

---

## Post-Processing Recommendations

### GIF (for README)
- Duration: 20–25s max (shorter = smaller file)
- Cut to scenes: 3, 5, 6, 7, 8, 12 for a compact README GIF
- Tool: ScreenToGif or Gifox (macOS)
- Target size: < 5MB for GitHub rendering
- Optimize: Use LiceCap or ezgif online optimizer

### MP4 (for Devpost, LinkedIn, YouTube)
- Full 40-second version
- Add optional voiceover or background music (royalty-free)
- Add captions / subtitles per scene
- Export: 1280×720 H.264, bitrate ~3000kbps
- Tool: OBS → ffmpeg for compression

### Subtitle track
If adding subtitles for LinkedIn:
```
[0:03] Upload any document
[0:11] Watch answers stream in real time
[0:16] Veritas Trust Score — 0 to 100
[0:19] Every answer cites its exact source page
[0:22] Insights surface automatically on upload
[0:26] Export formatted reports instantly
```

---

## Screenshot Captures During Recording

While recording, pause and capture full-resolution screenshots at:
- Scene 6 (streaming answer) — best general workspace screenshot
- Scene 7 (trust score visible) — best "differentiation" screenshot
- Scene 8 (citation highlighted) — best technical depth screenshot
- Scene 11 (HR workspace) — best workspace diversity screenshot

These become the screenshots in the README and Devpost gallery.
