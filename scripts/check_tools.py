#!/usr/bin/env python
# scripts/check_tools.py

from stepflow.worker.tools.tool_registry import tool_registry

print("=== 已注册的工具 ===")
for tool_name, tool_instance in tool_registry.items():
    print(f"工具名称: {tool_name}, 类型: {type(tool_instance).__name__}") 