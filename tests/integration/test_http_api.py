import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
import json
import asyncio
import time
from datetime import datetime, UTC

from stepflow.main import app
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal

# 创建测试客户端
client = TestClient(app)

# 在测试文件顶部添加调试信息
print("Available routes:")
for route in app.routes:
    print(f"  {route.path} [{route.methods}]")

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    """在异步上下文中设置和清理数据库"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(setup_database):
    """提供异步数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()

def test_api_health_check():
    """测试 API 服务是否正常运行"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_workflow_template_crud():
    """测试工作流模板的 CRUD 操作"""
    # 1. 创建模板
    template_data = {
        "name": "Test Template",
        "description": "A test workflow template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "TestWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    response = client.post("/workflow_templates/", json=template_data)
    print(f"Template creation response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    template_id = response.json()["template_id"]
    
    # 2. 获取模板
    response = client.get(f"/workflow_templates/{template_id}")
    assert response.status_code == 200
    template = response.json()
    assert template["name"] == "Test Template"
    
    # 3. 更新模板
    update_data = {
        "name": "Updated Template",
        "description": "An updated test workflow template"
    }
    response = client.put(f"/workflow_templates/{template_id}", json=update_data)
    assert response.status_code == 200
    
    # 4. 验证更新
    response = client.get(f"/workflow_templates/{template_id}")
    assert response.status_code == 200
    updated_template = response.json()
    assert updated_template["name"] == "Updated Template"
    
    # 5. 列出所有模板
    response = client.get("/workflow_templates/")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 1
    
    # 6. 删除模板
    response = client.delete(f"/workflow_templates/{template_id}")
    assert response.status_code == 200
    
    # 7. 验证删除
    response = client.get(f"/workflow_templates/{template_id}")
    assert response.status_code == 404

def test_workflow_execution_lifecycle():
    """测试工作流执行的生命周期"""
    # 1. 创建工作流模板
    template_data = {
        "name": "Lifecycle Test Template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "LifecycleTestWorkflow",
            "StartAt": "TaskState",
            "States": {
                "TaskState": {
                    "Type": "Task",
                    "ActivityType": "SimpleTask",
                    "End": True
                }
            }
        })
    }
    response = client.post("/workflow_templates/", json=template_data)
    assert response.status_code == 200
    template_id = response.json()["template_id"]
    
    # 2. 启动工作流执行
    execution_data = {
        "workflow_id": "lifecycle-test-execution",
        "template_id": template_id,
        "input": {"test": "data"}  # 直接使用字典，不使用 json.dumps
    }
    response = client.post("/workflow_executions/", json=execution_data)
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # 3. 获取工作流执行状态
    time.sleep(1)  # 等待工作流启动
    response = client.get(f"/workflow_executions/{run_id}")
    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] == "running"
    
    # 4. 获取活动任务
    time.sleep(1)  # 等待任务创建
    response = client.get(f"/activity_tasks/run/{run_id}")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    task = tasks[0]
    assert task["activity_type"] == "SimpleTask"
    
    # 5. 启动活动任务
    response = client.post(f"/activity_tasks/{task['task_token']}/start")
    assert response.status_code == 200
    
    # 6. 完成活动任务
    complete_data = {
        "result_data": json.dumps({"result": "success"})
    }
    response = client.post(f"/activity_tasks/{task['task_token']}/complete", json=complete_data)
    assert response.status_code == 200
    
    # 7. 等待工作流完成
    time.sleep(2)  # 增加等待时间从 1 秒到 2 秒
    response = client.get(f"/workflow_executions/{run_id}")
    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] == "completed"
    
    # 8. 获取工作流可见性
    response = client.get(f"/workflow_visibility/{run_id}")
    assert response.status_code == 200
    visibility = response.json()
    assert visibility["status"] == "completed"

def test_activity_task_failure_handling():
    """测试活动任务失败处理"""
    # 1. 创建工作流模板
    template_data = {
        "name": "Error Test Template",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "ErrorTestWorkflow",
            "StartAt": "TaskState",
            "States": {
                "TaskState": {
                    "Type": "Task",
                    "ActivityType": "ErrorTask",
                    "End": True
                }
            }
        })
    }
    response = client.post("/workflow_templates/", json=template_data)
    assert response.status_code == 200
    template_id = response.json()["template_id"]
    
    # 2. 启动工作流执行
    execution_data = {
        "workflow_id": "error-test-execution",
        "template_id": template_id,
        "input": {"should_fail": True}  # 直接使用字典，不使用 json.dumps
    }
    response = client.post("/workflow_executions/", json=execution_data)
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # 3. 获取活动任务
    time.sleep(1)
    response = client.get(f"/activity_tasks/run/{run_id}")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    task = tasks[0]
    
    # 4. 启动活动任务
    response = client.post(f"/activity_tasks/{task['task_token']}/start")
    assert response.status_code == 200
    
    # 5. 使任务失败
    fail_data = {
        "reason": "Task failed",
        "details": json.dumps({"error": "Test error"})
    }
    response = client.post(f"/activity_tasks/{task['task_token']}/fail", json=fail_data)
    assert response.status_code == 200
    
    # 6. 验证工作流状态
    time.sleep(2)
    response = client.get(f"/workflow_executions/{run_id}")
    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] == "failed"

def test_http_tool_workflow():
    """测试 HTTP 工具工作流"""
    # 1. 创建工作流模板
    template_data = {
        "name": "HTTP Tool Workflow",
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "HttpToolWorkflow",
            "StartAt": "HttpTask",
            "States": {
                "HttpTask": {
                    "Type": "Task",
                    "ActivityType": "HttpTool",
                    "End": True
                }
            }
        })
    }
    response = client.post("/workflow_templates/", json=template_data)
    assert response.status_code == 200
    template_id = response.json()["template_id"]
    
    # 2. 启动工作流执行
    execution_data = {
        "workflow_id": "http-tool-workflow",
        "template_id": template_id,
        "input": {  # 直接使用字典，不使用 json.dumps
            "url": "https://jsonplaceholder.typicode.com/todos/1",
            "method": "GET"
        }
    }
    response = client.post("/workflow_executions/", json=execution_data)
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # 3. 获取活动任务
    time.sleep(1)
    response = client.get(f"/activity_tasks/run/{run_id}")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    task = tasks[0]
    
    # 4. 启动活动任务
    response = client.post(f"/activity_tasks/{task['task_token']}/start")
    assert response.status_code == 200
    
    # 5. 完成活动任务
    complete_data = {
        "result_data": json.dumps({
            "status_code": 200,
            "body": {"userId": 1, "id": 1, "title": "delectus aut autem", "completed": False}
        })
    }
    response = client.post(f"/activity_tasks/{task['task_token']}/complete", json=complete_data)
    assert response.status_code == 200
    
    # 6. 验证工作流状态
    time.sleep(2)
    response = client.get(f"/workflow_executions/{run_id}")
    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] == "completed"

def test_app_is_running():
    """确认应用正在运行并响应请求"""
    response = client.get("/")
    assert response.status_code == 200
    print("Root response:", response.json())
    
    # 打印所有可用路由
    print("\nAll available routes:")
    for route in app.routes:
        print(f"  {route.path} [{', '.join(route.methods)}]")

def test_simplified_workflow():
    """测试简化的工作流"""
    # 1. 创建工作流模板
    template_data = {
        "name": "Simple Test Template",
        "template_id": "simple-test-template",  # 指定模板 ID
        "dsl_definition": json.dumps({
            "Version": "1.0",
            "Name": "SimpleTestWorkflow",
            "StartAt": "PassState",
            "States": {
                "PassState": {
                    "Type": "Pass",
                    "End": True
                }
            }
        })
    }
    response = client.post("/workflow_templates/", json=template_data)
    assert response.status_code in [200, 409]  # 允许已存在
    
    # 2. 启动工作流执行
    execution_data = {
        "workflow_id": "simple-test-workflow",
        "template_id": "simple-test-template",
        "input": {"test": "data"}  # 直接使用字典，不使用 json.dumps
    }
    response = client.post("/workflow_executions/", json=execution_data)
    assert response.status_code in [200, 201]
    run_id = response.json()["run_id"]
    
    # 3. 验证工作流状态
    time.sleep(2)
    response = client.get(f"/workflow_executions/{run_id}")
    assert response.status_code == 200
    execution = response.json()
    assert execution["status"] in ["completed", "running"]  # Pass 状态应该很快完成

def test_check_api_schema():
    """检查 API 模式以了解正确的请求格式"""
    
    # 获取 OpenAPI 模式
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    # 打印工作流模板和执行的请求体模式
    paths = schema.get("paths", {})
    
    # 更新路径检查
    if "/workflow_templates/" in paths:
        print("\nWorkflow Template Schema:")
        post_schema = paths["/workflow_templates/"].get("post", {})
        request_body = post_schema.get("requestBody", {})
        print(json.dumps(request_body, indent=2))
    
    if "/workflow_executions/" in paths:
        print("\nWorkflow Execution Schema:")
        post_schema = paths["/workflow_executions/"].get("post", {})
        request_body = post_schema.get("requestBody", {})
        print(json.dumps(request_body, indent=2))

def test_debug_routes():
    """调试可用的路由"""
    print("\n所有可用路由:")
    for route in app.routes:
        print(f"  {route.path} [{', '.join(route.methods)}]")
    
    # 测试根路径
    response = client.get("/")
    print(f"根路径响应: {response.status_code}")
    if response.status_code == 200:
        print(f"响应内容: {response.json()}")
    
    # 测试 OpenAPI 文档
    response = client.get("/docs")
    print(f"文档路径响应: {response.status_code}")
    
    # 测试 OpenAPI 模式
    response = client.get("/openapi.json")
    print(f"OpenAPI 模式响应: {response.status_code}")
    if response.status_code == 200:
        schema = response.json()
        print("可用路径:")
        for path in schema.get("paths", {}).keys():
            print(f"  {path}")

def test_basic_workflow():
    """基本工作流测试 - 使用实际路径"""
    
    # 打印所有路由
    print("\n所有可用路由:")
    for route in app.routes:
        print(f"  {route.path} [{', '.join(route.methods)}]")
    
    # 1. 检查服务是否运行
    response = client.get("/")
    assert response.status_code == 200
    print(f"根路径响应: {response.json()}")
    
    # 尝试不同的路径格式
    paths_to_try = [
        "/workflow_templates",
        "/workflow_templates/",
        "/templates",
        "/templates/",
        "/api/workflow_templates",
        "/api/templates"
    ]
    
    print("\n尝试不同的模板创建路径:")
    for path in paths_to_try:
        template_data = {
            "name": "Test Template",
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
        
        response = client.post(path, json=template_data)
        print(f"  {path}: {response.status_code}")
        if response.status_code in [200, 201]:
            print(f"    成功! 响应: {response.json()}")
            return  # 找到正确路径后退出 

def test_minimal_workflow_template():
    """最小化测试工作流模板 API"""
    
    # 1. 创建工作流模板
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
    
    if response.status_code == 200:
        template_id = response.json().get("template_id")
        print(f"创建的模板 ID: {template_id}")
        
        # 2. 获取工作流模板
        get_response = client.get(f"/workflow_templates/{template_id}")
        print(f"\n获取模板响应状态码: {get_response.status_code}")
        print(f"获取模板响应内容: {get_response.text}") 