"""Regression tests for DEBUG_MASTER_PLAN M-7.

config.py defaulted OTEL/Prometheus ON while .env.example said off, and
the trial nudge emails were hardcoded at uses 3/4 (a 5-query-limit relic;
the limit is 10). Defaults are now reconciled (observability opt-in) and
nudge thresholds derive from TRIAL_QUERY_LIMIT.
"""
import pathlib
import re

from app.core.config import Settings
from app.core.trial_enforcement import TRIAL_QUERY_LIMIT


def test_observability_defaults_are_off():
    assert Settings.model_fields["OTEL_ENABLED"].default is False
    assert Settings.model_fields["PROMETHEUS_ENABLED"].default is False


def test_env_examples_agree_with_config_defaults():
    root = pathlib.Path(__file__).resolve().parents[2]
    for env_file in (root / ".env.example", root / "backend" / ".env.example"):
        text = env_file.read_text(encoding="utf-8")
        assert re.search(r"^OTEL_ENABLED=false", text, re.M), env_file
        assert re.search(r"^PROMETHEUS_ENABLED=false", text, re.M), env_file


def test_trial_nudges_derive_from_limit():
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "api" / "v1" / "endpoints" / "query.py"
    ).read_text(encoding="utf-8")
    assert "TRIAL_QUERY_LIMIT - 2" in source
    assert "TRIAL_QUERY_LIMIT - 1" in source
    assert not re.search(r"_q_used == 3\b", source)
    assert TRIAL_QUERY_LIMIT == 10  # documents the current limit the UX keys on
