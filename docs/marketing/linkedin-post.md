# LinkedIn Launch Post — DocuMindAI

*Copy-paste ready. Adjust tone as needed for your personal voice.*

---

## Version A — Technical Audience (Recommended)

---

I've been working on an open-source project for the past several months, and I'm shipping it publicly today.

**DocuMindAI** — an AI document intelligence platform built around a zero-hallucination policy.

Here's the problem it addresses: knowledge workers — lawyers, analysts, researchers — increasingly use AI to query documents. But general AI assistants hallucinate. They blend document content with training-data knowledge and produce confident, plausible-sounding answers that can be factually wrong. For high-stakes professional work, that's not acceptable.

**The approach I took:**

Instead of trying to prompt the LLM to "not hallucinate," I made hallucination architecturally impossible. The pipeline enforces a strict token budget — only retrieved document evidence reaches the LLM. When evidence is absent, the system explicitly refuses to answer, rather than guessing.

On top of that:

— **Hybrid retrieval** — semantic search (pgvector + BAAI/bge-m3) fused with BM25 keyword search via Reciprocal Rank Fusion. Neither technique alone captures all query patterns.

— **Veritas Trust Engine** — a post-generation scoring layer (0–100) that evaluates citation density, structural alignment, hedging language, and source coherence before the answer reaches the user.

— **7 specialized workspaces** — General, HR, Legal, Finance, Study, Research, and Exam — each independently tuned for its domain's document types and retrieval patterns.

**Stack:** FastAPI (async) · SQLAlchemy v2 · Celery · PostgreSQL 16 + pgvector · Redis · Next.js 16 · React 19 · TypeScript · Google Gemini · BAAI/bge-m3 · PaddleOCR · Docling · OpenTelemetry

**What I found most interesting technically:**

Enforcing zero-hallucination at the architecture level required careful grounding service design — not just prompt engineering. The trust scoring system required thinking about what makes an AI answer *trustworthy* as a structured multi-factor evaluation, not just a binary pass/fail.

The project is fully open source under MIT at **github.com/kanwa2006/DocuMindAI**.

I'd genuinely appreciate feedback from anyone working in:
- AI/ML engineering
- RAG systems and retrieval
- Enterprise document workflows
- Open-source full-stack development

What would you test first? And what limitations do you see in the zero-hallucination approach?

#AI #OpenSource #RAG #FastAPI #NextJS #MachineLearning #DocumentAI #Python

---

## Version B — Broader Audience

---

I just open-sourced a project I'm really proud of: **DocuMindAI** 🧠

It's an AI system that answers questions about your documents — but unlike ChatGPT or other general AI tools, it:

✅ Only answers from your actual documents — not from its training data
✅ Shows you the exact page and passage its answer comes from
✅ Scores every answer with a "trust score" (0–100) before you see it
✅ Says *"I cannot answer this"* when it doesn't have enough evidence — instead of making something up

It supports 7 different use cases:
→ General document Q&A
→ HR and resume screening
→ Legal contract review
→ Financial statement analysis
→ Study and flashcards
→ Academic research
→ Exam paper generation

The whole thing is open source, self-hostable with Docker, and built with FastAPI + Next.js + PostgreSQL.

If you work with a lot of documents professionally and have thought about using AI for it, I'd love your perspective on what's missing or what would make this genuinely useful for you.

GitHub: **github.com/kanwa2006/DocuMindAI**

#AI #Documents #OpenSource #Productivity

---

## Version C — Concise (for reposting or summary)

---

Shipping DocuMindAI v1.0.0 today — open source, MIT license.

It's an AI document intelligence platform with a zero-hallucination policy:
- Hybrid retrieval (pgvector + BM25 + RRF)
- Veritas Trust Score on every answer
- 7 specialized workspaces
- Grounded citations to source pages
- Refuses to answer when evidence is absent

Stack: FastAPI · Next.js 16 · PostgreSQL + pgvector · Gemini · Celery

→ github.com/kanwa2006/DocuMindAI

Feedback welcome — especially from people working with RAG systems, enterprise document workflows, or AI reliability.

---

## Posting Tips

- Post Version A on a Tuesday or Wednesday, 8–10am local time (highest LinkedIn engagement)
- Include the GitHub link in the first comment (not the post body) for better reach — LinkedIn suppresses external links
- Add 3–5 relevant hashtags (already included above)
- Pin the post to your profile after publishing
- Respond to every comment in the first 2 hours — this boosts distribution significantly
