# Fix 1: Backend — multi-doc query uses all sources at once (no empty-filter bug)
# Fix 2: Frontend — readiness gate + blueprint column headers

with open('backend/agents/routes.py', encoding='utf-8') as f:
    content = f.read()

# Remove broken multi-doc routes
idx = content.find('\n# ── Student Mode ──────────────────────────────────────────────────────────────')
if idx != -1:
    content = content[:idx]
    print(f"Removed from position {idx}")

FIXED_ROUTES = '''

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
    return "\\n\\n---\\n\\n".join(
        f"[Page {c.get(\'page\',\'?\')}]\\n{c.get(\'chunk\',\'\')}" for c in chunks
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

    focus_str = f"\\nSpecial focus: {focus}" if focus else ""
    qna_str = "\\n5. LIKELY EXAM QUESTIONS (5 per unit with brief model answers)." if include_qna else ""
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

    prompt = f"""Generate exactly {count} exam-style flashcards on \'{topic}\' from this content.
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

    desc_str = f"\\nSpecial instructions from teacher: {description}" if description else ""
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
        section_blueprint += f"\\n- {n}: {nq} questions x {mq} marks each = {nq*mq} marks{sub_note}"
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
'''

content = content.rstrip() + '\n' + FIXED_ROUTES
with open('backend/agents/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("agents/routes.py: fixed OK")

import ast
ast.parse(open('backend/agents/routes.py', encoding='utf-8').read())
print("Syntax: OK")
