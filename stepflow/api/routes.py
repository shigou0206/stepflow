# stepflow/api/routes.py
from fastapi import APIRouter, HTTPException
from .controllers import create_workflow, get_workflow, update_workflow, execute_workflow
from stepflow.persistence.storage import get_workflow_context

router = APIRouter()

@router.post("/workflow", tags=["workflow"])
def create_workflow_api(workflow_def: dict):
    return create_workflow(workflow_def)

@router.get("/workflow/{workflow_id}", tags=["workflow"])
def get_workflow_api(workflow_id: str):
    return get_workflow(workflow_id)

@router.put("/workflow/{workflow_id}", tags=["workflow"])
def update_workflow_api(workflow_id: str, workflow_def: dict):
    return update_workflow(workflow_id, workflow_def)

@router.post("/workflow/{workflow_id}/execute", tags=["workflow"])
def execute_workflow_api(workflow_id: str):
    return execute_workflow(workflow_id)

@router.get("/workflow/{workflow_id}/context")
def get_workflow_context_api(workflow_id: str):
    """
    查询给定 workflow 的上下文(若有), 返回 { "context": {...} }
    """
    ctx = get_workflow_context(workflow_id)
    if not ctx:
        # 如果ctx是空, 你可能想区分"没找到" vs "context={}"; 
        # 这里先简单处理
        return {"context": {}}
    return {"context": ctx}