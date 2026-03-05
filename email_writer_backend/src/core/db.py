from __future__ import annotations

from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import Settings

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _build_async_sqlalchemy_url(settings: Settings) -> str:
    """
    Build an async SQLAlchemy URL from POSTGRES_* env vars.

    Uses asyncpg driver.
    """
    # Prefer POSTGRES_URL if it already looks like a full URL.
    if settings.postgres_url and settings.postgres_url.startswith("postgres"):
        # Ensure async driver if a sync url was provided
        if settings.postgres_url.startswith("postgresql+asyncpg://"):
            return settings.postgres_url
        if settings.postgres_url.startswith("postgresql://"):
            return settings.postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if settings.postgres_url.startswith("postgres://"):
            return settings.postgres_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return settings.postgres_url

    user = quote_plus(settings.postgres_user or "appuser")
    password = quote_plus(settings.postgres_password or "")
    host = settings.postgres_host or "localhost"
    port = settings.postgres_port or "5000"
    db = settings.postgres_db or "myapp"
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def init_engine(settings: Settings) -> None:
    """Initialize a global async SQLAlchemy engine and session factory."""
    global _engine, _session_factory
    if _engine is not None and _session_factory is not None:
        return

    url = _build_async_sqlalchemy_url(settings)
    _engine = create_async_engine(
        url,
        pool_pre_ping=True,
        future=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() at startup.")
    async with _session_factory() as session:
        yield session


async def ping_db(session: AsyncSession) -> bool:
    """Run a simple query to validate DB connectivity."""
    result = await session.execute(text("SELECT 1"))
    return result.scalar_one() == 1
