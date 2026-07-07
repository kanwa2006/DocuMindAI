"""
Smart PDF extraction router.

Routing logic:
  - Native PDFs (selectable text): pymupdf4llm → ~0.12s, excellent structure
  - Scanned / image-heavy PDFs:    falls through to existing OCR pipeline

This module does NOT modify any stable system (ocr_orchestrator, chunking_service).
It is a new upstream router that runs BEFORE the OCR pipeline is triggered.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def is_native_pdf(pdf_path: str) -> bool:
    """
    Returns True if the PDF has selectable text (not a scan).
    Heuristic: >70% of pages must have >50 characters of extractable text.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return False
        text_pages = sum(
            1 for page in doc if len(page.get_text().strip()) > 50
        )
        doc.close()
        return (text_pages / total_pages) > 0.70
    except Exception as e:
        logger.warning(f"[pdf_extractor] is_native_pdf check failed for {pdf_path}: {e}")
        return False


def extract_native_pdf(pdf_path: str) -> str | None:
    """
    Extract native PDF to LLM-ready Markdown via pymupdf4llm.
    Speed: ~0.12s. No GPU. Preserves headings, tables, lists.
    Returns None if extraction fails (caller falls back to OCR).
    """
    try:
        import pymupdf4llm
        md_text = pymupdf4llm.to_markdown(pdf_path)
        logger.info(
            f"[pdf_extractor] pymupdf4llm extracted {pdf_path}: "
            f"{len(md_text)} chars"
        )
        return md_text
    except Exception as e:
        logger.warning(f"[pdf_extractor] pymupdf4llm failed on {pdf_path}: {e}")
        return None


def smart_extract(pdf_path: str) -> dict:
    """
    Routes PDF to the fastest viable extraction method.

    Returns:
        {
            "text": str | None,
            "method": "pymupdf4llm" | "ocr_pipeline",
            "native": bool
        }

    If method == "ocr_pipeline", text is None and the caller
    must route to the existing OCR orchestrator.
    """
    if not Path(pdf_path).exists():
        logger.error(f"[pdf_extractor] File not found: {pdf_path}")
        return {"text": None, "method": "ocr_pipeline", "native": False}

    native = is_native_pdf(pdf_path)
    if native:
        text = extract_native_pdf(pdf_path)
        if text:
            return {"text": text, "method": "pymupdf4llm", "native": True}

    # Fall through — OCR pipeline handles this
    return {"text": None, "method": "ocr_pipeline", "native": False}


# Embedding model names for external reference
EMBEDDING_MODEL_PRIMARY = "BAAI/bge-m3"
EMBEDDING_MODEL_FALLBACK = "nomic-ai/nomic-embed-text-v1.5"
