#!/usr/bin/env python
# scripts/debug_workflow_templates.py

import asyncio
import json
import logging
from stepflow.infrastructure.database import AsyncSessionLocal
from stepflow.infrastructure.models import WorkflowTemplate

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def list_workflow_templates():
    """列出所有工作流模板"""
    logger.info("=== 列出所有工作流模板 ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        stmt = select(WorkflowTemplate)
        result = await session.execute(stmt)
        templates = result.scalars().all()
        
        logger.info(f"找到 {len(templates)} 个工作流模板:")
        for tpl in templates:
            logger.info(f"  模板 ID: {tpl.template_id}")
            logger.info(f"  名称: {tpl.name}")
            logger.info(f"  描述: {tpl.description}")
            logger.info(f"  创建时间: {tpl.created_at}")
            logger.info(f"  更新时间: {tpl.updated_at}")
            logger.info("  ---")

async def delete_template(template_id: str):
    """删除指定的工作流模板"""
    logger.info(f"=== 删除工作流模板: {template_id} ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import delete
        
        stmt = delete(WorkflowTemplate).where(WorkflowTemplate.template_id == template_id)
        result = await session.execute(stmt)
        await session.commit()
        
        logger.info(f"删除结果: 影响行数 = {result.rowcount}")

async def delete_all_test_templates():
    """删除所有测试模板"""
    logger.info("=== 删除所有测试模板 ===")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, delete
        
        # 查找所有测试模板
        stmt = select(WorkflowTemplate).where(WorkflowTemplate.template_id.like("http-failure-test%"))
        result = await session.execute(stmt)
        templates = result.scalars().all()
        
        logger.info(f"找到 {len(templates)} 个测试模板:")
        for tpl in templates:
            logger.info(f"  准备删除: {tpl.template_id}")
            await session.delete(tpl)
        
        await session.commit()
        logger.info("删除完成")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # 列出所有模板
        asyncio.run(list_workflow_templates())
    elif len(sys.argv) == 2 and sys.argv[1] == "--clean":
        # 删除所有测试模板
        asyncio.run(delete_all_test_templates())
    elif len(sys.argv) == 3 and sys.argv[1] == "--delete":
        # 删除指定模板
        template_id = sys.argv[2]
        asyncio.run(delete_template(template_id))
    else:
        print("用法:")
        print("  python debug_workflow_templates.py              # 列出所有模板")
        print("  python debug_workflow_templates.py --clean      # 删除所有测试模板")
        print("  python debug_workflow_templates.py --delete ID  # 删除指定模板") 