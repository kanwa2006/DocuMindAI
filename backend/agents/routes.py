"""
Extended agents for DocuMindAI v2.0 — Professional Modes.

Phase 3: Teacher Mode  - question paper, answer key, syllabus mapping, question bank
Phase 4: HR Mode       - resume parser, job matcher, candidate comparison
Phase 5: Finance Mode  - invoice/statement extraction, anomaly detection
Phase 6: Notes Mode    - handwritten notes summary, revision, keywords
"""
import json
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import User, Document
from backend.auth.routes import get_current_user
from backend.qa.indexer import query_user_index
from backend.qa.chain import call_gemini
from backend.config import GEMINI_MODEL
from backend.documents.storage import get_user_storage_dir

router = APIRouter(prefix="/agents", tags=["agents"])


def _clean_filename(filename: str) -> str:
    basename = os.path.basename(filename)
    parts = basename.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        return parts[1]
    return basename


def _get_doc_or_404(doc_id: int, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
        Document.is_indexed == 1
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found or not yet indexed.")
    return doc


def _get_context(user_id, source, query, top_k=20):
    chunks = query_user_index(user_id, query, top_k=top_k, source_filter=[source])
    if not chunks:
        return None, []
    ctx = "\n\n---\n\n".join(
        f"[Page {c.get('page','?')}]\n{c.get('chunk','')}" for c in chunks
    )
    return ctx, chunks


# ─────────────────────────────────────────────────────────────────────────────
# ORIGINAL AGENTS (kept)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/summarize/{doc_id}")
def agent_summarize(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, chunks = _get_context(current_user.id, _clean_filename(doc.filename), "summarize all main topics", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "Create a STRUCTURED SUMMARY:\n1. Overview (3-4 sentences)\n"
        "2. Section breakdown with bullets\n3. Key Takeaways (5 bullets)\n"
        f"4. Likely exam questions\n\nContent:\n{ctx}\n\nSummary:"
    )
    return {"doc_id": doc_id, "filename": doc.original_name, "summary": call_gemini(prompt, GEMINI_MODEL)}


@router.post("/key-concepts/{doc_id}")
def agent_key_concepts(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename), "key concepts definitions terms", 15)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "Extract ALL key concepts and definitions.\n"
        "Format: **Term** — explanation (1-2 sentences). Group under headings.\n\n"
        f"Content:\n{ctx}\n\nConcepts:"
    )
    return {"doc_id": doc_id, "filename": doc.original_name, "key_concepts": call_gemini(prompt, GEMINI_MODEL)}


