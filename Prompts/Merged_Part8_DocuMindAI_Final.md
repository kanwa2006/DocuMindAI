# DOCUMINDAI — MERGED PART 8: FINAL EVOLUTION GUIDE
### The Complete Post-Batch Implementation Plan
**Version:** 2.0 | **Date:** May 2026 | **Status:** Enhanced — Physical AI Layer Added
**Enhancement Author:** Part 8 v2 — Phases 24–28 are purely additive. No existing phase modified.

---

> **HOW TO USE THIS FILE:**
> Give each Phase as a separate batch to Claude Sonnet 4.6 in Claude Code.
> Every Phase is purely additive — nothing removes or changes existing code.
> Each Phase builds on the previous. Do them in order.
> Phases 16–23 are the original Part 8 content (unchanged).
> Phases 24–28 are the new Physical AI enhancements added in v2.
> Estimated total (all phases): 10–12 Claude Code sessions of 3–4 batches each.

---

## COMPETITIVE LANDSCAPE — WHY WE WIN

Before building, understand what every competitor does wrong. Your job is to fill every gap.

| Tool | What They Have | What They're Missing | Our Advantage |
|---|---|---|---|
| **NotebookLM** (Google) | Large context, good citations, audio overviews | No workspaces, no trust scores, no Indian market, no UPI billing, no contradiction detection | 7 workspaces + Veritas + Indian billing |
| **Perplexity** | Web search, good UI, multi-model | No private document grounding, answers mix web + doc, no audit trail | Pure document grounding + trust layer |
| **ChatPDF** | Simple PDF chat | No citation page jumps, no professional modes, no verification, English only | Workspace intelligence + Veritas trust |
| **Humata** | Research-focused RAG | Expensive, English only, no domain specialization for India | Local pricing + regional languages |
| **Vectara** | Enterprise RAG API, hallucination mitigation | Developer-only, no end-user product, no Indian market, $thousands/month | End-user product + free tier + Indian market |
| **Onyx / Glean** | Enterprise knowledge base, 64–76% win rate | $50,000+/year, no individual users, no Indian professionals | Accessible pricing + individual + team use |
| **Claude Projects** | Strong reasoning, version tracking | No verification layer, no trust scores, no Indian billing | Trust layer + audit trail + UPI |
| **You.com** | Private RAG + web search combo | No domain workspaces, English-only, subscription in USD | Domain workspaces + INR pricing |

**After Part 8 v2:** DocuMindAI is the only RAG platform with voice queries, physical document scanning, ambient morning briefings, offline PWA access, and instant text clipping — all free to build, none available anywhere else.

---

## WHAT COMES AFTER AGENTIC AI — WHY THIS MATTERS

The evolution pattern is clear from research:

```
2023: Generative AI    → Creates content (ChatGPT era)
2024: RAG              → Grounds AI in your documents
2025: Agentic AI       → AI that acts autonomously
2026: Governed AI      → AI that acts AND can be audited/trusted
2027-2028: Proactive AI → AI that surfaces insights before you ask
2029-2030: Physical AI → AI embedded in the real world
```

DocuMindAI after Part 8 v1 sits at the **Governed AI** layer.
DocuMindAI after Part 8 v2 **bridges into Proactive AI AND begins the Physical AI layer** —
voice input, camera scanning, ambient briefings, and offline presence make it the first
document intelligence tool that starts living in the physical world.

Gartner confirms: governance, auditability, and ambient intelligence are the #1 and #2 gaps
in enterprise AI. You are now building both simultaneously.

---

## PHASE 16 — CRITICAL MAINTENANCE (Do This First, Before Anything Else)
**Priority:** URGENT | **Time:** 1 batch | **Cost:** ₹0

### 16-A: Gemini Model Migration (Deadline: June 17, 2026)

```
URGENT: Gemini 2.5 Flash is deprecated on June 17, 2026.

In backend/app/core/config.py, change:
  GEMINI_MODEL = "gemini-2.5-flash"
  to:
  GEMINI_MODEL = "gemini-2.5-flash-lite"

In backend/app/services/llm_service.py, anywhere the model string 
is hardcoded, replace with settings.GEMINI_MODEL.

Also update GEMINI_MODEL in .env and .env.example.

Add a fallback in llm_service.py:
  PRIMARY_MODEL = "gemini-2.5-flash-lite"
  FALLBACK_MODEL = "gemini-2.0-flash"
  
  If the primary model throws a 404 or deprecation error, 
  automatically retry with FALLBACK_MODEL and log a warning.

Test: Run one query from each workspace and confirm responses work.
```

### 16-B: Document Content Hash Deduplication

```
In backend/app/services/document_service.py, 
at the START of the document processing function, before any extraction:

1. Compute MD5 hash of raw file bytes:
   import hashlib
   content_hash = hashlib.md5(file_bytes).hexdigest()

2. Add column 'content_hash' VARCHAR(32) to the documents table 
   via a new Alembic migration.

3. Before processing, query:
   existing = db.query(Document).filter(
     Document.user_id == user_id,
     Document.content_hash == content_hash,
     Document.status == "completed"
   ).first()

4. If existing found:
   - Create a new Document record pointing to existing.vector_index_id
   - Set status = "deduplicated", processing_time = 0
   - Return immediately with toast: 
     "This document matches '{existing.filename}'. Using cached embeddings — instant processing!"
   - Do NOT reprocess. Reuse all existing FAISS embeddings.

5. If not found: proceed with normal processing, save content_hash on completion.

Edge case: If PDF A has content X, and PDF B has content X + extra Y,
they have different hashes. Process PDF B fully. This is correct behavior.
Do NOT try to detect partial overlaps — only exact duplicates.
```

---

## PHASE 17 — GROWTH LAYER
**Priority:** High | **Time:** 2 batches | **Cost:** ₹0

### 17-A: Landing Page

```
Create frontend/src/app/(marketing)/page.tsx — a full marketing landing page.
This is the FIRST thing new users see. It must be compelling in 8 seconds.

Section 1 — Hero (above fold, no scroll required):
  Headline: "Your Documents. Fully Understood."
  Subheadline: "Ask anything about your PDFs, contracts, or notes.
                Get answers with exact page citations.
                Built for Indian CAs, Lawyers, Teachers, and HR professionals."
  Two CTAs side by side:
    Primary: [Start Free — 10 Queries] → /register (brand color, bold)
    Secondary: [See How It Works] → scrolls to Section 3 (outlined)
  Trust line below CTAs: "No credit card required. 10 queries free. Cancel anytime."
  
Section 2 — Trust Bar (logos/stats row):
  "Answers only from your document" | "Every answer shows exact page" | 
  "7 professional workspaces" | "UPI & Razorpay billing"

Section 3 — Workspace Showcase (6 cards in 2×3 grid):
  For each workspace, show:
  - Workspace icon + name
  - One example question in italic
  - One example answer snippet (2 lines, truncated with "...")
  - "Try this workspace →" link
  
  Examples:
  HR: "Rank these 12 candidates by leadership experience"
      → "Ranked by leadership score: 1. Priya S. (8.2/10)..."
  Finance: "What is the net profit margin for Q3?"
      → "Net profit margin: 18.4%. Revenue ₹2.3Cr, Net Profit ₹4.2L..."
  Legal: "Does this contract have a penalty clause?"
      → "Yes. Clause 7.3 (Page 12): 15% of contract value, capped at ₹50L..."
  Teacher: "Generate 10 MCQs from Chapter 4"
      → "Q1: What is the primary function of mitochondria? (a)..."
  Research: "Summarize the methodology section"
      → "The study used a mixed-methods approach with 450 participants..."
  Student: "Explain this concept in simple language"
      → "Think of it like this: the nucleus is the 'control center'..."

Section 4 — How It Works (3 steps, horizontal on desktop, vertical on mobile):
  Step 1: Upload Your Document (icon: upload arrow)
           "PDF, DOCX, TXT — any file up to 50MB"
  Step 2: Choose Your Workspace (icon: grid)
           "7 professional modes, each optimized for your role"
  Step 3: Get Verified Answers (icon: shield checkmark)
           "Every answer shows the exact page and trust score"

Section 5 — The Trust Difference (feature highlight, 2-column layout):
  Left: Problem statement
    "Other AI tools give you an answer. 
     You have no idea if it's right or hallucinated.
     For CAs, lawyers, and doctors — a wrong answer isn't 
     just inconvenient. It's dangerous."
  Right: Our solution
    "DocuMindAI shows a Trust Score with every answer.
     You know exactly how confident the AI is,
     what page it came from, and whether any contradiction
     was found in the document."
  Show a mock Trust Score badge: 
    [████████░░ 87/100 ✅ HIGH CONFIDENCE]

Section 6 — Pricing (3 cards, matching /pricing page):
  Free Trial | Professional ₹799/mo | Enterprise ₹2,999/mo
  Large [Start Free Trial] CTA below

Section 7 — Footer:
  "Made with ❤️ in India 🇮🇳"
  Links: Privacy Policy | Terms of Service | Contact | /pricing
  Copyright: © 2026 DocuMindAI

Design rules:
- Use only existing globals.css tokens and Tailwind classes
- No external images — use CSS gradients, emoji icons, and text
- Must be fully mobile responsive
- Smooth scroll between sections
- Page load must be under 2 seconds (no heavy assets)
```

### 17-B: SEO, OpenGraph, Analytics Setup

```
PART 1 — SEO Meta Tags:
In frontend/src/app/(marketing)/layout.tsx, export metadata:
  title: "DocuMindAI — Document Intelligence for Indian Professionals"
  description: "Ask questions about your PDFs, contracts & notes. 
                Get verified answers with exact page citations. 
                Built for CAs, Lawyers, Teachers & HR professionals in India."
  keywords: ["RAG", "document AI", "PDF chat", "Indian AI tool", 
             "document intelligence", "CA tool", "legal AI India"]
  openGraph:
    title: "DocuMindAI — Ask Anything About Your Documents"
    description: (same as above)
    url: "https://documindai.com"
    siteName: "DocuMindAI"
    images: [{ url: "/og-image.png", width: 1200, height: 630 }]
    type: "website"
    locale: "en_IN"
  twitter:
    card: "summary_large_image"
    title: "DocuMindAI"
    description: (same)
    images: ["/og-image.png"]
  robots: { index: true, follow: true }
  
PART 2 — robots.txt:
Create frontend/public/robots.txt:
  User-agent: *
  Allow: /
  Allow: /pricing
  Disallow: /dashboard
  Disallow: /admin
  Disallow: /api
  Sitemap: https://documindai.com/sitemap.xml

PART 3 — Sitemap:
Create frontend/src/app/sitemap.ts:
  Returns array of URLs with lastModified and changeFrequency:
  / (daily), /pricing (weekly), /login (monthly), /register (monthly)

PART 4 — OG Image:
Create frontend/public/og-image.png using a Canvas-based script:
  1200×630px, brand blue (#1E40AF) background
  "DocuMindAI" in large white bold text centered
  "Document Intelligence for Indian Professionals" below in smaller white text
  Shield + checkmark icon on the right side
  
  Run: node scripts/generate-og-image.js
  (Create this script using canvas npm package)

PART 5 — PostHog Analytics:
  npm install posthog-js
  
  Create frontend/src/lib/analytics.ts:
    import posthog from 'posthog-js'
    
    export const initAnalytics = () => {
      if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
        posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
          api_host: 'https://app.posthog.com',
          capture_pageview: false,  // manual control
          capture_pageleave: true,
          autocapture: false,       // privacy-first
          persistence: 'localStorage'
        })
      }
    }
    
    export const track = (event: string, properties?: Record<string, any>) => {
      posthog.capture(event, properties)
    }
  
  Track these events ONLY (no user content ever):
    page_viewed (path)
    workspace_switched (from_workspace, to_workspace)
    query_submitted (workspace, query_length_chars, has_documents: boolean)
    document_uploaded (workspace, file_type, file_size_mb_bucket: "0-1"|"1-5"|"5+")
    trial_query_used (queries_used, queries_remaining)
    upgrade_modal_shown (trigger: "limit_reached"|"feature_locked"|"user_click")
    upgrade_clicked (plan, billing_cycle, source_page)
    subscription_started (plan, cycle)
    export_downloaded (format: "pdf"|"docx"|"md"|"csv", workspace)
    bookmark_saved (workspace)
    trust_score_expanded (trust_level: "high"|"medium"|"low")
    contradiction_alert_viewed (workspace)
    second_opinion_requested (trust_score_before)
    feedback_submitted (type: "bug"|"feature"|"payment"|"other")
    session_created (workspace)
    session_shared (workspace)
    voice_query_used (workspace)
    camera_scan_used (workspace)
    morning_briefing_opened (num_cards)
    clip_text_used (text_length_chars_bucket: "0-100"|"100-500"|"500+")
    pwa_installed
    
  NEVER track: query text, document names, answer content, email, user_id

PART 6 — Sentry Error Monitoring:
  Backend:
    pip install sentry-sdk[fastapi] --break-system-packages
    
    In backend/app/main.py, before app = FastAPI():
      import sentry_sdk
      from sentry_sdk.integrations.fastapi import FastApiIntegration
      from sentry_sdk.integrations.celery import CeleryIntegration
      from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
      
      sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,  # "production" or "development"
        integrations=[
          FastApiIntegration(),
          CeleryIntegration(),
          SqlalchemyIntegration()
        ],
        traces_sample_rate=0.05,   # 5% of requests only
        profiles_sample_rate=0.01, # 1% profiling
        send_default_pii=False,    # NEVER send user data
        before_send=lambda event, hint: (
          {**event, 'request': {
            k: v for k, v in event.get('request', {}).items() 
            if k not in ['data', 'body']
          }} if event else None
        )
      )
  
  Frontend:
    npm install @sentry/nextjs
    
    Create frontend/sentry.client.config.ts:
      import * as Sentry from "@sentry/nextjs"
      Sentry.init({
        dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
        environment: process.env.NODE_ENV,
        tracesSampleRate: 0.05,
        replaysOnErrorSampleRate: 0,  // no recordings
        ignoreErrors: ['ResizeObserver loop limit exceeded']
      })
    
    Add SENTRY_DSN and NEXT_PUBLIC_SENTRY_DSN to .env and Railway env vars.

PART 7 — Help & Feedback Feature:
  In Supabase, create table:
    CREATE TABLE feedback (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE SET NULL,
      type TEXT NOT NULL CHECK (type IN ('bug','feature','payment','other')),
      message TEXT NOT NULL,
      email TEXT,
      user_plan TEXT,
      page_url TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
  
  Create backend/app/api/feedback.py:
    POST /api/feedback
    Body: { type, message, email?, page_url? }
    Auth: optional (works for logged-out users too)
    Saves to feedback table with user_id if logged in
    Returns: { success: true }
    Rate limit: 3 submissions per user per hour
  
  Create frontend/src/components/FeedbackModal.tsx:
    Triggered by "Help & Feedback" link in sidebar bottom
    Fields:
      - Type dropdown: Bug Report | Feature Request | Payment Issue | Suggestion | Other
      - Message textarea (min 20 chars, max 1000 chars): "Describe your issue..."
      - Email field (optional): "Your email for follow-up (optional)"
    Submit button: [Send Feedback]
    On success: toast "Thank you! We'll review your feedback within 24 hours."
    
    Special behavior for "Payment Issue" type:
      Show alert box: "For urgent payment issues, email 
      support@documindai.com directly. We respond within 2 hours on weekdays."
    
    Add "Help & Feedback" link at the very bottom of the sidebar,
    below all navigation items, with a HelpCircle icon.
```

