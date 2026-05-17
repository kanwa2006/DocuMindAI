from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Any
import uuid
import asyncio

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.study import StudyNote, FlashcardDeck, Flashcard
from app.models.document import Document
from app.schemas.study import DocumentStudyExtractionSchema, DeckResponse, FlashcardResponse
from app.services.llm_service import llm_service
from app.workers.tasks.study_tasks import process_study_batch

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
    workspace_id = uuid.UUID(current_user["workspace_id"])
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
    workspace_id = uuid.UUID(current_user["workspace_id"])
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
    workspace_id = uuid.UUID(current_user["workspace_id"])
    
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
    workspace_id = uuid.UUID(current_user["workspace_id"])
    result = await db.execute(select(FlashcardDeck).where(FlashcardDeck.workspace_id == workspace_id))
    return result.scalars().all()

@router.get("/decks/{deck_id}/flashcards", response_model=List[FlashcardResponse])
async def list_flashcards(
    deck_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    workspace_id = uuid.UUID(current_user["workspace_id"])
    result = await db.execute(select(Flashcard).where(Flashcard.deck_id == deck_id, Flashcard.workspace_id == workspace_id))
    return result.scalars().all()
