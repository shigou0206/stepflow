# tests/test_api.py
import pytest
import requests
import time

BASE_URL = "http://127.0.0.1:8000/api"

@pytest.fixture(scope="session", autouse=True)
def wait_for_server():
    # 若你已确保服务器启动, 可去掉这步
    time.sleep(1)
    yield

def test_pass_task_succeed():
    """
    测试最小 DSL: Pass -> Task -> Succeed
    """
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

    # 1) 创建工作流
    r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
    assert r.status_code == 200, f"Create workflow failed: {r.text}"
    data = r.json()
    wf_id = data["workflow_id"]
    assert wf_id, "Should return a workflow_id"

    # # 2) 执行工作流
    r = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute")
    assert r.status_code == 200, f"Execute workflow failed: {r.text}"
    data = r.json()
    assert data["message"] == "Execution finished"

    # # 3) 查询一下
    # r = requests.get(f"{BASE_URL}/workflow/{wf_id}")
    # assert r.status_code == 200, f"Get workflow DSL failed: {r.text}"
    # data = r.json()
    # assert "definition" in data
    # assert data["definition"]["StartAt"] == "PassState"


# def test_choice_branch():
#     """
#     测试 Choice 状态, 根据 context 中 'counter' 是否 < 3 
#     分支到 MyTask or Done
#     """
#     workflow_dsl = {
#         "StartAt": "CheckCounter",
#         "States": {
#             "CheckCounter": {
#                 "Type": "Choice",
#                 "Choices": [
#                     {
#                         "Variable": "$.counter",
#                         "NumericLessThan": 3,
#                         "Next": "MyTask"
#                     }
#                 ],
#                 "Default": "Done"
#             },
#             "MyTask": {
#                 "Type": "Task",
#                 "Resource": "shell.exec",
#                 "Parameters": {
#                     "command": "echo 'Choice Branch Execution'"
#                 },
#                 "Next": "Done"
#             },
#             "Done": {
#                 "Type": "Succeed"
#             }
#         }
#     }

#     # 创建
#     r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
#     assert r.status_code == 200, f"Create workflow failed: {r.text}"
#     data = r.json()
#     wf_id = data["workflow_id"]
#     assert wf_id

#     # 注意: 这里可给 context= {"counter":2} or {"counter":5} 
#     #   通过某API? 
#     #   或  DSL 中 if you support "context": {...} in POST body?
#     #   这里假设 2 => should run MyTask
#     #           5 => skip MyTask => "Done" directly

#     # 先设置counter=2 => expect MyTask
#     # 你若后端支持 /workflow/{id}/execute?context=????
#     # or a separate API to update context?

#     # 先执行 => counter=2
#     r = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute", json={"context":{"counter":2}})
#     assert r.status_code == 200, f"Execute fail: {r.text}"
#     exec_data = r.json()
#     assert exec_data["message"] == "Execution finished", exec_data

#     # 再 断言?
#     # 你可在后端有 logs or final context?

#     # 另一个branch => counter=5
#     # 需要 "reset"? or create a new workflow? 
#     # 这里使用同 DSL, create a new workflow again
#     r2 = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
#     assert r2.status_code == 200, f"Create second workflow fail: {r2.text}"
#     data2 = r2.json()
#     wf_id2 = data2["workflow_id"]
#     assert wf_id2

#     r2 = requests.post(f"{BASE_URL}/workflow/{wf_id2}/execute", json={"context":{"counter":5}})
#     assert r2.status_code == 200, f"Execute fail: {r2.text}"
#     exec_data2 = r2.json()
#     assert exec_data2["message"] == "Execution finished"

# def test_fail_state():
#     """
#     测试 Fail 状态, DSL 里写 cause => 立即中断
#     """
#     workflow_dsl = {
#         "StartAt": "Check",
#         "States": {
#             "Check": {
#                 "Type": "Fail",
#                 "Cause": "SomethingWentWrong"
#             }
#         }
#     }

#     # 创建
#     r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
#     assert r.status_code == 200, f"Create fail-state workflow: {r.text}"
#     data = r.json()
#     wf_id = data["workflow_id"]
#     assert wf_id

#     # 执行
#     r = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute")
#     # 这里你后端可能返回 200 with "Execution finished" but actually is "Failed"? 
#     # or 4xx?
#     # 看你如何设计. 
#     # 先假设执行成功, message= "Execution finished" but final status= fail
#     assert r.status_code == 200, f"Execute fail: {r.text}"
#     data = r.json()
#     # 你后端 maybe: data["message"] = "Execution failState triggered"
#     # or "Execution finished"? 
#     # we do a mild assertion
#     assert "message" in data

# def test_dynamic_parameters():
#     """
#     测试 'dynamic' 模式 => 
#     DSL: 
#       InputPath => "$.someContext"
#       Task => shell.exec => command.$ => "$.cmdStr"
#     """
#     workflow_dsl = {
#       "StartAt": "PassInput",
#       "States": {
#         "PassInput": {
#           "Type": "Pass",
#           "Next": "TaskState"
#         },
#         "TaskState": {
#           "Type": "Task",
#           "Resource": "shell.exec",
#           "InputPath": "$.someContext",
#           "Parameters": {
#             "command.$": "$.cmdStr" 
#           },
#           "Next": "Done"
#         },
#         "Done": {
#           "Type": "Succeed"
#         }
#       }
#     }

#     # create
#     r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
#     assert r.status_code == 200, f"Create workflow fail: {r.text}"
#     data = r.json()
#     wf_id = data["workflow_id"]
#     assert wf_id

#     # execute => with context={"someContext":{"cmdStr":"echo Dynamic Param!"}}
#     exec_payload = {
#       "context": {
#         "someContext": {
#           "cmdStr": "echo 'Dynamic Param!'"
#         }
#       }
#     }
#     r2 = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute", json=exec_payload)
#     assert r2.status_code == 200, f"Execute fail: {r2.text}"
#     data2 = r2.json()
#     assert data2["message"] == "Execution finished"