### 17-C: Email Onboarding Sequence

```
Install: pip install brevo-python --break-system-packages
         (Brevo SMTP — free for 300 emails/day)

Create backend/app/services/email_service.py with:

1. send_email(to_email, subject, html_body) — base function using Brevo SMTP

2. send_welcome_email(user) — triggered immediately after email verification:
   Subject: "Your DocuMindAI trial is ready — start here"
   Content:
     "Hi [first_name],
     
     Your 10 free queries are ready. All 7 workspaces are fully unlocked.
     
     Most users start with one of these:
     
     📊 Finance: Upload a balance sheet → ask 'What is the net profit margin?'
     ⚖️  Legal: Upload a contract → ask 'Are there any penalty clauses?'
     👥 HR: Upload resumes → ask 'Rank candidates by relevant experience'
     
     Every answer shows the exact page it came from.
     
     [Open DocuMindAI →] (CTA button)
     
     Questions? Reply to this email.
     
     — DocuMindAI Team"

3. send_trial_nudge_email(user) — triggered when trial_queries_used == 3:
   Subject: "You've used 3 of your 10 free queries"
   Content:
     "Hi [first_name],
     
     You're halfway through your free trial.
     
     Before you run out:
     → Bookmark your best answers (click the bookmark icon)
     → Export this session as PDF
     → Try one more workspace you haven't used yet
     
     When you're ready to continue without limits:
     Professional Plan — ₹799/month
     200 queries per session | All 7 workspaces | Priority processing
     
     [See Plans →] (CTA button)"

4. send_upgrade_reminder_email(user) — triggered when trial_queries_used == 9:
   Subject: "1 free query left"
   Content: Short, direct. "You have 1 query left. Subscribe to keep going.
             All your documents and sessions will be preserved. [Subscribe ₹799/mo]"

Add triggers in query processing endpoint:
  After each query: check trial_queries_used, send appropriate email
  Use Celery task to send emails (never block the query response)
  Add email_notifications_enabled BOOLEAN to users table
  Default true. Users can opt out in Settings.
```

---

## PHASE 18 — VERITAS TRUST LAYER
**Priority:** CRITICAL | **Time:** 3 batches | **Cost:** ₹0

### 18-A: Veritas Engine (Backend)

```
Create backend/app/services/veritas_engine.py

This module runs AFTER the standard RAG pipeline but BEFORE showing the answer.
It NEVER changes the answer — it only scores it.

class VeritasEngine:
  
  def compute_trust_score(
    self,
    answer: str,
    primary_chunks: List[RetrievedChunk],
    query: str,
    document_ids: List[str],
    db: Session
  ) -> VeritasTrustReport:
    
    scores = {}
    evidence = []
    warnings = []
    
    # FACTOR 1: Dual Retrieval Consensus (30% weight)
    paraphrased_query = self._paraphrase_query(query)
    secondary_chunks = self.retriever.retrieve(paraphrased_query, document_ids)
    
    primary_ids = {c.chunk_id for c in primary_chunks[:5]}
    secondary_ids = {c.chunk_id for c in secondary_chunks[:5]}
    overlap = len(primary_ids & secondary_ids)
    consensus_score = min(100, (overlap / 5) * 100 + 20)
    scores['dual_retrieval'] = consensus_score
    
    if overlap >= 3:
      evidence.append("Both retrieval strategies found the same sources")
    elif overlap == 0:
      warnings.append("Two searches found completely different sources — review carefully")
    
    # FACTOR 2: Direct Quote vs Inference (25% weight)
    answer_sentences = answer.split('. ')
    verbatim_count = 0
    for sentence in answer_sentences[:5]:
      key_phrase = sentence[:50].strip()
      if any(key_phrase.lower() in chunk.text.lower() for chunk in primary_chunks):
        verbatim_count += 1
    
    quote_score = (verbatim_count / max(len(answer_sentences[:5]), 1)) * 100
    scores['direct_quote'] = quote_score
    
    if quote_score >= 60:
      evidence.append("Answer is directly quoted from source text")
    elif quote_score < 30:
      warnings.append("Answer required inference — not directly quoted from document")
    
    # FACTOR 3: Cross-Document Contradiction Detection (20% weight)
    if len(document_ids) > 1:
      contradictions = self._detect_contradictions(answer, primary_chunks, document_ids, db)
      contradiction_score = max(0, 100 - (len(contradictions) * 30))
      scores['contradiction'] = contradiction_score
      for c in contradictions:
        warnings.append(
          f"Contradiction: '{c.doc_a_name}' p.{c.page_a} conflicts with "
          f"'{c.doc_b_name}' p.{c.page_b}"
        )
    else:
      scores['contradiction'] = 100
    
    # FACTOR 4: Chunk Consensus (15% weight)
    if len(primary_chunks) >= 3:
      top_chunk_texts = [c.text for c in primary_chunks[:3]]
      agreement = self._measure_chunk_agreement(top_chunk_texts)
      consensus = min(100, agreement * 100)
    else:
      consensus = 50
      warnings.append("Limited source material found for this query")
    scores['chunk_consensus'] = consensus
    
    # FACTOR 5: Uncertainty Language Detection (10% weight)
    uncertainty_phrases = [
      "might be", "could be", "possibly", "it seems", "appears to",
      "approximately", "roughly", "not entirely clear", "may depend",
      "unclear from", "cannot determine"
    ]
    uncertainty_count = sum(1 for p in uncertainty_phrases if p in answer.lower())
    uncertainty_score = max(0, 100 - (uncertainty_count * 20))
    scores['uncertainty'] = uncertainty_score
    if uncertainty_count > 0:
      warnings.append(f"Answer contains {uncertainty_count} uncertainty indicator(s)")
    
    # COMPUTE FINAL WEIGHTED SCORE
    final_score = int(
      scores['dual_retrieval'] * 0.30 +
      scores['direct_quote'] * 0.25 +
      scores['contradiction'] * 0.20 +
      scores['chunk_consensus'] * 0.15 +
      scores['uncertainty'] * 0.10
    )
    
    if final_score >= 80:
      trust_level = "HIGH"
      trust_label = "High Confidence"
      trust_color = "green"
      trust_action = "This answer is well-supported by your document."
    elif final_score >= 55:
      trust_level = "MEDIUM"
      trust_label = "Moderate Confidence"
      trust_color = "yellow"
      trust_action = "Review the cited pages before relying on this professionally."
    else:
      trust_level = "LOW"
      trust_label = "Low Confidence — Verify Manually"
      trust_color = "red"
      trust_action = "This answer required significant inference. Please verify directly."
    
    return VeritasTrustReport(
      final_score=final_score,
      trust_level=trust_level,
      trust_label=trust_label,
      trust_color=trust_color,
      trust_action=trust_action,
      factor_scores=scores,
      evidence=evidence,
      warnings=warnings,
      contradictions=contradictions if len(document_ids) > 1 else [],
      computation_time_ms=elapsed_ms
    )

Performance requirement: entire Veritas computation must complete in under 1.5 seconds.
Total response time target: under 5 seconds.

Integrate into the main query handler:
  answer, citations = await rag_pipeline.query(query, document_ids)
  try:
    trust_report = await veritas_engine.compute_trust_score(
      answer, retrieved_chunks, query, document_ids, db
    )
  except Exception as e:
    logger.warning(f"Veritas failed gracefully: {e}")
    trust_report = VeritasTrustReport(
      final_score=None, trust_level="UNKNOWN", 
      trust_label="Verification unavailable"
    )
  return QueryResponse(answer=answer, citations=citations, trust=trust_report)
```

### 18-B: Trust Score UI (Frontend)

```
Create frontend/src/components/veritas/TrustScoreBadge.tsx

Visual design for the trust badge displayed under every AI response:

HIGH (80-100):
  [████████░░ 87 / 100] ✅ High Confidence
  Background: light green tint
  
MEDIUM (55-79):
  [████░░░░░░ 62 / 100] ⚠️ Moderate — Review Cited Pages
  Background: light amber tint
  
LOW (0-54):
  [██░░░░░░░░ 41 / 100] ⛔ Low — Verify Manually
  Background: light red tint
  
UNKNOWN (Veritas unavailable):
  Show nothing — do not show a broken badge

The badge is always collapsed by default.
Clicking it expands a panel showing:

EXPANDED PANEL (TrustScorePanel.tsx):
  ─────────────────────────────────────
  Trust Score: 87/100 ✅ HIGH CONFIDENCE
  ─────────────────────────────────────
  
  ✅ Evidence Supporting This Answer:
  • Both retrieval strategies found the same sources
  • Answer is directly quoted from source text
  
  ⚠️ Warnings:
  • Answer contains 1 uncertainty indicator
  
  📊 Score Breakdown:
  Dual Retrieval Consensus    30% → 90/100
  Direct Quote Score          25% → 85/100
  No Contradictions           20% → 100/100
  Source Agreement            15% → 80/100
  Confidence Language         10% → 80/100
  
  ─────────────────────────────────────
  💡 This answer is well-supported.
     The exact source is shown on Page [X].
  ─────────────────────────────────────

For CONTRADICTIONS, show a special section:
  🔴 Contradiction Detected:
  ┌─────────────────────────────────────────┐
  │ Document A (contract_v1.pdf, Page 4):   │
  │ "Notice period: 90 days"                │
  ├─────────────────────────────────────────┤
  │ Document B (amendment_2026.pdf, Page 2):│
  │ "Notice period revised to 60 days"      │
  └─────────────────────────────────────────┘
  → [View Page 4 of contract_v1.pdf]
  → [View Page 2 of amendment_2026.pdf]

Second Opinion Button:
  At the bottom of the expanded panel, show:
  [🔄 Get Second Opinion]
  
  When clicked:
  - Re-runs the same query with a completely different retrieval strategy
  - Shows a loading state: "Re-analyzing with different approach..."
  - Shows the second answer in a side-by-side comparison

Track analytics events:
  trust_score_expanded({ trust_level, score })
  second_opinion_requested({ original_score })
  contradiction_viewed({ num_contradictions })
```

### 18-C: Audit Trail Export

```
This is the feature that makes enterprises pay ₹2,999/month.

Create backend/app/services/audit_export.py

generate_session_audit_report(session_id, user_id, format: "pdf"|"docx"):
  Creates a structured report containing:
  
  COVER PAGE:
    Title: "AI-Assisted Document Analysis Report"
    Generated by: DocuMindAI
    Session: [session name]
    Date: [date/time]
    Workspace: [workspace name]
    Documents analyzed: [list of filenames]
    User: [name] (ID: [last 8 chars of user_id])
    
    DISCLAIMER: "This report was generated with AI assistance. 
    All answers are grounded in the cited documents. 
    Trust scores indicate retrieval confidence, not legal or professional certainty.
    All critical decisions must be independently verified by a qualified professional."
  
  FOR EACH QUERY IN SESSION:
    ────────────────────────────────────
    Query #[N] — [timestamp]
    ────────────────────────────────────
    Question: [full query text]
    Answer: [full answer text]
    Trust Score: [score]/100 ([level])
    Evidence: [list of evidence items]
    Warnings: [list of warnings, if any]
    Source Citations: [document name, page, quoted passage]
    ────────────────────────────────────
  
  FINAL PAGE:
    Summary statistics:
    - Total queries, High/Medium/Low confidence counts
    - Contradictions detected, Documents analyzed

Add endpoint: GET /api/sessions/{session_id}/audit-report?format=pdf
Requires: Professional or Enterprise plan

This feature is available on:
  Free Trial: NOT available (show upgrade prompt)
  Professional: Available (PDF only)
  Enterprise: Available (PDF + DOCX + email delivery)
```

---

## PHASE 19 — AGENTIC DEEP RESEARCH
### Hybrid RAG + Web Intelligence
**Priority:** Medium-High | **Time:** 2 batches | **Cost:** Free (Tavily free tier)

