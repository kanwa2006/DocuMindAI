"""Regression guard for the silent-failure table entry `finance.py:505`.

When the extraction LLM response failed to parse, the endpoint set
`extraction_data = {}` and carried on. `compute_ratios` then produced all 15
ratios with `value: None`, and the endpoint returned HTTP 200.

That output is byte-identical to the legitimate result "this document contains
no financial statements". A CA reading fifteen empty ratio cards could not
tell whether the document had no numbers or the system had failed to read
them — and the second case is the one where you retry rather than conclude.

Three states are now distinguishable:

  extraction FAILED        -> 502, nothing persisted
  no financials in the doc -> 200, extraction_status="no_financial_data"
  extraction succeeded     -> 200, extraction_status="ok"
"""
import inspect
import uuid

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import finance as finance_module

RATIOS_SRC = inspect.getsource(finance_module.compute_financial_ratios)


def test_extraction_failure_does_not_fall_through_to_an_empty_dict():
    """`extraction_data = {}` in the except branch IS the defect."""
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(RATIOS_SRC))
    for handler in (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)):
        for node in ast.walk(handler):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "extraction_data"
                    for t in node.targets
                )
                and isinstance(node.value, ast.Dict)
                and not node.value.keys
            ):
                raise AssertionError(
                    "the extraction failure path assigns an empty dict and "
                    "continues, so all 15 ratios come back None with HTTP 200 "
                    "— indistinguishable from a document that genuinely has no "
                    "financials (finance.py:505)."
                )


def test_extraction_failure_raises_rather_than_returning_empty_ratios():
    assert "status_code=502" in RATIOS_SRC, (
        "the extraction failure path no longer raises. Nothing was extracted, "
        "so there is nothing to report — returning 15 empty ratios presents a "
        "failure as a finding."
    )
    assert "NOT a finding that the document has no" in RATIOS_SRC, (
        "the failure message should state explicitly that this is not a "
        "finding of 'no financial data' — that is the exact confusion the "
        "silent version created."
    )


def test_the_legitimate_empty_case_is_named_not_just_blank():
    assert "no_financial_data" in RATIOS_SRC, (
        "a successful extraction that finds no line items must be labelled "
        "`no_financial_data`. Otherwise the honest empty result is still "
        "indistinguishable from the failure it was just separated from."
    )
    assert '"extraction_status"' in RATIOS_SRC


@pytest.mark.asyncio
async def test_parse_failure_surfaces_as_502(monkeypatch):
    """End-to-end on the endpoint function, with the model returning garbage."""

    async def _garbage(*args, **kwargs):
        return "I cannot produce that."

    async def _doc_text(db, document_id, current_user):
        return "Some contract text with no tables.", []

    monkeypatch.setattr(
        "app.services.llm_service.llm_service.generate", _garbage, raising=False
    )
    monkeypatch.setattr(finance_module, "_get_document_text", _doc_text)

    class _Req:
        document_ids = [str(uuid.uuid4())]

    with pytest.raises(HTTPException) as exc:
        await finance_module.compute_financial_ratios(
            _Req(),
            current_user={"id": str(uuid.uuid4()), "workspace_id": "finance"},
            db=object(),
        )

    assert exc.value.status_code == 502, (
        f"expected 502 on extraction failure, got {exc.value.status_code}. A "
        "200 carrying fifteen empty ratios is the defect."
    )
