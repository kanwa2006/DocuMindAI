"""Study material generation (Celery).

P0-7: used `AsyncSessionLocal` in a sync Celery task via `asyncio.run()`; a
pooled asyncpg connection from a previous event loop failed intermittently with
"got Future attached to a different loop". Now `SyncSessionLocal`.

P0-8: `extracted_text` was hardcoded to "Simulated study material for
{filename}. Mitochondria is the powerhouse of the cell. Photosynthesis converts
light to energy using chlorophyll." — so every document a student uploaded
produced flashcards about mitochondria and photosynthesis regardless of subject.
Now reads the document's real chunk text.

P0-9: rows carried only `workspace_id`, a category slug shared by every user.
`owner_id` is derived from the document being processed.
"""
import asyncio
import logging
import uuid

from sqlalchemy.future import select

from app.core.tenant_scope import tenant_scope
from app.db.session import SyncSessionLocal
from app.models.document import Document
from app.models.study import Flashcard, FlashcardDeck, StudyNote
from app.schemas.study import DocumentStudyExtractionSchema
from app.services.llm_service import llm_service
from app.workers.celery_app import celery_app
from app.workers.tasks._document_text import DocumentTextUnavailable, load_document_text

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run one async LLM call on an isolated event loop (see legal_tasks/P0-7)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _process_study_logic(document_id: uuid.UUID, workspace_id: uuid.UUID) -> None:
    db = SyncSessionLocal()
    try:
        doc = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()
        if not doc:
            logger.error("Document %s not found.", document_id)
            return

        owner_id = doc.owner_id  # P0-9: the document's owner is the tenant

        with tenant_scope(owner_id):
            # P0-8: the student's actual material, not the mitochondria stub.
            extracted_text = load_document_text(db, document_id)
            logger.info(
                "Extracting study materials from %s (%d chars)",
                document_id,
                len(extracted_text),
            )

            extraction = _run_async(
                llm_service.generate_json(
                    query=(
                        "Extract key concepts into study notes and generate "
                        "associated flashcards."
                    ),
                    grounded_context=extracted_text,
                    response_schema=DocumentStudyExtractionSchema,
                )
            )

            deck = FlashcardDeck(
                workspace_id=workspace_id,
                owner_id=owner_id,
                title=f"Deck: {doc.filename}",
                description=extraction.document_summary,
            )
            db.add(deck)
            db.flush()

            note_count = card_count = 0
            for note_data in extraction.notes:
                note = StudyNote(
                    workspace_id=workspace_id,
                    owner_id=owner_id,
                    document_id=document_id,
                    title=note_data.title,
                    content=note_data.content,
                    tags=note_data.tags,
                )
                note.embedding = _run_async(
                    llm_service.get_embedding(f"{note.title} {note.content}")
                )
                db.add(note)
                note_count += 1

                for fc_data in note_data.flashcards:
                    flashcard = Flashcard(
                        workspace_id=workspace_id,
                        owner_id=owner_id,
                        deck_id=deck.id,
                        document_id=document_id,
                        front=fc_data.front,
                        back=fc_data.back,
                        citation=fc_data.citation,
                    )
                    flashcard.embedding = _run_async(
                        llm_service.get_embedding(
                            f"{flashcard.front} {flashcard.back}"
                        )
                    )
                    db.add(flashcard)
                    card_count += 1

            db.commit()
            logger.info(
                "Processed study document %s — %d notes, %d flashcards",
                document_id,
                note_count,
                card_count,
            )
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.study_tasks.process_study_batch", bind=True)
def process_study_batch(self, document_id: str, workspace_id: str):
    """PHASE 1: ASYNC STUDY PIPELINE — note and flashcard generation."""
    try:
        _process_study_logic(uuid.UUID(document_id), uuid.UUID(workspace_id))
    except DocumentTextUnavailable:
        # Permanent — retrying cannot produce text extraction never made.
        logger.error("Document %s has no extractable text; not retrying.", document_id)
        raise
    except Exception as exc:
        logger.error("Failed to process study document %s. Retrying...", document_id)
        self.retry(exc=exc, countdown=10)