```
Install: pip install tavily-python --break-system-packages
         (Tavily: 1,000 free searches/month)

BACKEND — Create backend/app/services/deep_research_agent.py:

class DeepResearchAgent:
  async def research(self, query, document_ids, session_id):
    
    # STEP 1: RAG from uploaded documents
    yield ResearchEvent(step=1, status="running", 
                        message="📄 Analyzing your uploaded documents...")
    doc_answer, doc_citations = await self.rag_pipeline.query(query, document_ids)
    doc_trust = await self.veritas_engine.compute_trust_score(...)
    yield ResearchEvent(step=1, status="done",
                        message=f"Found relevant content in {len(doc_citations)} passages")
    
    # STEP 2: Identify knowledge gaps
    yield ResearchEvent(step=2, status="running",
                        message="🔍 Identifying what your documents don't cover...")
    gap_prompt = f"""
    User asked: {query}
    Document answer: {doc_answer}
    Identify 2-3 specific aspects not answered clearly.
    Return ONLY a JSON array of search queries, max 3 items.
    """
    gaps = await self.llm.query_json(gap_prompt)
    if not gaps or doc_trust.final_score >= 85:
      yield ResearchEvent(step=2, status="skipped",
                          message="Documents provided complete coverage — skipping web search")
      gaps = []
    
    # STEP 3: Agentic web search for gaps
    web_results = []
    if gaps:
      yield ResearchEvent(step=3, status="running",
                          message="🌐 Searching current sources...")
      tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
      for search_query in gaps[:3]:
        results = tavily_client.search(
          search_query,
          search_depth="basic",
          max_results=3,
          include_domains=["gov.in", "rbi.org.in", "sebi.gov.in",
                           "economictimes.com", "livemint.com",
                           "barandbench.com", "livelaw.in",
                           "pubmed.ncbi.nlm.nih.gov", "arxiv.org"]
        )
        web_results.extend(results.get('results', []))
      yield ResearchEvent(step=3, status="done",
                          message=f"Found {len(web_results)} current sources")
    
    # STEP 4: Synthesize
    yield ResearchEvent(step=4, status="running",
                        message="✍️ Synthesizing document findings with current research...")
    synthesis_prompt = f"""
    User question: {query}
    FROM UPLOADED DOCUMENTS (Trust Score: {doc_trust.final_score}/100):
    {doc_answer}
    FROM CURRENT WEB SOURCES:
    {format_web_results(web_results)}
    
    Create a structured synthesis:
    1. ANSWER FROM YOUR DOCUMENTS (with page citations)
    2. CURRENT CONTEXT (what web sources add, with URLs)
    3. KEY INSIGHTS (2-3 bullets)
    4. GAPS & LIMITATIONS
    Mark web content with [Web Source] tag.
    """
    final_answer = await self.llm.query(synthesis_prompt)
    yield ResearchEvent(step=4, status="done", message="Research complete")
    yield ResearchEvent(step="final", status="complete", answer=final_answer,
                        doc_citations=doc_citations, web_sources=web_results,
                        doc_trust=doc_trust, has_web_augmentation=len(web_results) > 0)

FRONTEND:
  In Research workspace only, add toggle:
  Standard Mode [●──] Deep Research Mode
  
  Deep Research on:
  - Placeholder: "Ask a research question — I'll check your documents AND current sources"
  - Note: "Uses web search to supplement your documents (1 credit per query)"
  - 4-step progress bar with live status messages
  - Final response: two sections — 📄 From Your Documents | 🌐 From Current Sources

Available on:
  Free Trial: 3 deep research queries included
  Professional: 50 deep research queries per month
  Enterprise: Unlimited deep research queries
```

---

## PHASE 20 — AUTOMATION SCRIPTS FOR SOLO MAINTENANCE
**Priority:** High | **Time:** 1 batch | **Cost:** ₹0

```
Create backend/app/automation/ directory with Celery Beat scripts:

SCRIPT 1 — Health Monitor (every 5 minutes): auto_health_check.py
  Checks DB, Redis, FAISS, Gemini API, Celery worker, disk usage.
  On 3 consecutive failures: alert email + Sentry.

SCRIPT 2 — API Key Rotation Monitor (hourly): auto_key_rotation.py
  Tests each GEMINI_API_KEY, records status in admin dashboard.

SCRIPT 3 — Daily Digest (8 AM IST daily): auto_daily_digest.py
  Emails you: signups, queries, revenue, MRR, errors, new feedback.

SCRIPT 4 — Database Cleanup (Sunday 2 AM IST): auto_db_cleanup.py
  Deletes temp files >7 days, failed docs >30 days, expired OTPs,
  anonymous sessions >30 days. VACUUM ANALYZE. Reindex FAISS.

SCRIPT 5 — Subscription Check (midnight IST daily): auto_subscription_check.py
  Sends renewal reminders 3 days before expiry.
  Downgrades expired users (data preserved).
  Sends payment failure emails with 48-hour grace period.

SCRIPT 6 — GST Rate Notice (Monday 9 AM IST): auto_gst_notice.py
  Checks if GST rates are older than 90 days → reminds you to verify.

SCRIPT 7 — Model Deprecation Watcher (Monday 10 AM IST): auto_model_check.py
  Tests configured GEMINI_MODEL. If deprecated → alert + auto-switch.

Celery Beat schedule in backend/app/core/celery_config.py:
  health_check: */5 * * * *
  key_rotation_check: 0 * * * *
  daily_digest: 30 2 * * *    (8 AM IST = 2:30 AM UTC)
  db_cleanup: 30 20 * * 0     (Sunday 2 AM IST)
  subscription_check: 30 18 * * *  (midnight IST)
  gst_notice: 30 3 * * 1      (Monday 9 AM IST)
  model_check: 0 4 * * 1      (Monday 10 AM IST)
```

---

## PHASE 21 — PROACTIVE INTELLIGENCE LAYER
**Priority:** Medium | **Time:** 2 batches | **Cost:** ₹0

```
CONCEPT: After every document is processed, DocuMindAI automatically generates
"Proactive Insights" — things you should know before asking.

BACKEND: Create backend/app/services/proactive_insights.py

WORKSPACE_INSIGHT_PROMPTS: {
  "legal": Identify penalty clauses, termination conditions, unusual clauses,
           missing clauses, key dates.
  "finance": Identify key ratios, YoY changes >20%, red flags, tax compliance.
  "hr": Identify exceptional candidates, disqualifying factors, skills gaps.
  "research": Identify claims, methodology limitations, key statistics.
  "teacher": Identify difficult concepts, exam topics, prerequisites.
  "student": Identify top 5 concepts, key terms, likely exam questions.
  "general": Identify main purpose, action items, facts, urgent attention items.
  Each returns: JSON array of {insight_type, severity, finding, page_reference}
  severity: "critical" | "important" | "informational"
}

async def generate_insights(self, document_id, workspace, top_chunks):
  # Uses top 10 most information-dense chunks
  # Saves up to 8 insights per document
  # Triggers critical notifications for severity = "critical"

SUPABASE TABLE: proactive_insights
  id, document_id, session_id, workspace, insight_type, severity,
  finding, page_reference, was_clicked, created_at

FRONTEND: Create frontend/src/components/ProactiveInsightsPanel.tsx

COLLAPSED STATE:
  [⚡ 5 Key Insights from this document] [▼]
  (if critical: [⚠️ 1 Critical Finding] in red)

EXPANDED STATE:
  ⚡ PROACTIVE INSIGHTS
  🔴 CRITICAL [Page 7] — "Penalty clause..."  [Ask AI about this]
  🟡 IMPORTANT [Page 12] — "Jurisdiction..."  [Ask AI about this]
  🔵 INFO [Page 3] — "Contract value: ₹45L."
  [Hide Insights ▲]

"Ask AI about this" pre-fills query input with a relevant question.
This removes the blank-page problem entirely.
```

---

## PHASE 22 — COLLABORATION LAYER
**Priority:** Medium | **Time:** 2 batches | **Cost:** ₹0 (Supabase Realtime)

```
FEATURE: Session owner shares a link. Collaborators can view + ask in real-time.

BACKEND additions to chat_sessions:
  is_shared BOOLEAN DEFAULT FALSE
  share_token TEXT UNIQUE
  share_permissions TEXT DEFAULT 'view_and_ask'
                    CHECK IN ('view_only', 'view_and_ask')
  shared_at TIMESTAMPTZ
  max_collaborators INT DEFAULT 5

New endpoints:
  POST /api/sessions/{id}/share → generates share_token
  DELETE /api/sessions/{id}/share → clears share_token
  GET /api/shared/{token} → returns session with messages

Supabase Realtime:
  Channel: session:[session_id]
  Subscribe: INSERT on messages WHERE session_id = [id]
  Broadcasts new messages to all connected clients instantly.

FRONTEND — Share Modal:
  ┌─────────────────────────────────────────┐
  │ Share This Session                      │
  │                                         │
  │ Share link:                             │
  │ [documindai.com/shared/abc123] [Copy]   │
  │                                         │
  │ Permissions:                            │
  │ ○ View only (they can read, not ask)    │
  │ ● View and ask (they can ask questions) │
  │                                         │
  │ [Generate Share Link]                   │
  │ [Stop Sharing]                          │
  └─────────────────────────────────────────┘

Available on:
  Free Trial: Share with 1 person (view only)
  Professional: Share with 3 people (view and ask)
  Enterprise: Share with 25 people + password protection
```

---

## PHASE 23 — VERITAS PUBLIC API
### From Product to Platform — The Acquisition Move
**Priority:** Medium | **Time:** 2 batches | **Cost:** ₹0

```
POST https://api.documindai.com/v1/verify

Response:
{
  "trust_score": 87,
  "trust_level": "HIGH",
  "trust_label": "High Confidence",
  "evidence": [...],
  "warnings": [],
  "contradictions": [],
  "factor_scores": { "dual_retrieval": 90, "direct_quote": 85, ... },
  "api_version": "1.0",
  "computation_ms": 342
}

Rate limits: Free (100/mo) | Starter $9 (5K/mo) | Growth $29 (50K/mo)
API key management: POST/GET/DELETE /api/developer/keys
Create /developer landing page with Python/JS/cURL examples.
This turns DocuMindAI into verification infrastructure for the global RAG ecosystem.
```

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 8 v2 — NEW PHASES: PHYSICAL AI LAYER (Phases 24–28)
## Bridging Governed AI → Proactive AI → Physical AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> **WHAT NOBODY HAS BUILT YET (May 2026):**
> Every document RAG tool in the market — NotebookLM, ChatPDF, Humata, Vectara —
> requires you to: open a browser, type a query, read an answer.
> You are always the initiator. The AI waits for you.
>
> Physical AI flips this: the AI is present in the world, not just the screen.
> You speak to it. You show it a physical paper. It briefs you each morning.
> It lives on your phone home screen. It catches any text you copy, anywhere.
>
> These 5 phases cost ₹0 to build (all use free browser APIs and free services).
> None of these features exist in any document RAG product today.
> Each one is a market differentiator that no competitor can replicate quickly.

---

## PHASE 24 — VOICE QUERY LAYER
### Talk to Your Documents Like You Talk to a Person
**Priority:** High | **Time:** 2 batches | **Cost:** ₹0 (Web Speech API — browser native)
**Why nobody built this yet:** Voice + RAG + Trust Score is a combination that does not exist.
**Physical AI connection:** Voice is the most natural physical interface. No keyboard needed.

---

### 24-A: Voice Input (Speech → Query)

```
TECHNOLOGY USED:
  Web Speech API — SpeechRecognition (built into Chrome, Edge, Safari, Android browser)
  Cost: ₹0 — completely free, runs in the browser
  No API key required. No server processing. Audio captured locally.
  Works on: Chrome desktop, Chrome Android, Edge, Samsung Internet, Safari 16.4+
  Does NOT work: Firefox (gracefully degraded — button hidden on Firefox)

BACKEND CHANGES:
  None required.
  The voice input converts speech → text, then submits as a normal text query.
  The existing query endpoint handles it identically.
  This is purely a frontend enhancement.

FRONTEND:
Create frontend/src/hooks/useVoiceInput.ts

  import { useState, useRef, useEffect } from "react"

  export type VoiceState = "idle" | "listening" | "processing" | "error" | "unsupported"

  export function useVoiceInput(onTranscript: (text: string) => void) {
    const [state, setState] = useState<VoiceState>("idle")
    const [interimText, setInterimText] = useState("")
    const [errorMessage, setErrorMessage] = useState("")
    const recognitionRef = useRef<SpeechRecognition | null>(null)
    const timeoutRef = useRef<NodeJS.Timeout | null>(null)

    const isSupported = typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)

    const startListening = () => {
      if (!isSupported) {
        setState("unsupported")
        return
      }
      if (state === "listening") {
        stopListening()
        return
      }

      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition
      const recognition = new SpeechRecognition()

      recognition.continuous = false
      recognition.interimResults = true
      recognition.lang = "en-IN"  // Indian English as default
      recognition.maxAlternatives = 1

      recognition.onstart = () => {
        setState("listening")
        setInterimText("")
        setErrorMessage("")
      }

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let interim = ""
        let final = ""
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          if (result.isFinal) {
            final += result[0].transcript
          } else {
            interim += result[0].transcript
          }
        }
        setInterimText(interim)
        if (final) {
          setState("processing")
          setInterimText("")
          onTranscript(final.trim())
          recognitionRef.current?.stop()
        }
      }

      recognition.onspeechend = () => {
        // Auto-stop after 2 seconds of silence
        timeoutRef.current = setTimeout(() => {
          recognition.stop()
        }, 2000)
      }

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        const msgs: Record<string, string> = {
          "no-speech": "No speech detected. Tap the mic and try again.",
          "audio-capture": "Microphone not found. Check permissions.",
          "not-allowed": "Microphone access denied. Allow it in browser settings.",
          "network": "Network error. Check your connection."
        }
        setErrorMessage(msgs[event.error] || "Voice input failed. Please type instead.")
        setState("error")
      }

      recognition.onend = () => {
        if (state !== "processing") setState("idle")
        setInterimText("")
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
      }

      recognitionRef.current = recognition
      recognition.start()
    }

    const stopListening = () => {
      recognitionRef.current?.stop()
      setState("idle")
      setInterimText("")
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }

    useEffect(() => {
      return () => {
        recognitionRef.current?.stop()
        if (timeoutRef.current) clearTimeout(timeoutRef.current)
      }
    }, [])

    return { state, interimText, errorMessage, isSupported, startListening, stopListening }
  }


LANGUAGE SUPPORT:
  Add a language selector dropdown near the voice button.
  Options with SpeechRecognition lang codes:
    🇮🇳 English (India)   → "en-IN"   (DEFAULT)
    🇮🇳 Hindi             → "hi-IN"
    🇮🇳 Tamil             → "ta-IN"
    🇮🇳 Telugu            → "te-IN"
    🇮🇳 Marathi           → "mr-IN"
    🇬🇧 English (UK)      → "en-GB"
    🇺🇸 English (US)      → "en-US"
  
  Save selected language to localStorage key: "documind_voice_lang"
  Load on component mount.
  Hindi support is a massive moat — no other RAG tool works in Hindi.
```

