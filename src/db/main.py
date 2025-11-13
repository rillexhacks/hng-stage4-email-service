from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings
from ..models import Base
from ..template_service.template_models import TemplateBase

# Engine for the first database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.environment == "development"),
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Engine for the second database
template_engine = create_async_engine(
    settings.TEMPLATE_DATABASE_URL,
    echo=(settings.environment == "development"),
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocalDB2 = sessionmaker(
    bind=template_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Dependency for DB1
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency for DB2
async def get_template_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocalDB2() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Initialize both databases
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with template_engine.begin() as conn:
        await conn.run_sync(TemplateBase.metadata.create_all)
    print("Both databases tables created successfully")
