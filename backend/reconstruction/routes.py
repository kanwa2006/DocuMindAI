"""
Reconstruction API routes — new endpoints that sit alongside the existing ones.
Does NOT modify any existing routes or RAG behaviour.

Endpoints:
  POST /recon/{doc_id}/start     — trigger reconstruction job (background)
  GET  /recon/{doc_id}/status    — polling: overall status + per-page progress
  GET  /recon/{doc_id}/page/{n}  — get page data (text + tables + image as b64)
  GET  /recon/{doc_id}/image/{n} — serve page image as PNG (for <img src>)
"""
import os
import threading
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Document, User
from backend.auth.routes import get_current_user
from backend.documents.storage import get_user_storage_dir
from backend.reconstruction.processor import (
    reconstruct_document,
    load_reconstruction,
    get_page_image_b64,
)

router = APIRouter(prefix="/recon", tags=["reconstruction"])

# In-memory progress tracker: {f"{user_id}_{doc_id}": {...}}
_progress: dict = {}


def _recon_dir(user_id: int, doc_filename: str) -> str:
    """Reconstruction cache lives under storage/{user_id}/recon/{doc_uuid}/"""
    uuid_part = os.path.basename(doc_filename).split("_")[0]
    base = get_user_storage_dir(user_id)
    return os.path.join(base, "recon", uuid_part)


def _job_key(user_id: int, doc_id: int) -> str:
    return f"{user_id}_{doc_id}"


# ── POST /recon/{doc_id}/start ─────────────────────────────────────────────────

@router.post("/{doc_id}/start")
def start_reconstruction(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fp = os.path.join(get_user_storage_dir(current_user.id), doc.filename)
    if not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="File not found on disk")

    recon_dir = _recon_dir(current_user.id, doc.filename)
    key = _job_key(current_user.id, doc_id)

    # Return cached result if already done
    cached = load_reconstruction(recon_dir)
    if cached and cached.get("ready"):
        _progress[key] = {
            "status": "done",
            "current_page": cached["total_pages"],
            "total_pages": cached["total_pages"],
            "stage": "complete",
            "eta_seconds": 0,
        }
        return {"status": "already_done", "total_pages": cached["total_pages"]}

    # If already running, don't start again
    if _progress.get(key, {}).get("status") == "running":
        return {"status": "already_running"}

    # Init progress
    _progress[key] = {
        "status": "running",
        "current_page": 0,
        "total_pages": 0,
        "stage": "starting",
        "eta_seconds": -1,
    }

    # Launch background thread
    def _run():
        def _cb(page_num, total, stage, eta):
            _progress[key] = {
                "status": "running",
                "current_page": page_num,
                "total_pages": total,
                "stage": stage,
                "eta_seconds": eta,
            }

        try:
            result = reconstruct_document(fp, recon_dir, progress_callback=_cb)
            _progress[key] = {
                "status": "done" if not result.get("error") else "error",
                "current_page": result.get("total_pages", 0),
                "total_pages": result.get("total_pages", 0),
                "stage": "complete",
                "eta_seconds": 0,
                "error": result.get("error"),
            }
        except Exception as e:
            _progress[key] = {
                "status": "error",
                "current_page": 0,
                "total_pages": 0,
                "stage": "failed",
                "eta_seconds": 0,
                "error": str(e),
            }

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {"status": "started"}


# ── DELETE /recon/{doc_id}/cache ───────────────────────────────────────────────

@router.delete("/{doc_id}/cache")
def clear_cache(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete cached reconstruction so it will be re-processed fresh on next start."""
    import shutil
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    recon_dir = _recon_dir(current_user.id, doc.filename)
    key = _job_key(current_user.id, doc_id)

    # Stop any running job
    if _progress.get(key, {}).get("status") == "running":
        _progress.pop(key, None)

    # Remove cached files
    if os.path.exists(recon_dir):
        shutil.rmtree(recon_dir, ignore_errors=True)
    _progress.pop(key, None)

    return {"status": "cleared", "message": "Cache deleted. Run /start to re-process."}


# ── GET /recon/{doc_id}/status ─────────────────────────────────────────────────

@router.get("/{doc_id}/status")
def get_status(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    recon_dir = _recon_dir(current_user.id, doc.filename)
    key = _job_key(current_user.id, doc_id)

    # Check disk first (persisted result)
    if key not in _progress:
        cached = load_reconstruction(recon_dir)
        if cached and cached.get("ready"):
            return {
                "status": "done",
                "current_page": cached["total_pages"],
                "total_pages": cached["total_pages"],
                "stage": "complete",
                "eta_seconds": 0,
            }
        return {
            "status": "not_started",
            "current_page": 0,
            "total_pages": 0,
            "stage": "idle",
            "eta_seconds": -1,
        }

    return _progress[key]


# ── GET /recon/{doc_id}/summary ────────────────────────────────────────────────

@router.get("/{doc_id}/summary")
def get_summary(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return pages.json metadata (without images — those come per-page)."""
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    recon_dir = _recon_dir(current_user.id, doc.filename)
    cached = load_reconstruction(recon_dir)
    if not cached:
        raise HTTPException(status_code=404, detail="Reconstruction not done yet")

    # Strip text/tables from summary response (too heavy) — client fetches per page
    summary_pages = [
        {
            "page": p["page"],
            "type": p.get("type", "unknown"),
            "confidence": p.get("confidence", "unknown"),
            "has_image": p.get("has_image", False),
            "has_text": p.get("has_text", False),
            "has_tables": p.get("has_tables", False),
            "ocr_used": p.get("ocr_used", False),
            "error": p.get("error"),
        }
        for p in cached.get("pages", [])
    ]
    return {
        "total_pages": cached["total_pages"],
        "pages": summary_pages,
    }


# ── GET /recon/{doc_id}/page/{n} ───────────────────────────────────────────────

@router.get("/{doc_id}/page/{page_num}")
def get_page(
    doc_id: int,
    page_num: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return full page data: text + tables + image (base64 PNG)."""
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    recon_dir = _recon_dir(current_user.id, doc.filename)
    cached = load_reconstruction(recon_dir)
    if not cached:
        raise HTTPException(status_code=404, detail="Reconstruction not done yet")

    pages = cached.get("pages", [])
    if page_num < 1 or page_num > len(pages):
        raise HTTPException(status_code=404, detail=f"Page {page_num} not found")

    page_data = pages[page_num - 1].copy()

    # Attach image as base64
    img_b64 = get_page_image_b64(recon_dir, page_num)
    page_data["image_b64"] = img_b64

    return page_data


# ── GET /recon/{doc_id}/image/{n} ─────────────────────────────────────────────

@router.get("/{doc_id}/image/{page_num}")
def get_page_image(
    doc_id: int,
    page_num: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve the page PNG directly (for <img> tags or download)."""
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.user_id == current_user.id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    recon_dir = _recon_dir(current_user.id, doc.filename)
    img_path = os.path.join(recon_dir, f"page_{page_num}.png")
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Page image not found")

    with open(img_path, "rb") as f:
        data = f.read()

    return Response(
        content=data,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="page_{page_num}.png"'},
    )
