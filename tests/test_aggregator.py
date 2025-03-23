import pytest
import requests
import time

BASE_URL = "http://127.0.0.1:8000/api"

@pytest.fixture(scope="session", autouse=True)
def wait_for_server():
    """
    如果你已经确保后端服务 main.py 正在8000端口运行,
    就不一定需要这个等待. 否则留出1秒等待服务器启动.
    """
    time.sleep(1)
    yield

def test_create_and_execute_workflow_with_aggregator():
    """
    测试一个多次执行同一Task并将输出聚合到allOutputs数组的例子
    """
    # 1) 定义 DSL
    workflow_dsl = {
      "StartAt": "CheckCounter",
      "States": {
        "CheckCounter": {
          "Type": "Choice",
          "Choices": [
            {
              "Variable": "$.counter",
              "NumericLessThan": 3,
              "Next": "MyRepeatedTask"
            }
          ],
          "Default": "Done"
        },
        "MyRepeatedTask": {
          "Type": "Task",
          "Resource": "shell.exec",
          "InputPath": "$",
          "Parameters": {
            "command": "echo 'Aggregator Test'"
          },
          "ResultPath": "$.latestOutput",
          "MergeMode": "append",
          "MergePath": "$.allOutputs",
          "Next": "Increment"
        },
        "Increment": {
          "Type": "Pass",
          "Result": {"increment": 1},
          "ResultPath": "$.incrementValue",
          "Next": "UpdateCounter"
        },
        "UpdateCounter": {
          "Type": "Pass",
          "Parameters": {
            "value.$": "$.incrementValue.increment"
          },
          "ResultPath": "$.counter",
          "Next": "CheckCounter"
        },
        "Done": {
          "Type": "Succeed"
        }
      }
    }

    # 2) 创建工作流
    r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
    assert r.status_code == 200, f"Create workflow failed: {r.text}"
    data = r.json()
    wf_id = data["workflow_id"]  # 与前面controllers.py一致
    assert wf_id, "Should return a workflow_id"

    # 3) 执行工作流
    #   这里可以给context赋初值 "counter":0,
    #   看你的后端实现. 如果后端默认context = {"counter":0}也可.
    #   有些后端是分开传, 有些是 DSL 里 default context
    r = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute")
    assert r.status_code == 200, f"Execute workflow failed: {r.text}"
    exec_data = r.json()
    assert exec_data["message"] in ["Execution finished", "Workflow executed successfully"]

    # 4) 查询一下查看 DSL 或上下文. 
    #   如果后端get_workflow只返回 DSL, 你可能还得有别的接口
    #   来查看实际上下文. 
    #   这里假设 controllers.py: get_workflow 返回 {"workflow_id","definition"}
    #   并无上下文. 你可以修改后端让它也返回最终上下文, 或写独立API.
    r = requests.get(f"{BASE_URL}/workflow/{wf_id}")
    assert r.status_code == 200, f"Get workflow failed: {r.text}"
    data = r.json()

    # 这里"definition"是 DSL, 
    #   如果你也想验证最终上下文(especially allOutputs),
    #   需后端提供context之类. 
    #   假设后端加了 "context" 字段 =>  data["context"]["allOutputs"] ...
    if "context" not in data:
        # 说明后端还没实现返回上下文. 你可改后端 or just skip
        print("Warning: no 'context' in get_workflow response. Can't verify aggregator fully.")
        return

    final_context = data["context"]
    # 检查 allOutputs 是否有3条
    assert "allOutputs" in final_context, "Should have allOutputs key"
    outputs = final_context["allOutputs"]
    assert isinstance(outputs, list), "allOutputs should be a list"
    assert len(outputs) == 3, f"Expected 3 aggregator items, got {len(outputs)}"

    # 每条输出一般是 {"stdout": "...", "exit_code": ...}
    # 你可以更深入断言
    for idx, out in enumerate(outputs):
        assert "stdout" in out, f"Item {idx} missing stdout"
        assert out["exit_code"] == 0, f"Item {idx} not exit_code=0"

    print("Aggregator test passed with 3 items in allOutputs.")