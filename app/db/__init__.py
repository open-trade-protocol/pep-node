"""Database module for the peer node.

Provides both sync and async engines:
- sync_engine: for SQLModel.metadata.create_all() and migrations
- async_session_factory: for async query execution
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as sa_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


def _get_db_url() -> str:
    """Get the database URL from environment or defaults."""
    # Check env vars first (allows test overrides)
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("OT_DATABASE_URL")
    if db_url:
        return db_url
    # Fallback to pydantic settings
    try:
        from app.core.config import settings
        return settings.database_url
    except Exception:
        return "sqlite+aiosqlite:///./pepnode.db"


# Lazy engine creation
_sync_engine: Optional[object] = None
_async_engine: Optional[object] = None
_async_session_factory: Optional[object] = None


def _ensure_engines():
    """Lazily create engines on first access."""
    global _sync_engine, _async_engine, _async_session_factory

    if _sync_engine is not None:
        return

    db_url = _get_db_url()
    is_sqlite = "sqlite" in db_url

    # Sync engine for metadata operations
    if is_sqlite:
        sync_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
    else:
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    _sync_engine = create_engine(sync_url, echo=False, pool_pre_ping=True)

    # Async engine — ensure +asyncpg driver for PostgreSQL URLs
    if is_sqlite:
        async_url = db_url
    else:
        if "+asyncpg" not in db_url:
            async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            async_url = db_url
    _async_engine = create_async_engine(
        async_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

    _async_session_factory = sa_sessionmaker(
        _async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


def get_engine():
    """Get the async SQLAlchemy engine."""
    _ensure_engines()
    return _async_engine


def get_sync_engine():
    """Get the sync SQLAlchemy engine (for metadata ops)."""
    _ensure_engines()
    return _sync_engine


def get_session_factory():
    """Get the async session factory."""
    _ensure_engines()
    return _async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    _ensure_engines()
    async with _async_session_factory() as session:
        yield session


@asynccontextmanager
async def get_session_context():
    """Context manager for database sessions."""
    _ensure_engines()
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables.

    Creates all tables defined in SQLModel metadata.
    Safe to call multiple times — does nothing if tables exist.
    """
    _ensure_engines()
    SQLModel.metadata.create_all(_sync_engine)


async def drop_all_tables():
    """Drop all tables. ONLY for development/testing."""
    _ensure_engines()
    SQLModel.metadata.drop_all(_sync_engine)


def close():
    """Close the engines and dispose of connections."""
    if _sync_engine:
        _sync_engine.dispose()
    if _async_engine:
        _async_engine.dispose()
