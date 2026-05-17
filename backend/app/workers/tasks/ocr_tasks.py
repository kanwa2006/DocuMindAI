import asyncio
import uuid
import logging
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.services.ocr_orchestrator import ocr_orchestrator
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

async def _process_ocr_logic(document_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return

        logger.info(f"Initiating OCR Pipeline for Document {document_id}")
        
        # PHASE 1 & 10: Execute routed OCR extraction (runs on GPU queue)
        try:
            # Pass a mock file path and mime type for prototype
            result = await ocr_orchestrator.extract_document(
                file_path=f"/tmp/docs/{doc.id}.pdf", 
                mime_type="application/pdf", 
                hint="academic" if "research" in doc.filename.lower() else "auto"
            )
            
            logger.info(f"OCR Extraction successful via {result.engine_name} with confidence {result.confidence}")
            
            # Save OCR result / bounding boxes to DB
            # doc.extracted_text = result.text
            # doc.ocr_metadata = {"tables": result.tables, "formulas": result.formulas, "bboxes": result.bounding_boxes}
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"OCR Pipeline failed for {document_id}: {str(e)}")
            await db.rollback()
            raise


@celery_app.task(name="app.workers.tasks.ocr_tasks.extract_document_ocr", bind=True)
def extract_document_ocr(self, document_id: str):
    """
    PHASE 10: PERFORMANCE HARDENING
    Executes heavy OCR tasks specifically on the `ocr-gpu-queue` to prevent
    blocking LLM inference or lightweight CPU queues.
    """
    try:
        asyncio.run(_process_ocr_logic(uuid.UUID(document_id)))
    except Exception as exc:
        logger.error(f"Failed to extract OCR for {document_id}. Retrying...")
        self.retry(exc=exc, countdown=15)
