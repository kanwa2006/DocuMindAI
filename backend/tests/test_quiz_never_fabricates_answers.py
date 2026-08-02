"""Regression guard for the silent-failure table entry `study.py:235`.

When the model's JSON failed to parse, `generate_quiz` called `_stub_quiz`,
which fabricated questions like:

    question:      "Sample hard question 1 about Photosynthesis."
    options:       ["Option A", "Option B", "Option C", "Option D"]
    correct_index: 0                      # ALWAYS Option A
    explanation:   "The correct answer is Option A based on … fundamentals."

Those rows were PERSISTED to `study_quizzes` and returned with HTTP 200. So
`/quiz/{id}/submit` then graded a real student against invented answers and
told them they were wrong. Nothing anywhere reported a failure.

`exams.py:419` already modelled honest behaviour by refusing. A quiz needs to
be stricter still: an exam paper is a document the reader judges for
themselves, whereas a quiz is SCORED. There is no such thing as a degraded
quiz, so the endpoint now fails loudly and writes nothing.
"""
import ast
import inspect
import pathlib

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import study as study_module

STUDY_SRC = pathlib.Path(inspect.getfile(study_module)).read_text(encoding="utf-8")


def test_the_stub_quiz_generator_no_longer_exists():
    """Deleted, not merely unwired — an unused fabricator is one call away."""
    assert not hasattr(study_module, "_stub_quiz"), (
        "_stub_quiz still exists. It fabricates answers with correct_index=0 "
        "and an explanation asserting Option A is correct; leaving it defined "
        "keeps that one call site away from returning."
    )

    tree = ast.parse(STUDY_SRC)
    defined = {
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_stub_quiz" not in defined


def test_no_fabricated_answer_text_remains_in_the_module():
    """The specific strings a student would have been shown."""
    for fabricated in (
        "The correct answer is Option A",
        '"Option A", "Option B", "Option C", "Option D"',
    ):
        # Allow the explanatory comments that record WHY this was removed;
        # reject the values themselves appearing in executable code.
        tree = ast.parse(STUDY_SRC)
        literals = [
            n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        ]
        assert not any(fabricated in lit for lit in literals), (
            f"the fabricated quiz text {fabricated!r} is still a string "
            "literal in study.py — it can still reach a student."
        )


@pytest.mark.asyncio
async def test_unparseable_model_output_raises_and_persists_nothing(monkeypatch):
    """The core contract: fail loudly, write nothing."""

    class _DB:
        def __init__(self):
            self.added = []

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            raise AssertionError(
                "commit() was called after a quiz parse failure — a fabricated "
                "or empty quiz is being persisted, which is what allowed a "
                "student to be graded against invented answers."
            )

        async def refresh(self, obj):
            pass

    async def _garbage(*args, **kwargs):
        return "I'm sorry, I cannot produce that as JSON."

    monkeypatch.setattr(
        "app.services.llm_service.llm_service.provider.generate", _garbage,
        raising=False,
    )

    from app.api.v1.endpoints.study import generate_quiz

    class _Req:
        topic = "Photosynthesis"
        count = 5
        difficulty = "hard"
        doc_ids = []
        workspace_id = None

    db = _DB()
    with pytest.raises(HTTPException) as exc:
        await generate_quiz(
            _Req(), current_user={"id": "00000000-0000-0000-0000-000000000001",
                                  "workspace_id": "study"}, db=db,
        )

    assert exc.value.status_code == 502, (
        f"expected a loud 502, got {exc.value.status_code}. A 200 with "
        "fabricated questions is the defect."
    )
    assert not db.added, "a quiz row was staged despite the generation failure"


@pytest.mark.asyncio
async def test_empty_question_list_is_also_a_failure(monkeypatch):
    """`[]` parses fine as JSON and is still an unusable quiz."""

    class _DB:
        def add(self, obj):
            raise AssertionError("an empty quiz must not be persisted")

        async def commit(self):
            raise AssertionError("an empty quiz must not be committed")

        async def refresh(self, obj):
            pass

    async def _empty(*args, **kwargs):
        return "[]"

    monkeypatch.setattr(
        "app.services.llm_service.llm_service.provider.generate", _empty,
        raising=False,
    )

    from app.api.v1.endpoints.study import generate_quiz

    class _Req:
        topic = "Photosynthesis"
        count = 5
        difficulty = "hard"
        doc_ids = []
        workspace_id = None

    with pytest.raises(HTTPException) as exc:
        await generate_quiz(
            _Req(), current_user={"id": "00000000-0000-0000-0000-000000000001",
                                  "workspace_id": "study"}, db=_DB(),
        )
    assert exc.value.status_code == 502
