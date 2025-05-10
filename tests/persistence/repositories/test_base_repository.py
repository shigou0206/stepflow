import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from stepflow.persistence.database import async_engine, AsyncSessionLocal
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from stepflow.persistence.repositories.base_repository import BaseRepository

# 定义一个临时模型用于测试
TestBase = declarative_base()

class TestEntity(TestBase):
    __tablename__ = "test_entities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_base_repository_crud(db_session: AsyncSession):
    repo = BaseRepository(db_session, TestEntity)

    # Create
    entity = TestEntity(name="First")
    created = await repo.create(entity)
    assert created.id is not None
    assert created.name == "First"

    # Get by ID
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "First"

    # Update
    fetched.name = "Updated"
    updated = await repo.update(fetched)
    assert updated.name == "Updated"

    # List All
    all_items = await repo.list_all()
    assert len(all_items) == 1
    assert all_items[0].name == "Updated"

    # Delete
    deleted = await repo.delete(updated.id)
    assert deleted is True
    assert await repo.get_by_id(updated.id) is None