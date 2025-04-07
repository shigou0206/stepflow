#!/usr/bin/env python
# scripts/reset_db.py

import asyncio
import os
from pathlib import Path

from stepflow.infrastructure.database import async_engine, Base
from stepflow.infrastructure.seed_data import seed_data

async def reset_db():
    """重置数据库：删除现有数据库，创建新表并填充种子数据"""
    print("重置数据库...")
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    
    # 检查数据库文件是否存在
    db_file = project_root / "stepflow.db"
    if db_file.exists():
        print(f"删除现有数据库文件: {db_file}")
        os.remove(db_file)
    
    print("使用 SQLAlchemy 创建表...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("表创建完成！")
    
    # 填充种子数据
    print("填充种子数据...")
    await seed_data()
    print("数据库重置完成！")

if __name__ == "__main__":
    asyncio.run(reset_db()) 