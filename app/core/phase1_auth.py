"""
Phase 1: Foundation - Authentication & JWT Validation

Handles JWT token validation, user identification, and tenant resolution.
This is the security boundary of the entire system.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# HTTP Bearer scheme (extracts Bearer token from Authorization header)
bearer_scheme = HTTPBearer()


def create_access_token(
    subject: str,
    tenant_id: str,
    app_key: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT token.

    Args:
        subject: User ID or email
        tenant_id: Tenant ID (multi-tenant)
        app_key: App key (mandirmitra, gruhamitra, etc.)
        expires_delta: Custom expiration delta

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode = {
        "sub": subject,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def verify_token(token: str) -> Dict:
    """
    Verify a JWT token and return its payload.

    Args:
        token: JWT token string

    Returns:
        Token payload dict with sub, tenant_id, app_key

    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Extract required fields
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        app_key: str = payload.get("app_key")

        if user_id is None or tenant_id is None:
            logger.warning(f"Invalid token payload: missing required fields")
            raise credentials_exception

        return {
            "user_id": user_id,
            "sub": user_id,  # Backward compatibility
            "tenant_id": tenant_id,
            "app_key": app_key,
        }

    except JWTError as e:
        logger.warning(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected token verification error: {str(e)}")
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict:
    """
    Dependency: Extract and validate current user from Authorization header.

    This is the main authentication checkpoint for all protected endpoints.

    Usage in routers:
        @router.post("/donations")
        async def create_donation(
            payload: DonationCreate,
            current_user: Dict = Depends(get_current_user),
        ):
            tenant_id = current_user["tenant_id"]
            user_id = current_user["user_id"]
            # ... rest of endpoint

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User info dict: {user_id, tenant_id, app_key}

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    return await verify_token(token)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict]:
    """
    Optional authentication: Extract user if token is provided, otherwise return None.

    Use this for endpoints that work with or without authentication.

    Args:
        credentials: Optional HTTP Bearer token

    Returns:
        User info dict if authenticated, None otherwise
    """
    if not credentials:
        return None

    token = credentials.credentials
    try:
        return await verify_token(token)
    except HTTPException:
        return None
