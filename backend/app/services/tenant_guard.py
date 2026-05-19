import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import HTTPException

from app.models.document import Document

logger = logging.getLogger("audit.tenant")


class TenantBoundaryViolation(HTTPException):
    """Raised when a retrieval request crosses tenant scope. doc_id never leaks to caller."""

    def __init__(self, detail: str = "Access denied: tenant boundary violation") -> None:
        super().__init__(status_code=403, detail=detail)


def _scope_matches(
    user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID],
    doc: Document,
) -> bool:
    if organization_id is not None:
        return getattr(doc, "organization_id", None) == organization_id
    return getattr(doc, "owner_id", None) == user_id


def _log_boundary_violation(
    user_id: uuid.UUID,
    doc_id: uuid.UUID,
    reason: str,
) -> None:
    """Structured audit log — synchronous, survives session rollback."""
    logger.warning(
        "[TENANT_BOUNDARY_VIOLATION] event=tenant_boundary_violation user_id=%s reason=%s timestamp=%s",
        str(user_id),
        reason,
        datetime.utcnow().isoformat(),
        # doc_id intentionally excluded from log message to prevent leaking other-tenant IDs
        extra={"doc_id": str(doc_id)},  # available to log handlers but not in the message
    )


def validate_retrieval_scope(
    user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID],
    requested_doc_ids: list[uuid.UUID],
    db_docs: list[Document],
) -> None:
    """
    Hard blocking guard called before EVERY retrieval operation.
    Raises TenantBoundaryViolation (HTTP 403) if any doc is outside tenant scope.
    Violation is logged before raising — audit trail is always written.
    CRITICAL: Never remove or bypass this call in retrieval paths.
    """
    db_doc_map: dict[uuid.UUID, Document] = {doc.id: doc for doc in db_docs}

    for doc_id in requested_doc_ids:
        doc = db_doc_map.get(doc_id)
        if doc is None:
            _log_boundary_violation(user_id, doc_id, "doc_not_found_in_scope")
            raise TenantBoundaryViolation()
        if not _scope_matches(user_id, organization_id, doc):
            _log_boundary_violation(user_id, doc_id, "retrieval_scope_mismatch")
            raise TenantBoundaryViolation()

    # Secondary check: validate DB-returned docs weren't injected from another tenant
    for doc in db_docs:
        if not _scope_matches(user_id, organization_id, doc):
            _log_boundary_violation(user_id, doc.id, "db_scope_mismatch")
            raise TenantBoundaryViolation()
