import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# ─────────────────────────────── 环境切换 ────────────────────────────────

ENV = os.getenv("STEPFLOW_ENV", "dev")

if ENV == "test":
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
else:
    DATABASE_URL = "sqlite+aiosqlite:///stepflow.db"

# 👇 同步连接字符串用于 Alembic 或同步工具
SQLALCHEMY_DATABASE_URL = "sqlite:///stepflow.db"

# ─────────────────────────────── 引擎和会话 ────────────────────────────────

async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
)

Base = declarative_base()

# ─────────────────────────────── 会话工厂 ────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()