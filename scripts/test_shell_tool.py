#!/usr/bin/env python
# scripts/test_shell_tool.py

import asyncio
import json
import logging
from stepflow.worker.tools.shell_tool import ShellTool

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_shell_tool():
    """测试 ShellTool 执行"""
    logger.info("=== 测试 ShellTool ===")
    
    # 创建 ShellTool 实例
    tool = ShellTool()
    
    # 测试用例 1: 基本命令
    params1 = {
        "command": "echo 'Hello from ShellTool'",
        "timeout": 5,
        "shell": True
    }
    
    logger.info(f"执行命令: {params1['command']}")
    result1 = await tool.execute(params1)
    logger.info(f"执行结果: {result1}")
    
    # 测试用例 2: 列出目录
    params2 = {
        "command": "ls -la",
        "timeout": 5,
        "shell": True
    }
    
    logger.info(f"执行命令: {params2['command']}")
    result2 = await tool.execute(params2)
    logger.info(f"执行结果: {result2}")
    
    # 测试用例 3: 缺少命令参数
    params3 = {
        "timeout": 5,
        "shell": True
    }
    
    logger.info(f"执行缺少命令的请求")
    result3 = await tool.execute(params3)
    logger.info(f"执行结果: {result3}")

if __name__ == "__main__":
    asyncio.run(test_shell_tool()) 