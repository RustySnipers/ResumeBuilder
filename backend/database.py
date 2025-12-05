"""
Database Configuration and Connection Management - Phase 2.1

This module provides async PostgreSQL database connection pooling using SQLAlchemy 2.0
with proper dependency injection for FastAPI.

Features:
- Async connection pooling with configurable pool size
- Environment-based configuration
- Session management with automatic cleanup
- Dependency injection for FastAPI endpoints
"""

from pathlib import Path
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator, Optional
import os
import tempfile

from backend.config import is_lite_mode

# ============================================================================
# Database Configuration
# ============================================================================

_LITE_MODE = is_lite_mode()
_lite_temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None

if _LITE_MODE:
    _lite_temp_dir = tempfile.TemporaryDirectory()
    default_sqlite_path = Path(_lite_temp_dir.name) / "lite.db"
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{default_sqlite_path}",
    )
else:
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/resumebuilder",
    )

# Create async engine with connection pooling
# pool_size: Number of connections to maintain in the pool
# max_overflow: Maximum number of connections that can be created beyond pool_size
# pool_pre_ping: Verify connections before using (prevents stale connections)
# echo: Log all SQL statements (set to False in production)
if _LITE_MODE:
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
    )

# Create async session factory
# expire_on_commit=False: Prevent automatic expiration of objects after commit
# This allows objects to be used after the session is closed
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all ORM models
Base = declarative_base()


# ============================================================================
# Dependency Injection for FastAPI
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session generator for FastAPI dependency injection.

    Usage in FastAPI endpoints:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            users = result.scalars().all()
            return users

    The session is automatically committed on success and rolled back on error,
    then properly closed in the finally block to return connection to pool.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# Database Initialization and Cleanup
# ============================================================================

async def init_db() -> None:
    """
    Initialize database by creating all tables.

    Note: In production, use Alembic migrations instead of create_all().
    This is primarily for testing and development.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database engine and dispose of connection pool.

    Call this during application shutdown to ensure clean connection closure.
    """
    await engine.dispose()
    if _lite_temp_dir:
        _lite_temp_dir.cleanup()


# ============================================================================
# Health Check
# ============================================================================

async def check_db_health() -> bool:
    """
    Check if database is accessible and healthy.

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
