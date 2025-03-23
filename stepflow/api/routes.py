# stepflow/api/routes.py
from fastapi import APIRouter
from .controllers import create_workflow, get_workflow, update_workflow, execute_workflow

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