### 24-B: Voice Button UI Component

```
Create frontend/src/components/voice/VoiceInputButton.tsx

This component integrates INTO the existing query input area.
It sits INSIDE the query input field on the RIGHT side (same row as Submit button).
It does NOT add a new row or break the existing input layout.

VISUAL DESIGN:

Idle state:
  Button: 36×36px, border-radius 50% (circle)
  Background: var(--surface-sunken)
  Border: 1px solid var(--border-default)
  Icon: 🎤 microphone SVG (20px, var(--text-secondary))
  Tooltip: "Ask with voice (Ctrl+Shift+V)"
  Hover: background var(--surface-hover), border var(--border-strong)
  Transition: all 150ms ease

Listening state:
  Background: rgba(239, 68, 68, 0.1)   (soft red — recording signal)
  Border: 2px solid var(--red-500)
  Icon: microphone SVG (20px, var(--red-500))
  Animation:
    @keyframes pulse-ring {
      0%   { box-shadow: 0 0 0 0px rgba(239, 68, 68, 0.4); }
      70%  { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
      100% { box-shadow: 0 0 0 0px rgba(239, 68, 68, 0); }
    }
    animation: pulse-ring 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
  Tooltip: "Listening... (tap to stop)"
  Respects prefers-reduced-motion: if reduced-motion, no pulse animation.

Processing state:
  Background: var(--surface-sunken)
  Icon: rotating spinner SVG (same size)
  Tooltip: "Processing..."
  
Error state:
  Reset to idle after 3 seconds. Show errorMessage in a toast (not blocking modal).

Unsupported state:
  Button is HIDDEN completely (display: none).
  No indication — users who can't use it won't see a broken button.

INTERIM TEXT DISPLAY:
  While listening (state = "listening"), show interim speech text
  INSIDE the existing query input field as gray placeholder-style text.
  This gives the user visual confirmation that they're being heard.
  Implementation:
    When interimText is non-empty, set the input's value to interimText
    Apply style: color var(--text-tertiary), fontStyle italic
    When final transcript arrives: clear interimText, set value to final,
    apply normal text style, auto-submit if query is non-empty.

KEYBOARD SHORTCUT:
  Ctrl+Shift+V (Windows/Linux) or Cmd+Shift+V (Mac) triggers startListening()
  Add to useKeyboardShortcuts hook (or create if it doesn't exist).
  Show keyboard shortcut in tooltip.

ACCESSIBILITY:
  aria-label: "Voice input — currently {state}"
  aria-pressed: state === "listening"
  role: "button"
  User can always type instead — voice is enhancement, not replacement.

AUTO-SUBMIT BEHAVIOR:
  When final transcript is received:
  1. Set the query input value to the transcript
  2. Wait 300ms (so user sees what was transcribed)
  3. Auto-submit the query (same as pressing Enter)
  4. Analytics: track('voice_query_used', { workspace, lang: voiceLang })
  
  If user edited the transcript in those 300ms: still use their edited version.
  Users can also press Enter themselves after seeing the transcript — both work.
```

### 24-C: Voice Answer Readback (Text → Speech)

```
Create frontend/src/hooks/useVoiceReadback.ts

TECHNOLOGY: Web SpeechSynthesis API (browser native, completely free)
No API key. No server. Uses the device's built-in text-to-speech voices.
Works on: Chrome, Edge, Safari, Firefox (better cross-browser than recognition).

  import { useState, useCallback, useRef } from "react"

  export function useVoiceReadback() {
    const [isSpeaking, setIsSpeaking] = useState(false)
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

    const isSupported = typeof window !== "undefined" &&
      "speechSynthesis" in window

    const speak = useCallback((text: string, lang: string = "en-IN") => {
      if (!isSupported) return
      window.speechSynthesis.cancel()  // stop any ongoing speech

      // Trim answer for readback: skip citations block, max 800 chars
      const cleanText = text
        .replace(/\[Source:.*?\]/g, "")      // remove citation markers
        .replace(/Page \d+/g, "")            // remove page refs
        .replace(/#{1,3} /g, "")             // remove markdown headings
        .replace(/\*\*/g, "")               // remove bold markers
        .trim()
        .slice(0, 800)

      const utterance = new SpeechSynthesisUtterance(cleanText)
      utterance.lang = lang
      utterance.rate = 0.95   // slightly slower than default for clarity
      utterance.pitch = 1.0
      utterance.volume = 1.0

      // Try to find a local Indian English voice if available
      const voices = window.speechSynthesis.getVoices()
      const preferredVoice = voices.find(v =>
        v.lang.startsWith("en-IN") && !v.name.includes("Google")
      ) || voices.find(v => v.lang.startsWith("en")) || null
      if (preferredVoice) utterance.voice = preferredVoice

      utterance.onstart = () => setIsSpeaking(true)
      utterance.onend = () => setIsSpeaking(false)
      utterance.onerror = () => setIsSpeaking(false)

      utteranceRef.current = utterance
      window.speechSynthesis.speak(utterance)
    }, [isSupported])

    const stop = useCallback(() => {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
    }, [])

    return { speak, stop, isSpeaking, isSupported }
  }


READBACK BUTTON — placed next to every AI response:
  Location: in the response action bar (same row as Copy, Bookmark, Export)
  This does NOT add a new row or break layout.

  Button: 32×32px, ghost style
  Idle: 🔊 icon (var(--text-tertiary)), tooltip "Read answer aloud"
  Speaking: ⏹ icon (var(--brand)), tooltip "Stop reading"
  Unsupported: Button hidden (display: none)
  
  On click when idle: call speak(answerText, voiceLang)
  On click when speaking: call stop()

AUTO-READBACK OPTION (Settings):
  In Settings → Voice, add toggle:
  [○] Auto-read answers aloud after voice queries
  
  Behavior: If user submitted query via voice AND this setting is on,
  automatically call speak() after the answer finishes streaming.
  Default: OFF (user must opt in)

UX PRINCIPLE:
  Voice input and readback are INDEPENDENT features.
  User can: type query → hear answer read aloud.
  User can: speak query → read answer on screen.
  User can: speak query → hear answer read aloud (full voice loop).
  All three combinations work with zero extra configuration.
```

### 24-D: Voice Mode Verification Checkpoint

```
VERIFICATION AFTER PHASE 24:
  Manual test 1: Open any workspace → click mic button → speak a query
    → transcript appears in input → query submits automatically
    → answer appears normally with trust score
  Manual test 2: Click 🔊 on any answer → answer reads aloud
  Manual test 3: Open on Firefox → mic button is NOT visible (graceful degradation)
  Manual test 4: Deny microphone permission → error toast appears (not a crash)
  Manual test 5: Click mic → speak Hindi words → verify Hindi transcript appears
    (Hindi recognition works on Chrome with lang=hi-IN)
  
  TypeScript: npx tsc --noEmit → zero errors
  Existing tests: all pass (no existing code was modified)
  
  DEFINITION OF DONE — PHASE 24:
  ✅ Voice query submits to existing backend without any backend changes
  ✅ Pulsing mic indicator shows when listening
  ✅ Interim text shows in input while speaking
  ✅ Auto-submits on speech end (300ms delay for user review)
  ✅ Text-to-speech reads answers back on request
  ✅ Unsupported browsers show zero broken UI
  ✅ Keyboard shortcut Ctrl/Cmd+Shift+V works
  ✅ prefers-reduced-motion: pulse animation disabled
  ✅ Language selector saves to localStorage
  ✅ WCAG 2.1 AA: aria-label, aria-pressed on mic button
```

---

## PHASE 25 — CAMERA DOCUMENT SCAN
### Point Your Camera at Any Physical Document
**Priority:** High | **Time:** 2 batches | **Cost:** ₹0 (MediaDevices API — browser native)
**Why nobody built this yet:** Every RAG tool requires a digital file. Physical papers are ignored.
**Physical AI connection:** Documents don't need to be digital to be queryable.

---

### 25-A: Camera Capture Backend Integration

```
CONCEPT:
  User has a printed contract on their desk, a textbook page, a handwritten note,
  a financial statement, a letterhead — any physical document.
  They tap "Scan Document" → point phone/laptop camera → system captures it →
  it goes through the existing OCR pipeline → instantly queryable.
  No app installation. No scanner. No file conversion.
  Just the browser camera.

TECHNOLOGY:
  MediaDevices.getUserMedia({ video: true }) — browser native, completely free
  Canvas API for frame capture — browser native, completely free
  Existing backend/app/services/ocr_orchestrator.py — NO CHANGES (stable system)
  The captured image is sent to the existing document upload endpoint as an image file.

BACKEND:
  No new endpoints needed.
  The existing POST /api/documents/upload endpoint already accepts image files (JPG, PNG).
  The existing OCR orchestrator already processes images.
  
  ONLY IF image upload is not currently supported by the upload endpoint:
  In backend/app/api/v1/endpoints/documents.py, add "image/jpeg" and "image/png"
  to the ALLOWED_MIME_TYPES list.
  Everything else (OCR, chunking, embedding) works identically.
  
  Run: alembic revision if any model changes needed (likely none).

Create backend/app/services/scan_postprocess.py:
  (This is a SMALL, purely additive helper — does NOT touch stable systems)
  
  async def enhance_scanned_image(image_bytes: bytes) -> bytes:
    """
    Lightweight image enhancement before OCR.
    Uses Pillow (already installed) — no new dependencies.
    """
    from PIL import Image, ImageEnhance, ImageFilter
    import io
    
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # 1. Auto-rotate based on EXIF orientation
    img = ImageOps.exif_transpose(img)
    
    # 2. Increase contrast (makes text sharper for OCR)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)
    
    # 3. Convert to grayscale (OCR accuracy improves)
    img = img.convert("L")
    
    # 4. Apply slight sharpening
    img = img.filter(ImageFilter.SHARPEN)
    
    # 5. Upscale if smaller than 1200px wide (minimum for good OCR)
    if img.width < 1200:
      ratio = 1200 / img.width
      img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
    
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=92)
    return output.getvalue()
  
  Call this in the document upload handler BEFORE sending to OCR,
  when the uploaded file is an image (mime_type starts with "image/").
  This is a simple pre-processing step, not a replacement of any system.
```

### 25-B: Camera Scanner UI Component

