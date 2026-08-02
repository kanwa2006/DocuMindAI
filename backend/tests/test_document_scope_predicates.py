"""Regression guard for final_audit H5.

Five single-document endpoints scoped by `Document.workspace_id == <JWT claim>`
in addition to `owner_id`. `User.workspace_id` is the constant "general" for
every user (`auth.py:394`), but uploads store the REAL workspace, so for six of
the seven workspaces the claim and the stored value disagree and every one of
these endpoints 404s:

  • GET    /documents/{id}          → metadata unreachable
  • HEAD   /documents/{id}          → the frontend READY transition never fires
  • GET    /documents/{id}/signed-url
  • DELETE /documents/{id}          → the document can never be deleted by anyone
  • HEAD   /documents/{id}/status

It escaped because `list_documents` takes an EXPLICIT `workspace_id` query
param and kept working — a list-based smoke test passes while every
single-document operation fails.

The assertion is on the emitted SQL rather than on results, because with a
single seeded tenant a spurious extra predicate that happens to match is
indistinguishable from a correct query. `owner_id` must be present (that is
the tenant key) and `workspace_id` must be absent (it is a category key that
does not identify a tenant and, here, does not even identify the row).
"""
import uuid

import pytest

from app.api.v1.endpoints import documents as documents_module

USER = {"id": str(uuid.uuid4()), "workspace_id": "general"}
DOC_ID = str(uuid.uuid4())


class _CapturingDB:
    """Records the WHERE clause of every statement handed to execute().

    Only the WHERE clause, deliberately: `select(Document)` emits every column
    — including `documents.workspace_id` — in the SELECT list, so matching
    against the whole statement can never tell a selected column apart from a
    filter predicate. The first version of this guard did exactly that and
    failed against correct code.
    """

    def __init__(self):
        self.where = []

    async def execute(self, stmt):
        self.where.append(str(stmt.whereclause))
        raise _StopEndpoint()


class _StopEndpoint(Exception):
    """Abort the endpoint once its lookup statement has been captured."""


async def _capture_lookup_where(endpoint):
    db = _CapturingDB()
    try:
        await endpoint(DOC_ID, current_user=USER, db=db)
    except _StopEndpoint:
        pass
    assert db.where, f"{endpoint.__name__} issued no lookup query"
    return db.where[0]


ENDPOINTS = [
    documents_module.get_document,
    documents_module.head_document,
    documents_module.get_signed_url,
    documents_module.delete_document,
    documents_module.head_document_status,
]


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: e.__name__)
@pytest.mark.asyncio
async def test_single_document_lookup_is_scoped_by_owner_only(endpoint):
    where = await _capture_lookup_where(endpoint)

    assert "owner_id" in where, (
        f"{endpoint.__name__} lost its owner_id predicate — that is the tenant "
        f"key and removing it is a cross-tenant read. WHERE was:\n{where}"
    )
    assert "workspace_id" not in where, (
        f"{endpoint.__name__} filters on workspace_id. The JWT claim is the "
        f"constant 'general' while uploads store the real workspace, so this "
        f"404s every document from the other six workspaces (H5). "
        f"WHERE was:\n{where}"
    )
