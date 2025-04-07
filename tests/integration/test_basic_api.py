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

def test_basic_workflow():
    """最基本的工作流测试"""
    
    # 1. 创建工作流模板
    template_data = {
        "name": "Basic Test Template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "BasicWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    
    print("\n1. 创建工作流模板:")
    response = client.post("/workflow_templates/", json=template_data)
    print(f"响应: {response.status_code} - {response.text}")
    assert response.status_code == 200
    template_id = response.json()["template_id"]
    
    # 2. 启动工作流执行
    execution_data = {
        "template_id": template_id,
        "workflow_id": "basic-test-workflow",
        "input": {"test": "data"}
    }
    
    print("\n2. 启动工作流执行:")
    response = client.post("/workflow_executions/", json=execution_data)
    print(f"响应: {response.status_code} - {response.text}")
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # 3. 获取工作流执行状态
    print("\n3. 获取工作流执行状态:")
    time.sleep(1)
    response = client.get(f"/workflow_executions/{run_id}")
    print(f"响应: {response.status_code} - {response.text}")
    assert response.status_code == 200
    execution = response.json()
    print(f"工作流状态: {execution['status']}") 