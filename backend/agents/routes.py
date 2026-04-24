"""
Simple tool-based agents for DocuMindAI.

Agents transform the system from a Q&A tool into a multifunctional
document assistant. Each agent performs a specific document task:

- /agents/summarize/{doc_id}     → structured document summary
- /agents/key-concepts/{doc_id}  → bullet list of key concepts
- /agents/export-table/{doc_id}  → extracted tables as CSV text
"""
import json
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import User, Document
from backend.auth.routes import get_current_user
from backend.qa.indexer import query_user_index
from backend.qa.chain import call_gemini, build_prompt
from backend.config import GEMINI_MODEL, DATABASE_URL
from backend.documents.storage import get_user_storage_dir

router = APIRouter(prefix="/agents", tags=["agents"])


def _clean_filename(filename: str) -> str:
    basename = os.path.basename(filename)
    parts = basename.split("_", 1)
    if len(parts) == 2 and len(parts[0]) == 32 and parts[0].isalnum():
        return parts[1]
    return basename


def _get_doc_or_404(doc_id: int, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
        Document.is_indexed == 1
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found or not yet indexed.")
    return doc


# ── Agent 1: Structured Summary ───────────────────────────────────────────────

@router.post("/summarize/{doc_id}")
def agent_summarize(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a structured, section-wise summary of a document."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    source = _clean_filename(doc.filename)

    chunks = query_user_index(
        current_user.id,
        "summarize all main topics and key points",
        top_k=20,
        source_filter=[source]
    )
    if not chunks:
        raise HTTPException(422, "No indexed content found for this document.")

    context = "\n\n---\n\n".join(
        f"[Page {c.get('page', '?')}]\n{c.get('chunk', '')}" for c in chunks
    )
    prompt = (
        "You are a document summarization agent.\n"
        "Create a STRUCTURED SUMMARY of the document below.\n\n"
        "Format:\n"
        "1. Overview (3-4 sentences)\n"
        "2. Section-by-section breakdown with bullet points\n"
        "3. Key Takeaways (5 bullets)\n"
        "4. Likely exam/viva questions (if academic)\n\n"
        f"Document Content:\n{context}\n\n"
        "Structured Summary:"
    )
    try:
        summary = call_gemini(prompt, GEMINI_MODEL)
    except Exception as e:
        raise HTTPException(503, f"AI service unavailable: {e}")

    return {"doc_id": doc_id, "filename": doc.original_name, "summary": summary}


# ── Agent 2: Key Concepts ─────────────────────────────────────────────────────

@router.post("/key-concepts/{doc_id}")
def agent_key_concepts(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Extract key concepts, definitions, and terms from a document."""
    doc = _get_doc_or_404(doc_id, current_user, db)
    source = _clean_filename(doc.filename)

    chunks = query_user_index(
        current_user.id,
        "key concepts definitions terms important topics",
        top_k=15,
        source_filter=[source]
    )
    if not chunks:
        raise HTTPException(422, "No indexed content found.")

    context = "\n\n---\n\n".join(c.get("chunk", "") for c in chunks)
    prompt = (
        "You are a concept extraction agent.\n"
        "Extract ALL key concepts, definitions, and important terms from the text below.\n\n"
        "Format each as:\n"
        "**Term/Concept** — Brief definition or explanation (1-2 sentences)\n\n"
        "Group related concepts under headings if possible.\n\n"
        f"Document Content:\n{context}\n\n"
        "Key Concepts:"
    )
    try:
        concepts = call_gemini(prompt, GEMINI_MODEL)
    except Exception as e:
        raise HTTPException(503, f"AI service unavailable: {e}")

    return {"doc_id": doc_id, "filename": doc.original_name, "key_concepts": concepts}


# ── Agent 3: Table Extraction & Export ────────────────────────────────────────

@router.post("/export-table/{doc_id}")
def agent_export_table(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract all tables from a document and return them as:
    - Markdown tables (for display / copy-paste into Word/Docs)
    - CSV text (for Excel import)
    """
    doc = _get_doc_or_404(doc_id, current_user, db)
    source = _clean_filename(doc.filename)

    # Search for table chunks specifically
    chunks = query_user_index(
        current_user.id,
        "table rows columns data",
        top_k=10,
        source_filter=[source]
    )

    # Filter chunks that contain [TABLE] markers
    table_chunks = [c for c in chunks if "[TABLE" in c.get("chunk", "")]

    # Also extract directly from the PDF file using pdfplumber
    raw_tables_csv = []
    try:
        import pdfplumber
        fp = os.path.join(get_user_storage_dir(current_user.id), doc.filename)
        if os.path.exists(fp):
            with pdfplumber.open(fp) as pdf:
                for pg_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for t_idx, table in enumerate(tables or []):
                        if not table:
                            continue
                        csv_rows = []
                        for row in table:
                            csv_rows.append(",".join(
                                f'"{str(c or "").replace(chr(10), " ").strip()}"'
                                for c in row
                            ))
                        raw_tables_csv.append({
                            "page": pg_num + 1,
                            "table_index": t_idx + 1,
                            "csv": "\n".join(csv_rows)
                        })
    except Exception as e:
        print(f"[Agent Export Table Error] {e}")

    markdown_tables = [c.get("chunk", "") for c in table_chunks]

    return {
        "doc_id": doc_id,
        "filename": doc.original_name,
        "tables_found": len(raw_tables_csv),
        "markdown_tables": markdown_tables,
        "csv_tables": raw_tables_csv,
        "usage_hint": (
            "Copy markdown_tables content into any markdown editor or Google Docs. "
            "Copy csv_tables[].csv content into a .csv file and open in Excel."
        )
    }