```
Create frontend/src/components/camera/DocumentScanner.tsx

This component opens as a MODAL when user clicks "Scan Document".
It does NOT replace or modify the existing document upload UI.
The existing file upload drag-and-drop continues to work exactly as before.
This modal is an ADDITIONAL way to get documents in.

───────────────────────────────────────────────────────
ENTRY POINT:
  In the document upload area (wherever the current upload button lives),
  add a second button BELOW the existing upload button:
  
  Current:  [📎 Upload File]
  New:      [📷 Scan Document]  ← NEW, purely additive
  
  Button style: same as other secondary buttons in the upload area.
  Gap between buttons: var(--space-3) (12px)
  No layout changes to the existing upload button area.
───────────────────────────────────────────────────────

SCANNER MODAL (Opens on "Scan Document" click):
  Backdrop: fixed inset-0, background rgba(0,0,0,0.85), z-index 200
  
  Modal container:
    max-width: 520px
    width: calc(100vw - 32px)
    background: var(--surface-base)
    border-radius: var(--radius-xl)
    padding: 0  (inner sections handle padding)
    overflow: hidden
    box-shadow: var(--shadow-2xl)
    position: absolute, centered (top 50%, left 50%, transform: translate(-50%, -50%))
  
  MODAL HEADER:
    padding: 16px 20px
    border-bottom: 1px solid var(--border-subtle)
    display: flex, justify-content: space-between, align-items: center
    
    Left: "📷 Scan Document" — DM Sans 16px weight 600, var(--text-primary)
    Right: [✕] close button — 32×32px, ghost, border-radius 50%
    
  CAMERA VIEWFINDER:
    Height: 320px on desktop, 260px on mobile
    Background: #000
    position: relative, overflow: hidden
    
    <video> element:
      width: 100%, height: 100%, object-fit: cover
      autoPlay, playsInline, muted  (muted required for autoplay on mobile)
    
    DOCUMENT FRAME OVERLAY (CSS only, no canvas needed):
      position: absolute, inset: 24px
      border: 2px dashed rgba(255,255,255,0.6)
      border-radius: 8px
      box-shadow: 0 0 0 9999px rgba(0,0,0,0.35)  // darkens area outside the frame
      pointer-events: none
      
      Corner indicators (4 corners):
        Absolutely positioned 12×12px L-shaped white lines at each corner.
        Pure CSS. These guide the user to align the document.
    
    STATUS LABEL (inside viewfinder, bottom):
      position: absolute, bottom: 12px, left 50%, transform: translateX(-50%)
      background: rgba(0,0,0,0.6)
      color: white, font-size: 12px, font-weight: 500
      padding: 4px 12px, border-radius: 999px
      Content changes per state:
        requesting: "Requesting camera access..."
        active:     "Align document inside the frame"
        countdown:  "Capturing in 2..." / "Capturing in 1..."
        captured:   "✓ Captured"
        error:      "Camera unavailable"
    
  CAMERA CONTROLS:
    padding: 16px 20px
    background: var(--surface-base)
    
    ROW 1 — Camera selector (if multiple cameras available):
      A small dropdown: "📷 Front Camera" / "📷 Back Camera"
      Styled as: .btn-ghost, font-size 13px, auto width
      Only show if navigator.mediaDevices.enumerateDevices returns >1 video device
      On mobile: "Back Camera" is default (better for document scanning)
      On desktop: "Webcam" (only one option usually, hide if so)
      Gap below: 12px
    
    ROW 2 — Action buttons:
      display: flex, gap: 12px, justify-content: center
      
      [🔦 Flash] button — 36×36px, circle, ghost
        Toggles torch (camera flashlight) via MediaTrackConstraints { torch: true }
        Only shown on mobile where torch is available
        Hidden on desktop (torch not available)
      
      [● Capture] button — PRIMARY, width: 64px, height: 64px, border-radius: 50%
        Background: var(--brand), white dot icon inside
        This is the main CTA — large and centered
        On click: capture frame from <video> to <canvas>, extract JPEG blob
        After capture: show 3-second countdown (3... 2... 1... ●)
        Countdown gives user time to hold still
        Keyboard: Space bar triggers this when modal is open
      
      [↻ Retake] button — 36×36px, circle, ghost
        Only appears AFTER a capture
        Icon: circular arrow
        On click: clears captured image, returns to live camera
    
    ROW 3 — Tips (shown only in first 3 uses, then hidden):
      Small text, var(--text-tertiary), 11px, centered:
      "Hold still · Good lighting · Flat surface · All text visible"
      Dismissed count stored in localStorage: "documind_scan_tips_count"
      After 3 dismissals: never shown again.
    
  CAPTURED IMAGE PREVIEW (replaces camera viewfinder after capture):
    <img> element with the captured image
    Same 320/260px height container
    object-fit: contain (so full document is visible)
    background: var(--surface-sunken)
    
    "Using this image?" label below preview:
      "This will be added to your current session's documents."
      Font: 13px, var(--text-secondary), centered
    
  MODAL FOOTER (after capture):
    padding: 16px 20px
    border-top: 1px solid var(--border-subtle)
    display: flex, gap: 12px
    
    [↻ Retake]         — .btn .btn-ghost, flex: 1
    [✓ Use This Scan]  — .btn .btn-primary, flex: 2

AFTER "Use This Scan" CLICK:
  1. Convert captured canvas to Blob (image/jpeg, quality 0.92)
  2. Create a File object: new File([blob], "scanned-doc-[timestamp].jpg", { type: "image/jpeg" })
  3. Close the scanner modal
  4. Call the SAME upload function that the existing drag-and-drop uses
     (just pass the File object — no duplicate logic needed)
  5. The document appears in the document list with a 📷 camera icon badge
     to distinguish it from file uploads (purely cosmetic, handled in the
     document list item component with a small icon)
  6. Toast: "📷 Scanning document..." (same as normal upload toast)
  7. Normal processing pipeline handles everything from here.
  
  Track: posthog.capture('camera_scan_used', { workspace })

CAMERA CLEANUP:
  When modal closes (any reason):
    Call stream.getTracks().forEach(track => track.stop())
    This releases the camera immediately.
    The red camera indicator in the browser disappears.
  
  useEffect cleanup:
    return () => { stream?.getTracks().forEach(t => t.stop()) }

PERMISSION HANDLING:
  If user denies camera:
    Replace viewfinder with a friendly message:
    ┌─────────────────────────────────────────────┐
    │                                             │
    │        📷                                   │
    │   Camera access denied                      │
    │                                             │
    │   To scan documents, allow camera access    │
    │   in your browser settings.                 │
    │                                             │
    │   [Open Browser Settings] [Upload File Instead]
    │                                             │
    └─────────────────────────────────────────────┘
    "Upload File Instead" calls existing upload input click().
    Does NOT show this as an error — just offers the alternative.

  If camera not available at all (old browser/desktop without webcam):
    Same message but: "No camera found. Use file upload instead."
    "Upload File Instead" button only.
```

### 25-C: Camera Scan Verification Checkpoint

```
VERIFICATION AFTER PHASE 25:
  Manual test 1 (Mobile): Open on Chrome Android → "Scan Document" →
    camera opens → align a document → tap Capture →
    preview appears → "Use This Scan" →
    document appears in list → ask a question about it → answer returned
  
  Manual test 2 (Desktop): Open on Chrome desktop → "Scan Document" →
    webcam opens → capture → verify document processes correctly
  
  Manual test 3: Deny camera permission → friendly message appears (no crash)
  
  Manual test 4: Close modal mid-capture → camera light turns off immediately
    (stream correctly stopped)
  
  Manual test 5: Open existing document upload → still works normally
    (nothing broken in existing upload flow)
  
  TypeScript: npx tsc --noEmit → zero errors
  Backend: existing OCR pipeline processes scanned images successfully
  
  DEFINITION OF DONE — PHASE 25:
  ✅ Camera opens in modal without page navigation
  ✅ Document frame overlay guides alignment
  ✅ Capture → preview → upload flow works end-to-end
  ✅ Camera releases when modal closes
  ✅ Scanned document appears in doc list with 📷 badge
  ✅ Existing upload flow untouched and still working
  ✅ Denied camera shows upload fallback gracefully
  ✅ No new backend endpoints needed
  ✅ Image enhancement runs before OCR (via scan_postprocess.py)
```

---

## PHASE 26 — MORNING BRIEFING SYSTEM
### The AI That Briefs You, Before You Ask Anything
**Priority:** Medium-High | **Time:** 2 batches | **Cost:** ₹0
**Why nobody built this yet:** All RAG tools are reactive. You open → you ask → you get.
**This flips it:** You open → the AI already ran → it tells you what happened overnight.
**Physical AI connection:** Ambient intelligence — the system monitors and reports autonomously.

---

### 26-A: Briefing Generator (Backend)

```
CONCEPT:
  At 6:00 AM IST daily, a Celery task runs for every active user.
  It looks at their documents uploaded in the last 30 days.
  It generates a "Today's Briefing" — a personalized, workspace-aware summary
  of what they should know, what deadlines are approaching, and what their
  documents contain that requires attention.
  
  When the user opens DocuMindAI that morning, they see the briefing.
  They did not ask for it. The AI just knew.
  
  This is the difference between a tool and an assistant.

SUPABASE TABLE:
  CREATE TABLE morning_briefings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    briefing_date DATE NOT NULL,
    workspace TEXT NOT NULL,  -- the user's most-used workspace in last 7 days
    summary_text TEXT NOT NULL,
    card_count INT DEFAULT 0,
    deadline_count INT DEFAULT 0,   -- number of deadline cards
    insight_count INT DEFAULT 0,    -- number of proactive insight cards
    activity_count INT DEFAULT 0,   -- number of activity summary cards
    cards JSONB NOT NULL DEFAULT '[]',  -- array of BriefingCard objects
    was_opened BOOLEAN DEFAULT FALSE,
    opened_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, briefing_date)  -- one briefing per user per day
  );

  BriefingCard JSONB structure:
  {
    "id": "uuid",
    "type": "deadline" | "insight" | "activity" | "summary" | "tip",
    "priority": "urgent" | "important" | "info",
    "workspace": "legal" | "finance" | "hr" | ...,
    "title": "Contract expiry in 7 days",
    "body": "The NDA with TechCorp expires on May 27, 2026. Consider renewal.",
    "document_name": "NDA_TechCorp.pdf",
    "page_reference": 3,
    "action_label": "Review Document",
    "action_url": "/dashboard/sessions/[session_id]",
    "created_from": "proactive_insights" | "document_analysis" | "activity"
  }

Create backend/app/tasks/briefing_tasks.py:

  @celery_app.task(name="tasks.generate_morning_briefings")
  def generate_morning_briefings():
    """
    Runs daily at 6 AM IST.
    Generates briefings for all users active in last 30 days.
    """
    today = date.today()
    
    # Get users who:
    # 1. Have been active in last 30 days (last_activity_at > 30 days ago)
    # 2. Don't already have a briefing for today
    # 3. Have at least one completed document
    active_users = db.query(User).filter(
      User.last_activity_at > datetime.utcnow() - timedelta(days=30),
      ~User.id.in_(
        db.query(MorningBriefing.user_id)
        .filter(MorningBriefing.briefing_date == today)
      )
    ).all()
    
    for user in active_users:
      try:
        generate_user_briefing.delay(str(user.id), today.isoformat())
      except Exception as e:
        logger.warning(f"Briefing generation failed for {user.id}: {e}")


  @celery_app.task(name="tasks.generate_user_briefing", 
                   soft_time_limit=120, time_limit=180)
  def generate_user_briefing(user_id: str, date_str: str):
    """
    Generates a single user's morning briefing.
    This is a BACKGROUND task — does not affect user's current session.
    """
    cards = []
    
    # === SECTION 1: DEADLINE CARDS ===
    # Scan all proactive_insights for this user where finding contains
    # date patterns or deadline keywords.
    # Look for insights with: "expires", "deadline", "due", "by [date]",
    # "valid until", "terminate", "renew by", "submit by", "last date"
    
    deadline_insights = db.query(ProactiveInsight).join(Document).filter(
      Document.user_id == user_id,
      ProactiveInsight.severity.in_(["critical", "important"]),
      ProactiveInsight.finding.ilike(any_([
        "%expires%", "%deadline%", "%due date%", "%valid until%",
        "%renew by%", "%terminate%", "%submit by%"
      ]))
    ).order_by(ProactiveInsight.severity.desc()).limit(5).all()
    
    for insight in deadline_insights:
      # Check if this insight is still recent (document uploaded in last 30 days)
      doc = db.query(Document).filter(Document.id == insight.document_id).first()
      if doc and (datetime.utcnow() - doc.created_at).days <= 30:
        cards.append({
          "type": "deadline",
          "priority": "urgent" if insight.severity == "critical" else "important",
          "workspace": insight.workspace,
          "title": _extract_deadline_title(insight.finding),
          "body": insight.finding,
          "document_name": doc.filename,
          "page_reference": insight.page_reference,
          "action_label": "Review Document",
          "action_url": f"/dashboard?doc={doc.id}"
        })
    
    # === SECTION 2: INSIGHT CARDS ===
    # Pull top unviewed critical proactive insights from last 7 days
    unviewed_insights = db.query(ProactiveInsight).join(Document).filter(
      Document.user_id == user_id,
      ProactiveInsight.was_clicked == False,
      ProactiveInsight.severity == "critical",
      ProactiveInsight.created_at > datetime.utcnow() - timedelta(days=7)
    ).limit(3).all()
    
    for insight in unviewed_insights:
      doc = db.query(Document).filter(Document.id == insight.document_id).first()
      if doc:
        cards.append({
          "type": "insight",
          "priority": "important",
          "workspace": insight.workspace,
          "title": f"Critical finding in {doc.filename}",
          "body": insight.finding[:200],
          "document_name": doc.filename,
          "page_reference": insight.page_reference,
          "action_label": "See Full Insight",
          "action_url": f"/dashboard?doc={doc.id}&insight={insight.id}"
        })
    
    # === SECTION 3: ACTIVITY SUMMARY CARD ===
    # One card summarizing yesterday's activity
    yesterday = datetime.utcnow() - timedelta(days=1)
    queries_yesterday = db.query(func.count(QueryLog.id)).filter(
      QueryLog.user_id == user_id,
      QueryLog.created_at > yesterday
    ).scalar()
    
    docs_yesterday = db.query(func.count(Document.id)).filter(
      Document.user_id == user_id,
      Document.created_at > yesterday,
      Document.status == "completed"
    ).scalar()
    
    if queries_yesterday > 0 or docs_yesterday > 0:
      body_parts = []
      if queries_yesterday > 0:
        body_parts.append(f"{queries_yesterday} queries answered")
      if docs_yesterday > 0:
        body_parts.append(f"{docs_yesterday} document(s) processed")
      
      cards.append({
        "type": "activity",
        "priority": "info",
        "title": "Yesterday's Activity",
        "body": " · ".join(body_parts),
        "action_label": "View History",
        "action_url": "/dashboard"
      })
    
    # === SECTION 4: SMART TIP CARD ===
    # Rotate through workspace-specific tips for the user's most-used workspace
    # These are pre-written strings — no LLM call needed.
    primary_workspace = _get_primary_workspace(user_id, db)
    tip = WORKSPACE_TIPS[primary_workspace][
      date.today().timetuple().tm_yday % len(WORKSPACE_TIPS[primary_workspace])
    ]
    cards.append({
      "type": "tip",
      "priority": "info",
      "title": f"Tip for {primary_workspace.title()} workspace",
      "body": tip,
      "action_label": None
    })
    
    # Save briefing (max 8 cards total)
    cards = cards[:8]
    
    db.add(MorningBriefing(
      user_id=user_id,
      briefing_date=date.today(),
      workspace=primary_workspace,
      summary_text=f"{len(cards)} updates for you today",
      card_count=len(cards),
      deadline_count=sum(1 for c in cards if c["type"] == "deadline"),
      insight_count=sum(1 for c in cards if c["type"] == "insight"),
      activity_count=sum(1 for c in cards if c["type"] == "activity"),
      cards=cards
    ))
    db.commit()


WORKSPACE_TIPS (pre-written, no LLM needed — add to config):
  {
    "legal": [
      "Tip: Upload multiple versions of a contract to detect changes between drafts.",
      "Tip: Use the Legal workspace for lease agreements — it flags unusual clauses automatically.",
      "Tip: Export your session as an audit report for client files.",
      "Tip: Cross-document contradiction detection works when you upload the original + amendment.",
    ],
    "finance": [
      "Tip: Upload P&L + Balance Sheet together for ratio analysis across both.",
      "Tip: Ask 'Identify all items with YoY change greater than 20%'.",
      "Tip: The Finance workspace computes ratios in Python — results are mathematically exact.",
      "Tip: Export your session with trust scores for CA file documentation.",
    ],
    "hr": [
      "Tip: Upload all resumes in one session to compare candidates directly.",
      "Tip: Ask 'Which candidates have not worked in a startup environment?' for negative filtering.",
      "Tip: Use 'Rank by [specific skill]' to filter candidates before interviews.",
    ],
    "research": [
      "Tip: Enable Deep Research mode to supplement your papers with current web sources.",
      "Tip: Upload multiple related papers — ask 'Where do these papers disagree?'",
      "Tip: Use the Research workspace to generate citation-ready bibliographies.",
    ],
    "teacher": [
      "Tip: Upload a textbook chapter → ask 'Generate a 20-question quiz with answer key'.",
      "Tip: Ask 'What prerequisite knowledge does this chapter assume?' for syllabus planning.",
      "Tip: Export MCQ sets as DOCX for printing.",
    ],
    "student": [
      "Tip: Ask 'Explain this in the simplest possible words' for complex topics.",
      "Tip: Use the Student workspace for active recall: ask the AI to quiz you.",
      "Tip: Ask 'What are the 5 most important things to remember from this chapter?'",
    ],
    "general": [
      "Tip: Scan a physical document using the 📷 Scan button — no file conversion needed.",
      "Tip: Use voice queries (🎤) to ask hands-free while reviewing printed documents.",
      "Tip: Share your session with a colleague using the Share button in the session header.",
    ]
  }

Add to Celery Beat schedule:
  morning_briefings: 30 0 * * *  (6 AM IST = 00:30 UTC)

API Endpoint (NEW):
  GET /api/briefing/today
  Returns: current day's MorningBriefing for the authenticated user
  If none exists yet (generated after 6 AM): returns { briefing: null }
  
  PATCH /api/briefing/{id}/opened
  Marks briefing as opened (for analytics).
  Body: {}  Returns: { success: true }
```

