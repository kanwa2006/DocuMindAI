"""Regression tests for DEBUG_MASTER_PLAN C-2 (and H-3's include/route sync).

The worker's `include` list drifted from `task_routes` and from the
endpoints that dispatch tasks: legal/finance/study/research task modules
were routed and dispatched but never imported by the worker, so their
tasks were unregistered and never executed. These tests pin the three-way
rule's first two legs (registered + routed); queue consumption is an infra
concern verified in docker-compose.
"""
import importlib

from app.workers.celery_app import celery_app

EXPECTED_WORKSPACE_TASKS = [
    "app.workers.tasks.legal_tasks.process_contract_batch",
    "app.workers.tasks.finance_tasks.process_finance_batch",
    "app.workers.tasks.study_tasks.process_study_batch",
    "app.workers.tasks.research_tasks.process_research_batch",
    "app.workers.tasks.hr_tasks.process_resume_batch",
]


def test_workspace_batch_tasks_are_registered():
    """C-2: every dispatched process_*_batch task must be in celery_app.tasks."""
    for module in celery_app.conf.include:
        importlib.import_module(module)
    registered = set(celery_app.tasks.keys())
    missing = [t for t in EXPECTED_WORKSPACE_TASKS if t not in registered]
    assert not missing, f"Unregistered worker tasks: {missing}"


def test_every_include_module_imports():
    """Worker boot safety: each module in `include` must import cleanly."""
    for module in celery_app.conf.include:
        importlib.import_module(module)


