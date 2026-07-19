"""Regression tests for DEBUG_MASTER_PLAN M-2.

The retrieval cache was written as `retrieval:{workspace}:{hash}` while
delete_document purged `retrieval:uid_{uid}:*` — the patterns never
matched, so deleted-document content could be served from cache for up to
the TTL. The write key is now built by a single helper whose prefix
matches the purge pattern and scopes entries per tenant.
"""
import fnmatch
import uuid

from app.api.v1.endpoints.query import _retrieval_cache_key


def test_cache_key_matches_delete_purge_pattern():
    user_id = str(uuid.uuid4())
    key = _retrieval_cache_key(user_id, "legal", "what is clause 4?", [uuid.uuid4()])
    purge_pattern = f"retrieval:uid_{user_id}:*"  # documents.py delete pattern
    assert fnmatch.fnmatch(key, purge_pattern)


def test_cache_key_is_tenant_scoped():
    q = "same question"
    docs = [uuid.UUID("00000000-0000-0000-0000-000000000001")]
    key_a = _retrieval_cache_key("user-a", "general", q, docs)
    key_b = _retrieval_cache_key("user-b", "general", q, docs)
    assert key_a != key_b


def test_cache_key_varies_by_attached_docs_and_query():
    base = _retrieval_cache_key("u", "general", "q1", [])
    assert base != _retrieval_cache_key("u", "general", "q2", [])
    assert base != _retrieval_cache_key("u", "general", "q1", [uuid.uuid4()])
    # …and is stable for identical inputs / doc-id order.
    d1, d2 = uuid.uuid4(), uuid.uuid4()
    assert _retrieval_cache_key("u", "general", "q1", [d1, d2]) == \
        _retrieval_cache_key("u", "general", "q1", [d2, d1])