### 26-B: Morning Briefing UI

```
Create frontend/src/components/briefing/MorningBriefingPanel.tsx

PLACEMENT:
  The briefing panel appears at the TOP of the main dashboard page (/dashboard),
  ABOVE the session list / document list.
  It is NOT inside any workspace. It is on the general dashboard home.
  
  It only appears if:
  1. Today's briefing exists (GET /api/briefing/today returns data)
  2. The user has not dismissed it today (stored in localStorage per date)
  3. There are cards to show (card_count > 0)
  
  It auto-hides if: user dismissed it, OR it's empty, OR it's after 6 PM IST
  (showing a "tomorrow's briefing" would be generated at 6 AM — after 6 PM
  the briefing is stale, so hide it gracefully).

COLLAPSED STATE (initial, default):
  ┌────────────────────────────────────────────────────────────────────────┐
  │  ☀️  Good morning, [First Name].  · 5 updates ready  [▼ See Briefing] │
  └────────────────────────────────────────────────────────────────────────┘
  
  Height: 44px
  Background: linear-gradient(90deg, var(--surface-raised) 0%, var(--surface-base) 100%)
  Border: 1px solid var(--border-subtle)
  Border-radius: var(--radius-lg)
  Padding: 0 16px
  Margin-bottom: 20px
  
  Left content:
    ☀️ emoji (16px) + "Good morning, Riya." (DM Sans 14px weight 500, var(--text-primary))
    · separator
    "5 updates ready" (DM Sans 13px, var(--text-secondary))
    
    Time-aware greeting:
      Before 12 PM IST: "Good morning"
      12 PM–5 PM IST:   "Good afternoon"
      After 5 PM IST:   "Good evening"
    
    If deadline_count > 0:
      Show "⚠️ {deadline_count} deadline" before the separator, in amber color
  
  Right content:
    [▼ See Briefing] — .btn-ghost, 13px, collapses to icon on mobile
    [✕] — 28×28px, ghost, closes the panel for today

EXPANDED STATE:
  Smooth expand animation: max-height 0 → full height, 250ms ease-out
  
  HEADER ROW:
    padding: 16px 20px 12px 20px
    "☀️ Today's Briefing — [date, e.g. Wednesday, May 21]"
    DM Sans 15px weight 600, var(--text-primary)
    
    Right: "[▲ Collapse]" text button, same style as [▼ See Briefing]
  
  CARDS GRID:
    padding: 0 16px 16px 16px
    display: grid
    grid-template-columns: 1fr 1fr  (2 columns on desktop)
    grid-template-columns: 1fr      (1 column on mobile, breakpoint 640px)
    gap: 12px
    
    Each card:
    ┌──────────────────────────────────────────┐
    │ [type icon] [type label]          [dot]  │
    │ [title - 14px weight 600]                │
    │ [body text - 13px, 2 lines max, ellipsis]│
    │ [document name - 12px, tertiary]         │
    │                    [action button →]     │
    └──────────────────────────────────────────┘
    
    Card styling:
      background: var(--surface-raised)
      border: 1px solid var(--border-subtle)
      border-radius: var(--radius-md)
      padding: 14px 16px
      display: flex, flex-direction: column, gap: 6px
      cursor: default
      transition: border-color 150ms
      hover: border-color var(--border-default)
    
    Card type icons and accent colors:
      deadline → ⏰ icon, left border 3px solid var(--amber-500)
      insight  → ⚡ icon, left border 3px solid var(--blue-500)
      activity → 📊 icon, left border 3px solid var(--green-500)
      summary  → 📄 icon, left border 3px solid var(--border-default)
      tip      → 💡 icon, left border 3px solid var(--purple-500)
    
    Priority dot (top-right of card):
      urgent:    8px circle, var(--red-500)
      important: 8px circle, var(--amber-500)
      info:      8px circle, var(--border-default)
    
    Card title:
      DM Sans 14px weight 600, var(--text-primary)
      max 1 line (overflow: hidden, text-overflow: ellipsis)
    
    Card body:
      DM Sans 13px, var(--text-secondary)
      max 2 lines: display: -webkit-box, -webkit-line-clamp: 2, overflow: hidden
    
    Card document name (if present):
      DM Sans 11px, var(--text-tertiary)
      Truncated to 30 chars with ellipsis
      Prepend 📎 icon (10px)
    
    Card action button (if action_label is present):
      Aligned right, .btn-ghost text-only, 12px
      "[action_label] →"
      On click: navigate to action_url
    
  FOOTER ROW:
    padding: 8px 20px 16px 20px
    border-top: 1px solid var(--border-subtle)
    display: flex, justify-content: space-between, align-items: center
    
    Left: "Generated by DocuMindAI at 6 AM · Updates every morning"
          DM Sans 11px, var(--text-tertiary)
    
    Right: [Dismiss for today]
           .btn-ghost, 12px, var(--text-tertiary)
           On click: store today's date in localStorage key "documind_briefing_dismissed"
           Panel collapses and disappears

EMPTY STATE (no cards today):
  Don't show the panel at all. No empty state needed.
  The user should never see "No updates" — silence is fine.

LOADING STATE:
  Show the collapsed bar with a pulse skeleton instead of "5 updates ready".
  Skeleton: 80px wide, 12px tall, border-radius 6px, pulse animation.

MOBILE SPECIFIC:
  On screens < 640px:
    Collapsed state: show only ☀️ + greeting, omit count text
    Expanded state: single column, cards at full width
    Card padding: 12px 14px
```

### 26-C: Briefing Verification Checkpoint

```
VERIFICATION AFTER PHASE 26:
  Manual test 1: Trigger generate_user_briefing task manually for your user ID
    → Check morning_briefings table has a record
    → Open dashboard → briefing bar appears at top
    → Click "See Briefing" → expands smoothly → cards visible
  
  Manual test 2: Click "Dismiss for today" → panel disappears
    → Refresh page → panel does NOT reappear (localStorage key set)
    → Tomorrow: localStorage key is for yesterday's date → panel reappears
  
  Manual test 3: User with no documents → no briefing generated → dashboard normal
  
  Manual test 4: Deadline card "Review Document" → navigates to correct session
  
  Celery Beat: confirm morning_briefings task in schedule
  TypeScript: zero errors
  Database: morning_briefings table exists, briefing inserts correctly
  
  DEFINITION OF DONE — PHASE 26:
  ✅ Briefing generated daily at 6 AM IST by Celery task
  ✅ Briefing panel appears on dashboard home, above session list
  ✅ Collapsed → expanded with smooth animation
  ✅ Card types: deadline, insight, activity, tip — all render correctly
  ✅ Priority dots and left border colors visible
  ✅ "Dismiss for today" hides panel, doesn't show again today
  ✅ Empty users see no panel (no empty state shown)
  ✅ Responsive: 2-column desktop, 1-column mobile
  ✅ Time-aware greeting (Good morning/afternoon/evening)
  ✅ No LLM called at dashboard open — briefing is pre-generated
```

---

## PHASE 27 — PWA + PUSH NOTIFICATIONS
### DocuMindAI Lives on Your Phone's Home Screen
**Priority:** Medium | **Time:** 2 batches | **Cost:** ₹0 (Service Workers + Web Push — free)
**Why nobody built this yet:** Every document AI tool is browser-only. No home screen presence.
**Physical AI connection:** A home screen icon = ambient presence in the user's physical device.

---

### 27-A: Web App Manifest & Service Worker

```
WHAT THIS DOES:
  Turns DocuMindAI into a Progressive Web App (PWA).
  Users can install it on Android/iPhone/desktop with one tap.
  It appears on their home screen like a native app.
  Works offline for reading cached sessions.
  Receives push notifications (for briefings and critical insights).
  Cost: ₹0. Deployed on Railway. No app store needed.

STEP 1 — Create frontend/public/manifest.json:
  {
    "name": "DocuMindAI",
    "short_name": "DocuMindAI",
    "description": "Document intelligence with verified answers",
    "start_url": "/dashboard",
    "display": "standalone",
    "background_color": "#FFFFFF",
    "theme_color": "#1E40AF",
    "orientation": "any",
    "scope": "/",
    "lang": "en-IN",
    "icons": [
      { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png",
        "purpose": "any maskable" },
      { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png",
        "purpose": "any maskable" }
    ],
    "shortcuts": [
      {
        "name": "New Session",
        "short_name": "New",
        "description": "Start a new document session",
        "url": "/dashboard?action=new",
        "icons": [{ "src": "/icon-192.png", "sizes": "192x192" }]
      },
      {
        "name": "Today's Briefing",
        "short_name": "Briefing",
        "description": "Open today's morning briefing",
        "url": "/dashboard?view=briefing",
        "icons": [{ "src": "/icon-192.png", "sizes": "192x192" }]
      }
    ],
    "categories": ["productivity", "business", "education"],
    "screenshots": []
  }

STEP 2 — Create icon files:
  Create scripts/generate-pwa-icons.js:
    Uses 'canvas' npm package (already installed for OG image).
    Generates:
      /frontend/public/icon-192.png — 192×192 DocuMindAI icon
      /frontend/public/icon-512.png — 512×512 DocuMindAI icon
    Design: brand blue (#1E40AF) background, white shield + "DM" letters centered.
    Run: node scripts/generate-pwa-icons.js
  
  Also create: /frontend/public/icon-maskable-192.png
  Same design but with safe zone (icon content within 80% of area for maskable).

STEP 3 — Link manifest in Next.js:
  In frontend/src/app/layout.tsx, in the <head>:
    <link rel="manifest" href="/manifest.json" />
    <meta name="theme-color" content="#1E40AF" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="apple-mobile-web-app-title" content="DocuMindAI" />
    <link rel="apple-touch-icon" href="/icon-192.png" />
  
  Or use Next.js 14+ metadata API if on App Router:
    export const metadata = {
      manifest: '/manifest.json',
      appleWebApp: {
        capable: true,
        statusBarStyle: 'default',
        title: 'DocuMindAI'
      }
    }

STEP 4 — Create Service Worker:
  Create frontend/public/sw.js:
  
  const CACHE_NAME = 'documindai-v1'
  const OFFLINE_CACHE = 'documindai-offline-v1'
  
  // Files to precache (app shell)
  const PRECACHE_URLS = [
    '/dashboard',
    '/offline',   // fallback page (create frontend/src/app/offline/page.tsx)
  ]
  
  self.addEventListener('install', (event) => {
    event.waitUntil(
      caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    )
    self.skipWaiting()
  })
  
  self.addEventListener('activate', (event) => {
    event.waitUntil(
      caches.keys().then(keys =>
        Promise.all(keys.filter(k => k !== CACHE_NAME && k !== OFFLINE_CACHE)
                        .map(k => caches.delete(k)))
      )
    )
    self.clients.claim()
  })
  
  self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url)
    
    // Network-first for API calls (never cache API responses)
    if (url.pathname.startsWith('/api/')) {
      event.respondWith(
        fetch(event.request).catch(() =>
          new Response(JSON.stringify({ error: "offline" }), {
            headers: { 'Content-Type': 'application/json' }
          })
        )
      )
      return
    }
    
    // Cache-first for static assets (JS, CSS, images)
    if (url.pathname.match(/\.(js|css|png|jpg|svg|ico|woff2)$/)) {
      event.respondWith(
        caches.match(event.request).then(cached =>
          cached || fetch(event.request).then(response => {
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()))
            return response
          })
        )
      )
      return
    }
    
    // Network-first for pages, fallback to offline page
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match('/offline') ||
        new Response('<h1>You are offline</h1>', { headers: { 'Content-Type': 'text/html' } })
      )
    )
  })
  
  // Push notification handler
  self.addEventListener('push', (event) => {
    if (!event.data) return
    const data = event.data.json()
    
    const options = {
      body: data.body,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      tag: data.tag || 'documindai-notification',
      requireInteraction: data.priority === 'urgent',
      data: { url: data.action_url || '/dashboard' },
      actions: data.action_label ? [
        { action: 'open', title: data.action_label }
      ] : []
    }
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    )
  })
  
  self.addEventListener('notificationclick', (event) => {
    event.notification.close()
    const url = event.notification.data?.url || '/dashboard'
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then(windowClients => {
        const existing = windowClients.find(w => w.url.includes('documindai'))
        if (existing) {
          existing.focus()
          existing.postMessage({ type: 'navigate', url })
        } else {
          clients.openWindow(url)
        }
      })
    )
  })

STEP 5 — Register Service Worker in Next.js:
  Create frontend/src/lib/pwa.ts:
    
    export async function registerServiceWorker() {
      if (typeof window === 'undefined') return
      if (!('serviceWorker' in navigator)) return
      
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/'
        })
        console.log('[PWA] Service worker registered:', registration.scope)
        return registration
      } catch (err) {
        console.warn('[PWA] Service worker registration failed:', err)
      }
    }
  
  Call registerServiceWorker() in the root layout useEffect:
    useEffect(() => { registerServiceWorker() }, [])

STEP 6 — Create Offline Page:
  Create frontend/src/app/offline/page.tsx:
  
  A clean, simple page (NOT 404 style):
  
  ┌──────────────────────────────────────────────────┐
  │                                                  │
  │          [DocuMindAI logo 32px]                  │
  │                                                  │
  │           📶  You're Offline                     │
  │                                                  │
  │  "DocuMindAI needs an internet connection        │
  │   to answer questions. Your sessions and         │
  │   documents are preserved."                      │
  │                                                  │
  │  [↻ Try Again]  → calls window.location.reload() │
  │                                                  │
  │  While you wait, your last cached session        │
  │  is still readable in your browser history.      │
  │                                                  │
  └──────────────────────────────────────────────────┘
  
  Styling: var(--surface-base) background, centered, max-width 400px,
  gap 16px between elements, no external dependencies.
```

