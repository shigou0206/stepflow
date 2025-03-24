# # tests/test_api.py
# import pytest
# import requests
# import time

# BASE_URL = "http://127.0.0.1:8000/api"

# @pytest.fixture(scope="session", autouse=True)
# def wait_for_server():
#     # 若已确定服务启动，可去掉这一步
#     time.sleep(1)
#     yield

# def test_task_with_context_check():
#     """
#     测试一个 Task 状态执行后，把输出写到 context["shellOutput"],
#     并在执行完成后查询 context 验证结果
#     """

#     # 1. 准备 DSL: Task -> shell.exec -> resultPath => $.shellOutput
#     workflow_dsl = {
#         "StartAt": "MyTask",
#         "States": {
#             "MyTask": {
#                 "Type": "Task",
#                 "Resource": "shell.exec",
#                 "Parameters": {
#                     "command": "echo 'Hello Context Test!'"
#                 },
#                 "ResultPath": "$.shellOutput",
#                 "OutputPath": "$.shellOutput",
#                 "Next": "Done"
#             },
#             "Done": {
#                 "Type": "Succeed"
#             }
#         }
#     }

#     # 2. 创建工作流
#     r = requests.post(f"{BASE_URL}/workflow", json=workflow_dsl)
#     assert r.status_code == 200, f"Create workflow failed: {r.text}"
#     data = r.json()
#     wf_id = data["workflow_id"]
#     assert wf_id, "workflow_id not returned"

#     # 3. 执行工作流 (POST /workflow/{wf_id}/execute)
#     # 如果你支持传入初始context, 也可以 pass json={"context":{"key":"val"}}
#     r_exec = requests.post(f"{BASE_URL}/workflow/{wf_id}/execute")
#     assert r_exec.status_code == 200, f"Execution request failed: {r_exec.text}"
#     exec_info = r_exec.json()
#     assert exec_info["message"] == "Execution finished", f"message: {exec_info}"

#     # 4. 查询上下文 (GET /workflow/{wf_id}/context)
#     r_ctx = requests.get(f"{BASE_URL}/workflow/{wf_id}/context")
#     assert r_ctx.status_code == 200, f"Get context fail: {r_ctx.text}"
#     ctx_data = r_ctx.json()
#     # ctx_data => { "context": {...} }
#     assert "context" in ctx_data, f"missing 'context' field in response: {ctx_data}"
#     final_ctx = ctx_data["context"]

#     # 5. 断言 final_ctx 包含我们想要的 "shellOutput"
#     assert "shellOutput" in final_ctx, f"final_ctx missing shellOutput: {final_ctx}"
#     shell_out = final_ctx["shellOutput"]

#     # stdout 里应该包含 "Hello Context Test!"
#     assert "stdout" in shell_out, f"shellOutput missing 'stdout': {shell_out}"
#     assert "Hello Context Test!" in shell_out["stdout"], f"stdout content mismatch: {shell_out['stdout']}"
#     # exit_code 应该是 0
#     assert shell_out.get("exit_code") == 0, f"exit_code not 0: {shell_out}"