import pytest
from fastapi.testclient import TestClient
import json

from stepflow.main import app

# 创建测试客户端
client = TestClient(app)

def test_debug_app_configuration():
    """详细检查应用配置"""
    print("\n应用详情:")
    print(f"应用标题: {app.title}")
    print(f"应用版本: {app.version}")
    
    print("\n所有路由:")
    for route in app.routes:
        print(f"  路径: {route.path}")
        print(f"  方法: {route.methods}")
        print(f"  名称: {getattr(route, 'name', 'N/A')}")
        print(f"  类型: {type(route)}")
        if hasattr(route, "endpoint"):
            print(f"  端点: {route.endpoint.__name__}")
        print("  ---")
    
    # 测试根路径
    response = client.get("/")
    print(f"\n根路径响应: {response.status_code}")
    if response.status_code == 200:
        print(f"响应内容: {response.json()}")
    
    # 获取 OpenAPI 模式
    response = client.get("/openapi.json")
    if response.status_code == 200:
        schema = response.json()
        print("\nAPI 路径:")
        for path in schema.get("paths", {}).keys():
            print(f"  {path}") 