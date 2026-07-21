"""Regression tests for DEBUG_MASTER_PLAN H-4.

`GET /research/synthesis/{project_id}` returned a hardcoded fake payload
("X causes Y", "Paper A suggests…") regardless of data. It now clusters
real findings (Python cosine math), asks the LLM only to classify
candidate cross-paper pairs, and persists ContradictionReport rows.
"""
import math
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.research import synthesize_project
from app.models.research import ResearchFinding
from app.schemas.research import ContradictionVerdictSchema

USER = {"id": str(uuid.uuid4()), "workspace_id": "research"}


def _finding(statement, paper_id, embedding):
    f = ResearchFinding(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        paper_id=paper_id,
        statement=statement,
    )
    f.embedding = embedding
    return f


def _db_returning(rows):
    db = MagicMock()
    result = MagicMock()
    result.all.return_value = rows
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_empty_project_returns_empty_payload():
    db = _db_returning([])
    payload = await synthesize_project(uuid.uuid4(), USER, db)
    assert payload == {"status": "success", "clusters": [], "contradictions": []}


@pytest.mark.asyncio
async def test_synthesis_is_derived_from_findings_not_static():
    paper_a, paper_b = uuid.uuid4(), uuid.uuid4()
    # ~0.9 cosine between the two vectors → same cluster + contradiction candidate
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.9, math.sqrt(1 - 0.81), 0.0]
    rows = [
        (_finding("Drug X reduces symptoms significantly", paper_a, v1), "Paper A"),
        (_finding("Drug X shows no measurable effect", paper_b, v2), "Paper B"),
    ]
    db = _db_returning(rows)

    verdict = ContradictionVerdictSchema(
        verdict="contradict",
        description="A reports efficacy while B reports no effect.",
    )
    with patch(
        "app.services.llm_service.llm_service.generate_json",
        new=AsyncMock(return_value=verdict),
    ):
        payload = await synthesize_project(uuid.uuid4(), USER, db)

    statements = [
        f["statement"] for c in payload["clusters"] for f in c["findings"]
    ]
    assert "Drug X reduces symptoms significantly" in statements
    assert "Drug X shows no measurable effect" in statements
    # The old static strings must be gone.
    assert all(c["topic"] != "X causes Y" for c in payload["clusters"])

    assert payload["contradictions"] == [
        {"description": "A reports efficacy while B reports no effect.",
         "severity": "HIGH"}
    ]
    db.add.assert_called_once()   # ContradictionReport persisted
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_failure_skips_pair_loudly_without_fabrication(caplog):
    import logging

    paper_a, paper_b = uuid.uuid4(), uuid.uuid4()
    v1 = [1.0, 0.0]
    v2 = [0.9, math.sqrt(1 - 0.81)]
    rows = [
        (_finding("Statement one about a topic", paper_a, v1), "Paper A"),
        (_finding("Statement two about the same topic", paper_b, v2), "Paper B"),
    ]
    db = _db_returning(rows)
    with patch(
        "app.services.llm_service.llm_service.generate_json",
        new=AsyncMock(side_effect=RuntimeError("llm down")),
    ), caplog.at_level(logging.ERROR, logger="app.api.v1.endpoints.research"):
        payload = await synthesize_project(uuid.uuid4(), USER, db)

    assert payload["contradictions"] == []       # nothing fabricated
    assert payload["clusters"]                   # clustering still works
    assert any("Contradiction check failed" in r.message for r in caplog.records)
