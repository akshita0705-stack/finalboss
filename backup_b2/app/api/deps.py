from typing import Generator, Optional, List
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Security, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import decode_access_token, hash_api_key
from app.core.logging import logger
from app.db.session import SessionLocal, get_db
from app.models.user import User, ApiKey

token_auth_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(token_auth_scheme),
) -> User:
    """Validate JWT token and return authenticated User object."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims",
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
        )

    return user


class UserScope:
    """The authenticated user plus the installation IDs they own (via their extension API keys)."""

    def __init__(self, user: User, installation_ids: List[str]):
        self.user = user
        self.installation_ids = installation_ids


def get_user_scope(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserScope:
    """JWT-authenticated scope. Data is visible only for installations linked to this user."""
    rows = (
        db.query(ApiKey.installation_id)
        .filter(ApiKey.user_id == current_user.id, ApiKey.is_active == True)
        .distinct()
        .all()
    )
    return UserScope(current_user, [r[0] for r in rows])


def require_role(allowed_roles: List[str]):
    """Enforce role-based access control on endpoints."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {allowed_roles}",
            )
        return current_user
    return role_checker


def get_installation_scope(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Depends(api_key_header_scheme),
    x_installation_id: Optional[str] = Header(None, alias="X-Installation-ID"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(token_auth_scheme),
) -> str:
    """
    Authenticate Chrome Extension or client requests and resolve installation scope.
    Accepts:
    1. Valid extension API key in X-API-Key header.
    2. Bearer JWT token with installation_id claim.
    3. In development mode with dev key, accepts provided X-Installation-ID.
    """
    # 1. Check API Key
    if x_api_key:
        if x_api_key == settings.EXTENSION_API_KEY and settings.ENVIRONMENT != "production":
            # Development-only shared key. Disabled when ENVIRONMENT=production.
            return x_installation_id or "default-dev-installation"

        # Check hashed key in database
        hashed = hash_api_key(x_api_key)
        api_record = db.query(ApiKey).filter(ApiKey.hashed_key == hashed, ApiKey.is_active == True).first()
        if api_record:
            api_record.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return api_record.installation_id

    # 2. Check JWT Bearer token
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("installation_id"):
            return payload["installation_id"]
        if not payload:
            # The Chrome extension sends its installation API key as a Bearer value.
            api_record = (
                db.query(ApiKey)
                .filter(ApiKey.hashed_key == hash_api_key(credentials.credentials), ApiKey.is_active == True)
                .first()
            )
            if api_record:
                api_record.last_used_at = datetime.now(timezone.utc)
                db.commit()
                return api_record.installation_id

    # 3. Allow anonymous/dev fallback installation ID only if configured
    if settings.DEBUG and settings.ENVIRONMENT != "production" and x_installation_id:
        return x_installation_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized. Provide a valid X-API-Key or Bearer token.",
    )



def resolve_installation_ids_from_token(db: Session, token: Optional[str]) -> Optional[List[str]]:
    """Validate a JWT passed outside the Authorization header (WebSocket / EventSource) and
    return the installation IDs owned by that user. Returns None when the token is invalid."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        return None
    rows = (
        db.query(ApiKey.installation_id)
        .filter(ApiKey.user_id == user.id, ApiKey.is_active == True)
        .distinct()
        .all()
    )
    return [r[0] for r in rows]
