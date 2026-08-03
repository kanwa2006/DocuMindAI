"""Regression guard for the silent-failure table entry `legal.py:85`.

`_log_audit` swallowed every failure at WARNING and returned None, so a
dropped entry in the IMMUTABLE COMPLIANCE AUDIT TRAIL was indistinguishable
from a successful write.

An audit log that silently loses records is worse than having no audit log,
because its entire value is that you can rely on it: a missing entry reads as
"this event never happened". Losing one quietly converts an absence of
evidence into evidence of absence.

Two things now hold:
  • the failure is logged at ERROR with the event, user, document and analysis
  • the outcome is RETURNED, and the endpoint reports `audit_logged` so the
    caller is not told an action was recorded when it was not

The same treatment is applied to the analysis persistence swallow one block
away — it answers the same question ("was this recorded?") and produced the
same lie (a report returned as though saved).
"""
import inspect
import logging
import uuid

import pytest

from app.api.v1.endpoints import legal as legal_module

AUDIT_SRC = inspect.getsource(legal_module._log_audit)
REPORT_SRC = inspect.getsource(legal_module.generate_risk_report)


class _FailingDB:
    """A session whose commit always fails."""

    def __init__(self):
        self.rolled_back = False

    def add(self, obj):
        pass

    async def commit(self):
        raise RuntimeError("database is down")

    async def rollback(self):
        self.rolled_back = True


class _WorkingDB:
    def add(self, obj):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


@pytest.mark.asyncio
async def test_audit_failure_returns_false_and_logs_at_error(caplog):
    db = _FailingDB()
    with caplog.at_level(logging.ERROR, logger=legal_module.__name__):
        ok = await legal_module._log_audit(
            db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "analysis_created", {}
        )

    assert ok is False, (
        "_log_audit returned a truthy/None result after failing to write. The "
        "caller cannot distinguish a lost compliance record from a written one."
    )
    assert any("AUDIT ENTRY LOST" in r.message for r in caplog.records), (
        "a dropped audit entry produced no ERROR log. WARNING was the original "
        "defect — this is the immutable compliance trail."
    )
    assert db.rolled_back, (
        "a failed audit write left the session dirty; it must not poison the "
        "request that triggered it."
    )


@pytest.mark.asyncio
async def test_successful_audit_returns_true():
    ok = await legal_module._log_audit(
        _WorkingDB(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "x", {}
    )
    assert ok is True


def test_audit_failure_is_not_swallowed_at_warning():
    assert "logger.warning" not in AUDIT_SRC, (
        "_log_audit logs its failure at WARNING again. A lost compliance audit "
        "record is not a warning-level event."
    )
    assert "return False" in AUDIT_SRC and "return True" in AUDIT_SRC, (
        "_log_audit no longer reports its outcome, so the endpoint cannot tell "
        "the caller the record was lost."
    )


def test_the_endpoint_reports_whether_it_recorded_anything():
    assert '"audit_logged"' in REPORT_SRC, (
        "the risk report does not tell the caller whether the compliance audit "
        "entry was written."
    )
    assert '"persisted"' in REPORT_SRC, (
        "the risk report does not tell the caller whether the analysis was "
        "actually saved — the same silent failure, one block away."
    )


def test_audit_rows_are_not_linked_to_an_unsaved_analysis():
    """After a rollback `analysis.id` is None; don't pretend otherwise."""
    assert "analysis_ref = analysis.id if persisted else None" in REPORT_SRC, (
        "audit rows still reference `analysis.id` unconditionally. When "
        "persistence failed that value is None (the uuid4 default is applied "
        "at flush and the rollback discarded it), so the audit entry silently "
        "loses its link to the analysis it describes."
    )
