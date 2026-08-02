"""Regression guard for final_audit H4.

Nine chat routes resolved a `ChatSession` by `id + workspace_id` while
`ChatSession.owner_id` existed and was populated. `workspace_id` is
`uuid5(NAMESPACE_DNS, slug)` — a CATEGORY key, identical for every user — so
those routes were effectively scoped by "is this a chat" and not by "is this
YOUR chat":

  • GET    /chats                  listed every user's sessions
  • with an id from that list: read the transcript, append messages, rename,
    re-tag, pin
  • POST   /chats/{id}/share       minted a PUBLIC link to another user's
    conversation, then readable unauthenticated at GET /shared/{token}

Only `delete_chat_session` used `owner_id`, and its comment called that a
"belt-and-suspenders ownership check" — treating the tenant key as redundant
is precisely the inversion that caused this.

Guard shape: a source-level assertion over the whole module rather than a
per-route call, because the nine routes have nine different signatures and the
property under test ("no route scopes a session by workspace") is a property
of the FILE. A behavioural check on two representative routes backs it up.
"""
import inspect
import re
import uuid

import pytest

from app.api.v1.endpoints import chats as chats_module

SOURCE = inspect.getsource(chats_module)


def test_no_route_scopes_a_chat_session_by_workspace():
    """`ChatSession.workspace_id` must never appear in a filter predicate."""
    offenders = re.findall(r"ChatSession\.workspace_id\s*==", SOURCE)
    assert not offenders, (
        f"{len(offenders)} route(s) filter a ChatSession by workspace_id. That "
        "column is uuid5 of the workspace SLUG and is identical for every "
        "user, so it does not identify a tenant — it lists, reads, mutates and "
        "SHARES other users' chats (H4). The tenant key is owner_id."
    )


def test_session_lookups_are_scoped_by_owner():
    """Every session lookup must carry an owner predicate."""
    owner_predicates = re.findall(r"ChatSession\.owner_id\s*==", SOURCE)
    assert len(owner_predicates) >= 9, (
        f"only {len(owner_predicates)} ChatSession.owner_id predicates found; "
        "expected at least 9 (one per session-resolving route). A route that "
        "resolves a session without one is reachable cross-tenant."
    )


def test_workspace_id_is_still_written_on_create():
    """The category column is still SET — this fix narrows reads, not writes.

    Dropping the write would break per-workspace chat listing, which is a
    legitimate use of the category key.
    """
    create_src = inspect.getsource(chats_module.create_chat_session)
    assert "workspace_id=resolve_workspace_id" in create_src, (
        "create_chat_session no longer records the workspace category; "
        "per-workspace chat listing depends on it."
    )


# ── Behavioural backup for two representative routes ─────────────────────────

USER = {"id": str(uuid.uuid4()), "workspace_id": "general"}
SESSION_ID = str(uuid.uuid4())


class _StopEndpoint(Exception):
    pass


class _CapturingDB:
    """Captures the WHERE clause of the first statement, then aborts.

    Only the WHERE clause: `select(ChatSession)` emits every column — including
    `chat_sessions.workspace_id` — in the SELECT list, which is
    indistinguishable from a predicate if you match the whole statement.
    """

    def __init__(self):
        self.where = []

    async def execute(self, stmt):
        self.where.append(str(stmt.whereclause))
        raise _StopEndpoint()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [chats_module.toggle_pin_session, chats_module.get_chat_messages],
    ids=lambda e: e.__name__,
)
async def test_representative_routes_filter_by_owner_not_workspace(endpoint):
    db = _CapturingDB()
    try:
        await endpoint(SESSION_ID, current_user=USER, db=db)
    except _StopEndpoint:
        pass

    assert db.where, f"{endpoint.__name__} issued no lookup query"
    where = db.where[0]
    assert "owner_id" in where, (
        f"{endpoint.__name__} resolves a session with no owner predicate — "
        f"reachable cross-tenant. WHERE was:\n{where}"
    )
    assert "workspace_id" not in where, (
        f"{endpoint.__name__} filters by workspace_id, which is identical for "
        f"every user (H4). WHERE was:\n{where}"
    )
