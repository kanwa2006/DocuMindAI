"""Shared worker-side loader for a document's real extracted text.

Not a Celery task module — deliberately underscore-prefixed so it is never
mistaken for one and never added to `celery_app.include`.

Exists because P0-8 was systemic, not a one-off. Several workspace task modules
each hardcoded a plausible-looking placeholder instead of reading the uploaded
document:

    legal_tasks    "Simulated text. 1. Confidentiality... 2. Liability capped at $50."
    finance_tasks  "Simulated invoice for {filename}. Vendor: AWS. Total: $5050.00..."

Both looked like working features and produced confident, well-formed output
about a document nobody uploaded — the most dangerous failure mode in a product
whose entire promise is that answers come from *your* documents. Fixing each
module with its own private copy of a text loader would repeat the duplication
that let the class spread; the loader lives here once.
"""
from __future__ import annotations

import uuid

from sqlalchemy.future import select

from app.models.document_chunk import DocumentChunk


class DocumentTextUnavailable(RuntimeError):
    """The document produced no extractable text.

    Raised rather than falling back to placeholder text or an empty string.
    Analysis built on text we do not have is worse than no analysis, because it
    looks correct. Callers should treat this as PERMANENT — retrying cannot
    conjure text that extraction never produced, so it must not consume a
    Celery retry budget.
    """


def load_document_text(db, document_id: uuid.UUID) -> str:
    """Return the document's real extracted text, in chunk order.

    Takes a SYNC session: every caller is a Celery task, and Celery must use
    `SyncSessionLocal` (see the async/sync invariant in CLAUDE.md and P0-7).
    """
    chunks = (
        db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        .scalars()
        .all()
    )
    text = "\n".join(c.text_content for c in chunks if c.text_content)
    if not text.strip():
        raise DocumentTextUnavailable(
            f"Document {document_id} has no extracted text — refusing to analyse "
            "a document whose contents are unknown. Check extraction/OCR first."
        )
    return text
