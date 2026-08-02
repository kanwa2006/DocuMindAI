"""Regression guard for final_audit S13.

`_get_tavily` referenced `settings.TAVILY_API_KEY`, a field that did not exist
in `core/config.py`. The resulting `AttributeError` was caught by an
over-broad `except Exception`, so the client was None forever and the
advertised "hybrid RAG + web intelligence" pipeline had been document-only
since the day it shipped.

The damaging part was not the missing key — it was that step 3 still emitted
`status="done", message="Found 0 current source(s)"`. A step that never ran
reported success, and the synthesis prompt then told the model "No web sources
found", inviting it to describe an absence as a finding.

These tests pin the three properties that make that impossible:

1. `TAVILY_API_KEY` exists on Settings, so the AttributeError cannot recur.
2. With no key configured, step 3 reports SKIPPED — never "done".
3. `_get_tavily` does not swallow a missing key as if it were a client error.
"""
import inspect
import re
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings, settings
from app.services.deep_research_agent import DeepResearchAgent

FAKE_CHUNKS = [
    {
        "chunk_id": "c1",
        "document_id": "d1",
        "filename": "paper.pdf",
        "page_number": 2,
        "chunk_index": 0,
        "text_content": "Transformers use self-attention over token sequences.",
        "similarity_score": 0.9,
        "lexical_score": 0.5,
        "rrf_score": 0.03,
        "layout_metadata": None,
    }
]


def test_tavily_api_key_is_a_declared_setting():
    """The field must exist, or `settings.TAVILY_API_KEY` raises AttributeError."""
    assert "TAVILY_API_KEY" in Settings.model_fields, (
        "TAVILY_API_KEY is not declared on Settings — reading it raises "
        "AttributeError, which is exactly how web search silently never ran (S13)."
    )
    # Optional: absence must be a supported state, not a startup failure.
    assert Settings.model_fields["TAVILY_API_KEY"].default is None


def test_missing_key_is_not_swallowed_as_a_generic_exception():
    """A bare `except Exception` here is what hid the missing field.

    Matched against the parsed handlers rather than the raw source: the
    function's own docstring explains the old `except Exception`, and a naive
    text search matches that prose and fails on correct code.
    """
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(DeepResearchAgent._get_tavily)))
    caught = [
        handler.type.id
        for handler in ast.walk(tree)
        if isinstance(handler, ast.ExceptHandler)
        and isinstance(handler.type, ast.Name)
    ]
    assert "Exception" not in caught, (
        "_get_tavily catches bare Exception again. That makes a missing config "
        "field, an uninstalled package and a real client error indistinguishable "
        f"— all three become 'return None' forever (S13). Caught: {caught}"
    )


@pytest.mark.asyncio
async def test_web_step_reports_skipped_not_done_when_unconfigured(monkeypatch):
    """With no API key, step 3 must say SKIPPED — never 'Found 0 sources'."""
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None, raising=False)
    agent = DeepResearchAgent()

    with patch(
        "app.services.retrieval_service.RetrievalService.retrieve_chunks",
        new=AsyncMock(return_value={"results": FAKE_CHUNKS, "tracing": {}}),
    ), patch(
        "app.services.llm_service.llm_service.generate_answer",
        new=AsyncMock(return_value={"answer": "An answer.", "generation_time_sec": 0.1}),
    ), patch(
        # Force a non-empty gap list so step 3 is actually reached.
        "app.services.llm_service.llm_service.generate",
        new=AsyncMock(return_value='["what is the current rate?"]'),
    ):
        events = [
            e async for e in agent.research(
                "q", [str(uuid.uuid4())], owner_id=str(uuid.uuid4()), db=object()
            )
        ]

    step3 = [e for e in events if e.step == 3]
    assert step3, "step 3 never ran — the test did not reach the web-search step"

    statuses = {e.status for e in step3}
    assert "skipped" in statuses, (
        f"step 3 did not report skipped with no API key; statuses were {statuses}"
    )
    assert "done" not in statuses, (
        "step 3 reported DONE for a web search that never ran — this is the "
        "exact false success S13 describes. "
        f"Messages: {[e.message for e in step3]}"
    )
    assert not any("Found 0" in e.message for e in step3), (
        "step 3 still claims it 'Found 0 current source(s)', which asserts a "
        "search took place."
    )
