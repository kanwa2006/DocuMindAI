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


def test_task_routes_reference_existing_modules():
    """H-3: no task_route may point at a nonexistent module (the phantom
    embedding_tasks/retrieval_tasks routes were dead config)."""
    for pattern in celery_app.conf.task_routes:
        module_path = pattern.rsplit(".", 1)[0] if pattern.endswith(".*") else pattern
        importlib.import_module(module_path)


def test_routed_queues_are_consumed_by_compose_worker():
    """H-3: every queue in task_routes must appear in the deployed worker's
    -Q list (three-way rule leg 3). Parses docker-compose so drift fails CI."""
    import pathlib
    import re

    compose = pathlib.Path(__file__).resolve().parents[2] / "infrastructure" / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8")
    match = re.search(r"worker\s+-Q\s+([\w,\-]+)", text)
    assert match, "worker -Q queue list not found in docker-compose.yml"
    consumed = set(match.group(1).split(","))

    routed = set(celery_app.conf.task_routes.values())
    unconsumed = routed - consumed
    assert not unconsumed, f"Routed queues with no consumer: {unconsumed}"


