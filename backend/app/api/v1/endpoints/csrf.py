import os
import binascii
from fastapi import APIRouter, Response

router = APIRouter()

# FIX 0.4: Environment-aware secure flag
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

# FIX 0.5: CSRF exempt paths are in middleware.py — this endpoint is already exempt
@router.get("/csrf-token")
async def get_csrf_token(response: Response):
    """
    Dispenses a synchronizer token for CSRF protection.
    The frontend must fetch this and include it in X-CSRF-Token header for mutations.
    """
    csrf_token = binascii.hexlify(os.urandom(32)).decode()

    # FIX 0.4: secure=IS_PRODUCTION so cookie is stored on HTTP localhost
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,       # Must be readable by JS to populate the header
        secure=IS_PRODUCTION,
        samesite="strict",
        path="/"
    )
    return {"csrf_token": csrf_token}
