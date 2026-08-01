"""Regression guard for P0-7 — Celery tasks must not use the async DB session.

`CLAUDE.md` states the invariant: FastAPI + asyncpg on the request path, Celery +
`SyncSessionLocal` (psycopg2) on the worker path, never mixed.

Violating it does not fail loudly or consistently, which is why it survived so
long. A sync Celery task calling `asyncio.run()` builds a NEW event loop every
invocation, while the async engine pools connections bound to the loop that
created them. The first task in a worker process succeeds (fresh connection),
the second fails with `RuntimeError: got Future attached to a different loop`,
the third succeeds again. Intermittent, ~50%, and it kills the task at its FIRST
query — which is why the Legal workspace never produced a contract despite every
other piece of it being correct.

This is a RATCHET. `KNOWN_VIOLATIONS` may only ever shrink. A new task module
that reaches for `AsyncSessionLocal` fails immediately; each module repaired
gets deleted from the list. When the list is empty, delete it and the
`allowed` branch with it.
"""
import ast
from pathlib import Path

import pytest

TASKS_DIR = Path(__file__).resolve().parents[1] / "app" / "workers" / "tasks"


def _imports_async_session(module: Path) -> bool:
    """True if the module actually IMPORTS the async session.

    Deliberately AST-based rather than a substring search: these modules
    document the P0-7 defect in their own docstrings, and a `"AsyncSessionLocal"
    in source` check matches that prose and reports a repaired module as broken.
    A guard that greps its own documentation is a false signal, not a guard.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(alias.name == "AsyncSessionLocal" for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(alias.name.endswith("AsyncSessionLocal") for alias in node.names):
                return True
    return False


def _code_string_constants(module: Path) -> list[str]:
    """Every string literal in the module EXCEPT docstrings.

    Docstrings are excluded so a module may describe the defect it fixed
    without the guard mistaking that description for the defect itself.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value not in docstrings
    ]

# Modules still carrying the P0-7 defect. NEVER add to this list — fix the
# module instead. See legal_tasks.py for the repaired reference implementation.
KNOWN_VIOLATIONS = {
    "export_tasks.py",
    "hr_tasks.py",
    "ocr_tasks.py",
}


def _task_modules() -> list[Path]:
    return sorted(
        p for p in TASKS_DIR.glob("*.py") if p.name != "__init__.py"
    )


def test_task_modules_exist():
    """Guard against the glob silently matching nothing and vacuously passing."""
    assert _task_modules(), f"no task modules found under {TASKS_DIR}"


@pytest.mark.parametrize("module", _task_modules(), ids=lambda p: p.name)
def test_celery_task_module_does_not_use_async_session(module: Path):
    uses_async_session = _imports_async_session(module)

    if module.name in KNOWN_VIOLATIONS:
        # Ratchet: if this fires, the module was fixed — remove it from
        # KNOWN_VIOLATIONS so the guard starts protecting it.
        assert uses_async_session, (
            f"{module.name} no longer uses AsyncSessionLocal — remove it from "
            "KNOWN_VIOLATIONS so this test protects it from regressing."
        )
        pytest.xfail(f"{module.name} still has the known P0-7 defect")

    assert not uses_async_session, (
        f"{module.name} uses AsyncSessionLocal inside a Celery task. Celery is "
        "sync and must use SyncSessionLocal (psycopg2); asyncio.run() creates a "
        "new event loop per call and pooled asyncpg connections from a previous "
        "loop fail with 'got Future attached to a different loop'. See "
        "legal_tasks.py for the repaired pattern."
    )


def test_repaired_module_uses_sync_session():
    """legal_tasks.py is the reference implementation — pin it explicitly."""
    legal = TASKS_DIR / "legal_tasks.py"
    assert not _imports_async_session(legal)
    tree = ast.parse(legal.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "SyncSessionLocal" in imported


@pytest.mark.parametrize("module", _task_modules(), ids=lambda p: p.name)
def test_no_task_module_fabricates_source_text(module: Path):
    """P0-8 was systemic — four workspaces shipped placeholder source text.

        legal    "Simulated text. 1. Confidentiality... 2. Liability capped at $50."
        finance  "Simulated invoice ... Vendor: AWS. Total: $5050.00 ..."
        research "Simulated paper text ... We demonstrate that X causes Y ..."
        study    "Simulated study material ... Mitochondria is the powerhouse ..."

    Each looked like a working feature and produced confident, well-formed output
    about a document nobody uploaded. Docstrings are excluded so a module may
    describe the defect it fixed without tripping this guard.
    """
    offenders = [
        s for s in _code_string_constants(module)
        if "simulated" in s.lower() and len(s) > 40
    ]
    assert not offenders, (
        f"{module.name} appears to fabricate source text instead of reading the "
        f"uploaded document (P0-8): {[s[:70] for s in offenders]}"
    )


def test_validation_gateway_is_not_short_circuited():
    """P0-9-adjacent: research's anti-hallucination check was `... or True`.

    That accepted every evidence quote including invented ones, and made the
    reject branch unreachable. It existed because the source text was fabricated,
    so a real quote could never match — the two defects propped each other up.

    Checked via AST, not text search: this module documents the old expression in
    its own docstring, and a substring check reports the FIXED module as broken.
    That mistake has now been made twice in this file — inspect code, never prose.
    """
    tree = ast.parse((TASKS_DIR / "research_tasks.py").read_text(encoding="utf-8"))
    short_circuits = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.BoolOp)
        and isinstance(node.op, ast.Or)
        and any(
            isinstance(v, ast.Constant) and v.value is True for v in node.values
        )
    ]
    assert not short_circuits, (
        "research_tasks.py has an `or True` short-circuit again — line(s) "
        f"{[n.lineno for n in short_circuits]}. The Validation Gateway must be "
        "able to reject a hallucinated evidence quote."
    )


def test_legal_tasks_reads_real_document_text():
    """P0-8: the hardcoded placeholder contract must never come back.

    `contract_text` was literally "Simulated text. 1. Confidentiality: ...
    2. Liability capped at $50.", so every contract in the product yielded the
    same two fabricated clauses while looking entirely plausible.
    """
    legal = TASKS_DIR / "legal_tasks.py"
    placeholders = [
        s for s in _code_string_constants(legal) if "Simulated text" in s
    ]
    assert not placeholders, (
        f"legal_tasks.py contains placeholder contract text again (P0-8): {placeholders}"
    )
    tree = ast.parse(legal.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "DocumentChunk" in imported, (
        "legal_tasks.py must read real extracted text from DocumentChunk"
    )
