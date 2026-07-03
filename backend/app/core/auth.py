import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Depends, WebSocketException, status, Request
import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthProvider:
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        Validates JWT token. In production with Auth0/Clerk, this fetches JWKS
        from the IDP and enforces algorithms=["RS256"]. 
        For this architectural foundation, it decodes and strictly extracts identity claims.
        """
        try:
            # BUG-003 FIX: Use settings.AUTH_SECRET_KEY directly.
            # Pydantic validates this field at startup — no fallback needed.
            # The old getattr(..., 'development_secret_do_not_use') allowed attackers
            # who know that string to forge valid JWTs for any user.
            secret = settings.AUTH_SECRET_KEY

            # BUG-013 FIX: Only accept the algorithm we actually issue.
            # Accepting RS256 alongside HS256 enables algorithm-confusion attacks.
            algorithms = [settings.JWT_ALGORITHM]

            claims = jwt.decode(token, secret, algorithms=algorithms, options={"verify_signature": True})
            
            user_id = claims.get("sub")
            if not user_id:
                raise ValueError("Token missing sub (user_id)")
                
            # Enforce multi-tenant isolation. Default to personal workspace if organization tenant is missing.
            workspace_id = claims.get("workspace_id", user_id)
            
            # Audit logging hook
            logger.info(f"[Security Audit] Authenticated user {user_id} in workspace {workspace_id}")
            
            return {
                "id": user_id,
                "email": claims.get("email", "unknown@domain.com"),
                "workspace_id": workspace_id,
                "roles": claims.get("roles", ["user"])
            }
        except Exception as e:
            logger.error(f"[Auth] JWT Validation failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI Dependency to enforce protected routes and extract the validated tenant context from cookies."""
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return AuthProvider.verify_token(token)


async def get_optional_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Like get_current_user but returns None instead of raising for unauthenticated requests."""
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return AuthProvider.verify_token(token)
    except HTTPException:
        return None
