"""Regression guard for final_audit P-1 and P-2.

Two loops issued one query per item:

  P-1 `workers/tasks/export_tasks.py` — one SELECT per clause to fetch its
      redlines, so a 50-clause contract ran 51 queries instead of 2.
  P-2 `api/v1/endpoints/research.py` — for each doc_id, one query for the
      Document and another for its chunks: 2N round trips for N documents, on
      a REQUEST-path endpoint.

Against Supabase's pooler every round trip carries network latency, so both
scaled linearly with input size.

The assertion is on the NUMBER OF QUERIES as the input grows, not on elapsed
time — timing is environment-dependent and would be flaky, whereas "this must
not grow with N" is exactly the property that was violated.

`_load_owned_docs_with_text` additionally closed a tenancy hole both research
loops shared (they scoped by `workspace_id`, identical for every user), so the
owner predicate is pinned here too.
"""
import uuid

import pytest

from app.api.v1.endpoints.research import _load_owned_docs_with_text


class _Doc:
    def __init__(self, doc_id):
        self.id = doc_id
        self.filename = f"{doc_id}.pdf"


class _Chunk:
    def __init__(self, doc_id, idx):
        self.document_id = doc_id
        self.chunk_index = idx
        self.text_content = f"text {idx} of {doc_id}"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _CountingDB:
    """Counts executed statements and serves canned Document / chunk rows."""

    def __init__(self, docs, chunks_per_doc):
        self.docs = docs
        self.chunks_per_doc = chunks_per_doc
        self.query_count = 0
        self.wheres = []

    async def execute(self, stmt):
        self.query_count += 1
        self.wheres.append(str(stmt.whereclause))
        # First call is the Document lookup, second is the chunk lookup.
        if self.query_count == 1:
            return _Result(self.docs)
        return _Result(
            [_Chunk(d.id, i) for d in self.docs for i in range(self.chunks_per_doc)]
        )


@pytest.mark.parametrize("n_docs", [1, 5, 20])
@pytest.mark.asyncio
async def test_research_doc_loading_is_constant_query_count(n_docs):
    docs = [_Doc(uuid.uuid4()) for _ in range(n_docs)]
    db = _CountingDB(docs, chunks_per_doc=3)

    out = await _load_owned_docs_with_text(
        db, [str(d.id) for d in docs], uuid.uuid4(),
        chunks_per_doc=6, max_chars=3000,
    )

    assert len(out) == n_docs
    assert db.query_count == 2, (
        f"loading {n_docs} documents took {db.query_count} queries. This must "
        "be 2 regardless of N — one for the documents, one for their chunks. "
        "A per-document loop is 2N sequential round trips (P-2)."
    )


@pytest.mark.asyncio
async def test_research_doc_loading_is_scoped_by_owner():
    docs = [_Doc(uuid.uuid4())]
    db = _CountingDB(docs, chunks_per_doc=1)

    await _load_owned_docs_with_text(
        db, [str(docs[0].id)], uuid.uuid4(), chunks_per_doc=2, max_chars=100
    )

    doc_where = db.wheres[0]
    assert "owner_id" in doc_where, (
        "documents are loaded without an owner predicate. Both research loops "
        "previously scoped by workspace_id, which is identical for every user, "
        f"so another user's document text came back inside the response. "
        f"WHERE was:\n{doc_where}"
    )


@pytest.mark.asyncio
async def test_per_document_chunk_cap_does_not_starve_later_documents():
    """A single SQL LIMIT across the batch would give doc 1 everything."""
    docs = [_Doc(uuid.uuid4()) for _ in range(3)]
    db = _CountingDB(docs, chunks_per_doc=5)

    out = await _load_owned_docs_with_text(
        db, [str(d.id) for d in docs], uuid.uuid4(),
        chunks_per_doc=2, max_chars=10_000,
    )

    for doc, excerpt in out:
        assert excerpt, f"{doc.filename} got no text — later docs were starved"


def test_export_redlines_are_fetched_in_one_query():
    """P-1: the clause loop must not contain a db.execute."""
    import ast
    import inspect

    from app.workers.tasks import export_tasks

    src = inspect.getsource(export_tasks)
    tree = ast.parse(src)

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        # Only the BODY counts. A `db.execute(...)` in the loop's ITERATOR
        # expression (`for row in db.execute(...).scalars().all():`) runs
        # exactly once and is the batched form — the fix, not the defect.
        # The first version of this guard walked the whole For node and
        # flagged the correct code.
        for statement in node.body:
            for inner in ast.walk(statement):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "execute"
                ):
                    offenders.append(getattr(inner, "lineno", "?"))

    assert not offenders, (
        f"export_tasks.py issues a query inside a for-loop BODY (lines "
        f"{offenders}). A 50-clause contract then runs 51 queries instead of 2 "
        "(P-1). Batch with .in_() and group in Python."
    )
