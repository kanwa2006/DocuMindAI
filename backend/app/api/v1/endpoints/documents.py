import uuid
import re
import hmac
import hashlib
import logging
import os
import time
from typing import Optional, List, Any
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.models.document import Document, DocumentStatus
from app.core.auth import get_current_user
from app.core.workspace import resolve_workspace_id
from app.core.config import settings
from app.workers.tasks.document_tasks import process_document, process_clip_document
from app.services.extraction_router import route_extraction
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

ALLOWED_MIMES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    # P8: PowerPoint
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-powerpoint",  # legacy .ppt — accepted at the API edge, extractor will reject if it's not actually pptx
]


class ClipRequest(BaseModel):
    title: Optional[str] = None
    content: str
    source_hint: Optional[str] = None  # "email", "message", "web", "note", "other"
    # P1: pin the clip to a specific chat session so it never leaks into
    # other chats in the same workspace. Optional for backwards compat.
    chat_session_id: Optional[str] = None


class VerifyUploadRequest(BaseModel):
    document_id: str
    filename: str
    object_key: str
    # FIX 0.7: optional metadata the frontend can supply to avoid NOT NULL errors
    file_hash: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    # P1: per-chat isolation. When set, retrieval will only see this doc for
    # queries made in this specific chat session.
    chat_session_id: Optional[str] = None


