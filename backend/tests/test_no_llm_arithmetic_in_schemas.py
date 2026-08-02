"""Regression guard for final_audit S10.

The Finance response schema instructed the model to do the arithmetic:

    3. Ratios → show the formula, the inputs, then the result:
       **Current Ratio** = Current Assets / Current Liabilities = ₹X / ₹Y = **2.4x**

That is a direct violation of extract-then-compute — "the LLM extracts fields;
Python computes every number" — in the exact workspace the invariant exists to
protect. A model asked to evaluate `₹X / ₹Y` in-context produces an
authoritative-looking number carrying a real page citation, which is the worst
possible failure shape: wrong, precise, and sourced.

It was live on every finance chat query via `query.py:520`.

The 15 ratios computed in Python on the finance ENDPOINTS were never affected
— that is what makes this insidious. The endpoints were correct, so anyone
checking "do we compute ratios in Python?" found the right answer and stopped,
while the chat path quietly asked the model to do it instead.

These tests pin the invariant at the schema layer for every workspace, not
just finance, since the same instruction could be added to any of them.
"""
import re

import pytest

from app.services.response_schemas import get_response_schema

WORKSPACES = ["general", "hr", "legal", "finance", "research", "study", "exam"]

# A worked arithmetic EXAMPLE: an expression followed by `=` and a concrete
# numeric result. This is what tells a model "evaluate this yourself".
_WORKED_RESULT = re.compile(
    r"=\s*[₹$€£]?\s*[\dX]+\s*[/*+\-]\s*[₹$€£]?\s*[\dY]+\s*=\s*\*{0,2}[\d.]+",
)


@pytest.mark.parametrize("workspace", WORKSPACES)
def test_no_schema_contains_a_worked_arithmetic_example(workspace):
    schema = get_response_schema(workspace)
    match = _WORKED_RESULT.search(schema)
    assert not match, (
        f"the {workspace} schema shows the model a worked calculation "
        f"({match.group(0)!r}). Demonstrating `inputs = result` instructs the "
        "model to evaluate the expression, which is exactly how S10 put LLM "
        "arithmetic on the finance query path. Python computes every number."
    )


def test_finance_schema_explicitly_forbids_arithmetic():
    schema = get_response_schema("finance")
    lowered = schema.lower()
    assert "never perform arithmetic" in lowered, (
        "the finance schema no longer forbids arithmetic outright. Extract-"
        "then-compute is the reason figures in this product cannot be "
        "hallucinated; the finance workspace is where it matters most (S10)."
    )
    assert "computed in python" in lowered, (
        "the finance schema should tell the model that ratios arrive already "
        "computed, so it presents rather than derives them."
    )


def test_finance_schema_does_not_license_deriving_figures():
    """`Mark any value you had to derive` was a licence to derive."""
    schema = get_response_schema("finance")
    assert not re.search(r"value you had to derive", schema, re.I), (
        "the finance schema still invites the model to derive values and just "
        "label them. Under extract-then-compute the model must not derive at "
        "all — labelling a hallucinated figure does not make it safe (S10)."
    )


def test_finance_schema_still_instructs_traceable_ratio_presentation():
    """The fix must not silently delete the feature it was narrowing.

    Ratios still have to be shown with their formula and named inputs — that
    traceability is the point of computing them in Python. Only the model's
    evaluation of them is removed.
    """
    schema = get_response_schema("finance")
    assert "Current Ratio" in schema and "Current Assets / Current Liabilities" in schema, (
        "ratio presentation guidance was removed entirely rather than narrowed "
        "to formatting. The formula and its named inputs must still be shown."
    )
