#!/usr/bin/env python
# scripts/check_service_methods.py

import inspect
from stepflow.application.workflow_template_service import WorkflowTemplateService
from stepflow.infrastructure.repositories.workflow_template_repository import WorkflowTemplateRepository

def check_service_methods():
    """检查服务类的方法签名"""
    print("检查 WorkflowTemplateService 的方法签名...")
    
    # 获取 create_template 方法的签名
    signature = inspect.signature(WorkflowTemplateService.create_template)
    print(f"create_template 方法签名: {signature}")
    
    # 获取所有参数
    params = signature.parameters
    print(f"参数列表: {list(params.keys())}")
    
    # 检查必需参数
    required_params = [name for name, param in params.items() 
                      if param.default == inspect.Parameter.empty and name != 'self']
    print(f"必需参数: {required_params}")
    
    # 检查可选参数
    optional_params = [name for name, param in params.items() 
                      if param.default != inspect.Parameter.empty and name != 'self']
    print(f"可选参数: {optional_params}")

if __name__ == "__main__":
    check_service_methods() 