@router.post("/clip")
async def clip_text(
    request: ClipRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 28 — Instant Text Clip.
    Accepts raw text, deduplicates via MD5, creates a Document record,
    dispatches process_clip_document Celery task (no OCR, no file storage).
    Returns immediately with estimated_seconds: 5.
    """
    if len(request.content) < 50:
        raise HTTPException(status_code=400, detail="Text must be at least 50 characters")
    if len(request.content) > 50000:
        raise HTTPException(status_code=400, detail="Text must be under 50,000 characters")

    owner_id = uuid.UUID(current_user["id"])
    ws_uuid = resolve_workspace_id(current_user.get("workspace_id"))

    content_hash = hashlib.md5(request.content.encode()).hexdigest()

    # Deduplication check
    dup_result = await db.execute(
        select(Document).where(
            Document.owner_id == owner_id,
            Document.content_hash == content_hash,
        )
    )
    existing = dup_result.scalar_one_or_none()
    if existing:
        return {
            "document_id": str(existing.id),
            "status": "deduplicated",
            "estimated_seconds": 0,
            "message": "Text matches a previous clip. Using cached embeddings.",
        }

    # Build filename from source_hint + title or first 40 chars of content
    prefix_map = {
        "email": "Email — ",
        "message": "Message — ",
        "web": "Web — ",
        "note": "Note — ",
        "other": "Clip — ",
    }
    prefix = prefix_map.get(request.source_hint or "", "Clip — ")
    base = (request.title or request.content[:40].strip()).replace("\n", " ")
    filename = (prefix + base)[:60]

    doc_id = uuid.uuid4()
    file_hash = hashlib.sha256(request.content.encode()).hexdigest()
    size_bytes = len(request.content.encode("utf-8"))

    # P1: persist chat_session_id so per-chat retrieval can filter to this clip
    chat_uuid: Optional[uuid.UUID] = None
    if request.chat_session_id:
        try:
            chat_uuid = uuid.UUID(request.chat_session_id)
        except (ValueError, TypeError):
            chat_uuid = None

    new_doc = Document(
        id=doc_id,
        filename=filename,
        file_hash=file_hash,
        mime_type="text/plain",
        size_bytes=size_bytes,
        storage_path=f"clip://{doc_id}",
        status=DocumentStatus.PROCESSING,
        owner_id=owner_id,
        workspace_id=ws_uuid,
        chat_session_id=chat_uuid,
        content_hash=content_hash,
        source="clip",
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    process_clip_document.delay(str(doc_id), request.content)

    return {
        "document_id": str(doc_id),
        "filename": filename,
        "status": "processing",
        "estimated_seconds": 5,
    }


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
    ws_uuid = resolve_workspace_id(current_user.get("workspace_id"))

    storage_path = request.object_key

    # FIX 0.7: Compute fallback values — never let NOT NULL columns be None
    file_hash = request.file_hash or hashlib.sha256(storage_path.encode()).hexdigest()
    mime_type = request.mime_type or "application/pdf"
    size_bytes = request.size_bytes
    if size_bytes is None:
        local_path = Path(storage_path)
        size_bytes = local_path.stat().st_size if local_path.exists() else 0

    # P1: persist chat_session_id so the retrieval path in /query/stream can
    # restrict the vector search to only the docs attached to this chat.
    chat_uuid: Optional[uuid.UUID] = None
    if request.chat_session_id:
        try:
            chat_uuid = uuid.UUID(request.chat_session_id)
        except (ValueError, TypeError):
            chat_uuid = None

    new_doc = Document(
        id=doc_id,
        filename=request.filename,
        storage_path=storage_path,
        owner_id=owner_id,
        workspace_id=ws_uuid,
        chat_session_id=chat_uuid,
        file_hash=file_hash,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # Always dispatch the Celery worker. It chunks, embeds, and flips status to READY.
    # The previous "extraction_router skip OCR" optimization marked native PDFs as
    # INDEXING but never enqueued the task — documents stayed in INDEXING forever
    # with no chunks/embeddings, blocking every grounded query. The worker uses
    # PyMuPDF internally and handles native PDFs efficiently.
    try:
        process_document.delay(str(new_doc.id))
        logger.info(
            f"[verify_upload] dispatched process_document for {request.filename} "
            f"(id={new_doc.id}, size={size_bytes} bytes)"
        )
    except Exception as exc:
        # Worker/broker down — surface a real failure instead of leaving the doc
        # stuck in PROCESSING forever.
        logger.error(f"[verify_upload] Could not enqueue process_document: {exc}")
        new_doc.status = DocumentStatus.FAILED
        await db.commit()
        await db.refresh(new_doc)
        raise HTTPException(
            status_code=503,
            detail="Document queue unavailable. Try again in a moment.",
        )

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
        raise HTTPException(status_code=415, detail="Unsupported file type. Accepted: PDF, DOCX, PPTX.")

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
    Local file upload endpoint for development.

    Writes the file UNDER settings.STORAGE_PATH so the Celery worker's
    LocalStorageProvider.download_file (which does `base_dir / object_key`)
    finds it. Returns an absolute storage_path so verify_upload, the worker,
    and any serve-file endpoint all agree on the filesystem location.
    """
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Accepted: PDF, DOCX, PPTX.")

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
    safe_workspace = re.sub(r'[^\w.\-]', '_', workspace_id or "general")
    file_hash = hashlib.sha256(content).hexdigest()
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"

    storage_base = Path(settings.STORAGE_PATH).resolve()
    storage_dir = storage_base / safe_workspace
    storage_dir.mkdir(parents=True, exist_ok=True)
    abs_path = storage_dir / unique_name

    with open(abs_path, "wb") as f:
        f.write(content)

    storage_path = str(abs_path)
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
    chat_session_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    FIX 6.6: Accepts optional workspace_id query param to filter documents.
    Falls back to JWT workspace_id. Strict owner isolation enforced.

    P1: Accepts optional chat_session_id to restrict the list to docs
    attached to a single chat. When provided, this is the only view that
    matters for the chat's chip rail — docs from other chats in the same
    workspace are excluded.
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
    )

    # P1: per-chat isolation filter. Empty/None chat_session_id means
    # "all of this workspace's docs"; a real UUID means "only this chat".
    if chat_session_id:
        try:
            chat_uuid = uuid.UUID(chat_session_id)
            stmt = stmt.where(Document.chat_session_id == chat_uuid)
        except (ValueError, TypeError):
            # Invalid id → return empty list rather than leaking everything
            return []

    stmt = stmt.order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
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


