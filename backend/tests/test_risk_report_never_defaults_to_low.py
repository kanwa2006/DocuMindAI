"""Regression guard for the silent-failure table entry `legal.py:390`.

When the risk-analysis LLM response failed to parse, the endpoint returned:

    {"overall_risk_score": 0, "overall_risk_level": "Low",
     "summary": "Unable to parse risk analysis."}

with HTTP 200. So a PARSE ERROR rendered in the UI as a green ring reading
"0/100 — Low Risk". This is the single output a lawyer acts on directly, and
it said the safest possible thing at exactly the moment the system knew
nothing at all.

One line below, the same defect in quieter form: `risk_data.get(
"overall_risk_level", "Low")` meant a response that PARSED but omitted the key
also became "Low".

"Unassessable" is not invented for this fix — it is already in `RISK_LEVELS`
(value -1, deliberately excluded from the consistency drift check) and the
system prompt already instructs the model to use it when confidence is low.
The failure path simply was not using the vocabulary the success path had.

The score is None rather than 0 because 0 is a claim ("no risk found") and
None is the absence of one.
"""
import ast
import inspect
import pathlib

from app.api.v1.endpoints import legal as legal_module

LEGAL_SRC = pathlib.Path(inspect.getfile(legal_module)).read_text(encoding="utf-8")
RISK_REPORT_SRC = inspect.getsource(legal_module.generate_risk_report)


def test_unassessable_is_a_known_risk_level():
    """The honest value must exist in the vocabulary the rest of the code uses."""
    assert legal_module.RISK_LEVELS.get("Unassessable") == -1, (
        "Unassessable is missing from RISK_LEVELS, or no longer sorts below "
        "every real level. The consistency drift check relies on it being "
        "negative so an unassessed report is not compared as if it were a "
        "verdict."
    )


def test_parse_failure_does_not_report_low_risk():
    """The except branch must not assert a risk level it did not compute."""
    tree = ast.parse(inspect.cleandoc(RISK_REPORT_SRC))

    for handler in (n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)):
        for node in ast.walk(handler):
            if not isinstance(node, ast.Dict):
                continue
            pairs = {
                k.value: v for k, v in zip(node.keys, node.values)
                if isinstance(k, ast.Constant)
            }
            level = pairs.get("overall_risk_level")
            if level is None:
                continue
            assert isinstance(level, ast.Constant) and level.value == "Unassessable", (
                "the risk-report failure path sets overall_risk_level to "
                f"{getattr(level, 'value', level)!r}. A parse error must never "
                "render as a risk VERDICT — least of all the safest one. Use "
                "'Unassessable'."
            )
            score = pairs.get("overall_risk_score")
            assert isinstance(score, ast.Constant) and score.value is None, (
                "the failure path reports a numeric risk score. 0 is a claim "
                "('no risk found'); None is the absence of one."
            )


def test_missing_key_does_not_default_to_low():
    """A response that parses but omits the key is equally unassessed."""
    assert 'risk_data.get("overall_risk_level", "Low")' not in LEGAL_SRC, (
        "overall_risk_level still defaults to 'Low' when the model omits it. "
        "An absent verdict is not a verdict of low risk."
    )
    assert 'risk_data.get("overall_risk_score", 0)' not in LEGAL_SRC, (
        "overall_risk_score still defaults to 0 when the model omits it."
    )


def test_an_unassessable_contract_escalates_for_human_review():
    """The case most needing a human must not slip under the threshold.

    This also guards a real crash: `overall_score` is now None on the failure
    path, and the original `if overall_score >= 70` would raise TypeError.
    """
    assert 'if overall_level == "Unassessable"' in RISK_REPORT_SRC, (
        "an unassessed contract no longer escalates. Previously it could not: "
        "the failure path claimed Low/0 and sailed under every trigger. An "
        "unassessed contract is exactly what a human should look at."
    )
    assert "overall_score >= 70" not in RISK_REPORT_SRC or "(overall_score or 0) >= 70" in RISK_REPORT_SRC, (
        "the escalation threshold compares a possibly-None score directly, "
        "which raises TypeError on the failure path."
    )
