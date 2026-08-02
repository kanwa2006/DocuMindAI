"""Regression guard for final_audit H1 / S3.

`RetrievalService.retrieve_chunks` filtered on `Document.workspace_id`, which
is `uuid5(DNS, "legal"|"general"|...)` — identical for every user. It is a
category key, not a tenant key, so a session-less query retrieved across every
user's READY documents and returned their text verbatim with page citations.

These tests pin the two properties that make that impossible to reintroduce:

1. `owner_id` is a REQUIRED parameter (fail closed — a caller that forgets it
   raises TypeError instead of silently retrieving cross-tenant).
2. The emitted SQL carries an `owner_id` predicate on BOTH the vector and the
   lexical branch, so no fusion input can bypass it.

Test 3 pins S3's sibling: an EMPTY document_ids list means "no documents were
attached", which must not degrade to "no document filter at all".
"""
import inspect
import uuid

import pytest

from app.services.retrieval_service import RetrievalService


def test_owner_id_is_required_and_has_no_default():
    """Fail closed: forgetting the tenant key must be a TypeError, not a leak."""
    sig = inspect.signature(RetrievalService.retrieve_chunks)
    assert "owner_id" in sig.parameters, "owner_id parameter was removed"
    assert sig.parameters["owner_id"].default is inspect.Parameter.empty, (
        "owner_id must not have a default — an optional tenant key is one "
        "forgotten kwarg away from cross-tenant retrieval (H1)."
    )


@pytest.mark.asyncio
async def test_both_query_branches_filter_by_owner(monkeypatch):
    """The owner predicate must appear on the vector AND the lexical branch.

    RRF fuses both candidate lists, so a filter on only one still leaks: the
    unfiltered branch contributes another tenant's chunks to the fused output.
    """
    captured = []

    class _FakeResult:
        def all(self):
            return []

    class _FakeDB:
        async def execute(self, stmt):
            captured.append(str(stmt.compile(compile_kwargs={"literal_binds": False})))
            return _FakeResult()

    monkeypatch.setattr(
        "app.services.embedding_service.embedding_service.generate_embeddings",
        lambda texts: [[0.0] * 1024],
    )

    owner_id = uuid.uuid4()
    await RetrievalService.retrieve_chunks(
        db=_FakeDB(), query="anything", owner_id=owner_id, top_k=5
    )

    assert len(captured) == 2, "expected exactly the vector and lexical statements"
    for sql in captured:
        assert "owner_id" in sql, (
            "a retrieval branch has no owner_id predicate — this is H1 "
            f"reintroduced. SQL was:\n{sql}"
        )


@pytest.mark.asyncio
async def test_empty_document_ids_is_not_treated_as_no_filter(monkeypatch):
    """S3: `[]` means "the user attached nothing", never "match everything"."""
    captured = []

    class _FakeResult:
        def all(self):
            return []

    class _FakeDB:
        async def execute(self, stmt):
            captured.append(str(stmt.compile(compile_kwargs={"literal_binds": False})))
            return _FakeResult()

    monkeypatch.setattr(
        "app.services.embedding_service.embedding_service.generate_embeddings",
        lambda texts: [[0.0] * 1024],
    )

    await RetrievalService.retrieve_chunks(
        db=_FakeDB(), query="anything", owner_id=uuid.uuid4(), document_ids=[]
    )

    for sql in captured:
        assert "documents.id IN" in sql or "document_id IN" in sql or "IN (" in sql, (
            "an empty document_ids list dropped the id filter entirely, so a "
            "query with no attached documents scanned the whole corpus (S3). "
            f"SQL was:\n{sql}"
        )
