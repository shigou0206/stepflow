# scripts/create_tables.py

import asyncio
from stepflow.infrastructure.database import async_engine, Base
from stepflow.infrastructure.models import *

async def async_main():
    async with async_engine.begin() as conn:
        # 在异步上下文里，用 run_sync(...) 让 Base.metadata.create_all(...) 同步执行
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(async_main())