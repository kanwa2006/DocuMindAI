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
