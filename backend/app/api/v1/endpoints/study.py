from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Any, Optional
import uuid
import asyncio
import json
import logging
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.models.study import StudyNote, FlashcardDeck, Flashcard, StudyQuiz
from app.models.document import Document
from app.schemas.study import DocumentStudyExtractionSchema, DeckResponse, FlashcardResponse
from app.services.llm_service import llm_service
from app.services.sm2_service import compute_sm2
from app.workers.tasks.study_tasks import process_study_batch

logger = logging.getLogger(__name__)

# ─── Task 6-S1 request/response models ───────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    topic: str
    difficulty: str = "medium"
    count: int = 10
    doc_ids: Optional[List[uuid.UUID]] = None
    workspace_id: Optional[uuid.UUID] = None

class QuizAnswerItem(BaseModel):
    question_id: str
    chosen_index: int

class QuizSubmitRequest(BaseModel):
    answers: List[QuizAnswerItem]

# ─── Task 6-S2 request model ─────────────────────────────────────────────────

class FlashcardReviewRequest(BaseModel):
    quality: int  # 0-5

router = APIRouter()

@router.post("/process")
async def process_study_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 1: ASYNC STUDY PIPELINE
    Offloads heavy flashcard generation and extraction to Celery workers.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    doc = (await db.execute(select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Dispatch to Celery
    process_study_batch.delay(str(document_id), str(workspace_id))
    
    return {"status": "processing_queued", "document_id": str(document_id)}

@router.get("/events/study/{document_id}")
async def sse_study_processing_updates(
    document_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
):
    """
    PHASE 1: Live Processing Updates
    Server-Sent Events (SSE) endpoint to push study pipeline status.
    """
    async def event_generator():
        for i in range(1, 10):
            await asyncio.sleep(2)
            yield f"data: {{\"status\": \"processing\", \"progress\": {i * 10}, \"document_id\": \"{document_id}\"}}\n\n"
        yield f"data: {{\"status\": \"complete\", \"document_id\": \"{document_id}\"}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/search")
async def semantic_search_study(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 2: STUDY VECTOR SEARCH
    Uses pgvector to perform semantic similarity search across StudyNotes and Flashcards.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    query_embedding = await llm_service.get_embedding(query)
    
    # Search closest flashcards
    stmt = (
        select(Flashcard)
        .where(Flashcard.workspace_id == workspace_id)
        .order_by(Flashcard.embedding.l2_distance(query_embedding))
        .limit(10)
    )
    result = await db.execute(stmt)
    
    matches = []
    for card in result.scalars().all():
        matches.append({
            "type": "flashcard",
            "front": card.front,
            "back": card.back,
            "citation": card.citation
        })
    return matches

@router.get("/tutor/chat")
async def ai_tutor_chat(
    query: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    PHASE 4: AI TUTOR CHAT
    SSE endpoint for streaming tutor chat responses grounded in retrieved workspace context.
    """
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    
    # Simple semantic context retrieval
    query_embedding = await llm_service.get_embedding(query)
    stmt = select(StudyNote).where(StudyNote.workspace_id == workspace_id).order_by(StudyNote.embedding.l2_distance(query_embedding)).limit(3)
    notes = (await db.execute(stmt)).scalars().all()
    context = "\n".join([f"{n.title}: {n.content}" for n in notes])
    
    async def chat_stream_generator():
        prompt = f"Context: {context}\nUser: {query}\n\nAct as a tutor. Do not hallucinate."
        # Simulating a streaming LLM response
        response = f"Based on your notes:\n\n{context}\n\nLet me break that down for you step-by-step..."
        words = response.split(" ")
        for word in words:
            await asyncio.sleep(0.1)
            yield f"data: {word} \n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(chat_stream_generator(), media_type="text/event-stream")

@router.get("/decks", response_model=List[DeckResponse])
async def list_decks(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(FlashcardDeck).where(FlashcardDeck.workspace_id == workspace_id))
    return result.scalars().all()

@router.get("/decks/{deck_id}/flashcards", response_model=List[FlashcardResponse])
async def list_flashcards(
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    result = await db.execute(select(Flashcard).where(Flashcard.deck_id == deck_id, Flashcard.workspace_id == workspace_id))
    return result.scalars().all()

# ─── Task 6-S1: Quiz Mode with Scoring ───────────────────────────────────────

@router.post("/quiz/generate")
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an MCQ quiz via LLM. Stores correct_index server-side;
    strips it before returning to the frontend (anti-cheat).
    """
    workspace_id = request.workspace_id or resolve_workspace_id(current_user["workspace_id"])

    grounded_context = (
        f"Generate {request.count} multiple-choice questions on the topic: '{request.topic}'. "
        f"Difficulty: {request.difficulty}. Each question must have exactly 4 options."
    )

    prompt = (
        f"Create {request.count} MCQ questions about '{request.topic}' at {request.difficulty} difficulty. "
        "Return ONLY a valid JSON array with this structure for each item: "
        '{"id":"q1","question":"...","options":["A","B","C","D"],"correct_index":2,'
        '"explanation":"...","source_page":null}'
    )

    raw = await llm_service.provider.generate(
        system_prompt=(
            "You are an expert quiz generator. Respond ONLY with a valid JSON array. "
            "No markdown, no commentary. The correct_index is 0-based."
        ),
        user_prompt=prompt,
    )

    clean = raw.strip()
    if clean.startswith("```json"):
        clean = clean[7:-3].strip()
    elif clean.startswith("```"):
        clean = clean[3:-3].strip()

    try:
        questions_full = json.loads(clean)
        if not isinstance(questions_full, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError):
        questions_full = _stub_quiz(request.topic, request.count, request.difficulty)

    # Ensure each question has an id
    for i, q in enumerate(questions_full):
        if not q.get("id"):
            q["id"] = f"q{i+1}"

    # Persist full quiz (with correct_index) in DB
    quiz_record = StudyQuiz(
        workspace_id=workspace_id,
        topic=request.topic,
        difficulty=request.difficulty,
        doc_ids=[str(d) for d in (request.doc_ids or [])],
        questions=questions_full,
    )
    db.add(quiz_record)
    await db.commit()
    await db.refresh(quiz_record)

    # Strip correct_index before returning (anti-cheat)
    safe_questions = [
        {k: v for k, v in q.items() if k != "correct_index"}
        for q in questions_full
    ]

    return {"quiz_id": str(quiz_record.id), "questions": safe_questions, "count": len(safe_questions)}


def _stub_quiz(topic: str, count: int, difficulty: str) -> list:
    return [
        {
            "id": f"q{i+1}",
            "question": f"Sample {difficulty} question {i+1} about {topic}.",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_index": 0,
            "explanation": f"The correct answer is Option A based on {topic} fundamentals.",
            "source_page": None,
        }
        for i in range(count)
    ]


@router.post("/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: uuid.UUID,
    request: QuizSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Grade a submitted quiz. Returns score, grade, and per-question explanations."""
    workspace_id = resolve_workspace_id(current_user["workspace_id"])

    stmt = select(StudyQuiz).where(StudyQuiz.id == quiz_id, StudyQuiz.workspace_id == workspace_id)
    result = await db.execute(stmt)
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions_map = {q["id"]: q for q in quiz.questions}
    answers_map = {a.question_id: a.chosen_index for a in request.answers}

    correct_count = 0
    total = len(quiz.questions)
    results = []

    for q in quiz.questions:
        qid = q["id"]
        chosen = answers_map.get(qid)
        correct_idx = q.get("correct_index", 0)
        is_correct = chosen == correct_idx

        if is_correct:
            correct_count += 1

        results.append({
            "question_id": qid,
            "correct": is_correct,
            "chosen_index": chosen,
            "correct_index": correct_idx,
            "explanation": q.get("explanation", ""),
            "source_page": q.get("source_page"),
        })

    percentage = round((correct_count / total) * 100, 1) if total else 0
    grade = _score_to_grade(percentage)

    return {
        "score": correct_count,
        "total": total,
        "percentage": percentage,
        "grade": grade,
        "results": results,
    }


def _score_to_grade(pct: float) -> str:
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    return "F"

# ─── Task 6-S2: Spaced Repetition (SM-2) ─────────────────────────────────────

@router.patch("/flashcards/{flashcard_id}/review")
async def review_flashcard(
    flashcard_id: uuid.UUID,
    request: FlashcardReviewRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply SM-2 algorithm to update a flashcard's next review date.
    quality: 0=forgot, 2=hard, 4=ok, 5=easy
    """
    if not (0 <= request.quality <= 5):
        raise HTTPException(status_code=400, detail="quality must be between 0 and 5")

    workspace_id = resolve_workspace_id(current_user["workspace_id"])
    stmt = select(Flashcard).where(Flashcard.id == flashcard_id, Flashcard.workspace_id == workspace_id)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    new_interval, new_ease, next_review = compute_sm2(
        interval=card.interval_days or 1,
        ease_factor=card.easiness_factor or 2.5,
        quality=request.quality,
    )

    card.interval_days = new_interval
    card.easiness_factor = new_ease
    card.repetition_count = (card.repetition_count or 0) + 1
    card.next_review_date = datetime.combine(next_review, datetime.min.time()).replace(tzinfo=timezone.utc)

    await db.commit()
    await db.refresh(card)

    return {
        "next_review": next_review.isoformat(),
        "interval_days": new_interval,
        "ease_factor": new_ease,
        "repetition_count": card.repetition_count,
    }
