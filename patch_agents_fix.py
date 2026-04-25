# Fix student + multi-doc teacher routes to use correct helper pattern

with open('backend/agents/routes.py', encoding='utf-8') as f:
    content = f.read()

# Remove the broken async routes added earlier
BROKEN_START = '\n# ── Student Mode ──────────────────────────────────────────────────────────────\n@router.post("/student/study-plan")'
BROKEN_END = '            "reused": False, "status": "Processing"}'

# Find and remove the broken section
if '/student/study-plan' in content:
    # Find start of broken section
    idx_start = content.find('\n# ── Student Mode')
    if idx_start != -1:
        content = content[:idx_start]
        print(f"Removed broken section from position {idx_start}")

CORRECT_ROUTES = '''

# ── Student Mode ──────────────────────────────────────────────────────────────

@router.post("/student/study-plan")
def student_study_plan(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Time-based study plan from multiple documents."""
    doc_ids   = body.get("doc_ids", [])
    time_plan = body.get("time_plan", "1 day")
    focus     = body.get("focus", "")
    include_qna = body.get("include_qna", True)

    if not doc_ids:
        raise HTTPException(status_code=400, detail="Provide at least one doc_id")

    combined_text = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if not doc or doc.is_indexed != 1:
            continue
        source = _clean_filename(doc.filename)
        ctx, _ = _get_context(current_user.id, source, "summarize all topics", 25)
        if ctx:
            combined_text.append(f"[Document: {doc.original_name}]\\n{ctx}")

    if not combined_text:
        raise HTTPException(status_code=404, detail="No valid indexed documents found")

    context = "\\n\\n".join(combined_text)[:12000]
    focus_str = f"\\nSpecial focus: {focus}" if focus else ""
    qna_str = "\\n5. LIKELY EXAM QUESTIONS (5 per unit with brief model answers)." if include_qna else ""

    prompt = f"""You are an expert academic tutor. A student has {time_plan} to prepare.{focus_str}

Based on these documents:
{context}

Create a complete, actionable study plan for {time_plan} preparation:

1. PRIORITY TOPICS (highest exam importance first)
2. TIME SCHEDULE (break {time_plan} into slots — what to cover in each)
3. KEY CONCEPTS (ultra-concise bullets per unit/topic)
4. MUST-KNOW FORMULAS / DEFINITIONS (the non-negotiables){qna_str}
6. LAST-MINUTE TIPS (what to focus on in final 15 minutes)

Be specific, actionable, prioritize ruthlessly."""

    return {"study_plan": call_gemini(prompt, GEMINI_MODEL), "time_plan": time_plan, "doc_count": len(doc_ids)}


@router.post("/student/flashcards")
def student_flashcards(body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Q&A flashcards from multiple documents."""
    doc_ids = body.get("doc_ids", [])
    topic   = body.get("topic", "all topics")
    count   = min(body.get("count", 20), 50)

    combined_text = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if not doc or doc.is_indexed != 1:
            continue
        source = _clean_filename(doc.filename)
        ctx, _ = _get_context(current_user.id, source, topic, 20)
        if ctx:
            combined_text.append(ctx)

    if not combined_text:
        raise HTTPException(status_code=404, detail="No valid indexed documents found")

    context = "\\n\\n".join(combined_text)[:10000]
    prompt = f"""Generate {count} exam-style flashcards on '{topic}' from this content.
Format each as:
Q: [question]
A: [concise answer]
---

Content:
{context}"""
    return {"flashcards": call_gemini(prompt, GEMINI_MODEL), "topic": topic}


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
        raise HTTPException(status_code=400, detail="Provide at least one doc_id")

    combined_text = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if not doc or doc.is_indexed != 1:
            continue
        source = _clean_filename(doc.filename)
        ctx, _ = _get_context(current_user.id, source, "all topics concepts definitions", 20)
        if ctx:
            combined_text.append(f"[{doc.original_name}]\\n{ctx}")

    if not combined_text:
        raise HTTPException(status_code=404, detail="No valid indexed documents found")

    context = "\\n\\n".join(combined_text)[:12000]
    desc_str = f"\\nSpecial instructions: {description}" if description else ""

    section_blueprint = ""
    total_marks = 0
    for s in sections:
        n = s.get("name", "Part")
        mq = s.get("marks_each", 5)
        nq = s.get("num_questions", 5)
        sub = " (with sub-questions a, b, c)" if s.get("allow_sub") else ""
        section_blueprint += f"\\n- {n}: {nq} questions x {mq} marks each = {nq*mq} marks{sub}"
        total_marks += nq * mq

    prompt = f"""You are an expert exam paper setter for {exam_style} level.
Create a professional question paper with these exact sections:{section_blueprint}
Total marks: {total_marks}
Difficulty: {difficulty}{desc_str}

Source content:
{context}

Format exactly as a real exam paper:
- Header: Exam Title, Total Marks: {total_marks}, Time: ___ Hours
- Each section clearly labeled
- Questions numbered correctly
- Sub-questions labeled (a), (b), (c) where applicable
- Marks shown in brackets [marks] after each question
{"- Include complete Answer Key at the end." if include_answers else ""}

Include at least one table/comparison question if content supports it."""

    return {
        "question_paper": call_gemini(prompt, GEMINI_MODEL),
        "total_marks": total_marks,
        "sections": len(sections),
        "doc_count": len(doc_ids)
    }
'''

content = content.rstrip() + '\n' + CORRECT_ROUTES
with open('backend/agents/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("agents/routes.py: student + multi-teacher routes fixed OK")

# Verify syntax
import ast
ast.parse(open('backend/agents/routes.py', encoding='utf-8').read())
print("Syntax check: OK")
