import pytest
import pytest_asyncio
import subprocess
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from stepflow.infrastructure.database import Base
from stepflow.main import app

# 创建内存数据库引擎
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestingSessionLocal = sessionmaker(
    test_engine, expire_on_commit=False, class_=AsyncSession
)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """在整个测试会话中只设置一次数据库"""
    # 创建表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 可选：应用 Alembic 迁移
    # project_root = Path(__file__).parent.parent.parent
    # alembic_ini = project_root / "alembic.ini"
    # if alembic_ini.exists():
    #     subprocess.run(["alembic", "upgrade", "head"], check=True)
    
    yield
    
    # 清理表（可选）
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    """提供事务隔离的数据库会话"""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()  # 回滚而不是提交

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # 创建表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async with TestingSessionLocal() as session:
        yield session
    
    # 清理表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) 