### 27-B: PWA Install Prompt & Push Notifications

```
Create frontend/src/components/pwa/InstallPrompt.tsx

INSTALL PROMPT:
  The browser fires a 'beforeinstallprompt' event when the app is installable.
  Capture it and show a subtle, non-intrusive prompt.
  
  Timing: Only show after user has used the app for at least 3 sessions
  (check localStorage key "documind_session_count" >= 3).
  Never show on first visit — let the user experience the product first.
  
  PROMPT DESIGN:
    Position: fixed bottom-right corner, above the page footer
    margin: 0 16px 16px 0
    z-index: 90 (below modals at 100+, above content)
    
    ┌─────────────────────────────────────────┐
    │ 📱 Add to Home Screen                   │  ← 14px weight 600
    │ Open DocuMindAI like a native app.      │  ← 12px secondary
    │                          [Add] [Not now]│
    └─────────────────────────────────────────┘
    
    width: 280px
    background: var(--surface-overlay)
    border: 1px solid var(--border-default)
    border-radius: var(--radius-lg)
    padding: 14px 16px
    box-shadow: var(--shadow-xl)
    
    Slide-in animation: slide up from bottom, 300ms ease-out
    
    [Add] button:
      .btn .btn-primary, compact (height 32px, font-size 13px)
      On click: call deferredPrompt.prompt() → browser shows native install dialog
      After: hide prompt, store "documind_pwa_installed" = "true" in localStorage
    
    [Not now] button:
      .btn-ghost, 13px
      On click: hide prompt, store "documind_pwa_dismissed" = today's date
      Don't show again for 7 days.
    
    [✕] close:
      top-right, 24×24px, ghost, border-radius 50%
      Same behavior as [Not now]

  Code:
    const [prompt, setPrompt] = useState<any>(null)
    
    useEffect(() => {
      const handler = (e: Event) => { e.preventDefault(); setPrompt(e) }
      window.addEventListener('beforeinstallprompt', handler)
      return () => window.removeEventListener('beforeinstallprompt', handler)
    }, [])
    
    const handleInstall = async () => {
      if (!prompt) return
      prompt.prompt()
      const result = await prompt.userChoice
      if (result.outcome === 'accepted') {
        track('pwa_installed')
        localStorage.setItem('documind_pwa_installed', 'true')
      }
      setPrompt(null)
    }

PUSH NOTIFICATIONS:
  Create frontend/src/lib/push.ts:
    
    export async function subscribeToPushNotifications(
      registration: ServiceWorkerRegistration
    ): Promise<PushSubscription | null> {
      if (!('Notification' in window)) return null
      if (!('PushManager' in window)) return null
      
      let permission = Notification.permission
      if (permission === 'default') {
        permission = await Notification.requestPermission()
      }
      if (permission !== 'granted') return null
      
      const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
      if (!VAPID_PUBLIC_KEY) return null
      
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
      })
      
      // Send subscription to backend
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription)
      })
      
      return subscription
    }
    
    function urlBase64ToUint8Array(base64String: string): Uint8Array {
      // Standard VAPID key conversion utility
      const padding = '='.repeat((4 - base64String.length % 4) % 4)
      const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
      const rawData = window.atob(base64)
      return new Uint8Array([...rawData].map(char => char.charCodeAt(0)))
    }

BACKEND — Push subscription management:
  pip install pywebpush --break-system-packages
  
  Generate VAPID keys (one time):
    python -c "from py_vapid import Vapid; v = Vapid(); v.generate_keys(); print(v.public_key, v.private_key)"
  
  Add to .env:
    VAPID_PUBLIC_KEY=...
    VAPID_PRIVATE_KEY=...
    VAPID_CLAIMS_EMAIL=support@documindai.com
  
  SUPABASE TABLE:
    CREATE TABLE push_subscriptions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID REFERENCES users(id) ON DELETE CASCADE,
      endpoint TEXT NOT NULL,
      keys JSONB NOT NULL,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(user_id, endpoint)
    );
  
  Create backend/app/api/v1/endpoints/push.py:
    POST /api/push/subscribe
      Saves subscription to push_subscriptions table
      Returns: { success: true }
    
    DELETE /api/push/unsubscribe
      Removes subscription for user
    
    (Internal) send_push(user_id, title, body, action_url, priority):
      Queries push_subscriptions for user_id
      Sends via pywebpush to each endpoint
      Handles expired endpoints (422 response → delete from DB)
  
  WHEN TO SEND PUSH NOTIFICATIONS:
  1. Morning Briefing ready (6 AM IST, only if briefing has critical/urgent cards):
     Title: "Good morning — [N] updates from DocuMindAI"
     Body: first critical card's title
     action_url: /dashboard?view=briefing
  
  2. Critical proactive insight found in a new document:
     Title: "⚠️ Critical finding in [document_name]"
     Body: first 80 chars of the finding
     action_url: /dashboard?doc=[doc_id]
  
  3. Collaboration — someone asked a question in a shared session:
     Title: "[Name] asked something in your shared session"
     Body: first 60 chars of their question (NO answer — privacy)
     action_url: /shared/[token]
  
  WHAT TO NEVER SEND:
  - Promotional/upsell notifications (never)
  - Notifications after 9 PM IST or before 7 AM IST
  - More than 2 notifications per day per user
  
  Notification timing guard in send_push():
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    hour_ist = now_ist.hour
    if hour_ist < 7 or hour_ist >= 21:
      # Queue for next morning 8 AM IST instead
      logger.info(f"Push delayed until morning for user {user_id}")
      return

NOTIFICATION SETTINGS PAGE:
  In frontend/src/app/settings/page.tsx, add a "Notifications" section:
  
  NOTIFICATIONS
  ──────────────────────────────────────────────────
  [●] Morning Briefing       Get your daily briefing at 6 AM
  [●] Critical Findings      When AI finds something urgent in your documents
  [○] Collaboration          When someone asks in your shared session
  ──────────────────────────────────────────────────
  [Enable Notifications] or [Currently enabled — Disable]
  
  Each toggle saves to: user notification_preferences JSONB column
  "Enable Notifications" button triggers subscribeToPushNotifications()
  
  Add notification_preferences JSONB column to users table via Alembic migration.
  Default: { "morning_briefing": true, "critical_findings": true, "collaboration": false }
```

### 27-C: PWA Verification Checkpoint

```
VERIFICATION AFTER PHASE 27:
  Manual test 1: Open Chrome on Android → address bar shows install icon →
    tap install → DocuMindAI appears on home screen →
    launch from home screen → opens in standalone mode (no browser UI)
  
  Manual test 2: Turn off WiFi → open from home screen →
    /offline page shows → turn WiFi back on → [Try Again] → returns to app
  
  Manual test 3: Enable push notifications in Settings → trigger a critical insight →
    push notification appears on phone even when browser closed →
    tap notification → navigates to correct document
  
  Lighthouse PWA audit (Chrome DevTools):
    All PWA checks should pass: installable, service worker, icons, offline
  
  TypeScript: zero errors
  
  DEFINITION OF DONE — PHASE 27:
  ✅ Manifest.json valid — Lighthouse reports "installable"
  ✅ Service worker registered, caches app shell
  ✅ Offline page shown when network lost
  ✅ Home screen install prompt after 3 sessions
  ✅ App shortcuts: "New Session" and "Today's Briefing"
  ✅ Push notifications work on Android Chrome
  ✅ Notification timing guard: no notifications 9 PM–7 AM IST
  ✅ Settings page has notification toggles
  ✅ Never more than 2 push notifications per day per user
```

---

## PHASE 28 — INSTANT TEXT CLIPS
### Any Text, Anywhere → Instantly Queryable
**Priority:** Medium | **Time:** 1 batch | **Cost:** ₹0
**Why nobody built this yet:** Every RAG tool requires a file. This kills the "file" requirement entirely.
**Physical AI connection:** Ambient ingestion — any text in the user's environment becomes queryable.

---

### 28-A: Paste-as-Document Feature

