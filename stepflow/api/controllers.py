# stepflow/api/controllers.py
from fastapi import HTTPException
from stepflow.api.schemas import WorkflowDef
from stepflow.persistence.storage import (
    create_workflow_instance,
    get_workflow_definition_by_id,  # 此函数根据 instance_id 返回对应的 definition (instance.definition)
    update_instance_status
)
from stepflow.engine.executor import WorkflowEngine

def create_workflow(workflow_def: dict):
    """
    1. 校验 DSL
    2. 存入数据库（创建一个 WorkflowInstance，同时保存 DSL 到实例中）
    3. 返回 {"message": "Workflow created", "workflow_id": ...}
    """
    try:
        wf = WorkflowDef(**workflow_def)  # 使用 Pydantic 校验 DSL
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 创建 workflow instance，并返回实例ID
    wf_id = create_workflow_instance(wf.dict())
    return {
        "message": "Workflow created",
        "workflow_id": wf_id
    }

def get_workflow(workflow_id: str):
    """
    返回 {"workflow_id": ..., "definition": ...}
    这里 definition 从实例记录中取（注意：在新的设计中，
    DSL 存在 WorkflowDefinition 表中，get_workflow_definition 根据 instance_id 获取 definition）
    """
    wf_def = get_workflow_definition_by_id(workflow_id)
    if not wf_def:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": workflow_id,
        "definition": wf_def
    }

def update_workflow(workflow_id: str, workflow_def: dict):
    """
    更新工作流实例的 DSL（定义），返回更新信息
    注意：此处简单起见，直接调用 update_instance_status 来更新定义字段
    """
    try:
        wf = WorkflowDef(**workflow_def)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # 使用 update_instance_status 更新定义; 状态暂设为 "CREATED"（可根据实际需求调整）
    update_instance_status(
        instance_id=workflow_id,
        status="CREATED",
        context={},            # 这里重置上下文；你也可保留原有上下文
        definition=wf.dict()
    )
    return {
        "message": "Workflow updated",
        "workflow_id": workflow_id
    }

def execute_workflow(workflow_id: str):
    """
    根据 workflow_id 获取定义并执行工作流；
    测试时要求 r.json()["message"] == "Execution finished"
    """
    wf_def = get_workflow_definition_by_id(workflow_id)
    if not wf_def:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    engine = WorkflowEngine(wf_def)
    engine.run()
    
    return {
        "message": "Execution finished",
        "workflow_id": workflow_id
    }