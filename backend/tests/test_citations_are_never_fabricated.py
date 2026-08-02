"""Regression guard for the silent-failure table entry `research.py:228`.

When bibliographic metadata extraction failed, the endpoint substituted

    {"author": "", "title": doc.filename, "journal": "", "year": "", ...}

and handed it to a REAL formatter. The APA/MLA/IEEE formatters fill blanks
with "Unknown Author" and "n.d.", so the output was a correctly formatted
bibliography entry for a paper whose metadata had never been read:

    Unknown Author (n.d.). meridian_vendor_msa.pdf. .

Indistinguishable in the response from a genuine citation, in the one feature
whose entire purpose is bibliographic accuracy. A researcher pastes that into
a manuscript.

A citation that could not be extracted is now REPORTED as a failure, not
rendered as a citation.
"""
import inspect
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints import research as research_module


class _Doc:
    def __init__(self, name):
        self.id = uuid.uuid4()
        self.filename = name


async def _one_doc(*args, **kwargs):
    return [(_Doc("meridian_vendor_msa.pdf"), "Some extracted body text.")]


class _Req:
    def __init__(self, fmt="APA"):
        self.doc_ids = [str(uuid.uuid4())]
        self.format = fmt


@pytest.mark.asyncio
async def test_failed_extraction_produces_no_citation_at_all():
    """The core contract: a failure must not become a bibliography entry."""
    with patch.object(research_module, "_load_owned_docs_with_text", _one_doc), patch(
        "app.services.llm_service.llm_service.generate",
        new=AsyncMock(side_effect=RuntimeError("model unavailable")),
    ):
        result = await research_module.export_citations(
            _Req(), current_user={"id": str(uuid.uuid4()), "workspace_id": "research"},
            db=object(),
        )

    assert result["citations"] == [], (
        f"a citation was emitted for a document whose metadata extraction "
        f"failed: {result['citations']!r}. That is a fabricated bibliography "
        "entry — formatted correctly, sourced from nothing."
    )
    assert result["count"] == 0
    assert result["failed_count"] == 1, "the failure was not reported to the caller"
    assert result["failed"][0]["filename"] == "meridian_vendor_msa.pdf"


@pytest.mark.asyncio
async def test_the_filename_never_becomes_a_citation_title():
    """The specific fabrication: filename promoted to a paper title."""
    with patch.object(research_module, "_load_owned_docs_with_text", _one_doc), patch(
        "app.services.llm_service.llm_service.generate",
        new=AsyncMock(side_effect=RuntimeError("model unavailable")),
    ):
        result = await research_module.export_citations(
            _Req(), current_user={"id": str(uuid.uuid4()), "workspace_id": "research"},
            db=object(),
        )

    assert not any("meridian_vendor_msa.pdf" in c for c in result["citations"]), (
        "the filename is being formatted as a citation title. A PDF filename "
        "is not a paper title, and 'Unknown Author (n.d.)' around it does not "
        "make the entry honest — it makes it look deliberate."
    )


@pytest.mark.asyncio
async def test_a_successful_extraction_still_produces_a_citation():
    """The fix must not suppress real citations along with fabricated ones."""
    good = (
        '{"author": "Vaswani, Ashish", "title": "Attention Is All You Need", '
        '"journal": "NeurIPS", "year": "2017", "doi": "", "volume": "30", '
        '"issue": "", "pages": "5998-6008", "publisher": ""}'
    )
    with patch.object(research_module, "_load_owned_docs_with_text", _one_doc), patch(
        "app.services.llm_service.llm_service.generate",
        new=AsyncMock(return_value=good),
    ):
        result = await research_module.export_citations(
            _Req(), current_user={"id": str(uuid.uuid4()), "workspace_id": "research"},
            db=object(),
        )

    assert result["count"] == 1 and result["failed_count"] == 0
    assert "Vaswani" in result["citations"][0]


def test_the_filename_fallback_metadata_is_gone_from_the_source():
    """No dict literal may map "title" to the document's filename.

    Matched over the AST, not the source text. The fix's own comment quotes
    the old `{"title": doc.filename}` while explaining why it was removed, and
    a text scan flags that explanation as the defect. That mistake has now
    been made three times in this test suite (P-1, S12, here) — a guard that
    greps for the thing it documents will always fail on correct code.
    """
    import ast
    import textwrap

    tree = ast.parse(
        textwrap.dedent(inspect.getsource(research_module.export_citations))
    )

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and key.value == "title"):
                continue
            if (
                isinstance(value, ast.Attribute)
                and value.attr == "filename"
            ):
                offenders.append(node.lineno)

    assert not offenders, (
        f"a dict at line(s) {offenders} maps \"title\" to a document filename. "
        "That single substitution is what turned an extraction failure into a "
        "correctly formatted, entirely invented bibliography entry."
    )
