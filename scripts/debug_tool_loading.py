#!/usr/bin/env python
# scripts/debug_tool_loading.py

import sys
import os
import importlib.util
import inspect

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

print("=== 调试工具加载过程 ===")

# 1. 检查 tool_registry.py 文件
registry_path = os.path.join(project_root, "stepflow", "worker", "tools", "tool_registry.py")
print(f"工具注册表文件路径: {registry_path}")
print(f"文件是否存在: {os.path.exists(registry_path)}")

# 2. 加载 tool_registry.py 模块
print("\n加载 tool_registry 模块:")
try:
    spec = importlib.util.spec_from_file_location("tool_registry", registry_path)
    registry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_module)
    
    # 检查模块中的 tool_registry 变量
    if hasattr(registry_module, "tool_registry"):
        print("找到 tool_registry 变量!")
        registry = registry_module.tool_registry
        print(f"注册表类型: {type(registry)}")
        print("注册的工具:")
        for name, tool in registry.items():
            print(f"  - {name}: {type(tool).__name__}")
    else:
        print("未找到 tool_registry 变量!")
except Exception as e:
    print(f"加载失败: {str(e)}")
    import traceback
    traceback.print_exc()

# 3. 检查 HttpTool 类
http_tool_path = os.path.join(project_root, "stepflow", "worker", "tools", "http_tool.py")
print(f"\nHttpTool 文件路径: {http_tool_path}")
print(f"文件是否存在: {os.path.exists(http_tool_path)}")

print("\n加载 HttpTool 类:")
try:
    spec = importlib.util.spec_from_file_location("http_tool", http_tool_path)
    http_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(http_module)
    
    # 检查模块中的 HttpTool 类
    if hasattr(http_module, "HttpTool"):
        print("找到 HttpTool 类!")
        http_tool_class = http_module.HttpTool
        print(f"类名: {http_tool_class.__name__}")
        
        # 检查类方法
        print("类方法:")
        for name, method in inspect.getmembers(http_tool_class, predicate=inspect.isfunction):
            if not name.startswith("__"):
                print(f"  - {name}: {method}")
                
        # 创建实例并检查方法
        print("\n创建实例并检查方法:")
        http_tool = http_tool_class()
        for name, method in inspect.getmembers(http_tool, predicate=inspect.ismethod):
            if not name.startswith("__"):
                print(f"  - {name}: {method}")
    else:
        print("未找到 HttpTool 类!")
except Exception as e:
    print(f"加载失败: {str(e)}")
    import traceback
    traceback.print_exc()

# 4. 模拟活动工作器的工具查找过程
print("\n模拟活动工作器的工具查找过程:")
try:
    from stepflow.worker.tools.tool_registry import tool_registry
    
    # 测试不同的活动类型名称
    test_types = ["HttpTool", "http_tool", "HTTP_TOOL", "httptool", "ShellTool", "shell_tool"]
    
    for activity_type in test_types:
        tool = tool_registry.get(activity_type)
        if tool:
            print(f"找到工具 '{activity_type}': {type(tool).__name__}")
            
            # 检查 execute 方法
            if hasattr(tool, "execute"):
                print(f"  - 有 execute 方法: {tool.execute}")
            else:
                print(f"  - 没有 execute 方法!")
                
            # 检查 run 方法
            if hasattr(tool, "run"):
                print(f"  - 有 run 方法: {tool.run}")
            else:
                print(f"  - 没有 run 方法!")
        else:
            print(f"未找到工具 '{activity_type}'")
except Exception as e:
    print(f"模拟失败: {str(e)}")
    import traceback
    traceback.print_exc() 