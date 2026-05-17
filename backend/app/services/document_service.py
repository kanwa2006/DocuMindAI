import hashlib
import uuid
import logging
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentCreate
from app.core.storage import storage_service
from app.workers.tasks.document_tasks import process_document

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = ["application/pdf"]

class DocumentService:
    @staticmethod
    async def ingest_document(
        db: AsyncSession, 
        file: UploadFile, 
        owner_id: uuid.UUID, 
        workspace_id: uuid.UUID | None = None
    ) -> Document:
        # 1. Validation
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported file type. Only PDF is supported currently.")

        # Security Hardening: Validate PDF Magic Number to prevent malicious payload uploads
        magic_number = await file.read(5)
        if magic_number != b"%PDF-":
            logger.warning(f"[Security Audit] Malicious file upload blocked. Invalid signature from user {owner_id}")
            raise HTTPException(status_code=400, detail="Invalid file signature. File is not a valid PDF.")
        await file.seek(0)
        
        # 2. Compute hash and size
        file_hash_obj = hashlib.sha256()
        size_bytes = 0
        
        while chunk := await file.read(8192):
            file_hash_obj.update(chunk)
            size_bytes += len(chunk)
            # Enforce 50MB Max File Size to prevent denial of service
            if size_bytes > 50 * 1024 * 1024:
                logger.warning(f"[Security Audit] Denial of Service attempt blocked. File too large from user {owner_id}")
                raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")
            
        await file.seek(0) # Reset pointer for actual saving
        file_hash = file_hash_obj.hexdigest()
        
        # 3. Secure Distributed Storage Strategy
        # We construct an object key isolating files by workspace to prevent tenant collision
        doc_uuid = uuid.uuid4()
        object_key = f"workspaces/{workspace_id}/{doc_uuid}.pdf"
        storage_uri = await storage_service.save_upload_file(file, object_key)
        
        # 4. Database Persistence
        db_doc = Document(
            id=doc_uuid,
            filename=file.filename,
            file_hash=file_hash,
            mime_type=file.content_type,
            size_bytes=size_bytes,
            storage_path=storage_uri,
            status=DocumentStatus.UPLOADED,
            owner_id=owner_id,
            workspace_id=workspace_id
        )
        db.add(db_doc)
        try:
            await db.commit()
            await db.refresh(db_doc)
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to persist document metadata: {str(e)}")
            raise HTTPException(status_code=500, detail="Database persistence failed")
            
        # 5. Async Processing Hook
        process_document.delay(str(db_doc.id))
        
        return db_doc
