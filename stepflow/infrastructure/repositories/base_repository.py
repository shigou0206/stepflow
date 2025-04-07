import asyncio
from typing import Dict, Any, Type, TypeVar, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

T = TypeVar('T')

# 创建一个锁管理器
class LockManager:
    """管理资源锁，避免并发访问冲突"""
    
    def __init__(self):
        self.locks: Dict[str, asyncio.Lock] = {}
    
    async def acquire(self, resource_id: str) -> asyncio.Lock:
        """获取资源锁"""
        if resource_id not in self.locks:
            self.locks[resource_id] = asyncio.Lock()
        
        lock = self.locks[resource_id]
        await lock.acquire()
        return lock
    
    def release(self, resource_id: str) -> None:
        """释放资源锁"""
        if resource_id in self.locks and not self.locks[resource_id].locked():
            # 如果锁不再被使用，可以从字典中移除
            del self.locks[resource_id]

# 创建全局锁管理器实例
lock_manager = LockManager()

class BaseRepository:
    """基础仓库类，提供通用的CRUD操作"""
    
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    async def get_by_id(self, id_value: Any) -> Optional[T]:
        """根据ID获取实体"""
        result = await self.session.get(self.model_class, id_value)
        return result
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        self.session.add(entity)
        try:
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except IntegrityError:
            await self.session.rollback()
            raise
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        # 获取实体ID
        entity_id = getattr(entity, self.get_id_attribute())
        
        # 使用锁确保并发安全
        async with await lock_manager.acquire(f"{self.model_class.__name__}:{entity_id}"):
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
    
    async def delete(self, id_value: Any) -> bool:
        """删除实体"""
        # 使用锁确保并发安全
        async with await lock_manager.acquire(f"{self.model_class.__name__}:{id_value}"):
            entity = await self.get_by_id(id_value)
            if not entity:
                return False
            
            await self.session.delete(entity)
            await self.session.commit()
            return True
    
    async def list_all(self) -> list[T]:
        """列出所有实体"""
        result = await self.session.execute(select(self.model_class))
        return result.scalars().all()
    
    def get_id_attribute(self) -> str:
        """获取ID属性名称，子类可以覆盖此方法"""
        return "id" 