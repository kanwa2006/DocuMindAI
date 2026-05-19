"""
Extraction router — sits upstream of the OCR pipeline.
Routes PDFs to the fastest available extraction method.
Wraps stable systems — never modifies them.
"""
import logging
import asyncio
from functools import partial
from app.services.pdf_extractor import smart_extract

logger = logging.getLogger(__name__)


async def route_extraction(pdf_path: str) -> dict:
    """
    Try pymupdf4llm first (native PDFs, ~0.12s).
    Fall back to OCR pipeline for scanned / complex documents.

    Returns:
        {
            "text": str | None,
            "method": "pymupdf4llm" | "ocr_pipeline",
            "needs_ocr": bool,
            "quality": "high" | "pending"
        }
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(smart_extract, pdf_path))

    if result["method"] == "pymupdf4llm" and result["text"]:
        logger.info(
            f"[extraction_router] Native PDF via pymupdf4llm: "
            f"{len(result['text'])} chars — OCR skipped"
        )
        return {
            "text": result["text"],
            "method": "pymupdf4llm",
            "needs_ocr": False,
            "quality": "high",
        }

    logger.info(
        f"[extraction_router] Scanned/complex PDF detected → routing to OCR pipeline"
    )
    return {
        "text": None,
        "method": "ocr_pipeline",
        "needs_ocr": True,
        "quality": "pending",
    }
