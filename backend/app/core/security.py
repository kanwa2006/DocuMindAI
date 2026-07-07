from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Any, Union
import jwt
from app.core.config import settings

# FIX 0.9: Replace SHA256 with bcrypt — proper salt + key stretching
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """bcrypt hash — includes salt automatically. Safe for storage."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time bcrypt comparison — safe against timing attacks."""
    return pwd_context.verify(plain_password, hashed_password)


# Legacy alias kept so existing callers in auth.py still work
get_password_hash = hash_password


def create_access_token(
    subject: Union[str, Any],
    user_id: str,
    workspace_id: str,
    roles: list
) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "exp": expire,
        "sub": str(user_id),
        "email": str(subject),
        "workspace_id": str(workspace_id),
        "roles": roles
    }
    return jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any],
    user_id: str,
    workspace_id: str,
    roles: list
) -> str:
    """
    BUG-008 FIX: Refresh tokens must live longer than access tokens.
    Previously create_access_token() was called for both, meaning refresh
    tokens expired in 60 minutes — identical to access tokens, making
    the refresh mechanism useless.

    Refresh tokens now expire in REFRESH_TOKEN_EXPIRE_DAYS (default 7 days)
    and carry token_type='refresh' so the /auth/refresh endpoint can reject
    access tokens masquerading as refresh tokens.
    """
    expire = datetime.utcnow() + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
    )
    to_encode = {
        "exp": expire,
        "sub": str(user_id),
        "email": str(subject),
        "workspace_id": str(workspace_id),
        "roles": roles,
        "token_type": "refresh",
    }
    return jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

