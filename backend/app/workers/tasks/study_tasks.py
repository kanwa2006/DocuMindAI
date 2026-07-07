import asyncio
import uuid
import logging
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.study import StudyNote, FlashcardDeck, Flashcard
from app.models.document import Document
from app.schemas.study import DocumentStudyExtractionSchema
from app.services.llm_service import llm_service
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

async def _process_study_logic(document_id: uuid.UUID, workspace_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return

        logger.info(f"Extracting study materials from {document_id}")
        extracted_text = f"Simulated study material for {doc.filename}. Mitochondria is the powerhouse of the cell. Photosynthesis converts light to energy using chlorophyll."
        
        # Security: Prompt Injection Defense
        if "ignore previous instructions" in extracted_text.lower():
            extracted_text = "SANITIZED: Prompt injection detected."

        extraction = await llm_service.generate_json(
            query="Extract key concepts into study notes and generate associated flashcards.",
            grounded_context=extracted_text,
            response_schema=DocumentStudyExtractionSchema
        )
        
        # Create a Deck for this document
        deck = FlashcardDeck(
            workspace_id=workspace_id,
            title=f"Deck: {doc.filename}",
            description=extraction.document_summary
        )
        db.add(deck)
        await db.flush()
        
        for note_data in extraction.notes:
            note = StudyNote(
                workspace_id=workspace_id,
                document_id=document_id,
                title=note_data.title,
                content=note_data.content,
                tags=note_data.tags
            )
            
            # PHASE 2: Vector Search
            note.embedding = await llm_service.get_embedding(f"{note.title} {note.content}")
            db.add(note)
            
            for fc_data in note_data.flashcards:
                flashcard = Flashcard(
                    workspace_id=workspace_id,
                    deck_id=deck.id,
                    document_id=document_id,
                    front=fc_data.front,
                    back=fc_data.back,
                    citation=fc_data.citation
                )
                
                # PHASE 2: Vector Search
                flashcard.embedding = await llm_service.get_embedding(f"{flashcard.front} {flashcard.back}")
                db.add(flashcard)

        await db.commit()
        logger.info(f"Successfully processed study document {document_id}")


@celery_app.task(name="app.workers.tasks.study_tasks.process_study_batch", bind=True)
def process_study_batch(self, document_id: str, workspace_id: str):
    """
    PHASE 1: ASYNC STUDY PIPELINE
    Offloads heavy flashcard and note generation to Celery workers.
    """
    try:
        asyncio.run(_process_study_logic(uuid.UUID(document_id), uuid.UUID(workspace_id)))
    except Exception as exc:
        logger.error(f"Failed to process study document {document_id}. Retrying...")
        self.retry(exc=exc, countdown=10)
