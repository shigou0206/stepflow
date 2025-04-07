import asyncio
from stepflow.infrastructure.database import Base, async_engine

async def init_db():
    """初始化数据库，创建所有表"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表已创建")

if __name__ == "__main__":
    asyncio.run(init_db()) 