"""SQLAlchemy async engine, session factory, and Base class."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_AsyncSessionLocal = None


def _prepare_url(raw: str) -> str:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    if raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(raw)
    params = parse_qs(parsed.query, keep_blank_values=True)

    if "sslmode" in params:
        ssl_val = params.pop("sslmode")[0]
        if "ssl" not in params:
            params["ssl"] = [ssl_val]

    params.pop("channel_binding", None)

    hostname = parsed.hostname or ""
    if ("localhost" in hostname or "127.0.0.1" in hostname) and "ssl" not in params:
        params["ssl"] = ["disable"]

    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _get_engine():
    global _engine, _AsyncSessionLocal
    if _engine is None:
        url = _prepare_url(settings.DATABASE_URL)
        _engine = create_async_engine(url, echo=False, poolclass=NullPool)
        _AsyncSessionLocal = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


def __getattr__(name: str):
    if name == "engine":
        return _get_engine()
    if name == "AsyncSessionLocal":
        _get_engine()
        return _AsyncSessionLocal
    raise AttributeError(f"module 'database.connection' has no attribute {name!r}")


async def get_db():
    _get_engine()
    async with _AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables declared on Base.metadata if they don't already exist."""
    from database import models  # noqa: F401

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
