"""Regression tests for DEBUG_MASTER_PLAN C-4.

/query/stream never emitted the `trust_report` SSE event the frontend
already parses (lib/api.ts askQuestionStream -> onTrustReport). These tests
pin the caller-side Veritas wiring in endpoints/query.py: the payload must
match the frontend TrustReport interface (TrustScoreBadge.tsx) and the
frame must render as a well-formed SSE event that never breaks the stream.
"""
import json

import pytest

from app.api.v1.endpoints.query import _compute_trust_event, _veritas_sse_payload
from app.services.veritas_engine import VeritasTrustReport

CHUNKS = [
    {"text_content": "Revenue rose 20% in Q1.", "filename": "r.pdf", "page_number": 1},
    {"text_content": "Costs fell 5%.", "filename": "r.pdf", "page_number": 2},
    {"text_content": "Margin improved.", "filename": "r.pdf", "page_number": 3},
]

FRONTEND_KEYS = {
    "final_score", "level", "evidence_items", "warnings",
    "factors", "contradictions", "summary",
}


def test_payload_matches_frontend_trust_report_interface():
    report = VeritasTrustReport(
        final_score=72, grade="MEDIUM", evidence=["e"], warnings=["w"],
        factor_scores={"dual_retrieval": 70.0, "direct_quote": 55.0},
    )
    payload = _veritas_sse_payload(report)
    assert set(payload.keys()) == FRONTEND_KEYS
    assert payload["level"] in ("HIGH", "MEDIUM", "LOW")
    for factor in payload["factors"]:
        assert set(factor.keys()) == {"name", "weight", "score"}


def test_very_low_and_unknown_grades_map_to_low():
    for grade in ("VERY_LOW", "UNKNOWN"):
        payload = _veritas_sse_payload(VeritasTrustReport(final_score=10, grade=grade))
        assert payload["level"] == "LOW"


@pytest.mark.asyncio
async def test_compute_trust_event_renders_sse_frame():
    frame = await _compute_trust_event(
        "Revenue rose 20% in Q1. (r.pdf, p.1)", CHUNKS, "revenue?", ["d1"], None
    )
    assert frame.startswith("event: trust_report\ndata: ")
    data = json.loads(frame.split("data: ", 1)[1].strip())
    assert 0 <= data["final_score"] <= 100
    assert set(data.keys()) == FRONTEND_KEYS


@pytest.mark.asyncio
async def test_compute_trust_event_failure_is_loud_not_fatal(caplog, monkeypatch):
    """A Veritas failure must log at ERROR and return "" (stream unbroken)."""
    import logging
    from app.api.v1.endpoints import query as query_module

    async def boom(**kwargs):
        raise RuntimeError("veritas exploded")

    monkeypatch.setattr(query_module.veritas_engine, "compute_trust_score", boom)
    with caplog.at_level(logging.ERROR, logger="app.api.v1.endpoints.query"):
        frame = await _compute_trust_event("a", CHUNKS, "q", None, None)
    assert frame == ""
    assert any("Veritas trust computation failed" in r.message for r in caplog.records)
