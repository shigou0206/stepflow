#!/usr/bin/env python
# scripts/debug_tool_registry.py

import sys
import os
import importlib
import inspect

# 打印当前 Python 路径
print("Python 路径:")
for path in sys.path:
    print(f"  - {path}")

# 尝试直接导入工具注册表
print("\n尝试导入工具注册表:")
try:
    from stepflow.worker.tools.tool_registry import tool_registry
    print("导入成功!")
    print("已注册的工具:")
    for name, tool in tool_registry.items():
        print(f"  - {name}: {type(tool).__name__}")
except Exception as e:
    print(f"导入失败: {str(e)}")
    import traceback
    traceback.print_exc()

# 尝试手动加载 http_tool.py
print("\n尝试手动加载 http_tool.py:")
try:
    # 获取项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    http_tool_path = os.path.join(project_root, "stepflow", "worker", "tools", "http_tool.py")
    
    print(f"HTTP 工具路径: {http_tool_path}")
    if os.path.exists(http_tool_path):
        print("文件存在!")
        
        # 尝试导入模块
        spec = importlib.util.spec_from_file_location("http_tool", http_tool_path)
        http_tool_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(http_tool_module)
        
        # 检查模块内容
        print("模块内容:")
        for name, obj in inspect.getmembers(http_tool_module):
            if not name.startswith("__"):
                print(f"  - {name}: {type(obj)}")
    else:
        print("文件不存在!")
except Exception as e:
    print(f"加载失败: {str(e)}")
    import traceback
    traceback.print_exc()

# 尝试模拟活动工作器的工具查找过程
print("\n模拟活动工作器的工具查找过程:")
try:
    from stepflow.worker.tools.tool_registry import tool_registry
    
    # 测试不同的活动类型名称
    test_types = ["HttpTool", "http_tool", "HTTP_TOOL", "httptool", "ShellTool", "shell_tool"]
    
    for activity_type in test_types:
        tool = tool_registry.get(activity_type)
        if tool:
            print(f"找到工具 '{activity_type}': {type(tool).__name__}")
        else:
            print(f"未找到工具 '{activity_type}'")
except Exception as e:
    print(f"模拟失败: {str(e)}") 