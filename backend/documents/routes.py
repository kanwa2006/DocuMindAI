import os
import unicodedata
from urllib.parse import quote
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Document, User
from backend.auth.routes import get_current_user
from backend.documents.storage import save_uploaded_file, delete_document_file, get_user_storage_dir
from backend.documents.ocr import process_pdf
from backend.qa.indexer import build_user_index

router = APIRouter(prefix="/documents", tags=["documents"])


def _clean_filename(filename: str) -> str:
    """Remove UUID prefix: 'abc123_BDS.pdf' → 'BDS.pdf'"""
    basename = os.path.basename(filename)
    parts = basename.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        return parts[1]
    return basename


def _process_and_index(user_id, file_path, doc_id, db_url):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.documents.storage import get_images_dir
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    DB = sessionmaker(bind=engine)()
    try:
        text, _ = process_pdf(file_path, get_images_dir(user_id))
        build_user_index(user_id, text, file_path)
        doc = DB.query(Document).filter(Document.id == doc_id).first()
        if doc: doc.is_indexed = 1; DB.commit()
    except Exception as e:
        print(f"[Indexer Error] {e}")
        doc = DB.query(Document).filter(Document.id == doc_id).first()
        if doc: doc.is_indexed = 2; DB.commit()
    finally:
        DB.close()


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = save_uploaded_file(current_user.id, unique_name, await file.read())
    doc = Document(user_id=current_user.id, filename=unique_name, original_name=file.filename, is_indexed=0)
    db.add(doc); db.commit(); db.refresh(doc)
    from backend.config import DATABASE_URL
    background_tasks.add_task(_process_and_index, current_user.id, file_path, doc.id, DATABASE_URL)
    return {"message": "Upload successful", "doc_id": doc.id, "filename": file.filename}


@router.get("/list")
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id": d.id,
            "original_name": d.original_name,
            "filename": d.filename,
            "uploaded_at": d.uploaded_at.isoformat(),
            "is_indexed": d.is_indexed,
            "status": {0:"Processing", 1:"Ready", 2:"Failed"}[d.is_indexed]
        }
        for d in db.query(Document).filter(Document.user_id == current_user.id).all()
    ]


@router.get("/info/{doc_id}")
def document_info(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    fp = os.path.join(get_user_storage_dir(current_user.id), doc.filename)
    kb = round(os.path.getsize(fp)/1024, 1) if os.path.exists(fp) else 0
    return {
        "id": doc.id,
        "original_name": doc.original_name,
        "uploaded_at": doc.uploaded_at.isoformat(),
        "status": {0:"Processing", 1:"Ready", 2:"Failed"}[doc.is_indexed],
        "file_size": f"{round(kb/1024,2)} MB" if kb > 1024 else f"{kb} KB"
    }


@router.get("/view/{doc_id}")
def view_document(doc_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    from backend.auth.routes import verify_token_string
    user = verify_token_string(token, db)
    if not user: raise HTTPException(status_code=401, detail="Invalid token")
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user.id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    fp = os.path.join(get_user_storage_dir(user.id), doc.filename)
    if not os.path.exists(fp): raise HTTPException(status_code=404, detail="File not found")
    # Sanitize filename for HTTP headers (latin-1 only allows ASCII subset)
    # Use RFC 5987 encoding for full Unicode support alongside an ASCII fallback
    safe_name = unicodedata.normalize("NFKD", doc.original_name)
    safe_name = safe_name.encode("ascii", errors="replace").decode("ascii").replace("?", "_")
    encoded_name = quote(doc.original_name, safe="")
    content_disposition = f'inline; filename="{safe_name}"; filename*=UTF-8\'\'{encoded_name}'
    return FileResponse(path=fp, media_type="application/pdf",
                        headers={"Content-Disposition": content_disposition})


@router.delete("/{doc_id}")
def delete_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")

    # Delete physical file
    delete_document_file(current_user.id, doc.filename)

    # ✅ Fix: pass CLEAN filename so indexer finds the right chunks
    clean_name = _clean_filename(doc.filename)
    try:
        from backend.qa.indexer import _remove_chunks_for_file
        _remove_chunks_for_file(current_user.id, clean_name)
        print(f"[Delete] Removed chunks for '{clean_name}' from index")
    except Exception as e:
        print(f"[Delete] Could not remove chunks: {e}")

    db.delete(doc); db.commit()
    return {"message": f"'{doc.original_name}' deleted successfully"}
