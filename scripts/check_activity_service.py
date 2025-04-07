#!/usr/bin/env python
# scripts/check_activity_service.py

import inspect
from stepflow.application.activity_task_service import ActivityTaskService
from stepflow.infrastructure.repositories.activity_task_repository import ActivityTaskRepository

def check_service_methods():
    """检查 ActivityTaskService 的方法签名"""
    print("检查 ActivityTaskService 的方法签名...")
    
    # 获取所有方法
    methods = [method for method in dir(ActivityTaskService) if not method.startswith('_')]
    print(f"可用方法: {methods}")
    
    # 检查 get_tasks_by_run_id 方法
    if 'get_tasks_by_run_id' in methods:
        signature = inspect.signature(ActivityTaskService.get_tasks_by_run_id)
        print(f"get_tasks_by_run_id 方法签名: {signature}")
        
        # 获取所有参数
        params = signature.parameters
        print(f"参数列表: {list(params.keys())}")
        
        # 检查必需参数
        required_params = [name for name, param in params.items() 
                          if param.default == inspect.Parameter.empty and name != 'self']
        print(f"必需参数: {required_params}")
    else:
        print("缺少 get_tasks_by_run_id 方法")
    
    # 检查 ActivityTaskRepository 的 list_by_run_id 方法
    repo_methods = [method for method in dir(ActivityTaskRepository) if not method.startswith('_')]
    print(f"\nActivityTaskRepository 可用方法: {repo_methods}")
    
    if 'list_by_run_id' in repo_methods:
        signature = inspect.signature(ActivityTaskRepository.list_by_run_id)
        print(f"list_by_run_id 方法签名: {signature}")
    else:
        print("ActivityTaskRepository 缺少 list_by_run_id 方法")

if __name__ == "__main__":
    check_service_methods() 