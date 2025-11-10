
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import settings  


Base = declarative_base()


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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session



async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
