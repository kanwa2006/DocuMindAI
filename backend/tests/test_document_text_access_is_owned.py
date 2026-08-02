"""Regression guard for final_audit H6, H7 and H10.

Three ways to reach another tenant's content WITHOUT touching a `workspace_id`
filter — so the class ratchet in `test_owned_model_reads_are_owner_scoped.py`
could not see any of them:

  H7  `legal.py` and `finance.py` each had a private `_get_document_text` that
      selected chunks by `document_id` ALONE. `/legal/contracts/compare` feeds
      it two caller-supplied ids, so it returned any document's full text to
      any authenticated user.
  H6  `/finance/analyze` carried a comment reading "# Verify document
      ownership" directly above `select(Document).where(Document.id == doc_id)`
      — a comment describing a control that did not exist. Worse than no
      comment: it stops the next reader looking.
  H10 `/query/stream` loaded `ChatMessage` by `session_id` alone. Pass another
      user's session_id and their transcript enters the LLM prompt and is
      paraphrased back in the answer — a read of someone else's conversation,
      laundered through the model. H4 did NOT fix this; that finding covered
      the `/chats` routes, and this is a separate reader of the same table.

`ChatMessage` and `DocumentChunk` have no owner column of their own —
ownership lives on the parent — so these tests assert on the JOIN/lookup path
rather than on a column.
"""
import ast
import inspect
import re
import uuid

import pytest
from fastapi import HTTPException

from app.core.document_access import get_owned_document, get_owned_document_text


class _Result:
    def __init__(self, row=None, rows=None):
        self._row, self._rows = row, rows or []

    def scalar_one_or_none(self):
        return self._row

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _DB:
    """Returns no Document — i.e. the caller does not own it."""

    def __init__(self):
        self.wheres = []

    async def execute(self, stmt):
        self.wheres.append(str(stmt.whereclause))
        return _Result(row=None)


@pytest.mark.asyncio
async def test_unowned_document_lookup_raises_404_not_403():
    """404, not 403 — a 403 confirms the id exists and belongs to somebody."""
    db = _DB()
    with pytest.raises(HTTPException) as exc:
        await get_owned_document(db, str(uuid.uuid4()), {"id": str(uuid.uuid4())})
    assert exc.value.status_code == 404, (
        f"got {exc.value.status_code}; 403 would be an enumeration oracle"
    )
    assert "owner_id" in db.wheres[0], (
        f"the ownership lookup has no owner predicate: {db.wheres[0]}"
    )


@pytest.mark.asyncio
async def test_document_text_requires_ownership_before_reading_chunks():
    """H6/H7: chunk text must be unreachable when the document is not yours."""
    db = _DB()
    with pytest.raises(HTTPException) as exc:
        await get_owned_document_text(db, str(uuid.uuid4()), {"id": str(uuid.uuid4())})
    assert exc.value.status_code == 404
    assert len(db.wheres) == 1, (
        "the chunk query ran even though the ownership check failed — text "
        "must be unreachable, not merely unreturned (H7)."
    )


@pytest.mark.parametrize("module_name", ["legal", "finance"])
def test_workspace_helpers_delegate_ownership_and_do_not_reimplement_it(module_name):
    """H7: neither module may reintroduce a private chunk-by-id lookup."""
    module = __import__(
        f"app.api.v1.endpoints.{module_name}", fromlist=["_get_document_text"]
    )
    src = inspect.getsource(module._get_document_text)

    assert "get_owned_document_text" in src, (
        f"{module_name}._get_document_text no longer delegates to the shared "
        "owner-scoped helper. Two copies of this function is how H7 happened — "
        "both were missing the same check."
    )
    assert "DocumentChunk" not in src, (
        f"{module_name}._get_document_text queries DocumentChunk directly again. "
        "Ownership must be enforced in one place (H7)."
    )
    assert "current_user" in src, (
        f"{module_name}._get_document_text does not take the caller, so it "
        "cannot check ownership (H7)."
    )


def test_finance_analyze_has_no_comment_claiming_an_absent_control():
    """H6: the 'Verify document ownership' comment described nothing real."""
    from app.api.v1.endpoints import finance

    src = inspect.getsource(finance.compute_financial_ratios)
    if re.search(r"#\s*Verify document ownership", src):
        assert "get_owned_document" in src or "_get_document_text" in src, (
            "a comment claims ownership is verified but no owner-scoped lookup "
            "is present. A control that only exists in a comment is worse than "
            "an absent one — it stops the next reader looking (H6)."
        )
    # And regardless of comments: this endpoint must not reach document text
    # through a bare Document lookup.
    assert "_get_document_text(db, doc_id, current_user)" in src, (
        "compute_financial_ratios no longer routes document text through the "
        "owner-scoped helper (H6)."
    )


def test_query_stream_joins_chat_history_to_an_owned_session():
    """H10: ChatMessage has no owner column, so the join IS the filter."""
    from app.api.v1.endpoints import query as query_module

    src = inspect.getsource(query_module.ask_question_stream)
    tree = ast.parse(inspect.cleandoc(src))

    selects_chatmessage = any(
        isinstance(n, ast.Name) and n.id == "ChatMessage" for n in ast.walk(tree)
    )
    assert selects_chatmessage, "test is stale — ChatMessage no longer loaded here"

    assert "ChatSession.owner_id" in src, (
        "chat history is loaded without joining ChatSession and filtering "
        "owner_id. A caller can pass another user's session_id and have that "
        "transcript fed into the LLM prompt and paraphrased back (H10)."
    )
    assert "ChatMessage.session_id" in src
