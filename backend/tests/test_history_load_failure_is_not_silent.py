"""Regression guard for the silent-failure table entry `query.py:328`.

Loading a chat's history and attached documents was wrapped in
`except Exception: logger.warning(...)`, leaving `attached_doc_ids = []`.

`[]` is not a neutral value here — it is MEANINGFUL. It means "this chat has
no documents", which makes GroundingService short-circuit, `is_grounded` go
False, and the stream answer in `mode: "general"` from the model's own
knowledge. That is correct when the chat really has no documents, and
completely wrong when it has documents that simply could not be read.

So a transient database error silently converted a grounded question about the
user's contract into a general-knowledge answer, with nothing anywhere saying
the documents had not been consulted. Confidently answering the wrong question
is worse than not answering.

Note this survived an earlier fix in this same run: S3 changed empty-vs-None
handling in the retrieval layer, which did NOT neutralise this — the empty
list still flows through as "no documents". Re-verified against the current
code rather than assumed.
"""
import ast
import inspect
import textwrap

from app.api.v1.endpoints import query as query_module

STREAM_SRC = inspect.getsource(query_module.ask_question_stream)


def _history_handler() -> ast.ExceptHandler:
    """The except handler guarding the history / attached-docs load."""
    tree = ast.parse(textwrap.dedent(STREAM_SRC))
    for handler in (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)):
        body = ast.dump(handler)
        if "load" in body and ("history" in body or "attached" in body):
            return handler
    raise AssertionError(
        "could not locate the history/attached-docs except handler — this test "
        "is stale and must be updated rather than deleted."
    )


def test_history_load_failure_does_not_fall_through_to_an_answer():
    """The handler must stop the stream, not continue ungrounded."""
    handler = _history_handler()
    returns = [n for n in ast.walk(handler) if isinstance(n, ast.Return)]
    assert returns, (
        "the history/attached-docs failure handler does not return. Falling "
        "through leaves attached_doc_ids == [], which reads as 'this chat has "
        "no documents' and produces a general-knowledge answer to a question "
        "about the user's documents (query.py:328)."
    )


def test_the_failure_is_reported_to_the_client():
    handler = _history_handler()
    dumped = ast.dump(handler)
    assert "event: error" in STREAM_SRC, "the stream has no error event at all"
    # The handler itself must emit one, not rely on a later branch.
    assert "error" in dumped.lower(), (
        "the history/attached-docs failure is not surfaced to the client. The "
        "user must be told their documents were not consulted."
    )


def test_the_failure_is_logged_at_error_not_warning():
    handler = _history_handler()
    dumped = ast.dump(handler)
    assert "'warning'" not in dumped and "attr='warning'" not in dumped, (
        "the history/attached-docs failure is logged at WARNING again. It "
        "changes the answer the user receives; that is not a warning."
    )
    assert "attr='error'" in dumped, (
        "the failure should be logged at ERROR with the session id."
    )


def test_nothing_is_sent_to_the_model_after_the_failure():
    """The refusal must happen BEFORE generation, not after paying for it."""
    handler = _history_handler()
    for node in ast.walk(handler):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"generate", "generate_stream"}, (
                "the failure handler still calls the model. The point of "
                "refusing is that the answer would not have been grounded in "
                "the user's documents."
            )
