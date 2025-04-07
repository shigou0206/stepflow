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

def test_simple_template_creation():
    """测试简单的工作流模板创建"""
    template_data = {
        "name": "Simple Test Template",
        "description": "A test template",  # 添加描述字段
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "SimpleWorkflow",
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

def test_simple_workflow():
    """测试最简单的工作流"""
    # 1. 创建工作流模板
    template_data = {
        "name": "Simple Pass Workflow",
        "template_id": "simple-pass-workflow",  # 使用固定 ID
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "SimplePassWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    
    # 尝试创建模板（如果已存在则忽略）
    response = client.post("/workflow_templates/", json=template_data)
    print(f"Template creation response: {response.status_code} - {response.text}")
    assert response.status_code in [200, 409]  # 200=创建成功，409=已存在
    
    if response.status_code == 200:
        template_id = response.json()["template_id"]
    else:
        template_id = "simple-pass-workflow"
    
    # 2. 启动工作流执行
    execution_data = {
        "workflow_id": "simple-test-execution",
        "template_id": template_id,
        "input": {"test": "data"}
    }
    
    response = client.post("/workflow_executions/", json=execution_data)
    print(f"Execution creation response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # 3. 等待工作流完成
    time.sleep(2)
    response = client.get(f"/workflow_executions/{run_id}")
    print(f"Execution status response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] == "completed"  # Pass 状态应该很快完成 