import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
import json
import time

from stepflow.main import app
from stepflow.infrastructure.database import Base, async_engine

# 创建测试客户端
client = TestClient(app)

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    """在异步上下文中设置和清理数据库"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

def test_api_health():
    """测试 API 健康状态"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    print(f"API 健康状态: {response.json()}")

def test_create_template():
    """测试创建工作流模板"""
    template_data = {
        "name": "Minimal Test Template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "MinimalWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    
    print("\n测试工作流模板创建:")
    print(f"请求数据: {json.dumps(template_data, indent=2)}")
    
    response = client.post("/workflow_templates/", json=template_data)
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    assert response.status_code == 200
    result = response.json()
    assert "template_id" in result 