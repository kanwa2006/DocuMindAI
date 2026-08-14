"""M-6: auth-layer coverage (the original suite had none).

Pins the security contracts REPAIR_RULEBOOK §18 depends on: bcrypt
password hashing, HS256-only token issuance, refresh-token typing and
longer expiry, and expiry enforcement.
"""
from datetime import datetime, timedelta

import jwt as pyjwt
import pytest

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)

TOKEN_ARGS = dict(
    subject="user@example.com",
    user_id="user-123",
    workspace_id="general",
    roles=["user"],
)


def _decode(token):
    return pyjwt.decode(
        token, settings.AUTH_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


def test_password_hash_roundtrip_is_bcrypt():
    hashed = hash_password("s3cret-pw")
    assert hashed.startswith("$2")  # bcrypt marker — never SHA/plaintext
    assert verify_password("s3cret-pw", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip_hs256():
    claims = _decode(create_access_token(**TOKEN_ARGS))
    assert claims["sub"] == "user-123"
    assert claims["email"] == "user@example.com"
    assert claims["workspace_id"] == "general"
    assert "token_type" not in claims


def test_tokens_are_signed_hs256():
    header = pyjwt.get_unverified_header(create_access_token(**TOKEN_ARGS))
    assert header["alg"] == settings.JWT_ALGORITHM == "HS256"


def test_refresh_token_is_typed_and_lives_longer():
    access = _decode(create_access_token(**TOKEN_ARGS))
    refresh = _decode(create_refresh_token(**TOKEN_ARGS))
    assert refresh["token_type"] == "refresh"
    assert refresh["exp"] > access["exp"]


def test_expired_token_is_rejected():
    expired = pyjwt.encode(
        {"sub": "user-123", "exp": datetime.utcnow() - timedelta(seconds=10)},
        settings.AUTH_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        _decode(expired)


# ── BUG-008 regression: verify_token must pass token_type through ──────────────
# The /refresh endpoint calls AuthProvider.verify_token(refresh_token) and then
# checks `user.get("token_type") != "refresh"`. If verify_token strips the claim,
# that check ALWAYS raises 401 — silent session refresh is completely broken.
# These tests reproduce the exact failure condition.

from app.core.auth import AuthProvider  # noqa: E402


def test_verify_token_omits_token_type_for_access_tokens():
    """Access tokens have no token_type claim; verify_token must not invent one."""
    token = create_access_token(**TOKEN_ARGS)
    result = AuthProvider.verify_token(token)
    assert "token_type" not in result, (
        "verify_token must not add token_type for access tokens — "
        "the /refresh endpoint uses its absence to block access-token reuse"
    )


def test_verify_token_passes_token_type_for_refresh_tokens():
    """Refresh tokens carry token_type='refresh'; verify_token must return it.

    If this assertion fails the /refresh endpoint will always raise 401 because
    user.get('token_type') will be None instead of 'refresh'.
    """
    token = create_refresh_token(**TOKEN_ARGS)
    result = AuthProvider.verify_token(token)
    assert result.get("token_type") == "refresh", (
        "verify_token must pass token_type='refresh' through for refresh tokens — "
        "without it the /refresh endpoint always raises 401 (BUG-008 regression)"
    )


def test_refresh_endpoint_accepts_refresh_token_type():
    """Full /refresh contract: a properly typed refresh token must not be rejected
    by the token_type guard at endpoints/auth.py::refresh_session."""
    token = create_refresh_token(**TOKEN_ARGS)
    user = AuthProvider.verify_token(token)
    # Reproduce the guard logic exactly as it appears in the endpoint
    assert user.get("token_type") == "refresh", (
        "Refresh session would incorrectly 401 — token_type not passed through"
    )

