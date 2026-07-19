"""Regression test for DEBUG_MASTER_PLAN M-11.

process_document dispatched proactive insights with
getattr(doc, "workspace_type", None) — an attribute Document never had —
so the workspace always resolved to "general" and domain insight prompts
(legal risk, finance anomalies, HR standouts) never ran. The slug is now
read from the upload's ChatSession.workspace_type (uuid5 workspace ids
cannot be reversed).
"""
import pathlib
import re

from app.models.document import Document
from app.models.chat import ChatSession


def test_document_model_still_has_no_workspace_type():
    """The root cause: Document has no workspace_type. If someone adds one,
    this fix should be revisited (and this test updated)."""
    assert "workspace_type" not in Document.__table__.columns


def test_chat_session_carries_the_workspace_slug():
    assert "workspace_type" in ChatSession.__table__.columns


def test_dispatch_reads_workspace_from_chat_session():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "workers" / "tasks" / "document_tasks.py"
    ).read_text(encoding="utf-8")
    # The broken pattern must be gone…
    assert 'getattr(doc, "workspace_type"' not in source
    # …and the session lookup present, feeding the insights dispatch.
    assert re.search(r"ChatSession\.id == doc\.chat_session_id", source)
    assert "chat_session.workspace_type" in source
