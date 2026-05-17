import uuid
import re
import hashlib
import logging
import os
from typing import Optional, List, Any
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.models.document import Document
from app.core.auth import get_current_user
from app.core.config import settings
from app.workers.tasks.document_tasks import process_document
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# S3 client — only initialised when STORAGE_PROVIDER=s3
try:
    import boto3
    _s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL
    ) if settings.STORAGE_PROVIDER == 's3' else None
except Exception:
    _s3_client = None

ALLOWED_MIMES = ["application/pdf"]


class VerifyUploadRequest(BaseModel):
    document_id: str
    filename: str
    object_key: str
    # FIX 0.7: optional metadata the frontend can supply to avoid NOT NULL errors
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None


@router.post("/upload/verify", response_model=DocumentResponse)
async def verify_upload(
    request: VerifyUploadRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Called after a successful S3 PUT or local upload.
    FIX 0.7: supplies fallback values for all NOT NULL columns so IntegrityError
    cannot occur even when the frontend omits optional metadata.
    """
    doc_id = uuid.UUID(request.document_id)
    owner_id = uuid.UUID(current_user["id"])
    workspace_id = current_user.get("workspace_id", "general")

    # Resolve workspace_id to a UUID for the document table
    try:
        ws_uuid = uuid.UUID(workspace_id)
    except (ValueError, AttributeError):
        # workspace_id is a slug like "general" — generate deterministic UUID
        ws_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, workspace_id)

    storage_path = request.object_key

    # FIX 0.7: Compute fallback values — never let NOT NULL columns be None
    file_hash = request.file_hash or hashlib.sha256(storage_path.encode()).hexdigest()
    mime_type = request.mime_type or "application/pdf"
    size_bytes = request.size_bytes
    if size_bytes is None:
        local_path = Path(storage_path)
        size_bytes = local_path.stat().st_size if local_path.exists() else 0

    new_doc = Document(
        id=doc_id,
        filename=request.filename,
        storage_path=storage_path,
        owner_id=owner_id,
        workspace_id=ws_uuid,
        file_hash=file_hash,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # Trigger async OCR/extraction pipeline
    process_document.delay(str(new_doc.id))

    return new_doc


@router.get("/upload/presigned")
async def get_presigned_upload_url(
    filename: str,
    content_type: str,
    file_size: int = 0,
    workspace_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    FIX 0.8: Returns proper local upload URL when STORAGE_PROVIDER=local.
    Frontend checks provider field and switches to multipart POST instead of S3 PUT.
    """
    if content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=415, detail="Only PDF files are accepted.")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_MB}MB."
        )

    document_id = str(uuid.uuid4())
    effective_workspace = workspace_id or current_user.get("workspace_id", "general")
    object_name = f"workspaces/{effective_workspace}/{document_id}_{filename}"

    try:
        if settings.STORAGE_PROVIDER == 's3' and _s3_client:
            presigned_url = _s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': settings.S3_BUCKET,
                    'Key': object_name,
                    'ContentType': content_type
                },
                ExpiresIn=3600
            )
            return {
                "upload_url": presigned_url,
                "document_id": document_id,
                "object_key": object_name,
                "provider": "s3",
                "method": "PUT"
            }
        else:
            # FIX 0.8: Return a real local endpoint instead of a fake mock URL
            return {
                "upload_url": "/api/v1/documents/upload/local",
                "document_id": document_id,
                "object_key": object_name,
                "provider": "local",
                "method": "multipart",
                "workspace_id": effective_workspace
            }
    except Exception as e:
        logger.error(f"Failed to generate upload info: {e}")
        raise HTTPException(status_code=500, detail="Storage initialisation failed")


@router.post("/upload/local")
async def upload_local(
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    FIX 0.8: Local file upload endpoint for development.
    Saves PDF to ./storage/{workspace_id}/ and returns metadata
    needed by the verify endpoint.
    """
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    size = len(content)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.MAX_UPLOAD_MB}MB limit."
        )

    # Sanitise filename to prevent path traversal
    safe_name = re.sub(r'[^\w.\-]', '_', file.filename or "upload.pdf")
    file_hash = hashlib.sha256(content).hexdigest()
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    storage_dir = Path(f"./storage/{workspace_id}")
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_dir / unique_name)

    with open(storage_path, "wb") as f:
        f.write(content)

    logger.info(f"[upload_local] Saved {safe_name} → {storage_path} ({size} bytes)")

    return {
        "storage_path": storage_path,
        "filename": file.filename,
        "size_bytes": size,
        "mime_type": "application/pdf",
        "file_hash": file_hash,
        "workspace_id": workspace_id,
    }


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    workspace_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    FIX 6.6: Accepts optional workspace_id query param to filter documents.
    Falls back to JWT workspace_id. Strict owner isolation enforced.
    """
    effective_workspace = workspace_id or current_user.get("workspace_id", "general")
    try:
        ws_uuid = uuid.UUID(effective_workspace)
    except (ValueError, AttributeError):
        ws_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, effective_workspace)

    stmt = (
        select(Document)
        .where(Document.workspace_id == ws_uuid)
        .where(Document.owner_id == uuid.UUID(current_user["id"]))
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Fetch document metadata. Strict owner + workspace isolation."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid Document ID format.")

    effective_workspace = current_user.get("workspace_id", "general")
    try:
        ws_uuid = uuid.UUID(effective_workspace)
    except (ValueError, AttributeError):
        ws_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, effective_workspace)

    stmt = select(Document).where(
        Document.id == doc_uuid,
        Document.owner_id == uuid.UUID(current_user["id"]),
        Document.workspace_id == ws_uuid
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")

    return doc
