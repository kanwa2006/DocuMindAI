"""Class-wide guard for the `workspace_id`-instead-of-`owner_id` family.

This is the single most repeated defect in the register: H4 (chats), H5
(documents), H8 (exams), H11 (exports), plus a fourth site in `research.py`
that the register never listed and that was only found because an unrelated
N+1 fix required rewriting the same WHERE clause.

The shape is always identical. A model carries BOTH `workspace_id` and
`owner_id`. `workspace_id` is `uuid5(NAMESPACE_DNS, slug)` — a CATEGORY key,
byte-identical for every user — and the query filters on it while ignoring the
tenant key sitting right next to it. The result reads, and sometimes writes,
across tenants.

Per-finding tests close instances. This closes the CLASS: it walks every
endpoint module, finds every filter on `<Model>.workspace_id`, and requires an
`owner_id` filter on the same model in the same function. A new endpoint
written next month cannot reintroduce the pattern without failing here.

Models managed by the `tenant_scope` session hook (`TenantScoped` subclasses)
are exempt: for those, `owner_id` is injected into every ORM SELECT
automatically, so an explicit predicate is genuinely redundant and requiring
one would be cargo cult.
"""
import ast
import pathlib

import pytest

from app.core.tenant_scope import TenantScoped

ENDPOINTS_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints"
)

# ── Ratchet: this allowlist may only ever SHRINK ─────────────────────────────
#
# Modelled on tests/test_worker_session_discipline.py. Every entry below is a
# KNOWN cross-tenant read that cannot be closed by adding a predicate, because
# the model has NO owner column at all. Each needs an Alembic migration with a
# real backfill, which is an owner decision (see PROGRESS.md OWNER DECISIONS),
# not something to slip into a repair commit.
#
# Keyed by (module, function, model) rather than line number so the ratchet
# survives unrelated edits — a line-numbered allowlist rots on the first
# insertion above it and then has to be "fixed", which is how allowlists
# quietly grow.
#
# ADDING AN ENTRY REQUIRES THE OWNER'S SIGN-OFF. Removing one is always welcome.
KNOWN_OWNERLESS_MODELS = {
    # H3 — HR models have no ownership column at all. Live cross-tenant
    # disclosure of resume PII (name, email, phone, skills) AND cross-tenant
    # write via update_match_status / update_candidate_stage. Backfill is
    # derivable from JobRole.owner_id via job_id, but asserting ownership of
    # existing rows is the owner's call.
    ("hr.py", "list_job_candidates", "JobMatch"),
    ("hr.py", "get_job_analytics", "JobMatch"),
    ("hr.py", "export_candidates_csv", "JobMatch"),
    ("hr.py", "get_candidate_notes", "CandidateNote"),
    ("hr.py", "update_match_status", "JobMatch"),
    ("hr.py", "update_candidate_stage", "CandidateProfile"),
    ("hr.py", "score_candidate", "CandidateProfile"),
    ("hr.py", "score_candidate", "JobMatch"),
    # Found by this guard, not present in final_audit.md. Same schema gap:
    # no owner column, so every user sees every user's rows.
    ("benchmark.py", "list_benchmark_runs", "BenchmarkRun"),
    ("corrections.py", "list_corrections", "Correction"),
    ("corrections.py", "export_corrections", "Correction"),
}


def _tenant_scoped_model_names() -> set:
    """Names of models the do_orm_execute hook already scopes."""
    import app.models  # noqa: F401 - ensure every model module is imported

    names = set()
    stack = [TenantScoped]
    while stack:
        cls = stack.pop()
        for sub in cls.__subclasses__():
            names.add(sub.__name__)
            stack.append(sub)
    return names


def _model_of(node: ast.Compare | ast.Attribute):
    """`ExamPaper.workspace_id` -> 'ExamPaper'."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id
    return None


def _attrs_compared_in(fn: ast.AST):
    """Every `<Model>.<field> ==` comparison inside a function."""
    found = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute):
            model = _model_of(node.left)
            if model:
                found.append((model, node.left.attr, node.lineno))
    return found


def _endpoint_modules():
    return sorted(p for p in ENDPOINTS_DIR.glob("*.py") if p.name != "__init__.py")


@pytest.mark.parametrize("path", _endpoint_modules(), ids=lambda p: p.name)
def test_workspace_filter_is_never_the_only_tenant_filter(path):
    exempt = _tenant_scoped_model_names()
    tree = ast.parse(path.read_text(encoding="utf-8"))

    violations = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        compared = _attrs_compared_in(fn)
        ws_models = {m for m, attr, _ in compared if attr == "workspace_id"}
        owner_models = {m for m, attr, _ in compared if attr == "owner_id"}
        for model in ws_models - owner_models:
            if model in exempt:
                continue  # tenant_scope injects owner_id for these
            if (path.name, fn.name, model) in KNOWN_OWNERLESS_MODELS:
                continue  # ratchet: model has no owner column; owner decision
            line = next(
                ln for m, attr, ln in compared
                if m == model and attr == "workspace_id"
            )
            violations.append(f"{path.name}:{line} {fn.name}() filters "
                              f"{model}.workspace_id with no {model}.owner_id")

    assert not violations, (
        "Tenant filter missing — `workspace_id` is uuid5 of the workspace SLUG "
        "and is IDENTICAL for every user, so it does not identify a tenant.\n  "
        + "\n  ".join(violations)
        + "\n\nAdd `<Model>.owner_id == uuid.UUID(current_user['id'])`. If the "
        "model has no owner column at all, that is a schema gap needing a "
        "migration and a backfill — raise it with the owner and add it to "
        "KNOWN_OWNERLESS_MODELS; do not leave the read silently open."
    )


def test_ratchet_allowlist_has_no_stale_entries():
    """An entry that no longer corresponds to a real violation must be removed.

    Without this, the allowlist becomes a place where exemptions accumulate and
    outlive their reason — the failure mode that makes ratchets stop ratcheting.
    """
    exempt = _tenant_scoped_model_names()
    live = set()
    for path in _endpoint_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            compared = _attrs_compared_in(fn)
            ws_models = {m for m, attr, _ in compared if attr == "workspace_id"}
            owner_models = {m for m, attr, _ in compared if attr == "owner_id"}
            for model in ws_models - owner_models:
                if model not in exempt:
                    live.add((path.name, fn.name, model))

    stale = KNOWN_OWNERLESS_MODELS - live
    assert not stale, (
        f"KNOWN_OWNERLESS_MODELS lists {len(stale)} entries that are no longer "
        f"violations: {sorted(stale)}. The allowlist may only shrink — delete "
        "them so it keeps meaning what it says."
    )
