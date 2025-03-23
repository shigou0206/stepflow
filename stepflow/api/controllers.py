# stepflow/api/controllers.py
from fastapi import HTTPException
from stepflow.api.schemas import WorkflowDef
from stepflow.persistence.storage import (
    save_workflow_definition,
    get_workflow_definition,
)
from stepflow.engine.executor import WorkflowEngine

def create_workflow(workflow_def: dict):
    """
    1. 校验 DSL
    2. 存入DB (save_workflow_definition)
    3. 返回 {"message": "Workflow created", "workflow_id": ...}
    与测试脚本中 data["workflow_id"] 相匹配
    """
    try:
        wf = WorkflowDef(**workflow_def)  # Pydantic 校验
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    wf_id = save_workflow_definition(wf.dict())  # 后端存储, 返回新工作流ID
    return {
        "message": "Workflow created",
        "workflow_id": wf_id
    }


def get_workflow(workflow_id: str):
    """
    返回 {"workflow_id": ..., "definition": ...}
    与测试脚本中:
      data = r.json()
      assert "definition" in data
      assert data["definition"]["StartAt"] == ...
    相匹配
    """
    wf_def = get_workflow_definition(workflow_id)
    if not wf_def:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": workflow_id,
        "definition": wf_def
    }


def update_workflow(workflow_id: str, workflow_def: dict):
    """
    返回同样格式, 只是改 "message" 显示
    """
    try:
        wf = WorkflowDef(**workflow_def)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    updated_id = save_workflow_definition(wf.dict(), workflow_id=workflow_id)
    return {
        "message": "Workflow updated",
        "workflow_id": updated_id
    }


def execute_workflow(workflow_id: str):
    """
    测试脚本中断言:
      r.json()["message"] == "Execution finished"
    因此这里返回 Execution finished
    """
    wf_def = get_workflow_definition(workflow_id)
    if not wf_def:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # 执行
    engine = WorkflowEngine(wf_def)
    engine.run()
    
    return {
        "message": "Execution finished",
        "workflow_id": workflow_id
    }