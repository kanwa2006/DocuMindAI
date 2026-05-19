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
from app.core.config import settings
from app.workers.tasks.document_tasks import process_document
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
]


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

    # TASK 3.7: Route via extraction_router before OCR queue
    # Only attempt extraction for local files (S3 paths start with "workspaces/")
    if not storage_path.startswith("workspaces/") and mime_type == "application/pdf":
        try:
            extraction = await route_extraction(storage_path)
            if not extraction["needs_ocr"]:
                # Native PDF — text extracted; skip OCR, set INDEXING status
                new_doc.status = DocumentStatus.INDEXING
                await db.commit()
                await db.refresh(new_doc)
                logger.info(
                    f"[verify_upload] pymupdf4llm extraction OK for {request.filename} "
                    f"({len(extraction.get('text', '') or '')} chars) — OCR skipped"
                )
            else:
                # Scanned PDF — dispatch to Celery OCR task
                process_document.delay(str(new_doc.id))
        except Exception as exc:
            logger.warning(f"[verify_upload] extraction_router error: {exc} — falling back to OCR")
            process_document.delay(str(new_doc.id))
    else:
        # S3 path or non-PDF — dispatch OCR as before
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
