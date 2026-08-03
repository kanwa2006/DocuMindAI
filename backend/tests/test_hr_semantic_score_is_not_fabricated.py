"""Regression guard for the silent-failure table entry `hr.py:462`.

When the sentence-transformer failed to load, the endpoint set
`similarity = 0.0` and fell through to the blend:

    final_score = 0.6 * llm_score + 0.4 * 0.0 * 100
                = 0.6 * llm_score

So a candidate was ranked FORTY PERCENT LOWER than their LLM fit score because
a model failed to load on the server. The response reported
`semantic_similarity: 0.0`, which asserts that the comparison RAN and found no
resemblance between the résumé and the job description — a damning finding
about a person, published because of an infrastructure error.

The old log line said "using fit_score only", which is exactly the right
behaviour and exactly what the code did not do.

Now: no fabricated zero enters the blend, `semantic_score` is None, the
breakdown says `semantic_available: false`, and the score is the LLM fit score
alone — labelled as not comparable with semantically scored candidates.
"""
import ast
import inspect
import textwrap

from app.api.v1.endpoints import hr as hr_module

SCORE_SRC = inspect.getsource(hr_module.score_candidate)


def _similarity_handler() -> ast.ExceptHandler:
    tree = ast.parse(textwrap.dedent(SCORE_SRC))
    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
    assert handlers, "no except handler in score_candidate — test is stale"
    return handlers[0]


def test_failure_does_not_assign_a_zero_similarity():
    """`similarity = 0.0` in the handler IS the defect."""
    handler = _similarity_handler()
    for node in ast.walk(handler):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "similarity" for t in node.targets
        ):
            assert not (
                isinstance(node.value, ast.Constant)
                and node.value.value == 0.0
            ), (
                "the similarity failure path assigns 0.0, which then flows "
                "into the blend as `0.4 * 0 * 100` and silently costs the "
                "candidate 40% of their score — while reporting that the "
                "comparison ran and found no match (hr.py:462)."
            )


def test_the_blend_is_skipped_when_similarity_is_unavailable():
    assert "semantic_available" in SCORE_SRC, (
        "score_candidate no longer tracks whether semantic scoring actually "
        "ran, so it cannot avoid blending against a number it never measured."
    )
    assert "final_score = round(llm_score, 1)" in SCORE_SRC, (
        "when semantic similarity is unavailable the score must be the LLM fit "
        "score ALONE — which is what the original log line already claimed was "
        "happening. Blending against a fabricated zero is the defect."
    )


def test_the_response_does_not_report_a_similarity_that_was_never_computed():
    assert '"semantic_available": semantic_available' in SCORE_SRC, (
        "the response does not tell the caller whether semantic similarity "
        "was computed."
    )
    # The reported similarity must be conditional, never an unguarded number.
    assert "round(similarity, 4) if semantic_available else None" in SCORE_SRC, (
        "semantic_similarity is still reported unconditionally. Reporting 0.0 "
        "claims the résumé was compared to the job description and did not "
        "match — a finding about a person, asserted from a model load error."
    )


def test_the_persisted_semantic_score_is_null_not_zero():
    assert (
        "job_match.semantic_score = round(similarity, 4) if semantic_available else None"
        in SCORE_SRC
    ), (
        "a fabricated 0.0 is still persisted to JobMatch.semantic_score. The "
        "column is nullable precisely so 'not measured' can be distinguished "
        "from 'measured as zero' — and the UI's 'LLM score only' label keys "
        "off exactly that distinction."
    )
