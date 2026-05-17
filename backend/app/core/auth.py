import logging
from typing import Dict, Any, List
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
            # Enforce cryptographic signature check for production
            secret = getattr(settings, 'AUTH_SECRET_KEY', 'development_secret_do_not_use')
            algorithms = ["HS256", "RS256"]
            
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
