"""
JWT authentication and authorization for SessionScribe services.
"""

import jwt
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .credentials import credential_manager

logger = logging.getLogger(__name__)

security = HTTPBearer()

class JWTManager:
    """Manages JWT token verification for SessionScribe services."""
    
    def __init__(self):
        self.algorithm = 'HS256'
        self.issuer = 'SessionScribe'
        self.audience = 'SessionScribe-Services'
    
    def get_signing_key(self) -> str:
        """Get JWT signing key from credential manager."""
        signing_key = credential_manager.get_credential('jwt_signing_key')
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT signing key not configured"
            )
        return signing_key
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            signing_key = self.get_signing_key()
            
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience
            )
            
            # Check token expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
                logger.warning("JWT token expired")
                return None
            
            return payload
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return None
    
    def extract_session_id(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract session ID from JWT payload."""
        return payload.get('sessionId')
    
    def check_permission(self, payload: Dict[str, Any], required_permission: str) -> bool:
        """Check if token has required permission."""
        permissions = payload.get('permissions', [])
        return required_permission in permissions


# Global JWT manager instance
jwt_manager = JWTManager()


async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency to verify JWT token."""
    token = credentials.credentials
    payload = jwt_manager.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


def require_permission(permission: str):
    """FastAPI dependency factory to require specific permission."""
    async def permission_checker(payload: Dict[str, Any] = Depends(verify_jwt_token)) -> Dict[str, Any]:
        if not jwt_manager.check_permission(payload, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return payload
    
    return permission_checker


def require_session_access(session_id: str):
    """FastAPI dependency factory to require access to specific session."""
    async def session_checker(payload: Dict[str, Any] = Depends(verify_jwt_token)) -> Dict[str, Any]:
        token_session_id = jwt_manager.extract_session_id(payload)
        
        if token_session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token not valid for this session"
            )
        
        return payload
    
    return session_checker


class AuthMiddleware:
    """Middleware for authentication on WebSocket connections."""
    
    @staticmethod
    def verify_websocket_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify WebSocket connection token."""
        return jwt_manager.verify_token(token)
    
    @staticmethod
    def extract_token_from_query(query_params: Dict[str, str]) -> Optional[str]:
        """Extract token from WebSocket query parameters."""
        return query_params.get('token')
    
    @staticmethod
    def extract_token_from_header(headers: Dict[str, str]) -> Optional[str]:
        """Extract token from WebSocket headers."""
        auth_header = headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        return None