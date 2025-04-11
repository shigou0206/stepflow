#!/usr/bin/env python
# scripts/clean_test_data.py

import asyncio
import logging
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowTemplate, WorkflowExecution, ActivityTask, WorkflowEvent

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def clean_test_data():
    """清理测试数据"""
    logger.info("=== 开始清理测试数据 ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, delete
        
        # 1. 查找所有测试模板
        stmt = select(WorkflowTemplate).where(
            (WorkflowTemplate.template_id.like("test-%")) | 
            (WorkflowTemplate.template_id.like("http-failure-test%"))
        )
        result = await session.execute(stmt)
        templates = result.scalars().all()
        
        template_ids = [tpl.template_id for tpl in templates]
        logger.info(f"找到 {len(templates)} 个测试模板: {template_ids}")
        
        # 2. 查找使用这些模板的工作流执行
        if template_ids:
            stmt = select(WorkflowExecution).where(WorkflowExecution.template_id.in_(template_ids))
            result = await session.execute(stmt)
            executions = result.scalars().all()
            
            run_ids = [exec.run_id for exec in executions]
            logger.info(f"找到 {len(executions)} 个相关工作流执行: {run_ids}")
            
            # 3. 删除相关的活动任务
            if run_ids:
                stmt = delete(ActivityTask).where(ActivityTask.run_id.in_(run_ids))
                result = await session.execute(stmt)
                logger.info(f"删除了 {result.rowcount} 个活动任务")
                
                # 4. 删除相关的工作流事件
                stmt = delete(WorkflowEvent).where(WorkflowEvent.run_id.in_(run_ids))
                result = await session.execute(stmt)
                logger.info(f"删除了 {result.rowcount} 个工作流事件")
                
                # 5. 删除工作流执行
                for exec in executions:
                    await session.delete(exec)
                logger.info(f"删除了 {len(executions)} 个工作流执行")
        
        # 6. 删除模板
        for tpl in templates:
            await session.delete(tpl)
        logger.info(f"删除了 {len(templates)} 个工作流模板")
        
        # 提交更改
        await session.commit()
        logger.info("清理完成")

if __name__ == "__main__":
    asyncio.run(clean_test_data()) 