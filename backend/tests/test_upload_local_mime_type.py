"""Regression guard for BUG-004: upload_local must echo the real MIME type.

The /documents/upload/local endpoint hardcoded "application/pdf" in its
response regardless of the uploaded file type. The frontend (api.ts) passes
uploadMeta.mime_type directly to /documents/upload/verify, which stores it
in the Document.mime_type column. The Celery worker then branches on MIME
type to pick the right extractor: pdf_extractor for PDFs, python-docx for
DOCX, python-pptx for PPTX. With the hardcoded PDF type:

  - DOCX uploads: pdf_extractor fails / returns empty -> no text -> no chunks
  - PPTX uploads: pdf_extractor fails / returns empty -> no text -> no chunks

These tests pin the correct behaviour (actual content_type returned).
"""
import inspect


def test_upload_local_does_not_hardcode_pdf_mime():
    """Source-level check: the response must use file.content_type, not hardcoded PDF."""
    from app.api.v1.endpoints import documents

    src = inspect.getsource(documents.upload_local)

    assert "file.content_type" in src, (
        "upload_local must return file.content_type as mime_type. "
        "The hardcoded 'application/pdf' caused DOCX/PPTX to be stored "
        "with the wrong MIME type, sending them through the PDF extractor "
        "and producing empty text (BUG-004)."
    )

    # Verify no hardcoded literal in the return block
    lines = src.split("\n")
    in_return = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("return {"):
            in_return = True
        if in_return and "application/pdf" in stripped and not stripped.startswith("#"):
            raise AssertionError(
                f"Found hardcoded 'application/pdf' in the return block of "
                f"upload_local: {line!r}. This breaks DOCX/PPTX processing (BUG-004)."
            )
        if in_return and stripped == "}":
            break


def test_allowed_mimes_covers_docx_and_pptx():
    """ALLOWED_MIMES must include DOCX and PPTX."""
    from app.api.v1.endpoints.documents import ALLOWED_MIMES

    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in ALLOWED_MIMES
    assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" in ALLOWED_MIMES
    assert "application/pdf" in ALLOWED_MIMES
