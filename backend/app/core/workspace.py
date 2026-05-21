"""Workspace identifier resolution.

`User.workspace_id` is a String column whose value is usually a slug like
"general", "hr", "legal", etc. (set as default in models/org.py). But several
endpoints store/query `ChatSession.workspace_id` as a UUID column. The previous
code did `uuid.UUID(current_user["workspace_id"])` directly, which crashed
with ValueError on every slug.

This module resolves a slug or UUID string to a stable UUID using uuid5 against
a fixed namespace. Slugs always map to the same UUID across processes/restarts,
so no Workspace table or migration is required.
"""

import uuid
from typing import Optional
from fastapi import HTTPException

# Fixed namespace for DocuMind workspace slug → UUID derivation.
# Aligned with existing inline fallbacks in endpoints/documents.py (which used
# uuid.NAMESPACE_DNS), so historical Document rows whose workspace_id was
# generated from "general" remain reachable.
WORKSPACE_NAMESPACE = uuid.NAMESPACE_DNS

DEFAULT_WORKSPACE_SLUG = "general"

# Known slugs for the seven first-class workspaces. (Used only for validation hints.)
KNOWN_WORKSPACE_SLUGS = frozenset(
    {"general", "hr", "legal", "finance", "research", "study", "exam"}
)


def resolve_workspace_id(value: Optional[str]) -> uuid.UUID:
    """Accept a UUID string or a workspace slug; return a stable UUID.

    - Real UUID strings pass through unchanged.
    - Slugs (anything non-UUID) are hashed via uuid5 against a fixed namespace,
      yielding a deterministic UUID that is stable across restarts.
    - None / empty is treated as the default slug ("general") for compatibility
      with existing user rows whose `workspace_id` is NULL.
    - Truly malformed input raises HTTP 400.
    """
    if value is None or value == "":
        value = DEFAULT_WORKSPACE_SLUG

    candidate = str(value).strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Invalid workspace identifier")

    try:
        return uuid.UUID(candidate)
    except (ValueError, AttributeError):
        return uuid.uuid5(WORKSPACE_NAMESPACE, candidate.lower())
