"""Database connection management."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import get_settings
from src.models.database import Base

settings = get_settings()
engine = create_async_engine(
    settings.mysql_dsn,
    echo=False,
    pool_size=settings.mysql_pool_size,
    max_overflow=10,
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncSession:
    """Get database session."""
    async with async_session_maker() as session:
        return session
