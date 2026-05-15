"""
Phase 1: Foundation - Dependency Injection Functions

Provides Depends() functions for use in routers:
- Database sessions (PostgreSQL, MongoDB)
- Current user and tenant resolution
- Tenant isolation enforcement

These are the core dependencies that enable multi-tenancy and data isolation.
"""

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
import logging

from app.db.postgres import get_async_session
from app.core.phase1_auth import get_current_user

logger = logging.getLogger(__name__)


async def resolve_tenant_id(
    current_user: Dict = Depends(get_current_user),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> str:
    """
    Resolve the tenant ID for the current request.

    Priority:
    1. X-Tenant-ID header (override, for admin operations)
    2. current_user["tenant_id"] (from JWT token)
    3. Raise error if neither

    This ensures multi-tenant isolation: requests only affect the resolved tenant.

    Args:
        current_user: Authenticated user (from get_current_user dependency)
        x_tenant_id: Optional X-Tenant-ID header

    Returns:
        Tenant ID string

    Raises:
        HTTPException: If tenant cannot be resolved
    """
    tenant_id = x_tenant_id or current_user.get("tenant_id")

    if not tenant_id:
        logger.error("Could not resolve tenant ID from token or headers")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not resolve tenant ID",
        )

    return tenant_id


async def get_current_tenant_id(
    current_user: Dict = Depends(get_current_user),
) -> str:
    """
    Get tenant ID from current user token (simpler version without header override).

    Use this when you don't need X-Tenant-ID header override.

    Args:
        current_user: Authenticated user

    Returns:
        Tenant ID from token
    """
    return current_user.get("tenant_id")


async def get_current_user_id(
    current_user: Dict = Depends(get_current_user),
) -> str:
    """
    Get user ID from current user token.

    Args:
        current_user: Authenticated user

    Returns:
        User ID
    """
    return current_user.get("user_id")


async def get_session(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncSession:
    """
    Get PostgreSQL async session.

    Usage in routers:
        @router.post("/donations")
        async def create_donation(
            payload: DonationCreate,
            session: AsyncSession = Depends(get_session),
        ):
            # Use session for database operations
            session.add(donation)
            await session.commit()

    Args:
        session: Injected AsyncSession from dependency

    Returns:
        AsyncSession for database operations
    """
    return session


async def get_current_app_key(
    current_user: Dict = Depends(get_current_user),
) -> str:
    """
    Get app key from current user token.

    App key distinguishes between products:
    - mandirmitra: Temple management
    - gruhamitra: Housing management
    - legalmitra: Legal document management
    - investmitra: Investment tracking

    Args:
        current_user: Authenticated user

    Returns:
        App key (mandirmitra, gruhamitra, etc.)
    """
    return current_user.get("app_key", "mandirmitra")


# Combined dependency for common pattern: both session and tenant
async def get_session_and_tenant(
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: Dict = Depends(get_current_user),
) -> tuple[AsyncSession, str]:
    """
    Get both database session and tenant ID in one dependency.

    Useful for endpoints that need both database access and tenant isolation.

    Usage:
        @router.get("/donations")
        async def list_donations(
            session_tenant: tuple = Depends(get_session_and_tenant),
        ):
            session, tenant_id = session_tenant
            # Use session and tenant_id

    Args:
        session: PostgreSQL async session
        tenant_id: Resolved tenant ID
        current_user: Authenticated user

    Returns:
        Tuple of (session, tenant_id)
    """
    return (session, tenant_id)


# Example custom dependency for audit logging
async def get_request_context(
    current_user: Dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    app_key: str = Depends(get_current_app_key),
) -> Dict:
    """
    Get full request context for audit logging and business logic.

    Returns all context needed for operations: user, tenant, app.

    Usage:
        @router.post("/donations")
        async def create_donation(
            payload: DonationCreate,
            context: Dict = Depends(get_request_context),
            session: AsyncSession = Depends(get_session),
        ):
            user_id = context["user_id"]
            tenant_id = context["tenant_id"]
            # Audit log creation
            await log_audit_event(session, tenant_id, "donation.created", ...)

    Args:
        current_user: Authenticated user
        tenant_id: Resolved tenant ID
        app_key: App key (mandirmitra, gruhamitra, etc.)

    Returns:
        Dict with user_id, tenant_id, app_key
    """
    return {
        "user_id": current_user.get("user_id"),
        "tenant_id": tenant_id,
        "app_key": app_key,
    }
