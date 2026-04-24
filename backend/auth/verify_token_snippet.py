# ── ADD THIS FUNCTION to backend/auth/routes.py ──────────────────────────────
# Place it just after the existing get_current_user function

def verify_token_string(token: str, db) -> Optional[User]:
    """
    Verify a raw JWT token string and return the User object.
    Used by document viewer endpoint where token comes as query param.
    Returns None if token is invalid or expired.
    """
    try:
        from backend.config import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except Exception:
        return None

# ── Also make sure these imports exist at top of auth/routes.py ──────────────
# from typing import Optional
# import jwt  (or: from jose import jwt)
