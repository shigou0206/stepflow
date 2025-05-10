# stepflow/persistence/base_repository.py

import asyncio
from typing import Any, Type, TypeVar, Optional, List, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from stepflow.utils.lock_manager import lock_manager

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """通用异步 CRUD 仓储类，支持锁和事务安全"""

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    async def get_by_id(self, id_value: Any) -> Optional[T]:
        return await self.session.get(self.model_class, id_value)

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        try:
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except IntegrityError:
            await self.session.rollback()
            raise

    async def update(self, entity: T) -> T:
        entity_id = getattr(entity, self.get_id_attribute())
        key = f"{self.model_class.__name__}:{entity_id}"

        async with lock_manager.lock(key):
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)
            return entity

    async def delete(self, id_value: Any) -> bool:
        key = f"{self.model_class.__name__}:{id_value}"
        async with lock_manager.lock(key):
            entity = await self.get_by_id(id_value)
            if not entity:
                return False
            await self.session.delete(entity)
            await self.session.commit()
            return True

    async def list_all(self) -> List[T]:
        result = await self.session.execute(select(self.model_class))
        return result.scalars().all()

    def get_id_attribute(self) -> str:
        return "id"