# TASK 3.8 — HEAD /documents/{id} lightweight polling endpoint
@router.head("/{document_id}")
async def head_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lightweight polling endpoint. Returns status in X-Document-Status header."""
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

    return Response(
        status_code=200,
        headers={"X-Document-Status": str(doc.status.value if hasattr(doc.status, 'value') else doc.status)}
    )


# ── 9-C6: Signed document access URL ─────────────────────────────────────────

def _generate_signed_token(doc_id: str, user_id: str, expires_at: int) -> str:
    """HMAC-SHA256 signed URL token. Expires in 15 minutes."""
    message = f"{doc_id}:{user_id}:{expires_at}".encode()
    secret = settings.AUTH_SECRET_KEY.encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


@router.get("/{document_id}/signed-url")
async def get_signed_url(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return a 15-minute HMAC-signed URL for direct document access."""
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
        Document.workspace_id == ws_uuid,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")

    expires_at = int(time.time()) + 900  # 15 minutes
    token = _generate_signed_token(document_id, current_user["id"], expires_at)
    signed_url = f"/files/{document_id}?token={token}&expires={expires_at}"
    return {"signed_url": signed_url, "expires_at": expires_at}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Secure deletion: removes DB record, storage file, Qdrant vectors, Redis cache,
    and referenced eval benchmark rows. Returns granular status for each step.
    NEVER silently ignores vector deletion failures.
    """
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
        Document.workspace_id == ws_uuid,
    )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")

    storage_path = doc.storage_path
    vectors_purged = False
    cache_cleared = False
    partial_failure: Optional[str] = None

    # 1. Delete from DB
    await db.delete(doc)

    # 2. Delete referenced EvalBenchmarkQuery rows
    try:
        from app.models.eval_benchmark import EvalBenchmarkQuery
        from sqlalchemy import delete as sa_delete
        await db.execute(
            sa_delete(EvalBenchmarkQuery).where(
                EvalBenchmarkQuery.expected_doc_id == doc_uuid
            )
        )
    except Exception as exc:
        logger.warning("[delete_document] Failed to remove EvalBenchmarkQuery rows: %s", exc)

    await db.commit()

    # 3. Delete storage file
    try:
        local_file = Path(storage_path)
        if local_file.exists():
            local_file.unlink()
    except Exception as exc:
        logger.warning("[delete_document] Storage file deletion failed: %s", exc)

    # 4. Delete Qdrant vectors (must not be silently ignored)
    try:
        from app.core.config import settings as _s
        if _s.VECTOR_BACKEND == "qdrant":
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            user_id_str = current_user["id"]
            isolation_mode = getattr(_s, "VECTOR_ISOLATION_MODE", "user")
            if isolation_mode == "organization":
                org_id = current_user.get("organization_id", user_id_str)
                collection = f"docuMind_org_{org_id}"
            else:
                collection = f"docuMind_{user_id_str}"
            qclient = QdrantClient(host=_s.QDRANT_HOST, port=_s.QDRANT_PORT)
            qclient.delete(
                collection_name=collection,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=str(doc_uuid)))]
                ),
            )
        vectors_purged = True
    except Exception as exc:
        partial_failure = f"Vector deletion failed: {exc}"
        logger.error("[delete_document] %s", partial_failure)

    # 5. Purge Redis cache entries
    try:
        import aioredis
        redis = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        uid = current_user["id"]
        keys = await redis.keys(f"retrieval:uid_{uid}:*")
        if keys:
            await redis.delete(*keys)
        await redis.close()
        cache_cleared = True
    except Exception as exc:
        logger.warning("[delete_document] Redis cache purge failed: %s", exc)

    # 6. Audit log
    logger.info(
        "[AUDIT] event=document_deleted doc_id=%s user_id=%s vectors_purged=%s ts=%s",
        str(doc_uuid),
        current_user["id"],
        vectors_purged,
        __import__("datetime").datetime.utcnow().isoformat(),
    )

    if partial_failure:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=207,
            content={
                "deleted": True,
                "vectors_purged": False,
                "cache_cleared": cache_cleared,
                "warning": partial_failure,
            },
        )

    return {"deleted": True, "vectors_purged": vectors_purged, "cache_cleared": cache_cleared}


# TASK 4 — HEAD /documents/{id}/status (same headers as GET status, no body)
@router.head("/{document_id}/status")
async def head_document_status(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lightweight status poll. Returns X-Document-Status header with no body."""
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

    return Response(
        status_code=200,
        headers={"X-Document-Status": str(doc.status.value if hasattr(doc.status, 'value') else doc.status)}
    )