@router.post("/export-table/{doc_id}")
def agent_export_table(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _get_doc_or_404(doc_id, current_user, db)
    source = _clean_filename(doc.filename)
    chunks = query_user_index(current_user.id, "table rows columns data", top_k=10, source_filter=[source])
    table_chunks = [c for c in chunks if "[TABLE" in c.get("chunk", "")]
    raw_tables_csv = []
    try:
        import pdfplumber
        fp = os.path.join(get_user_storage_dir(current_user.id), doc.filename)
        if os.path.exists(fp):
            with pdfplumber.open(fp) as pdf:
                for pg_num, page in enumerate(pdf.pages):
                    for t_idx, table in enumerate(page.extract_tables() or []):
                        if not table:
                            continue
                        csv_rows = [",".join(f'"{str(c or "").replace(chr(10)," ").strip()}"' for c in row) for row in table]
                        raw_tables_csv.append({"page": pg_num+1, "table_index": t_idx+1, "csv": "\n".join(csv_rows)})
    except Exception as e:
        print(f"[Table Export] {e}")
    return {
        "doc_id": doc_id, "filename": doc.original_name,
        "tables_found": len(raw_tables_csv),
        "markdown_tables": [c.get("chunk","") for c in table_chunks],
        "csv_tables": raw_tables_csv
    }


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — TEACHER MODE
# ─────────────────────────────────────────────────────────────────────────────

class QuestionPaperRequest(BaseModel):
    doc_id: int
    units: Optional[str] = "all units"
    difficulty: Optional[str] = "mixed"   # easy / medium / hard / mixed
    total_marks: Optional[int] = 100
    num_questions: Optional[int] = 20
    include_answers: Optional[bool] = False

@router.post("/teacher/question-paper")
def teacher_question_paper(req: QuestionPaperRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a complete question paper from a document."""
    doc = _get_doc_or_404(req.doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "topics units chapters questions marks", 25)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    answer_note = "Include model answers after each question." if req.include_answers else "Questions only — no answers."
    prompt = (
        f"You are a professional exam paper setter.\n"
        f"Generate a {req.total_marks}-mark question paper with {req.num_questions} questions.\n"
        f"Units/Topics: {req.units}\nDifficulty: {req.difficulty}\n{answer_note}\n\n"
        "Format:\n"
        "SECTION A — Short Answer (2 marks each)\n"
        "SECTION B — Medium Answer (5 marks each)\n"
        "SECTION C — Long Answer (10 marks each)\n\n"
        "Rules:\n"
        "- Questions ONLY from the document content below\n"
        "- Include marks for each question\n"
        "- Cover all major topics\n"
        "- No repetition\n\n"
        f"Document Content:\n{ctx}\n\nQuestion Paper:"
    )
    result = call_gemini(prompt, GEMINI_MODEL)
    return {"doc_id": req.doc_id, "filename": doc.original_name, "question_paper": result,
            "config": {"marks": req.total_marks, "questions": req.num_questions, "difficulty": req.difficulty}}


@router.post("/teacher/answer-key/{doc_id}")
def teacher_answer_key(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a comprehensive answer key / study guide."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "definitions explanations answers concepts", 25)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "Generate a COMPLETE ANSWER KEY and STUDY GUIDE from this document.\n\n"
        "Format for each topic:\n"
        "### [Topic Name]\n"
        "**1-line definition:** ...\n"
        "**Detailed answer:** ... (3-5 sentences)\n"
        "**Key points:** bullet list\n"
        "**Exam tip:** one line\n\n"
        f"Document Content:\n{ctx}\n\nAnswer Key:"
    )
    return {"doc_id": doc_id, "filename": doc.original_name, "answer_key": call_gemini(prompt, GEMINI_MODEL)}


@router.post("/teacher/syllabus-map/{doc_id}")
def teacher_syllabus_map(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Extract unit → topic → subtopic structure from document."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "unit chapter topic subtopic section", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "Extract the complete SYLLABUS STRUCTURE from this document.\n\n"
        "Return as JSON:\n"
        '{"units": [{"unit": "Unit 1: ...", "topics": [{"topic": "...", "subtopics": ["...", "..."], "pages": [1,2]}]}]}\n\n'
        "If JSON is not possible, use plain text with Unit → Topic → Subtopic hierarchy.\n\n"
        f"Document:\n{ctx}\n\nSyllabus Map:"
    )
    raw = call_gemini(prompt, GEMINI_MODEL)
    try:
        # Try to extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            structured = json.loads(raw[start:end])
        else:
            structured = None
    except Exception:
        structured = None
    return {"doc_id": doc_id, "filename": doc.original_name, "syllabus_map": raw, "structured": structured}


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — HR / RESUME MODE
# ─────────────────────────────────────────────────────────────────────────────

class JobMatchRequest(BaseModel):
    doc_id: int
    job_description: str

@router.post("/hr/parse-resume/{doc_id}")
def hr_parse_resume(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Parse a resume/CV and extract structured fields."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "name email phone education skills experience projects certifications", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "You are a professional HR resume parser.\n"
        "Extract ALL information from this resume/CV.\n\n"
        "Return as JSON:\n"
        '{"name":"","email":"","phone":"","location":"","summary":"","education":[{"degree":"","institution":"","year":"","grade":""}],'
        '"experience":[{"role":"","company":"","duration":"","responsibilities":[]}],'
        '"skills":{"technical":[],"soft":[],"languages":[]},'
        '"projects":[{"name":"","description":"","technologies":[]}],'
        '"certifications":[],"achievements":[],"total_experience_years":""}\n\n'
        f"Resume Content:\n{ctx}\n\nParsed Resume JSON:"
    )
    raw = call_gemini(prompt, GEMINI_MODEL)
    try:
        start = raw.find("{"); end = raw.rfind("}") + 1
        parsed = json.loads(raw[start:end]) if start >= 0 and end > start else None
    except Exception:
        parsed = None
    return {"doc_id": doc_id, "filename": doc.original_name, "parsed_resume": parsed, "raw": raw}


@router.post("/hr/job-match")
def hr_job_match(req: JobMatchRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Match a resume against a job description and score the candidate."""
    doc = _get_doc_or_404(req.doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "skills experience education projects", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "You are an expert HR screening assistant.\n"
        "Compare this resume against the job description and provide a detailed match analysis.\n\n"
        "Return JSON:\n"
        '{"match_score": 0-100, "grade": "A/B/C/D", '
        '"matched_skills": [], "missing_skills": [], '
        '"matched_experience": [], "education_match": "yes/no/partial", '
        '"strengths": [], "gaps": [], '
        '"recommendation": "Shortlist/Maybe/Reject", '
        '"summary": "2-3 sentence verdict"}\n\n'
        f"JOB DESCRIPTION:\n{req.job_description}\n\n"
        f"RESUME CONTENT:\n{ctx}\n\nMatch Analysis JSON:"
    )
    raw = call_gemini(prompt, GEMINI_MODEL)
    try:
        start = raw.find("{"); end = raw.rfind("}") + 1
        analysis = json.loads(raw[start:end]) if start >= 0 and end > start else None
    except Exception:
        analysis = None
    return {"doc_id": req.doc_id, "filename": doc.original_name, "match_analysis": analysis, "raw": raw}


class CompareRequest(BaseModel):
    doc_ids: List[int]
    job_description: Optional[str] = ""

@router.post("/hr/compare-resumes")
def hr_compare_resumes(req: CompareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Compare 2-5 resumes side by side."""
    if not (2 <= len(req.doc_ids) <= 5):
        raise HTTPException(400, "Provide 2-5 resume document IDs.")
    candidates = []
    for doc_id in req.doc_ids:
        doc = _get_doc_or_404(doc_id, current_user, db)
        ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                               "skills experience education", 10)
        candidates.append({"name": doc.original_name, "content": ctx or ""})
    jd_section = f"Job Description:\n{req.job_description}\n\n" if req.job_description else ""
    candidate_sections = "\n\n".join(
        f"=== CANDIDATE {i+1}: {c['name']} ===\n{c['content']}" for i, c in enumerate(candidates)
    )
    prompt = (
        "Compare these candidates side by side.\n"
        f"{jd_section}"
        "Return JSON array:\n"
        '[{"candidate":"name","rank":1,"score":0-100,"skills":[],"experience":"","education":"","strengths":[],"weaknesses":[],"verdict":""}]\n\n'
        "Also add a 'recommendation' field with the best candidate name and reason.\n\n"
        f"{candidate_sections}\n\nComparison:"
    )
    raw = call_gemini(prompt, GEMINI_MODEL)
    try:
        start = raw.find("["); end = raw.rfind("]") + 1
        ranked = json.loads(raw[start:end]) if start >= 0 and end > start else None
    except Exception:
        ranked = None
    return {"candidates": [c["name"] for c in candidates], "comparison": ranked, "raw": raw}


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5 — FINANCE / INVOICE MODE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/finance/extract/{doc_id}")
def finance_extract(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Extract financial data from invoices, statements, receipts."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "amount total date vendor invoice tax GST payment", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "You are a financial document extraction specialist.\n"
        "Extract ALL financial data from this document.\n\n"
        "Return JSON:\n"
        '{"document_type":"invoice/statement/receipt/other",'
        '"vendor":"","customer":"","date":"","due_date":"",'
        '"currency":"","subtotal":0,"tax_amount":0,"total_amount":0,'
        '"line_items":[{"description":"","quantity":0,"unit_price":0,"amount":0}],'
        '"payment_status":"","bank_details":{},'
        '"anomalies":[],"summary":""}\n\n'
        f"Document:\n{ctx}\n\nFinancial Data JSON:"
    )
    raw = call_gemini(prompt, GEMINI_MODEL)
    try:
        start = raw.find("{"); end = raw.rfind("}") + 1
        extracted = json.loads(raw[start:end]) if start >= 0 and end > start else None
    except Exception:
        extracted = None
    return {"doc_id": doc_id, "filename": doc.original_name, "financial_data": extracted, "raw": raw}


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6 — HANDWRITTEN NOTES / REVISION MODE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/notes/summarize/{doc_id}")
def notes_summarize(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Summarize handwritten notes page by page with key concepts."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "notes summary topics concepts", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "These are OCR-extracted handwritten notes. Some words may be unclear.\n"
        "Summarize clearly and extract key concepts.\n\n"
        "Format:\n"
        "## Page-by-Page Summary\n[Page N]: 2-3 line summary\n\n"
        "## Key Concepts\n- **Term**: definition\n\n"
        "## Quick Revision Points\n1. ...\n\n"
        "## Important Formulas / Facts\n- ...\n\n"
        f"Notes Content:\n{ctx}\n\nSummary:"
    )
    return {"doc_id": doc_id, "filename": doc.original_name, "notes_summary": call_gemini(prompt, GEMINI_MODEL)}


@router.post("/notes/revision/{doc_id}")
def notes_revision(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a revision sheet with flashcard-style Q&A from notes."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    ctx, _ = _get_context(current_user.id, _clean_filename(doc.filename),
                           "key points facts definitions formulas", 20)
    if not ctx:
        raise HTTPException(422, "No indexed content found.")
    prompt = (
        "Generate a REVISION SHEET from these notes.\n\n"
        "Format:\n"
        "## Flashcards (Q&A)\nQ: ...\nA: ...\n\n"
        "## One-line Facts\n- ...\n\n"
        "## Formulas & Diagrams (text description)\n- ...\n\n"
        "## 5-Minute Review\n[3-4 paragraph summary]\n\n"
        f"Notes:\n{ctx}\n\nRevision Sheet:"
    )
    return {"doc_id": doc_id, "filename": doc.original_name, "revision_sheet": call_gemini(prompt, GEMINI_MODEL)}


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-DOC HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_multi_context(user_id: int, docs: list, query: str, top_k: int = 30) -> str:
    """
    Query FAISS using ALL source names from selected docs at once.
    This avoids the per-doc empty-result bug and gives richer context.
    """
    # Collect all valid source filenames from selected docs
    sources = [_clean_filename(doc.filename) for doc in docs if doc and doc.is_indexed == 1]
    if not sources:
        return ""
    # If only 1 source, use source_filter; if multiple, pass all at once
    source_filter = sources if len(sources) <= 10 else None  # beyond 10, query all
    chunks = query_user_index(user_id, query, top_k=top_k, source_filter=source_filter)
    if not chunks:
        # Fallback: no source filter (search entire user index)
        chunks = query_user_index(user_id, query, top_k=top_k, source_filter=None)
    if not chunks:
        return ""
    return "\n\n---\n\n".join(
        f"[Page {c.get('page','?')}]\n{c.get('chunk','')}" for c in chunks
    )


def _resolve_docs(doc_ids: list, user_id: int, db) -> list:
    """Resolve doc IDs to indexed Document objects (handles alias docs too)."""
    resolved = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.user_id == user_id
        ).first()
        if not doc:
            continue
        # For alias docs, resolve to canonical for FAISS lookup
        if doc.canonical_doc_id:
            canonical = db.query(Document).filter(Document.id == doc.canonical_doc_id).first()
            if canonical and canonical.is_indexed == 1:
                resolved.append(canonical)
            elif doc.is_indexed == 1:
                resolved.append(doc)
        elif doc.is_indexed == 1:
            resolved.append(doc)
    return resolved


# ─────────────────────────────────────────────────────────────────────────────
# STUDENT MODE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/student/study-plan")
def student_study_plan(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Time-based study plan from multiple documents."""
    doc_ids   = body.get("doc_ids", [])
    time_plan = body.get("time_plan", "1 day")
    focus     = body.get("focus", "")
    include_qna = body.get("include_qna", True)

    if not doc_ids:
        raise HTTPException(400, "Provide at least one doc_id")

    docs = _resolve_docs(doc_ids, current_user.id, db)
    if not docs:
        raise HTTPException(404, "No valid indexed documents found. Wait for processing to complete.")

    ctx = _get_multi_context(current_user.id, docs, "all topics units concepts summary", top_k=35)
    if not ctx:
        raise HTTPException(422, "Could not retrieve content from documents.")

    focus_str = f"\nSpecial focus: {focus}" if focus else ""
    qna_str = "\n5. LIKELY EXAM QUESTIONS (5 per unit with brief model answers)." if include_qna else ""
    doc_names = ", ".join(set(d.original_name for d in docs))

    prompt = f"""You are an expert academic tutor. A student has {time_plan} to prepare.{focus_str}
Documents: {doc_names}

Based on this content:
{ctx}

Create a complete, actionable study plan for {time_plan}:

1. PRIORITY TOPICS (highest exam importance first — be specific)
2. TIME SCHEDULE (break {time_plan} into clear slots — what to cover in each slot)
3. KEY CONCEPTS (ultra-concise bullets — one line per concept, group by unit/topic)
4. MUST-KNOW FORMULAS / DEFINITIONS (non-negotiables — memorize these){qna_str}
6. LAST-MINUTE TIPS (what to focus on in final 15 minutes)

Be specific. Use the actual document content. Prioritize ruthlessly."""

    return {"study_plan": call_gemini(prompt, GEMINI_MODEL), "time_plan": time_plan, "doc_count": len(docs)}


@router.post("/student/flashcards")
def student_flashcards(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Q&A flashcards from multiple documents."""
    doc_ids = body.get("doc_ids", [])
    topic   = body.get("topic", "all topics")
    count   = min(body.get("count", 20), 50)

    if not doc_ids:
        raise HTTPException(400, "Provide at least one doc_id")

    docs = _resolve_docs(doc_ids, current_user.id, db)
    if not docs:
        raise HTTPException(404, "No valid indexed documents found.")

    ctx = _get_multi_context(current_user.id, docs, topic, top_k=25)
    if not ctx:
        raise HTTPException(422, "Could not retrieve content from documents.")

    prompt = f"""Generate exactly {count} exam-style flashcards on '{topic}' from this content.
Format EACH flashcard as:
Q: [clear, specific question]
A: [concise, accurate answer — 1-3 lines]
---

Include a mix of: definitions, application questions, and recall questions.
Content:
{ctx}"""
    return {"flashcards": call_gemini(prompt, GEMINI_MODEL), "topic": topic, "count": count}


# ─────────────────────────────────────────────────────────────────────────────
# TEACHER MULTI-DOC ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/teacher/question-paper-multi")
def teacher_question_paper_multi(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Advanced question paper from multiple docs with multi-section blueprint."""
    doc_ids     = body.get("doc_ids", [])
    sections    = body.get("sections", [])
    difficulty  = body.get("difficulty", "mixed")
    description = body.get("description", "")
    include_answers = body.get("include_answers", False)
    exam_style  = body.get("exam_style", "university")

    if not doc_ids:
        raise HTTPException(400, "Provide at least one doc_id")
    if not sections:
        raise HTTPException(400, "Define at least one section (Part A, Part B, etc.)")

    docs = _resolve_docs(doc_ids, current_user.id, db)
    if not docs:
        raise HTTPException(404, "No valid indexed documents found. Ensure all PDFs are Ready (not Processing).")

    ctx = _get_multi_context(current_user.id, docs, "all topics concepts definitions problems", top_k=40)
    if not ctx:
        raise HTTPException(422, "Could not retrieve content. Ensure documents are fully indexed.")

    desc_str = f"\nSpecial instructions from teacher: {description}" if description else ""
    doc_names = ", ".join(set(d.original_name for d in docs))

    section_blueprint = ""
    total_marks = 0
    for s in sections:
        n  = s.get("name", "Part")
        mq = s.get("marks_each", 5)
        nq = s.get("num_questions", 5)
        qt = s.get("question_type", "mixed")  # direct | sub-question | case-based | mixed
        sub_note = ""
        if qt == "sub-question":
            sub_note = " (each question must have sub-parts: a, b, c)"
        elif qt == "case-based":
            sub_note = " (case-study/scenario based questions)"
        elif qt == "direct":
            sub_note = " (direct questions, no sub-parts)"
        else:
            allow_sub = s.get("allow_sub", False)
            sub_note = " (with sub-questions a,b,c)" if allow_sub else ""
        section_blueprint += f"\n- {n}: {nq} questions x {mq} marks each = {nq*mq} marks{sub_note}"
        total_marks += nq * mq

    prompt = f"""You are a professional exam paper setter for {exam_style} level examinations.

Source documents: {doc_names}
Difficulty: {difficulty}{desc_str}

Create a complete, professional question paper with EXACTLY these sections:
{section_blueprint}

TOTAL MARKS: {total_marks}

STRICT FORMATTING RULES:
1. Start with: Exam Title | Total Marks: {total_marks} | Time: __ Hours | Date: __
2. Label each section clearly (PART A, PART B, PART C, etc.)
3. Number questions within each section starting from 1
4. Show marks in brackets [Xm] after each question
5. For sub-questions: use (a), (b), (c) format
6. For case-based: provide a scenario/case first, then questions based on it
7. Include at least one table or comparison-style question where content allows
8. Make questions that test understanding, not just memorization
{"9. Add complete ANSWER KEY at the end with section-wise answers." if include_answers else ""}

Use ONLY content from the provided documents. Do not invent topics not covered in the source.

Source content:
{ctx}"""

    return {
        "question_paper": call_gemini(prompt, GEMINI_MODEL),
        "total_marks": total_marks,
        "sections": len(sections),
        "doc_count": len(docs),
        "doc_names": doc_names
    }
