from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(
    get_settings().database_url, pool_size=8, max_overflow=7, pool_pre_ping=True
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


# Audit writes use their own small pool. The request's own session is still checked out while the
# audit row is written, so sharing one pool can deadlock under load (every connection held by a
# request that is waiting for a second one).
audit_engine = create_async_engine(
    get_settings().database_url, pool_size=3, max_overflow=2, pool_pre_ping=True
)
AuditSessionLocal = async_sessionmaker(audit_engine, expire_on_commit=False)
