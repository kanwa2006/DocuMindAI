import logging
from app.workers.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.document_page import DocumentPage
from app.models.document_chunk import DocumentChunk
from app.services.ocr_service import OCRService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import embedding_service
from app.core.storage import storage_service
import tempfile
import os
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="app.workers.tasks.document_tasks.process_document")
def process_document(self, document_id: str):
    """
    Executes the OCR pipeline using a synchronous DB session inside the Celery worker.
    """
    logger.info(f"[Tracing] Task started: process_document for {document_id}")
    
    db = SyncSessionLocal()
    try:
        # 1. Fetch document
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found.")
            return {"status": "error", "detail": "Document not found"}
            
        # 2. Transition: PROCESSING
        doc.status = DocumentStatus.PROCESSING
        db.commit()
        
        # 3. Distributed Extraction Pipeline
        logger.info(f"Extracting text for {doc.filename} from {doc.storage_path}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            local_temp_path = tmp.name
            
        try:
            storage_service.download_file(doc.storage_path, local_temp_path)
            
            # Check file size to prevent worker crash
            from app.core.config import settings
            file_size_mb = os.path.getsize(local_temp_path) / (1024 * 1024)
            if file_size_mb > settings.MAX_UPLOAD_MB:
                raise ValueError(f"Document exceeds maximum size of {settings.MAX_UPLOAD_MB}MB")
                
            page_stream = OCRService.extract_document_stream(local_temp_path)
            
            # 4. Persistence, Chunking, and Embedding (Batched)
            total_chunks = 0
            total_pages = 0
            batch_size = 50 # Batch size for embeddings and DB commits
            current_batch_chunks = []
            
            for p_data in page_stream:
                total_pages += 1
                page_record = DocumentPage(
                    document_id=doc.id,
                    page_number=p_data["page_number"],
                    extracted_text=p_data["extracted_text"],
                    layout_metadata=p_data["layout_metadata"]
                )
                db.add(page_record)
                db.flush() # Need ID for chunk FK
                
                chunks = ChunkingService.chunk_page_text(p_data["extracted_text"], p_data["layout_metadata"])
                for idx, c in enumerate(chunks):
                    chunk_record = DocumentChunk(
                        document_id=doc.id,
                        page_id=page_record.id,
                        chunk_index=idx,
                        text_content=c["text_content"],
                        chunk_metadata=c["chunk_metadata"]
                    )
                    db.add(chunk_record)
                    current_batch_chunks.append(chunk_record)
                    total_chunks += 1
                    
                # Batch processing
                if len(current_batch_chunks) >= batch_size:
                    db.flush()
                    texts_to_embed = [c.text_content for c in current_batch_chunks]
                    vectors = embedding_service.generate_embeddings(texts_to_embed)
                    for chunk_record, vector in zip(current_batch_chunks, vectors):
                        chunk_record.embedding = vector
                    db.commit() # Commit this batch to avoid ballooning transaction
                    current_batch_chunks = []
                    
            # Process remaining chunks
            if current_batch_chunks:
                db.flush()
                texts_to_embed = [c.text_content for c in current_batch_chunks]
                vectors = embedding_service.generate_embeddings(texts_to_embed)
                for chunk_record, vector in zip(current_batch_chunks, vectors):
                    chunk_record.embedding = vector
                db.commit()
        finally:
            if os.path.exists(local_temp_path):
                os.remove(local_temp_path)
        

                
        # 5. Transition: EXTRACTED -> READY
        doc.status = DocumentStatus.EXTRACTED
        db.flush() 
        doc.status = DocumentStatus.READY
        db.commit()
        
        logger.info(f"[Tracing] Task successful: {total_pages} pages, {total_chunks} chunks extracted for {document_id}")
        return {"document_id": document_id, "pages": total_pages, "chunks": total_chunks, "status": "success"}
        
    except Exception as e:
        logger.error(f"[Tracing] Task failed for {document_id} - {str(e)}")
        db.rollback()
        
        try:
            self.retry(exc=e, countdown=2 ** self.request.retries, max_retries=3)
        except MaxRetriesExceededError:
            logger.error(f"[Tracing] Max retries exceeded for {document_id}. Moving to Dead-Letter Queue.")
            doc_fail = db.query(Document).filter(Document.id == document_id).first()
            if doc_fail:
                doc_fail.status = DocumentStatus.FAILED
                db.commit()
            return {"status": "error", "detail": "Dead letter threshold reached", "original_error": str(e)}
    finally:
        db.close()
