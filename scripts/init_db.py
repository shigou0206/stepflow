#!/usr/bin/env python
# scripts/init_db.py

import asyncio
import os
import subprocess
import re
from pathlib import Path

from stepflow.infrastructure.database import async_engine, Base
from stepflow.infrastructure.seed_data import seed_data

def get_alembic_heads():
    """获取当前的 Alembic 头版本"""
    try:
        result = subprocess.run(["alembic", "heads"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"获取头版本失败: {result.stderr}")
            return []
        
        # 解析输出以获取版本 ID
        heads = []
        for line in result.stdout.splitlines():
            match = re.search(r'([0-9a-f]+)(?:\s|\()', line)
            if match:
                heads.append(match.group(1))
        
        return heads
    except Exception as e:
        print(f"获取头版本时出错: {e}")
        return []

def merge_heads():
    """合并多个头版本"""
    heads = get_alembic_heads()
    
    if not heads:
        print("没有找到头版本")
        return False
    
    if len(heads) == 1:
        print(f"只有一个头版本: {heads[0]}，不需要合并")
        return True
    
    print(f"发现多个头版本: {heads}")
    
    # 创建合并迁移
    try:
        print("创建合并迁移...")
        subprocess.run(["alembic", "merge", "heads", "-m", "Merge multiple heads"], check=True)
        print("合并迁移创建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"创建合并迁移失败: {e}")
        return False

async def init_db():
    """初始化数据库：创建表并填充种子数据"""
    print("初始化数据库...")
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)  # 确保在项目根目录运行
    
    # 检查数据库文件是否存在
    db_file = project_root / "stepflow.db"
    db_exists = db_file.exists()
    
    if db_exists:
        print(f"数据库文件已存在: {db_file}")
    else:
        print(f"数据库文件不存在，将创建新数据库: {db_file}")
    
    # 尝试使用 Alembic 应用迁移
    alembic_ini = project_root / "alembic.ini"
    if alembic_ini.exists():
        try:
            # 检查是否有多个头版本
            if len(get_alembic_heads()) > 1:
                print("检测到多个头版本，尝试合并...")
                if not merge_heads():
                    raise Exception("无法合并头版本")
            
            print("应用 Alembic 迁移...")
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            print("迁移完成！")
        except Exception as e:
            print(f"Alembic 迁移失败: {e}")
            print("使用 SQLAlchemy 创建表...")
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("表创建完成！")
    else:
        print("未找到 alembic.ini，使用 SQLAlchemy 创建表...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("表创建完成！")
    
    # 填充种子数据
    print("填充种子数据...")
    await seed_data()
    print("数据库初始化完成！")

if __name__ == "__main__":
    asyncio.run(init_db()) 