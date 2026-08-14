"""
P0-9 — automatic tenant scoping for owner-scoped tables.

## Why this exists

`workspace_id` on the legal/finance/study/research tables is derived from a
workspace SLUG (`uuid5(NAMESPACE_DNS, "legal"|"finance"|...)`), so it is
IDENTICAL for every user. It partitions rows by category, not by tenant.
Roughly ninety queries filtered on it alone and therefore returned every
user's rows.

The obvious repair — add `owner_id ==` to all ninety `WHERE` clauses — is the
wrong shape. It duplicates one decision across ninety sites, and the ninety
-first query written next month silently reintroduces the vulnerability. The
layer that actually owns "which rows may this user see" is the **session**,
not the call site.

So: models inherit `TenantScoped`, and a `do_orm_execute` hook injects
`owner_id = <current owner>` into every ORM SELECT that touches them. Adding a
new owner-scoped table means inheriting the mixin. Writing a new endpoint
requires no discipline at all — it cannot forget a filter it never writes.

## Fail-closed

If no scope is active, a SELECT against a scoped model raises
`TenantScopeMissing` rather than returning unfiltered rows. An unscoped query
is a bug; the safe response is to fail loudly, not to serve every tenant's
data. Trusted internal work (migrations, admin, beat jobs) must say so
explicitly via `system_scope()` — a bypass you have to type, never a default.

## Limits — read before relying on this

- Covers **ORM** SELECTs. A raw `text()` query bypasses it entirely, exactly
  as it bypasses any ORM-level control.
- Covers reads. INSERTs still set `owner_id` explicitly; `owner_id` is
  `NOT NULL`, so a missed write fails loudly at the database instead of
  writing an unowned row.
- **ORM UPDATE and DELETE bypass this hook.** `_apply_tenant_scope` returns
  immediately for non-SELECT statements (`if not orm_execute_state.is_select:
  return`). SQLAlchemy's `with_loader_criteria` only applies to SELECT-path
  loaders. Safe practice for UPDATE/DELETE against a scoped model:
  add `where(Model.owner_id == current_owner_id())` explicitly, or
  fetch under a tenant_scope'd SELECT and mutate the returned objects
  so the ORM emits filtered UPDATEs. Any UPDATE/DELETE without an explicit
  owner predicate on a scoped table is a cross-tenant write vulnerability.
  (S26 — recorded 2026-08-14; shape change is an owner decision.)
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from sqlalchemy import Column, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, declared_attr, with_loader_criteria

# `None` = no scope established (fail closed).
# `_SYSTEM` = deliberate, explicit bypass for trusted internal work.
_SYSTEM = "system"
_current_owner: ContextVar[Optional[object]] = ContextVar(
    "documind_current_owner", default=None
)


class TenantScopeMissing(RuntimeError):
    """A scoped model was queried with no owner scope established.

    This is a programming error, not a user error: some code path reached a
    tenant-scoped table without going through `tenant_scope()` (request path)
    or `system_scope()` (trusted internal path).
    """


class TenantScoped:
    """Mixin marking a model as owned by exactly one user.

    Declares the tenant key itself so the column definition lives in one place
    rather than being copy-pasted into every model — the same duplication
    argument that motivates the query hook below.
    """

    @declared_attr
    def owner_id(cls):  # noqa: N805 - SQLAlchemy mixin convention
        return Column(UUID(as_uuid=True), index=True, nullable=False)


def current_owner_id() -> Optional[uuid.UUID]:
    """The owner scope in effect, or None under `system_scope()`/no scope."""
    value = _current_owner.get()
    return None if value is _SYSTEM or value is None else value  # type: ignore[return-value]


@contextmanager
def tenant_scope(owner_id: uuid.UUID | str) -> Iterator[None]:
    """Scope every ORM read in this context to a single owner.

    Set from the auth dependency on the request path, and from the task
    arguments on the Celery path — workers have no request to inherit from,
    so they must establish scope explicitly.
    """
    if isinstance(owner_id, str):
        owner_id = uuid.UUID(owner_id)
    token = _current_owner.set(owner_id)
    try:
        yield
    finally:
        _current_owner.reset(token)


@contextmanager
def system_scope() -> Iterator[None]:
    """Deliberate, auditable bypass for trusted non-tenant work.

    Legitimate uses: migrations, beat/cleanup jobs, admin tooling that is
    already authorized to see across tenants. Never use this to make a failing
    request-path query "work" — that reintroduces P0-9.
    """
    token = _current_owner.set(_SYSTEM)
    try:
        yield
    finally:
        _current_owner.reset(token)


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_scope(orm_execute_state) -> None:
    """Inject `owner_id = <current owner>` into every SELECT on a scoped model.

    `with_loader_criteria(..., include_aliases=True)` also covers eager loads
    and joined relationships, so a scoped row cannot be reached indirectly via
    a relationship from an unscoped one.
    """
    if not orm_execute_state.is_select:
        return
    # Column-level operations (bulk update/delete) and non-ORM statements are
    # out of scope for a loader-criteria hook.
    if orm_execute_state.is_column_load or orm_execute_state.is_relationship_load:
        return

    if not _statement_touches_scoped_model(orm_execute_state):
        return

    raw = _current_owner.get()
    if raw is _SYSTEM:
        return
    if raw is None:
        raise TenantScopeMissing(
            "Query against a tenant-scoped table with no owner scope. Wrap the "
            "request path in tenant_scope(user_id), or system_scope() if this "
            "is trusted internal work."
        )

    orm_execute_state.statement = orm_execute_state.statement.options(
        with_loader_criteria(
            TenantScoped,
            lambda cls: cls.owner_id == raw,
            include_aliases=True,
        )
    )


def _statement_touches_scoped_model(orm_execute_state) -> bool:
    """True when the statement reads at least one TenantScoped entity.

    Checked before raising so that the fail-closed behaviour applies only to
    scoped tables — unscoped models (users, documents, chats) keep their own
    existing controls and are unaffected by this hook.
    """
    for mapper in orm_execute_state.all_mappers:
        if issubclass(mapper.class_, TenantScoped):
            return True
    return False
