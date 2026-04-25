# Adds Student mode backend endpoint to agents/routes.py

with open('backend/agents/routes.py', encoding='utf-8') as f:
    content = f.read()

STUDENT_ROUTE = '''

# ── Student Mode ──────────────────────────────────────────────────────────────
@router.post("/student/study-plan")
async def student_study_plan(body: dict, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Generate a time-based study plan from multiple documents."""
    doc_ids   = body.get("doc_ids", [])
    time_plan = body.get("time_plan", "1 day")   # "30 min" | "1 hour" | "1 day"
    focus     = body.get("focus", "")
    include_qna = body.get("include_qna", True)

    if not doc_ids:
        raise HTTPException(status_code=400, detail="Provide at least one doc_id")

    combined_text = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if not doc:
            continue
        fp = get_doc_path(doc)
        chunks = retrieve_context(current_user.id, f"summarize all topics", doc_path=fp, k=30)
        combined_text.append(f"[Document: {doc.original_name}]\\n" + "\\n".join(chunks))

    if not combined_text:
        raise HTTPException(status_code=404, detail="No valid documents found")

    context = "\\n\\n".join(combined_text)[:12000]
    focus_str = f"\\nSpecial focus: {focus}" if focus else ""
    qna_str = "\\n- Include 5 likely exam questions per unit with brief model answers." if include_qna else ""

    prompt = f"""You are an expert academic tutor. A student has {time_plan} to prepare.
{focus_str}

Based on these documents:
{context}

Create a complete, actionable study plan for {time_plan} preparation:

1. PRIORITY TOPICS (what to study first — highest exam importance)
2. TIME SCHEDULE (break {time_plan} into slots: what to cover in each slot)
3. KEY CONCEPTS (bullet points per unit/topic — ultra-concise)
4. MUST-KNOW FORMULAS / DEFINITIONS (the non-negotiables)
5. QUICK REVISION SHEET (1-line summaries of each major topic){qna_str}
6. LAST-MINUTE TIPS (what to focus on in final 15 minutes before exam)

Be specific, actionable, and prioritize ruthlessly. The student has limited time."""

    text = await call_gemini(prompt)
    return {"study_plan": text, "time_plan": time_plan, "doc_count": len(doc_ids)}


@router.post("/student/flashcards")
async def student_flashcards(body: dict, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Generate Q&A flashcards from multiple documents."""
    doc_ids = body.get("doc_ids", [])
    topic   = body.get("topic", "all topics")
    count   = min(body.get("count", 20), 50)

    combined_text = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if not doc:
            continue
        fp = get_doc_path(doc)
        chunks = retrieve_context(current_user.id, topic, doc_path=fp, k=20)
        combined_text.append("\\n".join(chunks))

    context = "\\n\\n".join(combined_text)[:10000]
    prompt = f"""Generate {count} exam-style flashcards on '{topic}' from this content.
Format each as:
Q: [question]
A: [concise answer]
---

Content:
{context}"""
    text = await call_gemini(prompt)
    return {"flashcards": text, "topic": topic}


@router.post("/teacher/question-paper-multi")
async def teacher_question_paper_multi(body: dict, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Advanced question paper from multiple docs with multi-section blueprint."""
    doc_ids     = body.get("doc_ids", [])
    sections    = body.get("sections", [])   # [{name, marks_each, num_questions, allow_sub}]
    difficulty  = body.get("difficulty", "mixed")
    description = body.get("description", "")
    include_answers = body.get("include_answers", False)
    exam_style  = body.get("exam_style", "university")

    if not doc_ids:
        raise HTTPException(status_code=400, detail="Provide at least one doc_id")

    combined_text = []
    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if not doc:
            continue
        fp = get_doc_path(doc)
        chunks = retrieve_context(current_user.id, "all topics concepts", doc_path=fp, k=25)
        combined_text.append(f"[{doc.original_name}]\\n" + "\\n".join(chunks))

    context = "\\n\\n".join(combined_text)[:12000]
    desc_str = f"\\nSpecial instructions: {description}" if description else ""

    section_blueprint = ""
    total_marks = 0
    for s in sections:
        n = s.get("name", "Part")
        mq = s.get("marks_each", 5)
        nq = s.get("num_questions", 5)
        sub = " (with sub-questions a, b, c)" if s.get("allow_sub") else ""
        section_blueprint += f"\\n- {n}: {nq} questions × {mq} marks each = {nq*mq} marks{sub}"
        total_marks += nq * mq

    prompt = f"""You are an expert exam paper setter for {exam_style} level.
Create a professional question paper with these exact sections:{section_blueprint}
Total marks: {total_marks}
Difficulty: {difficulty}{desc_str}

Source content:
{context}

Format the paper exactly as a real exam paper:
- Header: Exam Title, Total Marks: {total_marks}, Time: ___ Hours
- Each section clearly labeled
- Questions numbered correctly
- Sub-questions labeled (a), (b), (c) where applicable
- Marks shown in brackets after each question
{"- Include a complete Answer Key at the end." if include_answers else ""}

Make questions that test understanding, not just memorization. Include at least one table/comparison question if appropriate."""

    text = await call_gemini(prompt)
    return {"question_paper": text, "total_marks": total_marks, "sections": len(sections), "doc_count": len(doc_ids)}
'''

# Add student routes before the last line
if '/student/study-plan' not in content:
    # Find a good insertion point - before the last router definition or at end
    content = content.rstrip() + '\n' + STUDENT_ROUTE
    with open('backend/agents/routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("agents/routes.py: Student + multi-doc teacher routes added OK")
else:
    print("agents/routes.py: already has student routes")