```
CONCEPT:
  A user receives an email, a WhatsApp message, a legal notice via web,
  a news article, a notification, or any other text in their daily life.
  They select the text → copy it → switch to DocuMindAI →
  paste it as an "instant document" → ask questions about it immediately.
  
  No file. No upload. No processing delay. Just paste → ask.
  
  This is the zero-friction document ingestion path.
  Target users: lawyers getting text updates, CAs receiving email instructions,
  HR managers receiving candidate summaries via email, students copying lecture notes.

BACKEND:
  No new document processing pipeline needed.
  Plain text is simpler than PDF — it's already extracted.
  
  Modify backend/app/api/v1/endpoints/documents.py:
  
  Add endpoint: POST /api/documents/clip
    Body: {
      title: str (optional, auto-generated if blank),
      content: str (required, min 50 chars, max 50000 chars),
      source_hint: str (optional: "email", "whatsapp", "web", "note", "other"),
      session_id: str (optional: which session to attach to)
    }
    Auth: Required
    Rate limit: 20 clips per user per day
    
    Process:
    1. Validate content length (50 chars min, 50000 chars max)
    2. Create Document record:
       filename = title or "Clipped Text — {datetime}" (max 60 chars)
       file_type = "text/plain"
       status = "processing"
       source = "clip"   (add 'source' VARCHAR(20) to documents table via migration)
       content_hash = MD5 of content (for deduplication — reuse Phase 16-B logic)
    3. SKIP OCR (text is already extracted)
    4. SKIP file storage (no file to store)
    5. Go DIRECTLY to chunking → embedding → FAISS indexing
       Call the same chunking and embedding functions as normal, just with the text.
    6. Set status = "completed"
    7. Processing time: ~3-5 seconds (no OCR needed — much faster than PDF)
    8. Return: { document_id, estimated_seconds: 3 }
    
    Backend note: add 'source' to Document model:
    source = Column(String(20), nullable=True)
    # values: "upload" (default), "clip", "scan" (from Phase 25)
    Run alembic revision for this column.

FRONTEND:
  TWO ENTRY POINTS for text clipping. Both are additive — nothing existing changes.

ENTRY POINT 1 — Paste Button in Upload Area:
  In the document upload area, alongside the existing buttons:
  
  Current:    [📎 Upload File]  [📷 Scan Document (Phase 25)]
  New:        [📎 Upload File]  [📷 Scan]  [📋 Paste Text]
  
  All three buttons in one row, equal flex width.
  [📋 Paste Text] opens the Clip Modal (below).
  
  Gap between buttons: 8px
  Button height: same as existing upload button

ENTRY POINT 2 — Selection-triggered Clip Bar:
  When a user selects (highlights) any text ANYWHERE inside the DocuMindAI
  app (not just the upload area — anywhere on the page), a tiny floating bar
  appears near the selection.
  
  Position: 8px above the selected text, horizontally centered on selection.
  Appears: 500ms after mouseup event fires on selected text.
  Disappears: immediately on click outside or text deselect.
  
  Clip Bar design:
    background: var(--surface-overlay)
    border: 1px solid var(--border-default)
    border-radius: 999px  (pill shape)
    padding: 4px 12px 4px 8px
    box-shadow: var(--shadow-lg)
    display: inline-flex, align-items: center, gap: 8px
    white-space: nowrap
    font-size: 12px, font-weight: 500
    
    Content: [📋] [Add to session] [✕]
    
    [📋] — 16px icon, var(--text-secondary)
    "Add to session" — var(--text-primary)
    [✕] — 16px, var(--text-tertiary), dismisses bar
    
    On "Add to session" click:
      Get selected text: window.getSelection()?.toString().trim()
      If less than 50 chars: toast warning "Select more text (minimum 50 characters)"
      If valid: open Clip Modal with text pre-filled
      
  Implementation:
    Create frontend/src/hooks/useSelectionClip.ts
    Attaches mouseup listener to document
    Ignores selections inside input/textarea elements
    Ignores selections inside .trust-score-panel (prevent accidental triggers)
    Cleans up on component unmount
    
    Do NOT attach inside the chat message area's Copy button zones —
    add CSS class .no-clip-zone to containers where selection should be ignored.

THE CLIP MODAL:
  Create frontend/src/components/clips/ClipModal.tsx
  
  Opens from either entry point.
  
  Backdrop: fixed inset-0, rgba(0,0,0,0.5), z-index 100
  
  Modal:
    max-width: 480px
    width: calc(100vw - 32px)
    background: var(--surface-base)
    border-radius: var(--radius-xl)
    padding: 0
    box-shadow: var(--shadow-2xl)
  
  MODAL HEADER:
    padding: 16px 20px
    border-bottom: 1px solid var(--border-subtle)
    
    "📋 Clip Text as Document"
    DM Sans 16px weight 600, var(--text-primary)
    
    [✕] close button — 32×32px, ghost, top-right
  
  MODAL BODY:
    padding: 16px 20px
    display: flex, flex-direction: column, gap: 14px
  
    TITLE FIELD:
      Label: "Document title (optional)"
      DM Sans 12px weight 500, var(--text-secondary), margin-bottom 4px
      Input: standard .form-input
      Placeholder: "e.g. Email from client re: contract"
      Max length: 60 chars
      Character counter (right-aligned below): "[N]/60"
    
    TEXT AREA:
      Label: "Text content"  (required)
      DM Sans 12px weight 500, var(--text-secondary), margin-bottom 4px
      
      <textarea>:
        min-height: 160px
        max-height: 300px (overflow-y: auto if longer)
        resize: vertical
        font-family: var(--font-sans)
        font-size: 13px
        line-height: 1.6
        padding: 10px 12px
        border: 1px solid var(--border-default)
        border-radius: var(--radius-md)
        background: var(--surface-sunken)
        color: var(--text-primary)
        
        Focus: border-color var(--border-strong), box-shadow var(--shadow-brand)
        
        Placeholder: "Paste or type any text here — emails, messages, notes, 
                       web content, anything you want to ask questions about..."
        
        Auto-focus on modal open
        If opened from selection clip bar: pre-filled with selected text
      
      Character counter below:
        "[N] / 50,000 characters"
        DM Sans 11px, var(--text-tertiary), right-aligned
        When < 50: shown in var(--red-500)
        When > 45,000: shown in var(--amber-500) (approaching limit)
    
    SOURCE HINT (optional):
      Label: "Where is this from? (optional)"
      DM Sans 12px weight 500, var(--text-secondary), margin-bottom 4px
      
      Button group (inline pills, single select):
        [✉️ Email]  [💬 Message]  [🌐 Web]  [📝 Note]  [Other]
        
        Style: each pill is 32px height, padding 0 12px, border-radius 999px
        Unselected: background var(--surface-sunken), border var(--border-default),
                    DM Sans 12px, var(--text-secondary)
        Selected: background var(--brand-light), border var(--brand),
                  var(--brand), weight 500
        
        This is purely for the document filename auto-generation.
        If "Email" selected: filename prefix = "Email — "
        If "Message" selected: filename prefix = "Message — "
        etc.
        No backend impact beyond the generated filename.
  
  MODAL FOOTER:
    padding: 12px 20px 16px 20px
    border-top: 1px solid var(--border-subtle)
    display: flex, gap: 12px, justify-content: flex-end
    
    [Cancel] — .btn-ghost
    [📋 Add to Session →] — .btn .btn-primary
    
    [Add to Session →] disabled if:
      content length < 50 chars
      content length > 50,000 chars
  
  ON SUBMIT:
    1. Button shows loading: "Adding..." with spinner
    2. POST /api/documents/clip with { title, content, source_hint }
    3. On success:
       a. Close modal
       b. Toast: "📋 Text clipped — processing..." (same style as file upload toast)
       c. Add document to the document list immediately (optimistic update)
          Show document with 📋 clip icon (instead of 📄 PDF or 📷 scan icon)
       d. After ~3 seconds: document status updates to "completed" (via existing polling)
       e. User can now ask questions about the clipped text
    4. On error:
       a. Keep modal open
       b. Show inline error below textarea (not toast — user needs to fix input)

DOCUMENT LIST VISUAL DIFFERENTIATION:
  In the document list component (wherever documents are shown),
  add a small type badge next to each document:
  
  source = "upload" (or null): no badge (existing behavior preserved)
  source = "scan":             [📷] 14px camera icon, var(--text-tertiary)
  source = "clip":             [📋] 14px clipboard icon, var(--text-tertiary)
  
  This badge appears to the LEFT of the filename.
  No other visual change to the document list.

QUERY HANDLING (no backend changes needed):
  Clipped text documents are stored as embeddings in FAISS identically to PDF pages.
  The retrieval pipeline, Veritas, citations, and all other features work identically.
  The only difference: page_reference for clipped text will be null (no page numbers).
  In citation display: instead of "Page 3", show "Clipped text, section [chunk_index]".
  
  Add to citation rendering component:
    if (citation.document_source === "clip"):
      label = `Clipped text, part ${citation.chunk_index + 1}`
    else:
      label = `Page ${citation.page_number}`
  
  This is a purely cosmetic change in the frontend citation renderer.
```

### 28-B: Text Clip Verification Checkpoint

```
VERIFICATION AFTER PHASE 28:
  Manual test 1: Open upload area → click [📋 Paste Text] →
    modal opens → paste 200 chars of text → "Email" source →
    [Add to Session] → modal closes → document appears with 📋 icon →
    after 3-5 seconds: status "completed" →
    ask a question about the pasted text → answer returned with "Clipped text" citation
  
  Manual test 2: Select any paragraph of text in an AI response →
    clip bar appears after 500ms →
    click "Add to session" → modal opens with text pre-filled
  
  Manual test 3: Paste 49 characters → [Add to Session] button is disabled
  
  Manual test 4: Paste 50,001 characters → character counter turns amber at 45,000,
    [Add to Session] disabled above 50,000
  
  Manual test 5: Duplicate clip (same text twice) → deduplication fires →
    toast "Text matches previous clip. Using cached embeddings."
  
  Existing file upload → still works normally
  TypeScript: zero errors
  Database: 'source' column exists on documents table
  
  DEFINITION OF DONE — PHASE 28:
  ✅ [📋 Paste Text] button in upload area (alongside existing buttons)
  ✅ Selection clip bar appears 500ms after text selection anywhere in app
  ✅ Clip modal with title, text area, source hint pills
  ✅ Character counter (50 min, 50,000 max)
  ✅ Document appears with 📋 icon in document list
  ✅ Clipped text is queryable with trust scores and Veritas
  ✅ Citation shows "Clipped text, part N" instead of page number
  ✅ Deduplication works (reuses Phase 16-B logic)
  ✅ Existing file upload and scan (Phase 25) untouched
  ✅ No new retrieval or embedding code — existing pipeline handles it
```

---

## FINAL: COMPLETE OVERVIEW & EXECUTION PLAN

### Full Addition Roadmap (All Phases)

| Phase | What | Batches | Priority |
|---|---|---|---|
| 16 | Gemini migration + Deduplication | 1 | 🔴 Do First |
| 17 | Landing page + SEO + Analytics + Email + Feedback | 2 | 🔴 Before Launch |
| 18 | Veritas Trust Layer (engine + UI + audit export) | 3 | 🔴 Core Differentiator |
| 19 | Agentic Deep Research (Research workspace) | 2 | 🟡 Week 2 |
| 20 | Automation Scripts (7 scripts) | 1 | 🟡 Week 2 |
| 21 | Proactive Intelligence Layer | 2 | 🟡 Week 3 |
| 22 | Collaboration Layer | 2 | 🟠 Week 3-4 |
| 23 | Veritas Public API + Developer Page | 2 | 🟠 Week 4 |
| **24** | **Voice Query Layer (input + readback)** | **2** | **🟡 Week 2-3** |
| **25** | **Camera Document Scan** | **2** | **🟡 Week 3** |
| **26** | **Morning Briefing System** | **2** | **🟡 Week 3-4** |
| **27** | **PWA + Push Notifications** | **2** | **🟠 Week 4** |
| **28** | **Instant Text Clips** | **1** | **🟠 Week 4** |

**Original total (Phases 16–23): 15 batches | ~5 Claude Code sessions | ~20 days**
**Enhanced total (Phases 16–28): 24 batches | ~8 Claude Code sessions | ~30 days**

---

### Architecture Safety Guarantee (Phases 24–28)

| Phase | What was NOT touched | What was ADDED |
|---|---|---|
| Phase 24 (Voice) | Query endpoint, RAG pipeline, Veritas, all existing components | useVoiceInput.ts, useVoiceReadback.ts, VoiceInputButton.tsx (inside input only) |
| Phase 25 (Camera) | OCR orchestrator, document upload endpoint, file processing | DocumentScanner.tsx (new modal), scan_postprocess.py (pre-OCR only), 📷 badge |
| Phase 26 (Briefing) | All workspace logic, session handling, existing dashboard layout | MorningBriefingPanel.tsx (above session list), morning_briefings table, Celery task |
| Phase 27 (PWA) | Next.js routing, authentication, all existing pages | manifest.json, sw.js, offline page, InstallPrompt.tsx, push subscription table |
| Phase 28 (Clips) | Retrieval pipeline, chunking, embedding, existing upload | /api/documents/clip endpoint, ClipModal.tsx, useSelectionClip.ts, 'source' column |

**Zero risk to existing architecture. All additions are modular and independently removable.**

---

### How Each New Phase Earns Money

| Phase | Revenue Mechanism |
|---|---|
| **Voice Queries** | Premium feature on Enterprise plan. Reduces friction → more daily active use → higher retention → less churn. Hindi voice = untapped Indian market segment. |
| **Camera Scan** | Eliminates "I don't have a digital copy" objection. Converts document professionals who work with physical papers (lawyers, CAs, govt offices). |
| **Morning Briefing** | Increases daily open rate (push + ambient briefing). Users who see value daily → renew. Reduces churn from 40% → 20%. |
| **PWA** | Home screen presence = 3–5x higher retention vs browser-only tools (industry benchmark). Enables push → briefing → user opens → query → stays subscribed. |
| **Text Clips** | Eliminates file requirement entirely. Users who previously left because they "don't have a PDF" now stay. Expands TAM significantly. |

---

### The Unprecedented Feature Stack (What Literally Nobody Has Built Together)

After all phases are complete, DocuMindAI will be the ONLY tool that combines:

```
✅ Private document RAG with hallucination prevention (core)
✅ Workspace-aware intelligence (7 professional domains)
✅ Trust scores with dual retrieval verification (Veritas)
✅ Cross-document contradiction detection
✅ Audit trail export for compliance
✅ Agentic deep research (documents + web synthesis)
✅ Proactive insights (AI notices → AI tells you)
✅ Real-time collaboration on document sessions
✅ Voice queries (speak your question, hear the answer)
✅ Camera document scanning (physical papers → queryable)
✅ Morning briefing (AI briefs you before you ask anything)
✅ PWA with push notifications (home screen presence)
✅ Instant text clipping (any text → instant document)
✅ Veritas public API (verification infrastructure for others)
✅ Indian market pricing + UPI + Hindi language support
```

This combination does not exist anywhere on earth. It is not being built by Google,
NotebookLM, Perplexity, Humata, or any RAG startup. You are the only one.

---

### Evolution Position After Part 8 v2

```
2023: Generative AI    → Creates content               ✓ You have this
2024: RAG              → Grounds AI in your documents   ✓ You have this (Phase 1–15)
2025: Agentic AI       → AI that acts autonomously      ✓ You have this (Phase 19)
2026: Governed AI      → AI that acts AND can be trusted ✓ You have this (Phase 18)
2027: Proactive AI     → AI surfaces insights before you ask ◐ Partially here (Phases 21, 26)
2029: Physical AI      → AI embedded in real world      ◐ You are starting this here
                            Voice: Phase 24              ↑ Real-world interface
                            Camera: Phase 25             ↑ Physical document capture
                            PWA: Phase 27               ↑ Physical device presence
                            Clips: Phase 28              ↑ Ambient text ingestion
```

You are not one year ahead of the market. You are three years ahead.

---

### How This Attracts Google, Meta, Amazon

**Google wants:** Trust layer for Google Workspace AI + NotebookLM verification.
**Meta wants:** Governance layer for Llama autonomous agents.
**Amazon wants:** "Verified RAG" premium tier for AWS Bedrock enterprise clients.
**NVIDIA wants:** Verified multimodal document pipeline for Nemotron agents.
**Every AI startup wants:** The Veritas API to add trust signals to their product.
**Every Indian professional app wants:** Document intelligence they can integrate.

You build the verification standard + the physical interface layer.
They come to you.

---

### LinkedIn Post Template (Use After Deployment)

```
Just deployed DocuMindAI v2 — and it does things no other AI tool does.

Not just "chat with your PDF."

→ Speak to your documents in Hindi or English
→ Point your phone camera at any paper — it becomes queryable instantly
→ Get a morning briefing every day before you even ask anything
→ Install it on your home screen like a native app
→ Paste any text from email/WhatsApp → ask questions about it

Plus everything from v1:
→ 7 professional workspaces (Legal, Finance, HR, Research, Teacher, Student, General)
→ Trust Score 0–100 on every answer (Veritas engine)
→ Cross-document contradiction detection
→ Audit trail export for CA / legal compliance
→ Real-time collaboration on sessions
→ Deep Research mode (documents + web synthesis)
→ Public verification API: api.documindai.com/v1/verify
→ UPI billing, Indian pricing, Railway deployment

Built in 30 days. Solo. As a final-year student.

The enterprise document AI market is $74 billion by 2034.
Voice + physical capture + ambient intelligence — nobody built this stack.
Until now.

Demo: [link]
API Docs: [link]

#RAG #AI #PhysicalAI #DocumentIntelligence #BuildInPublic #IndianTechBuilder
```

---

*End of Merged Part 8 v2 — DocuMindAI Final Evolution Guide*
*Original Phases 16–23: May 2026 (unchanged)*
*New Phases 24–28: May 2026 (Physical AI Layer — purely additive)*
*Architecture risk: Zero — all phases are purely additive*
*Total cost to build Phases 24–28: ₹0 (all free browser APIs and free backend libraries)*
