import hashlib
import uuid
import logging
from typing import Union
from fastapi import UploadFile, HTTPException
from sqlalchemy import select
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
    ) -> Union[Document, dict]:
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
        md5_obj = hashlib.md5()
        size_bytes = 0

        while chunk := await file.read(8192):
            file_hash_obj.update(chunk)
            md5_obj.update(chunk)
            size_bytes += len(chunk)
            # Enforce 50MB Max File Size to prevent denial of service
            if size_bytes > 50 * 1024 * 1024:
                logger.warning(f"[Security Audit] Denial of Service attempt blocked. File too large from user {owner_id}")
                raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

        await file.seek(0)
        file_hash = file_hash_obj.hexdigest()
        content_hash = md5_obj.hexdigest()

        # 3. Deduplication check — before any storage or processing
        existing_result = await db.execute(
            select(Document).where(
                Document.owner_id == owner_id,
                Document.content_hash == content_hash,
                Document.status == DocumentStatus.READY,
            )
        )
        existing_doc = existing_result.scalar_one_or_none()
        if existing_doc:
            new_doc = Document(
                filename=file.filename,
                file_hash=file_hash,
                mime_type=file.content_type,
                size_bytes=size_bytes,
                storage_path=existing_doc.storage_path,
                status=DocumentStatus.DEDUPLICATED,
                owner_id=owner_id,
                workspace_id=workspace_id,
                content_hash=content_hash,
                source="upload",
            )
            db.add(new_doc)
            try:
                await db.commit()
                await db.refresh(new_doc)
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to persist deduplicated document: {str(e)}")
                raise HTTPException(status_code=500, detail="Database persistence failed")
            return {
                "document_id": str(new_doc.id),
                "status": "deduplicated",
                "duplicate_of": existing_doc.filename,
                "message": f"This document matches '{existing_doc.filename}'. Using cached embeddings — instant processing!"
            }

        # Not a duplicate — proceed with normal processing
        # 4. Secure Distributed Storage Strategy
        doc_uuid = uuid.uuid4()
        object_key = f"workspaces/{workspace_id}/{doc_uuid}.pdf"
        storage_uri = await storage_service.save_upload_file(file, object_key)

        # 5. Database Persistence — save content_hash after successful processing
        db_doc = Document(
            id=doc_uuid,
            filename=file.filename,
            file_hash=file_hash,
            mime_type=file.content_type,
            size_bytes=size_bytes,
            storage_path=storage_uri,
            status=DocumentStatus.UPLOADED,
            owner_id=owner_id,
            workspace_id=workspace_id,
            content_hash=content_hash,
            source="upload",
        )
        db.add(db_doc)
        try:
            await db.commit()
            await db.refresh(db_doc)
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to persist document metadata: {str(e)}")
            raise HTTPException(status_code=500, detail="Database persistence failed")

        # 6. Async Processing Hook
        process_document.delay(str(db_doc.id))

        return db_doc
