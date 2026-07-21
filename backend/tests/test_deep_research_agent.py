"""Regression tests for DEBUG_MASTER_PLAN C-5.

Deep Research step 1 previously imported a nonexistent `retrieval_service`
singleton and called a nonexistent `.query()` method, so document RAG
always raised and was silently swallowed (doc_answer="", citations=[]).
These tests pin the rewritten step 1: real `RetrievalService.retrieve_chunks`
call, synthesized doc answer, populated citations, non-zero trust input.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.mark.asyncio
async def test_step1_retrieves_chunks_and_synthesizes_answer():
    agent = DeepResearchAgent()
    doc_id = str(uuid.uuid4())

    with patch(
        "app.services.retrieval_service.RetrievalService.retrieve_chunks",
        new=AsyncMock(return_value={"results": FAKE_CHUNKS, "tracing": {}}),
    ) as mock_retrieve, patch(
        "app.services.llm_service.llm_service.generate_answer",
        new=AsyncMock(return_value={"answer": "Self-attention (paper.pdf, p.2).", "generation_time_sec": 0.1}),
    ), patch(
        "app.services.llm_service.llm_service.generate",
        new=AsyncMock(return_value="[]"),
    ):
        events = [e async for e in agent.research("what is attention?", [doc_id], db=object())]

    mock_retrieve.assert_awaited_once()
    _, kwargs = mock_retrieve.await_args
    assert kwargs["query"] == "what is attention?"
    assert kwargs["document_ids"] == [uuid.UUID(doc_id)]

    step1_done = next(e for e in events if e.step == 1 and e.status == "done")
    assert "1 passages" in step1_done.message

    final = next(e for e in events if e.step == "final")
    assert final.doc_citations == FAKE_CHUNKS
    assert final.answer  # synthesis produced something
    assert final.doc_trust is not None
    assert final.doc_trust.final_score > 0


@pytest.mark.asyncio
async def test_step1_failure_is_loud_but_degrades(caplog):
    """A retrieval failure must log at ERROR (not silently pass) and still
    yield a usable degraded event stream."""
    import logging

    agent = DeepResearchAgent()
    with patch(
        "app.services.retrieval_service.RetrievalService.retrieve_chunks",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ), patch(
        "app.services.llm_service.llm_service.generate",
        new=AsyncMock(return_value="[]"),
    ), caplog.at_level(logging.ERROR, logger="app.services.deep_research_agent"):
        events = [e async for e in agent.research("q", [str(uuid.uuid4())], db=object())]

    assert any("RAG pipeline error" in r.message for r in caplog.records)
    final = next(e for e in events if e.step == "final")
    assert final.doc_trust.final_score == 0
    assert final.doc_citations == []
