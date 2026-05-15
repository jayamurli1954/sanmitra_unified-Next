"""
Phase 1: Foundation - PostgreSQL Configuration

Async SQLAlchemy setup for PostgreSQL.
Uses SQLAlchemy 2.0 async pattern with AsyncSession.

This handles:
- Connection pool management
- Transaction management
- Session lifecycle
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import logging

from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# Declarative base for ORM models
Base = declarative_base()

# Global engine instance (created on app startup)
engine = None

# Global session factory (created on app startup)
async_session_maker = None


async def init_postgres():
    """
    Initialize PostgreSQL connection.

    Called during application startup.
    Creates engine and session factory with proper pooling.
    """
    global engine, async_session_maker

    logger.info(f"Connecting to PostgreSQL: {settings.DATABASE_URL}")

    # Create async engine
    engine = create_async_engine(
        settings.POSTGRES_URI,
        echo=settings.ENVIRONMENT == "development",  # Log SQL if in debug mode
        future=True,
        pool_size=20,  # Connection pool size
        max_overflow=40,  # Max connections beyond pool_size
        pool_pre_ping=True,  # Test connections before using
        pool_recycle=3600,  # Recycle connections every hour
    )

    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire after commit
        autoflush=False,  # Explicit flush control
    )

    # Test connection
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: None)
        logger.info("✅ PostgreSQL connection successful")


async def close_postgres():
    """
    Close PostgreSQL connection.

    Called during application shutdown.
    Properly disposes engine and closes all connections.
    """
    global engine

    if engine:
        logger.info("Closing PostgreSQL connection...")
        await engine.dispose()
        logger.info("✅ PostgreSQL connection closed")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency: Get AsyncSession for database operations.

    Use in routers via: session: AsyncSession = Depends(get_async_session)

    Automatically handles:
    - Creating session
    - Rolling back on error
    - Closing session

    Yields:
        AsyncSession for database operations

    Example:
        @router.post("/donations")
        async def create_donation(
            payload: DonationCreate,
            session: AsyncSession = Depends(get_async_session),
        ):
            donation = Donation(**payload.dict())
            session.add(donation)
            await session.commit()
            return donation
    """
    if not async_session_maker:
        raise RuntimeError("PostgreSQL not initialized. Call init_postgres() first.")

    async with async_session_maker() as session:
        try:
            yield session
            # Commit if no exceptions
            await session.commit()
        except Exception:
            # Rollback on error
            await session.rollback()
            raise
        finally:
            await session.close()
