import asyncio
from typing import Dict
from contextlib import asynccontextmanager

class LockManager:
    """异步锁管理器，支持 async with 自动释放"""
    def __init__(self):
        self.locks: Dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def lock(self, resource_id: str):
        """异步上下文方式加锁"""
        if resource_id not in self.locks:
            self.locks[resource_id] = asyncio.Lock()

        lock = self.locks[resource_id]
        await lock.acquire()
        try:
            yield
        finally:
            lock.release()


# 创建全局实例
lock_manager = LockManager()