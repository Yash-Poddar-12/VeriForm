"""
veriform.persistence.database
=============================
SQLAlchemy 2.0 async database setup and session management.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from veriform.config import settings

# For MVP, default to a local SQLite file in the run directory if no DB URL is provided.
# A production setup would provide a Postgres asyncpg URL.
DATABASE_URL = os.getenv("VERIFORM_DATABASE_URL", "sqlite+aiosqlite:///veriform.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
