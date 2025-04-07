#!/usr/bin/env python
# scripts/test_workflow_repo.py

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.repositories.workflow_execution_repository import WorkflowExecutionRepository

async def test_repo_methods():
    """测试 WorkflowExecutionRepository 的方法"""
    print("测试 WorkflowExecutionRepository 的方法...")
    
    async with AsyncSessionLocal() as session:
        repo = WorkflowExecutionRepository(session)
        
        # 打印所有可用方法
        methods = [method for method in dir(repo) if not method.startswith('_')]
        print(f"可用方法: {methods}")
        
        # 检查是否有 get_by_id 或 get_by_run_id 方法
        if 'get_by_id' in methods:
            print("存在 get_by_id 方法")
        else:
            print("不存在 get_by_id 方法")
        
        if 'get_by_run_id' in methods:
            print("存在 get_by_run_id 方法")
        else:
            print("不存在 get_by_run_id 方法")

if __name__ == "__main__":
    asyncio.run(test_repo_methods()) 