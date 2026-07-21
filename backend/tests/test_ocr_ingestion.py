"""Regression tests for DEBUG_MASTER_PLAN C-3.

Ingestion previously extracted scanned/image pages with raw
`page.get_text("text")` (a stub returning ~nothing); the marketed
PaddleOCR/Docling orchestrator was dead code on the upload path. These
tests pin the new wiring in OCRService.extract_document_stream:
- native PDFs never touch the orchestrator (behavior unchanged)
- scanned pages route through the orchestrator (mocked engine here)
- orchestrator failure degrades loudly to raw text with observable metadata
- PaddleOCREngine parses the PaddleOCR 3.x result format
"""
import logging
from unittest.mock import AsyncMock, patch

import fitz
import pytest

from app.services.ocr_service import OCRService
from app.services.ocr_orchestrator import OCREngineResult, PaddleOCREngine


def _make_pdf(tmp_path, *, with_text: bool) -> str:
    doc = fitz.open()
    page = doc.new_page()
    if with_text:
        page.insert_text(
            (72, 100),
            "This is a native PDF page with plenty of extractable text content "
            "to exceed the fifty character native-detection heuristic.",
        )
    else:
        # An image-only page: draw a rectangle, no text layer.
        page.draw_rect(fitz.Rect(50, 50, 200, 200), fill=(0.5, 0.5, 0.5))
    path = str(tmp_path / ("native.pdf" if with_text else "scanned.pdf"))
    doc.save(path)
    doc.close()
    return path


def test_native_pdf_never_calls_orchestrator(tmp_path):
    path = _make_pdf(tmp_path, with_text=True)
    with patch(
        "app.services.ocr_orchestrator.ocr_orchestrator.extract_document",
        new=AsyncMock(side_effect=AssertionError("orchestrator must not run for native pages")),
    ):
        pages = list(OCRService.extract_document_stream(path))
    assert len(pages) == 1
    assert "native PDF page" in pages[0]["extracted_text"]
    assert pages[0]["layout_metadata"]["is_native"] is True


def test_scanned_page_routes_through_orchestrator(tmp_path):
    path = _make_pdf(tmp_path, with_text=False)
    fake = OCREngineResult(engine_name="PaddleOCR", text="Handwritten OCR text", confidence=0.91)
    with patch(
        "app.services.ocr_orchestrator.ocr_orchestrator.extract_document",
        new=AsyncMock(return_value=fake),
    ) as mock_extract:
        pages = list(OCRService.extract_document_stream(path))

    mock_extract.assert_awaited_once()
    _, kwargs = mock_extract.await_args
    assert kwargs.get("hint") == "handwritten"

    assert len(pages) == 1
    meta = pages[0]["layout_metadata"]
    assert pages[0]["extracted_text"] == "Handwritten OCR text"
    assert meta["is_native"] is False
    assert meta["ocr_engine"] == "PaddleOCR"
    assert meta["ocr_confidence"] == pytest.approx(0.91)


def test_scanned_page_ocr_failure_is_loud(tmp_path, caplog):
    path = _make_pdf(tmp_path, with_text=False)
    with patch(
        "app.services.ocr_orchestrator.ocr_orchestrator.extract_document",
        new=AsyncMock(side_effect=ValueError("All OCR engines failed")),
    ), caplog.at_level(logging.ERROR, logger="app.services.ocr_service"):
        pages = list(OCRService.extract_document_stream(path))

    assert any("falling back to raw text" in r.message for r in caplog.records)
    meta = pages[0]["layout_metadata"]
    assert meta["is_native"] is False
    assert meta["requires_fallback"] is True
    assert meta["ocr_failed"] is True


def test_scanned_ocr_disabled_by_config(tmp_path, monkeypatch):
    from app.core.config import settings

    path = _make_pdf(tmp_path, with_text=False)
    monkeypatch.setattr(settings, "OCR_SCANNED_ENABLED", False)
    with patch(
        "app.services.ocr_orchestrator.ocr_orchestrator.extract_document",
        new=AsyncMock(side_effect=AssertionError("must not run when disabled")),
    ):
        pages = list(OCRService.extract_document_stream(path))
    assert pages[0]["layout_metadata"]["requires_fallback"] is True
    assert pages[0]["layout_metadata"]["ocr_failed"] is False


@pytest.mark.asyncio
async def test_paddle_engine_parses_3x_result_format():
    """PaddleOCR 3.x returns OCRResult dicts (rec_texts/rec_scores/rec_polys),
    not the 2.x [box, (text, conf)] nesting the engine was written against."""

    class FakePaddle3:
        def predict(self, file_path):
            return [
                {
                    "rec_texts": ["Hello", "World"],
                    "rec_scores": [0.95, 0.88],
                    "rec_polys": [
                        [[0, 0], [10, 0], [10, 5], [0, 5]],
                        [[0, 10], [12, 10], [12, 15], [0, 15]],
                    ],
                }
            ]

    with patch("app.services.ocr_orchestrator.get_paddle_ocr", return_value=FakePaddle3()):
        result = await PaddleOCREngine().extract("dummy.png", "image/png")

    assert "Hello" in result.text and "World" in result.text
    assert result.confidence == pytest.approx((0.95 + 0.88) / 2)
    assert len(result.bounding_boxes) == 2
