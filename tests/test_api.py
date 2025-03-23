# tests/test_api.py
import pytest
import requests
import time

BASE_URL = "http://127.0.0.1:8000/api"

@pytest.fixture(scope="session", autouse=True)
def wait_for_server():
    # 等待服务器启动 (若你确保已启动, 可不需要这步)
    time.sleep(1)
    yield

def test_create_and_execute_workflow():
    # 1. 创建一个最小 DSL (包含 Pass, Task, Succeed)
    workflow_dsl = {
        "StartAt": "PassState",
        "States": {
            "PassState": {
                "Type": "Pass",
                "Result": {"cmd": "echo Hello"},
                "Next": "TaskState"
            },
            "TaskState": {
                "Type": "Task",
                "Resource": "shell.exec",
                "Parameters": {
                    "command": "echo 'Hello from shell_exec'"
                },
                "Next": "SuccessState"
            },
            "SuccessState": {
                "Type": "Succeed"
            }
        }
    }

    # 2. 创建工作流
    r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
    assert r.status_code == 200, r.text
    data = r.json()
    wf_id = data["workflow_id"]
    assert wf_id, "Should return a workflow_id"

    # 3. 执行工作流
    r = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["message"] == "Execution finished"

    # 4. 查询一下看能不能拿回 DSL
    r = requests.get(f"{BASE_URL}/workflow/{wf_id}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "definition" in data
    assert data["definition"]["StartAt"] == "PassState"