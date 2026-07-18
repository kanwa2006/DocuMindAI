"""Regression test for DEBUG_MASTER_PLAN M-3.

TenantContextMiddleware decoded the session JWT with ["HS256", "RS256"]
against the symmetric AUTH_SECRET_KEY — the algorithm-confusion pattern
BUG-013 removed from auth.py. The decode must pin settings.JWT_ALGORITHM.
"""
import re
import pathlib


def test_middleware_source_pins_jwt_algorithm():
    source = (
        pathlib.Path(__file__).resolve().parents[1] / "app" / "core" / "middleware.py"
    ).read_text(encoding="utf-8")
    assert not re.search(r"algorithms\s*=\s*\[[^\]]*RS256", source), (
        "RS256 must not be accepted by TenantContextMiddleware"
    )
    assert re.search(r"algorithms=\[settings\.JWT_ALGORITHM\]", source)


def test_hs256_session_still_derives_collection():
    """Functional check: a normal HS256 token still resolves the tenant."""
    import jwt

    from app.core.config import settings

    token = jwt.encode({"sub": "user-1"}, settings.AUTH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    claims = jwt.decode(
        token, settings.AUTH_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM], options={"verify_signature": True},
    )
    assert claims["sub"] == "user-1"
