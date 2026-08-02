"""Single owner-scoped `Document` lookup for the per-workspace process routes.

H9 — five endpoints (`legal`, `finance`, `study`, `research`, `hr`) each
resolved a caller-supplied `document_id` with

    select(Document).where(
        Document.id == document_id,
        Document.workspace_id == workspace_id,   # <- NOT a tenant key
    )

`workspace_id` is `uuid5(NAMESPACE_DNS, slug)`: a CATEGORY key, byte-identical
for every user. So the check established only "this document is in the Legal
category", never "this document is yours" — and each of these routes then
dispatched that document_id to Celery, where the worker extracts its text,
chunks it, and writes the results into the caller's workspace. A user could
hand over another user's document id and receive its contents back as their
own contract analysis, financial findings, flashcards or research extraction.

The register prescribes one shared helper rather than five one-line edits, and
that is the point: five copies of a security decision is five chances to get
it wrong, and this defect is already the fifth instance of the same mistake in
this codebase. There is now one place where "may this caller use this
document" is decided.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.document import Document


async def get_owned_document(
    db: AsyncSession,
    document_id: uuid.UUID | str,
    current_user: dict,
) -> Document:
    """Return the document if it belongs to the caller, else raise 404.

    404 rather than 403 deliberately: a 403 would confirm the id exists and
    belongs to somebody, which is an enumeration oracle. The caller cannot
    distinguish "no such document" from "not yours", which is the correct
    amount of information to disclose.

    Raises `HTTPException(422)` for a malformed id, matching what the
    per-endpoint `uuid.UUID(...)` conversions did before.
    """
    try:
        doc_uuid = (
            document_id if isinstance(document_id, uuid.UUID)
            else uuid.UUID(str(document_id))
        )
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid Document ID format.")

    doc = (
        await db.execute(
            select(Document).where(
                Document.id == doc_uuid,
                Document.owner_id == uuid.UUID(current_user["id"]),
            )
        )
    ).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc
